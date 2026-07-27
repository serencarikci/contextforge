"""HTTP-backed LLM and reranker provider unit tests with MockTransport."""

from __future__ import annotations

import json
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr

from contextforge.application.ports.llm_provider import (
    LlmMessage,
    PermanentLlmError,
    TransientLlmError,
)
from contextforge.application.ports.reranker import RerankCandidate
from contextforge.infrastructure.llm.providers import (
    AzureOpenAILlmProvider,
    OpenAICompatibleLlmProvider,
    OpenAILlmProvider,
    build_llm_provider,
)
from contextforge.infrastructure.reranking.rerankers import (
    OpenAICompatibleReranker,
    build_reranker,
)
from contextforge.shared.config.settings import LlmSettings, RerankSettings


def _chat_response(content: str = "hello from provider") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": "gpt-test",
            "choices": [
                {
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 11, "completion_tokens": 4, "total_tokens": 15},
        },
    )


@pytest.mark.unit
def test_build_llm_provider_variants() -> None:
    openai = build_llm_provider(
        LlmSettings(provider="openai", api_key=SecretStr("sk-test"), model="gpt-4o-mini")
    )
    azure = build_llm_provider(
        LlmSettings(
            provider="azure_openai",
            api_key=SecretStr("azure-key"),
            azure_endpoint="https://example.openai.azure.com",
            azure_deployment="deploy-1",
        )
    )
    compatible = build_llm_provider(
        LlmSettings(
            provider="openai_compatible",
            base_url="http://localhost:8001/v1",
            model="local-model",
        )
    )
    assert isinstance(openai, OpenAILlmProvider)
    assert isinstance(azure, AzureOpenAILlmProvider)
    assert isinstance(compatible, OpenAICompatibleLlmProvider)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_openai_compatible_complete_and_errors() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, json={"error": "busy"})
        if calls["n"] == 2:
            return httpx.Response(400, json={"error": "bad"})
        return _chat_response("grounded")

    transport = httpx.MockTransport(handler)
    settings = LlmSettings(
        provider="openai_compatible",
        base_url="http://llm.test/v1",
        model="local",
        api_key=SecretStr("token"),
        max_retries=0,
        retry_backoff_seconds=0.01,
    )
    provider = OpenAICompatibleLlmProvider(settings)
    provider._client = httpx.AsyncClient(
        base_url="http://llm.test/v1",
        transport=transport,
        headers={"Authorization": "Bearer token"},
    )
    messages = [LlmMessage(role="user", content="hi")]
    with pytest.raises(TransientLlmError):
        await provider.complete(messages)
    with pytest.raises(PermanentLlmError):
        await provider.complete(messages)
    completion = await provider.complete(messages)
    assert completion.content == "grounded"
    assert completion.usage.total_tokens == 15
    await provider.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_openai_compatible_stream() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = (
            b'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n'
            b'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n'
            b"data: [DONE]\n\n"
        )
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    provider = OpenAICompatibleLlmProvider(
        LlmSettings(provider="openai_compatible", base_url="http://llm.test/v1", model="local")
    )
    provider._client = httpx.AsyncClient(
        base_url="http://llm.test/v1",
        transport=httpx.MockTransport(handler),
    )
    parts: list[str] = []
    async for delta in provider.stream([LlmMessage(role="user", content="q")]):
        parts.append(delta)
    assert "".join(parts) == "Hello"
    await provider.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_azure_openai_complete_and_stream() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return _chat_response("azure-ok")
        body = b'data: {"choices":[{"delta":{"content":"Az"}}]}\n\ndata: [DONE]\n\n'
        return httpx.Response(200, content=body)

    settings = LlmSettings(
        provider="azure_openai",
        api_key=SecretStr("azure-key"),
        azure_endpoint="https://example.openai.azure.com",
        azure_deployment="deploy-1",
        max_retries=0,
        retry_backoff_seconds=0.01,
    )
    provider = AzureOpenAILlmProvider(settings)
    provider._client = httpx.AsyncClient(
        base_url="https://example.openai.azure.com",
        transport=httpx.MockTransport(handler),
    )
    completion = await provider.complete([LlmMessage(role="user", content="q")])
    assert completion.content == "azure-ok"
    streamed = [delta async for delta in provider.stream([LlmMessage(role="user", content="q")])]
    assert streamed == ["Az"]
    await provider.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_openai_compatible_reranker_orders_and_fallback() -> None:
    first, second = uuid4(), uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        assert payload["query"] == "leave policy"
        return httpx.Response(
            200,
            json={
                "results": [
                    {"index": 1, "relevance_score": 0.95},
                    {"index": 0, "relevance_score": 0.1},
                ]
            },
        )

    settings = RerankSettings(
        provider="openai_compatible",
        base_url="http://rerank.test",
        model="rerank-v1",
        api_key=SecretStr("rk"),
        max_retries=0,
        retry_backoff_seconds=0.01,
    )
    reranker = OpenAICompatibleReranker(settings)
    reranker._client = httpx.AsyncClient(
        base_url="http://rerank.test",
        transport=httpx.MockTransport(handler),
    )
    results = await reranker.rerank(
        query="leave policy",
        candidates=[
            RerankCandidate(chunk_id=first, content="network gear", score=0.2),
            RerankCandidate(chunk_id=second, content="leave policy", score=0.1),
        ],
        top_n=2,
    )
    assert results[0].chunk_id == second
    await reranker.close()

    fallback = build_reranker(settings)
    assert isinstance(fallback, OpenAICompatibleReranker)
    fallback._client = httpx.AsyncClient(
        base_url="http://rerank.test",
        transport=httpx.MockTransport(lambda _r: httpx.Response(500, json={"error": "down"})),
    )
    recovered = await fallback.rerank(
        query="leave policy",
        candidates=[
            RerankCandidate(chunk_id=first, content="network gear", score=0.2),
            RerankCandidate(chunk_id=second, content="leave policy details", score=0.1),
        ],
        top_n=1,
    )
    assert recovered[0].chunk_id == second
    await fallback.close()
