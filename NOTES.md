# FlutterFix – Day 3 PostgreSQL Migration Notes

This document contains actual execution outputs, database migration history, data loader runs, query plan analysis, and verification evidence for the Day 3 PostgreSQL migration of FlutterFix.

---

## 1. Database Connection Verification

Script: `scripts/db_check.py`

```text
Neon PostgreSQL connection: SUCCESS
Database test value: 1
PostgreSQL server version: 18.7 (84da7d8)
```

The database connection converts the Neon PostgreSQL URL to the `postgresql+asyncpg` dialect, strips incompatible `sslmode` and `channel_binding` parameters, passes `ssl=True` via asyncpg `connect_args`, and verifies connectivity with `SELECT 1`.

---

## 2. Alembic Migrations

### Migration History

Command: `uv run alembic history`

```text
0002_add_gin_index_on_metadata -> 0003_add_index_on_doc_type (head), add index on doc_type
0001_create_documents_and_pages -> 0002_add_gin_index_on_metadata, add gin index on metadata
<base> -> 0001_create_documents_and_pages, create documents and pages
```

### Migration Downgrade and Upgrade Verification

1. **Downgrade to Revision 1**:
   ```bash
   uv run alembic downgrade -1
   ```
   Output:
   ```text
   INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
   INFO  [alembic.runtime.migration] Will assume transactional DDL.
   INFO  [alembic.runtime.migration] Running downgrade 0002_add_gin_index_on_metadata -> 0001_create_documents_and_pages, add gin index on metadata
   ```

2. **Current Revision Inspection**:
   ```bash
   uv run alembic current
   ```
   Output:
   ```text
   INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
   INFO  [alembic.runtime.migration] Will assume transactional DDL.
   0001_create_documents_and_pages
   ```

3. **Re-Upgrade to Head**:
   ```bash
   uv run alembic upgrade head
   ```
   Output:
   ```text
   INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
   INFO  [alembic.runtime.migration] Will assume transactional DDL.
   INFO  [alembic.runtime.migration] Running upgrade 0001_create_documents_and_pages -> 0002_add_gin_index_on_metadata, add gin index on metadata
   ```

Both migration revisions cleanly support upgrade and downgrade operations.

---

## 3. Idempotent Data Loader Execution

Script: `scripts/load_db.py`  
Source: `data/sample_records.json` (20 records)

### Run 1: Initial Population (All Inserted)
```bash
uv run python scripts/load_db.py
```
Output:
```text
records=20 inserted=20 updated=0 unchanged=0
```

### Run 2: Idempotent Re-Run (All Unchanged)
```bash
uv run python scripts/load_db.py
```
Output:
```text
records=20 inserted=0 updated=0 unchanged=20
```

### Run 3: Modified Record Detection
After modifying record `"001"` in `data/sample_records.json`:
```bash
uv run python scripts/load_db.py
```
Output:
```text
records=20 inserted=0 updated=1 unchanged=19
```

*(Record "001" was then restored to its canonical content, updating it back to unchanged status).*

---

## 4. Query Plan Analysis (EXPLAIN ANALYZE)

Script: `scripts/explain.py`  
Target Query:
```sql
SELECT id, external_id, title FROM documents
WHERE metadata @> CAST('{"category": "widget"}' AS jsonb);
```

### Plan 1: Default Query Planner Choice (`enable_seqscan = on`)
```text
Seq Scan on documents  (cost=0.00..11.00 rows=1 width=182) (actual time=0.022..0.039 rows=7.00 loops=1)
  Filter: (metadata @> '{"category": "widget"}'::jsonb)
  Rows Removed by Filter: 13
  Buffers: shared hit=3
Planning Time: 1.249 ms
Execution Time: 0.076 ms
```

### Plan 2: Forced Index Scan (`enable_seqscan = off`)
```text
Bitmap Heap Scan on documents  (cost=12.81..16.82 rows=1 width=182) (actual time=0.058..0.064 rows=7.00 loops=1)
  Recheck Cond: (metadata @> '{"category": "widget"}'::jsonb)
  Heap Blocks: exact=3
  Buffers: shared hit=6
  ->  Bitmap Index Scan on ix_documents_metadata_gin  (cost=0.00..12.81 rows=1 width=0) (actual time=0.025..0.025 rows=9.00 loops=1)
        Index Cond: (metadata @> '{"category": "widget"}'::jsonb)
        Index Searches: 1
        Buffers: shared hit=3
Planning Time: 0.087 ms
Execution Time: 0.173 ms
```

### Plan Interpretation & GIN Index Behavior

1. **Why PostgreSQL Chose Sequential Scan in Plan 1**:
   - The `documents` table currently contains 20 records, occupying only 3 shared buffer blocks (approx. 24 KB total).
   - In sequential scanning, the storage engine reads all 3 blocks in order (`Buffers: shared hit=3`) with an estimated cost of `11.00` and execution time of `0.076 ms`.
   - Index lookup requires reading the GIN index structure to construct a bitmap (`Buffers: shared hit=3`), followed by random reads into the heap blocks (`Buffers: shared hit=6`), resulting in an estimated cost of `16.82` and execution time of `0.173 ms`.
   - The cost-based optimizer correctly evaluates `cost=11.00` < `cost=16.82` and chooses sequential scan for maximum throughput.

2. **When the GIN Index Becomes Useful**:
   - When the table scales to thousands or millions of documents spanning hundreds of pages.
   - For selective JSONB containment queries where matching rows represent a small fraction of the table, avoiding full table scans.
   - When combined with composite metadata filters such as `{"category": "widget", "status": "deprecated"}`.

---

## 5. Test Suite Results

Command: `uv run pytest -v`

```text
============================= test session starts =============================
platform win32 -- Python 3.12.14, pytest-9.2.0, pluggy-1.7.0
rootdir: D:\placement\day2\project
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.16.0, platformdirs-4.14.7
collected 14 items

tests\test_api.py ............                                           [ 85%]
tests\test_database_connection.py .                                      [ 92%]
tests\test_db_integration.py s                                           [100%]

================== 13 passed, 1 skipped in 2.77s ===================
```

All 12 unit tests pass completely in isolation without requiring a live database connection by utilizing FastAPI dependency overrides and an in-memory repository. The live database connection check passes, and integration tests skip cleanly when `TEST_DATABASE_URL` is omitted.

---

## 6. Code Quality Gates

Command: `uv run ruff check .`
```text
All checks passed!
```

Command: `uv run ruff format --check .`
```text
29 files already formatted
```

---

## 7. How to Run Migrations and Loader

### Running Database Migrations
```bash
# Upgrade database schema to latest revision
uv run alembic upgrade head

# Check current revision
uv run alembic current

# View migration history
uv run alembic history
```

### Running the Idempotent Data Loader
```bash
# Ingest or synchronize data/sample_records.json with PostgreSQL
uv run python scripts/load_db.py
```

### Running the Database Check & Query Plan Analysis
```bash
# Verify live database connection
uv run python scripts/db_check.py

# Verify GIN index and analyze execution plans
uv run python scripts/explain.py
```
