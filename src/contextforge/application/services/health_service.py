"""Health and readiness aggregation service."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Literal

from contextforge.application.ports.health import DependencyCheckResult, HealthCheckPort


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    """Aggregated readiness report across mandatory dependencies."""

    status: Literal["ready", "not_ready"]
    checks: dict[str, DependencyCheckResult]
    total_latency_ms: float


class HealthService:
    """Aggregates concurrent dependency readiness checks."""

    def __init__(self, checkers: list[HealthCheckPort]) -> None:
        self._checkers = checkers

    async def check_readiness(self) -> ReadinessReport:
        """Run all dependency checks concurrently and aggregate results."""
        started = time.perf_counter()
        results = await asyncio.gather(
            *[checker.check() for checker in self._checkers],
            return_exceptions=False,
        )
        checks = {result.name: result for result in results}
        overall: Literal["ready", "not_ready"] = (
            "ready" if all(item.status == "up" for item in results) else "not_ready"
        )
        total_latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return ReadinessReport(
            status=overall,
            checks=checks,
            total_latency_ms=total_latency_ms,
        )
