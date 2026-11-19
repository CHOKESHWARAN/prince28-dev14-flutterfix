import asyncio
from unittest.mock import AsyncMock, MagicMock

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


def test_repository_list_query_generation_and_pagination():
    session = AsyncMock()

    # Mock count query response
    count_res = MagicMock()
    count_res.scalar_one.return_value = 42

    # Mock docs query response
    sample_doc = Document(
        external_id="doc-001",
        title="Title 1",
        doc_type="widget",
        sha256="h1",
        metadata_={"category": "widget"},
    )
    docs_res = MagicMock()
    docs_res.scalars.return_value.all.return_value = [sample_doc]

    session.execute.side_effect = [count_res, docs_res]

    repo = DocumentRepository(session)
    items, total = asyncio.run(
        repo.list(q="button", limit=5, offset=10, filters={"doc_type": "widget"})
    )

    assert total == 42
    assert len(items) == 1
    assert items[0]["id"] == "doc-001"

    # Verify session.execute was called twice: once for count, once for query
    assert session.execute.call_count == 2
    count_call_stmt = str(session.execute.call_args_list[0][0][0])
    docs_call_stmt = str(session.execute.call_args_list[1][0][0])

    assert "count" in count_call_stmt.lower()

    # Check that doc_type column filter was included
    assert "documents.doc_type" in docs_call_stmt
    # Check that search query was included
    assert "lower(documents.title)" in docs_call_stmt.lower() or "like" in docs_call_stmt.lower()
    # Check limit and offset
    assert "LIMIT" in docs_call_stmt
    assert "OFFSET" in docs_call_stmt


def test_repository_list_jsonb_metadata_filtering():
    session = AsyncMock()

    count_res = MagicMock()
    count_res.scalar_one.return_value = 1

    sample_doc = Document(
        external_id="doc-002",
        title="Theme migration",
        doc_type="breaking_change",
        sha256="h2",
        metadata_={"category": "theming", "status": "deprecated"},
    )
    docs_res = MagicMock()
    docs_res.scalars.return_value.all.return_value = [sample_doc]

    session.execute.side_effect = [count_res, docs_res]

    repo = DocumentRepository(session)
    items, total = asyncio.run(repo.list(filters={"category": "theming"}))

    assert total == 1
    assert items[0]["id"] == "doc-002"

    docs_call_stmt = str(session.execute.call_args_list[1][0][0])
    # Check JSONB containment operator
    assert "@>" in docs_call_stmt


def test_repository_get_by_external_id_found():
    session = AsyncMock()

    sample_doc = Document(
        external_id="doc-100",
        title="Primary lookup",
        doc_type="guide",
        sha256="h100",
        metadata_={},
    )
    res = MagicMock()
    res.scalar_one_or_none.return_value = sample_doc
    session.execute.return_value = res

    repo = DocumentRepository(session)
    result = asyncio.run(repo.get("doc-100"))

    assert result is not None
    assert result["id"] == "doc-100"
    assert result["title"] == "Primary lookup"


def test_repository_get_by_topic_id_fallback():
    session = AsyncMock()

    # 1. Primary lookup returns None
    res1 = MagicMock()
    res1.scalar_one_or_none.return_value = None

    # 2. Topic lookup returns document
    sample_doc = Document(
        external_id="doc-200",
        title="Topic Fallback",
        doc_type="breaking_change",
        sha256="h200",
        metadata_={"topic_id": "flat-button"},
    )
    res2 = MagicMock()
    res2.scalars.return_value.first.return_value = sample_doc

    session.execute.side_effect = [res1, res2]

    repo = DocumentRepository(session)
    result = asyncio.run(repo.get("flat-button"))

    assert result is not None
    assert result["id"] == "doc-200"
    assert result["topic_id"] == "flat-button"


def test_repository_get_by_api_name_fallback():
    session = AsyncMock()

    # 1. Primary lookup returns None
    res1 = MagicMock()
    res1.scalar_one_or_none.return_value = None

    # 2. Topic lookup returns None
    res2 = MagicMock()
    res2.scalars.return_value.first.return_value = None

    # 3. API name lookup returns document
    sample_doc = Document(
        external_id="doc-300",
        title="API Fallback",
        doc_type="breaking_change",
        sha256="h300",
        metadata_={"api_name": "FlatButton"},
    )
    res3 = MagicMock()
    res3.scalars.return_value.first.return_value = sample_doc

    session.execute.side_effect = [res1, res2, res3]

    repo = DocumentRepository(session)
    result = asyncio.run(repo.get("FlatButton"))

    assert result is not None
    assert result["id"] == "doc-300"
    assert result["api_name"] == "FlatButton"


def test_repository_get_not_found():
    session = AsyncMock()

    res1 = MagicMock()
    res1.scalar_one_or_none.return_value = None

    res2 = MagicMock()
    res2.scalars.return_value.first.return_value = None

    res3 = MagicMock()
    res3.scalars.return_value.first.return_value = None

    session.execute.side_effect = [res1, res2, res3]

    repo = DocumentRepository(session)
    result = asyncio.run(repo.get("completely-unknown-id"))

    assert result is None
