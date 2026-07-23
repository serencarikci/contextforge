# ADR-001: Modular Monolith and Clean Architecture

- Status: Accepted
- Date: 2026-07-23

## Context

ContextForge will eventually include document ingestion, retrieval-augmented generation,
multilingual chat, authorization, and operational tooling. Starting with microservices
would force early network boundaries, duplicated deployment complexity, and premature
service contracts before the domain is stable.

## Decision

Adopt a modular monolith with Clean Architecture boundaries:

* `domain` — enterprise rules and entities
* `application` — use cases and ports
* `infrastructure` — adapters (PostgreSQL, Redis, Qdrant, MinIO)
* `api` — HTTP transport (FastAPI)

Modules communicate through explicit interfaces (ports) rather than framework imports.
Framework and infrastructure concerns must not leak into the domain layer.

## Consequences

Positive:

* Faster iteration while the product shape is still evolving
* Shared transactional consistency for metadata
* Clear extraction seams for future services

Negative:

* Requires discipline to keep module boundaries clean
* A single deployable unit can grow large if boundaries erode

## Alternatives considered

* Microservices from day one — rejected due to operational overhead and unclear boundaries
* Layered MVC without ports — rejected because infrastructure tends to leak into domain logic
