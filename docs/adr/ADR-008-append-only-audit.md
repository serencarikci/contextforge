# ADR-008: Append-Only Audit Trail with Sanitized Metadata

- Status: Accepted
- Date: 2026-07-23

## Context

Once multi-tenancy (ADR-005) and RBAC (ADR-006) exist, "who did what, to which resource,
in which organization, and when" becomes an operational and compliance requirement, not
just a nice-to-have: enterprise customers will ask for it, and it is the primary tool for
diagnosing "why does this user have access to X" after the fact. The audit trail needs to
be trustworthy — an event that can be edited or deleted after the fact is far weaker
evidence than one that provably could not have been altered — while also not becoming an
accidental secrets-leak vector, since call sites will often pass whatever
request/response context is at hand into the metadata bag.

## Decision

Every mutating application-service use case (create/update/suspend/archive/assign/
revoke/add-membership/etc., across organizations, customers, projects, knowledge spaces,
users, memberships, and role assignments) writes exactly one `AuditEvent` in the *same*
database transaction as the mutation itself, via `uow.audit.add(event)` before the unit
of work commits.

* **Append-only.** The `AuditEventRepository` port and its SQLAlchemy implementation
  expose `add` and `list`/query methods only — there is deliberately no `update` or
  `delete` method anywhere in the audit module. The `audit_events` table has no
  application-level code path that can mutate or remove a row once written. (Operators
  retain out-of-band DB access for legal/retention needs, but the application itself
  cannot edit history.)
* **Same-transaction durability.** Because the audit write happens inside the same
  `async with uow:` block as the domain mutation (see e.g.
  `CustomerService.create`, `OrganizationService.update`), an audit event exists if and
  only if the mutation it describes was actually committed — no separate "best effort"
  audit pipe that can silently drop events relative to the write it describes. This is
  exercised directly in
  `tests/integration/audit/test_audit_persistence.py`, which asserts a durable, queryable
  row exists after each write, not just that no exception was raised.
* **Structured, minimal fields.** `AuditEvent` carries `action` (a dotted verb string like
  `"customer.created"`), `resource_type`, `resource_id`, `organization_id`,
  `actor_user_id`, `correlation_id` (for tracing back to the originating request), and a
  free-form `metadata` dict for anything action-specific (e.g., `{"code": "DEV-CUST"}`).
* **Metadata is sanitized unconditionally, at construction time.**
  `AuditEvent.__post_init__` calls `AuditEvent.sanitize_metadata`, which drops any key
  whose lowercased form *contains* a forbidden substring (`password`, `secret`, `token`,
  `api_key`, `access_key`, `secret_key`, `authorization`, `cookie` — substring match, not
  exact match, so e.g. `user_password_hint` is also dropped) before the event is even
  constructed. Callers cannot opt out of this and cannot bypass it by constructing the
  dataclass directly — sanitization is in `__post_init__`, not in a helper callers must
  remember to invoke (see `tests/unit/domain/test_audit_event.py`).
* **Read access is itself permissioned.** Reading the audit trail requires the
  `audit:read` permission through `AuditQueryService`/`GET /api/v1/audit` — an organization
  admin can read their own organization's trail, a viewer cannot (see
  `tests/api/test_lifecycle_api.py::TestAuditLifecycle`).

## Consequences

Positive:

* Every audited mutation is provably backed by a durable, queryable, tamper-resistant
  record — a real foundation for "who changed this and when" support/compliance requests,
  not a best-effort log line that might be missing.
* Sanitization at the domain-entity boundary means every current and future call site
  gets the protection automatically; a developer adding a new audited use case cannot
  forget to sanitize, because there is nothing to remember — it is unconditional.
* Keeping the audit write in the same transaction as the mutation means there is exactly
  one failure mode to reason about (the whole transaction rolls back together), instead
  of two independent systems that can disagree.

Negative:

* Every additional mutating use case must remember to actually call
  `build_audit_event`/`uow.audit.add(...)` — there is no cross-cutting decorator or
  middleware enforcing "every write has an audit event" today; this is a code-review
  discipline, backed only by the specific persistence tests for the endpoints this commit
  introduces. A generic architecture test enforcing "every service mutation writes an
  audit event" is a reasonable future addition but is not implemented yet.
* Substring-based key matching in `sanitize_metadata` is intentionally aggressive (favors
  false positives over leaking a secret) — a legitimate field like `token_count` would
  also be dropped. Given today's metadata payloads are small and curated per call site,
  this trade-off was accepted; a future allowlist-per-action model could be more precise
  if this becomes a real limitation.
* No update/delete path also means there is no way to redact/correct a bad audit entry
  short of new compensating events or direct DB/operator intervention — by design, but
  worth remembering operationally.

## Alternatives considered

* **Fire-and-forget audit logging (e.g., publish to a queue/log sink, no DB row)** —
  rejected for this stage: durability and queryability ("show me every event for this
  customer") matter more right now than decoupling the write path, and there is no
  queue/log-aggregation infrastructure in place yet to receive it reliably.
* **Soft-delete/editable audit rows (an `is_deleted`/`updated_at` column)** — rejected:
  directly undermines the property that makes an audit trail useful as evidence — that it
  reflects what actually happened, unedited.
* **Allowlisting metadata fields per action instead of blocklisting forbidden
  substrings** — rejected for now as more precise but higher-maintenance: it would
  require touching a central allowlist every time a new audited action is added, whereas
  the blocklist protects every call site by default with zero per-action configuration.
