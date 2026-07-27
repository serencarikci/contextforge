from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from contextforge.bootstrap.app_factory import create_app
from contextforge.domain.exceptions.identity import InvalidDevelopmentIdentityError
from contextforge.modules.identity_access.application.services.identity_context_service import (
    build_request_context,
    development_identity_enabled,
)
from contextforge.shared.config.settings import Environment, Settings, clear_settings_cache


def _production_settings() -> Settings:
    settings = Settings()
    object.__setattr__(settings.app, "environment", Environment.PRODUCTION)
    return settings


@pytest.mark.security
def test_development_identity_enabled_is_false_in_production() -> None:
    assert development_identity_enabled(_production_settings()) is False


@pytest.mark.security
@pytest.mark.asyncio
async def test_build_request_context_raises_in_production_without_touching_the_database() -> None:
    settings = _production_settings()

    with pytest.raises(InvalidDevelopmentIdentityError) as exc_info:
        await build_request_context(
            None,  # type: ignore[arg-type]
            settings=settings,
            user_id=uuid4(),
            organization_id=uuid4(),
        )

    assert exc_info.value.code == "AUTHENTICATION_REQUIRED"


@pytest.mark.security
@pytest.mark.asyncio
async def test_build_request_context_raises_in_staging_too() -> None:
    settings = Settings()
    object.__setattr__(settings.app, "environment", Environment.STAGING)

    with pytest.raises(InvalidDevelopmentIdentityError):
        await build_request_context(
            None,  # type: ignore[arg-type]
            settings=settings,
            user_id=uuid4(),
            organization_id=uuid4(),
        )


@pytest.mark.security
def test_production_app_rejects_development_identity_headers_over_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CONTEXTFORGE_APP_ENVIRONMENT", "production")
    monkeypatch.setenv("CONTEXTFORGE_SECURITY_SECRET_KEY", "prod-secret-not-a-real-secret")
    clear_settings_cache()
    try:
        settings = Settings()
        app = create_app(settings)
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/customers",
                headers={
                    "X-ContextForge-User-ID": str(uuid4()),
                    "X-ContextForge-Organization-ID": str(uuid4()),
                },
            )
        assert response.status_code == 401

        assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
    finally:
        clear_settings_cache()
