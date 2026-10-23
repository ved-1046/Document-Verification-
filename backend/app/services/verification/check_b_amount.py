"""
Verification Check B — Amount mismatch between expense form and receipt.

Compares total_amount from the latest expense_form extraction
vs the latest receipt extraction.

Important:
- Normalizes Indian formatting (₹5,800 → 5800.00)
- Does NOT compare subtotal/tax/grand total interchangeably
- A mismatch is a signal for review, never fraud
- Returns both amounts and their source doc_version_ids as evidence
"""
import json
from decimal import Decimal, InvalidOperation
from sqlalchemy.orm import Session

from app.models.document_version import DocumentVersion, DocType
from app.models.request import Request
from app.models.extraction_run import ExtractionRun, ExtractionStatus
from app.models.extracted_field import ExtractedField
from app.models.reviewer_correction import ReviewerCorrection
from app.models.verification_check import (
    VerificationCheck, CheckType, CheckResult, CheckSeverity, ResolutionStatus,
)


def _get_amount(db: Session, request_id: int, doc_type: DocType) -> tuple[str | None, int | None]:
    """Return amount from the latest document version's latest run only."""
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
        ExtractedField.field_name == "total_amount",
        ExtractedField.normalized_value.isnot(None),
    ).first()
    correction = db.query(ReviewerCorrection).filter(
        ReviewerCorrection.document_version_id == doc.id,
        ReviewerCorrection.field_name == "total_amount",
    ).order_by(ReviewerCorrection.created_at.desc(), ReviewerCorrection.id.desc()).first()
    if correction:
        return correction.corrected_value, doc.id
    return (field.normalized_value, doc.id) if field else (None, doc.id)


def run(db: Session, request_id: int) -> VerificationCheck:
    form_amount, form_doc_id = _get_amount(db, request_id, DocType.expense_form)
    receipt_amount, receipt_doc_id = _get_amount(db, request_id, DocType.receipt)
    request = db.get(Request, request_id)
    claim_amount = str(request.claimed_amount) if request and request.claimed_amount is not None else None
    compared_form_amount = claim_amount if claim_amount is not None else form_amount
    compared_doc_type = "claim" if claim_amount is not None else "expense_form"
    compared_doc_id = None if claim_amount is not None else form_doc_id

    if compared_form_amount is None and receipt_amount is None:
        return VerificationCheck(
            request_id=request_id,
            check_type=CheckType.amount_mismatch,
            rule_name="amount_match_check",
            result=CheckResult.info,
            severity=CheckSeverity.low,
            explanation="No total_amount found in either expense form or receipt. Check A will flag missing fields.",
            evidence_references=json.dumps([
                {"doc_type": compared_doc_type, "amount": compared_form_amount, "doc_version_id": compared_doc_id},
                {"doc_type": "receipt", "amount": receipt_amount, "doc_version_id": receipt_doc_id},
            ]),
            resolution_status=ResolutionStatus.open,
        )

    if compared_form_amount is None or receipt_amount is None:
        missing_doc = "claim amount" if compared_form_amount is None and claim_amount is not None else (
            "expense form" if compared_form_amount is None else "receipt"
        )
        return VerificationCheck(
            request_id=request_id,
            check_type=CheckType.amount_mismatch,
            rule_name="amount_match_check",
            result=CheckResult.info,
            severity=CheckSeverity.low,
            explanation=f"Amount comparison could not run: total_amount is unavailable in the {missing_doc}.",
            evidence_references=json.dumps([
                {"doc_type": compared_doc_type, "amount": compared_form_amount, "doc_version_id": compared_doc_id},
                {"doc_type": "receipt", "amount": receipt_amount, "doc_version_id": receipt_doc_id},
            ]),
            resolution_status=ResolutionStatus.open,
        )

    evidence = json.dumps([
        {"doc_type": compared_doc_type, "field": "claimed_amount" if claim_amount is not None else "total_amount", "amount": compared_form_amount, "doc_version_id": compared_doc_id},
        {"doc_type": "receipt", "field": "total_amount", "amount": receipt_amount, "doc_version_id": receipt_doc_id},
    ])

    try:
        form_dec = Decimal(str(compared_form_amount).replace(",", ""))
        rcpt_dec = Decimal(str(receipt_amount).replace(",", ""))
    except InvalidOperation:
        return VerificationCheck(
            request_id=request_id,
            check_type=CheckType.amount_mismatch,
            rule_name="amount_match_check",
            result=CheckResult.info,
            severity=CheckSeverity.low,
            explanation=f"Could not parse amounts for comparison. Claim/form: '{compared_form_amount}', Receipt: '{receipt_amount}'.",
            evidence_references=evidence,
            resolution_status=ResolutionStatus.open,
        )

    if form_dec == rcpt_dec:
        return VerificationCheck(
            request_id=request_id,
            check_type=CheckType.amount_mismatch,
            rule_name="amount_match_check",
            result=CheckResult.pass_,
            severity=CheckSeverity.low,
            explanation=f"Amounts match: claim/form={compared_form_amount}, receipt={receipt_amount}.",
            evidence_references=evidence,
            resolution_status=ResolutionStatus.open,
        )
    else:
        diff = abs(form_dec - rcpt_dec)
        return VerificationCheck(
            request_id=request_id,
            check_type=CheckType.amount_mismatch,
            rule_name="amount_match_check",
            result=CheckResult.flag,
            severity=CheckSeverity.high,
            explanation=(
                f"Amount discrepancy detected: claim/form shows {compared_form_amount}, "
                f"receipt shows {receipt_amount} (difference: {diff}). "
                f"A reviewer should inspect both documents."
            ),
            evidence_references=evidence,
            resolution_status=ResolutionStatus.open,
        )
