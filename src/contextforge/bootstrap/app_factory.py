"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from contextforge.api.exception_handlers import register_exception_handlers
from contextforge.api.middleware import register_middleware
from contextforge.api.routers import api_router
from contextforge.bootstrap.lifespan import lifespan
from contextforge.shared.config.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    resolved = settings or get_settings()
    docs_url = "/docs" if resolved.api.docs_enabled else None
    redoc_url = "/redoc" if resolved.api.docs_enabled else None
    openapi_url = "/openapi.json" if resolved.api.docs_enabled else None

    application = FastAPI(
        title="ContextForge API",
        version=resolved.app.version,
        description=(
            "Secure enterprise knowledge platform foundation. "
            "Document ingestion, RAG, and chat are not implemented in this release."
        ),
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        root_path=resolved.api.root_path,
    )
    application.state.settings = resolved

    register_middleware(application, resolved)
    register_exception_handlers(application)
    application.include_router(api_router, prefix="/api/v1")

    return application
