"""Document request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from contextforge.modules.documents.domain.enums import (
    ChunkEmbeddingStatus,
    DocumentFormat,
    DocumentParseStatus,
    DocumentStatus,
)


class DocumentMetadataUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    knowledge_space_id: UUID
    title: str
    filename: str
    content_type: str
    size_bytes: int
    checksum_sha256: str | None
    status: DocumentStatus
    uploaded_by_user_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class DocumentParseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    document_id: UUID
    format: DocumentFormat
    status: DocumentParseStatus
    extracted_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    character_count: int
    page_count: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    parsed_at: datetime
    created_at: datetime
    updated_at: datetime


class DocumentChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    document_id: UUID
    parse_result_id: UUID
    knowledge_space_id: UUID
    chunk_index: int
    content: str
    content_hash: str
    char_start: int
    char_end: int
    token_count: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding_status: ChunkEmbeddingStatus
    language: str | None = None
    embedding_model: str | None = None
    embedding_dimensions: int | None = None
    embedded_at: datetime | None = None
    embedding_error: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentChunkListResponse(BaseModel):
    items: list[DocumentChunkResponse]
    total: int


class DocumentEmbeddingResponse(BaseModel):
    document_id: UUID
    model: str
    dimensions: int
    language: str
    embedded_count: int
    failed_count: int
    skipped_count: int
    items: list[DocumentChunkResponse]


__all__ = [
    "DocumentChunkListResponse",
    "DocumentChunkResponse",
    "DocumentEmbeddingResponse",
    "DocumentMetadataUpdateRequest",
    "DocumentParseResponse",
    "DocumentResponse",
]
