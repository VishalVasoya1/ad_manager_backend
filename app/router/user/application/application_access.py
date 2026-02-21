"""Application access layer Ã¢â‚¬â€ DB queries."""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.model.application import Application
from app.services.logger.logger import get_logger

logger = get_logger(__name__)


class ApplicationQuery:
    """Database queries used by the application router."""

    @staticmethod
    async def get_all(db: AsyncSession, page: int, size: int, search: Optional[str], app_type: Optional[str], status: Optional[str]):
        """Return paginated applications with optional name, type, and status filters."""
        logger.debug(
            "ApplicationQuery.get_all called page=%s size=%s search=%s app_type=%s status=%s",
            page, size, search, app_type, status
        )
        stmt = select(Application).where(Application.is_deleted.is_(False))
        if search:
            stmt = stmt.where(Application.name.ilike(f"%{search}%"))
        if app_type:
            stmt = stmt.where(Application.type == app_type)
        if status:
            stmt = stmt.where(Application.status == status)
        total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        stmt = stmt.order_by(Application.created_at.desc()).offset((page - 1) * size).limit(size)
        result = await db.execute(stmt)
        items = result.scalars().all()
        logger.debug("ApplicationQuery.get_all returned total=%s page_items=%s", total, len(items))
        return total, items

    @staticmethod
    async def get_by_id(app_id: UUID, db: AsyncSession) -> Optional[Application]:
        """Return an active application by ID."""
        logger.debug("ApplicationQuery.get_by_id called app_id=%s", app_id)
        result = await db.execute(
            select(Application).where(Application.id == app_id, Application.is_deleted.is_(False))
        )
        item = result.scalar_one_or_none()
        logger.debug("ApplicationQuery.get_by_id found=%s", bool(item))
        return item

    @staticmethod
    async def get_by_package_name(package_name: str, db: AsyncSession) -> Optional[Application]:
        """Return an active application by package name."""
        logger.debug("ApplicationQuery.get_by_package_name called package_name=%s", package_name)
        result = await db.execute(
            select(Application).where(
                Application.package_name == package_name,
                Application.is_deleted.is_(False)
            )
        )
        item = result.scalar_one_or_none()
        logger.debug("ApplicationQuery.get_by_package_name found=%s", bool(item))
        return item

    @staticmethod
    async def get_by_package_name_any(package_name: str, db: AsyncSession) -> Optional[Application]:
        """Return an application by package name regardless of soft-delete status."""
        logger.debug("ApplicationQuery.get_by_package_name_any called package_name=%s", package_name)
        result = await db.execute(
            select(Application).where(Application.package_name == package_name)
        )
        item = result.scalar_one_or_none()
        logger.debug("ApplicationQuery.get_by_package_name_any found=%s", bool(item))
        return item

    @staticmethod
    async def get_all_for_user(
        db: AsyncSession,
        user_id: UUID,
        page: int,
        size: int,
        search: Optional[str],
        app_type: Optional[str],
        status: Optional[str],
    ):
        """Return paginated applications assigned to the given user."""
        logger.debug(
            "ApplicationQuery.get_all_for_user called user_id=%s page=%s size=%s search=%s app_type=%s status=%s",
            user_id, page, size, search, app_type, status
        )
        from sqlalchemy import func
        stmt = select(Application).where(
            Application.is_deleted.is_(False),
            Application.assign_by == user_id,
        )
        if search:
            stmt = stmt.where(Application.name.ilike(f"%{search}%"))
        if app_type:
            stmt = stmt.where(Application.type == app_type)
        if status:
            stmt = stmt.where(Application.status == status)
        total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        stmt = stmt.order_by(Application.created_at.desc()).offset((page - 1) * size).limit(size)
        result = await db.execute(stmt)
        items = result.scalars().all()
        logger.debug("ApplicationQuery.get_all_for_user returned total=%s page_items=%s", total, len(items))
        return total, items

    @staticmethod
    async def get_by_id_for_user(app_id: UUID, user_id: UUID, db: AsyncSession) -> Optional[Application]:
        """Return an active application by ID only if it's assigned to the given user."""
        logger.debug("ApplicationQuery.get_by_id_for_user called app_id=%s user_id=%s", app_id, user_id)
        result = await db.execute(
            select(Application).where(
                Application.id == app_id,
                Application.is_deleted.is_(False),
                Application.assign_by == user_id,
            )
        )
        item = result.scalar_one_or_none()
        logger.debug("ApplicationQuery.get_by_id_for_user found=%s", bool(item))
        return item

    @staticmethod
    async def get_app_ids_for_user(user_id: UUID, db: AsyncSession) -> list:
        """Return list of app IDs assigned to the given user."""
        logger.debug("ApplicationQuery.get_app_ids_for_user called user_id=%s", user_id)
        result = await db.execute(
            select(Application.id).where(
                Application.is_deleted.is_(False),
                Application.assign_by == user_id,
            )
        )
        app_ids = result.scalars().all()
        logger.debug("ApplicationQuery.get_app_ids_for_user returned count=%s", len(app_ids))
        return app_ids


