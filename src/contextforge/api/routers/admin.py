from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from contextforge.api.dependencies.identity import get_request_context, get_uow
from contextforge.api.dependencies.pagination import get_pagination
from contextforge.api.dependencies.providers import (
    get_document_ops_service,
    get_feature_flag_service,
    get_ingestion_job_queue,
    get_llm_config_service,
    get_ops_service,
    get_retention_cleanup_service,
    get_token_usage_service,
)
from contextforge.api.schemas.admin import (
    AdminDashboardResponse,
    AdminUserResponse,
    BulkDocumentIdsRequest,
    BulkDocumentResultResponse,
    DocumentOverviewResponse,
    FeatureFlagCreateRequest,
    FeatureFlagResponse,
    FeatureFlagsResolvedResponse,
    FeatureFlagUpdateRequest,
    IngestionOverviewResponse,
    KnowledgeSpaceStatsResponse,
    LlmConnectivityResponse,
    LlmProviderCreateRequest,
    LlmProviderResponse,
    LlmProviderUpdateRequest,
    OpsOverviewResponse,
    OrganizationSettingsResponse,
    OrganizationSettingsUpdateRequest,
    PromptPreviewRequest,
    PromptPreviewResponse,
    PromptTemplateCreateRequest,
    PromptTemplateResponse,
    RetentionPolicyCreateRequest,
    RetentionPolicyResponse,
    RetentionPolicyUpdateRequest,
    RetentionRunRequest,
    RetentionRunResponse,
    RolePermissionsResponse,
    RolePermissionsUpdateRequest,
    TokenPricingCreateRequest,
    TokenPricingResponse,
    TokenUsageItemResponse,
    UsageOverviewResponse,
    UsageTrendPointResponse,
)
from contextforge.api.schemas.common import PaginationMeta, PaginationResponse
from contextforge.api.schemas.ingestion import IngestionJobResponse
from contextforge.api.schemas.roles import RoleResponse
from contextforge.api.schemas.users import UserResponse
from contextforge.application.context.request_context import RequestContext
from contextforge.application.pagination import PaginationParams
from contextforge.application.ports.ingestion_job_queue import IngestionJobQueuePort
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.modules.admin.application.services.admin_role_service import AdminRoleService
from contextforge.modules.admin.application.services.admin_user_service import AdminUserService
from contextforge.modules.admin.application.services.audit_export_service import AuditExportService
from contextforge.modules.admin.application.services.dashboard_service import DashboardService
from contextforge.modules.admin.application.services.document_ops_service import DocumentOpsService
from contextforge.modules.admin.application.services.feature_flag_service import FeatureFlagService
from contextforge.modules.admin.application.services.ingestion_ops_service import (
    IngestionOpsService,
)
from contextforge.modules.admin.application.services.knowledge_space_admin_service import (
    KnowledgeSpaceAdminService,
)
from contextforge.modules.admin.application.services.llm_config_service import LlmConfigService
from contextforge.modules.admin.application.services.ops_service import OpsService
from contextforge.modules.admin.application.services.organization_settings_service import (
    OrganizationSettingsService,
)
from contextforge.modules.admin.application.services.prompt_admin_service import PromptAdminService
from contextforge.modules.admin.application.services.retention_service import (
    RetentionCleanupService,
)
from contextforge.modules.admin.application.services.token_usage_service import TokenUsageService
from contextforge.modules.admin.application.services.usage_analytics_service import (
    UsageAnalyticsService,
)
from contextforge.modules.admin.domain.entities.feature_flag import FeatureFlag
from contextforge.modules.admin.domain.entities.llm_provider_config import LlmProviderConfig
from contextforge.modules.admin.domain.entities.organization_settings import OrganizationSettings
from contextforge.modules.admin.domain.entities.prompt_template import PromptTemplate
from contextforge.modules.admin.domain.entities.retention import RetentionPolicy, RetentionRun
from contextforge.modules.admin.domain.entities.token_pricing import TokenPricing
from contextforge.modules.admin.domain.entities.token_usage import TokenUsageAggregate
from contextforge.modules.admin.domain.enums import (
    LlmProviderKind,
    PromptLanguage,
    PromptTemplateName,
    RetentionResourceType,
)
from contextforge.modules.identity_access.domain.enums import UserStatus

