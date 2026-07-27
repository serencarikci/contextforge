from __future__ import annotations

from enum import StrEnum


class PromptLanguage(StrEnum):
    EN = "en"
    TR = "tr"


class PromptTemplateName(StrEnum):
    SYSTEM = "system"
    USER = "user"
    CITATION = "citation"
    MULTILINGUAL = "multilingual"


class LlmProviderKind(StrEnum):
    MOCK = "mock"
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    OPENAI_COMPATIBLE = "openai_compatible"


class RetentionResourceType(StrEnum):
    CONVERSATIONS = "conversations"
    DOCUMENTS = "documents"
    AUDIT_EVENTS = "audit_events"
    ANALYTICS = "analytics"
    EXPORTS = "exports"
    INGESTION_JOBS = "ingestion_jobs"
    TEMPORARY = "temporary"


class RetentionRunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class LlmConnectivityStatus(StrEnum):
    OK = "ok"
    ERROR = "error"
    SKIPPED = "skipped"


__all__ = [
    "LlmConnectivityStatus",
    "LlmProviderKind",
    "PromptLanguage",
    "PromptTemplateName",
    "RetentionResourceType",
    "RetentionRunStatus",
]
