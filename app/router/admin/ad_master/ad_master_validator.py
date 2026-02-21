"""Ad Master Pydantic request/response validators."""

from typing import Optional
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator

class AdMasterCreateRequest(BaseModel):
    title: str
    type: str

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v):
        if v not in ("ad_format", "ad_platform"):
            raise ValueError("Type must be 'ad_format' or 'ad_platform'")
        return v.lower()


class AdMasterUpdateRequest(BaseModel):
    title: Optional[str] = None


class AdMasterOut(BaseModel):
    id: UUID
    title: str
    type: str
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AdMasterSearchOut(BaseModel):
    """Minimal ad master projection used in search results."""

    id: UUID
    title: str

    class Config:
        from_attributes = True


