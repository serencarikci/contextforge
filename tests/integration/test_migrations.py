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


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "table_name",
    [
        "users",
        "organizations",
        "organization_memberships",
        "permissions",
        "roles",
        "role_permissions",
        "role_assignments",
        "customers",
        "projects",
        "knowledge_spaces",
        "knowledge_space_memberships",
        "audit_events",
    ],
)
async def test_identity_and_knowledge_domain_tables_exist(
    db_session: AsyncSession, table_name: str
) -> None:
    result = await db_session.execute(
        text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = :table_name)"
        ),
        {"table_name": table_name},
    )
    assert result.scalar_one() is True, f"expected table '{table_name}' to exist"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_migration_seeds_expected_permission_count(db_session: AsyncSession) -> None:
    from contextforge.shared.constants.rbac import PERMISSIONS

    result = await db_session.execute(text("SELECT COUNT(*) FROM permissions"))
    assert result.scalar_one() == len(PERMISSIONS)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_migration_seeds_expected_system_role_count(db_session: AsyncSession) -> None:
    from contextforge.shared.constants.rbac import SYSTEM_ROLES

    result = await db_session.execute(
        text("SELECT COUNT(*) FROM roles WHERE organization_id IS NULL AND is_system = true")
    )
    assert result.scalar_one() == len(SYSTEM_ROLES)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_migration_seeds_role_permission_mappings(db_session: AsyncSession) -> None:
    from contextforge.shared.constants.rbac import ROLE_PERMISSIONS

    expected_row_count = sum(len(codes) for codes in ROLE_PERMISSIONS.values())
    result = await db_session.execute(text("SELECT COUNT(*) FROM role_permissions"))
    assert result.scalar_one() == expected_row_count


@pytest.mark.integration
@pytest.mark.asyncio
async def test_migration_seeds_permission_and_role_ids_are_deterministic(
    db_session: AsyncSession,
) -> None:
    from contextforge.modules.identity_access.domain.enums import SystemRoleCode
    from contextforge.shared.constants.rbac import system_role_id

    expected_id = system_role_id(SystemRoleCode.ORGANIZATION_ADMIN.value)
    result = await db_session.execute(
        text("SELECT id FROM roles WHERE code = :code AND organization_id IS NULL"),
        {"code": SystemRoleCode.ORGANIZATION_ADMIN.value},
    )
    assert result.scalar_one() == expected_id
