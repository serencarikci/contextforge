"""Integration tests for Alembic migrations."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _alembic_config() -> Config:
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    return config


@pytest.mark.integration
def test_alembic_upgrade_head() -> None:
    config = _alembic_config()
    command.upgrade(config, "head")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_system_metadata_table_exists(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text(
            "SELECT EXISTS ("
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'system_metadata'"
            ")"
        )
    )
    exists = result.scalar_one()
    assert exists is True
