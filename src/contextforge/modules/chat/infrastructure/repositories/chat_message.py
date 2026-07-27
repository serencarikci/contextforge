from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.chat.domain.entities.message import ChatMessage, MessageCitation
from contextforge.modules.chat.domain.enums import MessageRole, MessageStatus
from contextforge.modules.chat.infrastructure.models.message import (
    ChatMessageModel,
    MessageCitationModel,
)


@dataclass(frozen=True, slots=True)
class MessageStats:
    total_messages: int
    assistant_messages: int
    failed_messages: int
    avg_latency_ms: float
    avg_retrieval_ms: float
    total_prompt_tokens: int
    total_completion_tokens: int


class SqlAlchemyChatMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entity: ChatMessage) -> ChatMessage:
        model = ChatMessageModel(
            id=entity.id,
            conversation_id=entity.conversation_id,
            organization_id=entity.organization_id,
            role=entity.role.value,
            status=entity.status.value,
            content=entity.content,
            language=entity.language,
            sequence_no=entity.sequence_no,
            parent_message_id=entity.parent_message_id,
            model_name=entity.model_name,
            prompt_tokens=entity.prompt_tokens,
            completion_tokens=entity.completion_tokens,
            total_tokens=entity.total_tokens,
            latency_ms=entity.latency_ms,
            retrieval_ms=entity.retrieval_ms,
            error_code=entity.error_code,
            error_message=entity.error_message,
            idempotency_key=entity.idempotency_key,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, entity: ChatMessage) -> ChatMessage:
        statement = select(ChatMessageModel).where(ChatMessageModel.id == entity.id)
        result = await self._session.execute(statement)
        model = result.scalar_one()

        model.status = entity.status.value
        model.content = entity.content
        model.language = entity.language
        model.model_name = entity.model_name
        model.prompt_tokens = entity.prompt_tokens
        model.completion_tokens = entity.completion_tokens
        model.total_tokens = entity.total_tokens
        model.latency_ms = entity.latency_ms
        model.retrieval_ms = entity.retrieval_ms
        model.error_code = entity.error_code
        model.error_message = entity.error_message
        model.updated_at = entity.updated_at

        await self._session.flush()
        return self._to_entity(model)

    async def get(self, organization_id: UUID, message_id: UUID) -> ChatMessage | None:
        statement = select(ChatMessageModel).where(
            ChatMessageModel.id == message_id,
            ChatMessageModel.organization_id == organization_id,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def get_by_idempotency_key(
        self, organization_id: UUID, idempotency_key: str
    ) -> ChatMessage | None:
        statement = select(ChatMessageModel).where(
            ChatMessageModel.organization_id == organization_id,
            ChatMessageModel.idempotency_key == idempotency_key,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def get_by_sequence(
        self, organization_id: UUID, conversation_id: UUID, sequence_no: int
    ) -> ChatMessage | None:
        statement = select(ChatMessageModel).where(
            ChatMessageModel.organization_id == organization_id,
            ChatMessageModel.conversation_id == conversation_id,
            ChatMessageModel.sequence_no == sequence_no,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def next_sequence_no(self, organization_id: UUID, conversation_id: UUID) -> int:
        statement = select(func.max(ChatMessageModel.sequence_no)).where(
            ChatMessageModel.organization_id == organization_id,
            ChatMessageModel.conversation_id == conversation_id,
        )
        result = await self._session.execute(statement)
        current_max = result.scalar_one_or_none()
        return 1 if current_max is None else current_max + 1

    async def list_by_conversation(
        self,
        organization_id: UUID,
        conversation_id: UUID,
        *,
        limit: int,
        offset: int,
        ascending: bool = True,
        before_sequence: int | None = None,
    ) -> tuple[list[ChatMessage], int]:
        conditions = [
            ChatMessageModel.organization_id == organization_id,
            ChatMessageModel.conversation_id == conversation_id,
        ]
        if before_sequence is not None:
            conditions.append(ChatMessageModel.sequence_no < before_sequence)

        count_statement = (
            select(func.count()).select_from(ChatMessageModel).where(and_(*conditions))
        )
        total = (await self._session.execute(count_statement)).scalar_one()

        order = (
            ChatMessageModel.sequence_no.asc() if ascending else ChatMessageModel.sequence_no.desc()
        )
        statement = (
            select(ChatMessageModel)
            .where(and_(*conditions))
            .order_by(order)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(statement)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models], total

    async def list_recent_for_context(
        self, organization_id: UUID, conversation_id: UUID, *, limit: int
    ) -> list[ChatMessage]:
        statement = (
            select(ChatMessageModel)
            .where(
                ChatMessageModel.organization_id == organization_id,
                ChatMessageModel.conversation_id == conversation_id,
                ChatMessageModel.status == MessageStatus.COMPLETED.value,
                ChatMessageModel.role.in_([MessageRole.USER.value, MessageRole.ASSISTANT.value]),
            )
            .order_by(ChatMessageModel.sequence_no.desc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        models = list(result.scalars().all())
        models.reverse()
        return [self._to_entity(model) for model in models]

    async def list_after_sequence(
        self, organization_id: UUID, conversation_id: UUID, *, after_sequence: int
    ) -> list[ChatMessage]:
        statement = (
            select(ChatMessageModel)
            .where(
                ChatMessageModel.organization_id == organization_id,
                ChatMessageModel.conversation_id == conversation_id,
                ChatMessageModel.sequence_no > after_sequence,
                ChatMessageModel.status == MessageStatus.COMPLETED.value,
                ChatMessageModel.role.in_([MessageRole.USER.value, MessageRole.ASSISTANT.value]),
            )
            .order_by(ChatMessageModel.sequence_no.asc())
        )
        result = await self._session.execute(statement)
        return [self._to_entity(model) for model in result.scalars().all()]

    async def aggregate_stats(
        self,
        organization_id: UUID,
        *,
        since: datetime | None = None,
        conversation_id: UUID | None = None,
    ) -> MessageStats:
        conditions = [ChatMessageModel.organization_id == organization_id]
        if since is not None:
            conditions.append(ChatMessageModel.created_at >= since)
        if conversation_id is not None:
            conditions.append(ChatMessageModel.conversation_id == conversation_id)

        statement = select(
            func.count(),
            func.count().filter(ChatMessageModel.role == MessageRole.ASSISTANT.value),
            func.count().filter(ChatMessageModel.status == MessageStatus.FAILED.value),
            func.coalesce(
                func.avg(ChatMessageModel.latency_ms).filter(
                    ChatMessageModel.role == MessageRole.ASSISTANT.value
                ),
                0.0,
            ),
            func.coalesce(
                func.avg(ChatMessageModel.retrieval_ms).filter(
                    ChatMessageModel.role == MessageRole.ASSISTANT.value
                ),
                0.0,
            ),
            func.coalesce(func.sum(ChatMessageModel.prompt_tokens), 0),
            func.coalesce(func.sum(ChatMessageModel.completion_tokens), 0),
        ).where(and_(*conditions))
        result = await self._session.execute(statement)
        row = result.one()
        return MessageStats(
            total_messages=row[0],
            assistant_messages=row[1],
            failed_messages=row[2],
            avg_latency_ms=float(row[3]),
            avg_retrieval_ms=float(row[4]),
            total_prompt_tokens=int(row[5]),
            total_completion_tokens=int(row[6]),
        )

    async def add_citations(self, citations: list[MessageCitation]) -> list[MessageCitation]:
        if not citations:
            return []
        models = [
            MessageCitationModel(
                id=citation.id,
                message_id=citation.message_id,
                organization_id=citation.organization_id,
                document_id=citation.document_id,
                document_title=citation.document_title,
                chunk_id=citation.chunk_id,
                knowledge_space_id=citation.knowledge_space_id,
                page=citation.page,
                chunk_index=citation.chunk_index,
                snippet=citation.snippet,
                rank=citation.rank,
            )
            for citation in citations
        ]
        self._session.add_all(models)
        await self._session.flush()
        return citations

    async def list_citations(
        self, organization_id: UUID, message_id: UUID
    ) -> list[MessageCitation]:
        statement = (
            select(MessageCitationModel)
            .where(
                MessageCitationModel.organization_id == organization_id,
                MessageCitationModel.message_id == message_id,
            )
            .order_by(MessageCitationModel.rank.asc())
        )
        result = await self._session.execute(statement)
        return [self._citation_to_entity(model) for model in result.scalars().all()]

    async def list_citations_for_messages(
        self, organization_id: UUID, message_ids: list[UUID]
    ) -> dict[UUID, list[MessageCitation]]:
        if not message_ids:
            return {}
        statement = (
            select(MessageCitationModel)
            .where(
                MessageCitationModel.organization_id == organization_id,
                MessageCitationModel.message_id.in_(message_ids),
            )
            .order_by(MessageCitationModel.message_id.asc(), MessageCitationModel.rank.asc())
        )
        result = await self._session.execute(statement)
        grouped: dict[UUID, list[MessageCitation]] = {}
        for model in result.scalars().all():
            grouped.setdefault(model.message_id, []).append(self._citation_to_entity(model))
        return grouped

    @staticmethod
    def _to_entity(model: ChatMessageModel) -> ChatMessage:
        return ChatMessage(
            conversation_id=model.conversation_id,
            organization_id=model.organization_id,
            role=MessageRole(model.role),
            content=model.content,
            sequence_no=model.sequence_no,
            id=model.id,
            status=MessageStatus(model.status),
            language=model.language,
            parent_message_id=model.parent_message_id,
            model_name=model.model_name,
            prompt_tokens=model.prompt_tokens,
            completion_tokens=model.completion_tokens,
            total_tokens=model.total_tokens,
            latency_ms=model.latency_ms,
            retrieval_ms=model.retrieval_ms,
            error_code=model.error_code,
            error_message=model.error_message,
            idempotency_key=model.idempotency_key,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _citation_to_entity(model: MessageCitationModel) -> MessageCitation:
        return MessageCitation(
            message_id=model.message_id,
            organization_id=model.organization_id,
            document_id=model.document_id,
            document_title=model.document_title,
            chunk_id=model.chunk_id,
            knowledge_space_id=model.knowledge_space_id,
            snippet=model.snippet,
            rank=model.rank,
            id=model.id,
            page=model.page,
            chunk_index=model.chunk_index,
        )


__all__ = ["SqlAlchemyChatMessageRepository"]
