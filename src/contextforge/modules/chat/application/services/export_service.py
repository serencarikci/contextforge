from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.services.command_support import build_audit_event
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import ResourceNotFoundError
from contextforge.modules.chat.application.services.access import ensure_conversation_access
from contextforge.modules.chat.domain.entities.analytics import ChatAnalyticsEvent
from contextforge.modules.chat.domain.entities.conversation import Conversation
from contextforge.modules.chat.domain.entities.message import ChatMessage, MessageCitation
from contextforge.modules.chat.domain.enums import AnalyticsEventType, ExportFormat
from contextforge.shared.config.settings import ChatSettings


@dataclass(frozen=True, slots=True)
class _ExportBundle:
    conversation: Conversation
    turns: list[tuple[ChatMessage, list[MessageCitation]]]


class ExportService:
    def __init__(self, settings: ChatSettings) -> None:
        self._settings = settings

    async def _load(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        conversation_id: UUID,
        *,
        export_format: ExportFormat,
    ) -> _ExportBundle:
        async with uow:
            ctx.require_permission("chat:use")
            conversation = await uow.conversations.get(ctx.organization_id, conversation_id)
            if conversation is None:
                raise ResourceNotFoundError("Conversation not found.")
            await ensure_conversation_access(uow, ctx, conversation)

            messages, _total = await uow.chat_messages.list_by_conversation(
                ctx.organization_id,
                conversation_id,
                limit=self._settings.export_max_messages,
                offset=0,
                ascending=True,
            )
            citations_by_message = await uow.chat_messages.list_citations_for_messages(
                ctx.organization_id, [message.id for message in messages]
            )
            turns = [(message, citations_by_message.get(message.id, [])) for message in messages]

            await uow.chat_analytics.add(
                ChatAnalyticsEvent(
                    organization_id=ctx.organization_id,
                    event_type=AnalyticsEventType.CONVERSATION_EXPORTED,
                    conversation_id=conversation_id,
                    user_id=ctx.user_id,
                    payload={"format": export_format.value, "message_count": len(turns)},
                )
            )
            await uow.audit.add(
                build_audit_event(
                    ctx,
                    action="chat.conversation.exported",
                    resource_type="conversation",
                    resource_id=conversation_id,
                    metadata={"format": export_format.value},
                )
            )
        return _ExportBundle(conversation=conversation, turns=turns)

    async def stream_json(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, conversation_id: UUID
    ) -> AsyncIterator[str]:
        bundle = await self._load(uow, ctx, conversation_id, export_format=ExportFormat.JSON)
        conversation = bundle.conversation

        header = {
            "conversation_id": str(conversation.id),
            "title": conversation.title,
            "status": conversation.status.value,
            "preferred_language": conversation.preferred_language.value,
            "detected_language": conversation.detected_language,
            "created_at": conversation.created_at.isoformat(),
        }
        yield "{"
        yield json.dumps(header, ensure_ascii=False)[1:-1]
        yield ', "messages": ['
        for index, (message, citations) in enumerate(bundle.turns):
            if index > 0:
                yield ", "
            payload = {
                "id": str(message.id),
                "role": message.role.value,
                "status": message.status.value,
                "content": message.content,
                "language": message.language,
                "sequence_no": message.sequence_no,
                "created_at": message.created_at.isoformat(),
                "citations": [
                    {
                        "document_id": str(citation.document_id),
                        "document_title": citation.document_title,
                        "page": citation.page,
                        "snippet": citation.snippet,
                    }
                    for citation in citations
                ],
            }
            yield json.dumps(payload, ensure_ascii=False)
        yield "]}"

    async def stream_markdown(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, conversation_id: UUID
    ) -> AsyncIterator[str]:
        bundle = await self._load(uow, ctx, conversation_id, export_format=ExportFormat.MARKDOWN)
        conversation = bundle.conversation

        yield f"# {conversation.title}\n\n"
        yield f"- Status: {conversation.status.value}\n"
        language = conversation.detected_language or conversation.preferred_language.value
        yield f"- Language: {language}\n"
        yield f"- Created: {conversation.created_at.isoformat()}\n\n"
        yield "---\n\n"
        for message, citations in bundle.turns:
            label = message.role.value.capitalize()
            yield f"### {label} (#{message.sequence_no})\n\n"
            yield f"{message.content}\n\n"
            if citations:
                yield "**Sources:**\n\n"
                for citation in citations:
                    page_suffix = f", p.{citation.page}" if citation.page is not None else ""
                    yield f"- {citation.document_title}{page_suffix}\n"
                yield "\n"


__all__ = ["ExportService"]
