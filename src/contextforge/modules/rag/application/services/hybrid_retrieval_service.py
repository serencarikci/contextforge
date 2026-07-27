from __future__ import annotations

import time
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from contextforge.application.ports.embedding_provider import EmbeddingProviderPort
from contextforge.application.ports.lexical_search import LexicalSearchHit, LexicalSearchPort
from contextforge.application.ports.vector_store import VectorStorePort
from contextforge.modules.documents.infrastructure.models.document import DocumentModel
from contextforge.modules.documents.infrastructure.models.document_chunk import DocumentChunkModel
from contextforge.modules.documents.infrastructure.models.document_parse_result import (
    DocumentParseResultModel,
)
from contextforge.modules.rag.domain.fusion import (
    estimate_page_from_span,
    reciprocal_rank_fusion,
    weighted_fuse,
)
from contextforge.modules.rag.domain.types import RetrievedChunk
from contextforge.shared.config.settings import RagSettings
from contextforge.shared.logging.setup import get_logger

logger = get_logger(__name__)


class HybridRetrievalService:
    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProviderPort,
        vector_store: VectorStorePort,
        lexical_search: LexicalSearchPort,
        session_factory: async_sessionmaker[AsyncSession],
        settings: RagSettings,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store
        self._lexical_search = lexical_search
        self._session_factory = session_factory
        self._settings = settings

    async def retrieve(
        self,
        *,
        organization_id: UUID,
        query: str,
        knowledge_space_ids: list[UUID],
        top_k: int | None = None,
        limit: int | None = None,
        offset: int = 0,
        language: str | None = None,
    ) -> tuple[list[RetrievedChunk], float]:
        started = time.perf_counter()
        if not knowledge_space_ids:
            return [], 0.0

        effective_top_k = top_k or self._settings.top_k
        candidate_k = effective_top_k * self._settings.candidate_multiplier
        page_limit = limit if limit is not None else effective_top_k

        embedded = await self._embedding_provider.embed_texts(
            [query], language=language or self._settings.default_language
        )
        query_vector = embedded.vectors[0]

        dense_hits = await self._vector_store.search(
            organization_id=organization_id,
            query_vector=query_vector,
            knowledge_space_ids=knowledge_space_ids,
            top_k=candidate_k,
        )
        lexical_hits = await self._lexical_search.search(
            organization_id=organization_id,
            query=query,
            knowledge_space_ids=knowledge_space_ids,
            top_k=candidate_k,
            corpus_limit=self._settings.lexical_corpus_limit,
        )

        dense_scores = {hit.chunk_id: hit.score for hit in dense_hits}
        lexical_scores = {hit.chunk_id: hit.score for hit in lexical_hits}

        if self._settings.fusion_method == "rrf":
            fused = reciprocal_rank_fusion(
                [
                    [hit.chunk_id for hit in dense_hits],
                    [hit.chunk_id for hit in lexical_hits],
                ],
                k=self._settings.rrf_k,
            )
        else:
            fused = weighted_fuse(
                dense_scores,
                lexical_scores,
                dense_weight=self._settings.dense_weight,
                lexical_weight=self._settings.lexical_weight,
            )

        ordered_ids = [
            chunk_id
            for chunk_id, _score in sorted(fused.items(), key=lambda item: item[1], reverse=True)
        ]
        page_ids = ordered_ids[offset : offset + page_limit]
        hydrated = await self._hydrate_chunks(
            organization_id=organization_id,
            chunk_ids=page_ids,
            knowledge_space_ids=set(knowledge_space_ids),
            dense_scores=dense_scores,
            lexical_scores=lexical_scores,
            fused_scores=fused,
            dense_titles={hit.chunk_id: hit.document_title for hit in dense_hits},
            lexical_meta={hit.chunk_id: hit for hit in lexical_hits},
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "hybrid_retrieval_completed",
            extra={
                "organization_id": str(organization_id),
                "dense_hits": len(dense_hits),
                "lexical_hits": len(lexical_hits),
                "returned": len(hydrated),
                "retrieval_ms": elapsed_ms,
            },
        )
        return hydrated, elapsed_ms

    async def _hydrate_chunks(
        self,
        *,
        organization_id: UUID,
        chunk_ids: list[UUID],
        knowledge_space_ids: set[UUID],
        dense_scores: dict[UUID, float],
        lexical_scores: dict[UUID, float],
        fused_scores: dict[UUID, float],
        dense_titles: dict[UUID, str | None],
        lexical_meta: dict[UUID, LexicalSearchHit],
    ) -> list[RetrievedChunk]:
        if not chunk_ids:
            return []
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
                    DocumentChunkModel.id.in_(chunk_ids),
                )
            )
        )
        async with self._session_factory() as session:
            rows = (await session.execute(statement)).all()

        by_id = {chunk.id: (chunk, title, page_count) for chunk, title, page_count in rows}
        results: list[RetrievedChunk] = []
        for chunk_id in chunk_ids:
            row = by_id.get(chunk_id)
            if row is None:
                lexical = lexical_meta.get(chunk_id)
                if lexical is None:
                    continue
                if lexical.knowledge_space_id not in knowledge_space_ids:
                    continue
                page = estimate_page_from_span(
                    char_start=lexical.char_start,
                    char_end=lexical.char_end,
                    page_count=lexical.page_count,
                )
                results.append(
                    RetrievedChunk(
                        chunk_id=chunk_id,
                        organization_id=organization_id,
                        document_id=lexical.document_id,
                        knowledge_space_id=lexical.knowledge_space_id,
                        content=lexical.content,
                        score=fused_scores.get(chunk_id, 0.0),
                        dense_score=dense_scores.get(chunk_id),
                        lexical_score=lexical_scores.get(chunk_id),
                        chunk_index=lexical.chunk_index,
                        document_title=lexical.document_title or dense_titles.get(chunk_id),
                        char_start=lexical.char_start,
                        char_end=lexical.char_end,
                        page_count=lexical.page_count,
                        page=page,
                    )
                )
                continue

            chunk, title, page_count = row
            if chunk.knowledge_space_id not in knowledge_space_ids:
                continue
            page = estimate_page_from_span(
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                page_count=page_count,
            )
            if (
                page is None
                and page_count is not None
                and page_count > 0
                and chunk.char_start is not None
            ):
                page = max(1, min(page_count, (chunk.char_start // 1800) + 1))
            results.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    organization_id=chunk.organization_id,
                    document_id=chunk.document_id,
                    knowledge_space_id=chunk.knowledge_space_id,
                    content=chunk.content,
                    score=fused_scores.get(chunk.id, 0.0),
                    dense_score=dense_scores.get(chunk.id),
                    lexical_score=lexical_scores.get(chunk.id),
                    chunk_index=chunk.chunk_index,
                    document_title=title or dense_titles.get(chunk.id),
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    page_count=page_count,
                    page=page,
                )
            )
        return results


__all__ = ["HybridRetrievalService"]
