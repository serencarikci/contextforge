"""Port for post-retrieval document reranking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RerankCandidate:
    """Candidate chunk presented to a reranker."""

    chunk_id: UUID
    content: str
    score: float


@dataclass(frozen=True, slots=True)
class RerankResult:
    """Reranked candidate with a new relevance score."""

    chunk_id: UUID
    score: float


class RerankerPort(Protocol):
    """Scores query/document pairs and returns a reordered top-N list."""

    async def rerank(
        self,
        *,
        query: str,
        candidates: list[RerankCandidate],
        top_n: int,
    ) -> list[RerankResult]:
        """Rerank candidates for ``query`` and return at most ``top_n`` results."""
        ...


__all__ = ["RerankCandidate", "RerankResult", "RerankerPort"]
