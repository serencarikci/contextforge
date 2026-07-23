"""Application service for enqueueing and querying ingestion jobs."""

from __future__ import annotations

from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.pagination import Page, PaginationParams
from contextforge.application.ports.ingestion_job_queue import IngestionJobQueuePort
from contextforge.application.services.command_support import build_audit_event
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import InvalidResourceStateError, ResourceNotFoundError
from contextforge.modules.ingestion.domain.entities.ingestion_job import IngestionJob
from contextforge.modules.ingestion.domain.enums import IngestionJobStatus
from contextforge.shared.config.settings import IngestionSettings
from contextforge.shared.logging.setup import get_logger

logger = get_logger(__name__)


class IngestionJobService:
    """Creates and manages durable document ingestion jobs."""

    def __init__(self, settings: IngestionSettings) -> None:
        self._settings = settings

    async def enqueue_for_document(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        queue: IngestionJobQueuePort,
        *,
        document_id: UUID,
        knowledge_space_id: UUID,
    ) -> IngestionJob | None:
        if not self._settings.enabled:
            return None

        async with uow:
            ctx.require_permission("document:create")
            document = await uow.documents.get(ctx.organization_id, document_id)
            if document is None:
                raise ResourceNotFoundError("Document not found.")
            ctx.require_knowledge_space_access(document.knowledge_space_id)

            job = IngestionJob.create(
                organization_id=ctx.organization_id,
                document_id=document.id,
                knowledge_space_id=knowledge_space_id,
                requested_by_user_id=ctx.user_id,
                max_attempts=self._settings.max_attempts,
            )
            job = await uow.ingestion_jobs.add(job)
            event = build_audit_event(
                ctx,
                action="ingestion_job.enqueued",
                resource_type="ingestion_job",
                resource_id=job.id,
                metadata={"document_id": str(document_id)},
            )
            await uow.audit.add(event)

        await queue.enqueue(job.id)
        logger.info(
            "ingestion_job_created",
            extra={"job_id": str(job.id), "document_id": str(document_id)},
        )
        return job

    async def get(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, job_id: UUID
    ) -> IngestionJob:
        async with uow:
            ctx.require_permission("document:read")
            job = await uow.ingestion_jobs.get(ctx.organization_id, job_id)
            if job is None:
                raise ResourceNotFoundError("Ingestion job not found.")
            ctx.require_knowledge_space_access(job.knowledge_space_id)
            return job

    async def list_for_document(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        document_id: UUID,
    ) -> list[IngestionJob]:
        async with uow:
            ctx.require_permission("document:read")
            document = await uow.documents.get(ctx.organization_id, document_id)
            if document is None:
                raise ResourceNotFoundError("Document not found.")
            ctx.require_knowledge_space_access(document.knowledge_space_id)
            return await uow.ingestion_jobs.list_by_document(ctx.organization_id, document_id)

    async def list(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        pagination: PaginationParams,
        *,
        status: IngestionJobStatus | None = None,
    ) -> Page[IngestionJob]:
        async with uow:
            ctx.require_permission("document:read")
            items, total = await uow.ingestion_jobs.list_by_organization(
                ctx.organization_id,
                status=status,
                limit=pagination.limit,
                offset=pagination.offset,
            )
            return Page(items=items, limit=pagination.limit, offset=pagination.offset, total=total)

    async def retry_failed(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        queue: IngestionJobQueuePort,
        job_id: UUID,
    ) -> IngestionJob:
        async with uow:
            ctx.require_permission("document:update")
            job = await uow.ingestion_jobs.get(ctx.organization_id, job_id)
            if job is None:
                raise ResourceNotFoundError("Ingestion job not found.")
            ctx.require_knowledge_space_access(job.knowledge_space_id)
            if job.status is not IngestionJobStatus.FAILED:
                raise InvalidResourceStateError("Only failed ingestion jobs can be retried.")
            job.reset_for_manual_retry()
            job = await uow.ingestion_jobs.update(job)
            event = build_audit_event(
                ctx,
                action="ingestion_job.retried",
                resource_type="ingestion_job",
                resource_id=job.id,
                metadata={"document_id": str(job.document_id)},
            )
            await uow.audit.add(event)

        await queue.enqueue(job.id)
        return job


__all__ = ["IngestionJobService"]
