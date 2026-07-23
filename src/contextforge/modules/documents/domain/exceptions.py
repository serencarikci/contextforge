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


__all__ = [
    "DocumentChunkError",
    "DocumentParseError",
    "UnsupportedDocumentFormatError",
]
