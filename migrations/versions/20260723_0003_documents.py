"""Create documents table; seed document permissions and role mappings.

Revision ID: 20260723_0003
Revises: 20260723_0002
Create Date: 2026-07-23 00:00:00

Creates the ``documents`` table: metadata for files whose bytes live in
object storage (MinIO). Foreign keys to ``organizations``, ``knowledge_spaces``,
and ``users`` all use ``ondelete="RESTRICT"``, consistent with the rest of the
tenant-scoped schema.

Seed data (upgrade only)
-------------------------
This migration seeds only the *new* RBAC reference rows introduced for
documents -- it does not touch the reference data seeded by
``20260723_0002``:

- the four ``document:*`` permissions (``document:create``, ``document:read``,
  ``document:update``, ``document:delete``)
- the corresponding ``role_permissions`` mappings for system roles that
  receive document permissions (``organization_admin`` gets all four via the
  "org admin has every permission" convention; ``project_manager`` and
  ``knowledge_manager`` get all four; ``developer`` gets create/read/update;
  ``support_agent`` and ``viewer`` get read only; ``platform_admin`` gets
  none, matching ``20260723_0002``)

Inserts use ``INSERT ... ON CONFLICT DO NOTHING`` so this migration is safe
to re-run against a database that already has these rows (e.g. if seeded
out-of-band), matching the "idempotent insert" requirement for additive
migrations.

Permission ids are deterministic (``uuid.uuid5`` over the same fixed
namespace as ``20260723_0002`` -- see
``contextforge.shared.constants.rbac.permission_id`` / ``system_role_id``).

Downgrade
---------
Downgrade removes exactly what upgrade added: the seeded ``role_permissions``
rows for the new document permission codes, the four ``document:*``
permissions themselves, and the ``documents`` table. It does not touch any
other RBAC reference data.
"""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import insert as pg_insert

revision: str = "20260723_0003"
down_revision: str | None = "20260723_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

try:
    from contextforge.shared.constants.rbac import permission_id, system_role_id
except ImportError:  # pragma: no cover
    _RBAC_UUID_NAMESPACE = _uuid.UUID("6f2a9b4e-2c3f-4b8a-9d1e-8a2b6f4c1e3a")

    def permission_id(code: str) -> _uuid.UUID:
        return _uuid.uuid5(_RBAC_UUID_NAMESPACE, f"permission:{code}")

    def system_role_id(code: str) -> _uuid.UUID:
        return _uuid.uuid5(_RBAC_UUID_NAMESPACE, f"role:{code}")


NEW_PERMISSIONS: tuple[tuple[str, str], ...] = (
    ("document:create", "Create documents"),
    ("document:read", "Read documents"),
    ("document:update", "Update documents"),
    ("document:delete", "Delete documents"),
)

NEW_PERMISSION_CODES: tuple[str, ...] = tuple(code for code, _ in NEW_PERMISSIONS)

NEW_ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "platform_admin": (),
    "organization_admin": (
        "document:create",
        "document:read",
        "document:update",
        "document:delete",
    ),
    "project_manager": (
        "document:create",
        "document:read",
        "document:update",
        "document:delete",
    ),
    "developer": ("document:create", "document:read", "document:update"),
    "support_agent": ("document:read",),
    "knowledge_manager": (
        "document:create",
        "document:read",
        "document:update",
        "document:delete",
    ),
    "viewer": ("document:read",),
}


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_space_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
            name=op.f("fk_documents_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_space_id"],
            ["knowledge_spaces.id"],
            name=op.f("fk_documents_knowledge_space_id_knowledge_spaces"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name=op.f("fk_documents_uploaded_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
    )
    op.create_index(
        "ix_documents_organization_id_knowledge_space_id",
        "documents",
        ["organization_id", "knowledge_space_id"],
    )
    op.create_index(
        "ix_documents_organization_id_status",
        "documents",
        ["organization_id", "status"],
    )

    _seed_document_rbac_reference_data()


def _seed_document_rbac_reference_data() -> None:
    """Insert the four ``document:*`` permissions and their role mappings.

    Idempotent: uses ``ON CONFLICT DO NOTHING`` so re-running against a
    database that already has these rows is a no-op.
    """
    permissions_table = sa.table(
        "permissions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String),
        sa.column("description", sa.Text),
    )
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("role_id", postgresql.UUID(as_uuid=True)),
        sa.column("permission_id", postgresql.UUID(as_uuid=True)),
    )
    roles_table = sa.table(
        "roles",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String),
    )

    connection = op.get_bind()

    permission_rows = [
        {"id": permission_id(code), "code": code, "description": description}
        for code, description in NEW_PERMISSIONS
    ]
    connection.execute(
        pg_insert(permissions_table)
        .values(permission_rows)
        .on_conflict_do_nothing(index_elements=["code"])
    )

    role_codes_present = {
        row[0] for row in connection.execute(sa.select(roles_table.c.code)).fetchall()
    }

    role_permission_rows = [
        {"role_id": system_role_id(role_code), "permission_id": permission_id(perm_code)}
        for role_code, perm_codes in NEW_ROLE_PERMISSIONS.items()
        for perm_code in perm_codes
        if role_code in role_codes_present
    ]
    if role_permission_rows:
        connection.execute(
            pg_insert(role_permissions_table)
            .values(role_permission_rows)
            .on_conflict_do_nothing(index_elements=["role_id", "permission_id"])
        )


def downgrade() -> None:
    connection = op.get_bind()

    permissions_table = sa.table(
        "permissions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String),
    )
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("role_id", postgresql.UUID(as_uuid=True)),
        sa.column("permission_id", postgresql.UUID(as_uuid=True)),
    )

    new_permission_ids = [permission_id(code) for code in NEW_PERMISSION_CODES]
    connection.execute(
        role_permissions_table.delete().where(
            role_permissions_table.c.permission_id.in_(new_permission_ids)
        )
    )
    connection.execute(
        permissions_table.delete().where(permissions_table.c.code.in_(NEW_PERMISSION_CODES))
    )

    op.drop_index("ix_documents_organization_id_status", table_name="documents")
    op.drop_index("ix_documents_organization_id_knowledge_space_id", table_name="documents")
    op.drop_table("documents")
