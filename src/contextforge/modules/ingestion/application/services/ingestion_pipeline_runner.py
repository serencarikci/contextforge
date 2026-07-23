"""Background pipeline runner: parse -> chunk -> embed with failure handling."""

from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from contextforge.application.ports.ingestion_job_queue import IngestionJobQueuePort
from contextforge.application.ports.object_storage import ObjectStoragePort
from contextforge.application.ports.vector_store import VectorStorePort
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.modules.documents.application.ports.document_chunker import DocumentChunkerPort
from contextforge.modules.documents.application.ports.document_parser import DocumentParserPort
from contextforge.modules.documents.application.services.document_chunking_service import (
    DocumentChunkingService,
)
from contextforge.modules.documents.application.services.document_embedding_service import (
    DocumentEmbeddingService,
)
from contextforge.modules.documents.application.services.document_parsing_service import (
    DocumentParsingService,
)
from contextforge.modules.documents.domain.enums import DocumentParseStatus
from contextforge.modules.documents.domain.exceptions import DocumentEmbeddingError
from contextforge.modules.identity_access.application.services.identity_context_service import (
    build_request_context,
)
from contextforge.modules.ingestion.domain.enums import IngestionJobStep
from contextforge.modules.ingestion.domain.exceptions import IngestionJobError
from contextforge.shared.config.settings import IngestionSettings, Settings
from contextforge.shared.logging.setup import get_logger

logger = get_logger(__name__)


class IngestionPipelineRunner:
    """Processes one ingestion job end-to-end for a background worker."""

    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        queue: IngestionJobQueuePort,
        storage: ObjectStoragePort,
        parser: DocumentParserPort,
        chunker: DocumentChunkerPort,
        embedding_service: DocumentEmbeddingService,
        vector_store: VectorStorePort,
        ingestion_settings: IngestionSettings | None = None,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._queue = queue
        self._storage = storage
        self._parser = parser
        self._chunker = chunker
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._ingestion_settings = ingestion_settings or settings.ingestion
        self._parsing_service = DocumentParsingService(parser)
        self._chunking_service = DocumentChunkingService(chunker)

    def _uow(self) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self._session_factory)

    async def process_job(self, job_id: UUID) -> None:
        uow = self._uow()
        async with uow:
            claimed = await uow.ingestion_jobs.claim(job_id)
            if claimed is None:
                logger.info("ingestion_job_not_claimable", extra={"job_id": str(job_id)})
                return
            job = claimed

        try:
            await self._run_pipeline(job_id=job.id)
        except Exception as exc:
            await self._handle_failure(job_id, exc)

    async def _run_pipeline(self, *, job_id: UUID) -> None:
        uow = self._uow()
        async with uow:
            job = await uow.ingestion_jobs.get_by_id(job_id)
            if job is None:
                return
            ctx = await build_request_context(
                uow,
                settings=self._settings,
                user_id=job.requested_by_user_id,
                organization_id=job.organization_id,
                knowledge_space_id=job.knowledge_space_id,
            )
            document_id = job.document_id

        parse_uow = self._uow()
        parse_result = await self._parsing_service.parse_document(
            parse_uow, ctx, self._storage, document_id
        )
        if parse_result.status is not DocumentParseStatus.SUCCEEDED:
            raise IngestionJobError(
                parse_result.error_message or "Document parsing failed.",
                code=parse_result.error_code or IngestionJobError.code,
            )

        await self._set_step(job_id, IngestionJobStep.CHUNK)
        chunk_uow = self._uow()
        chunks = await self._chunking_service.chunk_document(
            chunk_uow, ctx, document_id, vector_store=self._vector_store
        )
        if not chunks:
            raise IngestionJobError("Chunking produced no chunks.")

        await self._set_step(job_id, IngestionJobStep.EMBED)
        embed_uow = self._uow()
        embed_result = await self._embedding_service.embed_document(
            embed_uow, ctx, document_id, force=True
        )
        if embed_result.failed_count > 0 or embed_result.embedded_count == 0:
            raise DocumentEmbeddingError(
                f"Embedding failed for {embed_result.failed_count} chunk(s)."
            )

        finish_uow = self._uow()
        async with finish_uow:
            job = await finish_uow.ingestion_jobs.get_by_id(job_id)
            if job is None:
                return
            job.mark_succeeded()
            await finish_uow.ingestion_jobs.update(job)
        logger.info(
            "ingestion_job_succeeded",
            extra={"job_id": str(job_id), "document_id": str(document_id)},
        )

    async def _set_step(self, job_id: UUID, step: IngestionJobStep) -> None:
        uow = self._uow()
        async with uow:
            job = await uow.ingestion_jobs.get_by_id(job_id)
            if job is None:
                return
            job.advance_step(step)
            await uow.ingestion_jobs.update(job)

    async def _handle_failure(self, job_id: UUID, exc: Exception) -> None:
        error_code = getattr(exc, "code", IngestionJobError.code)
        error_message = getattr(exc, "message", str(exc))
        should_requeue = False

        uow = self._uow()
        async with uow:
            job = await uow.ingestion_jobs.get_by_id(job_id)
            if job is None:
                return
            job.register_attempt_failure(error_code=str(error_code), error_message=error_message)
            if job.can_retry:
                job.requeue_for_retry()
                should_requeue = True
            else:
                job.mark_failed()
            await uow.ingestion_jobs.update(job)
            document_id = job.document_id
            attempt_count = job.attempt_count

        logger.warning(
            "ingestion_job_failed",
            extra={
                "job_id": str(job_id),
                "document_id": str(document_id),
                "attempt_count": attempt_count,
                "error_code": error_code,
                "requeue": should_requeue,
            },
            exc_info=exc,
        )

        if should_requeue:
            delay = self._ingestion_settings.retry_backoff_seconds * (
                2 ** max(attempt_count - 1, 0)
            )
            await asyncio.sleep(delay)
            await self._queue.enqueue(job_id)


__all__ = ["IngestionPipelineRunner"]
