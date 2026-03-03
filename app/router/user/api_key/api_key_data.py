"""API-key based data router: returns all assigned application data without JWT."""

from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.postgres import get_db
from app.model.ad_field import AdField
from app.model.ad_type import AdType
from app.model.application import Application
from app.services.logger.logger import get_logger
from app.utils.helper import exception_format_response, format_response, load_message_details

_BASE = Path(__file__).resolve().parents[4]
logger = get_logger(__name__)
error_details = load_message_details(str(_BASE / "app" / "data" / "error_details.json"))
success_details = load_message_details(str(_BASE / "app" / "data" / "success_details.json"))


class ApiKeyDataRouter:
    """Public GET endpoint that resolves user scope from an application API key."""

    def __init__(self):
        self.router = APIRouter(prefix="/ads/v1/api-key", tags=["API Key Data"])
        self.router.get("/applications", status_code=status.HTTP_200_OK)(self.get_user_application_data)

    async def get_user_application_data(
        self,
        api_key: str = Query(..., min_length=1),
        db: AsyncSession = Depends(get_db),
    ):
        """Return all assigned applications and their connected ad types/ad fields for the API key owner."""
        endpoint = "/ads/v1/api-key/applications"
        try:
            owner_app = await self._get_application_by_api_key(db=db, api_key=api_key)
            if not owner_app:
                self.raise_detailed_exception(endpoint, "invalid_api_key")

            user_id = owner_app.assign_by
            apps = await self._get_user_applications(db=db, user_id=user_id)

            if not apps:
                success_type = "application_retrieve_success"
                return format_response(
                    detail_type=success_details[success_type]["detail_type"],
                    data={"user_id": user_id, "items": []},
                    msg=success_details[success_type]["msg"],
                    status_code=success_details[success_type]["status_code"],
                )

            app_ids = [app.id for app in apps]
            ad_types = await self._get_ad_types_for_apps(db=db, app_ids=app_ids)
            ad_fields = await self._get_ad_fields_for_apps(db=db, app_ids=app_ids)

            ad_types_by_app: dict[UUID, list[AdType]] = defaultdict(list)
            for ad_type in ad_types:
                ad_types_by_app[ad_type.app_id].append(ad_type)

            ad_fields_by_app: dict[UUID, list[AdField]] = defaultdict(list)
            for ad_field in ad_fields:
                ad_fields_by_app[ad_field.app_id].append(ad_field)

            items = []
            for app in apps:
                items.append(
                    {
                        "application": self._serialize_application(app),
                        "ad_types": [self._serialize_ad_type(item) for item in ad_types_by_app.get(app.id, [])],
                        "ad_fields": [self._serialize_ad_field(item) for item in ad_fields_by_app.get(app.id, [])],
                    }
                )

            success_type = "application_retrieve_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data={"user_id": user_id, "items": items},
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"{endpoint}: Failed to fetch API-key scoped applications")
            self.handle_exception(endpoint, e)

    async def _get_application_by_api_key(self, db: AsyncSession, api_key: str) -> Application | None:
        result = await db.execute(
            select(Application).where(
                Application.api_key == api_key,
                Application.is_deleted.is_(False),
            )
        )
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

    async def _get_ad_types_for_apps(self, db: AsyncSession, app_ids: list[UUID]) -> list[AdType]:
        if not app_ids:
            return []

        result = await db.execute(
            select(AdType)
            .where(
                AdType.app_id.in_(app_ids),
                AdType.is_deleted.is_(False),
            )
            .order_by(AdType.created_at.desc())
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

    @staticmethod
    def _iso(value: Any):
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return value

    @classmethod
    def _serialize_application(cls, app: Application) -> dict[str, Any]:
        return {
            "id": app.id,
            "name": app.name,
            "type": app.type,
            "status": app.status,
            "api_key": app.api_key,
            "assign_by": app.assign_by,
            "launch_date": cls._iso(app.launch_date),
            "package_name": app.package_name,
            "note": app.note,
            "created_by": app.created_by,
            "updated_by": app.updated_by,
            "created_at": cls._iso(app.created_at),
            "updated_at": cls._iso(app.updated_at),
        }

    @classmethod
    def _serialize_ad_type(cls, ad_type: AdType) -> dict[str, Any]:
        ad_format = ad_type.ad_format
        ad_platform = ad_type.ad_platform

        return {
            "id": ad_type.id,
            "app_id": ad_type.app_id,
            "ad_format_id": ad_type.ad_format_id,
            "ad_platform_id": ad_type.ad_platform_id,
            "status": ad_type.status,
            "created_by": ad_type.created_by,
            "updated_by": ad_type.updated_by,
            "created_at": cls._iso(ad_type.created_at),
            "updated_at": cls._iso(ad_type.updated_at),
            "ad_format": {
                "id": ad_format.id,
                "title": ad_format.title,
                "type": ad_format.type,
            } if ad_format else None,
            "ad_platform": {
                "id": ad_platform.id,
                "title": ad_platform.title,
                "type": ad_platform.type,
            } if ad_platform else None,
        }

    @classmethod
    def _serialize_ad_field(cls, ad_field: AdField) -> dict[str, Any]:
        return {
            "id": ad_field.id,
            "app_id": ad_field.app_id,
            "ad_type_id": ad_field.ad_type_id,
            "type": ad_field.type,
            "value": ad_field.value,
            "regex": ad_field.regex,
            "created_by": ad_field.created_by,
            "updated_by": ad_field.updated_by,
            "created_at": cls._iso(ad_field.created_at),
            "updated_at": cls._iso(ad_field.updated_at),
        }

    def handle_exception(self, endpoint, e):
        error_type = "exception_error"
        response = exception_format_response(
            detail_type=error_details[error_type]["detail_type"],
            msg=error_details[error_type]["msg"],
            reason=str(e),
        )
        logger.critical(f"{endpoint}: {response}")
        raise HTTPException(status_code=error_details[error_type]["status_code"], detail=[response])

    def raise_detailed_exception(self, endpoint: str, error_type: str):
        response = exception_format_response(
            detail_type=error_details[error_type]["detail_type"],
            msg=error_details[error_type]["msg"],
            reason=error_details[error_type]["reason"],
        )
        logger.critical(f"{endpoint}: {response}")
        raise HTTPException(status_code=error_details[error_type]["status_code"], detail=[response])


api_key_data_router = ApiKeyDataRouter()
