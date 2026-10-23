"""
Documents API router.

POST /api/v1/requests/{request_id}/documents          — Upload a document (submitter)
GET  /api/v1/requests/{request_id}/documents          — List document versions for a request
GET  /api/v1/documents/history                        — Version history (role-filtered)
GET  /api/v1/documents/{doc_id}/download              — Authorized file download
GET  /api/v1/documents/{doc_id}/extraction            — Get OCR extraction results
GET  /api/v1/documents/{doc_id}/page/{page_num}       — Get rendered page image
POST /api/v1/documents/{doc_id}/reprocess             — Retry processing (reviewer/approver)
"""
from fastapi import APIRouter, BackgroundTasks, Depends, Query, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker
from typing import Optional
import io

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.document_version import DocumentVersion, DocType, ProcessingStatus
from app.models.extraction_run import ExtractionRun
from app.models.user import User, UserRole
from app.schemas.request import DocumentVersionRead, ExtractionRunRead
from app.services import storage_service
from app.models.request import Request, RequestStatus
from app.models.user import UserRole
from app.services.request_service import (
    assert_can_view,
    assert_submitter_can_upload,
    get_request_or_404,
)
from app.services.audit.logger import log_event
from app.models.audit_event import AuditEventType

router = APIRouter(tags=["documents"])


@router.post("/requests/{request_id}/documents",
             response_model=DocumentVersionRead, status_code=201,
             summary="Upload a document to a request")
