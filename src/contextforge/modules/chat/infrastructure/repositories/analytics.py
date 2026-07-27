from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.chat.domain.entities.analytics import ChatAnalyticsEvent
from contextforge.modules.chat.domain.enums import AnalyticsEventType
from contextforge.modules.chat.infrastructure.models.analytics import ChatAnalyticsEventModel


class SqlAlchemyChatAnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: ChatAnalyticsEvent) -> ChatAnalyticsEvent:
        model = ChatAnalyticsEventModel(
            id=event.id,
            organization_id=event.organization_id,
            conversation_id=event.conversation_id,
            message_id=event.message_id,
            user_id=event.user_id,
            event_type=event.event_type.value,
            payload=event.payload,
            created_at=event.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return event

    async def count_by_event_type(
        self,
        organization_id: UUID,
        *,
        since: datetime | None = None,
        conversation_id: UUID | None = None,
    ) -> dict[str, int]:
        conditions = [ChatAnalyticsEventModel.organization_id == organization_id]
        if since is not None:
            conditions.append(ChatAnalyticsEventModel.created_at >= since)
        if conversation_id is not None:
            conditions.append(ChatAnalyticsEventModel.conversation_id == conversation_id)
        statement = (
            select(ChatAnalyticsEventModel.event_type, func.count())
            .where(and_(*conditions))
            .group_by(ChatAnalyticsEventModel.event_type)
        )
        result = await self._session.execute(statement)
        return {event_type: count for event_type, count in result.all()}

    @staticmethod
    def _to_entity(model: ChatAnalyticsEventModel) -> ChatAnalyticsEvent:
        return ChatAnalyticsEvent(
            organization_id=model.organization_id,
            event_type=AnalyticsEventType(model.event_type),
            id=model.id,
            conversation_id=model.conversation_id,
            message_id=model.message_id,
            user_id=model.user_id,
            payload=dict(model.payload),
            created_at=model.created_at,
        )


__all__ = ["SqlAlchemyChatAnalyticsRepository"]
