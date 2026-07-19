"""Tests for utility modules."""

import pytest


class TestCosts:
    def test_estimate_cost_gpt4(self):
        from model_canary.utils.costs import estimate_cost
        cost = estimate_cost("gpt-4o", 1000, 500)
        assert cost > 0
        assert cost < 1.0

    def test_estimate_cost_zero_tokens(self):
        from model_canary.utils.costs import estimate_cost
        cost = estimate_cost("gpt-4o", 0, 0)
        assert cost == 0.0

    def test_estimate_cost_unknown_model(self):
        from model_canary.utils.costs import estimate_cost
        cost = estimate_cost("unknown-model", 100, 50)
        assert cost > 0

    def test_get_model_pricing_known(self):
        from model_canary.utils.costs import get_model_pricing
        pricing = get_model_pricing("gpt-4o")
        assert pricing is not None
        assert "input" in pricing
        assert "output" in pricing

    def test_get_model_pricing_unknown(self):
        from model_canary.utils.costs import get_model_pricing
        pricing = get_model_pricing("nonexistent-model-v42")
        assert pricing is None

    def test_cost_different_models(self):
        from model_canary.utils.costs import estimate_cost
        gpt_cost = estimate_cost("gpt-4o", 1000, 1000)
        claude_cost = estimate_cost("claude-3-5-sonnet-20241022", 1000, 1000)
        assert gpt_cost != claude_cost


class TestEvaluatorLoader:
    def test_load_json(self):
        from model_canary.utils.evaluator_loader import load_evaluator
        evaluator = load_evaluator("json")
        assert evaluator.name == "json_validator"
        assert evaluator.evaluator_type == "json"

    def test_load_regex(self):
        from model_canary.utils.evaluator_loader import load_evaluator
        evaluator = load_evaluator("regex")
        assert evaluator.name == "regex"

    def test_load_contains(self):
        from model_canary.utils.evaluator_loader import load_evaluator
        evaluator = load_evaluator("contains")
        assert evaluator.name == "contains"

    def test_load_unknown(self):
        from model_canary.utils.evaluator_loader import load_evaluator
        with pytest.raises(ValueError, match="Evaluator 'unknown_thing' not found"):
            load_evaluator("unknown_thing")


class TestPluginManager:
    @pytest.mark.asyncio
    async def test_plugin_manager_empty(self):
        from model_canary.plugins.manager import PluginManager
        pm = PluginManager()
        assert pm.list_plugins() == {}

    def test_register_and_get(self):
        from model_canary.plugins.manager import PluginManager
        from model_canary.core.interfaces import Plugin, PluginType

        class TestPlugin(Plugin):
            def initialize(self, config=None):
                pass
            def shutdown(self):
                pass
            @property
            def name(self):
                return "test-plugin"
            @property
            def plugin_type(self):
                return PluginType.PROVIDER
            @property
            def version(self):
                return "1.0.0"

        pm = PluginManager()
        plugin = TestPlugin()
        pm.register("test-plugin", plugin)
        assert pm.get("test-plugin") == plugin
        assert "test-plugin" in pm.list_plugins()
        pm.unregister("test-plugin")
        with pytest.raises(Exception):
            pm.get("test-plugin")

    def test_get_plugins_by_type(self):
        from model_canary.plugins.manager import PluginManager
        from model_canary.core.interfaces import Plugin, PluginType
        pm = PluginManager()

        class ProvPlugin(Plugin):
            def initialize(self, config=None): pass
            def shutdown(self): pass
            @property
            def name(self): return "prov"
            @property
            def plugin_type(self): return PluginType.PROVIDER
            @property
            def version(self): return "1.0"

        class EvalPlugin(Plugin):
            def initialize(self, config=None): pass
            def shutdown(self): pass
            @property
            def name(self): return "eval"
            @property
            def plugin_type(self): return PluginType.EVALUATOR
            @property
            def version(self): return "1.0"

        pm.register("prov", ProvPlugin())
        pm.register("eval", EvalPlugin())
        providers = pm.get_plugins_by_type(PluginType.PROVIDER)
        assert len(providers) == 1
        evaluators = pm.get_plugins_by_type(PluginType.EVALUATOR)
        assert len(evaluators) == 1
        pm.shutdown_all()
        assert pm.list_plugins() == {}


