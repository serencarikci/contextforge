"""Application service for document lifecycle use cases."""

from __future__ import annotations

import hashlib
from uuid import UUID, uuid4

from contextforge.application.context.request_context import RequestContext
from contextforge.application.pagination import Page, PaginationParams
from contextforge.application.ports.object_storage import ObjectStoragePort
from contextforge.application.services.command_support import (
    build_audit_event,
    ensure_organization_writable,
)
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import InvalidResourceStateError, ResourceNotFoundError
from contextforge.modules.documents.domain.entities.document import (
    Document,
    ensure_upload_size_within_limit,
)
from contextforge.modules.identity_access.domain.enums import KnowledgeSpaceStatus
from contextforge.shared.logging.setup import get_logger

logger = get_logger(__name__)


class DocumentService:
    """Use cases for uploading, reading, and managing documents."""

    async def upload(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        minio: ObjectStoragePort,
        *,
        knowledge_space_id: UUID,
        title: str,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> Document:
        ensure_upload_size_within_limit(len(data))

        async with uow:
            ctx.require_permission("document:create")
            ctx.require_knowledge_space_access(knowledge_space_id)

            organization = await uow.organizations.get_by_id(ctx.organization_id)
            if organization is None:  # pragma: no cover
                raise ResourceNotFoundError("Organization not found.")
            ensure_organization_writable(organization)

            knowledge_space = await uow.knowledge_spaces.get(
                ctx.organization_id, knowledge_space_id
            )
            if knowledge_space is None:
                raise ResourceNotFoundError("Knowledge space not found.")
            if knowledge_space.status == KnowledgeSpaceStatus.ARCHIVED:
                raise InvalidResourceStateError(
                    "Archived knowledge spaces cannot receive new documents."
                )

            document_id = uuid4()
            storage_key = minio.build_object_key(
                ctx.organization_id, knowledge_space_id, document_id, filename
            )
            checksum = hashlib.sha256(data).hexdigest()

            document = Document(
                id=document_id,
                organization_id=ctx.organization_id,
                knowledge_space_id=knowledge_space_id,
                title=title,
                filename=filename,
                content_type=content_type,
                size_bytes=len(data),
                storage_key=storage_key,
                checksum_sha256=checksum,
                uploaded_by_user_id=ctx.user_id,
            )

            await minio.put_object(storage_key, data, len(data), content_type)
            try:
                document = await uow.documents.add(document)
            except Exception:
                await minio.remove_object(storage_key)
                raise

            event = build_audit_event(
                ctx,
                action="document.uploaded",
                resource_type="document",
                resource_id=document.id,
                metadata={
                    "knowledge_space_id": str(knowledge_space_id),
                    "filename": document.filename,
                    "size_bytes": document.size_bytes,
                },
            )
            await uow.audit.add(event)
            return document

    async def get(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, document_id: UUID
    ) -> Document:
        async with uow:
            ctx.require_permission("document:read")
            document = await uow.documents.get(ctx.organization_id, document_id)
            if document is None:
                raise ResourceNotFoundError("Document not found.")
            ctx.require_knowledge_space_access(document.knowledge_space_id)
            return document

    async def list(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        pagination: PaginationParams,
        *,
        knowledge_space_id: UUID | None = None,
        query: str | None = None,
    ) -> Page[Document]:
        async with uow:
            ctx.require_permission("document:read")

            if knowledge_space_id is not None:
                ctx.require_knowledge_space_access(knowledge_space_id)
                items, total = await uow.documents.list(
                    ctx.organization_id,
                    limit=pagination.limit,
                    offset=pagination.offset,
                    knowledge_space_id=knowledge_space_id,
                    query=query,
                )
                return Page(
                    items=items, limit=pagination.limit, offset=pagination.offset, total=total
                )

            if ctx.is_platform_admin:
                items, total = await uow.documents.list(
                    ctx.organization_id,
                    limit=pagination.limit,
                    offset=pagination.offset,
                    query=query,
                )
                return Page(
                    items=items, limit=pagination.limit, offset=pagination.offset, total=total
                )

            _max_scan = 10_000
            all_items, _ = await uow.documents.list(
                ctx.organization_id,
                limit=_max_scan,
                offset=0,
                query=query,
            )
            visible = [
                item
                for item in all_items
                if ctx.can_access_knowledge_space(item.knowledge_space_id)
            ]
            total = len(visible)
            page_items = visible[pagination.offset : pagination.offset + pagination.limit]
            return Page(
                items=page_items, limit=pagination.limit, offset=pagination.offset, total=total
            )

    async def update_metadata(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        document_id: UUID,
        *,
        title: str | None = None,
    ) -> Document:
        async with uow:
            ctx.require_permission("document:update")
            document = await uow.documents.get(ctx.organization_id, document_id)
            if document is None:
                raise ResourceNotFoundError("Document not found.")
            ctx.require_knowledge_space_access(document.knowledge_space_id)

            document.update_metadata(title=title)
            document = await uow.documents.update(document)

            event = build_audit_event(
                ctx,
                action="document.updated",
                resource_type="document",
                resource_id=document.id,
            )
            await uow.audit.add(event)
            return document

    async def replace_file(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        minio: ObjectStoragePort,
        document_id: UUID,
        *,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> Document:
        ensure_upload_size_within_limit(len(data))

        async with uow:
            ctx.require_permission("document:update")
            document = await uow.documents.get(ctx.organization_id, document_id)
            if document is None:
                raise ResourceNotFoundError("Document not found.")
            ctx.require_knowledge_space_access(document.knowledge_space_id)

            old_storage_key = document.storage_key
            new_storage_key = minio.build_object_key(
                document.organization_id, document.knowledge_space_id, document.id, filename
            )
            checksum = hashlib.sha256(data).hexdigest()

            await minio.put_object(new_storage_key, data, len(data), content_type)
            try:
                document.replace_file(
                    filename=filename,
                    content_type=content_type,
                    size_bytes=len(data),
                    storage_key=new_storage_key,
                    checksum_sha256=checksum,
                )
                document = await uow.documents.update(document)
                await uow.document_chunks.delete_by_document(document.id)
                await uow.document_parses.delete_by_document(document.id)
            except Exception:
                if new_storage_key != old_storage_key:
                    await minio.remove_object(new_storage_key)
                raise

            if new_storage_key != old_storage_key:
                try:
                    await minio.remove_object(old_storage_key)
                except Exception as exc:
                    logger.warning(
                        "document_old_object_cleanup_failed",
                        exc_info=exc,
                        extra={"storage_key": old_storage_key},
                    )

            event = build_audit_event(
                ctx,
                action="document.file_replaced",
                resource_type="document",
                resource_id=document.id,
                metadata={"filename": document.filename, "size_bytes": document.size_bytes},
            )
            await uow.audit.add(event)
            return document

    async def download(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        minio: ObjectStoragePort,
        document_id: UUID,
    ) -> tuple[Document, bytes]:
        async with uow:
            ctx.require_permission("document:read")
            document = await uow.documents.get(ctx.organization_id, document_id)
            if document is None:
                raise ResourceNotFoundError("Document not found.")
            ctx.require_knowledge_space_access(document.knowledge_space_id)

        data = await minio.get_object(document.storage_key)
        return document, data

    async def delete(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        minio: ObjectStoragePort,
        document_id: UUID,
    ) -> None:
        async with uow:
            ctx.require_permission("document:delete")
            document = await uow.documents.get(ctx.organization_id, document_id)
            if document is None:
                raise ResourceNotFoundError("Document not found.")
            ctx.require_knowledge_space_access(document.knowledge_space_id)

            document.soft_delete()
            document = await uow.documents.update(document)

            event = build_audit_event(
                ctx,
                action="document.deleted",
                resource_type="document",
                resource_id=document.id,
            )
            await uow.audit.add(event)

        try:
            await minio.remove_object(document.storage_key)
        except Exception as exc:
            logger.warning(
                "document_object_cleanup_failed",
                exc_info=exc,
                extra={"storage_key": document.storage_key},
            )


__all__ = ["DocumentService"]
