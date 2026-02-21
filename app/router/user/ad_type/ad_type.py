"""User-side Ad Type router Ã¢â‚¬â€ GET only, restricted to user's assigned applications."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.postgres import get_db
from app.services.Jwt.bearer import require_user
from app.services.logger.logger import get_logger
from app.utils.helper import load_message_details, format_response, exception_format_response
from app.router.user.ad_type.ad_type_access import AdTypeQuery
from app.router.user.ad_type.ad_type_validator import AdTypeOut
from app.router.user.application.application_access import ApplicationQuery
from app.services.activity.activity_service import ActivityService

_BASE = Path(__file__).resolve().parents[4]
logger = get_logger(__name__)
error_details = load_message_details(str(_BASE / "app" / "data" / "error_details.json"))
success_details = load_message_details(str(_BASE / "app" / "data" / "success_details.json"))


class UserAdTypeRouter:
    """Read-only ad type endpoints for regular users.
    A user can only see ad types that belong to their assigned applications.
    """

    def __init__(self):
        self.router = APIRouter(prefix="/ads/v1/adtype", tags=["User - Ad Type"])
        self.router.get("", status_code=status.HTTP_200_OK, dependencies=[Depends(require_user)])(self.get_all)
        self.router.get("/{ad_type_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(require_user)])(self.get)

    async def get_all(
        self,
        request: Request,
        app_id: Optional[UUID] = Query(None),
        status_filter: Optional[str] = Query(None, alias="status"),
        db: AsyncSession = Depends(get_db),
        payload=Depends(require_user),
    ):
        """Return all ad types belonging to the logged-in user's assigned applications."""
        endpoint = "/ads/v1/adtype"
        try:
            user_id = UUID(payload["user_id"])
            ip_address = request.client.host if request.client else None

            user_app_ids = await ApplicationQuery.get_app_ids_for_user(user_id, db)
            items = await AdTypeQuery.get_all_for_user(db, user_app_ids, app_id, status_filter)

            await ActivityService.log_activity(
                db=db,
                user_id=user_id,
                module="ad_type",
                action="view",
                description="User listed ad types for their assigned applications.",
                ip_address=ip_address,
            )
            await db.commit()

            success_type = "ad_type_retrieve_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data=[AdTypeOut.model_validate(i).model_dump() for i in items],
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            return self.handle_exception(endpoint, e)

    async def get(
        self,
        request: Request,
        ad_type_id: UUID,
        db: AsyncSession = Depends(get_db),
        payload=Depends(require_user),
    ):
        """Return a single ad type by ID Ã¢â‚¬â€ only if it belongs to one of the user's assigned applications."""
        endpoint = f"/ads/v1/adtype/{ad_type_id}"
        try:
            user_id = UUID(payload["user_id"])
            ip_address = request.client.host if request.client else None

            user_app_ids = await ApplicationQuery.get_app_ids_for_user(user_id, db)
            item = await AdTypeQuery.get_by_id_for_user(ad_type_id, user_app_ids, db)
            if not item:
                self.raise_detailed_exception(endpoint, "ad_type_not_found")

            await ActivityService.log_activity(
                db=db,
                user_id=user_id,
                module="ad_type",
                action="view",
                reference_id=ad_type_id,
                description=f"User viewed ad type {ad_type_id}.",
                ip_address=ip_address,
            )
            await db.commit()

            success_type = "ad_type_retrieve_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data=AdTypeOut.model_validate(item).model_dump(),
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            return self.handle_exception(endpoint, e)

    def handle_exception(self, endpoint, e):
        error_type = "exception_error"
        response = exception_format_response(
            detail_type=error_details[error_type]["detail_type"],
            msg=error_details[error_type]["msg"],
            reason=str(e),
        )
        logger.critical(f"{endpoint}: {error_type} - {response}")
        raise HTTPException(status_code=error_details[error_type]["status_code"], detail=[response])

    def raise_detailed_exception(self, endpoint: str, error_type: str):
        response = exception_format_response(
            detail_type=error_details[error_type]["detail_type"],
            msg=error_details[error_type]["msg"],
            reason=error_details[error_type]["reason"],
        )
        logger.critical(f"{endpoint}: {error_type} - {response}")
        raise HTTPException(status_code=error_details[error_type]["status_code"], detail=[response])


