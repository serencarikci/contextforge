from __future__ import annotations

from typing import Protocol
from uuid import UUID


class StreamCancellationPort(Protocol):
    def begin(self, message_id: UUID) -> None: ...

    def is_cancelled(self, message_id: UUID) -> bool: ...

    def cancel(self, message_id: UUID) -> bool: ...

    def end(self, message_id: UUID) -> None: ...


__all__ = ["StreamCancellationPort"]
