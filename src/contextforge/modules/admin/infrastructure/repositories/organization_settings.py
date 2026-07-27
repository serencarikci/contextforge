from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.admin.domain.entities.organization_settings import (
    OrganizationQuotas,
    OrganizationSettings,
)
from contextforge.modules.admin.infrastructure.models.organization_settings import (
    OrganizationSettingsModel,
)


class SqlAlchemyOrganizationSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, organization_id: UUID) -> OrganizationSettings | None:
        statement = select(OrganizationSettingsModel).where(
            OrganizationSettingsModel.organization_id == organization_id
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        return None if model is None else self._to_entity(model)

    async def get_or_default(self, organization_id: UUID) -> OrganizationSettings:
        existing = await self.get(organization_id)
        if existing is not None:
            return existing
        return OrganizationSettings(organization_id=organization_id)

    async def upsert(self, entity: OrganizationSettings) -> OrganizationSettings:
        statement = select(OrganizationSettingsModel).where(
            OrganizationSettingsModel.organization_id == entity.organization_id
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            model = OrganizationSettingsModel(
                organization_id=entity.organization_id,
                quotas=entity.quotas.to_mapping(),
                defaults=dict(entity.defaults),
                feature_overrides=dict(entity.feature_overrides),
                is_active=entity.is_active,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
            self._session.add(model)
        else:
            model.quotas = entity.quotas.to_mapping()
            model.defaults = dict(entity.defaults)
            model.feature_overrides = dict(entity.feature_overrides)
            model.is_active = entity.is_active
            model.updated_at = entity.updated_at
        await self._session.flush()
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: OrganizationSettingsModel) -> OrganizationSettings:
        return OrganizationSettings(
            organization_id=model.organization_id,
            quotas=OrganizationQuotas.from_mapping(dict(model.quotas or {})),
            defaults=dict(model.defaults or {}),
            feature_overrides={k: bool(v) for k, v in dict(model.feature_overrides or {}).items()},
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
