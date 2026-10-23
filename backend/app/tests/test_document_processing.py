"""Regression tests for extraction-run status persistence and API responses."""

from app.core.security import create_access_token
from app.models.document_version import DocType, DocumentVersion, ProcessingStatus
from app.models.extracted_field import ExtractedField
from app.models.extraction_run import ExtractionRun, ExtractionStatus
from app.models.request import Request, RequestStatus, RequestType
from app.models.user import User, UserRole
from app.services.document_processing.processor import DocumentProcessor


SAMPLE_EXPENSE_TEXT = (
    "Employee: Alex Sharma\nMerchant: Acme Store\nDate: 10/21/2026\n"
    "Total: INR 1250.50\nPurpose: Client visit"
)


def _document(db_session):
    submitter = User(
        display_name="Extraction Test Submitter",
        email="extraction-test@example.com",
        password_hash="unused-test-hash",
        role=UserRole.submitter,
        is_active=True,
    )
    db_session.add(submitter)
    db_session.flush()
    request = Request(
        request_number="REQ-2099-7001",
        request_type=RequestType.expense_reimbursement,
        title="Extraction regression claim",
        submitter_id=submitter.id,
        status=RequestStatus.processing,
    )
    db_session.add(request)
    db_session.flush()
    document = DocumentVersion(
        request_id=request.id,
        doc_type=DocType.expense_form,
        original_filename="expense-form.pdf",
        storage_key="test/expense-form.pdf",
        mime_type="application/pdf",
        file_size=1,
        file_hash="a" * 64,
        version_number=1,
        uploader_id=submitter.id,
        processing_status=ProcessingStatus.pending,
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document, submitter


def _headers(user):
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


def _mock_extraction(monkeypatch):
    monkeypatch.setattr(
        DocumentProcessor,
        "_extract_pages",
        lambda self, doc: [(0, SAMPLE_EXPENSE_TEXT)],
    )
    monkeypatch.setattr(DocumentProcessor, "_run_ocr", lambda self, pages, run_id: [])


def test_successful_extraction_persists_success_fields_and_api_response(
    db_session, client, monkeypatch
):
    document, submitter = _document(db_session)
    _mock_extraction(monkeypatch)
    monkeypatch.setattr(DocumentProcessor, "_advance_and_verify", lambda self, doc: None)

    DocumentProcessor(db_session).process(document.id)
    db_session.expire_all()

    saved_document = db_session.get(DocumentVersion, document.id)
    run = db_session.query(ExtractionRun).filter_by(document_version_id=document.id).one()
    fields = db_session.query(ExtractedField).filter_by(extraction_run_id=run.id).all()
    assert saved_document.processing_status == ProcessingStatus.ready
    assert run.status == ExtractionStatus.success
    assert run.completed_at is not None
    assert {field.field_name: field.normalized_value for field in fields}["total_amount"] == "1250.50"

    response = client.get(
        f"/api/v1/documents/{document.id}/extraction", headers=_headers(submitter)
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "success"
    assert any(field["field_name"] == "total_amount" for field in payload["fields"])


def test_failed_extraction_persists_terminal_status_error_and_api_response(
    db_session, client, monkeypatch
):
    document, submitter = _document(db_session)

    def fail_extraction(self, doc):
        raise RuntimeError("synthetic extraction failure")

    monkeypatch.setattr(DocumentProcessor, "_extract_pages", fail_extraction)

    DocumentProcessor(db_session).process(document.id)
    db_session.expire_all()

    saved_document = db_session.get(DocumentVersion, document.id)
    run = db_session.query(ExtractionRun).filter_by(document_version_id=document.id).one()
    assert saved_document.processing_status == ProcessingStatus.failed
    assert saved_document.processing_error == "synthetic extraction failure"
    assert run.status == ExtractionStatus.failed
    assert run.error_details == "synthetic extraction failure"
    assert run.completed_at is not None
    assert db_session.query(ExtractedField).filter_by(extraction_run_id=run.id).count() == 0

    response = client.get(
        f"/api/v1/documents/{document.id}/extraction", headers=_headers(submitter)
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "failed"
    assert response.json()["error_details"] == "synthetic extraction failure"
    assert response.json()["fields"] == []


def test_verification_error_does_not_mark_successful_extraction_failed(
    db_session, monkeypatch
):
    document, _ = _document(db_session)
    _mock_extraction(monkeypatch)

    def fail_verification(self, doc):
        raise RuntimeError("synthetic verification failure")

    monkeypatch.setattr(DocumentProcessor, "_advance_and_verify", fail_verification)

    DocumentProcessor(db_session).process(document.id)
    db_session.expire_all()

    saved_document = db_session.get(DocumentVersion, document.id)
    run = db_session.query(ExtractionRun).filter_by(document_version_id=document.id).one()
    assert saved_document.processing_status == ProcessingStatus.ready
    assert run.status == ExtractionStatus.success
    assert db_session.query(ExtractedField).filter_by(extraction_run_id=run.id).count() > 0
