"""Application service for searching conversations by title or message content."""

from __future__ import annotations

from contextforge.application.context.request_context import RequestContext
from contextforge.application.pagination import Page, PaginationParams
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import ResourceNotFoundError
from contextforge.modules.chat.domain.entities.conversation import Conversation

_MIN_QUERY_LENGTH = 2


class ConversationSearchService:
    """Full-text-ish search over conversation titles and message content.

    Uses a portable ``ILIKE`` fallback (see the repository implementation);
    the underlying tables also carry generated ``tsvector`` columns for a
    future native full-text search upgrade.
    """

    async def search(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        pagination: PaginationParams,
        *,
        query: str,
    ) -> Page[Conversation]:
        cleaned = query.strip()
        if len(cleaned) < _MIN_QUERY_LENGTH:
            raise ResourceNotFoundError("Search query must be at least 2 characters.")

        async with uow:
            ctx.require_permission("chat:use")
            can_see_all = ctx.is_platform_admin or ctx.has_permission("chat:manage")
            items, total = await uow.conversations.search(
                ctx.organization_id,
                query=cleaned,
                limit=pagination.limit,
                offset=pagination.offset,
                visible_to_user_id=None if can_see_all else ctx.user_id,
            )
            return Page(items=items, limit=pagination.limit, offset=pagination.offset, total=total)


__all__ = ["ConversationSearchService"]
