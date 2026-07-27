from __future__ import annotations

from redis.asyncio import Redis


class RedisAdminCache:
    def __init__(self, redis: Redis[str], *, key_prefix: str = "contextforge:admin:") -> None:
        self._redis = redis
        self._prefix = key_prefix

    def _key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    async def get(self, key: str) -> str | None:
        value = await self._redis.get(self._key(key))
        return value if value is not None else None

    async def set(self, key: str, value: str, *, ttl_seconds: int) -> None:
        full = self._key(key)
        if ttl_seconds <= 0:
            await self._redis.set(full, value)
        else:
            await self._redis.set(full, value, ex=ttl_seconds)

    async def delete(self, key: str) -> None:
        await self._redis.delete(self._key(key))

    async def bump_version(self, namespace: str) -> int:
        return int(await self._redis.incr(self._key(f"ver:{namespace}")))

    async def get_version(self, namespace: str) -> int:
        raw = await self._redis.get(self._key(f"ver:{namespace}"))
        return int(raw) if raw is not None else 0
