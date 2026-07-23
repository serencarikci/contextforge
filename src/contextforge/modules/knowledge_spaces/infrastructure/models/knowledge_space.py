"""Knowledge space ORM model."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from contextforge.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from contextforge.modules.identity_access.domain.enums import (
    KnowledgeSpaceStatus,
    KnowledgeSpaceVisibility,
)


class KnowledgeSpaceModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A namespace for knowledge content, owned by an organization."""

    __tablename__ = "knowledge_spaces"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "slug", name="uq_knowledge_spaces_organization_id_slug"
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    visibility: Mapped[str] = mapped_column(
        String(20), nullable=False, default=KnowledgeSpaceVisibility.ORGANIZATION.value
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=KnowledgeSpaceStatus.ACTIVE.value
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"KnowledgeSpaceModel(id={self.id!s}, slug={self.slug!r})"
