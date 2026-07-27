from __future__ import annotations

from enum import StrEnum


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ConversationStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class MessageStatus(StrEnum):
    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FeedbackRating(StrEnum):
    UP = "up"
    DOWN = "down"


class FeedbackCategory(StrEnum):
    INCORRECT = "incorrect"
    INCOMPLETE = "incomplete"
    IRRELEVANT = "irrelevant"
    OUTDATED = "outdated"
    CITATION_PROBLEM = "citation_problem"
    UNSAFE = "unsafe"
    UNCLEAR = "unclear"
    OTHER = "other"


class ExportFormat(StrEnum):
    JSON = "json"
    MARKDOWN = "markdown"


class AnalyticsEventType(StrEnum):
    CONVERSATION_CREATED = "conversation_created"
    CONVERSATION_ARCHIVED = "conversation_archived"
    CONVERSATION_DELETED = "conversation_deleted"
    MESSAGE_SENT = "message_sent"
    ANSWER_GENERATED = "answer_generated"
    ANSWER_FAILED = "answer_failed"
    STREAM_CANCELLED = "stream_cancelled"
    FEEDBACK_SUBMITTED = "feedback_submitted"
    CONVERSATION_EXPORTED = "conversation_exported"


class ConversationParticipantRole(StrEnum):
    OWNER = "owner"
    PARTICIPANT = "participant"


class ChatLanguagePreference(StrEnum):
    AUTO = "auto"
    TR = "tr"
    EN = "en"


__all__ = [
    "AnalyticsEventType",
    "ChatLanguagePreference",
    "ConversationParticipantRole",
    "ConversationStatus",
    "ExportFormat",
    "FeedbackCategory",
    "FeedbackRating",
    "MessageRole",
    "MessageStatus",
]
