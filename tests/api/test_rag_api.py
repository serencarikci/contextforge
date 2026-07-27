"""API tests for RAG search and query endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from contextforge.application.ports.lexical_search import LexicalDocument
from contextforge.application.ports.vector_store import VectorSearchHit
from contextforge.bootstrap.app_factory import create_app
from contextforge.infrastructure.retrieval import InMemoryLexicalSearch
from contextforge.shared.config.settings import Settings, clear_settings_cache

if TYPE_CHECKING:
    from tests.conftest import TenantScenario


class _FakeVectorStore:
    def __init__(self, hits: list[VectorSearchHit] | None = None) -> None:
        self.hits = hits or []

    async def ensure_ready(self, *, dimensions: int) -> None:
        return None

    async def upsert_chunk_vectors(self, points: list[object]) -> None:
        return None

    async def delete_by_document(self, organization_id: object, document_id: object) -> None:
        return None

    async def search(
        self,
        *,
        organization_id: UUID,
        query_vector: list[float],
        knowledge_space_ids: list[UUID],
        top_k: int,
    ) -> list[VectorSearchHit]:
        del query_vector, top_k
        return [
            hit
            for hit in self.hits
            if hit.organization_id == organization_id
            and hit.knowledge_space_id in set(knowledge_space_ids)
        ]


def _create_knowledge_space(api_client: TestClient, headers: dict[str, str]) -> str:
    response = api_client.post(
        "/api/v1/knowledge-spaces",
        json={"name": "RAG KS", "slug": f"rag-ks-{uuid4().hex[:10]}"},
        headers=headers,
    )
    assert response.status_code == 201
    return str(response.json()["id"])


@pytest.mark.api
def test_rag_query_returns_answer_and_citations(
    integration_settings: Settings, tenant_scenario: TenantScenario
) -> None:
    clear_settings_cache()
    app = create_app(integration_settings)
    headers = tenant_scenario.admin_headers()

    with TestClient(app) as api_client:
        ks_id = UUID(_create_knowledge_space(api_client, headers))
        org_id = tenant_scenario.organization_id
        chunk_id = uuid4()
        document_id = uuid4()

        lexical = InMemoryLexicalSearch(
            [
                LexicalDocument(
                    chunk_id=chunk_id,
                    organization_id=org_id,
                    document_id=document_id,
                    knowledge_space_id=ks_id,
                    content="Employees receive twenty days of annual leave each year.",
                    chunk_index=0,
                    document_title="Leave Policy",
                    char_start=0,
                    char_end=60,
                    page_count=1,
                )
            ]
        )
        app.state.lexical_search = lexical
        app.state.vector_store = _FakeVectorStore(
            [
                VectorSearchHit(
                    chunk_id=chunk_id,
                    organization_id=org_id,
                    document_id=document_id,
                    knowledge_space_id=ks_id,
                    score=0.91,
                    chunk_index=0,
                    document_title="Leave Policy",
                )
            ]
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
