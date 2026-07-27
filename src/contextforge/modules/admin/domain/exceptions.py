from __future__ import annotations

from contextforge.domain.exceptions.base import ApplicationError, DomainError


class SystemRoleImmutableError(ApplicationError):
    code = "SYSTEM_ROLE_IMMUTABLE"
    http_status = 403


class UnknownPermissionError(DomainError):
    code = "UNKNOWN_PERMISSION"


class QuotaExceededError(ApplicationError):
    code = "QUOTA_EXCEEDED"
    http_status = 409


class RetentionPolicyDisabledError(ApplicationError):
    code = "RETENTION_DISABLED"
    http_status = 409


class SecretDecryptionError(ApplicationError):
    code = "SECRET_DECRYPTION_FAILED"
    http_status = 500


__all__ = [
    "QuotaExceededError",
    "RetentionPolicyDisabledError",
    "SecretDecryptionError",
    "SystemRoleImmutableError",
    "UnknownPermissionError",
]
