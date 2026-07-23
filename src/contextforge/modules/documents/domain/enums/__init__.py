"""Domain enums for the documents module."""

from __future__ import annotations

from enum import StrEnum


class DocumentStatus(StrEnum):
    ACTIVE = "active"
    DELETED = "deleted"


__all__ = ["DocumentStatus"]
