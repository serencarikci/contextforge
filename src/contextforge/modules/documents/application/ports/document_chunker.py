from __future__ import annotations

from typing import Protocol

from contextforge.modules.documents.domain.entities.document_chunk import ChunkDraft
from contextforge.modules.documents.domain.enums import DocumentFormat
from contextforge.shared.types.aliases import JSONValue


class DocumentChunkerPort(Protocol):
    def chunk(
        self,
        *,
        text: str,
        format: DocumentFormat,
        document_metadata: dict[str, JSONValue],
    ) -> list[ChunkDraft]: ...


__all__ = ["DocumentChunkerPort"]
