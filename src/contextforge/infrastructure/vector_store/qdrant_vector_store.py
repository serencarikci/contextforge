"""Qdrant-backed vector store for document chunk embeddings."""

from __future__ import annotations

import asyncio
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from contextforge.application.ports.vector_store import ChunkVectorPoint, VectorStoreError
from contextforge.shared.config.settings import QdrantSettings
from contextforge.shared.logging.setup import get_logger

logger = get_logger(__name__)


class QdrantVectorStore:
    """Stores multilingual chunk embeddings in Qdrant."""

    def __init__(self, settings: QdrantSettings) -> None:
        self._settings = settings
        api_key = None
        if settings.api_key is not None:
            value = settings.api_key.get_secret_value()
            api_key = value or None
        self._client = QdrantClient(
            url=settings.url,
            api_key=api_key,
            timeout=int(settings.timeout_seconds),
            check_compatibility=False,
        )
        self._ensured_dimensions: int | None = None

    async def ensure_ready(self, *, dimensions: int) -> None:
        def _ensure() -> None:
            collections = self._client.get_collections().collections
            exists = any(
                collection.name == self._settings.collection_name for collection in collections
            )
            if not exists:
                self._client.create_collection(
                    collection_name=self._settings.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=dimensions,
                        distance=qmodels.Distance.COSINE,
                    ),
                )
                self._client.create_payload_index(
                    collection_name=self._settings.collection_name,
                    field_name="organization_id",
                    field_schema=qmodels.PayloadSchemaType.KEYWORD,
                )
                self._client.create_payload_index(
                    collection_name=self._settings.collection_name,
                    field_name="document_id",
                    field_schema=qmodels.PayloadSchemaType.KEYWORD,
                )
                self._client.create_payload_index(
                    collection_name=self._settings.collection_name,
                    field_name="knowledge_space_id",
                    field_schema=qmodels.PayloadSchemaType.KEYWORD,
                )
                self._client.create_payload_index(
                    collection_name=self._settings.collection_name,
                    field_name="language",
                    field_schema=qmodels.PayloadSchemaType.KEYWORD,
                )
                return

            info = self._client.get_collection(self._settings.collection_name)
            vectors = info.config.params.vectors
            size = getattr(vectors, "size", None)
            if size is not None and int(size) != dimensions:
                raise VectorStoreError(
                    f"Qdrant collection {self._settings.collection_name!r} has size {size}, "
                    f"expected {dimensions}."
                )

        try:
            await asyncio.to_thread(_ensure)
            self._ensured_dimensions = dimensions
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(f"Failed to ensure Qdrant collection: {exc}") from exc

    async def upsert_chunk_vectors(self, points: list[ChunkVectorPoint]) -> None:
        if not points:
            return
        dimensions = len(points[0].vector)
        if self._ensured_dimensions != dimensions:
            await self.ensure_ready(dimensions=dimensions)

        qdrant_points = [
            qmodels.PointStruct(
                id=str(point.chunk_id),
                vector=point.vector,
                payload={
                    "organization_id": str(point.organization_id),
                    "document_id": str(point.document_id),
                    "knowledge_space_id": str(point.knowledge_space_id),
                    "chunk_index": point.chunk_index,
                    "content_hash": point.content_hash,
                    "language": point.language,
                    **{key: value for key, value in point.payload.items()},
                },
            )
            for point in points
        ]

        try:
            await asyncio.to_thread(
                self._client.upsert,
                collection_name=self._settings.collection_name,
                points=qdrant_points,
                wait=True,
            )
        except Exception as exc:
            raise VectorStoreError(f"Failed to upsert chunk vectors: {exc}") from exc

    async def delete_by_document(self, organization_id: UUID, document_id: UUID) -> None:
        def _delete() -> None:
            collections = {
                collection.name for collection in self._client.get_collections().collections
            }
            if self._settings.collection_name not in collections:
                return
            self._client.delete(
                collection_name=self._settings.collection_name,
                points_selector=qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="organization_id",
                                match=qmodels.MatchValue(value=str(organization_id)),
                            ),
                            qmodels.FieldCondition(
                                key="document_id",
                                match=qmodels.MatchValue(value=str(document_id)),
                            ),
                        ]
                    )
                ),
            )

        try:
            await asyncio.to_thread(_delete)
        except Exception as exc:
            raise VectorStoreError(f"Failed to delete document vectors: {exc}") from exc

    async def close(self) -> None:
        await asyncio.to_thread(self._client.close)
        logger.info("qdrant_vector_store_closed")


__all__ = ["QdrantVectorStore"]
