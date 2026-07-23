#!/usr/bin/env python
"""Idempotent local development data bootstrap.

Invoked by ``make bootstrap-dev``. Creates a deterministic development
tenant (organization, users, memberships, role assignments, a customer, a
project, and two knowledge spaces) so a fresh local environment has
something usable to develop and test against immediately after
``make migrate``.

Every entity id is derived deterministically with ``uuid.uuid5`` over a
fixed namespace, so running this script twice (or on a fresh database
seeded from the same migrations) always produces the exact same ids. The
script looks up each entity by its natural key (slug/email/code) before
creating it, so it is safe to run repeatedly -- it will not create
duplicates and will not fail on the second run.

At the end, it prints the development identity headers for the seeded
admin user so they can be pasted straight into ``curl`` or an HTTP client:

    X-ContextForge-User-ID: <uuid>
    X-ContextForge-Organization-ID: <uuid>
"""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from dataclasses import dataclass

from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.infrastructure.database.session import DatabaseManager
from contextforge.infrastructure.object_storage.minio_client import MinioClient
from contextforge.modules.customers.domain.entities.customer import Customer
from contextforge.modules.documents.domain.entities.document import Document
from contextforge.modules.identity_access.domain.entities.membership import (
    OrganizationMembership,
)
from contextforge.modules.identity_access.domain.entities.rbac import RoleAssignment
from contextforge.modules.identity_access.domain.entities.user import User
from contextforge.modules.identity_access.domain.enums import (
    KnowledgeSpaceAccessLevel,
    KnowledgeSpaceVisibility,
    PreferredLanguage,
    SystemRoleCode,
)
from contextforge.modules.knowledge_spaces.domain.entities.knowledge_space import (
    KnowledgeSpace,
    KnowledgeSpaceMembership,
)
from contextforge.modules.organizations.domain.entities.organization import Organization
from contextforge.modules.projects.domain.entities.project import Project
from contextforge.shared.config.settings import get_settings

DEV_UUID_NAMESPACE = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

ORG_SLUG = "contextforge-dev"
ORG_NAME = "ContextForge Dev"

ADMIN_EMAIL = "admin@contextforge.local"
ADMIN_NAME = "Dev Admin"
ADMIN_LANGUAGE = PreferredLanguage.EN

DEVELOPER_EMAIL = "developer@contextforge.local"
DEVELOPER_NAME = "Dev Developer"
DEVELOPER_LANGUAGE = PreferredLanguage.TR

CUSTOMER_CODE = "DEV-CUST"
CUSTOMER_NAME = "Demo Customer"

PROJECT_KEY = "DEMO"
PROJECT_NAME = "Demo Project"

KS_ORG_VISIBLE_SLUG = "company-handbook"
KS_RESTRICTED_SLUG = "incident-playbooks"

WELCOME_DOCUMENT_TITLE = "Welcome"
WELCOME_DOCUMENT_FILENAME = "welcome.txt"
WELCOME_DOCUMENT_CONTENT = b"Welcome to the ContextForge Company Handbook knowledge space.\n"


def _dev_uuid(name: str) -> uuid.UUID:
    """Deterministic UUID for a piece of bootstrap sample data."""
    return uuid.uuid5(DEV_UUID_NAMESPACE, name)


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    """Ids of every entity ensured by :func:`bootstrap`, for callers/tests."""

    organization_id: uuid.UUID
    admin_user_id: uuid.UUID
    admin_membership_id: uuid.UUID
    developer_user_id: uuid.UUID
    developer_membership_id: uuid.UUID
    customer_id: uuid.UUID
    project_id: uuid.UUID
    org_visible_knowledge_space_id: uuid.UUID
    restricted_knowledge_space_id: uuid.UUID
    welcome_document_id: uuid.UUID | None


