"""Ad master model for dynamic dropdown management."""

from typing import ClassVar
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.model.base import BaseModel


class AdMaster(BaseModel):
    """Stores ad formats and ad platforms for dynamic configuration."""

    __tablename__: ClassVar[str] = "ad_master"

    __table_args__: ClassVar = (
        CheckConstraint(
            "type IN ('ad_format','ad_platform')",
            name="ck_ad_master_type",
        ),
        UniqueConstraint(
            "type",
            "title",
            name="uq_ad_master_type_title",
        ),
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    type: Mapped[str] = mapped_column(
        String(50),
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
