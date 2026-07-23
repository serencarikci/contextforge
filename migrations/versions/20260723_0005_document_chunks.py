"""Create document_chunks table for CFG-004 semantic chunking pipeline.

Revision ID: 20260723_0005
Revises: 20260723_0004
Create Date: 2026-07-23 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260723_0005"
down_revision: str | None = "20260723_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parse_result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_space_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=False),
        sa.Column("char_end", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "embedding_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
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
            name=op.f("fk_document_chunks_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_document_chunks_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parse_result_id"],
            ["document_parse_results.id"],
            name=op.f("fk_document_chunks_parse_result_id_document_parse_results"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_space_id"],
            ["knowledge_spaces.id"],
            name=op.f("fk_document_chunks_knowledge_space_id_knowledge_spaces"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_chunks")),
        sa.UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_document_chunks_document_id_chunk_index",
        ),
    )
    op.create_index(
        "ix_document_chunks_organization_id_knowledge_space_id",
        "document_chunks",
        ["organization_id", "knowledge_space_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_chunks_organization_id_embedding_status",
        "document_chunks",
        ["organization_id", "embedding_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_chunks_organization_id_embedding_status",
        table_name="document_chunks",
    )
    op.drop_index(
        "ix_document_chunks_organization_id_knowledge_space_id",
        table_name="document_chunks",
    )
    op.drop_table("document_chunks")
