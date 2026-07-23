"""Document parse result ORM model."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from contextforge.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from contextforge.modules.documents.domain.enums import DocumentParseStatus


class DocumentParseResultModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Persisted parse outcome for a stored document (one row per document)."""

    __tablename__ = "document_parse_results"
    __table_args__ = (
        UniqueConstraint("document_id", name="uq_document_parse_results_document_id"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    format: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DocumentParseStatus.FAILED.value
    )
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    character_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return (
            f"DocumentParseResultModel(id={self.id!s}, document_id={self.document_id!s}, "
            f"status={self.status!r})"
        )
