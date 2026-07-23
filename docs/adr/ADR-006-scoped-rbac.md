# ADR-006: Scoped Role-Based Access Control (RBAC)

- Status: Accepted
- Date: 2026-07-23

## Context

Beyond organization-level tenancy (ADR-005), ContextForge needs finer-grained
authorization: an organization admin should manage everything in their organization, but
a project lead or knowledge-space contributor should only be able to act within the
project or knowledge space they were actually granted access to. Knowledge spaces in
particular need a visibility model (`organization` vs `restricted`) because sensitive
content (e.g., incident playbooks, HR records) must not be readable by every organization
member by default.

A flat "one role per user" model cannot express "admin of Project A, viewer of Project
B" for the same person, so the design needs assignment-level scoping, not just role-level
scoping.

## Decision

Adopt a scoped RBAC model with three building blocks:

1. **Permissions** — fine-grained, colon-namespaced strings (e.g., `customer:read`,
   `project:create`, `knowledge_space:manage_members`, `role:manage`, `audit:read`).
   Permissions are data, not code — they live in `permissions`/`role_permissions` tables,
   seeded declaratively from `contextforge.shared.constants.rbac` by migration (not
   application code), so the canonical catalog has one source of truth.
2. **Roles** — named bundles of permissions. **System roles**
   (`platform_admin`, `organization_admin`, `developer`, `viewer`, ...) are global
   (`organization_id IS NULL`), immutable via the API, and identical across every
   organization. Organizations may additionally define their own custom roles
   (`organization_id` set, `is_system=False`), which *can* be renamed/updated.
3. **Role assignments** — the actual grant, linking an `OrganizationMembership` to a
   `Role` at exactly one scope: organization-wide (`project_id` and
   `knowledge_space_id` both `NULL`), a specific project (`project_id` set), or a
   specific knowledge space (`knowledge_space_id` set). A single assignment can never
   target both a project and a knowledge space at once (enforced as a domain invariant on
   `RoleAssignment`, see `tests/unit/authorization/test_role_assignment_scope.py`).

`RequestContext.permissions` is the union of the caller's *organization-scoped* role
assignments' permissions, plus (only when the request targets a specific
project/knowledge space) that project's/knowledge space's own scoped permissions layered
on top. `has_permission`/`require_permission` check this frozenset; there is no
runtime database lookup during a permission check — everything needed is resolved once
during `build_request_context` (see ADR-007).

**Knowledge-space visibility** is a distinct, additional gate from permissions:

* `visibility=organization` spaces are visible to anyone in the organization who holds
  `knowledge_space:read` — no explicit grant needed.
* `visibility=restricted` spaces require an *explicit* grant — either a
  knowledge-space-scoped role assignment or a `KnowledgeSpaceMembership` row — regardless
  of how broad the caller's organization-wide permissions are. Even an
  `organization_admin` gets `404` on a restricted space they were not explicitly granted
  access to (see `tests/security/test_restricted_knowledge_space_access.py`). Only
  `platform_admin` bypasses this.
* Denial is always `404`, never `403`, so a caller cannot enumerate the existence of
  restricted spaces they cannot see.

The one hardcoded exception is `platform_admin`: `RequestContext.is_platform_admin` (set
from the `User.is_platform_admin` column) bypasses every permission and visibility check.
It cannot be assigned or revoked through the role-assignment API
(`RoleService.assign_role` explicitly rejects assigning the `platform_admin` role code)
— it is a break-glass operator flag set directly on the user record, not a normal RBAC
grant.

## Consequences

Positive:

* Authorization decisions are pure, in-memory set operations against
  `RequestContext.permissions`/`accessible_*_ids` — fast, and trivially unit-testable
  without a database (`tests/unit/authorization/test_request_context.py`).
* The same primitive (`RoleAssignment` + scope) expresses org-wide, per-project, and
  per-knowledge-space grants without three separate tables or code paths.
* Restricted-visibility knowledge spaces get real content isolation, not just a
  permission flag — critical for the "not every employee can read the incident
  playbooks" requirement.

Negative:

* Permissions are computed once at request-context build time; a role change does not
  take effect for a request already in flight (acceptable given request lifetimes are
  short, but worth remembering).
* Two scoping primitives for knowledge spaces (`RoleAssignment` at KS scope, and
  `KnowledgeSpaceMembership`) is slightly more surface area than one; kept both because
  role assignments carry an actual `Role` (bundle of permissions incl. `manage_members`),
  while `KnowledgeSpaceMembership.access_level` is a simpler reader/contributor/manager
  tier for straightforward space membership — collapsing them would have forced every
  knowledge-space grant through the heavier role-assignment machinery.
* Listing organization-wide resources still requires org-level `*:read`; a
  project/knowledge-space-scoped-only grant cannot enumerate everything in the
  organization (e.g., `GET /projects` requires org-level `project:read`, not just access
  to one project) — this is intentional today, but is a rougher edge than per-item
  visibility filtering that may need revisiting once project-scoped listing becomes a
  real product requirement.

## Alternatives considered

* **Single flat role per user (no scoping)** — rejected: cannot express "admin of one
  project, viewer of another" without proliferating roles like `project_a_admin`.
* **Attribute-based access control (ABAC) / policy engine (e.g., OPA)** — rejected for
  now as premature: the permission surface is small and well-understood; introducing an
  external policy engine adds an operational dependency this stage does not need.
* **Permission checks embedded as SQL row-level security (RLS) policies** — rejected:
  would duplicate the same logic in two languages (SQL policies and Python) and make
  `RequestContext`'s in-memory checks (needed for non-DB-backed authorization, like KS
  visibility branching) redundant rather than authoritative.
