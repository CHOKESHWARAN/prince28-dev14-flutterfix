"""App factory: build a fully wired FastAPI app from settings."""

import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import APIRouter, FastAPI

from flutterfix.api.errors import register_error_handlers
from flutterfix.api.middleware import request_context
from flutterfix.api.routes import chat, documents, health, ingest
from flutterfix.config import Settings, get_settings
from flutterfix.db.llm_calls import make_recorder
from flutterfix.db.session import make_engine, make_sessionmaker
from flutterfix.llm.gateway import build_gateway
from flutterfix.logging_setup import setup_logging

logger = logging.getLogger("flutterfix")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)
    engine = make_engine(settings)  # no connection is opened yet

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("starting", extra={"status": settings.app_env})
        worker_task = None
        if settings.worker_in_api:
            try:
                from arq import run_worker

                from flutterfix.workers.main import WorkerSettings

                worker_task = asyncio.create_task(run_worker(WorkerSettings))
                logger.info("Background ARQ worker task started in API process")
            except Exception as exc:
                logger.warning("Could not start background worker in API: %s", exc)

        yield

        if worker_task:
            worker_task.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await worker_task

        if hasattr(app.state, "redis_pool") and app.state.redis_pool:
            with suppress(Exception):
                await app.state.redis_pool.close()

        await engine.dispose()  # close every pooled connection on shutdown

    app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = engine
    app.state.sessionmaker = make_sessionmaker(engine)
    app.state.system_prompt = chat.load_prompt(settings.prompts_dir)  # missing file: no start
    app.state.gateway = build_gateway(settings, make_recorder(app.state.sessionmaker))

    app.middleware("http")(request_context)
    register_error_handlers(app)

    v1 = APIRouter(prefix="/v1")
    v1.include_router(documents.router)
    v1.include_router(chat.router)
    v1.include_router(ingest.router)
    app.include_router(health.router)
    app.include_router(v1)
    return app
