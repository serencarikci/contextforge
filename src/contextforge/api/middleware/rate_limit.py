"""Sliding-window rate limiting for ``/api/v1`` routes."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from contextforge.shared.config.settings import RateLimitSettings, Settings


class _MemorySlidingWindow:
    """Process-local sliding window limiter."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self._limit = limit
        self._window = float(window_seconds)
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self._limit:
                retry_after = max(1, int(self._window - (now - bucket[0])) + 1)
                return False, retry_after
            bucket.append(now)
            return True, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Reject excess requests to ``/api/v1`` with HTTP 429."""

    def __init__(self, app: object, settings: Settings) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._config: RateLimitSettings = settings.rate_limit
        self._memory = _MemorySlidingWindow(
            limit=self._config.requests,
            window_seconds=self._config.window_seconds,
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not self._config.enabled:
            return await call_next(request)

        path = request.url.path
        if not path.startswith("/api/v1"):
            return await call_next(request)
        for prefix in self._config.exclude_path_prefixes:
            if path.startswith(prefix):
                return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        identity = request.headers.get("X-ContextForge-User-ID", client_host)
        key = f"{client_host}:{identity}"

        allowed, retry_after = await self._allow(request, key)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limit_exceeded",
                        "message": "Too many requests. Please retry later.",
                    }
                },
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)

    async def _allow(self, request: Request, key: str) -> tuple[bool, int]:
        if self._config.backend == "redis":
            redis_wrapper = getattr(request.app.state, "redis_client", None)
            raw = getattr(redis_wrapper, "client", None) if redis_wrapper is not None else None
            if raw is not None:
                return await self._check_redis(raw, key)
        return self._memory.allow(key)

    async def _check_redis(self, client: object, key: str) -> tuple[bool, int]:
        now = time.time()
        window = float(self._config.window_seconds)
        redis_key = f"{self._config.redis_key_prefix}:{key}"
        cutoff = now - window
        try:
            pipe = client.pipeline()  # type: ignore[attr-defined]
            pipe.zremrangebyscore(redis_key, 0, cutoff)
            pipe.zcard(redis_key)
            pipe.zadd(redis_key, {f"{now}": now})
            pipe.expire(redis_key, int(window) + 1)
            results = await pipe.execute()
            count = int(results[1])
            if count >= self._config.requests:
                return False, max(1, int(window))
            return True, 0
        except Exception:
            return self._memory.allow(key)
