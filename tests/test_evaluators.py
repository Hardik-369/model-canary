"""Tests for evaluators."""

import pytest
from model_canary.core.models import PromptConfig, PromptResult, TokenUsage, LatencyMetrics, CostMetrics


@pytest.fixture
def sample_result():
    return PromptResult(
        prompt_name="test",
        prompt_text="test",
        model="gpt-4",
        provider="openai",
        response='{"name": "John", "age": 30}',
        token_usage=TokenUsage(prompt_tokens=5, completion_tokens=10, total_tokens=15),
        latency=LatencyMetrics(total_time=0.1, total_time_ms=100.0),
        cost=CostMetrics(total_cost=0.0001),
    )


@pytest.fixture
def json_prompt():
    return PromptConfig(
        name="json-test",
        prompt="Return JSON",
        required_json_schema={"name": "string", "age": "integer"},
    )


class TestJSONEvaluator:
    @pytest.mark.asyncio
    async def test_valid_json(self, sample_result):
        from model_canary.evaluators.json_validator import JSONValidatorEvaluator
        evaluator = JSONValidatorEvaluator()
        prompt = PromptConfig(name="test", prompt="Return JSON")
        result = await evaluator.evaluate(prompt, sample_result)
        assert result["passed"] is True
        assert result["score"] > 0

    @pytest.mark.asyncio
    async def test_invalid_json(self):
        from model_canary.evaluators.json_validator import JSONValidatorEvaluator
        evaluator = JSONValidatorEvaluator()
        result = PromptResult(
            prompt_name="test", prompt_text="test",
            model="gpt-4", provider="openai",
            response="Not JSON",
        )
        prompt = PromptConfig(name="test", prompt="Return JSON")
        eval_result = await evaluator.evaluate(prompt, result)
        assert eval_result["passed"] is False
        assert eval_result["score"] == 0.0

    @pytest.mark.asyncio
    async def test_schema_validation(self, json_prompt, sample_result):
        from model_canary.evaluators.json_validator import JSONValidatorEvaluator
        evaluator = JSONValidatorEvaluator()
        result = await evaluator.evaluate(json_prompt, sample_result)
        assert result["passed"] is True
        assert result["score"] == 1.0

    @pytest.mark.asyncio
    async def test_schema_mismatch(self, json_prompt):
        from model_canary.evaluators.json_validator import JSONValidatorEvaluator
        evaluator = JSONValidatorEvaluator()
        result = PromptResult(
            prompt_name="test", prompt_text="test",
            model="gpt-4", provider="openai",
            response='{"name": "John"}',
        )
        eval_result = await evaluator.evaluate(json_prompt, result)
        assert eval_result["details"]["schema_valid"] is False
        assert len(eval_result["details"]["schema_errors"]) > 0


class TestRegexEvaluator:
    @pytest.mark.asyncio
    async def test_pattern_match(self):
        from model_canary.evaluators.regex import RegexEvaluator
        evaluator = RegexEvaluator({"patterns": [{"pattern": r"\d+"}]})
        result = PromptResult(
            prompt_name="test", prompt_text="test",
            model="gpt-4", provider="openai",
            response="12345",
        )
        eval_result = await evaluator.evaluate(PromptConfig(name="test", prompt="test"), result)
        assert eval_result["passed"] is True

    @pytest.mark.asyncio
    async def test_pattern_no_match(self):
        from model_canary.evaluators.regex import RegexEvaluator
        evaluator = RegexEvaluator({"patterns": [{"pattern": r"\d+"}]})
        result = PromptResult(
            prompt_name="test", prompt_text="test",
            model="gpt-4", provider="openai",
            response="hello",
        )
        eval_result = await evaluator.evaluate(PromptConfig(name="test", prompt="test"), result)
        assert eval_result["passed"] is False


class TestContainsEvaluator:
    @pytest.mark.asyncio
    async def test_required_found(self):
        from model_canary.evaluators.contains import ContainsEvaluator
        evaluator = ContainsEvaluator({"required": ["world", "hello"]})
        result = PromptResult(
            prompt_name="test", prompt_text="test",
            model="gpt-4", provider="openai",
            response="hello world",
        )
        eval_result = await evaluator.evaluate(PromptConfig(name="test", prompt="test"), result)
        assert eval_result["passed"] is True

    @pytest.mark.asyncio
    async def test_required_missing(self):
        from model_canary.evaluators.contains import ContainsEvaluator
        evaluator = ContainsEvaluator({"required": ["hello", "world"]})
        result = PromptResult(
            prompt_name="test", prompt_text="test",
            model="gpt-4", provider="openai",
            response="hello",
        )
        eval_result = await evaluator.evaluate(PromptConfig(name="test", prompt="test"), result)
        assert eval_result["passed"] is False

    @pytest.mark.asyncio
    async def test_forbidden_found(self):
        from model_canary.evaluators.contains import ContainsEvaluator
        evaluator = ContainsEvaluator({"forbidden": ["bad", "evil"]})
        result = PromptResult(
            prompt_name="test", prompt_text="test",
            model="gpt-4", provider="openai",
            response="this is bad",
        )
        eval_result = await evaluator.evaluate(PromptConfig(name="test", prompt="test"), result)
        assert eval_result["passed"] is False


