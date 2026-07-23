"""API tests for not-found/validation error branches not hit by happy paths."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from tests.conftest import TenantScenario


@pytest.mark.api
def test_update_nonexistent_project_returns_404(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.patch(
        f"/api/v1/projects/{uuid4()}",
        json={"name": "Ghost Project"},
        headers=tenant_scenario.admin_headers(),
    )
    assert response.status_code == 404


@pytest.mark.api
def test_create_project_with_nonexistent_customer_returns_404(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.post(
        "/api/v1/projects",
        json={
            "name": "Orphan Project",
            "key": f"ORPH{uuid4().hex[:4].upper()}",
            "customer_id": str(uuid4()),
        },
        headers=tenant_scenario.admin_headers(),
    )
    assert response.status_code == 404


@pytest.mark.api
def test_get_nonexistent_project_returns_404(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.get(
        f"/api/v1/projects/{uuid4()}", headers=tenant_scenario.admin_headers()
    )
    assert response.status_code == 404


@pytest.mark.api
def test_archive_nonexistent_project_returns_404(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.post(
        f"/api/v1/projects/{uuid4()}/archive", headers=tenant_scenario.admin_headers()
    )
    assert response.status_code == 404


@pytest.mark.api
def test_list_projects_by_status_filter(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    create_response = api_client.post(
        "/api/v1/projects",
        json={"name": "Filtered Project", "key": f"FILT{uuid4().hex[:4].upper()}"},
        headers=tenant_scenario.admin_headers(),
    )
    project_id = create_response.json()["id"]
    api_client.post(
        f"/api/v1/projects/{project_id}/archive", headers=tenant_scenario.admin_headers()
    )

    response = api_client.get(
        "/api/v1/projects",
        params={"status": "archived", "query": "Filtered"},
        headers=tenant_scenario.admin_headers(),
    )
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert project_id in ids


@pytest.mark.api
def test_update_nonexistent_customer_returns_404(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.patch(
        f"/api/v1/customers/{uuid4()}",
        json={"name": "Ghost Customer"},
        headers=tenant_scenario.admin_headers(),
    )
    assert response.status_code == 404


@pytest.mark.api
def test_archive_nonexistent_customer_returns_404(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.post(
        f"/api/v1/customers/{uuid4()}/archive", headers=tenant_scenario.admin_headers()
    )
    assert response.status_code == 404


@pytest.mark.api
def test_list_customers_by_status_and_query(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.get(
        "/api/v1/customers",
        params={"status": "active", "query": "API Tenant"},
        headers=tenant_scenario.admin_headers(),
    )
    assert response.status_code == 200
    assert response.json()["pagination"]["total"] >= 1


@pytest.mark.api
def test_duplicate_customer_code_returns_409(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    payload = {"name": "Duplicate Customer", "code": f"DUP{uuid4().hex[:5].upper()}"}
    first = api_client.post(
        "/api/v1/customers", json=payload, headers=tenant_scenario.admin_headers()
    )
    assert first.status_code == 201
    second = api_client.post(
        "/api/v1/customers", json=payload, headers=tenant_scenario.admin_headers()
    )
    assert second.status_code == 409


@pytest.mark.api
def test_get_nonexistent_membership_returns_404(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.get(
        f"/api/v1/memberships/{uuid4()}", headers=tenant_scenario.admin_headers()
    )
    assert response.status_code == 404


@pytest.mark.api
def test_get_nonexistent_user_returns_404(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.get(f"/api/v1/users/{uuid4()}", headers=tenant_scenario.admin_headers())
    assert response.status_code == 404


@pytest.mark.api
def test_update_role_not_found_returns_404(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.patch(
        f"/api/v1/roles/{uuid4()}",
        json={"name": "Ghost Role"},
        headers=tenant_scenario.admin_headers(),
    )
    assert response.status_code == 404


@pytest.mark.api
def test_duplicate_role_code_returns_409(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    payload = {"code": "duplicate_role_code", "name": "First"}
    first = api_client.post("/api/v1/roles", json=payload, headers=tenant_scenario.admin_headers())
    assert first.status_code == 201
    second = api_client.post("/api/v1/roles", json=payload, headers=tenant_scenario.admin_headers())
    assert second.status_code == 409


@pytest.mark.api
def test_revoke_nonexistent_role_assignment_returns_404(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.delete(
        f"/api/v1/roles/assignments/{uuid4()}", headers=tenant_scenario.admin_headers()
    )
    assert response.status_code == 404


@pytest.mark.api
def test_assign_role_with_nonexistent_membership_returns_404(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    roles_response = api_client.get("/api/v1/roles", headers=tenant_scenario.admin_headers())
    viewer_role_id = next(role["id"] for role in roles_response.json() if role["code"] == "viewer")
    response = api_client.post(
        "/api/v1/roles/assignments",
        json={"membership_id": str(uuid4()), "role_id": viewer_role_id},
        headers=tenant_scenario.admin_headers(),
    )
    assert response.status_code == 404


@pytest.mark.api
def test_update_nonexistent_knowledge_space_returns_404(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.patch(
        f"/api/v1/knowledge-spaces/{uuid4()}",
        json={"description": "Ghost"},
        headers=tenant_scenario.admin_headers(),
    )
    assert response.status_code == 404


@pytest.mark.api
def test_list_knowledge_spaces_with_visibility_and_status_filters(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.get(
        "/api/v1/knowledge-spaces",
        params={"status": "active"},
        headers=tenant_scenario.admin_headers(),
    )
    assert response.status_code == 200
