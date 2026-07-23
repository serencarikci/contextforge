"""Application service for querying audit events."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.pagination import Page, PaginationParams
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.modules.audit.domain.entities.audit_event import AuditEvent


class AuditQueryService:
    """Read-only use cases for the append-only audit trail."""

    async def list(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        pagination: PaginationParams,
        *,
        action: str | None = None,
        resource_type: str | None = None,
        actor_user_id: UUID | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> Page[AuditEvent]:
        async with uow:
            ctx.require_permission("audit:read")
            events, total = await uow.audit.list(
                ctx.organization_id,
                limit=pagination.limit,
                offset=pagination.offset,
                action=action,
                resource_type=resource_type,
                actor_user_id=actor_user_id,
                occurred_from=occurred_from,
                occurred_to=occurred_to,
            )
            return Page(items=events, limit=pagination.limit, offset=pagination.offset, total=total)


__all__ = ["AuditQueryService"]
