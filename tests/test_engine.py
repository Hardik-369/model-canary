from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime
from unittest.mock import ANY, AsyncMock, MagicMock, PropertyMock, patch

import pytest

# Mock litellm before any provider imports
if "litellm" not in sys.modules:
    _litellm_mock = MagicMock()
    _litellm_mock.acompletion = AsyncMock()
    _litellm_mock.amodel_list = AsyncMock()
    sys.modules["litellm"] = _litellm_mock

from model_canary.core.models import (
    AlertConfig,
    CanaryRunResult,
    CostMetrics,
    DriftReport,
    DriftSeverity,
    DriftType,
    Fingerprint,
    LatencyMetrics,
    ModelCanaryConfig,
    PromptConfig,
    PromptResult,
    ProviderConfig,
    StorageConfig,
    TestSuiteConfig,
    TokenUsage,
)
from model_canary.fingerprinting.engine import FingerprintingEngine
from model_canary.drift.engine import DriftDetectionEngine


# =============================================================================
# Model Tests
# =============================================================================

class TestModels:
    def test_canary_run_result_defaults(self):
        result = CanaryRunResult(suite_name="test")
        assert result.status == "running"
        assert result.drift_count == 0
        assert result.success_rate == 0.0
        assert result.has_critical_drift is False

    def test_canary_run_result_with_data(self):
        report = DriftReport(
            run_id="r1",
            prompt_name="p1",
            model="gpt-4o",
            provider="openai",
            drift_type=DriftType.OUTPUT_DRIFT,
            severity=DriftSeverity.HIGH,
            baseline_fingerprint=Fingerprint(prompt_name="p1", model="gpt-4o", provider="openai"),
            current_fingerprint=Fingerprint(prompt_name="p1", model="gpt-4o", provider="openai"),
            drift_score=0.85,
        )
        result = CanaryRunResult(
            suite_name="test",
            status="completed",
            total_prompts=10,
            successful_prompts=8,
            drift_reports=[report],
        )
        assert result.status == "completed"
        assert result.success_rate == 80.0
        assert result.drift_count == 1

    def test_canary_run_result_critical_drift(self):
        report = DriftReport(
            run_id="r1",
            prompt_name="p1",
            model="gpt-4o",
            provider="openai",
            drift_type=DriftType.OUTPUT_DRIFT,
            severity=DriftSeverity.CRITICAL,
            baseline_fingerprint=Fingerprint(prompt_name="p1", model="gpt-4o", provider="openai"),
            current_fingerprint=Fingerprint(prompt_name="p1", model="gpt-4o", provider="openai"),
        )
        result = CanaryRunResult(
            suite_name="test",
            drift_reports=[report],
        )
        assert result.has_critical_drift is True

    def test_prompt_result_success(self):
        result = PromptResult(
            prompt_name="test",
            prompt_text="Hello",
            model="gpt-4o",
            provider="openai",
            response="Hi",
        )
        assert result.success is True
        assert result.error is None

    def test_prompt_result_error(self):
        result = PromptResult(
            prompt_name="test",
            prompt_text="Hello",
            model="gpt-4o",
            provider="openai",
            response="",
            error="API failure",
        )
        assert result.success is False
        assert result.error == "API failure"

    def test_prompt_result_refusal(self):
        result = PromptResult(
            prompt_name="test",
            prompt_text="Hello",
            model="gpt-4o",
            provider="openai",
            response="I cannot answer that",
            refusal=True,
            refusal_reason="safety",
        )
        assert result.success is False
        assert result.refusal is True

    def test_prompt_config_severity_default(self):
        cfg = PromptConfig(name="test", prompt="Hi")
        assert cfg.severity == DriftSeverity.MEDIUM

    def test_provider_config_defaults(self):
        cfg = ProviderConfig(name="test", type="openai")
        assert cfg.timeout == 30.0
        assert cfg.max_retries == 3
        assert cfg.retry_delay == 1.0

    def test_drift_report_acknowledge(self):
        fp = Fingerprint(prompt_name="p1", model="gpt-4o", provider="openai")
        report = DriftReport(
            run_id="r1",
            prompt_name="p1",
            model="gpt-4o",
            provider="openai",
            drift_type=DriftType.OUTPUT_DRIFT,
            severity=DriftSeverity.HIGH,
            baseline_fingerprint=fp,
            current_fingerprint=fp,
        )
        now = datetime.now(UTC)
        report.acknowledged = True
        report.acknowledged_by = "admin"
        report.acknowledged_at = now
        assert report.acknowledged is True
        assert report.acknowledged_by == "admin"

    def test_fingerprint_defaults(self):
        fp = Fingerprint(prompt_name="p1", model="gpt-4o", provider="openai")
        assert fp.token_count == 0
        assert fp.latency_ms == 0.0
        assert fp.cost_usd == 0.0
        assert fp.refusal is False