async def _ensure_user(
    uow: SqlAlchemyUnitOfWork,
    *,
    email: str,
    display_name: str,
    preferred_language: PreferredLanguage,
) -> User:
    existing = await uow.users.get_by_email(email)
    if existing is not None:
        return existing
    user = User(
        id=_dev_uuid(f"user:{email}"),
        email=email,
        display_name=display_name,
        preferred_language=preferred_language,
    )
    return await uow.users.add(user)


async def _ensure_organization(uow: SqlAlchemyUnitOfWork) -> Organization:
    existing = await uow.organizations.get_by_slug(ORG_SLUG)
    if existing is not None:
        return existing
    organization = Organization(
        id=_dev_uuid(f"organization:{ORG_SLUG}"),
        name=ORG_NAME,
        slug=ORG_SLUG,
    )
    return await uow.organizations.add(organization)


async def _ensure_membership(
    uow: SqlAlchemyUnitOfWork, *, organization_id: uuid.UUID, user: User
) -> OrganizationMembership:
    existing = await uow.memberships.get_by_org_and_user(organization_id, user.id)
    if existing is not None:
        return existing
    membership = OrganizationMembership(
        id=_dev_uuid(f"membership:{ORG_SLUG}:{user.email}"),
        organization_id=organization_id,
        user_id=user.id,
    )
    return await uow.memberships.add(membership)


async def _ensure_org_scope_role_assignment(
    uow: SqlAlchemyUnitOfWork,
    *,
    organization_id: uuid.UUID,
    membership: OrganizationMembership,
    role_code: SystemRoleCode,
) -> RoleAssignment:
    role = await uow.rbac.get_system_role_by_code(role_code.value)
    if role is None:  # pragma: no cover
        msg = f"System role '{role_code.value}' is not seeded. Run migrations first."
        raise RuntimeError(msg)

    already_exists = await uow.rbac.assignment_exists(
        organization_id, membership.id, role.id, None, None
    )
    if already_exists:
        existing_assignments, _ = await uow.rbac.list_assignments(
            organization_id, limit=1000, offset=0
        )
        for assignment in existing_assignments:
            if (
                assignment.membership_id == membership.id
                and assignment.role_id == role.id
                and assignment.is_organization_scope
            ):
                return assignment

        raise RuntimeError(  # pragma: no cover
            f"Role assignment for {membership.id}/{role.id} reported as existing but not found."
        )

    assignment = RoleAssignment(
        id=_dev_uuid(f"role_assignment:{ORG_SLUG}:{role_code.value}:{membership.id}"),
        organization_id=organization_id,
        membership_id=membership.id,
        role_id=role.id,
    )
    return await uow.rbac.add_assignment(assignment)


async def _ensure_customer(uow: SqlAlchemyUnitOfWork, *, organization_id: uuid.UUID) -> Customer:
    existing = await uow.customers.get_by_code(organization_id, CUSTOMER_CODE)
    if existing is not None:
        return existing
    customer = Customer(
        id=_dev_uuid(f"customer:{ORG_SLUG}:{CUSTOMER_CODE}"),
        organization_id=organization_id,
        name=CUSTOMER_NAME,
        code=CUSTOMER_CODE,
    )
    return await uow.customers.add(customer)


async def _ensure_project(
    uow: SqlAlchemyUnitOfWork, *, organization_id: uuid.UUID, customer_id: uuid.UUID
) -> Project:
    existing = await uow.projects.get_by_key(organization_id, PROJECT_KEY)
    if existing is not None:
        return existing
    project = Project(
        id=_dev_uuid(f"project:{ORG_SLUG}:{PROJECT_KEY}"),
        organization_id=organization_id,
        name=PROJECT_NAME,
        key=PROJECT_KEY,
        customer_id=customer_id,
    )
    return await uow.projects.add(project)


