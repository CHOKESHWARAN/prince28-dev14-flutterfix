"""Integration tests against a real PostgreSQL test database."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from flutterfix.api.main import create_app
from flutterfix.db.models import Document, Page
from flutterfix.db.repository import DocumentRepository
from scripts.load_db import load_sample_records


@pytest.mark.asyncio
async def test_migrations_created_expected_tables(fresh_database):
    """Verify all tables and Alembic version tracking are initialized."""
    from sqlalchemy.ext.asyncio import create_async_engine

    async_url = fresh_database["async_url"]
    engine = create_async_engine(async_url, connect_args=fresh_database["connect_args"])
    try:
        async with engine.connect() as conn:
            res = await conn.execute(
                text(
                    """
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public'
                    """
                )
            )
            tables = {row[0] for row in res.fetchall()}
    finally:
        await engine.dispose()

    assert "alembic_version" in tables
    assert "documents" in tables
    assert "pages" in tables


@pytest.mark.asyncio
async def test_loader_idempotency_against_real_db(fresh_database, tmp_path):
    """Verify load_sample_records inserts, skips on rerun, and updates on modified input."""
    # Write a small test batch
    sample_records = [
        {
            "id": "int-001",
            "title": "Initial Button Migration",
            "category": "widget",
            "doc_type": "widget",
            "published_on": "2024-01-10",
            "description": "Initial description",
            "year": 2024,
            "tags": ["material", "button"],
        },
        {
            "id": "int-002",
            "title": "Navigator Migration",
            "category": "navigation",
            "doc_type": "navigation",
            "published_on": "2024-02-15",
            "description": "Navigator description",
            "year": 2024,
            "tags": ["router"],
        },
    ]

    data_file = tmp_path / "sample.json"

    data_file.write_text(json.dumps(sample_records), encoding="utf-8")

    # Run 1: initial insertion
    total, inserted, updated, unchanged = await load_sample_records(data_path=data_file)
    assert total == 2
    assert inserted == 2
    assert updated == 0
    assert unchanged == 0

    # Run 2: exact same file -> all unchanged
    total, inserted, updated, unchanged = await load_sample_records(data_path=data_file)
    assert total == 2
    assert inserted == 0
    assert updated == 0
    assert unchanged == 2

    # Run 3: modify one record -> 1 updated, 1 unchanged
    sample_records[0]["title"] = "Updated Button Migration"
    data_file.write_text(json.dumps(sample_records), encoding="utf-8")
    total, inserted, updated, unchanged = await load_sample_records(data_path=data_file)
    assert total == 2
    assert inserted == 0
    assert updated == 1
    assert unchanged == 1


@pytest.mark.asyncio
async def test_repository_and_metadata_filtering(db_session):
    """Verify repository queries, JSONB numeric values, and doc_type filters."""
    repo = DocumentRepository(db_session)

    # Insert test documents with diverse metadata
    doc1 = Document(
        external_id="filter-001",
        title="ElevatedButton Migration",
        doc_type="widget",
        sha256="hash-001",
        metadata_={"category": "widget", "year": 2024, "status": "deprecated"},
    )
    doc1.pages.append(Page(page_no=1, text="Button details"))

    doc2 = Document(
        external_id="filter-002",
        title="Routing Updates",
        doc_type="navigation",
        sha256="hash-002",
        metadata_={"category": "navigation", "year": 2025, "status": "stable"},
    )
    doc2.pages.append(Page(page_no=1, text="Navigation details"))

    db_session.add_all([doc1, doc2])
    await db_session.commit()

    # 1. Dedicated doc_type filter
    items, total = await repo.list(filters={"doc_type": "widget"})
    assert total == 1
    assert items[0]["id"] == "filter-001"

    # 2. JSONB metadata string filter
    items, total = await repo.list(filters={"category": "navigation"})
    assert total == 1
    assert items[0]["id"] == "filter-002"

    # 3. Combined filters
    items, total = await repo.list(filters={"doc_type": "widget", "status": "deprecated"})
    assert total == 1
    assert items[0]["id"] == "filter-001"

    # 4. Search query
    items, total = await repo.list(q="Routing")
    assert total == 1
    assert items[0]["id"] == "filter-002"


def test_api_integration_and_readiness(fresh_database):
    """Verify the real FastAPI application against the fresh PostgreSQL database."""
    app = create_app()
    with TestClient(app) as client:
        # Liveness check
        r_health = client.get("/health")
        assert r_health.status_code == 200
        assert r_health.json()["status"] == "ok"

        # Readiness check against real database
        r_ready = client.get("/ready")
        assert r_ready.status_code == 200
        checks = r_ready.json()["checks"]
        assert checks["database"] is True

        # Document listing
        r_docs = client.get("/v1/documents")
        assert r_docs.status_code == 200
        assert "items" in r_docs.json()


def test_safety_validation_protects_critical_databases():
    """Verify that protected databases and invalid identifiers are rejected."""
    from tests.integration.conftest import _validate_safe_test_db_name

    # Must raise for critical system and app databases
    for protected in ["app", "app_test", "postgres", "neondb"]:
        with pytest.raises(ValueError):
            _validate_safe_test_db_name(protected)

    # Must raise for SQL injection or invalid patterns
    for invalid in ["flutterfix_test_123; DROP TABLE users;", "test_db", "flutterfix_test_"]:
        with pytest.raises(ValueError):
            _validate_safe_test_db_name(invalid)
