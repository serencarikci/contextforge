"""Port for text embedding providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EmbeddingBatchResult:
    """Vectors produced for a batch of texts."""

    vectors: list[list[float]]
    model: str
    dimensions: int


class EmbeddingProviderPort(Protocol):
    """Generates dense vectors for multilingual document chunk text."""

    @property
    def model(self) -> str:
        """Configured embedding model name."""
        ...

    @property
    def dimensions(self) -> int:
        """Vector dimensionality produced by this provider."""
        ...

    async def embed_texts(
        self,
        texts: list[str],
        *,
        language: str | None = None,
    ) -> EmbeddingBatchResult:
        """Embed ``texts`` with retries for transient provider failures."""
        ...


__all__ = ["EmbeddingBatchResult", "EmbeddingProviderPort"]
