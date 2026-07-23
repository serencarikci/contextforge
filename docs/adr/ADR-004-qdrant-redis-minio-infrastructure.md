# ADR-004: Qdrant, Redis, and MinIO Infrastructure

- Status: Accepted
- Date: 2026-07-23

## Context

The long-term product requires:

* Vector similarity search over document chunks
* Caching, rate limiting, and coordination primitives
* Durable object storage for uploaded enterprise documents

Delaying these systems until later commits would force disruptive infrastructure
changes when RAG and ingestion work begins.

## Decision

Include the following infrastructure from the first commit:

* **Qdrant** — future vector retrieval backend
* **Redis** — future caching, rate limiting, and asynchronous coordination
* **MinIO** — S3-compatible storage for document binaries (`contextforge-documents`)

This commit configures clients, Docker Compose services, and readiness checks only.
No RAG, embedding, ingestion, or chat business logic is implemented yet.

## Consequences

Positive:

* Local development mirrors the eventual production topology
* Readiness endpoint validates the full dependency set early
* Later feature commits can focus on domain behavior

Negative:

* Higher local resource usage than an API-only bootstrap
* Operators must understand multiple services from day one

## Alternatives considered

* API + PostgreSQL only in commit one — rejected because later infrastructure wiring
  would delay feature delivery and hide integration risk
* Managed cloud services only (no local MinIO/Qdrant) — rejected for local reproducibility
