from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from contextforge.api.dependencies.identity import get_request_context, get_uow
from contextforge.api.dependencies.providers import get_feedback_service
from contextforge.api.schemas.chat import (
    ChatMessageResponse,
    MessageCitationResponse,
    MessageFeedbackRequest,
    MessageFeedbackResponse,
)
from contextforge.application.context.request_context import RequestContext
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import ResourceNotFoundError
from contextforge.modules.chat.application.services.access import ensure_conversation_access
from contextforge.modules.chat.application.services.feedback_service import FeedbackService

router = APIRouter(prefix="/messages", tags=["chat"])


@router.get("/{message_id}", response_model=ChatMessageResponse)
async def get_message(
    message_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ChatMessageResponse:
    async with uow:
        ctx.require_permission("chat:use")
        message = await uow.chat_messages.get(ctx.organization_id, message_id)
        if message is None:
            raise ResourceNotFoundError("Message not found.")
        conversation = await uow.conversations.get(ctx.organization_id, message.conversation_id)
        if conversation is None:
            raise ResourceNotFoundError("Conversation not found.")
        await ensure_conversation_access(uow, ctx, conversation)
        citations = await uow.chat_messages.list_citations(ctx.organization_id, message_id)

    return ChatMessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        role=message.role,
        status=message.status,
        content=message.content,
        language=message.language,
        sequence_no=message.sequence_no,
        parent_message_id=message.parent_message_id,
        model_name=message.model_name,
        prompt_tokens=message.prompt_tokens,
        completion_tokens=message.completion_tokens,
        total_tokens=message.total_tokens,
        latency_ms=message.latency_ms,
        retrieval_ms=message.retrieval_ms,
        error_code=message.error_code,
        error_message=message.error_message,
        created_at=message.created_at,
        updated_at=message.updated_at,
        citations=[MessageCitationResponse.model_validate(c) for c in citations],
    )


@router.put(
    "/{message_id}/feedback",
    response_model=MessageFeedbackResponse,
    status_code=status.HTTP_200_OK,
)
async def submit_message_feedback(
    message_id: UUID,
    payload: MessageFeedbackRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[FeedbackService, Depends(get_feedback_service)],
) -> MessageFeedbackResponse:
    feedback = await service.submit(
        uow,
        ctx,
        message_id,
        rating=payload.rating,
        score=payload.score,
        category=payload.category,
        comment=payload.comment,
    )
    return MessageFeedbackResponse.model_validate(feedback)


@router.delete("/{message_id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message_feedback(
    message_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[FeedbackService, Depends(get_feedback_service)],
) -> None:
    await service.delete(uow, ctx, message_id)
