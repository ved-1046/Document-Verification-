"""
Verification Check A — Missing or unreadable required fields.

Required fields: employee_name, expense_date, total_amount, merchant_name
Result: pass if all present; flag if any absent or unreadable.

Important:
- "unreadable" (OCR returned garbled text) ≠ "missing" (not found at all)
- A flag is a signal for review — never described as proof of wrongdoing
"""
import json
from sqlalchemy.orm import Session
from app.models.document_version import DocumentVersion, DocType, ProcessingStatus
from app.models.extraction_run import ExtractionRun, ExtractionStatus
from app.models.extracted_field import ExtractedField
from app.models.reviewer_correction import ReviewerCorrection
from app.models.verification_check import (
    VerificationCheck, CheckType, CheckResult, CheckSeverity, ResolutionStatus,
)

REQUIRED_FIELDS_BY_TYPE = {
    DocType.expense_form: ["employee_name", "expense_date", "total_amount"],
    DocType.receipt: ["merchant_name", "expense_date", "total_amount"],
}


def run(db: Session, request_id: int, doc_version_id: int) -> VerificationCheck:
    """
    Check that all required fields were extracted from the given document version.
    Returns a single VerificationCheck record (not yet committed).
    """
    document = db.get(DocumentVersion, doc_version_id)
    required_fields = REQUIRED_FIELDS_BY_TYPE.get(document.doc_type, []) if document else []
    run = db.query(ExtractionRun).filter(
        ExtractionRun.document_version_id == doc_version_id,
    ).order_by(ExtractionRun.started_at.desc(), ExtractionRun.id.desc()).first()

    if not run or run.status != ExtractionStatus.success:
        pending = (document and document.processing_status in {
            ProcessingStatus.pending, ProcessingStatus.processing
        }) or (run and run.status in {ExtractionStatus.pending, ExtractionStatus.running})
        state = run.status.value if run else (document.processing_status.value if document else "not_started")
        return VerificationCheck(
            request_id=request_id,
            check_type=CheckType.missing_field,
            rule_name="required_fields_check",
            result=CheckResult.info,
            severity=CheckSeverity.low if pending else CheckSeverity.medium,
            explanation=(
                "Extraction is still pending for this document."
                if pending else f"Required-field check could not run because the latest extraction status is {state}."
            ),
            evidence_references=json.dumps([{
                "doc_version_id": doc_version_id,
                "doc_type": document.doc_type.value if document else None,
                "required_fields": required_fields,
                "missing_fields": required_fields,
                "found_fields": [],
            }]),
            resolution_status=ResolutionStatus.open,
        )

    # Gather all extracted field names for this run (excluding raw page text)
    extracted = db.query(ExtractedField).filter(
        ExtractedField.extraction_run_id == run.id,
        ExtractedField.field_name != "_raw_page_text",
        ExtractedField.normalized_value.isnot(None),
    ).all()

    found = {ef.field_name for ef in extracted}
    corrections = db.query(ReviewerCorrection).filter(
        ReviewerCorrection.request_id == request_id,
        ReviewerCorrection.document_version_id == doc_version_id,
        ReviewerCorrection.field_name.in_(required_fields or [""]),
    ).all()
    corrected = {correction.field_name for correction in corrections if correction.corrected_value.strip()}
    found.update(corrected)
    missing = [f for f in required_fields if f not in found]
    evidence = [{
        "doc_version_id": doc_version_id,
        "doc_type": document.doc_type.value if document else None,
        "required_fields": required_fields,
        "found_fields": sorted(found),
        "missing_fields": missing,
        "reviewer_corrected_fields": sorted(corrected),
    }]

    if not required_fields:
        result = VerificationCheck(
            request_id=request_id,
            check_type=CheckType.missing_field,
            rule_name="required_fields_check",
            result=CheckResult.info,
            severity=CheckSeverity.low,
            explanation="No required-field rule is configured for this supporting document type.",
            evidence_references=json.dumps(evidence),
            resolution_status=ResolutionStatus.open,
        )
        return result
    elif not missing:
        return VerificationCheck(
            request_id=request_id,
            check_type=CheckType.missing_field,
            rule_name="required_fields_check",
            result=CheckResult.pass_,
            severity=CheckSeverity.low,
            explanation="All required fields were successfully extracted.",
            evidence_references=json.dumps(evidence),
            resolution_status=ResolutionStatus.open,
        )
    else:
        return VerificationCheck(
            request_id=request_id,
            check_type=CheckType.missing_field,
            rule_name="required_fields_check",
            result=CheckResult.flag,
            severity=CheckSeverity.high,
            explanation=(
                f"The following required fields were not found or could not be read: "
                f"{', '.join(missing)}. A reviewer should inspect the document."
            ),
            evidence_references=json.dumps(evidence),
            resolution_status=ResolutionStatus.open,
        )
