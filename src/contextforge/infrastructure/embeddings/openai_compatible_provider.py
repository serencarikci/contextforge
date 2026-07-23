"""OpenAI-compatible multilingual embedding provider with retries."""

from __future__ import annotations

import httpx

from contextforge.application.ports.embedding_provider import EmbeddingBatchResult
from contextforge.infrastructure.embeddings.retry import retry_async
from contextforge.modules.documents.domain.exceptions import (
    PermanentEmbeddingError,
    TransientEmbeddingError,
)
from contextforge.modules.documents.domain.language import normalize_multilingual_text
from contextforge.shared.config.settings import EmbeddingSettings
from contextforge.shared.logging.setup import get_logger

logger = get_logger(__name__)


class OpenAICompatibleEmbeddingProvider:
    """HTTP embedding client for OpenAI-compatible multilingual model APIs."""

    def __init__(self, settings: EmbeddingSettings) -> None:
        self._settings = settings
        if settings.api_key is None or not settings.api_key.get_secret_value():
            raise PermanentEmbeddingError(
                "Embedding API key is required for openai_compatible provider."
            )
        self._client = httpx.AsyncClient(
            base_url=settings.base_url.rstrip("/"),
            timeout=settings.timeout_seconds,
            headers={
                "Authorization": f"Bearer {settings.api_key.get_secret_value()}",
                "Content-Type": "application/json",
            },
        )

    @property
    def model(self) -> str:
        return self._settings.model

    @property
    def dimensions(self) -> int:
        return self._settings.dimensions

    async def embed_texts(
        self,
        texts: list[str],
        *,
        language: str | None = None,
    ) -> EmbeddingBatchResult:
        del language
        normalized = [normalize_multilingual_text(text) for text in texts]
        if not normalized:
            return EmbeddingBatchResult(vectors=[], model=self.model, dimensions=self.dimensions)

        async def _call() -> EmbeddingBatchResult:
            return await self._embed_once(normalized)

        return await retry_async(
            _call,
            max_retries=self._settings.max_retries,
            backoff_seconds=self._settings.retry_backoff_seconds,
        )

    async def _embed_once(self, texts: list[str]) -> EmbeddingBatchResult:
        payload: dict[str, object] = {
            "model": self.model,
            "input": texts,
        }
        if self.dimensions:
            payload["dimensions"] = self.dimensions
        try:
            response = await self._client.post("/embeddings", json=payload)
        except httpx.TimeoutException as exc:
            raise TransientEmbeddingError("Embedding provider timed out.") from exc
        except httpx.TransportError as exc:
            raise TransientEmbeddingError("Embedding provider transport failed.") from exc

        if response.status_code in {408, 425, 429, 500, 502, 503, 504}:
            raise TransientEmbeddingError(
                f"Embedding provider returned retryable status {response.status_code}."
            )
        if response.status_code >= 400:
            raise PermanentEmbeddingError(
                f"Embedding provider returned status {response.status_code}: {response.text}"
            )

        body = response.json()
        data = body.get("data")
        if not isinstance(data, list) or len(data) != len(texts):
            raise PermanentEmbeddingError("Embedding provider returned an invalid payload.")

        ordered = sorted(data, key=lambda item: int(item.get("index", 0)))
        vectors: list[list[float]] = []
        for item in ordered:
            embedding = item.get("embedding")
            if not isinstance(embedding, list) or not embedding:
                raise PermanentEmbeddingError("Embedding provider returned an empty vector.")
            vectors.append([float(value) for value in embedding])

        dimensions = len(vectors[0]) if vectors else self.dimensions
        model_name = str(body.get("model") or self.model)
        return EmbeddingBatchResult(vectors=vectors, model=model_name, dimensions=dimensions)

    async def close(self) -> None:
        await self._client.aclose()


__all__ = ["OpenAICompatibleEmbeddingProvider"]
