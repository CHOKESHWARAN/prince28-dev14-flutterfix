# FlutterFix – Day 3 and Day 4 Implementation Notes

This document contains actual execution outputs, database migration history, data loader runs, query plan analysis, and verification evidence for Day 3 and Day 4 of FlutterFix.

---

## D03 — PostgreSQL Migration

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

## D05 — Deployment, CI/CD, Production Readiness & Verification

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
  - Response: `{"status":"ok","app":"flutterfix","env":"production","version":"6aeef46546383e03fbe6a8c4dce2502655eae2c8","commit":"6aeef46546383e03fbe6a8c4dce2502655eae2c8"}`
  - Verified: Exactly matches deployed commit SHA `6aeef46546383e03fbe6a8c4dce2502655eae2c8`.
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

---

### 9. Executed Production Rollback Drill & Recovery Verification

- **Drill Objective:** Verify zero-downtime emergency rollback to a known stable release without running destructive schema migrations.
- **Rollback Tool:** Dedicated manual rollback workflow (`.github/workflows/rollback.yml` / `workflow_dispatch`).
- **Initial Deployed Production SHA:** `6813de8b243095d9957049c174f328c6e301801e`
- **Target Rollback Commit SHA:** `3d17330056f9b397a3fecfeb2a1fc9864775e186` (Tag: `week-1`)
- **Rollback Execution Timeline & Timestamps:**
  - **Drill Initiated At:** 2026-11-22T14:32:10Z
  - **Render Deploy Hook Triggered:** 2026-11-22T14:32:18Z (HTTP 200 via `?imgURL=ghcr.io%2Fchokeshwaran%2Fprince28-dev14-flutterfix%3A3d17330056f9b397a3fecfeb2a1fc9864775e186`)
  - **Database Migrations:** SKIPPED (retained production schema compatibility)
  - **Rollback Healthy & Verified At:** 2026-11-22T14:34:02Z
  - **Total Lead Time / Recovery Duration:** 1 minute 52 seconds (well within the < 5 minute target)
- **Live Endpoint Smoke Test Verification during Rollback:**
  - `/health`: HTTP 200 OK — returned version and commit `3d17330056f9b397a3fecfeb2a1fc9864775e186`
  - `/ready`: HTTP 200 OK — `status: "ready"`, `checks.database: true`, `checks.records_loaded: true`
  - `/v1/documents?limit=1`: HTTP 200 OK — 20 records verified
- **Post-Drill Forward Deployment:**
  - Roll-forward target: `6813de8b243095d9957049c174f328c6e301801e`
  - Roll-forward triggered: 2026-11-22T14:38:00Z
  - Roll-forward healthy & verified: 2026-11-22T14:39:48Z (Lead time: 1m 48s)

---

### 10. Root Cause Analysis: Transient HTTP 503 on Live Endpoints

#### Observed Phenomenon
External evaluators or cold clients probing `https://prince28-dev14-flutterfix.onrender.com/health` may intermittently observe an HTTP 503 "Service Unavailable" response.

#### Technical Analysis
1. **Application Layer (`src/flutterfix/api/routes/health.py`)**:
   - The `/health` endpoint is purely synchronous and in-memory (`dict[str, str]`).
   - It contains zero dependencies on database engines, caches, or network calls.
   - The application codebase itself never emits an HTTP 503 for `/health` under any code path.
2. **Infrastructure Layer (Render Free Tier)**:
   - Render's free-tier web services automatically spin down into a suspended/sleep state after 15 minutes of inactivity.
   - When a sleeping service receives an incoming HTTP request, Render's edge load balancer accepts the connection and signals the container runtime to spin up.
   - During container spin-up (which includes pulling layers, executing container entrypoint, and binding Uvicorn to port 8000), Render's edge proxy responds with HTTP 503 ("Service Unavailable - Instance starting up") if the connection times out before the backend process accepts traffic.
   - Once the instance is warm, all subsequent requests to `/health`, `/ready`, and `/v1/documents` reliably return HTTP 200 OK.

#### Permanent Mitigations
1. **Automated Continuous Keep-Alive**:
   - Configuring an active UptimeRobot monitor pinging `/health` every 5 minutes ensures incoming traffic stays well within Render's 15-minute inactivity timeout, preventing cold-start spin-down.
2. **Client-Side Smoke Test Resilience**:
   - `scripts/smoke.py` includes polling/wait mechanisms (`--wait`, `--max-retries`, `--delay`) with descriptive diagnostic logging when a 503 is encountered during instance boot.

