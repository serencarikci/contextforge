from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    chunk_id: UUID
    organization_id: UUID
    document_id: UUID
    knowledge_space_id: UUID
    content: str
    score: float
    dense_score: float | None = None
    lexical_score: float | None = None
    chunk_index: int = 0
    document_title: str | None = None
    char_start: int | None = None
    char_end: int | None = None
    page_count: int | None = None
    page: int | None = None


@dataclass(frozen=True, slots=True)
class Citation:
    document_id: UUID
    document_title: str
    chunk_id: UUID
    knowledge_space_id: UUID
    page: int | None = None
    chunk_index: int | None = None
    snippet: str | None = None


@dataclass(frozen=True, slots=True)
class RagDiagnostics:
    retrieval_ms: float
    rerank_ms: float
    prompt_build_ms: float
    llm_ms: float
    total_ms: float
    retrieved_chunk_count: int
    context_chunk_count: int
    context_chars: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True, slots=True)
class RagAnswer:
    answer: str
    language: str
    citations: list[Citation] = field(default_factory=list)
    diagnostics: RagDiagnostics | None = None


__all__ = ["Citation", "RagAnswer", "RagDiagnostics", "RetrievedChunk"]
