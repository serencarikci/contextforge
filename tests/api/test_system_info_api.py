"""API test for the public system info endpoint's capability flags."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
def test_system_info_reports_expected_capability_flags(api_client: TestClient) -> None:
    """No identity headers are required -- system info is intentionally public."""
    response = api_client.get("/api/v1/system/info")
    assert response.status_code == 200
    body = response.json()

    assert body["authentication"] == "development_only"

    capabilities = body["capabilities"]
    implemented = (
        "identity_context",
        "multi_tenancy",
        "rbac",
        "customers",
        "projects",
        "knowledge_spaces",
        "audit_log",
        "document_ingestion",
        "document_parsing",
    )
    for flag in implemented:
        assert capabilities[flag] is True, f"expected capability '{flag}' to be True"

    not_yet_implemented = ("rag", "chat", "multilingual_answers")
    for flag in not_yet_implemented:
        assert capabilities[flag] is False, f"expected capability '{flag}' to be False"
