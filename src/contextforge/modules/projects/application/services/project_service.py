"""Application service for project lifecycle use cases."""

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
from contextforge.domain.exceptions.identity import ResourceNotFoundError
from contextforge.modules.identity_access.application.policies.authorization import (
    require_project_access,
)
from contextforge.modules.identity_access.domain.enums import PreferredLanguage, ProjectStatus
from contextforge.modules.projects.domain.entities.project import Project


class ProjectService:
    """Use cases for creating, reading, and managing projects."""

    async def create(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        *,
        name: str,
        key: str,
        customer_id: UUID | None = None,
        description: str | None = None,
        default_language: PreferredLanguage | None = None,
    ) -> Project:
        async with uow:
            ctx.require_permission("project:create")

            organization = await uow.organizations.get_by_id(ctx.organization_id)
            if organization is None:  # pragma: no cover - defensive
                raise ResourceNotFoundError("Organization not found.")
            ensure_organization_writable(organization)

            if customer_id is not None:
                customer = await uow.customers.get(ctx.organization_id, customer_id)
                if customer is None:
                    raise ResourceNotFoundError("Customer not found.")
                customer.ensure_active_for_projects()

            project = Project(
                organization_id=ctx.organization_id,
                name=name,
                key=key,
                customer_id=customer_id,
                description=description,
                default_language=default_language or PreferredLanguage.EN,
            )
            try:
                project = await uow.projects.add(project)
            except IntegrityError as exc:
                translate_integrity_error(exc, message="A project with this key already exists.")

            event = build_audit_event(
                ctx,
                action="project.created",
                resource_type="project",
                resource_id=project.id,
                metadata={"key": project.key},
            )
            await uow.audit.add(event)
            return project

    async def get(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, project_id: UUID
    ) -> Project:
        async with uow:
            require_project_access(ctx, project_id)
            project = await uow.projects.get(ctx.organization_id, project_id)
            if project is None:
                raise ResourceNotFoundError("Project not found.")
            return project

    async def list(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        pagination: PaginationParams,
        *,
        status: ProjectStatus | None = None,
        customer_id: UUID | None = None,
        query: str | None = None,
    ) -> Page[Project]:
        async with uow:
            ctx.require_permission("project:read")
            projects, total = await uow.projects.list(
                ctx.organization_id,
                limit=pagination.limit,
                offset=pagination.offset,
                status=status,
                customer_id=customer_id,
                query=query,
            )
            return Page(
                items=projects, limit=pagination.limit, offset=pagination.offset, total=total
            )

    async def update(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        project_id: UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        default_language: PreferredLanguage | None = None,
        status: ProjectStatus | None = None,
    ) -> Project:
        async with uow:
            require_project_access(ctx, project_id)
            ctx.require_permission("project:update")
            project = await uow.projects.get(ctx.organization_id, project_id)
            if project is None:
                raise ResourceNotFoundError("Project not found.")

            project.update(
                name=name,
                description=description,
                default_language=default_language,
                status=status,
            )
            project = await uow.projects.update(project)

            event = build_audit_event(
                ctx,
                action="project.updated",
                resource_type="project",
                resource_id=project.id,
            )
            await uow.audit.add(event)
            return project

    async def archive(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, project_id: UUID
    ) -> Project:
        async with uow:
            require_project_access(ctx, project_id)
            ctx.require_permission("project:archive")
            project = await uow.projects.get(ctx.organization_id, project_id)
            if project is None:
                raise ResourceNotFoundError("Project not found.")

            project.archive()
            project = await uow.projects.update(project)

            event = build_audit_event(
                ctx,
                action="project.archived",
                resource_type="project",
                resource_id=project.id,
            )
            await uow.audit.add(event)
            return project


__all__ = ["ProjectService"]
