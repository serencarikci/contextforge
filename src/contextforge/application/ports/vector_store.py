from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from contextforge.shared.types.aliases import JSONValue


@dataclass(frozen=True, slots=True)
class ChunkVectorPoint:
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
    chunk_id: UUID
    organization_id: UUID
    document_id: UUID
    knowledge_space_id: UUID
    score: float
    chunk_index: int | None = None
    document_title: str | None = None
    payload: dict[str, JSONValue] = field(default_factory=dict)


class VectorStoreError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class VectorStorePort(Protocol):
    async def ensure_ready(self, *, dimensions: int) -> None: ...

    async def upsert_chunk_vectors(self, points: list[ChunkVectorPoint]) -> None: ...

    async def delete_by_document(self, organization_id: UUID, document_id: UUID) -> None: ...

    async def search(
        self,
        *,
        organization_id: UUID,
        query_vector: list[float],
        knowledge_space_ids: list[UUID],
        top_k: int,
    ) -> list[VectorSearchHit]: ...


__all__ = [
    "ChunkVectorPoint",
    "VectorSearchHit",
    "VectorStoreError",
    "VectorStorePort",
]
