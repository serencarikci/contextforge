"""Unit tests for development-identity environment gating."""

from __future__ import annotations

import pytest

from contextforge.modules.identity_access.application.services.identity_context_service import (
    development_identity_enabled,
)
from contextforge.shared.config.settings import Environment, Settings


def _settings_for(environment: Environment) -> Settings:
    settings = Settings()
    object.__setattr__(settings.app, "environment", environment)
    return settings


@pytest.mark.unit
@pytest.mark.parametrize(
    "environment",
    [Environment.LOCAL, Environment.TEST, Environment.DEVELOPMENT],
)
def test_development_identity_enabled_for_non_production_environments(
    environment: Environment,
) -> None:
    settings = _settings_for(environment)
    assert development_identity_enabled(settings) is True


@pytest.mark.unit
@pytest.mark.parametrize("environment", [Environment.STAGING, Environment.PRODUCTION])
def test_development_identity_disabled_for_staging_and_production(
    environment: Environment,
) -> None:
    settings = _settings_for(environment)
    assert development_identity_enabled(settings) is False
