"""Ad Field access layer — DB queries."""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.model.ad_field import AdField


class AdFieldQuery:
    """Database queries used by the ad field router."""

    @staticmethod
    async def get_all(db: AsyncSession, app_id: Optional[UUID] = None, ad_type_id: Optional[UUID] = None, type_: Optional[str] = None, user_id: Optional[UUID] = None):
        """Return all active ad fields with optional filters for app_id, ad_type_id, type, and user_id (created_by/updated_by)."""
        stmt = select(AdField).where(AdField.is_deleted.is_(False))
        
        if app_id:
            stmt = stmt.where(AdField.app_id == app_id)
        
        if ad_type_id:
            stmt = stmt.where(AdField.ad_type_id == ad_type_id)
        
        if type_:
            stmt = stmt.where(AdField.type == type_)
        
        if user_id:
            stmt = stmt.where((AdField.created_by == user_id) | (AdField.updated_by == user_id))
        
        stmt = stmt.order_by(AdField.created_at.desc())
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_by_id(field_id: UUID, db: AsyncSession) -> Optional[AdField]:
        """Return an active ad field by ID."""
        result = await db.execute(
            select(AdField).where(AdField.id == field_id, AdField.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()
