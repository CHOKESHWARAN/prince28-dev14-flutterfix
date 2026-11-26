import pytest
from pydantic import ValidationError

from flutterfix.config import Settings


def test_health_is_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_sha_fallback_to_render_git_commit():
    from fastapi.testclient import TestClient

    from flutterfix.api.main import create_app

    test_settings = Settings(
        app_env="local",
        git_sha="local",
        render_git_commit="396aeb7510f61bc9f2e3f97300ec76cbfa4f5031",
        _env_file=None,
    )
    assert test_settings.git_sha == "396aeb7510f61bc9f2e3f97300ec76cbfa4f5031"

    app = create_app(settings=test_settings)
    c = TestClient(app)
    resp = c.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "396aeb7510f61bc9f2e3f97300ec76cbfa4f5031"
    assert data["commit"] == "396aeb7510f61bc9f2e3f97300ec76cbfa4f5031"


def test_settings_sha_fallback_matrix():
    # 1. 'local' falls back to render_git_commit
    s1 = Settings(app_env="local", git_sha="local", render_git_commit="sha123", _env_file=None)
    assert s1.git_sha == "sha123"

    # 2. 'dev' falls back to render_git_commit
    s2 = Settings(app_env="local", git_sha="dev", render_git_commit="sha123", _env_file=None)
    assert s2.git_sha == "sha123"

    # 3. empty string falls back to render_git_commit
    s3 = Settings(app_env="local", git_sha="", render_git_commit="sha123", _env_file=None)
    assert s3.git_sha == "sha123"

    # 4. Explicit non-local/dev SHA is preserved
    s4 = Settings(app_env="local", git_sha="customsha", render_git_commit="sha123", _env_file=None)
    assert s4.git_sha == "customsha"

    # 5. Without render_git_commit, default is preserved
    s5 = Settings(app_env="local", git_sha="dev", render_git_commit=None, _env_file=None)
    assert s5.git_sha == "dev"


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


def test_doc_type_filtering(client):
    response = client.get("/v1/documents", params={"doc_type": "widget"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == "001"
    assert items[0]["doc_type"] == "widget"


def test_extracted_metadata_filtering(client):
    # Test doc_kind
    res = client.get("/v1/documents", params={"doc_kind": "guideline", "limit": 3})
    assert res.status_code == 200
    assert len(res.json()["items"]) == 1
    assert res.json()["items"][0]["id"] == "001"

    # Test language
    res = client.get("/v1/documents", params={"language": "en", "limit": 3})
    assert res.status_code == 200
    assert len(res.json()["items"]) == 2

    # Test array field matching (page contains 'migration')
    res = client.get("/v1/documents", params={"page": "migration"})
    assert res.status_code == 200
    assert len(res.json()["items"]) == 1
    assert res.json()["items"][0]["id"] == "001"


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
