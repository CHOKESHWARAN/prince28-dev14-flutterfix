"""Integration tests for IngestJob and IngestItem database persistence."""

import uuid

import pytest
from sqlalchemy import func, select

from flutterfix.config import Settings
from flutterfix.db.models import IngestItem, IngestJob
from flutterfix.db.session import make_engine, make_sessionmaker


@pytest.mark.asyncio
async def test_ingest_job_lifecycle(database_url):
    engine = make_engine(Settings(app_env="ci", database_url=database_url, _env_file=None))
    sessionmaker = make_sessionmaker(engine)

    async with sessionmaker() as session:
        job_id = uuid.uuid4().hex
        job = IngestJob(id=job_id, requested=2)
        session.add(job)
        await session.commit()

        item1 = IngestItem(
            job_id=job_id,
            record={"url": "https://docs.flutter.dev/test1", "sha256": "sha1"},
            status="queued",
        )
        item2 = IngestItem(
            job_id=job_id,
            record={"url": "https://docs.flutter.dev/test2", "sha256": "sha2"},
            status="queued",
        )
        session.add_all([item1, item2])
        await session.commit()

        # Update item1 to done with 3 pages
        item1.status = "done"
        item1.pages = 3
        # Update item2 to failed
        item2.status = "failed"
        item2.error = "Test failure"
        item2.attempts = 3
        await session.commit()

        # Verify counts
        stmt = (
            select(IngestItem.status, func.count(IngestItem.id), func.sum(IngestItem.pages))
            .where(IngestItem.job_id == job_id)
            .group_by(IngestItem.status)
        )
        rows = dict((await session.execute(stmt)).all())
        assert rows.get("done") == 1
        assert rows.get("failed") == 1

        # Cleanup
        await session.delete(job)
        await session.commit()

    await engine.dispose()
