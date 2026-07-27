"""Audit trail export for administrators."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.modules.audit.domain.entities.audit_event import AuditEvent


@dataclass(frozen=True, slots=True)
class AuditExport:
    content_type: str
    filename: str
    body: str


class AuditExportService:
    async def export(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        *,
        export_format: str = "json",
        action: str | None = None,
        resource_type: str | None = None,
        actor_user_id: UUID | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        limit: int = 5000,
    ) -> AuditExport:
        async with uow:
            ctx.require_permission("admin:audit")
            events, _total = await uow.audit.list(
                ctx.organization_id,
                limit=min(limit, 10000),
                offset=0,
                action=action,
                resource_type=resource_type,
                actor_user_id=actor_user_id,
                occurred_from=occurred_from,
                occurred_to=occurred_to,
            )
        fmt = export_format.lower().strip()
        if fmt == "csv":
            return AuditExport(
                content_type="text/csv",
                filename="audit_export.csv",
                body=self._to_csv(events),
            )
        return AuditExport(
            content_type="application/json",
            filename="audit_export.json",
            body=self._to_json(events),
        )

    @staticmethod
    def _to_json(events: list[AuditEvent]) -> str:
        payload = [
            {
                "id": str(event.id),
                "organization_id": str(event.organization_id) if event.organization_id else None,
                "actor_user_id": str(event.actor_user_id) if event.actor_user_id else None,
                "action": event.action,
                "resource_type": event.resource_type,
                "resource_id": str(event.resource_id) if event.resource_id else None,
                "correlation_id": event.correlation_id,
                "metadata": event.metadata,
                "occurred_at": event.occurred_at.isoformat(),
            }
            for event in events
        ]
        return json.dumps(payload, ensure_ascii=True, indent=2)

    @staticmethod
    def _to_csv(events: list[AuditEvent]) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "id",
                "organization_id",
                "actor_user_id",
                "action",
                "resource_type",
                "resource_id",
                "correlation_id",
                "occurred_at",
            ]
        )
        for event in events:
            writer.writerow(
                [
                    str(event.id),
                    str(event.organization_id) if event.organization_id else "",
                    str(event.actor_user_id) if event.actor_user_id else "",
                    event.action,
                    event.resource_type,
                    str(event.resource_id) if event.resource_id else "",
                    event.correlation_id or "",
                    event.occurred_at.isoformat(),
                ]
            )
        return buffer.getvalue()
