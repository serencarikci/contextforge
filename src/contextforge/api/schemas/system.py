"""System information response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CapabilitiesSchema(BaseModel):
    document_ingestion: bool = False
    rag: bool = False
    chat: bool = False
    multilingual_answers: bool = False


class SystemInfoResponse(BaseModel):
    name: str
    version: str
    environment: str
    capabilities: CapabilitiesSchema = Field(default_factory=CapabilitiesSchema)
