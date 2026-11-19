import asyncio
import json
import tempfile
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

import scripts.load_db as loader_module
from flutterfix.db.models import Document, Page
from scripts.load_db import compute_sha256, load_sample_records, parse_date


def test_compute_sha256_canonical_ordering():
    # Identical content with different key order must yield the exact same SHA-256
    record_a = {"b": 2, "a": 1, "c": [1, 2]}
    record_b = {"a": 1, "c": [1, 2], "b": 2}
    assert compute_sha256(record_a) == compute_sha256(record_b)


def test_compute_sha256_distinct_changes():
    record_a = {"id": "1", "title": "A"}
    record_b = {"id": "1", "title": "B"}
    assert compute_sha256(record_a) != compute_sha256(record_b)


def test_parse_date_handling():
    assert parse_date("2024-05-14") == date(2024, 5, 14)
    assert parse_date(date(2023, 1, 1)) == date(2023, 1, 1)
    assert parse_date(None) is None
    assert parse_date("") is None
    assert parse_date("not-a-date") is None
    assert parse_date(12345) is None


def test_loader_missing_file_raises():
    missing_path = Path("non_existent_records_file_xyz.json")
    with pytest.raises(FileNotFoundError):
        asyncio.run(load_sample_records(data_path=missing_path))


def test_loader_invalid_json_format_raises():
    with tempfile.TemporaryDirectory() as tmp_dir:
        invalid_file = Path(tmp_dir) / "invalid.json"
        invalid_file.write_text('{"not": "a list"}', encoding="utf-8")
        with pytest.raises(ValueError, match="must contain a list of records"):
            asyncio.run(load_sample_records(data_path=invalid_file))


def test_loader_new_document_insertion(monkeypatch):
    data = [
        {
            "id": "101",
            "title": "New Migration Guide",
            "page": "https://docs.flutter.dev/new",
            "category": "widget",
            "published_on": "2024-03-01",
            "description": "Details about new migration.",
        }
    ]

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    @asynccontextmanager
    async def mock_begin():
        yield

    mock_session.begin = mock_begin

    @asynccontextmanager
    async def mock_session_local():
        yield mock_session

    monkeypatch.setattr(loader_module, "AsyncSessionLocal", mock_session_local)

    with tempfile.TemporaryDirectory() as tmp_dir:
        sample_file = Path(tmp_dir) / "sample.json"
        sample_file.write_text(json.dumps(data), encoding="utf-8")

        total, inserted, updated, unchanged = asyncio.run(
            load_sample_records(data_path=sample_file)
        )

    assert total == 1
    assert inserted == 1
    assert updated == 0
    assert unchanged == 0
    assert mock_session.add.called
    added_doc = mock_session.add.call_args[0][0]
    assert added_doc.external_id == "101"
    assert added_doc.doc_type == "widget"
    assert added_doc.published_on == date(2024, 3, 1)


