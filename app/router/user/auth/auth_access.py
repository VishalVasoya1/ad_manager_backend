"""Auth access layer Ã¢â‚¬â€ DB queries for authentication."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.model.user import User
from app.services.logger.logger import get_logger

logger = get_logger(__name__)


class AuthQuery:
    """Database queries used by the auth router."""

    @staticmethod
    async def get_user_by_email(email: str, db: AsyncSession):
        """Return an active user matching the given email."""
        logger.debug("AuthQuery.get_user_by_email called email=%s", email)
        result = await db.execute(
            select(User).where(User.email == email, User.is_deleted.is_(False))
        )
        user = result.scalar_one_or_none()
        logger.debug("AuthQuery.get_user_by_email found=%s", bool(user))
        return user

    @staticmethod
    async def get_user_by_id(user_id, db: AsyncSession):
        """Return an active user matching the given ID."""
        logger.debug("AuthQuery.get_user_by_id called user_id=%s", user_id)
        result = await db.execute(
            select(User).where(User.id == user_id, User.is_deleted.is_(False))
        )
        user = result.scalar_one_or_none()
        logger.debug("AuthQuery.get_user_by_id found=%s", bool(user))
        return user

    @staticmethod
    async def insert_user(user_data: dict, db: AsyncSession) -> User:
        """Insert and return a new user record."""
        logger.debug("AuthQuery.insert_user called email=%s role=%s", user_data.get("email"), user_data.get("role"))
        new_user = User(**user_data)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        logger.info("AuthQuery.insert_user created user_id=%s", new_user.id)
        return new_user


