"""RAG API request/response schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RagQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    knowledge_space_ids: list[UUID] | None = None
    language: str | None = Field(default=None, min_length=2, max_length=8)
    top_k: int | None = Field(default=None, ge=1, le=100)


class RagSearchRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    knowledge_space_ids: list[UUID] | None = None
    language: str | None = Field(default=None, min_length=2, max_length=8)
    top_k: int | None = Field(default=None, ge=1, le=100)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class CitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: UUID
    document_title: str
    chunk_id: UUID
    knowledge_space_id: UUID
    page: int | None = None
    chunk_index: int | None = None
    snippet: str | None = None


class RagDiagnosticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class RetrievedChunkResponse(BaseModel):
    chunk_id: UUID
    document_id: UUID
    knowledge_space_id: UUID
    score: float
    chunk_index: int
    document_title: str | None = None
    page: int | None = None
    snippet: str | None = None


class RagSearchResponse(BaseModel):
    items: list[RetrievedChunkResponse]
    diagnostics: RagDiagnosticsResponse


class RagQueryResponse(BaseModel):
    answer: str
    language: str
    citations: list[CitationResponse]
    diagnostics: RagDiagnosticsResponse | None = None
