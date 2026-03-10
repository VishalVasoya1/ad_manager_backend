"""Redis cache service for API-key scoped application data."""

import json
from collections import defaultdict
from datetime import date, datetime
from time import perf_counter
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.redis import RedisManager
from app.config.setting import settings
from app.model.ad_field import AdField
from app.model.application import Application
from app.services.logger.logger import get_logger

logger = get_logger(__name__)


class ApiKeyCacheService:
    """Read-through and write-through cache operations for API-key data."""

    def __init__(self, key_prefix: str = "ad_manager:api_key_data"):
        self.key_prefix = key_prefix

    def _redis_key(self, api_key: str) -> str:
        return f"{self.key_prefix}:{api_key}"

    @staticmethod
    def _json_default(value: Any):
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, UUID):
            return str(value)
        return value

    async def get_api_key_data(self, api_key: str) -> dict[str, Any] | None:
        """Return cached payload by API key if available."""
        redis = RedisManager.get_client()
        if not redis:
            return None
        start = perf_counter()
        try:
            raw = await redis.get(self._redis_key(api_key))
            took_ms = (perf_counter() - start) * 1000
            logger.info(
                "Redis GET key=%s cache_hit=%s took_ms=%.2f",
                self._redis_key(api_key),
                bool(raw),
                took_ms,
            )
            return json.loads(raw) if raw else None
        except Exception as e:
            logger.warning("Redis get failed for api_key cache: %s", str(e))
            return None

    async def set_api_key_data(self, api_key: str, payload: dict[str, Any]) -> None:
        """Set cached payload by API key."""
        redis = RedisManager.get_client()
        if not redis:
            return
        start = perf_counter()
        try:
            await redis.set(
                self._redis_key(api_key),
                json.dumps(payload, default=self._json_default),
                ex=settings.REDIS_CACHE_TTL_SECONDS,
            )
            took_ms = (perf_counter() - start) * 1000
            logger.info(
                "Redis SET key=%s ttl_seconds=%s took_ms=%.2f",
                self._redis_key(api_key),
                settings.REDIS_CACHE_TTL_SECONDS,
                took_ms,
            )
        except Exception as e:
            logger.warning("Redis set failed for api_key cache: %s", str(e))

    async def delete_api_key(self, api_key: str) -> None:
        """Delete cached payload for an API key."""
        redis = RedisManager.get_client()
        if not redis:
            return
        start = perf_counter()
        try:
            deleted = await redis.delete(self._redis_key(api_key))
            took_ms = (perf_counter() - start) * 1000
            logger.info(
                "Redis DEL key=%s deleted_count=%s took_ms=%.2f",
                self._redis_key(api_key),
                deleted,
                took_ms,
            )
        except Exception as e:
            logger.warning("Redis delete failed for api_key cache: %s", str(e))

    async def refresh_user_cache(self, db: AsyncSession, user_id: UUID) -> None:
        """Refresh cache entries for all active applications assigned to a user."""
        start = perf_counter()
        try:
            apps = await self._get_user_applications(db=db, user_id=user_id)
            if not apps:
                took_ms = (perf_counter() - start) * 1000
                logger.info("Redis refresh skipped user_id=%s apps=0 took_ms=%.2f", str(user_id), took_ms)
                return
            app_ids = [app.id for app in apps]
            ad_fields = await self._get_ad_fields_for_apps(db=db, app_ids=app_ids)
            payload = self._build_payload(user_id=user_id, apps=apps, ad_fields=ad_fields)
            for app in apps:
                await self.set_api_key_data(app.api_key, payload)
            took_ms = (perf_counter() - start) * 1000
            logger.info(
                "Redis refresh user_id=%s apps=%s ad_fields=%s took_ms=%.2f",
                str(user_id),
                len(apps),
                len(ad_fields),
                took_ms,
            )
        except Exception as e:
            logger.warning("Failed to refresh user cache user_id=%s: %s", str(user_id), str(e))

    async def get_user_id_for_application(
        self, db: AsyncSession, app_id: UUID, include_deleted: bool = False
    ) -> UUID | None:
        """Get application owner user_id by app_id."""
        stmt = select(Application.assign_by).where(Application.id == app_id)
        if not include_deleted:
            stmt = stmt.where(Application.is_deleted.is_(False))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_user_applications(self, db: AsyncSession, user_id: UUID) -> list[Application]:
        result = await db.execute(
            select(Application)
            .where(
                Application.assign_by == user_id,
                Application.is_deleted.is_(False),
            )
            .order_by(Application.created_at.desc())
        )
        return list(result.scalars().all())

    async def _get_ad_fields_for_apps(self, db: AsyncSession, app_ids: list[UUID]) -> list[AdField]:
        if not app_ids:
            return []
        result = await db.execute(
            select(AdField)
            .where(
                AdField.app_id.in_(app_ids),
                AdField.is_deleted.is_(False),
            )
            .order_by(AdField.created_at.desc())
        )
        return list(result.scalars().all())

    def _build_payload(self, user_id: UUID, apps: list[Application], ad_fields: list[AdField]) -> dict[str, Any]:
        ad_fields_by_app: dict[UUID, list[AdField]] = defaultdict(list)
        for ad_field in ad_fields:
            ad_fields_by_app[ad_field.app_id].append(ad_field)

        items = []
        for app in apps:
            items.append(
                {
                    "application": self._serialize_application(app),
                    "ad_fields": [self._serialize_ad_field(item) for item in ad_fields_by_app.get(app.id, [])],
                }
            )

        return {
            "user_id": str(user_id),
            "items": items,
        }

    @staticmethod
    def _iso(value: Any):
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, UUID):
            return str(value)
        return value

    @classmethod
    def _serialize_application(cls, app: Application) -> dict[str, Any]:
        return {
            "id": cls._iso(app.id),
            "name": app.name,
            "type": app.type,
            "status": app.status,
            "api_key": app.api_key,
            "assign_by": cls._iso(app.assign_by),
            "launch_date": cls._iso(app.launch_date),
            "package_name": app.package_name,
            "note": app.note,
            "created_by": cls._iso(app.created_by),
            "updated_by": cls._iso(app.updated_by),
            "created_at": cls._iso(app.created_at),
            "updated_at": cls._iso(app.updated_at),
        }

    @classmethod
    def _serialize_ad_field(cls, ad_field: AdField) -> dict[str, Any]:
        return {
            "id": cls._iso(ad_field.id),
            "app_id": cls._iso(ad_field.app_id),
            "type": ad_field.type,
            "value": ad_field.value,
            "regex": ad_field.regex,
            "created_by": cls._iso(ad_field.created_by),
            "updated_by": cls._iso(ad_field.updated_by),
            "created_at": cls._iso(ad_field.created_at),
            "updated_at": cls._iso(ad_field.updated_at),
        }


api_key_cache_service = ApiKeyCacheService()
