"""System information endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from contextforge.api.dependencies.providers import get_system_info_service
from contextforge.api.schemas.system import CapabilitiesSchema, SystemInfoResponse
from contextforge.application.services.system_info_service import SystemInfoService

router = APIRouter(prefix="/system")


@router.get("/info", response_model=SystemInfoResponse)
async def system_info(
    service: Annotated[SystemInfoService, Depends(get_system_info_service)],
) -> SystemInfoResponse:
    """Return safe system information and explicit capability flags."""
    info = service.get_info()
    return SystemInfoResponse(
        name=info.name,
        version=info.version,
        environment=info.environment,
        capabilities=CapabilitiesSchema(
            document_ingestion=info.capabilities.document_ingestion,
            rag=info.capabilities.rag,
            chat=info.capabilities.chat,
            multilingual_answers=info.capabilities.multilingual_answers,
        ),
    )
