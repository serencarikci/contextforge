"""Additional unit tests to cover logging, settings edge cases, and helpers."""

from __future__ import annotations

import json
import logging

import pytest

from contextforge.domain.exceptions.base import ApplicationError, DomainError
from contextforge.shared.config.settings import Settings, clear_settings_cache
from contextforge.shared.logging.formatters import ConsoleFormatter, JsonFormatter
from contextforge.shared.logging.setup import LoggerAdapter, configure_logging, get_logger
from contextforge.shared.types.aliases import EntityId, JSONValue
from contextforge.shared.utilities.correlation import is_valid_correlation_id


@pytest.mark.unit
def test_json_formatter_includes_exception() -> None:
    formatter = JsonFormatter(service_name="contextforge-api", environment="test")
    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="boom",
        args=(),
        exc_info=None,
    )
    try:
        raise RuntimeError("x")
    except RuntimeError:
        record.exc_info = __import__("sys").exc_info()
    payload = json.loads(formatter.format(record))
    assert payload["level"] == "ERROR"
    assert "exception" in payload


@pytest.mark.unit
def test_console_formatter_and_adapter() -> None:
    configure_logging(
        Settings().logging,
        environment="test",
    )
    logger = LoggerAdapter(get_logger("test.adapter"), {"route": "/x"})
    logger.info("hello")
    formatter = ConsoleFormatter(service_name="contextforge-api", environment="test")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    text = formatter.format(record)
    assert "contextforge-api" in text


@pytest.mark.unit
def test_cors_origins_json_and_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONTEXTFORGE_API__CORS_ORIGINS", '["http://a","http://b"]')
    clear_settings_cache()
    assert Settings().api.cors_origins == ["http://a", "http://b"]

    monkeypatch.setenv("CONTEXTFORGE_API__CORS_ORIGINS", "http://a, http://b")
    clear_settings_cache()
    assert Settings().api.cors_origins == ["http://a", "http://b"]


@pytest.mark.unit
def test_application_error_custom_code() -> None:
    err = ApplicationError("failed", code="CUSTOM")
    assert err.code == "CUSTOM"
    assert DomainError("x").code == "DOMAIN_ERROR"


@pytest.mark.unit
def test_type_aliases_importable() -> None:
    value: JSONValue = {"ok": True}
    assert value["ok"] is True
    assert EntityId


@pytest.mark.unit
def test_correlation_uuid_value_error_path() -> None:

    assert is_valid_correlation_id("00000000-0000-0000-0000-00000000000g") is False
