from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from contextforge.shared.utilities.datetime import utc_now

_FLAG_KEY_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
MAX_FLAG_KEY_LENGTH = 120


def normalize_flag_key(key: str) -> str:
    cleaned = key.strip().lower()
    if len(cleaned) > MAX_FLAG_KEY_LENGTH:
        msg = f"Feature flag key must be at most {MAX_FLAG_KEY_LENGTH} characters"
        raise ValueError(msg)
    if not _FLAG_KEY_RE.fullmatch(cleaned):
        msg = (
            "Feature flag key must be lowercase alphanumeric segments separated by '.', '_', or '-'"
        )
        raise ValueError(msg)
    return cleaned


@dataclass(slots=True)
class FeatureFlag:
    key: str
    id: UUID = field(default_factory=uuid4)
    organization_id: UUID | None = None
    description: str | None = None
    enabled_globally: bool = False
    value: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.key = normalize_flag_key(self.key)
        if self.description is not None:
            self.description = self.description.strip() or None

    def update(
        self,
        *,
        description: str | None = None,
        enabled: bool | None = None,
        value: dict[str, Any] | None = None,
    ) -> None:
        if description is not None:
            self.description = description.strip() or None
        if enabled is not None:
            self.enabled_globally = enabled
        if value is not None:
            self.value = dict(value)
        self.updated_at = utc_now()


def resolve_flags(
    *,
    global_flags: list[FeatureFlag],
    organization_flags: list[FeatureFlag],
    settings_overrides: dict[str, bool] | None = None,
) -> dict[str, bool]:
    resolved = {flag.key: flag.enabled_globally for flag in global_flags}
    for flag in organization_flags:
        resolved[flag.key] = flag.enabled_globally
    for key, enabled in (settings_overrides or {}).items():
        resolved[key] = enabled
    return dict(sorted(resolved.items()))


__all__ = [
    "MAX_FLAG_KEY_LENGTH",
    "FeatureFlag",
    "normalize_flag_key",
    "resolve_flags",
]
