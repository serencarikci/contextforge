# ADR-003: Asynchronous Python Stack

- Status: Accepted
- Date: 2026-07-23

## Context

The API must handle concurrent I/O against PostgreSQL, Redis, Qdrant, and MinIO.
Readiness checks and future retrieval workflows benefit from non-blocking concurrency.

## Decision

Use an asynchronous Python stack:

* FastAPI for the HTTP layer
* Uvicorn as the ASGI server
* SQLAlchemy 2 asyncio API with asyncpg
* Concurrent readiness checks via `asyncio.gather`
* `httpx.AsyncClient` for HTTP-based dependency probes

Blocking third-party SDKs (for example MinIO) are isolated with `asyncio.to_thread`
and bounded by timeouts.

## Consequences

Positive:

* Efficient concurrent dependency checks
* Natural fit for I/O-heavy RAG and ingestion workflows later
* Consistent async session/transaction model

Negative:

* Blocking CPU-bound work can stall the event loop
* Contributors must avoid sync DB calls inside async routes
* Some libraries require thread offloading

## Alternatives considered

* Synchronous Flask/Django stack — rejected for weaker native concurrency model
* Mixing sync SQLAlchemy in async routes — rejected due to event-loop blocking risk
