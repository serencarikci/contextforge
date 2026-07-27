from __future__ import annotations

from uuid import uuid4

import pytest

from contextforge.modules.chat.domain.entities.feedback import MessageFeedback
from contextforge.modules.chat.domain.entities.memory import ConversationMemory
from contextforge.modules.chat.domain.enums import FeedbackCategory, FeedbackRating


def _make_feedback(**overrides: object) -> MessageFeedback:
    defaults: dict[str, object] = {
        "message_id": uuid4(),
        "conversation_id": uuid4(),
        "organization_id": uuid4(),
        "user_id": uuid4(),
        "rating": FeedbackRating.UP,
    }
    defaults.update(overrides)
    return MessageFeedback(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestMessageFeedback:
    def test_score_out_of_range_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="score"):
            _make_feedback(score=6)

    def test_score_within_range_is_accepted(self) -> None:
        feedback = _make_feedback(score=3)
        assert feedback.score == 3

    def test_comment_is_trimmed_and_truncated(self) -> None:
        feedback = _make_feedback(comment="  " + "x" * 3000 + "  ")
        assert feedback.comment is not None
        assert len(feedback.comment) == 2000

    def test_blank_comment_becomes_none(self) -> None:
        feedback = _make_feedback(comment="   ")
        assert feedback.comment is None

    def test_update_changes_rating_and_category(self) -> None:
        feedback = _make_feedback()
        feedback.update(
            rating=FeedbackRating.DOWN,
            score=2,
            category=FeedbackCategory.INCOMPLETE,
            comment="Missing details",
        )
        assert feedback.rating == FeedbackRating.DOWN
        assert feedback.score == 2
        assert feedback.category == FeedbackCategory.INCOMPLETE
        assert feedback.comment == "Missing details"


@pytest.mark.unit
def test_conversation_memory_update() -> None:
    memory = ConversationMemory(
        conversation_id=uuid4(),
        organization_id=uuid4(),
        summary_text="Initial summary",
        covered_until_sequence=4,
        token_estimate=10,
    )
    before = memory.updated_at
    memory.update(summary_text="Updated summary", covered_until_sequence=8, token_estimate=20)
    assert memory.summary_text == "Updated summary"
    assert memory.covered_until_sequence == 8
    assert memory.token_estimate == 20
    assert memory.updated_at >= before
