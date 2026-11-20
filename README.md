# FlutterFix

[![CI](https://github.com/CHOKESHWARAN/prince28-dev14-flutterfix/actions/workflows/ci.yml/badge.svg)](https://github.com/CHOKESHWARAN/prince28-dev14-flutterfix/actions/workflows/ci.yml)
[![CD](https://github.com/CHOKESHWARAN/prince28-dev14-flutterfix/actions/workflows/cd.yml/badge.svg)](https://github.com/CHOKESHWARAN/prince28-dev14-flutterfix/actions/workflows/cd.yml)
[![Live Service](https://img.shields.io/badge/Render-Live%20Production-brightgreen?logo=render)](https://prince28-dev14-flutterfix.onrender.com/health)

A Flutter and Dart mentor that answers from official docs and breaking-changes pages for the user's Flutter version.

**Status:** Day 5 Completed — Production Cloud Deployment, Automated CD Pipeline, Zero-Downtime Rollouts, Smoke Testing & Continuous Monitoring.

---

## 1. Project Overview

Flutter and Dart evolve rapidly: null safety migrations, Material 3 style defaults, deprecated widget constructors, and new Android build conventions frequently break existing codebases. Online tutorials are often outdated. FlutterFix systematically assists mobile developers in navigating Flutter version transitions by citing official migration guides and validating API compatibility against target SDK versions.

- **Developer:** Chokeshwaran M (`chokeshwaran.m.it.28@psvpec.in`)
- **Package:** `flutterfix`
- **Runtime:** Python 3.12 (FastAPI, SQLAlchemy 2.0 Async, Alembic)
- **Infrastructure:** PostgreSQL 17 + `pgvector`, Redis 7
- **Dependency & Tool Management:** `uv`, `poethepoet`, Docker Compose

---

## 2. Prerequisites

- **Python:** 3.12 or newer
- **uv:** Package and project manager (`>= 0.11.0`)
- **Docker & Docker Compose:** Docker Desktop (or Docker Engine on Linux)

---

## 3. Installation

Clone the repository and install all dependencies in a virtual environment:

```bash
git clone https://github.com/CHOKESHWARAN/prince28-dev14-flutterfix.git
cd prince28-dev14-flutterfix
uv sync
```

---

## 4. Environment Configuration

Copy the example environment file to `.env`:

```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

### Safe Example Configuration (`.env`):
```dotenv
APP_ENV=local
APP_NAME=flutterfix
LOG_LEVEL=INFO
PORT=8000
DATABASE_URL=postgresql://app:app@localhost:5433/app
TEST_DATABASE_URL=postgresql://app:app@localhost:5433/app_test
```
*(Never commit real database credentials or production API keys to source control).*

---

## 5. Local Docker Compose Startup (One-Command)

Start the entire development stack in one command:

```bash
docker compose up --build -d
```

### What this starts automatically:
1. **`db` (PostgreSQL 17 + `pgvector`)**: Runs on port `5433:5432`, persists data in the `flutterfix_postgres_data` named volume, and creates `app_test` database via init script.
2. **`redis` (Redis 7)**: Internal cache & message queue service on port 6379 (not publicly exposed on host).
3. **`migrate` (Database Migrations & Seeding)**: Waits for `db` healthcheck, executes `alembic upgrade head`, loads seed records via `python scripts/load_db.py`, and exits cleanly.
4. **`api` (FastAPI Application)**: Multi-stage container running as non-root user `app` (UID/GID 10001) on port `8000:8000`.

API is accessible directly at:
```text
http://localhost:8000
```

---

## 6. API URLs & Endpoints

- **Interactive Swagger Docs:** http://localhost:8000/docs
- **ReDoc API Documentation:** http://localhost:8000/redoc
- **API Base Route:** http://localhost:8000/v1/documents

---

## 7. Health Endpoint (Liveness)

- **URL:** `GET /health`
- **Purpose:** Verifies that the FastAPI process is running and accepting HTTP requests.
- **Behavior:** Returns `HTTP 200 {"status": "ok", "app": "flutterfix", "env": "local"}` immediately without touching PostgreSQL or external networks.

---

## 8. Readiness Endpoint

- **URL:** `GET /ready`
- **Purpose:** Verifies database connectivity and data loading status.
- **Behavior:**
  - `HTTP 200` when PostgreSQL is connected (`SELECT 1`) and documents are loaded (`SELECT count(*) FROM documents > 0`).
  - `HTTP 503` when the database is unreachable or down, returning `{"status": "not_ready", "checks": {"database": false, "records_loaded": false}}`.

---

## 9. Database Migrations

Apply Alembic migrations to head:

```bash
# Windows
uv run poe migrate

# Linux / macOS
make migrate
```

---

## 10. Database Seeding

Load initial documentation records:

```bash
# Windows
uv run poe seed

# Linux / macOS
make seed
```

---

## 11. Unit Tests

Run fast, isolated unit tests (no real database required):

```bash
# Windows
uv run poe test

# Linux / macOS
make test
```

---

## 12. Integration Tests

Run integration tests against a dedicated temporary database:

```bash
# Windows
uv run poe test-integration

# Linux / macOS
make test-integration
```
*Note: Each run dynamically creates a unique database (`flutterfix_test_<uuid>`), applies Alembic migrations, runs tests, and guarantees teardown drop even if setup fails.*

---

## 13. Code Coverage

Generate terminal coverage report and HTML report:

```bash
# Windows
uv run poe cov

# Linux / macOS
make cov
```
HTML report will be generated at `htmlcov/index.html`.

---

## 14. Code Linting & Formatting

Verify Ruff rules and code formatting:

```bash
# Windows
uv run poe lint

# Linux / macOS
make lint
```

---

## 15. Development Command Reference

| Task | Windows (Poe) | Mac / Linux (Make) | Description |
|:---|:---|:---|:---|
| Start Dev Server | `uv run poe dev` | `make dev` | FastAPI reload server without access logs |
| Run Unit Tests | `uv run poe test` | `make test` | Fast unit test suite in `tests/unit` |
| Run Integration Tests | `uv run poe test-integration` | `make test-integration` | Integration tests with fresh test database |
| Code Coverage Report | `uv run poe cov` | `make cov` | Terminal & HTML coverage report |
| Lint & Format Check | `uv run poe lint` | `make lint` | Ruff lint and format verification |
| Run Migrations | `uv run poe migrate` | `make migrate` | Apply Alembic migrations to head |
| Seed Database | `uv run poe seed` | `make seed` | Load sample data records |
| Compose Up | `docker compose up --build -d` | `make up` | Start Docker Compose stack in background |
| Compose Down | `docker compose down` | `make down` | Stop Docker Compose stack |
| Compose Logs | `docker compose logs -f` | `make logs` | Tail live container logs |
| Reset Volumes | `docker compose down -v` | `make reset` | Tear down containers and delete database volume |

---

## 16. Troubleshooting & Shutdown

### Troubleshooting
- **Port Conflict on 5433:** Ensure no other local PostgreSQL instance is using port 5433. Edit the host port mapping in `docker-compose.yml` if needed.
- **Port Conflict on 8000:** Stop any running Uvicorn dev process before starting `docker compose up`.
- **Docker Desktop Stopped:** If `docker compose` fails with pipe connection errors, verify Docker Desktop is running.
- **Integration Tests Skipped:** When `TEST_DATABASE_URL` is omitted, integration tests skip cleanly to allow offline development.

### Shutdown
Gracefully stop all Compose services while preserving database volume data:
```bash
docker compose down
```
To purge the local database volume and restart from a clean slate:
```bash
docker compose down -v
```

---

## 17. Day 5 — Production Cloud Deployment & Continuous Delivery

- **Live Production URL:** https://prince28-dev14-flutterfix.onrender.com
- **Liveness Endpoint:** `GET https://prince28-dev14-flutterfix.onrender.com/health`
  - Validates process liveness and dynamically reports the live git commit SHA via `RENDER_GIT_COMMIT`.
- **Readiness Endpoint:** `GET https://prince28-dev14-flutterfix.onrender.com/ready`
  - Validates production Neon PostgreSQL connectivity and verifies that documents are loaded.
- **API Documentation:** https://prince28-dev14-flutterfix.onrender.com/docs
- **Automated Smoke Test Suite:**
  ```bash
  # Standalone CLI
  python scripts/smoke.py --url https://prince28-dev14-flutterfix.onrender.com

  # Via Poe task
  uv run poe smoke
  ```
- **CI/CD Architecture:**
  - **CI:** Executes `lint and test` (lint, unit tests, PostgreSQL 17 + `pgvector` integration tests) and `build image` (GHCR image build on PRs, push on merge to `main`).
  - **CD:** Automatically executes pre-deployment Neon database migrations, triggers Render deployment, and runs smoke tests.
  - **Rollback:** Dedicated manual rollback workflow (`.github/workflows/rollback.yml`) that skips database migrations.
  - **Monitoring:** Monitored 24/7 with UptimeRobot HTTP(s) health check every 5 minutes and nightly automated health check workflow.
