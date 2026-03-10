"""Application settings loaded from .env file."""

from functools import lru_cache
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, unquote

from pydantic_settings import BaseSettings, SettingsConfigDict
from app.services.logger.logger import get_logger

logger = get_logger(__name__)
_BASE = Path(__file__).resolve().parents[2]
_ENV_PATH = _BASE / ".env.dev"


class Settings(BaseSettings):
    """Reads all configuration from the .env file at project root."""

    APP_NAME: str = "Ads Backend"
    APP_ENV: str = "development"
    DEBUG: bool | str = False

    SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    DB_URL: str

    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    REDIS_URL: str
    REDIS_CACHE_TTL_SECONDS: int = 3600

    @property
    def DEBUG_BOOL(self) -> bool:
        """Normalize DEBUG to bool for mixed env values."""
        if isinstance(self.DEBUG, bool):
            return self.DEBUG
        return str(self.DEBUG).strip().lower() in {"1", "true", "yes", "on", "debug", "development"}

    @property
    def DATABASE_URL(self) -> str:
        """Return PostgreSQL URL from environment."""
        return self.DB_URL

    @property
    def CACHE_REDIS_URL(self) -> str:
        """Return Redis URL from environment."""
        return self.REDIS_URL

    @property
    def DB_PARSED(self) -> tuple[str, str, str, int, str]:
        """Return parsed DB URL parts: user, password, host, port, database."""
        parsed = urlparse(self.DB_URL)
        user = unquote(parsed.username or "")
        password = unquote(parsed.password or "")
        host = parsed.hostname or ""
        port = parsed.port or 5432
        database = parsed.path.lstrip("/")
        if not all([user, password, host, database]):
            raise ValueError("DB_URL must include user, password, host, port, and database")
        return user, password, host, port, database

    model_config = SettingsConfigDict(
        env_file=str(_ENV_PATH),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    config = Settings()
    logger.info("Settings loaded APP_ENV=%s DEBUG=%s", config.APP_ENV, config.DEBUG)
    return config


settings: Settings = get_settings()
