"""Organization membership endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from contextforge.api.dependencies.identity import get_request_context, get_uow
from contextforge.api.dependencies.pagination import get_pagination
from contextforge.api.schemas.common import PaginationMeta, PaginationResponse
from contextforge.api.schemas.memberships import MembershipCreateRequest, MembershipResponse
from contextforge.application.context.request_context import RequestContext
from contextforge.application.pagination import PaginationParams
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.modules.identity_access.application.services.membership_service import (
    MembershipService,
)
from contextforge.modules.identity_access.domain.enums import MembershipStatus

router = APIRouter(prefix="/memberships", tags=["memberships"])

_service = MembershipService()


@router.post("", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    payload: MembershipCreateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> MembershipResponse:
    """Add an existing user as a member of the caller's organization."""
    membership = await _service.add_member(uow, ctx, user_id=payload.user_id)
    return MembershipResponse.model_validate(membership)


@router.get("", response_model=PaginationResponse[MembershipResponse])
async def list_memberships(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    status_filter: Annotated[MembershipStatus | None, Query(alias="status")] = None,
    query: Annotated[str | None, Query()] = None,
) -> PaginationResponse[MembershipResponse]:
    page = await _service.list(uow, ctx, pagination, status=status_filter, query=query)
    return PaginationResponse(
        items=[MembershipResponse.model_validate(item) for item in page.items],
        pagination=PaginationMeta(limit=page.limit, offset=page.offset, total=page.total),
    )


@router.get("/{membership_id}", response_model=MembershipResponse)
async def get_membership(
    membership_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> MembershipResponse:
    membership = await _service.get(uow, ctx, membership_id)
    return MembershipResponse.model_validate(membership)


@router.post("/{membership_id}/suspend", response_model=MembershipResponse)
async def suspend_membership(
    membership_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> MembershipResponse:
    membership = await _service.suspend(uow, ctx, membership_id)
    return MembershipResponse.model_validate(membership)


@router.delete("/{membership_id}", response_model=MembershipResponse)
async def remove_membership(
    membership_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> MembershipResponse:
    membership = await _service.remove(uow, ctx, membership_id)
    return MembershipResponse.model_validate(membership)
