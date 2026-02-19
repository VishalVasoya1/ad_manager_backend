"""Centralized activity and login log service."""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.model.user_activity import UserActivity
from app.model.user_login_log import UserLoginLog


class ActivityService:
    """
    Provides static helpers to log user activity and login events.

    IMPORTANT: These methods only ADD objects to the session.
    The calling router is responsible for committing the transaction.
    """

    @staticmethod
    async def log_activity(
        db: AsyncSession,
        user_id: UUID,
        module: str,
        action: str,
        reference_id: Optional[UUID] = None,
        description: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> UserActivity:
        """Insert a user activity record into the session (no commit)."""
        activity = UserActivity(
            user_id=user_id,
            module=module,
            action=action,
            reference_id=reference_id,
            description=description,
            ip_address=ip_address,
        )
        db.add(activity)
        return activity

    @staticmethod
    async def log_login(
        db: AsyncSession,
        user_id: UUID,
        login_status: str,
        ip_address: Optional[str] = None,
        device_info: Optional[str] = None,
    ) -> UserLoginLog:
        """Insert a login log record into the session (no commit)."""
        login_log = UserLoginLog(
            user_id=user_id,
            login_status=login_status,
            ip_address=ip_address,
            device_info=device_info,
        )
        db.add(login_log)
        return login_log

    @staticmethod
    async def stamp_logout(
        db: AsyncSession,
        user_id: UUID,
    ) -> Optional[UserLoginLog]:
        """
        Update the logout_time of the most recent successful login log
        for the given user. Caller must commit after calling this.
        """
        from datetime import datetime, timezone

        result = await db.execute(
            select(UserLoginLog)
            .where(
                UserLoginLog.user_id == user_id,
                UserLoginLog.login_status == "success",
                UserLoginLog.logout_time.is_(None),
            )
            .order_by(UserLoginLog.login_time.desc())
            .limit(1)
        )
        login_log = result.scalar_one_or_none()
        if login_log:
            login_log.logout_time = datetime.now(timezone.utc)
        return login_log
