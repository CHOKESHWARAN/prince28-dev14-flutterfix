"""Unit test configuration and fixtures for FlutterFix."""

import os

os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT", "1")

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from flutterfix.api.deps import (
    get_db_session,
    get_gateway,
    get_repository,
    get_usage_repo,
)
from flutterfix.api.main import create_app
from flutterfix.config import Settings
from flutterfix.db.repository import ALLOWED_FILTER_KEYS, InvalidFilterError
from flutterfix.llm.gateway import FakeLLM, LLMGateway

SAMPLE_DOCS = [
    {
        "id": "001",
        "title": "Alpha guideline",
        "topic_id": "flat-button",
        "category": "widget",
        "doc_type": "widget",
        "doc_kind": "guideline",
        "language": "en",
        "year": 2023,
        "page": ["buttons", "migration"],
        "topics": ["buttons", "styling"],
    },
    {
        "id": "002",
        "title": "Beta circular",
        "topic_id": "will-pop-scope",
        "category": "navigation",
        "doc_type": "navigation",
        "doc_kind": "circular",
        "language": "en",
        "year": 2024,
        "page": ["navigation"],
        "topics": ["navigation"],
    },
    {
        "id": "003",
        "title": "Gamma notice",
        "topic_id": "sound-null-safety",
        "category": "language",
        "doc_type": "language",
        "doc_kind": "notice",
        "language": "es",
        "year": 2025,
        "page": ["null-safety"],
        "topics": ["dart"],
    },
]


class FakeDocumentRepository:
    """In-memory fake repository for unit tests that run without a real database."""

    def __init__(self, docs: list[dict[str, Any]] | None = None) -> None:
        self.docs = list(docs or SAMPLE_DOCS)

    async def list(
        self,
        q: str | None = None,
        limit: int = 20,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        results = list(self.docs)

        if filters:
            for k, v in filters.items():
                if k not in ALLOWED_FILTER_KEYS:
                    raise InvalidFilterError(f"Invalid filter parameter '{k}'")

                def _matches(doc_val: Any, expected: Any) -> bool:
                    if doc_val is None:
                        return False
                    if isinstance(doc_val, list):
                        return str(expected) in [str(x) for x in doc_val]
                    return str(doc_val) == str(expected)

                results = [d for d in results if _matches(d.get(k), v)]

        if q:
            needle = q.lower()
            results = [
                d
                for d in results
                if needle in str(d.get("title", "")).lower()
                or any(needle in str(val).lower() for val in d.values())
            ]

        total = len(results)
        paginated = results[offset : offset + limit]
        return paginated, total

    async def get(self, external_id: str) -> dict[str, Any] | None:
        needle = external_id.lower().replace("_", "-")
        for d in self.docs:
            if d.get("id") == external_id or d.get("topic_id") == needle:
                return d
        return None


@pytest.fixture
def fake_repo():
    return FakeDocumentRepository()


@pytest.fixture
def mock_session():
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 1
    mock_result.scalar.return_value = 20
    session.execute.return_value = mock_result
    return session


class FakeUsage:
    async def by_day(self, days=7):
        return [
            {
                "day": "2026-11-25",
                "calls": 3,
                "errors": 1,
                "fallbacks": 1,
                "tokens_in": 300,
                "tokens_out": 120,
                "cost_inr": 0.0642,
            }
        ]


@pytest.fixture
def llm():
    return FakeLLM()


@pytest.fixture
def test_app(fake_repo, mock_session, llm):
    settings = Settings(app_env="ci")
    app = create_app(settings)
    app.dependency_overrides[get_repository] = lambda: fake_repo
    app.dependency_overrides[get_db_session] = lambda: mock_session
    app.dependency_overrides[get_gateway] = lambda: LLMGateway([llm])
    app.dependency_overrides[get_usage_repo] = lambda: FakeUsage()
    return app


@pytest.fixture
def client(test_app):
    with TestClient(test_app) as test_client:
        yield test_client


@pytest.fixture
def failing_db_client(fake_repo):
    """Client configured with a failing database session to test 503 readiness."""
    failing_session = AsyncMock()
    failing_session.execute.side_effect = ConnectionRefusedError("Database unavailable")

    settings = Settings(app_env="ci")
    app = create_app(settings)
    app.dependency_overrides[get_repository] = lambda: fake_repo
    app.dependency_overrides[get_db_session] = lambda: failing_session

    with TestClient(app) as test_client:
        yield test_client
