"""Ad Field access layer — DB queries."""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.model.ad_field import AdField
from app.services.logger.logger import get_logger

logger = get_logger(__name__)


class AdFieldQuery:
    """Database queries used by the ad field router."""

    @staticmethod
    async def get_all(db: AsyncSession, app_id: Optional[UUID] = None, type_: Optional[str] = None, user_id: Optional[UUID] = None):
        """Return all active ad fields with optional filters for app_id, type, and user_id."""
        logger.debug("AdFieldQuery.get_all called app_id=%s type_=%s user_id=%s", app_id, type_, user_id)
        stmt = select(AdField).where(AdField.is_deleted.is_(False))

        if app_id:
            stmt = stmt.where(AdField.app_id == app_id)
        if type_:
            stmt = stmt.where(AdField.type == type_)
        if user_id:
            stmt = stmt.where((AdField.created_by == user_id) | (AdField.updated_by == user_id))

        stmt = stmt.order_by(AdField.created_at.desc())
        result = await db.execute(stmt)
        items = result.scalars().all()
        logger.debug("AdFieldQuery.get_all returned count=%s", len(items))
        return items

    @staticmethod
    async def get_by_id(field_id: UUID, db: AsyncSession) -> Optional[AdField]:
        """Return an active ad field by ID."""
        logger.debug("AdFieldQuery.get_by_id called field_id=%s", field_id)
        result = await db.execute(
            select(AdField).where(AdField.id == field_id, AdField.is_deleted.is_(False))
        )
        item = result.scalar_one_or_none()
        logger.debug("AdFieldQuery.get_by_id found=%s", bool(item))
        return item

    @staticmethod
    async def get_all_for_user(db: AsyncSession, user_app_ids: list, app_id: Optional[UUID] = None, type_: Optional[str] = None):
        """Return all active ad fields that belong to the user's assigned applications."""
        logger.debug("AdFieldQuery.get_all_for_user called user_app_ids=%s app_id=%s type_=%s", len(user_app_ids), app_id, type_)
        stmt = select(AdField).where(
            AdField.is_deleted.is_(False),
            AdField.app_id.in_(user_app_ids),
        )
        if app_id:
            stmt = stmt.where(AdField.app_id == app_id)
        if type_:
            stmt = stmt.where(AdField.type == type_)
        stmt = stmt.order_by(AdField.created_at.desc())
        result = await db.execute(stmt)
        items = result.scalars().all()
        logger.debug("AdFieldQuery.get_all_for_user returned count=%s", len(items))
        return items

    @staticmethod
    async def get_by_id_for_user(field_id: UUID, user_app_ids: list, db: AsyncSession) -> Optional[AdField]:
        """Return an active ad field by ID only if it belongs to the user's assigned applications."""
        logger.debug("AdFieldQuery.get_by_id_for_user called field_id=%s user_app_ids=%s", field_id, len(user_app_ids))
        result = await db.execute(
            select(AdField).where(
                AdField.id == field_id,
                AdField.is_deleted.is_(False),
                AdField.app_id.in_(user_app_ids),
            )
        )
        item = result.scalar_one_or_none()
        logger.debug("AdFieldQuery.get_by_id_for_user found=%s", bool(item))
        return item
