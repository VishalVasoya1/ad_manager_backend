"""JWT bearer authentication dependency and admin role guard."""

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.Jwt.jwt_authentication import decode_jwt
from app.services.logger.logger import get_logger
from app.config.postgres import get_db

logger = get_logger(__name__)


class JWTBearer(HTTPBearer):
    """Validates Bearer tokens and checks against the blacklist."""

    async def __call__(self, request: Request, db: AsyncSession = Depends(get_db)):
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)

        if not credentials:
            raise HTTPException(status_code=403, detail="Missing authorization header.")

        if credentials.scheme.lower() != "bearer":
            logger.warning("Invalid auth scheme.")
            raise HTTPException(status_code=403, detail="Invalid auth scheme.")

        token = credentials.credentials

        payload = decode_jwt(token)
        if not payload:
            logger.warning("Token expired or invalid.")
            raise HTTPException(status_code=401, detail=[{
                "type": "Session Expired",
                "msg": "Session is over. Please login again.",
                "reason": "The authentication token has expired or is invalid.",
            }])

        from app.model.token_blacklist import TokenBlacklist
        result = await db.execute(
            select(TokenBlacklist).where(TokenBlacklist.token == token)
        )
        if result.scalar_one_or_none():
            logger.warning("Blacklisted token used.")
            raise HTTPException(status_code=401, detail=[{
                "type": "Token Revoked",
                "msg": "You have been logged out. Please login again.",
                "reason": "This token has been invalidated.",
            }])

        request.state.token = token
        logger.info(f"JWT token verified. Payload: {payload}")
        return payload


jwt_bearer = JWTBearer()


def require_admin(payload: dict = Depends(jwt_bearer)):
    """Raise 403 if the authenticated user is not an admin."""
    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail=[{
                "type": "Access Denied",
                "msg": "Admin access required.",
                "ctx": {"reason": "Only admin users are allowed to perform this action."},
            }]
        )
    return payload


def require_user(payload: dict = Depends(jwt_bearer)):
    """Raise 403 if the authenticated user is not a regular user (role='user')."""
    if payload.get("role") != "user":
        raise HTTPException(
            status_code=403,
            detail=[{
                "type": "Access Denied",
                "msg": "User access required.",
                "ctx": {"reason": "Only regular users are allowed to access this endpoint."},
            }]
        )
    return payload
