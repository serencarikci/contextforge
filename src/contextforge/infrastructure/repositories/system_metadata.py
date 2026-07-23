"""SQLAlchemy implementation of the system metadata repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.domain.entities.system_metadata import SystemMetadata
from contextforge.infrastructure.database.models.system_metadata import SystemMetadataModel
from contextforge.shared.utilities.datetime import utc_now


class SqlAlchemySystemMetadataRepository:
    """Persists SystemMetadata using an explicit AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_key(self, key: str) -> SystemMetadata | None:
        statement = select(SystemMetadataModel).where(SystemMetadataModel.key == key)
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def upsert(self, entity: SystemMetadata) -> SystemMetadata:
        statement = select(SystemMetadataModel).where(SystemMetadataModel.key == entity.key)
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        now = utc_now()

        if model is None:
            model = SystemMetadataModel(
                id=entity.id,
                key=entity.key,
                value=entity.value,
                created_at=entity.created_at,
                updated_at=now,
            )
            self._session.add(model)
        else:
            model.value = entity.value
            model.updated_at = now

        await self._session.flush()
        return self._to_entity(model)

    async def delete_by_key(self, key: str) -> bool:
        statement = select(SystemMetadataModel).where(SystemMetadataModel.key == key)
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    @staticmethod
    def _to_entity(model: SystemMetadataModel) -> SystemMetadata:
        return SystemMetadata(
            id=model.id,
            key=model.key,
            value=dict(model.value),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
