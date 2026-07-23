"""API tests for customer creation authorization: org admin vs. viewer."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from tests.conftest import TenantScenario


@pytest.mark.api
def test_org_admin_can_create_customer(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.post(
        "/api/v1/customers",
        json={"name": "Brand New Customer", "code": "BRANDNEW"},
        headers=tenant_scenario.admin_headers(),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Brand New Customer"
    assert body["code"] == "BRANDNEW"
    assert body["organization_id"] == str(tenant_scenario.organization_id)
    assert body["status"] == "active"


@pytest.mark.api
def test_org_admin_can_read_customer(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.get(
        f"/api/v1/customers/{tenant_scenario.customer_id}",
        headers=tenant_scenario.admin_headers(),
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(tenant_scenario.customer_id)


@pytest.mark.api
def test_viewer_can_read_customer(api_client: TestClient, tenant_scenario: TenantScenario) -> None:
    response = api_client.get(
        f"/api/v1/customers/{tenant_scenario.customer_id}",
        headers=tenant_scenario.viewer_headers(),
    )
    assert response.status_code == 200


@pytest.mark.api
def test_viewer_cannot_create_customer(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.post(
        "/api/v1/customers",
        json={"name": "Viewer Attempt Co", "code": "VIEWERNO"},
        headers=tenant_scenario.viewer_headers(),
    )
    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.api
def test_viewer_cannot_archive_customer(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.post(
        f"/api/v1/customers/{tenant_scenario.customer_id}/archive",
        headers=tenant_scenario.viewer_headers(),
    )
    assert response.status_code == 403


@pytest.mark.api
def test_list_customers_returns_only_tenant_customers(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.get("/api/v1/customers", headers=tenant_scenario.admin_headers())
    assert response.status_code == 200
    body = response.json()
    returned_ids = {item["id"] for item in body["items"]}
    assert str(tenant_scenario.customer_id) in returned_ids
    assert str(tenant_scenario.other_organization_customer_id) not in returned_ids
