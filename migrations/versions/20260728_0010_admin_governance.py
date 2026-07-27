from __future__ import annotations

import uuid as _uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import insert as pg_insert

revision: str = "20260728_0010"
down_revision: str | None = "20260727_0009"
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
    ("admin:dashboard", "View the administration dashboard"),
    ("admin:users", "Administer users across the organization"),
    ("admin:organizations", "Administer organization settings and quotas"),
    ("admin:roles", "Administer custom role permission sets"),
    ("admin:knowledge_spaces", "View knowledge-space administration statistics"),
    ("admin:documents", "Run document administration and bulk operations"),
    ("admin:ingestion", "Administer the ingestion queue and job lifecycle"),
    ("admin:audit", "Export the audit trail"),
    ("admin:usage", "View usage, token, and cost analytics"),
    ("admin:prompts", "Administer versioned prompt templates"),
    ("admin:llm", "Administer LLM provider configurations"),
    ("admin:settings", "Administer organization settings and feature flags"),
    ("admin:ops", "View operational health and worker status"),
    ("admin:retention", "Administer data retention policies and runs"),
)

NEW_PERMISSION_CODES: tuple[str, ...] = tuple(code for code, _ in NEW_PERMISSIONS)

_ALL_ADMIN = tuple(NEW_PERMISSION_CODES)

NEW_ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "platform_admin": (),
    "organization_admin": _ALL_ADMIN,
    "project_manager": (),
    "developer": (),
    "support_agent": (),
    "knowledge_manager": (
        "admin:knowledge_spaces",
        "admin:documents",
        "admin:ingestion",
    ),
    "viewer": (),
}


