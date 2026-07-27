from __future__ import annotations

from uuid import uuid4

import pytest

from contextforge.modules.chat.application.services.memory_strategies.recent import (
    RecentMessagesStrategy,
)
from contextforge.modules.chat.application.services.memory_strategies.summary import (
    SummaryStrategy,
)
from contextforge.modules.chat.application.services.memory_strategies.token_budget import (
    TokenBudgetStrategy,
)
from contextforge.modules.chat.domain.entities.memory import ConversationMemory
from contextforge.modules.chat.domain.entities.message import ChatMessage
from contextforge.modules.chat.domain.enums import MessageRole


def _turn(role: MessageRole, content: str, sequence_no: int) -> ChatMessage:
    return ChatMessage(
        conversation_id=uuid4(),
        organization_id=uuid4(),
        role=role,
        content=content,
        sequence_no=sequence_no,
    )


def _sample_turns(count: int) -> list[ChatMessage]:
    turns: list[ChatMessage] = []
    for i in range(count):
        role = MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
        turns.append(_turn(role, f"Message number {i}", i + 1))
    return turns


@pytest.mark.unit
class TestRecentMessagesStrategy:
    def test_empty_messages_yields_empty_string(self) -> None:
        strategy = RecentMessagesStrategy(max_messages=5)
        assert strategy.build([], None) == ""

    def test_includes_only_last_n_messages(self) -> None:
        strategy = RecentMessagesStrategy(max_messages=2)
        turns = _sample_turns(5)
        result = strategy.build(turns, None)
        assert "Message number 3" in result
        assert "Message number 4" in result
        assert "Message number 0" not in result

    def test_formats_roles_as_labels(self) -> None:
        strategy = RecentMessagesStrategy(max_messages=2)
        turns = [_turn(MessageRole.USER, "Hi", 1), _turn(MessageRole.ASSISTANT, "Hello", 2)]
        result = strategy.build(turns, None)
        assert "User: Hi" in result
        assert "Assistant: Hello" in result


@pytest.mark.unit
class TestTokenBudgetStrategy:
    def test_empty_messages_yields_empty_string(self) -> None:
        strategy = TokenBudgetStrategy(max_tokens=1000)
        assert strategy.build([], None) == ""

    def test_always_includes_at_least_one_message(self) -> None:
        strategy = TokenBudgetStrategy(max_tokens=1)
        turns = _sample_turns(3)
        result = strategy.build(turns, None)
        assert "Message number 2" in result

    def test_respects_chronological_order(self) -> None:
        strategy = TokenBudgetStrategy(max_tokens=10_000)
        turns = _sample_turns(3)
        result = strategy.build(turns, None)
        first_index = result.index("Message number 0")
        last_index = result.index("Message number 2")
        assert first_index < last_index


@pytest.mark.unit
class TestSummaryStrategy:
    def test_no_summary_no_messages_yields_empty_string(self) -> None:
        strategy = SummaryStrategy(max_recent_messages=3)
        assert strategy.build([], None) == ""

    def test_includes_summary_text(self) -> None:
        strategy = SummaryStrategy(max_recent_messages=3)
        memory = ConversationMemory(
            conversation_id=uuid4(),
            organization_id=uuid4(),
            summary_text="Earlier the user asked about pricing.",
            covered_until_sequence=5,
            token_estimate=12,
        )
        result = strategy.build([], memory)
        assert "Earlier the user asked about pricing." in result

    def test_combines_summary_and_recent_turns(self) -> None:
        strategy = SummaryStrategy(max_recent_messages=2)
        memory = ConversationMemory(
            conversation_id=uuid4(),
            organization_id=uuid4(),
            summary_text="Prior context.",
            covered_until_sequence=2,
            token_estimate=5,
        )
        turns = _sample_turns(4)
        result = strategy.build(turns, memory)
        assert "Prior context." in result
        assert "Message number 2" in result
        assert "Message number 3" in result
        assert "Message number 0" not in result
