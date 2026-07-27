from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from contextforge.domain.exceptions.identity import InvalidResourceStateError
from contextforge.modules.admin.domain.enums import PromptLanguage, PromptTemplateName
from contextforge.shared.utilities.datetime import utc_now

_VERSION_RE = re.compile(r"^v[0-9]+(?:\.[0-9]+)*$")
MAX_PROMPT_CONTENT_LENGTH = 20_000
_PLACEHOLDER_RE = re.compile(r"\{\{([a-z_][a-z0-9_]*)\}\}")


def normalize_prompt_version(version: str) -> str:
    cleaned = version.strip().lower()
    if not _VERSION_RE.fullmatch(cleaned):
        msg = "Prompt version must look like 'v1' or 'v2.1'"
        raise ValueError(msg)
    return cleaned


def extract_placeholders(content: str) -> list[str]:
    return sorted(set(_PLACEHOLDER_RE.findall(content)))


@dataclass(slots=True)
class PromptTemplate:
    name: PromptTemplateName
    version: str
    language: PromptLanguage
    content: str
    id: UUID = field(default_factory=uuid4)
    organization_id: UUID | None = None
    is_active: bool = False
    is_system: bool = False
    created_by: UUID | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.version = normalize_prompt_version(self.version)
        self.content = self._validate_content(self.content)

    @staticmethod
    def _validate_content(content: str) -> str:
        cleaned = content.strip()
        if not cleaned:
            msg = "Prompt content is required"
            raise ValueError(msg)
        if len(cleaned) > MAX_PROMPT_CONTENT_LENGTH:
            msg = f"Prompt content must be at most {MAX_PROMPT_CONTENT_LENGTH} characters"
            raise ValueError(msg)
        return cleaned

    @property
    def placeholders(self) -> list[str]:
        return extract_placeholders(self.content)

    def _ensure_editable(self) -> None:
        if self.is_system:
            raise InvalidResourceStateError("System prompt templates cannot be modified.")

    def activate(self) -> None:
        self.is_active = True
        self.updated_at = utc_now()

    def deactivate(self) -> None:
        self._ensure_editable()
        self.is_active = False
        self.updated_at = utc_now()

    def render(self, values: dict[str, str]) -> str:
        rendered = self.content
        for key, value in values.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", value)
        return rendered.strip()


__all__ = [
    "MAX_PROMPT_CONTENT_LENGTH",
    "PromptTemplate",
    "extract_placeholders",
    "normalize_prompt_version",
]
