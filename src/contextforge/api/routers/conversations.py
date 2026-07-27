"""Conversation lifecycle, membership, messaging, suggestion, and export endpoints."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from fastapi.responses import StreamingResponse

from contextforge.api.dependencies.identity import get_request_context, get_uow
from contextforge.api.dependencies.pagination import get_pagination
from contextforge.api.dependencies.providers import (
    get_chat_analytics_service,
    get_chat_service,
    get_conversation_search_service,
    get_conversation_service,
    get_export_service,
    get_suggestion_service,
)
from contextforge.api.schemas.chat import (
    ChatAnalyticsOverviewResponse,
    ChatAnswerResponse,
    ChatMessageResponse,
    ConversationCreateRequest,
    ConversationParticipantResponse,
    ConversationResponse,
    ConversationUpdateRequest,
    KnowledgeSpaceLinkListResponse,
    KnowledgeSpaceLinkRequest,
    MessageSendRequest,
    ParticipantAddRequest,
    SuggestionsResponse,
)
from contextforge.api.schemas.common import PaginationMeta, PaginationResponse
from contextforge.application.context.request_context import RequestContext
from contextforge.application.pagination import PaginationParams
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.modules.chat.application.services.analytics_service import AnalyticsService
from contextforge.modules.chat.application.services.chat_service import ChatService
from contextforge.modules.chat.application.services.conversation_search_service import (
    ConversationSearchService,
)
from contextforge.modules.chat.application.services.conversation_service import (
    ConversationService,
)
from contextforge.modules.chat.application.services.export_service import ExportService
from contextforge.modules.chat.application.services.suggestion_service import SuggestionService
from contextforge.modules.chat.domain.entities.message import ChatMessage, MessageCitation
from contextforge.modules.chat.domain.enums import ConversationStatus, ExportFormat

router = APIRouter(prefix="/conversations", tags=["chat"])


def _message_response(
    message: ChatMessage, citations: list[MessageCitation] | None = None
) -> ChatMessageResponse:
    from contextforge.api.schemas.chat import MessageCitationResponse

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
        citations=[MessageCitationResponse.model_validate(c) for c in (citations or [])],
    )


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationResponse:
    conversation = await service.create(
        uow,
        ctx,
        title=payload.title,
        knowledge_space_ids=payload.knowledge_space_ids,
        preferred_language=payload.preferred_language,
    )
    return ConversationResponse.model_validate(conversation)


@router.get("", response_model=PaginationResponse[ConversationResponse])
async def list_conversations(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    status_filter: Annotated[ConversationStatus | None, Query(alias="status")] = None,
    pinned: Annotated[bool | None, Query()] = None,
) -> PaginationResponse[ConversationResponse]:
    page = await service.list_conversations(
        uow, ctx, pagination, status=status_filter, pinned=pinned
    )
    return PaginationResponse(
        items=[ConversationResponse.model_validate(item) for item in page.items],
        pagination=PaginationMeta(limit=page.limit, offset=page.offset, total=page.total),
    )


@router.get("/search", response_model=PaginationResponse[ConversationResponse])
async def search_conversations(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    service: Annotated[ConversationSearchService, Depends(get_conversation_search_service)],
    q: Annotated[str, Query(min_length=2, max_length=200)],
) -> PaginationResponse[ConversationResponse]:
    page = await service.search(uow, ctx, pagination, query=q)
    return PaginationResponse(
        items=[ConversationResponse.model_validate(item) for item in page.items],
        pagination=PaginationMeta(limit=page.limit, offset=page.offset, total=page.total),
    )


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationResponse:
    conversation = await service.get(uow, ctx, conversation_id)
    return ConversationResponse.model_validate(conversation)


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    payload: ConversationUpdateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationResponse:
    conversation = await service.update(
        uow,
        ctx,
        conversation_id,
        title=payload.title,
        pinned=payload.pinned,
        preferred_language=payload.preferred_language,
    )
    return ConversationResponse.model_validate(conversation)


@router.post("/{conversation_id}/archive", response_model=ConversationResponse)
async def archive_conversation(
    conversation_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationResponse:
    conversation = await service.archive(uow, ctx, conversation_id)
    return ConversationResponse.model_validate(conversation)


@router.post("/{conversation_id}/restore", response_model=ConversationResponse)
async def restore_conversation(
    conversation_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationResponse:
    conversation = await service.restore(uow, ctx, conversation_id)
    return ConversationResponse.model_validate(conversation)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> None:
    await service.delete(uow, ctx, conversation_id)


@router.get("/{conversation_id}/knowledge-spaces", response_model=KnowledgeSpaceLinkListResponse)
async def list_conversation_knowledge_spaces(
    conversation_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> KnowledgeSpaceLinkListResponse:
    ids = await service.list_knowledge_spaces(uow, ctx, conversation_id)
    return KnowledgeSpaceLinkListResponse(knowledge_space_ids=ids)


@router.post(
    "/{conversation_id}/knowledge-spaces",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def add_conversation_knowledge_space(
    conversation_id: UUID,
    payload: KnowledgeSpaceLinkRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> None:
    await service.add_knowledge_space(uow, ctx, conversation_id, payload.knowledge_space_id)


@router.delete(
    "/{conversation_id}/knowledge-spaces/{knowledge_space_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_conversation_knowledge_space(
    conversation_id: UUID,
    knowledge_space_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> None:
    await service.remove_knowledge_space(uow, ctx, conversation_id, knowledge_space_id)


@router.get(
    "/{conversation_id}/participants",
    response_model=list[ConversationParticipantResponse],
)
async def list_conversation_participants(
    conversation_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> list[ConversationParticipantResponse]:
    participants = await service.list_participants(uow, ctx, conversation_id)
    return [ConversationParticipantResponse.model_validate(item) for item in participants]


@router.post(
    "/{conversation_id}/participants",
    response_model=ConversationParticipantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_conversation_participant(
    conversation_id: UUID,
    payload: ParticipantAddRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationParticipantResponse:
    participant = await service.add_participant(
        uow, ctx, conversation_id, user_id=payload.user_id, role=payload.role
    )
    return ConversationParticipantResponse.model_validate(participant)


@router.delete(
    "/{conversation_id}/participants/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_conversation_participant(
    conversation_id: UUID,
    user_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> None:
    await service.remove_participant(uow, ctx, conversation_id, user_id)


@router.get("/{conversation_id}/messages", response_model=PaginationResponse[ChatMessageResponse])
async def list_conversation_messages(
    conversation_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> PaginationResponse[ChatMessageResponse]:
    await conversation_service.get(uow, ctx, conversation_id)
    async with uow:
        messages, total = await uow.chat_messages.list_by_conversation(
            ctx.organization_id,
            conversation_id,
            limit=pagination.limit,
            offset=pagination.offset,
            ascending=True,
        )
        citations_by_message = await uow.chat_messages.list_citations_for_messages(
            ctx.organization_id, [message.id for message in messages]
        )
    return PaginationResponse(
        items=[
            _message_response(message, citations_by_message.get(message.id)) for message in messages
        ],
        pagination=PaginationMeta(limit=pagination.limit, offset=pagination.offset, total=total),
    )


@router.post("/{conversation_id}/messages", response_model=ChatAnswerResponse)
async def send_conversation_message(
    conversation_id: UUID,
    payload: MessageSendRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[ChatService, Depends(get_chat_service)],
    idempotency_key_header: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ChatAnswerResponse:
    answer = await service.send_message(
        uow,
        ctx,
        conversation_id,
        content=payload.content,
        idempotency_key=idempotency_key_header or payload.idempotency_key,
    )
    return ChatAnswerResponse(
        user_message=_message_response(answer.user_message),
        assistant_message=_message_response(answer.assistant_message, answer.citations),
    )


@router.post("/{conversation_id}/messages/stream")
async def stream_conversation_message(
    conversation_id: UUID,
    payload: MessageSendRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[ChatService, Depends(get_chat_service)],
    idempotency_key_header: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> StreamingResponse:
    async def event_stream() -> AsyncIterator[str]:
        async for item in service.stream_send_message(
            uow,
            ctx,
            conversation_id,
            content=payload.content,
            idempotency_key=idempotency_key_header or payload.idempotency_key,
        ):
            event_name = item["event"]
            data = json.dumps(item["data"], ensure_ascii=False)
            yield f"event: {event_name}\ndata: {data}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post(
    "/{conversation_id}/messages/{message_id}/cancel",
    response_model=ChatMessageResponse,
)
async def cancel_conversation_message(
    conversation_id: UUID,
    message_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatMessageResponse:
    message = await service.cancel_message(uow, ctx, conversation_id, message_id)
    return _message_response(message)


@router.get("/{conversation_id}/suggestions", response_model=SuggestionsResponse)
async def get_conversation_suggestions(
    conversation_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[SuggestionService, Depends(get_suggestion_service)],
) -> SuggestionsResponse:
    suggestions = await service.suggest(uow, ctx, conversation_id)
    return SuggestionsResponse(suggestions=suggestions)


@router.get("/{conversation_id}/analytics", response_model=ChatAnalyticsOverviewResponse)
async def get_conversation_analytics(
    conversation_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[AnalyticsService, Depends(get_chat_analytics_service)],
    since: Annotated[datetime | None, Query()] = None,
) -> ChatAnalyticsOverviewResponse:
    overview = await service.get_overview(uow, ctx, since=since, conversation_id=conversation_id)
    return ChatAnalyticsOverviewResponse(
        total_messages=overview.total_messages,
        assistant_messages=overview.assistant_messages,
        failed_messages=overview.failed_messages,
        avg_latency_ms=overview.avg_latency_ms,
        avg_retrieval_ms=overview.avg_retrieval_ms,
        total_prompt_tokens=overview.total_prompt_tokens,
        total_completion_tokens=overview.total_completion_tokens,
        feedback_up_count=overview.feedback_up_count,
        feedback_down_count=overview.feedback_down_count,
        events_by_type=overview.events_by_type,
    )


@router.get("/{conversation_id}/export")
async def export_conversation(
    conversation_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[ExportService, Depends(get_export_service)],
    export_format: Annotated[ExportFormat, Query(alias="format")] = ExportFormat.JSON,
) -> StreamingResponse:
    if export_format == ExportFormat.MARKDOWN:
        return StreamingResponse(
            service.stream_markdown(uow, ctx, conversation_id),
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="conversation-{conversation_id}.md"'
            },
        )
    return StreamingResponse(
        service.stream_json(uow, ctx, conversation_id),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="conversation-{conversation_id}.json"'
        },
    )
