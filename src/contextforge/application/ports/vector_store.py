"""Port for vector store operations over document chunks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from contextforge.shared.types.aliases import JSONValue


@dataclass(frozen=True, slots=True)
class ChunkVectorPoint:
    """One chunk vector ready to upsert into the vector store."""

    chunk_id: UUID
    organization_id: UUID
    document_id: UUID
    knowledge_space_id: UUID
    chunk_index: int
    content_hash: str
    language: str
    vector: list[float]
    payload: dict[str, JSONValue]


@dataclass(frozen=True, slots=True)
class VectorSearchHit:
    """One dense-search result from the vector store."""

    chunk_id: UUID
    organization_id: UUID
    document_id: UUID
    knowledge_space_id: UUID
    score: float
    chunk_index: int | None = None
    document_title: str | None = None
    payload: dict[str, JSONValue] = field(default_factory=dict)


class VectorStoreError(Exception):
    """Raised when a vector store operation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class VectorStorePort(Protocol):
    """Persists chunk embeddings for similarity retrieval."""

    async def ensure_ready(self, *, dimensions: int) -> None:
        """Ensure the backing collection exists for the configured dimensions."""
        ...

    async def upsert_chunk_vectors(self, points: list[ChunkVectorPoint]) -> None:
        """Insert or replace vectors for the given chunks."""
        ...

    async def delete_by_document(self, organization_id: UUID, document_id: UUID) -> None:
        """Remove all vectors belonging to a document."""
        ...

    async def search(
        self,
        *,
        organization_id: UUID,
        query_vector: list[float],
        knowledge_space_ids: list[UUID],
        top_k: int,
    ) -> list[VectorSearchHit]:
        """Dense similarity search scoped to an organization and knowledge spaces."""
        ...


__all__ = [
    "ChunkVectorPoint",
    "VectorSearchHit",
    "VectorStoreError",
    "VectorStorePort",
]
