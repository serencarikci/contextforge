"""Logging configuration and helpers."""

from __future__ import annotations

import logging
from typing import Any

from contextforge.shared.config.settings import LoggingSettings
from contextforge.shared.logging.formatters import ConsoleFormatter, JsonFormatter


def configure_logging(settings: LoggingSettings, *, environment: str) -> None:
    """Configure root logging handlers based on settings."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(settings.level)

    handler = logging.StreamHandler()
    if settings.format == "json":
        handler.setFormatter(
            JsonFormatter(service_name=settings.service_name, environment=environment)
        )
    else:
        handler.setFormatter(
            ConsoleFormatter(service_name=settings.service_name, environment=environment)
        )
    root.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter[logging.Logger]):
    """Adapter that injects extra structured fields."""

    def process(self, msg: str, kwargs: Any) -> tuple[str, Any]:
        extra = kwargs.setdefault("extra", {})
        if self.extra:
            extra.update(self.extra)
        return msg, kwargs
