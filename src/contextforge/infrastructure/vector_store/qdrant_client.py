"""Qdrant health client for readiness checks."""

from __future__ import annotations

import asyncio
import time

from qdrant_client import QdrantClient

from contextforge.application.ports.health import DependencyCheckResult
from contextforge.domain.exceptions.base import DependencyUnavailableError
from contextforge.shared.config.settings import QdrantSettings
from contextforge.shared.logging.setup import get_logger

logger = get_logger(__name__)


class QdrantHealthClient:
    """Qdrant client used for readiness probes.

    Full vector operations will be introduced in later commits.
    """

    name = "qdrant"

    def __init__(self, settings: QdrantSettings) -> None:
        self._settings = settings
        api_key = None
        if settings.api_key is not None:
            value = settings.api_key.get_secret_value()
            api_key = value or None
        self._client = QdrantClient(
            url=settings.url,
            api_key=api_key,
            timeout=int(settings.timeout_seconds),
            check_compatibility=False,
        )

    async def verify(self) -> None:
        result = await self.check()
        if result.status != "up":
            raise DependencyUnavailableError(
                f"Qdrant is unavailable: {result.detail or 'connection failed'}"
            )

    async def check(self) -> DependencyCheckResult:
        started = time.perf_counter()
        try:
            await asyncio.wait_for(
                asyncio.to_thread(self._client.get_collections),
                timeout=self._settings.timeout_seconds,
            )
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            return DependencyCheckResult(name=self.name, status="up", latency_ms=latency_ms)
        except Exception as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.warning("qdrant_readiness_failed", exc_info=exc)
            return DependencyCheckResult(
                name=self.name,
                status="down",
                latency_ms=latency_ms,
                detail="connection failed",
            )

    async def close(self) -> None:
        await asyncio.to_thread(self._client.close)
        logger.info("qdrant_client_closed")
