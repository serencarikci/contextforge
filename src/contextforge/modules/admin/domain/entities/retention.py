"""Retention policy and retention run entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from contextforge.modules.admin.domain.enums import RetentionResourceType, RetentionRunStatus
from contextforge.shared.utilities.datetime import utc_now

MIN_RETENTION_DAYS = 1
MAX_RETENTION_DAYS = 36_500

_PURGE_ONLY_RESOURCES = frozenset(
    {
        RetentionResourceType.AUDIT_EVENTS,
        RetentionResourceType.ANALYTICS,
    }
)


@dataclass(slots=True)
class RetentionPolicy:
    """How long one resource family is kept for an organization (or globally)."""

    resource_type: RetentionResourceType
    retention_days: int
    id: UUID = field(default_factory=uuid4)
    organization_id: UUID | None = None
    soft_delete_first: bool = True
    enabled: bool = True
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.retention_days = self._validate_days(self.retention_days)
        if self.soft_delete_first and self.resource_type in _PURGE_ONLY_RESOURCES:
            msg = (
                f"Retention for '{self.resource_type.value}' is purge-only; "
                "soft_delete_first must be false"
            )
            raise ValueError(msg)

    @staticmethod
    def _validate_days(days: int) -> int:
        if not isinstance(days, int) or isinstance(days, bool):
            msg = "retention_days must be an integer"
            raise TypeError(msg)
        if days < MIN_RETENTION_DAYS or days > MAX_RETENTION_DAYS:
            msg = f"retention_days must be between {MIN_RETENTION_DAYS} and {MAX_RETENTION_DAYS}"
            raise ValueError(msg)
        return days

    @property
    def is_global(self) -> bool:
        return self.organization_id is None

    def cutoff(self, *, now: datetime | None = None) -> datetime:
        """Timestamp before which rows are eligible for cleanup."""
        reference = now or utc_now()
        return reference - timedelta(days=self.retention_days)

    def update(
        self,
        *,
        retention_days: int | None = None,
        soft_delete_first: bool | None = None,
        enabled: bool | None = None,
    ) -> None:
        if retention_days is not None:
            self.retention_days = self._validate_days(retention_days)
        if soft_delete_first is not None:
            if soft_delete_first and self.resource_type in _PURGE_ONLY_RESOURCES:
                msg = (
                    f"Retention for '{self.resource_type.value}' is purge-only; "
                    "soft_delete_first must be false"
                )
                raise ValueError(msg)
            self.soft_delete_first = soft_delete_first
        if enabled is not None:
            self.enabled = enabled
        self.updated_at = utc_now()


@dataclass(slots=True)
class RetentionRun:
    """One execution of a retention policy."""

    policy_id: UUID
    id: UUID = field(default_factory=uuid4)
    organization_id: UUID | None = None
    status: RetentionRunStatus = RetentionRunStatus.RUNNING
    started_at: datetime = field(default_factory=utc_now)
    finished_at: datetime | None = None
    deleted_count: int = 0
    summary: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)

    def mark_succeeded(self, *, deleted_count: int, summary: dict[str, Any] | None = None) -> None:
        if deleted_count < 0:
            msg = "deleted_count must be non-negative"
            raise ValueError(msg)
        self.status = RetentionRunStatus.SUCCEEDED
        self.deleted_count = deleted_count
        self.summary = dict(summary or {})
        self.finished_at = utc_now()

    def mark_failed(self, *, error_code: str, error_message: str) -> None:
        self.status = RetentionRunStatus.FAILED
        self.summary = {"error_code": error_code, "error_message": error_message[:2000]}
        self.finished_at = utc_now()


__all__ = [
    "MAX_RETENTION_DAYS",
    "MIN_RETENTION_DAYS",
    "RetentionPolicy",
    "RetentionRun",
]
