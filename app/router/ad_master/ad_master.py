"""Ad Master router — CRUD and search. Write operations are admin-only."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.postgres import get_db
from app.services.Jwt.bearer import jwt_bearer, require_admin
from app.services.logger.logger import get_logger
from app.utils.helper import load_message_details, format_response, exception_format_response
from app.router.ad_master.ad_master_access import AdMasterQuery
from app.router.ad_master.ad_master_validator import AdMasterCreateRequest, AdMasterUpdateRequest, AdMasterOut, AdMasterSearchOut
from app.model.ad_master import AdMaster


_BASE = Path(__file__).resolve().parents[3]
logger = get_logger(__name__)
error_details = load_message_details(str(_BASE / "app" / "data" / "error_details.json"))
success_details = load_message_details(str(_BASE / "app" / "data" / "success_details.json"))


class AdMasterRouter:
    """CRUD endpoints for ad master (ad_format / ad_platform) management."""

    def __init__(self):
        self.router = APIRouter(prefix="/admin/ads/v1/ad-master", tags=["Ad Master"])
        self.router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])(self.create)
        self.router.get("/search", status_code=status.HTTP_200_OK, dependencies=[Depends(jwt_bearer)])(self.search)
        self.router.get("", status_code=status.HTTP_200_OK, dependencies=[Depends(jwt_bearer)])(self.get_all)
        self.router.get("/{ad_master_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(jwt_bearer)])(self.get)
        self.router.put("/{ad_master_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(require_admin)])(self.update)
        self.router.delete("/{ad_master_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(require_admin)])(self.delete)

    async def search(self, request: Request, type: Optional[str] = Query(None), db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Search ad master entries by type (ad_format or ad_platform)."""
        endpoint = "/ad-master/search"
        try:
            items = await AdMasterQuery.search_by_type(type, db)
            return [AdMasterSearchOut.model_validate(i).model_dump() for i in items]
        except HTTPException as e:
            raise e
        except Exception as e:
            return self.handle_exception(endpoint, e)

    async def create(self, request: Request, body: AdMasterCreateRequest, db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Create a new ad master entry. Reactivates a soft-deleted record if the title+type already exists."""
        endpoint = "/ad-master"
        try:
            admin_id = UUID(payload["user_id"])
            existing = await AdMasterQuery.get_by_title_and_type_any(body.title, body.type, db)
            if existing and not existing.is_deleted:
                self.raise_detailed_exception(endpoint, "ad_master_already_exists")

            ad = AdMaster(title=body.title, type=body.type, created_by=admin_id, updated_by=admin_id)
            db.add(ad)
            await db.flush()
            await db.refresh(ad)

            await db.commit()
            await db.refresh(ad)

            success_type = "ad_master_create_success"
            return format_response(detail_type=success_details[success_type]["detail_type"], data=AdMasterOut.model_validate(ad).model_dump(), msg=success_details[success_type]["msg"], status_code=success_details[success_type]["status_code"])
        except HTTPException as e:
            raise e
        except Exception as e:
            return self.handle_exception(endpoint, e)

    async def get_all(self, request: Request, user_id: Optional[UUID] = Query(None), type: Optional[str] = Query(None), db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Return all active ad master entries with optional filters for user_id and type."""
        endpoint = "/ad-master"
       
        try:
            admin_id = UUID(payload["user_id"])
            items = await AdMasterQuery.get_all(db, user_id, type)

            await db.commit()

            success_type = "ad_master_retrieve_success"
            return format_response(detail_type=success_details[success_type]["detail_type"], data=[AdMasterOut.model_validate(i).model_dump() for i in items], msg=success_details[success_type]["msg"], status_code=success_details[success_type]["status_code"])
        except HTTPException as e:
            raise e
        except Exception as e:
            return self.handle_exception(endpoint, e)

    async def get(self, request: Request, ad_master_id: UUID, db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Return a single ad master entry by ID."""
        endpoint = f"/ad-master/{ad_master_id}"
        try:
            admin_id = UUID(payload["user_id"])
            ad = await AdMasterQuery.get_by_id(ad_master_id, db)
            if not ad:
                self.raise_detailed_exception(endpoint, "ad_master_not_found")

        
            await db.commit()

            success_type = "ad_master_retrieve_success"
            return format_response(detail_type=success_details[success_type]["detail_type"], data=AdMasterOut.model_validate(ad).model_dump(), msg=success_details[success_type]["msg"], status_code=success_details[success_type]["status_code"])
        except HTTPException as e:
            raise e
        except Exception as e:
            return self.handle_exception(endpoint, e)

    async def update(self, request: Request, ad_master_id: UUID, body: AdMasterUpdateRequest, db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Update the title of an ad master entry."""
        endpoint = f"/ad-master/{ad_master_id}"
    
        try:
            admin_id = UUID(payload["user_id"])
            ad = await AdMasterQuery.get_by_id(ad_master_id, db)
            if not ad:
                self.raise_detailed_exception(endpoint, "ad_master_not_found")

            if body.title:
                ad.title = body.title
            ad.updated_by = admin_id

            await db.flush()
            await db.commit()
            await db.refresh(ad)

            success_type = "ad_master_update_success"
            return format_response(detail_type=success_details[success_type]["detail_type"], data=AdMasterOut.model_validate(ad).model_dump(), msg=success_details[success_type]["msg"], status_code=success_details[success_type]["status_code"])
        except HTTPException as e:
            raise e
        except Exception as e:
            return self.handle_exception(endpoint, e)

    async def delete(self, request: Request, ad_master_id: UUID, db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Soft-delete an ad master entry."""
        endpoint = f"/ad-master/{ad_master_id}"
  
        try:
            admin_id = UUID(payload["user_id"])
            ad = await AdMasterQuery.get_by_id(ad_master_id, db)
            if not ad:
                self.raise_detailed_exception(endpoint, "ad_master_not_found")

            ad.is_deleted = True
            await db.flush()
            await db.commit()

            success_type = "ad_master_delete_success"
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


ad_master_router = AdMasterRouter()
