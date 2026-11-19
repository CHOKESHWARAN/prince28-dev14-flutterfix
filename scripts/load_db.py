"""Idempotent data loader: imports data/sample_records.json into PostgreSQL."""

import asyncio
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from flutterfix.config import get_settings
from flutterfix.db.models import Document, Page
from flutterfix.db.session import AsyncSessionLocal, dispose_engine


def compute_sha256(record: dict[str, Any]) -> str:
    """Generate SHA-256 fingerprint from canonical JSON representation."""
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_date(value: Any) -> date | None:
    """Safely parse ISO date strings or date objects."""
    if not value:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except (ValueError, TypeError):
            return None
    return None


async def load_sample_records(data_path: Path | None = None) -> tuple[int, int, int, int]:
    """Load records into PostgreSQL idempotently in a single transaction."""
    settings = get_settings()
    path = data_path or settings.data_file

    if not path.exists():
        raise FileNotFoundError(f"Records file not found: {path}")

    raw_data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_data, list):
        raise ValueError("Data file must contain a list of records")

    inserted = 0
    updated = 0
    unchanged = 0
    total = len(raw_data)

    async with AsyncSessionLocal() as session, session.begin():
        # Query existing documents keyed by external_id
        stmt = select(Document).options(selectinload(Document.pages))
        result = await session.execute(stmt)
        existing_map: dict[str, Document] = {doc.external_id: doc for doc in result.scalars().all()}

        seen_in_batch: set[str] = set()

        for row in raw_data:
            if not isinstance(row, dict) or "id" not in row:
                continue

            external_id = str(row.get("id"))
            if external_id in seen_in_batch:
                continue
            seen_in_batch.add(external_id)

            sha = compute_sha256(row)

            title = row.get("title") or row.get("topic") or f"Record {external_id}"
            source_url = row.get("page") or row.get("breaking_change_url")
            licence = row.get("licence") or row.get("license") or "CC-BY-4.0"
            doc_type = row.get("doc_type") or row.get("category") or "breaking_change"
            published_on = parse_date(row.get("published_on") or row.get("date"))
            page_text = row.get("description") or title

            # Metadata contains all record attributes for JSONB filtering
            metadata_dict = dict(row)

            if external_id not in existing_map:
                # New record: insert document and initial page
                doc = Document(
                    external_id=external_id,
                    title=title,
                    source_url=source_url,
                    licence=licence,
                    doc_type=doc_type,
                    published_on=published_on,
                    sha256=sha,
                    metadata_=metadata_dict,
                )
                doc.pages.append(Page(page_no=1, text=page_text))
                session.add(doc)
                inserted += 1
                existing_map[external_id] = doc
            else:
                doc = existing_map[external_id]
                if doc.sha256 != sha:
                    # Modified record: update document fields and page text
                    doc.title = title
                    doc.source_url = source_url
                    doc.licence = licence
                    doc.doc_type = doc_type
                    doc.published_on = published_on
                    doc.sha256 = sha
                    doc.metadata_ = metadata_dict

                    if doc.pages:
                        doc.pages[0].text = page_text
                    else:
                        doc.pages.append(Page(page_no=1, text=page_text))

                    updated += 1
                else:
                    unchanged += 1

    return total, inserted, updated, unchanged


async def main() -> int:
    try:
        total, inserted, updated, unchanged = await load_sample_records()
        print(f"records={total} inserted={inserted} updated={updated} unchanged={unchanged}")
        return 0
    except Exception as exc:
        print(f"Failed to load records: {exc}", file=sys.stderr)
        return 1
    finally:
        await dispose_engine()


if __name__ == "__main__":
    code = asyncio.run(main())
    sys.exit(code)
