from __future__ import annotations

import uuid as _uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from migrations.helpers import existing_role_codes
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import insert as pg_insert

revision: str = "20260724_0008"
down_revision: str | None = "20260723_0007"
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


NEW_PERMISSIONS: tuple[tuple[str, str], ...] = (("rag:query", "Query the RAG retrieval engine"),)

NEW_PERMISSION_CODES: tuple[str, ...] = tuple(code for code, _ in NEW_PERMISSIONS)

NEW_ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "platform_admin": (),
    "organization_admin": ("rag:query",),
    "project_manager": ("rag:query",),
    "developer": ("rag:query",),
    "support_agent": ("rag:query",),
    "knowledge_manager": ("rag:query",),
    "viewer": ("rag:query",),
}


def upgrade() -> None:
    _seed_rag_rbac_reference_data()


def _seed_rag_rbac_reference_data() -> None:
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

    role_codes_present = existing_role_codes(
        connection,
        roles_table,
        fallback=NEW_ROLE_PERMISSIONS,
    )

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
    permission_ids = [permission_id(code) for code in NEW_PERMISSION_CODES]
    connection.execute(
        sa.delete(role_permissions_table).where(
            role_permissions_table.c.permission_id.in_(permission_ids)
        )
    )
    connection.execute(
        sa.delete(permissions_table).where(permissions_table.c.code.in_(NEW_PERMISSION_CODES))
    )
