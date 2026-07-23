"""HTML text extraction using BeautifulSoup."""

from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from contextforge.modules.documents.domain.entities.document_parse_result import (
    ExtractedDocumentContent,
)
from contextforge.modules.documents.domain.exceptions import DocumentParseError
from contextforge.shared.types.aliases import JSONValue


def parse_html(data: bytes) -> ExtractedDocumentContent:
    """Extract visible text and basic metadata from an HTML byte payload."""
    if not data:
        raise DocumentParseError("HTML content is empty.")

    try:
        try:
            decoded = data.decode("utf-8")
        except UnicodeDecodeError:
            decoded = data.decode("utf-8", errors="replace")

        soup = BeautifulSoup(decoded, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else None
        text = soup.get_text(separator="\n", strip=True)
        text = "\n".join(line for line in text.splitlines() if line.strip()).strip()
        if not text:
            raise DocumentParseError("HTML produced no extractable text.")

        metadata: dict[str, JSONValue] = {"parser": "beautifulsoup4"}
        if title:
            metadata["title"] = title
        description = _meta_content(soup, "description")
        if description:
            metadata["description"] = description
        author = _meta_content(soup, "author")
        if author:
            metadata["author"] = author

        return ExtractedDocumentContent(text=text, metadata=metadata, page_count=None)
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError(f"Failed to parse HTML: {exc}") from exc


def _meta_content(soup: BeautifulSoup, name: str) -> str | None:
    tag = soup.find("meta", attrs={"name": name})
    if not isinstance(tag, Tag):
        return None
    content = tag.get("content")
    if content is None:
        return None
    text = str(content).strip()
    return text or None
