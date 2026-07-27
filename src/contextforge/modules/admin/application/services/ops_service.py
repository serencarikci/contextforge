from __future__ import annotations

from dataclasses import dataclass

from contextforge.application.context.request_context import RequestContext
from contextforge.application.ports.ingestion_job_queue import IngestionJobQueuePort
from contextforge.application.services.health_service import HealthService, ReadinessReport
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.shared.config.settings import Settings


@dataclass(frozen=True, slots=True)
class OpsOverview:
    readiness: ReadinessReport
    ingestion_pending: int
    ingestion_failed: int
    queue_depth: int | None
    llm_configured: bool
    retention_enabled: bool


class OpsService:
    def __init__(self, health: HealthService, settings: Settings) -> None:
        self._health = health
        self._settings = settings

    async def overview(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        queue: IngestionJobQueuePort | None = None,
    ) -> OpsOverview:
        async with uow:
            ctx.require_permission("admin:ops")
            ingestion = await uow.admin_stats.ingestion_overview(ctx.organization_id)
            llm_configs = await uow.llm_provider_configs.list_for_organization(
                ctx.organization_id, include_global=True
            )
            llm_configured = any(cfg.is_active for cfg in llm_configs) or bool(
                self._settings.llm.provider
            )
        readiness = await self._health.check_readiness()
        queue_depth: int | None = None
        if queue is not None:
            try:
                queue_depth = await queue.depth()
            except Exception:
                queue_depth = None
        return OpsOverview(
            readiness=readiness,
            ingestion_pending=ingestion.by_status.get("pending", 0),
            ingestion_failed=ingestion.by_status.get("failed", 0),
            queue_depth=queue_depth,
            llm_configured=llm_configured,
            retention_enabled=self._settings.admin.retention_enabled,
        )
