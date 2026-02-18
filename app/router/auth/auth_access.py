"""Auth access layer — DB queries for authentication."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.model.user import User


class AuthQuery:
    """Database queries used by the auth router."""

    @staticmethod
    async def get_user_by_email(email: str, db: AsyncSession):
        """Return an active user matching the given email."""
        result = await db.execute(
            select(User).where(User.email == email, User.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(user_id, db: AsyncSession):
        """Return an active user matching the given ID."""
        result = await db.execute(
            select(User).where(User.id == user_id, User.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def insert_user(user_data: dict, db: AsyncSession) -> User:
        """Insert and return a new user record."""
        new_user = User(**user_data)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user
