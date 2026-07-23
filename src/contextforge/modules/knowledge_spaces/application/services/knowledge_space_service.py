"""Application service for knowledge space lifecycle use cases."""

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
from contextforge.domain.exceptions.identity import DuplicateResourceError, ResourceNotFoundError
from contextforge.modules.identity_access.domain.enums import (
    KnowledgeSpaceAccessLevel,
    KnowledgeSpaceStatus,
    KnowledgeSpaceVisibility,
)
from contextforge.modules.knowledge_spaces.domain.entities.knowledge_space import (
    KnowledgeSpace,
    KnowledgeSpaceMembership,
)

_MAX_VISIBILITY_SCAN = 10_000


class KnowledgeSpaceService:
    """Use cases for creating, reading, and managing knowledge spaces."""

    async def create(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        *,
        name: str,
        slug: str,
        project_id: UUID | None = None,
        description: str | None = None,
        visibility: KnowledgeSpaceVisibility | None = None,
    ) -> KnowledgeSpace:
        async with uow:
            ctx.require_permission("knowledge_space:create")

            organization = await uow.organizations.get_by_id(ctx.organization_id)
            if organization is None:  # pragma: no cover
                raise ResourceNotFoundError("Organization not found.")
            ensure_organization_writable(organization)

            if project_id is not None:
                project = await uow.projects.get(ctx.organization_id, project_id)
                if project is None:
                    raise ResourceNotFoundError("Project not found.")
                project.ensure_active_for_knowledge_spaces()

            knowledge_space = KnowledgeSpace(
                organization_id=ctx.organization_id,
                name=name,
                slug=slug,
                project_id=project_id,
                description=description,
                visibility=visibility or KnowledgeSpaceVisibility.ORGANIZATION,
            )
            try:
                knowledge_space = await uow.knowledge_spaces.add(knowledge_space)
            except IntegrityError as exc:
                translate_integrity_error(
                    exc, message="A knowledge space with this slug already exists."
                )

            event = build_audit_event(
                ctx,
                action="knowledge_space.created",
                resource_type="knowledge_space",
                resource_id=knowledge_space.id,
                metadata={"slug": knowledge_space.slug},
            )
            await uow.audit.add(event)
            return knowledge_space

    async def get(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, knowledge_space_id: UUID
    ) -> KnowledgeSpace:
        async with uow:
            knowledge_space = await uow.knowledge_spaces.get(
                ctx.organization_id, knowledge_space_id
            )
            if knowledge_space is None:
                raise ResourceNotFoundError("Knowledge space not found.")
            ctx.require_knowledge_space_access(knowledge_space_id)
            return knowledge_space

    async def list(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        pagination: PaginationParams,
        *,
        status: KnowledgeSpaceStatus | None = None,
        project_id: UUID | None = None,
        query: str | None = None,
    ) -> Page[KnowledgeSpace]:
        async with uow:
            if ctx.is_platform_admin:
                items, total = await uow.knowledge_spaces.list(
                    ctx.organization_id,
                    limit=pagination.limit,
                    offset=pagination.offset,
                    status=status,
                    project_id=project_id,
                    query=query,
                )
                return Page(
                    items=items, limit=pagination.limit, offset=pagination.offset, total=total
                )

            all_items, _ = await uow.knowledge_spaces.list(
                ctx.organization_id,
                limit=_MAX_VISIBILITY_SCAN,
                offset=0,
                status=status,
                project_id=project_id,
                query=query,
            )
            visible = [item for item in all_items if ctx.can_access_knowledge_space(item.id)]
            total = len(visible)
            page_items = visible[pagination.offset : pagination.offset + pagination.limit]
            return Page(
                items=page_items, limit=pagination.limit, offset=pagination.offset, total=total
            )

    async def update(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        knowledge_space_id: UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        visibility: KnowledgeSpaceVisibility | None = None,
    ) -> KnowledgeSpace:
        async with uow:
            ctx.require_knowledge_space_access(knowledge_space_id)
            ctx.require_permission("knowledge_space:update")
            knowledge_space = await uow.knowledge_spaces.get(
                ctx.organization_id, knowledge_space_id
            )
            if knowledge_space is None:
                raise ResourceNotFoundError("Knowledge space not found.")

            knowledge_space.update(name=name, description=description, visibility=visibility)
            knowledge_space = await uow.knowledge_spaces.update(knowledge_space)

            event = build_audit_event(
                ctx,
                action="knowledge_space.updated",
                resource_type="knowledge_space",
                resource_id=knowledge_space.id,
            )
            await uow.audit.add(event)
            return knowledge_space

    async def archive(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, knowledge_space_id: UUID
    ) -> KnowledgeSpace:
        async with uow:
            ctx.require_knowledge_space_access(knowledge_space_id)
            ctx.require_permission("knowledge_space:archive")
            knowledge_space = await uow.knowledge_spaces.get(
                ctx.organization_id, knowledge_space_id
            )
            if knowledge_space is None:
                raise ResourceNotFoundError("Knowledge space not found.")

            knowledge_space.archive()
            knowledge_space = await uow.knowledge_spaces.update(knowledge_space)

            event = build_audit_event(
                ctx,
                action="knowledge_space.archived",
                resource_type="knowledge_space",
                resource_id=knowledge_space.id,
            )
            await uow.audit.add(event)
            return knowledge_space

    async def add_membership(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        knowledge_space_id: UUID,
        *,
        membership_id: UUID,
        access_level: KnowledgeSpaceAccessLevel,
    ) -> KnowledgeSpaceMembership:
        async with uow:
            ctx.require_knowledge_space_access(knowledge_space_id)
            ctx.require_permission("knowledge_space:manage_members")

            knowledge_space = await uow.knowledge_spaces.get(
                ctx.organization_id, knowledge_space_id
            )
            if knowledge_space is None:
                raise ResourceNotFoundError("Knowledge space not found.")

            membership = await uow.memberships.get_by_id(ctx.organization_id, membership_id)
            if membership is None:
                raise ResourceNotFoundError("Membership not found.")

            existing = await uow.knowledge_spaces.get_membership_by_org_membership(
                ctx.organization_id, knowledge_space_id, membership_id
            )
            if existing is not None:
                raise DuplicateResourceError(
                    "Membership already has access to this knowledge space."
                )

            ks_membership = KnowledgeSpaceMembership(
                organization_id=ctx.organization_id,
                knowledge_space_id=knowledge_space_id,
                membership_id=membership_id,
                access_level=access_level,
            )
            try:
                ks_membership = await uow.knowledge_spaces.add_membership(ks_membership)
            except IntegrityError as exc:
                translate_integrity_error(
                    exc, message="Membership already has access to this knowledge space."
                )

            event = build_audit_event(
                ctx,
                action="knowledge_space_membership.added",
                resource_type="knowledge_space_membership",
                resource_id=ks_membership.id,
                metadata={"membership_id": str(membership_id)},
            )
            await uow.audit.add(event)
            return ks_membership

    async def list_memberships(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        knowledge_space_id: UUID,
        pagination: PaginationParams,
    ) -> Page[KnowledgeSpaceMembership]:
        async with uow:
            ctx.require_knowledge_space_access(knowledge_space_id)
            ctx.require_permission("knowledge_space:read")

            items, total = await uow.knowledge_spaces.list_memberships(
                ctx.organization_id,
                knowledge_space_id,
                limit=pagination.limit,
                offset=pagination.offset,
            )
            return Page(items=items, limit=pagination.limit, offset=pagination.offset, total=total)

    async def update_membership(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        knowledge_space_id: UUID,
        ks_membership_id: UUID,
        *,
        access_level: KnowledgeSpaceAccessLevel,
    ) -> KnowledgeSpaceMembership:
        async with uow:
            ctx.require_knowledge_space_access(knowledge_space_id)
            ctx.require_permission("knowledge_space:manage_members")

            ks_membership = await uow.knowledge_spaces.get_membership(
                ctx.organization_id, knowledge_space_id, ks_membership_id
            )
            if ks_membership is None:
                raise ResourceNotFoundError("Knowledge space membership not found.")

            ks_membership.update_access_level(access_level)
            ks_membership = await uow.knowledge_spaces.update_membership(ks_membership)

            event = build_audit_event(
                ctx,
                action="knowledge_space_membership.updated",
                resource_type="knowledge_space_membership",
                resource_id=ks_membership.id,
            )
            await uow.audit.add(event)
            return ks_membership

    async def remove_membership(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        knowledge_space_id: UUID,
        ks_membership_id: UUID,
    ) -> None:
        async with uow:
            ctx.require_knowledge_space_access(knowledge_space_id)
            ctx.require_permission("knowledge_space:manage_members")

            deleted = await uow.knowledge_spaces.delete_membership(
                ctx.organization_id, knowledge_space_id, ks_membership_id
            )
            if not deleted:
                raise ResourceNotFoundError("Knowledge space membership not found.")

            event = build_audit_event(
                ctx,
                action="knowledge_space_membership.removed",
                resource_type="knowledge_space_membership",
                resource_id=ks_membership_id,
            )
            await uow.audit.add(event)


__all__ = ["KnowledgeSpaceService"]
