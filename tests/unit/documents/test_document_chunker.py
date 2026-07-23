"""Unit tests for the semantic text chunker."""

from __future__ import annotations

import pytest

from contextforge.modules.documents.domain.enums import DocumentFormat
from contextforge.modules.documents.domain.exceptions import DocumentChunkError
from contextforge.modules.documents.infrastructure.chunking.semantic_text_chunker import (
    ChunkerConfig,
    SemanticTextChunker,
)


def _long_paragraph(words: int = 400) -> str:
    return " ".join(f"word{i}" for i in range(words))


@pytest.mark.unit
class TestSemanticTextChunker:
    def test_splits_markdown_by_headings(self) -> None:
        text = (
            "# Intro\n\n"
            + _long_paragraph(80)
            + "\n\n# Details\n\n"
            + _long_paragraph(80)
            + "\n\n## Nested\n\n"
            + _long_paragraph(60)
        )
        chunker = SemanticTextChunker(ChunkerConfig(target_chars=400, max_chars=700, min_chars=20))
        drafts = chunker.chunk(
            text=text,
            format=DocumentFormat.MARKDOWN,
            document_metadata={"document_title": "Guide"},
        )
        assert len(drafts) >= 2
        assert drafts[0].index == 0
        assert all(draft.content_hash for draft in drafts)
        assert all(draft.token_count > 0 for draft in drafts)
        assert any(draft.metadata.get("section_title") == "Details" for draft in drafts)
        assert drafts[0].metadata["document_title"] == "Guide"
        assert drafts[0].metadata["source_format"] == "markdown"
        assert drafts[0].metadata["chunker"] == "semantic_text_v1"

    def test_packs_paragraphs_with_overlap(self) -> None:
        paragraphs = [_long_paragraph(120) for _ in range(6)]
        text = "\n\n".join(paragraphs)
        chunker = SemanticTextChunker(
            ChunkerConfig(target_chars=500, max_chars=800, overlap_chars=80, min_chars=20)
        )
        drafts = chunker.chunk(
            text=text,
            format=DocumentFormat.HTML,
            document_metadata={},
        )
        assert len(drafts) >= 2
        assert drafts[0].char_start == 0
        assert drafts[-1].char_end > drafts[0].char_end

    def test_rejects_empty_text(self) -> None:
        chunker = SemanticTextChunker()
        with pytest.raises(DocumentChunkError):
            chunker.chunk(text="   ", format=DocumentFormat.PDF, document_metadata={})
