"""Ad Master access layer — DB queries."""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.model.ad_master import AdMaster


class AdMasterQuery:
    """Database queries used by the ad master router."""

    @staticmethod
    async def get_all(db: AsyncSession, user_id: Optional[UUID] = None, type_: Optional[str] = None):
        """Return all active ad master entries with optional filters for user_id (created_by/updated_by) and type."""
        stmt = select(AdMaster).where(AdMaster.is_deleted.is_(False))
        
        if user_id:
            stmt = stmt.where((AdMaster.created_by == user_id) | (AdMaster.updated_by == user_id))
        
        if type_:
            stmt = stmt.where(AdMaster.type == type_)
        
        stmt = stmt.order_by(AdMaster.created_at.desc())
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_by_id(ad_master_id: UUID, db: AsyncSession) -> Optional[AdMaster]:
        """Return an active ad master entry by ID."""
        result = await db.execute(
            select(AdMaster).where(AdMaster.id == ad_master_id, AdMaster.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_title_and_type(title: str, type_: str, db: AsyncSession) -> Optional[AdMaster]:
        """Return an active ad master entry matching the given title and type."""
        result = await db.execute(
            select(AdMaster).where(AdMaster.title == title, AdMaster.type == type_, AdMaster.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_title_and_type_any(title: str, type_: str, db: AsyncSession) -> Optional[AdMaster]:
        """Return an ad master entry matching the given title and type regardless of soft-delete status."""
        result = await db.execute(
            select(AdMaster).where(AdMaster.title == title, AdMaster.type == type_)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def search_by_type(type_: Optional[str], db: AsyncSession):
        """Return active ad master entries filtered by type, ordered by title."""
        stmt = select(AdMaster).where(AdMaster.is_deleted.is_(False))
        if type_:
            stmt = stmt.where(AdMaster.type == type_)
        stmt = stmt.order_by(AdMaster.title)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_by_id_and_type(ad_master_id: UUID, type_: str, db: AsyncSession) -> Optional[AdMaster]:
        """Return an active ad master entry matching the given ID and type."""
        result = await db.execute(
            select(AdMaster).where(
                AdMaster.id == ad_master_id,
                AdMaster.type == type_,
                AdMaster.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()
