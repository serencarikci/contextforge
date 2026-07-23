"""SQLAlchemy implementation of the audit event repository (append-only)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.audit.domain.entities.audit_event import AuditEvent
from contextforge.modules.audit.infrastructure.models.audit_event import AuditEventModel


class SqlAlchemyAuditEventRepository:
    """Persists append-only AuditEvent records using an explicit AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entity: AuditEvent) -> AuditEvent:
        model = AuditEventModel(
            id=entity.id,
            organization_id=entity.organization_id,
            actor_user_id=entity.actor_user_id,
            action=entity.action,
            resource_type=entity.resource_type,
            resource_id=entity.resource_id,
            correlation_id=entity.correlation_id,
            metadata_=dict(entity.metadata),
            occurred_at=entity.occurred_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def list(
        self,
        organization_id: UUID,
        *,
        limit: int,
        offset: int,
        action: str | None = None,
        resource_type: str | None = None,
        actor_user_id: UUID | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> tuple[list[AuditEvent], int]:
        conditions = [AuditEventModel.organization_id == organization_id]
        if action is not None:
            conditions.append(AuditEventModel.action == action)
        if resource_type is not None:
            conditions.append(AuditEventModel.resource_type == resource_type)
        if actor_user_id is not None:
            conditions.append(AuditEventModel.actor_user_id == actor_user_id)
        if occurred_from is not None:
            conditions.append(AuditEventModel.occurred_at >= occurred_from)
        if occurred_to is not None:
            conditions.append(AuditEventModel.occurred_at <= occurred_to)

        count_statement = select(func.count()).select_from(AuditEventModel).where(and_(*conditions))
        total = (await self._session.execute(count_statement)).scalar_one()

        statement = (
            select(AuditEventModel)
            .where(and_(*conditions))
            .order_by(AuditEventModel.occurred_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(statement)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models], total

    @staticmethod
    def _to_entity(model: AuditEventModel) -> AuditEvent:
        return AuditEvent(
            action=model.action,
            resource_type=model.resource_type,
            id=model.id,
            organization_id=model.organization_id,
            actor_user_id=model.actor_user_id,
            resource_id=model.resource_id,
            correlation_id=model.correlation_id,
            metadata=dict(model.metadata_),
            occurred_at=model.occurred_at,
        )