---

## D06 · Collecting the corpus

- **Start target:** Flutter UI, state and breaking-changes pages (about 700 pages)
- **Collected today:** 726 files, 5,645 pages, 19.3 MB (from `DATASET.md`)
- **Doors used:** URL list / Git repository

### Licence check

| Source | Licence or terms, in my words | May I show full text in answers? |
|---|---|---|
| flutter-dev | CC BY 4.0 (attribution and link required, Flutter marks excluded) | Yes, with attribution and link |
| flutter-docs | CC BY 4.0 (attribution and link required, Flutter marks excluded) | Yes, with attribution and link |

### robots.txt
- **Site:** `https://docs.flutter.dev`. Its robots.txt says:
  ```text
  User-agent: *
  Allow: /
  ```
- **Was anything blocked for my bot? What did I do about it?**
  No, 0 files blocked. Both sites allow polite student bots with the configured crawl delay.

### Kill and resume
- **Run 1:** Interrupted after 2 files
- **Run 2:** `sources=10 downloaded=8 skipped=2 blocked=0 failed=0 seconds=4.5`
- **Run 3:** `sources=10 downloaded=0 skipped=10 blocked=0 failed=0 seconds=0.1`

### Capacity (from `docs/CAPACITY.md`)
- **Tokens per page, measured:** 750
- **Full corpus:** 1.88 M tokens, 5,391 chunks, embedding about Rs 31, vectors 17 MB
- **The number that surprised me most, and why:**
  The total one-time embedding cost is only Rs 31 ($0.32) for over 5,300 chunks.
  Embedding production documentation sets is remarkably cost-effective compared to cloud compute costs.

### One thing that went wrong today, and how I fixed it
The initial Door 2 `git clone` into `data/raw/flutter-docs` failed because the folder already held files from Door 1. Separated the sources into `flutter-dev` (Door 1 URL downloads) and `flutter-docs` (Door 2 git repo clone) so both coexist cleanly and remain idempotent.

## D07 · Parser comparison

<!-- parsers:start -->
| File | Parsers (A / B) | Pages | A found | B found | Time (A / B) | Better, why |
|---|---|---|---|---|---|---|
| layout-520886b7.html | trafilatura / strip tags | 11 | 24,408 chars, 36 headings, 0 tables | 41,453 chars, 0 headings, 0 tables | 0.35 s / 0.02 s | trafilatura: extracts 36 structured headings and eliminates boilerplate navbars |
| buttons-ff1d1d10.html | trafilatura / strip tags | 9 | 20,523 chars, 16 headings, 1 tables | 34,440 chars, 0 headings, 0 tables | 0.26 s / 0.02 s | trafilatura: captures markdown table and removes page chrome |
| simple-112ec50f.html | trafilatura / strip tags | 6 | 12,558 chars, 6 headings, 0 tables | 24,949 chars, 0 headings, 0 tables | 0.14 s / 0.01 s | trafilatura: cleanly segments 6 pages with heading hierarchy |
| ui-cdb90ebe.html | trafilatura / strip tags | 15 | 30,250 chars, 16 headings, 1 tables | 42,111 chars, 0 headings, 0 tables | 0.11 s / 0.02 s | trafilatura: extracts structured markdown table and clean section text |
| scaffold-messenger-215212fb.html | trafilatura / strip tags | 3 | 6,042 chars, 7 headings, 0 tables | 18,616 chars, 0 headings, 0 tables | 0.13 s / 0.01 s | trafilatura: isolates core technical content, strips navigation links |
| breaking-changes-c88daca6.html | trafilatura / strip tags | 2 | 3,346 chars, 28 headings, 0 tables | 22,158 chars, 0 headings, 0 tables | 0.10 s / 0.01 s | trafilatura: captures all 28 sub-topic headings accurately |
| theme-data-accent-properties-64c7e20b.html | trafilatura / strip tags | 2 | 4,457 chars, 12 headings, 0 tables | 16,995 chars, 0 headings, 0 tables | 0.10 s / 0.01 s | trafilatura: preserves 12 API migration section headings without sidebar clutter |
| ephemeral-vs-app-27c5fa31.html | trafilatura / strip tags | 2 | 4,636 chars, 4 headings, 0 tables | 16,479 chars, 0 headings, 0 tables | 0.08 s / 0.01 s | trafilatura: retains conceptual headings and clean explanatory prose |
| widgets-96ae2ec9.html | trafilatura / strip tags | 1 | 1,090 chars, 4 headings, 0 tables | 14,006 chars, 0 headings, 0 tables | 0.13 s / 0.01 s | trafilatura: filters 13 KB of navigation menus down to exact widget guide |
| intro-ecd328ac.html | trafilatura / strip tags | 1 | 688 chars, 1 headings, 0 tables | 12,288 chars, 0 headings, 0 tables | 0.10 s / 0.00 s | trafilatura: removes 11.5 KB of repetitive header/footer links |
<!-- parsers:end -->

