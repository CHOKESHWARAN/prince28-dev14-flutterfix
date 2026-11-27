"""Redis queue helpers for ARQ."""

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from flutterfix.config import get_settings


def parse_redis_settings(redis_url: str) -> RedisSettings:
    """Parse a redis connection URL into Arq RedisSettings."""
    return RedisSettings.from_dsn(redis_url)


async def get_redis_pool(redis_url: str | None = None) -> ArqRedis:
    """Create and return an ArqRedis connection pool."""
    url = redis_url or get_settings().redis_url
    settings = parse_redis_settings(url)
    return await create_pool(settings)


async def enqueue_ingest_item(pool: ArqRedis, item_id: int) -> str | None:
    """Enqueue an ingestion item by its ID.

    Uses a deterministic job ID (f"ingest_item_{item_id}") to prevent duplicate
    processing in the queue.
    """
    job = await pool.enqueue_job(
        "process_ingest_item",
        item_id,
        _job_id=f"ingest_item_{item_id}",
    )
    return job.job_id if job else None
