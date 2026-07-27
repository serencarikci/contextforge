"""Cache port used by feature-flag and settings resolvers."""

from __future__ import annotations

from typing import Protocol


class AdminCachePort(Protocol):
    """Small key/value cache with TTL and versioned invalidation."""

    async def get(self, key: str) -> str | None:
        """Return the cached string value, or ``None`` on miss."""
        ...

    async def set(self, key: str, value: str, *, ttl_seconds: int) -> None:
        """Store ``value`` under ``key`` with a TTL."""
        ...

    async def delete(self, key: str) -> None:
        """Remove a single key."""
        ...

    async def bump_version(self, namespace: str) -> int:
        """Increment and return a namespace version used to salt cache keys."""
        ...

    async def get_version(self, namespace: str) -> int:
        """Return the current namespace version (default ``0``)."""
        ...
