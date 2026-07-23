"""Ingestion job ORM model."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from contextforge.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from contextforge.modules.ingestion.domain.enums import IngestionJobStatus, IngestionJobStep


class IngestionJobModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Persisted background ingestion job."""

    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        Index("ix_ingestion_jobs_organization_id_status", "organization_id", "status"),
        Index("ix_ingestion_jobs_document_id", "document_id"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    knowledge_space_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge_spaces.id", ondelete="RESTRICT"),
        nullable=False,
    )
    requested_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=IngestionJobStatus.PENDING.value
    )
    current_step: Mapped[str] = mapped_column(
        String(20), nullable=False, default=IngestionJobStep.QUEUED.value
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return (
            f"IngestionJobModel(id={self.id!s}, document_id={self.document_id!s}, "
            f"status={self.status!r})"
        )
