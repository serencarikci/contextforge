"""Application service orchestrating chat message send/stream flows.

Architecture boundary: this is the *only* chat service that touches
retrieval/LLM concerns, and it does so exclusively through
``RagQueryService`` -- never directly against Qdrant or an LLM provider.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import ResourceNotFoundError
from contextforge.modules.chat.application.ports.cancellation import StreamCancellationPort
from contextforge.modules.chat.application.services.access import ensure_conversation_access
from contextforge.modules.chat.application.services.language_service import LanguageService
from contextforge.modules.chat.application.services.memory_service import MemoryService
from contextforge.modules.chat.application.services.streaming import iterate_with_heartbeat
from contextforge.modules.chat.domain.entities.analytics import ChatAnalyticsEvent
from contextforge.modules.chat.domain.entities.conversation import Conversation
from contextforge.modules.chat.domain.entities.message import ChatMessage, MessageCitation
from contextforge.modules.chat.domain.enums import AnalyticsEventType, MessageRole, MessageStatus
from contextforge.modules.chat.domain.exceptions import NoAccessibleKnowledgeSpacesError
from contextforge.modules.rag.application.services.context_builder import (
    build_citations,
    select_context_chunks,
)
from contextforge.modules.rag.application.services.rag_query_service import RagQueryService
from contextforge.modules.rag.domain.types import Citation, RagAnswer
from contextforge.shared.config.settings import ChatSettings, RagSettings
from contextforge.shared.logging.setup import get_logger
from contextforge.shared.utilities.tokens import estimate_tokens

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ChatAnswer:
    """Result of a synchronous (non-streaming) chat exchange."""

    user_message: ChatMessage
    assistant_message: ChatMessage
    citations: list[MessageCitation]


def _citation_entities(
    citations: list[Citation], *, message_id: UUID, organization_id: UUID
) -> list[MessageCitation]:
    return [
        MessageCitation(
            message_id=message_id,
            organization_id=organization_id,
            document_id=citation.document_id,
            document_title=citation.document_title,
            chunk_id=citation.chunk_id,
            knowledge_space_id=citation.knowledge_space_id,
            snippet=citation.snippet or "",
            rank=rank,
            page=citation.page,
            chunk_index=citation.chunk_index,
        )
        for rank, citation in enumerate(citations, start=1)
    ]


class ChatService:
    """Sends and streams chat messages, grounded via ``RagQueryService``."""

    def __init__(
        self,
        *,
        rag_query_service: RagQueryService,
        memory_service: MemoryService,
        language_service: LanguageService,
        cancellation: StreamCancellationPort,
        chat_settings: ChatSettings,
        rag_settings: RagSettings,
    ) -> None:
        self._rag = rag_query_service
        self._memory = memory_service
        self._language = language_service
        self._cancellation = cancellation
        self._chat_settings = chat_settings
        self._rag_settings = rag_settings

    def _validate_content(self, content: str) -> str:
        cleaned = content.strip()
        if not cleaned:
            msg = "Message content is required."
            raise ValueError(msg)
        if len(cleaned) > self._chat_settings.max_message_length:
            msg = (
                "Message content exceeds the maximum length of "
                f"{self._chat_settings.max_message_length} characters."
            )
            raise ValueError(msg)
        return cleaned

    async def _load_open_conversation(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, conversation_id: UUID
    ) -> Conversation:
        conversation = await uow.conversations.get(ctx.organization_id, conversation_id)
        if conversation is None:
            raise ResourceNotFoundError("Conversation not found.")
        await ensure_conversation_access(uow, ctx, conversation)
        conversation.ensure_open_for_messages()
        return conversation

    async def _resolve_knowledge_space_ids(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        conversation_id: UUID,
    ) -> list[UUID] | None:
        """Re-validate a conversation's linked knowledge spaces on every message.

        Returns ``None`` when the conversation has no explicit links (letting
        ``RagQueryService`` fall back to the caller's full accessible set), or
        the accessible subset of explicitly linked spaces. Raises if the
        conversation has links but none remain accessible -- silently falling
        back to "everything the caller can see" would defeat the purpose of
        scoping a conversation to specific knowledge spaces.
        """
        linked = await uow.conversations.list_knowledge_space_ids(
            ctx.organization_id, conversation_id
        )
        if not linked:
            return None
        accessible = [ks_id for ks_id in linked if ctx.can_access_knowledge_space(ks_id)]
        if not accessible:
            raise NoAccessibleKnowledgeSpacesError(
                "None of this conversation's knowledge spaces are currently accessible."
            )
        return accessible

    async def send_message(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        conversation_id: UUID,
        *,
        content: str,
        idempotency_key: str | None = None,
    ) -> ChatAnswer:
        content = self._validate_content(content)

        async with uow:
            ctx.require_permission("chat:use")
            if idempotency_key:
                existing = await uow.chat_messages.get_by_idempotency_key(
                    ctx.organization_id, idempotency_key
                )
                if existing is not None:
                    return await self._replay(uow, ctx, existing)

            conversation = await self._load_open_conversation(uow, ctx, conversation_id)
            language = self._language.resolve(
                preference=conversation.preferred_language, message_text=content
            )
            conversation.record_detected_language(language)

            user_sequence = await uow.chat_messages.next_sequence_no(
                ctx.organization_id, conversation_id
            )
            user_message = ChatMessage(
                conversation_id=conversation_id,
                organization_id=ctx.organization_id,
                role=MessageRole.USER,
                content=content,
                sequence_no=user_sequence,
                language=language,
                idempotency_key=idempotency_key,
            )
            user_message = await uow.chat_messages.add(user_message)
            await uow.chat_analytics.add(
                ChatAnalyticsEvent(
                    organization_id=ctx.organization_id,
                    event_type=AnalyticsEventType.MESSAGE_SENT,
                    conversation_id=conversation_id,
                    message_id=user_message.id,
                    user_id=ctx.user_id,
                )
            )

            history_context = await self._memory.build_history_context(
                uow, organization_id=ctx.organization_id, conversation_id=conversation_id
            )

            resolution_error: Exception | None = None
            ks_ids: list[UUID] | None = None
            try:
                ks_ids = await self._resolve_knowledge_space_ids(uow, ctx, conversation_id)
            except NoAccessibleKnowledgeSpacesError as exc:
                resolution_error = exc

            conversation.touch_activity()
            await uow.conversations.update(conversation)

        assistant_sequence = user_message.sequence_no + 1

        if resolution_error is not None:
            return await self._fail_message(
                uow,
                ctx,
                conversation_id,
                user_message,
                assistant_sequence,
                language,
                resolution_error,
            )

        try:
            answer = await self._rag.query(
                uow,
                ctx,
                question=content,
                knowledge_space_ids=ks_ids,
                language=language,
                history_context=history_context,
            )
        except Exception as exc:
            return await self._fail_message(
                uow, ctx, conversation_id, user_message, assistant_sequence, language, exc
            )

        return await self._complete_message(
            uow, ctx, conversation_id, user_message, assistant_sequence, answer
        )

    async def _replay(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, user_message: ChatMessage
    ) -> ChatAnswer:
        assistant_message = await uow.chat_messages.get_by_sequence(
            ctx.organization_id, user_message.conversation_id, user_message.sequence_no + 1
        )
        citations: list[MessageCitation] = []
        if assistant_message is not None:
            citations = await uow.chat_messages.list_citations(
                ctx.organization_id, assistant_message.id
            )
        else:
            assistant_message = ChatMessage(
                conversation_id=user_message.conversation_id,
                organization_id=ctx.organization_id,
                role=MessageRole.ASSISTANT,
                content="",
                sequence_no=user_message.sequence_no + 1,
                status=MessageStatus.PENDING,
                parent_message_id=user_message.id,
            )
        return ChatAnswer(
            user_message=user_message, assistant_message=assistant_message, citations=citations
        )

    async def _fail_message(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        conversation_id: UUID,
        user_message: ChatMessage,
        sequence_no: int,
        language: str,
        exc: Exception,
    ) -> ChatAnswer:
        error_code = getattr(exc, "code", "CHAT_GENERATION_FAILED")
        async with uow:
            assistant_message = ChatMessage(
                conversation_id=conversation_id,
                organization_id=ctx.organization_id,
                role=MessageRole.ASSISTANT,
                content="",
                sequence_no=sequence_no,
                status=MessageStatus.FAILED,
                language=language,
                parent_message_id=user_message.id,
            )
            assistant_message.mark_failed(error_code=error_code, error_message=str(exc))
            assistant_message = await uow.chat_messages.add(assistant_message)
            await uow.chat_analytics.add(
                ChatAnalyticsEvent(
                    organization_id=ctx.organization_id,
                    event_type=AnalyticsEventType.ANSWER_FAILED,
                    conversation_id=conversation_id,
                    message_id=assistant_message.id,
                    user_id=ctx.user_id,
                    payload={"error_code": error_code},
                )
            )
        logger.warning(
            "chat_answer_failed",
            extra={"conversation_id": str(conversation_id), "error_code": error_code},
        )
        return ChatAnswer(
            user_message=user_message, assistant_message=assistant_message, citations=[]
        )

    async def _complete_message(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        conversation_id: UUID,
        user_message: ChatMessage,
        sequence_no: int,
        answer: RagAnswer,
    ) -> ChatAnswer:
        diagnostics = answer.diagnostics
        async with uow:
            assistant_message = ChatMessage(
                conversation_id=conversation_id,
                organization_id=ctx.organization_id,
                role=MessageRole.ASSISTANT,
                content=answer.answer,
                sequence_no=sequence_no,
                status=MessageStatus.COMPLETED,
                language=answer.language,
                parent_message_id=user_message.id,
                model_name=self._rag.model_name,
                prompt_tokens=diagnostics.prompt_tokens if diagnostics else 0,
                completion_tokens=diagnostics.completion_tokens if diagnostics else 0,
                total_tokens=diagnostics.total_tokens if diagnostics else 0,
                latency_ms=int(diagnostics.total_ms) if diagnostics else 0,
                retrieval_ms=int(diagnostics.retrieval_ms) if diagnostics else 0,
            )
            assistant_message = await uow.chat_messages.add(assistant_message)

            citation_entities = _citation_entities(
                answer.citations,
                message_id=assistant_message.id,
                organization_id=ctx.organization_id,
            )
            if citation_entities:
                citation_entities = await uow.chat_messages.add_citations(citation_entities)

            await uow.chat_analytics.add(
                ChatAnalyticsEvent(
                    organization_id=ctx.organization_id,
                    event_type=AnalyticsEventType.ANSWER_GENERATED,
                    conversation_id=conversation_id,
                    message_id=assistant_message.id,
                    user_id=ctx.user_id,
                    payload={"total_tokens": assistant_message.total_tokens},
                )
            )
            await self._memory.maybe_update_summary(
                uow, organization_id=ctx.organization_id, conversation_id=conversation_id
            )
        return ChatAnswer(
            user_message=user_message,
            assistant_message=assistant_message,
            citations=citation_entities,
        )

    async def stream_send_message(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        conversation_id: UUID,
        *,
        content: str,
        idempotency_key: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        content = self._validate_content(content)

        async with uow:
            ctx.require_permission("chat:use")
            existing: ChatMessage | None = None
            if idempotency_key:
                existing = await uow.chat_messages.get_by_idempotency_key(
                    ctx.organization_id, idempotency_key
                )
            if existing is not None:
                replay = await self._replay(uow, ctx, existing)
                yield {
                    "event": "stream.started",
                    "data": {
                        "conversation_id": str(conversation_id),
                        "user_message_id": str(replay.user_message.id),
                        "message_id": str(replay.assistant_message.id),
                    },
                }
                yield {
                    "event": "generation.completed",
                    "data": {
                        "message_id": str(replay.assistant_message.id),
                        "content": replay.assistant_message.content,
                        "replayed": True,
                    },
                }
                return

            conversation = await self._load_open_conversation(uow, ctx, conversation_id)
            language = self._language.resolve(
                preference=conversation.preferred_language, message_text=content
            )
            conversation.record_detected_language(language)

            user_sequence = await uow.chat_messages.next_sequence_no(
                ctx.organization_id, conversation_id
            )
            user_message = ChatMessage(
                conversation_id=conversation_id,
                organization_id=ctx.organization_id,
                role=MessageRole.USER,
                content=content,
                sequence_no=user_sequence,
                language=language,
                idempotency_key=idempotency_key,
            )
            user_message = await uow.chat_messages.add(user_message)
            await uow.chat_analytics.add(
                ChatAnalyticsEvent(
                    organization_id=ctx.organization_id,
                    event_type=AnalyticsEventType.MESSAGE_SENT,
                    conversation_id=conversation_id,
                    message_id=user_message.id,
                    user_id=ctx.user_id,
                )
            )

            history_context = await self._memory.build_history_context(
                uow, organization_id=ctx.organization_id, conversation_id=conversation_id
            )

            resolution_error: Exception | None = None
            ks_ids: list[UUID] | None = None
            try:
                ks_ids = await self._resolve_knowledge_space_ids(uow, ctx, conversation_id)
            except NoAccessibleKnowledgeSpacesError as exc:
                resolution_error = exc

            assistant_sequence = await uow.chat_messages.next_sequence_no(
                ctx.organization_id, conversation_id
            )
            assistant_message = ChatMessage(
                conversation_id=conversation_id,
                organization_id=ctx.organization_id,
                role=MessageRole.ASSISTANT,
                content="",
                sequence_no=assistant_sequence,
                status=MessageStatus.PENDING,
                language=language,
                parent_message_id=user_message.id,
            )
            assistant_message = await uow.chat_messages.add(assistant_message)

            conversation.touch_activity()
            await uow.conversations.update(conversation)

        message_id = assistant_message.id
        self._cancellation.begin(message_id)
        yield {
            "event": "stream.started",
            "data": {
                "conversation_id": str(conversation_id),
                "user_message_id": str(user_message.id),
                "message_id": str(message_id),
            },
        }

        try:
            if resolution_error is not None:
                raise resolution_error

            yield {"event": "retrieval.started", "data": {}}
            chunks, diagnostics = await self._rag.search(
                uow, ctx, question=content, knowledge_space_ids=ks_ids, language=language
            )
            yield {
                "event": "retrieval.completed",
                "data": {
                    "retrieval_ms": diagnostics.retrieval_ms,
                    "retrieved_chunk_count": diagnostics.retrieved_chunk_count,
                },
            }

            context_chunks = select_context_chunks(
                chunks,
                max_tokens=self._rag_settings.max_context_tokens,
                max_chunks=self._rag_settings.max_chunks_in_context,
            )
            citations = build_citations(context_chunks)
            for rank, citation in enumerate(citations, start=1):
                yield {
                    "event": "citation",
                    "data": {
                        "rank": rank,
                        "document_id": str(citation.document_id),
                        "document_title": citation.document_title,
                        "chunk_id": str(citation.chunk_id),
                        "knowledge_space_id": str(citation.knowledge_space_id),
                        "page": citation.page,
                        "chunk_index": citation.chunk_index,
                        "snippet": citation.snippet,
                    },
                }

            yield {"event": "generation.started", "data": {}}
            assembled: list[str] = []
            cancelled = False
            source = self._rag.stream_query(
                uow,
                ctx,
                question=content,
                knowledge_space_ids=ks_ids,
                language=language,
                history_context=history_context,
            )
            async for kind, payload in iterate_with_heartbeat(
                source, interval=self._chat_settings.stream_heartbeat_seconds
            ):
                if kind == "heartbeat":
                    yield {"event": "heartbeat", "data": {}}
                    continue
                if kind == "error":
                    raise RuntimeError(payload)
                if self._cancellation.is_cancelled(message_id):
                    cancelled = True
                    break
                assembled.append(payload)
                yield {"event": "token.delta", "data": {"delta": payload}}

            full_content = "".join(assembled)

            if cancelled:
                async with uow:
                    stored = await uow.chat_messages.get(ctx.organization_id, message_id)
                    if stored is not None:
                        stored.content = full_content
                        stored.mark_cancelled()
                        await uow.chat_messages.update(stored)
                    await uow.chat_analytics.add(
                        ChatAnalyticsEvent(
                            organization_id=ctx.organization_id,
                            event_type=AnalyticsEventType.STREAM_CANCELLED,
                            conversation_id=conversation_id,
                            message_id=message_id,
                            user_id=ctx.user_id,
                        )
                    )
                yield {"event": "stream.cancelled", "data": {"message_id": str(message_id)}}
                return

            completion_tokens = estimate_tokens(full_content)
            async with uow:
                stored = await uow.chat_messages.get(ctx.organization_id, message_id)
                assert stored is not None
                stored.mark_completed(
                    content=full_content,
                    model_name=self._rag.model_name,
                    prompt_tokens=0,
                    completion_tokens=completion_tokens,
                    total_tokens=completion_tokens,
                    latency_ms=0,
                    retrieval_ms=int(diagnostics.retrieval_ms),
                    language=language,
                )
                stored = await uow.chat_messages.update(stored)

                citation_entities = _citation_entities(
                    citations, message_id=message_id, organization_id=ctx.organization_id
                )
                if citation_entities:
                    await uow.chat_messages.add_citations(citation_entities)

                await uow.chat_analytics.add(
                    ChatAnalyticsEvent(
                        organization_id=ctx.organization_id,
                        event_type=AnalyticsEventType.ANSWER_GENERATED,
                        conversation_id=conversation_id,
                        message_id=message_id,
                        user_id=ctx.user_id,
                        payload={"total_tokens": completion_tokens},
                    )
                )
                await self._memory.maybe_update_summary(
                    uow, organization_id=ctx.organization_id, conversation_id=conversation_id
                )
            yield {
                "event": "generation.completed",
                "data": {"message_id": str(message_id), "total_tokens": completion_tokens},
            }
        except Exception as exc:
            error_code = getattr(exc, "code", "CHAT_GENERATION_FAILED")
            async with uow:
                stored = await uow.chat_messages.get(ctx.organization_id, message_id)
                if stored is not None:
                    stored.mark_failed(error_code=error_code, error_message=str(exc))
                    await uow.chat_messages.update(stored)
                await uow.chat_analytics.add(
                    ChatAnalyticsEvent(
                        organization_id=ctx.organization_id,
                        event_type=AnalyticsEventType.ANSWER_FAILED,
                        conversation_id=conversation_id,
                        message_id=message_id,
                        user_id=ctx.user_id,
                        payload={"error_code": error_code},
                    )
                )
            logger.warning(
                "chat_stream_failed",
                extra={"conversation_id": str(conversation_id), "error_code": error_code},
            )
            yield {
                "event": "stream.error",
                "data": {"message": "The assistant failed to generate a response."},
            }
        finally:
            self._cancellation.end(message_id)

    async def cancel_message(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        conversation_id: UUID,
        message_id: UUID,
    ) -> ChatMessage:
        async with uow:
            ctx.require_permission("chat:use")
            conversation = await uow.conversations.get(ctx.organization_id, conversation_id)
            if conversation is None:
                raise ResourceNotFoundError("Conversation not found.")
            await ensure_conversation_access(uow, ctx, conversation)

            message = await uow.chat_messages.get(ctx.organization_id, message_id)
            if message is None or message.conversation_id != conversation_id:
                raise ResourceNotFoundError("Message not found.")

            self._cancellation.cancel(message_id)
            if message.status in {MessageStatus.PENDING, MessageStatus.STREAMING}:
                message.mark_cancelled()
                message = await uow.chat_messages.update(message)
                await uow.chat_analytics.add(
                    ChatAnalyticsEvent(
                        organization_id=ctx.organization_id,
                        event_type=AnalyticsEventType.STREAM_CANCELLED,
                        conversation_id=conversation_id,
                        message_id=message_id,
                        user_id=ctx.user_id,
                    )
                )
            return message


__all__ = ["ChatAnswer", "ChatService"]
