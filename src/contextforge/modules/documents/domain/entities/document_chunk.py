"""Document chunk entity prepared for embedding and retrieval."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from contextforge.modules.documents.domain.enums import ChunkEmbeddingStatus
from contextforge.shared.types.aliases import JSONValue
from contextforge.shared.utilities.datetime import utc_now


def estimate_token_count(text: str) -> int:
    """Approximate token count for embedding planning (chars / 4)."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def content_sha256(text: str) -> str:
    """Stable hash used later for embedding deduplication."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ChunkDraft:
    """In-memory chunk produced by a text chunker before persistence."""

    index: int
    content: str
    char_start: int
    char_end: int
    metadata: dict[str, JSONValue] = field(default_factory=dict)

    @property
    def token_count(self) -> int:
        return estimate_token_count(self.content)

    @property
    def content_hash(self) -> str:
        return content_sha256(self.content)


@dataclass(slots=True)
class DocumentChunk:
    """Persisted semantic chunk ready for embedding generation."""

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
    id: UUID = field(default_factory=uuid4)
    metadata: dict[str, JSONValue] = field(default_factory=dict)
    embedding_status: ChunkEmbeddingStatus = ChunkEmbeddingStatus.PENDING
    language: str | None = None
    embedding_model: str | None = None
    embedding_dimensions: int | None = None
    embedded_at: datetime | None = None
    embedding_error: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @classmethod
    def from_draft(
        cls,
        draft: ChunkDraft,
        *,
        organization_id: UUID,
        document_id: UUID,
        parse_result_id: UUID,
        knowledge_space_id: UUID,
    ) -> DocumentChunk:
        return cls(
            organization_id=organization_id,
            document_id=document_id,
            parse_result_id=parse_result_id,
            knowledge_space_id=knowledge_space_id,
            chunk_index=draft.index,
            content=draft.content,
            content_hash=draft.content_hash,
            char_start=draft.char_start,
            char_end=draft.char_end,
            token_count=draft.token_count,
            metadata=dict(draft.metadata),
            embedding_status=ChunkEmbeddingStatus.PENDING,
        )

    def mark_embedded(
        self,
        *,
        language: str,
        model: str,
        dimensions: int,
    ) -> None:
        self.embedding_status = ChunkEmbeddingStatus.EMBEDDED
        self.language = language
        self.embedding_model = model
        self.embedding_dimensions = dimensions
        self.embedded_at = utc_now()
        self.embedding_error = None
        self.updated_at = utc_now()

    def mark_embedding_failed(self, error_message: str) -> None:
        self.embedding_status = ChunkEmbeddingStatus.FAILED
        self.embedding_error = error_message[:2000]
        self.embedded_at = None
        self.updated_at = utc_now()


__all__ = [
    "ChunkDraft",
    "DocumentChunk",
    "content_sha256",
    "estimate_token_count",
]
