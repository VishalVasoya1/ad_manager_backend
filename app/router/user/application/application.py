"""User-side Application router Ã¢â‚¬â€ GET only, restricted to assigned applications."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.postgres import get_db
from app.services.Jwt.bearer import require_user
from app.services.logger.logger import get_logger
from app.utils.helper import load_message_details, format_response, exception_format_response
from app.router.user.application.application_access import ApplicationQuery
from app.router.user.application.application_validator import ApplicationOut
from app.services.activity.activity_service import ActivityService

_BASE = Path(__file__).resolve().parents[4]
logger = get_logger(__name__)
error_details = load_message_details(str(_BASE / "app" / "data" / "error_details.json"))
success_details = load_message_details(str(_BASE / "app" / "data" / "success_details.json"))


class UserApplicationRouter:
    """Read-only application endpoints for regular users.
    A user can only see applications that are assigned to them (assign_by == user_id).
    """

    def __init__(self):
        self.router = APIRouter(prefix="/ads/v1/application", tags=["User - Application"])
        self.router.get("", status_code=status.HTTP_200_OK, dependencies=[Depends(require_user)])(self.get_all)
        self.router.get("/{app_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(require_user)])(self.get)

    async def get_all(
        self,
        request: Request,
        page: int = Query(1, ge=1),
        size: int = Query(10, ge=1, le=100),
        search: Optional[str] = None,
        app_type: Optional[str] = Query(None, alias="type"),
        status_filter: Optional[str] = Query(None, alias="status"),
        db: AsyncSession = Depends(get_db),
        payload=Depends(require_user),
    ):
        """Return a paginated list of applications assigned to the logged-in user."""
        endpoint = "/ads/v1/application"
        try:
            user_id = UUID(payload["user_id"])
            ip_address = request.client.host if request.client else None

            total, apps = await ApplicationQuery.get_all_for_user(
                db, user_id, page, size, search, app_type, status_filter
            )

            await ActivityService.log_activity(
                db=db,
                user_id=user_id,
                module="application",
                action="view",
                description="User listed their assigned applications.",
                ip_address=ip_address,
            )
            await db.commit()

            success_type = "application_retrieve_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data={
                    "pagiation": {"total": total, "page": page, "size": size},
                    "items": [ApplicationOut.model_validate(a).model_dump() for a in apps],
                },
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
        app_id: UUID,
        db: AsyncSession = Depends(get_db),
        payload=Depends(require_user),
    ):
        """Return a single application by ID Ã¢â‚¬â€ only if it is assigned to the logged-in user."""
        endpoint = f"/ads/v1/application/{app_id}"
        try:
            user_id = UUID(payload["user_id"])
            ip_address = request.client.host if request.client else None

            app = await ApplicationQuery.get_by_id_for_user(app_id, user_id, db)
            if not app:
                self.raise_detailed_exception(endpoint, "application_not_found")

            await ActivityService.log_activity(
                db=db,
                user_id=user_id,
                module="application",
                action="view",
                reference_id=app_id,
                description=f"User viewed application {app_id}.",
                ip_address=ip_address,
            )
            await db.commit()

            success_type = "application_retrieve_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data=ApplicationOut.model_validate(app).model_dump(),
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


