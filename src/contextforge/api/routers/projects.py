"""Project endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from contextforge.api.dependencies.identity import get_request_context, get_uow
from contextforge.api.dependencies.pagination import get_pagination
from contextforge.api.schemas.common import PaginationMeta, PaginationResponse
from contextforge.api.schemas.projects import (
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
)
from contextforge.application.context.request_context import RequestContext
from contextforge.application.pagination import PaginationParams
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.modules.identity_access.domain.enums import ProjectStatus
from contextforge.modules.projects.application.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])

_service = ProjectService()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ProjectResponse:
    project = await _service.create(
        uow,
        ctx,
        name=payload.name,
        key=payload.key,
        customer_id=payload.customer_id,
        description=payload.description,
        default_language=payload.default_language,
    )
    return ProjectResponse.model_validate(project)


@router.get("", response_model=PaginationResponse[ProjectResponse])
async def list_projects(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    status_filter: Annotated[ProjectStatus | None, Query(alias="status")] = None,
    customer_id: Annotated[UUID | None, Query()] = None,
    query: Annotated[str | None, Query()] = None,
) -> PaginationResponse[ProjectResponse]:
    page = await _service.list(
        uow, ctx, pagination, status=status_filter, customer_id=customer_id, query=query
    )
    return PaginationResponse(
        items=[ProjectResponse.model_validate(item) for item in page.items],
        pagination=PaginationMeta(limit=page.limit, offset=page.offset, total=page.total),
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ProjectResponse:
    project = await _service.get(uow, ctx, project_id)
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ProjectResponse:
    project = await _service.update(
        uow,
        ctx,
        project_id,
        name=payload.name,
        description=payload.description,
        default_language=payload.default_language,
        status=payload.status,
    )
    return ProjectResponse.model_validate(project)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    project_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ProjectResponse:
    project = await _service.archive(uow, ctx, project_id)
    return ProjectResponse.model_validate(project)
