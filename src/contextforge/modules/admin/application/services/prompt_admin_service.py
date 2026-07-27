"""Versioned prompt template administration."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.services.command_support import build_audit_event
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import InvalidResourceStateError, ResourceNotFoundError
from contextforge.modules.admin.domain.entities.prompt_template import PromptTemplate
from contextforge.modules.admin.domain.enums import PromptLanguage, PromptTemplateName


@dataclass(frozen=True, slots=True)
class PromptPreview:
    template_id: UUID
    placeholders: list[str]
    rendered: str


class PromptAdminService:
    async def list(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        *,
        language: str | None = None,
    ) -> list[PromptTemplate]:
        async with uow:
            ctx.require_permission("admin:prompts")
            return await uow.prompt_templates.list_templates(
                organization_id=ctx.organization_id, language=language
            )

    async def create(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        *,
        name: PromptTemplateName,
        version: str,
        language: PromptLanguage,
        content: str,
        activate: bool = False,
    ) -> PromptTemplate:
        async with uow:
            ctx.require_permission("admin:prompts")
            template = PromptTemplate(
                name=name,
                version=version,
                language=language,
                content=content,
                organization_id=ctx.organization_id,
                created_by=ctx.user_id,
                is_active=False,
            )
            template = await uow.prompt_templates.add(template)
            if activate:
                await uow.prompt_templates.deactivate_siblings(template)
                template.activate()
                template = await uow.prompt_templates.update(template)
            event = build_audit_event(
                ctx,
                action="prompt_template.created",
                resource_type="prompt_template",
                resource_id=template.id,
                metadata={"name": template.name.value, "version": template.version},
            )
            await uow.audit.add(event)
            return template

    async def activate(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, template_id: UUID
    ) -> PromptTemplate:
        async with uow:
            ctx.require_permission("admin:prompts")
            template = await self._get_owned(uow, ctx, template_id)
            await uow.prompt_templates.deactivate_siblings(template)
            template.activate()
            template = await uow.prompt_templates.update(template)
            event = build_audit_event(
                ctx,
                action="prompt_template.activated",
                resource_type="prompt_template",
                resource_id=template.id,
            )
            await uow.audit.add(event)
            return template

    async def deactivate(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, template_id: UUID
    ) -> PromptTemplate:
        async with uow:
            ctx.require_permission("admin:prompts")
            template = await self._get_owned(uow, ctx, template_id)
            template.deactivate()
            template = await uow.prompt_templates.update(template)
            event = build_audit_event(
                ctx,
                action="prompt_template.deactivated",
                resource_type="prompt_template",
                resource_id=template.id,
            )
            await uow.audit.add(event)
            return template

    async def preview(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        template_id: UUID,
        values: dict[str, str],
    ) -> PromptPreview:
        async with uow:
            ctx.require_permission("admin:prompts")
            template = await self._get_owned(uow, ctx, template_id)
            return PromptPreview(
                template_id=template.id,
                placeholders=template.placeholders,
                rendered=template.render(values),
            )

    async def rollback(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, template_id: UUID
    ) -> PromptTemplate:
        """Activate a prior template version, deactivating its siblings."""
        return await self.activate(uow, ctx, template_id)

    async def delete(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, template_id: UUID
    ) -> None:
        async with uow:
            ctx.require_permission("admin:prompts")
            template = await self._get_owned(uow, ctx, template_id)
            if template.is_system:
                raise InvalidResourceStateError("System prompt templates cannot be deleted.")
            await uow.prompt_templates.delete(template_id)
            event = build_audit_event(
                ctx,
                action="prompt_template.deleted",
                resource_type="prompt_template",
                resource_id=template_id,
            )
            await uow.audit.add(event)

    @staticmethod
    async def _get_owned(
        uow: SqlAlchemyUnitOfWork, ctx: RequestContext, template_id: UUID
    ) -> PromptTemplate:
        template = await uow.prompt_templates.get(template_id)
        if template is None:
            raise ResourceNotFoundError("Prompt template not found.")
        if template.organization_id is None:
            if not ctx.is_platform_admin:
                raise ResourceNotFoundError("Prompt template not found.")
            return template
        if template.organization_id != ctx.organization_id:
            raise ResourceNotFoundError("Prompt template not found.")
        return template
