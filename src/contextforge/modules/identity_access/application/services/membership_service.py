"""Application service for organization membership lifecycle use cases."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError

from contextforge.application.context.request_context import RequestContext
from contextforge.application.pagination import Page, PaginationParams
from contextforge.application.services.command_support import (
    build_audit_event,
    ensure_organization_writable,
    translate_integrity_error,
)
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import (
    DuplicateResourceError,
    ResourceNotFoundError,
)
from contextforge.modules.identity_access.domain.entities.membership import (
    OrganizationMembership,
)
from contextforge.modules.identity_access.domain.enums import MembershipStatus


class MembershipService:
    """Use cases for adding, viewing, and managing organization memberships."""

    async def add_member(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, *, user_id: UUID
    ) -> OrganizationMembership:
        async with uow:
            ctx.require_permission("organization:manage_members")

            organization = await uow.organizations.get_by_id(ctx.organization_id)
            if organization is None:  # pragma: no cover - defensive
                raise ResourceNotFoundError("Organization not found.")
            ensure_organization_writable(organization)
            organization.ensure_accepts_memberships()

            user = await uow.users.get_by_id(user_id)
            if user is None:
                raise ResourceNotFoundError("User not found.")
            user.ensure_active_for_assignment()

            existing = await uow.memberships.get_by_org_and_user(ctx.organization_id, user_id)
            if existing is not None:
                raise DuplicateResourceError("User is already a member of this organization.")

            membership = OrganizationMembership(
                organization_id=ctx.organization_id,
                user_id=user_id,
            )
            try:
                membership = await uow.memberships.add(membership)
            except IntegrityError as exc:
                translate_integrity_error(
                    exc, message="User is already a member of this organization."
                )

            event = build_audit_event(
                ctx,
                action="membership.added",
                resource_type="organization_membership",
                resource_id=membership.id,
                metadata={"user_id": str(user_id)},
            )
            await uow.audit.add(event)
            return membership

    async def get(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, membership_id: UUID
    ) -> OrganizationMembership:
        async with uow:
            ctx.require_permission("user:read")
            membership = await uow.memberships.get_by_id(ctx.organization_id, membership_id)
            if membership is None:
                raise ResourceNotFoundError("Membership not found.")
            return membership

    async def list(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        pagination: PaginationParams,
        *,
        status: MembershipStatus | None = None,
        query: str | None = None,
    ) -> Page[OrganizationMembership]:
        async with uow:
            ctx.require_permission("user:read")
            memberships, total = await uow.memberships.list_for_organization(
                ctx.organization_id,
                limit=pagination.limit,
                offset=pagination.offset,
                status=status,
                query=query,
            )
            return Page(
                items=memberships,
                limit=pagination.limit,
                offset=pagination.offset,
                total=total,
            )

    async def suspend(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, membership_id: UUID
    ) -> OrganizationMembership:
        async with uow:
            ctx.require_permission("organization:manage_members")
            membership = await uow.memberships.get_by_id(ctx.organization_id, membership_id)
            if membership is None:
                raise ResourceNotFoundError("Membership not found.")

            membership.suspend()
            membership = await uow.memberships.update(membership)

            event = build_audit_event(
                ctx,
                action="membership.suspended",
                resource_type="organization_membership",
                resource_id=membership.id,
            )
            await uow.audit.add(event)
            return membership

    async def remove(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, membership_id: UUID
    ) -> OrganizationMembership:
        async with uow:
            ctx.require_permission("organization:manage_members")
            membership = await uow.memberships.get_by_id(ctx.organization_id, membership_id)
            if membership is None:
                raise ResourceNotFoundError("Membership not found.")

            membership.remove()
            membership = await uow.memberships.update(membership)

            event = build_audit_event(
                ctx,
                action="membership.removed",
                resource_type="organization_membership",
                resource_id=membership.id,
            )
            await uow.audit.add(event)
            return membership


__all__ = ["MembershipService"]
