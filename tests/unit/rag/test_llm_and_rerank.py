"""Unit tests for LLM providers and rerankers."""

from __future__ import annotations

from uuid import uuid4

import pytest

from contextforge.application.ports.llm_provider import LlmMessage
from contextforge.application.ports.reranker import RerankCandidate, RerankResult
from contextforge.infrastructure.llm.providers import MockLlmProvider, build_llm_provider
from contextforge.infrastructure.reranking.rerankers import (
    HashingCrossEncoderReranker,
    NoopReranker,
    build_reranker,
)
from contextforge.shared.config.settings import LlmSettings, RerankSettings


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_llm_complete_and_stream() -> None:
    provider = MockLlmProvider(LlmSettings(provider="mock", model="mock-1"))
    messages = [
        LlmMessage(role="system", content="system\n[cite:123]"),
        LlmMessage(role="user", content="What is the leave policy?"),
    ]
    completion = await provider.complete(messages)
    assert completion.content
    assert completion.usage.total_tokens > 0
    chunks: list[str] = []
    async for delta in provider.stream(messages):
        chunks.append(delta)
    assert "".join(chunks) == completion.content


@pytest.mark.unit
def test_build_llm_provider_defaults_to_mock() -> None:
    provider = build_llm_provider(LlmSettings(provider="mock"))
    assert isinstance(provider, MockLlmProvider)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hashing_reranker_orders_by_overlap() -> None:
    reranker = HashingCrossEncoderReranker()
    a = uuid4()
    b = uuid4()
    results = await reranker.rerank(
        query="vacation leave policy",
        candidates=[
            RerankCandidate(chunk_id=a, content="network routers and switches", score=0.9),
            RerankCandidate(chunk_id=b, content="vacation leave policy for employees", score=0.1),
        ],
        top_n=2,
    )
    assert results[0].chunk_id == b


@pytest.mark.unit
@pytest.mark.asyncio
async def test_noop_reranker_preserves_order() -> None:
    reranker = build_reranker(RerankSettings(provider="noop"))
    assert isinstance(reranker, NoopReranker)
    first, second = uuid4(), uuid4()
    results = await reranker.rerank(
        query="q",
        candidates=[
            RerankCandidate(chunk_id=first, content="a", score=1.0),
            RerankCandidate(chunk_id=second, content="b", score=0.5),
        ],
        top_n=1,
    )
    assert results == [RerankResult(chunk_id=first, score=1.0)]
