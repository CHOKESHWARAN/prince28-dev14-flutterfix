"""Document ingestion background worker task."""

import asyncio
import contextlib
import hashlib
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from flutterfix.config import Settings
from flutterfix.db.models import Document, IngestItem
from flutterfix.ingest.parse import ParseError, parse_file
from flutterfix.ingest.store import document_id, save_document
from flutterfix.llm.doc_meta import DocMeta
from flutterfix.llm.extract import extract
from flutterfix.llm.gateway import LLMGateway
from flutterfix.llm.prompts import latest_prompt


def resolve_github_raw_url(url: str, commit: str) -> str:
    """Convert a GitHub web view URL to an exact commit-pinned raw content URL."""
    # Example: https://github.com/flutter/website/blob/HEAD/sites/docs/...
    # Target:  https://raw.githubusercontent.com/flutter/website/{commit}/sites/docs/...
    parsed = urlparse(url)
    if "github.com" in parsed.netloc:
        parts = [p for p in parsed.path.split("/") if p]
        # parts: [owner, repo, "blob", branch_or_head, *path_parts]
        if len(parts) >= 5 and parts[2] == "blob":
            owner, repo = parts[0], parts[1]
            path_part = "/".join(parts[4:])
            return f"https://raw.githubusercontent.com/{owner}/{repo}/{commit}/{path_part}"
    return url


def resolve_download_url(record: dict[str, Any]) -> str:
    """Resolve the best remote URL to download document content."""
    url = record.get("url", "")
    commit = record.get("commit")
    if commit and "github.com" in url:
        return resolve_github_raw_url(url, commit)
    return url


async def retrieve_file(
    record: dict[str, Any],
    http_client: httpx.AsyncClient | None = None,
) -> tuple[Path, bool]:
    """Retrieve document file either from local filesystem or by downloading.

    Returns (path_to_file, is_temporary).
    """
    local_path = Path(record.get("path", ""))
    expected_sha = record.get("sha256", "")

    # 1. Check local file on disk
    if local_path.is_file():
        content = local_path.read_bytes()
        actual_sha = hashlib.sha256(content).hexdigest()
        if not expected_sha or actual_sha == expected_sha:
            return local_path, False

    # 2. Download from remote URL
    url = resolve_download_url(record)
    client = http_client or httpx.AsyncClient(timeout=30.0)
    should_close_client = http_client is None
    try:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        content = resp.content
    finally:
        if should_close_client:
            await client.aclose()

    # Verify SHA-256
    actual_sha = hashlib.sha256(content).hexdigest()
    if expected_sha and actual_sha != expected_sha:
        raise ValueError(
            f"SHA-256 verification failed for {url}. Expected {expected_sha}, got {actual_sha}"
        )

    # Write to a temporary file preserving extension for parse_file
    suffix = local_path.suffix or Path(urlparse(url).path).suffix or ".html"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        temp_file.write(content)
        temp_path_str = temp_file.name
    return Path(temp_path_str), True


async def process_ingest_item(ctx: dict[str, Any], item_id: int) -> dict[str, Any]:
    """ARQ task: process a single ingestion item."""
    sessionmaker = ctx["sessionmaker"]
    gateway: LLMGateway | None = ctx.get("gateway")
    settings: Settings = ctx["settings"]
    http_client: httpx.AsyncClient | None = ctx.get("http_client")
    max_tries = settings.ingest_max_tries

    async with sessionmaker() as session:
        item = await session.get(IngestItem, item_id)
        if not item:
            return {"status": "not_found", "item_id": item_id}

        # Skip already finished items
        if item.status in ("done", "skipped"):
            return {"status": item.status, "item_id": item_id}

        # Mark as running
        item.status = "running"
        item.attempts += 1
        item.updated_at = func.now()
        await session.commit()

        record = dict(item.record)
        expected_sha = record.get("sha256", "")
        doc_id = document_id(expected_sha) if expected_sha else f"doc_{item_id}"

        # Idempotency check: does document already exist in documents table?
        stmt = (
            select(Document)
            .options(selectinload(Document.pages))
            .where(Document.external_id == doc_id)
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            item.status = "skipped"
            item.pages = len(existing.pages)
            item.updated_at = func.now()
            await session.commit()
            return {"status": "skipped", "item_id": item_id, "pages": item.pages}

        temp_path: Path | None = None
        try:
            # 1. Retrieve file (local or remote)
            file_path, is_temp = await retrieve_file(record, http_client)
            if is_temp:
                temp_path = file_path

            # 2. Parse document
            parsed = await asyncio.to_thread(parse_file, file_path)

            # 3. Extract metadata with LLM if gateway is configured
            extracted_metadata = {}
            if gateway:
                version, prompt = latest_prompt("extract", directory=settings.prompts_dir)
                title = parsed.title or record.get("title") or file_path.stem
                text = "\n\n".join(p.text for p in parsed.pages[:3])[:6000]
                try:
                    res = await extract(gateway, DocMeta, prompt, version, title, text)
                    if res.record:
                        extracted_metadata = res.record.model_dump(mode="json")
                except Exception:
                    # Non-fatal for document insertion; metadata can be repaired later
                    pass

                # Pace model requests
                if settings.ingest_rpm > 0:
                    await asyncio.sleep(60.0 / settings.ingest_rpm)

            # 4. Save document and pages
            doc = await save_document(session, record, parsed)
            if doc and extracted_metadata:
                doc.metadata_ = {**doc.metadata_, **extracted_metadata}
                await session.commit()

            # 5. Mark item done
            item.status = "done"
            item.pages = len(parsed.pages)
            item.error = ""
            item.updated_at = func.now()
            await session.commit()
            return {"status": "done", "item_id": item_id, "pages": item.pages}

        except Exception as exc:
            err_msg = str(exc)[:500]
            item.error = err_msg
            item.updated_at = func.now()

            # Determine whether error is permanent or retryable
            is_permanent = isinstance(exc, (ParseError, ValueError)) or item.attempts >= max_tries
            item.status = "failed" if is_permanent else "queued"
            await session.commit()

            if not is_permanent:
                raise  # Let ARQ handle retry
            return {"status": "failed", "item_id": item_id, "error": err_msg}

        finally:
            if temp_path and temp_path.exists():
                with contextlib.suppress(OSError):
                    temp_path.unlink()
