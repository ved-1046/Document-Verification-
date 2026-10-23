"""
VerificationCheck model.

Each run of the verification engine stores its checks here.
Supported check types:
  missing_field   — a required field was absent or unreadable
  amount_mismatch — amounts in two documents don't match
  date_mismatch   — dates expected to match don't

Important: a flag is a signal for human review, NOT proof of wrongdoing.
The resolution_status tracks whether a reviewer has addressed it.
"""
import enum
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class CheckType(str, enum.Enum):
    missing_field = "missing_field"
    amount_mismatch = "amount_mismatch"
    date_mismatch = "date_mismatch"


class CheckResult(str, enum.Enum):
    pass_ = "pass"
    flag = "flag"
    info = "info"
    error = "error"


class CheckSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ResolutionStatus(str, enum.Enum):
    open = "open"
    resolved = "resolved"
    dismissed = "dismissed"


class VerificationCheck(Base):
    __tablename__ = "verification_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"), nullable=False, index=True)
    # JSON array of document_version IDs used in this check, stored as CSV string
    document_version_ids: Mapped[str | None] = mapped_column(String(200), nullable=True)
    check_type: Mapped[CheckType] = mapped_column(Enum(CheckType), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(100), nullable=False)
    result: Mapped[CheckResult] = mapped_column(Enum(CheckResult), nullable=False)
    severity: Mapped[CheckSeverity] = mapped_column(Enum(CheckSeverity), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON: list of {doc_version_id, field_name, extracted_value, page_number}
    evidence_references: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolution_status: Mapped[ResolutionStatus] = mapped_column(
        Enum(ResolutionStatus), nullable=False, default=ResolutionStatus.open
    )
    # ChangeMap: only current checks drive review UI; historical rows preserved.
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    # Relationships
    request: Mapped["Request"] = relationship("Request", back_populates="verification_checks")

    def __repr__(self) -> str:
        return f"<VerificationCheck id={self.id} type={self.check_type} result={self.result}>"
