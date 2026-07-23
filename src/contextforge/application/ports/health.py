"""Port for infrastructure readiness checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class DependencyCheckResult:
    """Result of a single dependency readiness check."""

    name: str
    status: Literal["up", "down"]
    latency_ms: float
    detail: str | None = None


class HealthCheckPort(Protocol):
    """Port implemented by infrastructure clients that support readiness checks."""

    name: str

    async def check(self) -> DependencyCheckResult:
        """Execute a readiness probe against the dependency."""
        ...
