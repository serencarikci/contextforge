from __future__ import annotations

from typing import Protocol
from uuid import UUID


class IngestionJobQueuePort(Protocol):
    async def enqueue(self, job_id: UUID) -> None: ...

    async def dequeue(self, *, timeout_seconds: float) -> UUID | None: ...

    async def depth(self) -> int: ...


__all__ = ["IngestionJobQueuePort"]