async def upload_document(
    request_id: int,
    background_tasks: BackgroundTasks,
    doc_type: DocType = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = get_request_or_404(db, request_id)
    assert_submitter_can_upload(user, req)

    # Validate MIME type before touching the DB
    storage_service.validate_upload(file)

    # Compute next version number for this doc_type
    existing_count = db.query(DocumentVersion).filter(
        DocumentVersion.request_id == request_id,
        DocumentVersion.doc_type == doc_type,
    ).count()
    version_number = existing_count + 1

    # Save file to disk (before any DB writes so we never lose the file)
    storage_key, file_size, file_hash = await storage_service.save_upload(
        file, request_id, version_number, doc_type.value
    )

    # Create DocumentVersion record
    doc = DocumentVersion(
        request_id=request_id,
        doc_type=doc_type,
        original_filename=file.filename or "document",
        mime_type=file.content_type,
        file_size=file_size,
        file_hash=file_hash,
        storage_key=storage_key,
        version_number=version_number,
        uploader_id=user.id,
        processing_status=ProcessingStatus.pending,
    )
    db.add(doc)
    db.flush()

    log_event(db, AuditEventType.document_uploaded, actor_id=user.id,
              request_id=request_id, entity_type="document_version",
              entity_id=doc.id, summary=f"Uploaded {doc_type.value} v{version_number}")

    db.commit()
    db.refresh(doc)

    # Kick off OCR in the background
    background_tasks.add_task(_process_document, doc.id, db.get_bind())
    return doc


@router.get("/requests/{request_id}/documents",
            response_model=list[DocumentVersionRead],
            summary="List all document versions for a request")
def list_documents(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = get_request_or_404(db, request_id)
    assert_can_view(user, req)
    return db.query(DocumentVersion).filter(
        DocumentVersion.request_id == request_id
    ).order_by(DocumentVersion.uploaded_at.asc()).all()


@router.get("/documents/history",
            summary="List document versions across requests (preserves all versions)")
def document_history(
    request_id: Optional[int] = Query(None, description="Filter to a single request"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = (
        db.query(DocumentVersion, Request)
        .join(Request, DocumentVersion.request_id == Request.id)
        .order_by(DocumentVersion.uploaded_at.desc())
    )
    if user.role == UserRole.submitter:
        q = q.filter(Request.submitter_id == user.id)
    elif user.role == UserRole.reviewer:
        q = q.filter(Request.assigned_reviewer_id == user.id)
    elif user.role == UserRole.approver:
        q = q.filter(Request.assigned_approver_id == user.id)
    if request_id is not None:
        req = get_request_or_404(db, request_id)
        assert_can_view(user, req)
        q = q.filter(DocumentVersion.request_id == request_id)

    rows = q.limit(500).all()
    return [
        {
            "id": doc.id,
            "request_id": doc.request_id,
            "request_number": req.request_number,
            "request_title": req.title,
            "request_status": req.status.value,
            "doc_type": doc.doc_type.value,
            "version_number": doc.version_number,
            "original_filename": doc.original_filename,
            "mime_type": doc.mime_type,
            "file_size": doc.file_size,
            "uploader_id": doc.uploader_id,
            "uploader_name": doc.uploader.display_name,
            "uploaded_at": doc.uploaded_at.isoformat(),
            "processing_status": doc.processing_status.value,
            "processing_error": doc.processing_error,
        }
        for doc, req in rows
    ]


@router.get("/documents/{doc_id}/download",
            summary="Authorized file download")
def download_document(
    doc_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = db.get(DocumentVersion, doc_id)
    if not doc:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=404, detail="Document not found.")
    req = get_request_or_404(db, doc.request_id)
    assert_can_view(user, req)
    path = storage_service.get_file_path(doc.storage_key)
    return FileResponse(
        path=str(path),
        filename=doc.original_filename,
        media_type=doc.mime_type,
    )


@router.get("/documents/{doc_id}/extraction",
            summary="Get OCR extraction results for a document version")
def get_extraction(
    doc_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = db.get(DocumentVersion, doc_id)
    if not doc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Document not found.")
    req = get_request_or_404(db, doc.request_id)
    assert_can_view(user, req)

    run = db.query(ExtractionRun).filter(
        ExtractionRun.document_version_id == doc_id
    ).order_by(ExtractionRun.started_at.desc()).first()

    if not run:
        return {"status": "no_extraction", "fields": []}

    fields = [
        {
            "id": f.id,
            "field_name": f.field_name,
            "extracted_value": f.extracted_value,
            "normalized_value": f.normalized_value,
            "page_number": f.page_number,
            "bounding_box": f.bounding_box,
            "confidence": f.confidence,
        }
        for f in run.extracted_fields
    ]
    return {
        "run_id": run.id,
        "ocr_engine": run.ocr_engine,
        "status": run.status.value,
        "error_details": run.error_details,
        "fields": fields,
    }


@router.get("/documents/{doc_id}/page/{page_num}",
            summary="Get a rendered page image from a document")
def get_page_image(
    doc_id: int,
    page_num: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    import fitz  # PyMuPDF
    from fastapi import HTTPException

    doc_record = db.get(DocumentVersion, doc_id)
    if not doc_record:
        raise HTTPException(status_code=404, detail="Document not found.")
    req = get_request_or_404(db, doc_record.request_id)
    assert_can_view(user, req)

    path = storage_service.get_file_path(doc_record.storage_key)

    try:
        pdf = fitz.open(str(path))
        if page_num < 0 or page_num >= len(pdf):
            raise HTTPException(status_code=404, detail=f"Page {page_num} not found.")
        page = pdf[page_num]
        pix = page.get_pixmap(dpi=120)
        img_bytes = pix.tobytes("png")
        pdf.close()
    except Exception as e:
        if "404" in str(e):
            raise
        raise HTTPException(status_code=422, detail=f"Could not render page: {e}")

    return StreamingResponse(io.BytesIO(img_bytes), media_type="image/png")


@router.post("/documents/{doc_id}/reprocess",
             status_code=202,
             summary="Retry OCR processing for a document (reviewer/approver)")
def reprocess_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.reviewer, UserRole.approver)),
):
    doc = db.get(DocumentVersion, doc_id)
    if not doc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Document not found.")
    req = get_request_or_404(db, doc.request_id)
    assert_can_view(user, req)

    doc.processing_status = ProcessingStatus.pending
    doc.processing_error = None
    db.commit()

    background_tasks.add_task(_process_document, doc_id, db.get_bind())
    return {"detail": "Reprocessing queued.", "document_version_id": doc_id}


def _process_document(doc_version_id: int, bind=None) -> None:
    """Background task: run OCR + verification on a document version."""
    from app.services.document_processing.processor import DocumentProcessor

    # Use the same database bind as the request endpoint. This also keeps
    # background processing inside isolated test databases when dependencies
    # are overridden by the test client.
    db = sessionmaker(bind=bind)() if bind is not None else None
    if db is None:
        from app.db.session import SessionLocal
        db = SessionLocal()
    try:
        processor = DocumentProcessor(db)
        processor.process(doc_version_id)
    finally:
        db.close()
