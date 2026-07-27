"""BM25 lexical search adapters."""

from __future__ import annotations

import re
from uuid import UUID

from rank_bm25 import BM25Okapi  # type: ignore[import-untyped]
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from contextforge.application.ports.lexical_search import LexicalDocument, LexicalSearchHit
from contextforge.modules.documents.infrastructure.models.document import DocumentModel
from contextforge.modules.documents.infrastructure.models.document_chunk import DocumentChunkModel
from contextforge.modules.documents.infrastructure.models.document_parse_result import (
    DocumentParseResultModel,
)

_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text) if token]


def bm25_search(
    query: str,
    documents: list[LexicalDocument],
    *,
    top_k: int,
) -> list[LexicalSearchHit]:
    if not documents or top_k < 1:
        return []
    query_tokens = tokenize(query)
    corpus = [tokenize(doc.content) for doc in documents]
    if not query_tokens or not any(corpus):
        return []
    bm25 = BM25Okapi(corpus)
    scores = [float(score) for score in bm25.get_scores(query_tokens)]
    if max(scores, default=0.0) <= 0.0:
        scores = [float(len(set(query_tokens) & set(tokens))) for tokens in corpus]
    ranked = sorted(
        zip(documents, scores, strict=True),
        key=lambda item: item[1],
        reverse=True,
    )
    hits: list[LexicalSearchHit] = []
    for document, score in ranked[:top_k]:
        if score <= 0:
            continue
        hits.append(
            LexicalSearchHit(
                chunk_id=document.chunk_id,
                organization_id=document.organization_id,
                document_id=document.document_id,
                knowledge_space_id=document.knowledge_space_id,
                score=score,
                content=document.content,
                chunk_index=document.chunk_index,
                document_title=document.document_title,
                char_start=document.char_start,
                char_end=document.char_end,
                page_count=document.page_count,
            )
        )
    return hits


class InMemoryLexicalSearch:
    """Process-local BM25 index used by unit/API tests."""

    def __init__(self, documents: list[LexicalDocument] | None = None) -> None:
        self._documents = list(documents or [])

    def replace(self, documents: list[LexicalDocument]) -> None:
        self._documents = list(documents)

    async def search(
        self,
        *,
        organization_id: UUID,
        query: str,
        knowledge_space_ids: list[UUID],
        top_k: int,
        corpus_limit: int,
    ) -> list[LexicalSearchHit]:
        allowed = set(knowledge_space_ids)
        scoped = [
            document
            for document in self._documents
            if document.organization_id == organization_id
            and document.knowledge_space_id in allowed
        ][:corpus_limit]
        return bm25_search(query, scoped, top_k=top_k)


class PostgresBm25LexicalSearch:
    """Loads authorized chunks from PostgreSQL and ranks them with Okapi BM25."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def search(
        self,
        *,
        organization_id: UUID,
        query: str,
        knowledge_space_ids: list[UUID],
        top_k: int,
        corpus_limit: int,
    ) -> list[LexicalSearchHit]:
        if not knowledge_space_ids:
            return []
        documents = await self._load_corpus(
            organization_id=organization_id,
            knowledge_space_ids=knowledge_space_ids,
            corpus_limit=corpus_limit,
        )
        return bm25_search(query, documents, top_k=top_k)

    async def _load_corpus(
        self,
        *,
        organization_id: UUID,
        knowledge_space_ids: list[UUID],
        corpus_limit: int,
    ) -> list[LexicalDocument]:
        statement = (
            select(
                DocumentChunkModel,
                DocumentModel.title,
                DocumentParseResultModel.page_count,
            )
            .join(
                DocumentModel,
                and_(
                    DocumentModel.id == DocumentChunkModel.document_id,
                    DocumentModel.organization_id == DocumentChunkModel.organization_id,
                ),
            )
            .outerjoin(
                DocumentParseResultModel,
                and_(
                    DocumentParseResultModel.document_id == DocumentChunkModel.document_id,
                    DocumentParseResultModel.organization_id == DocumentChunkModel.organization_id,
                ),
            )
            .where(
                and_(
                    DocumentChunkModel.organization_id == organization_id,
                    DocumentChunkModel.knowledge_space_id.in_(knowledge_space_ids),
                )
            )
            .order_by(DocumentChunkModel.created_at.desc())
            .limit(corpus_limit)
        )
        async with self._session_factory() as session:
            result = await session.execute(statement)
            rows = result.all()
        documents: list[LexicalDocument] = []
        for chunk, title, page_count in rows:
            documents.append(
                LexicalDocument(
                    chunk_id=chunk.id,
                    organization_id=chunk.organization_id,
                    document_id=chunk.document_id,
                    knowledge_space_id=chunk.knowledge_space_id,
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    document_title=title,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    page_count=page_count,
                )
            )
        return documents


__all__ = [
    "InMemoryLexicalSearch",
    "PostgresBm25LexicalSearch",
    "bm25_search",
    "tokenize",
]
