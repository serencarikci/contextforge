"""Base domain and application exception types."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for domain-layer errors."""

    code: str = "DOMAIN_ERROR"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class ApplicationError(Exception):
    """Base class for application-layer errors."""

    code: str = "APPLICATION_ERROR"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class InfrastructureError(ApplicationError):
    """Raised when an infrastructure dependency fails."""

    code = "INFRASTRUCTURE_ERROR"


class DependencyUnavailableError(InfrastructureError):
    """Raised when a mandatory dependency is unavailable."""

    code = "DEPENDENCY_UNAVAILABLE"
