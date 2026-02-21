"""Pydantic schemas for user activity."""

import json
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class ActivityOut(BaseModel):
    """Serialised user activity record."""

    id: UUID
    user_id: UUID
    module: str
    action: str
    reference_id: Optional[UUID]
    description: Optional[Any]
    ip_address: Optional[str]
    created_at: datetime

    @field_validator("description", mode="before")
    @classmethod
    def parse_json_description(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    class Config:
        from_attributes = True



