"""
ExtractedField model.

Stores one field extracted from one ExtractionRun.
We NEVER overwrite these — ReviewerCorrection records corrections separately.

Supported field names (from spec):
  employee_name, employee_id, merchant_name, expense_date, currency,
  total_amount, expense_purpose, reference_number

Design note:
  extracted_value  = raw text from OCR
  normalized_value = parsed/cleaned value (e.g. "5800.00" from "₹5,800/-")
  Both are preserved. Neither is deleted when a reviewer corrects a value.
"""
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    extraction_run_id: Mapped[int] = mapped_column(
        ForeignKey("extraction_runs.id"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    extracted_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Bounding box as "x0,y0,x1,y1" string (pixels on the rendered page image).
    # None when the OCR engine does not supply word-level coordinates.
    bounding_box: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationship
    extraction_run: Mapped["ExtractionRun"] = relationship("ExtractionRun", back_populates="extracted_fields")

    def __repr__(self) -> str:
        return f"<ExtractedField id={self.id} field={self.field_name!r} value={self.extracted_value!r}>"
