"""
Requests API router.

POST   /api/v1/requests                — Create a draft request (submitter)
GET    /api/v1/requests                — List visible requests (role-filtered)
GET    /api/v1/requests/{id}           — Get a single request
POST   /api/v1/requests/{id}/submit    — Submit a draft for processing (submitter only)
GET    /api/v1/requests/{id}/checks    — Get verification check results
GET    /api/v1/requests/{id}/history   — Get review action timeline
GET    /api/v1/requests/{id}/changemap — Field diffs after document replacement
GET    /api/v1/requests/{id}/evidence-graph — Interactive Evidence Impact Graph
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.request import Request, RequestStatus, RequestType
from app.models.review_action import ReviewAction, ReviewActionType
from app.models.user import User, UserRole
from app.schemas.request import RequestAssignmentUpdate, RequestCreate, RequestListItem, RequestRead, RequestUpdate
from app.services.request_service import (
    advance_if_processing_complete,
    assert_can_view,
    create_request,
    get_request_or_404,
    list_requests,
    list_review_queue,
    eligible_assignee,
    required_document_issue,
)
from app.services.changemap import build_changemap
from app.services.evidence_graph import build_evidence_graph
from app.services.decision_replay import build_decision_replay
from app.services.workflow.transitions import transition
from app.models.verification_check import VerificationCheck

router = APIRouter(prefix="/requests", tags=["requests"])


@router.post("", response_model=RequestRead, status_code=201,
             summary="Create a new draft request")
def create(
    body: RequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.submitter)),
):
    return create_request(
        db, user, body.title, body.description, body.request_type,
        body.expense_category, body.claimed_amount, body.expense_date, body.currency,
        body.assigned_reviewer_id, body.assigned_approver_id,
    )


@router.get("", response_model=list[RequestListItem], summary="List requests")
def list_all(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = []
    for req in list_requests(db, user, status_filter=status, search=search):
        item = RequestListItem.model_validate(req).model_dump()
        item["submitter_name"] = req.submitter.display_name
        result.append(item)
    return result


@router.get("/review-queue", response_model=list[RequestListItem],
            summary="Requests awaiting review (reviewer/approver)")
def review_queue(
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.reviewer, UserRole.approver)),
):
    results = []
    for req in list_review_queue(db, user):
        item = RequestListItem.model_validate(req).model_dump()
        item["submitter_name"] = req.submitter.display_name
        results.append(item)
    return results


@router.get("/lookup", response_model=RequestRead, summary="Look up by public request number")
def lookup_by_number(
    request_number: str = Query(..., min_length=1, max_length=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = db.query(Request).filter(Request.request_number == request_number.strip()).first()
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found.")
    assert_can_view(user, req)
    return req


@router.get("/{request_id}", response_model=RequestRead, summary="Get a single request")
def get_one(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = get_request_or_404(db, request_id)
    assert_can_view(user, req)
    return req


@router.patch("/{request_id}", response_model=RequestRead,
              summary="Update draft request details")
def update_request(
    request_id: int,
    body: RequestUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = get_request_or_404(db, request_id)
    assert_can_view(user, req)
    if user.role != UserRole.admin:
        if user.role != UserRole.submitter or req.submitter_id != user.id:
            raise HTTPException(status_code=403, detail="Only the claim submitter or an administrator may update claim details.")
        if req.status not in (RequestStatus.draft, RequestStatus.more_info_required):
            raise HTTPException(status_code=422, detail="Claim details can only be modified while in draft or awaiting information.")
    if body.title is not None and body.title.strip():
        req.title = body.title.strip()
    if body.description is not None:
        req.description = body.description.strip() or None
    if body.expense_category is not None and body.expense_category.strip():
        req.expense_category = body.expense_category.strip()
    if body.claimed_amount is not None:
        req.claimed_amount = body.claimed_amount
    if body.expense_date is not None:
        req.expense_date = body.expense_date
    if body.currency is not None and body.currency.strip():
        req.currency = body.currency.strip().upper()
    if body.assigned_reviewer_id is not None or body.assigned_approver_id is not None:
        rev_id = body.assigned_reviewer_id or req.assigned_reviewer_id
        app_id = body.assigned_approver_id or req.assigned_approver_id
        if rev_id and app_id:
            reviewer = eligible_assignee(db, rev_id, UserRole.reviewer, req.submitter_id)
            approver = eligible_assignee(db, app_id, UserRole.approver, req.submitter_id)
            if reviewer.id == approver.id:
                raise HTTPException(status_code=422, detail="Reviewer and approver must be different people.")
            req.assigned_reviewer_id = reviewer.id
            req.assigned_approver_id = approver.id
    from app.services.verification.runner import run_all_checks
    run_all_checks(db, req.id)
    db.commit()
    db.refresh(req)
    return req


@router.patch("/{request_id}/assignment", response_model=RequestRead,
              summary="Assign reviewer and approver")
def update_assignment(
    request_id: int,
    body: RequestAssignmentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = get_request_or_404(db, request_id)
    if user.role != UserRole.admin:
        if user.role != UserRole.submitter or req.submitter_id != user.id:
            raise HTTPException(status_code=403, detail="Only administrators or the claim submitter may change assignees.")
        if req.status not in (RequestStatus.draft, RequestStatus.more_info_required):
            raise HTTPException(status_code=422, detail="Assignees can only be modified while the claim is in draft or awaiting information.")
    if req.status in (RequestStatus.approved, RequestStatus.rejected):
        raise HTTPException(status_code=422, detail="Assignments cannot change after a final decision.")
    reviewer = eligible_assignee(db, body.assigned_reviewer_id, UserRole.reviewer, req.submitter_id)
    approver = eligible_assignee(db, body.assigned_approver_id, UserRole.approver, req.submitter_id)
    if reviewer.id == approver.id:
        raise HTTPException(status_code=422, detail="Reviewer and approver must be different people.")
    previous = f"Reviewer #{req.assigned_reviewer_id}; approver #{req.assigned_approver_id}"
    req.assigned_reviewer_id = reviewer.id
    req.assigned_approver_id = approver.id
    db.add(ReviewAction(
        request_id=req.id,
        actor_id=user.id,
        action_type=ReviewActionType.assigned,
        comment=f"Assignments updated: {previous} → reviewer {reviewer.display_name}; approver {approver.display_name}",
        previous_status=req.status.value,
        new_status=req.status.value,
    ))
    db.commit()
    db.refresh(req)
    return req


@router.post("/{request_id}/submit", response_model=RequestRead,
             summary="Submit a draft request for processing")
def submit(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.submitter)),
):
    req = get_request_or_404(db, request_id)
    assert_can_view(user, req)
    if req.status not in (RequestStatus.draft, RequestStatus.more_info_required):
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"This claim cannot be submitted because it is already in '{req.status.value.replace('_', ' ')}' status.",
        )
    document_issue = required_document_issue(db, request_id)
    if document_issue:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=document_issue,
        )
    if req.claimed_amount is None or req.expense_date is None:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Enter the claimed amount and expense date before submitting.",
        )
    if req.assigned_reviewer_id is None or req.assigned_approver_id is None:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Select an active reviewer and approver before submitting.",
        )
    eligible_assignee(db, req.assigned_reviewer_id, UserRole.reviewer, req.submitter_id)
    eligible_assignee(db, req.assigned_approver_id, UserRole.approver, req.submitter_id)
    if req.status == RequestStatus.draft:
        transition(db, req, RequestStatus.submitted, user,
                   ReviewActionType.submitted, comment="Submitted by submitter")
        action_type = ReviewActionType.submitted
    else:
        action_type = ReviewActionType.correction_submitted
    req.submitted_at = datetime.now(timezone.utc)
    transition(db, req, RequestStatus.processing, user,
               action_type, comment="Queued for OCR and verification")
    advance_if_processing_complete(db, req)
    from app.services.verification.runner import run_all_checks
    if req.status == RequestStatus.under_review:
        run_all_checks(db, req.id)
    db.commit()
    db.refresh(req)
    return req


@router.get("/{request_id}/checks", summary="Get verification check results")
def get_checks(
    request_id: int,
    include_history: bool = Query(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = get_request_or_404(db, request_id)
    assert_can_view(user, req)
    q = db.query(VerificationCheck).filter(
        VerificationCheck.request_id == request_id
    )
    if not include_history:
        q = q.filter(VerificationCheck.is_current.is_(True))
    checks = q.order_by(VerificationCheck.created_at.desc()).all()
    return [
        {
            "id": c.id,
            "check_type": c.check_type.value,
            "rule_name": c.rule_name,
            "result": c.result.value,
            "severity": c.severity.value,
            "explanation": c.explanation,
            "evidence_references": c.evidence_references,
            "resolution_status": c.resolution_status.value,
            "is_current": c.is_current,
            "created_at": c.created_at.isoformat(),
        }
        for c in checks
    ]


@router.get("/{request_id}/history", summary="Get the full review action timeline")
def get_history(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = get_request_or_404(db, request_id)
    assert_can_view(user, req)
    actions = db.query(ReviewAction).filter(
        ReviewAction.request_id == request_id
    ).order_by(ReviewAction.created_at.asc()).all()
    return [
        {
            "id": a.id,
            "actor_id": a.actor_id,
            "actor_name": a.actor.display_name,
            "action_type": a.action_type.value,
            "comment": a.comment,
            "previous_status": a.previous_status,
            "new_status": a.new_status,
            "created_at": a.created_at.isoformat(),
        }
        for a in actions
    ]


@router.get("/{request_id}/changemap", summary="Field diffs after document replacement")
def changemap(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = get_request_or_404(db, request_id)
    assert_can_view(user, req)
    return build_changemap(db, request_id)


@router.get("/{request_id}/evidence-graph", summary="Get the complete Evidence Impact Graph")
def get_evidence_graph(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = get_request_or_404(db, request_id)
    assert_can_view(user, req)
    return build_evidence_graph(db, request_id)


@router.get("/{request_id}/decision-replay", summary="Get the complete Decision Replay event timeline")
def get_decision_replay(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = get_request_or_404(db, request_id)
    assert_can_view(user, req)
    return build_decision_replay(db, request_id)

