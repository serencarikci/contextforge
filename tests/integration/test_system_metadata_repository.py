"""Integration tests for SystemMetadata persistence."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.domain.entities.system_metadata import SystemMetadata
from contextforge.infrastructure.repositories.system_metadata import (
    SqlAlchemySystemMetadataRepository,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_system_metadata_upsert_and_get(db_session: AsyncSession) -> None:
    repo = SqlAlchemySystemMetadataRepository(db_session)
    key = f"test.meta.{uuid4()}"
    entity = SystemMetadata(key=key, value={"enabled": True, "count": 1})

    saved = await repo.upsert(entity)
    await db_session.commit()

    loaded = await repo.get_by_key(key)
    assert loaded is not None
    assert loaded.key == key
    assert loaded.value == {"enabled": True, "count": 1}
    assert loaded.id == saved.id

    saved.update_value({"enabled": False, "count": 2})
    updated = await repo.upsert(saved)
    await db_session.commit()

    reloaded = await repo.get_by_key(key)
    assert reloaded is not None
    assert reloaded.value == {"enabled": False, "count": 2}
    assert updated.key == key

    deleted = await repo.delete_by_key(key)
    await db_session.commit()
    assert deleted is True
    assert await repo.get_by_key(key) is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_system_metadata_transaction_rollback(
    db_manager: object,
) -> None:
    from contextforge.infrastructure.database.session import DatabaseManager

    assert isinstance(db_manager, DatabaseManager)
    key = f"test.rollback.{uuid4()}"

    async with db_manager.session_factory() as session:
        repo = SqlAlchemySystemMetadataRepository(session)
        await repo.upsert(SystemMetadata(key=key, value={"temp": True}))
        await session.flush()
        await session.rollback()

    async with db_manager.session_factory() as session:
        repo = SqlAlchemySystemMetadataRepository(session)
        assert await repo.get_by_key(key) is None
