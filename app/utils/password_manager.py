"""Password hashing and verification service using bcrypt directly."""

import bcrypt
from app.services.logger.logger import get_logger

logger = get_logger(__name__)


class PasswordManager:
    """Utility class for password hashing and verification using bcrypt."""

    def get_hashed_password(self, password: str) -> str:
        """Hash a plaintext password."""
        logger.debug("Hashing password")
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        logger.debug("Password hashed successfully")
        return hashed

    def verify_password(self, password: str, hashed_pass: str) -> bool:
        """Verify a plaintext password against its hash."""
        logger.debug("Verifying password hash")
        is_valid = bcrypt.checkpw(password.encode("utf-8"), hashed_pass.encode("utf-8"))
        logger.debug("Password verification result=%s", is_valid)
        return is_valid
