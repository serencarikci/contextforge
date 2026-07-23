"""Create identity and knowledge domain tables; seed RBAC reference data.

Revision ID: 20260723_0002
Revises: 20260723_0001
Create Date: 2026-07-23 00:00:00

Creates the core tenancy/identity/knowledge schema:

- ``users``, ``organizations``, ``organization_memberships``
- ``permissions``, ``roles``, ``role_permissions``, ``role_assignments``
- ``customers``, ``projects``
- ``knowledge_spaces``, ``knowledge_space_memberships``
- ``audit_events``

All foreign keys to tenant business data use ``ondelete="RESTRICT"`` -- there
is no cascading delete of business entities in this schema.

Seed data (upgrade only)
-------------------------
This migration seeds the RBAC reference catalog:

- every permission in ``contextforge.shared.constants.rbac.PERMISSIONS``
- every system role in ``contextforge.shared.constants.rbac.SYSTEM_ROLES``
  (``organization_id IS NULL``, ``is_system = true``)
- the ``role_permissions`` mappings for assignable system roles, per
  ``contextforge.shared.constants.rbac.ROLE_PERMISSIONS`` (``platform_admin``
  intentionally has no rows -- it is not assignable through org-scoped APIs)

Permission and system role primary keys are deterministic: they are derived
with ``uuid.uuid5`` over a fixed namespace and the permission/role code (see
``contextforge.shared.constants.rbac.permission_id`` / ``system_role_id``), so
the same code always resolves to the same UUID across environments and test
runs. If the application package cannot be imported in the migration's
execution context, the same data and ID-derivation scheme are hardcoded below
as a fallback.

Downgrade
---------
Downgrade drops every table created here in reverse dependency order. The
seeded reference data (permissions, system roles, and their
``role_permissions`` mappings) lives only inside these tables, so dropping the
tables implicitly removes the seed data -- there is no separate "unseed" step.
"""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260723_0002"
down_revision: str | None = "20260723_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

try:
    from contextforge.shared.constants.rbac import (
        PERMISSIONS,
        ROLE_PERMISSIONS,
        SYSTEM_ROLES,
        permission_id,
        system_role_id,
    )
