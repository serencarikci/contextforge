"""SQLAlchemy unit of work for write use cases."""

from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from contextforge.modules.admin.infrastructure.repositories.admin_stats import (
    SqlAlchemyAdminStatsRepository,
)
from contextforge.modules.admin.infrastructure.repositories.feature_flag import (
    SqlAlchemyFeatureFlagRepository,
)
from contextforge.modules.admin.infrastructure.repositories.llm_provider_config import (
    SqlAlchemyLlmProviderConfigRepository,
)
from contextforge.modules.admin.infrastructure.repositories.organization_settings import (
    SqlAlchemyOrganizationSettingsRepository,
)
from contextforge.modules.admin.infrastructure.repositories.prompt_template import (
    SqlAlchemyPromptTemplateRepository,
)
from contextforge.modules.admin.infrastructure.repositories.retention import (
    SqlAlchemyRetentionRepository,
)
from contextforge.modules.admin.infrastructure.repositories.token_pricing import (
    SqlAlchemyTokenPricingRepository,
)
from contextforge.modules.admin.infrastructure.repositories.token_usage import (
    SqlAlchemyTokenUsageRepository,
)
from contextforge.modules.audit.infrastructure.repositories.audit_event import (
    SqlAlchemyAuditEventRepository,
)
from contextforge.modules.chat.infrastructure.repositories.analytics import (
    SqlAlchemyChatAnalyticsRepository,
)
from contextforge.modules.chat.infrastructure.repositories.chat_message import (
    SqlAlchemyChatMessageRepository,
)
from contextforge.modules.chat.infrastructure.repositories.conversation import (
    SqlAlchemyConversationRepository,
)
from contextforge.modules.chat.infrastructure.repositories.feedback import (
    SqlAlchemyMessageFeedbackRepository,
)
from contextforge.modules.customers.infrastructure.repositories.customer import (
    SqlAlchemyCustomerRepository,
)
from contextforge.modules.documents.infrastructure.repositories.document import (
    SqlAlchemyDocumentRepository,
)
from contextforge.modules.documents.infrastructure.repositories.document_chunk import (
    SqlAlchemyDocumentChunkRepository,
)
from contextforge.modules.documents.infrastructure.repositories.document_parse_result import (
    SqlAlchemyDocumentParseResultRepository,
)
from contextforge.modules.identity_access.infrastructure.repositories.membership import (
    SqlAlchemyMembershipRepository,
)
from contextforge.modules.identity_access.infrastructure.repositories.rbac import (
    SqlAlchemyRbacRepository,
)
from contextforge.modules.identity_access.infrastructure.repositories.user import (
    SqlAlchemyUserRepository,
)
from contextforge.modules.ingestion.infrastructure.repositories.ingestion_job import (
    SqlAlchemyIngestionJobRepository,
)
from contextforge.modules.knowledge_spaces.infrastructure.repositories.knowledge_space import (
    SqlAlchemyKnowledgeSpaceRepository,
)
from contextforge.modules.organizations.infrastructure.repositories.organization import (
    SqlAlchemyOrganizationRepository,
)
from contextforge.modules.projects.infrastructure.repositories.project import (
    SqlAlchemyProjectRepository,
)


class SqlAlchemyUnitOfWork:
    """Explicit transaction boundary owning a single AsyncSession."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.session: AsyncSession | None = None
        self.organizations: SqlAlchemyOrganizationRepository
        self.users: SqlAlchemyUserRepository
        self.memberships: SqlAlchemyMembershipRepository
        self.rbac: SqlAlchemyRbacRepository
        self.customers: SqlAlchemyCustomerRepository
        self.projects: SqlAlchemyProjectRepository
        self.knowledge_spaces: SqlAlchemyKnowledgeSpaceRepository
        self.documents: SqlAlchemyDocumentRepository
        self.document_parses: SqlAlchemyDocumentParseResultRepository
        self.document_chunks: SqlAlchemyDocumentChunkRepository
        self.ingestion_jobs: SqlAlchemyIngestionJobRepository
        self.audit: SqlAlchemyAuditEventRepository
        self.conversations: SqlAlchemyConversationRepository
        self.chat_messages: SqlAlchemyChatMessageRepository
        self.message_feedback: SqlAlchemyMessageFeedbackRepository
        self.chat_analytics: SqlAlchemyChatAnalyticsRepository
        self.organization_settings: SqlAlchemyOrganizationSettingsRepository
        self.feature_flags: SqlAlchemyFeatureFlagRepository
        self.prompt_templates: SqlAlchemyPromptTemplateRepository
        self.llm_provider_configs: SqlAlchemyLlmProviderConfigRepository
        self.token_pricing: SqlAlchemyTokenPricingRepository
        self.token_usage: SqlAlchemyTokenUsageRepository
        self.retention: SqlAlchemyRetentionRepository
        self.admin_stats: SqlAlchemyAdminStatsRepository

    async def __aenter__(self) -> Self:
        self.session = self._session_factory()
        self.organizations = SqlAlchemyOrganizationRepository(self.session)
        self.users = SqlAlchemyUserRepository(self.session)
        self.memberships = SqlAlchemyMembershipRepository(self.session)
        self.rbac = SqlAlchemyRbacRepository(self.session)
        self.customers = SqlAlchemyCustomerRepository(self.session)
        self.projects = SqlAlchemyProjectRepository(self.session)
        self.knowledge_spaces = SqlAlchemyKnowledgeSpaceRepository(self.session)
        self.documents = SqlAlchemyDocumentRepository(self.session)
        self.document_parses = SqlAlchemyDocumentParseResultRepository(self.session)
        self.document_chunks = SqlAlchemyDocumentChunkRepository(self.session)
        self.ingestion_jobs = SqlAlchemyIngestionJobRepository(self.session)
        self.audit = SqlAlchemyAuditEventRepository(self.session)
        self.conversations = SqlAlchemyConversationRepository(self.session)
        self.chat_messages = SqlAlchemyChatMessageRepository(self.session)
        self.message_feedback = SqlAlchemyMessageFeedbackRepository(self.session)
        self.chat_analytics = SqlAlchemyChatAnalyticsRepository(self.session)
        self.organization_settings = SqlAlchemyOrganizationSettingsRepository(self.session)
        self.feature_flags = SqlAlchemyFeatureFlagRepository(self.session)
        self.prompt_templates = SqlAlchemyPromptTemplateRepository(self.session)
        self.llm_provider_configs = SqlAlchemyLlmProviderConfigRepository(self.session)
        self.token_pricing = SqlAlchemyTokenPricingRepository(self.session)
        self.token_usage = SqlAlchemyTokenUsageRepository(self.session)
        self.retention = SqlAlchemyRetentionRepository(self.session)
        self.admin_stats = SqlAlchemyAdminStatsRepository(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        _tb: TracebackType | None,
    ) -> None:
        assert self.session is not None
        try:
            if exc_type is not None:
                await self.session.rollback()
            else:
                await self.session.commit()
        finally:
            await self.session.close()
            self.session = None

    async def commit(self) -> None:
        assert self.session is not None
        await self.session.commit()

    async def rollback(self) -> None:
        assert self.session is not None
        await self.session.rollback()
