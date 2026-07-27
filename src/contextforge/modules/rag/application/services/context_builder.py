"""Context packing and citation builders."""

from __future__ import annotations

from contextforge.modules.rag.application.security.prompt_guard import build_context_block
from contextforge.modules.rag.domain.types import Citation, RetrievedChunk
from contextforge.shared.utilities.tokens import estimate_tokens


def select_context_chunks(
    chunks: list[RetrievedChunk],
    *,
    max_tokens: int,
    max_chunks: int,
) -> list[RetrievedChunk]:
    selected: list[RetrievedChunk] = []
    used = 0
    for chunk in chunks:
        if len(selected) >= max_chunks:
            break
        tokens = estimate_tokens(chunk.content)
        if selected and used + tokens > max_tokens:
            continue
        selected.append(chunk)
        used += tokens
    return selected


def build_citations(chunks: list[RetrievedChunk], *, snippet_chars: int = 240) -> list[Citation]:
    citations: list[Citation] = []
    for chunk in chunks:
        title = chunk.document_title or "Untitled document"
        snippet = chunk.content.strip().replace("\n", " ")
        if len(snippet) > snippet_chars:
            snippet = snippet[: snippet_chars - 1] + "…"
        citations.append(
            Citation(
                document_id=chunk.document_id,
                document_title=title,
                chunk_id=chunk.chunk_id,
                knowledge_space_id=chunk.knowledge_space_id,
                page=chunk.page,
                chunk_index=chunk.chunk_index,
                snippet=snippet,
            )
        )
    return citations


def format_context(chunks: list[RetrievedChunk]) -> str:
    pairs = [(str(chunk.chunk_id), chunk.content) for chunk in chunks]
    numbered = []
    for chunk in chunks:
        marker = f"[cite:{chunk.chunk_id}]"
        numbered.append((str(chunk.chunk_id), f"{marker}\n{chunk.content}"))
    return build_context_block(numbered if numbered else pairs)


__all__ = ["build_citations", "format_context", "select_context_chunks"]
