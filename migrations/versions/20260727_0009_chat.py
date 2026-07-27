from __future__ import annotations

import uuid as _uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import insert as pg_insert

revision: str = "20260727_0009"
down_revision: str | None = "20260724_0008"
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
    ("chat:use", "Use enterprise chat conversations"),
    ("chat:manage", "Manage chat conversations, analytics, and moderation"),
)

NEW_PERMISSION_CODES: tuple[str, ...] = tuple(code for code, _ in NEW_PERMISSIONS)

NEW_ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "platform_admin": (),
    "organization_admin": ("chat:use", "chat:manage"),
    "project_manager": ("chat:use",),
    "developer": ("chat:use",),
    "support_agent": ("chat:use",),
    "knowledge_manager": ("chat:use", "chat:manage"),
    "viewer": ("chat:use",),
}


def upgrade() -> None:
    _create_conversations()
    _create_conversation_participants()
    _create_conversation_knowledge_spaces()
    _create_chat_messages()
    _create_message_citations()
    _create_conversation_memories()
    _create_message_feedback()
    _create_chat_analytics_events()
    _create_full_text_search_columns()
    _seed_chat_rbac_reference_data()


def _create_conversations() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("preferred_language", sa.String(length=8), nullable=False, server_default="auto"),
        sa.Column("detected_language", sa.String(length=8), nullable=True),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "last_activity_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("summary_text", sa.Text(), nullable=True),
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
            name=op.f("fk_conversations_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name=op.f("fk_conversations_owner_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversations")),
    )
    op.create_index(
        "ix_conversations_org_owner_status_activity",
        "conversations",
        ["organization_id", "owner_user_id", "status", "last_activity_at"],
    )


def _create_conversation_participants() -> None:
    op.create_table(
        "conversation_participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="participant"),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_conversation_participants_conversation_id_conversations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_conversation_participants_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_conversation_participants_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversation_participants")),
        sa.UniqueConstraint(
            "conversation_id",
            "user_id",
            name="uq_conversation_participants_conversation_user",
        ),
    )
    op.create_index(
        "ix_conversation_participants_organization_id",
        "conversation_participants",
        ["organization_id"],
    )


def _create_conversation_knowledge_spaces() -> None:
    op.create_table(
        "conversation_knowledge_spaces",
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_space_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_conversation_knowledge_spaces_conversation_id_conversations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_space_id"],
            ["knowledge_spaces.id"],
            name=op.f("fk_conversation_knowledge_spaces_knowledge_space_id_knowledge_spaces"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_conversation_knowledge_spaces_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "conversation_id",
            "knowledge_space_id",
            "organization_id",
            name=op.f("pk_conversation_knowledge_spaces"),
        ),
    )
    op.create_index(
        "ix_conversation_knowledge_spaces_knowledge_space_id",
        "conversation_knowledge_spaces",
        ["knowledge_space_id"],
    )


def _create_chat_messages() -> None:
    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="completed"),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("language", sa.String(length=8), nullable=True),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("parent_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model_name", sa.String(length=200), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retrieval_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
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
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_chat_messages_conversation_id_conversations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_chat_messages_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_message_id"],
            ["chat_messages.id"],
            name=op.f("fk_chat_messages_parent_message_id_chat_messages"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_messages")),
        sa.UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_chat_messages_organization_idempotency_key",
        ),
        sa.UniqueConstraint(
            "conversation_id",
            "sequence_no",
            name="uq_chat_messages_conversation_sequence",
        ),
    )
    op.create_index(
        "ix_chat_messages_conversation_id_sequence_no",
        "chat_messages",
        ["conversation_id", "sequence_no"],
    )
    op.create_index(
        "ix_chat_messages_organization_id_status",
        "chat_messages",
        ["organization_id", "status"],
    )


