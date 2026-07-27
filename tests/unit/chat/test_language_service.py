"""Unit tests for the heuristic Turkish/English language detector."""

from __future__ import annotations

import pytest

from contextforge.modules.chat.application.services.language_service import LanguageService
from contextforge.modules.chat.domain.enums import ChatLanguagePreference
from contextforge.shared.config.settings import ChatSettings


@pytest.fixture
def service() -> LanguageService:
    return LanguageService(ChatSettings())


@pytest.mark.unit
class TestDetect:
    def test_turkish_characters_force_turkish(self, service: LanguageService) -> None:
        assert service.detect("Bu döküman çok güzel") == "tr"

    def test_turkish_stopwords_without_special_chars(self, service: LanguageService) -> None:
        assert service.detect("bu ve bir ile ama gibi") == "tr"

    def test_english_stopwords_detected(self, service: LanguageService) -> None:
        assert service.detect("What is the policy for this and that") == "en"

    def test_empty_text_falls_back_to_default(self, service: LanguageService) -> None:
        default_language = ChatSettings().default_language
        assert service.detect("") == default_language

    def test_ambiguous_text_falls_back_to_default(self, service: LanguageService) -> None:
        default_language = ChatSettings().default_language
        assert service.detect("12345 !!! ???") == default_language


@pytest.mark.unit
class TestResolve:
    def test_explicit_turkish_preference_wins(self, service: LanguageService) -> None:
        result = service.resolve(preference=ChatLanguagePreference.TR, message_text="Hello world")
        assert result == "tr"

    def test_explicit_english_preference_wins(self, service: LanguageService) -> None:
        result = service.resolve(preference=ChatLanguagePreference.EN, message_text="Merhaba dünya")
        assert result == "en"

    def test_auto_preference_detects_language(self, service: LanguageService) -> None:
        result = service.resolve(
            preference=ChatLanguagePreference.AUTO, message_text="Merhaba, nasılsın?"
        )
        assert result == "tr"