async def _ensure_knowledge_space(
    uow: SqlAlchemyUnitOfWork,
    *,
    organization_id: uuid.UUID,
    slug: str,
    name: str,
    visibility: KnowledgeSpaceVisibility,
) -> KnowledgeSpace:
    existing = await uow.knowledge_spaces.get_by_slug(organization_id, slug)
    if existing is not None:
        return existing
    knowledge_space = KnowledgeSpace(
        id=_dev_uuid(f"knowledge_space:{ORG_SLUG}:{slug}"),
        organization_id=organization_id,
        name=name,
        slug=slug,
        visibility=visibility,
    )
    return await uow.knowledge_spaces.add(knowledge_space)


async def _ensure_knowledge_space_membership(
    uow: SqlAlchemyUnitOfWork,
    *,
    organization_id: uuid.UUID,
    knowledge_space_id: uuid.UUID,
    membership: OrganizationMembership,
    access_level: KnowledgeSpaceAccessLevel,
) -> KnowledgeSpaceMembership:
    existing = await uow.knowledge_spaces.get_membership_by_org_membership(
        organization_id, knowledge_space_id, membership.id
    )
    if existing is not None:
        return existing
    ks_membership = KnowledgeSpaceMembership(
        id=_dev_uuid(f"knowledge_space_membership:{ORG_SLUG}:{knowledge_space_id}:{membership.id}"),
        organization_id=organization_id,
        knowledge_space_id=knowledge_space_id,
        membership_id=membership.id,
        access_level=access_level,
    )
    return await uow.knowledge_spaces.add_membership(ks_membership)


async def _ensure_welcome_document(
    uow: SqlAlchemyUnitOfWork,
    minio: MinioClient,
    *,
    organization_id: uuid.UUID,
    knowledge_space_id: uuid.UUID,
    uploaded_by_user_id: uuid.UUID,
) -> Document:
    """Ensure a tiny "Welcome" sample document exists in the given knowledge space.

    Idempotent by title within the knowledge space: if a document titled
    ``WELCOME_DOCUMENT_TITLE`` already exists there, it is returned as-is
    without uploading anything new.
    """
    existing_items, _ = await uow.documents.list(
        organization_id,
        limit=100,
        offset=0,
        knowledge_space_id=knowledge_space_id,
        query=WELCOME_DOCUMENT_TITLE,
    )
    for item in existing_items:
        if item.title == WELCOME_DOCUMENT_TITLE:
            return item

    document_id = _dev_uuid(f"document:{ORG_SLUG}:{knowledge_space_id}:{WELCOME_DOCUMENT_TITLE}")
    storage_key = minio.build_object_key(
        organization_id, knowledge_space_id, document_id, WELCOME_DOCUMENT_FILENAME
    )
    document = Document(
        id=document_id,
        organization_id=organization_id,
        knowledge_space_id=knowledge_space_id,
        title=WELCOME_DOCUMENT_TITLE,
        filename=WELCOME_DOCUMENT_FILENAME,
        content_type="text/plain",
        size_bytes=len(WELCOME_DOCUMENT_CONTENT),
        storage_key=storage_key,
        checksum_sha256=hashlib.sha256(WELCOME_DOCUMENT_CONTENT).hexdigest(),
        uploaded_by_user_id=uploaded_by_user_id,
    )
    await minio.put_object(
        storage_key,
        WELCOME_DOCUMENT_CONTENT,
        len(WELCOME_DOCUMENT_CONTENT),
        "text/plain",
    )
    return await uow.documents.add(document)


