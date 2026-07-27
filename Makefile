.PHONY: install dev worker retention-worker up down logs lint format type-check test test-unit test-integration test-architecture test-authorization test-security coverage migrate migration downgrade bootstrap-dev seed-system-data validate-infra helm-lint terraform-validate backup-postgres load-test-smoke compose-prod-config frontend-install frontend-dev frontend-build frontend-test clean help

UV ?= uv
PYTHON ?= python3
COMPOSE ?= docker compose

help:
	@echo "ContextForge development commands"
	@echo "  make install              Install dependencies with uv"
	@echo "  make dev                  Run API locally with uvicorn"
	@echo "  make worker               Run the document ingestion worker"
	@echo "  make retention-worker     Run the retention cleanup worker"
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
	@echo "  make validate-infra       Helm + Terraform validation scripts"
	@echo "  make helm-lint            Lint/template Helm chart"
	@echo "  make terraform-validate   Fmt/validate Terraform"
	@echo "  make backup-postgres      Run Postgres backup script"
	@echo "  make load-test-smoke      Run k6 smoke scenario (k6 required)"
	@echo "  make compose-prod-config  Validate prod compose merge"
	@echo "  make frontend-install     Install frontend npm deps"
	@echo "  make frontend-dev         Run Next.js on :3001"
	@echo "  make frontend-build       Build frontend production bundle"
	@echo "  make frontend-test        Run frontend unit tests"
	@echo "  make clean                Remove caches and build artifacts"

install:
	$(UV) sync --all-groups
	$(UV) run pre-commit install || true

dev:
	$(UV) run uvicorn contextforge.main:app --host 0.0.0.0 --port 8000 --reload

worker:
	$(UV) run contextforge-ingestion-worker

retention-worker:
	$(UV) run contextforge-retention-worker

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
	$(UV) run pytest --cov=contextforge --cov-report=term-missing --cov-report=xml --cov-fail-under=80

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

validate-infra: helm-lint terraform-validate

helm-lint:
	./scripts/validate-helm.sh

terraform-validate:
	./scripts/validate-terraform.sh

backup-postgres:
	./scripts/backup/backup_postgres.sh

load-test-smoke:
	@if ! command -v k6 >/dev/null 2>&1; then echo "k6 not installed"; exit 1; fi
	k6 run perf/k6/smoke.js

compose-prod-config:
	$(COMPOSE) -f docker-compose.yml -f docker-compose.prod.yml config >/dev/null
	@echo "compose prod config OK"

frontend-install:
	cd frontend/web && npm install

frontend-dev:
	cd frontend/web && npm run dev

frontend-build:
	cd frontend/web && npm run build

frontend-test:
	cd frontend/web && npm test

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov coverage.xml dist build
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	rm -rf frontend/web/.next frontend/web/coverage
