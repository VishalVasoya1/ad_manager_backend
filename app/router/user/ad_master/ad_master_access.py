"""Ad Master access layer Ã¢â‚¬â€ DB queries."""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.model.ad_master import AdMaster
from app.services.logger.logger import get_logger

logger = get_logger(__name__)


class AdMasterQuery:
    """Database queries used by the ad master router."""

    @staticmethod
    async def get_all(db: AsyncSession, user_id: Optional[UUID] = None, type_: Optional[str] = None):
        """Return all active ad master entries with optional filters for user_id (created_by/updated_by) and type."""
        logger.debug("AdMasterQuery.get_all called user_id=%s type_=%s", user_id, type_)
        stmt = select(AdMaster).where(AdMaster.is_deleted.is_(False))
        
        if user_id:
            stmt = stmt.where((AdMaster.created_by == user_id) | (AdMaster.updated_by == user_id))
        
        if type_:
            stmt = stmt.where(AdMaster.type == type_)
        
        stmt = stmt.order_by(AdMaster.created_at.desc())
        result = await db.execute(stmt)
        items = result.scalars().all()
        logger.debug("AdMasterQuery.get_all returned count=%s", len(items))
        return items

    @staticmethod
    async def get_by_id(ad_master_id: UUID, db: AsyncSession) -> Optional[AdMaster]:
        """Return an active ad master entry by ID."""
        logger.debug("AdMasterQuery.get_by_id called ad_master_id=%s", ad_master_id)
        result = await db.execute(
            select(AdMaster).where(AdMaster.id == ad_master_id, AdMaster.is_deleted.is_(False))
        )
        item = result.scalar_one_or_none()
        logger.debug("AdMasterQuery.get_by_id found=%s", bool(item))
        return item

    @staticmethod
    async def get_by_title_and_type(title: str, type_: str, db: AsyncSession) -> Optional[AdMaster]:
        """Return an active ad master entry matching the given title and type."""
        logger.debug("AdMasterQuery.get_by_title_and_type called title=%s type_=%s", title, type_)
        result = await db.execute(
            select(AdMaster).where(AdMaster.title == title, AdMaster.type == type_, AdMaster.is_deleted.is_(False))
        )
        item = result.scalar_one_or_none()
        logger.debug("AdMasterQuery.get_by_title_and_type found=%s", bool(item))
        return item

    @staticmethod
    async def get_by_title_and_type_any(title: str, type_: str, db: AsyncSession) -> Optional[AdMaster]:
        """Return an ad master entry matching the given title and type regardless of soft-delete status."""
        logger.debug("AdMasterQuery.get_by_title_and_type_any called title=%s type_=%s", title, type_)
        result = await db.execute(
            select(AdMaster).where(AdMaster.title == title, AdMaster.type == type_)
        )
        item = result.scalar_one_or_none()
        logger.debug("AdMasterQuery.get_by_title_and_type_any found=%s", bool(item))
        return item

    @staticmethod
    async def search_by_type(type_: Optional[str], db: AsyncSession):
        """Return active ad master entries filtered by type, ordered by created_at descending."""
        logger.debug("AdMasterQuery.search_by_type called type_=%s", type_)
        stmt = select(AdMaster).where(AdMaster.is_deleted.is_(False))
        if type_:
            stmt = stmt.where(AdMaster.type == type_)
        stmt = stmt.order_by(AdMaster.created_at.desc())
        result = await db.execute(stmt)
        items = result.scalars().all()
        logger.debug("AdMasterQuery.search_by_type returned count=%s", len(items))
        return items

    @staticmethod
    async def get_by_id_and_type(ad_master_id: UUID, type_: str, db: AsyncSession) -> Optional[AdMaster]:
        """Return an active ad master entry matching the given ID and type."""
        logger.debug("AdMasterQuery.get_by_id_and_type called ad_master_id=%s type_=%s", ad_master_id, type_)
        result = await db.execute(
            select(AdMaster).where(
                AdMaster.id == ad_master_id,
                AdMaster.type == type_,
                AdMaster.is_deleted.is_(False),
            )
        )
        item = result.scalar_one_or_none()
        logger.debug("AdMasterQuery.get_by_id_and_type found=%s", bool(item))
        return item


