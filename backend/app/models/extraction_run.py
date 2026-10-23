"""
ExtractionRun model.

Each OCR/text-extraction pass on a DocumentVersion creates one ExtractionRun.
This lets us track which engine was used, whether it succeeded, and
link ExtractedFields to the specific run.
"""
import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class ExtractionStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_version_id: Mapped[int] = mapped_column(
        ForeignKey("document_versions.id"), nullable=False, index=True
    )
    ocr_engine: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "tesseract-5.3.1"
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[ExtractionStatus] = mapped_column(
        Enum(ExtractionStatus), nullable=False, default=ExtractionStatus.pending
    )
    error_details: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # Relationships
    document_version: Mapped["DocumentVersion"] = relationship("DocumentVersion", back_populates="extraction_runs")
    extracted_fields: Mapped[list["ExtractedField"]] = relationship("ExtractedField", back_populates="extraction_run")

    def __repr__(self) -> str:
        return f"<ExtractionRun id={self.id} doc={self.document_version_id} status={self.status}>"
