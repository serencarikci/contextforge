from __future__ import annotations

from contextforge.domain.exceptions.base import ApplicationError, DomainError


class AuthenticationError(ApplicationError):
    code = "AUTHENTICATION_REQUIRED"
    http_status = 401


class InvalidDevelopmentIdentityError(AuthenticationError):
    code = "INVALID_DEVELOPMENT_IDENTITY"
    http_status = 401


class AuthorizationError(ApplicationError):
    code = "PERMISSION_DENIED"
    http_status = 403


class UserInactiveError(AuthorizationError):
    code = "USER_INACTIVE"
    http_status = 403


class OrganizationInactiveError(AuthorizationError):
    code = "ORGANIZATION_INACTIVE"
    http_status = 403


class MembershipInactiveError(AuthorizationError):
    code = "MEMBERSHIP_INACTIVE"
    http_status = 403


class ResourceNotFoundError(ApplicationError):
    code = "RESOURCE_NOT_FOUND"
    http_status = 404


class DuplicateResourceError(ApplicationError):
    code = "DUPLICATE_RESOURCE"
    http_status = 409


class InvalidResourceStateError(DomainError):
    code = "INVALID_RESOURCE_STATE"


class TenantMismatchError(AuthorizationError):
    code = "TENANT_MISMATCH"
    http_status = 403
