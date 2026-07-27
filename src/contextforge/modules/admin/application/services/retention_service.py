from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, delete, select, update

from contextforge.application.context.request_context import RequestContext
from contextforge.application.services.command_support import build_audit_event
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import ResourceNotFoundError
from contextforge.modules.admin.domain.entities.retention import RetentionPolicy, RetentionRun
from contextforge.modules.admin.domain.enums import RetentionResourceType
from contextforge.modules.admin.domain.exceptions import RetentionPolicyDisabledError
from contextforge.modules.audit.infrastructure.models.audit_event import AuditEventModel
from contextforge.modules.chat.infrastructure.models.analytics import ChatAnalyticsEventModel
from contextforge.modules.chat.infrastructure.models.conversation import ConversationModel
from contextforge.modules.documents.infrastructure.models.document import DocumentModel
from contextforge.modules.ingestion.infrastructure.models.ingestion_job import IngestionJobModel
from contextforge.shared.config.settings import AdminSettings
from contextforge.shared.logging.setup import get_logger
from contextforge.shared.utilities.datetime import utc_now

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RetentionRunResult:
    run: RetentionRun
    deleted_count: int


class RetentionCleanupService:
    def __init__(self, settings: AdminSettings) -> None:
        self._settings = settings

    async def list_policies(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext
    ) -> list[RetentionPolicy]:
        async with uow:
            ctx.require_permission("admin:retention")
            return await uow.retention.list_policies(ctx.organization_id)

    async def create_policy(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        *,
        resource_type: RetentionResourceType,
        retention_days: int,
        soft_delete_first: bool = True,
        enabled: bool = True,
    ) -> RetentionPolicy:
        async with uow:
            ctx.require_permission("admin:retention")
            policy = RetentionPolicy(
                resource_type=resource_type,
                retention_days=retention_days,
                organization_id=ctx.organization_id,
                soft_delete_first=soft_delete_first,
                enabled=enabled,
            )
            policy = await uow.retention.add_policy(policy)
            event = build_audit_event(
                ctx,
                action="retention_policy.created",
                resource_type="retention_policy",
                resource_id=policy.id,
                metadata={"resource_type": policy.resource_type.value},
            )
            await uow.audit.add(event)
            return policy

    async def update_policy(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        policy_id: UUID,
        *,
        retention_days: int | None = None,
        soft_delete_first: bool | None = None,
        enabled: bool | None = None,
    ) -> RetentionPolicy:
        async with uow:
            ctx.require_permission("admin:retention")
            policy = await self._get_owned_policy(uow, ctx, policy_id)
            policy.update(
                retention_days=retention_days,
                soft_delete_first=soft_delete_first,
                enabled=enabled,
            )
            policy = await uow.retention.update_policy(policy)
            event = build_audit_event(
                ctx,
                action="retention_policy.updated",
                resource_type="retention_policy",
                resource_id=policy.id,
            )
            await uow.audit.add(event)
            return policy

    async def delete_policy(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, policy_id: UUID
    ) -> None:
        async with uow:
            ctx.require_permission("admin:retention")
            await self._get_owned_policy(uow, ctx, policy_id)
            await uow.retention.delete_policy(policy_id)
            event = build_audit_event(
                ctx,
                action="retention_policy.deleted",
                resource_type="retention_policy",
                resource_id=policy_id,
            )
            await uow.audit.add(event)

    async def list_runs(self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext) -> list[RetentionRun]:
        async with uow:
            ctx.require_permission("admin:retention")
            return await uow.retention.list_runs(ctx.organization_id)

    async def run_policy(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        policy_id: UUID | None = None,
    ) -> list[RetentionRunResult]:
        if not self._settings.retention_enabled:
            raise RetentionPolicyDisabledError("Retention cleanup is disabled.")

        async with uow:
            ctx.require_permission("admin:retention")
            if policy_id is not None:
                policies = [await self._get_owned_policy(uow, ctx, policy_id)]
            else:
                policies = [
                    p
                    for p in await uow.retention.list_policies(ctx.organization_id)
                    if p.enabled and (p.organization_id in (None, ctx.organization_id))
                ]

        results: list[RetentionRunResult] = []
        for policy in policies:
            results.append(await self._execute_policy(uow, ctx.organization_id, policy))
        return results

    async def run_all_enabled(self, uow: SqlAlchemyUnitOfWork) -> list[RetentionRunResult]:
        if not self._settings.retention_enabled:
            return []
        async with uow:
            policies = await uow.retention.list_enabled()
        results: list[RetentionRunResult] = []
        for policy in policies:
            org_id = policy.organization_id
            results.append(await self._execute_policy(uow, org_id, policy))
        return results

    async def _execute_policy(
        self,
        uow: SqlAlchemyUnitOfWork,
        organization_id: UUID | None,
        policy: RetentionPolicy,
    ) -> RetentionRunResult:
        run = RetentionRun(policy_id=policy.id, organization_id=organization_id)
        async with uow:
            run = await uow.retention.add_run(run)
        try:
            cutoff = policy.cutoff()
            deleted = await self._cleanup_resource(
                uow,
                policy.resource_type,
                organization_id=organization_id,
                cutoff=cutoff,
                soft_delete_first=policy.soft_delete_first,
            )
            run.mark_succeeded(
                deleted_count=deleted,
                summary={"resource_type": policy.resource_type.value, "cutoff": cutoff.isoformat()},
            )
        except Exception as exc:
            logger.exception("retention_run_failed", extra={"policy_id": str(policy.id)})
            run.mark_failed(error_code="RETENTION_FAILED", error_message=str(exc))
        async with uow:
            run = await uow.retention.update_run(run)
        return RetentionRunResult(run=run, deleted_count=run.deleted_count)

    async def _cleanup_resource(
        self,
        uow: SqlAlchemyUnitOfWork,
        resource_type: RetentionResourceType,
        *,
        organization_id: UUID | None,
        cutoff: datetime,
        soft_delete_first: bool,
    ) -> int:
        batch = self._settings.retention_batch_size
        deleted_total = 0
        async with uow:
            assert uow.session is not None
            session = uow.session
            if resource_type == RetentionResourceType.CONVERSATIONS:
                conditions = [ConversationModel.created_at < cutoff]
                if organization_id is not None:
                    conditions.append(ConversationModel.organization_id == organization_id)
                if soft_delete_first:
                    result = await session.execute(
                        update(ConversationModel)
                        .where(
                            and_(
                                *conditions,
                                ConversationModel.status != "archived",
                            )
                        )
                        .values(status="archived")
                        .execution_options(synchronize_session=False)
                    )
                    deleted_total = int(getattr(result, "rowcount", 0) or 0)
                else:
                    ids = (
                        (
                            await session.execute(
                                select(ConversationModel.id).where(and_(*conditions)).limit(batch)
                            )
                        )
                        .scalars()
                        .all()
                    )
                    if ids:
                        result = await session.execute(
                            delete(ConversationModel).where(ConversationModel.id.in_(ids))
                        )
                        deleted_total = int(getattr(result, "rowcount", 0) or 0)
            elif resource_type == RetentionResourceType.DOCUMENTS:
                conditions = [DocumentModel.created_at < cutoff]
                if organization_id is not None:
                    conditions.append(DocumentModel.organization_id == organization_id)
                if soft_delete_first:
                    result = await session.execute(
                        update(DocumentModel)
                        .where(and_(*conditions, DocumentModel.status == "active"))
                        .values(status="deleted", deleted_at=utc_now())
                        .execution_options(synchronize_session=False)
                    )
                    deleted_total = int(getattr(result, "rowcount", 0) or 0)
                else:
                    ids = (
                        (
                            await session.execute(
                                select(DocumentModel.id).where(and_(*conditions)).limit(batch)
                            )
                        )
                        .scalars()
                        .all()
                    )
                    if ids:
                        result = await session.execute(
                            delete(DocumentModel).where(DocumentModel.id.in_(ids))
                        )
                        deleted_total = int(getattr(result, "rowcount", 0) or 0)
            elif resource_type == RetentionResourceType.AUDIT_EVENTS:
                conditions = [AuditEventModel.occurred_at < cutoff]
                if organization_id is not None:
                    conditions.append(AuditEventModel.organization_id == organization_id)
                result = await session.execute(delete(AuditEventModel).where(and_(*conditions)))
                deleted_total = int(getattr(result, "rowcount", 0) or 0)
            elif resource_type == RetentionResourceType.ANALYTICS:
                conditions = [ChatAnalyticsEventModel.created_at < cutoff]
                if organization_id is not None:
                    conditions.append(ChatAnalyticsEventModel.organization_id == organization_id)
                result = await session.execute(
                    delete(ChatAnalyticsEventModel).where(and_(*conditions))
                )
                deleted_total = int(getattr(result, "rowcount", 0) or 0)
            elif resource_type == RetentionResourceType.INGESTION_JOBS:
                conditions = [
                    IngestionJobModel.created_at < cutoff,
                    IngestionJobModel.status.in_(("succeeded", "failed", "cancelled")),
                ]
                if organization_id is not None:
                    conditions.append(IngestionJobModel.organization_id == organization_id)
                result = await session.execute(delete(IngestionJobModel).where(and_(*conditions)))
                deleted_total = int(getattr(result, "rowcount", 0) or 0)
            elif resource_type in {
                RetentionResourceType.EXPORTS,
                RetentionResourceType.TEMPORARY,
            }:
                deleted_total = 0
            else:
                deleted_total = 0
        return deleted_total

    @staticmethod
    async def _get_owned_policy(
        uow: SqlAlchemyUnitOfWork, ctx: RequestContext, policy_id: UUID
    ) -> RetentionPolicy:
        policy = await uow.retention.get_policy(policy_id)
        if policy is None:
            raise ResourceNotFoundError("Retention policy not found.")
        if policy.organization_id is None:
            if not ctx.is_platform_admin:
                raise ResourceNotFoundError("Retention policy not found.")
            return policy
        if policy.organization_id != ctx.organization_id:
            raise ResourceNotFoundError("Retention policy not found.")
        return policy
