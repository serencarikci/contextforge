from __future__ import annotations

from contextforge.domain.exceptions.base import DomainError


class UnsupportedDocumentFormatError(DomainError):
    code = "UNSUPPORTED_DOCUMENT_FORMAT"


class DocumentParseError(DomainError):
    code = "DOCUMENT_PARSE_FAILED"


class DocumentChunkError(DomainError):
    code = "DOCUMENT_CHUNK_FAILED"


class DocumentEmbeddingError(DomainError):
    code = "DOCUMENT_EMBEDDING_FAILED"


class TransientEmbeddingError(DomainError):
    code = "EMBEDDING_PROVIDER_TRANSIENT"


class PermanentEmbeddingError(DomainError):
    code = "EMBEDDING_PROVIDER_ERROR"


__all__ = [
    "DocumentChunkError",
    "DocumentEmbeddingError",
    "DocumentParseError",
    "PermanentEmbeddingError",
    "TransientEmbeddingError",
    "UnsupportedDocumentFormatError",
]
