"""Build RequestContext from validated identity and RBAC data."""

from __future__ import annotations

from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import (
    InvalidDevelopmentIdentityError,
    MembershipInactiveError,
    OrganizationInactiveError,
    TenantMismatchError,
    UserInactiveError,
)
from contextforge.modules.identity_access.domain.enums import (
    MembershipStatus,
    OrganizationStatus,
    UserStatus,
)
from contextforge.shared.config.settings import Environment, Settings
from contextforge.shared.logging.context import get_correlation_id
from contextforge.shared.utilities.correlation import is_valid_correlation_id


def development_identity_enabled(settings: Settings) -> bool:
    return settings.app.environment in {
        Environment.LOCAL,
        Environment.TEST,
        Environment.DEVELOPMENT,
    }


async def build_request_context(
    uow: SqlAlchemyUnitOfWork,
    *,
    settings: Settings,
    user_id: UUID,
    organization_id: UUID,
    project_id: UUID | None = None,
    knowledge_space_id: UUID | None = None,
) -> RequestContext:
    """Load and validate identity, then assemble authorization context."""
    if not development_identity_enabled(settings):
        raise InvalidDevelopmentIdentityError(
            "Development identity is disabled in this environment. "
            "Real authentication is not yet implemented.",
            code="AUTHENTICATION_REQUIRED",
        )

    user = await uow.users.get_by_id(user_id)
    if user is None:
        raise InvalidDevelopmentIdentityError(
            "User not found.", code="INVALID_DEVELOPMENT_IDENTITY"
        )
    if user.status == UserStatus.SUSPENDED:
        raise UserInactiveError("User is suspended.")
    if user.status == UserStatus.ARCHIVED:
        raise UserInactiveError("User is archived.")
    if user.status != UserStatus.ACTIVE:
        raise UserInactiveError("User is not active.")

    organization = await uow.organizations.get_by_id(organization_id)
    if organization is None:
        raise InvalidDevelopmentIdentityError(
            "Organization not found.",
            code="INVALID_DEVELOPMENT_IDENTITY",
        )
    if organization.status == OrganizationStatus.ARCHIVED:
        raise OrganizationInactiveError("Organization is archived.")

    membership = await uow.memberships.get_by_org_and_user(organization_id, user_id)
    if membership is None or membership.status == MembershipStatus.REMOVED:
        raise MembershipInactiveError("Active organization membership is required.")
    if membership.status == MembershipStatus.SUSPENDED:
        raise MembershipInactiveError("Organization membership is suspended.")
    if membership.status != MembershipStatus.ACTIVE:
        raise MembershipInactiveError("Organization membership is not active.")

    if project_id is not None:
        project = await uow.projects.get(organization_id, project_id)
        if project is None:
            raise TenantMismatchError("Project does not belong to the organization context.")

    if knowledge_space_id is not None:
        space = await uow.knowledge_spaces.get(organization_id, knowledge_space_id)
        if space is None:
            raise TenantMismatchError(
                "Knowledge space does not belong to the organization context."
            )

    org_perms = await uow.rbac.get_organization_scope_permission_codes(
        organization_id, membership.id
    )
    permissions = set(org_perms)
    if project_id is not None:
        permissions |= await uow.rbac.get_project_scope_permission_codes(
            organization_id, membership.id, project_id
        )
    if knowledge_space_id is not None:
        permissions |= await uow.rbac.get_knowledge_space_scope_permission_codes(
            organization_id, membership.id, knowledge_space_id
        )

    accessible_project_ids = await uow.rbac.list_accessible_project_ids(
        organization_id, membership.id
    )
    role_ks_ids = await uow.rbac.list_accessible_knowledge_space_ids_from_roles(
        organization_id, membership.id
    )
    membership_ks_ids = await uow.knowledge_spaces.list_accessible_ids_for_membership(
        organization_id, membership.id
    )
    org_visible = await uow.knowledge_spaces.list_organization_visible_ids(organization_id)

    correlation = get_correlation_id() or ""
    correlation_id = correlation if is_valid_correlation_id(correlation) else str(user.id)

    return RequestContext(
        correlation_id=correlation_id,
        user_id=user.id,
        organization_id=organization.id,
        organization_membership_id=membership.id,
        preferred_language=user.preferred_language,
        permissions=frozenset(permissions),
        project_id=project_id,
        knowledge_space_id=knowledge_space_id,
        is_platform_admin=user.is_platform_admin,
        accessible_project_ids=frozenset(accessible_project_ids),
        accessible_knowledge_space_ids=frozenset(role_ks_ids | membership_ks_ids),
        organization_visible_knowledge_space_ids=frozenset(org_visible),
    )
