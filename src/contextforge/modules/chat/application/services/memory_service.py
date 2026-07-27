"""Conversation memory service: prompt history context + rolling summaries.

All methods expect to be called from *inside* an already-open
``SqlAlchemyUnitOfWork`` context (``async with uow:``) -- typically from
``ChatService`` -- since they read/write conversation and message repositories
as part of a larger unit of work.
"""

from __future__ import annotations

from uuid import UUID

from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.modules.chat.application.services.memory_strategies import (
    MemoryStrategy,
    format_turn,
)
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
from contextforge.shared.config.settings import ChatSettings
from contextforge.shared.utilities.tokens import estimate_tokens

_COMPACT_LINE_MAX_CHARS = 240
_SUMMARY_MAX_CHARS = 4000


class MemoryService:
    """Builds prompt-ready conversation history and maintains rolling summaries."""

    def __init__(self, settings: ChatSettings) -> None:
        self._settings = settings

    def _strategy(self) -> MemoryStrategy:
        name = self._settings.memory_strategy
        if name == "recent":
            return RecentMessagesStrategy(max_messages=self._settings.history_max_messages)
        if name == "summary":
            return SummaryStrategy(
                max_recent_messages=self._settings.memory_summary_recent_messages
            )
        return TokenBudgetStrategy(max_tokens=self._settings.memory_token_budget)

    async def build_history_context(
        self,
        uow: SqlAlchemyUnitOfWork,
        *,
        organization_id: UUID,
        conversation_id: UUID,
    ) -> str | None:
        """Return prompt-ready history text, or ``None`` if there is none yet."""
        strategy = self._strategy()
        if isinstance(strategy, SummaryStrategy):
            memory = await uow.conversations.get_memory(organization_id, conversation_id)
            after_sequence = memory.covered_until_sequence if memory is not None else 0
            messages = await uow.chat_messages.list_after_sequence(
                organization_id, conversation_id, after_sequence=after_sequence
            )
            text = strategy.build(messages, memory)
        else:
            messages = await uow.chat_messages.list_recent_for_context(
                organization_id, conversation_id, limit=self._settings.history_max_messages
            )
            text = strategy.build(messages, None)
        return text or None

    async def maybe_update_summary(
        self,
        uow: SqlAlchemyUnitOfWork,
        *,
        organization_id: UUID,
        conversation_id: UUID,
    ) -> ConversationMemory | None:
        """Fold older turns into the rolling summary once enough have accumulated.

        No-op unless ``memory_strategy`` is ``"summary"``. Uses deterministic,
        extractive summarization (each folded turn is compacted to a single
        short line) rather than an LLM call, so memory maintenance never
        depends on LLM availability and never performs a second LLM round-trip
        per message.
        """
        if self._settings.memory_strategy != "summary":
            return None

        memory = await uow.conversations.get_memory(organization_id, conversation_id)
        after_sequence = memory.covered_until_sequence if memory is not None else 0
        pending = await uow.chat_messages.list_after_sequence(
            organization_id, conversation_id, after_sequence=after_sequence
        )
        trigger = self._settings.memory_summary_trigger_messages
        keep_recent = self._settings.memory_summary_recent_messages
        if len(pending) <= trigger:
            return memory

        to_fold = pending[: len(pending) - keep_recent]
        if not to_fold:
            return memory

        folded_lines = [self._compact_turn(message) for message in to_fold]
        existing = memory.summary_text if memory is not None else ""
        combined = "\n".join(line for line in [existing, *folded_lines] if line)
        new_summary = combined[-_SUMMARY_MAX_CHARS:]
        covered_until = to_fold[-1].sequence_no

        if memory is None:
            memory = ConversationMemory(
                conversation_id=conversation_id,
                organization_id=organization_id,
                summary_text=new_summary,
                covered_until_sequence=covered_until,
                token_estimate=estimate_tokens(new_summary),
            )
        else:
            memory.update(
                summary_text=new_summary,
                covered_until_sequence=covered_until,
                token_estimate=estimate_tokens(new_summary),
            )
        return await uow.conversations.upsert_memory(memory)

    @staticmethod
    def _compact_turn(message: ChatMessage) -> str:
        line = format_turn(message)
        if len(line) <= _COMPACT_LINE_MAX_CHARS:
            return line
        return f"{line[: _COMPACT_LINE_MAX_CHARS - 1]}…"


__all__ = ["MemoryService"]
