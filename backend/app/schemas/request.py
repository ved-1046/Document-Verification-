"""
Pydantic schemas for Request and DocumentVersion endpoints.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.models.request import RequestStatus, RequestType
from app.models.document_version import DocType, ProcessingStatus


# ── Request schemas ───────────────────────────────────────────────────────────

class RequestCreate(BaseModel):
    title: str = "Expense Reimbursement"
    description: Optional[str] = None
    request_type: RequestType = RequestType.expense_reimbursement
    expense_category: str = "other"
    claimed_amount: Optional[Decimal] = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    expense_date: Optional[date] = None
    currency: str = "INR"
    assigned_reviewer_id: Optional[int] = None
    assigned_approver_id: Optional[int] = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        cleaned = v.strip() if v else ""
        return cleaned or "Expense Reimbursement"

    @field_validator("expense_category")
    @classmethod
    def category_not_empty(cls, v: str) -> str:
        value = v.strip()
        if not value or len(value) > 80:
            raise ValueError("expense_category must contain 1 to 80 characters")
        return value

    @field_validator("currency")
    @classmethod
    def currency_code(cls, v: str) -> str:
        value = v.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise ValueError("currency must be a three-letter code")
        return value


class RequestRead(BaseModel):
    id: int
    request_number: str
    request_type: RequestType
    title: str
    description: Optional[str]
    expense_category: str = "other"
    claimed_amount: Optional[Decimal] = None
    expense_date: Optional[date] = None
    currency: str = "INR"
    submitter_id: int
    assigned_reviewer_id: Optional[int]
    assigned_approver_id: Optional[int] = None
    submitter: Optional["RequestIdentity"] = None
    assigned_reviewer: Optional["RequestIdentity"] = None
    assigned_approver: Optional["RequestIdentity"] = None
    status: RequestStatus
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime]

    model_config = {"from_attributes": True}


class RequestListItem(BaseModel):
    id: int
    request_number: str
    title: str
    expense_category: str = "other"
    claimed_amount: Optional[Decimal] = None
    expense_date: Optional[date] = None
    currency: str = "INR"
    submitter_name: Optional[str] = None
    assigned_reviewer_id: Optional[int] = None
    assigned_approver_id: Optional[int] = None
    assigned_reviewer: Optional["RequestIdentity"] = None
    assigned_approver: Optional["RequestIdentity"] = None
    status: RequestStatus
    request_type: RequestType
    submitter_id: int
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RequestIdentity(BaseModel):
    id: int
    display_name: str
    role: str

    model_config = {"from_attributes": True}


RequestRead.model_rebuild()
RequestListItem.model_rebuild()


class RequestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    expense_category: Optional[str] = None
    claimed_amount: Optional[Decimal] = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    expense_date: Optional[date] = None
    currency: Optional[str] = None
    assigned_reviewer_id: Optional[int] = None
    assigned_approver_id: Optional[int] = None


class RequestAssignmentUpdate(BaseModel):
    assigned_reviewer_id: int
    assigned_approver_id: int


# ── Document schemas ──────────────────────────────────────────────────────────

class DocumentVersionRead(BaseModel):
    id: int
    request_id: int
    doc_type: DocType
    original_filename: str
    mime_type: str
    file_size: int
    version_number: int
    uploader_id: int
    uploader_name: Optional[str] = None
    uploaded_at: datetime
    processing_status: ProcessingStatus
    processing_error: Optional[str]

    model_config = {"from_attributes": True}


class ExtractionFieldRead(BaseModel):
    id: int
    field_name: str
    extracted_value: Optional[str]
    normalized_value: Optional[str]
    page_number: Optional[int]
    bounding_box: Optional[str]
    confidence: Optional[float]

    model_config = {"from_attributes": True}


class ExtractionRunRead(BaseModel):
    id: int
    document_version_id: int
    ocr_engine: str
    status: str
    error_details: Optional[str]
    fields: list[ExtractionFieldRead] = []

    model_config = {"from_attributes": True}
