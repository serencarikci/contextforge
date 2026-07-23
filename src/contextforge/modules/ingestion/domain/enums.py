"""Ingestion job domain enums."""

from __future__ import annotations

from enum import StrEnum


class IngestionJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class IngestionJobStep(StrEnum):
    QUEUED = "queued"
    PARSE = "parse"
    CHUNK = "chunk"
    EMBED = "embed"
    DONE = "done"


__all__ = ["IngestionJobStatus", "IngestionJobStep"]
