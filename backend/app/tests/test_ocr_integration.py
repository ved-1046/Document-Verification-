"""Focused OCR path tests using generated documents and the configured Tesseract binary."""

import io
from pathlib import Path

import fitz
import pytest
from PIL import Image, ImageDraw, ImageFont

from app.core.config import settings
from app.services.document_processing.normalizer import extract_fields
from app.services.document_processing.processor import DocumentProcessor
from app.services.ocr.engine import OCREngine
from app.models.document_version import DocType, DocumentVersion, ProcessingStatus
from app.models.extracted_field import ExtractedField
from app.models.extraction_run import ExtractionRun, ExtractionStatus
from app.models.request import Request, RequestStatus, RequestType
from app.models.user import User, UserRole


FORM_TEXT = (
    "SAMPLE EXPENSE REIMBURSEMENT FORM\n"
    "Employee name: Alex Sharma\n"
    "Expense date: 22 October 2026\n"
    "Amount claimed: INR 2,000.00\n"
    "Business purpose: Local travel for work meeting"
)
RECEIPT_TEXT = (
    "SAMPLE RECEIPT\n"
    "Merchant: Acme Transit\n"
    "Date: 22 October 2026\n"
    "TOTAL: INR 2,000.00\n"
    "Reference: OCR-TEST-2026"
)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    windows_font = "C:/Windows/Fonts/arial.ttf"
    try:
        return ImageFont.truetype(windows_font, size)
    except OSError:
        return ImageFont.load_default(size=size)


def _known_text_image(text: str) -> Image.Image:
    image = Image.new("RGB", (1800, 1200), "white")
    draw = ImageDraw.Draw(image)
    font = _font(58)
    for line_number, line in enumerate(text.splitlines()):
        draw.text((100, 100 + line_number * 150), line, fill="black", font=font)
    return image


def _scanned_pdf_bytes(text: str) -> bytes:
    image = _known_text_image(text)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    pdf = fitz.open()
    page = pdf.new_page(width=612, height=792)
    page.insert_image(page.rect, stream=buffer.getvalue())
    result = pdf.tobytes()
    pdf.close()
    return result


@pytest.fixture
def tesseract_engine():
    engine = OCREngine(settings.tesseract_cmd or None)
    if not engine.is_available:
        pytest.skip(f"Tesseract with eng data is unavailable: {engine.unavailable_reason}")
    return engine


def test_native_text_pdf_stays_on_native_extraction_path(tmp_path, monkeypatch, tesseract_engine):
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((50, 60), FORM_TEXT, fontsize=14)
    path = tmp_path / "native-expense-form.pdf"
    pdf.save(path)
    pdf.close()

    processor = DocumentProcessor(db=None)
    processor.ocr = tesseract_engine

    def unexpected_ocr(*_args, **_kwargs):
        raise AssertionError("Native text PDF should not invoke Tesseract")

    monkeypatch.setattr(processor.ocr, "extract_blocks", unexpected_ocr)
    pages = processor._extract_pdf(path)
    fields = extract_fields("\n".join(text for _, text in pages))
    assert pages[0][1].startswith("SAMPLE EXPENSE REIMBURSEMENT FORM")
    assert fields["employee_name"] == "Alex Sharma"
    assert fields["expense_date"] == "2026-10-22"
    assert fields["total_amount"] == "2000.00"


def test_scanned_pdf_uses_tesseract_fallback_and_normalizes_known_values(tmp_path, tesseract_engine):
    path = tmp_path / "scanned-receipt.pdf"
    path.write_bytes(_scanned_pdf_bytes(RECEIPT_TEXT))
    processor = DocumentProcessor(db=None)
    processor.ocr = tesseract_engine

    pages = processor._extract_pdf(path)
    fields = extract_fields("\n".join(text for _, text in pages))
    raw_blocks = processor._raw_ocr_blocks[0]

    assert len(raw_blocks) > 5
    assert any(block.confidence is not None and block.bbox for block in raw_blocks)
    assert fields["merchant_name"] == "Acme Transit"
    assert fields["expense_date"] == "2026-10-22"
    assert fields["total_amount"] == "2000.00"


