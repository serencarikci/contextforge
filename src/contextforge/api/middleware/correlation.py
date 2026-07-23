"""Correlation ID middleware."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from contextforge.shared.logging.context import set_correlation_id
from contextforge.shared.utilities.correlation import resolve_correlation_id

CORRELATION_HEADER = "X-Correlation-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Accept or generate a correlation ID for each request."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming = request.headers.get(CORRELATION_HEADER)
        correlation_id = resolve_correlation_id(incoming)
        set_correlation_id(correlation_id)
        request.state.correlation_id = correlation_id

        response = await call_next(request)
        response.headers[CORRELATION_HEADER] = correlation_id
        return response
