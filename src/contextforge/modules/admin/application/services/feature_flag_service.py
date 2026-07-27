from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.services.command_support import build_audit_event
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import ResourceNotFoundError
from contextforge.modules.admin.application.ports.admin_cache import AdminCachePort
from contextforge.modules.admin.domain.entities.feature_flag import FeatureFlag, resolve_flags
from contextforge.shared.config.settings import AdminSettings


class FeatureFlagService:
    def __init__(self, cache: AdminCachePort, settings: AdminSettings) -> None:
        self._cache = cache
        self._settings = settings

    async def list_flags(self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext) -> list[FeatureFlag]:
        async with uow:
            ctx.require_permission("admin:settings")
            return await uow.feature_flags.list_visible(ctx.organization_id)

    async def resolve(self, uow: SqlAlchemyUnitOfWork, organization_id: UUID) -> dict[str, bool]:
        version = await self._cache.get_version("flags")
        cache_key = f"flags:{organization_id}:{version}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return dict(json.loads(cached))

        async with uow:
            global_flags = await uow.feature_flags.list_global()
            org_flags = await uow.feature_flags.list_for_organization(organization_id)
            settings = await uow.organization_settings.get(organization_id)
            overrides = settings.feature_overrides if settings is not None else {}
            resolved = resolve_flags(
                global_flags=global_flags,
                organization_flags=org_flags,
                settings_overrides=overrides,
            )
        await self._cache.set(
            cache_key, json.dumps(resolved), ttl_seconds=self._settings.cache_ttl_seconds
        )
        return resolved

    async def create(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        *,
        key: str,
        description: str | None = None,
        enabled: bool = False,
        value: dict[str, Any] | None = None,
        global_flag: bool = False,
    ) -> FeatureFlag:
        async with uow:
            ctx.require_permission("admin:settings")
            organization_id = None if global_flag and ctx.is_platform_admin else ctx.organization_id
            if global_flag and not ctx.is_platform_admin:
                organization_id = ctx.organization_id
            flag = FeatureFlag(
                key=key,
                organization_id=organization_id,
                description=description,
                enabled_globally=enabled,
                value=dict(value or {}),
            )
            flag = await uow.feature_flags.add(flag)
            event = build_audit_event(
                ctx,
                action="feature_flag.created",
                resource_type="feature_flag",
                resource_id=flag.id,
                metadata={"key": flag.key},
            )
            await uow.audit.add(event)
        await self._cache.bump_version("flags")
        return flag

    async def update(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        flag_id: UUID,
        *,
        description: str | None = None,
        enabled: bool | None = None,
        value: dict[str, Any] | None = None,
    ) -> FeatureFlag:
        async with uow:
            ctx.require_permission("admin:settings")
            flag = await uow.feature_flags.get(flag_id)
            if flag is None or (
                flag.organization_id is not None
                and flag.organization_id != ctx.organization_id
                and not ctx.is_platform_admin
            ):
                raise ResourceNotFoundError("Feature flag not found.")
            flag.update(description=description, enabled=enabled, value=value)
            flag = await uow.feature_flags.update(flag)
            event = build_audit_event(
                ctx,
                action="feature_flag.updated",
                resource_type="feature_flag",
                resource_id=flag.id,
            )
            await uow.audit.add(event)
        await self._cache.bump_version("flags")
        return flag

    async def delete(self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, flag_id: UUID) -> None:
        async with uow:
            ctx.require_permission("admin:settings")
            flag = await uow.feature_flags.get(flag_id)
            if flag is None or (
                flag.organization_id is not None
                and flag.organization_id != ctx.organization_id
                and not ctx.is_platform_admin
            ):
                raise ResourceNotFoundError("Feature flag not found.")
            await uow.feature_flags.delete(flag_id)
            event = build_audit_event(
                ctx,
                action="feature_flag.deleted",
                resource_type="feature_flag",
                resource_id=flag_id,
            )
            await uow.audit.add(event)
        await self._cache.bump_version("flags")
