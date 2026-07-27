"""Application service for chat usage/quality analytics aggregations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import ResourceNotFoundError
from contextforge.modules.chat.application.services.access import ensure_conversation_access


@dataclass(frozen=True, slots=True)
class ChatAnalyticsOverview:
    """Aggregate chat usage and quality metrics."""

    total_messages: int
    assistant_messages: int
    failed_messages: int
    avg_latency_ms: float
    avg_retrieval_ms: float
    total_prompt_tokens: int
    total_completion_tokens: int
    feedback_up_count: int
    feedback_down_count: int
    events_by_type: dict[str, int]


class AnalyticsService:
    """Read-only aggregations over chat messages, feedback, and events."""

    async def get_overview(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        *,
        since: datetime | None = None,
        conversation_id: UUID | None = None,
    ) -> ChatAnalyticsOverview:
        async with uow:
            if conversation_id is None:
                ctx.require_permission("chat:manage")
            else:
                ctx.require_permission("chat:use")
                conversation = await uow.conversations.get(ctx.organization_id, conversation_id)
                if conversation is None:
                    raise ResourceNotFoundError("Conversation not found.")
                await ensure_conversation_access(uow, ctx, conversation)

            message_stats = await uow.chat_messages.aggregate_stats(
                ctx.organization_id, since=since, conversation_id=conversation_id
            )
            feedback_counts = await uow.message_feedback.counts_by_rating(
                ctx.organization_id, since=since, conversation_id=conversation_id
            )
            event_counts = await uow.chat_analytics.count_by_event_type(
                ctx.organization_id, since=since, conversation_id=conversation_id
            )

            return ChatAnalyticsOverview(
                total_messages=message_stats.total_messages,
                assistant_messages=message_stats.assistant_messages,
                failed_messages=message_stats.failed_messages,
                avg_latency_ms=message_stats.avg_latency_ms,
                avg_retrieval_ms=message_stats.avg_retrieval_ms,
                total_prompt_tokens=message_stats.total_prompt_tokens,
                total_completion_tokens=message_stats.total_completion_tokens,
                feedback_up_count=feedback_counts.get("up", 0),
                feedback_down_count=feedback_counts.get("down", 0),
                events_by_type=event_counts,
            )


__all__ = ["AnalyticsService", "ChatAnalyticsOverview"]
