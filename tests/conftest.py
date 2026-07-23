"""Shared pytest fixtures."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from contextforge.infrastructure.database.session import DatabaseManager
    from contextforge.shared.config.settings import Settings

os.environ.setdefault("CONTEXTFORGE_APP__ENVIRONMENT", "test")
os.environ.setdefault("CONTEXTFORGE_LOGGING__LEVEL", "WARNING")
os.environ.setdefault("CONTEXTFORGE_LOGGING__FORMAT", "console")
os.environ.setdefault("CONTEXTFORGE_SECURITY__SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("CONTEXTFORGE_API__DOCS_ENABLED", "true")
os.environ.setdefault("CONTEXTFORGE_INGESTION__RETRY_BACKOFF_SECONDS", "0.01")
os.environ.setdefault("CONTEXTFORGE_INGESTION__WORKER_IDLE_SLEEP_SECONDS", "0.01")
os.environ.setdefault("CONTEXTFORGE_INGESTION__POLL_TIMEOUT_SECONDS", "1")


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    from contextforge.shared.config.settings import clear_settings_cache

    clear_settings_cache()
    yield
    clear_settings_cache()


@pytest.fixture(scope="session")
def integration_settings() -> Settings:
    from contextforge.shared.config.settings import Settings, clear_settings_cache

    os.environ.setdefault("CONTEXTFORGE_APP__ENVIRONMENT", "test")
    os.environ.setdefault("CONTEXTFORGE_POSTGRES__HOST", "localhost")
    os.environ.setdefault("CONTEXTFORGE_POSTGRES__PORT", "5432")
    os.environ.setdefault("CONTEXTFORGE_POSTGRES__USER", "contextforge")
    os.environ.setdefault("CONTEXTFORGE_POSTGRES__PASSWORD", "contextforge_dev_password")
    os.environ.setdefault("CONTEXTFORGE_POSTGRES__DATABASE", "contextforge")
    os.environ.setdefault("CONTEXTFORGE_REDIS__URL", "redis://localhost:6379/0")
    os.environ.setdefault("CONTEXTFORGE_QDRANT__URL", "http://localhost:6333")
    os.environ.setdefault("CONTEXTFORGE_MINIO__ENDPOINT", "localhost:9000")
    os.environ.setdefault("CONTEXTFORGE_MINIO__ACCESS_KEY", "contextforge_minio")
    os.environ.setdefault("CONTEXTFORGE_MINIO__SECRET_KEY", "contextforge_minio_secret")
    os.environ.setdefault("CONTEXTFORGE_MINIO__BUCKET", "contextforge-documents")
    os.environ.setdefault("CONTEXTFORGE_MINIO__SECURE", "false")
    clear_settings_cache()
    return Settings()


@pytest.fixture
def api_client(integration_settings: Settings) -> TestClient:
    from contextforge.bootstrap.app_factory import create_app
    from contextforge.shared.config.settings import clear_settings_cache

    clear_settings_cache()
    app = create_app(integration_settings)
    with TestClient(app) as client:
        yield client


@pytest_asyncio.fixture
async def db_manager(integration_settings: Settings) -> DatabaseManager:
    from contextforge.infrastructure.database.session import DatabaseManager

    manager = DatabaseManager(integration_settings.postgres)
    yield manager
    await manager.dispose()


@pytest_asyncio.fixture
async def db_session(db_manager: DatabaseManager) -> AsyncSession:
    async with db_manager.session_factory() as session:
        yield session
        await session.rollback()


USER_ID_HEADER = "X-ContextForge-User-ID"
ORGANIZATION_ID_HEADER = "X-ContextForge-Organization-ID"


@dataclass(frozen=True, slots=True)
class TenantScenario:
    """Ids for a small authorization/tenancy test fixture."""

    organization_id: UUID
    admin_user_id: UUID
    viewer_user_id: UUID
    viewer_membership_id: UUID
    customer_id: UUID
    restricted_knowledge_space_id: UUID
    other_organization_id: UUID
    other_organization_customer_id: UUID

    def admin_headers(self) -> dict[str, str]:
        return {
            USER_ID_HEADER: str(self.admin_user_id),
            ORGANIZATION_ID_HEADER: str(self.organization_id),
        }

    def viewer_headers(self) -> dict[str, str]:
        return {
            USER_ID_HEADER: str(self.viewer_user_id),
            ORGANIZATION_ID_HEADER: str(self.organization_id),
        }


@pytest_asyncio.fixture
async def tenant_scenario(
    db_manager: DatabaseManager, integration_settings: Settings
) -> TenantScenario:
    from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
    from contextforge.modules.customers.application.services.customer_service import (
        CustomerService,
    )
    from contextforge.modules.identity_access.application.services.identity_context_service import (
        build_request_context,
    )
    from contextforge.modules.identity_access.application.services.membership_service import (
        MembershipService,
    )
    from contextforge.modules.identity_access.application.services.role_service import (
        RoleService,
    )
    from contextforge.modules.identity_access.application.services.user_service import (
        UserService,
    )
    from contextforge.modules.identity_access.domain.enums import (
        KnowledgeSpaceVisibility,
        SystemRoleCode,
    )
    from contextforge.modules.knowledge_spaces.application.services.knowledge_space_service import (
        KnowledgeSpaceService,
    )
    from contextforge.modules.organizations.application.services.organization_service import (
        OrganizationService,
    )

    suffix = uuid4().hex[:12]

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    admin_user = await UserService().create(
        uow, email=f"api-admin-{suffix}@example.com", display_name="API Admin"
    )

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    organization = await OrganizationService().create(
        uow,
        name=f"API Tenant {suffix}",
        slug=f"api-tenant-{suffix}",
        creator_user_id=admin_user.id,
    )

    async with SqlAlchemyUnitOfWork(db_manager.session_factory) as uow:
        admin_ctx = await build_request_context(
            uow,
            settings=integration_settings,
            user_id=admin_user.id,
            organization_id=organization.id,
        )

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    viewer_user = await UserService().create(
        uow, email=f"api-viewer-{suffix}@example.com", display_name="API Viewer"
    )

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    viewer_membership = await MembershipService().add_member(uow, admin_ctx, user_id=viewer_user.id)

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    viewer_role = next(
        role
        for role in await RoleService().list_roles(uow, admin_ctx)
        if role.code == SystemRoleCode.VIEWER.value
    )

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    await RoleService().assign_role(
        uow, admin_ctx, membership_id=viewer_membership.id, role_id=viewer_role.id
    )

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    customer = await CustomerService().create(
        uow, admin_ctx, name="API Tenant Customer", code=f"C{suffix[:8].upper()}"
    )

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    restricted_space = await KnowledgeSpaceService().create(
        uow,
        admin_ctx,
        name="Incident Playbooks",
        slug=f"incident-playbooks-{suffix}",
        visibility=KnowledgeSpaceVisibility.RESTRICTED,
    )

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    other_admin_user = await UserService().create(
        uow, email=f"api-other-admin-{suffix}@example.com", display_name="Other Org Admin"
    )

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    other_organization = await OrganizationService().create(
        uow,
        name=f"Other API Tenant {suffix}",
        slug=f"other-api-tenant-{suffix}",
        creator_user_id=other_admin_user.id,
    )

    async with SqlAlchemyUnitOfWork(db_manager.session_factory) as uow:
        other_admin_ctx = await build_request_context(
            uow,
            settings=integration_settings,
            user_id=other_admin_user.id,
            organization_id=other_organization.id,
        )

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    other_customer = await CustomerService().create(
        uow, other_admin_ctx, name="Other Tenant Customer", code=f"O{suffix[:8].upper()}"
    )

    return TenantScenario(
        organization_id=organization.id,
        admin_user_id=admin_user.id,
        viewer_user_id=viewer_user.id,
        viewer_membership_id=viewer_membership.id,
        customer_id=customer.id,
        restricted_knowledge_space_id=restricted_space.id,
        other_organization_id=other_organization.id,
        other_organization_customer_id=other_customer.id,
    )
