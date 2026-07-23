"""Port for splitting parsed document text into semantic chunks."""

from __future__ import annotations

from typing import Protocol

from contextforge.modules.documents.domain.entities.document_chunk import ChunkDraft
from contextforge.modules.documents.domain.enums import DocumentFormat
from contextforge.shared.types.aliases import JSONValue


class DocumentChunkerPort(Protocol):
    """Splits extracted text into overlapping semantic chunks."""

    def chunk(
        self,
        *,
        text: str,
        format: DocumentFormat,
        document_metadata: dict[str, JSONValue],
    ) -> list[ChunkDraft]:
        """Return ordered chunk drafts for embedding and retrieval."""
        ...


__all__ = ["DocumentChunkerPort"]
