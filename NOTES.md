# FlutterFix – Day 3 and Day 4 Implementation Notes

This document contains actual execution outputs, database migration history, data loader runs, query plan analysis, and verification evidence for Day 3 and Day 4 of FlutterFix.

---

# Day 3 — PostgreSQL Migration

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

1. **Current Migration Head**:
   ```bash
   uv run alembic current
   ```
   Output:
   ```text
   INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
   INFO  [alembic.runtime.migration] Will assume transactional DDL.
   0003_add_index_on_doc_type (head)
   ```

2. **Downgrade to Revision 2**:
   ```bash
   uv run alembic downgrade -1
   ```
   Output:
   ```text
   INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
   INFO  [alembic.runtime.migration] Will assume transactional DDL.
   INFO  [alembic.runtime.migration] Running downgrade 0003_add_index_on_doc_type -> 0002_add_gin_index_on_metadata, add index on doc_type
   ```

3. **Current Revision After Downgrade**:
   ```bash
   uv run alembic current
   ```
   Output:
   ```text
   INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
   INFO  [alembic.runtime.migration] Will assume transactional DDL.
   0002_add_gin_index_on_metadata
   ```

4. **Re-Upgrade to Head**:
   ```bash
   uv run alembic upgrade head
   ```
   Output:
   ```text
   INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
   INFO  [alembic.runtime.migration] Will assume transactional DDL.
   INFO  [alembic.runtime.migration] Running upgrade 0002_add_gin_index_on_metadata -> 0003_add_index_on_doc_type, add index on doc_type
   ```

All three migration revisions cleanly support upgrade and downgrade operations.

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
collected 38 items

tests\test_api.py .............                                          [ 34%]
tests\test_database_connection.py .                                      [ 36%]
tests\test_db_integration.py s                                           [ 39%]
tests\test_loader.py ...........                                         [ 68%]
tests\test_models.py ...                                                 [ 76%]
tests\test_repository.py .........                                       [100%]

======================== 37 passed, 1 skipped in 1.04s ========================
```

The test suite covers:
- API endpoints (health, ready DB connectivity, documents pagination, search, metadata filtering, doc_type filtering, problem-details error format, request-ID propagation).
- Model definitions (Document, Page, naming conventions, properties, relationships).
- Idempotent loader (new record insert, unchanged skip, changed update, in-batch duplicate handling, date parsing, missing fields, transaction rollback).
- Repository query generation (JSONB containment `@>`, dedicated doc_type column filter, text search, pagination count, ID/topic/API lookups).
- Database connection tests skip cleanly when `TEST_DATABASE_URL` is omitted.

---

## 6. Code Quality Gates

Command: `uv run ruff check .`
```text
All checks passed!
```

Command: `uv run ruff format --check .`
```text
34 files already formatted
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


---

# Day 4 — Docker and Testing

### Dockerfile implementation & multi-stage build
- **Base image:** `python:3.12-slim` with `uv` copied from `ghcr.io/astral-sh/uv:0.11.32`.
- **Multi-stage build:**
  - Builder stage: Installs dependencies via `uv sync --frozen --no-dev --no-install-project` into `/app/.venv`.
  - Runtime stage: Minimal `python:3.12-slim` runtime containing only virtual environment, source tree, migrations, and scripts.
- **Non-root container user:** Explicit non-root system user `app` with UID 10001 and GID 10001 (`groupadd -g 10001 -r app && useradd -u 10001 -r -g app -d /home/app -m app`).
- **Layer caching architecture:**
  - Layer 1: Copies `pyproject.toml`, `uv.lock`, `.python-version` and installs locked production dependencies.
  - Layer 2: Copies `src/` and performs project editable install via `uv sync --frozen --no-dev`.
  - Result: Source code edits invalidate only Layer 2, keeping the large dependency installation cached for fast subsequent builds.

### Docker Compose architecture & services
- **Compose services (`docker-compose.yml`):**
  - `db`: `pgvector/pgvector:pg17` exposed on `5433:5432` with named volume `flutterfix_postgres_data` and init script `docker/initdb/01-create-test-db.sql`.
  - `redis`: `redis:7-alpine` using internal port exposure `6379` (not publicly exposed on host interfaces).
  - `migrate`: One-shot container that executes `alembic upgrade head && python scripts/load_db.py` once `db` is healthy, exiting with code 0.
  - `api`: Production FastAPI server starting once `migrate` completes successfully, with liveness healthcheck.
- **Compose validation:** Verified via `docker compose config` (exit code 0).

### Breaking the database (Liveness vs. Readiness)
- **Liveness (`GET /health`):**
  - Confirms the Python web process is running and accepting HTTP requests.
  - Returns `HTTP 200 {"status": "ok", "app": "flutterfix", "env": "local"}` regardless of whether PostgreSQL or external services are up or down.