class TestScheduler:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        from model_canary.scheduler.engine import CanaryScheduler
        scheduler = CanaryScheduler()
        await scheduler.start()
        assert scheduler.is_running() is True
        await scheduler.stop()
        assert scheduler.is_running() is False

    @pytest.mark.asyncio
    async def test_add_remove_job(self):
        from model_canary.scheduler.engine import CanaryScheduler
        scheduler = CanaryScheduler()
        await scheduler.start()

        async def dummy_job():
            pass

        await scheduler.add_job("test-job", dummy_job, "*/5 * * * *")
        assert "test-job" in scheduler.get_jobs()
        await scheduler.remove_job("test-job")
        assert "test-job" not in scheduler.get_jobs()
        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_interval_job(self):
        from model_canary.scheduler.engine import CanaryScheduler
        scheduler = CanaryScheduler()
        await scheduler.start()

        async def dummy():
            pass

        await scheduler.add_job("interval-job", dummy, "interval", interval_seconds=60)
        assert "interval-job" in scheduler.get_jobs()
        await scheduler.remove_job("interval-job")
        await scheduler.stop()

    def test_is_cron(self):
        from model_canary.scheduler.engine import CanaryScheduler
        scheduler = CanaryScheduler()
        assert scheduler._is_cron("*/5 * * * *") is True
        assert scheduler._is_cron("0 */2 * * *") is True
        assert scheduler._is_cron("*/5 * * * * *") is True
        assert scheduler._is_cron("300") is False
        assert scheduler._is_cron("interval") is False


class TestReportGenerator:
    @pytest.mark.asyncio
    async def test_generate_json(self):
        from model_canary.reporting.generator import ReportGenerator
        from model_canary.core.models import CanaryRunResult
        result = CanaryRunResult(suite_name="test", status="completed")
        gen = ReportGenerator()
        report = await gen.generate_report(result, format="json")
        assert '"suite_name": "test"' in report
        assert '"status": "completed"' in report

    @pytest.mark.asyncio
    async def test_generate_markdown(self):
        from model_canary.reporting.generator import ReportGenerator
        from model_canary.core.models import CanaryRunResult
        result = CanaryRunResult(suite_name="test", status="completed")
        gen = ReportGenerator()
        report = await gen.generate_report(result, format="md")
        assert "test" in report
        assert "COMPLETED" in report

    @pytest.mark.asyncio
    async def test_generate_html(self):
        from model_canary.reporting.generator import ReportGenerator
        from model_canary.core.models import CanaryRunResult
        result = CanaryRunResult(suite_name="test", status="completed")
        gen = ReportGenerator()
        report = await gen.generate_report(result, format="html")
        assert "<html" in report
        assert "Model Canary Report" in report

    @pytest.mark.asyncio
    async def test_generate_csv(self):
        from model_canary.reporting.generator import ReportGenerator
        from model_canary.core.models import CanaryRunResult
        result = CanaryRunResult(suite_name="test")
        gen = ReportGenerator()
        report = await gen.generate_report(result, format="csv")
        assert "type,severity" in report


class TestMetricsCollector:
    def test_metrics_disabled(self):
        from model_canary.metrics.collector import MetricsCollector
        mc = MetricsCollector(enabled=False)
        assert mc.get_metrics_dict()["enabled"] is False

    def test_metrics_enabled(self):
        from model_canary.metrics.collector import MetricsCollector
        mc = MetricsCollector(enabled=True)
        assert mc.get_metrics_dict()["enabled"] is True
        metrics_text = mc.get_metrics()
        assert len(metrics_text) > 0

    def test_record_provider_health(self):
        from model_canary.metrics.collector import MetricsCollector
        mc = MetricsCollector(enabled=True)
        mc.record_provider_health("openai", True)
        mc.record_provider_health("anthropic", False)
        metrics_text = mc.get_metrics()
        assert "model_canary_provider_health" in metrics_text


class TestBenchmarkRunner:
    @pytest.mark.asyncio
    async def test_init_and_close(self):
        from model_canary.benchmark.runner import BenchmarkRunner
        runner = BenchmarkRunner()
        # No error on init/close
        await runner.close()

    def test_benchmark_runner_config(self):
        from model_canary.benchmark.runner import BenchmarkRunner
        from model_canary.core.models import ModelCanaryConfig
        config = ModelCanaryConfig()
        runner = BenchmarkRunner(config=config)
        assert runner._config is not None
