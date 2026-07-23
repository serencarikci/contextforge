"""Document domain exceptions."""

from __future__ import annotations

from contextforge.domain.exceptions.base import DomainError


class UnsupportedDocumentFormatError(DomainError):
    """Raised when a document format is not supported by the parsing pipeline."""

    code = "UNSUPPORTED_DOCUMENT_FORMAT"


class DocumentParseError(DomainError):
    """Raised when document bytes cannot be parsed into text."""

    code = "DOCUMENT_PARSE_FAILED"


class DocumentChunkError(DomainError):
    """Raised when parsed text cannot be split into usable chunks."""

    code = "DOCUMENT_CHUNK_FAILED"


class DocumentEmbeddingError(DomainError):
    """Raised when embedding generation or vector persistence fails."""

    code = "DOCUMENT_EMBEDDING_FAILED"


class TransientEmbeddingError(DomainError):
    """Raised for retryable embedding provider failures."""

    code = "EMBEDDING_PROVIDER_TRANSIENT"


class PermanentEmbeddingError(DomainError):
    """Raised for non-retryable embedding provider failures."""

    code = "EMBEDDING_PROVIDER_ERROR"


__all__ = [
    "DocumentChunkError",
    "DocumentEmbeddingError",
    "DocumentParseError",
    "PermanentEmbeddingError",
    "TransientEmbeddingError",
    "UnsupportedDocumentFormatError",
]
