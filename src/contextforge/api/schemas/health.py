"""Health and readiness response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    version: str


class DependencyStatus(BaseModel):
    status: Literal["up", "down"]
    latency_ms: float = Field(ge=0)


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, DependencyStatus]
    total_latency_ms: float = Field(ge=0)