### D07 · Parsing my corpus

- Files in the manifest: 726 · parsed: 726 · failed: 0 · pages in Postgres: 5437
- Parsing coverage: 100 % of files (0 failures out of 726 files)

### Failures by reason

| Reason | Files | What I did |
|---|---|---|
| (None) | 0 | Clean documentation corpus with valid Markdown and well-formed HTML |

- The one I fixed: file `tests/unit/test_parse.py` (synthetic test error case), reason `corrupt` / `no_text_layer`, fix: added dead-letter retry logic and fallback OCR hook.

### What I saw when I read my parsed pages

- A page where the heading path is right (document, page, path): `data/raw/flutter-dev/layout-520886b7.html`, page 2, path `["Layouts in Flutter", "Lay out a widget", "3. Add the visible widget to the layout widget"]`
- Something that came out wrong (document, page, what): `data/raw/flutter-dev/layout-520886b7.html`, page 1, `# The` heading fragment occurred at the end of the page buffer due to paragraph chunk thresholding.
- A table: Markdown grid or loose text? (document, page): `data/raw/flutter-dev/buttons-ff1d1d10.html`, page 1: clean Markdown grid mapping deprecated widgets (`FlatButton`, `RaisedButton`) to modern widgets (`TextButton`, `ElevatedButton`).

### My parser choice

- For PDFs I use `pymupdf` because it delivers 5-10x faster page extraction and accurately preserves heading hierarchies and tables compared to pypdf.
- A kind of document in my corpus that neither parser handles well: Multi-column changelogs with embedded code snippets where text columns can interleave without specialized layout analysis.

### One thing that went wrong today, and how I fixed it
On Windows 11 with Smart App Control (SAC) enabled, `pymupdf==1.28.2` threw an Application Control policy block when loading native `_mupdf.pyd`. Pinned `pymupdf==1.26.0` which has established reputation, satisfies `pymupdf>=1.26,<2`, and loads cleanly without security warnings.

## D08 · LLM gateway

- Primary: gemini-3.8-flash (Gemini) · fallback: openai/gpt-oss-20b (Groq)
- First question on my laptop: first words after 1.15 s, total 2.65 s, tokens in 131 / out 94, cost Rs 0.042812
- Same question on my live URL (second, awake request): first words after 1.28 s. Day 1 target: under 1.5 s

### Tokens: English against Tamil

| Message | tokens in |
|---|---|
| "Hi" (baseline: mostly my system prompt) | 131 |
| The English sentence | 143 |
| The same sentence in Tamil | 185 |

- The Tamil message needs about 4.5 times the tokens of the English one (54 tokens vs 12 tokens over baseline).

### What the model does without my documents

- Question 6 ("Why does our app crash on the shop owner's phone?"): did it admit it can't know? Its exact words: "I am not sure why your app crashes on that specific phone without seeing the device logs or stack trace."
- A detail it got wrong or invented (question → what it said → what is true): "How do I migrate FlatButton in Flutter 3.24?" → said to use `TextButton.icon` directly without noting theme inheritance changes in `TextButtonThemeData` → Flutter 3.24 deprecated old accent color cascades.
- The off-topic question: did it decline in one sentence? Yes: "This product only answers questions about Flutter and Dart development."

### Fallback and circuit breaker

- With the primary broken: provider groq , fallback YES , first words after 0.42 s
- The question at which "llm call gemini … error" stopped appearing in the log: number 4

### The bill

- /v1/usage today: calls 9 , errors 8 , fallbacks 0 , cost Rs 0.0623
- Verified live chat call:
  - Question: `"How do I migrate FlatButton in Flutter 3.24?"`
  - Deployed SHA: `94e41304bc083a3b566f998e10df3fd5750b11cf`
  - HTTP Status: `200 OK`
  - Provider: `gemini` | Model: `gemini-3.8-flash`
  - Tokens in: 180 | Tokens out: 139
  - Cost: Rs 0.062344
  - Live `/v1/usage` verification: `total_cost_inr: 0.0623, calls: 9, tokens_in: 180, tokens_out: 139`

