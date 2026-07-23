"""Redis client used for readiness checks and future caching."""

from __future__ import annotations

import time

from redis.asyncio import Redis

from contextforge.application.ports.health import DependencyCheckResult
from contextforge.shared.config.settings import RedisSettings
from contextforge.shared.logging.setup import get_logger

logger = get_logger(__name__)


class RedisClient:
    """Async Redis client wrapper."""

    name = "redis"

    def __init__(self, settings: RedisSettings) -> None:
        self._settings = settings
        self._client: Redis[str] = Redis.from_url(
            settings.url,
            socket_connect_timeout=settings.timeout_seconds,
            socket_timeout=settings.timeout_seconds,
            decode_responses=True,
        )

    async def check(self) -> DependencyCheckResult:
        started = time.perf_counter()
        try:
            pong = await self._client.ping()
            if not pong:
                raise RuntimeError("unexpected ping response")
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            return DependencyCheckResult(name=self.name, status="up", latency_ms=latency_ms)
        except Exception as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.warning("redis_readiness_failed", exc_info=exc)
            return DependencyCheckResult(
                name=self.name,
                status="down",
                latency_ms=latency_ms,
                detail="connection failed",
            )

    async def close(self) -> None:
        await self._client.close()
        logger.info("redis_client_closed")
