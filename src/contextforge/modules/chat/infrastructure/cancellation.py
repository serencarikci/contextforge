from __future__ import annotations

import threading
from uuid import UUID


class InMemoryStreamCancellationRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cancelled: set[UUID] = set()
        self._active: set[UUID] = set()

    def begin(self, message_id: UUID) -> None:
        with self._lock:
            self._active.add(message_id)
            self._cancelled.discard(message_id)

    def is_cancelled(self, message_id: UUID) -> bool:
        with self._lock:
            return message_id in self._cancelled

    def cancel(self, message_id: UUID) -> bool:
        with self._lock:
            if message_id not in self._active:
                return False
            self._cancelled.add(message_id)
            return True

    def end(self, message_id: UUID) -> None:
        with self._lock:
            self._active.discard(message_id)
            self._cancelled.discard(message_id)


__all__ = ["InMemoryStreamCancellationRegistry"]
