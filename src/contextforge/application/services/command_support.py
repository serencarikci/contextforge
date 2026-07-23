"""Shared helpers for application services."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from contextforge.application.context.request_context import RequestContext
from contextforge.domain.exceptions.identity import (
    DuplicateResourceError,
    OrganizationInactiveError,
)
from contextforge.modules.audit.domain.entities.audit_event import AuditEvent
from contextforge.modules.identity_access.domain.enums import OrganizationStatus
from contextforge.modules.organizations.domain.entities.organization import Organization
from contextforge.shared.logging.context import get_correlation_id
from contextforge.shared.utilities.correlation import is_valid_correlation_id


def ensure_organization_writable(organization: Organization) -> None:
    if organization.status == OrganizationStatus.SUSPENDED:
        raise OrganizationInactiveError("Suspended organizations cannot perform write operations.")
    if organization.status == OrganizationStatus.ARCHIVED:
        raise OrganizationInactiveError("Archived organizations cannot perform write operations.")
    organization.ensure_writable()


def translate_integrity_error(
    exc: IntegrityError, *, message: str = "Resource already exists."
) -> None:
    raise DuplicateResourceError(message) from exc


def build_audit_event(
    ctx: RequestContext,
    *,
    action: str,
    resource_type: str,
    resource_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    correlation_id: UUID | None = None
    if is_valid_correlation_id(ctx.correlation_id):
        correlation_id = UUID(ctx.correlation_id)
    return AuditEvent(
        action=action,
        resource_type=resource_type,
        organization_id=ctx.organization_id,
        actor_user_id=ctx.user_id,
        resource_id=resource_id,
        correlation_id=correlation_id,
        metadata=metadata or {},
    )


def build_audit_event_for_actor(
    *,
    actor_user_id: UUID | None,
    organization_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    """Build an audit event for bootstrap-like flows without a full RequestContext.

    Used by use cases such as organization/user creation where no authenticated
    tenant context exists yet (the actor is not yet a member of any organization).
    """
    candidate = get_correlation_id()
    correlation_id: UUID | None = None
    if is_valid_correlation_id(candidate):
        assert candidate is not None
        correlation_id = UUID(candidate)
    return AuditEvent(
        action=action,
        resource_type=resource_type,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        resource_id=resource_id,
        correlation_id=correlation_id,
        metadata=metadata or {},
    )
