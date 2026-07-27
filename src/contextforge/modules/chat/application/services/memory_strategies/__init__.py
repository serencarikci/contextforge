from __future__ import annotations

from typing import Protocol

from contextforge.modules.chat.domain.entities.memory import ConversationMemory
from contextforge.modules.chat.domain.entities.message import ChatMessage
from contextforge.modules.chat.domain.enums import MessageRole


class MemoryStrategy(Protocol):
    def build(self, messages: list[ChatMessage], memory: ConversationMemory | None) -> str: ...


def format_turn(message: ChatMessage) -> str:
    label = "User" if message.role == MessageRole.USER else "Assistant"
    content = " ".join(message.content.split())
    return f"{label}: {content}"


__all__ = ["MemoryStrategy", "format_turn"]
