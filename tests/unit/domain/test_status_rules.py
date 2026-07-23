"""Unit tests for organization/user/membership status transition invariants."""

from __future__ import annotations

from uuid import uuid4

import pytest

from contextforge.domain.exceptions.identity import InvalidResourceStateError
from contextforge.modules.identity_access.domain.entities.membership import (
    OrganizationMembership,
)
from contextforge.modules.identity_access.domain.entities.user import User
from contextforge.modules.identity_access.domain.enums import (
    MembershipStatus,
    OrganizationStatus,
    UserStatus,
)
from contextforge.modules.organizations.domain.entities.organization import Organization


@pytest.mark.unit
class TestOrganizationStatusRules:
    def test_new_organization_is_active(self) -> None:
        org = Organization(name="Acme Inc", slug="acme")
        assert org.status == OrganizationStatus.ACTIVE

    def test_suspend_from_active(self) -> None:
        org = Organization(name="Acme Inc", slug="acme")
        org.suspend()
        assert org.status == OrganizationStatus.SUSPENDED

    def test_archive_from_suspended(self) -> None:
        org = Organization(name="Acme Inc", slug="acme")
        org.suspend()
        org.archive()
        assert org.status == OrganizationStatus.ARCHIVED

    def test_cannot_suspend_archived_organization(self) -> None:
        org = Organization(name="Acme Inc", slug="acme")
        org.archive()
        with pytest.raises(InvalidResourceStateError):
            org.suspend()

    def test_cannot_rename_suspended_organization(self) -> None:
        org = Organization(name="Acme Inc", slug="acme")
        org.suspend()
        with pytest.raises(InvalidResourceStateError):
            org.rename("New Name")

    def test_cannot_rename_archived_organization(self) -> None:
        org = Organization(name="Acme Inc", slug="acme")
        org.archive()
        with pytest.raises(InvalidResourceStateError):
            org.rename("New Name")

    def test_archived_organization_cannot_receive_memberships(self) -> None:
        org = Organization(name="Acme Inc", slug="acme")
        org.archive()
        with pytest.raises(InvalidResourceStateError):
            org.ensure_accepts_memberships()

    def test_active_organization_accepts_memberships(self) -> None:
        org = Organization(name="Acme Inc", slug="acme")
        org.ensure_accepts_memberships()

    def test_suspended_organization_still_accepts_memberships(self) -> None:

        org = Organization(name="Acme Inc", slug="acme")
        org.suspend()
        org.ensure_accepts_memberships()


@pytest.mark.unit
class TestUserStatusRules:
    def test_new_user_is_active(self) -> None:
        user = User(email="user@example.com", display_name="Test User")
        assert user.status == UserStatus.ACTIVE

    def test_suspend_from_active(self) -> None:
        user = User(email="user@example.com", display_name="Test User")
        user.suspend()
        assert user.status == UserStatus.SUSPENDED

    def test_cannot_suspend_archived_user(self) -> None:
        user = User(email="user@example.com", display_name="Test User")
        user.archive()
        with pytest.raises(InvalidResourceStateError):
            user.suspend()

    def test_active_user_passes_active_checks(self) -> None:
        user = User(email="user@example.com", display_name="Test User")
        user.ensure_active_for_actions()
        user.ensure_active_for_assignment()

    def test_suspended_user_fails_active_for_actions(self) -> None:
        user = User(email="user@example.com", display_name="Test User")
        user.suspend()
        with pytest.raises(InvalidResourceStateError):
            user.ensure_active_for_actions()

    def test_archived_user_fails_active_for_assignment(self) -> None:
        user = User(email="user@example.com", display_name="Test User")
        user.archive()
        with pytest.raises(InvalidResourceStateError):
            user.ensure_active_for_assignment()

    def test_suspended_user_can_still_be_assigned(self) -> None:

        user = User(email="user@example.com", display_name="Test User")
        user.suspend()
        user.ensure_active_for_assignment()

    def test_update_profile_requires_active_user(self) -> None:
        user = User(email="user@example.com", display_name="Test User")
        user.archive()
        with pytest.raises(InvalidResourceStateError):
            user.update_profile(display_name="New Name")


@pytest.mark.unit
class TestMembershipStatusRules:
    def test_new_membership_is_active(self) -> None:
        membership = OrganizationMembership(organization_id=uuid4(), user_id=uuid4())
        assert membership.status == MembershipStatus.ACTIVE

    def test_suspend_from_active(self) -> None:
        membership = OrganizationMembership(organization_id=uuid4(), user_id=uuid4())
        membership.suspend()
        assert membership.status == MembershipStatus.SUSPENDED

    def test_cannot_suspend_removed_membership(self) -> None:
        membership = OrganizationMembership(organization_id=uuid4(), user_id=uuid4())
        membership.remove()
        with pytest.raises(InvalidResourceStateError):
            membership.suspend()

    def test_ensure_active_passes_for_active_membership(self) -> None:
        membership = OrganizationMembership(organization_id=uuid4(), user_id=uuid4())
        membership.ensure_active()

    def test_ensure_active_fails_for_suspended_membership(self) -> None:
        membership = OrganizationMembership(organization_id=uuid4(), user_id=uuid4())
        membership.suspend()
        with pytest.raises(InvalidResourceStateError):
            membership.ensure_active()

    def test_ensure_active_fails_for_removed_membership(self) -> None:
        membership = OrganizationMembership(organization_id=uuid4(), user_id=uuid4())
        membership.remove()
        with pytest.raises(InvalidResourceStateError):
            membership.ensure_active()
