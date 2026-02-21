"""Pydantic schemas for user login logs."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class LoginLogOut(BaseModel):
    """Serialised login log record."""

    id: UUID
    user_id: UUID
    login_time: datetime
    logout_time: Optional[datetime]
    ip_address: Optional[str]
    device_info: Optional[str]
    login_status: str
    created_at: datetime

    class Config:
        from_attributes = True


