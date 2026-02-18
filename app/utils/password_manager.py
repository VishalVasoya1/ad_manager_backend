"""Password hashing and verification service using bcrypt directly."""

import bcrypt


class PasswordManager:
    """Utility class for password hashing and verification using bcrypt."""

    def get_hashed_password(self, password: str) -> str:
        """Hash a plaintext password."""
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, password: str, hashed_pass: str) -> bool:
        """Verify a plaintext password against its hash."""
        return bcrypt.checkpw(password.encode("utf-8"), hashed_pass.encode("utf-8"))
