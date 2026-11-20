"""Unit tests for smoke test script logic."""

import io
import json
import urllib.error
from unittest.mock import MagicMock, patch

from scripts.smoke import check_documents, check_health, check_ready


def make_response(status: int, data: dict):
    resp = MagicMock()
    resp.status = status
    body_bytes = json.dumps(data).encode("utf-8")
    resp.read.return_value = body_bytes
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = None
    return resp


def test_check_health_success():
    mock_resp = make_response(
        200, {"status": "ok", "commit": "sha123", "app": "flutterfix", "env": "production"}
    )
    with patch("urllib.request.urlopen", return_value=mock_resp):
        ok, msg = check_health("https://example.com", expected_sha="sha123")
        assert ok is True
        assert "HTTP 200 OK" in msg


def test_check_health_sha_mismatch():
    mock_resp = make_response(
        200, {"status": "ok", "commit": "old_sha", "app": "flutterfix", "env": "production"}
    )
    with patch("urllib.request.urlopen", return_value=mock_resp):
        ok, msg = check_health("https://example.com", expected_sha="new_sha")
        assert ok is False
        assert "SHA mismatch" in msg


def test_check_health_http_error():
    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.HTTPError(
            "https://example.com/health", 500, "Error", {}, io.BytesIO()
        ),
    ):
        ok, msg = check_health("https://example.com")
        assert ok is False
        assert "Request failed" in msg


def test_check_ready_success():
    mock_resp = make_response(
        200, {"status": "ready", "checks": {"database": True, "records_loaded": True}}
    )
    with patch("urllib.request.urlopen", return_value=mock_resp):
        ok, msg = check_ready("https://example.com")
        assert ok is True
        assert "status: ready" in msg


def test_check_ready_database_failed():
    mock_resp = make_response(
        200, {"status": "not_ready", "checks": {"database": False, "records_loaded": False}}
    )
    with patch("urllib.request.urlopen", return_value=mock_resp):
        ok, msg = check_ready("https://example.com")
        assert ok is False


def test_check_documents_success():
    mock_resp = make_response(
        200, {"total": 20, "items": [{"id": "001", "title": "Widget Migration"}]}
    )
    with patch("urllib.request.urlopen", return_value=mock_resp):
        ok, msg = check_documents("https://example.com")
        assert ok is True
        assert "total records: 20" in msg


def test_check_documents_empty():
    mock_resp = make_response(200, {"total": 0, "items": []})
    with patch("urllib.request.urlopen", return_value=mock_resp):
        ok, msg = check_documents("https://example.com")
        assert ok is False
        assert "Expected at least 1 item" in msg
