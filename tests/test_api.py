import pytest
from pydantic import ValidationError

from flutterfix.config import Settings


def test_health_is_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_when_records_loaded(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["checks"]["database"] is True
    assert response.json()["checks"]["records_loaded"] is True


def test_ready_is_503_when_database_unavailable(failing_db_client):
    response = failing_db_client.get("/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"]["database"] is False


def test_list_documents_paginates(client):
    response = client.get("/v1/documents", params={"limit": 2})
    body = response.json()
    assert response.status_code == 200
    assert body["total"] == 3
    assert len(body["items"]) == 2


def test_search_filters_records(client):
    response = client.get("/v1/documents", params={"q": "beta"})
    assert [record["id"] for record in response.json()["items"]] == ["002"]


def test_metadata_filtering(client):
    response = client.get("/v1/documents", params={"category": "widget"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == "001"


def test_invalid_filter_name_is_400(client):
    response = client.get("/v1/documents", params={"unknown_filter": "value"})
    assert response.status_code == 400
    assert "Invalid filter parameter" in response.json()["detail"]


def test_get_document_found(client):
    response = client.get("/v1/documents/001")
    assert response.status_code == 200
    assert response.json()["title"] == "Alpha guideline"


def test_missing_document_is_problem_details(client):
    response = client.get("/v1/documents/999")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["status"] == 404
    assert body["title"] == "Not Found"
    assert body["request_id"] == response.headers["X-Request-ID"]


def test_bad_limit_is_422_problem(client):
    response = client.get("/v1/documents", params={"limit": 0})
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["errors"][0]["field"] == "query.limit"


def test_request_id_is_echoed(client):
    response = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert response.headers["X-Request-ID"] == "abc123"


def test_app_refuses_to_start_without_app_env(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
