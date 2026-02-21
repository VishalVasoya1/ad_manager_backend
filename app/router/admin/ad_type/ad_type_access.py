"""Ad Type access layer Ã¢â‚¬â€ DB queries."""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.model.ad_type import AdType
from app.services.logger.logger import get_logger

logger = get_logger(__name__)


class AdTypeQuery:
    """Database queries used by the ad type router."""

    @staticmethod
    async def get_all(db: AsyncSession, app_id: Optional[UUID] = None, status: Optional[str] = None, user_id: Optional[UUID] = None):
        """Return all active ad types with optional filters for app_id, status, and user_id (created_by/updated_by)."""
        logger.debug("AdTypeQuery.get_all called app_id=%s status=%s user_id=%s", app_id, status, user_id)
        stmt = select(AdType).where(AdType.is_deleted.is_(False))
        
        if app_id:
            stmt = stmt.where(AdType.app_id == app_id)
        
        if status:
            stmt = stmt.where(AdType.status == status)
        
        if user_id:
            stmt = stmt.where((AdType.created_by == user_id) | (AdType.updated_by == user_id))
        
        stmt = stmt.order_by(AdType.created_at.desc())
        result = await db.execute(stmt)
        items = result.scalars().all()
        logger.debug("AdTypeQuery.get_all returned count=%s", len(items))
        return items

    @staticmethod
    async def get_by_id(ad_type_id: UUID, db: AsyncSession) -> Optional[AdType]:
        """Return an active ad type by ID."""
        logger.debug("AdTypeQuery.get_by_id called ad_type_id=%s", ad_type_id)
        result = await db.execute(
            select(AdType).where(AdType.id == ad_type_id, AdType.is_deleted.is_(False))
        )
        item = result.scalar_one_or_none()
        logger.debug("AdTypeQuery.get_by_id found=%s", bool(item))
        return item

    @staticmethod
    async def get_all_for_user(db: AsyncSession, user_app_ids: list, app_id: Optional[UUID] = None, status: Optional[str] = None):
        """Return all active ad types that belong to the user's assigned applications."""
        logger.debug(
            "AdTypeQuery.get_all_for_user called user_app_ids=%s app_id=%s status=%s",
            len(user_app_ids), app_id, status
        )
        stmt = select(AdType).where(
            AdType.is_deleted.is_(False),
            AdType.app_id.in_(user_app_ids),
        )
        if app_id:
            stmt = stmt.where(AdType.app_id == app_id)
        if status:
            stmt = stmt.where(AdType.status == status)
        stmt = stmt.order_by(AdType.created_at.desc())
        result = await db.execute(stmt)
        items = result.scalars().all()
        logger.debug("AdTypeQuery.get_all_for_user returned count=%s", len(items))
        return items

    @staticmethod
    async def get_by_id_for_user(ad_type_id: UUID, user_app_ids: list, db: AsyncSession) -> Optional[AdType]:
        """Return an active ad type by ID only if it belongs to the user's assigned applications."""
        logger.debug(
            "AdTypeQuery.get_by_id_for_user called ad_type_id=%s user_app_ids=%s",
            ad_type_id, len(user_app_ids)
        )
        result = await db.execute(
            select(AdType).where(
                AdType.id == ad_type_id,
                AdType.is_deleted.is_(False),
                AdType.app_id.in_(user_app_ids),
            )
        )
        item = result.scalar_one_or_none()
        logger.debug("AdTypeQuery.get_by_id_for_user found=%s", bool(item))
        return item


