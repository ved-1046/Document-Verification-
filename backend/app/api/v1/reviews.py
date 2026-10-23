"""
Reviews API router.

POST /api/v1/requests/{id}/request-correction  — Reviewer requests more info
POST /api/v1/requests/{id}/corrections          — Reviewer corrects a field value
POST /api/v1/requests/{id}/resolve-check        — Reviewer resolves/dismisses a check
POST /api/v1/requests/{id}/approve              — Approver approves (non-submitter only)
POST /api/v1/requests/{id}/reject               — Approver rejects (non-submitter only)
GET  /api/v1/audit                              — Audit log (approver only)
"""
import json
from typing import Optional
from pydantic import BaseModel, field_validator
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.request import Request, RequestStatus
from app.models.document_version import DocumentVersion
from app.models.extraction_run import ExtractionRun, ExtractionStatus
from app.models.extracted_field import ExtractedField
from app.models.review_action import ReviewActionType
from app.models.reviewer_correction import ReviewerCorrection
from app.models.verification_check import VerificationCheck, ResolutionStatus, CheckResult
from app.models.audit_event import AuditEvent, AuditEventType
from app.models.user import User, UserRole
from app.services.request_service import assert_assigned_approver, assert_assigned_reviewer, assert_can_view, get_request_or_404, required_document_issue
from app.services.workflow.transitions import transition
from app.services.audit.logger import log_event
from app.services.verification.runner import run_all_checks
from app.services.document_processing.normalizer import FIELD_NAMES

router = APIRouter(tags=["reviews"])


class CorrectionRequestBody(BaseModel):
    comment: str

    @field_validator("comment")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("comment is required")
        return v.strip()


class FieldCorrectionBody(BaseModel):
    document_version_id: int
    field_name: str
    corrected_value: str
    original_extracted_value: Optional[str] = None
    reason: str

    @field_validator("field_name")
    @classmethod
    def supported_field(cls, value: str) -> str:
        if value not in FIELD_NAMES:
            raise ValueError("field_name must be a supported extracted expense field")
        return value

    @field_validator("corrected_value")
    @classmethod
    def corrected_value_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("corrected_value is required")
        return value.strip()

    @field_validator("reason")
    @classmethod
    def correction_reason_required(cls, value: str) -> str:
        reason = value.strip()
        if not reason:
            raise ValueError("reason is required")
        return reason


class ResolveCheckBody(BaseModel):
    resolution_status: str  # "resolved" or "dismissed"
    reason: Optional[str] = None


class ApproveRejectBody(BaseModel):
    comment: str

    @field_validator("comment")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("comment (decision reason) is required and must not be empty")
        return v.strip()


class ReviewCompletionBody(BaseModel):
    comment: str

    @field_validator("comment")
    @classmethod
    def not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A review summary is required")
        return value.strip()


@router.post("/requests/{request_id}/request-correction",
             summary="Reviewer requests more information from submitter")
def request_correction(
    request_id: int,
    body: CorrectionRequestBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.reviewer)),
):
    req = get_request_or_404(db, request_id)
    assert_assigned_reviewer(user, req)
    transition(db, req, RequestStatus.more_info_required, user,
               ReviewActionType.correction_requested, comment=body.comment)
    db.commit()
    return {"detail": "Correction requested.", "request_id": request_id}


@router.post("/requests/{request_id}/corrections",
             status_code=201,
             summary="Reviewer corrects an extracted field value")
