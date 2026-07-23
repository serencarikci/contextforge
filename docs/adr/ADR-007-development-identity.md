# ADR-007: Header-Based Development Identity (Interim, Non-Production Auth)

- Status: Accepted
- Date: 2026-07-23

## Context

This commit introduces multi-tenancy and RBAC (ADR-005, ADR-006), both of which need a
concrete, authenticated caller and organization before they mean anything. Real
authentication (OIDC/SSO — see the roadmap in `README.md`) is deliberately **out of
scope** for this stage of the product. Blocking every tenancy/authorization use case,
integration test, and API endpoint on a full OIDC implementation would stall the rest of
the roadmap for no immediate benefit, since there are not yet any real end users.

A lightweight stand-in was needed that (a) lets every downstream layer (RBAC,
tenancy, audit) be built and tested against a *real* identity/organization resolution
path today, and (b) can be swapped for real authentication later without changing the
shape of `RequestContext` or any application service.

## Decision

Introduce **development identity**: the caller supplies their identity directly via two
request headers, resolved by `contextforge.api.dependencies.identity` and validated by
`build_request_context` (`identity_context_service.py`):

```
X-ContextForge-User-ID: <uuid>
X-ContextForge-Organization-ID: <uuid>
```

Key properties:

* **Environment-gated.** `development_identity_enabled(settings)` returns `True` only for
  `local`, `test`, and `development` environments. For `staging` and `production` it
  returns `False`, and `build_request_context` immediately raises
  `InvalidDevelopmentIdentityError` (HTTP 401, code `AUTHENTICATION_REQUIRED`) —
  regardless of whether the headers were sent — before any header value is even
  inspected (see `tests/security/test_production_disables_development_identity.py`).
  There is no code path by which these headers grant access outside of
  local/test/development.
* **Still validated against the database, not just well-formed.** A syntactically valid
  header UUID is not sufficient: `build_request_context` looks up the user, organization,
  and membership rows and enforces they exist and are active (not suspended/archived/
  removed) before building a `RequestContext`. A forged UUID for a nonexistent user is
  rejected the same as a missing header.
* **No role/permission headers are ever honored.** There is no
  `X-ContextForge-Role`/`X-ContextForge-Permissions` header at all — permissions are
  always derived server-side from the database (`RoleAssignment` rows), never from
  anything the client sends. If a client sends such a header anyway, it is silently
  ignored by every endpoint (see `tests/security/test_role_headers_ignored.py`).
* **Missing headers fail closed.** No user id header → `401` before touching the
  database (`_require_uuid_header`); the organization id header is required for any
  endpoint that needs tenancy context.
* **Isolated from the authorization model.** `build_request_context` is the *only* code
  path that turns headers into a `RequestContext`; `RequestContext`,
  `RequestContext.has_permission`, and every application service downstream have no
  knowledge of *how* the caller was identified. Replacing development identity with real
  session/JWT-based authentication later only requires changing what feeds
  `build_request_context`'s `user_id`/`organization_id` arguments — not the function
  itself, not the services, not the RBAC model.
* `scripts/bootstrap_dev.py` exists specifically to make this usable end-to-end locally:
  it seeds a deterministic admin user + organization and prints the exact header values
  to use.

## Consequences

Positive:

* Every tenancy, RBAC, and audit code path in this commit is exercised by real HTTP
  requests through the real dependency-injection chain, not mocked — the
  `tests/api/` and `tests/security/` suites are meaningful today, not deferred.
* The blast radius of "this is not real auth" is contained to one function
  (`build_request_context`) and one dependency module
  (`api/dependencies/identity.py`); swapping in OIDC/JWT later does not require touching
  application services, domain entities, or RBAC logic.
* Fails safe by construction: three independent layers (environment gate, presence
  check, DB-backed active-status check) all have to be bypassed for an unauthenticated
  caller to get a `RequestContext`, and the environment gate alone makes this impossible
  outside local/test/development regardless of the other two.

Negative:

* There is, by definition, no cryptographic proof of identity — anyone who can reach the
  API in a non-production environment can claim to be any user id they can guess/enumerate.
  This is only acceptable because production and staging disable it entirely; it must
  never be relaxed for those environments.
* Two more headers to remember when calling the API locally (mitigated by
  `bootstrap-dev` printing them, and by `docs`/README examples always including them).
* Adds one more thing to delete/replace when real authentication ships — tracked
  explicitly in the README's "Auth roadmap" section so it is not forgotten.

## Alternatives considered

* **Hardcode a single fake "dev user" with no headers at all** — rejected: this commit's
  whole point is to exercise multi-tenancy and per-user RBAC; a single implicit identity
  cannot express "act as the admin" vs. "act as the viewer" in the same test suite/`curl`
  session.
* **Build a minimal real JWT/session login now** — rejected as premature: no real
  identity provider integration exists yet, and building a throwaway one just to satisfy
  interim testing needs would be wasted, disposable work compared to headers that map
  1:1 onto "who" and "which org," and that can be turned off with one environment check.
* **Basic auth with a shared local password** — rejected: still would not let a caller
  choose *which* user/organization to act as without inventing yet another header/param,
  so it would have bought nothing over the header approach while looking more like real
  auth (risking someone mistakenly relying on it as if it were).
