"""Versioned prompt registry loaded from YAML files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

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


class PromptRegistry:
    """Loads and renders versioned prompt templates."""

    def __init__(self, settings: PromptSettings, *, root: Path | None = None) -> None:
        self._settings = settings
        self._root = root or _PROMPTS_ROOT
        self._cache: dict[tuple[str, str], PromptBundle] = {}

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

    def render(self, template: str, **values: str) -> str:
        rendered = template
        for key, value in values.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", value)
        return rendered.strip()


__all__ = ["PromptBundle", "PromptRegistry"]
