from __future__ import annotations

from uuid import uuid4

import pytest

from contextforge.domain.exceptions.identity import InvalidResourceStateError
from contextforge.modules.chat.domain.entities.message import ChatMessage, MessageCitation
from contextforge.modules.chat.domain.enums import MessageRole, MessageStatus


def _make_message(**overrides: object) -> ChatMessage:
    defaults: dict[str, object] = {
        "conversation_id": uuid4(),
        "organization_id": uuid4(),
        "role": MessageRole.USER,
        "content": "Hello there",
        "sequence_no": 1,
    }
    defaults.update(overrides)
    return ChatMessage(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestChatMessageValidation:
    def test_negative_sequence_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="sequence_no"):
            _make_message(sequence_no=-1)

    def test_oversized_content_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="content"):
            _make_message(content="x" * 32_001)

    def test_default_status_is_completed(self) -> None:
        message = _make_message()
        assert message.status == MessageStatus.COMPLETED


@pytest.mark.unit
class TestChatMessageLifecycle:
    def test_mark_streaming(self) -> None:
        message = _make_message(status=MessageStatus.PENDING, content="")
        message.mark_streaming()
        assert message.status == MessageStatus.STREAMING

    def test_append_delta_while_streaming(self) -> None:
        message = _make_message(status=MessageStatus.PENDING, content="")
        message.mark_streaming()
        message.append_delta("Hel")
        message.append_delta("lo")
        assert message.content == "Hello"

    def test_append_delta_after_completion_raises(self) -> None:
        message = _make_message()
        with pytest.raises(InvalidResourceStateError):
            message.append_delta("more")

    def test_mark_completed_sets_fields(self) -> None:
        message = _make_message(status=MessageStatus.PENDING, content="")
        message.mark_completed(
            content="Final answer",
            model_name="gpt-test",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            latency_ms=120,
            retrieval_ms=40,
            language="en",
        )
        assert message.status == MessageStatus.COMPLETED
        assert message.content == "Final answer"
        assert message.model_name == "gpt-test"
        assert message.total_tokens == 15
        assert message.error_code is None

    def test_mark_failed_truncates_long_errors(self) -> None:
        message = _make_message(status=MessageStatus.PENDING, content="")
        message.mark_failed(error_code="BOOM", error_message="x" * 3000)
        assert message.status == MessageStatus.FAILED
        assert message.error_code == "BOOM"
        assert len(message.error_message or "") == 2000

    def test_mark_cancelled(self) -> None:
        message = _make_message(status=MessageStatus.STREAMING, content="partial")
        message.mark_cancelled()
        assert message.status == MessageStatus.CANCELLED


@pytest.mark.unit
def test_message_citation_defaults() -> None:
    citation = MessageCitation(
        message_id=uuid4(),
        organization_id=uuid4(),
        document_id=uuid4(),
        document_title="Handbook",
        chunk_id=uuid4(),
        knowledge_space_id=uuid4(),
        snippet="An excerpt",
        rank=1,
    )
    assert citation.page is None
    assert citation.chunk_index is None
    assert citation.rank == 1
