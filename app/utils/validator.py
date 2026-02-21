"""Custom validators for fields used across the ad_manager application."""

import re
from app.services.logger.logger import get_logger

logger = get_logger(__name__)


def check_email(cls, v: str) -> str:
    """Validate email format."""
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(pattern, v):
        logger.warning("Email validation failed")
        raise ValueError("Invalid email format")
    return v.lower()


def check_password(cls, v: str) -> str:
    """Validate password: min 6 characters."""
    if len(v) < 6:
        logger.warning("Password validation failed due to min length")
        raise ValueError("Password must be at least 6 characters long")
    return v


def check_role(cls, v: str) -> str:
    """Validate user role."""
    if v not in ("admin", "user"):
        logger.warning("Role validation failed role=%s", v)
        raise ValueError("Role must be 'admin' or 'user'")
    return v.lower()


def check_status(cls, v: str) -> str:
    """Validate status value."""
    if v not in ("active", "inactive"):
        logger.warning("Status validation failed status=%s", v)
        raise ValueError("Status must be 'active' or 'inactive'")
    return v.lower()


def check_app_type(cls, v: str) -> str:
    """Validate application type."""
    if v not in ("android", "ios"):
        logger.warning("App type validation failed app_type=%s", v)
        raise ValueError("App type must be 'android' or 'ios'")
    return v.lower()


def check_ad_master_type(cls, v: str) -> str:
    """Validate ad master type."""
    if v not in ("ad_format", "ad_platform"):
        logger.warning("Ad master type validation failed type=%s", v)
        raise ValueError("Type must be 'ad_format' or 'ad_platform'")
    return v.lower()


def check_ad_field_type(cls, v: str) -> str:
    """Validate ad field type."""
    valid = ("radio", "dropdown", "input", "textfield", "checkbox")
    if v not in valid:
        logger.warning("Ad field type validation failed type=%s", v)
        raise ValueError(f"Ad field type must be one of: {', '.join(valid)}")
    return v.lower()
