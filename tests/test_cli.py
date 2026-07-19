from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, ANY

import pytest
from typer.testing import CliRunner

from model_canary.cli import app
from model_canary.core.models import (
    CanaryRunResult,
    DriftReport,
    DriftSeverity,
    DriftType,
    Fingerprint,
    LatencyMetrics,
    TokenUsage,
    CostMetrics,
    PromptResult,
)

runner = CliRunner()


def _make_run_result(suite_name: str = "test-suite", status: str = "completed") -> CanaryRunResult:
    return CanaryRunResult(
        suite_name=suite_name,
        models_tested=["gpt-4o"],
        providers_tested=["openai"],
        status=status,
        total_cost=0.001,
        duration_ms=500.0,
        successful_prompts=1,
        total_prompts=1,
        drift_count=0,
    )


# =============================================================================
# Basic CLI Tests
# =============================================================================

class TestBasicCLI:
    def test_version(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "Model Canary" in result.stdout

    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Detect AI Model Drift" in result.stdout

    def test_no_command_shows_help(self):
        result = runner.invoke(app, [])
        assert result.exit_code in (0, 2)


# =============================================================================
# Init Command
# =============================================================================

class TestInitCommand:
    def test_init(self, tmp_path: Path):
        target = str(tmp_path / "myproject")
        result = runner.invoke(app, ["init", target])
        assert result.exit_code == 0
        assert (tmp_path / "myproject" / "model-canary.yml").exists()
        assert (tmp_path / "myproject" / "prompts" / "coding").is_dir()
        assert (tmp_path / "myproject" / "prompts" / "json").is_dir()

    def test_init_existing_no_force(self, tmp_path: Path):
        target = str(tmp_path / "existing")
        runner.invoke(app, ["init", target])
        result = runner.invoke(app, ["init", target])
        assert result.exit_code == 1
        assert "already exists" in result.stdout

    def test_init_existing_with_force(self, tmp_path: Path):
        target = str(tmp_path / "existing")
        runner.invoke(app, ["init", target])
        result = runner.invoke(app, ["init", target, "--force"])
        assert result.exit_code == 0


# =============================================================================
# Config Command
# =============================================================================

class TestConfigCommand:
    @pytest.fixture(autouse=True)
    def setup_method(self, tmp_path: Path):
        self.config_path = tmp_path / "model-canary.yml"
        self.config_path.write_text("""
version: "1"
project_name: test
providers:
  - name: test-provider
    type: openai
    api_key: sk-test
    default_model: gpt-4o
test_suites: []
storage:
  backend: sqlite
  connection_string: sqlite+aiosqlite:///test.db
alerting:
  enabled: true
  channels:
    - log
  min_severity: medium
""")

    def test_config_show(self):
        result = runner.invoke(app, ["config", "--show", "-c", str(self.config_path)])
        assert result.exit_code == 0

    def test_config_validate(self):
        result = runner.invoke(app, ["config", "--validate", "-c", str(self.config_path)])
        assert result.exit_code == 0

    def test_config_list_files(self):
        result = runner.invoke(app, ["config", "-c", str(self.config_path)])
        assert result.exit_code == 0

    def test_config_no_files(self, tmp_path: Path):
        result = runner.invoke(app, ["config", "-c", str(tmp_path / "nonexistent.yml")])
        assert result.exit_code == 0


# =============================================================================
# Run Command
# =============================================================================

class TestRunCommand:
    @pytest.fixture(autouse=True)
    def setup_method(self, tmp_path: Path):
        self.config_path = tmp_path / "model-canary.yml"
        self.config_path.write_text("""
version: "1"
project_name: test
providers:
  - name: openai
    type: openai
    api_key: sk-test
    default_model: gpt-4o
test_suites:
  - name: production
    enabled: true
    prompts:
      - name: test-prompt
        prompt: "Say hello"
        model: gpt-4o
        evaluators:
          - json
storage:
  backend: sqlite
  connection_string: sqlite+aiosqlite:///test.db
alerting:
  enabled: true
  channels:
    - log
  min_severity: low
""")

    def test_run_suite(self):
        mock_engine = MagicMock()
        mock_engine.run_suite = AsyncMock(return_value=_make_run_result())
        mock_engine.run_all_suites = AsyncMock(return_value=[_make_run_result()])

        with patch("model_canary.cli.CanaryEngine", return_value=mock_engine):
            result = runner.invoke(app, ["run", "--suite", "production", "-c", str(self.config_path)])
            assert result.exit_code == 0

    def test_run_single_prompt(self):
        mock_engine = MagicMock()
        mock_result = _make_run_result()
        mock_engine.run_prompt = AsyncMock(return_value=mock_result)

        with patch("model_canary.cli.CanaryEngine", return_value=mock_engine):
            result = runner.invoke(app, ["run", "--prompt", "Say hello", "--provider", "openai", "-c", str(self.config_path)])
            assert result.exit_code == 0

    def test_run_all_suites(self):
        mock_engine = MagicMock()
        mock_engine.run_all_suites = AsyncMock(return_value=[_make_run_result()])

        with patch("model_canary.cli.CanaryEngine", return_value=mock_engine):
            result = runner.invoke(app, ["run", "-c", str(self.config_path)])
            assert result.exit_code == 0


# =============================================================================
# List Command
# =============================================================================

class TestListCommand:
    def test_list(self, tmp_path: Path):
        config_path = tmp_path / "model-canary.yml"
        config_path.write_text("""
version: "1"
project_name: test
providers:
  - name: openai
    type: openai
    api_key: sk-test
    default_model: gpt-4o
test_suites:
  - name: production
    enabled: true
    prompts:
      - name: test
        prompt: "Hi"
        model: gpt-4o
storage:
  backend: sqlite
  connection_string: sqlite+aiosqlite:///test.db
alerting:
  enabled: true
  channels:
    - log
  min_severity: low
""")
        result = runner.invoke(app, ["list", "-c", str(config_path)])
        assert result.exit_code == 0
        assert "openai" in result.stdout
        assert "production" in result.stdout


# =============================================================================
# Prompts Command
# =============================================================================

class TestPromptsCommand:
    def test_prompts_list(self, tmp_path: Path):
        config_path = tmp_path / "model-canary.yml"
        config_path.write_text("""
version: "1"
project_name: test
providers:
  - name: openai
    type: openai
    api_key: sk-test
    default_model: gpt-4o
test_suites:
  - name: production
    enabled: true
    prompts:
      - name: json-test
        prompt: "Return JSON"
        model: gpt-4o
        category: json
        severity: high
        evaluators:
          - json
storage:
  backend: sqlite
  connection_string: sqlite+aiosqlite:///test.db
alerting:
  enabled: true
  channels:
    - log
  min_severity: low
""")
        result = runner.invoke(app, ["prompts", "--list", "-c", str(config_path)])
        assert result.exit_code == 0
        assert "json-test" in result.stdout

    def test_prompts_list_by_category(self, tmp_path: Path):
        config_path = tmp_path / "model-canary.yml"
        config_path.write_text("""
version: "1"
project_name: test
providers:
  - name: openai
    type: openai
    api_key: sk-test
    default_model: gpt-4o
test_suites:
  - name: production
    enabled: true
    prompts:
      - name: json-test
        prompt: "Return JSON"
        model: gpt-4o
        category: json
        severity: high
        evaluators:
          - json
storage:
  backend: sqlite
  connection_string: sqlite+aiosqlite:///test.db
alerting:
  enabled: true
  channels:
    - log
  min_severity: low
""")
        result = runner.invoke(app, ["prompts", "--list", "--category", "json", "-c", str(config_path)])
        assert result.exit_code == 0
        assert "json-test" in result.stdout

    def test_prompts_discover_tree(self, tmp_path: Path):
        orig_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            (tmp_path / "prompts" / "coding").mkdir(parents=True)
            (tmp_path / "prompts" / "coding" / "test.md").write_text("test")
            result = runner.invoke(app, ["prompts"])
            assert result.exit_code == 0
        finally:
            os.chdir(orig_cwd)


# =============================================================================
# Providers Command
# =============================================================================

class TestProvidersCommand:
    def test_providers(self):
        from model_canary.providers.registry import get_provider_registry
        reg = get_provider_registry()
        reg._providers.clear()
        result = runner.invoke(app, ["providers"])
        assert result.exit_code == 0


# =============================================================================
# Doctor Command
# =============================================================================

class TestDoctorCommand:
    def test_doctor_no_config(self):
        result = runner.invoke(app, ["doctor", "-c", "/nonexistent/path/model-canary.yml"])
        assert result.exit_code == 0

    def test_doctor_with_config(self, tmp_path: Path):
        config_path = tmp_path / "model-canary.yml"
        config_path.write_text("""
version: "1"
project_name: test
providers:
  - name: openai
    type: openai
    api_key: sk-test
    default_model: gpt-4o
test_suites: []
storage:
  backend: sqlite
  connection_string: sqlite+aiosqlite:///test.db
alerting:
  enabled: true
  channels:
    - log
  min_severity: low
""")
        result = runner.invoke(app, ["doctor", "-c", str(config_path)])
        assert result.exit_code == 0


# =============================================================================
# Alerts Command
# =============================================================================

class TestAlertsCommand:
    def test_alerts_config(self, tmp_path: Path):
        config_path = tmp_path / "model-canary.yml"
        config_path.write_text("""
version: "1"
project_name: test
providers: []
test_suites: []
storage:
  backend: sqlite
  connection_string: sqlite+aiosqlite:///test.db
alerting:
  enabled: true
  channels:
    - log
  min_severity: medium
""")
        result = runner.invoke(app, ["alerts", "-c", str(config_path)])
        assert result.exit_code == 0

    def test_alerts_send_test(self, tmp_path: Path):
        config_path = tmp_path / "model-canary.yml"
        config_path.write_text("""
version: "1"
project_name: test
providers: []
test_suites: []
storage:
  backend: sqlite
  connection_string: sqlite+aiosqlite:///test.db
alerting:
  enabled: true
  channels:
    - log
  min_severity: medium
""")
        result = runner.invoke(app, ["alerts", "--test", "-c", str(config_path)])
        assert result.exit_code == 0


# =============================================================================
# History Command
# =============================================================================

class TestHistoryCommand:
    def test_history_empty(self, tmp_path: Path):
        config_path = tmp_path / "model-canary.yml"
        config_path.write_text("""
version: "1"
project_name: test
providers: []
test_suites: []
storage:
  backend: sqlite
  connection_string: sqlite+aiosqlite:///test.db
alerting:
  enabled: true
  channels:
    - log
  min_severity: low
""")
        from model_canary.engine import CanaryEngine
        mock_engine = MagicMock()
        mock_engine.initialize = AsyncMock()
        mock_engine._storage = MagicMock()
        mock_engine._storage.get_drift_reports = AsyncMock(return_value=[])

        with patch("model_canary.cli.CanaryEngine", return_value=mock_engine):
            result = runner.invoke(app, ["history", "-c", str(config_path)])
            assert result.exit_code == 0


# =============================================================================
# Dashboard Command
# =============================================================================

class TestDashboardCommand:
    def test_dashboard_missing_deps(self):
        with patch.dict("sys.modules", {"uvicorn": None}):
            result = runner.invoke(app, ["dashboard"])
        assert result.exit_code == 0
        assert "not installed" in result.stdout
