"""SQLAlchemy repository for retention policies and runs."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ColumnElement, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.admin.domain.entities.retention import RetentionPolicy, RetentionRun
from contextforge.modules.admin.domain.enums import RetentionResourceType, RetentionRunStatus
from contextforge.modules.admin.infrastructure.models.retention import (
    RetentionPolicyModel,
    RetentionRunModel,
)


class SqlAlchemyRetentionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_policy(self, policy_id: UUID) -> RetentionPolicy | None:
        result = await self._session.execute(
            select(RetentionPolicyModel).where(RetentionPolicyModel.id == policy_id)
        )
        model = result.scalar_one_or_none()
        return None if model is None else self._policy_to_entity(model)

    async def list_policies(
        self, organization_id: UUID, *, include_global: bool = True
    ) -> list[RetentionPolicy]:
        if include_global:
            condition = or_(
                RetentionPolicyModel.organization_id.is_(None),
                RetentionPolicyModel.organization_id == organization_id,
            )
        else:
            condition = RetentionPolicyModel.organization_id == organization_id
        result = await self._session.execute(
            select(RetentionPolicyModel)
            .where(condition)
            .order_by(RetentionPolicyModel.resource_type.asc())
        )
        return [self._policy_to_entity(m) for m in result.scalars().all()]

    async def list_enabled(self, organization_id: UUID | None = None) -> list[RetentionPolicy]:
        conditions: list[ColumnElement[bool]] = [RetentionPolicyModel.enabled.is_(True)]
        if organization_id is None:
            conditions.append(RetentionPolicyModel.organization_id.is_(None))
        else:
            conditions.append(
                or_(
                    RetentionPolicyModel.organization_id.is_(None),
                    RetentionPolicyModel.organization_id == organization_id,
                )
            )
        result = await self._session.execute(select(RetentionPolicyModel).where(and_(*conditions)))
        return [self._policy_to_entity(m) for m in result.scalars().all()]

    async def add_policy(self, entity: RetentionPolicy) -> RetentionPolicy:
        model = RetentionPolicyModel(
            id=entity.id,
            organization_id=entity.organization_id,
            resource_type=entity.resource_type.value,
            retention_days=entity.retention_days,
            soft_delete_first=entity.soft_delete_first,
            enabled=entity.enabled,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._policy_to_entity(model)

    async def update_policy(self, entity: RetentionPolicy) -> RetentionPolicy:
        result = await self._session.execute(
            select(RetentionPolicyModel).where(RetentionPolicyModel.id == entity.id)
        )
        model = result.scalar_one()
        model.retention_days = entity.retention_days
        model.soft_delete_first = entity.soft_delete_first
        model.enabled = entity.enabled
        model.updated_at = entity.updated_at
        await self._session.flush()
        return self._policy_to_entity(model)

    async def delete_policy(self, policy_id: UUID) -> bool:
        result = await self._session.execute(
            select(RetentionPolicyModel).where(RetentionPolicyModel.id == policy_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    async def add_run(self, entity: RetentionRun) -> RetentionRun:
        model = RetentionRunModel(
            id=entity.id,
            policy_id=entity.policy_id,
            organization_id=entity.organization_id,
            status=entity.status.value,
            started_at=entity.started_at,
            finished_at=entity.finished_at,
            deleted_count=entity.deleted_count,
            summary=dict(entity.summary),
            created_at=entity.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._run_to_entity(model)

    async def update_run(self, entity: RetentionRun) -> RetentionRun:
        result = await self._session.execute(
            select(RetentionRunModel).where(RetentionRunModel.id == entity.id)
        )
        model = result.scalar_one()
        model.status = entity.status.value
        model.finished_at = entity.finished_at
        model.deleted_count = entity.deleted_count
        model.summary = dict(entity.summary)
        await self._session.flush()
        return self._run_to_entity(model)

    async def list_runs(self, organization_id: UUID, *, limit: int = 50) -> list[RetentionRun]:
        result = await self._session.execute(
            select(RetentionRunModel)
            .where(
                or_(
                    RetentionRunModel.organization_id == organization_id,
                    RetentionRunModel.organization_id.is_(None),
                )
            )
            .order_by(RetentionRunModel.started_at.desc())
            .limit(limit)
        )
        return [self._run_to_entity(m) for m in result.scalars().all()]

    @staticmethod
    def _policy_to_entity(model: RetentionPolicyModel) -> RetentionPolicy:
        return RetentionPolicy(
            resource_type=RetentionResourceType(model.resource_type),
            retention_days=model.retention_days,
            id=model.id,
            organization_id=model.organization_id,
            soft_delete_first=model.soft_delete_first,
            enabled=model.enabled,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _run_to_entity(model: RetentionRunModel) -> RetentionRun:
        return RetentionRun(
            policy_id=model.policy_id,
            id=model.id,
            organization_id=model.organization_id,
            status=RetentionRunStatus(model.status),
            started_at=model.started_at,
            finished_at=model.finished_at,
            deleted_count=model.deleted_count,
            summary=dict(model.summary or {}),
            created_at=model.created_at,
        )
