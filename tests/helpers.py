"""Shared HTTP helpers for API and security tests."""

from __future__ import annotations

from uuid import UUID, uuid4

import httpx
from fastapi.testclient import TestClient

from contextforge.application.ports.lexical_search import LexicalDocument
from contextforge.application.ports.vector_store import VectorSearchHit
from contextforge.infrastructure.retrieval import InMemoryLexicalSearch
from tests.fakes import FakeVectorStore


def create_knowledge_space(
    api_client: TestClient,
    headers: dict[str, str],
    *,
    name: str = "Test KS",
    slug_prefix: str = "ks",
) -> UUID:
    response = api_client.post(
        "/api/v1/knowledge-spaces",
        json=_knowledge_space_payload(name=name, slug_prefix=slug_prefix),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


async def acreate_knowledge_space(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    name: str = "Ingest KS",
    slug_prefix: str = "ingest-ks",
) -> UUID:
    response = await client.post(
        "/api/v1/knowledge-spaces",
        json=_knowledge_space_payload(name=name, slug_prefix=slug_prefix),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


def _knowledge_space_payload(*, name: str, slug_prefix: str) -> dict[str, str]:
    return {"name": name, "slug": f"{slug_prefix}-{uuid4().hex[:10]}"}


def seed_retrieval_stubs(
    app: object,
    *,
    organization_id: UUID,
    knowledge_space_id: UUID,
    content: str,
    title: str = "Leave Policy",
    score: float = 0.91,
    include_vector: bool = True,
) -> tuple[UUID, UUID]:
    """Plant in-memory lexical/vector hits without uploading a real document."""
    chunk_id = uuid4()
    document_id = uuid4()
    app.state.lexical_search = InMemoryLexicalSearch(  # type: ignore[attr-defined]
        [
            LexicalDocument(
                chunk_id=chunk_id,
                organization_id=organization_id,
                document_id=document_id,
                knowledge_space_id=knowledge_space_id,
                content=content,
                chunk_index=0,
                document_title=title,
                char_start=0,
                char_end=len(content),
                page_count=1,
            )
        ]
    )
    if include_vector:
        app.state.vector_store = FakeVectorStore(  # type: ignore[attr-defined]
            [
                VectorSearchHit(
                    chunk_id=chunk_id,
                    organization_id=organization_id,
                    document_id=document_id,
                    knowledge_space_id=knowledge_space_id,
                    score=score,
                    chunk_index=0,
                    document_title=title,
                )
            ]
        )
    return chunk_id, document_id


def ingest_markdown_document(
    api_client: TestClient,
    headers: dict[str, str],
    knowledge_space_id: UUID,
    *,
    title: str,
    content: bytes,
    filename: str = "doc.md",
) -> tuple[UUID, UUID, str]:
    upload = api_client.post(
        "/api/v1/documents",
        data={"knowledge_space_id": str(knowledge_space_id), "title": title},
        files={"file": (filename, content, "text/markdown")},
        headers=headers,
    )
    assert upload.status_code == 201, upload.text
    document_id = UUID(upload.json()["id"])

    parse_response = api_client.post(f"/api/v1/documents/{document_id}/parse", headers=headers)
    assert parse_response.status_code == 200, parse_response.text

    chunk_response = api_client.post(f"/api/v1/documents/{document_id}/chunks", headers=headers)
    assert chunk_response.status_code == 200, chunk_response.text
    chunks = chunk_response.json()["items"]
    assert chunks
    return document_id, UUID(chunks[0]["id"]), title


def seed_grounding_content(
    app: object,
    api_client: TestClient,
    headers: dict[str, str],
    *,
    organization_id: UUID,
    knowledge_space_id: UUID,
    title: str = "Leave Policy",
    content: bytes = b"Employees receive twenty days of annual leave each year.",
    body_text: str | None = None,
) -> None:
    text = body_text if body_text is not None else content.decode("utf-8")
    document_id, chunk_id, document_title = ingest_markdown_document(
        api_client,
        headers,
        knowledge_space_id,
        title=title,
        content=content,
    )
    app.state.lexical_search = InMemoryLexicalSearch(  # type: ignore[attr-defined]
        [
            LexicalDocument(
                chunk_id=chunk_id,
                organization_id=organization_id,
                document_id=document_id,
                knowledge_space_id=knowledge_space_id,
                content=text,
                chunk_index=0,
                document_title=document_title,
                char_start=0,
                char_end=len(text),
                page_count=1,
            )
        ]
    )
    app.state.vector_store = FakeVectorStore(  # type: ignore[attr-defined]
        [
            VectorSearchHit(
                chunk_id=chunk_id,
                organization_id=organization_id,
                document_id=document_id,
                knowledge_space_id=knowledge_space_id,
                score=0.9,
                chunk_index=0,
                document_title=document_title,
            )
        ]
    )


def create_conversation(
    api_client: TestClient,
    headers: dict[str, str],
    knowledge_space_id: UUID | None = None,
    *,
    title: str = "Leave questions",
) -> dict[str, object]:
    payload: dict[str, object] = {"title": title}
    if knowledge_space_id is not None:
        payload["knowledge_space_ids"] = [str(knowledge_space_id)]
    response = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


__all__ = [
    "acreate_knowledge_space",
    "create_conversation",
    "create_knowledge_space",
    "ingest_markdown_document",
    "seed_grounding_content",
    "seed_retrieval_stubs",
]
