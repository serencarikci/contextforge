from __future__ import annotations

from uuid import uuid4

import pytest

from contextforge.modules.admin.domain.entities.organization_settings import (
    OrganizationQuotas,
    OrganizationSettings,
    validate_defaults,
    validate_feature_overrides,
)


@pytest.mark.unit
def test_quotas_accept_null_and_zero() -> None:
    quotas = OrganizationQuotas(
        max_users=0,
        max_documents=None,
        max_conversations=10,
        max_monthly_tokens=None,
    )
    assert quotas.max_users == 0
    assert quotas.is_exceeded("max_users", 0) is True
    assert quotas.is_exceeded("max_documents", 999) is False
    assert quotas.remaining("max_conversations", 3) == 7


@pytest.mark.unit
def test_quotas_reject_negative_and_non_int() -> None:
    with pytest.raises(ValueError, match="max_users"):
        OrganizationQuotas(max_users=-1)
    with pytest.raises(TypeError, match="max_documents"):
        OrganizationQuotas.from_mapping({"max_documents": "unlimited"})


@pytest.mark.unit
def test_quotas_from_mapping_ignores_unknown_keys() -> None:
    quotas = OrganizationQuotas.from_mapping(
        {"max_users": 5, "unknown_quota": 99, "max_documents": 20}
    )
    assert quotas.to_mapping() == {
        "max_users": 5,
        "max_documents": 20,
        "max_conversations": None,
        "max_monthly_tokens": None,
    }


@pytest.mark.unit
def test_validate_defaults_rejects_unknown_and_bad_values() -> None:
    with pytest.raises(ValueError, match="Unknown default keys"):
        validate_defaults({"not_a_key": "x"})
    with pytest.raises(ValueError, match="default_language"):
        validate_defaults({"default_language": "de"})
    with pytest.raises(ValueError, match="memory_strategy"):
        validate_defaults({"memory_strategy": "magic"})
    assert validate_defaults({"default_language": "TR", "retention_days": 30}) == {
        "default_language": "tr",
        "retention_days": 30,
    }


@pytest.mark.unit
def test_feature_overrides_must_be_bool() -> None:
    with pytest.raises(TypeError, match="boolean"):
        validate_feature_overrides({"beta": "yes"})
    assert validate_feature_overrides({"beta.search": True, "kill.switch": False}) == {
        "beta.search": True,
        "kill.switch": False,
    }


@pytest.mark.unit
def test_organization_settings_merge_and_replace() -> None:
    settings = OrganizationSettings(organization_id=uuid4())
    settings.replace_quotas(OrganizationQuotas(max_users=12))
    settings.merge_defaults({"default_language": "en"})
    settings.merge_feature_overrides({"chat.v2": True})
    settings.set_active(False)

    assert settings.quotas.max_users == 12
    assert settings.defaults["default_language"] == "en"
    assert settings.feature_overrides["chat.v2"] is True
    assert settings.is_active is False
