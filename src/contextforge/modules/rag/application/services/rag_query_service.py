"""End-to-end RAG query pipeline."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.ports.llm_provider import LlmMessage, LlmProviderPort
from contextforge.application.ports.reranker import RerankCandidate, RerankerPort
from contextforge.application.services.command_support import build_audit_event
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import ResourceNotFoundError
from contextforge.modules.rag.application.prompts.registry import PromptRegistry
from contextforge.modules.rag.application.security.prompt_guard import (
    sanitize_model_answer,
    sanitize_user_question,
    wrap_conversation_history,
)
from contextforge.modules.rag.application.services.context_builder import (
    build_citations,
    format_context,
    select_context_chunks,
)
from contextforge.modules.rag.application.services.hybrid_retrieval_service import (
    HybridRetrievalService,
)
from contextforge.modules.rag.domain.types import RagAnswer, RagDiagnostics, RetrievedChunk
from contextforge.shared.config.settings import RagSettings, RerankSettings
from contextforge.shared.logging.setup import get_logger

logger = get_logger(__name__)


class RagQueryService:
    """Permission-aware RAG orchestration: retrieve → rerank → prompt → LLM → citations."""

    def __init__(
        self,
        *,
        retrieval: HybridRetrievalService,
        reranker: RerankerPort,
        llm: LlmProviderPort,
        prompts: PromptRegistry,
        rag_settings: RagSettings,
        rerank_settings: RerankSettings,
    ) -> None:
        self._retrieval = retrieval
        self._reranker = reranker
        self._llm = llm
        self._prompts = prompts
        self._rag_settings = rag_settings
        self._rerank_settings = rerank_settings

    @property
    def model_name(self) -> str:
        """Configured LLM model/deployment name, for observability/attribution."""
        return self._llm.model

    def _resolve_knowledge_spaces(
        self,
        ctx: RequestContext,
        knowledge_space_ids: list[UUID] | None,
    ) -> list[UUID]:
        if knowledge_space_ids:
            allowed: list[UUID] = []
            for ks_id in knowledge_space_ids:
                if ctx.can_access_knowledge_space(ks_id):
                    allowed.append(ks_id)
            return allowed
        return sorted(
            set(ctx.accessible_knowledge_space_ids)
            | set(ctx.organization_visible_knowledge_space_ids)
        )

    def _filter_authorized(
        self, ctx: RequestContext, chunks: list[RetrievedChunk]
    ) -> list[RetrievedChunk]:
        return [
            chunk for chunk in chunks if ctx.can_access_knowledge_space(chunk.knowledge_space_id)
        ]

    async def search(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        *,
        question: str,
        knowledge_space_ids: list[UUID] | None = None,
        top_k: int | None = None,
        limit: int | None = None,
        offset: int = 0,
        language: str | None = None,
    ) -> tuple[list[RetrievedChunk], RagDiagnostics]:
        total_started = time.perf_counter()
        ctx.require_permission("rag:query")
        safe_question = sanitize_user_question(question)
        if not safe_question:
            raise ResourceNotFoundError("Question is required.")
        ks_ids = self._resolve_knowledge_spaces(ctx, knowledge_space_ids)
        if not ks_ids:
            raise ResourceNotFoundError("No accessible knowledge spaces for retrieval.")

        chunks, retrieval_ms = await self._retrieval.retrieve(
            organization_id=ctx.organization_id,
            query=safe_question,
            knowledge_space_ids=ks_ids,
            top_k=top_k,
            limit=limit,
            offset=offset,
            language=language,
        )
        chunks = self._filter_authorized(ctx, chunks)

        rerank_started = time.perf_counter()
        if len(chunks) > 1:
            reranked = await self._reranker.rerank(
                query=safe_question,
                candidates=[
                    RerankCandidate(
                        chunk_id=chunk.chunk_id, content=chunk.content, score=chunk.score
                    )
                    for chunk in chunks
                ],
                top_n=self._rerank_settings.top_n,
            )
            by_id = {chunk.chunk_id: chunk for chunk in chunks}
            ordered: list[RetrievedChunk] = []
            for item in reranked:
                original = by_id.get(item.chunk_id)
                if original is None:
                    continue
                ordered.append(
                    RetrievedChunk(
                        chunk_id=original.chunk_id,
                        organization_id=original.organization_id,
                        document_id=original.document_id,
                        knowledge_space_id=original.knowledge_space_id,
                        content=original.content,
                        score=item.score,
                        dense_score=original.dense_score,
                        lexical_score=original.lexical_score,
                        chunk_index=original.chunk_index,
                        document_title=original.document_title,
                        char_start=original.char_start,
                        char_end=original.char_end,
                        page_count=original.page_count,
                        page=original.page,
                    )
                )
            chunks = ordered
        rerank_ms = round((time.perf_counter() - rerank_started) * 1000, 2)
        total_ms = round((time.perf_counter() - total_started) * 1000, 2)
        diagnostics = RagDiagnostics(
            retrieval_ms=retrieval_ms,
            rerank_ms=rerank_ms,
            prompt_build_ms=0.0,
            llm_ms=0.0,
            total_ms=total_ms,
            retrieved_chunk_count=len(chunks),
            context_chunk_count=len(chunks),
            context_chars=sum(len(chunk.content) for chunk in chunks),
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
        )
        async with uow:
            event = build_audit_event(
                ctx,
                action="rag.searched",
                resource_type="rag_query",
                resource_id=None,
                metadata={"chunk_count": len(chunks), "retrieval_ms": retrieval_ms},
            )
            await uow.audit.add(event)
        return chunks, diagnostics

    async def query(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        *,
        question: str,
        knowledge_space_ids: list[UUID] | None = None,
        language: str | None = None,
        top_k: int | None = None,
        history_context: str | None = None,
    ) -> RagAnswer:
        total_started = time.perf_counter()
        chunks, search_diagnostics = await self.search(
            uow,
            ctx,
            question=question,
            knowledge_space_ids=knowledge_space_ids,
            top_k=top_k,
            language=language,
        )
        safe_question = sanitize_user_question(question)
        lang = (language or self._rag_settings.default_language).lower()
        if lang not in {"en", "tr"}:
            lang = self._rag_settings.default_language

        prompt_started = time.perf_counter()
        context_chunks = select_context_chunks(
            chunks,
            max_tokens=self._rag_settings.max_context_tokens,
            max_chunks=self._rag_settings.max_chunks_in_context,
        )
        bundle = self._prompts.get(language=lang)
        context_text = format_context(context_chunks)
        citation_hint = self._prompts.render(bundle.citation, chunk_id="CHUNK_ID")
        multilingual = self._prompts.render(bundle.multilingual, language=lang)
        system_prompt = f"{bundle.system.strip()}\n\n{citation_hint}\n\n{multilingual}".strip()
        user_prompt = self._prompts.render(
            bundle.user,
            language=lang,
            question=safe_question,
            context=context_text or "No authorized excerpts were retrieved.",
        )
        if history_context:
            safe_history = wrap_conversation_history(history_context)
            if safe_history:
                user_prompt = f"{safe_history}\n\n{user_prompt}"
        messages = [
            LlmMessage(role="system", content=system_prompt),
            LlmMessage(role="user", content=user_prompt),
        ]
        prompt_ms = round((time.perf_counter() - prompt_started) * 1000, 2)

        llm_started = time.perf_counter()
        completion = await self._llm.complete(messages)
        llm_ms = round((time.perf_counter() - llm_started) * 1000, 2)
        citations = build_citations(context_chunks)
        total_ms = round((time.perf_counter() - total_started) * 1000, 2)
        diagnostics = RagDiagnostics(
            retrieval_ms=search_diagnostics.retrieval_ms,
            rerank_ms=search_diagnostics.rerank_ms,
            prompt_build_ms=prompt_ms,
            llm_ms=llm_ms,
            total_ms=total_ms,
            retrieved_chunk_count=search_diagnostics.retrieved_chunk_count,
            context_chunk_count=len(context_chunks),
            context_chars=len(context_text),
            prompt_tokens=completion.usage.prompt_tokens,
            completion_tokens=completion.usage.completion_tokens,
            total_tokens=completion.usage.total_tokens,
        )
        logger.info(
            "rag_query_completed",
            extra={
                "organization_id": str(ctx.organization_id),
                "language": lang,
                "retrieved_chunk_count": diagnostics.retrieved_chunk_count,
                "context_chunk_count": diagnostics.context_chunk_count,
                "retrieval_ms": diagnostics.retrieval_ms,
                "rerank_ms": diagnostics.rerank_ms,
                "prompt_build_ms": diagnostics.prompt_build_ms,
                "llm_ms": diagnostics.llm_ms,
                "total_ms": diagnostics.total_ms,
                "total_tokens": diagnostics.total_tokens,
            },
        )
        async with uow:
            event = build_audit_event(
                ctx,
                action="rag.answered",
                resource_type="rag_query",
                resource_id=None,
                metadata={
                    "language": lang,
                    "citation_count": len(citations),
                    "total_ms": total_ms,
                },
            )
            await uow.audit.add(event)
        return RagAnswer(
            answer=sanitize_model_answer(completion.content),
            language=lang,
            citations=citations,
            diagnostics=diagnostics,
        )

    async def stream_query(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        *,
        question: str,
        knowledge_space_ids: list[UUID] | None = None,
        language: str | None = None,
        top_k: int | None = None,
        history_context: str | None = None,
    ) -> AsyncIterator[str]:
        chunks, _diagnostics = await self.search(
            uow,
            ctx,
            question=question,
            knowledge_space_ids=knowledge_space_ids,
            top_k=top_k,
            language=language,
        )
        safe_question = sanitize_user_question(question)
        lang = (language or self._rag_settings.default_language).lower()
        if lang not in {"en", "tr"}:
            lang = self._rag_settings.default_language
        context_chunks = select_context_chunks(
            chunks,
            max_tokens=self._rag_settings.max_context_tokens,
            max_chunks=self._rag_settings.max_chunks_in_context,
        )
        bundle = self._prompts.get(language=lang)
        context_text = format_context(context_chunks)
        citation_hint = self._prompts.render(bundle.citation, chunk_id="CHUNK_ID")
        multilingual = self._prompts.render(bundle.multilingual, language=lang)
        system_prompt = f"{bundle.system.strip()}\n\n{citation_hint}\n\n{multilingual}".strip()
        user_prompt = self._prompts.render(
            bundle.user,
            language=lang,
            question=safe_question,
            context=context_text or "No authorized excerpts were retrieved.",
        )
        if history_context:
            safe_history = wrap_conversation_history(history_context)
            if safe_history:
                user_prompt = f"{safe_history}\n\n{user_prompt}"
        messages = [
            LlmMessage(role="system", content=system_prompt),
            LlmMessage(role="user", content=user_prompt),
        ]
        async for delta in self._llm.stream(messages):
            yield delta


__all__ = ["RagQueryService"]
