"""Administration-specific domain and application errors."""

from __future__ import annotations

from contextforge.domain.exceptions.base import ApplicationError, DomainError


class SystemRoleImmutableError(ApplicationError):
    """Raised when a caller tries to mutate a shared system role."""

    code = "SYSTEM_ROLE_IMMUTABLE"
    http_status = 403


class UnknownPermissionError(DomainError):
    """Raised when a permission code is not part of the seeded catalog."""

    code = "UNKNOWN_PERMISSION"


class QuotaExceededError(ApplicationError):
    """Raised when an organization quota would be exceeded."""

    code = "QUOTA_EXCEEDED"
    http_status = 409


class RetentionPolicyDisabledError(ApplicationError):
    """Raised when a retention run is requested while retention is disabled."""

    code = "RETENTION_DISABLED"
    http_status = 409


class SecretDecryptionError(ApplicationError):
    """Raised when a stored provider secret cannot be decrypted."""

    code = "SECRET_DECRYPTION_FAILED"
    http_status = 500


__all__ = [
    "QuotaExceededError",
    "RetentionPolicyDisabledError",
    "SecretDecryptionError",
    "SystemRoleImmutableError",
    "UnknownPermissionError",
]
