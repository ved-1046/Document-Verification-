"""
Verification runner — runs all three checks for a request and stores results.

Called automatically after successful OCR extraction.
Can also be re-triggered (reviewer corrections, new document version).

Each call creates NEW VerificationCheck rows — old rows are NOT deleted
(they are part of the audit trail).
"""
from sqlalchemy.orm import Session
from app.services.verification import check_a_missing, check_b_amount, check_c_date
from app.models.document_version import DocumentVersion
from app.models.verification_check import VerificationCheck
from app.services.audit.logger import log_event
from app.models.audit_event import AuditEventType


def _supersede_previous_checks(db: Session, request_id: int) -> None:
    """Mark prior checks as historical; new run becomes the current view (ChangeMap)."""
    db.query(VerificationCheck).filter(
        VerificationCheck.request_id == request_id,
        VerificationCheck.is_current.is_(True),
    ).update({VerificationCheck.is_current: False}, synchronize_session=False)


def run_all_checks(db: Session, request_id: int) -> list:
    """
    Run Checks A, B, and C for a request and persist results.
    Returns the newly created VerificationCheck objects.
    """
    _supersede_previous_checks(db, request_id)
    results = []

    # Check A — run once per document version that has a completed extraction
    docs = db.query(DocumentVersion).filter(
        DocumentVersion.request_id == request_id
    ).all()

    for doc in docs:
        check_a = check_a_missing.run(db, request_id, doc.id)
        db.add(check_a)
        results.append(check_a)

    # Check B — compares across form and receipt
    check_b = check_b_amount.run(db, request_id)
    db.add(check_b)
    results.append(check_b)

    # Check C — compares dates across form and receipt
    check_c = check_c_date.run(db, request_id)
    db.add(check_c)
    results.append(check_c)

    log_event(
        db,
        AuditEventType.verification_run,
        request_id=request_id,
        summary=f"Verification run completed ({len(results)} checks)",
    )
    db.flush()
    return results
