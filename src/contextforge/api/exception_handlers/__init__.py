"""Exception handler registration."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from contextforge.domain.exceptions.base import (
    ApplicationError,
    DependencyUnavailableError,
    DomainError,
)
from contextforge.shared.logging.context import get_correlation_id
from contextforge.shared.logging.setup import get_logger

logger = get_logger(__name__)


def _error_payload(code: str, message: str) -> dict[str, object]:
    return {
        "error": {
            "code": code,
            "message": message,
            "correlation_id": get_correlation_id(),
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Register consistent API exception handlers."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        logger.info(
            "validation_error",
            extra={"path": request.url.path, "errors": exc.errors()},
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_payload(
                "VALIDATION_ERROR",
                "Request validation failed.",
            ),
        )

    @app.exception_handler(DomainError)
    async def domain_exception_handler(request: Request, exc: DomainError) -> JSONResponse:
        logger.warning(
            "domain_error",
            extra={
                "path": request.url.path,
                "error_code": exc.code,
                "error_message": exc.message,
            },
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error_payload(exc.code, exc.message),
        )

    @app.exception_handler(DependencyUnavailableError)
    async def dependency_exception_handler(
        request: Request,
        exc: DependencyUnavailableError,
    ) -> JSONResponse:
        logger.error(
            "dependency_unavailable",
            extra={"path": request.url.path, "code": exc.code},
            exc_info=exc,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=_error_payload(
                exc.code,
                "A required dependency is currently unavailable.",
            ),
        )

    @app.exception_handler(ApplicationError)
    async def application_exception_handler(
        request: Request,
        exc: ApplicationError,
    ) -> JSONResponse:
        logger.error(
            "application_error",
            extra={"path": request.url.path, "code": exc.code},
            exc_info=exc,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_payload(exc.code, exc.message),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        code = "HTTP_ERROR"
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            code = "NOT_FOUND"
        elif exc.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
            code = "METHOD_NOT_ALLOWED"
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(code, str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_exception",
            extra={"path": request.url.path},
            exc_info=exc,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_payload(
                "INTERNAL_SERVER_ERROR",
                "An unexpected error occurred.",
            ),
        )
