"""Dependencies: endpoints ask for these instead of building them."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from flutterfix.config import Settings
from flutterfix.db.repository import DocumentRepository
from flutterfix.db.session import AsyncSessionLocal
from flutterfix.store import RecordStore


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_store(request: Request) -> RecordStore:
    return getattr(request.app.state, "store", None)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an asynchronous database session per request."""
    async with AsyncSessionLocal() as session:
        yield session


def get_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentRepository:
    """Dependency injection for DocumentRepository."""
    return DocumentRepository(session)


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
StoreDep = Annotated[RecordStore, Depends(get_store)]
RepoDep = Annotated[DocumentRepository, Depends(get_repository)]
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]
