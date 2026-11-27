"""ARQ worker configuration and entrypoint."""

import httpx
from arq.connections import RedisSettings

from flutterfix.config import get_settings
from flutterfix.db.session import make_engine, make_sessionmaker
from flutterfix.llm.gateway import build_gateway
from flutterfix.workers.ingest import process_ingest_item


async def startup(ctx: dict) -> None:
    """Initialize database, HTTP client, and LLM gateway on worker startup."""
    settings = get_settings()
    engine = make_engine(settings)
    sessionmaker = make_sessionmaker(engine)
    has_keys = bool(settings.gemini_api_key or settings.groq_api_key)
    gateway = build_gateway(settings) if has_keys else None
    http_client = httpx.AsyncClient(timeout=30.0)

    ctx["settings"] = settings
    ctx["engine"] = engine
    ctx["sessionmaker"] = sessionmaker
    ctx["gateway"] = gateway
    ctx["http_client"] = http_client


async def shutdown(ctx: dict) -> None:
    """Clean up resources on worker shutdown."""
    if "http_client" in ctx and ctx["http_client"]:
        await ctx["http_client"].aclose()
    if "engine" in ctx and ctx["engine"]:
        await ctx["engine"].dispose()


settings = get_settings()


class WorkerSettings:
    """ARQ Worker configuration class."""

    functions = [process_ingest_item]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = settings.ingest_concurrency
    job_timeout = settings.ingest_job_timeout
    max_tries = settings.ingest_max_tries
