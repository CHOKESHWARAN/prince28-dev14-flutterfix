"""App factory: build a fully wired FastAPI app from settings."""

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from flutterfix.api.errors import register_error_handlers
from flutterfix.api.middleware import request_context
from flutterfix.api.routes import documents, health
from flutterfix.config import Settings, get_settings
from flutterfix.db.session import dispose_engine
from flutterfix.logging_setup import setup_logging

logger = logging.getLogger("flutterfix")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("application starting", extra={"env": settings.app_env})
        yield
        logger.info("application shutting down; disposing db engine")
        await dispose_engine()

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.state.settings = settings

    app.middleware("http")(request_context)
    register_error_handlers(app)

    v1 = APIRouter(prefix="/v1")
    v1.include_router(documents.router)
    app.include_router(health.router)
    app.include_router(v1)
    return app
