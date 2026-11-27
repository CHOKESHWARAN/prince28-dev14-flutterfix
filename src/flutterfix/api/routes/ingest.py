"""Background ingestion endpoints (Day 10)."""

import json
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from flutterfix.api.deps import get_app_settings, get_session
from flutterfix.config import Settings
from flutterfix.db.models import Document, IngestItem, IngestJob, ParseFailure
from flutterfix.ingest.store import document_id
from flutterfix.workers.queue import enqueue_ingest_item, get_redis_pool

router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestRequest(BaseModel):
    limit: int = Field(default=10, ge=1, le=1000)
    source: str | None = None
    retry_failed: bool = False


def verify_admin_token(
    settings: Annotated[Settings, Depends(get_app_settings)],
    x_admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
) -> str:
    """Authenticate request using X-Admin-Token."""
    expected = settings.admin_token.get_secret_value()
    if not x_admin_token or x_admin_token != expected:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing X-Admin-Token header.",
        )
    return x_admin_token


def load_manifest_records(manifest_file: Any) -> list[dict[str, Any]]:
    """Read downloaded records from the manifest."""
    from pathlib import Path

    path = Path(manifest_file)
    if not path.is_file():
        return []

    records = []
    seen = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("status") == "downloaded":
            url = item.get("url")
            if url and url not in seen:
                seen.add(url)
                records.append(item)
    return records


@router.post("", status_code=202)
async def trigger_ingest(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    token: Annotated[str, Depends(verify_admin_token)],
    payload: IngestRequest | None = None,
    limit: Annotated[int | None, Query(ge=1, le=1000)] = None,
    source: Annotated[str | None, Query()] = None,
    retry_failed: Annotated[bool | None, Query()] = None,
) -> dict[str, Any]:
    """Start a batch document ingestion job in the background."""
    eff_limit = limit or (payload.limit if payload else 10)
    eff_source = source or (payload.source if payload else None)
    eff_retry = (
        retry_failed if retry_failed is not None else (payload.retry_failed if payload else False)
    )

    # 1. Load manifest records
    all_records = load_manifest_records(settings.manifest_file)
    if eff_source:
        all_records = [r for r in all_records if r.get("source") == eff_source]

    # 2. Filter out already ingested documents
    existing_docs = set(
        await session.scalars(select(Document.external_id).where(Document.doc_type != "record"))
    )
    failed_paths = set()
    if not eff_retry:
        failed_paths = set(await session.scalars(select(ParseFailure.path)))

    eligible = []
    for r in all_records:
        ext_id = document_id(r.get("sha256", ""))
        if ext_id in existing_docs:
            continue
        if r.get("path") in failed_paths:
            continue
        eligible.append(r)

    selected = eligible[:eff_limit]

    # 3. Create IngestJob and IngestItems
    job = IngestJob(
        id=uuid.uuid4().hex,
        requested=len(selected),
    )
    session.add(job)

    items = [
        IngestItem(
            job_id=job.id,
            record=rec,
            status="queued",
            attempts=0,
            pages=0,
        )
        for rec in selected
    ]
    session.add_all(items)
    await session.commit()
    await session.refresh(job)

    # 4. Push items to Redis via ARQ
    redis_pool = getattr(request.app.state, "redis_pool", None)
    if redis_pool is None:
        try:
            redis_pool = await get_redis_pool(settings.redis_url)
            request.app.state.redis_pool = redis_pool
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Redis queue unavailable: {exc}",
            ) from exc

    try:
        for it in items:
            await enqueue_ingest_item(redis_pool, it.id)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to enqueue ingestion items into Redis: {exc}",
        ) from exc

    response.status_code = 202
    return {
        "job_id": job.id,
        "status": "accepted",
        "queued": len(items),
        "total_requested": job.requested,
    }


@router.get("/dead-letter")
async def get_dead_letter(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Retrieve permanently failed documents (dead-letter queue)."""
    stmt = (
        select(IngestItem)
        .where(IngestItem.status == "failed")
        .order_by(IngestItem.updated_at.desc())
    )
    results = (await session.execute(stmt)).scalars().all()

    items = [
        {
            "id": item.id,
            "job_id": item.job_id,
            "url": item.record.get("url"),
            "path": item.record.get("path"),
            "error": item.error,
            "attempts": item.attempts,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }
        for item in results
    ]
    return {
        "total": len(items),
        "items": items,
    }


@router.get("/{job_id}")
async def get_ingest_job_progress(
    job_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Get the progress and status counts for an ingestion job."""
    job = await session.get(IngestJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"No ingestion job with id '{job_id}'.")

    # Group counts by status
    stmt = (
        select(IngestItem.status, func.count(IngestItem.id), func.sum(IngestItem.pages))
        .where(IngestItem.job_id == job_id)
        .group_by(IngestItem.status)
    )
    rows = (await session.execute(stmt)).all()

    counts = {"queued": 0, "running": 0, "done": 0, "skipped": 0, "failed": 0}
    total_pages = 0
    for status_str, count_num, pages_num in rows:
        counts[status_str] = count_num
        if pages_num:
            total_pages += int(pages_num)

    return {
        "job_id": job.id,
        "total_requested": job.requested,
        "queued": counts.get("queued", 0),
        "running": counts.get("running", 0),
        "done": counts.get("done", 0),
        "skipped": counts.get("skipped", 0),
        "failed": counts.get("failed", 0),
        "pages": total_pages,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }
