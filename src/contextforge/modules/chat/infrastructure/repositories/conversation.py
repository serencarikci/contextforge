from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.chat.domain.entities.conversation import (
    Conversation,
    ConversationKnowledgeSpaceLink,
    ConversationParticipant,
)
from contextforge.modules.chat.domain.entities.memory import ConversationMemory
from contextforge.modules.chat.domain.enums import (
    ChatLanguagePreference,
    ConversationParticipantRole,
    ConversationStatus,
)
from contextforge.modules.chat.infrastructure.models.conversation import (
    ConversationKnowledgeSpaceModel,
    ConversationModel,
    ConversationParticipantModel,
)
from contextforge.modules.chat.infrastructure.models.memory import ConversationMemoryModel
from contextforge.modules.chat.infrastructure.models.message import ChatMessageModel


class SqlAlchemyConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entity: Conversation) -> Conversation:
        model = ConversationModel(
            id=entity.id,
            organization_id=entity.organization_id,
            owner_user_id=entity.owner_user_id,
            title=entity.title,
            status=entity.status.value,
            preferred_language=entity.preferred_language.value,
            detected_language=entity.detected_language,
            pinned=entity.pinned,
            last_activity_at=entity.last_activity_at,
            summary_text=entity.summary_text,
            deleted_at=entity.deleted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def get(
        self,
        organization_id: UUID,
        conversation_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Conversation | None:
        conditions = [
            ConversationModel.id == conversation_id,
            ConversationModel.organization_id == organization_id,
        ]
        if not include_deleted:
            conditions.append(ConversationModel.status != ConversationStatus.DELETED.value)
        statement = select(ConversationModel).where(and_(*conditions))
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def update(self, entity: Conversation) -> Conversation:
        statement = select(ConversationModel).where(ConversationModel.id == entity.id)
        result = await self._session.execute(statement)
        model = result.scalar_one()

        model.title = entity.title
        model.status = entity.status.value
        model.preferred_language = entity.preferred_language.value
        model.detected_language = entity.detected_language
        model.pinned = entity.pinned
        model.last_activity_at = entity.last_activity_at
        model.summary_text = entity.summary_text
        model.deleted_at = entity.deleted_at
        model.updated_at = entity.updated_at

        await self._session.flush()
        return self._to_entity(model)

    async def list_conversations(
        self,
        organization_id: UUID,
        *,
        limit: int,
        offset: int,
        status: ConversationStatus | None = None,
        pinned: bool | None = None,
        visible_to_user_id: UUID | None = None,
        query: str | None = None,
    ) -> tuple[list[Conversation], int]:
        conditions = [ConversationModel.organization_id == organization_id]
        if status is not None:
            conditions.append(ConversationModel.status == status.value)
        else:
            conditions.append(ConversationModel.status != ConversationStatus.DELETED.value)
        if pinned is not None:
            conditions.append(ConversationModel.pinned == pinned)
        if visible_to_user_id is not None:
            participant_subquery = exists(
                select(ConversationParticipantModel.id).where(
                    ConversationParticipantModel.conversation_id == ConversationModel.id,
                    ConversationParticipantModel.user_id == visible_to_user_id,
                )
            )
            conditions.append(
                or_(
                    ConversationModel.owner_user_id == visible_to_user_id,
                    participant_subquery,
                )
            )
        if query and query.strip():
            conditions.append(ConversationModel.title.ilike(f"%{query.strip()}%"))

        count_statement = (
            select(func.count()).select_from(ConversationModel).where(and_(*conditions))
        )
        total = (await self._session.execute(count_statement)).scalar_one()

        statement = (
            select(ConversationModel)
            .where(and_(*conditions))
            .order_by(
                ConversationModel.pinned.desc(),
                ConversationModel.last_activity_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(statement)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models], total

    async def search(
        self,
        organization_id: UUID,
        *,
        query: str,
        limit: int,
        offset: int,
        visible_to_user_id: UUID | None = None,
    ) -> tuple[list[Conversation], int]:
        pattern = f"%{query.strip()}%"
        message_match = exists(
            select(ChatMessageModel.id).where(
                ChatMessageModel.conversation_id == ConversationModel.id,
                ChatMessageModel.content.ilike(pattern),
            )
        )
        conditions = [
            ConversationModel.organization_id == organization_id,
            ConversationModel.status != ConversationStatus.DELETED.value,
            or_(ConversationModel.title.ilike(pattern), message_match),
        ]
        if visible_to_user_id is not None:
            participant_subquery = exists(
                select(ConversationParticipantModel.id).where(
                    ConversationParticipantModel.conversation_id == ConversationModel.id,
                    ConversationParticipantModel.user_id == visible_to_user_id,
                )
            )
            conditions.append(
                or_(
                    ConversationModel.owner_user_id == visible_to_user_id,
                    participant_subquery,
                )
            )

        count_statement = (
            select(func.count()).select_from(ConversationModel).where(and_(*conditions))
        )
        total = (await self._session.execute(count_statement)).scalar_one()

        statement = (
            select(ConversationModel)
            .where(and_(*conditions))
            .order_by(ConversationModel.last_activity_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(statement)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models], total

    async def add_participant(
        self, participant: ConversationParticipant
    ) -> ConversationParticipant:
        model = ConversationParticipantModel(
            id=participant.id,
            conversation_id=participant.conversation_id,
            organization_id=participant.organization_id,
            user_id=participant.user_id,
            role=participant.role.value,
        )
        self._session.add(model)
        await self._session.flush()
        return self._participant_to_entity(model)

    async def list_participants(
        self, organization_id: UUID, conversation_id: UUID
    ) -> list[ConversationParticipant]:
        statement = select(ConversationParticipantModel).where(
            ConversationParticipantModel.organization_id == organization_id,
            ConversationParticipantModel.conversation_id == conversation_id,
        )
        result = await self._session.execute(statement)
        return [self._participant_to_entity(model) for model in result.scalars().all()]

    async def is_participant(
        self, organization_id: UUID, conversation_id: UUID, user_id: UUID
    ) -> bool:
        statement = (
            select(func.count())
            .select_from(ConversationParticipantModel)
            .where(
                ConversationParticipantModel.organization_id == organization_id,
                ConversationParticipantModel.conversation_id == conversation_id,
                ConversationParticipantModel.user_id == user_id,
            )
        )
        result = await self._session.execute(statement)
        return result.scalar_one() > 0

    async def remove_participant(
        self, organization_id: UUID, conversation_id: UUID, user_id: UUID
    ) -> bool:
        statement = select(ConversationParticipantModel).where(
            ConversationParticipantModel.organization_id == organization_id,
            ConversationParticipantModel.conversation_id == conversation_id,
            ConversationParticipantModel.user_id == user_id,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    async def add_knowledge_space_link(
        self, link: ConversationKnowledgeSpaceLink
    ) -> ConversationKnowledgeSpaceLink:
        model = ConversationKnowledgeSpaceModel(
            conversation_id=link.conversation_id,
            knowledge_space_id=link.knowledge_space_id,
            organization_id=link.organization_id,
        )
        self._session.add(model)
        await self._session.flush()
        return link

    async def remove_knowledge_space_link(
        self, organization_id: UUID, conversation_id: UUID, knowledge_space_id: UUID
    ) -> bool:
        statement = select(ConversationKnowledgeSpaceModel).where(
            ConversationKnowledgeSpaceModel.organization_id == organization_id,
            ConversationKnowledgeSpaceModel.conversation_id == conversation_id,
            ConversationKnowledgeSpaceModel.knowledge_space_id == knowledge_space_id,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    async def list_knowledge_space_ids(
        self, organization_id: UUID, conversation_id: UUID
    ) -> list[UUID]:
        statement = select(ConversationKnowledgeSpaceModel.knowledge_space_id).where(
            ConversationKnowledgeSpaceModel.organization_id == organization_id,
            ConversationKnowledgeSpaceModel.conversation_id == conversation_id,
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def has_knowledge_space_link(
        self, organization_id: UUID, conversation_id: UUID, knowledge_space_id: UUID
    ) -> bool:
        statement = (
            select(func.count())
            .select_from(ConversationKnowledgeSpaceModel)
            .where(
                ConversationKnowledgeSpaceModel.organization_id == organization_id,
                ConversationKnowledgeSpaceModel.conversation_id == conversation_id,
                ConversationKnowledgeSpaceModel.knowledge_space_id == knowledge_space_id,
            )
        )
        result = await self._session.execute(statement)
        return result.scalar_one() > 0

    async def get_memory(
        self, organization_id: UUID, conversation_id: UUID
    ) -> ConversationMemory | None:
        statement = select(ConversationMemoryModel).where(
            ConversationMemoryModel.organization_id == organization_id,
            ConversationMemoryModel.conversation_id == conversation_id,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._memory_to_entity(model)

    async def upsert_memory(self, memory: ConversationMemory) -> ConversationMemory:
        statement = select(ConversationMemoryModel).where(
            ConversationMemoryModel.organization_id == memory.organization_id,
            ConversationMemoryModel.conversation_id == memory.conversation_id,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            model = ConversationMemoryModel(
                id=memory.id,
                conversation_id=memory.conversation_id,
                organization_id=memory.organization_id,
                summary_text=memory.summary_text,
                covered_until_sequence=memory.covered_until_sequence,
                token_estimate=memory.token_estimate,
                created_at=memory.created_at,
                updated_at=memory.updated_at,
            )
            self._session.add(model)
        else:
            model.summary_text = memory.summary_text
            model.covered_until_sequence = memory.covered_until_sequence
            model.token_estimate = memory.token_estimate
            model.updated_at = memory.updated_at
        await self._session.flush()
        return self._memory_to_entity(model)

    @staticmethod
    def _to_entity(model: ConversationModel) -> Conversation:
        return Conversation(
            organization_id=model.organization_id,
            owner_user_id=model.owner_user_id,
            id=model.id,
            title=model.title,
            status=ConversationStatus(model.status),
            preferred_language=ChatLanguagePreference(model.preferred_language),
            detected_language=model.detected_language,
            pinned=model.pinned,
            last_activity_at=model.last_activity_at,
            summary_text=model.summary_text,
            deleted_at=model.deleted_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _participant_to_entity(model: ConversationParticipantModel) -> ConversationParticipant:
        return ConversationParticipant(
            conversation_id=model.conversation_id,
            organization_id=model.organization_id,
            user_id=model.user_id,
            role=ConversationParticipantRole(model.role),
            id=model.id,
        )

    @staticmethod
    def _memory_to_entity(model: ConversationMemoryModel) -> ConversationMemory:
        return ConversationMemory(
            conversation_id=model.conversation_id,
            organization_id=model.organization_id,
            summary_text=model.summary_text,
            covered_until_sequence=model.covered_until_sequence,
            token_estimate=model.token_estimate,
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


__all__ = ["SqlAlchemyConversationRepository"]
