"""User-side Ad Master router Ã¢â‚¬â€ GET only, global read access."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.postgres import get_db
from app.services.Jwt.bearer import require_user
from app.services.logger.logger import get_logger
from app.utils.helper import load_message_details, format_response, exception_format_response
from app.router.user.ad_master.ad_master_access import AdMasterQuery
from app.router.user.ad_master.ad_master_validator import AdMasterOut
from app.services.activity.activity_service import ActivityService

_BASE = Path(__file__).resolve().parents[4]
logger = get_logger(__name__)
error_details = load_message_details(str(_BASE / "app" / "data" / "error_details.json"))
success_details = load_message_details(str(_BASE / "app" / "data" / "success_details.json"))


class UserAdMasterRouter:
    """Read-only ad master endpoints for regular users.
    Ad master entries (ad_format / ad_platform) are global reference data accessible to all authenticated users.
    """

    def __init__(self):
        self.router = APIRouter(prefix="/ads/v1/admaster", tags=["User - Ad Master"])
        self.router.get("", status_code=status.HTTP_200_OK, dependencies=[Depends(require_user)])(self.get_all)
        self.router.get("/{ad_master_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(require_user)])(self.get)

    async def get_all(
        self,
        request: Request,
        type_filter: Optional[str] = Query(None, alias="type"),
        db: AsyncSession = Depends(get_db),
        payload=Depends(require_user),
    ):
        """Return all active ad master entries. Optionally filter by type (ad_format / ad_platform)."""
        endpoint = "/ads/v1/admaster"
        try:
            user_id = UUID(payload["user_id"])
            ip_address = request.client.host if request.client else None

            items = await AdMasterQuery.get_all(db, type_=type_filter)

            await ActivityService.log_activity(
                db=db,
                user_id=user_id,
                module="ad_master",
                action="view",
                description="User listed all ad master entries.",
                ip_address=ip_address,
            )
            await db.commit()

            success_type = "ad_master_retrieve_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data=[AdMasterOut.model_validate(i).model_dump() for i in items],
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
        ad_master_id: UUID,
        db: AsyncSession = Depends(get_db),
        payload=Depends(require_user),
    ):
        """Return a single ad master entry by ID."""
        endpoint = f"/ads/v1/admaster/{ad_master_id}"
        try:
            user_id = UUID(payload["user_id"])
            ip_address = request.client.host if request.client else None

            item = await AdMasterQuery.get_by_id(ad_master_id, db)
            if not item:
                self.raise_detailed_exception(endpoint, "ad_master_not_found")

            await ActivityService.log_activity(
                db=db,
                user_id=user_id,
                module="ad_master",
                action="view",
                reference_id=ad_master_id,
                description=f"User viewed ad master {ad_master_id}.",
                ip_address=ip_address,
            )
            await db.commit()

            success_type = "ad_master_retrieve_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data=AdMasterOut.model_validate(item).model_dump(),
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


