"""Basic import tests."""
from model_canary import __version__
from model_canary.core.models import (
    ModelCanaryConfig, ProviderConfig, PromptConfig, Fingerprint, DriftReport,
    CanaryRunResult, DriftSeverity, DriftType, TokenUsage, LatencyMetrics, CostMetrics,
)
from model_canary.core.exceptions import (
    ModelCanaryError, ProviderError, ProviderAuthError, ConfigError,
)
from model_canary.core.interfaces import (
    Provider, Evaluator, Fingerprinter, DriftDetector, StorageBackend, Alerter, Plugin,
)
from model_canary.fingerprinting.engine import FingerprintingEngine
from model_canary.drift.engine import DriftDetectionEngine
from model_canary.config.loader import detect_config_files, load_config


def test_version():
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_drift_severity_values():
    assert DriftSeverity.LOW.value == "low"
    assert DriftSeverity.MEDIUM.value == "medium"
    assert DriftSeverity.HIGH.value == "high"
    assert DriftSeverity.CRITICAL.value == "critical"


def test_drift_type_values():
    assert DriftType.OUTPUT_DRIFT.value == "output_drift"
    assert DriftType.SEMANTIC_DRIFT.value == "semantic_drift"
    assert DriftType.LATENCY_SPIKE.value == "latency_spike"
    assert DriftType.COST_SPIKE.value == "cost_spike"
    assert DriftType.REFUSAL_INCREASE.value == "refusal_increase"


def test_provider_config():
    cfg = ProviderConfig(name="test", type="openai", api_key="sk-xxx")
    assert cfg.name == "test"
    assert cfg.provider_type == "openai"
    assert cfg.api_key == "sk-xxx"


def test_prompt_config():
    cfg = PromptConfig(name="test-prompt", prompt="Hello, world!")
    assert cfg.name == "test-prompt"
    assert cfg.prompt == "Hello, world!"
    assert cfg.severity == DriftSeverity.MEDIUM


def test_token_usage():
    usage = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    assert usage.prompt_tokens == 10
    assert usage.completion_tokens == 20
    assert usage.total_tokens == 30


def test_latency_metrics():
    metrics = LatencyMetrics(total_time=1.5, total_time_ms=1500.0)
    assert metrics.total_time == 1.5
    assert metrics.total_time_ms == 1500.0


def test_fingerprint_defaults():
    fp = Fingerprint(prompt_name="test", model="gpt-4", provider="openai")
    assert fp.prompt_name == "test"
    assert fp.model == "gpt-4"
    assert fp.provider == "openai"
    assert fp.refusal == False
    assert fp.tool_call_count == 0


def test_drift_report():
    baseline = Fingerprint(prompt_name="test", model="gpt-4", provider="openai")
    current = Fingerprint(prompt_name="test", model="gpt-4", provider="openai")
    report = DriftReport(
        run_id="run-1",
        prompt_name="test",
        model="gpt-4",
        provider="openai",
        drift_type=DriftType.OUTPUT_DRIFT,
        severity=DriftSeverity.HIGH,
        baseline_fingerprint=baseline,
        current_fingerprint=current,
        drift_score=0.85,
        message="Test drift",
    )
    assert report.drift_type == DriftType.OUTPUT_DRIFT
    assert report.severity == DriftSeverity.HIGH
    assert report.drift_score == 0.85


def test_canary_run_result():
    result = CanaryRunResult(suite_name="test-suite")
    assert result.suite_name == "test-suite"
    assert result.status == "running"
    assert result.total_prompts == 0
    assert result.drift_count == 0
    assert result.success_rate == 0.0


def test_model_canary_config():
    config = ModelCanaryConfig()
    assert config.version == "1"
    assert config.project_name == "model-canary"
    assert config.storage.backend == "sqlite"


def test_fingerprinting_engine():
    engine = FingerprintingEngine()
    from model_canary.core.models import PromptResult
    result = PromptResult(
        prompt_name="test",
        prompt_text="Hello",
        model="gpt-4",
        provider="openai",
        response="Hello, world!",
    )
    import asyncio
    fp = asyncio.run(engine.fingerprint(result))
    assert fp.prompt_name == "test"
    assert fp.model == "gpt-4"
    assert fp.provider == "openai"
    assert len(fp.sha256_hash) == 64


def test_drift_detection():
    engine = DriftDetectionEngine()
    from model_canary.core.models import Fingerprint
    baseline = Fingerprint(
        prompt_name="test", model="gpt-4", provider="openai",
        sha256_hash="a" * 64, latency_ms=100.0, cost_usd=0.01,
    )
    current = Fingerprint(
        prompt_name="test", model="gpt-4", provider="openai",
        sha256_hash="b" * 64, latency_ms=200.0, cost_usd=0.02,
    )
    import asyncio
    reports = asyncio.run(engine.detect(baseline, current))
    assert len(reports) >= 1
    output_drifts = [r for r in reports if r.drift_type == DriftType.OUTPUT_DRIFT]
    latency_drifts = [r for r in reports if r.drift_type == DriftType.LATENCY_SPIKE]
    cost_drifts = [r for r in reports if r.drift_type == DriftType.COST_SPIKE]
    assert len(output_drifts) >= 1
    assert len(latency_drifts) >= 1
    assert len(cost_drifts) >= 1


def test_config_detection():
    import tempfile, os
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmp:
        orig = Path.cwd()
        os.chdir(tmp)
        try:
            files = detect_config_files()
            assert files == []
            Path("model-canary.yml").write_text("version: '1'\n")
            files = detect_config_files()
            assert len(files) >= 1
        finally:
            os.chdir(orig)


def test_exceptions():
    err = ModelCanaryError("test error")
    assert str(err) == "test error"
    auth_err = ProviderAuthError("auth failed")
    assert isinstance(auth_err, ProviderError)
    assert isinstance(auth_err, ModelCanaryError)
    config_err = ConfigError("bad config")
    assert isinstance(config_err, ModelCanaryError)
