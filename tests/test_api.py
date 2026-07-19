from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure litellm mock is available for import
if "litellm" not in sys.modules:
    _litellm_mock = MagicMock()
    _litellm_mock.acompletion = AsyncMock()
    _litellm_mock.amodel_list = AsyncMock()
    sys.modules["litellm"] = _litellm_mock

from model_canary.api.app import create_app
from model_canary.core.models import (
    CanaryRunResult,
    DriftReport,
    DriftSeverity,
    DriftType,
    Fingerprint,
)


def _make_drift() -> DriftReport:
    return DriftReport(
        id="test-drift-1",
        run_id="test-run-1",
        prompt_name="test-prompt",
        model="gpt-4o",
        provider="openai",
        drift_type=DriftType.OUTPUT_DRIFT,
        severity=DriftSeverity.HIGH,
        baseline_fingerprint=Fingerprint(
            prompt_name="test-prompt", model="gpt-4o", provider="openai"
        ),
        current_fingerprint=Fingerprint(
            prompt_name="test-prompt", model="gpt-4o", provider="openai"
        ),
        drift_score=0.85,
        message="Output drift detected",
    )


def _make_run_result() -> CanaryRunResult:
    return CanaryRunResult(
        suite_name="test-suite",
        models_tested=["gpt-4o"],
        providers_tested=["openai"],
        status="completed",
        total_cost=0.001,
        duration_ms=500.0,
        successful_prompts=1,
        total_prompts=1,
        drift_count=1,
    )


def _make_mock_engine():
    engine = MagicMock()
    engine.initialize = AsyncMock()
    engine.close = AsyncMock()
    engine._storage = MagicMock()
    engine._config = MagicMock()
    engine._providers = {"openai": MagicMock()}

    suite = MagicMock()
    suite.name = "production"
    suite.enabled = True
    p = MagicMock()
    p.name = "test-prompt"
    p.description = "desc"
    p.category = "json"
    p.severity = DriftSeverity.HIGH
    p.evaluators = ["json"]
    suite.prompts = [p]

    engine._config.test_suites = [suite]
    engine._storage.get_drift_reports = AsyncMock(return_value=[_make_drift()])
    engine._storage.get_run_result = AsyncMock(return_value=_make_run_result())
    engine._storage.get_fingerprint_history = AsyncMock(return_value=[
        Fingerprint(prompt_name="test", model="gpt-4o", provider="openai")
    ])
    engine.run_suite = AsyncMock(return_value=_make_run_result())
    engine.run_all_suites = AsyncMock(return_value=[_make_run_result()])
    engine.run_prompt = AsyncMock(return_value=_make_run_result())
    engine.benchmark = AsyncMock(return_value={"openai/gpt-4o": {"latency_ms": 500}})
    engine.compare = AsyncMock(return_value={"hash_match": True})

    return engine


class TestAPI:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.mock_engine = _make_mock_engine()
        self.app = create_app(config_path="/fake/config.yml", _engine=self.mock_engine)
        self.client = TestClient(self.app)

    # ===== Health =====

    def test_health(self):
        resp = self.client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data

    # ===== Runs =====

    def test_list_runs(self):
        resp = self.client.get("/api/v1/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert "runs" in data
        assert "total" in data

    def test_get_run_found(self):
        resp = self.client.get("/api/v1/runs/test-run-1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["suite_name"] == "test-suite"

    def test_get_run_not_found(self):
        engine = self.app.state.engine
        # Override mock to return None
        with patch.object(engine, "_storage") as mock_storage:
            mock_storage.get_run_result = AsyncMock(return_value=None)
            resp = self.client.get("/api/v1/runs/nonexistent")
            assert resp.status_code == 404

    # ===== Drifts =====

    def test_list_drifts(self):
        resp = self.client.get("/api/v1/drifts")
        assert resp.status_code == 200
        data = resp.json()
        assert "drifts" in data
        assert data["total"] > 0

    def test_list_drifts_with_filters(self):
        resp = self.client.get("/api/v1/drifts?prompt_name=test&model=gpt-4o&severity=high&limit=10&offset=0")
        assert resp.status_code == 200

    def test_get_drift_found(self):
        resp = self.client.get("/api/v1/drifts/test-drift-1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["drift_type"] == "output_drift"

    def test_get_drift_not_found(self):
        resp = self.client.get("/api/v1/drifts/nonexistent")
        assert resp.status_code == 404

    # ===== Fingerprints =====

    def test_list_fingerprints(self):
        resp = self.client.get("/api/v1/fingerprints?prompt_name=test")
        assert resp.status_code == 200
        data = resp.json()
        assert "fingerprints" in data

    # ===== Execution =====

    def test_execute_run_all(self):
        resp = self.client.post("/api/v1/run")
        assert resp.status_code == 200

    def test_execute_run_suite(self):
        resp = self.client.post("/api/v1/run?suite_name=production")
        assert resp.status_code == 200

    def test_execute_prompt(self):
        resp = self.client.post("/api/v1/run/prompt?prompt=Hello&provider=openai")
        assert resp.status_code == 200

    # ===== Benchmark =====

    def test_benchmark(self):
        resp = self.client.post("/api/v1/benchmark?prompt=Hello&models=gpt-4o")
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data

    # ===== Compare =====

    def test_compare(self):
        resp = self.client.get("/api/v1/compare?prompt_name=test&provider_a=openai&provider_b=anthropic")
        assert resp.status_code == 200

    # ===== Stats =====

    def test_get_stats(self):
        resp = self.client.get("/api/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_drifts" in data

    # ===== Providers =====

    def test_list_providers(self):
        resp = self.client.get("/api/v1/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert "openai" in data["providers"]

    # ===== Prompts =====

    def test_list_prompts(self):
        resp = self.client.get("/api/v1/prompts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0
        assert len(data["prompts"]) > 0

    # ===== Dashboard =====

    def test_dashboard_html(self):
        resp = self.client.get("/dashboard")
        assert resp.status_code == 200
        assert "Model Canary Dashboard" in resp.text

    # ===== OpenAPI =====

    def test_docs(self):
        resp = self.client.get("/docs")
        assert resp.status_code == 200

    def test_openapi_json(self):
        resp = self.client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["info"]["title"] == "Model Canary API"
