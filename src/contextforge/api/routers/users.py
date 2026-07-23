"""User endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from contextforge.api.dependencies.identity import get_request_context, get_uow
from contextforge.api.schemas.users import UserCreateRequest, UserResponse, UserUpdateRequest
from contextforge.application.context.request_context import RequestContext
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.modules.identity_access.application.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])

_service = UserService()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> UserResponse:
    """Provision a new user. Requires ``user:manage`` in the caller's organization."""
    user = await _service.create(
        uow,
        email=payload.email,
        display_name=payload.display_name,
        preferred_language=payload.preferred_language,
        ctx=ctx,
    )
    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> UserResponse:
    user = await _service.get(uow, ctx, user_id)
    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    payload: UserUpdateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> UserResponse:
    user = await _service.update(
        uow,
        ctx,
        user_id,
        display_name=payload.display_name,
        preferred_language=payload.preferred_language,
    )
    return UserResponse.model_validate(user)


@router.post("/{user_id}/suspend", response_model=UserResponse)
async def suspend_user(
    user_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> UserResponse:
    user = await _service.suspend(uow, ctx, user_id)
    return UserResponse.model_validate(user)


@router.post("/{user_id}/archive", response_model=UserResponse)
async def archive_user(
    user_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> UserResponse:
    user = await _service.archive(uow, ctx, user_id)
    return UserResponse.model_validate(user)
