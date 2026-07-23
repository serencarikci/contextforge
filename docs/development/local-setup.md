# Local development guide

## Install tooling

```bash
# Python 3.13 + uv required
cp .env.example .env
make install
```

## Run with Docker Compose (recommended)

```bash
make up
curl -s http://localhost:8000/api/v1/health/live | jq
curl -s http://localhost:8000/api/v1/health/ready | jq
curl -s http://localhost:8000/api/v1/system/info | jq
```

## Run API on the host

1. Start dependencies: `docker compose up -d postgres redis qdrant minio minio-init`
2. Apply migrations: `make migrate`
3. Start API: `make dev`

## Pre-commit

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```
