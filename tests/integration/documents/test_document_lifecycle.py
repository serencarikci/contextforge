"""Integration tests for the document upload/get/download/delete lifecycle.

Exercises the full application-service write path against a real database
and a real MinIO instance: bytes are actually written to and read back from
object storage, and metadata is actually persisted/soft-deleted in
PostgreSQL.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from contextforge.application.context.request_context import RequestContext
from contextforge.application.pagination import PaginationParams
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import InvalidResourceStateError, ResourceNotFoundError
from contextforge.infrastructure.database.session import DatabaseManager
from contextforge.infrastructure.object_storage.minio_client import MinioClient
from contextforge.modules.documents.application.services.document_service import DocumentService
from contextforge.modules.documents.domain.entities.document import MAX_DOCUMENT_SIZE_BYTES
from contextforge.modules.documents.domain.enums import DocumentStatus
from contextforge.modules.identity_access.application.services.identity_context_service import (
    build_request_context,
)
from contextforge.modules.identity_access.application.services.user_service import UserService
from contextforge.modules.knowledge_spaces.application.services.knowledge_space_service import (
    KnowledgeSpaceService,
)
from contextforge.modules.organizations.application.services.organization_service import (
    OrganizationService,
)
from contextforge.shared.config.settings import Settings


class _Tenant:
    """A freshly-created organization/admin pair plus a context refresher.

    A single ``RequestContext`` snapshot only knows about knowledge spaces
    that existed when it was built (just like a real HTTP request). Tests
    that create a knowledge space and then immediately act on it need a
    freshly rebuilt context, exactly as ``get_request_context`` rebuilds one
    per request in the real API.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        settings: Settings,
        user_id: UUID,
        organization_id: UUID,
    ) -> None:
        self._db_manager = db_manager
        self._settings = settings
        self.user_id = user_id
        self.organization_id = organization_id

    async def refresh_ctx(self) -> RequestContext:
        async with SqlAlchemyUnitOfWork(self._db_manager.session_factory) as uow:
            return await build_request_context(
                uow,
                settings=self._settings,
                user_id=self.user_id,
                organization_id=self.organization_id,
            )


