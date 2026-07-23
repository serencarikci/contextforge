"""Redis-backed ingestion job queue."""

from __future__ import annotations

from uuid import UUID

from redis.asyncio import Redis

from contextforge.shared.config.settings import IngestionSettings
from contextforge.shared.logging.setup import get_logger

logger = get_logger(__name__)


class RedisIngestionJobQueue:
    """Simple Redis list queue for ingestion job ids."""

    def __init__(self, redis: Redis[str], settings: IngestionSettings) -> None:
        self._redis = redis
        self._settings = settings

    async def enqueue(self, job_id: UUID) -> None:
        await self._redis.lpush(self._settings.queue_key, str(job_id))
        logger.info("ingestion_job_enqueued", extra={"job_id": str(job_id)})

    async def dequeue(self, *, timeout_seconds: float) -> UUID | None:
        timeout = max(1, int(timeout_seconds))
        result = await self._redis.brpop(self._settings.queue_key, timeout=timeout)
        if result is None:
            return None
        _key, raw_job_id = result
        return UUID(raw_job_id)


class InMemoryIngestionJobQueue:
    """Process-local queue used by unit/API tests."""

    def __init__(self) -> None:
        self._items: list[UUID] = []

    async def enqueue(self, job_id: UUID) -> None:
        self._items.append(job_id)

    async def dequeue(self, *, timeout_seconds: float) -> UUID | None:
        del timeout_seconds
        if not self._items:
            return None
        return self._items.pop(0)

    @property
    def pending(self) -> list[UUID]:
        return list(self._items)


__all__ = ["InMemoryIngestionJobQueue", "RedisIngestionJobQueue"]
