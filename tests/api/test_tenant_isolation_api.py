from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from tests.conftest import TenantScenario


@pytest.mark.api
def test_cross_tenant_customer_access_returns_404(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.get(
        f"/api/v1/customers/{tenant_scenario.other_organization_customer_id}",
        headers=tenant_scenario.admin_headers(),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.api
def test_cross_tenant_organization_access_returns_404(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.get(
        f"/api/v1/organizations/{tenant_scenario.other_organization_id}",
        headers=tenant_scenario.admin_headers(),
    )
    assert response.status_code == 404


@pytest.mark.api
def test_nonexistent_customer_returns_404(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.get(
        f"/api/v1/customers/{uuid4()}",
        headers=tenant_scenario.admin_headers(),
    )
    assert response.status_code == 404


@pytest.mark.api
def test_own_organization_is_accessible(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.get(
        f"/api/v1/organizations/{tenant_scenario.organization_id}",
        headers=tenant_scenario.admin_headers(),
    )
    assert response.status_code == 200
