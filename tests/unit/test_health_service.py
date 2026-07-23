"""Unit tests for health aggregation."""

from __future__ import annotations

import pytest

from contextforge.application.ports.health import DependencyCheckResult
from contextforge.application.services.health_service import HealthService


class _StubChecker:
    def __init__(self, result: DependencyCheckResult) -> None:
        self._result = result

    @property
    def name(self) -> str:
        return self._result.name

    async def check(self) -> DependencyCheckResult:
        return self._result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_readiness_all_up() -> None:
    service = HealthService(
        [
            _StubChecker(DependencyCheckResult("postgresql", "up", 1.0)),
            _StubChecker(DependencyCheckResult("redis", "up", 1.5)),
            _StubChecker(DependencyCheckResult("qdrant", "up", 2.0)),
            _StubChecker(DependencyCheckResult("minio", "up", 2.5)),
        ]
    )
    report = await service.check_readiness()
    assert report.status == "ready"
    assert set(report.checks) == {"postgresql", "redis", "qdrant", "minio"}
    assert report.total_latency_ms >= 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_readiness_one_down() -> None:
    service = HealthService(
        [
            _StubChecker(DependencyCheckResult("postgresql", "up", 1.0)),
            _StubChecker(DependencyCheckResult("redis", "down", 1.5, detail="connection failed")),
            _StubChecker(DependencyCheckResult("qdrant", "up", 2.0)),
            _StubChecker(DependencyCheckResult("minio", "up", 2.5)),
        ]
    )
    report = await service.check_readiness()
    assert report.status == "not_ready"
    assert report.checks["redis"].status == "down"
    assert report.checks["postgresql"].status == "up"
