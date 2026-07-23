"""Knowledge space and knowledge space membership endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from contextforge.api.dependencies.identity import get_request_context, get_uow
from contextforge.api.dependencies.pagination import get_pagination
from contextforge.api.schemas.common import PaginationMeta, PaginationResponse
from contextforge.api.schemas.knowledge_spaces import (
    KnowledgeSpaceCreateRequest,
    KnowledgeSpaceMembershipCreateRequest,
    KnowledgeSpaceMembershipResponse,
    KnowledgeSpaceMembershipUpdateRequest,
    KnowledgeSpaceResponse,
    KnowledgeSpaceUpdateRequest,
)
from contextforge.application.context.request_context import RequestContext
from contextforge.application.pagination import PaginationParams
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.modules.identity_access.domain.enums import KnowledgeSpaceStatus
from contextforge.modules.knowledge_spaces.application.services.knowledge_space_service import (
    KnowledgeSpaceService,
)

router = APIRouter(prefix="/knowledge-spaces", tags=["knowledge-spaces"])

_service = KnowledgeSpaceService()


@router.post("", response_model=KnowledgeSpaceResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_space(
    payload: KnowledgeSpaceCreateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> KnowledgeSpaceResponse:
    knowledge_space = await _service.create(
        uow,
        ctx,
        name=payload.name,
        slug=payload.slug,
        project_id=payload.project_id,
        description=payload.description,
        visibility=payload.visibility,
    )
    return KnowledgeSpaceResponse.model_validate(knowledge_space)


@router.get("", response_model=PaginationResponse[KnowledgeSpaceResponse])
async def list_knowledge_spaces(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    status_filter: Annotated[KnowledgeSpaceStatus | None, Query(alias="status")] = None,
    project_id: Annotated[UUID | None, Query()] = None,
    query: Annotated[str | None, Query()] = None,
) -> PaginationResponse[KnowledgeSpaceResponse]:
    page = await _service.list(
        uow, ctx, pagination, status=status_filter, project_id=project_id, query=query
    )
    return PaginationResponse(
        items=[KnowledgeSpaceResponse.model_validate(item) for item in page.items],
        pagination=PaginationMeta(limit=page.limit, offset=page.offset, total=page.total),
    )


@router.get("/{knowledge_space_id}", response_model=KnowledgeSpaceResponse)
async def get_knowledge_space(
    knowledge_space_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> KnowledgeSpaceResponse:
    knowledge_space = await _service.get(uow, ctx, knowledge_space_id)
    return KnowledgeSpaceResponse.model_validate(knowledge_space)


@router.patch("/{knowledge_space_id}", response_model=KnowledgeSpaceResponse)
async def update_knowledge_space(
    knowledge_space_id: UUID,
    payload: KnowledgeSpaceUpdateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> KnowledgeSpaceResponse:
    knowledge_space = await _service.update(
        uow,
        ctx,
        knowledge_space_id,
        name=payload.name,
        description=payload.description,
        visibility=payload.visibility,
    )
    return KnowledgeSpaceResponse.model_validate(knowledge_space)


@router.post("/{knowledge_space_id}/archive", response_model=KnowledgeSpaceResponse)
async def archive_knowledge_space(
    knowledge_space_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> KnowledgeSpaceResponse:
    knowledge_space = await _service.archive(uow, ctx, knowledge_space_id)
    return KnowledgeSpaceResponse.model_validate(knowledge_space)


@router.post(
    "/{knowledge_space_id}/memberships",
    response_model=KnowledgeSpaceMembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_knowledge_space_membership(
    knowledge_space_id: UUID,
    payload: KnowledgeSpaceMembershipCreateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> KnowledgeSpaceMembershipResponse:
    membership = await _service.add_membership(
        uow,
        ctx,
        knowledge_space_id,
        membership_id=payload.membership_id,
        access_level=payload.access_level,
    )
    return KnowledgeSpaceMembershipResponse.model_validate(membership)


@router.get(
    "/{knowledge_space_id}/memberships",
    response_model=PaginationResponse[KnowledgeSpaceMembershipResponse],
)
async def list_knowledge_space_memberships(
    knowledge_space_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
) -> PaginationResponse[KnowledgeSpaceMembershipResponse]:
    page = await _service.list_memberships(uow, ctx, knowledge_space_id, pagination)
    return PaginationResponse(
        items=[KnowledgeSpaceMembershipResponse.model_validate(item) for item in page.items],
        pagination=PaginationMeta(limit=page.limit, offset=page.offset, total=page.total),
    )


@router.patch(
    "/{knowledge_space_id}/memberships/{ks_membership_id}",
    response_model=KnowledgeSpaceMembershipResponse,
)
async def update_knowledge_space_membership(
    knowledge_space_id: UUID,
    ks_membership_id: UUID,
    payload: KnowledgeSpaceMembershipUpdateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> KnowledgeSpaceMembershipResponse:
    membership = await _service.update_membership(
        uow,
        ctx,
        knowledge_space_id,
        ks_membership_id,
        access_level=payload.access_level,
    )
    return KnowledgeSpaceMembershipResponse.model_validate(membership)


@router.delete(
    "/{knowledge_space_id}/memberships/{ks_membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_knowledge_space_membership(
    knowledge_space_id: UUID,
    ks_membership_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> None:
    await _service.remove_membership(uow, ctx, knowledge_space_id, ks_membership_id)
