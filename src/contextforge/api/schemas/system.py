"""System information response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CapabilitiesSchema(BaseModel):
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
    rag: bool = False
    chat: bool = False
    multilingual_answers: bool = False


class SystemInfoResponse(BaseModel):
    name: str
    version: str
    environment: str
    capabilities: CapabilitiesSchema = Field(default_factory=CapabilitiesSchema)
    authentication: str = "development_only"
