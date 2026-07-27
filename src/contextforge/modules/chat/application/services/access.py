from __future__ import annotations

from contextforge.application.context.request_context import RequestContext
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import ResourceNotFoundError
from contextforge.modules.chat.domain.entities.conversation import Conversation


async def ensure_conversation_access(
    uow: SqlAlchemyUnitOfWork,
    ctx: RequestContext,
    conversation: Conversation,
) -> None:
    if ctx.is_platform_admin or ctx.has_permission("chat:manage"):
        return
    if conversation.owner_user_id == ctx.user_id:
        return
    is_participant = await uow.conversations.is_participant(
        ctx.organization_id, conversation.id, ctx.user_id
    )
    if not is_participant:
        raise ResourceNotFoundError("Conversation not found.")


def ensure_owner_or_manage(ctx: RequestContext, conversation: Conversation) -> None:
    if ctx.is_platform_admin or ctx.has_permission("chat:manage"):
        return
    if conversation.owner_user_id == ctx.user_id:
        return
    raise ResourceNotFoundError("Conversation not found.")


__all__ = ["ensure_conversation_access", "ensure_owner_or_manage"]
