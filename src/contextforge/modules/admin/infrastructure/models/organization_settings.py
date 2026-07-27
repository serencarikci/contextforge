from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from contextforge.infrastructure.database.base import Base, TimestampMixin


class OrganizationSettingsModel(Base, TimestampMixin):
    __tablename__ = "organization_settings"

    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    quotas: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    defaults: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    feature_overrides: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"OrganizationSettingsModel(organization_id={self.organization_id!s})"
