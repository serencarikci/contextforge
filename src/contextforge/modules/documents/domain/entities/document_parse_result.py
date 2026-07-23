"""Parsed document content and persisted parse-result aggregate."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from contextforge.modules.documents.domain.enums import DocumentFormat, DocumentParseStatus
from contextforge.shared.types.aliases import JSONValue
from contextforge.shared.utilities.datetime import utc_now


@dataclass(frozen=True, slots=True)
class ExtractedDocumentContent:
    """In-memory result produced by a format-specific parser."""

    text: str
    metadata: dict[str, JSONValue] = field(default_factory=dict)
    page_count: int | None = None


@dataclass(slots=True)
class DocumentParseResult:
    """Persisted outcome of parsing a stored document."""

    organization_id: UUID
    document_id: UUID
    format: DocumentFormat
    status: DocumentParseStatus
    id: UUID = field(default_factory=uuid4)
    extracted_text: str | None = None
    metadata: dict[str, JSONValue] = field(default_factory=dict)
    character_count: int = 0
    page_count: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    parsed_at: datetime = field(default_factory=utc_now)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @classmethod
    def succeeded(
        cls,
        *,
        organization_id: UUID,
        document_id: UUID,
        format: DocumentFormat,
        content: ExtractedDocumentContent,
        existing_id: UUID | None = None,
        created_at: datetime | None = None,
    ) -> DocumentParseResult:
        now = utc_now()
        return cls(
            id=existing_id or uuid4(),
            organization_id=organization_id,
            document_id=document_id,
            format=format,
            status=DocumentParseStatus.SUCCEEDED,
            extracted_text=content.text,
            metadata=dict(content.metadata),
            character_count=len(content.text),
            page_count=content.page_count,
            error_code=None,
            error_message=None,
            parsed_at=now,
            created_at=created_at or now,
            updated_at=now,
        )

    @classmethod
    def failed(
        cls,
        *,
        organization_id: UUID,
        document_id: UUID,
        format: DocumentFormat,
        error_code: str,
        error_message: str,
        existing_id: UUID | None = None,
        created_at: datetime | None = None,
    ) -> DocumentParseResult:
        now = utc_now()
        return cls(
            id=existing_id or uuid4(),
            organization_id=organization_id,
            document_id=document_id,
            format=format,
            status=DocumentParseStatus.FAILED,
            extracted_text=None,
            metadata={},
            character_count=0,
            page_count=None,
            error_code=error_code,
            error_message=error_message,
            parsed_at=now,
            created_at=created_at or now,
            updated_at=now,
        )


__all__ = ["DocumentParseResult", "ExtractedDocumentContent"]
