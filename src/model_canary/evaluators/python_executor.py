from __future__ import annotations

from typing import Any

from model_canary.core.models import PromptConfig, PromptResult
from model_canary.evaluators.base import BaseEvaluator


class PythonEvaluator(BaseEvaluator):
    @property
    def name(self) -> str:
        return "python"

    @property
    def evaluator_type(self) -> str:
        return "python"

    async def evaluate(
        self,
        prompt: PromptConfig,
        result: PromptResult,
        **kwargs: Any,
    ) -> dict[str, Any]:
        assertion_code = self._config.get("assertion", "")
        if not assertion_code:
            return {"passed": True, "score": 1.0, "details": {"note": "No assertion code configured"}}

        local_vars = {
            "response": result.response,
            "prompt": prompt,
            "result": result,
            "token_usage": result.token_usage,
            "latency": result.latency,
            "cost": result.cost,
            "tool_calls": result.tool_calls,
        }

        try:
            compiled = compile(assertion_code, "<evaluator>", "exec")
            exec(compiled, {"__builtins__": __builtins__}, local_vars)
            passed = local_vars.get("passed", True)
            score = local_vars.get("score", 1.0 if passed else 0.0)
            details = local_vars.get("details", {})
        except Exception as e:
            passed = False
            score = 0.0
            details = {"error": str(e)}

        return {
            "passed": passed,
            "score": score,
            "details": details,
        }
