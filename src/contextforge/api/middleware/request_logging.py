"""Structured request logging and timing middleware."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from contextforge.shared.logging.setup import get_logger

logger = get_logger("contextforge.api.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, route, status, and duration without bodies or secrets."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            route = request.scope.get("route")
            route_path = getattr(route, "path", request.url.path)
            logger.info(
                "request_completed",
                extra={
                    "http_method": request.method,
                    "route": route_path,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "correlation_id": getattr(request.state, "correlation_id", None),
                    "client_host": request.client.host if request.client else None,
                },
            )
