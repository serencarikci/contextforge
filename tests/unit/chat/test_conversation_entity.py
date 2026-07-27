from __future__ import annotations

from uuid import uuid4

import pytest

from contextforge.domain.exceptions.identity import InvalidResourceStateError
from contextforge.modules.chat.domain.entities.conversation import (
    DEFAULT_TITLE,
    MAX_TITLE_LENGTH,
    Conversation,
    normalize_title,
)
from contextforge.modules.chat.domain.enums import (
    ChatLanguagePreference,
    ConversationStatus,
)


def _make_conversation(**overrides: object) -> Conversation:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "owner_user_id": uuid4(),
    }
    defaults.update(overrides)
    return Conversation(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestNormalizeTitle:
    def test_none_falls_back_to_default(self) -> None:
        assert normalize_title(None) == DEFAULT_TITLE

    def test_blank_falls_back_to_default(self) -> None:
        assert normalize_title("   ") == DEFAULT_TITLE

    def test_collapses_internal_whitespace(self) -> None:
        assert normalize_title("  Hello   world  ") == "Hello world"

    def test_truncates_overlong_titles(self) -> None:
        title = normalize_title("x" * (MAX_TITLE_LENGTH + 50))
        assert len(title) == MAX_TITLE_LENGTH


@pytest.mark.unit
class TestConversationLifecycle:
    def test_new_conversation_is_active(self) -> None:
        conversation = _make_conversation()
        assert conversation.status == ConversationStatus.ACTIVE
        assert conversation.pinned is False
        assert conversation.deleted_at is None

    def test_rename_normalizes_title(self) -> None:
        conversation = _make_conversation()
        conversation.rename("  My Chat  ")
        assert conversation.title == "My Chat"

    def test_set_pinned_toggles_flag(self) -> None:
        conversation = _make_conversation()
        conversation.set_pinned(True)
        assert conversation.pinned is True
        conversation.set_pinned(False)
        assert conversation.pinned is False

    def test_set_preferred_language(self) -> None:
        conversation = _make_conversation()
        conversation.set_preferred_language(ChatLanguagePreference.TR)
        assert conversation.preferred_language == ChatLanguagePreference.TR

    def test_record_detected_language(self) -> None:
        conversation = _make_conversation()
        conversation.record_detected_language("tr")
        assert conversation.detected_language == "tr"

    def test_touch_activity_updates_timestamp(self) -> None:
        conversation = _make_conversation()
        before = conversation.last_activity_at
        conversation.touch_activity()
        assert conversation.last_activity_at >= before

    def test_ensure_open_for_messages_allows_active(self) -> None:
        conversation = _make_conversation()
        conversation.ensure_open_for_messages()

    def test_ensure_open_for_messages_rejects_archived(self) -> None:
        conversation = _make_conversation()
        conversation.archive()
        with pytest.raises(InvalidResourceStateError):
            conversation.ensure_open_for_messages()

    def test_archive_then_restore(self) -> None:
        conversation = _make_conversation()
        conversation.archive()
        assert conversation.status == ConversationStatus.ARCHIVED
        conversation.restore()
        assert conversation.status == ConversationStatus.ACTIVE

    def test_soft_delete_sets_deleted_at(self) -> None:
        conversation = _make_conversation()
        conversation.soft_delete()
        assert conversation.status == ConversationStatus.DELETED
        assert conversation.deleted_at is not None

    def test_restore_from_soft_delete_clears_deleted_at(self) -> None:
        conversation = _make_conversation()
        conversation.soft_delete()
        conversation.restore()
        assert conversation.status == ConversationStatus.ACTIVE
        assert conversation.deleted_at is None

    def test_cannot_rename_deleted_conversation(self) -> None:
        conversation = _make_conversation()
        conversation.soft_delete()
        with pytest.raises(InvalidResourceStateError):
            conversation.rename("New title")

    def test_cannot_pin_deleted_conversation(self) -> None:
        conversation = _make_conversation()
        conversation.soft_delete()
        with pytest.raises(InvalidResourceStateError):
            conversation.set_pinned(True)
