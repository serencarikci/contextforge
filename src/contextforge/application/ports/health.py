from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class DependencyCheckResult:
    name: str
    status: Literal["up", "down"]
    latency_ms: float
    detail: str | None = None


class HealthCheckPort(Protocol):
    name: str

    async def check(self) -> DependencyCheckResult: ...
