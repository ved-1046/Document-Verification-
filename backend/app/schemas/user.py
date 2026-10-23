"""
Pydantic schemas for User and Auth endpoints.
"""

from datetime import datetime

from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserCreate(BaseModel):
    display_name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.submitter

    @field_validator("password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 bytes")
        return v

    @field_validator("display_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("display_name must not be empty")
        return v.strip()


class UserRead(BaseModel):
    id: int
    display_name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserSummary(BaseModel):
    id: int
    display_name: str
    role: UserRole

    model_config = {"from_attributes": True}


class AdminUserCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    role: UserRole
    is_active: bool = True

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Full name is required")
        return value


class AdminUserUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Full name is required")
        return value


class AdminUserCreated(UserRead):
    temporary_password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if len(value) < 10:
            raise ValueError("New password must be at least 10 characters")
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 bytes")
        return value
