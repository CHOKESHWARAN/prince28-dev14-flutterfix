"""Integration test fixtures: creates a fresh, isolated PostgreSQL database per test session."""

import os

os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT", "1")

import asyncio
import concurrent.futures
import contextlib
import os
import re
import uuid
from collections.abc import AsyncGenerator
from urllib.parse import urlparse, urlunparse

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from flutterfix.config import get_settings
from flutterfix.db.session import dispose_engine
from flutterfix.db.url import build_asyncpg_db_url

# Safety safeguard: NEVER drop these system or application databases
PROTECTED_DATABASES = {
    "postgres",
    "app",
    "app_test",
    "neondb",
    "template0",
    "template1",
}
TEST_DB_NAME_PATTERN = re.compile(r"^flutterfix_test_[0-9a-f]{12}$")


def _validate_safe_test_db_name(name: str) -> None:
    """Ensure the target database name is strictly a generated temporary test database."""
    if not TEST_DB_NAME_PATTERN.match(name):
        raise ValueError(
            f"Unsafe database name '{name}'. Must match pattern 'flutterfix_test_<uuid>'."
        )
    if name.lower() in PROTECTED_DATABASES:
        raise ValueError(f"Refusing to operate on protected database: '{name}'")


@pytest.fixture(scope="session")
def raw_test_db_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip(
            "TEST_DATABASE_URL not set. Skipping integration tests requiring real PostgreSQL.",
            allow_module_level=True,
        )
    return url


@pytest.fixture(scope="session")
def test_db_name() -> str:
    name = f"flutterfix_test_{uuid.uuid4().hex[:12]}"
    _validate_safe_test_db_name(name)
    return name


def _get_connect_args(url: str) -> dict:
    return {"ssl": False} if "localhost" in url or "127.0.0.1" in url else {}


@pytest.fixture(scope="session")
def fresh_database(raw_test_db_url: str, test_db_name: str):
    """Session fixture: creates an isolated DB, runs migrations, and guarantees drop on teardown."""
    _validate_safe_test_db_name(test_db_name)

    parsed = urlparse(raw_test_db_url)
    admin_url = raw_test_db_url
    admin_async_url, admin_connect_args = build_asyncpg_db_url(admin_url)

    target_url = urlunparse(parsed._replace(path=f"/{test_db_name}"))
    target_async_url, target_connect_args = build_asyncpg_db_url(target_url)

    async def _create_database():
        admin_engine = create_async_engine(
            admin_async_url,
            isolation_level="AUTOCOMMIT",
            connect_args=admin_connect_args,
        )
        try:
            async with admin_engine.connect() as conn:
                await conn.execute(text(f'CREATE DATABASE "{test_db_name}"'))
        finally:
            await admin_engine.dispose()

    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.submit(asyncio.run, _create_database()).result()
    except Exception as exc:
        err_msg = str(exc).lower()
        if (
            isinstance(exc, (OSError, ConnectionRefusedError))
            or "connection refused" in err_msg
            or "cannot connect" in err_msg
            or "failed to connect" in err_msg
        ):
            pytest.skip(
                f"PostgreSQL at {admin_url} is not reachable. Skipping integration tests.",
                allow_module_level=True,
            )
        raise

    orig_env = os.environ.get("APP_ENV")
    orig_db_url = os.environ.get("DATABASE_URL")

    try:
        os.environ["APP_ENV"] = "ci"
        os.environ["DATABASE_URL"] = target_url
        get_settings.cache_clear()

        import flutterfix.db.session as session_mod

        async def _rebind_session():
            await session_mod.dispose_engine()
            session_mod.engine = session_mod.create_engine_from_settings()
            session_mod.AsyncSessionLocal = async_sessionmaker(
                bind=session_mod.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.submit(asyncio.run, _rebind_session()).result()

        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option(
            "sqlalchemy.url", target_async_url.render_as_string(hide_password=False)
        )
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.submit(command.upgrade, alembic_cfg, "head").result()

        yield {
            "db_name": test_db_name,
            "db_url": target_url,
            "async_url": target_async_url,
            "connect_args": target_connect_args,
        }
    finally:

        async def _cleanup_database():
            await dispose_engine()
            cleanup_engine = create_async_engine(
                admin_async_url,
                isolation_level="AUTOCOMMIT",
                connect_args=admin_connect_args,
            )
            try:
                async with cleanup_engine.connect() as conn:
                    await conn.execute(
                        text(
                            """
                            SELECT pg_terminate_backend(pid)
                            FROM pg_stat_activity
                            WHERE datname = :datname AND pid <> pg_backend_pid()
                            """
                        ),
                        {"datname": test_db_name},
                    )
                    _validate_safe_test_db_name(test_db_name)
                    await conn.execute(text(f'DROP DATABASE IF EXISTS "{test_db_name}"'))

                    # Verify that the temporary database no longer exists after teardown
                    verify_stmt = text("SELECT 1 FROM pg_database WHERE datname = :datname")
                    check_result = await conn.execute(verify_stmt, {"datname": test_db_name})
                    if check_result.scalar() is not None:
                        raise RuntimeError(
                            f"Database cleanup verification failed: '{test_db_name}' "
                            "still exists after DROP DATABASE."
                        )
            finally:
                await cleanup_engine.dispose()

        try:
            # Execute cleanup without hiding exceptions
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.submit(asyncio.run, _cleanup_database()).result()
        finally:
            # Ensure environment restoration runs even if cleanup raises
            if orig_env is not None:
                os.environ["APP_ENV"] = orig_env
            else:
                os.environ.pop("APP_ENV", None)

            if orig_db_url is not None:
                os.environ["DATABASE_URL"] = orig_db_url
            else:
                os.environ.pop("DATABASE_URL", None)

            get_settings.cache_clear()

            with (
                contextlib.suppress(Exception),
                concurrent.futures.ThreadPoolExecutor() as executor,
            ):
                executor.submit(asyncio.run, _rebind_session()).result()


@pytest.fixture
async def db_session(fresh_database) -> AsyncGenerator[AsyncSession, None]:
    async_url = fresh_database["async_url"]
    engine = create_async_engine(async_url, connect_args=fresh_database["connect_args"])
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()
