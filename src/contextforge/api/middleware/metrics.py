"""Prometheus metrics middleware and scrape endpoint helpers."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_COUNT = Counter(
    "contextforge_http_requests_total",
    "Total HTTP requests",
    ["method", "path_template", "status"],
)
REQUEST_LATENCY = Histogram(
    "contextforge_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path_template"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
DEPENDENCY_UP = Gauge(
    "contextforge_dependency_up",
    "Dependency availability (1=up, 0=down)",
    ["dependency"],
)


def _normalize_path(path: str) -> str:
    """Collapse UUID-looking path segments for low-cardinality labels."""
    parts: list[str] = []
    for part in path.split("/"):
        if not part:
            parts.append(part)
            continue
        if len(part) == 36 and part.count("-") == 4:
            parts.append("{id}")
        else:
            parts.append(part)
    return "/".join(parts) or "/"


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record request counts and latency histograms."""

    def __init__(self, app: object, metrics_path: str = "/metrics") -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._metrics_path = metrics_path

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path == self._metrics_path:
            return await call_next(request)

        started = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - started
        path = _normalize_path(request.url.path)
        method = request.method
        status = str(response.status_code)
        REQUEST_COUNT.labels(method=method, path_template=path, status=status).inc()
        REQUEST_LATENCY.labels(method=method, path_template=path).observe(elapsed)
        return response


async def render_metrics(request: Request) -> Response:
    """Update dependency gauges when possible and return Prometheus exposition."""
    settings = request.app.state.settings
    if settings.observability.dependency_gauge_enabled:
        await _refresh_dependency_gauges(request)

    payload = generate_latest()
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)


async def _refresh_dependency_gauges(request: Request) -> None:
    mapping = {
        "postgres": "database",
        "redis": "redis_client",
        "qdrant": "qdrant_client",
        "minio": "minio_client",
    }
    for dependency, attr in mapping.items():
        client = getattr(request.app.state, attr, None)
        if client is None:
            DEPENDENCY_UP.labels(dependency=dependency).set(0)
            continue
        checker = getattr(client, "check", None) or getattr(client, "ping", None)
        if checker is None and attr == "database":
            DEPENDENCY_UP.labels(dependency=dependency).set(1)
            continue
        try:
            if checker is None:
                DEPENDENCY_UP.labels(dependency=dependency).set(1)
                continue
            result = checker()
            if hasattr(result, "__await__"):
                result = await result
            status = getattr(result, "status", None)
            if status is None:
                DEPENDENCY_UP.labels(dependency=dependency).set(1 if result else 0)
            else:
                DEPENDENCY_UP.labels(dependency=dependency).set(1 if status == "up" else 0)
        except Exception:
            DEPENDENCY_UP.labels(dependency=dependency).set(0)
