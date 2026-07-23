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
    caps = info.capabilities
    return SystemInfoResponse(
        name=info.name,
        version=info.version,
        environment=info.environment,
        capabilities=CapabilitiesSchema(
            identity_context=caps.identity_context,
            multi_tenancy=caps.multi_tenancy,
            rbac=caps.rbac,
            customers=caps.customers,
            projects=caps.projects,
            knowledge_spaces=caps.knowledge_spaces,
            audit_log=caps.audit_log,
            document_ingestion=caps.document_ingestion,
            document_parsing=caps.document_parsing,
            document_chunking=caps.document_chunking,
            document_embeddings=caps.document_embeddings,
            ingestion_workers=caps.ingestion_workers,
            rag=caps.rag,
            chat=caps.chat,
            multilingual_answers=caps.multilingual_answers,
        ),
        authentication=info.authentication,
    )
