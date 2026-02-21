"""DB queries for user activity."""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.model.user_activity import UserActivity
from app.services.logger.logger import get_logger

logger = get_logger(__name__)


class ActivityQuery:
    """Database queries used by the activity router."""

    @staticmethod
    async def get_all(
        db: AsyncSession,
        page: int,
        size: int,
        user_id: Optional[UUID] = None,
        module: Optional[str] = None,
        action: Optional[str] = None,
    ):
        """Return paginated activity records with optional filters."""
        logger.debug(
            "ActivityQuery.get_all called page=%s size=%s user_id=%s module=%s action=%s",
            page, size, user_id, module, action
        )
        stmt = select(UserActivity)

        if user_id:
            stmt = stmt.where(UserActivity.user_id == user_id)
        if module:
            stmt = stmt.where(UserActivity.module == module)
        if action:
            stmt = stmt.where(UserActivity.action == action)

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(total_stmt)).scalar_one()

        stmt = stmt.order_by(UserActivity.created_at.desc()).offset((page - 1) * size).limit(size)
        result = await db.execute(stmt)
        items = result.scalars().all()
        logger.debug("ActivityQuery.get_all returned total=%s page_items=%s", total, len(items))
        return total, items

    @staticmethod
    async def get_by_id(db: AsyncSession, activity_id: UUID) -> Optional[UserActivity]:
        """Return a single activity record by ID."""
        logger.debug("ActivityQuery.get_by_id called activity_id=%s", activity_id)
        result = await db.execute(
            select(UserActivity).where(UserActivity.id == activity_id)
        )
        item = result.scalar_one_or_none()
        logger.debug("ActivityQuery.get_by_id found=%s", bool(item))
        return item



