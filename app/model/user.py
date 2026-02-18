"""User model with RBAC and soft delete support."""

from typing import ClassVar
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, VARCHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.model.base import BaseModel


class User(BaseModel):
    """Represents system users with role-based access."""

    __tablename__: ClassVar[str] = "app_user"

    __table_args__: ClassVar = (
        CheckConstraint("role IN ('admin','user')", name="ck_user_role"),
        CheckConstraint("status IN ('active','inactive')", name="ck_user_status"),
    )

    email: Mapped[str] = mapped_column(
        VARCHAR(255),
        unique=True,
        nullable=False,
        index=True,
    )

    password: Mapped[str] = mapped_column(
        VARCHAR(255),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        VARCHAR(20),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        VARCHAR(20),
        nullable=False,
        default="active",
        index=True,
    )

    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("app_user.id"),
        nullable=True,
    )

    updated_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("app_user.id"),
        nullable=True,
    )

    creator = relationship(
        "User",
        foreign_keys=[created_by],
        remote_side="User.id",
        lazy="joined",
    )

    updater = relationship(
        "User",
        foreign_keys=[updated_by],
        remote_side="User.id",
        lazy="joined",
    )

    def is_admin(self) -> bool:
        return self.role == "admin"

    def is_active(self) -> bool:
        return self.status == "active"
