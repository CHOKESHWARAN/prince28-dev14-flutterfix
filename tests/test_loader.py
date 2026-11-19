import asyncio
import tempfile
from datetime import date
from pathlib import Path

import pytest

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
