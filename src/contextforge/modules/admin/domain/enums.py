"""Domain enums for the administration and governance module."""

from __future__ import annotations

from enum import StrEnum


class PromptLanguage(StrEnum):
    """Languages a prompt template can be authored in."""

    EN = "en"
    TR = "tr"


class PromptTemplateName(StrEnum):
    """The prompt slots a bundle is composed of.

    Mirrors the keys of the YAML bundles under
    ``modules/rag/application/prompts`` so a database row can override exactly
    one slot without replacing the whole bundle.
    """

    SYSTEM = "system"
    USER = "user"
    CITATION = "citation"
    MULTILINGUAL = "multilingual"


class LlmProviderKind(StrEnum):
    """Provider implementations an organization can be configured against."""

    MOCK = "mock"
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    OPENAI_COMPATIBLE = "openai_compatible"


class RetentionResourceType(StrEnum):
    """Resource families a retention policy can target."""

    CONVERSATIONS = "conversations"
    DOCUMENTS = "documents"
    AUDIT_EVENTS = "audit_events"
    ANALYTICS = "analytics"
    EXPORTS = "exports"
    INGESTION_JOBS = "ingestion_jobs"
    TEMPORARY = "temporary"


class RetentionRunStatus(StrEnum):
    """Lifecycle of a single retention policy execution."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class LlmConnectivityStatus(StrEnum):
    """Outcome of a provider connectivity probe."""

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
