"""Application service for user lifecycle use cases."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError

from contextforge.application.context.request_context import RequestContext
from contextforge.application.services.command_support import (
    build_audit_event,
    build_audit_event_for_actor,
    translate_integrity_error,
)
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import ResourceNotFoundError
from contextforge.modules.identity_access.domain.entities.user import User
from contextforge.modules.identity_access.domain.enums import PreferredLanguage


class UserService:
    """Use cases for provisioning and managing users."""

    async def create(
        self,
        uow: SqlAlchemyUnitOfWork,
        *,
        email: str,
        display_name: str,
        preferred_language: PreferredLanguage = PreferredLanguage.EN,
        ctx: RequestContext | None = None,
    ) -> User:
        """Provision a new user.

        When ``ctx`` is provided the caller must hold ``user:manage`` (this is
        the normal API path: an organization admin provisioning a new user).
        When ``ctx`` is ``None`` this behaves as local/dev bootstrap
        provisioning with no tenant attached to the audit trail.
        """
        async with uow:
            if ctx is not None:
                ctx.require_permission("user:manage")

            user = User(
                email=email,
                display_name=display_name,
                preferred_language=preferred_language,
            )
            try:
                user = await uow.users.add(user)
            except IntegrityError as exc:
                translate_integrity_error(exc, message="A user with this email already exists.")

            if ctx is not None:
                event = build_audit_event(
                    ctx,
                    action="user.created",
                    resource_type="user",
                    resource_id=user.id,
                    metadata={"email": user.email},
                )
            else:
                event = build_audit_event_for_actor(
                    actor_user_id=None,
                    organization_id=None,
                    action="user.created",
                    resource_type="user",
                    resource_id=user.id,
                    metadata={"email": user.email},
                )
            await uow.audit.add(event)
            return user

    async def get(self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, user_id: UUID) -> User:
        async with uow:
            if user_id != ctx.user_id:
                await self._require_same_organization_membership(uow, ctx, user_id)
                ctx.require_permission("user:read")

            user = await uow.users.get_by_id(user_id)
            if user is None:
                raise ResourceNotFoundError("User not found.")
            return user

    async def update(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        user_id: UUID,
        *,
        display_name: str | None = None,
        preferred_language: PreferredLanguage | None = None,
    ) -> User:
        async with uow:
            if user_id != ctx.user_id:
                await self._require_same_organization_membership(uow, ctx, user_id)
                ctx.require_permission("user:manage")

            user = await uow.users.get_by_id(user_id)
            if user is None:
                raise ResourceNotFoundError("User not found.")

            user.update_profile(display_name=display_name, preferred_language=preferred_language)
            user = await uow.users.update(user)

            event = build_audit_event(
                ctx,
                action="user.updated",
                resource_type="user",
                resource_id=user.id,
            )
            await uow.audit.add(event)
            return user

    async def suspend(self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, user_id: UUID) -> User:
        async with uow:
            await self._require_same_organization_membership(uow, ctx, user_id)
            ctx.require_permission("user:manage")

            user = await uow.users.get_by_id(user_id)
            if user is None:
                raise ResourceNotFoundError("User not found.")

            user.suspend()
            user = await uow.users.update(user)

            event = build_audit_event(
                ctx,
                action="user.suspended",
                resource_type="user",
                resource_id=user.id,
            )
            await uow.audit.add(event)
            return user

    async def archive(self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, user_id: UUID) -> User:
        async with uow:
            await self._require_same_organization_membership(uow, ctx, user_id)
            ctx.require_permission("user:manage")

            user = await uow.users.get_by_id(user_id)
            if user is None:
                raise ResourceNotFoundError("User not found.")

            user.archive()
            user = await uow.users.update(user)

            event = build_audit_event(
                ctx,
                action="user.archived",
                resource_type="user",
                resource_id=user.id,
            )
            await uow.audit.add(event)
            return user

    @staticmethod
    async def _require_same_organization_membership(
        uow: SqlAlchemyUnitOfWork, ctx: RequestContext, user_id: UUID
    ) -> None:
        """Ensure ``user_id`` is a member of the caller's organization.

        Raised as ``ResourceNotFoundError`` so callers cannot distinguish
        "does not exist" from "exists in another organization".
        """
        membership = await uow.memberships.get_by_org_and_user(ctx.organization_id, user_id)
        if membership is None:
            raise ResourceNotFoundError("User not found.")


__all__ = ["UserService"]