router = APIRouter(prefix="/admin", tags=["admin"])

_dashboard = DashboardService()
_users = AdminUserService()
_org_settings = OrganizationSettingsService()
_roles = AdminRoleService()
_ks_admin = KnowledgeSpaceAdminService()
_ingestion_ops = IngestionOpsService()
_audit_export = AuditExportService()
_usage = UsageAnalyticsService()
_prompts = PromptAdminService()


def _org_settings_response(settings: OrganizationSettings) -> OrganizationSettingsResponse:
    return OrganizationSettingsResponse(
        organization_id=settings.organization_id,
        quotas=settings.quotas.to_mapping(),
        defaults=dict(settings.defaults),
        feature_overrides=dict(settings.feature_overrides),
        is_active=settings.is_active,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


def _prompt_response(template: PromptTemplate) -> PromptTemplateResponse:
    return PromptTemplateResponse(
        id=template.id,
        organization_id=template.organization_id,
        name=template.name.value,
        version=template.version,
        language=template.language.value,
        content=template.content,
        is_active=template.is_active,
        is_system=template.is_system,
        placeholders=template.placeholders,
        created_by=template.created_by,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def _llm_response(config: LlmProviderConfig) -> LlmProviderResponse:
    return LlmProviderResponse(
        id=config.id,
        organization_id=config.organization_id,
        provider=config.provider.value,
        model=config.model,
        base_url=config.base_url,
        api_key_set=config.api_key_set,
        api_key_hint=config.api_key_hint,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        timeout_seconds=config.timeout_seconds,
        max_retries=config.max_retries,
        rate_limit_rpm=config.rate_limit_rpm,
        is_active=config.is_active,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


def _flag_response(flag: FeatureFlag) -> FeatureFlagResponse:
    return FeatureFlagResponse(
        id=flag.id,
        key=flag.key,
        description=flag.description,
        enabled_globally=flag.enabled_globally,
        organization_id=flag.organization_id,
        value=dict(flag.value),
        created_at=flag.created_at,
        updated_at=flag.updated_at,
    )


def _retention_policy_response(policy: RetentionPolicy) -> RetentionPolicyResponse:
    return RetentionPolicyResponse(
        id=policy.id,
        organization_id=policy.organization_id,
        resource_type=policy.resource_type.value,
        retention_days=policy.retention_days,
        soft_delete_first=policy.soft_delete_first,
        enabled=policy.enabled,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


def _retention_run_response(run: RetentionRun) -> RetentionRunResponse:
    return RetentionRunResponse(
        id=run.id,
        policy_id=run.policy_id,
        organization_id=run.organization_id,
        status=run.status.value,
        started_at=run.started_at,
        finished_at=run.finished_at,
        deleted_count=run.deleted_count,
        summary=dict(run.summary),
    )


def _token_usage_item(row: TokenUsageAggregate) -> TokenUsageItemResponse:
    return TokenUsageItemResponse(
        provider=row.provider,
        model=row.model,
        prompt_tokens=row.prompt_tokens,
        completion_tokens=row.completion_tokens,
        request_count=row.request_count,
        estimated_cost=row.estimated_cost,
        total_tokens=row.total_tokens,
        organization_id=row.organization_id,
    )


def _pricing_response(pricing: TokenPricing) -> TokenPricingResponse:
    return TokenPricingResponse.model_validate(pricing)


@router.get("/dashboard", response_model=AdminDashboardResponse)
async def get_dashboard(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> AdminDashboardResponse:
    dashboard = await _dashboard.get_dashboard(uow, ctx)
    return AdminDashboardResponse.model_validate(dashboard)


@router.get("/users", response_model=PaginationResponse[AdminUserResponse])
async def list_admin_users(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    q: Annotated[str | None, Query()] = None,
    status_filter: Annotated[UserStatus | None, Query(alias="status")] = None,
) -> PaginationResponse[AdminUserResponse]:
    page = await _users.list_users(uow, ctx, pagination, q=q, status=status_filter)
    return PaginationResponse(
        items=[AdminUserResponse.model_validate(item) for item in page.items],
        pagination=PaginationMeta(limit=page.limit, offset=page.offset, total=page.total),
    )


@router.post("/users/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> UserResponse:
    user = await _users.activate(uow, ctx, user_id)
    return UserResponse.model_validate(user)


@router.post("/users/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> UserResponse:
    user = await _users.deactivate(uow, ctx, user_id)
    return UserResponse.model_validate(user)


@router.get("/organizations/settings", response_model=OrganizationSettingsResponse)
async def get_organization_settings(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> OrganizationSettingsResponse:
    settings = await _org_settings.get(uow, ctx)
    return _org_settings_response(settings)


@router.patch("/organizations/settings", response_model=OrganizationSettingsResponse)
async def update_organization_settings(
    payload: OrganizationSettingsUpdateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> OrganizationSettingsResponse:
    settings = await _org_settings.update(
        uow,
        ctx,
        quotas=payload.quotas,
        defaults=payload.defaults,
        feature_overrides=payload.feature_overrides,
        is_active=payload.is_active,
    )
    return _org_settings_response(settings)


@router.get("/roles/{role_id}/permissions", response_model=RolePermissionsResponse)
async def get_role_permissions(
    role_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> RolePermissionsResponse:
    codes = await _roles.get_permissions(uow, ctx, role_id)
    return RolePermissionsResponse(role_id=role_id, permission_codes=codes)


@router.put("/roles/{role_id}/permissions", response_model=RolePermissionsResponse)
async def replace_role_permissions(
    role_id: UUID,
    payload: RolePermissionsUpdateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> RolePermissionsResponse:
    codes = await _roles.replace_permissions(
        uow, ctx, role_id, permission_codes=payload.permission_codes
    )
    return RolePermissionsResponse(role_id=role_id, permission_codes=codes)


@router.delete("/roles/{role_id}", response_model=RoleResponse)
async def archive_admin_role(
    role_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> RoleResponse:
    role = await _roles.archive_role(uow, ctx, role_id)
    return RoleResponse.model_validate(role)


@router.get(
    "/knowledge-spaces/{knowledge_space_id}/stats",
    response_model=KnowledgeSpaceStatsResponse,
)
async def knowledge_space_stats(
    knowledge_space_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> KnowledgeSpaceStatsResponse:
    stats = await _ks_admin.get_stats(uow, ctx, knowledge_space_id)
    return KnowledgeSpaceStatsResponse.model_validate(stats)


@router.get("/documents/overview", response_model=DocumentOverviewResponse)
async def documents_overview(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[DocumentOpsService, Depends(get_document_ops_service)],
) -> DocumentOverviewResponse:
    overview = await service.overview(uow, ctx)
    return DocumentOverviewResponse.model_validate(overview)


@router.post("/documents/bulk-reprocess", response_model=BulkDocumentResultResponse)
async def documents_bulk_reprocess(
    payload: BulkDocumentIdsRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[DocumentOpsService, Depends(get_document_ops_service)],
    queue: Annotated[IngestionJobQueuePort, Depends(get_ingestion_job_queue)],
) -> BulkDocumentResultResponse:
    result = await service.bulk_reprocess(uow, ctx, queue, payload.document_ids)
    return BulkDocumentResultResponse.model_validate(result)


@router.post("/documents/bulk-delete", response_model=BulkDocumentResultResponse)
async def documents_bulk_delete(
    payload: BulkDocumentIdsRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[DocumentOpsService, Depends(get_document_ops_service)],
) -> BulkDocumentResultResponse:
    result = await service.bulk_delete(uow, ctx, payload.document_ids)
    return BulkDocumentResultResponse.model_validate(result)


@router.get("/ingestion/overview", response_model=IngestionOverviewResponse)
async def ingestion_overview(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    queue: Annotated[IngestionJobQueuePort, Depends(get_ingestion_job_queue)],
) -> IngestionOverviewResponse:
    overview = await _ingestion_ops.overview(uow, ctx, queue)
    return IngestionOverviewResponse.model_validate(overview)


@router.post("/ingestion/jobs/{job_id}/cancel", response_model=IngestionJobResponse)
async def cancel_ingestion_job(
    job_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> IngestionJobResponse:
    job = await _ingestion_ops.cancel(uow, ctx, job_id)
    return IngestionJobResponse.model_validate(job)


@router.get("/audit/export")
async def export_audit(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    export_format: Annotated[str, Query(alias="format")] = "json",
    action: Annotated[str | None, Query()] = None,
    resource_type: Annotated[str | None, Query()] = None,
    actor_user_id: Annotated[UUID | None, Query()] = None,
    occurred_from: Annotated[datetime | None, Query()] = None,
    occurred_to: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=10000)] = 5000,
) -> Response:
    export = await _audit_export.export(
        uow,
        ctx,
        export_format=export_format,
        action=action,
        resource_type=resource_type,
        actor_user_id=actor_user_id,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        limit=limit,
    )
    return Response(
        content=export.body,
        media_type=export.content_type,
        headers={"Content-Disposition": f'attachment; filename="{export.filename}"'},
    )


@router.get("/usage/overview", response_model=UsageOverviewResponse)
async def usage_overview(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> UsageOverviewResponse:
    overview = await _usage.overview(uow, ctx)
    return UsageOverviewResponse.model_validate(overview)


@router.get("/usage/trends", response_model=list[UsageTrendPointResponse])
async def usage_trends(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> list[UsageTrendPointResponse]:
    points = await _usage.trends(uow, ctx, days=days)
    return [UsageTrendPointResponse.model_validate(point) for point in points]


@router.get("/usage/tokens", response_model=list[TokenUsageItemResponse])
async def list_token_usage(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[TokenUsageService, Depends(get_token_usage_service)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> list[TokenUsageItemResponse]:
    rows = await service.list_tokens(uow, ctx, days=days)
    return [_token_usage_item(row) for row in rows]


@router.get("/usage/pricing", response_model=list[TokenPricingResponse])
async def list_token_pricing(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[TokenUsageService, Depends(get_token_usage_service)],
) -> list[TokenPricingResponse]:
    rows = await service.list_pricing(uow, ctx)
    return [_pricing_response(row) for row in rows]


@router.post(
    "/usage/pricing",
    response_model=TokenPricingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_token_pricing(
    payload: TokenPricingCreateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[TokenUsageService, Depends(get_token_usage_service)],
) -> TokenPricingResponse:
    pricing = await service.upsert_pricing(
        uow,
        ctx,
        provider=payload.provider,
        model=payload.model,
        input_price_per_1k=payload.input_price_per_1k,
        output_price_per_1k=payload.output_price_per_1k,
        currency=payload.currency,
    )
    return _pricing_response(pricing)


@router.get("/usage/tokens/export")
async def export_token_usage(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[TokenUsageService, Depends(get_token_usage_service)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    export_format: Annotated[str, Query(alias="format")] = "json",
) -> Response:
    export = await service.export_tokens(uow, ctx, days=days, export_format=export_format)
    return Response(
        content=export.body,
        media_type=export.content_type,
        headers={"Content-Disposition": f'attachment; filename="{export.filename}"'},
    )


@router.get("/prompts", response_model=list[PromptTemplateResponse])
async def list_prompts(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    language: Annotated[str | None, Query()] = None,
) -> list[PromptTemplateResponse]:
    templates = await _prompts.list(uow, ctx, language=language)
    return [_prompt_response(item) for item in templates]


@router.post("/prompts", response_model=PromptTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    payload: PromptTemplateCreateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> PromptTemplateResponse:
    template = await _prompts.create(
        uow,
        ctx,
        name=PromptTemplateName(payload.name),
        version=payload.version,
        language=PromptLanguage(payload.language),
        content=payload.content,
        activate=payload.activate,
    )
    return _prompt_response(template)


@router.post("/prompts/{template_id}/activate", response_model=PromptTemplateResponse)
async def activate_prompt(
    template_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> PromptTemplateResponse:
    template = await _prompts.activate(uow, ctx, template_id)
    return _prompt_response(template)


@router.post("/prompts/{template_id}/deactivate", response_model=PromptTemplateResponse)
async def deactivate_prompt(
    template_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> PromptTemplateResponse:
    template = await _prompts.deactivate(uow, ctx, template_id)
    return _prompt_response(template)


@router.post("/prompts/{template_id}/preview", response_model=PromptPreviewResponse)
async def preview_prompt(
    template_id: UUID,
    payload: PromptPreviewRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> PromptPreviewResponse:
    preview = await _prompts.preview(uow, ctx, template_id, payload.values)
    return PromptPreviewResponse(
        id=preview.template_id,
        placeholders=preview.placeholders,
        rendered=preview.rendered,
    )


@router.post("/prompts/{template_id}/rollback", response_model=PromptTemplateResponse)
async def rollback_prompt(
    template_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> PromptTemplateResponse:
    template = await _prompts.rollback(uow, ctx, template_id)
    return _prompt_response(template)


@router.delete("/prompts/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    template_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> None:
    await _prompts.delete(uow, ctx, template_id)


@router.get("/llm-providers", response_model=list[LlmProviderResponse])
async def list_llm_providers(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[LlmConfigService, Depends(get_llm_config_service)],
) -> list[LlmProviderResponse]:
    configs = await service.list(uow, ctx)
    return [_llm_response(item) for item in configs]


@router.post(
    "/llm-providers",
    response_model=LlmProviderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_llm_provider(
    payload: LlmProviderCreateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[LlmConfigService, Depends(get_llm_config_service)],
) -> LlmProviderResponse:
    config = await service.create(
        uow,
        ctx,
        provider=LlmProviderKind(payload.provider),
        model=payload.model,
        base_url=payload.base_url,
        api_key=payload.api_key,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        timeout_seconds=payload.timeout_seconds,
        max_retries=payload.max_retries,
        rate_limit_rpm=payload.rate_limit_rpm,
        is_active=payload.is_active,
    )
    return _llm_response(config)


@router.patch("/llm-providers/{config_id}", response_model=LlmProviderResponse)
async def update_llm_provider(
    config_id: UUID,
    payload: LlmProviderUpdateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[LlmConfigService, Depends(get_llm_config_service)],
) -> LlmProviderResponse:
    config = await service.update(
        uow,
        ctx,
        config_id,
        model=payload.model,
        base_url=payload.base_url,
        api_key=payload.api_key,
        clear_api_key=payload.clear_api_key,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        timeout_seconds=payload.timeout_seconds,
        max_retries=payload.max_retries,
        rate_limit_rpm=payload.rate_limit_rpm,
        is_active=payload.is_active,
    )
    return _llm_response(config)


@router.delete("/llm-providers/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_provider(
    config_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[LlmConfigService, Depends(get_llm_config_service)],
) -> None:
    await service.delete(uow, ctx, config_id)


@router.post("/llm-providers/{config_id}/test", response_model=LlmConnectivityResponse)
async def test_llm_provider(
    config_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[LlmConfigService, Depends(get_llm_config_service)],
) -> LlmConnectivityResponse:
    result = await service.test_connectivity(uow, ctx, config_id)
    return LlmConnectivityResponse(
        status=result.status.value,
        latency_ms=result.latency_ms,
        detail=result.detail,
    )


@router.get("/feature-flags", response_model=list[FeatureFlagResponse])
async def list_feature_flags(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
) -> list[FeatureFlagResponse]:
    flags = await service.list_flags(uow, ctx)
    return [_flag_response(flag) for flag in flags]


@router.get("/feature-flags/resolved", response_model=FeatureFlagsResolvedResponse)
async def resolved_feature_flags(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
) -> FeatureFlagsResolvedResponse:
    flags = await service.resolve(uow, ctx.organization_id)
    return FeatureFlagsResolvedResponse(flags=flags)


@router.post(
    "/feature-flags",
    response_model=FeatureFlagResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_feature_flag(
    payload: FeatureFlagCreateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
) -> FeatureFlagResponse:
    flag = await service.create(
        uow,
        ctx,
        key=payload.key,
        description=payload.description,
        enabled=payload.enabled,
        value=payload.value,
        global_flag=payload.global_flag,
    )
    return _flag_response(flag)


@router.patch("/feature-flags/{flag_id}", response_model=FeatureFlagResponse)
async def update_feature_flag(
    flag_id: UUID,
    payload: FeatureFlagUpdateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
) -> FeatureFlagResponse:
    flag = await service.update(
        uow,
        ctx,
        flag_id,
        description=payload.description,
        enabled=payload.enabled,
        value=payload.value,
    )
    return _flag_response(flag)


@router.delete("/feature-flags/{flag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feature_flag(
    flag_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
) -> None:
    await service.delete(uow, ctx, flag_id)


@router.get("/ops/overview", response_model=OpsOverviewResponse)
async def ops_overview(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[OpsService, Depends(get_ops_service)],
    queue: Annotated[IngestionJobQueuePort, Depends(get_ingestion_job_queue)],
) -> OpsOverviewResponse:
    overview = await service.overview(uow, ctx, queue)
    return OpsOverviewResponse(
        readiness_status=overview.readiness.status,
        ingestion_pending=overview.ingestion_pending,
        ingestion_failed=overview.ingestion_failed,
        queue_depth=overview.queue_depth,
        llm_configured=overview.llm_configured,
        retention_enabled=overview.retention_enabled,
    )


@router.get("/retention/policies", response_model=list[RetentionPolicyResponse])
async def list_retention_policies(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[RetentionCleanupService, Depends(get_retention_cleanup_service)],
) -> list[RetentionPolicyResponse]:
    policies = await service.list_policies(uow, ctx)
    return [_retention_policy_response(policy) for policy in policies]


@router.post(
    "/retention/policies",
    response_model=RetentionPolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_retention_policy(
    payload: RetentionPolicyCreateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[RetentionCleanupService, Depends(get_retention_cleanup_service)],
) -> RetentionPolicyResponse:
    policy = await service.create_policy(
        uow,
        ctx,
        resource_type=RetentionResourceType(payload.resource_type),
        retention_days=payload.retention_days,
        soft_delete_first=payload.soft_delete_first,
        enabled=payload.enabled,
    )
    return _retention_policy_response(policy)


@router.patch("/retention/policies/{policy_id}", response_model=RetentionPolicyResponse)
async def update_retention_policy(
    policy_id: UUID,
    payload: RetentionPolicyUpdateRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[RetentionCleanupService, Depends(get_retention_cleanup_service)],
) -> RetentionPolicyResponse:
    policy = await service.update_policy(
        uow,
        ctx,
        policy_id,
        retention_days=payload.retention_days,
        soft_delete_first=payload.soft_delete_first,
        enabled=payload.enabled,
    )
    return _retention_policy_response(policy)


@router.delete("/retention/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_retention_policy(
    policy_id: UUID,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[RetentionCleanupService, Depends(get_retention_cleanup_service)],
) -> None:
    await service.delete_policy(uow, ctx, policy_id)


@router.get("/retention/runs", response_model=list[RetentionRunResponse])
async def list_retention_runs(
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[RetentionCleanupService, Depends(get_retention_cleanup_service)],
) -> list[RetentionRunResponse]:
    runs = await service.list_runs(uow, ctx)
    return [_retention_run_response(run) for run in runs]


@router.post("/retention/run", response_model=list[RetentionRunResponse])
async def run_retention(
    payload: RetentionRunRequest,
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    service: Annotated[RetentionCleanupService, Depends(get_retention_cleanup_service)],
) -> list[RetentionRunResponse]:
    results = await service.run_policy(uow, ctx, policy_id=payload.policy_id)
    return [_retention_run_response(item.run) for item in results]
