.PHONY: install dev up down logs lint format type-check test test-unit test-integration test-architecture test-authorization test-security coverage migrate migration downgrade bootstrap-dev seed-system-data clean help

UV ?= uv
PYTHON ?= python3
COMPOSE ?= docker compose

help:
	@echo "ContextForge development commands"
	@echo "  make install              Install dependencies with uv"
	@echo "  make dev                  Run API locally with uvicorn"
	@echo "  make up                   Start full Docker Compose stack"
	@echo "  make down                 Stop Docker Compose stack"
	@echo "  make logs                 Tail Compose logs"
	@echo "  make lint                 Run Ruff lint"
	@echo "  make format               Format with Ruff"
	@echo "  make type-check           Run mypy"
	@echo "  make test                 Run all tests"
	@echo "  make test-unit            Run unit tests"
	@echo "  make test-integration     Run integration tests"
	@echo "  make test-architecture    Run architecture tests"
	@echo "  make test-authorization   Run authorization-marked tests"
	@echo "  make test-security        Run security-marked tests"
	@echo "  make coverage             Run tests with coverage"
	@echo "  make migrate              Apply Alembic migrations"
	@echo "  make migration name=...   Create a new Alembic migration"
	@echo "  make downgrade            Downgrade one Alembic migration"
	@echo "  make bootstrap-dev        Seed deterministic local development data"
	@echo "  make seed-system-data     Verify RBAC reference data is seeded"
	@echo "  make clean                Remove caches and build artifacts"

install:
	$(UV) sync --all-groups
	$(UV) run pre-commit install || true

dev:
	$(UV) run uvicorn contextforge.main:app --host 0.0.0.0 --port 8000 --reload

up:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

lint:
	$(UV) run ruff check .

format:
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

type-check:
	$(UV) run mypy

test:
	$(UV) run pytest

test-unit:
	$(UV) run pytest -m unit

test-integration:
	$(UV) run pytest -m integration

test-architecture:
	$(UV) run pytest -m architecture

test-authorization:
	$(UV) run pytest -m authorization

test-security:
	$(UV) run pytest -m security

coverage:
	$(UV) run pytest --cov=contextforge --cov-report=term-missing --cov-report=xml --cov-fail-under=85

migrate:
	$(UV) run alembic upgrade head

migration:
	@if [ -z "$(name)" ]; then echo "Usage: make migration name=\"description\""; exit 1; fi
	$(UV) run alembic revision --autogenerate -m "$(name)"

downgrade:
	$(UV) run alembic downgrade -1

bootstrap-dev:
	$(UV) run python scripts/bootstrap_dev.py

seed-system-data:
	$(UV) run python scripts/seed_system_data.py

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov coverage.xml dist build
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
