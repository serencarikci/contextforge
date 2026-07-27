from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class _AdminModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AdminDashboardResponse(_AdminModel):
    membership_count: int
    active_membership_count: int
    document_count: int
    conversation_count: int
    knowledge_space_count: int
    ingestion_pending: int
    ingestion_running: int
    ingestion_failed: int
    audit_recent_count: int
    token_usage_today: int


class AdminUserResponse(_AdminModel):
    id: UUID
    email: str
    display_name: str
    status: str
    preferred_language: str
    membership_id: UUID
    membership_status: str
    created_at: datetime
    updated_at: datetime


class OrganizationSettingsResponse(_AdminModel):
    organization_id: UUID
    quotas: dict[str, Any]
    defaults: dict[str, Any]
    feature_overrides: dict[str, bool]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OrganizationSettingsUpdateRequest(BaseModel):
    quotas: dict[str, Any] | None = None
    defaults: dict[str, Any] | None = None
    feature_overrides: dict[str, bool] | None = None
    is_active: bool | None = None


class RolePermissionsUpdateRequest(BaseModel):
    permission_codes: list[str] = Field(default_factory=list)


class RolePermissionsResponse(_AdminModel):
    role_id: UUID
    permission_codes: list[str]


class KnowledgeSpaceStatsResponse(_AdminModel):
    knowledge_space_id: UUID
    document_count: int
    chunk_count: int
    conversation_link_count: int


class DocumentOverviewResponse(_AdminModel):
    by_status: dict[str, int]
    by_parse_status: dict[str, int]
    by_embedding_status: dict[str, int]
    recent_failed_parse_count: int


class BulkDocumentIdsRequest(BaseModel):
    document_ids: list[UUID] = Field(min_length=1, max_length=200)


class BulkDocumentResultResponse(_AdminModel):
    processed: int
    skipped: int
    job_ids: list[UUID] = Field(default_factory=list)


class IngestionOverviewResponse(_AdminModel):
    by_status: dict[str, int]
    queue_depth: int | None = None


class UsageOverviewResponse(_AdminModel):
    active_memberships: int
    conversations: int
    messages: int
    documents: int
    feedback_count: int


class UsageTrendPointResponse(_AdminModel):
    day: str
    conversation_count: int


class TokenUsageItemResponse(_AdminModel):
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    request_count: int
    estimated_cost: Decimal
    total_tokens: int
    organization_id: UUID | None = None


class TokenPricingResponse(_AdminModel):
    id: UUID
    provider: str
    model: str
    input_price_per_1k: Decimal
    output_price_per_1k: Decimal
    currency: str
    effective_from: datetime
    effective_to: datetime | None
    created_at: datetime
    updated_at: datetime


class TokenPricingCreateRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=200)
    model: str = Field(min_length=1, max_length=200)
    input_price_per_1k: Decimal
    output_price_per_1k: Decimal
    currency: str | None = Field(default=None, min_length=3, max_length=3)


class PromptTemplateResponse(_AdminModel):
    id: UUID
    organization_id: UUID | None
    name: str
    version: str
    language: str
    content: str
    is_active: bool
    is_system: bool
    placeholders: list[str]
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class PromptTemplateCreateRequest(BaseModel):
    name: str
    version: str
    language: str
    content: str
    activate: bool = False


class PromptPreviewRequest(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)


class PromptPreviewResponse(_AdminModel):
    id: UUID
    placeholders: list[str]
    rendered: str


class LlmProviderResponse(_AdminModel):
    id: UUID
    organization_id: UUID | None
    provider: str
    model: str
    base_url: str | None
    api_key_set: bool
    api_key_hint: str | None
    temperature: float
    max_tokens: int
    timeout_seconds: float
    max_retries: int
    rate_limit_rpm: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LlmProviderCreateRequest(BaseModel):
    provider: str
    model: str
    base_url: str | None = None
    api_key: str | None = None
    temperature: float = 0.2
    max_tokens: int = 1024
    timeout_seconds: float = 60.0
    max_retries: int = 2
    rate_limit_rpm: int | None = None
    is_active: bool = True


class LlmProviderUpdateRequest(BaseModel):
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    clear_api_key: bool = False
    temperature: float | None = None
    max_tokens: int | None = None
    timeout_seconds: float | None = None
    max_retries: int | None = None
    rate_limit_rpm: int | None = None
    is_active: bool | None = None


class LlmConnectivityResponse(_AdminModel):
    status: str
    latency_ms: float | None = None
    detail: str | None = None


class FeatureFlagResponse(_AdminModel):
    id: UUID
    key: str
    description: str | None
    enabled_globally: bool
    organization_id: UUID | None
    value: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class FeatureFlagCreateRequest(BaseModel):
    key: str
    description: str | None = None
    enabled: bool = False
    value: dict[str, Any] = Field(default_factory=dict)
    global_flag: bool = False


class FeatureFlagUpdateRequest(BaseModel):
    description: str | None = None
    enabled: bool | None = None
    value: dict[str, Any] | None = None


class FeatureFlagsResolvedResponse(_AdminModel):
    flags: dict[str, bool]


class OpsOverviewResponse(_AdminModel):
    readiness_status: str
    ingestion_pending: int
    ingestion_failed: int
    queue_depth: int | None
    llm_configured: bool
    retention_enabled: bool


class RetentionPolicyResponse(_AdminModel):
    id: UUID
    organization_id: UUID | None
    resource_type: str
    retention_days: int
    soft_delete_first: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime


class RetentionPolicyCreateRequest(BaseModel):
    resource_type: str
    retention_days: int
    soft_delete_first: bool = True
    enabled: bool = True


class RetentionPolicyUpdateRequest(BaseModel):
    retention_days: int | None = None
    soft_delete_first: bool | None = None
    enabled: bool | None = None


class RetentionRunResponse(_AdminModel):
    id: UUID
    policy_id: UUID
    organization_id: UUID | None
    status: str
    started_at: datetime
    finished_at: datetime | None
    deleted_count: int
    summary: dict[str, Any]


class RetentionRunRequest(BaseModel):
    policy_id: UUID | None = None


__all__ = [
    "AdminDashboardResponse",
    "AdminUserResponse",
    "BulkDocumentIdsRequest",
    "BulkDocumentResultResponse",
    "DocumentOverviewResponse",
    "FeatureFlagCreateRequest",
    "FeatureFlagResponse",
    "FeatureFlagUpdateRequest",
    "FeatureFlagsResolvedResponse",
    "IngestionOverviewResponse",
    "KnowledgeSpaceStatsResponse",
    "LlmConnectivityResponse",
    "LlmProviderCreateRequest",
    "LlmProviderResponse",
    "LlmProviderUpdateRequest",
    "OpsOverviewResponse",
    "OrganizationSettingsResponse",
    "OrganizationSettingsUpdateRequest",
    "PromptPreviewRequest",
    "PromptPreviewResponse",
    "PromptTemplateCreateRequest",
    "PromptTemplateResponse",
    "RetentionPolicyCreateRequest",
    "RetentionPolicyResponse",
    "RetentionPolicyUpdateRequest",
    "RetentionRunRequest",
    "RetentionRunResponse",
    "RolePermissionsResponse",
    "RolePermissionsUpdateRequest",
    "TokenPricingCreateRequest",
    "TokenPricingResponse",
    "TokenUsageItemResponse",
    "UsageOverviewResponse",
    "UsageTrendPointResponse",
]
