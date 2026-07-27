from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.ports.ingestion_job_queue import IngestionJobQueuePort
from contextforge.application.services.command_support import build_audit_event
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import InvalidResourceStateError, ResourceNotFoundError
from contextforge.modules.ingestion.domain.entities.ingestion_job import IngestionJob
from contextforge.modules.ingestion.domain.enums import IngestionJobStatus


@dataclass(frozen=True, slots=True)
class IngestionOpsOverview:
    by_status: dict[str, int]
    queue_depth: int | None


class IngestionOpsService:
    async def overview(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        queue: IngestionJobQueuePort | None = None,
    ) -> IngestionOpsOverview:
        async with uow:
            ctx.require_permission("admin:ingestion")
            stats = await uow.admin_stats.ingestion_overview(ctx.organization_id)
        queue_depth: int | None = None
        if queue is not None and hasattr(queue, "depth"):
            try:
                queue_depth = int(await queue.depth())
            except Exception:
                queue_depth = None
        return IngestionOpsOverview(by_status=stats.by_status, queue_depth=queue_depth)

    async def cancel(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, job_id: UUID
    ) -> IngestionJob:
        async with uow:
            ctx.require_permission("admin:ingestion")
            job = await uow.ingestion_jobs.get(ctx.organization_id, job_id)
            if job is None:
                raise ResourceNotFoundError("Ingestion job not found.")
            if job.status != IngestionJobStatus.PENDING:
                raise InvalidResourceStateError("Only pending ingestion jobs can be cancelled.")
            job.cancel()
            job = await uow.ingestion_jobs.update(job)
            event = build_audit_event(
                ctx,
                action="ingestion_job.cancelled",
                resource_type="ingestion_job",
                resource_id=job.id,
            )
            await uow.audit.add(event)
            return job
