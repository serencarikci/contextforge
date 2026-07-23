"""System information service."""

from __future__ import annotations

from dataclasses import dataclass

from contextforge.shared.config.settings import Settings


@dataclass(frozen=True, slots=True)
class SystemCapabilities:
    """Explicit capability flags for features not yet implemented."""

    document_ingestion: bool = False
    rag: bool = False
    chat: bool = False
    multilingual_answers: bool = False


@dataclass(frozen=True, slots=True)
class SystemInfo:
    """Safe, non-sensitive system information."""

    name: str
    version: str
    environment: str
    capabilities: SystemCapabilities


class SystemInfoService:
    """Builds the public system information payload."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_info(self) -> SystemInfo:
        """Return current system information."""
        return SystemInfo(
            name="ContextForge API",
            version=self._settings.app.version,
            environment=self._settings.app.environment.value,
            capabilities=SystemCapabilities(),
        )
