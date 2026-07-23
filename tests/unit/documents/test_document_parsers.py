"""Unit tests for format detection and format-specific parsers."""

from __future__ import annotations

import base64
from io import BytesIO

import pytest
from docx import Document as DocxDocument
from pypdf import PdfWriter

from contextforge.modules.documents.domain.enums import DocumentFormat
from contextforge.modules.documents.domain.exceptions import (
    DocumentParseError,
    UnsupportedDocumentFormatError,
)
from contextforge.modules.documents.domain.format_detection import detect_document_format
from contextforge.modules.documents.infrastructure.parsing.composite_parser import (
    CompositeDocumentParser,
)
from contextforge.modules.documents.infrastructure.parsing.docx_parser import parse_docx
from contextforge.modules.documents.infrastructure.parsing.html_parser import parse_html
from contextforge.modules.documents.infrastructure.parsing.markdown_parser import parse_markdown
from contextforge.modules.documents.infrastructure.parsing.pdf_parser import parse_pdf

_MINIMAL_PDF = base64.b64decode(
    "JVBERi0xLjQKMSAwIG9iajw8IC9UeXBlIC9DYXRhbG9nIC9QYWdlcyAyIDAgUiA+PmVuZG9iagoyIDAg"
    "b2JqPDwgL1R5cGUgL1BhZ2VzIC9LaWRzIFszIDAgUl0gL0NvdW50IDEgPj5lbmRvYmoKMyAwIG9iajw8"
    "IC9UeXBlIC9QYWdlIC9QYXJlbnQgMiAwIFIgL01lZGlhQm94IFswIDAgMzAwIDE0NF0gL0NvbnRlbnRz"
    "IDQgMCBSIC9SZXNvdXJjZXM8PCAvRm9udDw8IC9GMSA1IDAgUiA+PiA+PiA+PmVuZG9iago0IDAgb2Jq"
    "PDwgL0xlbmd0aCA0MCA+PnN0cmVhbQpCVCAvRjEgMjQgVGYgNTAgNTAgVGQgKEhlbGxvIFBERikgVGog"
    "RVQKZW5kc3RyZWFtCmVuZG9iago1IDAgb2JqPDwgL1R5cGUgL0ZvbnQgL1N1YnR5cGUgL1R5cGUxIC9C"
    "YXNlRm9udCAvSGVsdmV0aWNhID4+ZW5kb2JqCnhyZWYKMCA2CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAw"
    "MDAwMDAwOSAwMDAwMCBuIAowMDAwMDAwMDU2IDAwMDAwIG4gCjAwMDAwMDAxMTEgMDAwMDAgbiAKMDAw"
    "MDAwMDIzMyAwMDAwMCBuIAowMDAwMDAwMzIwIDAwMDAwIG4gCnRyYWlsZXI8PCAvU2l6ZSA2IC9Sb290"
    "IDEgMCBSID4+CnN0YXJ0eHJlZgozODgKJSVFT0YK"
)


def _docx_bytes(text: str) -> bytes:
    document = DocxDocument()
    document.add_paragraph(text)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


@pytest.mark.unit
class TestDetectDocumentFormat:
    def test_detects_by_extension(self) -> None:
        assert (
            detect_document_format(filename="notes.MD", content_type="application/octet-stream")
            is DocumentFormat.MARKDOWN
        )

    def test_detects_by_content_type_when_extension_unknown(self) -> None:
        assert (
            detect_document_format(filename="blob", content_type="application/pdf")
            is DocumentFormat.PDF
        )

    def test_unsupported_raises(self) -> None:
        with pytest.raises(UnsupportedDocumentFormatError):
            detect_document_format(filename="archive.zip", content_type="application/zip")


@pytest.mark.unit
class TestFormatParsers:
    def test_parse_markdown_with_front_matter(self) -> None:
        payload = b"---\ntitle: Spec\nauthor: Ada\n---\n\n# Hello\n\nBody text.\n"
        result = parse_markdown(payload)
        assert "Hello" in result.text
        assert result.metadata["title"] == "Spec"
        assert result.metadata["author"] == "Ada"

    def test_parse_markdown_rejects_empty(self) -> None:
        with pytest.raises(DocumentParseError):
            parse_markdown(b"---\ntitle: Only Meta\n---\n\n")

    def test_parse_html_strips_scripts(self) -> None:
        html = b"<html><head><title>Page</title><script>evil()</script></head>"
        html += b"<body><p>Visible</p></body></html>"
        result = parse_html(html)
        assert "Visible" in result.text
        assert result.metadata["title"] == "Page"
        assert "evil" not in result.text

    def test_parse_html_rejects_empty(self) -> None:
        with pytest.raises(DocumentParseError):
            parse_html(b"<html><body><script>x</script></body></html>")

    def test_parse_docx(self) -> None:
        result = parse_docx(_docx_bytes("Hello DOCX"))
        assert "Hello DOCX" in result.text

    def test_parse_docx_rejects_corrupt(self) -> None:
        with pytest.raises(DocumentParseError):
            parse_docx(b"not-a-docx")

    def test_parse_pdf(self) -> None:
        result = parse_pdf(_MINIMAL_PDF)
        assert "Hello PDF" in result.text
        assert result.page_count == 1

    def test_parse_pdf_rejects_blank(self) -> None:
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        buffer = BytesIO()
        writer.write(buffer)
        with pytest.raises(DocumentParseError):
            parse_pdf(buffer.getvalue())

    def test_composite_dispatches(self) -> None:
        parser = CompositeDocumentParser()
        md = parser.parse(
            format=DocumentFormat.MARKDOWN,
            data=b"# Title\n\nBody",
            filename="a.md",
        )
        assert "Body" in md.text
