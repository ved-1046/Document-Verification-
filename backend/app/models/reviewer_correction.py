"""
ReviewerCorrection model.

When a reviewer corrects an extracted value, we DO NOT modify ExtractedField.
We create a ReviewerCorrection that records:
  - the original extracted value (preserved)
  - the corrected value
  - who corrected it and why
  - which document version and field it applies to

The verification engine re-runs using corrected values where present.
"""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class ReviewerCorrection(Base):
    __tablename__ = "reviewer_corrections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"), nullable=False, index=True)
    document_version_id: Mapped[int] = mapped_column(
        ForeignKey("document_versions.id"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    original_extracted_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_value: Mapped[str] = mapped_column(Text, nullable=False)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    request: Mapped["Request"] = relationship("Request", back_populates="corrections")
    document_version: Mapped["DocumentVersion"] = relationship("DocumentVersion")
    reviewer: Mapped["User"] = relationship("User", back_populates="corrections")

    def __repr__(self) -> str:
        return f"<ReviewerCorrection id={self.id} field={self.field_name!r} by={self.reviewer_id}>"
