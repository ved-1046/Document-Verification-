"""
AuditEvent model.

Low-level security and compliance log.
Records every significant system event regardless of business workflow.
These events are append-only: never update or delete.
"""
import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class AuditEventType(str, enum.Enum):
    user_registered = "user_registered"
    user_login = "user_login"
    user_login_failed = "user_login_failed"
    request_created = "request_created"
    request_status_changed = "request_status_changed"
    document_uploaded = "document_uploaded"
    document_downloaded = "document_downloaded"
    extraction_started = "extraction_started"
    extraction_completed = "extraction_completed"
    extraction_failed = "extraction_failed"
    verification_run = "verification_run"
    field_corrected = "field_corrected"
    review_action = "review_action"
    unauthorized_access_attempt = "unauthorized_access_attempt"
    invalid_transition_attempt = "invalid_transition_attempt"


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    request_id: Mapped[int | None] = mapped_column(ForeignKey("requests.id"), nullable=True, index=True)
    event_type: Mapped[AuditEventType] = mapped_column(Enum(AuditEventType), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Human-readable summary. NO secrets or personal data.
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    actor: Mapped["User | None"] = relationship("User")
    request: Mapped["Request | None"] = relationship("Request", back_populates="audit_events")

    def __repr__(self) -> str:
        return f"<AuditEvent id={self.id} type={self.event_type}>"
