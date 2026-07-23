"""FastAPI dependencies for identity, tenancy, and authorization context.

Authentication in this release is "development identity": the caller
supplies a validated ``X-ContextForge-User-ID`` (and, for tenant-scoped
routes, ``X-ContextForge-Organization-ID``) header. Real authentication is
not yet implemented; :func:`development_identity_enabled` gates this mode to
non-production environments.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header

from contextforge.api.dependencies.providers import get_database, get_settings_dependency
from contextforge.application.context.request_context import RequestContext
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import (
    AuthenticationError,
    InvalidDevelopmentIdentityError,
    UserInactiveError,
)
from contextforge.infrastructure.database.session import DatabaseManager
from contextforge.modules.identity_access.application.services.identity_context_service import (
    build_request_context,
    development_identity_enabled,
)
from contextforge.modules.identity_access.domain.enums import UserStatus
from contextforge.shared.config.settings import Settings

USER_ID_HEADER = "X-ContextForge-User-ID"
ORGANIZATION_ID_HEADER = "X-ContextForge-Organization-ID"
PROJECT_ID_HEADER = "X-ContextForge-Project-ID"
KNOWLEDGE_SPACE_ID_HEADER = "X-ContextForge-Knowledge-Space-ID"


def _require_uuid_header(value: str | None, header_name: str) -> UUID:
    if value is None or not value.strip():
        raise AuthenticationError(f"{header_name} header is required.")
    try:
        return UUID(value.strip())
    except ValueError as exc:
        raise InvalidDevelopmentIdentityError(
            f"{header_name} header must be a valid UUID.",
        ) from exc


def _optional_uuid_header(value: str | None, header_name: str) -> UUID | None:
    if value is None or not value.strip():
        return None
    try:
        return UUID(value.strip())
    except ValueError as exc:
        raise InvalidDevelopmentIdentityError(
            f"{header_name} header must be a valid UUID.",
        ) from exc


async def get_uow(
    database: Annotated[DatabaseManager, Depends(get_database)],
) -> SqlAlchemyUnitOfWork:
    """Provide a fresh, unopened unit of work bound to the request's engine.

    Services own the transaction boundary themselves (``async with uow:``),
    so this dependency only constructs the object -- it never opens a session.
    """
    return SqlAlchemyUnitOfWork(database.session_factory)


async def get_active_user_id(
    settings: Annotated[Settings, Depends(get_settings_dependency)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    x_contextforge_user_id: Annotated[str | None, Header(alias=USER_ID_HEADER)] = None,
) -> UUID:
    """Validate the acting user for routes that have no organization context yet.

    Used by "bootstrap-like" endpoints such as creating an organization or
    provisioning a user, where the caller is not necessarily a member of any
    organization yet.
    """
    if not development_identity_enabled(settings):
        raise InvalidDevelopmentIdentityError(
            "Development identity is disabled in this environment. "
            "Real authentication is not yet implemented.",
        )
    user_id = _require_uuid_header(x_contextforge_user_id, USER_ID_HEADER)
    async with uow:
        user = await uow.users.get_by_id(user_id)
    if user is None:
        raise InvalidDevelopmentIdentityError("User not found.")
    if user.status != UserStatus.ACTIVE:
        raise UserInactiveError("User is not active.")
    return user.id


async def get_request_context(
    settings: Annotated[Settings, Depends(get_settings_dependency)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    x_contextforge_user_id: Annotated[str | None, Header(alias=USER_ID_HEADER)] = None,
    x_contextforge_organization_id: Annotated[
        str | None, Header(alias=ORGANIZATION_ID_HEADER)
    ] = None,
    x_contextforge_project_id: Annotated[str | None, Header(alias=PROJECT_ID_HEADER)] = None,
    x_contextforge_knowledge_space_id: Annotated[
        str | None, Header(alias=KNOWLEDGE_SPACE_ID_HEADER)
    ] = None,
) -> RequestContext:
    """Build the authorization context for tenant-scoped routes."""
    user_id = _require_uuid_header(x_contextforge_user_id, USER_ID_HEADER)
    organization_id = _require_uuid_header(x_contextforge_organization_id, ORGANIZATION_ID_HEADER)
    project_id = _optional_uuid_header(x_contextforge_project_id, PROJECT_ID_HEADER)
    knowledge_space_id = _optional_uuid_header(
        x_contextforge_knowledge_space_id, KNOWLEDGE_SPACE_ID_HEADER
    )

    async with uow:
        return await build_request_context(
            uow,
            settings=settings,
            user_id=user_id,
            organization_id=organization_id,
            project_id=project_id,
            knowledge_space_id=knowledge_space_id,
        )


__all__ = [
    "KNOWLEDGE_SPACE_ID_HEADER",
    "ORGANIZATION_ID_HEADER",
    "PROJECT_ID_HEADER",
    "USER_ID_HEADER",
    "get_active_user_id",
    "get_request_context",
    "get_uow",
]
