"""Repository port for organization persistence."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from contextforge.modules.identity_access.domain.enums import OrganizationStatus
from contextforge.modules.organizations.domain.entities.organization import Organization


class OrganizationRepository(Protocol):
    """Port for persisting and loading Organization aggregates."""

    async def get_by_id(self, organization_id: UUID) -> Organization | None:
        """Return the organization with the given id, or None if missing."""
        ...

    async def get_by_slug(self, slug: str) -> Organization | None:
        """Return the organization with the given slug, or None if missing."""
        ...

    async def add(self, entity: Organization) -> Organization:
        """Persist a new organization and return the persisted entity."""
        ...

    async def update(self, entity: Organization) -> Organization:
        """Persist changes to an existing organization and return the entity."""
        ...

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        limit: int,
        offset: int,
        status: OrganizationStatus | None = None,
    ) -> tuple[list[Organization], int]:
        """Return a page of organizations the given user is a member of, plus total count."""
        ...
