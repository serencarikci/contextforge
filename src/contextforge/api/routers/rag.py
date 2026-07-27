"""RAG search and answer endpoints."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from contextforge.api.dependencies.identity import get_request_context, get_uow
from contextforge.api.dependencies.providers import get_rag_query_service
from contextforge.api.schemas.rag import (
    CitationResponse,
    RagDiagnosticsResponse,
    RagQueryRequest,
    RagQueryResponse,
    RagSearchRequest,
    RagSearchResponse,
    RetrievedChunkResponse,
)
from contextforge.application.context.request_context import RequestContext
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.modules.rag.application.services.rag_query_service import RagQueryService

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/search", response_model=RagSearchResponse)
async def rag_search(
    payload: RagSearchRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[RagQueryService, Depends(get_rag_query_service)],
) -> RagSearchResponse:
    chunks, diagnostics = await service.search(
        uow,
        ctx,
        question=payload.question,
        knowledge_space_ids=payload.knowledge_space_ids,
        language=payload.language,
        top_k=payload.top_k,
        limit=payload.limit,
        offset=payload.offset,
    )
    return RagSearchResponse(
        items=[
            RetrievedChunkResponse(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                knowledge_space_id=chunk.knowledge_space_id,
                score=chunk.score,
                chunk_index=chunk.chunk_index,
                document_title=chunk.document_title,
                page=chunk.page,
                snippet=(chunk.content[:240] + "…") if len(chunk.content) > 240 else chunk.content,
            )
            for chunk in chunks
        ],
        diagnostics=RagDiagnosticsResponse.model_validate(diagnostics),
    )


@router.post("/query", response_model=RagQueryResponse)
async def rag_query(
    payload: RagQueryRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[RagQueryService, Depends(get_rag_query_service)],
) -> RagQueryResponse:
    answer = await service.query(
        uow,
        ctx,
        question=payload.question,
        knowledge_space_ids=payload.knowledge_space_ids,
        language=payload.language,
        top_k=payload.top_k,
    )
    return RagQueryResponse(
        answer=answer.answer,
        language=answer.language,
        citations=[CitationResponse.model_validate(item) for item in answer.citations],
        diagnostics=RagDiagnosticsResponse.model_validate(answer.diagnostics)
        if answer.diagnostics is not None
        else None,
    )


@router.post("/query/stream")
async def rag_query_stream(
    payload: RagQueryRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[RagQueryService, Depends(get_rag_query_service)],
) -> StreamingResponse:
    async def event_stream() -> AsyncIterator[str]:
        async for delta in service.stream_query(
            uow,
            ctx,
            question=payload.question,
            knowledge_space_ids=payload.knowledge_space_ids,
            language=payload.language,
            top_k=payload.top_k,
        ):
            yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
