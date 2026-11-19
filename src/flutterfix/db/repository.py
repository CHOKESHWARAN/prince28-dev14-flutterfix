"""Repository layer for Document queries against PostgreSQL with JSONB filtering."""

import json
from typing import Any

from sqlalchemy import Text as StringText
from sqlalchemy import cast, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from flutterfix.db.models import Document

# Safe allowed filter keys for dynamic metadata queries
ALLOWED_FILTER_KEYS = {
    "category",
    "status",
    "deprecated_in",
    "removed_in",
    "api_name",
    "replacement",
    "topic_id",
    "flutter_version",
    "dart_version",
    "change_type",
    "widget_or_api",
    "year",
    "doc_type",
    "title",
}


class InvalidFilterError(ValueError):
    """Raised when an invalid filter key is supplied."""


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def to_dict(doc: Document) -> dict[str, Any]:
        """Convert a Document model instance into the exact API dictionary format."""
        data: dict[str, Any] = dict(doc.metadata_ or {})

        # Ensure canonical top-level fields match the original API contract
        data["id"] = doc.external_id
        data["title"] = doc.title
        if doc.source_url:
            data["source_url"] = doc.source_url
            data.setdefault("page", doc.source_url)
            data.setdefault("breaking_change_url", doc.source_url)
        if doc.licence:
            data.setdefault("licence", doc.licence)
        if doc.doc_type:
            data.setdefault("doc_type", doc.doc_type)

        return data

    async def list(
        self,
        q: str | None = None,
        limit: int = 20,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Query documents with optional text search, pagination, and JSONB metadata filters."""
        query = select(Document).options(selectinload(Document.pages))

        # Validate and apply metadata filters
        if filters:
            for key, val in filters.items():
                if key not in ALLOWED_FILTER_KEYS:
                    allowed = sorted(ALLOWED_FILTER_KEYS)
                    raise InvalidFilterError(
                        f"Invalid filter parameter '{key}'. Allowed: {allowed}"
                    )

                if key == "doc_type":
                    query = query.where(Document.doc_type == str(val))
                else:
                    filter_payload = json.dumps({key: val})
                    query = query.where(Document.metadata_.op("@>")(cast(filter_payload, JSONB)))

        # Apply search query across title, external_id, or metadata text
        if q:
            needle = f"%{q}%"
            query = query.where(
                or_(
                    Document.title.ilike(needle),
                    Document.external_id.ilike(needle),
                    cast(Document.metadata_, JSONB).cast(StringText).ilike(needle),
                )
            )

        # Count total matching rows
        count_query = select(func.count()).select_from(query.order_by(None).subquery())
        total_res = await self.session.execute(count_query)
        total = total_res.scalar_one()

        # Apply ordering and pagination
        query = query.order_by(Document.external_id.asc()).offset(offset).limit(limit)
        results = await self.session.execute(query)
        docs = results.scalars().all()

        return [self.to_dict(doc) for doc in docs], total

    async def get(self, external_id: str) -> dict[str, Any] | None:
        """Fetch a single document by external_id or alternate topic/api identifiers."""
        # 1. Primary lookup by external_id
        stmt = (
            select(Document)
            .options(selectinload(Document.pages))
            .where(Document.external_id == external_id)
        )
        res = await self.session.execute(stmt)
        doc = res.scalar_one_or_none()
        if doc is not None:
            return self.to_dict(doc)

        # 2. Secondary lookup by topic_id in metadata
        needle = external_id.lower().replace("_", "-")
        filter_topic = json.dumps({"topic_id": needle})
        stmt_topic = (
            select(Document)
            .options(selectinload(Document.pages))
            .where(Document.metadata_.op("@>")(cast(filter_topic, JSONB)))
        )
        res_topic = await self.session.execute(stmt_topic)
        doc = res_topic.scalars().first()
        if doc is not None:
            return self.to_dict(doc)

        # Check widget_or_api / api_name
        stmt_meta = (
            select(Document)
            .options(selectinload(Document.pages))
            .where(
                or_(
                    Document.metadata_.op("@>")(cast(json.dumps({"api_name": external_id}), JSONB)),
                    Document.metadata_.op("@>")(
                        cast(json.dumps({"widget_or_api": external_id}), JSONB)
                    ),
                )
            )
        )
        res_meta = await self.session.execute(stmt_meta)
        doc = res_meta.scalars().first()
        if doc is not None:
            return self.to_dict(doc)

        return None
