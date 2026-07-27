"""Conversation aggregate: a multi-turn chat session scoped to an organization."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from contextforge.domain.exceptions.identity import InvalidResourceStateError
from contextforge.modules.chat.domain.enums import (
    ChatLanguagePreference,
    ConversationParticipantRole,
    ConversationStatus,
)
from contextforge.shared.utilities.datetime import utc_now

MAX_TITLE_LENGTH = 200
DEFAULT_TITLE = "New conversation"


def normalize_title(title: str | None) -> str:
    """Collapse whitespace and enforce length bounds, falling back to a default."""
    cleaned = " ".join((title or "").split()).strip()
    if not cleaned:
        return DEFAULT_TITLE
    if len(cleaned) > MAX_TITLE_LENGTH:
        cleaned = cleaned[:MAX_TITLE_LENGTH].rstrip()
    return cleaned


@dataclass(slots=True)
class Conversation:
    """A chat session between one or more users and the assistant."""

    organization_id: UUID
    owner_user_id: UUID
    id: UUID = field(default_factory=uuid4)
    title: str = DEFAULT_TITLE
    status: ConversationStatus = ConversationStatus.ACTIVE
    preferred_language: ChatLanguagePreference = ChatLanguagePreference.AUTO
    detected_language: str | None = None
    pinned: bool = False
    last_activity_at: datetime = field(default_factory=utc_now)
    summary_text: str | None = None
    deleted_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.title = normalize_title(self.title)

    def _ensure_mutable(self) -> None:
        if self.status == ConversationStatus.DELETED:
            raise InvalidResourceStateError("Deleted conversations cannot be modified.")

    def ensure_open_for_messages(self) -> None:
        """Raise unless the conversation can currently accept new messages."""
        if self.status != ConversationStatus.ACTIVE:
            raise InvalidResourceStateError("Only active conversations can accept new messages.")

    def rename(self, title: str) -> None:
        self._ensure_mutable()
        self.title = normalize_title(title)
        self.updated_at = utc_now()

    def set_pinned(self, pinned: bool) -> None:
        self._ensure_mutable()
        self.pinned = pinned
        self.updated_at = utc_now()

    def set_preferred_language(self, preference: ChatLanguagePreference) -> None:
        self._ensure_mutable()
        self.preferred_language = preference
        self.updated_at = utc_now()

    def record_detected_language(self, language: str) -> None:
        self.detected_language = language
        self.updated_at = utc_now()

    def touch_activity(self) -> None:
        self.last_activity_at = utc_now()
        self.updated_at = utc_now()

    def archive(self) -> None:
        self._ensure_mutable()
        self.status = ConversationStatus.ARCHIVED
        self.updated_at = utc_now()

    def restore(self) -> None:
        """Reactivate an archived or soft-deleted conversation."""
        self.status = ConversationStatus.ACTIVE
        self.deleted_at = None
        self.updated_at = utc_now()

    def soft_delete(self) -> None:
        self.status = ConversationStatus.DELETED
        self.deleted_at = utc_now()
        self.updated_at = utc_now()


@dataclass(slots=True)
class ConversationParticipant:
    """A user granted access to a conversation."""

    conversation_id: UUID
    organization_id: UUID
    user_id: UUID
    role: ConversationParticipantRole = ConversationParticipantRole.PARTICIPANT
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class ConversationKnowledgeSpaceLink:
    """Associates a conversation with a knowledge space used for grounding."""

    conversation_id: UUID
    knowledge_space_id: UUID
    organization_id: UUID


__all__ = [
    "DEFAULT_TITLE",
    "MAX_TITLE_LENGTH",
    "Conversation",
    "ConversationKnowledgeSpaceLink",
    "ConversationParticipant",
    "normalize_title",
]
