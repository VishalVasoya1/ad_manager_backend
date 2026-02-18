"""User access layer — DB queries for user management."""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.model.user import User


class UserQuery:
    """Database queries used by the user router."""

    @staticmethod
    async def get_all_users(
        db: AsyncSession,
        page: int,
        size: int,
        search: Optional[str],
        role: Optional[str],
        status: Optional[str],
    ):
        """Return paginated users with optional email search, role, and status filters."""
        stmt = select(User).where(User.is_deleted.is_(False))

        if search:
            stmt = stmt.where(User.email.ilike(f"%{search}%"))
        if role:
            stmt = stmt.where(User.role == role)
        if status:
            stmt = stmt.where(User.status == status)

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(total_stmt)).scalar_one()

        stmt = stmt.order_by(User.created_at.desc()).offset((page - 1) * size).limit(size)
        result = await db.execute(stmt)
        return total, result.scalars().all()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
        """Return an active user by ID."""
        result = await db.execute(
            select(User).where(User.id == user_id, User.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Return an active user by email."""
        result = await db.execute(
            select(User).where(User.email == email.lower(), User.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_email_any(db: AsyncSession, email: str) -> Optional[User]:
        """Return a user by email regardless of soft-delete status."""
        result = await db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()
