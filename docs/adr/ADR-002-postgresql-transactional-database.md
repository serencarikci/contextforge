# ADR-002: PostgreSQL as the Transactional Database

- Status: Accepted
- Date: 2026-07-23

## Context

ContextForge needs durable transactional storage for application metadata, future
document records, access-control data, and operational state. Vector similarity search
and object blobs have different access patterns.

## Decision

Use PostgreSQL as the system of record for transactional data.

* SQLAlchemy 2 async mappings with asyncpg
* UUID primary keys
* Timezone-aware UTC timestamps
* JSONB for flexible structured metadata (for example `SystemMetadata.value`)

Vector embeddings will initially live in Qdrant. Raw document binaries will live in MinIO.
PostgreSQL stores references and transactional metadata that relate those systems.

## Consequences

Positive:

* Strong consistency for metadata and future tenancy/auth records
* Mature tooling (Alembic, backups, observability)
* JSONB supports evolving metadata without frequent schema churn

Negative:

* Cross-store consistency between PostgreSQL, Qdrant, and MinIO must be designed carefully
* Large binary payloads must not be stored in PostgreSQL

## Alternatives considered

* MongoDB as primary store — rejected due to weaker relational integrity needs
* Storing vectors in PostgreSQL (pgvector) initially — deferred; Qdrant is purpose-built for
  vector retrieval and is already part of the infrastructure plan
* Storing documents as BYTEA — rejected in favor of S3-compatible object storage
