"""
Request model.

Status transitions are enforced in the workflow service, not here.
The model just stores the current state.
"""
import enum
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class RequestStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    processing = "processing"
    under_review = "under_review"
    pending_approval = "pending_approval"
    more_info_required = "more_info_required"
    approved = "approved"
    rejected = "rejected"
    processing_failed = "processing_failed"


class RequestType(str, enum.Enum):
    expense_reimbursement = "expense_reimbursement"
    # Future: invoice_verification = "invoice_verification"


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Human-readable number e.g. "REQ-2024-001"
    request_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    request_type: Mapped[RequestType] = mapped_column(
        Enum(RequestType), nullable=False, default=RequestType.expense_reimbursement
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    expense_category: Mapped[str] = mapped_column(String(80), nullable=False, default="other")
    claimed_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    expense_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")

    submitter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_approver_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus), nullable=False, default=RequestStatus.draft
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    submitter: Mapped["User"] = relationship("User", back_populates="requests", foreign_keys=[submitter_id])
    assigned_reviewer: Mapped["User | None"] = relationship("User", foreign_keys=[assigned_reviewer_id])
    assigned_approver: Mapped["User | None"] = relationship("User", foreign_keys=[assigned_approver_id])
    document_versions: Mapped[list["DocumentVersion"]] = relationship("DocumentVersion", back_populates="request")
    verification_checks: Mapped[list["VerificationCheck"]] = relationship("VerificationCheck", back_populates="request")
    review_actions: Mapped[list["ReviewAction"]] = relationship("ReviewAction", back_populates="request")
    corrections: Mapped[list["ReviewerCorrection"]] = relationship("ReviewerCorrection", back_populates="request")
    audit_events: Mapped[list["AuditEvent"]] = relationship("AuditEvent", back_populates="request")

    def __repr__(self) -> str:
        return f"<Request id={self.id} number={self.request_number!r} status={self.status}>"
