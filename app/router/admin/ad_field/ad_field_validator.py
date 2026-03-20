"""Ad Field Pydantic request/response validators."""

from typing import Optional
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator


class AdFieldCreateRequest(BaseModel):
    app_id: UUID
    title: Optional[str] = None
    type: str
    value: Optional[str] = None
    type_value: Optional[str] = None
    regex: Optional[str] = None

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v):
        valid = ("radio", "dropdown", "input", "textfield", "checkbox")
        if v not in valid:
            raise ValueError(f"Ad field type must be one of: {', '.join(valid)}")
        return v.lower()


class AdFieldUpdateRequest(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    value: Optional[str] = None
    type_value: Optional[str] = None
    regex: Optional[str] = None

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v):
        valid = ("radio", "dropdown", "input", "textfield", "checkbox")
        if v and v.lower() not in valid:
            raise ValueError(f"Ad field type must be one of: {', '.join(valid)}")
        return v.lower() if v else v


class AdFieldOut(BaseModel):
    id: UUID
    app_id: UUID
    title: Optional[str]
    type: str
    value: Optional[str]
    type_value: Optional[str]
    regex: Optional[str]
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
