"""SQLAlchemy implementation of the document repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.documents.domain.entities.document import Document
from contextforge.modules.documents.domain.enums import DocumentStatus
from contextforge.modules.documents.infrastructure.models.document import DocumentModel


class SqlAlchemyDocumentRepository:
    """Persists Document aggregates using an explicit AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        organization_id: UUID,
        document_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Document | None:
        conditions = [
            DocumentModel.id == document_id,
            DocumentModel.organization_id == organization_id,
        ]
        if not include_deleted:
            conditions.append(DocumentModel.status != DocumentStatus.DELETED.value)
        statement = select(DocumentModel).where(and_(*conditions))
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def add(self, entity: Document) -> Document:
        model = DocumentModel(
            id=entity.id,
            organization_id=entity.organization_id,
            knowledge_space_id=entity.knowledge_space_id,
            title=entity.title,
            filename=entity.filename,
            content_type=entity.content_type,
            size_bytes=entity.size_bytes,
            storage_key=entity.storage_key,
            checksum_sha256=entity.checksum_sha256,
            status=entity.status.value,
            uploaded_by_user_id=entity.uploaded_by_user_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, entity: Document) -> Document:
        statement = select(DocumentModel).where(DocumentModel.id == entity.id)
        result = await self._session.execute(statement)
        model = result.scalar_one()

        model.title = entity.title
        model.filename = entity.filename
        model.content_type = entity.content_type
        model.size_bytes = entity.size_bytes
        model.storage_key = entity.storage_key
        model.checksum_sha256 = entity.checksum_sha256
        model.status = entity.status.value
        model.updated_at = entity.updated_at
        model.deleted_at = entity.deleted_at

        await self._session.flush()
        return self._to_entity(model)

    async def list(
        self,
        organization_id: UUID,
        *,
        limit: int,
        offset: int,
        knowledge_space_id: UUID | None = None,
        query: str | None = None,
    ) -> tuple[list[Document], int]:
        conditions = [
            DocumentModel.organization_id == organization_id,
            DocumentModel.status != DocumentStatus.DELETED.value,
        ]
        if knowledge_space_id is not None:
            conditions.append(DocumentModel.knowledge_space_id == knowledge_space_id)
        if query and query.strip():
            pattern = f"%{query.strip()}%"
            conditions.append(
                DocumentModel.title.ilike(pattern) | DocumentModel.filename.ilike(pattern)
            )

        count_statement = select(func.count()).select_from(DocumentModel).where(and_(*conditions))
        total = (await self._session.execute(count_statement)).scalar_one()

        statement = (
            select(DocumentModel)
            .where(and_(*conditions))
            .order_by(DocumentModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(statement)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models], total

    @staticmethod
    def _to_entity(model: DocumentModel) -> Document:
        return Document(
            organization_id=model.organization_id,
            knowledge_space_id=model.knowledge_space_id,
            title=model.title,
            filename=model.filename,
            content_type=model.content_type,
            size_bytes=model.size_bytes,
            storage_key=model.storage_key,
            uploaded_by_user_id=model.uploaded_by_user_id,
            id=model.id,
            checksum_sha256=model.checksum_sha256,
            status=DocumentStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )
