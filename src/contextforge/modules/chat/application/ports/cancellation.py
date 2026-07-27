"""Port for cooperative cancellation of in-flight streaming answers."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID


class StreamCancellationPort(Protocol):
    """Tracks whether an in-flight assistant message stream should stop early.

    Implementations are process-local: a stream is only cancellable by a
    request served by the same application instance that is running it.
    """

    def begin(self, message_id: UUID) -> None:
        """Register a new in-flight stream for ``message_id``."""
        ...

    def is_cancelled(self, message_id: UUID) -> bool:
        """Return whether cancellation has been requested for ``message_id``."""
        ...

    def cancel(self, message_id: UUID) -> bool:
        """Request cancellation. Returns ``True`` if an in-flight stream was found."""
        ...

    def end(self, message_id: UUID) -> None:
        """Release tracking state for ``message_id`` once the stream finishes."""
        ...


__all__ = ["StreamCancellationPort"]
