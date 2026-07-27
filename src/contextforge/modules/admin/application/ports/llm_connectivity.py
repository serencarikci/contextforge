"""Port for probing LLM provider connectivity without exposing secrets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from contextforge.modules.admin.domain.entities.llm_provider_config import LlmProviderConfig
from contextforge.modules.admin.domain.enums import LlmConnectivityStatus


@dataclass(frozen=True, slots=True)
class LlmConnectivityResult:
    status: LlmConnectivityStatus
    latency_ms: float | None = None
    detail: str | None = None


class LlmConnectivityCheckPort(Protocol):
    async def check(
        self,
        config: LlmProviderConfig,
        *,
        api_key: str | None,
        timeout_seconds: float,
    ) -> LlmConnectivityResult:
        """Probe whether the configured provider endpoint is reachable."""
        ...
