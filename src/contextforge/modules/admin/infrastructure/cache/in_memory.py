"""Process-local admin cache used in tests and when Redis is unavailable."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(slots=True)
class _Entry:
    value: str
    expires_at: float | None


class InMemoryAdminCache:
    def __init__(self) -> None:
        self._store: dict[str, _Entry] = {}
        self._versions: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expires_at is not None and entry.expires_at <= time.monotonic():
            self._store.pop(key, None)
            return None
        return entry.value

    async def set(self, key: str, value: str, *, ttl_seconds: int) -> None:
        expires_at = None if ttl_seconds <= 0 else time.monotonic() + ttl_seconds
        self._store[key] = _Entry(value=value, expires_at=expires_at)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def bump_version(self, namespace: str) -> int:
        current = self._versions.get(namespace, 0) + 1
        self._versions[namespace] = current
        return current

    async def get_version(self, namespace: str) -> int:
        return self._versions.get(namespace, 0)
