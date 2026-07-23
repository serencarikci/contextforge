"""Thin authorization policy helpers built on top of ``RequestContext``.

These are convenience wrappers around ``RequestContext`` used by application
services to keep authorization checks consistent and readable. They do not
hold any state of their own and never touch the database.
"""

from __future__ import annotations

from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.domain.exceptions.identity import ResourceNotFoundError


def ensure_same_organization(ctx: RequestContext, organization_id: UUID) -> None:
    """Raise ``ResourceNotFoundError`` when the target belongs to another tenant.

    Cross-tenant access is always surfaced as "not found" rather than
    "forbidden" so callers cannot probe for the existence of resources in
    organizations they do not belong to.
    """
    if ctx.organization_id != organization_id:
        raise ResourceNotFoundError("Resource not found.")


def require_self_or_permission(
    ctx: RequestContext, target_user_id: UUID, permission_code: str
) -> None:
    """Allow self-service actions, otherwise require the given permission."""
    if ctx.user_id == target_user_id:
        return
    ctx.require_permission(permission_code)


def require_project_access(ctx: RequestContext, project_id: UUID) -> None:
    """Raise ``ResourceNotFoundError`` when the caller cannot access the project."""
    if not ctx.can_access_project(project_id):
        raise ResourceNotFoundError("Project not found.")


def require_knowledge_space_access(ctx: RequestContext, knowledge_space_id: UUID) -> None:
    """Raise ``ResourceNotFoundError`` when the caller cannot access the knowledge space."""
    ctx.require_knowledge_space_access(knowledge_space_id)
