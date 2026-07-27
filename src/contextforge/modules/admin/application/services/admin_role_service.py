from __future__ import annotations

from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.services.command_support import build_audit_event
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import ResourceNotFoundError
from contextforge.modules.admin.domain.exceptions import (
    SystemRoleImmutableError,
    UnknownPermissionError,
)
from contextforge.modules.identity_access.domain.entities.rbac import Role


class AdminRoleService:
    async def get_permissions(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, role_id: UUID
    ) -> list[str]:
        async with uow:
            ctx.require_permission("admin:roles")
            role = await self._require_org_role(uow, ctx, role_id)
            return await uow.rbac.list_permission_codes_for_role(role.id)

    async def replace_permissions(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        role_id: UUID,
        *,
        permission_codes: list[str],
    ) -> list[str]:
        async with uow:
            ctx.require_permission("admin:roles")
            role = await self._require_org_role(uow, ctx, role_id)
            if role.is_system:
                raise SystemRoleImmutableError("System role permissions cannot be changed.")
            permissions = await uow.rbac.get_permissions_by_codes(permission_codes)
            found = {permission.code for permission in permissions}
            missing = sorted(set(permission_codes) - found)
            if missing:
                raise UnknownPermissionError(f"Unknown permissions: {', '.join(missing)}")
            await uow.rbac.replace_role_permissions(
                role.id, [permission.id for permission in permissions]
            )
            await uow.audit.add(
                build_audit_event(
                    ctx,
                    action="role.permissions_replaced",
                    resource_type="role",
                    resource_id=role.id,
                    metadata={"permission_codes": sorted(found)},
                )
            )
            return sorted(found)

    async def archive_role(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, role_id: UUID
    ) -> Role:
        async with uow:
            ctx.require_permission("admin:roles")
            role = await self._require_org_role(uow, ctx, role_id)
            if role.is_system:
                raise SystemRoleImmutableError("System roles cannot be archived.")
            role.archive()
            role = await uow.rbac.update_role(role)
            await uow.audit.add(
                build_audit_event(
                    ctx,
                    action="role.archived",
                    resource_type="role",
                    resource_id=role.id,
                )
            )
            return role

    @staticmethod
    async def _require_org_role(
        uow: SqlAlchemyUnitOfWork, ctx: RequestContext, role_id: UUID
    ) -> Role:
        role = await uow.rbac.get_role(role_id)
        if role is None or role.organization_id != ctx.organization_id:
            if role is None or (
                role.organization_id is not None and role.organization_id != ctx.organization_id
            ):
                raise ResourceNotFoundError("Role not found.")
            if role.is_system and role.organization_id is None:
                return role
            if role.organization_id != ctx.organization_id:
                raise ResourceNotFoundError("Role not found.")
        return role


__all__ = ["AdminRoleService"]
