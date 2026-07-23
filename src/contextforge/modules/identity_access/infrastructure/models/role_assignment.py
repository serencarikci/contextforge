"""Role assignment ORM model.

A role assignment grants a role to a membership at exactly one scope:
organization-wide (both ``project_id`` and ``knowledge_space_id`` are NULL),
project-scoped, or knowledge-space-scoped. The uniqueness index coalesces the
nullable scope columns to a sentinel UUID so PostgreSQL's NULL-distinctness
rules don't allow duplicate assignments at the same scope.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, func, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from contextforge.infrastructure.database.base import Base, UUIDPrimaryKeyMixin
from contextforge.shared.utilities.datetime import utc_now

_NULL_SCOPE_SENTINEL = "00000000-0000-0000-0000-000000000000"


class RoleAssignmentModel(Base, UUIDPrimaryKeyMixin):
    """Assigns a role to a membership, optionally scoped to a project or knowledge space."""

    __tablename__ = "role_assignments"
    __table_args__ = (
        CheckConstraint(
            "(project_id IS NULL AND knowledge_space_id IS NULL) OR "
            "(project_id IS NOT NULL AND knowledge_space_id IS NULL) OR "
            "(project_id IS NULL AND knowledge_space_id IS NOT NULL)",
            name="exclusive_scope",
        ),
        Index(
            "uq_role_assignments_membership_role_scope",
            "membership_id",
            "role_id",
            text(f"COALESCE(project_id, '{_NULL_SCOPE_SENTINEL}'::uuid)"),
            text(f"COALESCE(knowledge_space_id, '{_NULL_SCOPE_SENTINEL}'::uuid)"),
            unique=True,
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    membership_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organization_memberships.id", ondelete="RESTRICT"),
        nullable=False,
    )
    role_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=True,
    )
    knowledge_space_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge_spaces.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"RoleAssignmentModel(id={self.id!s}, membership_id={self.membership_id!s}, "
            f"role_id={self.role_id!s})"
        )
