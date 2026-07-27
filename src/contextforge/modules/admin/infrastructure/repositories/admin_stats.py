from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from contextforge.modules.audit.infrastructure.models.audit_event import AuditEventModel
from contextforge.modules.chat.infrastructure.models.conversation import (
    ConversationKnowledgeSpaceModel,
    ConversationModel,
)
from contextforge.modules.chat.infrastructure.models.message import ChatMessageModel
from contextforge.modules.documents.infrastructure.models.document import DocumentModel
from contextforge.modules.documents.infrastructure.models.document_chunk import DocumentChunkModel
from contextforge.modules.documents.infrastructure.models.document_parse_result import (
    DocumentParseResultModel,
)
from contextforge.modules.identity_access.infrastructure.models.membership import (
    OrganizationMembershipModel,
)
from contextforge.modules.ingestion.infrastructure.models.ingestion_job import IngestionJobModel
from contextforge.modules.knowledge_spaces.infrastructure.models.knowledge_space import (
    KnowledgeSpaceModel,
)


@dataclass(frozen=True, slots=True)
class DashboardCounts:
    membership_count: int
    active_membership_count: int
    document_count: int
    conversation_count: int
    ingestion_pending: int
    ingestion_running: int
    ingestion_failed: int
    audit_recent_count: int
    knowledge_space_count: int


@dataclass(frozen=True, slots=True)
class DocumentOverviewStats:
    by_status: dict[str, int]
    by_parse_status: dict[str, int]
    by_embedding_status: dict[str, int]
    recent_failed_parse_count: int


@dataclass(frozen=True, slots=True)
class KnowledgeSpaceStats:
    document_count: int
    chunk_count: int
    conversation_link_count: int
    knowledge_space_id: UUID


@dataclass(frozen=True, slots=True)
class IngestionOverviewStats:
    by_status: dict[str, int]


@dataclass(frozen=True, slots=True)
class UsageOverviewStats:
    active_memberships: int
    conversations: int
    messages: int
    documents: int
    feedback_count: int


class SqlAlchemyAdminStatsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def dashboard_counts(
        self, organization_id: UUID, *, audit_since: datetime
    ) -> DashboardCounts:
        membership_count = await self._count(
            select(func.count())
            .select_from(OrganizationMembershipModel)
            .where(OrganizationMembershipModel.organization_id == organization_id)
        )
        active_membership_count = await self._count(
            select(func.count())
            .select_from(OrganizationMembershipModel)
            .where(
                and_(
                    OrganizationMembershipModel.organization_id == organization_id,
                    OrganizationMembershipModel.status == "active",
                )
            )
        )
        document_count = await self._count(
            select(func.count())
            .select_from(DocumentModel)
            .where(
                and_(
                    DocumentModel.organization_id == organization_id,
                    DocumentModel.status == "active",
                )
            )
        )
        conversation_count = await self._count(
            select(func.count())
            .select_from(ConversationModel)
            .where(ConversationModel.organization_id == organization_id)
        )
        ingestion_pending = await self._count_ingestion(organization_id, "pending")
        ingestion_running = await self._count_ingestion(organization_id, "running")
        ingestion_failed = await self._count_ingestion(organization_id, "failed")
        audit_recent_count = await self._count(
            select(func.count())
            .select_from(AuditEventModel)
            .where(
                and_(
                    AuditEventModel.organization_id == organization_id,
                    AuditEventModel.occurred_at >= audit_since,
                )
            )
        )
        knowledge_space_count = await self._count(
            select(func.count())
            .select_from(KnowledgeSpaceModel)
            .where(KnowledgeSpaceModel.organization_id == organization_id)
        )
        return DashboardCounts(
            membership_count=membership_count,
            active_membership_count=active_membership_count,
            document_count=document_count,
            conversation_count=conversation_count,
            ingestion_pending=ingestion_pending,
            ingestion_running=ingestion_running,
            ingestion_failed=ingestion_failed,
            audit_recent_count=audit_recent_count,
            knowledge_space_count=knowledge_space_count,
        )

    async def document_overview(self, organization_id: UUID) -> DocumentOverviewStats:
        by_status = await self._group_count(
            DocumentModel.status,
            DocumentModel.organization_id == organization_id,
        )
        by_parse = await self._group_count(
            DocumentParseResultModel.status,
            DocumentParseResultModel.organization_id == organization_id,
        )
        by_embed = await self._group_count(
            DocumentChunkModel.embedding_status,
            DocumentChunkModel.organization_id == organization_id,
        )
        failed_parse = by_parse.get("failed", 0)
        return DocumentOverviewStats(
            by_status=by_status,
            by_parse_status=by_parse,
            by_embedding_status=by_embed,
            recent_failed_parse_count=failed_parse,
        )

    async def knowledge_space_stats(
        self, organization_id: UUID, knowledge_space_id: UUID
    ) -> KnowledgeSpaceStats:
        document_count = await self._count(
            select(func.count())
            .select_from(DocumentModel)
            .where(
                and_(
                    DocumentModel.organization_id == organization_id,
                    DocumentModel.knowledge_space_id == knowledge_space_id,
                    DocumentModel.status == "active",
                )
            )
        )
        chunk_count = await self._count(
            select(func.count())
            .select_from(DocumentChunkModel)
            .where(
                and_(
                    DocumentChunkModel.organization_id == organization_id,
                    DocumentChunkModel.knowledge_space_id == knowledge_space_id,
                )
            )
        )
        conversation_link_count = await self._count(
            select(func.count())
            .select_from(ConversationKnowledgeSpaceModel)
            .where(
                and_(
                    ConversationKnowledgeSpaceModel.organization_id == organization_id,
                    ConversationKnowledgeSpaceModel.knowledge_space_id == knowledge_space_id,
                )
            )
        )
        return KnowledgeSpaceStats(
            document_count=document_count,
            chunk_count=chunk_count,
            conversation_link_count=conversation_link_count,
            knowledge_space_id=knowledge_space_id,
        )

    async def ingestion_overview(self, organization_id: UUID) -> IngestionOverviewStats:
        by_status = await self._group_count(
            IngestionJobModel.status,
            IngestionJobModel.organization_id == organization_id,
        )
        return IngestionOverviewStats(by_status=by_status)

    async def usage_overview(self, organization_id: UUID) -> UsageOverviewStats:
        from contextforge.modules.chat.infrastructure.models.feedback import MessageFeedbackModel

        active_memberships = await self._count(
            select(func.count())
            .select_from(OrganizationMembershipModel)
            .where(
                and_(
                    OrganizationMembershipModel.organization_id == organization_id,
                    OrganizationMembershipModel.status == "active",
                )
            )
        )
        conversations = await self._count(
            select(func.count())
            .select_from(ConversationModel)
            .where(ConversationModel.organization_id == organization_id)
        )
        messages = await self._count(
            select(func.count())
            .select_from(ChatMessageModel)
            .where(ChatMessageModel.organization_id == organization_id)
        )
        documents = await self._count(
            select(func.count())
            .select_from(DocumentModel)
            .where(
                and_(
                    DocumentModel.organization_id == organization_id,
                    DocumentModel.status == "active",
                )
            )
        )
        feedback_count = await self._count(
            select(func.count())
            .select_from(MessageFeedbackModel)
            .where(MessageFeedbackModel.organization_id == organization_id)
        )
        return UsageOverviewStats(
            active_memberships=active_memberships,
            conversations=conversations,
            messages=messages,
            documents=documents,
            feedback_count=feedback_count,
        )

    async def usage_trends(
        self, organization_id: UUID, *, since: datetime
    ) -> list[tuple[str, int]]:
        day_col = func.date_trunc("day", ConversationModel.created_at)
        result = await self._session.execute(
            select(day_col, func.count())
            .where(
                and_(
                    ConversationModel.organization_id == organization_id,
                    ConversationModel.created_at >= since,
                )
            )
            .group_by(day_col)
            .order_by(day_col.asc())
        )
        return [
            (str(row[0].date()) if row[0] is not None else "", int(row[1])) for row in result.all()
        ]

    async def _count_ingestion(self, organization_id: UUID, status: str) -> int:
        return await self._count(
            select(func.count())
            .select_from(IngestionJobModel)
            .where(
                and_(
                    IngestionJobModel.organization_id == organization_id,
                    IngestionJobModel.status == status,
                )
            )
        )

    async def _count(self, statement: Select[tuple[int]]) -> int:
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def _group_count(self, column: Any, *conditions: ColumnElement[bool]) -> dict[str, int]:
        statement = select(column, func.count()).where(and_(*conditions)).group_by(column)
        result = await self._session.execute(statement)
        return {str(row[0]): int(row[1]) for row in result.all()}
