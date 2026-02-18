"""User Pydantic validators."""

from typing import Optional
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=50)
    role: str
    status: str = "active"

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return v

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, v):
        if v.lower() not in ("admin", "user"):
            raise ValueError("Role must be 'admin' or 'user'")
        return v.lower()

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if v.lower() not in ("active", "inactive"):
            raise ValueError("Status must be 'active' or 'inactive'")
        return v.lower()


class UserOut(BaseModel):
    """Serialised user data returned in API responses."""

    id: UUID
    email: EmailStr
    role: str
    status: str
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    status: Optional[str] = None
    password: Optional[str] = None

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, v):
        if v and v.lower() not in ("admin", "user"):
            raise ValueError("Role must be 'admin' or 'user'")
        return v.lower() if v else v

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if v and v.lower() not in ("active", "inactive"):
            raise ValueError("Status must be 'active' or 'inactive'")
        return v.lower() if v else v