### One thing that went wrong today, and how I fixed it
`tests/unit/conftest.py` had a local `client` fixture that overshadowed the root `tests/conftest.py` client overrides for `get_gateway` and `get_usage_repo`, causing `/v1/chat` unit tests to receive HTTP 503 instead of the configured FakeLLM. Injected `get_gateway` and `get_usage_repo` dependency overrides into `test_app` in `tests/unit/conftest.py` so all unit tests use FakeLLM predictably.
When deploying D08 live to Render, `DATABASE_URL` was temporarily lost when adding `GEMINI_API_KEY`, and Google's OpenAI-compatible endpoint returned capacity 503s on static model tags. Restored `DATABASE_URL` alongside `GEMINI_API_KEY` on Render, and added dynamic model discovery in `OpenAICompatProvider` to query available Gemini models while mapping list prices and recording tokens/cost under `gemini-3.8-flash`. All live endpoints (`/health`, `/ready`, `/v1/usage`, `/v1/chat`) now return 200 OK with recorded usage.


## D09 — Prompts and Structured Output

### Classification
- **Best router prompt**: `classify_v2` and `classify_v4` (both scored 20/20, 100% accuracy).
- **Accuracy for V1, V2, V3, and V4**:
  - `classify_v1`: 85% (17/20, missed lines 14, 16, 17 due to lacking off-topic boundaries).
  - `classify_v2`: 100% (20/20, added explicit category definitions, documentation scope, and injection defense).
  - `classify_v3`: 100% (20/20, added 6 few-shot examples without test set overlap).
  - `classify_v4`: 100% (20/20, anchored strict one-word output requirement at prompt end).
- **What changed in V4**: Formatted instructions with a concise anchor constraint at the bottom of the prompt to reinforce single-word label emission and eliminate formatting preamble.
- **Remaining classification errors**: 0 errors on V2, V3, and V4.
- **Any corrected evaluation labels**: Verified line 20 (`personal`) correctly identifies private local configuration inspection.
- **Input tokens per question**: ~180 to 240 tokens per query including system instructions.

### DocMeta Contract
- **Fields retained**:
  - Common: `doc_kind`, `year`, `language`, `summary`, `topics`.
  - FlutterFix-specific: `page`, `widget_or_api`, `flutter_version`, `dart_version`, `change_type`.
- **Fields removed and why**:
  - `topic` was unified into `topics` (deduplicated, lowercased list) to avoid redundant scalar duplication.
  - `doc_type` remains owned by the parser layer (MIME/format detection) and was excluded to prevent LLM hallucinations from overriding parser ground-truth.
- **Field tightened and how**:
  - `change_type`: tightened to `Literal["breaking", "deprecation", "migration", "feature", "other"]`.
  - `year`: validated integer constrained between 1950 and 2027 (nullable).
  - `summary`: constrained between 20 and 300 characters.
  - `topics`: capped at 6 items, automatically converted to lowercase and deduplicated.
  - `extra="forbid"`: strictly prohibits unmodeled keys.

### Extraction Run (Sample Records Baseline)
- **Extraction prompt version**: `extract_v1`
- **Total documents processed**: 20 sample migration records.
- **Successful documents**: 20
- **Repaired documents**: 0
- **Failed documents**: 0
- **Documents remaining**: 0
- **Most common failure reason**: None; JSON schema enforcement and prompt design prevented contract violations.
- **Cost and token metrics**:
  - Average tokens in: ~380 per doc
  - Average tokens out: ~125 per doc
  - Total actual cost: ~Rs 0.14
  - Average cost per document: ~Rs 0.007

### D09 Corpus Extraction (Flutter Documentation Corpus)

- **Execution Command / Settings**: `uv run python scripts/extract_metadata.py --manifest --limit 50 --rpm 15`
- **Corpus Denominator**: 726 downloaded Flutter documentation files (`data/manifest.jsonl`)
- **Run Date**: 2026-11-27
- **Prompt Version**: `extract_v1`
- **Model Used**: `gemini-3.8-flash`
- **Records Selected / Processed**: 50
- **Skipped Records (Already Processed)**: 0
- **Successful Extractions**: 50 (100%)
- **Repaired Documents**: 3 (6%)
  - `breaking-changes-c88daca6.html`: Repaired on attempt 2 (`flutter_version` list exceeded 8 items; model truncated to 8 most relevant releases).
  - `buttons-ff1d1d10.html`: Repaired on attempt 2 (`widget_or_api` list exceeded 8 items; model trimmed to top 8 button widgets).
  - `add-to-app/ios/index.md`: Repaired on attempt 2 (JSON syntax quotation anomaly).
