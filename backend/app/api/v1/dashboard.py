"""
Dashboard summary — counts and queues from live database data.
"""
from collections import Counter
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.request import Request, RequestStatus
from app.models.user import User, UserRole
from app.models.verification_check import VerificationCheck, CheckResult, ResolutionStatus
from app.services.request_service import list_review_queue

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

ALL_STATUSES = list(RequestStatus)


@router.get("/summary", summary="Dashboard metrics")
def dashboard_summary(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Request)
    if user.role == UserRole.submitter:
        q = q.filter(Request.submitter_id == user.id)
    elif user.role == UserRole.reviewer:
        q = q.filter(Request.assigned_reviewer_id == user.id)
    elif user.role == UserRole.approver:
        q = q.filter(Request.assigned_approver_id == user.id)
    if search:
        q = q.filter(
            Request.request_number.ilike(f"%{search}%")
            | Request.title.ilike(f"%{search}%")
        )

    rows = q.all()
    by_status = {s.value: 0 for s in ALL_STATUSES}
    for r in rows:
        by_status[r.status.value] = by_status.get(r.status.value, 0) + 1

    check_q = db.query(VerificationCheck).filter(
        VerificationCheck.is_current.is_(True),
        VerificationCheck.result == CheckResult.flag,
        VerificationCheck.resolution_status == ResolutionStatus.open,
    )
    if user.role != UserRole.admin:
        ids = [r.id for r in rows]
        if ids:
            check_q = check_q.filter(VerificationCheck.request_id.in_(ids))
        else:
            flagged = []
            check_q = None

    flagged = check_q.all() if check_q is not None else flagged
    issue_counts = Counter(c.check_type.value for c in flagged)

    review_queue_len = len(list_review_queue(db, user)) if user.role in (UserRole.reviewer, UserRole.approver) else 0

    turnaround = None
    completed = [
        r for r in rows
        if r.status in (RequestStatus.approved, RequestStatus.rejected) and r.submitted_at
    ]
    if completed:
        deltas = [
            (r.updated_at - r.submitted_at).total_seconds() / 3600.0
            for r in completed
            if r.updated_at and r.submitted_at
        ]
        if deltas:
            turnaround = round(sum(deltas) / len(deltas), 2)

    return {
        "total_requests": len(rows),
        "by_status": by_status,
        "review_queue_count": review_queue_len,
        "common_check_issues": [
            {"check_type": k, "count": v} for k, v in issue_counts.most_common(5)
        ],
        "avg_turnaround_hours": turnaround,
    }
