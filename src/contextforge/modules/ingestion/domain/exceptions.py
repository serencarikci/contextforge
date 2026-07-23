"""Ingestion domain exceptions."""

from __future__ import annotations

from contextforge.domain.exceptions.base import DomainError


class IngestionJobError(DomainError):
    """Raised when an ingestion job cannot be processed."""

    code = "INGESTION_JOB_FAILED"


__all__ = ["IngestionJobError"]
