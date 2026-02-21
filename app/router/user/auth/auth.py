"""User Auth router Ã¢â‚¬â€ login and logout for role='user' accounts."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.postgres import get_db
from app.services.Jwt.jwt_authentication import create_access_token, create_refresh_token
from app.services.Jwt.bearer import jwt_bearer
from app.utils.password_manager import PasswordManager
from app.services.logger.logger import get_logger
from app.utils.helper import load_message_details, exception_format_response, format_response
from app.router.user.auth.auth_access import AuthQuery
from app.router.user.auth.auth_validator import AuthLoginRequest, AuthResponse
from app.model.token_blacklist import TokenBlacklist
from app.services.activity.activity_service import ActivityService
from sqlalchemy import select

_BASE = Path(__file__).resolve().parents[4]
logger = get_logger(__name__)
error_details = load_message_details(str(_BASE / "app" / "data" / "error_details.json"))
success_details = load_message_details(str(_BASE / "app" / "data" / "success_details.json"))


class UserAuthRouter:
    """Handles authentication for regular users (role='user')."""

    def __init__(self):
        self.router = APIRouter(prefix="/ads/v1/auth", tags=["User Auth"])
        self.router.post("/login", status_code=status.HTTP_200_OK)(self.login)
        self.router.post("/logout", status_code=status.HTTP_200_OK, dependencies=[Depends(jwt_bearer)])(self.logout)

    async def login(self, request: Request, body: AuthLoginRequest, db: AsyncSession = Depends(get_db)):
        """Validate credentials for role='user' accounts and return tokens."""
        endpoint = "/ads/v1/auth/login"
        try:
            logger.info(f"{endpoint}: Login attempt for {body.email}")
            user = await AuthQuery.get_user_by_email(body.email, db)

            ip_address = request.client.host if request.client else None
            device_info = request.headers.get("user-agent")

            if not user:
                self.raise_detailed_exception(endpoint, "invalid_credentials_error")

            password_manager = PasswordManager()
            if not password_manager.verify_password(body.password, user.password):
                await ActivityService.log_login(
                    db=db,
                    user_id=user.id,
                    login_status="failed",
                    ip_address=ip_address,
                    device_info=device_info,
                )
                await db.commit()
                self.raise_detailed_exception(endpoint, "invalid_credentials_error")

            # Only allow role='user' Ã¢â‚¬â€ not admins
            if user.role.lower() != "user":
                await ActivityService.log_login(
                    db=db,
                    user_id=user.id,
                    login_status="failed",
                    ip_address=ip_address,
                    device_info=device_info,
                )
                await db.commit()
                self.raise_detailed_exception(endpoint, "invalid_credentials_error")

            access_token = create_access_token({"user_id": str(user.id), "role": user.role})
            refresh_token = create_refresh_token({"user_id": str(user.id), "role": user.role})

            await ActivityService.log_login(
                db=db,
                user_id=user.id,
                login_status="success",
                ip_address=ip_address,
                device_info=device_info,
            )
            await ActivityService.log_activity(
                db=db,
                user_id=user.id,
                module="auth",
                action="login",
                description=f"User '{user.email}' (role: {user.role}) logged in successfully from {ip_address or 'unknown IP'}.",
                ip_address=ip_address,
            )
            await db.commit()

            success_type = "user_login_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data={
                    **AuthResponse.model_validate(user).model_dump(),
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                },
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )

        except HTTPException as http_error:
            raise http_error
        except Exception as e:
            logger.exception(f"{endpoint}: Exception during login")
            self.handle_exception(endpoint, e)

    async def logout(self, request: Request, db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Blacklist the current token and stamp the logout time."""
        endpoint = "/ads/v1/auth/logout"
        try:
            token = request.state.token
            user_id = UUID(payload["user_id"])

            result = await db.execute(
                select(TokenBlacklist).where(TokenBlacklist.token == token)
            )
            if result.scalar_one_or_none():
                self.raise_detailed_exception(endpoint, "token_already_revoked")

            db.add(TokenBlacklist(token=token))
            await ActivityService.stamp_logout(db=db, user_id=user_id)

            ip_address = request.client.host if request.client else None
            await ActivityService.log_activity(
                db=db,
                user_id=user_id,
                module="auth",
                action="logout",
                description=f"User (ID: {user_id}) logged out and token was blacklisted from {ip_address or 'unknown IP'}.",
                ip_address=ip_address,
            )
            await db.commit()

            success_type = "user_logout_success"
            return format_response(
                detail_type=success_details[success_type]["detail_type"],
                data=None,
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )

        except HTTPException as http_error:
            raise http_error
        except Exception as e:
            logger.exception(f"{endpoint}: Exception during logout")
            self.handle_exception(endpoint, e)

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


