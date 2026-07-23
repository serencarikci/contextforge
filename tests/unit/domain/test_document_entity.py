"""Unit tests for the Document entity: validation, lifecycle, and size limits."""

from __future__ import annotations

from uuid import uuid4

import pytest

from contextforge.domain.exceptions.identity import InvalidResourceStateError
from contextforge.modules.documents.domain.entities.document import (
    MAX_DOCUMENT_SIZE_BYTES,
    Document,
    ensure_upload_size_within_limit,
)
from contextforge.modules.documents.domain.enums import DocumentStatus


def _make_document(**overrides: object) -> Document:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "knowledge_space_id": uuid4(),
        "title": "Handbook Intro",
        "filename": "intro.pdf",
        "content_type": "application/pdf",
        "size_bytes": 1024,
        "storage_key": "org/ks/doc/intro.pdf",
        "uploaded_by_user_id": uuid4(),
    }
    defaults.update(overrides)
    return Document(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestDocumentValidation:
    def test_new_document_is_active(self) -> None:
        document = _make_document()
        assert document.status == DocumentStatus.ACTIVE
        assert document.deleted_at is None

    def test_title_is_trimmed(self) -> None:
        document = _make_document(title="  Handbook Intro  ")
        assert document.title == "Handbook Intro"

    @pytest.mark.parametrize("title", ["a", "x" * 201])
    def test_title_length_is_validated(self, title: str) -> None:
        with pytest.raises(ValueError, match="title"):
            _make_document(title=title)

    def test_filename_must_not_be_empty(self) -> None:
        with pytest.raises(ValueError, match="filename"):
            _make_document(filename="")

    def test_filename_too_long_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="filename"):
            _make_document(filename="x" * 256)

    def test_content_type_is_required(self) -> None:
        with pytest.raises(ValueError, match="content_type"):
            _make_document(content_type="")

    def test_negative_size_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="size_bytes"):
            _make_document(size_bytes=-1)

    def test_storage_key_is_required(self) -> None:
        with pytest.raises(ValueError, match="storage_key"):
            _make_document(storage_key="")

    def test_size_over_limit_is_rejected(self) -> None:
        with pytest.raises(InvalidResourceStateError):
            _make_document(size_bytes=MAX_DOCUMENT_SIZE_BYTES + 1)

    def test_size_at_limit_is_accepted(self) -> None:
        document = _make_document(size_bytes=MAX_DOCUMENT_SIZE_BYTES)
        assert document.size_bytes == MAX_DOCUMENT_SIZE_BYTES


@pytest.mark.unit
class TestEnsureUploadSizeWithinLimit:
    def test_zero_bytes_is_allowed(self) -> None:
        ensure_upload_size_within_limit(0)

    def test_exactly_max_is_allowed(self) -> None:
        ensure_upload_size_within_limit(MAX_DOCUMENT_SIZE_BYTES)

    def test_over_max_raises(self) -> None:
        with pytest.raises(InvalidResourceStateError):
            ensure_upload_size_within_limit(MAX_DOCUMENT_SIZE_BYTES + 1)


@pytest.mark.unit
class TestDocumentLifecycle:
    def test_update_metadata_changes_title(self) -> None:
        document = _make_document()
        document.update_metadata(title="New Title")
        assert document.title == "New Title"

    def test_update_metadata_with_none_title_is_noop(self) -> None:
        document = _make_document()
        document.update_metadata(title=None)
        assert document.title == "Handbook Intro"

    def test_soft_delete_marks_deleted(self) -> None:
        document = _make_document()
        document.soft_delete()
        assert document.status == DocumentStatus.DELETED
        assert document.deleted_at is not None

    def test_cannot_update_metadata_after_delete(self) -> None:
        document = _make_document()
        document.soft_delete()
        with pytest.raises(InvalidResourceStateError):
            document.update_metadata(title="New Title")

    def test_cannot_delete_twice(self) -> None:
        document = _make_document()
        document.soft_delete()
        with pytest.raises(InvalidResourceStateError):
            document.soft_delete()

    def test_cannot_replace_file_after_delete(self) -> None:
        document = _make_document()
        document.soft_delete()
        with pytest.raises(InvalidResourceStateError):
            document.replace_file(
                filename="new.pdf",
                content_type="application/pdf",
                size_bytes=10,
                storage_key="org/ks/doc/new.pdf",
            )

    def test_replace_file_updates_fields(self) -> None:
        document = _make_document()
        document.replace_file(
            filename="new.pdf",
            content_type="application/pdf",
            size_bytes=2048,
            storage_key="org/ks/doc/new.pdf",
            checksum_sha256="abc123",
        )
        assert document.filename == "new.pdf"
        assert document.size_bytes == 2048
        assert document.storage_key == "org/ks/doc/new.pdf"
        assert document.checksum_sha256 == "abc123"

    def test_replace_file_rejects_oversized_upload(self) -> None:
        document = _make_document()
        with pytest.raises(InvalidResourceStateError):
            document.replace_file(
                filename="huge.bin",
                content_type="application/octet-stream",
                size_bytes=MAX_DOCUMENT_SIZE_BYTES + 1,
                storage_key="org/ks/doc/huge.bin",
            )
