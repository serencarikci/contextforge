"""JSON and console log formatters."""

from __future__ import annotations

import json
import logging
import traceback
from datetime import UTC, datetime
from typing import Any, cast

from contextforge.shared.logging.context import get_correlation_id


class JsonFormatter(logging.Formatter):
    """Emit structured JSON log records."""

    def __init__(self, *, service_name: str, environment: str) -> None:
        super().__init__()
        self._service_name = service_name
        self._environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "service": self._service_name,
            "environment": self._environment,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None) or get_correlation_id(),
        }

        for key in (
            "http_method",
            "route",
            "status_code",
            "duration_ms",
            "path",
            "client_host",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = "".join(traceback.format_exception(*record.exc_info)).strip()

        return json.dumps(payload, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable formatter for local development."""

    def __init__(self, *, service_name: str, environment: str) -> None:
        super().__init__(
            fmt=(
                "%(asctime)s | %(levelname)-8s | %(service)s | %(environment)s | "
                "cid=%(correlation_id)s | %(name)s | %(message)s"
            ),
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        self._service_name = service_name
        self._environment = environment

    def format(self, record: logging.LogRecord) -> str:
        record_any = cast(Any, record)
        if not hasattr(record, "service"):
            record_any.service = self._service_name
        if not hasattr(record, "environment"):
            record_any.environment = self._environment
        if not hasattr(record, "correlation_id"):
            record_any.correlation_id = get_correlation_id() or "-"
        elif record_any.correlation_id is None:
            record_any.correlation_id = "-"
        return super().format(record)
