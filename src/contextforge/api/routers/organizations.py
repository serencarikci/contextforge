"""Organization endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from contextforge.api.dependencies.identity import (
    get_active_user_id,
    get_request_context,
    get_uow,
)
from contextforge.api.dependencies.pagination import get_pagination
from contextforge.api.schemas.common import PaginationMeta, PaginationResponse
from contextforge.api.schemas.organizations import (
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
)
from contextforge.application.context.request_context import RequestContext
from contextforge.application.pagination import PaginationParams
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.modules.organizations.application.services.organization_service import (
    OrganizationService,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])

_service = OrganizationService()


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    creator_user_id: Annotated[UUID, Depends(get_active_user_id)],
) -> OrganizationResponse:
    """Create a new organization. The caller becomes its organization admin."""
    organization = await _service.create(
        uow, name=payload.name, slug=payload.slug, creator_user_id=creator_user_id
    )
    return OrganizationResponse.model_validate(organization)


@router.get("", response_model=PaginationResponse[OrganizationResponse])
async def list_organizations(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    user_id: Annotated[UUID, Depends(get_active_user_id)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
) -> PaginationResponse[OrganizationResponse]:
    """List organizations the caller is a member of."""
    page = await _service.list_for_user(uow, user_id=user_id, pagination=pagination)
    return PaginationResponse(
        items=[OrganizationResponse.model_validate(item) for item in page.items],
        pagination=PaginationMeta(limit=page.limit, offset=page.offset, total=page.total),
    )


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> OrganizationResponse:
    organization = await _service.get(uow, ctx, organization_id)
    return OrganizationResponse.model_validate(organization)


@router.patch("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: UUID,
    payload: OrganizationUpdateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> OrganizationResponse:
    organization = await _service.update(uow, ctx, organization_id, name=payload.name)
    return OrganizationResponse.model_validate(organization)


@router.post("/{organization_id}/suspend", response_model=OrganizationResponse)
async def suspend_organization(
    organization_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> OrganizationResponse:
    organization = await _service.suspend(uow, ctx, organization_id)
    return OrganizationResponse.model_validate(organization)


@router.post("/{organization_id}/archive", response_model=OrganizationResponse)
async def archive_organization(
    organization_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> OrganizationResponse:
    organization = await _service.archive(uow, ctx, organization_id)
    return OrganizationResponse.model_validate(organization)
