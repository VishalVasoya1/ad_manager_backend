"""Class-based Redis client lifecycle manager."""

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config.settings import settings
from app.services.logger.logger import get_logger

logger = get_logger(__name__)


class RedisManager:
    """Manages a singleton async Redis client."""

    _client: Redis | None = None

    @classmethod
    async def init(cls) -> None:
        """Initialize Redis client for cache operations."""
        try:
            cls._client = Redis.from_url(settings.CACHE_REDIS_URL, decode_responses=True)
            await cls._client.ping()
            logger.info("Redis cache connected")
        except RedisError as e:
            cls._client = None
            logger.warning("Redis unavailable; continuing without cache: %s", str(e))

    @classmethod
    async def close(cls) -> None:
        """Close Redis client on app shutdown."""
        if cls._client is not None:
            await cls._client.close()
            cls._client = None
            logger.info("Redis cache connection closed")

    @classmethod
    def get_client(cls) -> Redis | None:
        """Return initialized Redis client or None."""
        return cls._client
