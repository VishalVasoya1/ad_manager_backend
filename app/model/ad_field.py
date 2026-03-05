"""Ad field model for dynamic ad configuration inputs."""

from typing import ClassVar
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.model.base import BaseModel


class AdField(BaseModel):
    """Represents dynamic fields attached to an application."""

    __tablename__: ClassVar[str] = "ad_field"

    __table_args__: ClassVar = (
        CheckConstraint(
            "type IN ('radio','dropdown','input','textfield','checkbox')",
            name="ck_ad_field_type",
        ),
    )

    app_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("application.id"),
        nullable=False,
        index=True,
    )

    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    regex: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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

    application = relationship(
        "Application",
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
