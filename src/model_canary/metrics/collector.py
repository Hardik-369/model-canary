from __future__ import annotations

import logging
from typing import Any

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest

from model_canary.core.models import CanaryRunResult

logger = logging.getLogger("model_canary.metrics")


class MetricsCollector:
    def __init__(self, enabled: bool = True, prefix: str = "model_canary", registry: CollectorRegistry | None = None) -> None:
        self._enabled = enabled
        self._prefix = prefix
        self._registry = registry or CollectorRegistry()

        if enabled:
            self._init_metrics()

    def _init_metrics(self) -> None:
        self._run_counter = Counter(
            f"{self._prefix}_runs_total",
            "Total number of canary runs",
            ["status", "suite"],
            registry=self._registry,
        )
        self._drift_counter = Counter(
            f"{self._prefix}_drifts_total",
            "Total number of drifts detected",
            ["type", "severity"],
            registry=self._registry,
        )
        self._prompt_counter = Counter(
            f"{self._prefix}_prompts_total",
            "Total number of prompts executed",
            ["status", "provider"],
            registry=self._registry,
        )
        self._latency_histogram = Histogram(
            f"{self._prefix}_latency_ms",
            "Latency of model responses in milliseconds",
            ["provider", "model"],
            buckets=[50, 100, 200, 500, 1000, 2000, 5000, 10000, 30000],
            registry=self._registry,
        )
        self._cost_gauge = Gauge(
            f"{self._prefix}_total_cost_usd",
            "Total cost in USD",
            ["suite"],
            registry=self._registry,
        )
        self._tokens_histogram = Histogram(
            f"{self._prefix}_tokens_total",
            "Total tokens per prompt",
            ["provider"],
            buckets=[100, 500, 1000, 2000, 4000, 8000, 16000, 32000, 64000],
            registry=self._registry,
        )
        self._refusal_gauge = Gauge(
            f"{self._prefix}_refusals_total",
            "Total number of refusals",
            ["provider", "model"],
            registry=self._registry,
        )
        self._drift_score_gauge = Gauge(
            f"{self._prefix}_drift_score",
            "Drift score for detected drifts",
            ["type", "severity"],
            registry=self._registry,
        )
        self._provider_health_gauge = Gauge(
            f"{self._prefix}_provider_health",
            "Provider health status (1=up, 0=down)",
            ["provider"],
            registry=self._registry,
        )

    def record_run(self, result: CanaryRunResult) -> None:
        if not self._enabled:
            return
        try:
            self._run_counter.labels(status=result.status, suite=result.suite_name).inc()
            self._cost_gauge.labels(suite=result.suite_name).set(result.total_cost)

            for report in result.drift_reports:
                self._drift_counter.labels(
                    type=report.drift_type.value, severity=report.severity.value
                ).inc()
                self._drift_score_gauge.labels(
                    type=report.drift_type.value, severity=report.severity.value
                ).set(report.drift_score)

            for prompt_result in result.prompt_results:
                status = "success" if prompt_result.success else "failure"
                self._prompt_counter.labels(
                    status=status, provider=prompt_result.provider
                ).inc()
                self._latency_histogram.labels(
                    provider=prompt_result.provider,
                    model=prompt_result.model,
                ).observe(prompt_result.latency.total_time_ms)
                self._tokens_histogram.labels(
                    provider=prompt_result.provider,
                ).observe(prompt_result.token_usage.total_tokens)

                if prompt_result.refusal:
                    self._refusal_gauge.labels(
                        provider=prompt_result.provider,
                        model=prompt_result.model,
                    ).inc()

        except Exception as e:
            logger.warning("Failed to record metrics: %s", e)

    def record_provider_health(self, provider_name: str, is_healthy: bool) -> None:
        if not self._enabled:
            return
        try:
            self._provider_health_gauge.labels(provider=provider_name).set(1 if is_healthy else 0)
        except Exception:
            pass

    def get_metrics(self) -> str:
        return generate_latest(self._registry).decode("utf-8")

    def get_metrics_dict(self) -> dict[str, Any]:
        return {"enabled": self._enabled, "prefix": self._prefix}
