"""System information service."""

from __future__ import annotations

from dataclasses import dataclass

from contextforge.shared.config.settings import Settings


@dataclass(frozen=True, slots=True)
class SystemCapabilities:
    """Explicit capability flags for implemented and planned features."""

    identity_context: bool = True
    multi_tenancy: bool = True
    rbac: bool = True
    customers: bool = True
    projects: bool = True
    knowledge_spaces: bool = True
    audit_log: bool = True
    document_ingestion: bool = True
    document_parsing: bool = True
    document_chunking: bool = True
    document_embeddings: bool = True
    ingestion_workers: bool = True
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
    authentication: str = "development_only"


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
            authentication="development_only",
        )
