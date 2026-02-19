"""Login logs router — view user login and logout history."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.postgres import get_db
from app.services.Jwt.bearer import require_admin
from app.services.logger.logger import get_logger
from app.utils.helper import load_message_details, format_response, exception_format_response
from app.router.logs.logs_access import LoginLogQuery
from app.router.logs.logs_validator import LoginLogOut

_BASE = Path(__file__).resolve().parents[3]
logger = get_logger(__name__)
error_details = load_message_details(str(_BASE / "app" / "data" / "error_details.json"))
success_details = load_message_details(str(_BASE / "app" / "data" / "success_details.json"))


class LoginLogsRouter:
    """Read-only endpoints for user login log history. Admin only."""

    def __init__(self):
        self.router = APIRouter(
            prefix="/admin/ads/v1/logs/login",
            tags=["Login Logs"],
            dependencies=[Depends(require_admin)],
        )
        self.router.get("", status_code=status.HTTP_200_OK)(self.get_all)
        self.router.get("/{log_id}", status_code=status.HTTP_200_OK)(self.get_one)

    async def get_all(
        self,
        request: Request,
        page: int = Query(1, ge=1),
        size: int = Query(10, ge=1, le=100),
        user_id: Optional[UUID] = None,
        login_status: Optional[str] = Query(None, pattern="^(success|failed)$"),
        db: AsyncSession = Depends(get_db),
    ):
        """Return paginated login logs. Filter by user_id and/or login_status."""
        endpoint = "/logs/login"
        try:
            total, logs = await LoginLogQuery.get_all(
                db=db, page=page, size=size, user_id=user_id, login_status=login_status
            )
            success_type = "login_logs_retrieve_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data={
                    "pagination": {"total": total, "page": page, "size": size},
                    "items": [LoginLogOut.model_validate(log).model_dump() for log in logs],
                },
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"{endpoint}: Failed to retrieve login logs")
            self.handle_exception(endpoint, e)

    async def get_one(
        self,
        request: Request,
        log_id: UUID,
        db: AsyncSession = Depends(get_db),
    ):
        """Return a single login log by ID."""
        endpoint = f"/logs/login/{log_id}"
        try:
            log = await LoginLogQuery.get_by_id(db=db, log_id=log_id)
            if not log:
                self.raise_detailed_exception(endpoint, "login_log_not_found")

            success_type = "login_logs_retrieve_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data=LoginLogOut.model_validate(log).model_dump(),
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"{endpoint}: Failed to retrieve login log")
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
