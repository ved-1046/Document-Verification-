"""
DocumentVersion model.

Important design decision: we NEVER delete old document versions.
Each upload creates a new DocumentVersion. The version_number field
tracks sequence per request. The most recent version with status='ready'
is the "current" version for review purposes.
"""
import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class DocType(str, enum.Enum):
    expense_form = "expense_form"
    receipt = "receipt"
    supporting_document = "supporting_document"


class ProcessingStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"), nullable=False, index=True)
    doc_type: Mapped[DocType] = mapped_column(Enum(DocType), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # Storage key: relative path under STORAGE_DIR, e.g. "req-1/v1-receipt.pdf"
    # We never expose the raw filesystem path in API responses.
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 hex
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    uploader_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus), nullable=False, default=ProcessingStatus.pending
    )
    processing_error: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # Relationships
    request: Mapped["Request"] = relationship("Request", back_populates="document_versions")
    uploader: Mapped["User"] = relationship("User")
    extraction_runs: Mapped[list["ExtractionRun"]] = relationship("ExtractionRun", back_populates="document_version")

    def __repr__(self) -> str:
        return f"<DocumentVersion id={self.id} request={self.request_id} type={self.doc_type} v={self.version_number}>"

    @property
    def uploader_name(self) -> str | None:
        return self.uploader.display_name if self.uploader is not None else None
