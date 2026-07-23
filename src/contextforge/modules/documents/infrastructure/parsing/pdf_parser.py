"""PDF text extraction using pypdf."""

from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

from contextforge.modules.documents.domain.entities.document_parse_result import (
    ExtractedDocumentContent,
)
from contextforge.modules.documents.domain.exceptions import DocumentParseError
from contextforge.shared.types.aliases import JSONValue


def parse_pdf(data: bytes) -> ExtractedDocumentContent:
    """Extract text and document info from a PDF byte payload."""
    if not data:
        raise DocumentParseError("PDF content is empty.")

    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise DocumentParseError("Encrypted PDF files are not supported.")

        pages: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(page_text.strip())
        text = "\n\n".join(pages).strip()
        if not text:
            raise DocumentParseError("PDF produced no extractable text.")

        metadata: dict[str, JSONValue] = {"parser": "pypdf"}
        info = reader.metadata
        if info is not None:
            title = _meta_str(info.title)
            author = _meta_str(info.author)
            subject = _meta_str(info.subject)
            if title:
                metadata["title"] = title
            if author:
                metadata["author"] = author
            if subject:
                metadata["subject"] = subject

        return ExtractedDocumentContent(
            text=text,
            metadata=metadata,
            page_count=len(reader.pages),
        )
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError(f"Failed to parse PDF: {exc}") from exc


def _meta_str(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
