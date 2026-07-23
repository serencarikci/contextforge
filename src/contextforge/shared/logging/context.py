"""Logging context for correlation IDs."""

from __future__ import annotations

from contextvars import ContextVar

correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    """Return the current correlation ID, if set."""
    return correlation_id_ctx.get()


def set_correlation_id(correlation_id: str | None) -> None:
    """Set the current correlation ID in context."""
    correlation_id_ctx.set(correlation_id)
