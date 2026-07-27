from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol
from uuid import UUID

import yaml

from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.shared.config.settings import PromptSettings

_PROMPTS_ROOT = Path(__file__).resolve().parents[2] / "prompts"


@dataclass(frozen=True, slots=True)
class PromptBundle:
    version: str
    language: str
    system: str
    user: str
    citation: str
    multilingual: str


class PromptOverrideSource(Protocol):
    async def active_slot_contents(
        self,
        uow: SqlAlchemyUnitOfWork,
        *,
        organization_id: UUID,
        language: str,
    ) -> dict[str, str]: ...


class PromptRegistry:
    def __init__(
        self,
        settings: PromptSettings,
        *,
        root: Path | None = None,
        override_source: PromptOverrideSource | None = None,
    ) -> None:
        self._settings = settings
        self._root = root or _PROMPTS_ROOT
        self._cache: dict[tuple[str, str], PromptBundle] = {}
        self._override_source = override_source

    def get(self, *, language: str | None = None, version: str | None = None) -> PromptBundle:
        lang = (language or self._settings.default_language).lower()
        if lang not in {"en", "tr"}:
            lang = self._settings.default_language
        ver = version or self._settings.active_version
        key = (ver, lang)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        path = self._root / ver / f"{lang}.yaml"
        if not path.is_file():
            fallback_lang = self._settings.default_language
            path = self._root / self._settings.active_version / f"{fallback_lang}.yaml"
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        bundle = PromptBundle(
            version=str(raw.get("version") or ver),
            language=str(raw.get("language") or lang),
            system=str(raw.get("system") or ""),
            user=str(raw.get("user") or ""),
            citation=str(raw.get("citation") or ""),
            multilingual=str(raw.get("multilingual") or ""),
        )
        self._cache[key] = bundle
        return bundle

    async def get_for_organization(
        self,
        uow: SqlAlchemyUnitOfWork,
        *,
        organization_id: UUID,
        language: str | None = None,
        version: str | None = None,
    ) -> PromptBundle:
        base = self.get(language=language, version=version)
        if self._override_source is None:
            return base
        overrides = await self._override_source.active_slot_contents(
            uow, organization_id=organization_id, language=base.language
        )
        if not overrides:
            return base
        return replace(
            base,
            system=overrides.get("system", base.system),
            user=overrides.get("user", base.user),
            citation=overrides.get("citation", base.citation),
            multilingual=overrides.get("multilingual", base.multilingual),
        )

    def render(self, template: str, **values: str) -> str:
        rendered = template
        for key, value in values.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", value)
        return rendered.strip()


__all__ = ["PromptBundle", "PromptOverrideSource", "PromptRegistry"]