# =============================================================================
# FingerprintingEngine Tests
# =============================================================================

class TestFingerprintingEngine:
    @pytest.fixture
    def engine(self):
        return FingerprintingEngine()

    def test_fingerprint_creation(self, engine):
        result = PromptResult(
            prompt_name="test-prompt",
            prompt_text="Say hello",
            model="gpt-4o",
            provider="openai",
            response="Hello world!",
            token_usage=TokenUsage(prompt_tokens=5, completion_tokens=10, total_tokens=15),
            latency=LatencyMetrics(total_time=0.5, total_time_ms=500.0),
            cost=CostMetrics(total_cost=0.001, cost_per_prompt_token=0.0001, cost_per_completion_token=0.00005),
        )

        import asyncio
        fp = asyncio.run(engine.fingerprint(result))
        assert fp.prompt_name == "test-prompt"
        assert fp.model == "gpt-4o"
        assert fp.provider == "openai"
        assert len(fp.sha256_hash) == 64
        assert fp.token_count == 15
        assert fp.latency_ms == 500.0
        assert fp.cost_usd == 0.001

    def test_sha256_consistency(self, engine):
        text = "Hello world!"
        hash1 = engine._compute_sha256(text)
        hash2 = engine._compute_sha256(text)
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_cosine_similarity_identical(self, engine):
        v = [1.0, 2.0, 3.0]
        sim = engine.cosine_similarity(v, v)
        assert abs(sim - 1.0) < 1e-10

    def test_cosine_similarity_orthogonal(self, engine):
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]
        sim = engine.cosine_similarity(v1, v2)
        assert abs(sim) < 1e-10

    def test_cosine_similarity_zero_vector(self, engine):
        v1 = [0.0, 0.0, 0.0]
        v2 = [1.0, 0.0, 0.0]
        sim = engine.cosine_similarity(v1, v2)
        assert sim == 0.0

    def test_refusal_detection(self, engine):
        result = PromptResult(
            prompt_name="test",
            prompt_text="Do something bad",
            model="gpt-4o",
            provider="openai",
            response="I cannot help with that request",
            refusal=True,
        )
        assert engine._is_refusal(result) is True

    def test_refusal_patterns(self, engine):
        texts = [
            "I'm sorry, I cannot do that",
            "I am sorry, but I can't help",
            "Sorry, but I can't answer",
            "I apologize, but I am unable to",
            "As an AI assistant, I don't",
        ]
        for text in texts:
            result = PromptResult(
                prompt_name="test",
                prompt_text="Hi",
                model="gpt-4o",
                provider="openai",
                response=text,
            )
            assert engine._is_refusal(result) is True, f"Should detect refusal in: {text}"

    def test_refusal_patterns_no_false_positive(self, engine):
        result = PromptResult(
            prompt_name="test",
            prompt_text="Hi",
            model="gpt-4o",
            provider="openai",
            response="Sure, I can help you with that!",
        )
        assert engine._is_refusal(result) is False

    def test_json_schema_extraction(self, engine):
        obj = {"name": "John", "age": 30, "items": [1, 2, 3]}
        schema = engine._extract_json_schema(obj)
        assert schema["type"] == "dict"
        assert "properties" in schema
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["age"]["type"] == "integer"

    def test_json_schema_hash(self, engine):
        text = 'Here is the JSON: {"name": "John", "age": 30}'
        hash_val = engine._compute_json_schema_hash(text)
        assert hash_val is not None
        assert len(hash_val) == 64

    def test_json_schema_hash_no_json(self, engine):
        text = "This is plain text without JSON"
        hash_val = engine._compute_json_schema_hash(text)
        assert hash_val is None


