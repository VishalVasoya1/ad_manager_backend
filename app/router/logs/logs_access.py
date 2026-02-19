"""DB queries for user login logs."""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.model.user_login_log import UserLoginLog


class LoginLogQuery:
    """Database queries used by the login logs router."""

    @staticmethod
    async def get_all(
        db: AsyncSession,
        page: int,
        size: int,
        user_id: Optional[UUID] = None,
        login_status: Optional[str] = None,
    ):
        """Return paginated login logs with optional filters."""
        stmt = select(UserLoginLog)

        if user_id:
            stmt = stmt.where(UserLoginLog.user_id == user_id)
        if login_status:
            stmt = stmt.where(UserLoginLog.login_status == login_status)

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(total_stmt)).scalar_one()

        stmt = stmt.order_by(UserLoginLog.login_time.desc()).offset((page - 1) * size).limit(size)
        result = await db.execute(stmt)
        return total, result.scalars().all()

    @staticmethod
    async def get_by_id(db: AsyncSession, log_id: UUID) -> Optional[UserLoginLog]:
        """Return a single login log by ID."""
        result = await db.execute(
            select(UserLoginLog).where(UserLoginLog.id == log_id)
        )
        return result.scalar_one_or_none()
