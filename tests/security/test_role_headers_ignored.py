"""Security test: there is no client-supplied role/permission header.

Authorization is derived exclusively from the caller's identity
(`X-ContextForge-User-ID`/`X-ContextForge-Organization-ID`) resolved against
the database -- role assignments, not request headers. This test proves that
sending a forged `X-ContextForge-Role`-style header cannot escalate a
viewer's privileges: the API must still enforce the DB-backed permission set
and must not read/trust any role/permission header.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from contextforge.api.dependencies.identity import (
    KNOWLEDGE_SPACE_ID_HEADER,
    ORGANIZATION_ID_HEADER,
    PROJECT_ID_HEADER,
    USER_ID_HEADER,
)

if TYPE_CHECKING:
    from tests.conftest import TenantScenario

_RECOGNIZED_HEADERS = {
    USER_ID_HEADER,
    ORGANIZATION_ID_HEADER,
    PROJECT_ID_HEADER,
    KNOWLEDGE_SPACE_ID_HEADER,
}


@pytest.mark.security
def test_forged_role_header_does_not_grant_write_access(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    forged_headers = {
        **tenant_scenario.viewer_headers(),
        "X-ContextForge-Role": "organization_admin",
        "X-ContextForge-Permissions": "customer:create,customer:archive",
        "X-ContextForge-Is-Platform-Admin": "true",
    }
    response = api_client.post(
        "/api/v1/customers",
        json={"name": "Forged Role Co", "code": "FORGED01"},
        headers=forged_headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.security
def test_forged_role_header_does_not_bypass_archive_permission(
    api_client: TestClient, tenant_scenario: TenantScenario
) -> None:
    forged_headers = {
        **tenant_scenario.viewer_headers(),
        "X-ContextForge-Role": "organization_admin",
    }
    response = api_client.post(
        f"/api/v1/customers/{tenant_scenario.customer_id}/archive",
        headers=forged_headers,
    )
    assert response.status_code == 403


@pytest.mark.security
def test_identity_dependency_only_declares_uuid_headers() -> None:
    """The identity dependency's own header contract is fixed and minimal --
    there is no role/permission header parameter to (mis)trust in the first
    place, independent of what the caller sends over the wire."""
    assert {
        "X-ContextForge-User-ID",
        "X-ContextForge-Organization-ID",
        "X-ContextForge-Project-ID",
        "X-ContextForge-Knowledge-Space-ID",
    } == _RECOGNIZED_HEADERS
