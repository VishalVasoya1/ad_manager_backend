"""Ad Type Pydantic request/response validators."""

from typing import Optional
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator

class AdTypeCreateRequest(BaseModel):
    app_id: UUID
    ad_format_id: UUID
    ad_platform_id: UUID
    status: str

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if v not in ("active", "inactive"):
            raise ValueError("Status must be 'active' or 'inactive'")
        return v.lower()

class AdTypeUpdateRequest(BaseModel):
    status: Optional[str] = None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if v and v.lower() not in ("active", "inactive"):
            raise ValueError("Status must be 'active' or 'inactive'")
        return v.lower() if v else v

class AdTypeOut(BaseModel):
    id: UUID
    app_id: UUID
    ad_format_id: UUID
    ad_platform_id: UUID
    status: str
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True


