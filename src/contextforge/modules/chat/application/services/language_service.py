"""Lightweight Turkish/English language detection heuristic.

This is intentionally not a full statistical language identifier: chat
messages are short, and the goal is a fast, dependency-free heuristic that is
"good enough" to pick a prompt language and a citation/suggestion language.
"""

from __future__ import annotations

import re

from contextforge.modules.chat.domain.enums import ChatLanguagePreference
from contextforge.shared.config.settings import ChatSettings

_TURKISH_CHARS = re.compile(r"[çğıöşüÇĞİÖŞÜ]")

_TURKISH_STOPWORDS = frozenset(
    {
        "ve",
        "bir",
        "bu",
        "şu",
        "için",
        "ile",
        "çok",
        "ama",
        "fakat",
        "gibi",
        "değil",
        "mi",
        "mı",
        "mu",
        "mü",
        "ne",
        "nasıl",
        "neden",
        "niçin",
        "merhaba",
        "selam",
        "teşekkür",
        "teşekkürler",
        "lütfen",
        "evet",
        "hayır",
        "olan",
        "olarak",
        "kadar",
        "daha",
        "en",
        "de",
        "da",
        "ki",
        "hangi",
        "nerede",
        "kim",
        "benim",
        "senin",
        "bizim",
        "onun",
    }
)

_ENGLISH_STOPWORDS = frozenset(
    {
        "the",
        "is",
        "are",
        "and",
        "or",
        "what",
        "how",
        "why",
        "when",
        "where",
        "who",
        "which",
        "please",
        "thanks",
        "thank",
        "you",
        "this",
        "that",
        "with",
        "for",
        "can",
        "could",
        "would",
        "hello",
        "hi",
        "my",
        "your",
        "our",
        "their",
        "does",
        "do",
    }
)

_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


class LanguageService:
    """Detects tr/en for chat messages and resolves conversation language."""

    def __init__(self, settings: ChatSettings) -> None:
        self._settings = settings

    def detect(self, text: str) -> str:
        """Return ``"tr"`` or ``"en"`` for ``text`` using a cheap heuristic."""
        if _TURKISH_CHARS.search(text):
            return "tr"

        words = [word.lower() for word in _WORD_RE.findall(text)]
        if not words:
            return self._settings.default_language

        turkish_hits = sum(1 for word in words if word in _TURKISH_STOPWORDS)
        english_hits = sum(1 for word in words if word in _ENGLISH_STOPWORDS)

        if turkish_hits > english_hits:
            return "tr"
        if english_hits > turkish_hits:
            return "en"
        return self._settings.default_language

    def resolve(
        self,
        *,
        preference: ChatLanguagePreference,
        message_text: str,
    ) -> str:
        """Resolve the effective language for a message given user preference."""
        if preference == ChatLanguagePreference.TR:
            return "tr"
        if preference == ChatLanguagePreference.EN:
            return "en"
        return self.detect(message_text)


__all__ = ["LanguageService"]
