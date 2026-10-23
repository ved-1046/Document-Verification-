"""
Workflow transition service.

ALLOWED_TRANSITIONS defines every valid (from_status → to_status) move.
Any other transition raises WorkflowError (returned as 422 to the client).

Design decision: transitions are defined as an explicit allowlist — new statuses
must be deliberately added here. This prevents accidental state jumps.
"""
from fastapi import HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.models.request import Request, RequestStatus
from app.models.user import User, UserRole
from app.models.review_action import ReviewAction, ReviewActionType
from app.services.audit.logger import log_event
from app.models.audit_event import AuditEventType

# Explicit allowlist
ALLOWED_TRANSITIONS: dict[RequestStatus, set[RequestStatus]] = {
    RequestStatus.draft:             {RequestStatus.submitted},
    RequestStatus.submitted:         {RequestStatus.processing},
    RequestStatus.processing:        {RequestStatus.under_review, RequestStatus.processing_failed},
    RequestStatus.processing_failed: {RequestStatus.processing},                # retry
    RequestStatus.under_review:      {RequestStatus.more_info_required, RequestStatus.pending_approval},
    RequestStatus.pending_approval:  {RequestStatus.approved, RequestStatus.rejected},
    RequestStatus.more_info_required:{RequestStatus.processing},                # new doc uploaded → re-process
    RequestStatus.approved:          set(),                                      # terminal
    RequestStatus.rejected:          set(),                                      # terminal
}


def transition(
    db: Session,
    req: Request,
    new_status: RequestStatus,
    actor: User,
    action_type: ReviewActionType,
    comment: str | None = None,
    check_self_approve: bool = False,
) -> None:
    """
    Apply a status transition with full audit trail.

    - check_self_approve=True → raise 403 if actor is the submitter (approve/reject)
    - Records ReviewAction (immutable history) and AuditEvent.
    - Raises 422 on invalid transition.
    """
    current = req.status
    if new_status not in ALLOWED_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Cannot move from '{current.value}' to '{new_status.value}'. "
                f"Allowed next states: {[s.value for s in ALLOWED_TRANSITIONS.get(current, set())]}."
            ),
        )

    if check_self_approve and req.submitter_id == actor.id:
        log_event(db, AuditEventType.unauthorized_access_attempt,
                  actor_id=actor.id, request_id=req.id,
                  summary=f"Self-approval attempted on {req.request_number}")
        db.flush()
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Submitters may not approve or reject their own requests.",
        )

    review = ReviewAction(
        request_id=req.id,
        actor_id=actor.id,
        action_type=action_type,
        comment=comment,
        previous_status=current.value,
        new_status=new_status.value,
    )
    db.add(review)

    req.status = new_status
    from datetime import datetime, timezone
    req.updated_at = datetime.now(timezone.utc)

    log_event(db, AuditEventType.request_status_changed, actor_id=actor.id,
              request_id=req.id,
              summary=f"{current.value} → {new_status.value} by {actor.email}")
    db.flush()
