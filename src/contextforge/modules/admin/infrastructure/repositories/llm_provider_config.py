from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.admin.domain.entities.llm_provider_config import LlmProviderConfig
from contextforge.modules.admin.domain.enums import LlmProviderKind
from contextforge.modules.admin.infrastructure.models.llm_provider_config import (
    LlmProviderConfigModel,
)


class SqlAlchemyLlmProviderConfigRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, config_id: UUID) -> LlmProviderConfig | None:
        result = await self._session.execute(
            select(LlmProviderConfigModel).where(LlmProviderConfigModel.id == config_id)
        )
        model = result.scalar_one_or_none()
        return None if model is None else self._to_entity(model)

    async def list_for_organization(
        self, organization_id: UUID, *, include_global: bool = True
    ) -> list[LlmProviderConfig]:
        if include_global:
            condition = or_(
                LlmProviderConfigModel.organization_id.is_(None),
                LlmProviderConfigModel.organization_id == organization_id,
            )
        else:
            condition = LlmProviderConfigModel.organization_id == organization_id
        result = await self._session.execute(
            select(LlmProviderConfigModel)
            .where(condition)
            .order_by(LlmProviderConfigModel.provider.asc(), LlmProviderConfigModel.model.asc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def add(self, entity: LlmProviderConfig) -> LlmProviderConfig:
        model = LlmProviderConfigModel(
            id=entity.id,
            organization_id=entity.organization_id,
            provider=entity.provider.value,
            model=entity.model,
            base_url=entity.base_url,
            api_key_ciphertext=entity.api_key_ciphertext,
            api_key_hint=entity.api_key_hint,
            temperature=entity.temperature,
            max_tokens=entity.max_tokens,
            timeout_seconds=entity.timeout_seconds,
            max_retries=entity.max_retries,
            rate_limit_rpm=entity.rate_limit_rpm,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, entity: LlmProviderConfig) -> LlmProviderConfig:
        result = await self._session.execute(
            select(LlmProviderConfigModel).where(LlmProviderConfigModel.id == entity.id)
        )
        model = result.scalar_one()
        model.model = entity.model
        model.base_url = entity.base_url
        model.api_key_ciphertext = entity.api_key_ciphertext
        model.api_key_hint = entity.api_key_hint
        model.temperature = entity.temperature
        model.max_tokens = entity.max_tokens
        model.timeout_seconds = entity.timeout_seconds
        model.max_retries = entity.max_retries
        model.rate_limit_rpm = entity.rate_limit_rpm
        model.is_active = entity.is_active
        model.updated_at = entity.updated_at
        await self._session.flush()
        return self._to_entity(model)

    async def delete(self, config_id: UUID) -> bool:
        result = await self._session.execute(
            select(LlmProviderConfigModel).where(LlmProviderConfigModel.id == config_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    @staticmethod
    def _to_entity(model: LlmProviderConfigModel) -> LlmProviderConfig:
        return LlmProviderConfig(
            provider=LlmProviderKind(model.provider),
            model=model.model,
            id=model.id,
            organization_id=model.organization_id,
            base_url=model.base_url,
            api_key_ciphertext=model.api_key_ciphertext,
            api_key_hint=model.api_key_hint,
            temperature=model.temperature,
            max_tokens=model.max_tokens,
            timeout_seconds=model.timeout_seconds,
            max_retries=model.max_retries,
            rate_limit_rpm=model.rate_limit_rpm,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