async def _make_tenant(db_manager: DatabaseManager, settings: Settings) -> _Tenant:
    suffix = uuid4().hex[:12]
    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    admin = await UserService().create(
        uow, email=f"doc-admin-{suffix}@example.com", display_name="Doc Admin"
    )

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    organization = await OrganizationService().create(
        uow,
        name=f"Doc Org {suffix}",
        slug=f"doc-org-{suffix}",
        creator_user_id=admin.id,
    )

    return _Tenant(db_manager, settings, admin.id, organization.id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_document_upload_get_download_delete_roundtrip(
    db_manager: DatabaseManager, integration_settings: Settings
) -> None:
    tenant = await _make_tenant(db_manager, integration_settings)
    minio = MinioClient(integration_settings.minio)
    service = DocumentService()
    suffix = uuid4().hex[:8]

    ctx = await tenant.refresh_ctx()
    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    knowledge_space = await KnowledgeSpaceService().create(
        uow, ctx, name="Doc KS", slug=f"doc-ks-{suffix}"
    )
    ctx = await tenant.refresh_ctx()

    content = b"Hello, ContextForge document storage!"
    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    document = await service.upload(
        uow,
        ctx,
        minio,
        knowledge_space_id=knowledge_space.id,
        title="Roundtrip Doc",
        filename="roundtrip.txt",
        content_type="text/plain",
        data=content,
    )
    assert document.status == DocumentStatus.ACTIVE
    assert document.size_bytes == len(content)
    assert document.checksum_sha256 is not None

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    fetched = await service.get(uow, ctx, document.id)
    assert fetched.id == document.id
    assert fetched.title == "Roundtrip Doc"

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    downloaded_doc, downloaded_bytes = await service.download(uow, ctx, minio, document.id)
    assert downloaded_doc.id == document.id
    assert downloaded_bytes == content

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    updated = await service.update_metadata(uow, ctx, document.id, title="Renamed Doc")
    assert updated.title == "Renamed Doc"

    new_content = b"Replacement content bytes."
    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    replaced = await service.replace_file(
        uow,
        ctx,
        minio,
        document.id,
        filename="replacement.txt",
        content_type="text/plain",
        data=new_content,
    )
    assert replaced.filename == "replacement.txt"
    assert replaced.size_bytes == len(new_content)

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    _, redownloaded_bytes = await service.download(uow, ctx, minio, document.id)
    assert redownloaded_bytes == new_content

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    await service.delete(uow, ctx, minio, document.id)

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    with pytest.raises(ResourceNotFoundError):
        await service.get(uow, ctx, document.id)

    await minio.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_document_list_filters_by_knowledge_space(
    db_manager: DatabaseManager, integration_settings: Settings
) -> None:
    tenant = await _make_tenant(db_manager, integration_settings)
    minio = MinioClient(integration_settings.minio)
    service = DocumentService()
    suffix = uuid4().hex[:8]

    ctx = await tenant.refresh_ctx()
    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    ks_a = await KnowledgeSpaceService().create(uow, ctx, name="KS A", slug=f"ks-a-{suffix}")
    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    ks_b = await KnowledgeSpaceService().create(uow, ctx, name="KS B", slug=f"ks-b-{suffix}")
    ctx = await tenant.refresh_ctx()

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    doc_a = await service.upload(
        uow,
        ctx,
        minio,
        knowledge_space_id=ks_a.id,
        title="Doc A",
        filename="a.txt",
        content_type="text/plain",
        data=b"a",
    )
    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    await service.upload(
        uow,
        ctx,
        minio,
        knowledge_space_id=ks_b.id,
        title="Doc B",
        filename="b.txt",
        content_type="text/plain",
        data=b"b",
    )

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    page = await service.list(
        uow, ctx, PaginationParams(limit=10, offset=0), knowledge_space_id=ks_a.id
    )
    assert page.total == 1
    assert page.items[0].id == doc_a.id

    await minio.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_document_upload_rejects_oversized_payload(
    db_manager: DatabaseManager, integration_settings: Settings
) -> None:
    tenant = await _make_tenant(db_manager, integration_settings)
    minio = MinioClient(integration_settings.minio)
    service = DocumentService()
    suffix = uuid4().hex[:8]

    ctx = await tenant.refresh_ctx()
    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    knowledge_space = await KnowledgeSpaceService().create(
        uow, ctx, name="Oversized KS", slug=f"oversized-ks-{suffix}"
    )
    ctx = await tenant.refresh_ctx()

    oversized = b"x" * (MAX_DOCUMENT_SIZE_BYTES + 1)
    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    with pytest.raises(InvalidResourceStateError):
        await service.upload(
            uow,
            ctx,
            minio,
            knowledge_space_id=knowledge_space.id,
            title="Huge Doc",
            filename="huge.bin",
            content_type="application/octet-stream",
            data=oversized,
        )

    await minio.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_document_upload_rejects_archived_knowledge_space(
    db_manager: DatabaseManager, integration_settings: Settings
) -> None:
    tenant = await _make_tenant(db_manager, integration_settings)
    minio = MinioClient(integration_settings.minio)
    service = DocumentService()
    suffix = uuid4().hex[:8]

    ctx = await tenant.refresh_ctx()
    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    knowledge_space = await KnowledgeSpaceService().create(
        uow, ctx, name="Archived KS", slug=f"archived-ks-{suffix}"
    )
    ctx = await tenant.refresh_ctx()
    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    await KnowledgeSpaceService().archive(uow, ctx, knowledge_space.id)

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    with pytest.raises(InvalidResourceStateError):
        await service.upload(
            uow,
            ctx,
            minio,
            knowledge_space_id=knowledge_space.id,
            title="Doc In Archived KS",
            filename="doc.txt",
            content_type="text/plain",
            data=b"content",
        )

    await minio.close()
