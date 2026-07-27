"""Organization settings and quotas administration."""

from __future__ import annotations

from typing import Any

from contextforge.application.context.request_context import RequestContext
from contextforge.application.services.command_support import build_audit_event
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.modules.admin.domain.entities.organization_settings import (
    OrganizationQuotas,
    OrganizationSettings,
)


class OrganizationSettingsService:
    async def get(self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext) -> OrganizationSettings:
        async with uow:
            ctx.require_permission("admin:organizations")
            return await uow.organization_settings.get_or_default(ctx.organization_id)

    async def update(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        *,
        quotas: dict[str, Any] | None = None,
        defaults: dict[str, Any] | None = None,
        feature_overrides: dict[str, Any] | None = None,
        is_active: bool | None = None,
    ) -> OrganizationSettings:
        async with uow:
            ctx.require_permission("admin:organizations")
            settings = await uow.organization_settings.get_or_default(ctx.organization_id)
            if quotas is not None:
                settings.replace_quotas(OrganizationQuotas.from_mapping(quotas))
            if defaults is not None:
                settings.merge_defaults(defaults)
            if feature_overrides is not None:
                settings.merge_feature_overrides(feature_overrides)
            if is_active is not None:
                settings.set_active(is_active)
            settings = await uow.organization_settings.upsert(settings)
            event = build_audit_event(
                ctx,
                action="organization_settings.updated",
                resource_type="organization_settings",
                resource_id=settings.organization_id,
            )
            await uow.audit.add(event)
            return settings
