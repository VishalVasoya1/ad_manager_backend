"""Application access layer — DB queries."""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.model.application import Application


class ApplicationQuery:
    """Database queries used by the application router."""

    @staticmethod
    async def get_all(db: AsyncSession, page: int, size: int, search: Optional[str], app_type: Optional[str], status: Optional[str]):
        """Return paginated applications with optional name, type, and status filters."""
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
        return total, result.scalars().all()

    @staticmethod
    async def get_by_id(app_id: UUID, db: AsyncSession) -> Optional[Application]:
        """Return an active application by ID."""
        result = await db.execute(
            select(Application).where(Application.id == app_id, Application.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_package_name(package_name: str, db: AsyncSession) -> Optional[Application]:
        """Return an active application by package name."""
        result = await db.execute(
            select(Application).where(
                Application.package_name == package_name,
                Application.is_deleted.is_(False)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_package_name_any(package_name: str, db: AsyncSession) -> Optional[Application]:
        """Return an application by package name regardless of soft-delete status."""
        result = await db.execute(
            select(Application).where(Application.package_name == package_name)
        )
        return result.scalar_one_or_none()
