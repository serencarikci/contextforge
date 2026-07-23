"""Role ORM model.

System roles are shared across all tenants and have ``organization_id IS NULL``.
Organization roles are tenant-scoped. Uniqueness of ``code`` is enforced with two
partial unique indexes rather than a single composite unique constraint because
PostgreSQL treats every NULL as distinct, which would otherwise allow duplicate
system role codes.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from contextforge.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RoleModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A named collection of permissions, either system-wide or organization-scoped."""

    __tablename__ = "roles"
    __table_args__ = (
        Index(
            "uq_roles_code_system",
            "code",
            unique=True,
            postgresql_where=text("organization_id IS NULL"),
        ),
        Index(
            "uq_roles_organization_id_code",
            "organization_id",
            "code",
            unique=True,
            postgresql_where=text("organization_id IS NOT NULL"),
        ),
    )

    organization_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return f"RoleModel(id={self.id!s}, code={self.code!r}, is_system={self.is_system!r})"
