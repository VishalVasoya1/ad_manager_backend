"""Centralized activity and login log service."""

import json
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.model.user_activity import UserActivity
from app.model.user_login_log import UserLoginLog
from app.services.logger.logger import get_logger

logger = get_logger(__name__)


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
    ) -> Optional[UserActivity]:
        """Insert a user activity record into the session (no commit)."""
        if action.lower() == "view":
            logger.debug("Activity log skipped for action=view user_id=%s module=%s", user_id, module)
            return None

        logger.debug("Creating activity log user_id=%s module=%s action=%s reference_id=%s", user_id, module, action, reference_id)
        activity = UserActivity(
            user_id=user_id,
            module=module,
            action=action,
            reference_id=reference_id,
            description=description,
            ip_address=ip_address,
        )
        db.add(activity)
        logger.debug("Activity log added to session")
        return activity

    @staticmethod
    def build_update_description(
        old_data: dict[str, Any],
        updated_data: dict[str, Any],
        force_updated_fields: Optional[list[str]] = None,
    ) -> str:
        """Return a JSON string containing old data, new data, and changed fields."""
        changes: dict[str, dict[str, Any]] = {}
        all_keys = set(old_data) | set(updated_data)
        for key in all_keys:
            old_value = old_data.get(key)
            new_value = updated_data.get(key)
            if old_value != new_value:
                changes[key] = {"old": old_value, "new": new_value}

        for key in force_updated_fields or []:
            if key not in changes:
                changes[key] = {"old": old_data.get(key), "new": updated_data.get(key)}

        payload = {
            "old_data": old_data,
            "updated_data": updated_data,
            "updated_fields": list(changes.keys()),
            "changes": changes,
        }
        logger.debug("Update description built updated_fields=%s", payload["updated_fields"])
        return json.dumps(payload, default=str)

    @staticmethod
    async def log_login(
        db: AsyncSession,
        user_id: UUID,
        login_status: str,
        ip_address: Optional[str] = None,
        device_info: Optional[str] = None,
    ) -> UserLoginLog:
        """Insert a login log record into the session (no commit)."""
        logger.debug("Creating login log user_id=%s login_status=%s", user_id, login_status)
        login_log = UserLoginLog(
            user_id=user_id,
            login_status=login_status,
            ip_address=ip_address,
            device_info=device_info,
        )
        db.add(login_log)
        logger.debug("Login log added to session")
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
            logger.debug("Logout stamped for user_id=%s login_log_id=%s", user_id, login_log.id)
        else:
            logger.debug("No open successful login found to stamp logout for user_id=%s", user_id)
        return login_log
