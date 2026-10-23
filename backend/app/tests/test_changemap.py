from app.models.document_version import DocType, DocumentVersion, ProcessingStatus
from app.models.extracted_field import ExtractedField
from app.models.extraction_run import ExtractionRun, ExtractionStatus
from app.models.request import Request, RequestStatus, RequestType
from app.models.user import User, UserRole
from app.services.changemap import build_changemap


def test_pending_replacement_does_not_report_all_fields_removed(db_session):
    submitter = User(
        display_name="ChangeMap Test Submitter",
        email="changemap-test@example.com",
        password_hash="unused-test-hash",
        role=UserRole.submitter,
        is_active=True,
    )
    db_session.add(submitter)
    db_session.flush()
    request = Request(
        request_number="REQ-2099-7004",
        request_type=RequestType.expense_reimbursement,
        title="ChangeMap regression claim",
        submitter_id=submitter.id,
        status=RequestStatus.processing,
    )
    db_session.add(request)
    db_session.flush()

    versions = []
    for version_number, status in ((1, ProcessingStatus.ready), (2, ProcessingStatus.processing)):
        document = DocumentVersion(
            request_id=request.id,
            doc_type=DocType.receipt,
            original_filename=f"receipt-v{version_number}.pdf",
            storage_key=f"test/receipt-v{version_number}.pdf",
            mime_type="application/pdf",
            file_size=1,
            file_hash=str(version_number) * 64,
            version_number=version_number,
            uploader_id=submitter.id,
            processing_status=status,
        )
        db_session.add(document)
        db_session.flush()
        versions.append(document)

    old_run = ExtractionRun(
        document_version_id=versions[0].id,
        ocr_engine="test-text",
        status=ExtractionStatus.success,
    )
    db_session.add(old_run)
    db_session.flush()
    db_session.add(ExtractedField(
        extraction_run_id=old_run.id,
        field_name="total_amount",
        extracted_value="100.00",
        normalized_value="100.00",
    ))
    db_session.flush()

    change = build_changemap(db_session, request.id)["changes"][0]
    assert change["comparison_status"] == "processing"
    assert change["previous_extraction_status"] == "success"
    assert change["current_extraction_status"] == "not_started"
    assert change["field_diffs"] == []

    new_run = ExtractionRun(
        document_version_id=versions[1].id,
        ocr_engine="test-text",
        status=ExtractionStatus.success,
    )
    db_session.add(new_run)
    db_session.flush()
    db_session.add(ExtractedField(
        extraction_run_id=new_run.id,
        field_name="total_amount",
        extracted_value="125.00",
        normalized_value="125.00",
    ))
    db_session.flush()
    ready_change = build_changemap(db_session, request.id)["changes"][0]
    assert ready_change["comparison_status"] == "ready"
    assert ready_change["field_diffs"] == [{
        "field_name": "total_amount",
        "old_value": "100.00",
        "new_value": "125.00",
        "status": "changed",
        "old_version_id": versions[0].id,
        "new_version_id": versions[1].id,
    }]

    versions[1].processing_status = ProcessingStatus.failed
    failed_run = ExtractionRun(
        document_version_id=versions[1].id,
        ocr_engine="test-text",
        status=ExtractionStatus.failed,
        error_details="synthetic failure",
    )
    db_session.add(failed_run)
    db_session.flush()
    failed_change = build_changemap(db_session, request.id)["changes"][0]
    assert failed_change["comparison_status"] == "failed"
    assert failed_change["current_extraction_status"] == "failed"
    assert failed_change["field_diffs"] == []
