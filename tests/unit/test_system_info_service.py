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


@pytest.mark.unit
def test_system_info_service_implemented_capabilities(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONTEXTFORGE_APP__ENVIRONMENT", "test")
    clear_settings_cache()
    service = SystemInfoService(Settings())
    info = service.get_info()

    assert info.capabilities.identity_context is True
    assert info.capabilities.multi_tenancy is True
    assert info.capabilities.rbac is True
    assert info.capabilities.customers is True
    assert info.capabilities.projects is True
    assert info.capabilities.knowledge_spaces is True
    assert info.capabilities.audit_log is True

    assert info.capabilities.document_ingestion is True
    assert info.capabilities.document_parsing is True
    assert info.capabilities.document_chunking is True
    assert info.capabilities.document_embeddings is True
    assert info.capabilities.rag is False
    assert info.capabilities.chat is False
    assert info.capabilities.multilingual_answers is False

    assert info.authentication == "development_only"
