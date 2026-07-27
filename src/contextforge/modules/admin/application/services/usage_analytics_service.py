from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from contextforge.application.context.request_context import RequestContext
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.shared.utilities.datetime import utc_now


@dataclass(frozen=True, slots=True)
class UsageOverview:
    active_memberships: int
    conversations: int
    messages: int
    documents: int
    feedback_count: int


@dataclass(frozen=True, slots=True)
class UsageTrendPoint:
    day: str
    conversation_count: int


class UsageAnalyticsService:
    async def overview(self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext) -> UsageOverview:
        async with uow:
            ctx.require_permission("admin:usage")
            stats = await uow.admin_stats.usage_overview(ctx.organization_id)
            return UsageOverview(
                active_memberships=stats.active_memberships,
                conversations=stats.conversations,
                messages=stats.messages,
                documents=stats.documents,
                feedback_count=stats.feedback_count,
            )

    async def trends(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, *, days: int = 30
    ) -> list[UsageTrendPoint]:
        async with uow:
            ctx.require_permission("admin:usage")
            bounded = max(1, min(days, 365))
            since = utc_now() - timedelta(days=bounded)
            rows = await uow.admin_stats.usage_trends(ctx.organization_id, since=since)
            return [UsageTrendPoint(day=day, conversation_count=count) for day, count in rows]