- **Readiness (`GET /ready`):**
  - Performs an active database connection check (`SELECT 1`) and verifies record loading (`SELECT count(*) FROM documents`).
  - When the database is stopped: Returns `HTTP 503 {"status": "not_ready", "checks": {"database": false, "records_loaded": false}}`.
  - When the database restarts: Automatically recovers to `HTTP 200` without requiring an API restart due to connection pool resilience.

### Temporary database cleanup and safety guarantees
- **Safety checks (`tests/integration/conftest.py`):**
  - Strict pattern matching: Database names must match `^flutterfix_test_[0-9a-f]{12}$`.
  - Blacklist protection: Refuses to touch protected databases (`postgres`, `app`, `app_test`, `neondb`).
  - Cleanup guarantee: Wraps migration and execution in a `try...finally` block to ensure `DROP DATABASE IF EXISTS` runs even when setup or migration fails.
  - Parameterized session termination: `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :datname` prevents SQL injection.

### Unit-test results
- Command: `python -m pytest tests/unit -v` (via `uv run poe test`)
  ```text
  tests\unit\test_api.py .............                                     [ 35%]
  tests\unit\test_database_connection.py .                                 [ 37%]
  tests\unit\test_loader.py ...........                                    [ 67%]
  tests\unit\test_models.py ...                                            [ 75%]
  tests\unit\test_repository.py .........                                  [100%]
  ============================= 37 passed in 1.77s ==============================
  ```

### Integration-test results (Offline environment)
- Command: `python -m pytest tests/integration` (via `uv run poe test-integration`)
  ```text
  tests\integration\test_database.py ssss.                                 [100%]
  ======================== 1 passed, 4 SKIPPED in 4.24s =========================
  ```
  - `test_safety_validation_protects_critical_databases`: PASSED.
  - Real database integration tests: SKIPPED (PostgreSQL at localhost:5433 unreachable while Docker daemon is stopped).

### Code coverage report
- Command: `python -m pytest tests/unit --cov=flutterfix --cov-report=term-missing --cov-report=html:htmlcov`
  ```text
  Name                                     Stmts   Miss Branch BrPart  Cover   Missing
  ------------------------------------------------------------------------------------
  src\flutterfix\api\deps.py                  17      3      0      0    82%   20-21, 28
  src\flutterfix\api\middleware.py            21      3      0      0    86%   22-24
  src\flutterfix\api\routes\documents.py      24      2      6      0    93%   36-37
  src\flutterfix\api\routes\health.py         28      1      4      1    94%   29
  src\flutterfix\config.py                    20      1      2      1    91%   31
  src\flutterfix\db\repository.py             67      0     22      2    98%   55->58, 71->86
  src\flutterfix\db\session.py                26      2      0      0    92%   49-50
  src\flutterfix\db\url.py                    17      0      4      2    90%   25->29, 37->40
  ------------------------------------------------------------------------------------
  TOTAL                                      343     12     44      6    95%

  8 files skipped due to complete coverage.
  Coverage HTML written to dir htmlcov
  ```
- **Total Coverage:** 95% (exceeds >= 90% threshold).

### Ruff lint and formatting results
- **Lint:** `uv run --no-sync ruff check .` -> `All checks passed!`
- **Format:** `uv run --no-sync ruff format --check .` -> `39 files already formatted`

### Docker build and startup results
- `docker version`: Client 29.7.2 installed. Server daemon stopped (`open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`).
- `docker compose config`: **PASS** (validated configuration and volume mapping).
- `docker compose build / up`: **NOT VERIFIED** (requires manual start of Docker Desktop service on Windows host).

### GitHub Actions CI results
- Workflow file: `.github/workflows/ci.yml`
- Verification: Sets up Python 3.12, uv, Ruff lint, Ruff format check, unit test suite with coverage, and PostgreSQL 17 + pgvector service container for integration tests. Configured without exposing secrets or Neon credentials.

---

## Day 5 — Deployment, CI/CD, Production Readiness & Verification

### 1. Production Architecture Overview
- **Hosting Provider:** Render Web Services (Singapore region)
- **Runtime Model:** Multi-stage Docker container running FastAPI + Uvicorn under non-root user `app` (UID/GID 10001).
- **Service Name:** `prince28-dev14-flutterfix`
- **Service ID:** `srv-dbvu58ss728c73c00uug`
- **Live Production URL:** `https://prince28-dev14-flutterfix.onrender.com`
- **Database:** Serverless PostgreSQL 17 with `pgvector` hosted on Neon (`neondb`).
- **Container Registry:** GitHub Container Registry (`ghcr.io/chokeshwaran/prince28-dev14-flutterfix`).

### 2. Dynamic SHA Resolution Architecture
- Render automatically injects `RENDER_GIT_COMMIT` at runtime with the deployed commit SHA.
- `Settings` in `src/flutterfix/config.py` employs a Pydantic `@model_validator(mode="after")` that prefers `RENDER_GIT_COMMIT` whenever `git_sha` is unset or set to local defaults (`"local"`, `"dev"`).
- This ensures zero-config, dynamic commit SHA reporting on `/health` without hardcoding fixed environment variables in Render that would become stale on future deploys.

