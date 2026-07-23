"""DOCX text extraction using python-docx."""

from __future__ import annotations

from io import BytesIO

from docx import Document as DocxDocument

from contextforge.modules.documents.domain.entities.document_parse_result import (
    ExtractedDocumentContent,
)
from contextforge.modules.documents.domain.exceptions import DocumentParseError
from contextforge.shared.types.aliases import JSONValue


def parse_docx(data: bytes) -> ExtractedDocumentContent:
    """Extract text and core properties from a DOCX byte payload."""
    if not data:
        raise DocumentParseError("DOCX content is empty.")

    try:
        document = DocxDocument(BytesIO(data))
        paragraphs = [p.text.strip() for p in document.paragraphs if p.text and p.text.strip()]
        text = "\n\n".join(paragraphs).strip()
        if not text:
            raise DocumentParseError("DOCX produced no extractable text.")

        metadata: dict[str, JSONValue] = {"parser": "python-docx"}
        props = document.core_properties
        if props.title:
            metadata["title"] = str(props.title).strip()
        if props.author:
            metadata["author"] = str(props.author).strip()
        if props.subject:
            metadata["subject"] = str(props.subject).strip()
        if props.keywords:
            metadata["keywords"] = str(props.keywords).strip()

        return ExtractedDocumentContent(text=text, metadata=metadata, page_count=None)
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError(f"Failed to parse DOCX: {exc}") from exc
