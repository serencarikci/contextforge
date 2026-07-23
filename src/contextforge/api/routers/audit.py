"""Audit trail query endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from contextforge.api.dependencies.identity import get_request_context, get_uow
from contextforge.api.dependencies.pagination import get_pagination
from contextforge.api.schemas.audit import AuditEventResponse
from contextforge.api.schemas.common import PaginationMeta, PaginationResponse
from contextforge.application.context.request_context import RequestContext
from contextforge.application.pagination import PaginationParams
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.modules.audit.application.services.audit_query_service import (
    AuditQueryService,
)

router = APIRouter(prefix="/audit", tags=["audit"])

_service = AuditQueryService()


@router.get("", response_model=PaginationResponse[AuditEventResponse])
async def list_audit_events(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    action: Annotated[str | None, Query()] = None,
    resource_type: Annotated[str | None, Query()] = None,
    actor_user_id: Annotated[UUID | None, Query()] = None,
    occurred_from: Annotated[datetime | None, Query()] = None,
    occurred_to: Annotated[datetime | None, Query()] = None,
) -> PaginationResponse[AuditEventResponse]:
    page = await _service.list(
        uow,
        ctx,
        pagination,
        action=action,
        resource_type=resource_type,
        actor_user_id=actor_user_id,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
    )
    return PaginationResponse(
        items=[AuditEventResponse.model_validate(item) for item in page.items],
        pagination=PaginationMeta(limit=page.limit, offset=page.offset, total=page.total),
    )
