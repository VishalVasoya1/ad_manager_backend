"""Token blacklist model for logout/token invalidation."""

from datetime import datetime
from typing import ClassVar

from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.model.base import Base


class TokenBlacklist(Base):
    """Stores invalidated JWT tokens until they expire."""

    __tablename__: ClassVar[str] = "token_blacklist"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        index=True,
    )

    blacklisted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