except ImportError:  # pragma: no cover - fallback when the app package isn't importable
    _RBAC_UUID_NAMESPACE = _uuid.UUID("6f2a9b4e-2c3f-4b8a-9d1e-8a2b6f4c1e3a")

    def permission_id(code: str) -> _uuid.UUID:
        return _uuid.uuid5(_RBAC_UUID_NAMESPACE, f"permission:{code}")

    def system_role_id(code: str) -> _uuid.UUID:
        return _uuid.uuid5(_RBAC_UUID_NAMESPACE, f"role:{code}")

    PERMISSIONS: tuple[tuple[str, str], ...] = (
        ("organization:read", "Read organization details"),
        ("organization:update", "Update organization details"),
        ("organization:manage_members", "Manage organization memberships"),
        ("user:read", "Read user profiles within membership context"),
        ("user:manage", "Manage user lifecycle within membership context"),
        ("role:read", "Read roles and assignments"),
        ("role:manage", "Manage organization roles and assignments"),
        ("customer:create", "Create customers"),
        ("customer:read", "Read customers"),
        ("customer:update", "Update customers"),
        ("customer:archive", "Archive customers"),
        ("project:create", "Create projects"),
        ("project:read", "Read projects"),
        ("project:update", "Update projects"),
        ("project:archive", "Archive projects"),
        ("project:manage_members", "Manage project-scoped memberships"),
        ("knowledge_space:create", "Create knowledge spaces"),
        ("knowledge_space:read", "Read knowledge spaces"),
        ("knowledge_space:update", "Update knowledge spaces"),
        ("knowledge_space:archive", "Archive knowledge spaces"),
        ("knowledge_space:manage_members", "Manage knowledge-space memberships"),
        ("audit:read", "Read audit events"),
    )

    SYSTEM_ROLES: tuple[tuple[str, str, str], ...] = (
        ("platform_admin", "Platform Admin", "Platform-level administration"),
        ("organization_admin", "Organization Admin", "Full organization administration"),
        ("project_manager", "Project Manager", "Manage projects and knowledge spaces"),
        ("developer", "Developer", "Read project and knowledge resources"),
        ("support_agent", "Support Agent", "Read customer and project context"),
        ("knowledge_manager", "Knowledge Manager", "Manage knowledge spaces"),
        ("viewer", "Viewer", "Read-only access to tenant resources"),
    )

    _ORG_ADMIN_PERMS = tuple(code for code, _ in PERMISSIONS)
    _PROJECT_MANAGER_PERMS = (
        "project:create",
        "project:read",
        "project:update",
        "project:archive",
        "project:manage_members",
        "customer:read",
        "knowledge_space:create",
        "knowledge_space:read",
        "knowledge_space:update",
        "knowledge_space:archive",
        "knowledge_space:manage_members",
    )
    _READ_PERMS = ("customer:read", "project:read", "knowledge_space:read")
    _KNOWLEDGE_MANAGER_PERMS = (
        "customer:read",
        "project:read",
        "knowledge_space:create",
        "knowledge_space:read",
        "knowledge_space:update",
        "knowledge_space:archive",
        "knowledge_space:manage_members",
    )
    ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
        "platform_admin": (),
        "organization_admin": _ORG_ADMIN_PERMS,
        "project_manager": _PROJECT_MANAGER_PERMS,
        "developer": _READ_PERMS,
        "support_agent": _READ_PERMS,
        "knowledge_manager": _KNOWLEDGE_MANAGER_PERMS,
        "viewer": _READ_PERMS,
    }


