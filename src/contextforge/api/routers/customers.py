"""Customer endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from contextforge.api.dependencies.identity import get_request_context, get_uow
from contextforge.api.dependencies.pagination import get_pagination
from contextforge.api.schemas.common import PaginationMeta, PaginationResponse
from contextforge.api.schemas.customers import (
    CustomerCreateRequest,
    CustomerResponse,
    CustomerUpdateRequest,
)
from contextforge.application.context.request_context import RequestContext
from contextforge.application.pagination import PaginationParams
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.modules.customers.application.services.customer_service import CustomerService
from contextforge.modules.identity_access.domain.enums import CustomerStatus

router = APIRouter(prefix="/customers", tags=["customers"])

_service = CustomerService()


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> CustomerResponse:
    customer = await _service.create(
        uow, ctx, name=payload.name, code=payload.code, description=payload.description
    )
    return CustomerResponse.model_validate(customer)


@router.get("", response_model=PaginationResponse[CustomerResponse])
async def list_customers(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    status_filter: Annotated[CustomerStatus | None, Query(alias="status")] = None,
    query: Annotated[str | None, Query()] = None,
) -> PaginationResponse[CustomerResponse]:
    page = await _service.list(uow, ctx, pagination, status=status_filter, query=query)
    return PaginationResponse(
        items=[CustomerResponse.model_validate(item) for item in page.items],
        pagination=PaginationMeta(limit=page.limit, offset=page.offset, total=page.total),
    )


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> CustomerResponse:
    customer = await _service.get(uow, ctx, customer_id)
    return CustomerResponse.model_validate(customer)


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: UUID,
    payload: CustomerUpdateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> CustomerResponse:
    customer = await _service.update(
        uow, ctx, customer_id, name=payload.name, description=payload.description
    )
    return CustomerResponse.model_validate(customer)


@router.post("/{customer_id}/archive", response_model=CustomerResponse)
async def archive_customer(
    customer_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> CustomerResponse:
    customer = await _service.archive(uow, ctx, customer_id)
    return CustomerResponse.model_validate(customer)
