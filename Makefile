.PHONY: help dev test test-integration cov lint migrate seed up down logs reset

help:
	@echo "FlutterFix Development Tasks"
	@echo "  make dev              - Start development server with reload"
	@echo "  make test             - Run unit tests"
	@echo "  make test-integration - Run integration tests with fresh database"
	@echo "  make cov              - Run test coverage report"
	@echo "  make lint             - Run Ruff linting and formatting check"
	@echo "  make migrate          - Run Alembic database migrations"
	@echo "  make seed             - Load initial dataset into database"
	@echo "  make up               - Build and start Docker Compose stack in background"
	@echo "  make down             - Stop Docker Compose stack"
	@echo "  make logs             - Follow Docker Compose stack logs"
	@echo "  make reset            - Tear down Docker Compose stack and remove volumes"

dev:
	uv run poe dev

test:
	uv run poe test

test-integration:
	uv run poe test-integration

cov:
	uv run poe cov

lint:
	uv run poe lint

migrate:
	uv run poe migrate

seed:
	uv run poe seed

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

reset:
	@echo "WARNING: docker compose down -v deletes local Docker volumes and PostgreSQL data!"
	docker compose down -v
