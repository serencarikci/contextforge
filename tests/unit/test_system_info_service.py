"""Unit tests for system info service."""

from __future__ import annotations

import pytest

from contextforge.application.services.system_info_service import SystemInfoService
from contextforge.shared.config.settings import Settings, clear_settings_cache


@pytest.mark.unit
def test_system_info_service(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONTEXTFORGE_APP__ENVIRONMENT", "staging")
    clear_settings_cache()
    service = SystemInfoService(Settings())
    info = service.get_info()
    assert info.name == "ContextForge API"
    assert info.environment == "staging"
    assert info.capabilities.rag is False
