from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from contextforge.shared.utilities.datetime import utc_now

QUOTA_KEYS: tuple[str, ...] = (
    "max_users",
    "max_documents",
    "max_conversations",
    "max_monthly_tokens",
)

DEFAULT_KEYS: tuple[str, ...] = (
    "default_language",
    "memory_strategy",
    "llm_model",
    "retention_days",
)

_ALLOWED_LANGUAGES = frozenset({"en", "tr"})
_ALLOWED_MEMORY_STRATEGIES = frozenset({"recent", "token_budget", "summary"})
_MAX_QUOTA = 1_000_000_000


@dataclass(frozen=True, slots=True)
class OrganizationQuotas:
    max_users: int | None = None
    max_documents: int | None = None
    max_conversations: int | None = None
    max_monthly_tokens: int | None = None

    def __post_init__(self) -> None:
        for key in QUOTA_KEYS:
            value = getattr(self, key)
            if value is None:
                continue
            if not isinstance(value, int) or isinstance(value, bool):
                msg = f"Quota '{key}' must be an integer or null"
                raise TypeError(msg)
            if value < 0 or value > _MAX_QUOTA:
                msg = f"Quota '{key}' must be between 0 and {_MAX_QUOTA}"
                raise ValueError(msg)

    @classmethod
    def from_mapping(cls, raw: dict[str, Any] | None) -> OrganizationQuotas:
        payload = raw or {}
        return cls(**{key: payload.get(key) for key in QUOTA_KEYS})

    def to_mapping(self) -> dict[str, int | None]:
        return {key: getattr(self, key) for key in QUOTA_KEYS}

    def remaining(self, key: str, current: int) -> int | None:
        limit = getattr(self, key)
        if limit is None:
            return None
        return max(int(limit) - current, 0)

    def is_exceeded(self, key: str, current: int) -> bool:
        limit = getattr(self, key)
        if limit is None:
            return False
        return int(limit) >= current


def validate_defaults(raw: dict[str, Any] | None) -> dict[str, Any]:
    payload = raw or {}
    unknown = sorted(set(payload) - set(DEFAULT_KEYS))
    if unknown:
        msg = f"Unknown default keys: {', '.join(unknown)}"
        raise ValueError(msg)

    validated: dict[str, Any] = {}
    for key, value in payload.items():
        if value is None:
            continue
        if key == "default_language":
            language = str(value).lower()
            if language not in _ALLOWED_LANGUAGES:
                msg = "default_language must be one of: en, tr"
                raise ValueError(msg)
            validated[key] = language
        elif key == "memory_strategy":
            strategy = str(value).lower()
            if strategy not in _ALLOWED_MEMORY_STRATEGIES:
                msg = "memory_strategy must be one of: recent, token_budget, summary"
                raise ValueError(msg)
            validated[key] = strategy
        elif key == "retention_days":
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                msg = "retention_days must be a positive integer"
                raise ValueError(msg)
            validated[key] = value
        else:
            text = str(value).strip()
            if not text:
                msg = f"Default '{key}' must not be blank"
                raise ValueError(msg)
            validated[key] = text
    return validated


def validate_feature_overrides(raw: dict[str, Any] | None) -> dict[str, bool]:
    payload = raw or {}
    overrides: dict[str, bool] = {}
    for key, value in payload.items():
        cleaned = str(key).strip()
        if not cleaned:
            msg = "Feature override keys must not be blank"
            raise ValueError(msg)
        if not isinstance(value, bool):
            msg = f"Feature override '{cleaned}' must be a boolean"
            raise TypeError(msg)
        overrides[cleaned] = value
    return overrides


@dataclass(slots=True)
class OrganizationSettings:
    organization_id: UUID
    quotas: OrganizationQuotas = field(default_factory=OrganizationQuotas)
    defaults: dict[str, Any] = field(default_factory=dict)
    feature_overrides: dict[str, bool] = field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.defaults = validate_defaults(self.defaults)
        self.feature_overrides = validate_feature_overrides(self.feature_overrides)

    def replace_quotas(self, quotas: OrganizationQuotas) -> None:
        self.quotas = quotas
        self.updated_at = utc_now()

    def merge_defaults(self, defaults: dict[str, Any]) -> None:
        self.defaults = validate_defaults({**self.defaults, **defaults})
        self.updated_at = utc_now()

    def merge_feature_overrides(self, overrides: dict[str, Any]) -> None:
        self.feature_overrides = validate_feature_overrides({**self.feature_overrides, **overrides})
        self.updated_at = utc_now()

    def set_active(self, is_active: bool) -> None:
        self.is_active = is_active
        self.updated_at = utc_now()


__all__ = [
    "DEFAULT_KEYS",
    "QUOTA_KEYS",
    "OrganizationQuotas",
    "OrganizationSettings",
    "validate_defaults",
    "validate_feature_overrides",
]
