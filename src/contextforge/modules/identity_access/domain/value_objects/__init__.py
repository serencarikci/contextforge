"""Validated domain value objects."""

from __future__ import annotations

import re
from dataclasses import dataclass

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_CUSTOMER_CODE_RE = re.compile(r"^[A-Z0-9_-]+$")
_PROJECT_KEY_RE = re.compile(r"^[A-Z0-9-]+$")
_ROLE_CODE_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_PERMISSION_CODE_RE = re.compile(r"^[a-z][a-z0-9_]*(?:[:][a-z][a-z0-9_]*)+$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True, slots=True)
class OrganizationSlug:
    value: str

    def __post_init__(self) -> None:
        raw = self.value.strip().lower()
        if not _SLUG_RE.fullmatch(raw):
            msg = (
                "Organization slug must use lowercase letters, digits, and hyphens, "
                "and must not begin or end with a hyphen"
            )
            raise ValueError(msg)
        object.__setattr__(self, "value", raw)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class KnowledgeSpaceSlug:
    value: str

    def __post_init__(self) -> None:
        raw = self.value.strip().lower()
        if not _SLUG_RE.fullmatch(raw):
            msg = (
                "Knowledge space slug must use lowercase letters, digits, and hyphens, "
                "and must not begin or end with a hyphen"
            )
            raise ValueError(msg)
        object.__setattr__(self, "value", raw)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class NormalizedEmail:
    value: str

    def __post_init__(self) -> None:
        raw = self.value.strip().lower()
        if not _EMAIL_RE.fullmatch(raw):
            msg = "Invalid email address"
            raise ValueError(msg)
        object.__setattr__(self, "value", raw)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class CustomerCode:
    value: str

    def __post_init__(self) -> None:
        raw = self.value.strip().upper()
        if not _CUSTOMER_CODE_RE.fullmatch(raw):
            msg = "Customer code must use uppercase letters, digits, hyphens, and underscores"
            raise ValueError(msg)
        object.__setattr__(self, "value", raw)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ProjectKey:
    value: str

    def __post_init__(self) -> None:
        raw = self.value.strip().upper()
        if not _PROJECT_KEY_RE.fullmatch(raw):
            msg = "Project key must use uppercase letters, digits, and hyphens"
            raise ValueError(msg)
        object.__setattr__(self, "value", raw)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class RoleCode:
    value: str

    def __post_init__(self) -> None:
        raw = self.value.strip().lower()
        if not _ROLE_CODE_RE.fullmatch(raw):
            msg = "Role code must be lowercase snake_case"
            raise ValueError(msg)
        object.__setattr__(self, "value", raw)

    def __str__(self) -> str:
        return self.value


def validate_permission_code(value: str) -> str:
    raw = value.strip().lower()
    if not _PERMISSION_CODE_RE.fullmatch(raw):
        msg = "Permission code must use resource:action format"
        raise ValueError(msg)
    return raw
