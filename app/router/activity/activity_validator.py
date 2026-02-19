"""Pydantic schemas for user activity."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ActivityOut(BaseModel):
    """Serialised user activity record."""

    id: UUID
    user_id: UUID
    module: str
    action: str
    reference_id: Optional[UUID]
    description: Optional[str]
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
