"""Application service for conversation lifecycle use cases."""

from __future__ import annotations

from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.pagination import Page, PaginationParams
from contextforge.application.services.command_support import (
    build_audit_event,
    ensure_organization_writable,
)
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import (
    DuplicateResourceError,
    ResourceNotFoundError,
)
from contextforge.modules.chat.application.services.access import (
    ensure_conversation_access,
    ensure_owner_or_manage,
)
from contextforge.modules.chat.domain.entities.analytics import ChatAnalyticsEvent
from contextforge.modules.chat.domain.entities.conversation import (
    Conversation,
    ConversationKnowledgeSpaceLink,
    ConversationParticipant,
)
from contextforge.modules.chat.domain.enums import (
    AnalyticsEventType,
    ChatLanguagePreference,
    ConversationParticipantRole,
    ConversationStatus,
)
from contextforge.shared.config.settings import ChatSettings


class ConversationService:
    """Use cases for creating, reading, and managing conversations."""

    def __init__(self, settings: ChatSettings) -> None:
        self._settings = settings

    async def create(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        *,
        title: str | None = None,
        knowledge_space_ids: list[UUID] | None = None,
        preferred_language: ChatLanguagePreference | None = None,
    ) -> Conversation:
        async with uow:
            ctx.require_permission("chat:use")

            organization = await uow.organizations.get_by_id(ctx.organization_id)
            if organization is None:  # pragma: no cover
                raise ResourceNotFoundError("Organization not found.")
            ensure_organization_writable(organization)

            resolved_ks_ids = list(dict.fromkeys(knowledge_space_ids or []))
            for ks_id in resolved_ks_ids:
                ctx.require_knowledge_space_access(ks_id)

            conversation = Conversation(
                organization_id=ctx.organization_id,
                owner_user_id=ctx.user_id,
                title=title or "New conversation",
                preferred_language=preferred_language or ChatLanguagePreference.AUTO,
            )
            conversation = await uow.conversations.add(conversation)

            await uow.conversations.add_participant(
                ConversationParticipant(
                    conversation_id=conversation.id,
                    organization_id=ctx.organization_id,
                    user_id=ctx.user_id,
                    role=ConversationParticipantRole.OWNER,
                )
            )
            for ks_id in resolved_ks_ids:
                await uow.conversations.add_knowledge_space_link(
                    ConversationKnowledgeSpaceLink(
                        conversation_id=conversation.id,
                        knowledge_space_id=ks_id,
                        organization_id=ctx.organization_id,
                    )
                )

            await uow.chat_analytics.add(
                ChatAnalyticsEvent(
                    organization_id=ctx.organization_id,
                    event_type=AnalyticsEventType.CONVERSATION_CREATED,
                    conversation_id=conversation.id,
                    user_id=ctx.user_id,
                )
            )
            await uow.audit.add(
                build_audit_event(
                    ctx,
                    action="chat.conversation.created",
                    resource_type="conversation",
                    resource_id=conversation.id,
                )
            )
            return conversation

    async def get(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, conversation_id: UUID
    ) -> Conversation:
        async with uow:
            ctx.require_permission("chat:use")
            conversation = await uow.conversations.get(ctx.organization_id, conversation_id)
            if conversation is None:
                raise ResourceNotFoundError("Conversation not found.")
            await ensure_conversation_access(uow, ctx, conversation)
            return conversation

    async def list_conversations(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        pagination: PaginationParams,
        *,
        status: ConversationStatus | None = None,
        pinned: bool | None = None,
        query: str | None = None,
    ) -> Page[Conversation]:
        async with uow:
            ctx.require_permission("chat:use")
            can_see_all = ctx.is_platform_admin or ctx.has_permission("chat:manage")
            items, total = await uow.conversations.list_conversations(
                ctx.organization_id,
                limit=pagination.limit,
                offset=pagination.offset,
                status=status,
                pinned=pinned,
                visible_to_user_id=None if can_see_all else ctx.user_id,
                query=query,
            )
            return Page(items=items, limit=pagination.limit, offset=pagination.offset, total=total)

    async def update(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        conversation_id: UUID,
        *,
        title: str | None = None,
        pinned: bool | None = None,
        preferred_language: ChatLanguagePreference | None = None,
    ) -> Conversation:
        async with uow:
            ctx.require_permission("chat:use")
            conversation = await uow.conversations.get(ctx.organization_id, conversation_id)
            if conversation is None:
                raise ResourceNotFoundError("Conversation not found.")
            await ensure_conversation_access(uow, ctx, conversation)

            if title is not None:
                conversation.rename(title)
            if pinned is not None:
                conversation.set_pinned(pinned)
            if preferred_language is not None:
                conversation.set_preferred_language(preferred_language)
            conversation = await uow.conversations.update(conversation)

            await uow.audit.add(
                build_audit_event(
                    ctx,
                    action="chat.conversation.updated",
                    resource_type="conversation",
                    resource_id=conversation.id,
                )
            )
            return conversation

    async def archive(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, conversation_id: UUID
    ) -> Conversation:
        async with uow:
            ctx.require_permission("chat:use")
            conversation = await uow.conversations.get(ctx.organization_id, conversation_id)
            if conversation is None:
                raise ResourceNotFoundError("Conversation not found.")
            await ensure_conversation_access(uow, ctx, conversation)

            conversation.archive()
            conversation = await uow.conversations.update(conversation)

            await uow.chat_analytics.add(
                ChatAnalyticsEvent(
                    organization_id=ctx.organization_id,
                    event_type=AnalyticsEventType.CONVERSATION_ARCHIVED,
                    conversation_id=conversation.id,
                    user_id=ctx.user_id,
                )
            )
            await uow.audit.add(
                build_audit_event(
                    ctx,
                    action="chat.conversation.archived",
                    resource_type="conversation",
                    resource_id=conversation.id,
                )
            )
            return conversation

    async def restore(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, conversation_id: UUID
    ) -> Conversation:
        async with uow:
            ctx.require_permission("chat:use")
            conversation = await uow.conversations.get(
                ctx.organization_id, conversation_id, include_deleted=True
            )
            if conversation is None:
                raise ResourceNotFoundError("Conversation not found.")
            await ensure_conversation_access(uow, ctx, conversation)

            conversation.restore()
            conversation = await uow.conversations.update(conversation)

            await uow.audit.add(
                build_audit_event(
                    ctx,
                    action="chat.conversation.restored",
                    resource_type="conversation",
                    resource_id=conversation.id,
                )
            )
            return conversation

    async def delete(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, conversation_id: UUID
    ) -> None:
        async with uow:
            ctx.require_permission("chat:use")
            conversation = await uow.conversations.get(ctx.organization_id, conversation_id)
            if conversation is None:
                raise ResourceNotFoundError("Conversation not found.")
            await ensure_conversation_access(uow, ctx, conversation)

            conversation.soft_delete()
            conversation = await uow.conversations.update(conversation)

            await uow.chat_analytics.add(
                ChatAnalyticsEvent(
                    organization_id=ctx.organization_id,
                    event_type=AnalyticsEventType.CONVERSATION_DELETED,
                    conversation_id=conversation.id,
                    user_id=ctx.user_id,
                )
            )
            await uow.audit.add(
                build_audit_event(
                    ctx,
                    action="chat.conversation.deleted",
                    resource_type="conversation",
                    resource_id=conversation.id,
                )
            )

    async def add_knowledge_space(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        conversation_id: UUID,
        knowledge_space_id: UUID,
    ) -> None:
        async with uow:
            ctx.require_permission("chat:use")
            ctx.require_knowledge_space_access(knowledge_space_id)
            conversation = await uow.conversations.get(ctx.organization_id, conversation_id)
            if conversation is None:
                raise ResourceNotFoundError("Conversation not found.")
            await ensure_conversation_access(uow, ctx, conversation)

            if await uow.conversations.has_knowledge_space_link(
                ctx.organization_id, conversation_id, knowledge_space_id
            ):
                raise DuplicateResourceError(
                    "Knowledge space is already linked to this conversation."
                )
            await uow.conversations.add_knowledge_space_link(
                ConversationKnowledgeSpaceLink(
                    conversation_id=conversation_id,
                    knowledge_space_id=knowledge_space_id,
                    organization_id=ctx.organization_id,
                )
            )

    async def remove_knowledge_space(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        conversation_id: UUID,
        knowledge_space_id: UUID,
    ) -> None:
        async with uow:
            ctx.require_permission("chat:use")
            conversation = await uow.conversations.get(ctx.organization_id, conversation_id)
            if conversation is None:
                raise ResourceNotFoundError("Conversation not found.")
            await ensure_conversation_access(uow, ctx, conversation)

            removed = await uow.conversations.remove_knowledge_space_link(
                ctx.organization_id, conversation_id, knowledge_space_id
            )
            if not removed:
                raise ResourceNotFoundError("Knowledge space is not linked to this conversation.")

    async def list_knowledge_spaces(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, conversation_id: UUID
    ) -> list[UUID]:
        async with uow:
            ctx.require_permission("chat:use")
            conversation = await uow.conversations.get(ctx.organization_id, conversation_id)
            if conversation is None:
                raise ResourceNotFoundError("Conversation not found.")
            await ensure_conversation_access(uow, ctx, conversation)
            return await uow.conversations.list_knowledge_space_ids(
                ctx.organization_id, conversation_id
            )

    async def add_participant(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        conversation_id: UUID,
        *,
        user_id: UUID,
        role: ConversationParticipantRole = ConversationParticipantRole.PARTICIPANT,
    ) -> ConversationParticipant:
        async with uow:
            ctx.require_permission("chat:use")
            conversation = await uow.conversations.get(ctx.organization_id, conversation_id)
            if conversation is None:
                raise ResourceNotFoundError("Conversation not found.")
            ensure_owner_or_manage(ctx, conversation)

            existing = await uow.conversations.list_participants(
                ctx.organization_id, conversation_id
            )
            if len(existing) >= self._settings.max_participants:
                raise DuplicateResourceError(
                    "Conversation has reached its maximum number of participants."
                )
            if any(participant.user_id == user_id for participant in existing):
                raise DuplicateResourceError("User is already a participant.")

            member = await uow.memberships.get_by_org_and_user(ctx.organization_id, user_id)
            if member is None:
                raise ResourceNotFoundError("User is not a member of this organization.")

            participant = ConversationParticipant(
                conversation_id=conversation_id,
                organization_id=ctx.organization_id,
                user_id=user_id,
                role=role,
            )
            return await uow.conversations.add_participant(participant)

    async def remove_participant(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        conversation_id: UUID,
        user_id: UUID,
    ) -> None:
        async with uow:
            ctx.require_permission("chat:use")
            conversation = await uow.conversations.get(ctx.organization_id, conversation_id)
            if conversation is None:
                raise ResourceNotFoundError("Conversation not found.")
            if conversation.owner_user_id == user_id:
                raise DuplicateResourceError("The conversation owner cannot be removed.")
            ensure_owner_or_manage(ctx, conversation)

            removed = await uow.conversations.remove_participant(
                ctx.organization_id, conversation_id, user_id
            )
            if not removed:
                raise ResourceNotFoundError("Participant not found.")

    async def list_participants(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, conversation_id: UUID
    ) -> list[ConversationParticipant]:
        async with uow:
            ctx.require_permission("chat:use")
            conversation = await uow.conversations.get(ctx.organization_id, conversation_id)
            if conversation is None:
                raise ResourceNotFoundError("Conversation not found.")
            await ensure_conversation_access(uow, ctx, conversation)
            return await uow.conversations.list_participants(ctx.organization_id, conversation_id)


__all__ = ["ConversationService"]
