"""SQLAlchemy repository for ingestion jobs."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.ingestion.domain.entities.ingestion_job import IngestionJob
from contextforge.modules.ingestion.domain.enums import IngestionJobStatus, IngestionJobStep
from contextforge.modules.ingestion.infrastructure.models.ingestion_job import IngestionJobModel


class SqlAlchemyIngestionJobRepository:
    """Persists IngestionJob aggregates using an explicit AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, organization_id: UUID, job_id: UUID) -> IngestionJob | None:
        statement = select(IngestionJobModel).where(
            and_(
                IngestionJobModel.id == job_id,
                IngestionJobModel.organization_id == organization_id,
            )
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        return None if model is None else self._to_entity(model)

    async def get_by_id(self, job_id: UUID) -> IngestionJob | None:
        statement = select(IngestionJobModel).where(IngestionJobModel.id == job_id)
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        return None if model is None else self._to_entity(model)

    async def add(self, job: IngestionJob) -> IngestionJob:
        model = IngestionJobModel(
            id=job.id,
            organization_id=job.organization_id,
            document_id=job.document_id,
            knowledge_space_id=job.knowledge_space_id,
            requested_by_user_id=job.requested_by_user_id,
            status=job.status.value,
            current_step=job.current_step.value,
            attempt_count=job.attempt_count,
            max_attempts=job.max_attempts,
            last_error=job.last_error,
            error_code=job.error_code,
            queued_at=job.queued_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, job: IngestionJob) -> IngestionJob:
        statement = select(IngestionJobModel).where(IngestionJobModel.id == job.id)
        result = await self._session.execute(statement)
        model = result.scalar_one()
        model.status = job.status.value
        model.current_step = job.current_step.value
        model.attempt_count = job.attempt_count
        model.max_attempts = job.max_attempts
        model.last_error = job.last_error
        model.error_code = job.error_code
        model.queued_at = job.queued_at
        model.started_at = job.started_at
        model.finished_at = job.finished_at
        model.updated_at = job.updated_at
        await self._session.flush()
        return self._to_entity(model)

    async def claim(self, job_id: UUID) -> IngestionJob | None:
        statement = (
            select(IngestionJobModel)
            .where(
                and_(
                    IngestionJobModel.id == job_id,
                    IngestionJobModel.status == IngestionJobStatus.PENDING.value,
                )
            )
            .with_for_update()
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        job = self._to_entity(model)
        job.mark_running(IngestionJobStep.PARSE)
        return await self.update(job)

    async def list_by_document(
        self,
        organization_id: UUID,
        document_id: UUID,
    ) -> list[IngestionJob]:
        statement = (
            select(IngestionJobModel)
            .where(
                and_(
                    IngestionJobModel.organization_id == organization_id,
                    IngestionJobModel.document_id == document_id,
                )
            )
            .order_by(IngestionJobModel.created_at.desc())
        )
        result = await self._session.execute(statement)
        return [self._to_entity(model) for model in result.scalars().all()]

    async def list_by_organization(
        self,
        organization_id: UUID,
        *,
        status: IngestionJobStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[IngestionJob], int]:
        conditions = [IngestionJobModel.organization_id == organization_id]
        if status is not None:
            conditions.append(IngestionJobModel.status == status.value)

        total = (
            await self._session.execute(
                select(func.count()).select_from(IngestionJobModel).where(and_(*conditions))
            )
        ).scalar_one()
        statement = (
            select(IngestionJobModel)
            .where(and_(*conditions))
            .order_by(IngestionJobModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(statement)
        return [self._to_entity(model) for model in result.scalars().all()], total

    async def list_pending_ids(self, *, limit: int = 500) -> list[UUID]:
        statement = (
            select(IngestionJobModel.id)
            .where(IngestionJobModel.status == IngestionJobStatus.PENDING.value)
            .order_by(IngestionJobModel.queued_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    @staticmethod
    def _to_entity(model: IngestionJobModel) -> IngestionJob:
        return IngestionJob(
            id=model.id,
            organization_id=model.organization_id,
            document_id=model.document_id,
            knowledge_space_id=model.knowledge_space_id,
            requested_by_user_id=model.requested_by_user_id,
            status=IngestionJobStatus(model.status),
            current_step=IngestionJobStep(model.current_step),
            attempt_count=model.attempt_count,
            max_attempts=model.max_attempts,
            last_error=model.last_error,
            error_code=model.error_code,
            queued_at=model.queued_at,
            started_at=model.started_at,
            finished_at=model.finished_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
