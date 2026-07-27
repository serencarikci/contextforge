"""Organization-scoped user administration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.pagination import Page, PaginationParams
from contextforge.application.services.command_support import build_audit_event
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import InvalidResourceStateError, ResourceNotFoundError
from contextforge.modules.identity_access.domain.entities.user import User
from contextforge.modules.identity_access.domain.enums import UserStatus


@dataclass(frozen=True, slots=True)
class AdminUserListItem:
    id: UUID
    email: str
    display_name: str
    status: str
    preferred_language: str
    membership_id: UUID
    membership_status: str
    created_at: datetime
    updated_at: datetime


class AdminUserService:
    async def list_users(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        pagination: PaginationParams,
        *,
        q: str | None = None,
        status: UserStatus | None = None,
    ) -> Page[AdminUserListItem]:
        async with uow:
            ctx.require_permission("admin:users")
            users, total = await uow.users.list_for_organization(
                ctx.organization_id,
                limit=pagination.limit,
                offset=pagination.offset,
                search=q,
                status=status,
            )
            items: list[AdminUserListItem] = []
            for user in users:
                membership = await uow.memberships.get_by_org_and_user(ctx.organization_id, user.id)
                if membership is None:
                    continue
                items.append(
                    AdminUserListItem(
                        id=user.id,
                        email=user.email,
                        display_name=user.display_name,
                        status=user.status.value,
                        preferred_language=user.preferred_language.value,
                        membership_id=membership.id,
                        membership_status=membership.status.value,
                        created_at=user.created_at,
                        updated_at=user.updated_at,
                    )
                )
            return Page(
                items=items,
                limit=pagination.limit,
                offset=pagination.offset,
                total=total,
            )

    async def activate(self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, user_id: UUID) -> User:
        async with uow:
            ctx.require_permission("admin:users")
            membership = await uow.memberships.get_by_org_and_user(ctx.organization_id, user_id)
            if membership is None:
                raise ResourceNotFoundError("User not found.")
            user = await uow.users.get_by_id(user_id)
            if user is None:
                raise ResourceNotFoundError("User not found.")
            if user.status == UserStatus.ARCHIVED:
                raise InvalidResourceStateError("Archived users cannot be activated.")
            user.activate()
            user = await uow.users.update(user)
            await uow.audit.add(
                build_audit_event(
                    ctx,
                    action="user.activated",
                    resource_type="user",
                    resource_id=user.id,
                )
            )
            return user

    async def deactivate(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, user_id: UUID
    ) -> User:
        async with uow:
            ctx.require_permission("admin:users")
            membership = await uow.memberships.get_by_org_and_user(ctx.organization_id, user_id)
            if membership is None:
                raise ResourceNotFoundError("User not found.")
            user = await uow.users.get_by_id(user_id)
            if user is None:
                raise ResourceNotFoundError("User not found.")
            user.suspend()
            user = await uow.users.update(user)
            await uow.audit.add(
                build_audit_event(
                    ctx,
                    action="user.deactivated",
                    resource_type="user",
                    resource_id=user.id,
                )
            )
            return user


__all__ = ["AdminUserListItem", "AdminUserService"]
