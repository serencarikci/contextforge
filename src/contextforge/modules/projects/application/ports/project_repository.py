"""Repository port for project persistence."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from contextforge.modules.identity_access.domain.enums import ProjectStatus
from contextforge.modules.projects.domain.entities.project import Project


class ProjectRepository(Protocol):
    """Port for persisting and loading Project aggregates."""

    async def get(self, organization_id: UUID, project_id: UUID) -> Project | None:
        """Return the project with the given id scoped to the organization."""
        ...

    async def get_by_key(self, organization_id: UUID, key: str) -> Project | None:
        """Return the project with the given key within the organization."""
        ...

    async def add(self, entity: Project) -> Project:
        """Persist a new project and return the persisted entity."""
        ...

    async def update(self, entity: Project) -> Project:
        """Persist changes to an existing project and return the entity."""
        ...

    async def list(
        self,
        organization_id: UUID,
        *,
        limit: int,
        offset: int,
        status: ProjectStatus | None = None,
        customer_id: UUID | None = None,
        query: str | None = None,
    ) -> tuple[list[Project], int]:
        """Return a page of projects for the organization, plus total count."""
        ...
