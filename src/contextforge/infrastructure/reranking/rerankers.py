"""Reranker implementations."""

from __future__ import annotations

import hashlib
import re

import httpx

from contextforge.application.ports.reranker import RerankCandidate, RerankResult
from contextforge.shared.config.settings import RerankSettings
from contextforge.shared.utilities.retry import retry_async

_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


class NoopReranker:
    """Passthrough reranker that preserves hybrid order."""

    async def rerank(
        self,
        *,
        query: str,
        candidates: list[RerankCandidate],
        top_n: int,
    ) -> list[RerankResult]:
        del query
        return [
            RerankResult(chunk_id=item.chunk_id, score=item.score) for item in candidates[:top_n]
        ]


class HashingCrossEncoderReranker:
    """Deterministic local cross-encoder stand-in for tests and offline use."""

    async def rerank(
        self,
        *,
        query: str,
        candidates: list[RerankCandidate],
        top_n: int,
    ) -> list[RerankResult]:
        query_tokens = set(_TOKEN_RE.findall(query.lower()))
        scored: list[RerankResult] = []
        for candidate in candidates:
            content_tokens = set(_TOKEN_RE.findall(candidate.content.lower()))
            overlap = len(query_tokens & content_tokens)
            digest = hashlib.sha256(f"{query}:{candidate.chunk_id}".encode()).digest()
            tie_break = int.from_bytes(digest[:2], "big") / 65535.0
            score = overlap + 0.01 * tie_break + 0.1 * candidate.score
            scored.append(RerankResult(chunk_id=candidate.chunk_id, score=score))
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_n]


class OpenAICompatibleReranker:
    """HTTP reranker compatible with OpenAI-style scoring endpoints."""

    def __init__(self, settings: RerankSettings) -> None:
        self._settings = settings
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if settings.api_key is not None:
            secret = settings.api_key.get_secret_value()
            if secret:
                headers["Authorization"] = f"Bearer {secret}"
        self._client = httpx.AsyncClient(
            base_url=settings.base_url.rstrip("/"),
            headers=headers,
            timeout=settings.timeout_seconds,
        )

    async def rerank(
        self,
        *,
        query: str,
        candidates: list[RerankCandidate],
        top_n: int,
    ) -> list[RerankResult]:
        if not candidates:
            return []

        async def _call() -> list[RerankResult]:
            payload = {
                "model": self._settings.model,
                "query": query,
                "documents": [item.content for item in candidates],
                "top_n": top_n,
            }
            response = await self._client.post("/rerank", json=payload)
            if response.status_code >= 500:
                raise RuntimeError(f"rerank provider unavailable: {response.status_code}")
            if response.status_code >= 400:
                raise ValueError(f"rerank provider rejected request: {response.status_code}")
            body = response.json()
            results = body.get("results") or body.get("data") or []
            scored: list[RerankResult] = []
            for item in results:
                index = int(item.get("index", -1))
                if index < 0 or index >= len(candidates):
                    continue
                score = float(item.get("relevance_score", item.get("score", 0.0)))
                scored.append(RerankResult(chunk_id=candidates[index].chunk_id, score=score))
            if not scored:
                fallback = HashingCrossEncoderReranker()
                return await fallback.rerank(query=query, candidates=candidates, top_n=top_n)
            scored.sort(key=lambda row: row.score, reverse=True)
            return scored[:top_n]

        try:
            return await retry_async(
                _call,
                max_retries=self._settings.max_retries,
                backoff_seconds=self._settings.retry_backoff_seconds,
                retry_on=(RuntimeError, httpx.TransportError, httpx.TimeoutException),
            )
        except Exception:
            fallback = HashingCrossEncoderReranker()
            return await fallback.rerank(query=query, candidates=candidates, top_n=top_n)

    async def close(self) -> None:
        await self._client.aclose()


def build_reranker(
    settings: RerankSettings,
) -> NoopReranker | HashingCrossEncoderReranker | OpenAICompatibleReranker:
    if settings.provider == "noop":
        return NoopReranker()
    if settings.provider == "openai_compatible":
        return OpenAICompatibleReranker(settings)
    return HashingCrossEncoderReranker()


__all__ = [
    "HashingCrossEncoderReranker",
    "NoopReranker",
    "OpenAICompatibleReranker",
    "build_reranker",
]
