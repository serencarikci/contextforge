"""Structure-aware semantic text chunker for embedding preparation."""

from __future__ import annotations

import re
from dataclasses import dataclass

from contextforge.modules.documents.domain.entities.document_chunk import ChunkDraft
from contextforge.modules.documents.domain.enums import DocumentFormat
from contextforge.modules.documents.domain.exceptions import DocumentChunkError
from contextforge.shared.types.aliases import JSONValue

_HEADING_RE = re.compile(r"(?m)^(#{1,6})\s+(.+?)\s*$")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ\"'(\[])")
_WHITESPACE_RE = re.compile(r"[ \t]+")


@dataclass(frozen=True, slots=True)
class ChunkerConfig:
    target_chars: int = 1200
    max_chars: int = 1800
    min_chars: int = 100
    overlap_chars: int = 150


@dataclass(frozen=True, slots=True)
class _Unit:
    text: str
    start: int
    end: int
    section_title: str | None


class SemanticTextChunker:
    """Split text on headings/paragraphs/sentences, then pack with overlap."""

    def __init__(self, config: ChunkerConfig | None = None) -> None:
        self._config = config or ChunkerConfig()

    def chunk(
        self,
        *,
        text: str,
        format: DocumentFormat,
        document_metadata: dict[str, JSONValue],
    ) -> list[ChunkDraft]:
        normalized = _normalize_text(text)
        if not normalized:
            raise DocumentChunkError("Cannot chunk empty document text.")

        units = _split_semantic_units(normalized, format=format)
        if not units:
            raise DocumentChunkError("Document text produced no semantic units.")

        packed = self._pack_units(units)
        if not packed:
            raise DocumentChunkError("Document text produced no chunks.")

        drafts: list[ChunkDraft] = []
        for index, (content, start, end, section_title) in enumerate(packed):
            metadata: dict[str, JSONValue] = {
                "source_format": format.value,
                "chunker": "semantic_text_v1",
                **{
                    key: value
                    for key, value in document_metadata.items()
                    if key
                    in {
                        "document_title",
                        "document_filename",
                        "document_content_type",
                        "parse_title",
                        "parse_author",
                    }
                },
            }
            if section_title:
                metadata["section_title"] = section_title
            drafts.append(
                ChunkDraft(
                    index=index,
                    content=content,
                    char_start=start,
                    char_end=end,
                    metadata=metadata,
                )
            )
        return drafts

    def _pack_units(self, units: list[_Unit]) -> list[tuple[str, int, int, str | None]]:
        config = self._config
        chunks: list[tuple[str, int, int, str | None]] = []
        buffer_parts: list[str] = []
        buffer_start: int | None = None
        buffer_end: int | None = None
        buffer_section: str | None = None
        buffer_len = 0

        def flush() -> None:
            nonlocal buffer_parts, buffer_start, buffer_end, buffer_section, buffer_len
            if not buffer_parts or buffer_start is None or buffer_end is None:
                return
            content = "\n\n".join(buffer_parts).strip()
            if content:
                chunks.append((content, buffer_start, buffer_end, buffer_section))
            buffer_parts = []
            buffer_start = None
            buffer_end = None
            buffer_section = None
            buffer_len = 0

        for unit in units:
            unit_text = unit.text.strip()
            if not unit_text:
                continue
            unit_len = len(unit_text)

            if unit_len > config.max_chars:
                flush()
                for piece_start, piece_end, piece in _split_oversized(
                    unit_text, unit.start, config.max_chars, config.overlap_chars
                ):
                    chunks.append((piece, piece_start, piece_end, unit.section_title))
                continue

            projected = unit_len if buffer_len == 0 else buffer_len + 2 + unit_len
            if buffer_parts and projected > config.target_chars:
                flush()

            if not buffer_parts:
                buffer_start = unit.start
                buffer_section = unit.section_title
            buffer_parts.append(unit_text)
            buffer_end = unit.end
            buffer_len = projected if buffer_len else unit_len

            if buffer_len >= config.target_chars:
                flush()

        flush()

        if config.overlap_chars > 0 and len(chunks) > 1:
            chunks = _apply_overlap(chunks, config.overlap_chars)

        return [
            (content, start, end, section)
            for content, start, end, section in chunks
            if len(content) >= min(config.min_chars, 1)
        ]


