"""HTTP middleware registration."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from contextforge.api.middleware.correlation import CorrelationIdMiddleware
from contextforge.api.middleware.request_logging import RequestLoggingMiddleware
from contextforge.shared.config.settings import Settings


def register_middleware(app: FastAPI, settings: Settings) -> None:
    """Register middleware in the correct order."""
    # Starlette middleware executes in reverse addition order for requests.
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    if settings.api.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.api.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
        )
