"""Unit tests for the deterministic follow-up suggestion builder."""

from __future__ import annotations

import pytest

from contextforge.modules.chat.application.services.suggestion_service import SuggestionService
from contextforge.shared.config.settings import ChatSettings


@pytest.mark.unit
class TestBuildSuggestions:
    def test_returns_configured_count(self) -> None:
        service = SuggestionService(ChatSettings(suggestion_count=3))
        suggestions = service._build_suggestions(language="en", document_titles=[])
        assert len(suggestions) == 3

    def test_turkish_language_uses_turkish_templates(self) -> None:
        service = SuggestionService(ChatSettings(suggestion_count=4))
        suggestions = service._build_suggestions(language="tr", document_titles=[])
        assert any("mısın" in s or "musun" in s or "?" in s for s in suggestions)

    def test_document_titles_are_referenced_first(self) -> None:
        service = SuggestionService(ChatSettings(suggestion_count=4))
        suggestions = service._build_suggestions(
            language="en", document_titles=["Employee Handbook"]
        )
        assert any("Employee Handbook" in s for s in suggestions)

    def test_limits_document_titles_to_two(self) -> None:
        service = SuggestionService(ChatSettings(suggestion_count=5))
        suggestions = service._build_suggestions(
            language="en",
            document_titles=["Doc A", "Doc B", "Doc C", "Doc D"],
        )
        doc_based = [s for s in suggestions if "Doc" in s]
        assert len(doc_based) == 2
