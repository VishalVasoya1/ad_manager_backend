"""Ad Field router — CRUD. Write operations are admin-only."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.postgres import get_db
from app.services.Jwt.bearer import jwt_bearer, require_admin
from app.services.logger.logger import get_logger
from app.utils.helper import load_message_details, format_response, exception_format_response
from app.router.admin.ad_field.ad_field_access import AdFieldQuery
from app.router.admin.ad_field.ad_field_validator import AdFieldCreateRequest, AdFieldUpdateRequest, AdFieldOut
from app.model.ad_field import AdField
from app.services.cache.api_key_cache_service import api_key_cache_service
from app.services.activity.activity_service import ActivityService


_BASE = Path(__file__).resolve().parents[4]
logger = get_logger(__name__)
error_details = load_message_details(str(_BASE / "app" / "data" / "error_details.json"))
success_details = load_message_details(str(_BASE / "app" / "data" / "success_details.json"))


class AdFieldRouter:
    """CRUD endpoints for ad field management."""

    def __init__(self):
        self.router = APIRouter(prefix="/admin/ads/v1/adfield", tags=["Ad Field"])
        self.router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])(self.create)
        self.router.get("", status_code=status.HTTP_200_OK, dependencies=[Depends(jwt_bearer)])(self.get_all)
        self.router.get("/{field_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(jwt_bearer)])(self.get)
        self.router.put("/{field_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(require_admin)])(self.update)
        self.router.delete("/{field_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(require_admin)])(self.delete)

    async def create(self, request: Request, body: AdFieldCreateRequest, db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Create a new ad field."""
        endpoint = "/adfield"
        try:
            admin_id = UUID(payload["user_id"])
            ip_address = request.client.host if request.client else None

            field = AdField(**body.model_dump(), created_by=admin_id, updated_by=admin_id)
            db.add(field)
            await db.flush()
            await db.refresh(field)
            await db.commit()
            await db.refresh(field)
            owner_user_id = await api_key_cache_service.get_user_id_for_application(db=db, app_id=field.app_id)
            if owner_user_id:
                await api_key_cache_service.refresh_user_cache(db=db, user_id=owner_user_id)

            await ActivityService.log_activity(
                db=db,
                user_id=admin_id,
                module="ad_field",
                action="create",
                reference_id=field.id,
                description=f"Created '{body.type}' ad field for app '{body.app_id}', value='{body.value or 'N/A'}'.",
                ip_address=ip_address,
            )
            await db.commit()

            success_type = "ad_field_create_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data=AdFieldOut.model_validate(field).model_dump(),
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            return self.handle_exception(endpoint, e)

    async def get_all(self, request: Request, app_id: Optional[UUID] = Query(None), type: Optional[str] = Query(None), user_id: Optional[UUID] = Query(None), db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Return all active ad fields with optional filters for app_id, type, and user_id."""
        endpoint = "/adfield"
        try:
            admin_id = UUID(payload["user_id"])
            ip_address = request.client.host if request.client else None
            items = await AdFieldQuery.get_all(db, app_id, type, user_id)

            filters = []
            if app_id: filters.append(f"app_id='{app_id}'")
            if type: filters.append(f"type='{type}'")
            if user_id: filters.append(f"user_id='{user_id}'")
            filter_str = ", ".join(filters) if filters else "no filters"
            await ActivityService.log_activity(
                db=db,
                user_id=admin_id,
                module="ad_field",
                action="view",
                description=f"Listed {len(items)} ad fields with {filter_str}.",
                ip_address=ip_address,
            )
            await db.commit()

            success_type = "ad_field_retrieve_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data=[AdFieldOut.model_validate(i).model_dump() for i in items],
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            return self.handle_exception(endpoint, e)

    async def get(self, request: Request, field_id: UUID, db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Return a single ad field by ID."""
        endpoint = f"/adfield/{field_id}"
        try:
            admin_id = UUID(payload["user_id"])
            ip_address = request.client.host if request.client else None
            item = await AdFieldQuery.get_by_id(field_id, db)
            if not item:
                self.raise_detailed_exception(endpoint, "ad_field_not_found")

            await ActivityService.log_activity(
                db=db,
                user_id=admin_id,
                module="ad_field",
                action="view",
                reference_id=field_id,
                description=f"Viewed '{item.type}' ad field (app: '{item.app_id}', value: '{item.value or 'N/A'}').",
                ip_address=ip_address,
            )
            await db.commit()

            success_type = "ad_field_retrieve_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data=AdFieldOut.model_validate(item).model_dump(),
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            return self.handle_exception(endpoint, e)

    async def update(self, request: Request, field_id: UUID, body: AdFieldUpdateRequest, db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Update ad field fields. Only provided fields are changed."""
        endpoint = f"/adfield/{field_id}"
        try:
            admin_id = UUID(payload["user_id"])
            ip_address = request.client.host if request.client else None
            item = await AdFieldQuery.get_by_id(field_id, db)
            if not item:
                self.raise_detailed_exception(endpoint, "ad_field_not_found")

            old_app_id = item.app_id

            old_data = {
                "type": item.type,
                "value": item.value,
                "regex": item.regex,
                "app_id": str(item.app_id),
            }
            for field, value in body.model_dump(exclude_none=True).items():
                setattr(item, field, value)
            item.updated_by = admin_id

            await db.flush()
            await db.commit()
            await db.refresh(item)
            old_owner_user_id = await api_key_cache_service.get_user_id_for_application(
                db=db, app_id=old_app_id, include_deleted=True
            )
            new_owner_user_id = await api_key_cache_service.get_user_id_for_application(db=db, app_id=item.app_id)
            if old_owner_user_id:
                await api_key_cache_service.refresh_user_cache(db=db, user_id=old_owner_user_id)
            if new_owner_user_id and new_owner_user_id != old_owner_user_id:
                await api_key_cache_service.refresh_user_cache(db=db, user_id=new_owner_user_id)

            updated_data = {
                "type": item.type,
                "value": item.value,
                "regex": item.regex,
                "app_id": str(item.app_id),
            }
            description_json = ActivityService.build_update_description(
                old_data=old_data,
                updated_data=updated_data,
            )
            await ActivityService.log_activity(
                db=db,
                user_id=admin_id,
                module="ad_field",
                action="update",
                reference_id=field_id,
                description=description_json,
                ip_address=ip_address,
            )
            await db.commit()

            success_type = "ad_field_update_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data=AdFieldOut.model_validate(item).model_dump(),
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            return self.handle_exception(endpoint, e)

    async def delete(self, request: Request, field_id: UUID, db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Soft-delete an ad field."""
        endpoint = f"/adfield/{field_id}"
        try:
            admin_id = UUID(payload["user_id"])
            ip_address = request.client.host if request.client else None
            item = await AdFieldQuery.get_by_id(field_id, db)
            if not item:
                self.raise_detailed_exception(endpoint, "ad_field_not_found")
            old_app_id = item.app_id
            app_id = item.app_id

            item.is_deleted = True
            await db.flush()
            await db.commit()
            owner_user_id = await api_key_cache_service.get_user_id_for_application(
                db=db, app_id=app_id, include_deleted=True
            )
            if owner_user_id:
                await api_key_cache_service.refresh_user_cache(db=db, user_id=owner_user_id)

            await ActivityService.log_activity(
                db=db,
                user_id=admin_id,
                module="ad_field",
                action="delete",
                reference_id=field_id,
                description=f"Deleted '{item.type}' ad field (app: '{item.app_id}', value: '{item.value or 'N/A'}').",
                ip_address=ip_address,
            )
            await db.commit()

            success_type = "ad_field_delete_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data=None,
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            return self.handle_exception(endpoint, e)

    def handle_exception(self, endpoint, e):
        """Raise a generic 500 HTTP exception."""
        error_type = "exception_error"
        response = exception_format_response(
            detail_type=error_details[error_type]["detail_type"],
            msg=error_details[error_type]["msg"],
            reason=str(e),
        )
        logger.critical(f"{endpoint}: {error_type} - {response}")
        raise HTTPException(status_code=error_details[error_type]["status_code"], detail=[response])

    def raise_detailed_exception(self, endpoint: str, error_type: str):
        """Raise a typed HTTP exception using the error details registry."""
        response = exception_format_response(
            detail_type=error_details[error_type]["detail_type"],
            msg=error_details[error_type]["msg"],
            reason=error_details[error_type]["reason"],
        )
        logger.critical(f"{endpoint}: {error_type} - {response}")
        raise HTTPException(status_code=error_details[error_type]["status_code"], detail=[response])


ad_field_router = AdFieldRouter()