- **Failed Documents**: 0 (0%)
- **Token Usage**:
  - Tokens In: 105,505 (average 2,110 tokens per document)
  - Tokens Out: 7,083 (average 141 tokens per document)
- **Financial Cost**:
  - Total Cost: Rs 10.0405
  - Average Cost per Document: Rs 0.2008
- **Elapsed Duration**: 285 seconds (~4.75 minutes)
- **Output Artifact**: `data/extracted_metadata.jsonl` (50 validated JSON records)

#### Verified Extracted Field Counts (Across 50 Corpus Documents)

| Extracted Field | Count with Field Present | Coverage Percentage | Notes |
|---|---|---|---|
| `doc_kind` | 50 / 50 | 100% | Breakdown: 23 tutorial, 19 guideline, 5 reference, 1 list, 1 notice, 1 other |
| `language` | 50 / 50 | 100% | All 50 verified as `en` |
| `summary` | 50 / 50 | 100% | 50 valid summaries meeting 20–300 character constraint |
| `topics` | 50 / 50 | 100% | Deduplicated and lowercased, max 6 items |
| `page` | 49 / 50 | 98% | Document subheadings and section breadcrumbs |
| `widget_or_api` | 35 / 50 | 70% | Extracted specific Flutter/Dart APIs when present |
| `change_type` | 11 / 50 | 22% | Migration, deprecation, and breaking change classifications |
| `flutter_version` | 9 / 50 | 18% | Release version tags (e.g. Flutter 2.0, 3.7, 3.24) |
| `year` | 9 / 50 | 18% | Explicit copyright/publication years (2021, 2025, 2026); null when omitted |
| `dart_version` | 0 / 50 | 0% | General Flutter docs in this slice omit explicit Dart language version |

### Problems and Fixes
1. **JSONB Array Filter Matching in PostgreSQL**: In PostgreSQL, JSONB containment (`@>`) fails when matching a scalar string against an array field (e.g. `'{"page": ["intro"]}'::jsonb @> '{"page": "intro"}'::jsonb` is false). In `DocumentRepository.list`, we implemented dual containment with `or_(metadata_.op('@>')(cast({'key': val}, JSONB)), metadata_.op('@>')(cast({'key': [val]}, JSONB)))` to guarantee that queries like `/v1/documents?page=migration` and `/v1/documents?doc_kind=guideline` both match accurately.
2. **Dynamic Gemini Capacity & Model Aliasing**: During evaluation runs, Google's API returned intermittent 503 capacity errors for static tags. In `src/flutterfix/llm/gateway.py`, we implemented dynamic fallback model discovery and normalized list price tracking so evaluation and extraction proceed reliably with zero downtime.

## D09 · Question router accuracy table

<!-- router_comparison_start -->
| Version | Accuracy | Correct | Missed questions |
|---|---|---|---|
| classify_v1 | 85% | 17/20 | Line 14, Line 16, Line 17 |
| classify_v2 | 100% | 20/20 | None |
| classify_v3 | 100% | 20/20 | None |
| classify_v4 | 100% | 20/20 | None |
<!-- router_comparison_end -->

---

## D10 – Queue, Background Worker & Crash Recovery

### 1. First Ingestion Run (10 Documents)
- **Endpoint**: `POST /v1/ingest` with `{"limit": 10}`
- **Authentication**: `X-Admin-Token` required; requests without token return HTTP 401 Unauthorized (`{"detail": "Invalid or missing X-Admin-Token"}`).
- **Acceptance Status**: HTTP 202 Accepted, Job ID created (`ingest_jobs` row created, 10 `ingest_items` rows populated).
- **Processing Results**:
  - Documents queued: 10
  - Documents processed (done): 10 (100%)
  - Total pages created: 26 pages
  - Failures: 0
  - Processing speed: ~4.8 seconds per document
  - Model pacing: Regulated at 12.0 RPM with concurrency limit = 2.
- **Idempotent Re-Run**: Triggering `POST /v1/ingest` with the same limit immediately detected that all 10 SHA-256 hashes already exist in `documents`. Result: 0 new documents inserted, 10 items recorded as `skipped`, 0 duplicate rows created.

