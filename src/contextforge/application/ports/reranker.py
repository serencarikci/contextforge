from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RerankCandidate:
    chunk_id: UUID
    content: str
    score: float


@dataclass(frozen=True, slots=True)
class RerankResult:
    chunk_id: UUID
    score: float


class RerankerPort(Protocol):
    async def rerank(
        self,
        *,
        query: str,
        candidates: list[RerankCandidate],
        top_n: int,
    ) -> list[RerankResult]: ...


__all__ = ["RerankCandidate", "RerankResult", "RerankerPort"]
