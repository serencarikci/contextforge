from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EmbeddingBatchResult:
    vectors: list[list[float]]
    model: str
    dimensions: int


class EmbeddingProviderPort(Protocol):
    @property
    def model(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    async def embed_texts(
        self,
        texts: list[str],
        *,
        language: str | None = None,
    ) -> EmbeddingBatchResult: ...


__all__ = ["EmbeddingBatchResult", "EmbeddingProviderPort"]
