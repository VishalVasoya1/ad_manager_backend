"""User router — full CRUD for admin user management."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from app.config.postgres import get_db
from app.services.Jwt.bearer import jwt_bearer, require_admin
from app.utils.password_manager import PasswordManager
from app.services.logger.logger import get_logger
from app.utils.helper import (
    load_message_details,
    format_response,
    exception_format_response,
)
from app.router.user.user_access import UserQuery
from app.router.user.user_validator import (
    UserOut,
    UserCreateRequest,
    UserUpdateRequest,
)
from app.services.activity.activity_service import ActivityService

_BASE = Path(__file__).resolve().parents[3]
logger = get_logger(__name__)
error_details = load_message_details(str(_BASE / "app" / "data" / "error_details.json"))
success_details = load_message_details(str(_BASE / "app" / "data" / "success_details.json"))


class UserRouter:
    """CRUD endpoints for user management. Write operations are admin-only."""

    def __init__(self):
        self.router = APIRouter(prefix="/admin/ads/v1/user", tags=["User"])

        self.router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])(self.create_user)
        self.router.get("", status_code=status.HTTP_200_OK, dependencies=[Depends(jwt_bearer)])(self.get_all_users)
        self.router.get("/{user_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(jwt_bearer)])(self.get_user)
        self.router.put("/{user_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(require_admin)])(self.update_user)
        self.router.delete("/{user_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(require_admin)])(self.delete_user)

    async def create_user(
        self,
        request: Request,
        body: UserCreateRequest,
        db: AsyncSession = Depends(get_db),
        payload: dict = Depends(jwt_bearer),
    ):
        """Create a new user. Reactivates a soft-deleted user if the email already exists."""
        endpoint = "/user"
        
        try:
            admin_id = UUID(payload["user_id"])

            existing = await UserQuery.get_user_by_email_any(db=db, email=body.email.lower())
            if existing and not existing.is_deleted:
                self.raise_detailed_exception(endpoint, "user_already_exists_error")

            from app.model.user import User

            new_user = User(
                email=body.email.lower(),
                password=PasswordManager().get_hashed_password(body.password),
                role=body.role.lower(),
                status=body.status.lower(),
                is_deleted=False,
                created_by=admin_id,
                updated_by=admin_id,
            )
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)

            await ActivityService.log_activity(
                db=db,
                user_id=admin_id,
                module="user",
                action="create",
                reference_id=new_user.id,
                description=f"Created user {new_user.email} with role {new_user.role}.",
                ip_address=request.client.host if request.client else None,
            )
            await db.commit()

            success_type = "user_register_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data=UserOut.model_validate(new_user).model_dump(),
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Create user failed")
            self.handle_exception(endpoint, e)

    async def get_all_users(
        self,
        request: Request,
        page: int = Query(1, ge=1),
        size: int = Query(10, ge=1, le=100),
        search: Optional[str] = None,
        role: Optional[str] = None,
        status_filter: Optional[str] = Query(None, alias="status"),
        db: AsyncSession = Depends(get_db),
        payload: dict = Depends(jwt_bearer),
    ):
        """Return a paginated list of users with optional filters."""
        endpoint = "/user"
        
        try:
            admin_id = UUID(payload["user_id"])

            total, users = await UserQuery.get_all_users(
                db=db, page=page, size=size, search=search, role=role, status=status_filter,
            )
            await ActivityService.log_activity(
                db=db,
                user_id=admin_id,
                module="user",
                action="view",
                description="Listed all users.",
                ip_address=request.client.host if request.client else None,
            )
            await db.commit()
            success_type = "user_retrieve_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data={"pagiation" : {"total": total, "page": page, "size": size},
                      "items": [UserOut.model_validate(u).model_dump() for u in users]},
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.exception("List users failed")
            self.handle_exception(endpoint, e)

    async def get_user(
        self,
        request: Request,
        user_id: UUID,
        db: AsyncSession = Depends(get_db),
        payload: dict = Depends(jwt_bearer),
    ):
        """Return a single user by ID."""
        endpoint = f"/user/{user_id}"
        
        try:
            admin_id = UUID(payload["user_id"])
            user = await UserQuery.get_user_by_id(db=db, user_id=user_id)

            if not user:
                self.raise_detailed_exception(endpoint, "user_not_found")

            await ActivityService.log_activity(
                db=db,
                user_id=admin_id,
                module="user",
                action="view",
                reference_id=user_id,
                description=f"Viewed user {user.email}.",
                ip_address=request.client.host if request.client else None,
            )
            await db.commit()

            success_type = "user_retrieve_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data=UserOut.model_validate(user).model_dump(),
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )

        except HTTPException:
            raise
        except Exception as e:
            self.handle_exception(endpoint, e)

    async def update_user(
        self,
        request: Request,
        user_id: UUID,
        body: UserUpdateRequest,
        db: AsyncSession = Depends(get_db),
        payload: dict = Depends(jwt_bearer),
    ):
        """Update user fields. Only provided fields are changed."""
        endpoint = f"/user/{user_id}"
        
        try:
            admin_id = UUID(payload["user_id"])
            user = await UserQuery.get_user_by_id(db=db, user_id=user_id)

            if not user:
                self.raise_detailed_exception(endpoint, "user_not_found")

            if body.email:
                user.email = body.email.lower()
            if body.password:
                user.password = PasswordManager().get_hashed_password(body.password)
            if body.status:
                user.status = body.status.lower()
            
            user.updated_by = admin_id
            await db.commit()
            await db.refresh(user)

            await ActivityService.log_activity(
                db=db,
                user_id=admin_id,
                module="user",
                action="update",
                reference_id=user_id,
                description=f"Updated user {user.email}.",
                ip_address=request.client.host if request.client else None,
            )
            await db.commit()

            success_type = "user_update_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data=UserOut.model_validate(user).model_dump(),
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )

        except HTTPException:
            raise
        except Exception as e:
            self.handle_exception(endpoint, e)

    async def delete_user(
        self,
        request: Request,
        user_id: UUID,
        db: AsyncSession = Depends(get_db),
        payload: dict = Depends(jwt_bearer),
    ):
        """Soft-delete a user by setting is_deleted to True."""
        endpoint = f"/user/{user_id}"
        
        try:
            admin_id = UUID(payload["user_id"])
            user = await UserQuery.get_user_by_id(db=db, user_id=user_id)

            if not user:
                self.raise_detailed_exception(endpoint, "user_not_found")

            user.is_deleted = True
            await db.commit()

            await ActivityService.log_activity(
                db=db,
                user_id=admin_id,
                module="user",
                action="delete",
                reference_id=user_id,
                description=f"Deleted user {user_id}.",
                ip_address=request.client.host if request.client else None,
            )
            await db.commit()

            success_type = "user_delete_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data=None,
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )

        except HTTPException:
            raise
        except Exception as e:
            self.handle_exception(endpoint, e)

    def handle_exception(self, endpoint, e):
        """Raise a generic 500 HTTP exception."""
        error_type = "exception_error"
        response = exception_format_response(
            detail_type=error_details[error_type]["detail_type"],
            msg=error_details[error_type]["msg"],
            reason=str(e),
        )
        logger.critical(f"{endpoint}: {response}")
        raise HTTPException(status_code=error_details[error_type]["status_code"], detail=[response])

    def raise_detailed_exception(self, endpoint: str, error_type: str):
        """Raise a typed HTTP exception using the error details registry."""
        response = exception_format_response(
            detail_type=error_details[error_type]["detail_type"],
            msg=error_details[error_type]["msg"],
            reason=error_details[error_type]["reason"],
        )
        logger.critical(f"{endpoint}: {response}")
        raise HTTPException(status_code=error_details[error_type]["status_code"], detail=[response])


user_router = UserRouter()
