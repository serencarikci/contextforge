"""Repository port for knowledge space persistence."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from contextforge.modules.identity_access.domain.enums import (
    KnowledgeSpaceStatus,
    KnowledgeSpaceVisibility,
)
from contextforge.modules.knowledge_spaces.domain.entities.knowledge_space import (
    KnowledgeSpace,
    KnowledgeSpaceMembership,
)


class KnowledgeSpaceRepository(Protocol):
    """Port for persisting and loading KnowledgeSpace aggregates and their memberships."""

    async def get(self, organization_id: UUID, knowledge_space_id: UUID) -> KnowledgeSpace | None:
        """Return the knowledge space with the given id scoped to the organization."""
        ...

    async def get_by_slug(self, organization_id: UUID, slug: str) -> KnowledgeSpace | None:
        """Return the knowledge space with the given slug within the organization."""
        ...

    async def add(self, entity: KnowledgeSpace) -> KnowledgeSpace:
        """Persist a new knowledge space and return the persisted entity."""
        ...

    async def update(self, entity: KnowledgeSpace) -> KnowledgeSpace:
        """Persist changes to an existing knowledge space and return the entity."""
        ...

    async def list_organization_visible_ids(self, organization_id: UUID) -> set[UUID]:
        """Return ids of active, organization-visible knowledge spaces."""
        ...

    async def add_membership(self, entity: KnowledgeSpaceMembership) -> KnowledgeSpaceMembership:
        """Persist a new knowledge space membership and return the persisted entity."""
        ...

    async def get_membership(
        self,
        organization_id: UUID,
        knowledge_space_id: UUID,
        ks_membership_id: UUID,
    ) -> KnowledgeSpaceMembership | None:
        """Return a knowledge space membership by its own id."""
        ...

    async def get_membership_by_org_membership(
        self,
        organization_id: UUID,
        knowledge_space_id: UUID,
        membership_id: UUID,
    ) -> KnowledgeSpaceMembership | None:
        """Return a knowledge space membership by organization membership id."""
        ...

    async def update_membership(self, entity: KnowledgeSpaceMembership) -> KnowledgeSpaceMembership:
        """Persist changes to an existing knowledge space membership."""
        ...

    async def delete_membership(
        self, organization_id: UUID, knowledge_space_id: UUID, ks_membership_id: UUID
    ) -> bool:
        """Delete a knowledge space membership. Returns True if a row was deleted."""
        ...

    async def list_memberships(
        self,
        organization_id: UUID,
        knowledge_space_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[KnowledgeSpaceMembership], int]:
        """Return a page of memberships for the knowledge space, plus total count."""
        ...

    async def list_accessible_ids_for_membership(
        self, organization_id: UUID, membership_id: UUID
    ) -> set[UUID]:
        """Return knowledge space ids the membership has explicit access to."""
        ...

    async def list(
        self,
        organization_id: UUID,
        *,
        limit: int,
        offset: int,
        status: KnowledgeSpaceStatus | None = None,
        visibility: KnowledgeSpaceVisibility | None = None,
        project_id: UUID | None = None,
        query: str | None = None,
    ) -> tuple[list[KnowledgeSpace], int]:
        """Return a page of knowledge spaces for the organization, plus total count."""
        ...
