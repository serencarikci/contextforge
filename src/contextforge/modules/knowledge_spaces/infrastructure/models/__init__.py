"""Knowledge spaces ORM models."""

from contextforge.modules.knowledge_spaces.infrastructure.models.knowledge_space import (
    KnowledgeSpaceModel,
)
from contextforge.modules.knowledge_spaces.infrastructure.models.knowledge_space_membership import (
    KnowledgeSpaceMembershipModel,
)

__all__ = ["KnowledgeSpaceMembershipModel", "KnowledgeSpaceModel"]