def _normalize_text(text: str) -> str:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = _WHITESPACE_RE.sub(" ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _split_semantic_units(text: str, *, format: DocumentFormat) -> list[_Unit]:
    if format is DocumentFormat.MARKDOWN and _HEADING_RE.search(text):
        return _split_markdown_sections(text)
    return _split_paragraphs(text)


def _split_markdown_sections(text: str) -> list[_Unit]:
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        return _split_paragraphs(text)

    units: list[_Unit] = []
    first = matches[0]
    if first.start() > 0:
        preamble = text[: first.start()].strip()
        if preamble:
            units.extend(_units_from_block(preamble, 0, section_title=None))

    for index, match in enumerate(matches):
        section_title = match.group(2).strip()
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.start() : body_end].strip()
        if not block:
            continue
        absolute_start = text.find(block, match.start(), body_end)
        if absolute_start < 0:
            absolute_start = match.start()
        units.extend(_units_from_block(block, absolute_start, section_title=section_title))
    return units


def _split_paragraphs(text: str) -> list[_Unit]:
    units: list[_Unit] = []
    cursor = 0
    for raw in re.split(r"\n\s*\n", text):
        paragraph = raw.strip()
        if not paragraph:
            cursor += len(raw) + 2
            continue
        start = text.find(paragraph, cursor)
        if start < 0:
            start = cursor
        units.extend(_units_from_block(paragraph, start, section_title=None))
        cursor = start + len(paragraph)
    return units


def _units_from_block(block: str, absolute_start: int, *, section_title: str | None) -> list[_Unit]:
    if len(block) <= 900:
        return [
            _Unit(
                text=block,
                start=absolute_start,
                end=absolute_start + len(block),
                section_title=section_title,
            )
        ]

    units: list[_Unit] = []
    cursor = 0
    sentences = _SENTENCE_RE.split(block)
    if len(sentences) == 1:
        return [
            _Unit(
                text=block,
                start=absolute_start,
                end=absolute_start + len(block),
                section_title=section_title,
            )
        ]

    for sentence in sentences:
        piece = sentence.strip()
        if not piece:
            continue
        local = block.find(piece, cursor)
        if local < 0:
            local = cursor
        start = absolute_start + local
        units.append(
            _Unit(
                text=piece,
                start=start,
                end=start + len(piece),
                section_title=section_title,
            )
        )
        cursor = local + len(piece)
    return units


def _split_oversized(
    text: str, absolute_start: int, max_chars: int, overlap_chars: int
) -> list[tuple[int, int, str]]:
    pieces: list[tuple[int, int, str]] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + max_chars, length)
        if end < length:
            window = text[start:end]
            split_at = max(window.rfind("\n"), window.rfind(" "), window.rfind(". "))
            if split_at > max_chars // 3:
                end = start + split_at + 1
        piece = text[start:end].strip()
        if piece:
            piece_start = absolute_start + start
            pieces.append((piece_start, piece_start + len(piece), piece))
        if end >= length:
            break
        start = max(end - overlap_chars, start + 1)
    return pieces


def _apply_overlap(
    chunks: list[tuple[str, int, int, str | None]], overlap_chars: int
) -> list[tuple[str, int, int, str | None]]:
    if overlap_chars <= 0 or len(chunks) < 2:
        return chunks

    result: list[tuple[str, int, int, str | None]] = [chunks[0]]
    for index in range(1, len(chunks)):
        prev_content, prev_start, _prev_end, _prev_section = result[-1]
        content, start, end, section = chunks[index]
        overlap = prev_content[-overlap_chars:].strip()
        if not overlap or content.startswith(overlap):
            result.append((content, start, end, section))
            continue
        merged = f"{overlap}\n\n{content}".strip()
        overlap_start = max(prev_start, start - len(overlap))
        result.append((merged, overlap_start, end, section))
    return result


__all__ = ["ChunkerConfig", "SemanticTextChunker"]
