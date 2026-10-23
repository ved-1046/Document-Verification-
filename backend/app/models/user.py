"""
User model.

Roles:
  submitter  — creates requests, uploads documents
  reviewer   — inspects docs, corrects fields, requests corrections
  approver   — makes final decisions (approve/reject)
"""
import enum
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class UserRole(str, enum.Enum):
    submitter = "submitter"
    reviewer = "reviewer"
    approver = "approver"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.submitter)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships (back-references available via lazy load)
    requests: Mapped[list["Request"]] = relationship("Request", back_populates="submitter", foreign_keys="Request.submitter_id")
    review_actions: Mapped[list["ReviewAction"]] = relationship("ReviewAction", back_populates="actor")
    corrections: Mapped[list["ReviewerCorrection"]] = relationship("ReviewerCorrection", back_populates="reviewer")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role}>"
