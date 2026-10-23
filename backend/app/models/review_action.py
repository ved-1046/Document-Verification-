"""
ReviewAction model.

Every action a reviewer or approver takes on a request is recorded here.
This provides the full decision audit trail.

Action types:
  submitted          — submitter submitted the request
  assigned           — assigned to reviewer
  correction_requested — reviewer asked for more info/docs
  correction_submitted — submitter responded with updated docs
  field_corrected    — reviewer corrected an extracted field value
  approved           — approver approved the request
  rejected           — approver rejected the request
  reprocessed        — document reprocessed after correction
"""
import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class ReviewActionType(str, enum.Enum):
    submitted = "submitted"
    assigned = "assigned"
    correction_requested = "correction_requested"
    correction_submitted = "correction_submitted"
    field_corrected = "field_corrected"
    review_completed = "review_completed"
    approved = "approved"
    rejected = "rejected"
    reprocessed = "reprocessed"


class ReviewAction(Base):
    __tablename__ = "review_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"), nullable=False, index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action_type: Mapped[ReviewActionType] = mapped_column(Enum(ReviewActionType), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    request: Mapped["Request"] = relationship("Request", back_populates="review_actions")
    actor: Mapped["User"] = relationship("User", back_populates="review_actions")

    def __repr__(self) -> str:
        return f"<ReviewAction id={self.id} type={self.action_type} request={self.request_id}>"