# =============================================================================
# DriftDetectionEngine Tests
# =============================================================================

class TestDriftDetection:
    @pytest.fixture
    def engine(self):
        return DriftDetectionEngine(
            similarity_threshold=0.85,
            drift_threshold=0.1,
            latency_threshold_pct=50.0,
            cost_threshold_pct=50.0,
            token_threshold_pct=30.0,
        )

    @pytest.mark.asyncio
    async def test_output_drift(self, engine):
        baseline = Fingerprint(
            prompt_name="test", model="gpt-4o", provider="openai",
            sha256_hash="a" * 64,
        )
        current = Fingerprint(
            prompt_name="test", model="gpt-4o", provider="openai",
            sha256_hash="b" * 64,
        )
        reports = await engine.detect(baseline, current)
        drift_types = [r.drift_type for r in reports]
        assert DriftType.OUTPUT_DRIFT in drift_types

    @pytest.mark.asyncio
    async def test_no_drift_identical(self, engine):
        fp = Fingerprint(
            prompt_name="test", model="gpt-4o", provider="openai",
            sha256_hash="a" * 64,
            latency_ms=100.0, cost_usd=0.001, token_count=50,
        )
        reports = await engine.detect(fp, fp)
        assert len(reports) == 0

    @pytest.mark.asyncio
    async def test_latency_drift(self, engine):
        baseline = Fingerprint(
            prompt_name="test", model="gpt-4o", provider="openai",
            sha256_hash="a" * 64, latency_ms=100.0, cost_usd=0.001, token_count=50,
        )
        current = Fingerprint(
            prompt_name="test", model="gpt-4o", provider="openai",
            sha256_hash="a" * 64, latency_ms=300.0, cost_usd=0.001, token_count=50,
        )
        reports = await engine.detect(baseline, current)
        drift_types = [r.drift_type for r in reports]
        assert DriftType.LATENCY_SPIKE in drift_types

    @pytest.mark.asyncio
    async def test_cost_drift(self, engine):
        baseline = Fingerprint(
            prompt_name="test", model="gpt-4o", provider="openai",
            sha256_hash="a" * 64, latency_ms=100.0, cost_usd=0.001, token_count=50,
        )
        current = Fingerprint(
            prompt_name="test", model="gpt-4o", provider="openai",
            sha256_hash="a" * 64, latency_ms=100.0, cost_usd=0.005, token_count=50,
        )
        reports = await engine.detect(baseline, current)
        drift_types = [r.drift_type for r in reports]
        assert DriftType.COST_SPIKE in drift_types

    @pytest.mark.asyncio
    async def test_refusal_drift(self, engine):
        baseline = Fingerprint(
            prompt_name="test", model="gpt-4o", provider="openai",
            sha256_hash="a" * 64, latency_ms=100.0, cost_usd=0.001, token_count=50,
            refusal=False,
        )
        current = Fingerprint(
            prompt_name="test", model="gpt-4o", provider="openai",
            sha256_hash="a" * 64, latency_ms=100.0, cost_usd=0.001, token_count=50,
            refusal=True,
        )
        reports = await engine.detect(baseline, current)
        drift_types = [r.drift_type for r in reports]
        assert DriftType.REFUSAL_INCREASE in drift_types

    @pytest.mark.asyncio
    async def test_tool_calling_drift(self, engine):
        baseline = Fingerprint(
            prompt_name="test", model="gpt-4o", provider="openai",
            sha256_hash="a" * 64, latency_ms=100.0, cost_usd=0.001, token_count=50,
            tool_call_count=0,
        )
        current = Fingerprint(
            prompt_name="test", model="gpt-4o", provider="openai",
            sha256_hash="a" * 64, latency_ms=100.0, cost_usd=0.001, token_count=50,
            tool_call_count=3,
        )
        reports = await engine.detect(baseline, current)
        drift_types = [r.drift_type for r in reports]
        assert DriftType.TOOL_FAILURE in drift_types

    @pytest.mark.asyncio
    async def test_drift_report_structure(self, engine):
        baseline = Fingerprint(
            prompt_name="test", model="gpt-4o", provider="openai",
            sha256_hash="a" * 64, latency_ms=100.0, cost_usd=0.001, token_count=50,
        )
        current = Fingerprint(
            prompt_name="test", model="gpt-4o", provider="openai",
            sha256_hash="b" * 64, latency_ms=100.0, cost_usd=0.001, token_count=50,
        )
        reports = await engine.detect(baseline, current)
        assert len(reports) >= 1
        report = reports[0]
        assert report.run_id == current.run_id
        assert report.prompt_name == current.prompt_name
        assert report.model == current.model
        assert report.provider == current.provider
        assert isinstance(report.drift_type, DriftType)
        assert isinstance(report.severity, DriftSeverity)
        assert report.baseline_fingerprint is baseline
        assert report.current_fingerprint is current
        assert 0 <= report.drift_score <= 1.0
        assert isinstance(report.message, str)

    def test_drift_score_calculation(self, engine):
        score, pct = engine._calculate_drift_score(100.0, 150.0, 0.5)
        assert score > 0
        assert pct == 0.5

    def test_drift_score_zero_baseline(self, engine):
        score, pct = engine._calculate_drift_score(0.0, 100.0, 0.1)
        assert score == 1.0
        assert pct == float("inf")

    def test_drift_score_both_zero(self, engine):
        score, pct = engine._calculate_drift_score(0.0, 0.0, 0.1)
        assert score == 0.0
        assert pct == 0.0

    def test_severity_classification(self, engine):
        assert engine._classify_severity(0.95, 0.3) == DriftSeverity.CRITICAL
        assert engine._classify_severity(0.8, 0.3) == DriftSeverity.HIGH
        assert engine._classify_severity(0.5, 0.3) == DriftSeverity.MEDIUM
        assert engine._classify_severity(0.2, 0.1) == DriftSeverity.LOW


