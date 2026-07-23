"""SQLAlchemy unit of work for write use cases."""

from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from contextforge.modules.audit.infrastructure.repositories.audit_event import (
    SqlAlchemyAuditEventRepository,
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
        self.audit: SqlAlchemyAuditEventRepository

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
        self.audit = SqlAlchemyAuditEventRepository(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
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
