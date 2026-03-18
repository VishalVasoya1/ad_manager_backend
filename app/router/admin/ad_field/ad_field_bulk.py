"""Ad Field Bulk Operations router — Create, Update, Delete multiple ad fields at once."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.postgres import get_db
from app.services.Jwt.bearer import jwt_bearer, require_admin
from app.services.logger.logger import get_logger
from app.utils.helper import load_message_details, format_response, exception_format_response
from app.router.admin.ad_field.ad_field_access import AdFieldQuery
from app.router.admin.ad_field.ad_field_bulk_validator import (
    AdFieldBulkCreateRequest,
    AdFieldBulkUpdateRequest,
    AdFieldBulkDeleteRequest,
    BulkOperationResult,
)
from app.router.admin.ad_field.ad_field_validator import AdFieldOut
from app.model.ad_field import AdField
from app.services.cache.api_key_cache_service import api_key_cache_service
from app.services.activity.activity_service import ActivityService


_BASE = Path(__file__).resolve().parents[4]
logger = get_logger(__name__)
error_details = load_message_details(str(_BASE / "app" / "data" / "error_details.json"))
success_details = load_message_details(str(_BASE / "app" / "data" / "success_details.json"))


class AdFieldBulkRouter:
    """Bulk CRUD endpoints for ad field management."""

    def __init__(self):
        self.router = APIRouter(prefix="/admin/ads/v1/adfield/bulk", tags=["Ad Field Bulk Operations"])
        self.router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])(self.bulk_create)
        self.router.put("", status_code=status.HTTP_200_OK, dependencies=[Depends(require_admin)])(self.bulk_update)
        self.router.delete("", status_code=status.HTTP_200_OK, dependencies=[Depends(require_admin)])(self.bulk_delete)

    async def bulk_create(
        self,
        request: Request,
        body: AdFieldBulkCreateRequest,
        db: AsyncSession = Depends(get_db),
        payload=Depends(jwt_bearer)
    ):
        """Create multiple ad fields at once."""
        endpoint = "/adfield/bulk"
        try:
            admin_id = UUID(payload["user_id"])
            ip_address = request.client.host if request.client else None

            created_fields = []
            affected_app_ids = set()
            
            # Create all fields
            for field_data in body.fields:
                field = AdField(
                    **field_data.model_dump(),
                    created_by=admin_id,
                    updated_by=admin_id
                )
                db.add(field)
                affected_app_ids.add(field.app_id)
                created_fields.append(field)

            await db.flush()
            
            # Refresh all created fields
            for field in created_fields:
                await db.refresh(field)
            
            await db.commit()
            
            # Refresh all fields again after commit
            for field in created_fields:
                await db.refresh(field)

            # Refresh cache for all affected applications
            for app_id in affected_app_ids:
                owner_user_id = await api_key_cache_service.get_user_id_for_application(
                    db=db, app_id=app_id
                )
                if owner_user_id:
                    await api_key_cache_service.refresh_user_cache(db=db, user_id=owner_user_id)

            # Log activity
            await ActivityService.log_activity(
                db=db,
                user_id=admin_id,
                module="ad_field",
                action="bulk_create",
                description=f"Bulk created {len(created_fields)} ad fields for {len(affected_app_ids)} application(s).",
                ip_address=ip_address,
            )
            await db.commit()

            success_type = "ad_field_create_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data={
                    "created_count": len(created_fields),
                    "fields": [AdFieldOut.model_validate(f).model_dump() for f in created_fields]
                },
                msg=f"Successfully created {len(created_fields)} ad fields.",
                status_code=success_details[success_type]["status_code"],
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            return self.handle_exception(endpoint, e)

    async def bulk_update(
        self,
        request: Request,
        body: AdFieldBulkUpdateRequest,
        db: AsyncSession = Depends(get_db),
        payload=Depends(jwt_bearer)
    ):
        """Update multiple ad fields at once."""
        endpoint = "/adfield/bulk"
        try:
            admin_id = UUID(payload["user_id"])
            ip_address = request.client.host if request.client else None

            updated_fields = []
            failed_ids = []
            errors = []
            affected_app_ids = set()
            old_app_ids = set()

            for field_update in body.fields:
                try:
                    # Get the field
                    field = await AdFieldQuery.get_by_id(field_update.id, db)
                    if not field:
                        failed_ids.append(field_update.id)
                        errors.append(f"Field {field_update.id} not found")
                        continue

                    old_app_ids.add(field.app_id)

                    # Update fields
                    update_data = field_update.model_dump(exclude={'id'}, exclude_none=True)
                    for key, value in update_data.items():
                        setattr(field, key, value)
                    
                    field.updated_by = admin_id
                    affected_app_ids.add(field.app_id)
                    updated_fields.append(field)

                except Exception as e:
                    failed_ids.append(field_update.id)
                    errors.append(f"Error updating {field_update.id}: {str(e)}")

            await db.flush()
            await db.commit()
            
            # Refresh all updated fields
            for field in updated_fields:
                await db.refresh(field)

            # Refresh cache for all affected applications
            all_affected_apps = old_app_ids | affected_app_ids
            for app_id in all_affected_apps:
                owner_user_id = await api_key_cache_service.get_user_id_for_application(
                    db=db, app_id=app_id, include_deleted=True
                )
                if owner_user_id:
                    await api_key_cache_service.refresh_user_cache(db=db, user_id=owner_user_id)

            # Log activity
            await ActivityService.log_activity(
                db=db,
                user_id=admin_id,
                module="ad_field",
                action="bulk_update",
                description=f"Bulk updated {len(updated_fields)} ad fields, {len(failed_ids)} failed.",
                ip_address=ip_address,
            )
            await db.commit()

            success_type = "ad_field_update_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data={
                    "updated_count": len(updated_fields),
                    "failed_count": len(failed_ids),
                    "failed_ids": failed_ids,
                    "errors": errors,
                    "fields": [AdFieldOut.model_validate(f).model_dump() for f in updated_fields]
                },
                msg=f"Successfully updated {len(updated_fields)} ad fields.",
                status_code=success_details[success_type]["status_code"],
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            return self.handle_exception(endpoint, e)

    async def bulk_delete(
        self,
        request: Request,
        body: AdFieldBulkDeleteRequest,
        db: AsyncSession = Depends(get_db),
        payload=Depends(jwt_bearer)
    ):
        """Soft-delete multiple ad fields at once."""
        endpoint = "/adfield/bulk"
        try:
            admin_id = UUID(payload["user_id"])
            ip_address = request.client.host if request.client else None

            deleted_count = 0
            failed_ids = []
            errors = []
            affected_app_ids = set()

            for field_id in body.field_ids:
                try:
                    # Get the field
                    field = await AdFieldQuery.get_by_id(field_id, db)
                    if not field:
                        failed_ids.append(field_id)
                        errors.append(f"Field {field_id} not found")
                        continue

                    # Soft delete
                    field.is_deleted = True
                    affected_app_ids.add(field.app_id)
                    deleted_count += 1

                except Exception as e:
                    failed_ids.append(field_id)
                    errors.append(f"Error deleting {field_id}: {str(e)}")

            await db.flush()
            await db.commit()

            # Refresh cache for all affected applications
            for app_id in affected_app_ids:
                owner_user_id = await api_key_cache_service.get_user_id_for_application(
                    db=db, app_id=app_id, include_deleted=True
                )
                if owner_user_id:
                    await api_key_cache_service.refresh_user_cache(db=db, user_id=owner_user_id)

            # Log activity
            await ActivityService.log_activity(
                db=db,
                user_id=admin_id,
                module="ad_field",
                action="bulk_delete",
                description=f"Bulk deleted {deleted_count} ad fields, {len(failed_ids)} failed.",
                ip_address=ip_address,
            )
            await db.commit()

            success_type = "ad_field_delete_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data={
                    "deleted_count": deleted_count,
                    "failed_count": len(failed_ids),
                    "failed_ids": failed_ids,
                    "errors": errors
                },
                msg=f"Successfully deleted {deleted_count} ad fields.",
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


ad_field_bulk_router = AdFieldBulkRouter()
