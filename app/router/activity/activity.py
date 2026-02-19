"""User activity router — view audit trail of all user actions."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.postgres import get_db
from app.services.Jwt.bearer import require_admin
from app.services.logger.logger import get_logger
from app.utils.helper import load_message_details, format_response, exception_format_response
from app.router.activity.activity_access import ActivityQuery
from app.router.activity.activity_validator import ActivityOut

_BASE = Path(__file__).resolve().parents[3]
logger = get_logger(__name__)
error_details = load_message_details(str(_BASE / "app" / "data" / "error_details.json"))
success_details = load_message_details(str(_BASE / "app" / "data" / "success_details.json"))


class UserActivityRouter:
    """Read-only endpoints for user activity audit trail. Admin only."""

    def __init__(self):
        self.router = APIRouter(
            prefix="/admin/ads/v1/logs/activity",
            tags=["User Activity"],
            dependencies=[Depends(require_admin)],
        )
        self.router.get("", status_code=status.HTTP_200_OK)(self.get_all)
        self.router.get("/{activity_id}", status_code=status.HTTP_200_OK)(self.get_one)

    async def get_all(
        self,
        request: Request,
        page: int = Query(1, ge=1),
        size: int = Query(10, ge=1, le=100),
        user_id: Optional[UUID] = None,
        module: Optional[str] = None,
        action: Optional[str] = None,
        db: AsyncSession = Depends(get_db),
    ):
        """Return paginated activity logs. Filter by user_id, module, and/or action."""
        endpoint = "/logs/activity"
        try:
            total, activities = await ActivityQuery.get_all(
                db=db, page=page, size=size, user_id=user_id, module=module, action=action
            )
            success_type = "activity_retrieve_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data={
                    "pagination": {"total": total, "page": page, "size": size},
                    "items": [ActivityOut.model_validate(a).model_dump() for a in activities],
                },
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"{endpoint}: Failed to retrieve activity logs")
            self.handle_exception(endpoint, e)

    async def get_one(
        self,
        request: Request,
        activity_id: UUID,
        db: AsyncSession = Depends(get_db),
    ):
        """Return a single activity record by ID."""
        endpoint = f"/logs/activity/{activity_id}"
        try:
            activity = await ActivityQuery.get_by_id(db=db, activity_id=activity_id)
            if not activity:
                self.raise_detailed_exception(endpoint, "activity_not_found")

            success_type = "activity_retrieve_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data=ActivityOut.model_validate(activity).model_dump(),
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"{endpoint}: Failed to retrieve activity")
            self.handle_exception(endpoint, e)

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
