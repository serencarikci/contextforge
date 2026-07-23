"""Unit tests for validated domain value objects."""

from __future__ import annotations

import pytest

from contextforge.modules.identity_access.domain.value_objects import (
    CustomerCode,
    KnowledgeSpaceSlug,
    NormalizedEmail,
    OrganizationSlug,
    ProjectKey,
    RoleCode,
    validate_permission_code,
)


@pytest.mark.unit
class TestOrganizationSlug:
    @pytest.mark.parametrize(
        "raw",
        ["contextforge-dev", "acme", "org-123", "a1-b2-c3"],
    )
    def test_accepts_valid_slugs(self, raw: str) -> None:
        assert OrganizationSlug(raw).value == raw

    def test_normalizes_case_and_whitespace(self) -> None:
        assert OrganizationSlug(" Contextforge-Dev ").value == "contextforge-dev"

    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "-leading-hyphen",
            "trailing-hyphen-",
            "double--hyphen",
            "Has Spaces",
            "under_score",
        ],
    )
    def test_rejects_invalid_slugs(self, raw: str) -> None:
        with pytest.raises(ValueError, match="slug"):
            OrganizationSlug(raw)

    def test_str_returns_value(self) -> None:
        assert str(OrganizationSlug("acme")) == "acme"


@pytest.mark.unit
class TestKnowledgeSpaceSlug:
    def test_accepts_valid_slug(self) -> None:
        assert KnowledgeSpaceSlug("company-handbook").value == "company-handbook"

    def test_normalizes_case(self) -> None:
        assert KnowledgeSpaceSlug("Company-Handbook").value == "company-handbook"

    def test_rejects_spaces(self) -> None:
        with pytest.raises(ValueError, match="Knowledge space slug"):
            KnowledgeSpaceSlug("company handbook")

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValueError):
            KnowledgeSpaceSlug("")


@pytest.mark.unit
class TestNormalizedEmail:
    def test_normalizes_case_and_whitespace(self) -> None:
        assert NormalizedEmail("  Admin@ContextForge.Local ").value == "admin@contextforge.local"

    @pytest.mark.parametrize(
        "raw",
        ["not-an-email", "missing-at.example.com", "no-domain@", "@no-local.com", "a@b"],
    )
    def test_rejects_invalid_email(self, raw: str) -> None:
        with pytest.raises(ValueError, match="Invalid email address"):
            NormalizedEmail(raw)

    def test_str_returns_value(self) -> None:
        assert str(NormalizedEmail("user@example.com")) == "user@example.com"


@pytest.mark.unit
class TestCustomerCode:
    def test_normalizes_to_uppercase(self) -> None:
        assert CustomerCode("dev-cust").value == "DEV-CUST"

    @pytest.mark.parametrize("raw", ["DEV_CUST", "DEV-CUST-1", "A"])
    def test_accepts_valid_codes(self, raw: str) -> None:
        assert CustomerCode(raw).value == raw

    @pytest.mark.parametrize("raw", ["", "dev cust", "dev.cust", "dev@cust"])
    def test_rejects_invalid_codes(self, raw: str) -> None:
        with pytest.raises(ValueError, match="Customer code"):
            CustomerCode(raw)


@pytest.mark.unit
class TestProjectKey:
    def test_normalizes_to_uppercase(self) -> None:
        assert ProjectKey("demo").value == "DEMO"

    @pytest.mark.parametrize("raw", ["DEMO", "DEMO-2", "A1"])
    def test_accepts_valid_keys(self, raw: str) -> None:
        assert ProjectKey(raw).value == raw

    @pytest.mark.parametrize("raw", ["", "DEMO_1", "demo key", "DEMO.1"])
    def test_rejects_invalid_keys(self, raw: str) -> None:
        with pytest.raises(ValueError, match="Project key"):
            ProjectKey(raw)


@pytest.mark.unit
class TestRoleCode:
    def test_normalizes_case(self) -> None:
        assert RoleCode("Organization_Admin").value == "organization_admin"

    @pytest.mark.parametrize("raw", ["viewer", "project_manager", "a"])
    def test_accepts_valid_codes(self, raw: str) -> None:
        assert RoleCode(raw).value == raw

    @pytest.mark.parametrize("raw", ["", "1viewer", "-viewer", "viewer-role"])
    def test_rejects_invalid_codes(self, raw: str) -> None:
        with pytest.raises(ValueError, match="Role code"):
            RoleCode(raw)


@pytest.mark.unit
class TestPermissionCode:
    @pytest.mark.parametrize(
        "raw",
        ["customer:read", "knowledge_space:manage_members", "audit:read"],
    )
    def test_accepts_valid_codes(self, raw: str) -> None:
        assert validate_permission_code(raw) == raw

    @pytest.mark.parametrize("raw", ["", "customer", "customer-read", ":read", "customer:"])
    def test_rejects_invalid_codes(self, raw: str) -> None:
        with pytest.raises(ValueError, match="Permission code"):
            validate_permission_code(raw)
