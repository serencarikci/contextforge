"""SQLAlchemy repository for document parse results."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.documents.domain.entities.document_parse_result import DocumentParseResult
from contextforge.modules.documents.domain.enums import DocumentFormat, DocumentParseStatus
from contextforge.modules.documents.infrastructure.models.document_parse_result import (
    DocumentParseResultModel,
)
from contextforge.shared.types.aliases import JSONValue


class SqlAlchemyDocumentParseResultRepository:
    """Persists DocumentParseResult aggregates using an explicit AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_document(
        self,
        organization_id: UUID,
        document_id: UUID,
    ) -> DocumentParseResult | None:
        statement = select(DocumentParseResultModel).where(
            and_(
                DocumentParseResultModel.organization_id == organization_id,
                DocumentParseResultModel.document_id == document_id,
            )
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def upsert(self, entity: DocumentParseResult) -> DocumentParseResult:
        statement = select(DocumentParseResultModel).where(
            DocumentParseResultModel.document_id == entity.document_id
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()

        if model is None:
            model = DocumentParseResultModel(
                id=entity.id,
                organization_id=entity.organization_id,
                document_id=entity.document_id,
                format=entity.format.value,
                status=entity.status.value,
                extracted_text=entity.extracted_text,
                metadata_json=dict(entity.metadata),
                character_count=entity.character_count,
                page_count=entity.page_count,
                error_code=entity.error_code,
                error_message=entity.error_message,
                parsed_at=entity.parsed_at,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
            self._session.add(model)
        else:
            model.organization_id = entity.organization_id
            model.format = entity.format.value
            model.status = entity.status.value
            model.extracted_text = entity.extracted_text
            model.metadata_json = dict(entity.metadata)
            model.character_count = entity.character_count
            model.page_count = entity.page_count
            model.error_code = entity.error_code
            model.error_message = entity.error_message
            model.parsed_at = entity.parsed_at
            model.updated_at = entity.updated_at

        await self._session.flush()
        return self._to_entity(model)

    async def delete_by_document(self, document_id: UUID) -> None:
        statement = select(DocumentParseResultModel).where(
            DocumentParseResultModel.document_id == document_id
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

    @staticmethod
    def _to_entity(model: DocumentParseResultModel) -> DocumentParseResult:
        metadata: dict[str, JSONValue] = dict(model.metadata_json or {})
        return DocumentParseResult(
            id=model.id,
            organization_id=model.organization_id,
            document_id=model.document_id,
            format=DocumentFormat(model.format),
            status=DocumentParseStatus(model.status),
            extracted_text=model.extracted_text,
            metadata=metadata,
            character_count=model.character_count,
            page_count=model.page_count,
            error_code=model.error_code,
            error_message=model.error_message,
            parsed_at=model.parsed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
