"""Conversation memory strategies: turn recent turns into prompt context.

Each strategy implements :class:`MemoryStrategy` and converts a (already
fetched, oldest-first) slice of a conversation's messages -- plus an optional
durable summary -- into a single string appended to the RAG prompt via
``RagQueryService``'s ``history_context`` parameter.
"""

from __future__ import annotations

from typing import Protocol

from contextforge.modules.chat.domain.entities.memory import ConversationMemory
from contextforge.modules.chat.domain.entities.message import ChatMessage
from contextforge.modules.chat.domain.enums import MessageRole


class MemoryStrategy(Protocol):
    """Builds a history-context string from prior conversation turns."""

    def build(self, messages: list[ChatMessage], memory: ConversationMemory | None) -> str:
        """Return a prompt-ready history string (empty if there is nothing to add)."""
        ...


def format_turn(message: ChatMessage) -> str:
    """Render one message as a single labeled line."""
    label = "User" if message.role == MessageRole.USER else "Assistant"
    content = " ".join(message.content.split())
    return f"{label}: {content}"


__all__ = ["MemoryStrategy", "format_turn"]
