"""Composite document parser dispatching by detected format."""

from __future__ import annotations

from contextforge.modules.documents.domain.entities.document_parse_result import (
    ExtractedDocumentContent,
)
from contextforge.modules.documents.domain.enums import DocumentFormat
from contextforge.modules.documents.domain.exceptions import UnsupportedDocumentFormatError
from contextforge.modules.documents.infrastructure.parsing.docx_parser import parse_docx
from contextforge.modules.documents.infrastructure.parsing.html_parser import parse_html
from contextforge.modules.documents.infrastructure.parsing.markdown_parser import parse_markdown
from contextforge.modules.documents.infrastructure.parsing.pdf_parser import parse_pdf


class CompositeDocumentParser:
    """Routes parse requests to the matching format-specific extractor."""

    def parse(
        self,
        *,
        format: DocumentFormat,
        data: bytes,
        filename: str,
    ) -> ExtractedDocumentContent:
        del filename
        if format is DocumentFormat.PDF:
            return parse_pdf(data)
        if format is DocumentFormat.DOCX:
            return parse_docx(data)
        if format is DocumentFormat.HTML:
            return parse_html(data)
        if format is DocumentFormat.MARKDOWN:
            return parse_markdown(data)
        raise UnsupportedDocumentFormatError(f"Unsupported document format: {format.value}")


__all__ = ["CompositeDocumentParser"]
