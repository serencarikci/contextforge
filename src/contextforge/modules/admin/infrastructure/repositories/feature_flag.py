"""SQLAlchemy repository for feature flags."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.admin.domain.entities.feature_flag import FeatureFlag
from contextforge.modules.admin.infrastructure.models.feature_flag import FeatureFlagModel


class SqlAlchemyFeatureFlagRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, flag_id: UUID) -> FeatureFlag | None:
        result = await self._session.execute(
            select(FeatureFlagModel).where(FeatureFlagModel.id == flag_id)
        )
        model = result.scalar_one_or_none()
        return None if model is None else self._to_entity(model)

    async def get_by_key(self, key: str, *, organization_id: UUID | None) -> FeatureFlag | None:
        conditions = [FeatureFlagModel.key == key]
        if organization_id is None:
            conditions.append(FeatureFlagModel.organization_id.is_(None))
        else:
            conditions.append(FeatureFlagModel.organization_id == organization_id)
        result = await self._session.execute(select(FeatureFlagModel).where(and_(*conditions)))
        model = result.scalar_one_or_none()
        return None if model is None else self._to_entity(model)

    async def list_global(self) -> list[FeatureFlag]:
        result = await self._session.execute(
            select(FeatureFlagModel)
            .where(FeatureFlagModel.organization_id.is_(None))
            .order_by(FeatureFlagModel.key.asc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_for_organization(self, organization_id: UUID) -> list[FeatureFlag]:
        result = await self._session.execute(
            select(FeatureFlagModel)
            .where(FeatureFlagModel.organization_id == organization_id)
            .order_by(FeatureFlagModel.key.asc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_visible(self, organization_id: UUID) -> list[FeatureFlag]:
        result = await self._session.execute(
            select(FeatureFlagModel)
            .where(
                or_(
                    FeatureFlagModel.organization_id.is_(None),
                    FeatureFlagModel.organization_id == organization_id,
                )
            )
            .order_by(FeatureFlagModel.key.asc(), FeatureFlagModel.organization_id.asc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def add(self, entity: FeatureFlag) -> FeatureFlag:
        model = FeatureFlagModel(
            id=entity.id,
            key=entity.key,
            description=entity.description,
            enabled_globally=entity.enabled_globally,
            organization_id=entity.organization_id,
            value=dict(entity.value),
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, entity: FeatureFlag) -> FeatureFlag:
        result = await self._session.execute(
            select(FeatureFlagModel).where(FeatureFlagModel.id == entity.id)
        )
        model = result.scalar_one()
        model.description = entity.description
        model.enabled_globally = entity.enabled_globally
        model.value = dict(entity.value)
        model.updated_at = entity.updated_at
        await self._session.flush()
        return self._to_entity(model)

    async def delete(self, flag_id: UUID) -> bool:
        result = await self._session.execute(
            select(FeatureFlagModel).where(FeatureFlagModel.id == flag_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    @staticmethod
    def _to_entity(model: FeatureFlagModel) -> FeatureFlag:
        return FeatureFlag(
            key=model.key,
            id=model.id,
            organization_id=model.organization_id,
            description=model.description,
            enabled_globally=model.enabled_globally,
            value=dict(model.value or {}),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
