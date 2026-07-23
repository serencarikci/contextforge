"""Format detection helpers for the document parsing pipeline."""

from __future__ import annotations

from pathlib import PurePosixPath

from contextforge.modules.documents.domain.enums import DocumentFormat
from contextforge.modules.documents.domain.exceptions import UnsupportedDocumentFormatError

_EXTENSION_TO_FORMAT: dict[str, DocumentFormat] = {
    ".pdf": DocumentFormat.PDF,
    ".docx": DocumentFormat.DOCX,
    ".html": DocumentFormat.HTML,
    ".htm": DocumentFormat.HTML,
    ".md": DocumentFormat.MARKDOWN,
    ".markdown": DocumentFormat.MARKDOWN,
}

_CONTENT_TYPE_TO_FORMAT: dict[str, DocumentFormat] = {
    "application/pdf": DocumentFormat.PDF,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentFormat.DOCX,
    "text/html": DocumentFormat.HTML,
    "application/xhtml+xml": DocumentFormat.HTML,
    "text/markdown": DocumentFormat.MARKDOWN,
    "text/x-markdown": DocumentFormat.MARKDOWN,
}


def detect_document_format(*, filename: str, content_type: str) -> DocumentFormat:
    """Detect a supported document format from filename and content type.

    Extension takes precedence when present; content type is the fallback.
    Raises ``UnsupportedDocumentFormatError`` when neither maps to a known format.
    """
    suffix = PurePosixPath(filename.strip()).suffix.lower()
    if suffix in _EXTENSION_TO_FORMAT:
        return _EXTENSION_TO_FORMAT[suffix]

    normalized_type = content_type.split(";", maxsplit=1)[0].strip().lower()
    if normalized_type in _CONTENT_TYPE_TO_FORMAT:
        return _CONTENT_TYPE_TO_FORMAT[normalized_type]

    raise UnsupportedDocumentFormatError(
        f"Unsupported document format for filename={filename!r} content_type={content_type!r}."
    )


__all__ = ["detect_document_format"]
