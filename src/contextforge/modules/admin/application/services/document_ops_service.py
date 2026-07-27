from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.ports.ingestion_job_queue import IngestionJobQueuePort
from contextforge.application.services.command_support import build_audit_event
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.modules.admin.infrastructure.repositories.admin_stats import DocumentOverviewStats
from contextforge.modules.ingestion.domain.entities.ingestion_job import IngestionJob
from contextforge.shared.config.settings import IngestionSettings


@dataclass(frozen=True, slots=True)
class BulkDocumentResult:
    processed: int
    skipped: int
    job_ids: list[UUID]


class DocumentOpsService:
    def __init__(self, ingestion_settings: IngestionSettings) -> None:
        self._ingestion = ingestion_settings

    async def overview(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext
    ) -> DocumentOverviewStats:
        async with uow:
            ctx.require_permission("admin:documents")
            return await uow.admin_stats.document_overview(ctx.organization_id)

    async def bulk_reprocess(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        queue: IngestionJobQueuePort,
        document_ids: list[UUID],
    ) -> BulkDocumentResult:
        job_ids: list[UUID] = []
        processed = 0
        skipped = 0
        async with uow:
            ctx.require_permission("admin:documents")
            for document_id in document_ids:
                document = await uow.documents.get(ctx.organization_id, document_id)
                if document is None or document.status.value != "active":
                    skipped += 1
                    continue
                job = IngestionJob.create(
                    organization_id=ctx.organization_id,
                    document_id=document.id,
                    knowledge_space_id=document.knowledge_space_id,
                    requested_by_user_id=ctx.user_id,
                    max_attempts=self._ingestion.max_attempts,
                )
                job = await uow.ingestion_jobs.add(job)
                job_ids.append(job.id)
                processed += 1
            event = build_audit_event(
                ctx,
                action="documents.bulk_reprocess",
                resource_type="document",
                resource_id=None,
                metadata={"processed": processed, "skipped": skipped},
            )
            await uow.audit.add(event)

        for job_id in job_ids:
            await queue.enqueue(job_id)
        return BulkDocumentResult(processed=processed, skipped=skipped, job_ids=job_ids)

    async def bulk_delete(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        document_ids: list[UUID],
    ) -> BulkDocumentResult:
        processed = 0
        skipped = 0
        async with uow:
            ctx.require_permission("admin:documents")
            for document_id in document_ids:
                document = await uow.documents.get(ctx.organization_id, document_id)
                if document is None:
                    skipped += 1
                    continue
                try:
                    document.soft_delete()
                except Exception:
                    skipped += 1
                    continue
                await uow.documents.update(document)
                processed += 1
            event = build_audit_event(
                ctx,
                action="documents.bulk_delete",
                resource_type="document",
                resource_id=None,
                metadata={"processed": processed, "skipped": skipped},
            )
            await uow.audit.add(event)
        return BulkDocumentResult(processed=processed, skipped=skipped, job_ids=[])
