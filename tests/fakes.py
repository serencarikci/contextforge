from __future__ import annotations

from uuid import UUID

from contextforge.application.ports.vector_store import ChunkVectorPoint, VectorSearchHit


class FakeVectorStore:
    def __init__(self, hits: list[VectorSearchHit] | None = None) -> None:
        self.hits = hits or []
        self.upserted: list[ChunkVectorPoint] = []
        self.deleted: list[tuple[object, object]] = []
        self.ensure_ready_calls = 0

    async def ensure_ready(self, *, dimensions: int) -> None:
        del dimensions
        self.ensure_ready_calls += 1

    async def upsert_chunk_vectors(self, points: list[ChunkVectorPoint]) -> None:
        self.upserted.extend(points)

    async def delete_by_document(self, organization_id: object, document_id: object) -> None:
        self.deleted.append((organization_id, document_id))

    async def search(
        self,
        *,
        organization_id: UUID,
        query_vector: list[float],
        knowledge_space_ids: list[UUID],
        top_k: int,
    ) -> list[VectorSearchHit]:
        del query_vector, top_k
        allowed = set(knowledge_space_ids)
        return [
            hit
            for hit in self.hits
            if hit.organization_id == organization_id and hit.knowledge_space_id in allowed
        ]


__all__ = ["FakeVectorStore"]
