"""Application service for customer lifecycle use cases."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError

from contextforge.application.context.request_context import RequestContext
from contextforge.application.pagination import Page, PaginationParams
from contextforge.application.services.command_support import (
    build_audit_event,
    ensure_organization_writable,
    translate_integrity_error,
)
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.domain.exceptions.identity import ResourceNotFoundError
from contextforge.modules.customers.domain.entities.customer import Customer
from contextforge.modules.identity_access.domain.enums import CustomerStatus


class CustomerService:
    """Use cases for creating, reading, and managing customers."""

    async def create(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        *,
        name: str,
        code: str,
        description: str | None = None,
    ) -> Customer:
        async with uow:
            ctx.require_permission("customer:create")

            organization = await uow.organizations.get_by_id(ctx.organization_id)
            if organization is None:  # pragma: no cover - defensive
                raise ResourceNotFoundError("Organization not found.")
            ensure_organization_writable(organization)

            customer = Customer(
                organization_id=ctx.organization_id,
                name=name,
                code=code,
                description=description,
            )
            try:
                customer = await uow.customers.add(customer)
            except IntegrityError as exc:
                translate_integrity_error(exc, message="A customer with this code already exists.")

            event = build_audit_event(
                ctx,
                action="customer.created",
                resource_type="customer",
                resource_id=customer.id,
                metadata={"code": customer.code},
            )
            await uow.audit.add(event)
            return customer

    async def get(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, customer_id: UUID
    ) -> Customer:
        async with uow:
            ctx.require_permission("customer:read")
            customer = await uow.customers.get(ctx.organization_id, customer_id)
            if customer is None:
                raise ResourceNotFoundError("Customer not found.")
            return customer

    async def list(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        pagination: PaginationParams,
        *,
        status: CustomerStatus | None = None,
        query: str | None = None,
    ) -> Page[Customer]:
        async with uow:
            ctx.require_permission("customer:read")
            customers, total = await uow.customers.list(
                ctx.organization_id,
                limit=pagination.limit,
                offset=pagination.offset,
                status=status,
                query=query,
            )
            return Page(
                items=customers, limit=pagination.limit, offset=pagination.offset, total=total
            )

    async def update(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        customer_id: UUID,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> Customer:
        async with uow:
            ctx.require_permission("customer:update")
            customer = await uow.customers.get(ctx.organization_id, customer_id)
            if customer is None:
                raise ResourceNotFoundError("Customer not found.")

            customer.update(name=name, description=description)
            customer = await uow.customers.update(customer)

            event = build_audit_event(
                ctx,
                action="customer.updated",
                resource_type="customer",
                resource_id=customer.id,
            )
            await uow.audit.add(event)
            return customer

    async def archive(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext, customer_id: UUID
    ) -> Customer:
        async with uow:
            ctx.require_permission("customer:archive")
            customer = await uow.customers.get(ctx.organization_id, customer_id)
            if customer is None:
                raise ResourceNotFoundError("Customer not found.")

            customer.archive()
            customer = await uow.customers.update(customer)

            event = build_audit_event(
                ctx,
                action="customer.archived",
                resource_type="customer",
                resource_id=customer.id,
            )
            await uow.audit.add(event)
            return customer


__all__ = ["CustomerService"]
