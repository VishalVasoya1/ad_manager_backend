"""Auth Pydantic validators."""

from typing import Optional
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator

class AuthLoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def lower_email(cls, v):
        return v.lower()


class AuthResponse(BaseModel):
    """Serialised user data returned on successful login."""

    id: UUID
    email: str
    role: str
    status: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
