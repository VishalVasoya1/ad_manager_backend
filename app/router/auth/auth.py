"""Auth router — login and logout endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config.postgres import get_db
from app.services.Jwt.jwt_authentication import create_access_token, create_refresh_token
from app.services.Jwt.bearer import jwt_bearer
from app.utils.password_manager import PasswordManager
from app.services.logger.logger import get_logger
from app.utils.helper import load_message_details, exception_format_response, format_response
from app.router.auth.auth_access import AuthQuery
from app.router.auth.auth_validator import AuthLoginRequest, AuthResponse
from app.model.token_blacklist import TokenBlacklist
from app.services.activity.activity_service import ActivityService

_BASE = Path(__file__).resolve().parents[3]
logger = get_logger(__name__)
error_details = load_message_details(str(_BASE / "app" / "data" / "error_details.json"))
success_details = load_message_details(str(_BASE / "app" / "data" / "success_details.json"))


class AuthRouter:
    """Handles user authentication and session management."""

    def __init__(self):
        self.router = APIRouter(prefix="/admin/ads/v1/auth", tags=["Auth"])
        self.router.post("/login", status_code=status.HTTP_200_OK)(self.login)
        self.router.post("/logout", status_code=status.HTTP_200_OK, dependencies=[Depends(jwt_bearer)])(self.logout)

    async def login(self, request: Request, body: AuthLoginRequest, db: AsyncSession = Depends(get_db)):
        """Validate credentials and return access and refresh tokens."""
        endpoint = "/auth/login"
        try:
            logger.info(f"{endpoint}: Login attempt for {body.email}")
            user = await AuthQuery.get_user_by_email(body.email, db)

            ip_address = request.client.host if request.client else None
            device_info = request.headers.get("user-agent")

            if not user:
                await db.commit()
                return self.raise_detailed_exception(endpoint, "invalid_credentials_error")

            password_manager = PasswordManager()
            if not password_manager.verify_password(body.password, user.password):
                # Log failed login attempt
                await ActivityService.log_login(
                    db=db,
                    user_id=user.id,
                    login_status="failed",
                    ip_address=ip_address,
                    device_info=device_info,
                )
                await db.commit()
                return self.raise_detailed_exception(endpoint, "invalid_credentials_error")

            if user.role.lower() != "admin":
                await ActivityService.log_login(
                    db=db,
                    user_id=user.id,
                    login_status="failed",
                    ip_address=ip_address,
                    device_info=device_info,
                )
                await db.commit()
                return self.raise_detailed_exception(endpoint, "invalid_credentials_error")

            access_token = create_access_token({"user_id": str(user.id), "role": user.role})
            refresh_token = create_refresh_token({"user_id": str(user.id), "role": user.role})

            # Log successful login
            await ActivityService.log_login(
                db=db,
                user_id=user.id,
                login_status="success",
                ip_address=ip_address,
                device_info=device_info,
            )
            # Log login activity
            await ActivityService.log_activity(
                db=db,
                user_id=user.id,
                module="auth",
                action="login",
                description=f"User {user.email} logged in.",
                ip_address=ip_address,
            )

            await db.commit()

            success_type = "user_login_success"
            response = format_response(
                detail_type=success_details[success_type]["detail_type"],
                data={
                    **AuthResponse.model_validate(user).model_dump(),
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                },
                msg=success_details[success_type]["msg"],
                status_code=success_details[success_type]["status_code"],
            )
            logger.info(f"{endpoint}: Login successful for {user.email}")
            return response

        except HTTPException as http_error:
            raise http_error
        except Exception as e:
            logger.exception(f"{endpoint}: Exception occurred during login")
            return self.handle_exception(endpoint, e)

    async def logout(self, request: Request, db: AsyncSession = Depends(get_db), payload=Depends(jwt_bearer)):
        """Blacklist the current token and stamp the logout time."""
        endpoint = "/auth/logout"
        try:
            token = request.state.token
            user_id = UUID(payload["user_id"])

            result = await db.execute(
                select(TokenBlacklist).where(TokenBlacklist.token == token)
            )
            if result.scalar_one_or_none():
                return self.raise_detailed_exception(endpoint, "token_already_revoked")

            db.add(TokenBlacklist(token=token))

            # Stamp logout_time on the most recent login log
            await ActivityService.stamp_logout(db=db, user_id=user_id)

            # Log logout activity
            ip_address = request.client.host if request.client else None
            await ActivityService.log_activity(
                db=db,
                user_id=user_id,
                module="auth",
                action="logout",
                description=f"User {user_id} logged out.",
                ip_address=ip_address,
            )

            await db.commit()

            logger.info(f"{endpoint}: Token blacklisted for user {user_id}")

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
            logger.exception(f"{endpoint}: Exception occurred during logout")
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


auth_router = AuthRouter()
