from __future__ import annotations

from uuid import uuid4

import pytest

from contextforge.application.ports.lexical_search import LexicalDocument
from contextforge.infrastructure.retrieval.bm25_lexical_search import (
    InMemoryLexicalSearch,
    bm25_search,
)


@pytest.mark.unit
def test_bm25_prefers_keyword_overlap() -> None:
    org = uuid4()
    ks = uuid4()
    docs = [
        LexicalDocument(
            chunk_id=uuid4(),
            organization_id=org,
            document_id=uuid4(),
            knowledge_space_id=ks,
            content="payroll policy and salary guidelines",
            chunk_index=0,
            document_title="HR",
        ),
        LexicalDocument(
            chunk_id=uuid4(),
            organization_id=org,
            document_id=uuid4(),
            knowledge_space_id=ks,
            content="network firewall configuration notes",
            chunk_index=0,
            document_title="IT",
        ),
    ]
    hits = bm25_search("payroll salary", docs, top_k=2)
    assert hits
    assert "payroll" in hits[0].content


@pytest.mark.unit
@pytest.mark.asyncio
async def test_in_memory_lexical_respects_tenant_scope() -> None:
    org = uuid4()
    other = uuid4()
    ks = uuid4()
    search = InMemoryLexicalSearch(
        [
            LexicalDocument(
                chunk_id=uuid4(),
                organization_id=org,
                document_id=uuid4(),
                knowledge_space_id=ks,
                content="authorized tenant document about invoices",
                chunk_index=0,
            ),
            LexicalDocument(
                chunk_id=uuid4(),
                organization_id=other,
                document_id=uuid4(),
                knowledge_space_id=ks,
                content="foreign tenant invoices should not appear",
                chunk_index=0,
            ),
        ]
    )
    hits = await search.search(
        organization_id=org,
        query="invoices",
        knowledge_space_ids=[ks],
        top_k=5,
        corpus_limit=100,
    )
    assert hits
    assert all(hit.organization_id == org for hit in hits)