def test_exact_synthetic_receipt_runs_through_persisted_extraction_pipeline(
    db_session, isolated_storage, tesseract_engine
):
    fixture = Path(__file__).parent / "fixtures" / "synthetic_scanned_receipt_OCR_TEST.pdf"
    storage_key = "ocr-tests/exact-synthetic-receipt.pdf"
    stored_file = isolated_storage / storage_key
    stored_file.parent.mkdir(parents=True, exist_ok=True)
    stored_file.write_bytes(fixture.read_bytes())

    user = User(
        display_name="OCR Regression Submitter",
        email="ocr-regression@example.com",
        password_hash="test-only",
        role=UserRole.submitter,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    request = Request(
        request_number="REQ-2099-8002",
        request_type=RequestType.expense_reimbursement,
        title="Exact synthetic receipt OCR test",
        submitter_id=user.id,
        status=RequestStatus.processing,
    )
    db_session.add(request)
    db_session.flush()
    document = DocumentVersion(
        request_id=request.id,
        doc_type=DocType.receipt,
        original_filename=fixture.name,
        storage_key=storage_key,
        mime_type="application/pdf",
        file_size=stored_file.stat().st_size,
        file_hash="c" * 64,
        version_number=1,
        uploader_id=user.id,
        processing_status=ProcessingStatus.pending,
    )
    db_session.add(document)
    db_session.commit()

    processor = DocumentProcessor(db_session)
    processor.ocr = tesseract_engine
    processor.process(document.id)
    db_session.expire_all()

    saved_document = db_session.get(DocumentVersion, document.id)
    run = db_session.query(ExtractionRun).filter_by(document_version_id=document.id).one()
    stored_fields = db_session.query(ExtractedField).filter_by(extraction_run_id=run.id).all()
    normalized = {field.field_name: field.normalized_value for field in stored_fields}
    raw_fields = [field for field in stored_fields if field.field_name == "_raw_page_text"]

    assert saved_document.processing_status == ProcessingStatus.ready
    assert run.status == ExtractionStatus.success
    assert normalized["merchant_name"] == "ABC Stationery"
    assert normalized["expense_date"] == "2026-10-22"
    assert normalized["currency"] == "INR"
    assert normalized["total_amount"] == "450.00"
    assert normalized["reference_number"] == "OCR-TEST-450"
    assert normalized["expense_purpose"] == "OCR integration test"
    assert any(field.confidence is not None and field.bounding_box for field in raw_fields)


def test_supported_image_uses_tesseract_and_normalizes_known_values(tmp_path, tesseract_engine):
    path = tmp_path / "expense-form.png"
    _known_text_image(FORM_TEXT).save(path)
    processor = DocumentProcessor(db=None)
    processor.ocr = tesseract_engine

    pages = processor._extract_image(path)
    fields = extract_fields("\n".join(text for _, text in pages))

    assert fields["employee_name"] == "Alex Sharma"
    assert fields["expense_date"] == "2026-10-22"
    assert fields["total_amount"] == "2000.00"
    assert fields["expense_purpose"] == "Local travel for work meeting"


def test_scanned_pdf_ocr_results_are_persisted_by_the_document_processor(
    tmp_path, db_session, isolated_storage, tesseract_engine
):
    user = User(
        display_name="OCR Pipeline Submitter",
        email="ocr-pipeline@example.com",
        password_hash="test-only",
        role=UserRole.submitter,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    request = Request(
        request_number="REQ-2099-8001",
        request_type=RequestType.expense_reimbursement,
        title="Scanned receipt OCR test",
        submitter_id=user.id,
        status=RequestStatus.processing,
    )
    db_session.add(request)
    db_session.flush()
    storage_key = "ocr-tests/scanned-receipt.pdf"
    stored_file = isolated_storage / storage_key
    stored_file.parent.mkdir(parents=True, exist_ok=True)
    stored_file.write_bytes(_scanned_pdf_bytes(RECEIPT_TEXT))
    document = DocumentVersion(
        request_id=request.id,
        doc_type=DocType.receipt,
        original_filename="scanned-receipt.pdf",
        storage_key=storage_key,
        mime_type="application/pdf",
        file_size=stored_file.stat().st_size,
        file_hash="b" * 64,
        version_number=1,
        uploader_id=user.id,
        processing_status=ProcessingStatus.pending,
    )
    db_session.add(document)
    db_session.commit()

    processor = DocumentProcessor(db_session)
    processor.ocr = tesseract_engine
    processor.process(document.id)
    db_session.expire_all()

    saved_document = db_session.get(DocumentVersion, document.id)
    run = db_session.query(ExtractionRun).filter_by(document_version_id=document.id).one()
    stored_fields = db_session.query(ExtractedField).filter_by(extraction_run_id=run.id).all()
    normalized = {field.field_name: field.normalized_value for field in stored_fields}
    raw_ocr_fields = [field for field in stored_fields if field.field_name == "_raw_page_text"]
    assert saved_document.processing_status == ProcessingStatus.ready
    assert run.status == ExtractionStatus.success
    assert run.ocr_engine == "tesseract"
    assert normalized["merchant_name"] == "Acme Transit"
    assert normalized["expense_date"] == "2026-10-22"
    assert normalized["total_amount"] == "2000.00"
    assert raw_ocr_fields and any(field.confidence is not None for field in raw_ocr_fields)


def test_low_confidence_ocr_text_is_not_used_for_normalized_fields(tmp_path, monkeypatch):
    image_path = tmp_path / "low-confidence.png"
    _known_text_image(RECEIPT_TEXT).save(image_path)
    processor = DocumentProcessor(db=None)

    class LowConfidenceOCR:
        is_available = True

        def extract_blocks(self, _image, page=0):
            from app.services.ocr.engine import TextBlock
            return [TextBlock("TOTAL", page=page, confidence=0.20)]

        @staticmethod
        def reliable_text(_blocks, _threshold):
            return ""

    processor.ocr = LowConfidenceOCR()
    page_text = processor._extract_image(image_path)[0][1]
    assert page_text == ""
    assert extract_fields(page_text)["total_amount"] is None


def test_missing_executable_and_english_language_data_are_reported(monkeypatch):
    missing_executable = OCREngine(r"C:\missing\tesseract.exe")
    assert not missing_executable.is_available
    assert missing_executable.unavailable_reason
    processor = DocumentProcessor(db=None)
    processor.ocr = missing_executable
    with pytest.raises(RuntimeError, match="Tesseract OCR is unavailable"):
        processor._require_ocr()

    import pytesseract
    monkeypatch.setattr(pytesseract, "get_tesseract_version", lambda: "5.5")
    monkeypatch.setattr(pytesseract, "get_languages", lambda config="": ["osd"])
    missing_language = OCREngine()
    assert not missing_language.is_available
    assert "eng.traineddata" in missing_language.unavailable_reason
    processor.ocr = missing_language
    with pytest.raises(RuntimeError, match="eng.traineddata"):
        processor._require_ocr()
