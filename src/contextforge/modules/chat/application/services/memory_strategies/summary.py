"""Summary memory strategy: durable summary + a small window of recent turns."""

from __future__ import annotations

from contextforge.modules.chat.application.services.memory_strategies import format_turn
from contextforge.modules.chat.domain.entities.memory import ConversationMemory
from contextforge.modules.chat.domain.entities.message import ChatMessage


class SummaryStrategy:
    """Combines a durable rolling summary with the most recent turns.

    ``messages`` is expected to already be filtered to those *after*
    ``memory.covered_until_sequence`` (see ``MemoryService``); this strategy
    additionally caps how many of those recent turns it includes verbatim.
    """

    def __init__(self, *, max_recent_messages: int) -> None:
        self._max_recent_messages = max_recent_messages

    def build(self, messages: list[ChatMessage], memory: ConversationMemory | None) -> str:
        parts: list[str] = []
        if memory is not None and memory.summary_text.strip():
            parts.append(f"Summary of earlier conversation: {memory.summary_text.strip()}")
        window = messages[-self._max_recent_messages :] if messages else []
        if window:
            parts.append("\n".join(format_turn(message) for message in window))
        return "\n\n".join(parts)


__all__ = ["SummaryStrategy"]
