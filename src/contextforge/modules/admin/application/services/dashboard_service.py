"""Administration dashboard aggregations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from contextforge.application.context.request_context import RequestContext
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.shared.utilities.datetime import utc_now


@dataclass(frozen=True, slots=True)
class AdminDashboard:
    membership_count: int
    active_membership_count: int
    document_count: int
    conversation_count: int
    knowledge_space_count: int
    ingestion_pending: int
    ingestion_running: int
    ingestion_failed: int
    audit_recent_count: int
    token_usage_today: int


class DashboardService:
    async def get_dashboard(self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext) -> AdminDashboard:
        async with uow:
            ctx.require_permission("admin:dashboard")
            since = utc_now() - timedelta(hours=24)
            counts = await uow.admin_stats.dashboard_counts(ctx.organization_id, audit_since=since)
            token_usage_today = await uow.token_usage.total_for_day(
                ctx.organization_id, utc_now().date()
            )
            return AdminDashboard(
                membership_count=counts.membership_count,
                active_membership_count=counts.active_membership_count,
                document_count=counts.document_count,
                conversation_count=counts.conversation_count,
                knowledge_space_count=counts.knowledge_space_count,
                ingestion_pending=counts.ingestion_pending,
                ingestion_running=counts.ingestion_running,
                ingestion_failed=counts.ingestion_failed,
                audit_recent_count=counts.audit_recent_count,
                token_usage_today=token_usage_today,
            )
