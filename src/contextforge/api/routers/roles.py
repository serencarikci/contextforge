"""Role and role assignment endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from contextforge.api.dependencies.identity import get_request_context, get_uow
from contextforge.api.dependencies.pagination import get_pagination
from contextforge.api.schemas.common import PaginationMeta, PaginationResponse
from contextforge.api.schemas.roles import (
    RoleAssignmentCreateRequest,
    RoleAssignmentResponse,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
)
from contextforge.application.context.request_context import RequestContext
from contextforge.application.pagination import PaginationParams
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.modules.identity_access.application.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["roles"])

_service = RoleService()


@router.get("", response_model=list[RoleResponse])
async def list_roles(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> list[RoleResponse]:
    roles = await _service.list_roles(uow, ctx)
    return [RoleResponse.model_validate(role) for role in roles]


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: RoleCreateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> RoleResponse:
    role = await _service.create_org_role(
        uow, ctx, code=payload.code, name=payload.name, description=payload.description
    )
    return RoleResponse.model_validate(role)


@router.patch("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    payload: RoleUpdateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> RoleResponse:
    role = await _service.update_org_role(
        uow, ctx, role_id, name=payload.name, description=payload.description
    )
    return RoleResponse.model_validate(role)


@router.get("/assignments", response_model=PaginationResponse[RoleAssignmentResponse])
async def list_role_assignments(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
) -> PaginationResponse[RoleAssignmentResponse]:
    page = await _service.list_assignments(uow, ctx, pagination)
    return PaginationResponse(
        items=[RoleAssignmentResponse.model_validate(item) for item in page.items],
        pagination=PaginationMeta(limit=page.limit, offset=page.offset, total=page.total),
    )


@router.post(
    "/assignments", response_model=RoleAssignmentResponse, status_code=status.HTTP_201_CREATED
)
async def assign_role(
    payload: RoleAssignmentCreateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> RoleAssignmentResponse:
    assignment = await _service.assign_role(
        uow,
        ctx,
        membership_id=payload.membership_id,
        role_id=payload.role_id,
        project_id=payload.project_id,
        knowledge_space_id=payload.knowledge_space_id,
    )
    return RoleAssignmentResponse.model_validate(assignment)


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_role(
    assignment_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> None:
    await _service.revoke_role(uow, ctx, assignment_id)
