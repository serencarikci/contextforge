"""Application service for generating follow-up question suggestions.

Uses a deterministic, template-based fallback (no LLM call) so suggestions
are always available and never add latency or cost to a chat turn. Templates
are localized for Turkish and English.
"""

from __future__ import annotations

from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import ResourceNotFoundError
from contextforge.modules.chat.application.services.access import ensure_conversation_access
from contextforge.modules.chat.domain.enums import MessageRole, MessageStatus
from contextforge.shared.config.settings import ChatSettings

_GENERIC_TEMPLATES_EN = (
    "Can you provide more detail on this topic?",
    "What are the key risks or limitations here?",
    "Are there any related best practices I should know about?",
    "Can you summarize this in a few bullet points?",
    "What would you recommend as the next step?",
)

_GENERIC_TEMPLATES_TR = (
    "Bu konu hakkında daha fazla ayrıntı verebilir misin?",
    "Buradaki temel riskler veya kısıtlamalar nelerdir?",
    "Bilmem gereken ilgili en iyi uygulamalar var mı?",
    "Bunu birkaç madde halinde özetleyebilir misin?",
    "Sıradaki adım olarak ne önerirsin?",
)

_DOCUMENT_TEMPLATE_EN = 'What else does "{title}" say about this?'
_DOCUMENT_TEMPLATE_TR = '"{title}" bu konuda başka neler söylüyor?'


class SuggestionService:
    """Generates a short list of follow-up questions for a conversation."""

    def __init__(self, settings: ChatSettings) -> None:
        self._settings = settings

    async def suggest(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        conversation_id: UUID,
    ) -> list[str]:
        async with uow:
            ctx.require_permission("chat:use")
            conversation = await uow.conversations.get(ctx.organization_id, conversation_id)
            if conversation is None:
                raise ResourceNotFoundError("Conversation not found.")
            await ensure_conversation_access(uow, ctx, conversation)

            messages, _total = await uow.chat_messages.list_by_conversation(
                ctx.organization_id, conversation_id, limit=1, offset=0, ascending=False
            )
            last_assistant = next(
                (
                    message
                    for message in messages
                    if message.role == MessageRole.ASSISTANT
                    and message.status == MessageStatus.COMPLETED
                ),
                None,
            )
            language = conversation.detected_language or self._settings.default_language
            titles: list[str] = []
            if last_assistant is not None:
                citations = await uow.chat_messages.list_citations(
                    ctx.organization_id, last_assistant.id
                )
                seen: set[str] = set()
                for citation in citations:
                    if citation.document_title not in seen:
                        seen.add(citation.document_title)
                        titles.append(citation.document_title)

        return self._build_suggestions(language=language, document_titles=titles)

    def _build_suggestions(self, *, language: str, document_titles: list[str]) -> list[str]:
        is_turkish = language == "tr"
        doc_template = _DOCUMENT_TEMPLATE_TR if is_turkish else _DOCUMENT_TEMPLATE_EN
        generic = _GENERIC_TEMPLATES_TR if is_turkish else _GENERIC_TEMPLATES_EN

        suggestions: list[str] = [doc_template.format(title=title) for title in document_titles[:2]]
        for template in generic:
            if len(suggestions) >= self._settings.suggestion_count:
                break
            suggestions.append(template)
        return suggestions[: self._settings.suggestion_count]


__all__ = ["SuggestionService"]
