"""Markdown text extraction with optional YAML-like front matter."""

from __future__ import annotations

import re

from contextforge.modules.documents.domain.entities.document_parse_result import (
    ExtractedDocumentContent,
)
from contextforge.modules.documents.domain.exceptions import DocumentParseError
from contextforge.shared.types.aliases import JSONValue

_FRONT_MATTER_RE = re.compile(
    r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z",
    re.DOTALL,
)


def parse_markdown(data: bytes) -> ExtractedDocumentContent:
    """Decode Markdown bytes and extract optional front-matter metadata."""
    if not data:
        raise DocumentParseError("Markdown content is empty.")

    try:
        try:
            decoded = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DocumentParseError("Markdown content is not valid UTF-8.") from exc

        metadata: dict[str, JSONValue] = {"parser": "markdown"}
        body = decoded
        match = _FRONT_MATTER_RE.match(decoded)
        if match is not None:
            front_matter, body = match.group(1), match.group(2)
            metadata.update(_parse_simple_front_matter(front_matter))

        text = body.strip()
        if not text:
            raise DocumentParseError("Markdown produced no extractable text.")

        return ExtractedDocumentContent(text=text, metadata=metadata, page_count=None)
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError(f"Failed to parse Markdown: {exc}") from exc


def _parse_simple_front_matter(block: str) -> dict[str, JSONValue]:
    """Parse simple ``key: value`` front-matter lines (no nested YAML)."""
    result: dict[str, JSONValue] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", maxsplit=1)
        cleaned_key = key.strip()
        cleaned_value = value.strip().strip("\"'")
        if cleaned_key and cleaned_value:
            result[cleaned_key] = cleaned_value
    return result
