"""Optional integration tests against a live PostgreSQL instance."""

import asyncio
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from flutterfix.db.repository import DocumentRepository
from flutterfix.db.url import build_asyncpg_db_url

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")


@pytest.mark.skipif(not TEST_DB_URL, reason="TEST_DATABASE_URL not configured")
def test_live_postgres_queries():
    async def _run():
        url, connect_args = build_asyncpg_db_url(TEST_DB_URL)
        engine = create_async_engine(url, connect_args=connect_args)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar_one() == 1

            repo = DocumentRepository(session)
            items, total = await repo.list(limit=2)
            assert total >= 0
            assert isinstance(items, list)

        await engine.dispose()

    asyncio.run(_run())
