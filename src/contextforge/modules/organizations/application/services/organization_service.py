"""Application service for organization lifecycle use cases."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError

from contextforge.application.context.request_context import RequestContext
from contextforge.application.pagination import Page, PaginationParams
from contextforge.application.services.command_support import (
    build_audit_event,
    build_audit_event_for_actor,
    ensure_organization_writable,
    translate_integrity_error,
)
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import ResourceNotFoundError
from contextforge.modules.identity_access.domain.entities.membership import (
    OrganizationMembership,
)
from contextforge.modules.identity_access.domain.entities.rbac import RoleAssignment
from contextforge.modules.identity_access.domain.enums import SystemRoleCode
from contextforge.modules.organizations.domain.entities.organization import Organization


class OrganizationService:
    """Use cases for creating, reading, and managing organizations."""

    async def create(
        self,
        uow: SqlAlchemyUnitOfWork,
        *,
        name: str,
        slug: str,
        creator_user_id: UUID,
    ) -> Organization:
        """Create a new organization and make ``creator_user_id`` its admin.

        This is a bootstrap-like use case: it does not require an existing
        ``RequestContext`` because the creator is not yet a member of any
        organization. The creator's membership and ``organization_admin``
        role assignment are created in the same transaction as the
        organization itself.
        """
        async with uow:
            creator = await uow.users.get_by_id(creator_user_id)
            if creator is None:
                raise ResourceNotFoundError("User not found.")
            creator.ensure_active_for_assignment()

            organization = Organization(name=name, slug=slug)
            try:
                organization = await uow.organizations.add(organization)
            except IntegrityError as exc:
                translate_integrity_error(
                    exc, message="An organization with this slug already exists."
                )

            membership = OrganizationMembership(
                organization_id=organization.id,
                user_id=creator.id,
            )
            membership = await uow.memberships.add(membership)

            admin_role = await uow.rbac.get_system_role_by_code(
                SystemRoleCode.ORGANIZATION_ADMIN.value
            )
            if admin_role is None:  # pragma: no cover
                msg = "System role 'organization_admin' is not seeded."
                raise ResourceNotFoundError(msg)

            assignment = RoleAssignment(
                organization_id=organization.id,
                membership_id=membership.id,
                role_id=admin_role.id,
            )
            await uow.rbac.add_assignment(assignment)

            event = build_audit_event_for_actor(
                actor_user_id=creator.id,
                organization_id=organization.id,
                action="organization.created",
                resource_type="organization",
                resource_id=organization.id,
                metadata={"name": organization.name, "slug": organization.slug},
            )
            await uow.audit.add(event)

            return organization

    async def get(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, organization_id: UUID
    ) -> Organization:
        async with uow:
            if ctx.organization_id != organization_id:
                raise ResourceNotFoundError("Organization not found.")
            ctx.require_permission("organization:read")
            organization = await uow.organizations.get_by_id(organization_id)
            if organization is None:
                raise ResourceNotFoundError("Organization not found.")
            return organization

    async def list_for_user(
        self,
        uow: SqlAlchemyUnitOfWork,
        *,
        user_id: UUID,
        pagination: PaginationParams,
    ) -> Page[Organization]:
        async with uow:
            organizations, total = await uow.organizations.list_for_user(
                user_id, limit=pagination.limit, offset=pagination.offset
            )
            return Page(
                items=organizations,
                limit=pagination.limit,
                offset=pagination.offset,
                total=total,
            )

    async def update(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        organization_id: UUID,
        *,
        name: str | None = None,
    ) -> Organization:
        async with uow:
            if ctx.organization_id != organization_id:
                raise ResourceNotFoundError("Organization not found.")
            ctx.require_permission("organization:update")
            organization = await uow.organizations.get_by_id(organization_id)
            if organization is None:
                raise ResourceNotFoundError("Organization not found.")

            ensure_organization_writable(organization)
            if name is not None:
                organization.rename(name)

            try:
                organization = await uow.organizations.update(organization)
            except IntegrityError as exc:
                translate_integrity_error(
                    exc, message="An organization with this slug already exists."
                )

            event = build_audit_event(
                ctx,
                action="organization.updated",
                resource_type="organization",
                resource_id=organization.id,
                metadata={"name": organization.name},
            )
            await uow.audit.add(event)
            return organization

    async def suspend(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, organization_id: UUID
    ) -> Organization:
        async with uow:
            if ctx.organization_id != organization_id:
                raise ResourceNotFoundError("Organization not found.")
            ctx.require_permission("organization:update")
            organization = await uow.organizations.get_by_id(organization_id)
            if organization is None:
                raise ResourceNotFoundError("Organization not found.")

            organization.suspend()
            organization = await uow.organizations.update(organization)

            event = build_audit_event(
                ctx,
                action="organization.suspended",
                resource_type="organization",
                resource_id=organization.id,
            )
            await uow.audit.add(event)
            return organization

    async def archive(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, organization_id: UUID
    ) -> Organization:
        async with uow:
            if ctx.organization_id != organization_id:
                raise ResourceNotFoundError("Organization not found.")
            ctx.require_permission("organization:update")
            organization = await uow.organizations.get_by_id(organization_id)
            if organization is None:
                raise ResourceNotFoundError("Organization not found.")

            organization.archive()
            organization = await uow.organizations.update(organization)

            event = build_audit_event(
                ctx,
                action="organization.archived",
                resource_type="organization",
                resource_id=organization.id,
            )
            await uow.audit.add(event)
            return organization


__all__ = ["OrganizationService"]
