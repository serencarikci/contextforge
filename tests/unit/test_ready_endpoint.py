"""Unit tests for readiness router behavior with stubbed health service."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from contextforge.api.dependencies.providers import get_health_service
from contextforge.application.ports.health import DependencyCheckResult
from contextforge.application.services.health_service import HealthService, ReadinessReport
from contextforge.bootstrap.app_factory import create_app
from contextforge.shared.config.settings import Settings, clear_settings_cache


class _ReadyService(HealthService):
    def __init__(self, report: ReadinessReport) -> None:
        self._report = report
        super().__init__([])

    async def check_readiness(self) -> ReadinessReport:
        return self._report


@pytest.mark.unit
def test_ready_endpoint_ready_and_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONTEXTFORGE_APP__ENVIRONMENT", "test")
    monkeypatch.setenv("CONTEXTFORGE_API__CORS_ORIGINS", "http://localhost:3000")
    clear_settings_cache()
    app = create_app(Settings())

    ready_report = ReadinessReport(
        status="ready",
        checks={
            "postgresql": DependencyCheckResult("postgresql", "up", 1.0),
            "redis": DependencyCheckResult("redis", "up", 1.0),
            "qdrant": DependencyCheckResult("qdrant", "up", 1.0),
            "minio": DependencyCheckResult("minio", "up", 1.0),
        },
        total_latency_ms=2.0,
    )
    app.dependency_overrides[get_health_service] = lambda: _ReadyService(ready_report)
    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    not_ready = ReadinessReport(
        status="not_ready",
        checks={
            "postgresql": DependencyCheckResult("postgresql", "up", 1.0),
            "redis": DependencyCheckResult("redis", "down", 1.0),
            "qdrant": DependencyCheckResult("qdrant", "up", 1.0),
            "minio": DependencyCheckResult("minio", "up", 1.0),
        },
        total_latency_ms=2.0,
    )
    app.dependency_overrides[get_health_service] = lambda: _ReadyService(not_ready)
    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 503
        assert response.json()["status"] == "not_ready"
