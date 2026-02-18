"""Ad Type access layer — DB queries."""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.model.ad_type import AdType


class AdTypeQuery:
    """Database queries used by the ad type router."""

    @staticmethod
    async def get_all(db: AsyncSession, app_id: Optional[UUID] = None, status: Optional[str] = None, user_id: Optional[UUID] = None):
        """Return all active ad types with optional filters for app_id, status, and user_id (created_by/updated_by)."""
        stmt = select(AdType).where(AdType.is_deleted.is_(False))
        
        if app_id:
            stmt = stmt.where(AdType.app_id == app_id)
        
        if status:
            stmt = stmt.where(AdType.status == status)
        
        if user_id:
            stmt = stmt.where((AdType.created_by == user_id) | (AdType.updated_by == user_id))
        
        stmt = stmt.order_by(AdType.created_at.desc())
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_by_id(ad_type_id: UUID, db: AsyncSession) -> Optional[AdType]:
        """Return an active ad type by ID."""
        result = await db.execute(
            select(AdType).where(AdType.id == ad_type_id, AdType.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()
