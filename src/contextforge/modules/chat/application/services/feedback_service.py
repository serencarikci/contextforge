"""Application service for submitting and reading message feedback."""

from __future__ import annotations

from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.services.command_support import build_audit_event
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import InvalidResourceStateError, ResourceNotFoundError
from contextforge.modules.chat.application.services.access import ensure_conversation_access
from contextforge.modules.chat.domain.entities.analytics import ChatAnalyticsEvent
from contextforge.modules.chat.domain.entities.feedback import MessageFeedback
from contextforge.modules.chat.domain.enums import (
    AnalyticsEventType,
    FeedbackCategory,
    FeedbackRating,
    MessageRole,
)


class FeedbackService:
    """Use cases for recording per-user feedback on assistant messages."""

    async def submit(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        message_id: UUID,
        *,
        rating: FeedbackRating,
        score: int | None = None,
        category: FeedbackCategory | None = None,
        comment: str | None = None,
    ) -> MessageFeedback:
        async with uow:
            ctx.require_permission("chat:use")
            message = await uow.chat_messages.get(ctx.organization_id, message_id)
            if message is None:
                raise ResourceNotFoundError("Message not found.")
            if message.role != MessageRole.ASSISTANT:
                raise InvalidResourceStateError("Feedback can only be given on assistant messages.")

            conversation = await uow.conversations.get(ctx.organization_id, message.conversation_id)
            if conversation is None:
                raise ResourceNotFoundError("Conversation not found.")
            await ensure_conversation_access(uow, ctx, conversation)

            existing = await uow.message_feedback.get(ctx.organization_id, message_id, ctx.user_id)
            if existing is None:
                feedback = MessageFeedback(
                    message_id=message_id,
                    conversation_id=message.conversation_id,
                    organization_id=ctx.organization_id,
                    user_id=ctx.user_id,
                    rating=rating,
                    score=score,
                    category=category,
                    comment=comment,
                )
            else:
                existing.update(rating=rating, score=score, category=category, comment=comment)
                feedback = existing
            feedback = await uow.message_feedback.upsert(feedback)

            await uow.chat_analytics.add(
                ChatAnalyticsEvent(
                    organization_id=ctx.organization_id,
                    event_type=AnalyticsEventType.FEEDBACK_SUBMITTED,
                    conversation_id=message.conversation_id,
                    message_id=message_id,
                    user_id=ctx.user_id,
                    payload={"rating": rating.value},
                )
            )
            await uow.audit.add(
                build_audit_event(
                    ctx,
                    action="chat.feedback.submitted",
                    resource_type="message_feedback",
                    resource_id=feedback.id,
                    metadata={"rating": rating.value},
                )
            )
            return feedback

    async def delete(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, message_id: UUID
    ) -> None:
        async with uow:
            ctx.require_permission("chat:use")
            message = await uow.chat_messages.get(ctx.organization_id, message_id)
            if message is None:
                raise ResourceNotFoundError("Message not found.")
            conversation = await uow.conversations.get(ctx.organization_id, message.conversation_id)
            if conversation is None:
                raise ResourceNotFoundError("Conversation not found.")
            await ensure_conversation_access(uow, ctx, conversation)
            deleted = await uow.message_feedback.delete(
                ctx.organization_id, message_id, ctx.user_id
            )
            if not deleted:
                raise ResourceNotFoundError("Feedback not found.")
            await uow.audit.add(
                build_audit_event(
                    ctx,
                    action="chat.feedback.deleted",
                    resource_type="message_feedback",
                    resource_id=message_id,
                    metadata={},
                )
            )


__all__ = ["FeedbackService"]
