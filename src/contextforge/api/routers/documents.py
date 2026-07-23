"""Document endpoints: upload, read, update metadata/content, parse, download, delete."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status

from contextforge.api.dependencies.identity import get_request_context, get_uow
from contextforge.api.dependencies.pagination import get_pagination
from contextforge.api.dependencies.providers import get_document_parser, get_minio_client
from contextforge.api.schemas.common import PaginationMeta, PaginationResponse
from contextforge.api.schemas.documents import (
    DocumentMetadataUpdateRequest,
    DocumentParseResponse,
    DocumentResponse,
)
from contextforge.application.context.request_context import RequestContext
from contextforge.application.pagination import PaginationParams
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.infrastructure.object_storage.minio_client import MinioClient
from contextforge.modules.documents.application.ports.document_parser import DocumentParserPort
from contextforge.modules.documents.application.services.document_parsing_service import (
    DocumentParsingService,
)
from contextforge.modules.documents.application.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])

_service = DocumentService()


def _parsing_service(parser: DocumentParserPort) -> DocumentParsingService:
    return DocumentParsingService(parser)


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    minio: Annotated[MinioClient, Depends(get_minio_client)],
    knowledge_space_id: Annotated[UUID, Form()],
    title: Annotated[str, Form(min_length=2, max_length=200)],
    file: Annotated[UploadFile, File()],
) -> DocumentResponse:
    data = await file.read()
    document = await _service.upload(
        uow,
        ctx,
        minio,
        knowledge_space_id=knowledge_space_id,
        title=title,
        filename=file.filename or "upload.bin",
        content_type=file.content_type or "application/octet-stream",
        data=data,
    )
    return DocumentResponse.model_validate(document)


@router.get("", response_model=PaginationResponse[DocumentResponse])
async def list_documents(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    knowledge_space_id: Annotated[UUID | None, Query()] = None,
    query: Annotated[str | None, Query()] = None,
) -> PaginationResponse[DocumentResponse]:
    page = await _service.list(
        uow, ctx, pagination, knowledge_space_id=knowledge_space_id, query=query
    )
    return PaginationResponse(
        items=[DocumentResponse.model_validate(item) for item in page.items],
        pagination=PaginationMeta(limit=page.limit, offset=page.offset, total=page.total),
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> DocumentResponse:
    document = await _service.get(uow, ctx, document_id)
    return DocumentResponse.model_validate(document)


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document_metadata(
    document_id: UUID,
    payload: DocumentMetadataUpdateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> DocumentResponse:
    document = await _service.update_metadata(uow, ctx, document_id, title=payload.title)
    return DocumentResponse.model_validate(document)


@router.put("/{document_id}/content", response_model=DocumentResponse)
async def replace_document_content(
    document_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    minio: Annotated[MinioClient, Depends(get_minio_client)],
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form(min_length=2, max_length=200)] = None,
) -> DocumentResponse:
    data = await file.read()
    document = await _service.replace_file(
        uow,
        ctx,
        minio,
        document_id,
        filename=file.filename or "upload.bin",
        content_type=file.content_type or "application/octet-stream",
        data=data,
    )
    if title is not None:
        document = await _service.update_metadata(uow, ctx, document_id, title=title)
    return DocumentResponse.model_validate(document)


@router.post("/{document_id}/parse", response_model=DocumentParseResponse)
async def parse_document(
    document_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    minio: Annotated[MinioClient, Depends(get_minio_client)],
    parser: Annotated[DocumentParserPort, Depends(get_document_parser)],
) -> DocumentParseResponse:
    result = await _parsing_service(parser).parse_document(uow, ctx, minio, document_id)
    return DocumentParseResponse.model_validate(result)


@router.get("/{document_id}/parse", response_model=DocumentParseResponse)
async def get_document_parse_result(
    document_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    parser: Annotated[DocumentParserPort, Depends(get_document_parser)],
) -> DocumentParseResponse:
    result = await _parsing_service(parser).get_parse_result(uow, ctx, document_id)
    return DocumentParseResponse.model_validate(result)


@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    minio: Annotated[MinioClient, Depends(get_minio_client)],
) -> Response:
    document, data = await _service.download(uow, ctx, minio, document_id)
    return Response(
        content=data,
        media_type=document.content_type,
        headers={"Content-Disposition": f'attachment; filename="{document.filename}"'},
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    minio: Annotated[MinioClient, Depends(get_minio_client)],
) -> None:
    await _service.delete(uow, ctx, minio, document_id)
