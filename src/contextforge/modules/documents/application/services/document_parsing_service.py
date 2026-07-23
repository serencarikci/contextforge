"""Application service for document text extraction use cases."""

from __future__ import annotations

import asyncio
from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.ports.object_storage import ObjectStoragePort
from contextforge.application.services.command_support import build_audit_event
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import ResourceNotFoundError
from contextforge.modules.documents.application.ports.document_parser import DocumentParserPort
from contextforge.modules.documents.domain.entities.document_parse_result import DocumentParseResult
from contextforge.modules.documents.domain.enums import DocumentParseStatus
from contextforge.modules.documents.domain.exceptions import (
    DocumentParseError,
    UnsupportedDocumentFormatError,
)
from contextforge.modules.documents.domain.format_detection import detect_document_format
from contextforge.shared.logging.setup import get_logger

logger = get_logger(__name__)


class DocumentParsingService:
    """Loads stored documents and extracts text/metadata via a parser port."""

    def __init__(self, parser: DocumentParserPort) -> None:
        self._parser = parser

    async def parse_document(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        storage: ObjectStoragePort,
        document_id: UUID,
    ) -> DocumentParseResult:
        async with uow:
            ctx.require_permission("document:update")
            document = await uow.documents.get(ctx.organization_id, document_id)
            if document is None:
                raise ResourceNotFoundError("Document not found.")
            ctx.require_knowledge_space_access(document.knowledge_space_id)

            try:
                detected_format = detect_document_format(
                    filename=document.filename,
                    content_type=document.content_type,
                )
            except UnsupportedDocumentFormatError:
                raise

            existing = await uow.document_parses.get_by_document(ctx.organization_id, document_id)
            storage_key = document.storage_key
            organization_id = document.organization_id
            filename = document.filename
            existing_id = existing.id if existing is not None else None
            created_at = existing.created_at if existing is not None else None

        data = await storage.get_object(storage_key)

        try:
            content = await asyncio.to_thread(
                self._parser.parse,
                format=detected_format,
                data=data,
                filename=filename,
            )
            result = DocumentParseResult.succeeded(
                organization_id=organization_id,
                document_id=document_id,
                format=detected_format,
                content=content,
                existing_id=existing_id,
                created_at=created_at,
            )
        except (DocumentParseError, UnsupportedDocumentFormatError) as exc:
            result = DocumentParseResult.failed(
                organization_id=organization_id,
                document_id=document_id,
                format=detected_format,
                error_code=exc.code,
                error_message=exc.message,
                existing_id=existing_id,
                created_at=created_at,
            )
            logger.info(
                "document_parse_failed",
                extra={
                    "document_id": str(document_id),
                    "format": detected_format.value,
                    "error_code": exc.code,
                },
            )
        except Exception as exc:
            result = DocumentParseResult.failed(
                organization_id=organization_id,
                document_id=document_id,
                format=detected_format,
                error_code=DocumentParseError.code,
                error_message=f"Unexpected parse failure: {exc}",
                existing_id=existing_id,
                created_at=created_at,
            )
            logger.warning(
                "document_parse_unexpected_error",
                exc_info=exc,
                extra={"document_id": str(document_id), "format": detected_format.value},
            )

        async with uow:
            ctx.require_permission("document:update")
            document = await uow.documents.get(ctx.organization_id, document_id)
            if document is None:
                raise ResourceNotFoundError("Document not found.")
            ctx.require_knowledge_space_access(document.knowledge_space_id)

            result = await uow.document_parses.upsert(result)
            await uow.document_chunks.delete_by_document(document_id)
            action = (
                "document.parsed"
                if result.status is DocumentParseStatus.SUCCEEDED
                else "document.parse_failed"
            )
            event = build_audit_event(
                ctx,
                action=action,
                resource_type="document",
                resource_id=document_id,
                metadata={
                    "format": result.format.value,
                    "status": result.status.value,
                    "character_count": result.character_count,
                    "error_code": result.error_code,
                },
            )
            await uow.audit.add(event)
            return result

    async def get_parse_result(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        document_id: UUID,
    ) -> DocumentParseResult:
        async with uow:
            ctx.require_permission("document:read")
            document = await uow.documents.get(ctx.organization_id, document_id)
            if document is None:
                raise ResourceNotFoundError("Document not found.")
            ctx.require_knowledge_space_access(document.knowledge_space_id)

            result = await uow.document_parses.get_by_document(ctx.organization_id, document_id)
            if result is None:
                raise ResourceNotFoundError("Document parse result not found.")
            return result


__all__ = ["DocumentParsingService"]