def _create_message_citations() -> None:
    op.create_table(
        "message_citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_title", sa.String(length=200), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_space_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=False, server_default=""),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["chat_messages.id"],
            name=op.f("fk_message_citations_message_id_chat_messages"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_message_citations_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_message_citations_document_id_documents"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["document_chunks.id"],
            name=op.f("fk_message_citations_chunk_id_document_chunks"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_space_id"],
            ["knowledge_spaces.id"],
            name=op.f("fk_message_citations_knowledge_space_id_knowledge_spaces"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_message_citations")),
    )
    op.create_index("ix_message_citations_message_id", "message_citations", ["message_id"])
    op.create_index(
        "ix_message_citations_organization_id", "message_citations", ["organization_id"]
    )


def _create_conversation_memories() -> None:
    op.create_table(
        "conversation_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("covered_until_sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_estimate", sa.Integer(), nullable=False, server_default="0"),
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
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_conversation_memories_conversation_id_conversations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_conversation_memories_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversation_memories")),
    )
    op.create_index(
        "ix_conversation_memories_conversation_id",
        "conversation_memories",
        ["conversation_id"],
        unique=True,
    )


def _create_message_feedback() -> None:
    op.create_table(
        "message_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.String(length=10), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=30), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "score IS NULL OR (score >= 1 AND score <= 5)",
            name=op.f("ck_message_feedback_score_range"),
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["chat_messages.id"],
            name=op.f("fk_message_feedback_message_id_chat_messages"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_message_feedback_conversation_id_conversations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_message_feedback_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_message_feedback_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_message_feedback")),
        sa.UniqueConstraint("message_id", "user_id", name="uq_message_feedback_message_user"),
    )
    op.create_index("ix_message_feedback_conversation_id", "message_feedback", ["conversation_id"])
    op.create_index("ix_message_feedback_organization_id", "message_feedback", ["organization_id"])


def _create_chat_analytics_events() -> None:
    op.create_table(
        "chat_analytics_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column(
            "payload",
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
            name=op.f("fk_chat_analytics_events_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_chat_analytics_events_conversation_id_conversations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["chat_messages.id"],
            name=op.f("fk_chat_analytics_events_message_id_chat_messages"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_chat_analytics_events_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_analytics_events")),
    )
    op.create_index(
        "ix_chat_analytics_events_org_type_created",
        "chat_analytics_events",
        ["organization_id", "event_type", "created_at"],
    )


def _create_full_text_search_columns() -> None:
    op.execute(
        "ALTER TABLE chat_messages "
        "ADD COLUMN content_tsv tsvector "
        "GENERATED ALWAYS AS (to_tsvector('simple', coalesce(content, ''))) STORED"
    )
    op.create_index(
        "ix_chat_messages_content_tsv",
        "chat_messages",
        ["content_tsv"],
        postgresql_using="gin",
    )
    op.execute(
        "ALTER TABLE conversations "
        "ADD COLUMN title_tsv tsvector "
        "GENERATED ALWAYS AS (to_tsvector('simple', coalesce(title, ''))) STORED"
    )
    op.create_index(
        "ix_conversations_title_tsv",
        "conversations",
        ["title_tsv"],
        postgresql_using="gin",
    )


def _seed_chat_rbac_reference_data() -> None:
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

    op.drop_index("ix_conversations_title_tsv", table_name="conversations")
    op.execute("ALTER TABLE conversations DROP COLUMN title_tsv")
    op.drop_index("ix_chat_messages_content_tsv", table_name="chat_messages")
    op.execute("ALTER TABLE chat_messages DROP COLUMN content_tsv")

    op.drop_index("ix_chat_analytics_events_org_type_created", table_name="chat_analytics_events")
    op.drop_table("chat_analytics_events")

    op.drop_index("ix_message_feedback_organization_id", table_name="message_feedback")
    op.drop_index("ix_message_feedback_conversation_id", table_name="message_feedback")
    op.drop_table("message_feedback")

    op.drop_index("ix_conversation_memories_conversation_id", table_name="conversation_memories")
    op.drop_table("conversation_memories")

    op.drop_index("ix_message_citations_organization_id", table_name="message_citations")
    op.drop_index("ix_message_citations_message_id", table_name="message_citations")
    op.drop_table("message_citations")

    op.drop_index("ix_chat_messages_organization_id_status", table_name="chat_messages")
    op.drop_index("ix_chat_messages_conversation_id_sequence_no", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index(
        "ix_conversation_knowledge_spaces_knowledge_space_id",
        table_name="conversation_knowledge_spaces",
    )
    op.drop_table("conversation_knowledge_spaces")

    op.drop_index(
        "ix_conversation_participants_organization_id",
        table_name="conversation_participants",
    )
    op.drop_table("conversation_participants")

    op.drop_index("ix_conversations_org_owner_status_activity", table_name="conversations")
    op.drop_table("conversations")
