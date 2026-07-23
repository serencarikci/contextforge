"""Application service for semantic document chunking use cases."""

from __future__ import annotations

import asyncio
from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.services.command_support import build_audit_event
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import InvalidResourceStateError, ResourceNotFoundError
from contextforge.modules.documents.application.ports.document_chunker import DocumentChunkerPort
from contextforge.modules.documents.domain.entities.document_chunk import DocumentChunk
from contextforge.modules.documents.domain.enums import DocumentParseStatus
from contextforge.modules.documents.domain.exceptions import DocumentChunkError
from contextforge.shared.logging.setup import get_logger
from contextforge.shared.types.aliases import JSONValue

logger = get_logger(__name__)


class DocumentChunkingService:
    """Builds retrieval-ready chunks from a successful document parse result."""

    def __init__(self, chunker: DocumentChunkerPort) -> None:
        self._chunker = chunker

    async def chunk_document(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        document_id: UUID,
    ) -> list[DocumentChunk]:
        async with uow:
            ctx.require_permission("document:update")
            document = await uow.documents.get(ctx.organization_id, document_id)
            if document is None:
                raise ResourceNotFoundError("Document not found.")
            ctx.require_knowledge_space_access(document.knowledge_space_id)

            parse_result = await uow.document_parses.get_by_document(
                ctx.organization_id, document_id
            )
            if parse_result is None:
                raise InvalidResourceStateError(
                    "Document must be parsed successfully before chunking."
                )
            if parse_result.status is not DocumentParseStatus.SUCCEEDED:
                raise InvalidResourceStateError("Document parse failed; re-parse before chunking.")
            if not parse_result.extracted_text or not parse_result.extracted_text.strip():
                raise InvalidResourceStateError("Parsed document text is empty.")

            document_metadata: dict[str, JSONValue] = {
                "document_title": document.title,
                "document_filename": document.filename,
                "document_content_type": document.content_type,
            }
            if "title" in parse_result.metadata:
                document_metadata["parse_title"] = parse_result.metadata["title"]
            if "author" in parse_result.metadata:
                document_metadata["parse_author"] = parse_result.metadata["author"]

            text = parse_result.extracted_text
            fmt = parse_result.format
            parse_result_id = parse_result.id
            organization_id = document.organization_id
            knowledge_space_id = document.knowledge_space_id

            try:
                drafts = await asyncio.to_thread(
                    self._chunker.chunk,
                    text=text,
                    format=fmt,
                    document_metadata=document_metadata,
                )
            except DocumentChunkError:
                raise
            except Exception as exc:
                logger.warning(
                    "document_chunk_unexpected_error",
                    exc_info=exc,
                    extra={"document_id": str(document_id)},
                )
                raise DocumentChunkError(f"Failed to chunk document: {exc}") from exc

            chunks = [
                DocumentChunk.from_draft(
                    draft,
                    organization_id=organization_id,
                    document_id=document_id,
                    parse_result_id=parse_result_id,
                    knowledge_space_id=knowledge_space_id,
                )
                for draft in drafts
            ]
            stored = await uow.document_chunks.replace_for_document(
                organization_id, document_id, chunks
            )

            event = build_audit_event(
                ctx,
                action="document.chunked",
                resource_type="document",
                resource_id=document_id,
                metadata={
                    "chunk_count": len(stored),
                    "parse_result_id": str(parse_result_id),
                    "total_tokens": sum(chunk.token_count for chunk in stored),
                },
            )
            await uow.audit.add(event)
            return stored

    async def list_chunks(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        document_id: UUID,
    ) -> list[DocumentChunk]:
        async with uow:
            ctx.require_permission("document:read")
            document = await uow.documents.get(ctx.organization_id, document_id)
            if document is None:
                raise ResourceNotFoundError("Document not found.")
            ctx.require_knowledge_space_access(document.knowledge_space_id)
            return await uow.document_chunks.list_by_document(ctx.organization_id, document_id)


__all__ = ["DocumentChunkingService"]
