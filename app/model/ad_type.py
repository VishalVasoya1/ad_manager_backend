"""Ad type model linking application, format, and platform dynamically."""

from typing import ClassVar
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.model.base import BaseModel


class AdType(BaseModel):
    """Represents configured ad types per application."""

    __tablename__: ClassVar[str] = "ad_type"

    __table_args__: ClassVar = (
        CheckConstraint(
            "status IN ('active','inactive')",
            name="ck_ad_type_status",
        ),
    )

    app_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("application.id"),
        nullable=False,
        index=True,
    )

    ad_format_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ad_master.id"),
        nullable=False,
        index=True,
    )

    ad_platform_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ad_master.id"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
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

    application = relationship(
        "Application",
        lazy="joined",
    )

    ad_format = relationship(
        "AdMaster",
        foreign_keys=[ad_format_id],
        lazy="joined",
    )

    ad_platform = relationship(
        "AdMaster",
        foreign_keys=[ad_platform_id],
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