# =============================================================================
# CanaryEngine Tests
# =============================================================================

def _make_prompt_config(name: str = "test-prompt") -> PromptConfig:
    return PromptConfig(
        name=name,
        prompt="Say hello",
        model="gpt-4o",
        category="general",
        severity="high",
        evaluators=["json"],
        max_tokens=100,
        temperature=0.5,
    )


def _make_provider_config(name: str = "openai") -> ProviderConfig:
    return ProviderConfig(
        name=name,
        type="openai",
        api_key="sk-test",
        default_model="gpt-4o",
    )


def _make_suite_config(name: str = "production") -> TestSuiteConfig:
    return TestSuiteConfig(
        name=name,
        enabled=True,
        prompts=[_make_prompt_config()],
        schedule="*/5 * * * *",
    )


def _make_minimal_config() -> ModelCanaryConfig:
    return ModelCanaryConfig(
        project_name="test",
        providers=[_make_provider_config()],
        test_suites=[_make_suite_config()],
        storage=StorageConfig(backend="sqlite", connection_string="sqlite+aiosqlite:///test.db"),
        alerting=AlertConfig(enabled=True, channels=["log"], min_severity="low"),
    )


def _make_prompt_result(success: bool = True) -> PromptResult:
    return PromptResult(
        prompt_name="test-prompt",
        prompt_text="Say hello",
        model="gpt-4o",
        provider="openai",
        response="Hello there!" if success else "",
        success=success,
        error=None if success else "API error",
        latency=LatencyMetrics(total_time=0.5, total_time_ms=500.0),
        token_usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        cost=CostMetrics(total_cost=0.001, cost_per_prompt_token=0.0001, cost_per_completion_token=0.00005),
    )


def _make_fingerprint() -> Fingerprint:
    return Fingerprint(
        prompt_name="test-prompt",
        model="gpt-4o",
        provider="openai",
        sha256_hash="abc123",
    )


def _make_drift_report() -> DriftReport:
    return DriftReport(
        run_id="test-run",
        prompt_name="test-prompt",
        model="gpt-4o",
        provider="openai",
        drift_type=DriftType.OUTPUT_DRIFT,
        severity=DriftSeverity.HIGH,
        baseline_fingerprint=_make_fingerprint(),
        current_fingerprint=_make_fingerprint(),
        drift_score=0.85,
        message="Output drift detected",
    )


