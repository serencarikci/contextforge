"""Health and readiness endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from contextforge.api.dependencies.providers import get_health_service, get_settings_dependency
from contextforge.api.schemas.health import DependencyStatus, LivenessResponse, ReadinessResponse
from contextforge.application.services.health_service import HealthService
from contextforge.shared.config.settings import Settings

router = APIRouter(prefix="/health")


@router.get("/live", response_model=LivenessResponse)
async def liveness(
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> LivenessResponse:
    """Liveness probe that does not depend on external infrastructure."""
    return LivenessResponse(
        status="ok",
        service=settings.app.name,
        version=settings.app.version,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
)
async def readiness(
    response: Response,
    health_service: Annotated[HealthService, Depends(get_health_service)],
) -> ReadinessResponse:
    """Readiness probe that checks PostgreSQL, Redis, Qdrant, and MinIO."""
    report = await health_service.check_readiness()
    payload = ReadinessResponse(
        status=report.status,
        checks={
            name: DependencyStatus(status=check.status, latency_ms=check.latency_ms)
            for name, check in report.checks.items()
        },
        total_latency_ms=report.total_latency_ms,
    )
    if report.status != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return payload
