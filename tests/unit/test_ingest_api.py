"""Unit tests for background ingestion API endpoints."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from flutterfix.api.deps import get_session
from flutterfix.api.main import create_app
from flutterfix.config import Settings


@pytest.fixture
def mock_db():
    session = AsyncMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_res.all.return_value = []
    session.execute.return_value = mock_res
    session.scalars.return_value = []
    session.get.return_value = None
    return session


@pytest.fixture
def api_client(mock_db):
    settings = Settings(
        app_env="ci",
        admin_token="test-secret-token",
        _env_file=None,
    )
    app = create_app(settings)
    app.dependency_overrides[get_session] = lambda: mock_db
    app.state.redis_pool = AsyncMock()
    app.state.redis_pool.enqueue_job = AsyncMock(return_value=MagicMock(job_id="test_job_1"))
    with TestClient(app) as client:
        yield client


def test_ingest_post_unauthorized_without_token(api_client):
    res = api_client.post("/v1/ingest", json={"limit": 5})
    assert res.status_code == 401
    assert "Invalid or missing X-Admin-Token" in res.json()["detail"]


def test_ingest_post_unauthorized_with_wrong_token(api_client):
    res = api_client.post(
        "/v1/ingest",
        json={"limit": 5},
        headers={"X-Admin-Token": "wrong-token"},
    )
    assert res.status_code == 401


def test_ingest_post_success(api_client):
    # Mock session
    mock_session = AsyncMock()
    mock_session.scalars.return_value = []  # no existing docs or parse failures

    api_client.app.dependency_overrides = {
        **api_client.app.dependency_overrides,
    }

    res = api_client.post(
        "/v1/ingest",
        json={"limit": 3},
        headers={"X-Admin-Token": "test-secret-token"},
    )
    assert res.status_code == 202
    data = res.json()
    assert "job_id" in data
    assert data["status"] == "accepted"
    assert data["queued"] >= 0


def test_ingest_get_job_not_found(api_client):
    res = api_client.get("/v1/ingest/non_existent_job_123")
    assert res.status_code == 404
    assert "No ingestion job with id" in res.json()["detail"]


def test_ingest_dead_letter(api_client):
    res = api_client.get("/v1/ingest/dead-letter")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)
