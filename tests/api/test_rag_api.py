"""API tests for RAG search and query endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from tests.helpers import create_knowledge_space, seed_retrieval_stubs

from contextforge.bootstrap.app_factory import create_app
from contextforge.shared.config.settings import Settings, clear_settings_cache

if TYPE_CHECKING:
    from tests.conftest import TenantScenario


@pytest.mark.api
def test_rag_query_returns_answer_and_citations(
    integration_settings: Settings, tenant_scenario: TenantScenario
) -> None:
    clear_settings_cache()
    app = create_app(integration_settings)
    headers = tenant_scenario.admin_headers()

    with TestClient(app) as api_client:
        ks_id = create_knowledge_space(api_client, headers, name="RAG KS", slug_prefix="rag-ks")
        seed_retrieval_stubs(
            app,
            organization_id=tenant_scenario.organization_id,
            knowledge_space_id=ks_id,
            content="Employees receive twenty days of annual leave each year.",
            title="Leave Policy",
        )

        response = api_client.post(
            "/api/v1/rag/query",
            headers=headers,
            json={
                "question": "How many annual leave days do employees get?",
                "knowledge_space_ids": [str(ks_id)],
                "language": "en",
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["answer"]
        assert body["language"] == "en"
        assert body["citations"]
        assert body["citations"][0]["document_title"] == "Leave Policy"
        assert body["diagnostics"]["retrieved_chunk_count"] >= 1

        search = api_client.post(
            "/api/v1/rag/search",
            headers=headers,
            json={
                "question": "annual leave",
                "knowledge_space_ids": [str(ks_id)],
                "limit": 5,
                "offset": 0,
            },
        )
        assert search.status_code == 200
        assert search.json()["items"]

        stream = api_client.post(
            "/api/v1/rag/query/stream",
            headers=headers,
            json={
                "question": "How many annual leave days do employees get?",
                "knowledge_space_ids": [str(ks_id)],
                "language": "en",
            },
        )
        assert stream.status_code == 200
        assert "text/event-stream" in stream.headers.get("content-type", "")
        assert "data:" in stream.text
        assert "[DONE]" in stream.text


@pytest.mark.api
def test_rag_query_requires_identity(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/rag/query",
        json={"question": "What is the policy?"},
    )
    assert response.status_code == 401