async def bootstrap(uow: SqlAlchemyUnitOfWork, minio: MinioClient) -> BootstrapResult:
    """Ensure the full development dataset exists. Safe to call repeatedly."""
    async with uow:
        organization = await _ensure_organization(uow)

        admin_user = await _ensure_user(
            uow,
            email=ADMIN_EMAIL,
            display_name=ADMIN_NAME,
            preferred_language=ADMIN_LANGUAGE,
        )
        developer_user = await _ensure_user(
            uow,
            email=DEVELOPER_EMAIL,
            display_name=DEVELOPER_NAME,
            preferred_language=DEVELOPER_LANGUAGE,
        )

        admin_membership = await _ensure_membership(
            uow, organization_id=organization.id, user=admin_user
        )
        developer_membership = await _ensure_membership(
            uow, organization_id=organization.id, user=developer_user
        )

        await _ensure_org_scope_role_assignment(
            uow,
            organization_id=organization.id,
            membership=admin_membership,
            role_code=SystemRoleCode.ORGANIZATION_ADMIN,
        )
        await _ensure_org_scope_role_assignment(
            uow,
            organization_id=organization.id,
            membership=developer_membership,
            role_code=SystemRoleCode.DEVELOPER,
        )

        customer = await _ensure_customer(uow, organization_id=organization.id)
        project = await _ensure_project(
            uow, organization_id=organization.id, customer_id=customer.id
        )

        org_visible_space = await _ensure_knowledge_space(
            uow,
            organization_id=organization.id,
            slug=KS_ORG_VISIBLE_SLUG,
            name="Company Handbook",
            visibility=KnowledgeSpaceVisibility.ORGANIZATION,
        )
        restricted_space = await _ensure_knowledge_space(
            uow,
            organization_id=organization.id,
            slug=KS_RESTRICTED_SLUG,
            name="Incident Playbooks",
            visibility=KnowledgeSpaceVisibility.RESTRICTED,
        )

        await _ensure_knowledge_space_membership(
            uow,
            organization_id=organization.id,
            knowledge_space_id=restricted_space.id,
            membership=developer_membership,
            access_level=KnowledgeSpaceAccessLevel.CONTRIBUTOR,
        )

        welcome_document_id: uuid.UUID | None = None
        try:
            welcome_document = await _ensure_welcome_document(
                uow,
                minio,
                organization_id=organization.id,
                knowledge_space_id=org_visible_space.id,
                uploaded_by_user_id=admin_user.id,
            )
            welcome_document_id = welcome_document.id
        except Exception:  # noqa: S110
            pass

        return BootstrapResult(
            organization_id=organization.id,
            admin_user_id=admin_user.id,
            admin_membership_id=admin_membership.id,
            developer_user_id=developer_user.id,
            developer_membership_id=developer_membership.id,
            customer_id=customer.id,
            project_id=project.id,
            org_visible_knowledge_space_id=org_visible_space.id,
            restricted_knowledge_space_id=restricted_space.id,
            welcome_document_id=welcome_document_id,
        )


def _print_result(result: BootstrapResult) -> None:
    print("ContextForge development data bootstrap complete.")
    print(f"  organization:            {ORG_SLUG} ({result.organization_id})")
    print(f"  admin user:              {ADMIN_EMAIL} ({result.admin_user_id})")
    print(f"  developer user:         {DEVELOPER_EMAIL} ({result.developer_user_id})")
    print(f"  customer:                {CUSTOMER_CODE} ({result.customer_id})")
    print(f"  project:                 {PROJECT_KEY} ({result.project_id})")
    print(
        "  knowledge space (org):   "
        f"{KS_ORG_VISIBLE_SLUG} ({result.org_visible_knowledge_space_id})"
    )
    print(
        f"  knowledge space (rstr):  {KS_RESTRICTED_SLUG} ({result.restricted_knowledge_space_id})"
    )
    if result.welcome_document_id is not None:
        print(f"  welcome document:        {WELCOME_DOCUMENT_TITLE} ({result.welcome_document_id})")
    print()
    print("Use these development identity headers to call the API as the admin user:")
    print()
    print(f"X-ContextForge-User-ID: {result.admin_user_id}")
    print(f"X-ContextForge-Organization-ID: {result.organization_id}")


async def _main() -> None:
    settings = get_settings()
    database = DatabaseManager(settings.postgres)
    minio = MinioClient(settings.minio)
    try:
        uow = SqlAlchemyUnitOfWork(database.session_factory)
        result = await bootstrap(uow, minio)
    finally:
        await minio.close()
        await database.dispose()
    _print_result(result)


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
