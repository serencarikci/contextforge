"""Chat-specific domain/application errors.

Most error handling reuses the shared identity/tenancy error taxonomy
(``contextforge.domain.exceptions.identity``). These types cover chat-specific
conditions that do not map cleanly onto an existing error.
"""

from __future__ import annotations

from contextforge.domain.exceptions.base import ApplicationError


class NoAccessibleKnowledgeSpacesError(ApplicationError):
    """Raised when a conversation has no knowledge spaces the caller can use."""

    code = "NO_ACCESSIBLE_KNOWLEDGE_SPACES"
    http_status = 404


__all__ = ["NoAccessibleKnowledgeSpacesError"]
