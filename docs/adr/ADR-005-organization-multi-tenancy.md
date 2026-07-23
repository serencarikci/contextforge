# ADR-005: Organization-Scoped Multi-Tenancy

- Status: Accepted
- Date: 2026-07-23

## Context

ContextForge is a shared, multi-tenant platform: separate customer organizations must be
able to use the same deployment without ever seeing each other's data. Every business
entity introduced in this commit (users' memberships, customers, projects, knowledge
spaces, audit events) needs an unambiguous tenancy boundary before authorization or
document ingestion can be layered on top.

Two designs were considered for expressing that boundary: a separate database/schema per
tenant, or a single shared schema with an explicit tenant column enforced at the
repository layer.

## Decision

Adopt organization-scoped multi-tenancy within a single shared schema:

* Every tenant-owned table carries a non-nullable `organization_id` foreign key
  (`customers`, `projects`, `knowledge_spaces`, `knowledge_space_memberships`,
  `organization_memberships`, `role_assignments`, `audit_events`).
* `User` is the only entity that is *not* organization-scoped — a person can hold
  memberships in multiple organizations, mirroring how real people work across
  companies/contracts.
* Every repository method that reads or writes a tenant-owned row takes
  `organization_id` as an explicit, required parameter and filters by it — there is no
  "global" lookup by primary key alone for these entities. `get(organization_id, id)`,
  never `get(id)`.
* `RequestContext.organization_id` is resolved once per request (from the active
  membership, see ADR-007) and threaded through every application service call. Services
  never accept a caller-supplied organization id from the request body/path for scoping
  decisions — only `ctx.organization_id` is trusted.
* Cross-tenant access attempts (a real id that belongs to a *different* organization) are
  surfaced as `404 Not Found`, identical to "does not exist" — a caller must never be able
  to distinguish "this resource belongs to another tenant" from "this resource does not
  exist" (see `tests/api/test_tenant_isolation_api.py`).

## Consequences

Positive:

* A single database, single migration history, and single connection pool — no
  per-tenant provisioning workflow needed for this stage of the product.
* Tenancy enforcement is uniform and reviewable: every query has the same
  `organization_id == :org_id` predicate, making it easy to spot a missing check in
  review or via the `tests/integration/tenancy/` isolation tests.
* Adding a new tenant is just inserting an `Organization` row — no infrastructure change.

Negative:

* A single missed `organization_id` filter in a new repository method is a real security
  bug, not just a correctness bug — this is mitigated with the isolation tests in
  `tests/integration/tenancy/test_tenant_isolation.py` and the API-level cross-tenant
  tests, but it remains a sharp edge future contributors must respect.
* Very large tenants share the same tables/indexes as small ones; if usage becomes highly
  skewed, partitioning by `organization_id` may eventually be needed.
* Physical data isolation (e.g., for a customer requiring dedicated infrastructure) would
  require a follow-up migration to per-tenant databases; this ADR intentionally defers
  that until there is real demand.

## Alternatives considered

* **Database-per-tenant** — rejected for now: substantial operational overhead
  (migrations, connection pooling, backups multiplied by tenant count) for a product
  stage where the tenant count and scale are unknown.
* **Schema-per-tenant** (single database, one PostgreSQL schema per organization) —
  rejected: still multiplies migration/connection complexity relative to a shared schema,
  without the full isolation benefits of separate databases.
* **Trusting a client-supplied `organization_id` header/body field for scoping** —
  rejected outright as insecure; scoping must only ever come from the caller's *validated*
  membership (ADR-007), never from unauthenticated request data.
