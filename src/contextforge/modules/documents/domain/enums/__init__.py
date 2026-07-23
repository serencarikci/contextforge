"""Domain enums for the documents module."""

from __future__ import annotations

from enum import StrEnum


class DocumentStatus(StrEnum):
    ACTIVE = "active"
    DELETED = "deleted"


class DocumentFormat(StrEnum):
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    MARKDOWN = "markdown"


class DocumentParseStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


__all__ = ["DocumentFormat", "DocumentParseStatus", "DocumentStatus"]