class TestExactMatchEvaluator:
    @pytest.mark.asyncio
    async def test_exact_match(self):
        from model_canary.evaluators.exact_match import ExactMatchEvaluator
        evaluator = ExactMatchEvaluator({"expected": "Hello World"})
        result = PromptResult(
            prompt_name="test", prompt_text="test",
            model="gpt-4", provider="openai",
            response="Hello World",
        )
        prompt = PromptConfig(name="test", prompt="test", expected_output="Hello World")
        eval_result = await evaluator.evaluate(prompt, result)
        assert eval_result["passed"] is True

    @pytest.mark.asyncio
    async def test_case_insensitive(self):
        from model_canary.evaluators.exact_match import ExactMatchEvaluator
        evaluator = ExactMatchEvaluator({"expected": "hello world", "case_sensitive": False})
        result = PromptResult(
            prompt_name="test", prompt_text="test",
            model="gpt-4", provider="openai",
            response="Hello World",
        )
        prompt = PromptConfig(name="test", prompt="test", expected_output="hello world")
        eval_result = await evaluator.evaluate(prompt, result)
        assert eval_result["passed"] is True


class TestPythonEvaluator:
    @pytest.mark.asyncio
    async def test_python_assertion_pass(self):
        from model_canary.evaluators.python_executor import PythonEvaluator
        evaluator = PythonEvaluator({
            "assertion": "passed = len(response) > 0"
        })
        result = PromptResult(
            prompt_name="test", prompt_text="test",
            model="gpt-4", provider="openai",
            response="hello",
        )
        eval_result = await evaluator.evaluate(PromptConfig(name="test", prompt="test"), result)
        assert eval_result["passed"] is True

    @pytest.mark.asyncio
    async def test_python_assertion_fail(self):
        from model_canary.evaluators.python_executor import PythonEvaluator
        evaluator = PythonEvaluator({
            "assertion": "passed = len(response) > 100"
        })
        result = PromptResult(
            prompt_name="test", prompt_text="test",
            model="gpt-4", provider="openai",
            response="hi",
        )
        eval_result = await evaluator.evaluate(PromptConfig(name="test", prompt="test"), result)
        assert eval_result["passed"] is False


class TestBLEUEvaluator:
    @pytest.mark.asyncio
    async def test_bleu_identical(self):
        from model_canary.evaluators.bleu import BLEUEvaluator
        evaluator = BLEUEvaluator({"expected": "hello world"})
        result = PromptResult(
            prompt_name="test", prompt_text="test",
            model="gpt-4", provider="openai",
            response="hello world",
        )
        prompt = PromptConfig(name="test", prompt="test", expected_output="hello world")
        eval_result = await evaluator.evaluate(prompt, result)
        assert eval_result["score"] == pytest.approx(1.0, abs=0.1)

    @pytest.mark.asyncio
    async def test_bleu_no_match(self):
        from model_canary.evaluators.bleu import BLEUEvaluator
        evaluator = BLEUEvaluator({"expected": "hello world", "threshold": 0.0})
        result = PromptResult(
            prompt_name="test", prompt_text="test",
            model="gpt-4", provider="openai",
            response="goodbye universe",
        )
        prompt = PromptConfig(name="test", prompt="test", expected_output="hello world")
        eval_result = await evaluator.evaluate(prompt, result)
        assert eval_result["score"] < 1.0


class TestROUGEEvaluator:
    @pytest.mark.asyncio
    async def test_rouge_identical(self):
        from model_canary.evaluators.rouge import ROUGEEvaluator
        evaluator = ROUGEEvaluator({"expected": "hello world", "threshold": 0.0})
        result = PromptResult(
            prompt_name="test", prompt_text="test",
            model="gpt-4", provider="openai",
            response="hello world",
        )
        prompt = PromptConfig(name="test", prompt="test", expected_output="hello world")
        eval_result = await evaluator.evaluate(prompt, result)
        assert eval_result["score"] > 0.8

    @pytest.mark.asyncio
    async def test_rouge_empty(self):
        from model_canary.evaluators.rouge import ROUGEEvaluator
        evaluator = ROUGEEvaluator({"expected": ""})
        result = PromptResult(
            prompt_name="test", prompt_text="test",
            model="gpt-4", provider="openai",
            response="",
        )
        prompt = PromptConfig(name="test", prompt="test", expected_output="")
        eval_result = await evaluator.evaluate(prompt, result)
        assert eval_result["passed"] is True


class TestSimilarityEvaluator:
    @pytest.mark.asyncio
    async def test_similarity_basic(self):
        from model_canary.evaluators.similarity import SimilarityEvaluator
        evaluator = SimilarityEvaluator({"expected": "hello world", "threshold": 0.0})
        result = PromptResult(
            prompt_name="test", prompt_text="test",
            model="gpt-4", provider="openai",
            response="hello world",
        )
        prompt = PromptConfig(name="test", prompt="test", expected_output="hello world")
        eval_result = await evaluator.evaluate(prompt, result)
        assert isinstance(eval_result["score"], float)
        assert eval_result["passed"] is True
