import asyncio
from unittest.mock import AsyncMock

import pytest

from flutterfix.db.models import Document
from flutterfix.db.repository import ALLOWED_FILTER_KEYS, DocumentRepository, InvalidFilterError


def test_repository_to_dict_conversion():
    doc = Document(
        external_id="button-001",
        title="FlatButton Migration",
        source_url="https://docs.flutter.dev/buttons",
        licence="CC-BY-4.0",
        doc_type="breaking_change",
        sha256="hash123",
        metadata_={
            "topic_id": "flat-button",
            "category": "widget",
            "deprecated_in": "1.20",
        },
    )

    data = DocumentRepository.to_dict(doc)
    assert data["id"] == "button-001"
    assert data["title"] == "FlatButton Migration"
    assert data["source_url"] == "https://docs.flutter.dev/buttons"
    assert data["page"] == "https://docs.flutter.dev/buttons"
    assert data["breaking_change_url"] == "https://docs.flutter.dev/buttons"
    assert data["licence"] == "CC-BY-4.0"
    assert data["doc_type"] == "breaking_change"
    assert data["topic_id"] == "flat-button"
    assert data["category"] == "widget"


def test_repository_invalid_filter_rejected():
    session = AsyncMock()
    repo = DocumentRepository(session)

    with pytest.raises(InvalidFilterError, match="Invalid filter parameter 'malicious_key'"):
        asyncio.run(repo.list(filters={"malicious_key": "some_value"}))


def test_allowed_filter_keys_integrity():
    required_keys = {"category", "status", "api_name", "topic_id", "doc_type"}
    assert required_keys.issubset(ALLOWED_FILTER_KEYS)