def upgrade() -> None:
    op.create_table(
        "organization_settings",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "quotas",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "defaults",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "feature_overrides",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
            name=op.f("fk_organization_settings_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("organization_id", name=op.f("pk_organization_settings")),
    )

    op.create_table(
        "feature_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "enabled_globally", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
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
            name=op.f("fk_feature_flags_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_feature_flags")),
    )
    op.create_index(
        "uq_feature_flags_key_global",
        "feature_flags",
        ["key"],
        unique=True,
        postgresql_where=sa.text("organization_id IS NULL"),
    )
    op.create_index(
        "uq_feature_flags_key_organization",
        "feature_flags",
        ["key", "organization_id"],
        unique=True,
        postgresql_where=sa.text("organization_id IS NOT NULL"),
    )

    op.create_table(
        "prompt_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
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
            ["created_by"],
            ["users.id"],
            name=op.f("fk_prompt_templates_created_by_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_prompt_templates_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_templates")),
    )
    op.create_index(
        "uq_prompt_templates_global_identity",
        "prompt_templates",
        ["name", "version", "language"],
        unique=True,
        postgresql_where=sa.text("organization_id IS NULL"),
    )
    op.create_index(
        "uq_prompt_templates_organization_identity",
        "prompt_templates",
        ["organization_id", "name", "version", "language"],
        unique=True,
        postgresql_where=sa.text("organization_id IS NOT NULL"),
    )
    op.create_index(
        "ix_prompt_templates_lookup",
        "prompt_templates",
        ["organization_id", "language", "is_active"],
        unique=False,
    )

    op.create_table(
        "llm_provider_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=True),
        sa.Column("api_key_ciphertext", sa.Text(), nullable=True),
        sa.Column("api_key_hint", sa.String(length=20), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=False, server_default=sa.text("0.2")),
        sa.Column("max_tokens", sa.Integer(), nullable=False, server_default=sa.text("1024")),
        sa.Column("timeout_seconds", sa.Float(), nullable=False, server_default=sa.text("60.0")),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default=sa.text("2")),
        sa.Column("rate_limit_rpm", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
            name=op.f("fk_llm_provider_configs_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_llm_provider_configs")),
    )
    op.create_index(
        "uq_llm_provider_configs_global",
        "llm_provider_configs",
        ["provider", "model"],
        unique=True,
        postgresql_where=sa.text("organization_id IS NULL"),
    )
    op.create_index(
        "uq_llm_provider_configs_organization",
        "llm_provider_configs",
        ["organization_id", "provider", "model"],
        unique=True,
        postgresql_where=sa.text("organization_id IS NOT NULL"),
    )
    op.create_index(
        "ix_llm_provider_configs_organization_id",
        "llm_provider_configs",
        ["organization_id"],
        unique=False,
    )

    op.create_table(
        "token_pricing",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=200), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("input_price_per_1k", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("output_price_per_1k", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_token_pricing")),
    )
    op.create_index(
        "ix_token_pricing_provider_model_effective",
        "token_pricing",
        ["provider", "model", "effective_from"],
        unique=False,
    )

    op.create_table(
        "token_usage_daily",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("provider", sa.String(length=200), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "estimated_cost",
            sa.Numeric(precision=18, scale=6),
            nullable=False,
            server_default=sa.text("0"),
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
            name=op.f("fk_token_usage_daily_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_token_usage_daily")),
        sa.UniqueConstraint(
            "organization_id",
            "day",
            "provider",
            "model",
            name="uq_token_usage_daily_org_day_provider_model",
        ),
    )
    op.create_index(
        "ix_token_usage_daily_organization_day",
        "token_usage_daily",
        ["organization_id", "day"],
        unique=False,
    )

    op.create_table(
        "retention_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column(
            "soft_delete_first", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
            name=op.f("fk_retention_policies_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_retention_policies")),
    )
    op.create_index(
        "uq_retention_policies_global_resource",
        "retention_policies",
        ["resource_type"],
        unique=True,
        postgresql_where=sa.text("organization_id IS NULL"),
    )
    op.create_index(
        "uq_retention_policies_organization_resource",
        "retention_policies",
        ["organization_id", "resource_type"],
        unique=True,
        postgresql_where=sa.text("organization_id IS NOT NULL"),
    )

    op.create_table(
        "retention_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_retention_runs_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["policy_id"],
            ["retention_policies.id"],
            name=op.f("fk_retention_runs_policy_id_retention_policies"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_retention_runs")),
    )
    op.create_index(
        "ix_retention_runs_policy_id_started_at",
        "retention_runs",
        ["policy_id", "started_at"],
        unique=False,
    )

    op.add_column(
        "roles",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )

    _seed_admin_rbac_reference_data()


def _seed_admin_rbac_reference_data() -> None:
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
    permission_ids = [permission_id(code) for code in NEW_PERMISSION_CODES]
    connection.execute(
        sa.delete(role_permissions_table).where(
            role_permissions_table.c.permission_id.in_(permission_ids)
        )
    )
    connection.execute(
        sa.delete(permissions_table).where(permissions_table.c.code.in_(NEW_PERMISSION_CODES))
    )

    op.drop_column("roles", "archived_at")

    op.drop_index("ix_retention_runs_policy_id_started_at", table_name="retention_runs")
    op.drop_table("retention_runs")
    op.drop_index("uq_retention_policies_organization_resource", table_name="retention_policies")
    op.drop_index("uq_retention_policies_global_resource", table_name="retention_policies")
    op.drop_table("retention_policies")
    op.drop_index("ix_token_usage_daily_organization_day", table_name="token_usage_daily")
    op.drop_table("token_usage_daily")
    op.drop_index("ix_token_pricing_provider_model_effective", table_name="token_pricing")
    op.drop_table("token_pricing")
    op.drop_index("ix_llm_provider_configs_organization_id", table_name="llm_provider_configs")
    op.drop_index("uq_llm_provider_configs_organization", table_name="llm_provider_configs")
    op.drop_index("uq_llm_provider_configs_global", table_name="llm_provider_configs")
    op.drop_table("llm_provider_configs")
    op.drop_index("ix_prompt_templates_lookup", table_name="prompt_templates")
    op.drop_index("uq_prompt_templates_organization_identity", table_name="prompt_templates")
    op.drop_index("uq_prompt_templates_global_identity", table_name="prompt_templates")
    op.drop_table("prompt_templates")
    op.drop_index("uq_feature_flags_key_organization", table_name="feature_flags")
    op.drop_index("uq_feature_flags_key_global", table_name="feature_flags")
    op.drop_table("feature_flags")
    op.drop_table("organization_settings")
