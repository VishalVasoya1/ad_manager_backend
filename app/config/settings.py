"""Application settings loaded from .env file."""

from functools import lru_cache
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict
from app.services.logger.logger import get_logger

logger = get_logger(__name__)
_BASE = Path(__file__).resolve().parents[2]
_ENV_PATH = _BASE / ".env"


class Settings(BaseSettings):
    """Reads all configuration from the .env file at project root."""

    APP_NAME: str
    APP_ENV: str
    DEBUG: bool

    SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    DB_URL: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_NAME: Optional[str] = None
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[int] = None

    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None

    @property
    def DATABASE_URL(self) -> str:
        """Build the async PostgreSQL connection URL."""
        if self.DB_URL:
            return self.DB_URL
        if not all([self.DB_USER, self.DB_PASSWORD, self.DB_NAME, self.DB_HOST, self.DB_PORT]):
            raise ValueError("Set DB_URL or provide DB_USER, DB_PASSWORD, DB_NAME, DB_HOST, DB_PORT")
        password = quote_plus(self.DB_PASSWORD)
        url = f"postgresql+asyncpg://{self.DB_USER}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        logger.debug("DATABASE_URL generated for host=%s port=%s db=%s", self.DB_HOST, self.DB_PORT, self.DB_NAME)
        return url

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
