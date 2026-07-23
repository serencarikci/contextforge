"""Add embedding metadata columns to document_chunks for CFG-005.

Revision ID: 20260723_0006
Revises: 20260723_0005
Create Date: 2026-07-23 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260723_0006"
down_revision: str | None = "20260723_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("document_chunks", sa.Column("language", sa.String(length=16), nullable=True))
    op.add_column(
        "document_chunks",
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
    )
    op.add_column("document_chunks", sa.Column("embedding_dimensions", sa.Integer(), nullable=True))
    op.add_column(
        "document_chunks",
        sa.Column("embedded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("document_chunks", sa.Column("embedding_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("document_chunks", "embedding_error")
    op.drop_column("document_chunks", "embedded_at")
    op.drop_column("document_chunks", "embedding_dimensions")
    op.drop_column("document_chunks", "embedding_model")
    op.drop_column("document_chunks", "language")
