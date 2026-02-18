"""Application model with admin control and user assignment support."""

from datetime import date
from typing import ClassVar
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.model.base import BaseModel


class Application(BaseModel):
    """Represents applications managed by admin and assigned to users."""

    __tablename__: ClassVar[str] = "application"

    __table_args__: ClassVar = (
        CheckConstraint("type IN ('android','ios')", name="ck_application_type"),
        CheckConstraint("status IN ('active','inactive')", name="ck_application_status"),
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    launch_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    package_name: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        index=True,
    )

    api_key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    assign_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("app_user.id"),
        nullable=False,
        index=True,
    )

    created_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("app_user.id"),
        nullable=False,
    )

    updated_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("app_user.id"),
        nullable=False,
    )

    assigned_user = relationship(
        "User",
        foreign_keys=[assign_by],
        lazy="joined",
    )

    creator = relationship(
        "User",
        foreign_keys=[created_by],
        lazy="joined",
    )

    updater = relationship(
        "User",
        foreign_keys=[updated_by],
        lazy="joined",
    )

    def is_active(self) -> bool:
        return self.status == "active"