def test_loader_unchanged_record_detection(monkeypatch):
    record = {"id": "101", "title": "Stable Widget", "category": "widget"}
    sha = compute_sha256(record)

    existing_doc = Document(
        external_id="101",
        title="Stable Widget",
        doc_type="widget",
        sha256=sha,
        metadata_=record,
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [existing_doc]
    mock_session.execute.return_value = mock_result

    @asynccontextmanager
    async def mock_begin():
        yield

    mock_session.begin = mock_begin

    @asynccontextmanager
    async def mock_session_local():
        yield mock_session

    monkeypatch.setattr(loader_module, "AsyncSessionLocal", mock_session_local)

    with tempfile.TemporaryDirectory() as tmp_dir:
        sample_file = Path(tmp_dir) / "sample.json"
        sample_file.write_text(json.dumps([record]), encoding="utf-8")

        total, inserted, updated, unchanged = asyncio.run(
            load_sample_records(data_path=sample_file)
        )

    assert total == 1
    assert inserted == 0
    assert updated == 0
    assert unchanged == 1
    assert not mock_session.add.called


def test_loader_changed_record_updates(monkeypatch):
    old_record = {"id": "101", "title": "Old Title", "category": "widget"}
    old_sha = compute_sha256(old_record)

    existing_doc = Document(
        external_id="101",
        title="Old Title",
        doc_type="widget",
        sha256=old_sha,
        metadata_=old_record,
    )
    existing_doc.pages = [Page(page_no=1, text="Old page text")]

    new_record = {"id": "101", "title": "Updated Title", "category": "widget"}

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [existing_doc]
    mock_session.execute.return_value = mock_result

    @asynccontextmanager
    async def mock_begin():
        yield

    mock_session.begin = mock_begin

    @asynccontextmanager
    async def mock_session_local():
        yield mock_session

    monkeypatch.setattr(loader_module, "AsyncSessionLocal", mock_session_local)

    with tempfile.TemporaryDirectory() as tmp_dir:
        sample_file = Path(tmp_dir) / "sample.json"
        sample_file.write_text(json.dumps([new_record]), encoding="utf-8")

        total, inserted, updated, unchanged = asyncio.run(
            load_sample_records(data_path=sample_file)
        )

    assert total == 1
    assert inserted == 0
    assert updated == 1
    assert unchanged == 0
    assert existing_doc.title == "Updated Title"
    assert existing_doc.sha256 == compute_sha256(new_record)


def test_loader_duplicate_ids_in_batch(monkeypatch):
    data = [
        {"id": "101", "title": "Record First", "category": "widget"},
        {"id": "101", "title": "Record Duplicate", "category": "widget"},
    ]

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    @asynccontextmanager
    async def mock_begin():
        yield

    mock_session.begin = mock_begin

    @asynccontextmanager
    async def mock_session_local():
        yield mock_session

    monkeypatch.setattr(loader_module, "AsyncSessionLocal", mock_session_local)

    with tempfile.TemporaryDirectory() as tmp_dir:
        sample_file = Path(tmp_dir) / "sample.json"
        sample_file.write_text(json.dumps(data), encoding="utf-8")

        total, inserted, updated, unchanged = asyncio.run(
            load_sample_records(data_path=sample_file)
        )

    assert total == 2
    # Only 1 unique document inserted; duplicate ID skipped
    assert inserted == 1
    assert mock_session.add.call_count == 1


def test_loader_missing_optional_fields(monkeypatch):
    # Missing title, page, published_on, licence, doc_type, description
    minimal_record = {"id": "102"}

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    @asynccontextmanager
    async def mock_begin():
        yield

    mock_session.begin = mock_begin

    @asynccontextmanager
    async def mock_session_local():
        yield mock_session

    monkeypatch.setattr(loader_module, "AsyncSessionLocal", mock_session_local)

    with tempfile.TemporaryDirectory() as tmp_dir:
        sample_file = Path(tmp_dir) / "sample.json"
        sample_file.write_text(json.dumps([minimal_record]), encoding="utf-8")

        total, inserted, updated, unchanged = asyncio.run(
            load_sample_records(data_path=sample_file)
        )

    assert total == 1
    assert inserted == 1
    added_doc = mock_session.add.call_args[0][0]
    assert added_doc.title == "Record 102"
    assert added_doc.doc_type == "breaking_change"
    assert added_doc.licence == "CC-BY-4.0"
    assert added_doc.published_on is None
    assert len(added_doc.pages) == 1


def test_loader_transaction_rollback_on_error(monkeypatch):
    data = [{"id": "103", "title": "Crash Record"}]

    mock_session = AsyncMock()

    @asynccontextmanager
    async def mock_failing_begin():
        raise RuntimeError("Database transaction aborted unexpectedly")
        yield

    mock_session.begin = mock_failing_begin

    @asynccontextmanager
    async def mock_session_local():
        yield mock_session

    monkeypatch.setattr(loader_module, "AsyncSessionLocal", mock_session_local)

    with tempfile.TemporaryDirectory() as tmp_dir:
        sample_file = Path(tmp_dir) / "sample.json"
        sample_file.write_text(json.dumps(data), encoding="utf-8")

        with pytest.raises(RuntimeError, match="Database transaction aborted"):
            asyncio.run(load_sample_records(data_path=sample_file))
