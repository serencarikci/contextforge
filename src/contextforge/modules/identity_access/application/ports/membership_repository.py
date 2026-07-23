"""Repository port for organization membership persistence."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from contextforge.modules.identity_access.domain.entities.membership import (
    OrganizationMembership,
)
from contextforge.modules.identity_access.domain.enums import MembershipStatus


class MembershipRepository(Protocol):
    """Port for persisting and loading OrganizationMembership aggregates."""

    async def get_by_id(
        self, organization_id: UUID, membership_id: UUID
    ) -> OrganizationMembership | None:
        """Return the membership with the given id scoped to the organization."""
        ...

    async def get_by_org_and_user(
        self, organization_id: UUID, user_id: UUID
    ) -> OrganizationMembership | None:
        """Return the membership for the given user within the organization."""
        ...

    async def add(self, entity: OrganizationMembership) -> OrganizationMembership:
        """Persist a new membership and return the persisted entity."""
        ...

    async def update(self, entity: OrganizationMembership) -> OrganizationMembership:
        """Persist changes to an existing membership and return the entity."""
        ...

    async def list_for_organization(
        self,
        organization_id: UUID,
        *,
        limit: int,
        offset: int,
        status: MembershipStatus | None = None,
        query: str | None = None,
    ) -> tuple[list[OrganizationMembership], int]:
        """Return a page of memberships for the organization, plus total count."""
        ...
