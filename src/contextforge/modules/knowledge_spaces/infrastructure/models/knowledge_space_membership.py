"""Knowledge space membership ORM model."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from contextforge.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from contextforge.modules.identity_access.domain.enums import KnowledgeSpaceAccessLevel


class KnowledgeSpaceMembershipModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Grants an organization membership access to a knowledge space."""

    __tablename__ = "knowledge_space_memberships"
    __table_args__ = (
        UniqueConstraint(
            "knowledge_space_id",
            "membership_id",
            name="uq_knowledge_space_memberships_ks_membership",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    knowledge_space_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge_spaces.id", ondelete="RESTRICT"),
        nullable=False,
    )
    membership_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organization_memberships.id", ondelete="RESTRICT"),
        nullable=False,
    )
    access_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default=KnowledgeSpaceAccessLevel.READER.value
    )

    def __repr__(self) -> str:
        return (
            f"KnowledgeSpaceMembershipModel(id={self.id!s}, "
            f"knowledge_space_id={self.knowledge_space_id!s}, membership_id={self.membership_id!s})"
        )
