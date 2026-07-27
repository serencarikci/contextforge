from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class LexicalSearchHit:
    chunk_id: UUID
    organization_id: UUID
    document_id: UUID
    knowledge_space_id: UUID
    score: float
    content: str
    chunk_index: int
    document_title: str | None = None
    char_start: int | None = None
    char_end: int | None = None
    page_count: int | None = None


@dataclass(frozen=True, slots=True)
class LexicalDocument:
    chunk_id: UUID
    organization_id: UUID
    document_id: UUID
    knowledge_space_id: UUID
    content: str
    chunk_index: int
    document_title: str | None = None
    char_start: int | None = None
    char_end: int | None = None
    page_count: int | None = None


class LexicalSearchPort(Protocol):
    async def search(
        self,
        *,
        organization_id: UUID,
        query: str,
        knowledge_space_ids: list[UUID],
        top_k: int,
        corpus_limit: int,
    ) -> list[LexicalSearchHit]: ...


__all__ = ["LexicalDocument", "LexicalSearchHit", "LexicalSearchPort"]
