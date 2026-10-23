"""
Storage service — abstracts all filesystem operations.

Design decisions:
- Files stored under STORAGE_DIR/{request_id}/{version_number}_{doc_type}_{original_name}
- Storage keys are relative paths (never absolute) so the directory can be moved
- Path traversal: reject any storage_key that tries to escape STORAGE_DIR
- Original file always saved BEFORE processing begins; if processing fails, the file
  remains on disk and in document_versions with processing_status=failed
"""
import hashlib
import io
import shutil
from pathlib import Path
from fastapi import HTTPException, UploadFile, status
from app.core.config import settings

ALLOWED_MIME = {"image/png", "image/jpeg", "application/pdf"}


def _safe_path(storage_key: str) -> Path:
    """Resolve storage_key relative to STORAGE_DIR and guard against traversal."""
    base = settings.storage_path.resolve()
    target = (base / storage_key).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid storage key.",
        )
    return target


def validate_upload(file: UploadFile) -> None:
    """Raise 415 for bad MIME type; size is checked after reading."""
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type '{file.content_type}'. "
                f"Accepted: PNG, JPEG, PDF."
            ),
        )


async def save_upload(
    file: UploadFile,
    request_id: int,
    version_number: int,
    doc_type: str,
) -> tuple[str, int, str]:
    """
    Save an uploaded file to storage.

    Returns:
        (storage_key, file_size_bytes, sha256_hex)

    Raises:
        413 if file exceeds MAX_UPLOAD_MB
        422 if file appears corrupt (zero bytes)
    """
    # Read full content
    content = await file.read()
    size = len(content)

    if size == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file appears to be empty or corrupt.",
        )
    if size > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File size {size / 1_048_576:.1f} MB exceeds the "
                f"{settings.max_upload_mb} MB limit."
            ),
        )

    # Validate the actual file signature, not just the browser supplied MIME.
    if file.content_type == "application/pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="The uploaded file is not a valid PDF.")
    if file.content_type == "image/png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=422, detail="The uploaded file is not a valid PNG image.")
    if file.content_type == "image/jpeg" and not content.startswith(b"\xff\xd8\xff"):
        raise HTTPException(status_code=422, detail="The uploaded file is not a valid JPEG image.")
    try:
        if file.content_type == "application/pdf":
            import fitz
            with fitz.open(stream=content, filetype="pdf") as pdf:
                if not pdf.page_count:
                    raise ValueError("PDF contains no pages")
        else:
            from PIL import Image
            with Image.open(io.BytesIO(content)) as image:
                image.verify()
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail="Uploaded document is corrupt or cannot be opened.",
        ) from exc

    # Compute hash
    sha256 = hashlib.sha256(content).hexdigest()

    # Build safe filename
    safe_name = Path(file.filename or "document").name.replace(" ", "_")
    storage_key = f"{request_id}/v{version_number}_{doc_type}_{safe_name}"
    dest = _safe_path(storage_key)
    dest.parent.mkdir(parents=True, exist_ok=True)

    dest.write_bytes(content)
    return storage_key, size, sha256


def get_file_path(storage_key: str) -> Path:
    """Return the absolute path for a storage_key, guarded against traversal."""
    path = _safe_path(storage_key)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found.",
        )
    return path


def delete_if_exists(storage_key: str) -> None:
    """Remove a file from storage; silently ignore if it doesn't exist."""
    try:
        _safe_path(storage_key).unlink(missing_ok=True)
    except Exception:
        pass
