"""Document entity: metadata for a file stored in object storage."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from contextforge.domain.exceptions.identity import InvalidResourceStateError
from contextforge.modules.documents.domain.enums import DocumentStatus
from contextforge.shared.utilities.datetime import utc_now

MAX_DOCUMENT_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


def ensure_upload_size_within_limit(size_bytes: int) -> None:
    """Raise if ``size_bytes`` exceeds the maximum allowed document size."""
    if size_bytes > MAX_DOCUMENT_SIZE_BYTES:
        msg = (
            f"Document size ({size_bytes} bytes) exceeds the maximum allowed size "
            f"of {MAX_DOCUMENT_SIZE_BYTES} bytes."
        )
        raise InvalidResourceStateError(msg)


@dataclass(slots=True)
class Document:
    organization_id: UUID
    knowledge_space_id: UUID
    title: str
    filename: str
    content_type: str
    size_bytes: int
    storage_key: str
    uploaded_by_user_id: UUID
    id: UUID = field(default_factory=uuid4)
    checksum_sha256: str | None = None
    status: DocumentStatus = DocumentStatus.ACTIVE
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    deleted_at: datetime | None = None

    def __post_init__(self) -> None:
        self.title = self._validate_title(self.title)
        self.filename = self._validate_filename(self.filename)
        if not self.content_type or not self.content_type.strip():
            msg = "Document content_type is required"
            raise ValueError(msg)
        if self.size_bytes < 0:
            msg = "Document size_bytes must be >= 0"
            raise ValueError(msg)
        ensure_upload_size_within_limit(self.size_bytes)
        if not self.storage_key or not self.storage_key.strip():
            msg = "Document storage_key is required"
            raise ValueError(msg)

    @staticmethod
    def _validate_title(title: str) -> str:
        cleaned = title.strip()
        if len(cleaned) < 2 or len(cleaned) > 200:
            msg = "Document title must be between 2 and 200 characters"
            raise ValueError(msg)
        return cleaned

    @staticmethod
    def _validate_filename(filename: str) -> str:
        cleaned = filename.strip()
        if len(cleaned) < 1 or len(cleaned) > 255:
            msg = "Document filename must be between 1 and 255 characters"
            raise ValueError(msg)
        return cleaned

    def _ensure_active(self) -> None:
        if self.status == DocumentStatus.DELETED:
            raise InvalidResourceStateError("Deleted documents cannot be modified.")

    def update_metadata(self, *, title: str | None = None) -> None:
        self._ensure_active()
        if title is not None:
            self.title = self._validate_title(title)
        self.updated_at = utc_now()

    def replace_file(
        self,
        *,
        filename: str,
        content_type: str,
        size_bytes: int,
        storage_key: str,
        checksum_sha256: str | None = None,
    ) -> None:
        self._ensure_active()
        if not content_type or not content_type.strip():
            msg = "Document content_type is required"
            raise ValueError(msg)
        if size_bytes < 0:
            msg = "Document size_bytes must be >= 0"
            raise ValueError(msg)
        ensure_upload_size_within_limit(size_bytes)
        if not storage_key or not storage_key.strip():
            msg = "Document storage_key is required"
            raise ValueError(msg)

        self.filename = self._validate_filename(filename)
        self.content_type = content_type
        self.size_bytes = size_bytes
        self.storage_key = storage_key
        self.checksum_sha256 = checksum_sha256
        self.updated_at = utc_now()

    def soft_delete(self) -> None:
        self._ensure_active()
        self.status = DocumentStatus.DELETED
        self.deleted_at = utc_now()
        self.updated_at = utc_now()


__all__ = ["MAX_DOCUMENT_SIZE_BYTES", "Document", "ensure_upload_size_within_limit"]
