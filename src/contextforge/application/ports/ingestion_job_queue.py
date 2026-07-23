"""Port for background ingestion job queues."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID


class IngestionJobQueuePort(Protocol):
    """Distributes ingestion job ids to background workers."""

    async def enqueue(self, job_id: UUID) -> None:
        """Push a job id onto the worker queue."""
        ...

    async def dequeue(self, *, timeout_seconds: float) -> UUID | None:
        """Pop the next job id, or ``None`` when the timeout elapses."""
        ...


__all__ = ["IngestionJobQueuePort"]
