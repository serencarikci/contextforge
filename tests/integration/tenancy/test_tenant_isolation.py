"""Integration tests for tenant isolation of customers and projects.

Every business entity is scoped by ``organization_id``. These tests create
two independent organizations against the real database and assert that
lookups scoped to one organization never resolve entities that belong to
the other -- the core multi-tenancy guarantee the repository layer must
uphold regardless of what the application/API layers do on top of it.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.infrastructure.database.session import DatabaseManager
from contextforge.modules.customers.domain.entities.customer import Customer
from contextforge.modules.organizations.domain.entities.organization import Organization
from contextforge.modules.projects.domain.entities.project import Project


async def _make_organization(uow: SqlAlchemyUnitOfWork) -> Organization:
    suffix = uuid4().hex[:12]
    organization = Organization(name=f"Tenant {suffix}", slug=f"tenant-{suffix}")
    return await uow.organizations.add(organization)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_customer_lookup_is_isolated_between_organizations(
    db_manager: DatabaseManager,
) -> None:
    async with SqlAlchemyUnitOfWork(db_manager.session_factory) as uow:
        org_a = await _make_organization(uow)
        org_b = await _make_organization(uow)

        customer = Customer(organization_id=org_a.id, name="Acme Corp", code=f"C{uuid4().hex[:8]}")
        customer = await uow.customers.add(customer)

    async with SqlAlchemyUnitOfWork(db_manager.session_factory) as uow:
        found = await uow.customers.get(org_a.id, customer.id)
        assert found is not None
        assert found.id == customer.id

        not_found = await uow.customers.get(org_b.id, customer.id)
        assert not_found is None

        by_code_wrong_org = await uow.customers.get_by_code(org_b.id, customer.code)
        assert by_code_wrong_org is None
        by_code_right_org = await uow.customers.get_by_code(org_a.id, customer.code)
        assert by_code_right_org is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_project_lookup_is_isolated_between_organizations(
    db_manager: DatabaseManager,
) -> None:
    async with SqlAlchemyUnitOfWork(db_manager.session_factory) as uow:
        org_a = await _make_organization(uow)
        org_b = await _make_organization(uow)

        project = Project(
            organization_id=org_a.id, name="Demo Project", key=f"P{uuid4().hex[:6].upper()}"
        )
        project = await uow.projects.add(project)

    async with SqlAlchemyUnitOfWork(db_manager.session_factory) as uow:
        found = await uow.projects.get(org_a.id, project.id)
        assert found is not None

        not_found = await uow.projects.get(org_b.id, project.id)
        assert not_found is None

        by_key_wrong_org = await uow.projects.get_by_key(org_b.id, project.key)
        assert by_key_wrong_org is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_customer_list_only_returns_own_organization_rows(
    db_manager: DatabaseManager,
) -> None:
    async with SqlAlchemyUnitOfWork(db_manager.session_factory) as uow:
        org_a = await _make_organization(uow)
        org_b = await _make_organization(uow)

        for _ in range(3):
            await uow.customers.add(
                Customer(
                    organization_id=org_a.id,
                    name="Org A Customer",
                    code=f"A{uuid4().hex[:8]}",
                )
            )
        await uow.customers.add(
            Customer(organization_id=org_b.id, name="Org B Customer", code=f"B{uuid4().hex[:8]}")
        )

    async with SqlAlchemyUnitOfWork(db_manager.session_factory) as uow:
        items, total = await uow.customers.list(org_a.id, limit=100, offset=0)
        assert total == 3
        assert all(item.organization_id == org_a.id for item in items)
