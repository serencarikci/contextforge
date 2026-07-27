from __future__ import annotations

from typing import Protocol

from contextforge.modules.documents.domain.entities.document_parse_result import (
    ExtractedDocumentContent,
)
from contextforge.modules.documents.domain.enums import DocumentFormat


class DocumentParserPort(Protocol):
    def parse(
        self,
        *,
        format: DocumentFormat,
        data: bytes,
        filename: str,
    ) -> ExtractedDocumentContent: ...


__all__ = ["DocumentParserPort"]
