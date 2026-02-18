"""Async PostgreSQL engine, session factory, and FastAPI dependency."""

import importlib
import pkgutil
from typing import AsyncGenerator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings
from app.model.base import Base


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
    package = importlib.import_module(package_name)
    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        importlib.import_module(f"{package_name}.{module_name}")


async def init_db() -> None:
    """Import all models and create tables if they do not exist."""
    try:
        import_models("app.model")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database initialized and tables created")
    except SQLAlchemyError as e:
        print(f"❌ Database init failed: {e}")
        raise e


async def close_db() -> None:
    """Dispose the SQLAlchemy engine on shutdown."""
    await engine.dispose()
    print("✅ SQLAlchemy connection closed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for use as a FastAPI dependency."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
