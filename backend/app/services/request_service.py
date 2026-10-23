"""
Request service: business logic for request lifecycle.

- Creates human-readable request numbers (REQ-YYYY-NNN)
- Enforces status transition rules (delegated to workflow service)
- Enforces ownership: only the submitter may see their own draft requests
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.request import Request, RequestStatus, RequestType
from app.models.document_version import DocumentVersion, DocType, ProcessingStatus
from app.models.extraction_run import ExtractionRun, ExtractionStatus
from app.models.user import User, UserRole
from app.services.audit.logger import log_event
from app.models.audit_event import AuditEventType
from app.models.review_action import ReviewAction, ReviewActionType


def _next_request_number(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    count = db.query(Request).filter(
        Request.request_number.like(f"REQ-{year}-%")
    ).count()
    return f"REQ-{year}-{count + 1:04d}"


def create_request(db: Session, submitter: User, title: str,
                   description: str | None, request_type: RequestType,
                   expense_category: str = "other",
                   claimed_amount: Decimal | None = None,
                   expense_date: date | None = None,
                   currency: str = "INR",
                   assigned_reviewer_id: int | None = None,
                   assigned_approver_id: int | None = None) -> Request:
    reviewer = eligible_assignee(db, assigned_reviewer_id, UserRole.reviewer, submitter.id)
    approver = eligible_assignee(db, assigned_approver_id, UserRole.approver, submitter.id)
    if reviewer and approver and reviewer.id == approver.id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Reviewer and approver must be different people.")
    req = Request(
        request_number=_next_request_number(db),
        request_type=request_type,
        title=title,
        description=description,
        expense_category=expense_category,
        claimed_amount=claimed_amount,
        expense_date=expense_date,
        currency=currency,
        submitter_id=submitter.id,
        assigned_reviewer_id=reviewer.id if reviewer else None,
        assigned_approver_id=approver.id if approver else None,
        status=RequestStatus.draft,
    )
    db.add(req)
    db.flush()  # get req.id while still in transaction
    log_event(db, AuditEventType.request_created, actor_id=submitter.id,
              request_id=req.id, summary=f"Created: {req.request_number}")
    if reviewer or approver:
        db.add(ReviewAction(
            request_id=req.id,
            actor_id=submitter.id,
            action_type=ReviewActionType.assigned,
            comment=(f"Reviewer: {reviewer.display_name if reviewer else 'unassigned'}; "
                     f"approver: {approver.display_name if approver else 'unassigned'}"),
            previous_status=RequestStatus.draft.value,
            new_status=RequestStatus.draft.value,
        ))
    db.commit()
    db.refresh(req)
    return req


def get_request_or_404(db: Session, request_id: int) -> Request:
    req = db.get(Request, request_id)
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Request {request_id} not found.")
    return req


def assert_can_view(user: User, req: Request) -> None:
    """Limit every non-admin to owned or specifically assigned request records."""
    allowed = (
        user.role == UserRole.admin
        or (user.role == UserRole.submitter and req.submitter_id == user.id)
        or (user.role == UserRole.reviewer and req.assigned_reviewer_id == user.id)
        or (user.role == UserRole.approver and req.assigned_approver_id == user.id)
    )
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")


def list_requests(db: Session, user: User,
                  status_filter: str | None = None,
                  search: str | None = None) -> list[Request]:
    q = db.query(Request)
    if user.role == UserRole.submitter:
        q = q.filter(Request.submitter_id == user.id)
    elif user.role == UserRole.reviewer:
        q = q.filter(Request.assigned_reviewer_id == user.id)
    elif user.role == UserRole.approver:
        q = q.filter(Request.assigned_approver_id == user.id)
    if status_filter:
        q = q.filter(Request.status == status_filter)
    if search:
        q = q.filter(Request.request_number.ilike(f"%{search}%") |
                     Request.title.ilike(f"%{search}%"))
    return q.order_by(Request.updated_at.desc()).all()


def list_review_queue(db: Session, user: User | UserRole | None = None) -> list[Request]:
    """Return only requests assigned to this reviewer or approver."""
    role = user.role if isinstance(user, User) else user
    if role == UserRole.reviewer:
        q = db.query(Request).filter(
            Request.status.in_([
                RequestStatus.submitted,
                RequestStatus.processing,
                RequestStatus.under_review,
                RequestStatus.more_info_required,
            ])
        )
        if isinstance(user, User):
            q = q.filter(Request.assigned_reviewer_id == user.id)
    elif role == UserRole.approver:
        q = db.query(Request).filter(Request.status == RequestStatus.pending_approval)
        if isinstance(user, User):
            q = q.filter(Request.assigned_approver_id == user.id)
    else:
        return []
    return q.order_by(Request.updated_at.desc()).all()


def eligible_assignee(db: Session, user_id: int | None, role: UserRole, submitter_id: int) -> User | None:
    if user_id is None:
        return None
    user = db.get(User, user_id)
    if user is None or not user.is_active or user.role != role:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Selected {role.value} must be an active user with that role.")
    if user.id == submitter_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="The submitter cannot be assigned as the reviewer or approver.")
    return user


def assert_assigned_reviewer(user: User, req: Request) -> None:
    if user.role != UserRole.reviewer or req.assigned_reviewer_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the assigned reviewer may perform this action.")


def assert_assigned_approver(user: User, req: Request) -> None:
    if user.role != UserRole.approver or req.assigned_approver_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the assigned approver may perform this action.")


def advance_if_processing_complete(db: Session, req: Request) -> None:
    """
    When all uploaded documents have finished processing, move processing → under_review
    (or processing_failed if every document failed).
    """
    if req.status != RequestStatus.processing:
        return

    all_docs = db.query(DocumentVersion).filter(
        DocumentVersion.request_id == req.id
    ).order_by(DocumentVersion.version_number.asc()).all()
    if not all_docs:
        return

    # Check only latest document versions per doc_type
    latest_versions: dict[DocType, DocumentVersion] = {}
    for d in all_docs:
        latest_versions[d.doc_type] = d
    docs = list(latest_versions.values())

    pending = {ProcessingStatus.pending, ProcessingStatus.processing}
    if any(d.processing_status in pending for d in docs):
        return

    if any(d.processing_status == ProcessingStatus.ready for d in docs):
        req.status = RequestStatus.under_review
    else:
        req.status = RequestStatus.processing_failed
    req.updated_at = datetime.now(timezone.utc)


def required_document_issue(db: Session, request_id: int) -> str | None:
    """Return an actionable issue unless at least one valid expense document extracted successfully."""
    latest_documents = {
        doc_type: db.query(DocumentVersion).filter(
            DocumentVersion.request_id == request_id,
            DocumentVersion.doc_type == doc_type,
        ).order_by(DocumentVersion.version_number.desc(), DocumentVersion.id.desc()).first()
        for doc_type in (DocType.expense_form, DocType.receipt)
    }
    present_docs = [doc for doc in latest_documents.values() if doc is not None]
    if not present_docs:
        return "Upload the required document(s) before proceeding: expense form, receipt."

    for document in present_docs:
        if document.processing_status != ProcessingStatus.ready:
            state = document.processing_status.value.replace('_', ' ')
            return f"The latest {document.doc_type.value.replace('_', ' ')} (version {document.version_number}) is {state}."
        extraction = db.query(ExtractionRun).filter(
            ExtractionRun.document_version_id == document.id,
        ).order_by(ExtractionRun.started_at.desc(), ExtractionRun.id.desc()).first()
        if extraction is None or extraction.status != ExtractionStatus.success:
            state = extraction.status.value if extraction else "not started"
            return f"The latest {document.doc_type.value.replace('_', ' ')} extraction has not succeeded (status: {state})."
    return None


def assert_submitter_can_upload(user: User, req: Request) -> None:
    """Only the owning submitter may upload/replace documents."""
    if user.role != UserRole.submitter:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the submitter may upload documents.",
        )
    if req.submitter_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    if req.status not in (
        RequestStatus.draft,
        RequestStatus.more_info_required,
        RequestStatus.processing_failed,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Documents cannot be uploaded while request is in '{req.status.value}' status."
            ),
        )