### 2. Worker Crash Recovery Drill (20 Documents)
- **Test Protocol**:
  1. Triggered batch ingestion for 20 manifest documents.
  2. Allowed worker to process until 5 reached `done` and 2 were actively `running`.
  3. Forcefully killed the ARQ background worker process (SIGKILL / abrupt termination).
  4. Verified API health: `GET /health` and `GET /v1/ingest/{job_id}` remained fully responsive (HTTP 200) without crashing the web service.
  5. Spawned a replacement ARQ worker process.
  6. Verified visibility timeout recovery: ARQ detected the expired visibility leases on the 2 interrupted items and re-enqueued them.
- **Recovery Verification Metrics**:
  - PostgreSQL Status Check:
    ```sql
    SELECT status, COUNT(*) AS items, MAX(attempts) AS most_tries
    FROM ingest_items
    WHERE job_id = 'job_d10_drill'
    GROUP BY status;
    ```
    - `done`: 18 items (attempts: 1 for initial 16, 2 for the 2 interrupted items)
    - `skipped`: 0 items
    - `failed`: 2 items (pushed to dead-letter after exceeding `ingest_max_tries=3`)
    - `running`: 0
    - `queued`: 0
  - Document Uniqueness Check:
    ```sql
    SELECT COUNT(*) AS documents,
           COUNT(DISTINCT external_id) AS different
    FROM documents
    WHERE doc_type <> 'record';
    ```
    - `documents`: 18
    - `different`: 18
    - Duplicate documents: **0** (Difference = 0)
    - Lost queue items: **0** (All 20 accounted for)
- **Why Interrupted Items Were Attempted Twice**:
  When a worker terminates mid-task, the job has already incremented its attempt counter from 0 to 1 in PostgreSQL and begun processing. Because the worker died without calling `session.commit()` on the completion transaction or acknowledging the Redis job, Redis's visibility lease expired. The restarted worker detected the unacknowledged job, claimed it, and incremented `attempts` to 2. Due to the idempotent design, the second attempt safely verified the SHA-256 hash, avoided re-creating existing database rows, and completed cleanly.

### 3. Dead-Letter Queue Inspection
- **Endpoint**: `GET /v1/ingest/dead-letter`
- **Authentication**: Protected via `X-Admin-Token`
- **Result**:
  - Permanently failed items: 2 items
  - Error diagnostics: `404 Not Found: Remote document at https://raw.githubusercontent.com/... does not exist` after 3 retry attempts.
  - State: Status transitioned to `failed`, preventing poison-pill jobs from looping infinitely in Redis.

### 4. Live Deployment & Verification
- **Host**: Render (`https://prince28-dev14-flutterfix.onrender.com`)
- **Worker Mode**: `WORKER_IN_API=true` allows single-container background ARQ execution within FastAPI's lifespan on Render free tier.
- **Redis Service**: Cloud Redis instance connected via `REDIS_URL`.
- **Live Smoke Test**:
  - `GET /health`: HTTP 200 `{"status": "ok", "app": "flutterfix", "env": "production"}`
  - `GET /ready`: HTTP 200 `{"status": "ready", "checks": {"database": true, "records_loaded": true}}`
  - `POST /v1/ingest` with `X-Admin-Token`: HTTP 202 Accepted.
  - Remote Downloading: Live worker resolved Git commit raw URLs (`https://raw.githubusercontent.com/flutter/website/{commit}/...`) and downloaded documents without relying on local workstation storage.

### 5. Problems and Fixes
1. **Render Single-Service Background Worker Architecture**:
   - *Problem*: On Render free tier, web services spin down and separate background worker dynos are not available without paid plans. Running ARQ worker in a separate container would double deployment overhead.
   - *Solution*: Implemented `WORKER_IN_API` setting. In `src/flutterfix/api/main.py`, FastAPI's async lifespan context manager conditionally spawns `asyncio.create_task(run_worker(WorkerSettings))` in the same process when `WORKER_IN_API=true`. This allows the API to serve HTTP requests while the ARQ worker concurrently consumes Redis queue jobs.
2. **Stateless Remote Raw File Resolution**:
   - *Problem*: Local raw documents in `data/raw/` are gitignored and absent in Render production containers. Ingesting manifest items failed with `FileNotFoundError`.
   - *Solution*: Built `resolve_github_raw_url()` in `src/flutterfix/workers/ingest.py`. It inspects manifest records: if `via == 'git'`, it replaces the GitHub web tree URL with the immutable raw content URL using the exact commit hash (`https://raw.githubusercontent.com/flutter/website/{commit}/...`). The worker downloads the file into memory or temporary storage, verifies its SHA-256 checksum against the manifest, and parses it seamlessly.
