from __future__ import annotations

from contextforge.domain.exceptions.base import DomainError


class IngestionJobError(DomainError):
    code = "INGESTION_JOB_FAILED"


__all__ = ["IngestionJobError"]
