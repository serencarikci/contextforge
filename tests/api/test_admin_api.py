"""API tests for Phase 4 administration endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from tests.conftest import TenantScenario


@pytest.mark.api
def test_admin_dashboard_requires_permission(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.get(
        "/api/v1/admin/dashboard",
        headers=tenant_scenario.viewer_headers(),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.api
def test_admin_dashboard_for_org_admin(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.get(
        "/api/v1/admin/dashboard",
        headers=tenant_scenario.admin_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    assert "membership_count" in body
    assert "document_count" in body
    assert "token_usage_today" in body


@pytest.mark.api
def test_admin_list_users(api_client: TestClient, tenant_scenario: TenantScenario) -> None:
    response = api_client.get(
        "/api/v1/admin/users",
        headers=tenant_scenario.admin_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert body["pagination"]["total"] >= 1
    ids = {item["id"] for item in body["items"]}
    assert str(tenant_scenario.admin_user_id) in ids


@pytest.mark.api
def test_organization_settings_get_and_patch(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    headers = tenant_scenario.admin_headers()
    get_response = api_client.get("/api/v1/admin/organizations/settings", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["organization_id"] == str(tenant_scenario.organization_id)

    patch_response = api_client.patch(
        "/api/v1/admin/organizations/settings",
        headers=headers,
        json={"quotas": {"max_users": 50, "max_documents": 1000}},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["quotas"]["max_users"] == 50


@pytest.mark.api
def test_feature_flags_crud_and_resolved(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    headers = tenant_scenario.admin_headers()
    create = api_client.post(
        "/api/v1/admin/feature-flags",
        headers=headers,
        json={"key": "beta.search", "enabled": True, "description": "Beta search"},
    )
    assert create.status_code == 201
    flag_id = create.json()["id"]

    resolved = api_client.get("/api/v1/admin/feature-flags/resolved", headers=headers)
    assert resolved.status_code == 200
    assert resolved.json()["flags"].get("beta.search") is True

    delete = api_client.delete(f"/api/v1/admin/feature-flags/{flag_id}", headers=headers)
    assert delete.status_code == 204


@pytest.mark.api
def test_llm_provider_masks_secrets(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    headers = tenant_scenario.admin_headers()
    create = api_client.post(
        "/api/v1/admin/llm-providers",
        headers=headers,
        json={
            "provider": "mock",
            "model": "mock-llm",
            "api_key": "sk-secret-value-1234",
            "is_active": True,
        },
    )
    assert create.status_code == 201
    body = create.json()
    assert body["api_key_set"] is True
    assert body["api_key_hint"] is not None
    assert "sk-secret-value-1234" not in body["api_key_hint"]
    assert "api_key_ciphertext" not in body
    assert "api_key" not in body

    listed = api_client.get("/api/v1/admin/llm-providers", headers=headers)
    assert listed.status_code == 200
    assert all("api_key" not in item or item.get("api_key") is None for item in listed.json())

    config_id = body["id"]
    delete = api_client.delete(f"/api/v1/admin/llm-providers/{config_id}", headers=headers)
    assert delete.status_code == 204


@pytest.mark.api
def test_usage_and_ops_overview(api_client: TestClient, tenant_scenario: TenantScenario) -> None:
    headers = tenant_scenario.admin_headers()
    usage = api_client.get("/api/v1/admin/usage/overview", headers=headers)
    assert usage.status_code == 200
    assert "conversations" in usage.json()

    tokens = api_client.get("/api/v1/admin/usage/tokens", headers=headers)
    assert tokens.status_code == 200
    assert isinstance(tokens.json(), list)

    ops = api_client.get("/api/v1/admin/ops/overview", headers=headers)
    assert ops.status_code == 200
    assert "readiness_status" in ops.json()


@pytest.mark.api
def test_retention_policy_create_list(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    headers = tenant_scenario.admin_headers()
    create = api_client.post(
        "/api/v1/admin/retention/policies",
        headers=headers,
        json={
            "resource_type": "conversations",
            "retention_days": 90,
            "soft_delete_first": True,
            "enabled": True,
        },
    )
    assert create.status_code == 201
    policy_id = create.json()["id"]

    listed = api_client.get("/api/v1/admin/retention/policies", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == policy_id for item in listed.json())

    delete = api_client.delete(f"/api/v1/admin/retention/policies/{policy_id}", headers=headers)
    assert delete.status_code == 204
