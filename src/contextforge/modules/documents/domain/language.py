"""Lightweight language helpers for multilingual embedding metadata."""

from __future__ import annotations

import re
import unicodedata

_TURKISH_CHARS = set("ğüşıöçĞÜŞİÖÇâîûÂÎÛ")
_LATIN_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿĞÜŞİÖÇğüşıöç]+", re.UNICODE)


def normalize_multilingual_text(text: str) -> str:
    """Normalize unicode text before embedding."""
    cleaned = unicodedata.normalize("NFKC", text)
    return " ".join(cleaned.split()).strip()


def detect_language(text: str) -> str:
    """Detect a coarse document language code for embedding metadata.

    Returns ``tr`` when Turkish-specific characters dominate Latin tokens,
    otherwise ``en``. Empty text yields ``und``.
    """
    normalized = normalize_multilingual_text(text)
    if not normalized:
        return "und"

    turkish_hits = sum(1 for char in normalized if char in _TURKISH_CHARS)
    latin_tokens = _LATIN_WORD_RE.findall(normalized)
    if not latin_tokens and turkish_hits == 0:
        return "und"
    if turkish_hits >= 2 or (latin_tokens and turkish_hits / max(len(latin_tokens), 1) >= 0.05):
        return "tr"
    return "en"


__all__ = ["detect_language", "normalize_multilingual_text"]
