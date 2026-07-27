from __future__ import annotations

import time

import httpx

from contextforge.modules.admin.application.ports.llm_connectivity import LlmConnectivityResult
from contextforge.modules.admin.domain.entities.llm_provider_config import LlmProviderConfig
from contextforge.modules.admin.domain.enums import LlmConnectivityStatus, LlmProviderKind


class HttpLlmConnectivityChecker:
    async def check(
        self,
        config: LlmProviderConfig,
        *,
        api_key: str | None,
        timeout_seconds: float,
    ) -> LlmConnectivityResult:
        if config.provider == LlmProviderKind.MOCK:
            return LlmConnectivityResult(
                status=LlmConnectivityStatus.OK, latency_ms=0.0, detail="mock"
            )

        base = (config.base_url or "").rstrip("/")
        if not base:
            return LlmConnectivityResult(
                status=LlmConnectivityStatus.SKIPPED,
                detail="No base_url configured",
            )

        headers: dict[str, str] = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        url = f"{base}/models"
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.get(url, headers=headers)
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            if response.status_code < 500:
                return LlmConnectivityResult(
                    status=LlmConnectivityStatus.OK,
                    latency_ms=latency_ms,
                    detail=f"HTTP {response.status_code}",
                )
            return LlmConnectivityResult(
                status=LlmConnectivityStatus.ERROR,
                latency_ms=latency_ms,
                detail=f"HTTP {response.status_code}",
            )
        except Exception as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            return LlmConnectivityResult(
                status=LlmConnectivityStatus.ERROR,
                latency_ms=latency_ms,
                detail=str(exc)[:500],
            )
