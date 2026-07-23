# syntax=docker/dockerfile:1.7

FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:0.11.31 /uv /usr/local/bin/uv

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --frozen --no-dev --no-editable


FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    CONTEXTFORGE_LOGGING__FORMAT=json

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 contextforge \
    && useradd --system --uid 10001 --gid contextforge --home /app --shell /usr/sbin/nologin contextforge

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations
COPY scripts/docker-entrypoint.sh /app/scripts/docker-entrypoint.sh

RUN chmod +x /app/scripts/docker-entrypoint.sh \
    && chown -R contextforge:contextforge /app

USER contextforge

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8000/api/v1/health/live || exit 1

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["uvicorn", "contextforge.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
