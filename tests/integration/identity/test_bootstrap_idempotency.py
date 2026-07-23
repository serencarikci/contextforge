"""Integration tests that `scripts/bootstrap_dev.bootstrap` is safe to re-run.

Running the bootstrap function twice against the same database must:

* return the exact same deterministic ids both times
* not create duplicate rows (unique constraints would otherwise raise)
* not fail with an integrity error the second time around
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import text

from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.infrastructure.database.session import DatabaseManager
from contextforge.infrastructure.object_storage.minio_client import MinioClient
from contextforge.shared.config.settings import Settings

_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import bootstrap_dev  # noqa: E402


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bootstrap_dev_is_idempotent(
    db_manager: DatabaseManager, integration_settings: Settings
) -> None:
    minio = MinioClient(integration_settings.minio)
    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    first = await bootstrap_dev.bootstrap(uow, minio)

    uow_again = SqlAlchemyUnitOfWork(db_manager.session_factory)
    second = await bootstrap_dev.bootstrap(uow_again, minio)

    assert first == second

    async with db_manager.session_factory() as session:
        user_count = (
            await session.execute(
                text("SELECT COUNT(*) FROM users WHERE email = :email"),
                {"email": bootstrap_dev.ADMIN_EMAIL},
            )
        ).scalar_one()
        assert user_count == 1

        org_count = (
            await session.execute(
                text("SELECT COUNT(*) FROM organizations WHERE slug = :slug"),
                {"slug": bootstrap_dev.ORG_SLUG},
            )
        ).scalar_one()
        assert org_count == 1

        assignment_count = (
            await session.execute(
                text(
                    "SELECT COUNT(*) FROM role_assignments "
                    "WHERE organization_id = :org_id AND membership_id = :membership_id"
                ),
                {
                    "org_id": first.organization_id,
                    "membership_id": first.admin_membership_id,
                },
            )
        ).scalar_one()
        assert assignment_count == 1

        ks_membership_count = (
            await session.execute(
                text(
                    "SELECT COUNT(*) FROM knowledge_space_memberships "
                    "WHERE knowledge_space_id = :ks_id AND membership_id = :membership_id"
                ),
                {
                    "ks_id": first.restricted_knowledge_space_id,
                    "membership_id": first.developer_membership_id,
                },
            )
        ).scalar_one()
        assert ks_membership_count == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bootstrap_dev_admin_has_organization_admin_role(
    db_manager: DatabaseManager, integration_settings: Settings
) -> None:
    minio = MinioClient(integration_settings.minio)
    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    result = await bootstrap_dev.bootstrap(uow, minio)

    async with db_manager.session_factory() as session:
        role_code = (
            await session.execute(
                text(
                    "SELECT r.code FROM role_assignments ra "
                    "JOIN roles r ON r.id = ra.role_id "
                    "WHERE ra.membership_id = :membership_id"
                ),
                {"membership_id": result.admin_membership_id},
            )
        ).scalar_one()
        assert role_code == "organization_admin"
