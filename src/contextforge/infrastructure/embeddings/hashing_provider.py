"""Deterministic multilingual hashing embedding provider for local/test use."""

from __future__ import annotations

import hashlib
import math
import struct

from contextforge.application.ports.embedding_provider import EmbeddingBatchResult
from contextforge.modules.documents.domain.language import normalize_multilingual_text
from contextforge.shared.config.settings import EmbeddingSettings


class HashingMultilingualEmbeddingProvider:
    """Offline multilingual embedding provider using language-aware hashing.

    Suitable for local development and tests. Production deployments should use
    an ``openai_compatible`` multilingual model endpoint.
    """

    def __init__(self, settings: EmbeddingSettings) -> None:
        self._settings = settings

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
        vectors = [
            _hash_embed(
                normalize_multilingual_text(text),
                dimensions=self.dimensions,
                language=language or "und",
                model=self.model,
            )
            for text in texts
        ]
        return EmbeddingBatchResult(
            vectors=vectors,
            model=self.model,
            dimensions=self.dimensions,
        )


def _hash_embed(text: str, *, dimensions: int, language: str, model: str) -> list[float]:
    seed = f"{model}:{language}:{text}".encode()
    values: list[float] = []
    counter = 0
    while len(values) < dimensions:
        digest = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
        for index in range(0, len(digest), 4):
            if len(values) >= dimensions:
                break
            (raw,) = struct.unpack_from(">I", digest, index)
            values.append((raw / 0xFFFFFFFF) * 2.0 - 1.0)
        counter += 1
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


__all__ = ["HashingMultilingualEmbeddingProvider"]
