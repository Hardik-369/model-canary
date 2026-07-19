from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Protocol

from model_canary.core.models import (
    CanaryRunResult,
    DriftReport,
    Fingerprint,
    ModelInfo,
    PromptConfig,
    PromptResult,
)


class PluginType(str, Enum):
    PROVIDER = "provider"
    EVALUATOR = "evaluator"
    ALERTER = "alerter"
    STORAGE = "storage"
    FINGERPRINTER = "fingerprinter"
    DRIFT_DETECTOR = "drift_detector"
    SCHEDULER = "scheduler"
    REPORTER = "reporter"
    METRICS = "metrics"
    HOOK = "hook"


class Provider(ABC):
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> PromptResult:
        ...

    @abstractmethod
    async def list_models(self) -> list[ModelInfo]:
        ...

    @abstractmethod
    async def check_health(self) -> bool:
        ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def provider_type(self) -> str: ...


class Evaluator(ABC):
    @abstractmethod
    async def evaluate(
        self,
        prompt: PromptConfig,
        result: PromptResult,
        **kwargs: Any,
    ) -> dict[str, Any]:
        ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def evaluator_type(self) -> str: ...


class Fingerprinter(ABC):
    @abstractmethod
    async def fingerprint(
        self, result: PromptResult, **kwargs: Any
    ) -> Fingerprint:
        ...

    @property
    @abstractmethod
    def name(self) -> str: ...


class DriftDetector(ABC):
    @abstractmethod
    async def detect(
        self,
        baseline: Fingerprint,
        current: Fingerprint,
        **kwargs: Any,
    ) -> DriftReport | None:
        ...

    @property
    @abstractmethod
    def name(self) -> str: ...


class StorageBackend(ABC):
    @abstractmethod
    async def initialize(self) -> None:
        ...

    @abstractmethod
    async def close(self) -> None:
        ...

    @abstractmethod
    async def save_run_result(
        self, result: CanaryRunResult
    ) -> None:
        ...

    @abstractmethod
    async def save_drift_report(
        self, report: DriftReport
    ) -> None:
        ...

    @abstractmethod
    async def save_fingerprint(
        self, fingerprint: Fingerprint
    ) -> None:
        ...

    @abstractmethod
    async def get_run_result(
        self, run_id: str
    ) -> CanaryRunResult | None:
        ...

    @abstractmethod
    async def get_latest_fingerprint(
        self, prompt_name: str, model: str, provider: str
    ) -> Fingerprint | None:
        ...

    @abstractmethod
    async def get_drift_reports(
        self,
        prompt_name: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        severity: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DriftReport]:
        ...

    @abstractmethod
    async def get_fingerprint_history(
        self,
        prompt_name: str,
        model: str,
        provider: str,
        limit: int = 100,
    ) -> list[Fingerprint]:
        ...


class Alerter(ABC):
    @abstractmethod
    async def send_alert(
        self,
        report: DriftReport,
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> bool:
        ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def alerter_type(self) -> str: ...


class Plugin(ABC):
    @abstractmethod
    def initialize(self, config: dict[str, Any] | None = None) -> None:
        ...

    @abstractmethod
    def shutdown(self) -> None:
        ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def plugin_type(self) -> PluginType: ...

    @property
    @abstractmethod
    def version(self) -> str: ...


class Scheduler(ABC):
    @abstractmethod
    async def start(self) -> None:
        ...

    @abstractmethod
    async def stop(self) -> None:
        ...

    @abstractmethod
    async def add_job(
        self, job_id: str, func: callable, cron_expr: str, **kwargs: Any
    ) -> None:
        ...

    @abstractmethod
    async def remove_job(self, job_id: str) -> None:
        ...


class Reporter(ABC):
    @abstractmethod
    async def generate_report(
        self,
        run_result: CanaryRunResult,
        format: str = "html",
        **kwargs: Any,
    ) -> str:
        ...

    @property
    @abstractmethod
    def name(self) -> str: ...


class Hook(Protocol):
    async def on_run_start(
        self, config: Any, **kwargs: Any
    ) -> None: ...

    async def on_run_end(
        self, result: CanaryRunResult, **kwargs: Any
    ) -> None: ...

    async def on_drift_detected(
        self, report: DriftReport, **kwargs: Any
    ) -> None: ...

    async def on_prompt_complete(
        self, result: PromptResult, **kwargs: Any
    ) -> None: ...

    async def on_error(
        self, error: Exception, **kwargs: Any
    ) -> None: ...