def correct_field(
    request_id: int,
    body: FieldCorrectionBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.reviewer)),
):
    req = get_request_or_404(db, request_id)
    assert_assigned_reviewer(user, req)
    if req.status != RequestStatus.under_review:
        raise HTTPException(status_code=422, detail="Fields can only be corrected while the request is under review.")
    document = db.get(DocumentVersion, body.document_version_id)
    if document is None or document.request_id != request_id:
        raise HTTPException(status_code=422, detail="The selected document version does not belong to this request.")
    latest_document = db.query(DocumentVersion).filter(
        DocumentVersion.request_id == request_id,
        DocumentVersion.doc_type == document.doc_type,
    ).order_by(DocumentVersion.version_number.desc(), DocumentVersion.id.desc()).first()
    if latest_document is None or latest_document.id != document.id:
        raise HTTPException(status_code=409, detail="Corrections can only target the latest document version.")
    extraction = db.query(ExtractionRun).filter(
        ExtractionRun.document_version_id == document.id,
    ).order_by(ExtractionRun.started_at.desc(), ExtractionRun.id.desc()).first()
    if extraction is None or extraction.status != ExtractionStatus.success:
        raise HTTPException(status_code=409, detail="A correction requires a successfully extracted latest document version.")
    extracted_field = db.query(ExtractedField).filter(
        ExtractedField.extraction_run_id == extraction.id,
        ExtractedField.field_name == body.field_name,
    ).first()
    actual_original = (extracted_field.normalized_value or extracted_field.extracted_value) if extracted_field else None
    supplied_original = body.original_extracted_value or None
    if supplied_original != actual_original:
        raise HTTPException(status_code=409, detail="The extracted value changed. Refresh the claim before recording a correction.")

    correction = ReviewerCorrection(
        request_id=request_id,
        document_version_id=body.document_version_id,
        field_name=body.field_name,
        original_extracted_value=body.original_extracted_value,
        corrected_value=body.corrected_value,
        reviewer_id=user.id,
        reason=body.reason,
    )
    db.add(correction)

    log_event(db, AuditEventType.field_corrected, actor_id=user.id,
              request_id=request_id,
              summary=f"Field '{body.field_name}' corrected by {user.email}")
    run_all_checks(db, request_id)
    db.commit()
    db.refresh(correction)
    return {
        "id": correction.id,
        "field_name": correction.field_name,
        "original_extracted_value": correction.original_extracted_value,
        "corrected_value": correction.corrected_value,
        "reviewer_id": correction.reviewer_id,
        "created_at": correction.created_at.isoformat(),
    }


@router.get("/requests/{request_id}/corrections",
            summary="List reviewer corrections recorded for a request")
def list_corrections(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = get_request_or_404(db, request_id)
    assert_can_view(user, req)
    corrections = db.query(ReviewerCorrection).filter(
        ReviewerCorrection.request_id == request_id
    ).order_by(ReviewerCorrection.created_at.asc()).all()
    return [
        {
            "id": correction.id,
            "document_version_id": correction.document_version_id,
            "field_name": correction.field_name,
            "original_extracted_value": correction.original_extracted_value,
            "corrected_value": correction.corrected_value,
            "reviewer_id": correction.reviewer_id,
            "reviewer_name": correction.reviewer.display_name,
            "reason": correction.reason,
            "created_at": correction.created_at.isoformat(),
        }
        for correction in corrections
    ]


@router.post("/requests/{request_id}/resolve-check",
             summary="Resolve or dismiss a verification check")
def resolve_check(
    request_id: int,
    body: ResolveCheckBody,
    check_id: int = Query(..., description="Verification check id to resolve"),
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.reviewer)),
):
    req = get_request_or_404(db, request_id)
    assert_assigned_reviewer(user, req)
    if req.status != RequestStatus.under_review:
        raise HTTPException(status_code=422, detail="Checks can only be resolved while the request is under review.")
    check = db.query(VerificationCheck).filter(
        VerificationCheck.id == check_id,
        VerificationCheck.request_id == request_id,
    ).first()
    if not check:
        raise HTTPException(status_code=404, detail="Verification check not found.")

    try:
        check.resolution_status = ResolutionStatus(body.resolution_status)
    except ValueError:
        raise HTTPException(status_code=422, detail="resolution_status must be 'resolved' or 'dismissed'")

    log_event(db, AuditEventType.review_action, actor_id=user.id,
              request_id=request_id,
              entity_type="verification_check", entity_id=check_id,
              summary=f"Check {check_id} marked {body.resolution_status} by {user.email}")
    db.commit()
    return {"detail": f"Check marked {body.resolution_status}.", "check_id": check_id}


