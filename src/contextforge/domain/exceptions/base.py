"""Base domain and application exception types."""

from __future__ import annotations


class _CodedError(Exception):
    """Shared base for exceptions that expose a stable machine-readable code."""

    code: str = "ERROR"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class DomainError(_CodedError):
    """Base class for domain-layer errors."""

    code = "DOMAIN_ERROR"


class ApplicationError(_CodedError):
    """Base class for application-layer errors."""

    code = "APPLICATION_ERROR"


class InfrastructureError(ApplicationError):
    """Raised when an infrastructure dependency fails."""

    code = "INFRASTRUCTURE_ERROR"
