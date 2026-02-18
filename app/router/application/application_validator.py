"""Application Pydantic validators."""

from typing import Optional
from datetime import datetime, date
from uuid import UUID

from pydantic import BaseModel, field_validator

class ApplicationCreateRequest(BaseModel):
    name: str
    type: str
    status: str
    assign_by: UUID
    launch_date: Optional[date] = None
    package_name: Optional[str] = None
    note: Optional[str] = None

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v):
        if v not in ("android", "ios"):
            raise ValueError("App type must be 'android' or 'ios'")
        return v.lower()

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if v not in ("active", "inactive"):
            raise ValueError("Status must be 'active' or 'inactive'")
        return v.lower()


class ApplicationUpdateRequest(BaseModel):
    name: Optional[str] = None
    launch_date: Optional[date] = None
    type: Optional[str] = None
    package_name: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None
    assign_by: Optional[UUID] = None

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v):
        if v and v.lower() not in ("android", "ios"):
            raise ValueError("App type must be 'android' or 'ios'")
        return v.lower() if v else v

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if v and v.lower() not in ("active", "inactive"):
            raise ValueError("Status must be 'active' or 'inactive'")
        return v.lower() if v else v


class ApplicationOut(BaseModel):
    id: UUID
    name: str
    type: str
    status: str
    api_key: str
    assign_by: UUID
    launch_date: Optional[date]
    package_name: Optional[str]
    note: Optional[str]
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
