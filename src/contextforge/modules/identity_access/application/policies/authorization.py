"""Thin authorization helpers built on ``RequestContext``."""

from __future__ import annotations

from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.domain.exceptions.identity import ResourceNotFoundError


def require_project_access(ctx: RequestContext, project_id: UUID) -> None:
    """Raise ``ResourceNotFoundError`` when the caller cannot access the project."""
    if not ctx.can_access_project(project_id):
        raise ResourceNotFoundError("Project not found.")
