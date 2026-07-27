"""Knowledge-space administration statistics."""

from __future__ import annotations

from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import ResourceNotFoundError
from contextforge.modules.admin.infrastructure.repositories.admin_stats import KnowledgeSpaceStats


class KnowledgeSpaceAdminService:
    async def get_stats(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, knowledge_space_id: UUID
    ) -> KnowledgeSpaceStats:
        async with uow:
            ctx.require_permission("admin:knowledge_spaces")
            ks = await uow.knowledge_spaces.get(ctx.organization_id, knowledge_space_id)
            if ks is None:
                raise ResourceNotFoundError("Knowledge space not found.")
            return await uow.admin_stats.knowledge_space_stats(
                ctx.organization_id, knowledge_space_id
            )
