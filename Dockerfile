# Stage 1: Build virtual environment with locked dependencies
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy dependency specifications first to leverage Docker layer caching
COPY pyproject.toml uv.lock .python-version /app/

# Install locked production dependencies without the root project
RUN uv sync --frozen --no-dev --no-install-project

# Copy README and source tree to install the project package
COPY README.md /app/
COPY src/ /app/src/
RUN uv sync --frozen --no-dev


# Stage 2: Minimal runtime image
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8000

# Create dedicated non-root user with explicit UID/GID 10001
RUN groupadd -g 10001 -r app && useradd -u 10001 -r -g app -d /home/app -m app

WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Copy runtime files
COPY --chown=app:app src/ /app/src/
COPY --chown=app:app migrations/ /app/migrations/
COPY --chown=app:app scripts/ /app/scripts/
COPY --chown=app:app data/ /app/data/
COPY --chown=app:app alembic.ini pyproject.toml README.md /app/

USER app

EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn flutterfix.api.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
