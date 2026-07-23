"""Application service for multilingual chunk embedding generation."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.ports.embedding_provider import EmbeddingProviderPort
from contextforge.application.ports.vector_store import (
    ChunkVectorPoint,
    VectorStoreError,
    VectorStorePort,
)
from contextforge.application.services.command_support import build_audit_event
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import InvalidResourceStateError, ResourceNotFoundError
from contextforge.modules.documents.domain.entities.document_chunk import DocumentChunk
from contextforge.modules.documents.domain.enums import ChunkEmbeddingStatus
from contextforge.modules.documents.domain.exceptions import (
    DocumentEmbeddingError,
    PermanentEmbeddingError,
    TransientEmbeddingError,
)
from contextforge.modules.documents.domain.language import detect_language
from contextforge.shared.logging.setup import get_logger
from contextforge.shared.types.aliases import JSONValue
from contextforge.shared.utilities.retry import retry_async

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class DocumentEmbeddingResult:
    document_id: UUID
    model: str
    dimensions: int
    language: str
    embedded_count: int
    failed_count: int
    skipped_count: int
    chunks: list[DocumentChunk]


class DocumentEmbeddingService:
    """Generates embeddings for document chunks and stores them in Qdrant."""

    def __init__(
        self,
        embedding_provider: EmbeddingProviderPort,
        vector_store: VectorStorePort,
        *,
        batch_size: int = 32,
        max_retries: int = 3,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store
        self._batch_size = batch_size
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds

    async def embed_document(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        document_id: UUID,
        *,
        language: str | None = None,
        force: bool = False,
    ) -> DocumentEmbeddingResult:
        async with uow:
            ctx.require_permission("document:update")
            document = await uow.documents.get(ctx.organization_id, document_id)
            if document is None:
                raise ResourceNotFoundError("Document not found.")
            ctx.require_knowledge_space_access(document.knowledge_space_id)

            chunks = await uow.document_chunks.list_by_document(ctx.organization_id, document_id)
            if not chunks:
                raise InvalidResourceStateError(
                    "Document must be chunked before embedding generation."
                )

            detected_language = language or detect_language(
                "\n\n".join(chunk.content for chunk in chunks[:20])
            )
            targets = [
                chunk
                for chunk in chunks
                if force
                or chunk.embedding_status
                in {ChunkEmbeddingStatus.PENDING, ChunkEmbeddingStatus.FAILED}
            ]
            skipped_count = len(chunks) - len(targets)
            if not targets:
                return DocumentEmbeddingResult(
                    document_id=document_id,
                    model=self._embedding_provider.model,
                    dimensions=self._embedding_provider.dimensions,
                    language=detected_language,
                    embedded_count=0,
                    failed_count=0,
                    skipped_count=skipped_count,
                    chunks=chunks,
                )

            organization_id = document.organization_id
            knowledge_space_id = document.knowledge_space_id
            document_title = document.title

        try:
            if force:
                await retry_async(
                    lambda: self._vector_store.delete_by_document(organization_id, document_id),
                    max_retries=self._max_retries,
                    backoff_seconds=self._retry_backoff_seconds,
                    retry_on=(VectorStoreError, TransientEmbeddingError),
                )
            await retry_async(
                lambda: self._vector_store.ensure_ready(
                    dimensions=self._embedding_provider.dimensions
                ),
                max_retries=self._max_retries,
                backoff_seconds=self._retry_backoff_seconds,
                retry_on=(VectorStoreError, TransientEmbeddingError),
            )
        except (VectorStoreError, TransientEmbeddingError, PermanentEmbeddingError) as exc:
            message = getattr(exc, "message", str(exc))
            raise DocumentEmbeddingError(message) from exc

        embedded_count = 0
        failed_count = 0
        updated_targets: list[DocumentChunk] = []

        for start in range(0, len(targets), self._batch_size):
            batch = targets[start : start + self._batch_size]
            try:
                result = await self._embedding_provider.embed_texts(
                    [chunk.content for chunk in batch],
                    language=detected_language,
                )
                if len(result.vectors) != len(batch):
                    raise DocumentEmbeddingError("Embedding provider returned unexpected size.")

                points = [
                    ChunkVectorPoint(
                        chunk_id=chunk.id,
                        organization_id=organization_id,
                        document_id=document_id,
                        knowledge_space_id=knowledge_space_id,
                        chunk_index=chunk.chunk_index,
                        content_hash=chunk.content_hash,
                        language=detected_language,
                        vector=vector,
                        payload=_chunk_payload(
                            chunk,
                            language=detected_language,
                            model=result.model,
                            document_title=document_title,
                        ),
                    )
                    for chunk, vector in zip(batch, result.vectors, strict=True)
                ]

                async def _upsert(points: list[ChunkVectorPoint] = points) -> None:
                    await self._vector_store.upsert_chunk_vectors(points)

                await retry_async(
                    _upsert,
                    max_retries=self._max_retries,
                    backoff_seconds=self._retry_backoff_seconds,
                    retry_on=(VectorStoreError, TransientEmbeddingError),
                )
                for chunk in batch:
                    chunk.mark_embedded(
                        language=detected_language,
                        model=result.model,
                        dimensions=result.dimensions,
                    )
                    updated_targets.append(chunk)
                    embedded_count += 1
            except (
                DocumentEmbeddingError,
                TransientEmbeddingError,
                PermanentEmbeddingError,
                VectorStoreError,
            ) as exc:
                logger.warning(
                    "document_embedding_batch_failed",
                    exc_info=exc,
                    extra={"document_id": str(document_id), "batch_size": len(batch)},
                )
                message = getattr(exc, "message", str(exc))
                for chunk in batch:
                    chunk.mark_embedding_failed(message)
                    updated_targets.append(chunk)
                    failed_count += 1

        async with uow:
            ctx.require_permission("document:update")
            document = await uow.documents.get(ctx.organization_id, document_id)
            if document is None:
                raise ResourceNotFoundError("Document not found.")
            ctx.require_knowledge_space_access(document.knowledge_space_id)

            await uow.document_chunks.update_many(updated_targets)
            event = build_audit_event(
                ctx,
                action="document.embedded",
                resource_type="document",
                resource_id=document_id,
                metadata={
                    "embedded_count": embedded_count,
                    "failed_count": failed_count,
                    "skipped_count": skipped_count,
                    "language": detected_language,
                    "model": self._embedding_provider.model,
                    "dimensions": self._embedding_provider.dimensions,
                },
            )
            await uow.audit.add(event)
            all_chunks = await uow.document_chunks.list_by_document(
                ctx.organization_id, document_id
            )
            return DocumentEmbeddingResult(
                document_id=document_id,
                model=self._embedding_provider.model,
                dimensions=self._embedding_provider.dimensions,
                language=detected_language,
                embedded_count=embedded_count,
                failed_count=failed_count,
                skipped_count=skipped_count,
                chunks=all_chunks,
            )


def _chunk_payload(
    chunk: DocumentChunk,
    *,
    language: str,
    model: str,
    document_title: str,
) -> dict[str, JSONValue]:
    payload: dict[str, JSONValue] = {
        "language": language,
        "embedding_model": model,
        "document_title": document_title,
        "token_count": chunk.token_count,
        "char_start": chunk.char_start,
        "char_end": chunk.char_end,
    }
    for key in ("section_title", "source_format", "document_filename"):
        value = chunk.metadata.get(key)
        if isinstance(value, str):
            payload[key] = value
    return payload


__all__ = ["DocumentEmbeddingResult", "DocumentEmbeddingService"]
