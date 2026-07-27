from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.chat.domain.entities.feedback import MessageFeedback
from contextforge.modules.chat.domain.enums import FeedbackCategory, FeedbackRating
from contextforge.modules.chat.infrastructure.models.feedback import MessageFeedbackModel


class SqlAlchemyMessageFeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, organization_id: UUID, message_id: UUID, user_id: UUID
    ) -> MessageFeedback | None:
        statement = select(MessageFeedbackModel).where(
            MessageFeedbackModel.organization_id == organization_id,
            MessageFeedbackModel.message_id == message_id,
            MessageFeedbackModel.user_id == user_id,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def upsert(self, feedback: MessageFeedback) -> MessageFeedback:
        statement = select(MessageFeedbackModel).where(
            MessageFeedbackModel.organization_id == feedback.organization_id,
            MessageFeedbackModel.message_id == feedback.message_id,
            MessageFeedbackModel.user_id == feedback.user_id,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            model = MessageFeedbackModel(
                id=feedback.id,
                message_id=feedback.message_id,
                conversation_id=feedback.conversation_id,
                organization_id=feedback.organization_id,
                user_id=feedback.user_id,
                rating=feedback.rating.value,
                score=feedback.score,
                category=feedback.category.value if feedback.category else None,
                comment=feedback.comment,
                created_at=feedback.created_at,
                updated_at=feedback.updated_at,
            )
            self._session.add(model)
        else:
            model.rating = feedback.rating.value
            model.score = feedback.score
            model.category = feedback.category.value if feedback.category else None
            model.comment = feedback.comment
            model.updated_at = feedback.updated_at
        await self._session.flush()
        return self._to_entity(model)

    async def delete(self, organization_id: UUID, message_id: UUID, user_id: UUID) -> bool:
        statement = select(MessageFeedbackModel).where(
            MessageFeedbackModel.organization_id == organization_id,
            MessageFeedbackModel.message_id == message_id,
            MessageFeedbackModel.user_id == user_id,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    async def counts_by_rating(
        self,
        organization_id: UUID,
        *,
        since: datetime | None = None,
        conversation_id: UUID | None = None,
    ) -> dict[str, int]:
        conditions = [MessageFeedbackModel.organization_id == organization_id]
        if since is not None:
            conditions.append(MessageFeedbackModel.created_at >= since)
        if conversation_id is not None:
            conditions.append(MessageFeedbackModel.conversation_id == conversation_id)
        statement = (
            select(MessageFeedbackModel.rating, func.count())
            .where(and_(*conditions))
            .group_by(MessageFeedbackModel.rating)
        )
        result = await self._session.execute(statement)
        return {rating: count for rating, count in result.all()}

    @staticmethod
    def _to_entity(model: MessageFeedbackModel) -> MessageFeedback:
        return MessageFeedback(
            message_id=model.message_id,
            conversation_id=model.conversation_id,
            organization_id=model.organization_id,
            user_id=model.user_id,
            rating=FeedbackRating(model.rating),
            id=model.id,
            score=model.score,
            category=FeedbackCategory(model.category) if model.category else None,
            comment=model.comment,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


__all__ = ["SqlAlchemyMessageFeedbackRepository"]
