from datetime import date
from decimal import Decimal

from app.models.document_version import DocType, DocumentVersion, ProcessingStatus
from app.models.extracted_field import ExtractedField
from app.models.extraction_run import ExtractionRun, ExtractionStatus
from app.models.request import Request, RequestStatus, RequestType
from app.models.user import User, UserRole
from app.models.verification_check import CheckResult
from app.services.verification.runner import run_all_checks
from app.services.verification.check_a_missing import run as run_missing_check
from app.services.verification.check_b_amount import run as run_amount_check
from app.services.verification.check_c_date import run as run_date_check


def test_successful_checks_use_supported_pass_result_enum(db_session):
    submitter = User(
        display_name="Verification Test Submitter",
        email="verification-test@example.com",
        password_hash="unused-test-hash",
        role=UserRole.submitter,
        is_active=True,
    )
    db_session.add(submitter)
    db_session.flush()
    request = Request(
        request_number="REQ-2099-7002",
        request_type=RequestType.expense_reimbursement,
        title="Verification regression claim",
        submitter_id=submitter.id,
        status=RequestStatus.processing,
        claimed_amount=Decimal("2000.00"),
        expense_date=date(2026, 10, 22),
    )
    db_session.add(request)
    db_session.flush()

    for index, doc_type in enumerate((DocType.expense_form, DocType.receipt), start=1):
        document = DocumentVersion(
            request_id=request.id,
            doc_type=doc_type,
            original_filename=f"{doc_type.value}.pdf",
            storage_key=f"test/{doc_type.value}.pdf",
            mime_type="application/pdf",
            file_size=1,
            file_hash=str(index) * 64,
            version_number=1,
            uploader_id=submitter.id,
            processing_status=ProcessingStatus.ready,
        )
        db_session.add(document)
        db_session.flush()
        run = ExtractionRun(
            document_version_id=document.id,
            ocr_engine="test-text",
            status=ExtractionStatus.success,
        )
        db_session.add(run)
        db_session.flush()
        fields = {
            "employee_name": "Alex Submitter",
            "expense_date": "2026-10-22",
            "total_amount": "2000.00",
        }
        if doc_type == DocType.receipt:
            fields["merchant_name"] = "Sample Transport Provider"
        db_session.add_all(
            ExtractedField(
                extraction_run_id=run.id,
                field_name=name,
                extracted_value=value,
                normalized_value=value,
            )
            for name, value in fields.items()
        )

    db_session.flush()
    checks = run_all_checks(db_session, request.id)
    db_session.flush()
    passing = [c for c in checks if c.result == CheckResult.pass_]
    assert len(passing) == 4  # Two required-field checks, amount match, date match.

    receipt = db_session.query(DocumentVersion).filter_by(request_id=request.id, doc_type=DocType.receipt).one()
    receipt_run = db_session.query(ExtractionRun).filter_by(document_version_id=receipt.id).one()
    receipt_amount = db_session.query(ExtractedField).filter_by(
        extraction_run_id=receipt_run.id, field_name="total_amount"
    ).one()
    receipt_amount.normalized_value = "2100.00"
    mismatch = run_amount_check(db_session, request.id)
    assert mismatch.result == CheckResult.flag
    assert "discrepancy" in mismatch.explanation

    receipt_amount.normalized_value = None
    missing_amount = run_amount_check(db_session, request.id)
    assert missing_amount.result == CheckResult.info
    assert "could not run" in missing_amount.explanation

    receipt_date = db_session.query(ExtractedField).filter_by(
        extraction_run_id=receipt_run.id, field_name="expense_date"
    ).one()
    receipt_date.normalized_value = "10/11/2026"
    ambiguous_date = run_date_check(db_session, request.id)
    assert ambiguous_date.result == CheckResult.info
    assert "ambiguous or invalid" in ambiguous_date.explanation

    receipt.processing_status = ProcessingStatus.failed
    receipt_run.status = ExtractionStatus.failed
    failed_extraction_amount = run_amount_check(db_session, request.id)
    failed_extraction_date = run_date_check(db_session, request.id)
    assert failed_extraction_amount.result == CheckResult.info
    assert failed_extraction_date.result == CheckResult.info


def test_document_without_successful_extraction_is_reported_for_review(db_session):
    submitter = User(
        display_name="Pending Extraction Submitter",
        email="pending-extraction@example.com",
        password_hash="unused-test-hash",
        role=UserRole.submitter,
        is_active=True,
    )
    db_session.add(submitter)
    db_session.flush()
    request = Request(
        request_number="REQ-2099-7003",
        request_type=RequestType.expense_reimbursement,
        title="Pending extraction check",
        submitter_id=submitter.id,
        status=RequestStatus.processing,
    )
    db_session.add(request)
    db_session.flush()
    document = DocumentVersion(
        request_id=request.id,
        doc_type=DocType.receipt,
        original_filename="pending.pdf",
        storage_key="test/pending.pdf",
        mime_type="application/pdf",
        file_size=1,
        file_hash="a" * 64,
        version_number=1,
        uploader_id=submitter.id,
        processing_status=ProcessingStatus.pending,
    )
    db_session.add(document)
    db_session.flush()

    checks = run_all_checks(db_session, request.id)
    missing_check = next(c for c in checks if c.rule_name == "required_fields_check")
    assert missing_check.result == CheckResult.info
    assert "still pending" in missing_check.explanation
    document.processing_status = ProcessingStatus.failed
    failed_check = run_missing_check(db_session, request.id, document.id)
    assert failed_check.result == CheckResult.info
    assert "failed" in failed_check.explanation


def test_unsupported_document_type_has_no_required_fields_rule(db_session):
    submitter = User(
        display_name="Supporting Document Submitter",
        email="supporting-document@example.com",
        password_hash="unused-test-hash",
        role=UserRole.submitter,
        is_active=True,
    )
    db_session.add(submitter)
    db_session.flush()
    request = Request(
        request_number="REQ-2099-7005",
        request_type=RequestType.expense_reimbursement,
        title="Supporting document check",
        submitter_id=submitter.id,
        status=RequestStatus.processing,
    )
    db_session.add(request)
    db_session.flush()
    document = DocumentVersion(
        request_id=request.id,
        doc_type=DocType.supporting_document,
        original_filename="supporting.pdf",
        storage_key="test/supporting.pdf",
        mime_type="application/pdf",
        file_size=1,
        file_hash="b" * 64,
        version_number=1,
        uploader_id=submitter.id,
        processing_status=ProcessingStatus.ready,
    )
    db_session.add(document)
    db_session.flush()
    run = ExtractionRun(
        document_version_id=document.id,
        ocr_engine="test-text",
        status=ExtractionStatus.success,
    )
    db_session.add(run)
    db_session.flush()

    check = run_missing_check(db_session, request.id, document.id)
    assert check.result == CheckResult.info
    assert "No required-field rule" in check.explanation
