"""Ingestion job endpoints for listing, inspecting, and retrying failed jobs."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from contextforge.api.dependencies.identity import get_request_context, get_uow
from contextforge.api.dependencies.pagination import get_pagination
from contextforge.api.dependencies.providers import (
    get_ingestion_job_queue,
    get_ingestion_job_service,
)
from contextforge.api.schemas.common import PaginationMeta, PaginationResponse
from contextforge.api.schemas.ingestion import IngestionJobListResponse, IngestionJobResponse
from contextforge.application.context.request_context import RequestContext
from contextforge.application.pagination import PaginationParams
from contextforge.application.ports.ingestion_job_queue import IngestionJobQueuePort
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.modules.ingestion.application.services.ingestion_job_service import (
    IngestionJobService,
)
from contextforge.modules.ingestion.domain.enums import IngestionJobStatus

router = APIRouter(prefix="/ingestion-jobs", tags=["ingestion-jobs"])


@router.get("", response_model=PaginationResponse[IngestionJobResponse])
async def list_ingestion_jobs(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[IngestionJobService, Depends(get_ingestion_job_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    status_filter: Annotated[IngestionJobStatus | None, Query(alias="status")] = None,
) -> PaginationResponse[IngestionJobResponse]:
    page = await service.list(uow, ctx, pagination, status=status_filter)
    return PaginationResponse(
        items=[IngestionJobResponse.model_validate(item) for item in page.items],
        pagination=PaginationMeta(limit=page.limit, offset=page.offset, total=page.total),
    )


@router.get("/{job_id}", response_model=IngestionJobResponse)
async def get_ingestion_job(
    job_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[IngestionJobService, Depends(get_ingestion_job_service)],
) -> IngestionJobResponse:
    job = await service.get(uow, ctx, job_id)
    return IngestionJobResponse.model_validate(job)


@router.post(
    "/{job_id}/retry",
    response_model=IngestionJobResponse,
    status_code=status.HTTP_200_OK,
)
async def retry_ingestion_job(
    job_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[IngestionJobService, Depends(get_ingestion_job_service)],
    queue: Annotated[IngestionJobQueuePort, Depends(get_ingestion_job_queue)],
) -> IngestionJobResponse:
    job = await service.retry_failed(uow, ctx, queue, job_id)
    return IngestionJobResponse.model_validate(job)


documents_ingestion_router = APIRouter(prefix="/documents", tags=["ingestion-jobs"])


@documents_ingestion_router.get(
    "/{document_id}/ingestion-jobs",
    response_model=IngestionJobListResponse,
)
async def list_document_ingestion_jobs(
    document_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[IngestionJobService, Depends(get_ingestion_job_service)],
) -> IngestionJobListResponse:
    jobs = await service.list_for_document(uow, ctx, document_id)
    return IngestionJobListResponse(
        items=[IngestionJobResponse.model_validate(item) for item in jobs]
    )
