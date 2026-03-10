"""Async PostgreSQL engine, session factory, and FastAPI dependency."""

import importlib
import pkgutil
from typing import AsyncGenerator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config.setting import settings
from app.model.base import Base
from app.services.logger.logger import get_logger

logger = get_logger(__name__)


engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def import_models(package_name: str) -> None:
    """Dynamically import all modules in a package to register SQLAlchemy models."""
    logger.debug("Importing models from package=%s", package_name)
    package = importlib.import_module(package_name)
    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        logger.debug("Importing model module=%s.%s", package_name, module_name)
        importlib.import_module(f"{package_name}.{module_name}")


async def init_db() -> None:
    """Import all models and create tables if they do not exist."""
    try:
        logger.info("Initializing database schema")
        import_models("app.model")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized and tables created")
    except SQLAlchemyError as e:
        logger.exception("Database init failed")
        raise e


async def close_db() -> None:
    """Dispose the SQLAlchemy engine on shutdown."""
    logger.info("Closing database engine")
    await engine.dispose()
    logger.info("SQLAlchemy connection closed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for use as a FastAPI dependency."""
    async with AsyncSessionLocal() as session:
        try:
            logger.debug("Database session opened")
            yield session
        finally:
            await session.close()
            logger.debug("Database session closed")
