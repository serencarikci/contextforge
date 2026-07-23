"""Organization ORM model."""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from contextforge.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from contextforge.modules.identity_access.domain.enums import OrganizationStatus


class OrganizationModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A tenant organization."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=OrganizationStatus.ACTIVE.value
    )

    def __repr__(self) -> str:
        return f"OrganizationModel(id={self.id!s}, slug={self.slug!r})"
