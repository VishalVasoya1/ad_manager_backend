"""Application router — CRUD and API key reset. Write operations are admin-only."""

import secrets
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.postgres import get_db
from app.services.Jwt.bearer import jwt_bearer, require_admin
from app.services.logger.logger import get_logger
from app.utils.helper import load_message_details, format_response, exception_format_response
from app.router.application.application_access import ApplicationQuery
from app.router.application.application_validator import ApplicationCreateRequest, ApplicationUpdateRequest, ApplicationOut
from app.model.application import Application
from app.services.activity.activity_service import ActivityService


_BASE = Path(__file__).resolve().parents[3]
logger = get_logger(__name__)
error_details = load_message_details(str(_BASE / "app" / "data" / "error_details.json"))
success_details = load_message_details(str(_BASE / "app" / "data" / "success_details.json"))


class ApplicationRouter:
    """CRUD endpoints for application management. Write operations are admin-only."""

    def __init__(self):
        self.router = APIRouter(prefix="/admin/ads/v1/application", tags=["Application"])
        self.router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])(self.create)
        self.router.get("", status_code=status.HTTP_200_OK, dependencies=[Depends(jwt_bearer)])(self.get_all)
        self.router.get("/{app_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(jwt_bearer)])(self.get)
        self.router.put("/{app_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(require_admin)])(self.update)
        self.router.delete("/{app_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(require_admin)])(self.delete)
        self.router.post("/{app_id}/reset-api-key", status_code=status.HTTP_200_OK, dependencies=[Depends(require_admin)])(self.reset_api_key)

    async def create(self, request: Request, body: ApplicationCreateRequest, db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Create a new application. Reactivates a soft-deleted record if the package name already exists."""
        endpoint = "/application"
        try:
            admin_id = UUID(payload["user_id"])
            ip_address = request.client.host if request.client else None

            from app.router.user.user_access import UserQuery
            assigned_user = await UserQuery.get_user_by_id(db, body.assign_by)
            if not assigned_user:
                self.raise_detailed_exception(endpoint, "user_not_found")
            if assigned_user.role != "user":
                self.raise_detailed_exception(endpoint, "assign_by_must_be_user_role")

            if body.package_name:
                existing = await ApplicationQuery.get_by_package_name_any(body.package_name, db)
                if existing and not existing.is_deleted:
                    self.raise_detailed_exception(endpoint, "package_name_already_exists")

            app = Application(
                **body.model_dump(),
                api_key=secrets.token_urlsafe(32),
                created_by=admin_id,
                updated_by=admin_id,
            )
            db.add(app)
            await db.flush()
            await db.refresh(app)
            await db.commit()
            await db.refresh(app)

            await ActivityService.log_activity(
                db=db,
                user_id=admin_id,
                module="application",
                action="create",
                reference_id=app.id,
                description=f"Created application '{app.package_name}'.",
                ip_address=ip_address,
            )
            await db.commit()

            success_type = "application_create_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data=ApplicationOut.model_validate(app).model_dump(),
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )
        except HTTPException as http_error:
            raise http_error
        except Exception as e:
            logger.exception(f"{endpoint}: Exception during application creation")
            return self.handle_exception(endpoint, e)

    async def get_all(
        self,
        request: Request,
        page: int = Query(1, ge=1),
        size: int = Query(10, ge=1, le=100),
        search: Optional[str] = None,
        app_type: Optional[str] = Query(None, alias="type"),
        status_filter: Optional[str] = Query(None, alias="status"),
        db: AsyncSession = Depends(get_db),
        payload=Depends(jwt_bearer),
    ):
        """Return a paginated list of applications with optional filters."""
        endpoint = "/application"
        try:
            admin_id = UUID(payload["user_id"])
            ip_address = request.client.host if request.client else None
            total, apps = await ApplicationQuery.get_all(db, page, size, search, app_type, status_filter)

            await ActivityService.log_activity(
                db=db,
                user_id=admin_id,
                module="application",
                action="view",
                description="Listed all applications.",
                ip_address=ip_address,
            )
            await db.commit()

            success_type = "application_retrieve_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data={"pagiation": {"total": total, "page": page, "size": size},
                      "items": [ApplicationOut.model_validate(a).model_dump() for a in apps]},
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )
        except HTTPException as http_error:
            raise http_error
        except Exception as e:
            return self.handle_exception(endpoint, e)

    async def get(self, request: Request, app_id: UUID, db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Return a single application by ID."""
        endpoint = f"/application/{app_id}"
        try:
            admin_id = UUID(payload["user_id"])
            ip_address = request.client.host if request.client else None
            app = await ApplicationQuery.get_by_id(app_id, db)
            if not app:
                self.raise_detailed_exception(endpoint, "application_not_found")

            await ActivityService.log_activity(
                db=db,
                user_id=admin_id,
                module="application",
                action="view",
                reference_id=app_id,
                description=f"Viewed application {app_id}.",
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
        except HTTPException as http_error:
            raise http_error
        except Exception as e:
            return self.handle_exception(endpoint, e)

    async def update(self, request: Request, app_id: UUID, body: ApplicationUpdateRequest, db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Update application fields. Only provided fields are changed."""
        endpoint = f"/application/{app_id}"
        try:
            admin_id = UUID(payload["user_id"])
            ip_address = request.client.host if request.client else None
            app = await ApplicationQuery.get_by_id(app_id, db)
            if not app:
                self.raise_detailed_exception(endpoint, "application_not_found")

            if body.assign_by:
                from app.router.user.user_access import UserQuery
                assigned_user = await UserQuery.get_user_by_id(db, body.assign_by)
                if not assigned_user:
                    self.raise_detailed_exception(endpoint, "user_not_found")
                if assigned_user.role != "user":
                    self.raise_detailed_exception(endpoint, "assign_by_must_be_user_role")

            for field, value in body.model_dump(exclude_none=True).items():
                setattr(app, field, value)
            app.updated_by = admin_id

            await db.flush()
            await db.commit()
            await db.refresh(app)

            await ActivityService.log_activity(
                db=db,
                user_id=admin_id,
                module="application",
                action="update",
                reference_id=app_id,
                description=f"Updated application {app_id}.",
                ip_address=ip_address,
            )
            await db.commit()

            success_type = "application_update_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data=ApplicationOut.model_validate(app).model_dump(),
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )
        except HTTPException as http_error:
            raise http_error
        except Exception as e:
            return self.handle_exception(endpoint, e)

    async def delete(self, request: Request, app_id: UUID, db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Soft-delete an application."""
        endpoint = f"/application/{app_id}"
        try:
            admin_id = UUID(payload["user_id"])
            ip_address = request.client.host if request.client else None
            app = await ApplicationQuery.get_by_id(app_id, db)
            if not app:
                self.raise_detailed_exception(endpoint, "application_not_found")

            app.is_deleted = True
            await db.flush()
            await db.commit()

            await ActivityService.log_activity(
                db=db,
                user_id=admin_id,
                module="application",
                action="delete",
                reference_id=app_id,
                description=f"Deleted application {app_id}.",
                ip_address=ip_address,
            )
            await db.commit()

            success_type = "application_delete_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data=None,
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )
        except HTTPException as http_error:
            raise http_error
        except Exception as e:
            return self.handle_exception(endpoint, e)

    async def reset_api_key(self, request: Request, app_id: UUID, db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Regenerate and return a new API key for the application."""
        endpoint = f"/application/{app_id}/reset-api-key"
        try:
            admin_id = UUID(payload["user_id"])
            ip_address = request.client.host if request.client else None
            app = await ApplicationQuery.get_by_id(app_id, db)
            if not app:
                self.raise_detailed_exception(endpoint, "application_not_found")

            app.api_key = secrets.token_urlsafe(32)
            app.updated_by = admin_id

            await db.flush()
            await db.commit()
            await db.refresh(app)

            await ActivityService.log_activity(
                db=db,
                user_id=admin_id,
                module="application",
                action="update",
                reference_id=app_id,
                description=f"Reset API key for application {app_id}.",
                ip_address=ip_address,
            )
            await db.commit()

            success_type = "application_update_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data={"api_key": app.api_key},
                msg="API key reset successfully.",
                status_code=success_details[success_type]["status_code"],
            )
        except HTTPException as http_error:
            raise http_error
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


application_router = ApplicationRouter()
