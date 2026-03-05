"""Ad Field Pydantic request/response validators."""

from typing import Optional
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator


class AdFieldOut(BaseModel):
    id: UUID
    app_id: UUID
    type: str
    value: Optional[str]
    regex: Optional[str]
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
