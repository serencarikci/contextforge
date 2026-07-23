"""MinIO client used for readiness checks and future document storage."""

from __future__ import annotations

import asyncio
import time

from minio import Minio

from contextforge.application.ports.health import DependencyCheckResult
from contextforge.domain.exceptions.base import DependencyUnavailableError
from contextforge.shared.config.settings import MinioSettings
from contextforge.shared.logging.setup import get_logger

logger = get_logger(__name__)


class MinioClient:
    """MinIO wrapper with async-friendly readiness checks."""

    name = "minio"

    def __init__(self, settings: MinioSettings) -> None:
        self._settings = settings
        self._client = Minio(
            endpoint=settings.endpoint,
            access_key=settings.access_key.get_secret_value(),
            secret_key=settings.secret_key.get_secret_value(),
            secure=settings.secure,
            region=settings.region,
        )

    @property
    def client(self) -> Minio:
        return self._client

    async def verify(self) -> None:
        result = await self.check()
        if result.status != "up":
            raise DependencyUnavailableError(
                f"MinIO is unavailable: {result.detail or 'connection failed'}"
            )

    async def check(self) -> DependencyCheckResult:
        started = time.perf_counter()
        try:
            await asyncio.wait_for(
                asyncio.to_thread(self._client.bucket_exists, self._settings.bucket),
                timeout=self._settings.timeout_seconds,
            )
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            return DependencyCheckResult(name=self.name, status="up", latency_ms=latency_ms)
        except Exception as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.warning("minio_readiness_failed", exc_info=exc)
            return DependencyCheckResult(
                name=self.name,
                status="down",
                latency_ms=latency_ms,
                detail="connection failed",
            )

    async def close(self) -> None:

        logger.info("minio_client_closed")
