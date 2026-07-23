"""SQLAlchemy repository for document chunks."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.documents.domain.entities.document_chunk import DocumentChunk
from contextforge.modules.documents.domain.enums import ChunkEmbeddingStatus
from contextforge.modules.documents.infrastructure.models.document_chunk import DocumentChunkModel
from contextforge.shared.types.aliases import JSONValue


class SqlAlchemyDocumentChunkRepository:
    """Persists DocumentChunk rows using an explicit AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_document(
        self,
        organization_id: UUID,
        document_id: UUID,
    ) -> list[DocumentChunk]:
        statement = (
            select(DocumentChunkModel)
            .where(
                and_(
                    DocumentChunkModel.organization_id == organization_id,
                    DocumentChunkModel.document_id == document_id,
                )
            )
            .order_by(DocumentChunkModel.chunk_index.asc())
        )
        result = await self._session.execute(statement)
        return [self._to_entity(model) for model in result.scalars().all()]

    async def replace_for_document(
        self,
        organization_id: UUID,
        document_id: UUID,
        chunks: list[DocumentChunk],
    ) -> list[DocumentChunk]:
        await self._session.execute(
            delete(DocumentChunkModel).where(
                and_(
                    DocumentChunkModel.organization_id == organization_id,
                    DocumentChunkModel.document_id == document_id,
                )
            )
        )
        models = [self._to_model(chunk) for chunk in chunks]
        self._session.add_all(models)
        await self._session.flush()
        return [self._to_entity(model) for model in models]

    async def update_many(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        updated: list[DocumentChunk] = []
        for chunk in chunks:
            statement = select(DocumentChunkModel).where(DocumentChunkModel.id == chunk.id)
            result = await self._session.execute(statement)
            model = result.scalar_one()
            model.embedding_status = chunk.embedding_status.value
            model.language = chunk.language
            model.embedding_model = chunk.embedding_model
            model.embedding_dimensions = chunk.embedding_dimensions
            model.embedded_at = chunk.embedded_at
            model.embedding_error = chunk.embedding_error
            model.metadata_json = dict(chunk.metadata)
            model.updated_at = chunk.updated_at
            updated.append(self._to_entity(model))
        await self._session.flush()
        return updated

    async def delete_by_document(self, document_id: UUID) -> None:
        await self._session.execute(
            delete(DocumentChunkModel).where(DocumentChunkModel.document_id == document_id)
        )
        await self._session.flush()

    @staticmethod
    def _to_model(chunk: DocumentChunk) -> DocumentChunkModel:
        return DocumentChunkModel(
            id=chunk.id,
            organization_id=chunk.organization_id,
            document_id=chunk.document_id,
            parse_result_id=chunk.parse_result_id,
            knowledge_space_id=chunk.knowledge_space_id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            content_hash=chunk.content_hash,
            char_start=chunk.char_start,
            char_end=chunk.char_end,
            token_count=chunk.token_count,
            metadata_json=dict(chunk.metadata),
            embedding_status=chunk.embedding_status.value,
            language=chunk.language,
            embedding_model=chunk.embedding_model,
            embedding_dimensions=chunk.embedding_dimensions,
            embedded_at=chunk.embedded_at,
            embedding_error=chunk.embedding_error,
            created_at=chunk.created_at,
            updated_at=chunk.updated_at,
        )

    @staticmethod
    def _to_entity(model: DocumentChunkModel) -> DocumentChunk:
        metadata: dict[str, JSONValue] = dict(model.metadata_json or {})
        return DocumentChunk(
            id=model.id,
            organization_id=model.organization_id,
            document_id=model.document_id,
            parse_result_id=model.parse_result_id,
            knowledge_space_id=model.knowledge_space_id,
            chunk_index=model.chunk_index,
            content=model.content,
            content_hash=model.content_hash,
            char_start=model.char_start,
            char_end=model.char_end,
            token_count=model.token_count,
            metadata=metadata,
            embedding_status=ChunkEmbeddingStatus(model.embedding_status),
            language=model.language,
            embedding_model=model.embedding_model,
            embedding_dimensions=model.embedding_dimensions,
            embedded_at=model.embedded_at,
            embedding_error=model.embedding_error,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