def _make_run_result(suite_name: str = "test-suite") -> CanaryRunResult:
    return CanaryRunResult(
        id="test-run-id",
        suite_name=suite_name,
        models_tested=["gpt-4o"],
        providers_tested=["openai"],
        status="completed",
        total_cost=0.001,
        duration_ms=500.0,
        successful_prompts=1,
        total_prompts=1,
        drift_count=0,
    )


class TestCanaryEngine:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.config = _make_minimal_config()

        self.mock_provider = MagicMock()
        self.mock_provider.name = "openai"
        self.mock_provider.config = _make_provider_config()
        self.mock_provider.complete = AsyncMock(return_value=_make_prompt_result())
        self.mock_provider.close = AsyncMock()

        self.mock_storage = MagicMock()
        self.mock_storage.initialize = AsyncMock()
        self.mock_storage.close = AsyncMock()
        self.mock_storage.save_run_result = AsyncMock()
        self.mock_storage.save_fingerprint = AsyncMock()
        self.mock_storage.save_drift_report = AsyncMock()
        self.mock_storage.get_latest_fingerprint = AsyncMock(return_value=_make_fingerprint())
        self.mock_storage.get_drift_reports = AsyncMock(return_value=[_make_drift_report()])
        self.mock_storage.get_run_result = AsyncMock(return_value=_make_run_result())
        self.mock_storage.get_fingerprint_history = AsyncMock(return_value=[_make_fingerprint()])

        self.mock_fingerprinter = MagicMock()
        self.mock_fingerprinter.fingerprint = AsyncMock(return_value=_make_fingerprint())

        self.mock_drift_detector = MagicMock()
        self.mock_drift_detector.detect = AsyncMock(return_value=[_make_drift_report()])

        self.mock_alerter = MagicMock()
        self.mock_alerter.send_alert = AsyncMock()

        patchers = [
            patch("model_canary.engine.register_providers", return_value=None),
            patch("model_canary.engine.create_storage", return_value=self.mock_storage),
            patch("model_canary.engine.create_provider", return_value=self.mock_provider),
            patch("model_canary.engine.create_alerter", return_value=self.mock_alerter),
            patch("model_canary.engine.FingerprintingEngine", return_value=self.mock_fingerprinter),
            patch("model_canary.engine.DriftDetectionEngine", return_value=self.mock_drift_detector),
        ]
        for p in patchers:
            p.start()
        self._patchers = patchers
        yield
        for p in patchers:
            p.stop()

    def test_init_with_config(self):
        from model_canary.engine import CanaryEngine
        engine = CanaryEngine(config=self.config)
        assert engine.config is self.config
        assert engine._initialized is False

    def test_init_with_path(self, tmp_path):
        from model_canary.engine import CanaryEngine
        config_path = tmp_path / "model-canary.yml"
        config_path.write_text("""version: "1"\nproject_name: path-test\nproviders:\n  - name: openai\n    type: openai\n    api_key: sk-test\ntest_suites: []\nstorage:\n  backend: sqlite\n  connection_string: sqlite+aiosqlite:///test.db\nalerting:\n  enabled: true\n  channels:\n    - log\n  min_severity: low\n""")
        with patch("model_canary.engine.load_config") as mock_load:
            mock_load.return_value = self.config
            engine = CanaryEngine(config_path=str(config_path))
            assert engine.config is self.config

    @pytest.mark.asyncio
    async def test_initialize(self):
        from model_canary.engine import CanaryEngine
        engine = CanaryEngine(config=self.config)
        assert engine._initialized is False
        await engine.initialize()
        assert engine._initialized is True
        self.mock_storage.initialize.assert_called_once()
        assert "openai" in engine._providers
        assert "log" in engine._alerters

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self):
        from model_canary.engine import CanaryEngine
        engine = CanaryEngine(config=self.config)
        await engine.initialize()
        await engine.initialize()
        self.mock_storage.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_suite_success(self):
        from model_canary.engine import CanaryEngine
        engine = CanaryEngine(config=self.config)
        result = await engine.run_suite("production")
        assert result.status == "completed"
        assert result.suite_name == "production"
        assert result.total_prompts > 0
        self.mock_storage.save_run_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_suite_not_found(self):
        from model_canary.engine import CanaryEngine
        from model_canary.core.exceptions import ConfigError
        engine = CanaryEngine(config=self.config)
        with pytest.raises(ConfigError, match="not found"):
            await engine.run_suite("nonexistent")

    @pytest.mark.asyncio
    async def test_run_suite_provider_error(self):
        from model_canary.engine import CanaryEngine
        self.mock_provider.complete = AsyncMock(side_effect=Exception("Provider failure"))
        engine = CanaryEngine(config=self.config)
        result = await engine.run_suite("production")
        assert result.status == "completed"
        assert result.failed_prompts > 0

    @pytest.mark.asyncio
    async def test_run_all_suites(self):
        from model_canary.engine import CanaryEngine
        engine = CanaryEngine(config=self.config)
        results = await engine.run_all_suites()
        assert len(results) == 1
        assert results[0].suite_name == "production"

    @pytest.mark.asyncio
    async def test_run_all_suites_all_disabled(self):
        from model_canary.engine import CanaryEngine
        self.config.test_suites[0].enabled = False
        engine = CanaryEngine(config=self.config)
        results = await engine.run_all_suites()
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_run_prompt(self):
        from model_canary.engine import CanaryEngine
        engine = CanaryEngine(config=self.config)
        prompt_cfg = _make_prompt_config()
        result = await engine.run_prompt(prompt_cfg, "openai")
        assert result.status == "completed"
        assert result.suite_name == "adhoc"
        self.mock_storage.save_run_result.assert_called()

    @pytest.mark.asyncio
    async def test_run_prompt_new_provider(self):
        from model_canary.engine import CanaryEngine
        new_provider = MagicMock()
        new_provider.name = "anthropic"
        new_provider.complete = AsyncMock(return_value=_make_prompt_result())
        new_provider.close = AsyncMock()
        with patch("model_canary.engine.create_provider", return_value=new_provider) as mock_create:
            engine = CanaryEngine(config=self.config)
            await engine.initialize()
            prompt_cfg = _make_prompt_config()
            result = await engine.run_prompt(prompt_cfg, "anthropic")
            assert result.status == "completed"
            assert "anthropic" in engine._providers

    @pytest.mark.asyncio
    async def test_run_prompt_error(self):
        from model_canary.engine import CanaryEngine
        self.mock_provider.complete = AsyncMock(side_effect=Exception("Provider failure"))
        engine = CanaryEngine(config=self.config)
        prompt_cfg = _make_prompt_config()
        result = await engine.run_prompt(prompt_cfg, "openai")
        assert result.status == "failed"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_benchmark(self):
        from model_canary.engine import CanaryEngine
        engine = CanaryEngine(config=self.config)
        results = await engine.benchmark("Hello", ["gpt-4o"], ["openai"])
        assert "openai/gpt-4o" in results

    @pytest.mark.asyncio
    async def test_benchmark_error(self):
        from model_canary.engine import CanaryEngine
        self.mock_provider.complete = AsyncMock(side_effect=Exception("Benchmark fail"))
        engine = CanaryEngine(config=self.config)
        results = await engine.benchmark("Hello", ["gpt-4o"], ["openai"])
        assert "error" in results["openai/gpt-4o"]

    @pytest.mark.asyncio
    async def test_compare(self):
        from model_canary.engine import CanaryEngine
        engine = CanaryEngine(config=self.config)
        result = await engine.compare("test-prompt", "openai", "openai")
        assert "hash_match" in result

    @pytest.mark.asyncio
    async def test_compare_missing_fingerprints(self):
        from model_canary.engine import CanaryEngine
        self.mock_storage.get_latest_fingerprint = AsyncMock(return_value=None)
        engine = CanaryEngine(config=self.config)
        result = await engine.compare("test-prompt", "openai", "anthropic")
        assert "error" in result
        assert "Fingerprints not found" in result["error"]

    @pytest.mark.asyncio
    async def test_close(self):
        from model_canary.engine import CanaryEngine
        engine = CanaryEngine(config=self.config)
        await engine.initialize()
        await engine.close()
        assert engine._initialized is False
        self.mock_provider.close.assert_called()
        self.mock_storage.close.assert_called()

    def test_should_alert_above_threshold(self):
        from model_canary.engine import CanaryEngine
        engine = CanaryEngine(config=self.config)
        report = _make_drift_report()
        alert_cfg = AlertConfig(enabled=True, channels=["log"], min_severity="low")
        assert engine._should_alert(report, alert_cfg) is True

    def test_should_alert_below_threshold(self):
        from model_canary.engine import CanaryEngine
        engine = CanaryEngine(config=self.config)
        report = _make_drift_report()
        report.severity = DriftSeverity.LOW
        alert_cfg = AlertConfig(enabled=True, channels=["log"], min_severity="high")
        assert engine._should_alert(report, alert_cfg) is False

    def test_should_alert_equal_threshold(self):
        from model_canary.engine import CanaryEngine
        engine = CanaryEngine(config=self.config)
        report = _make_drift_report()
        report.severity = DriftSeverity.HIGH
        alert_cfg = AlertConfig(enabled=True, channels=["log"], min_severity="high")
        assert engine._should_alert(report, alert_cfg) is True

    @pytest.mark.asyncio
    async def test_get_evaluator_cached(self):
        from model_canary.engine import CanaryEngine
        engine = CanaryEngine(config=self.config)
        mock_eval = MagicMock()
        engine._evaluators["json"] = mock_eval
        result = await engine._get_evaluator("json")
        assert result is mock_eval

    @pytest.mark.asyncio
    async def test_get_evaluator_new(self):
        from model_canary.engine import CanaryEngine
        engine = CanaryEngine(config=self.config)
        mock_eval = MagicMock()
        with patch("model_canary.engine.load_evaluator", return_value=mock_eval) as mock_load:
            result = await engine._get_evaluator("json")
            assert result is mock_eval
            assert "json" in engine._evaluators
            mock_load.assert_called_once_with("json")

    @pytest.mark.asyncio
    async def test_get_evaluator_error(self):
        from model_canary.engine import CanaryEngine
        engine = CanaryEngine(config=self.config)
        with patch("model_canary.engine.load_evaluator", side_effect=Exception("load error")):
            result = await engine._get_evaluator("nonexistent")
            assert result is None

    @pytest.mark.asyncio
    async def test_send_alerts_disabled(self):
        from model_canary.engine import CanaryEngine
        engine = CanaryEngine(config=self.config)
        self.config.alerting.enabled = False
        run_result = _make_run_result()
        run_result.drift_reports = [_make_drift_report()]
        await engine._send_alerts(run_result)
        self.mock_alerter.send_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_alerts_enabled(self):
        from model_canary.engine import CanaryEngine
        engine = CanaryEngine(config=self.config)
        await engine.initialize()
        self.config.alerting.enabled = True
        self.config.alerting.max_alerts_per_run = 10
        run_result = _make_run_result()
        run_result.drift_reports = [_make_drift_report()]
        await engine._send_alerts(run_result)
        self.mock_alerter.send_alert.assert_called()
        assert run_result.alerts_sent > 0

    @pytest.mark.asyncio
    async def test_send_alerts_alerter_error(self):
        from model_canary.engine import CanaryEngine
        engine = CanaryEngine(config=self.config)
        self.config.alerting.enabled = True
        self.mock_alerter.send_alert = AsyncMock(side_effect=Exception("Alert failed"))
        run_result = _make_run_result()
        run_result.drift_reports = [_make_drift_report()]
        await engine._send_alerts(run_result)
        assert run_result.alerts_sent == 0

    @pytest.mark.asyncio
    async def test_init_storage_error(self):
        from model_canary.engine import CanaryEngine
        from model_canary.core.exceptions import StorageError
        self.mock_storage.initialize = AsyncMock(side_effect=Exception("Storage init failed"))
        engine = CanaryEngine(config=self.config)
        with pytest.raises(StorageError, match="Failed to initialize storage"):
            await engine.initialize()

    @pytest.mark.asyncio
    async def test_init_provider_no_providers(self):
        from model_canary.engine import CanaryEngine
        self.config.providers = []
        engine = CanaryEngine(config=self.config)
        await engine.initialize()
        assert len(engine._providers) == 0

    @pytest.mark.asyncio
    async def test_benchmark_no_providers(self):
        from model_canary.engine import CanaryEngine
        engine = CanaryEngine(config=self.config)
        await engine.initialize()
        results = await engine.benchmark("Hello", ["gpt-4o"], ["nonexistent"])
        assert len(results) == 0
