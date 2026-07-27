from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from contextforge.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from contextforge.shared.utilities.datetime import utc_now


class RetentionPolicyModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "retention_policies"
    __table_args__ = (
        Index(
            "uq_retention_policies_global_resource",
            "resource_type",
            unique=True,
            postgresql_where=text("organization_id IS NULL"),
        ),
        Index(
            "uq_retention_policies_organization_resource",
            "organization_id",
            "resource_type",
            unique=True,
            postgresql_where=text("organization_id IS NOT NULL"),
        ),
    )

    organization_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    soft_delete_first: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return (
            f"RetentionPolicyModel(id={self.id!s}, resource_type={self.resource_type!r}, "
            f"enabled={self.enabled!r})"
        )


class RetentionRunModel(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "retention_runs"
    __table_args__ = (Index("ix_retention_runs_policy_id_started_at", "policy_id", "started_at"),)

    policy_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("retention_policies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    def __repr__(self) -> str:
        return (
            f"RetentionRunModel(id={self.id!s}, policy_id={self.policy_id!s}, "
            f"status={self.status!r})"
        )
