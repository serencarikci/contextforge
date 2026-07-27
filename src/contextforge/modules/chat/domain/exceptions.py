from __future__ import annotations

from contextforge.domain.exceptions.base import ApplicationError


class NoAccessibleKnowledgeSpacesError(ApplicationError):
    code = "NO_ACCESSIBLE_KNOWLEDGE_SPACES"
    http_status = 404


__all__ = ["NoAccessibleKnowledgeSpacesError"]
