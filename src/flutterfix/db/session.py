"""SQLAlchemy asynchronous engine and session factory."""

import os
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from flutterfix.config import get_settings
from flutterfix.db.url import build_asyncpg_db_url

# Force pure Python mode on Windows to avoid DLL load issues with Cython C-extensions
os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT", "1")


def create_engine_from_settings() -> AsyncEngine:
    """Build the async SQLAlchemy engine using settings."""
    settings = get_settings()
    raw_url = (
        settings.database_url.get_secret_value()
        if settings.database_url
        else "postgresql+asyncpg://dummy:dummy@localhost/dummy"
    )
    url, connect_args = build_asyncpg_db_url(raw_url)

    return create_async_engine(
        url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


engine = create_engine_from_settings()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining an asynchronous database session."""
    async with AsyncSessionLocal() as session:
        yield session


async def check_database_connection() -> dict[str, str | int]:
    """Check connectivity to PostgreSQL with SELECT 1 and report server version."""
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        test_val = result.scalar_one()

        version_result = await conn.execute(text("SHOW server_version"))
        server_version = str(version_result.scalar_one())

        return {
            "status": "connected",
            "test_value": test_val,
            "server_version": server_version,
        }


async def dispose_engine() -> None:
    """Safely dispose of the engine connection pool."""
    await engine.dispose()
