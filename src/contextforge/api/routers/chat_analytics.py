from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from contextforge.api.dependencies.identity import get_request_context, get_uow
from contextforge.api.dependencies.providers import get_chat_analytics_service
from contextforge.api.schemas.chat import ChatAnalyticsOverviewResponse
from contextforge.application.context.request_context import RequestContext
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.modules.chat.application.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/chat/analytics", tags=["chat"])


@router.get("/overview", response_model=ChatAnalyticsOverviewResponse)
async def get_chat_analytics_overview(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[AnalyticsService, Depends(get_chat_analytics_service)],
    since: Annotated[datetime | None, Query()] = None,
) -> ChatAnalyticsOverviewResponse:
    overview = await service.get_overview(uow, ctx, since=since)
    return ChatAnalyticsOverviewResponse.model_validate(overview, from_attributes=True)
