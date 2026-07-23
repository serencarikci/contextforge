"""Repository port for document persistence."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from contextforge.modules.documents.domain.entities.document import Document


class DocumentRepository(Protocol):
    """Port for persisting and loading Document aggregates."""

    async def get(
        self,
        organization_id: UUID,
        document_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Document | None:
        """Return the document with the given id scoped to the organization.

        Excludes soft-deleted documents unless ``include_deleted`` is set.
        """
        ...

    async def add(self, entity: Document) -> Document:
        """Persist a new document and return the persisted entity."""
        ...

    async def update(self, entity: Document) -> Document:
        """Persist changes to an existing document and return the entity."""
        ...

    async def list(
        self,
        organization_id: UUID,
        *,
        limit: int,
        offset: int,
        knowledge_space_id: UUID | None = None,
        query: str | None = None,
    ) -> tuple[list[Document], int]:
        """Return a page of active documents for the organization, plus total count."""
        ...
