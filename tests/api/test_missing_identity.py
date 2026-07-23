"""API tests: requests without development identity headers are rejected."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
def test_list_customers_without_identity_returns_401(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/customers")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] in {"AUTHENTICATION_REQUIRED", "INVALID_DEVELOPMENT_IDENTITY"}


@pytest.mark.api
def test_create_customer_without_identity_returns_401(api_client: TestClient) -> None:
    response = api_client.post("/api/v1/customers", json={"name": "No Identity Co", "code": "NOID"})
    assert response.status_code == 401


@pytest.mark.api
def test_missing_organization_header_returns_401(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/customers", headers={"X-ContextForge-User-ID": str(uuid4())})
    assert response.status_code == 401


@pytest.mark.api
def test_malformed_user_id_header_returns_401(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/v1/customers",
        headers={
            "X-ContextForge-User-ID": "not-a-uuid",
            "X-ContextForge-Organization-ID": str(uuid4()),
        },
    )
    assert response.status_code == 401


@pytest.mark.api
def test_create_organization_requires_user_identity(api_client: TestClient) -> None:
    """Organization creation only needs an active user, not an org context yet."""
    response = api_client.post(
        "/api/v1/organizations", json={"name": "No Identity Org", "slug": "no-identity-org"}
    )
    assert response.status_code == 401


@pytest.mark.api
def test_unknown_user_id_returns_401(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/v1/customers",
        headers={
            "X-ContextForge-User-ID": str(uuid4()),
            "X-ContextForge-Organization-ID": str(uuid4()),
        },
    )
    assert response.status_code == 401