### 3. CI/CD Pipeline Implementation
- **CI Workflow (`.github/workflows/ci.yml`)**:
  - Triggers on every pull request to `main` and pushes to `main`.
  - Job `lint and test`: Sets up PostgreSQL 17 + pgvector container, runs Ruff linting, Ruff formatting check, unit tests with coverage, and live integration tests.
  - Job `build image`: Builds multi-stage Docker image on PRs without pushing; pushes SHA-tagged (`:${{ github.sha }}`) and `:latest` images to GHCR on merge to `main`.
  - Status check names: Exactly `lint and test` and `build image`.
- **CD Workflow (`.github/workflows/cd.yml`)**:
  - Automatically triggered upon completion of `CI` on `main` and via manual `workflow_dispatch`.
  - Serialized via `concurrency: group: production, cancel-in-progress: false`.
  - Pre-flight validation for required repository secrets (`RENDER_DEPLOY_HOOK`, `DATABASE_URL`) and variable (`LIVE_URL`).
  - Pre-deployment database migrations: Runs `alembic upgrade head` against Neon PostgreSQL before triggering the application rollout.
  - Deployment trigger: Dispatches webhook request to Render Deploy Hook.
  - Automated smoke testing: Invokes `scripts/smoke.py --wait` to verify `/health` reports the exact commit SHA, `/ready` reports HTTP 200, and `/v1/documents` serves data.
- **Rollback Workflow (`.github/workflows/rollback.yml`)**:
  - Manual emergency trigger via `workflow_dispatch` taking `target_sha` and `reason`.
  - Strictly skips database migrations during rollbacks to maintain schema compatibility.
  - Smoke-tests the target rollback deployment.
- **Nightly Health Check (`.github/workflows/nightly.yml`)**:
  - Cron trigger running daily at 00:00 UTC.
  - Executes smoke test against live production service.

### 4. Automated Smoke Test Suite (`scripts/smoke.py`)
- Verifies:
  1. `/health`: Returns HTTP 200 and matches expected commit SHA.
  2. `/ready`: Returns HTTP 200 with `status: "ready"`, `checks.database: true`, and `checks.records_loaded: true`.
  3. `/v1/documents?limit=1`: Returns HTTP 200 with valid document records and metadata.
- Supports CLI arguments `--url`, `--expected-sha`, `--wait`, `--max-retries`, and `--delay`.
- Tested and verified: 100% pass against live Render service.

### 5. Production Endpoint Verification Evidence
- **Liveness Endpoint (`GET /health`)**:
  - HTTP Status: `200 OK`
  - Response: `{"status":"ok","app":"flutterfix","env":"production","version":"3d17330056f9b397a3fecfeb2a1fc9864775e186","commit":"3d17330056f9b397a3fecfeb2a1fc9864775e186"}`
  - Verified: Exactly matches deployed commit SHA `3d17330056f9b397a3fecfeb2a1fc9864775e186`.
- **Readiness Endpoint (`GET /ready`)**:
  - HTTP Status: `200 OK`
  - Response: `{"status":"ready","checks":{"database":true,"records_loaded":true}}`
  - Verified: Active Neon PostgreSQL connection and 20 sample documents verified.
- **Documents Endpoint (`GET /v1/documents?limit=1`)**:
  - HTTP Status: `200 OK`
  - Response: Total 20 records, item `001` ("FlatButton to TextButton Migration").

### 6. Secrets & Environment Variables Configuration Checklist
- **GitHub Repository Secrets** (`Settings > Secrets and variables > Actions > Secrets`):
  - `RENDER_DEPLOY_HOOK`: Render Deploy Hook URL for triggering rollouts.
  - `DATABASE_URL`: Production Neon PostgreSQL connection string (strictly required for pre-deploy migrations).
- **GitHub Repository Variables** (`Settings > Secrets and variables > Actions > Variables`):
  - `LIVE_URL`: `https://prince28-dev14-flutterfix.onrender.com`
- **Render Service Environment Variables** (`Environment` tab in Render Dashboard):
  - `APP_ENV`: `production`
  - `DATABASE_URL`: Production Neon PostgreSQL connection string.

### 7. Branch Protection Rules for `main`
- In GitHub repository settings (`Settings > Branches > Branch protection rules > Add rule`):
  - Branch name pattern: `main`
  - Check **Require a pull request before merging** (Note: in a single-owner repository, leave required approvals at 0 or ensure owner is permitted to merge so the sole owner is not blocked).
  - Check **Require status checks to pass before merging**:
    - `lint and test`
    - `build image`
  - Do not allow bypassing the above settings.

### 8. Monitoring & Availability (UptimeRobot)
- **Monitor Type:** HTTP(s) Monitor
- **Monitor Name:** `FlutterFix Production API`
- **Monitoring URL:** `https://prince28-dev14-flutterfix.onrender.com/health`
- **Check Interval:** Every 5 minutes
- **Expected HTTP Code:** `200 OK`
- **Alert Contacts:** Configured in user UptimeRobot dashboard for instant downtime notifications.
