"""Repository port for RBAC (roles, permissions, role assignments) persistence."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from contextforge.modules.identity_access.domain.entities.rbac import (
    Permission,
    Role,
    RoleAssignment,
)


class RbacRepository(Protocol):
    """Port for persisting and loading roles, permissions, and role assignments."""

    async def list_roles(self, organization_id: UUID) -> list[Role]:
        """Return system roles plus organization-scoped roles for the organization."""
        ...

    async def get_role(self, role_id: UUID) -> Role | None:
        """Return the role with the given id, or None if missing."""
        ...

    async def get_system_role_by_code(self, code: str) -> Role | None:
        """Return the system role with the given code, or None if missing."""
        ...

    async def get_org_role_by_code(self, organization_id: UUID, code: str) -> Role | None:
        """Return the organization-scoped role with the given code, or None if missing."""
        ...

    async def add_role(self, role: Role) -> Role:
        """Persist a new role and return the persisted entity."""
        ...

    async def update_role(self, role: Role) -> Role:
        """Persist changes to an existing role and return the entity."""
        ...

    async def list_permissions(self) -> list[Permission]:
        """Return the full permission catalog."""
        ...

    async def get_organization_scope_permission_codes(
        self, organization_id: UUID, membership_id: UUID
    ) -> set[str]:
        """Return permission codes granted to the membership at organization scope."""
        ...

    async def get_project_scope_permission_codes(
        self, organization_id: UUID, membership_id: UUID, project_id: UUID
    ) -> set[str]:
        """Return permission codes granted to the membership for the given project."""
        ...

    async def get_knowledge_space_scope_permission_codes(
        self, organization_id: UUID, membership_id: UUID, knowledge_space_id: UUID
    ) -> set[str]:
        """Return permission codes granted to the membership for the given knowledge space."""
        ...

    async def list_accessible_project_ids(
        self, organization_id: UUID, membership_id: UUID
    ) -> set[UUID]:
        """Return project ids explicitly granted to the membership via role assignments."""
        ...

    async def list_accessible_knowledge_space_ids_from_roles(
        self, organization_id: UUID, membership_id: UUID
    ) -> set[UUID]:
        """Return knowledge space ids explicitly granted via role assignments."""
        ...

    async def add_assignment(self, assignment: RoleAssignment) -> RoleAssignment:
        """Persist a new role assignment and return the persisted entity."""
        ...

    async def get_assignment(
        self, organization_id: UUID, assignment_id: UUID
    ) -> RoleAssignment | None:
        """Return the role assignment with the given id, or None if missing."""
        ...

    async def delete_assignment(self, organization_id: UUID, assignment_id: UUID) -> bool:
        """Delete a role assignment. Returns True if a row was deleted."""
        ...

    async def list_assignments(
        self, organization_id: UUID, *, limit: int, offset: int
    ) -> tuple[list[RoleAssignment], int]:
        """Return a page of role assignments for the organization, plus total count."""
        ...

    async def assignment_exists(
        self,
        organization_id: UUID,
        membership_id: UUID,
        role_id: UUID,
        project_id: UUID | None,
        knowledge_space_id: UUID | None,
    ) -> bool:
        """Return True if an assignment already exists for the given membership/role/scope."""
        ...
