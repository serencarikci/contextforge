from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from contextforge.modules.admin.domain.enums import LlmProviderKind
from contextforge.shared.utilities.datetime import utc_now

MASKED_API_KEY = "***"


def mask_api_key(api_key: str | None) -> str | None:
    if api_key is None:
        return None
    cleaned = api_key.strip()
    if not cleaned:
        return None
    if len(cleaned) <= 4:
        return MASKED_API_KEY
    return f"{MASKED_API_KEY}{cleaned[-4:]}"


@dataclass(slots=True)
class LlmProviderConfig:
    provider: LlmProviderKind
    model: str
    id: UUID = field(default_factory=uuid4)
    organization_id: UUID | None = None
    base_url: str | None = None
    api_key_ciphertext: str | None = None
    api_key_hint: str | None = None
    temperature: float = 0.2
    max_tokens: int = 1024
    timeout_seconds: float = 60.0
    max_retries: int = 2
    rate_limit_rpm: int | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.model = self._validate_model(self.model)
        if self.base_url is not None:
            self.base_url = self._validate_base_url(self.base_url)
        self._validate_generation_params()

    @staticmethod
    def _validate_model(model: str) -> str:
        cleaned = model.strip()
        if not cleaned or len(cleaned) > 200:
            msg = "LLM model must be between 1 and 200 characters"
            raise ValueError(msg)
        return cleaned

    @staticmethod
    def _validate_base_url(base_url: str) -> str:
        cleaned = base_url.strip().rstrip("/")
        if not cleaned:
            msg = "LLM base_url must not be blank"
            raise ValueError(msg)
        if not cleaned.startswith(("http://", "https://")):
            msg = "LLM base_url must start with http:// or https://"
            raise ValueError(msg)
        if len(cleaned) > 500:
            msg = "LLM base_url must be at most 500 characters"
            raise ValueError(msg)
        return cleaned

    def _validate_generation_params(self) -> None:
        if not 0.0 <= self.temperature <= 2.0:
            msg = "LLM temperature must be between 0.0 and 2.0"
            raise ValueError(msg)
        if not 16 <= self.max_tokens <= 16000:
            msg = "LLM max_tokens must be between 16 and 16000"
            raise ValueError(msg)
        if not 0.0 < self.timeout_seconds <= 600.0:
            msg = "LLM timeout_seconds must be between 0 and 600"
            raise ValueError(msg)
        if not 0 <= self.max_retries <= 10:
            msg = "LLM max_retries must be between 0 and 10"
            raise ValueError(msg)
        if self.rate_limit_rpm is not None and not 1 <= self.rate_limit_rpm <= 100_000:
            msg = "LLM rate_limit_rpm must be between 1 and 100000"
            raise ValueError(msg)

    @property
    def api_key_set(self) -> bool:
        return bool(self.api_key_ciphertext)

    def set_api_key(self, *, ciphertext: str | None, hint: str | None) -> None:
        self.api_key_ciphertext = ciphertext or None
        self.api_key_hint = hint if ciphertext else None
        self.updated_at = utc_now()

    def update(
        self,
        *,
        model: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        rate_limit_rpm: int | None = None,
    ) -> None:
        if model is not None:
            self.model = self._validate_model(model)
        if base_url is not None:
            self.base_url = self._validate_base_url(base_url) if base_url.strip() else None
        if temperature is not None:
            self.temperature = temperature
        if max_tokens is not None:
            self.max_tokens = max_tokens
        if timeout_seconds is not None:
            self.timeout_seconds = timeout_seconds
        if max_retries is not None:
            self.max_retries = max_retries
        if rate_limit_rpm is not None:
            self.rate_limit_rpm = rate_limit_rpm
        self._validate_generation_params()
        self.updated_at = utc_now()

    def set_active(self, is_active: bool) -> None:
        self.is_active = is_active
        self.updated_at = utc_now()


__all__ = ["MASKED_API_KEY", "LlmProviderConfig", "mask_api_key"]
