"""Integration tests that audit events are actually persisted on write.

These exercise the full application-service write path (not just the
repository) against the real database: organization creation and customer
creation should each leave exactly one durable, queryable audit event row
behind, with the fields the audit trail promises (actor, organization,
resource, action).
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.infrastructure.database.session import DatabaseManager
from contextforge.modules.customers.application.services.customer_service import CustomerService
from contextforge.modules.identity_access.application.services.identity_context_service import (
    build_request_context,
)
from contextforge.modules.identity_access.application.services.user_service import UserService
from contextforge.modules.organizations.application.services.organization_service import (
    OrganizationService,
)
from contextforge.shared.config.settings import Settings


@pytest.mark.integration
@pytest.mark.asyncio
async def test_organization_creation_persists_audit_event(
    db_manager: DatabaseManager, integration_settings: Settings
) -> None:

    suffix = uuid4().hex[:12]
    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    user = await UserService().create(
        uow, email=f"audit-owner-{suffix}@example.com", display_name="Audit Owner"
    )

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    organization = await OrganizationService().create(
        uow,
        name=f"Audit Org {suffix}",
        slug=f"audit-org-{suffix}",
        creator_user_id=user.id,
    )

    async with SqlAlchemyUnitOfWork(db_manager.session_factory) as uow:
        events, total = await uow.audit.list(organization.id, limit=10, offset=0)
        assert total >= 1
        creation_events = [event for event in events if event.action == "organization.created"]
        assert len(creation_events) == 1

        event = creation_events[0]
        assert event.organization_id == organization.id
        assert event.actor_user_id == user.id
        assert event.resource_type == "organization"
        assert event.resource_id == organization.id
        assert event.metadata.get("slug") == organization.slug


@pytest.mark.integration
@pytest.mark.asyncio
async def test_customer_creation_persists_audit_event_with_sanitized_metadata(
    db_manager: DatabaseManager, integration_settings: Settings
) -> None:
    suffix = uuid4().hex[:12]
    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    admin = await UserService().create(
        uow, email=f"customer-admin-{suffix}@example.com", display_name="Customer Admin"
    )

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    organization = await OrganizationService().create(
        uow,
        name=f"Customer Org {suffix}",
        slug=f"customer-org-{suffix}",
        creator_user_id=admin.id,
    )

    async with SqlAlchemyUnitOfWork(db_manager.session_factory) as uow:
        ctx = await build_request_context(
            uow,
            settings=integration_settings,
            user_id=admin.id,
            organization_id=organization.id,
        )

    uow = SqlAlchemyUnitOfWork(db_manager.session_factory)
    customer = await CustomerService().create(
        uow, ctx, name="Demo Customer", code=f"C{suffix[:8].upper()}"
    )

    async with SqlAlchemyUnitOfWork(db_manager.session_factory) as uow:
        events, _ = await uow.audit.list(
            organization.id, limit=10, offset=0, resource_type="customer"
        )
        assert len(events) == 1
        event = events[0]
        assert event.action == "customer.created"
        assert event.resource_id == customer.id
        assert event.metadata == {"code": customer.code}

        assert "password" not in event.metadata
        assert "token" not in event.metadata
