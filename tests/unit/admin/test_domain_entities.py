"""Unit tests for administration domain entities."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from contextforge.modules.admin.domain.entities.feature_flag import FeatureFlag, resolve_flags
from contextforge.modules.admin.domain.entities.llm_provider_config import mask_api_key
from contextforge.modules.admin.domain.entities.organization_settings import OrganizationQuotas
from contextforge.modules.admin.domain.entities.prompt_template import PromptTemplate
from contextforge.modules.admin.domain.entities.retention import RetentionPolicy
from contextforge.modules.admin.domain.entities.token_pricing import TokenPricing, estimate_cost
from contextforge.modules.admin.domain.enums import (
    PromptLanguage,
    PromptTemplateName,
    RetentionResourceType,
)
from contextforge.shared.utilities.datetime import utc_now


def test_organization_quotas_validate_bounds() -> None:
    quotas = OrganizationQuotas(max_users=10, max_documents=None)
    assert quotas.remaining("max_users", 3) == 7
    assert quotas.is_exceeded("max_users", 10) is True
    with pytest.raises(ValueError):
        OrganizationQuotas(max_users=-1)


def test_feature_flag_resolution_precedence() -> None:
    global_flags = [FeatureFlag(key="beta.chat", enabled_globally=True)]
    org_flags = [FeatureFlag(key="beta.chat", enabled_globally=False)]
    resolved = resolve_flags(
        global_flags=global_flags,
        organization_flags=org_flags,
        settings_overrides={"beta.chat": True},
    )
    assert resolved["beta.chat"] is True


def test_mask_api_key() -> None:
    assert mask_api_key("sk-12345678") == "***5678"
    assert mask_api_key("abc") == "***"


def test_prompt_template_render_and_placeholders() -> None:
    template = PromptTemplate(
        name=PromptTemplateName.USER,
        version="v1",
        language=PromptLanguage.EN,
        content="Hello {{name}} from {{org}}",
    )
    assert template.placeholders == ["name", "org"]
    assert template.render({"name": "Ada"}) == "Hello Ada from {{org}}"


def test_token_pricing_estimate() -> None:
    pricing = TokenPricing(
        provider="mock",
        model="mock-1",
        input_price_per_1k=Decimal("1.0"),
        output_price_per_1k=Decimal("2.0"),
    )
    cost = estimate_cost(pricing, prompt_tokens=1000, completion_tokens=500)
    assert cost == Decimal("2.000000")


def test_retention_policy_cutoff_and_purge_only() -> None:
    policy = RetentionPolicy(
        resource_type=RetentionResourceType.CONVERSATIONS,
        retention_days=30,
    )
    assert policy.cutoff(now=utc_now()) < utc_now() - timedelta(days=29)
    with pytest.raises(ValueError):
        RetentionPolicy(
            resource_type=RetentionResourceType.AUDIT_EVENTS,
            retention_days=30,
            soft_delete_first=True,
        )
