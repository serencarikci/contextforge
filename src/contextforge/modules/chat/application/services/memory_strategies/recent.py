"""Recent-messages memory strategy: include the last N turns verbatim."""

from __future__ import annotations

from contextforge.modules.chat.application.services.memory_strategies import format_turn
from contextforge.modules.chat.domain.entities.memory import ConversationMemory
from contextforge.modules.chat.domain.entities.message import ChatMessage


class RecentMessagesStrategy:
    """Includes the last ``max_messages`` turns, formatted chronologically."""

    def __init__(self, *, max_messages: int) -> None:
        self._max_messages = max_messages

    def build(self, messages: list[ChatMessage], memory: ConversationMemory | None) -> str:
        del memory
        window = messages[-self._max_messages :] if messages else []
        if not window:
            return ""
        return "\n".join(format_turn(message) for message in window)


__all__ = ["RecentMessagesStrategy"]
