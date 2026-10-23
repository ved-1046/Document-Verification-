"""
Verification Check C — Date mismatch between expense form and receipt.

Compares expense_date from expense_form vs receipt.
Only flags if dates are found AND they differ.
"""
import json
import re
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.document_version import DocumentVersion, DocType
from app.models.request import Request
from app.models.extraction_run import ExtractionRun, ExtractionStatus
from app.models.extracted_field import ExtractedField
from app.models.reviewer_correction import ReviewerCorrection
from app.models.verification_check import (
    VerificationCheck, CheckType, CheckResult, CheckSeverity, ResolutionStatus,
)

DATE_FORMATS = [
    "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y",
    "%d/%m/%y", "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y",
    "%B %d %Y", "%b %d %Y",
]


def _normalize_date(raw: str) -> datetime | None:
    numeric = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", raw.strip())
    if numeric:
        first, second = int(numeric.group(1)), int(numeric.group(2))
        if first <= 12 and second <= 12 and first != second:
            return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt)
        except ValueError:
            continue
    return None


def _get_date(db: Session, request_id: int, doc_type: DocType) -> tuple[str | None, int | None]:
    doc = db.query(DocumentVersion).filter(
        DocumentVersion.request_id == request_id,
        DocumentVersion.doc_type == doc_type,
    ).order_by(DocumentVersion.version_number.desc(), DocumentVersion.id.desc()).first()
    if doc is None:
        return None, None
    run = db.query(ExtractionRun).filter(
        ExtractionRun.document_version_id == doc.id,
    ).order_by(ExtractionRun.started_at.desc(), ExtractionRun.id.desc()).first()
    if run is None or run.status != ExtractionStatus.success:
        return None, doc.id
    field = db.query(ExtractedField).filter(
        ExtractedField.extraction_run_id == run.id,
        ExtractedField.field_name == "expense_date",
        ExtractedField.normalized_value.isnot(None),
    ).first()
    correction = db.query(ReviewerCorrection).filter(
        ReviewerCorrection.document_version_id == doc.id,
        ReviewerCorrection.field_name == "expense_date",
    ).order_by(ReviewerCorrection.created_at.desc(), ReviewerCorrection.id.desc()).first()
    if correction:
        return correction.corrected_value, doc.id
    return (field.normalized_value, doc.id) if field else (None, doc.id)


def run(db: Session, request_id: int) -> VerificationCheck:
    form_date_raw, form_doc_id = _get_date(db, request_id, DocType.expense_form)
    rcpt_date_raw, rcpt_doc_id = _get_date(db, request_id, DocType.receipt)
    request = db.get(Request, request_id)
    claim_date_raw = request.expense_date.isoformat() if request and request.expense_date else None
    compared_date = claim_date_raw or form_date_raw
    compared_type = "claim" if claim_date_raw else "expense_form"
    compared_doc_id = None if claim_date_raw else form_doc_id

    if compared_date is None or rcpt_date_raw is None:
        return VerificationCheck(
            request_id=request_id,
            check_type=CheckType.date_mismatch,
            rule_name="date_match_check",
            result=CheckResult.info,
            severity=CheckSeverity.low,
            explanation="Date comparison skipped: claim/form date or receipt date is unavailable.",
            resolution_status=ResolutionStatus.open,
        )

    form_dt = _normalize_date(compared_date)
    rcpt_dt = _normalize_date(rcpt_date_raw)
    evidence = json.dumps([
        {"doc_type": compared_type, "field": "expense_date", "value": compared_date, "doc_version_id": compared_doc_id},
        {"doc_type": "receipt", "field": "expense_date", "value": rcpt_date_raw, "doc_version_id": rcpt_doc_id},
    ])

    if form_dt is None or rcpt_dt is None:
        return VerificationCheck(
            request_id=request_id,
            check_type=CheckType.date_mismatch,
            rule_name="date_match_check",
            result=CheckResult.info,
            severity=CheckSeverity.low,
            explanation=f"Date comparison could not run because one or both dates are ambiguous or invalid. Claim/form: '{compared_date}', Receipt: '{rcpt_date_raw}'.",
            evidence_references=evidence,
            resolution_status=ResolutionStatus.open,
        )

    if form_dt.date() == rcpt_dt.date():
        return VerificationCheck(
            request_id=request_id,
            check_type=CheckType.date_mismatch,
            rule_name="date_match_check",
            result=CheckResult.pass_,
            severity=CheckSeverity.low,
            explanation=f"Dates match: claim/form={compared_date}, receipt={rcpt_date_raw}.",
            evidence_references=evidence,
            resolution_status=ResolutionStatus.open,
        )
    else:
        return VerificationCheck(
            request_id=request_id,
            check_type=CheckType.date_mismatch,
            rule_name="date_match_check",
            result=CheckResult.flag,
            severity=CheckSeverity.medium,
            explanation=(
                f"Date discrepancy: claim/form shows '{compared_date}', "
                f"receipt shows '{rcpt_date_raw}'. A reviewer should verify both documents."
            ),
            evidence_references=evidence,
            resolution_status=ResolutionStatus.open,
        )
