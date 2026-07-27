"""Security tests for administration boundaries."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from tests.conftest import TenantScenario


@pytest.mark.security
def test_viewer_cannot_access_admin_surface(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    headers = tenant_scenario.viewer_headers()
    paths = (
        "/api/v1/admin/dashboard",
        "/api/v1/admin/users",
        "/api/v1/admin/organizations/settings",
        "/api/v1/admin/usage/overview",
        "/api/v1/admin/ops/overview",
        "/api/v1/admin/feature-flags",
        "/api/v1/admin/llm-providers",
        "/api/v1/admin/retention/policies",
    )
    for path in paths:
        response = api_client.get(path, headers=headers)
        assert response.status_code == 403, path
        assert response.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.security
def test_admin_cannot_read_other_tenant_knowledge_space_stats(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.get(
        f"/api/v1/admin/knowledge-spaces/{uuid4()}/stats",
        headers=tenant_scenario.admin_headers(),
    )
    assert response.status_code in {403, 404}


@pytest.mark.security
def test_llm_provider_response_never_includes_ciphertext(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    headers = tenant_scenario.admin_headers()
    create = api_client.post(
        "/api/v1/admin/llm-providers",
        headers=headers,
        json={
            "provider": "openai_compatible",
            "model": "gpt-test",
            "base_url": "http://127.0.0.1:9",
            "api_key": "super-secret-key-value",
        },
    )
    assert create.status_code == 201
    payload = create.json()
    serialized = str(payload)
    assert "super-secret-key-value" not in serialized
    assert "api_key_ciphertext" not in payload
    assert payload["api_key_set"] is True

    config_id = payload["id"]
    api_client.delete(f"/api/v1/admin/llm-providers/{config_id}", headers=headers)


@pytest.mark.security
def test_cross_tenant_admin_headers_do_not_leak_dashboard(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    response = api_client.get(
        "/api/v1/admin/dashboard",
        headers={
            "X-ContextForge-User-ID": str(tenant_scenario.admin_user_id),
            "X-ContextForge-Organization-ID": str(tenant_scenario.other_organization_id),
        },
    )
    assert response.status_code in {403, 404}
