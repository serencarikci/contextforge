"""Port for format-specific document parsing."""

from __future__ import annotations

from typing import Protocol

from contextforge.modules.documents.domain.entities.document_parse_result import (
    ExtractedDocumentContent,
)
from contextforge.modules.documents.domain.enums import DocumentFormat


class DocumentParserPort(Protocol):
    """Extracts plain text and metadata from raw document bytes."""

    def parse(
        self,
        *,
        format: DocumentFormat,
        data: bytes,
        filename: str,
    ) -> ExtractedDocumentContent:
        """Parse ``data`` for the given format.

        Implementations must raise ``DocumentParseError`` for corrupt or empty
        content, and ``UnsupportedDocumentFormatError`` for unknown formats.
        """
        ...


__all__ = ["DocumentParserPort"]
