"""Ad Type router — CRUD. Write operations are admin-only."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.postgres import get_db
from app.services.Jwt.bearer import jwt_bearer, require_admin
from app.services.logger.logger import get_logger
from app.utils.helper import load_message_details, format_response, exception_format_response
from app.router.ad_type.ad_type_access import AdTypeQuery
from app.router.ad_type.ad_type_validator import AdTypeCreateRequest, AdTypeUpdateRequest, AdTypeOut
from app.router.ad_master.ad_master_access import AdMasterQuery
from app.model.ad_type import AdType


_BASE = Path(__file__).resolve().parents[3]
logger = get_logger(__name__)
error_details = load_message_details(str(_BASE / "app" / "data" / "error_details.json"))
success_details = load_message_details(str(_BASE / "app" / "data" / "success_details.json"))


class AdTypeRouter:
    """CRUD endpoints for ad type management."""

    def __init__(self):
        self.router = APIRouter(prefix="/admin/ads/v1/ad-type", tags=["Ad Type"])
        self.router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])(self.create)
        self.router.get("", status_code=status.HTTP_200_OK, dependencies=[Depends(jwt_bearer)])(self.get_all)
        self.router.get("/{ad_type_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(jwt_bearer)])(self.get)
        self.router.put("/{ad_type_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(require_admin)])(self.update)
        self.router.delete("/{ad_type_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(require_admin)])(self.delete)

    async def create(self, request: Request, body: AdTypeCreateRequest, db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Create a new ad type, validating that the ad_format_id and ad_platform_id exist."""
        endpoint = "/ad-type"
        try:
            admin_id = UUID(payload["user_id"])

            if not await AdMasterQuery.get_by_id_and_type(body.ad_format_id, "ad_format", db):
                self.raise_detailed_exception(endpoint, "invalid_ad_format_id")

            if not await AdMasterQuery.get_by_id_and_type(body.ad_platform_id, "ad_platform", db):
                self.raise_detailed_exception(endpoint, "invalid_ad_platform_id")

            ad_type = AdType(**body.model_dump(), created_by=admin_id, updated_by=admin_id)
            db.add(ad_type)
            await db.flush()
            await db.refresh(ad_type)
            await db.commit()
            await db.refresh(ad_type)

            success_type = "ad_type_create_success"
            return format_response(detail_type=success_details[success_type]["detail_type"], data=AdTypeOut.model_validate(ad_type).model_dump(), msg=success_details[success_type]["msg"], status_code=success_details[success_type]["status_code"])
        except HTTPException as e:
            raise e
        except Exception as e:
            return self.handle_exception(endpoint, e)

    async def get_all(self, request: Request, app_id: Optional[UUID] = Query(None), status: Optional[str] = Query(None), user_id: Optional[UUID] = Query(None), db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Return all active ad types with optional filters for app_id, status, and user_id."""
        endpoint = "/ad-type"
        try:
            admin_id = UUID(payload["user_id"])
            items = await AdTypeQuery.get_all(db, app_id, status, user_id)

            await db.commit()

            success_type = "ad_type_retrieve_success"
            return format_response(detail_type=success_details[success_type]["detail_type"], data=[AdTypeOut.model_validate(i).model_dump() for i in items], msg=success_details[success_type]["msg"], status_code=success_details[success_type]["status_code"])
        except HTTPException as e:
            raise e
        except Exception as e:
            return self.handle_exception(endpoint, e)

    async def get(self, request: Request, ad_type_id: UUID, db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Return a single ad type by ID."""
        endpoint = f"/ad-type/{ad_type_id}"
        
        try:
            admin_id = UUID(payload["user_id"])
            item = await AdTypeQuery.get_by_id(ad_type_id, db)
            if not item:
                self.raise_detailed_exception(endpoint, "ad_type_not_found")

            await db.commit()

            success_type = "ad_type_retrieve_success"
            return format_response(detail_type=success_details[success_type]["detail_type"], data=AdTypeOut.model_validate(item).model_dump(), msg=success_details[success_type]["msg"], status_code=success_details[success_type]["status_code"])
        except HTTPException as e:
            raise e
        except Exception as e:
            return self.handle_exception(endpoint, e)

    async def update(self, request: Request, ad_type_id: UUID, body: AdTypeUpdateRequest, db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Update the status of an ad type."""
        endpoint = f"/ad-type/{ad_type_id}"
       
        try:
            admin_id = UUID(payload["user_id"])
            item = await AdTypeQuery.get_by_id(ad_type_id, db)
            if not item:
                self.raise_detailed_exception(endpoint, "ad_type_not_found")

            if body.status:
                item.status = body.status
            item.updated_by = admin_id

            await db.flush()
            
            await db.commit()
            await db.refresh(item)

            success_type = "ad_type_update_success"
            return format_response(detail_type=success_details[success_type]["detail_type"], data=AdTypeOut.model_validate(item).model_dump(), msg=success_details[success_type]["msg"], status_code=success_details[success_type]["status_code"])
        except HTTPException as e:
            raise e
        except Exception as e:
            return self.handle_exception(endpoint, e)

    async def delete(self, request: Request, ad_type_id: UUID, db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Soft-delete an ad type."""
        endpoint = f"/ad-type/{ad_type_id}"
        try:
            admin_id = UUID(payload["user_id"])
            item = await AdTypeQuery.get_by_id(ad_type_id, db)
            if not item:
                self.raise_detailed_exception(endpoint, "ad_type_not_found")

            item.is_deleted = True
            await db.flush()
            await db.commit()

            success_type = "ad_type_delete_success"
            return format_response(detail_type=success_details[success_type]["detail_type"], data=None, msg=success_details[success_type]["msg"], status_code=success_details[success_type]["status_code"])
        except HTTPException as e:
            raise e
        except Exception as e:
            return self.handle_exception(endpoint, e)

    def handle_exception(self, endpoint, e):
        """Raise a generic 500 HTTP exception."""
        error_type = "exception_error"
        response = exception_format_response(detail_type=error_details[error_type]["detail_type"], msg=error_details[error_type]["msg"], reason=str(e))
        logger.critical(f"{endpoint}: {error_type} - {response}")
        raise HTTPException(status_code=error_details[error_type]["status_code"], detail=[response])

    def raise_detailed_exception(self, endpoint: str, error_type: str):
        """Raise a typed HTTP exception using the error details registry."""
        response = exception_format_response(detail_type=error_details[error_type]["detail_type"], msg=error_details[error_type]["msg"], reason=error_details[error_type]["reason"])
        logger.critical(f"{endpoint}: {error_type} - {response}")
        raise HTTPException(status_code=error_details[error_type]["status_code"], detail=[response])


ad_type_router = AdTypeRouter()
