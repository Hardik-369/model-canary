from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DriftType(str, Enum):
    OUTPUT_DRIFT = "output_drift"
    SEMANTIC_DRIFT = "semantic_drift"
    STRUCTURAL_DRIFT = "structural_drift"
    FORMATTING_DRIFT = "formatting_drift"
    LATENCY_SPIKE = "latency_spike"
    COST_SPIKE = "cost_spike"
    REFUSAL_INCREASE = "refusal_increase"
    TOOL_FAILURE = "tool_failure"
    JSON_FAILURE = "json_failure"
    REASONING_DEGRADATION = "reasoning_degradation"
    API_FAILURE = "api_failure"
    PROVIDER_OUTAGE = "provider_outage"
    TOKEN_USAGE_DRIFT = "token_usage_drift"
    HALLUCINATION_DRIFT = "hallucination_drift"
    SAFETY_DRIFT = "safety_drift"
    CONTEXT_WINDOW_DRIFT = "context_window_drift"
    FUNCTION_CALLING_DRIFT = "function_calling_drift"
    PROMPT_INJECTION_DRIFT = "prompt_injection_drift"
    MODEL_ALIAS_DRIFT = "model_alias_drift"
    API_VERSION_DRIFT = "api_version_drift"
    UNKNOWN = "unknown"


class DriftSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProviderConfig(BaseModel):
    name: str
    provider_type: str = Field(alias="type")
    api_key: str | None = None
    base_url: str | None = None
    organization: str | None = None
    default_model: str | None = None
    models: list[str] = Field(default_factory=list)
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_rpm: int | None = None
    rate_limit_tpm: int | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def name_must_be_valid(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Provider name cannot be empty")
        return v.strip()


class PromptConfig(BaseModel):
    name: str
    description: str = ""
    prompt: str
    expected_output: str | None = None
    acceptable_outputs: list[str] = Field(default_factory=list)
    required_json_schema: dict[str, Any] | None = None
    severity: DriftSeverity = DriftSeverity.MEDIUM
    tags: list[str] = Field(default_factory=list)
    priority: int = 0
    category: str = "general"
    evaluators: list[str] = Field(default_factory=list)
    max_tokens: int | None = None
    temperature: float | None = None
    model: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])

    @field_validator("name")
    @classmethod
    def name_must_be_valid(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Prompt name cannot be empty")
        return v.strip()


class TestSuiteConfig(BaseModel):
    name: str
    description: str = ""
    prompts: list[PromptConfig] = Field(default_factory=list)
    providers: list[ProviderConfig] = Field(default_factory=list)
    schedule: str | None = None
    enabled: bool = True
    tags: list[str] = Field(default_factory=list)
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    reasoning_tokens: int | None = None


class LatencyMetrics(BaseModel):
    total_time: float = 0.0
    time_to_first_token: float | None = None
    time_per_output_token: float | None = None
    total_time_ms: float = 0.0


class CostMetrics(BaseModel):
    total_cost: float = 0.0
    cost_per_prompt_token: float = 0.0
    cost_per_completion_token: float = 0.0
    currency: str = "USD"


class ModelInfo(BaseModel):
    model_name: str
    model_version: str | None = None
    provider: str
    deployment_id: str | None = None


class ProviderInfo(BaseModel):
    provider_name: str
    provider_type: str
    base_url: str | None = None
    api_version: str | None = None
    is_available: bool = True
    latency_ms: float = 0.0


class PromptResult(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    prompt_name: str
    prompt_text: str
    model: str
    provider: str
    response: str
    stop_reason: str | None = None
    finish_reason: str | None = None
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    latency: LatencyMetrics = Field(default_factory=LatencyMetrics)
    cost: CostMetrics = Field(default_factory=CostMetrics)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    function_calls: list[dict[str, Any]] = Field(default_factory=list)
    refusal: bool = False
    refusal_reason: str | None = None
    error: str | None = None
    raw_response: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    run_id: str = ""
    evaluation_results: dict[str, Any] = Field(default_factory=dict)
    extra: dict[str, Any] = Field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.error is None and not self.refusal

    @property
    def response_length(self) -> int:
        return len(self.response)

    @property
    def response_tokens(self) -> int:
        return self.token_usage.completion_tokens


class Fingerprint(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    prompt_name: str
    model: str
    provider: str
    sha256_hash: str = ""
    embedding: list[float] | None = None
    token_count: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    refusal: bool = False
    stop_reason: str | None = None
    finish_reason: str | None = None
    json_schema_hash: str | None = None
    markdown_structure_hash: str | None = None
    tool_call_count: int = 0
    function_call_count: int = 0
    reasoning_length: int | None = None
    confidence_score: float | None = None
    response_length: int = 0
    response_hash: str = ""
    provider_info: ProviderInfo | None = None
    prompt_result_id: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    run_id: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


class DriftReport(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    run_id: str
    prompt_name: str
    model: str
    provider: str
    drift_type: DriftType
    severity: DriftSeverity
    baseline_fingerprint: Fingerprint
    current_fingerprint: Fingerprint
    drift_score: float = 0.0
    drift_details: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    previous_value: str | None = None
    current_value: str | None = None
    threshold: float | None = None
    message: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    acknowledged: bool = False
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class AlertConfig(BaseModel):
    enabled: bool = True
    channels: list[str] = Field(default_factory=lambda: ["log"])
    min_severity: DriftSeverity = DriftSeverity.MEDIUM
    cooldown_minutes: int = 60
    max_alerts_per_run: int = 10
    notification_templates: dict[str, str] = Field(default_factory=dict)


class StorageConfig(BaseModel):
    backend: str = "sqlite"
    connection_string: str = "sqlite:///model_canary.db"
    table_prefix: str = "mc_"
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False
    extra: dict[str, Any] = Field(default_factory=dict)


class EvaluatorConfig(BaseModel):
    name: str
    evaluator_type: str = Field(alias="type")
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    weight: float = 1.0
    fail_on_error: bool = False


class CanaryRunResult(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    suite_name: str
    status: str = "running"
    start_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    duration_ms: float = 0.0
    total_prompts: int = 0
    successful_prompts: int = 0
    failed_prompts: int = 0
    drift_reports: list[DriftReport] = Field(default_factory=list)
    fingerprints: list[Fingerprint] = Field(default_factory=list)
    prompt_results: list[PromptResult] = Field(default_factory=list)
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    models_tested: list[str] = Field(default_factory=list)
    providers_tested: list[str] = Field(default_factory=list)
    alerts_sent: int = 0
    error: str | None = None
    config_snapshot: dict[str, Any] | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        if self.total_prompts == 0:
            return 0.0
        return (self.successful_prompts / self.total_prompts) * 100.0

    @property
    def drift_count(self) -> int:
        return len(self.drift_reports)

    @property
    def has_critical_drift(self) -> bool:
        return any(
            r.severity == DriftSeverity.CRITICAL for r in self.drift_reports
        )


class ModelCanaryConfig(BaseModel):
    version: str = "1"
    project_name: str = "model-canary"
    providers: list[ProviderConfig] = Field(default_factory=list)
    test_suites: list[TestSuiteConfig] = Field(default_factory=list)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    alerting: AlertConfig = Field(default_factory=AlertConfig)
    schedule: str | None = None
    plugins: list[str] = Field(default_factory=list)
    log_level: str = "INFO"
    metrics_enabled: bool = True
    telemetry_enabled: bool = True
    max_concurrent: int = 5
    fingerprint_algorithm: str = "sha256"
    embedding_model: str = "all-MiniLM-L6-v2"
    similarity_threshold: float = 0.85
    drift_threshold: float = 0.1
    cache_responses: bool = True
    cache_ttl_seconds: int = 3600
    privacy_mode: bool = False
    extra: dict[str, Any] = Field(default_factory=dict)
