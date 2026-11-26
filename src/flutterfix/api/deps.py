"""Dependencies: endpoints ask for these instead of building them."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from flutterfix.config import Settings
from flutterfix.db import session as db_session
from flutterfix.db.llm_calls import LlmCallRepository
from flutterfix.db.repository import DocumentRepository


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an asynchronous database session per request."""
    async with db_session.AsyncSessionLocal() as session:
        yield session


def get_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentRepository:
    """Dependency injection for DocumentRepository."""
    return DocumentRepository(session)


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
RepoDep = Annotated[DocumentRepository, Depends(get_repository)]
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def get_gateway(request: Request):
    return request.app.state.gateway


def get_usage_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LlmCallRepository:
    return LlmCallRepository(session)


GatewayDep = Annotated[object, Depends(get_gateway)]
UsageDep = Annotated[LlmCallRepository, Depends(get_usage_repository)]
