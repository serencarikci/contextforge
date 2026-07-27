from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from tests.conftest import TenantScenario

    from contextforge.infrastructure.database.session import DatabaseManager


@pytest.mark.security
def test_viewer_without_membership_cannot_read_restricted_knowledge_space(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.get(
        f"/api/v1/knowledge-spaces/{tenant_scenario.restricted_knowledge_space_id}",
        headers=tenant_scenario.viewer_headers(),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.security
def test_viewer_without_membership_does_not_see_restricted_space_in_listing(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.get("/api/v1/knowledge-spaces", headers=tenant_scenario.viewer_headers())
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert str(tenant_scenario.restricted_knowledge_space_id) not in ids


@pytest.mark.security
@pytest.mark.asyncio
async def test_restricted_knowledge_space_genuinely_exists_and_is_restricted(
    tenant_scenario: TenantScenario, db_manager: DatabaseManager
) -> None:
    from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
    from contextforge.modules.identity_access.domain.enums import KnowledgeSpaceVisibility

    async with SqlAlchemyUnitOfWork(db_manager.session_factory) as uow:
        space = await uow.knowledge_spaces.get(
            tenant_scenario.organization_id, tenant_scenario.restricted_knowledge_space_id
        )
    assert space is not None
    assert space.visibility == KnowledgeSpaceVisibility.RESTRICTED


@pytest.mark.security
def test_organization_admin_without_explicit_grant_also_gets_404(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.get(
        f"/api/v1/knowledge-spaces/{tenant_scenario.restricted_knowledge_space_id}",
        headers=tenant_scenario.admin_headers(),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.security
def test_viewer_cannot_add_themselves_to_restricted_knowledge_space(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.post(
        f"/api/v1/knowledge-spaces/{tenant_scenario.restricted_knowledge_space_id}/memberships",
        json={
            "membership_id": str(tenant_scenario.viewer_membership_id),
            "access_level": "manager",
        },
        headers=tenant_scenario.viewer_headers(),
    )
    assert response.status_code in {403, 404}


@pytest.mark.security
def test_nonexistent_knowledge_space_is_also_404_for_admin(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.get(
        f"/api/v1/knowledge-spaces/{uuid4()}",
        headers=tenant_scenario.admin_headers(),
    )
    assert response.status_code == 404
