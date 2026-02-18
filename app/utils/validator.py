"""Custom validators for fields used across the ad_manager application."""

import re


def check_email(cls, v: str) -> str:
    """Validate email format."""
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(pattern, v):
        raise ValueError("Invalid email format")
    return v.lower()


def check_password(cls, v: str) -> str:
    """Validate password: min 6 characters."""
    if len(v) < 6:
        raise ValueError("Password must be at least 6 characters long")
    return v


def check_role(cls, v: str) -> str:
    """Validate user role."""
    if v not in ("admin", "user"):
        raise ValueError("Role must be 'admin' or 'user'")
    return v.lower()


def check_status(cls, v: str) -> str:
    """Validate status value."""
    if v not in ("active", "inactive"):
        raise ValueError("Status must be 'active' or 'inactive'")
    return v.lower()


def check_app_type(cls, v: str) -> str:
    """Validate application type."""
    if v not in ("android", "ios"):
        raise ValueError("App type must be 'android' or 'ios'")
    return v.lower()


def check_ad_master_type(cls, v: str) -> str:
    """Validate ad master type."""
    if v not in ("ad_format", "ad_platform"):
        raise ValueError("Type must be 'ad_format' or 'ad_platform'")
    return v.lower()


def check_ad_field_type(cls, v: str) -> str:
    """Validate ad field type."""
    valid = ("radio", "dropdown", "input", "textfield", "checkbox")
    if v not in valid:
        raise ValueError(f"Ad field type must be one of: {', '.join(valid)}")
    return v.lower()
