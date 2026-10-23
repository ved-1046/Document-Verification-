"""
Document processor: orchestrates OCR + structured extraction for a single DocumentVersion.

Flow:
1. Load DocumentVersion record from DB
2. Detect file type: PDF or image
3. For PDF: try fitz text extraction first; fall back to image-render OCR (max 10 pages)
4. For images: OCR directly
5. Store ExtractionRun + ExtractedField rows
6. Update processing_status on DocumentVersion
7. After successful extraction: trigger verification runner
8. If OCR binary unavailable or any error: set processing_failed, keep original file
"""
from datetime import datetime, timezone
import logging
from pathlib import Path
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document_version import DocumentVersion, ProcessingStatus
from app.models.extraction_run import ExtractionRun, ExtractionStatus
from app.models.extracted_field import ExtractedField
from app.models.request import RequestStatus
from app.services.ocr.engine import OCREngine, TextBlock
from app.services.document_processing.normalizer import extract_fields
from app.services.audit.logger import log_event
from app.models.audit_event import AuditEventType

MAX_PAGES = 10
MIN_OCR_CONFIDENCE = 0.50
logger = logging.getLogger(__name__)


class DocumentProcessor:
    def __init__(self, db: Session):
        self.db = db
        self.ocr = OCREngine(tesseract_cmd=settings.tesseract_cmd or None)
        self._raw_ocr_blocks: dict[int, list[TextBlock]] = {}

    def process(self, doc_version_id: int) -> None:
        """Entry point — handles all errors internally."""
        db = self.db
        doc = db.get(DocumentVersion, doc_version_id)
        if not doc:
            return

        doc.processing_status = ProcessingStatus.processing
        doc.processing_error = None
        db.commit()

        run = ExtractionRun(
            document_version_id=doc_version_id,
            ocr_engine=self.ocr.engine_name,
            status=ExtractionStatus.running,
        )
        db.add(run)
        # Persist the running record first so extraction errors can be recorded
        # after rolling back any partially-created extracted fields.
        db.commit()
        run_id = run.id

        try:
            page_texts = self._extract_pages(doc)
            # Preserve OCR line boundaries: labeled amounts can have the
            # currency/value on the next line, and headings span OCR tokens.
            full_text = "\n".join(text for _, text in page_texts).strip()
            if not full_text:
                # Differentiate blank documents from blurry / unreadable documents
                all_blocks = [b for blocks in self._raw_ocr_blocks.values() for b in blocks]
                if not all_blocks:
                    raise RuntimeError("No readable content found. Please upload a document containing the expense details.")
                confs = [b.confidence for b in all_blocks if b.confidence is not None]
                avg_conf = sum(confs) / len(confs) if confs else 0.0
                if avg_conf < 0.40:
                    raise RuntimeError("This document is difficult to read. Please upload a clearer photo or scan.")
                raise RuntimeError("No readable content found. Please upload a document containing the expense details.")
            fields_by_page = self._run_ocr(page_texts, run.id)

            # Build one unified text corpus for field normalization
            normalized = extract_fields(full_text)

            # Store fields — extracted_value = raw text, normalized_value = parsed value
            for field_name, norm_val in normalized.items():
                # Find the first block that contributed to this field (best-effort)
                ef = ExtractedField(
                    extraction_run_id=run.id,
                    field_name=field_name,
                    extracted_value=norm_val,      # For now same as normalized; raw blocks stored per-block below
                    normalized_value=norm_val,
                )
                db.add(ef)

            # Also save raw blocks for Evidence Lens bounding-box support
            for block_ef in fields_by_page:
                db.add(block_ef)

            run.status = ExtractionStatus.success
            run.completed_at = datetime.now(timezone.utc)
            doc.processing_status = ProcessingStatus.ready
            doc.processing_error = None

            log_event(db, AuditEventType.extraction_completed,
                      request_id=doc.request_id, entity_type="extraction_run",
                      entity_id=run.id, summary=f"OCR completed (engine={self.ocr.engine_name})")

            # Auto-populate request fields from receipt extraction if not already set
            try:
                from app.models.request import Request
                from app.models.document_version import DocType
                from decimal import Decimal
                from datetime import date
                req = db.get(Request, doc.request_id)
                if req and req.status in (RequestStatus.draft, RequestStatus.processing, RequestStatus.submitted):
                    if doc.doc_type == DocType.receipt:
                        if req.claimed_amount is None and normalized.get("total_amount"):
                            try:
                                req.claimed_amount = Decimal(normalized["total_amount"])
                            except Exception:
                                pass
                        if req.expense_date is None and normalized.get("expense_date"):
                            try:
                                req.expense_date = date.fromisoformat(normalized["expense_date"])
                            except Exception:
                                pass
                        if (not req.currency or req.currency == "INR") and normalized.get("currency"):
                            req.currency = normalized["currency"]
                        if normalized.get("merchant_name"):
                            merchant = normalized["merchant_name"].strip()
                            if not req.title or any(req.title.lower().startswith(p) for p in ("expense reimbursement", "untitled claim", "new expense claim", "general expense")):
                                req.title = f"{merchant} Reimbursement"
                    db.flush()
            except Exception as e:
                logger.warning("Could not auto-populate request fields from extraction: %s", e)

            db.commit()

        except Exception as exc:
            db.rollback()
            # Re-fetch after rollback
            doc = db.get(DocumentVersion, doc_version_id)
            run = db.get(ExtractionRun, run_id)
            if doc:
                doc.processing_status = ProcessingStatus.failed
                doc.processing_error = str(exc)[:500]
            if run:
                run.status = ExtractionStatus.failed
                run.completed_at = datetime.now(timezone.utc)
                run.error_details = str(exc)[:500]

            req = db.get(__import__('app.models.request', fromlist=['Request']).Request,
                         doc.request_id) if doc else None
            if req and req.status == RequestStatus.processing:
                req.status = RequestStatus.processing_failed

            db.commit()
            return

        # Verification is downstream of extraction. A verification error must
        # not roll back successfully extracted fields or relabel OCR as failed.
        try:
            self._advance_and_verify(doc)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Post-extraction verification failed for document %s", doc_version_id)

    def _extract_pages(self, doc: DocumentVersion) -> list[tuple[int, str]]:
        """
        Returns list of (page_index, page_text) tuples.
        For PDFs: tries text extraction then image fallback.
        For images: direct OCR.
        """
        from app.services.storage_service import get_file_path
        path = get_file_path(doc.storage_key)

        if doc.mime_type == "application/pdf":
            return self._extract_pdf(path)
        else:
            return self._extract_image(path)

    def _extract_pdf(self, path: Path) -> list[tuple[int, str]]:
        import fitz
        from PIL import Image, ImageStat
        import io

        pdf = fitz.open(str(path))
        pages: list[tuple[int, str]] = []
        self._raw_ocr_blocks = {}
        had_content_page = False
        try:
            for i, page in enumerate(pdf):
                if i >= MAX_PAGES:
                    break
                # Preserve native text extraction; OCR only pages without enough text.
                text = page.get_text("text").strip()
                if len(text) > 50:
                    pages.append((i, text))
                    had_content_page = True
                    continue
                self._require_ocr()
                pix = page.get_pixmap(dpi=250, alpha=False)
                with Image.open(io.BytesIO(pix.tobytes("png"))) as source:
                    image = source.convert("RGB")
                stat = ImageStat.Stat(image.convert("L"))
                min_v, max_v = stat.extrema[0]
                if (max_v - min_v) < 15 or stat.stddev[0] < 8.0:
                    continue  # Skip blank page in multi-page PDF
                had_content_page = True
                blocks = self.ocr.extract_blocks(image, page=i)
                self._raw_ocr_blocks[i] = blocks
                reliable_text = self.ocr.reliable_text(blocks, MIN_OCR_CONFIDENCE)
                if reliable_text.strip():
                    pages.append((i, reliable_text))
            if not pages:
                if not had_content_page:
                    raise RuntimeError("No readable content found. Please upload a document containing the expense details.")
                raise RuntimeError("This document is difficult to read. Please upload a clearer photo or scan.")
        finally:
            pdf.close()
        return pages

    def _extract_image(self, path: Path) -> list[tuple[int, str]]:
        from PIL import Image, ImageStat
        self._require_ocr()
        self._raw_ocr_blocks = {}
        with Image.open(str(path)) as source:
            image = source.convert("RGB")

        # Blank & resolution assessment
        stat = ImageStat.Stat(image.convert("L"))
        min_v, max_v = stat.extrema[0]
        if (max_v - min_v) < 15 or stat.stddev[0] < 8.0:
            raise RuntimeError("No readable content found. Please upload a document containing the expense details.")
        if image.width < 150 or image.height < 150:
            raise RuntimeError("This document is difficult to read due to low resolution. Please upload a clearer photo or scan.")

        blocks = self.ocr.extract_blocks(image, page=0)
        self._raw_ocr_blocks[0] = blocks
        reliable_text = self.ocr.reliable_text(blocks, MIN_OCR_CONFIDENCE)

        return [(0, reliable_text)]

    def _require_ocr(self) -> None:
        if self.ocr.is_available:
            return
        reason = self.ocr.unavailable_reason
        if reason and "language data" in reason.lower():
            raise RuntimeError(reason)
        raise RuntimeError(
            "Tesseract OCR is unavailable. Install Tesseract, install the eng language data, "
            "and set TESSERACT_CMD to the executable path."
            + (f" Details: {reason}" if reason else "")
        )

    def _run_ocr(self, page_texts: list[tuple[int, str]], run_id: int) -> list[ExtractedField]:
        """Store raw OCR blocks as ExtractedField rows for Evidence Lens."""
        fields = []
        for page_idx, text in page_texts:
            raw_blocks = self._raw_ocr_blocks.get(page_idx)
            if raw_blocks:
                for block in raw_blocks:
                    if not block.text.strip():
                        continue
                    fields.append(ExtractedField(
                        extraction_run_id=run_id,
                        field_name="_raw_page_text",
                        extracted_value=block.text[:2000],
                        normalized_value=None,
                        page_number=page_idx,
                        bounding_box=block.bbox,
                        confidence=block.confidence,
                    ))
                continue
            if text.strip():
                ef = ExtractedField(
                    extraction_run_id=run_id,
                    field_name="_raw_page_text",
                    extracted_value=text[:2000],
                    normalized_value=None,
                    page_number=page_idx,
                )
                fields.append(ef)
        return fields

    def _advance_and_verify(self, doc: DocumentVersion) -> None:
        """Move the parent request to under_review and run checks."""
        from app.models.request import Request
        from app.services.verification.runner import run_all_checks

        req = self.db.get(Request, doc.request_id)
        if not req:
            return
        from app.services.request_service import advance_if_processing_complete
        advance_if_processing_complete(self.db, req)
        self.db.flush()

        # Run all verification checks
        run_all_checks(self.db, req.id)