def upgrade() -> None:

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("preferred_language", sa.String(length=10), nullable=False),
        sa.Column(
            "is_platform_admin",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )

    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
        sa.UniqueConstraint("slug", name=op.f("uq_organizations_slug")),
    )

    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_permissions")),
        sa.UniqueConstraint("code", name=op.f("uq_permissions_code")),
    )

    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_roles_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
    )

    op.create_index(
        "uq_roles_code_system",
        "roles",
        ["code"],
        unique=True,
        postgresql_where=sa.text("organization_id IS NULL"),
    )
    op.create_index(
        "uq_roles_organization_id_code",
        "roles",
        ["organization_id", "code"],
        unique=True,
        postgresql_where=sa.text("organization_id IS NOT NULL"),
    )

    op.create_table(
        "organization_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_organization_memberships_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_organization_memberships_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organization_memberships")),
        sa.UniqueConstraint(
            "organization_id",
            "user_id",
            name=op.f("uq_organization_memberships_org_user"),
        ),
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name=op.f("fk_role_permissions_role_id_roles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            name=op.f("fk_role_permissions_permission_id_permissions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("role_id", "permission_id", name=op.f("pk_role_permissions")),
    )

    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_customers_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_customers")),
        sa.UniqueConstraint(
            "organization_id", "code", name=op.f("uq_customers_organization_id_code")
        ),
    )

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("key", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("default_language", sa.String(length=10), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_projects_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name=op.f("fk_projects_customer_id_customers"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
        sa.UniqueConstraint("organization_id", "key", name=op.f("uq_projects_organization_id_key")),
    )

    op.create_table(
        "knowledge_spaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_knowledge_spaces_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_knowledge_spaces_project_id_projects"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_spaces")),
        sa.UniqueConstraint(
            "organization_id",
            "slug",
            name=op.f("uq_knowledge_spaces_organization_id_slug"),
        ),
    )

    op.create_table(
        "role_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("membership_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("knowledge_space_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_role_assignments_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["membership_id"],
            ["organization_memberships.id"],
            name=op.f("fk_role_assignments_membership_id_organization_memberships"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name=op.f("fk_role_assignments_role_id_roles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_role_assignments_project_id_projects"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_space_id"],
            ["knowledge_spaces.id"],
            name=op.f("fk_role_assignments_knowledge_space_id_knowledge_spaces"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_role_assignments")),
        sa.CheckConstraint(
            "(project_id IS NULL AND knowledge_space_id IS NULL) OR "
            "(project_id IS NOT NULL AND knowledge_space_id IS NULL) OR "
            "(project_id IS NULL AND knowledge_space_id IS NOT NULL)",
            name=op.f("ck_role_assignments_exclusive_scope"),
        ),
    )

    op.create_index(
        "uq_role_assignments_membership_role_scope",
        "role_assignments",
        [
            "membership_id",
            "role_id",
            sa.text("COALESCE(project_id, '00000000-0000-0000-0000-000000000000'::uuid)"),
            sa.text("COALESCE(knowledge_space_id, '00000000-0000-0000-0000-000000000000'::uuid)"),
        ],
        unique=True,
    )

    op.create_table(
        "knowledge_space_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_space_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("membership_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("access_level", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_knowledge_space_memberships_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_space_id"],
            ["knowledge_spaces.id"],
            name=op.f("fk_knowledge_space_memberships_knowledge_space_id_knowledge_spaces"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["membership_id"],
            ["organization_memberships.id"],
            name=op.f("fk_knowledge_space_memberships_membership_id_organization_memberships"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_space_memberships")),
        sa.UniqueConstraint(
            "knowledge_space_id",
            "membership_id",
            name=op.f("uq_knowledge_space_memberships_ks_membership"),
        ),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_audit_events_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_audit_events_actor_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index(
        "ix_audit_events_organization_id_occurred_at",
        "audit_events",
        ["organization_id", "occurred_at"],
    )
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_resource_type", "audit_events", ["resource_type"])

    _seed_rbac_reference_data()


def _seed_rbac_reference_data() -> None:
    """Insert the canonical permission/system-role catalog and mappings."""
    permissions_table = sa.table(
        "permissions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String),
        sa.column("description", sa.Text),
    )
    roles_table = sa.table(
        "roles",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("organization_id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("is_system", sa.Boolean),
    )
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("role_id", postgresql.UUID(as_uuid=True)),
        sa.column("permission_id", postgresql.UUID(as_uuid=True)),
    )

    permission_rows = [
        {"id": permission_id(str(code)), "code": str(code), "description": description}
        for code, description in PERMISSIONS
    ]
    op.bulk_insert(permissions_table, permission_rows)

    role_rows = [
        {
            "id": system_role_id(str(code)),
            "organization_id": None,
            "code": str(code),
            "name": name,
            "description": description,
            "is_system": True,
        }
        for code, name, description in SYSTEM_ROLES
    ]
    op.bulk_insert(roles_table, role_rows)

    role_permission_rows = [
        {"role_id": system_role_id(str(role_code)), "permission_id": permission_id(str(perm_code))}
        for role_code, perm_codes in ROLE_PERMISSIONS.items()
        for perm_code in perm_codes
    ]
    if role_permission_rows:
        op.bulk_insert(role_permissions_table, role_permission_rows)


def downgrade() -> None:

    op.drop_table("audit_events")
    op.drop_table("knowledge_space_memberships")
    op.drop_index("uq_role_assignments_membership_role_scope", table_name="role_assignments")
    op.drop_table("role_assignments")
    op.drop_table("knowledge_spaces")
    op.drop_table("projects")
    op.drop_table("customers")
    op.drop_table("role_permissions")
    op.drop_table("organization_memberships")
    op.drop_index("uq_roles_organization_id_code", table_name="roles")
    op.drop_index("uq_roles_code_system", table_name="roles")
    op.drop_table("roles")
    op.drop_table("permissions")
    op.drop_table("organizations")
    op.drop_table("users")
