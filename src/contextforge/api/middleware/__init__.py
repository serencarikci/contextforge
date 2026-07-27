from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from contextforge.api.middleware.correlation import CorrelationIdMiddleware
from contextforge.api.middleware.metrics import MetricsMiddleware, render_metrics
from contextforge.api.middleware.rate_limit import RateLimitMiddleware
from contextforge.api.middleware.request_logging import RequestLoggingMiddleware
from contextforge.api.middleware.security_headers import SecurityHeadersMiddleware
from contextforge.shared.config.settings import Settings


def register_middleware(app: FastAPI, settings: Settings) -> None:

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)

    if settings.rate_limit.enabled:
        app.add_middleware(RateLimitMiddleware, settings=settings)

    if settings.observability.metrics_enabled:
        app.add_middleware(
            MetricsMiddleware,
            metrics_path=settings.observability.metrics_path,
        )
        app.add_api_route(
            settings.observability.metrics_path,
            render_metrics,
            methods=["GET"],
            include_in_schema=False,
        )

    if settings.api.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.api.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "X-Correlation-ID",
                "X-ContextForge-User-ID",
                "X-ContextForge-Organization-ID",
                "X-ContextForge-Project-ID",
                "X-ContextForge-Knowledge-Space-ID",
                "Idempotency-Key",
            ],
        )
