"""Application service for RBAC (roles, role assignments) use cases."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError

from contextforge.application.context.request_context import RequestContext
from contextforge.application.pagination import Page, PaginationParams
from contextforge.application.services.command_support import (
    build_audit_event,
    translate_integrity_error,
)
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import (
    AuthorizationError,
    DuplicateResourceError,
    InvalidResourceStateError,
    ResourceNotFoundError,
)
from contextforge.modules.identity_access.domain.entities.rbac import Role, RoleAssignment
from contextforge.modules.identity_access.domain.enums import SystemRoleCode


class RoleService:
    """Use cases for managing organization-scoped roles and role assignments."""

    async def list_roles(self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext) -> list[Role]:
        async with uow:
            ctx.require_permission("role:read")
            return await uow.rbac.list_roles(ctx.organization_id)

    async def create_org_role(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        *,
        code: str,
        name: str,
        description: str | None = None,
    ) -> Role:
        async with uow:
            ctx.require_permission("role:manage")

            existing = await uow.rbac.get_org_role_by_code(ctx.organization_id, code)
            if existing is not None:
                raise DuplicateResourceError("A role with this code already exists.")

            role = Role(
                code=code,
                name=name,
                organization_id=ctx.organization_id,
                description=description,
                is_system=False,
            )
            try:
                role = await uow.rbac.add_role(role)
            except IntegrityError as exc:
                translate_integrity_error(exc, message="A role with this code already exists.")

            event = build_audit_event(
                ctx,
                action="role.created",
                resource_type="role",
                resource_id=role.id,
                metadata={"code": role.code},
            )
            await uow.audit.add(event)
            return role

    async def update_org_role(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        role_id: UUID,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> Role:
        async with uow:
            ctx.require_permission("role:manage")

            role = await uow.rbac.get_role(role_id)
            if role is None or role.organization_id != ctx.organization_id:
                raise ResourceNotFoundError("Role not found.")

            role.update(name=name, description=description)
            role = await uow.rbac.update_role(role)

            event = build_audit_event(
                ctx,
                action="role.updated",
                resource_type="role",
                resource_id=role.id,
            )
            await uow.audit.add(event)
            return role

    async def assign_role(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        *,
        membership_id: UUID,
        role_id: UUID,
        project_id: UUID | None = None,
        knowledge_space_id: UUID | None = None,
    ) -> RoleAssignment:
        async with uow:
            ctx.require_permission("role:manage")

            role = await uow.rbac.get_role(role_id)
            if role is None:
                raise ResourceNotFoundError("Role not found.")
            if role.organization_id is not None and role.organization_id != ctx.organization_id:
                raise ResourceNotFoundError("Role not found.")
            if role.code == SystemRoleCode.PLATFORM_ADMIN.value:
                raise AuthorizationError("The platform_admin role cannot be assigned.")

            membership = await uow.memberships.get_by_id(ctx.organization_id, membership_id)
            if membership is None:
                raise ResourceNotFoundError("Membership not found.")

            if project_id is not None and knowledge_space_id is not None:
                raise InvalidResourceStateError(
                    "Role assignment cannot target both project and knowledge space."
                )
            if project_id is not None:
                project = await uow.projects.get(ctx.organization_id, project_id)
                if project is None:
                    raise ResourceNotFoundError("Project not found.")
            if knowledge_space_id is not None:
                knowledge_space = await uow.knowledge_spaces.get(
                    ctx.organization_id, knowledge_space_id
                )
                if knowledge_space is None:
                    raise ResourceNotFoundError("Knowledge space not found.")

            already_exists = await uow.rbac.assignment_exists(
                ctx.organization_id,
                membership_id,
                role_id,
                project_id,
                knowledge_space_id,
            )
            if already_exists:
                raise DuplicateResourceError("This role assignment already exists.")

            assignment = RoleAssignment(
                organization_id=ctx.organization_id,
                membership_id=membership_id,
                role_id=role_id,
                project_id=project_id,
                knowledge_space_id=knowledge_space_id,
            )
            try:
                assignment = await uow.rbac.add_assignment(assignment)
            except IntegrityError as exc:
                translate_integrity_error(exc, message="This role assignment already exists.")

            event = build_audit_event(
                ctx,
                action="role_assignment.created",
                resource_type="role_assignment",
                resource_id=assignment.id,
                metadata={"role_id": str(role_id), "membership_id": str(membership_id)},
            )
            await uow.audit.add(event)
            return assignment

    async def revoke_role(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, assignment_id: UUID
    ) -> None:
        async with uow:
            ctx.require_permission("role:manage")

            deleted = await uow.rbac.delete_assignment(ctx.organization_id, assignment_id)
            if not deleted:
                raise ResourceNotFoundError("Role assignment not found.")

            event = build_audit_event(
                ctx,
                action="role_assignment.revoked",
                resource_type="role_assignment",
                resource_id=assignment_id,
            )
            await uow.audit.add(event)

    async def list_assignments(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        pagination: PaginationParams,
    ) -> Page[RoleAssignment]:
        async with uow:
            ctx.require_permission("role:read")
            assignments, total = await uow.rbac.list_assignments(
                ctx.organization_id, limit=pagination.limit, offset=pagination.offset
            )
            return Page(
                items=assignments,
                limit=pagination.limit,
                offset=pagination.offset,
                total=total,
            )


__all__ = ["RoleService"]
