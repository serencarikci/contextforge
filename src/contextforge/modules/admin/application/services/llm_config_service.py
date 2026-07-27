"""LLM provider configuration administration with masked secrets."""

from __future__ import annotations

from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.services.command_support import build_audit_event
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import ResourceNotFoundError
from contextforge.modules.admin.application.ports.llm_connectivity import (
    LlmConnectivityCheckPort,
    LlmConnectivityResult,
)
from contextforge.modules.admin.application.ports.secret_cipher import SecretCipherPort
from contextforge.modules.admin.domain.entities.llm_provider_config import (
    LlmProviderConfig,
    mask_api_key,
)
from contextforge.modules.admin.domain.enums import LlmProviderKind
from contextforge.shared.config.settings import AdminSettings


class LlmConfigService:
    def __init__(
        self,
        cipher: SecretCipherPort,
        connectivity: LlmConnectivityCheckPort,
        settings: AdminSettings,
    ) -> None:
        self._cipher = cipher
        self._connectivity = connectivity
        self._settings = settings

    async def list(self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext) -> list[LlmProviderConfig]:
        async with uow:
            ctx.require_permission("admin:llm")
            return await uow.llm_provider_configs.list_for_organization(ctx.organization_id)

    async def create(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        *,
        provider: LlmProviderKind,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
        rate_limit_rpm: int | None = None,
        is_active: bool = True,
    ) -> LlmProviderConfig:
        async with uow:
            ctx.require_permission("admin:llm")
            ciphertext = self._cipher.encrypt(api_key) if api_key else None
            hint = mask_api_key(api_key)
            config = LlmProviderConfig(
                provider=provider,
                model=model,
                organization_id=ctx.organization_id,
                base_url=base_url,
                api_key_ciphertext=ciphertext,
                api_key_hint=hint,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                rate_limit_rpm=rate_limit_rpm,
                is_active=is_active,
            )
            config = await uow.llm_provider_configs.add(config)
            event = build_audit_event(
                ctx,
                action="llm_provider_config.created",
                resource_type="llm_provider_config",
                resource_id=config.id,
                metadata={"provider": config.provider.value, "model": config.model},
            )
            await uow.audit.add(event)
            return config

    async def update(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        config_id: UUID,
        *,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        clear_api_key: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        rate_limit_rpm: int | None = None,
        is_active: bool | None = None,
    ) -> LlmProviderConfig:
        async with uow:
            ctx.require_permission("admin:llm")
            config = await self._get_owned(uow, ctx, config_id)
            config.update(
                model=model,
                base_url=base_url,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                rate_limit_rpm=rate_limit_rpm,
            )
            if clear_api_key:
                config.set_api_key(ciphertext=None, hint=None)
            elif api_key is not None:
                config.set_api_key(
                    ciphertext=self._cipher.encrypt(api_key), hint=mask_api_key(api_key)
                )
            if is_active is not None:
                config.set_active(is_active)
            config = await uow.llm_provider_configs.update(config)
            event = build_audit_event(
                ctx,
                action="llm_provider_config.updated",
                resource_type="llm_provider_config",
                resource_id=config.id,
            )
            await uow.audit.add(event)
            return config

    async def delete(self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, config_id: UUID) -> None:
        async with uow:
            ctx.require_permission("admin:llm")
            await self._get_owned(uow, ctx, config_id)
            await uow.llm_provider_configs.delete(config_id)
            event = build_audit_event(
                ctx,
                action="llm_provider_config.deleted",
                resource_type="llm_provider_config",
                resource_id=config_id,
            )
            await uow.audit.add(event)

    async def test_connectivity(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, config_id: UUID
    ) -> LlmConnectivityResult:
        async with uow:
            ctx.require_permission("admin:llm")
            config = await self._get_owned(uow, ctx, config_id)
            api_key = None
            if config.api_key_ciphertext:
                api_key = self._cipher.decrypt(config.api_key_ciphertext)
        return await self._connectivity.check(
            config,
            api_key=api_key,
            timeout_seconds=self._settings.llm_test_timeout_seconds,
        )

    @staticmethod
    async def _get_owned(
        uow: SqlAlchemyUnitOfWork, ctx: RequestContext, config_id: UUID
    ) -> LlmProviderConfig:
        config = await uow.llm_provider_configs.get(config_id)
        if config is None:
            raise ResourceNotFoundError("LLM provider config not found.")
        if config.organization_id is None:
            if not ctx.is_platform_admin:
                raise ResourceNotFoundError("LLM provider config not found.")
            return config
        if config.organization_id != ctx.organization_id:
            raise ResourceNotFoundError("LLM provider config not found.")
        return config
