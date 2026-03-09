"""JWT token creation and verification."""

from datetime import datetime, timedelta, timezone
from typing import Union, Optional, Dict, Any

import jwt

from app.config.setting import settings
from app.services.logger.logger import get_logger

logger = get_logger(__name__)

ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS
JWT_ALGORITHM = settings.JWT_ALGORITHM
JWT_SECRET_KEY = settings.SECRET_KEY


def create_access_token(subject: Union[str, dict], expires_delta: int = None) -> str:
    """Create a signed short-lived access token."""
    try:
        expire_time = datetime.now(timezone.utc) + timedelta(
            minutes=expires_delta if expires_delta is not None else ACCESS_TOKEN_EXPIRE_MINUTES
        )
        to_encode = subject if isinstance(subject, dict) else {"sub": str(subject)}
        to_encode.update({"exp": expire_time})
        token = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        logger.info("JWT access token created successfully.")
        return token
    except Exception as e:
        logger.exception(f"Exception during token creation: {e}")
        raise


def create_refresh_token(subject: Union[str, dict]) -> str:
    """Create a signed long-lived refresh token."""
    try:
        expire_time = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode = subject if isinstance(subject, dict) else {"sub": str(subject)}
        to_encode.update({"exp": expire_time})
        token = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        logger.info("JWT refresh token created successfully.")
        return token
    except Exception as e:
        logger.exception(f"Exception during refresh token creation: {e}")
        raise


def decode_jwt(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify a JWT token. Returns None if expired or invalid."""
    try:
        decoded = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        logger.info(f"[DECODE SUCCESS] Payload: {decoded}")
        return decoded
    except jwt.ExpiredSignatureError:
        logger.warning("[JWT] Token expired.")
        return None
    except jwt.InvalidTokenError:
        logger.warning("[JWT] Invalid token.")
        return None
    except Exception as e:
        logger.exception(f"[JWT] Exception in decode: {str(e)}")
        return None
