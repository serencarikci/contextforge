"""Integration tests for repository filter/lookup paths not covered elsewhere.

These exercise the SQLAlchemy repository implementations directly (not
through the API/application layers) to cover slug/key/code lookups,
listing filters, and knowledge-space membership CRUD that the
authorization-focused API/security tests don't happen to exercise.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.infrastructure.database.session import DatabaseManager
from contextforge.modules.identity_access.domain.entities.membership import (
    OrganizationMembership,
)
from contextforge.modules.identity_access.domain.entities.user import User
from contextforge.modules.identity_access.domain.enums import (
    KnowledgeSpaceAccessLevel,
    KnowledgeSpaceStatus,
    KnowledgeSpaceVisibility,
    OrganizationStatus,
    ProjectStatus,
)
from contextforge.modules.knowledge_spaces.domain.entities.knowledge_space import (
    KnowledgeSpace,
    KnowledgeSpaceMembership,
)
from contextforge.modules.organizations.domain.entities.organization import Organization
from contextforge.modules.projects.domain.entities.project import Project


async def _make_org_with_membership(
    uow: SqlAlchemyUnitOfWork,
) -> tuple[Organization, OrganizationMembership]:
    suffix = uuid4().hex[:12]
    organization = await uow.organizations.add(
        Organization(name=f"Filters Org {suffix}", slug=f"filters-org-{suffix}")
    )
    user = await uow.users.add(
        User(email=f"filters-{suffix}@example.com", display_name="Filters User")
    )
    membership = await uow.memberships.add(
        OrganizationMembership(organization_id=organization.id, user_id=user.id)
    )
    return organization, membership


@pytest.mark.integration
@pytest.mark.asyncio
async def test_organization_repository_slug_lookup_and_list_for_user(
    db_manager: DatabaseManager,
) -> None:
    async with SqlAlchemyUnitOfWork(db_manager.session_factory) as uow:
        organization, membership = await _make_org_with_membership(uow)

        assert await uow.organizations.get_by_slug("no-such-slug-at-all") is None
        found = await uow.organizations.get_by_slug(organization.slug)
        assert found is not None
        assert found.id == organization.id

        items, total = await uow.organizations.list_for_user(membership.user_id, limit=10, offset=0)
        assert total == 1
        assert items[0].id == organization.id

        items_filtered, total_filtered = await uow.organizations.list_for_user(
            membership.user_id, limit=10, offset=0, status=OrganizationStatus.ARCHIVED
        )
        assert total_filtered == 0
        assert items_filtered == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_project_repository_key_lookup_and_list_filters(
    db_manager: DatabaseManager,
) -> None:
    async with SqlAlchemyUnitOfWork(db_manager.session_factory) as uow:
        organization, _ = await _make_org_with_membership(uow)

        assert await uow.projects.get_by_key(organization.id, "NOSUCHKEY") is None

        project = await uow.projects.add(
            Project(organization_id=organization.id, name="Alpha Project", key="ALPHA")
        )
        found = await uow.projects.get_by_key(organization.id, "ALPHA")
        assert found is not None
        assert found.id == project.id

        project.archive()
        await uow.projects.update(project)

        active_items, active_total = await uow.projects.list(
            organization.id, limit=10, offset=0, status=ProjectStatus.ACTIVE
        )
        assert active_total == 0
        assert active_items == []

        archived_items, archived_total = await uow.projects.list(
            organization.id, limit=10, offset=0, status=ProjectStatus.ARCHIVED, query="alpha"
        )
        assert archived_total == 1
        assert archived_items[0].id == project.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_knowledge_space_repository_full_lifecycle(
    db_manager: DatabaseManager,
) -> None:
    async with SqlAlchemyUnitOfWork(db_manager.session_factory) as uow:
        organization, membership = await _make_org_with_membership(uow)

        assert await uow.knowledge_spaces.get_by_slug(organization.id, "missing-slug") is None

        org_visible = await uow.knowledge_spaces.add(
            KnowledgeSpace(
                organization_id=organization.id,
                name="Org Visible Space",
                slug="org-visible-space",
                visibility=KnowledgeSpaceVisibility.ORGANIZATION,
            )
        )
        restricted = await uow.knowledge_spaces.add(
            KnowledgeSpace(
                organization_id=organization.id,
                name="Restricted Space",
                slug="restricted-space",
                visibility=KnowledgeSpaceVisibility.RESTRICTED,
            )
        )

        visible_ids = await uow.knowledge_spaces.list_organization_visible_ids(organization.id)
        assert visible_ids == {org_visible.id}

        org_visible.archive()
        await uow.knowledge_spaces.update(org_visible)
        assert await uow.knowledge_spaces.list_organization_visible_ids(organization.id) == set()

        ks_membership = await uow.knowledge_spaces.add_membership(
            KnowledgeSpaceMembership(
                organization_id=organization.id,
                knowledge_space_id=restricted.id,
                membership_id=membership.id,
                access_level=KnowledgeSpaceAccessLevel.READER,
            )
        )
        assert (
            await uow.knowledge_spaces.get_membership(
                organization.id, restricted.id, ks_membership.id
            )
        ) is not None
        assert (
            await uow.knowledge_spaces.get_membership_by_org_membership(
                organization.id, restricted.id, membership.id
            )
        ) is not None

        accessible = await uow.knowledge_spaces.list_accessible_ids_for_membership(
            organization.id, membership.id
        )
        assert accessible == {restricted.id}

        ks_membership.update_access_level(KnowledgeSpaceAccessLevel.MANAGER)
        updated = await uow.knowledge_spaces.update_membership(ks_membership)
        assert updated.access_level == KnowledgeSpaceAccessLevel.MANAGER

        members, total = await uow.knowledge_spaces.list_memberships(
            organization.id, restricted.id, limit=10, offset=0
        )
        assert total == 1
        assert members[0].id == ks_membership.id

        deleted = await uow.knowledge_spaces.delete_membership(
            organization.id, restricted.id, ks_membership.id
        )
        assert deleted is True
        deleted_again = await uow.knowledge_spaces.delete_membership(
            organization.id, restricted.id, ks_membership.id
        )
        assert deleted_again is False

        by_status, _ = await uow.knowledge_spaces.list(
            organization.id, limit=10, offset=0, status=KnowledgeSpaceStatus.ARCHIVED
        )
        assert {item.id for item in by_status} == {org_visible.id}

        by_visibility, _ = await uow.knowledge_spaces.list(
            organization.id,
            limit=10,
            offset=0,
            visibility=KnowledgeSpaceVisibility.RESTRICTED,
        )
        assert {item.id for item in by_visibility} == {restricted.id}

        by_query, _ = await uow.knowledge_spaces.list(
            organization.id, limit=10, offset=0, query="restricted"
        )
        assert {item.id for item in by_query} == {restricted.id}