@router.post("/requests/{request_id}/complete-review",
             summary="Complete review and send the request to its assigned approver")
def complete_review(
    request_id: int,
    body: ReviewCompletionBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.reviewer)),
):
    req = get_request_or_404(db, request_id)
    assert_assigned_reviewer(user, req)
    if req.status != RequestStatus.under_review:
        raise HTTPException(status_code=422, detail="Only claims under review can be sent for approval.")
    document_issue = required_document_issue(db, request_id)
    if document_issue:
        raise HTTPException(status_code=422, detail=document_issue)
    open_flags = db.query(VerificationCheck).filter(
        VerificationCheck.request_id == request_id,
        VerificationCheck.is_current.is_(True),
        VerificationCheck.result == CheckResult.flag,
        VerificationCheck.resolution_status == ResolutionStatus.open,
    ).count()
    if open_flags:
        raise HTTPException(
            status_code=422,
            detail=f"Resolve or dismiss the {open_flags} open verification flag(s) before sending the claim for approval.",
        )
    transition(db, req, RequestStatus.pending_approval, user,
               ReviewActionType.review_completed, comment=body.comment)
    db.commit()
    return {"detail": "Review completed; request sent to the assigned approver.", "request_id": request_id}


@router.post("/requests/{request_id}/approve",
             summary="Approver approves a request (cannot be the submitter)")
def approve(
    request_id: int,
    body: ApproveRejectBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.approver)),
):
    req = get_request_or_404(db, request_id)
    assert_assigned_approver(user, req)
    if req.status != RequestStatus.pending_approval:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Only claims in 'pending_approval' status can be approved. Current status: '{req.status.value}'.",
        )
    open_flags = db.query(VerificationCheck).filter(
        VerificationCheck.request_id == request_id,
        VerificationCheck.is_current.is_(True),
        VerificationCheck.result == CheckResult.flag,
        VerificationCheck.resolution_status == ResolutionStatus.open,
    ).count()
    if open_flags > 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot approve claim with {open_flags} open verification issue(s). All issues must be resolved or dismissed before approval.",
        )
    # Self-approval block enforced inside transition()
    transition(db, req, RequestStatus.approved, user,
               ReviewActionType.approved, comment=body.comment,
               check_self_approve=True)
    db.commit()
    return {"detail": "Request approved.", "request_id": request_id, "status": "approved"}


@router.post("/requests/{request_id}/reject",
             summary="Approver rejects a request (cannot be the submitter)")
def reject(
    request_id: int,
    body: ApproveRejectBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.approver)),
):
    req = get_request_or_404(db, request_id)
    assert_assigned_approver(user, req)
    if req.status != RequestStatus.pending_approval:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Only claims in 'pending_approval' status can be rejected. Current status: '{req.status.value}'.",
        )
    transition(db, req, RequestStatus.rejected, user,
               ReviewActionType.rejected, comment=body.comment,
               check_self_approve=True)
    db.commit()
    return {"detail": "Request rejected.", "request_id": request_id, "status": "rejected"}


@router.get("/audit", summary="Audit event log (approver only)")
def audit_log(
    request_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.approver, UserRole.admin)),
):
    q = db.query(AuditEvent).order_by(AuditEvent.created_at.desc())
    if request_id:
        req = get_request_or_404(db, request_id)
        assert_can_view(user, req)
        q = q.filter(AuditEvent.request_id == request_id)
    elif user.role != UserRole.admin:
        # An approver can only inspect the audit trail of requests assigned to them.
        q = q.join(Request, AuditEvent.request_id == Request.id).filter(
            Request.assigned_approver_id == user.id
        )
    events = q.limit(500).all()
    return [
        {
            "id": e.id,
            "event_type": e.event_type.value,
            "actor_id": e.actor_id,
            "request_id": e.request_id,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "summary": e.change_summary,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]
