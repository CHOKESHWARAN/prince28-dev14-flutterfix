"""Unit tests for background worker ingestion tasks (Step 6)."""

import hashlib
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from flutterfix.config import Settings
from flutterfix.db.models import Document, IngestItem
from flutterfix.workers.ingest import (
    process_ingest_item,
    resolve_download_url,
    resolve_github_raw_url,
    retrieve_file,
)


def test_resolve_github_raw_url():
    web_url = (
        "https://github.com/flutter/website/blob/HEAD/sites/docs/src/content/ui/widgets/index.md"
    )
    commit = "e6b465b615d34533d91174ffb76d1b3b765a625b"
    raw_url = resolve_github_raw_url(web_url, commit)
    expected = (
        "https://raw.githubusercontent.com/flutter/website/"
        f"{commit}/sites/docs/src/content/ui/widgets/index.md"
    )
    assert raw_url == expected


def test_resolve_download_url_git_and_http():
    # Git source with commit
    git_record = {
        "url": "https://github.com/flutter/website/blob/HEAD/test.md",
        "commit": "abc1234",
    }
    assert (
        resolve_download_url(git_record)
        == "https://raw.githubusercontent.com/flutter/website/abc1234/test.md"
    )

    # Standard HTTP source
    http_record = {"url": "https://docs.flutter.dev/ui"}
    assert resolve_download_url(http_record) == "https://docs.flutter.dev/ui"


@pytest.mark.asyncio
async def test_retrieve_file_from_local_disk():
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
        content = b"<html>Test local content</html>"
        f.write(content)
        temp_path = Path(f.name)

    sha = hashlib.sha256(content).hexdigest()
    record = {"path": str(temp_path), "sha256": sha}

    try:
        path, is_temp = await retrieve_file(record)
        assert path == temp_path
        assert is_temp is False
        assert path.read_bytes() == content
    finally:
        temp_path.unlink()


@pytest.mark.asyncio
async def test_retrieve_file_sha_mismatch_raises_error():
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
        f.write(b"content")
        temp_path = Path(f.name)

    # Fake expected SHA
    record = {"path": str(temp_path), "sha256": "wrong_sha256"}
    try:
        # Local file SHA doesn't match, so it falls back to remote URL which also fails or errors
        with pytest.raises((ValueError, httpx.HTTPError)):
            await retrieve_file(record)
    finally:
        temp_path.unlink()


@pytest.mark.asyncio
async def test_retrieve_file_remote_download():
    content = b"Remote downloaded markdown"
    sha = hashlib.sha256(content).hexdigest()
    record = {
        "url": "https://raw.githubusercontent.com/flutter/website/abc/test.md",
        "path": "non_existent_local.md",
        "sha256": sha,
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = content
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp

    path, is_temp = await retrieve_file(record, http_client=mock_client)
    assert is_temp is True
    assert path.read_bytes() == content
    path.unlink()


@pytest.mark.asyncio
async def test_process_ingest_item_idempotent_skip():
    # If Document already exists in DB, item should be marked skipped
    session = AsyncMock()
    mock_item = IngestItem(
        id=1,
        job_id="job1",
        record={"sha256": "f4571b83da2473b58087cbe6d31ebb5e8fd31ded197817cfabef490434167322"},
        status="queued",
        attempts=0,
    )
    session.get.return_value = mock_item

    mock_existing_doc = Document(
        external_id="f-f4571b83da2473b58087", pages=[MagicMock(), MagicMock()]
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_existing_doc
    session.execute.return_value = mock_result

    ctx = {
        "sessionmaker": MagicMock(return_value=session),
        "settings": Settings(app_env="ci"),
    }
    # Set context manager behavior on sessionmaker()
    session.__aenter__.return_value = session

    res = await process_ingest_item(ctx, item_id=1)
    assert res["status"] == "skipped"
    assert mock_item.status == "skipped"
    assert mock_item.pages == 2
