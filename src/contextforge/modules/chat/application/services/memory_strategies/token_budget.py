"""Token-budget memory strategy: greedily fit the most recent turns."""

from __future__ import annotations

from contextforge.modules.chat.application.services.memory_strategies import format_turn
from contextforge.modules.chat.domain.entities.memory import ConversationMemory
from contextforge.modules.chat.domain.entities.message import ChatMessage
from contextforge.shared.utilities.tokens import estimate_tokens


class TokenBudgetStrategy:
    """Includes as many of the most recent turns as fit within a token budget."""

    def __init__(self, *, max_tokens: int) -> None:
        self._max_tokens = max_tokens

    def build(self, messages: list[ChatMessage], memory: ConversationMemory | None) -> str:
        del memory
        selected: list[ChatMessage] = []
        used_tokens = 0
        for message in reversed(messages):
            tokens = estimate_tokens(message.content)
            if selected and used_tokens + tokens > self._max_tokens:
                break
            selected.append(message)
            used_tokens += tokens
        selected.reverse()
        if not selected:
            return ""
        return "\n".join(format_turn(message) for message in selected)


__all__ = ["TokenBudgetStrategy"]
