from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from model_canary.alerting.factory import create_alerter
from model_canary.config.loader import load_config
from model_canary.core.exceptions import (
    ConfigError,
    ProviderError,
    StorageError,
)
from model_canary.core.models import (
    AlertConfig,
    CanaryRunResult,
    DriftReport,
    DriftSeverity,
    ModelCanaryConfig,
    PromptConfig,
    ProviderConfig,
)
from model_canary.drift.engine import DriftDetectionEngine
from model_canary.evaluators.base import BaseEvaluator
from model_canary.fingerprinting.engine import FingerprintingEngine
from model_canary.providers.factory import create_provider
from model_canary.providers.registry import register_providers
from model_canary.storage.factory import create_storage
from model_canary.utils.evaluator_loader import load_evaluator

logger = logging.getLogger("model_canary.engine")


class CanaryEngine:
    def __init__(
        self,
        config: ModelCanaryConfig | None = None,
        config_path: str | None = None,
    ) -> None:
        if config is None:
            config = load_config(path=config_path)
        self._config = config
        self._providers: dict[str, Any] = {}
        self._storage = None
        self._fingerprinter = FingerprintingEngine(
            embedding_model=config.embedding_model,
            similarity_threshold=config.similarity_threshold,
        )
        self._drift_detector = DriftDetectionEngine(
            similarity_threshold=config.similarity_threshold,
            drift_threshold=config.drift_threshold,
        )
        self._alerters: dict[str, Any] = {}
        self._evaluators: dict[str, BaseEvaluator] = {}
        self._semaphore: asyncio.Semaphore | None = None
        self._initialized = False

    @property
    def config(self) -> ModelCanaryConfig:
        return self._config

    async def initialize(self) -> None:
        if self._initialized:
            return

        self._semaphore = asyncio.Semaphore(self._config.max_concurrent)

        register_providers()
        await self._init_storage()
        await self._init_providers()
        await self._init_alerters()
        await self._init_evaluators()

        self._initialized = True
        logger.info(
            "Model Canary initialized with %d providers, %d alerters, %d evaluators",
            len(self._providers),
            len(self._alerters),
            len(self._evaluators),
        )

    async def _init_storage(self) -> None:
        storage_cfg = self._config.storage
        try:
            self._storage = create_storage(storage_cfg)
            await self._storage.initialize()
            logger.info("Storage initialized: %s", storage_cfg.backend)
        except Exception as e:
            raise StorageError(f"Failed to initialize storage: {e}")

    async def _init_providers(self) -> None:
        for provider_cfg in self._config.providers:
            try:
                provider = create_provider(provider_cfg)
                self._providers[provider_cfg.name] = provider
                logger.debug("Provider initialized: %s (%s)", provider_cfg.name, provider_cfg.provider_type)
            except Exception as e:
                logger.warning("Failed to initialize provider '%s': %s", provider_cfg.name, e)

        if not self._providers:
            logger.warning("No providers configured")

    async def _init_alerters(self) -> None:
        self._alerters["log"] = create_alerter("log")
        alert_cfg = self._config.alerting
        for channel in alert_cfg.channels:
            if channel == "log":
                continue
            try:
                alerter = create_alerter(channel)
                self._alerters[channel] = alerter
            except Exception as e:
                logger.warning("Failed to initialize alerter '%s': %s", channel, e)

    async def _init_evaluators(self) -> None:
        pass

    async def _get_evaluator(
        self, evaluator_name: str
    ) -> BaseEvaluator | None:
        if evaluator_name in self._evaluators:
            return self._evaluators[evaluator_name]
        try:
            evaluator = load_evaluator(evaluator_name)
            self._evaluators[evaluator_name] = evaluator
            return evaluator
        except Exception as e:
            logger.warning("Failed to load evaluator '%s': %s", evaluator_name, e)
            return None

    async def run_suite(self, suite_name: str) -> CanaryRunResult:
        await self.initialize()

        suite = None
        for s in self._config.test_suites:
            if s.name == suite_name:
                suite = s
                break
        if not suite:
            raise ConfigError(f"Test suite '{suite_name}' not found")

        run_result = CanaryRunResult(
            suite_name=suite_name,
            models_tested=list(set(p.model for p in suite.prompts if p.model)),
            providers_tested=list(self._providers.keys()),
        )

        logger.info("Running suite '%s' with %d prompts", suite_name, len(suite.prompts))

        try:
            tasks = []
            for prompt_cfg in suite.prompts:
                for provider_name in self._providers:
                    tasks.append(
                        self._execute_prompt(prompt_cfg, provider_name, run_result)
                    )

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error("Prompt execution failed: %s", result)
                    run_result.failed_prompts += 1
                elif isinstance(result, tuple):
                    prompt_result, fingerprint, drift_reports = result
                    run_result.prompt_results.append(prompt_result)
                    run_result.fingerprints.append(fingerprint)
                    run_result.drift_reports.extend(drift_reports)
                    run_result.total_cost += prompt_result.cost.total_cost
                    run_result.total_latency_ms += prompt_result.latency.total_time_ms
                    if prompt_result.success:
                        run_result.successful_prompts += 1
                    else:
                        run_result.failed_prompts += 1

            run_result.status = "completed"
        except Exception as e:
            run_result.status = "failed"
            run_result.error = str(e)
            logger.error("Suite '%s' failed: %s", suite_name, e)

        run_result.end_time = datetime.now(UTC)
        run_result.duration_ms = (
            run_result.end_time - run_result.start_time
        ).total_seconds() * 1000
        run_result.total_prompts = (
            run_result.successful_prompts + run_result.failed_prompts
        )

        await self._storage.save_run_result(run_result)
        for fp in run_result.fingerprints:
            await self._storage.save_fingerprint(fp)
        for report in run_result.drift_reports:
            await self._storage.save_drift_report(report)

        await self._send_alerts(run_result)

        logger.info(
            "Suite '%s' completed: %d/%d prompts successful, %d drifts detected",
            suite_name,
            run_result.successful_prompts,
            run_result.total_prompts,
            run_result.drift_count,
        )

        return run_result

    async def _execute_prompt(
        self,
        prompt_cfg: PromptConfig,
        provider_name: str,
        run_result: CanaryRunResult,
    ) -> tuple:
        provider = self._providers.get(provider_name)
        if not provider:
            raise ProviderError(f"Provider '{provider_name}' not initialized")

        async with self._semaphore:
            model = prompt_cfg.model or provider.config.default_model

            result = await provider.complete(
                prompt=prompt_cfg.prompt,
                model=model,
                max_tokens=prompt_cfg.max_tokens,
                temperature=prompt_cfg.temperature,
                prompt_name=prompt_cfg.name,
            )
            result.run_id = run_result.id

            fingerprint = await self._fingerprinter.fingerprint(result)

            baseline = await self._storage.get_latest_fingerprint(
                prompt_cfg.name, model, provider.name
            )

            drift_reports: list[DriftReport] = []
            if baseline:
                drift_reports = await self._drift_detector.detect(
                    baseline, fingerprint, prompt_cfg
                )

            for evaluator_name in prompt_cfg.evaluators:
                evaluator = await self._get_evaluator(evaluator_name)
                if evaluator:
                    eval_result = await evaluator.evaluate(prompt_cfg, result)
                    result.evaluation_results[evaluator_name] = eval_result

            return result, fingerprint, drift_reports

    async def _send_alerts(self, run_result: CanaryRunResult) -> None:
        alert_cfg = self._config.alerting
        if not alert_cfg.enabled:
            return

        critical_reports = [
            r for r in run_result.drift_reports
            if self._should_alert(r, alert_cfg)
        ]

        sent_count = 0
        for report in critical_reports[:alert_cfg.max_alerts_per_run]:
            for name, alerter in self._alerters.items():
                try:
                    await alerter.send_alert(report)
                    sent_count += 1
                except Exception as e:
                    logger.error("Alerter '%s' failed: %s", name, e)

        run_result.alerts_sent = sent_count

    def _should_alert(
        self, report: DriftReport, alert_cfg: AlertConfig
    ) -> bool:
        severity_order = {
            DriftSeverity.LOW: 0,
            DriftSeverity.MEDIUM: 1,
            DriftSeverity.HIGH: 2,
            DriftSeverity.CRITICAL: 3,
        }
        min_order = severity_order.get(alert_cfg.min_severity, 1)
        report_order = severity_order.get(report.severity, 1)
        return report_order >= min_order

    async def run_all_suites(self) -> list[CanaryRunResult]:
        await self.initialize()
        results = []
        for suite in self._config.test_suites:
            if suite.enabled:
                result = await self.run_suite(suite.name)
                results.append(result)
        return results

    async def run_prompt(
        self,
        prompt_cfg: PromptConfig,
        provider_name: str,
        suite_name: str = "adhoc",
    ) -> CanaryRunResult:
        await self.initialize()

        if provider_name not in self._providers:
            provider = create_provider(
                ProviderConfig(
                    name=provider_name,
                    type=provider_name,
                )
            )
            self._providers[provider_name] = provider

        run_result = CanaryRunResult(
            suite_name=suite_name,
            models_tested=[prompt_cfg.model or ""] if prompt_cfg.model else [],
            providers_tested=[provider_name],
        )

        try:
            result, fingerprint, drift_reports = await self._execute_prompt(
                prompt_cfg, provider_name, run_result
            )
            run_result.prompt_results.append(result)
            run_result.fingerprints.append(fingerprint)
            run_result.drift_reports.extend(drift_reports)
            run_result.total_cost += result.cost.total_cost
            run_result.total_latency_ms += result.latency.total_time_ms
            run_result.successful_prompts = 1 if result.success else 0
            run_result.failed_prompts = 0 if result.success else 1
            run_result.status = "completed"
        except Exception as e:
            run_result.status = "failed"
            run_result.error = str(e)

        run_result.end_time = datetime.now(UTC)
        run_result.duration_ms = (
            run_result.end_time - run_result.start_time
        ).total_seconds() * 1000
        run_result.total_prompts = 1

        await self._storage.save_run_result(run_result)
        for fp in run_result.fingerprints:
            await self._storage.save_fingerprint(fp)
        for report in run_result.drift_reports:
            await self._storage.save_drift_report(report)

        return run_result

    async def benchmark(
        self,
        prompt: str,
        models: list[str],
        providers: list[str] | None = None,
    ) -> dict[str, Any]:
        await self.initialize()

        results = {}
        provider_list = providers or list(self._providers.keys())

        for provider_name in provider_list:
            provider = self._providers.get(provider_name)
            if not provider:
                continue
            for model in models:
                try:
                    result = await provider.complete(
                        prompt=prompt,
                        model=model,
                    )
                    results[f"{provider_name}/{model}"] = {
                        "provider": provider_name,
                        "model": model,
                        "latency_ms": result.latency.total_time_ms,
                        "total_cost": result.cost.total_cost,
                        "tokens": result.token_usage.total_tokens,
                        "prompt_tokens": result.token_usage.prompt_tokens,
                        "completion_tokens": result.token_usage.completion_tokens,
                        "response_length": result.response_length,
                        "refusal": result.refusal,
                        "finish_reason": result.finish_reason,
                        "response_preview": result.response[:200] if result.response else "",
                    }
                except Exception as e:
                    results[f"{provider_name}/{model}"] = {
                        "provider": provider_name,
                        "model": model,
                        "error": str(e),
                    }

        return results

    async def compare(
        self,
        prompt_name: str,
        provider1: str,
        provider2: str,
    ) -> dict[str, Any]:
        await self.initialize()

        fp1 = await self._storage.get_latest_fingerprint(prompt_name, "", provider1)
        fp2 = await self._storage.get_latest_fingerprint(prompt_name, "", provider2)

        if not fp1 or not fp2:
            return {
                "error": "Fingerprints not found for comparison",
                "fingerprint_1_found": fp1 is not None,
                "fingerprint_2_found": fp2 is not None,
            }

        diff = {
            "prompt_name": prompt_name,
            "provider_1": provider1,
            "provider_2": provider2,
            "hash_match": fp1.sha256_hash == fp2.sha256_hash,
            "latency_diff_ms": abs(fp1.latency_ms - fp2.latency_ms),
            "cost_diff_usd": abs(fp1.cost_usd - fp2.cost_usd),
            "token_diff": abs(fp1.token_count - fp2.token_count),
            "refusal_1": fp1.refusal,
            "refusal_2": fp2.refusal,
            "response_length_diff": abs(fp1.response_length - fp2.response_length),
        }

        if fp1.embedding and fp2.embedding:
            diff["semantic_similarity"] = self._fingerprinter.cosine_similarity(
                fp1.embedding, fp2.embedding
            )
        else:
            diff["semantic_similarity"] = None

        return diff

    async def close(self) -> None:
        for provider in self._providers.values():
            try:
                await provider.close()
            except Exception:
                pass
        if self._storage:
            await self._storage.close()
        self._initialized = False
