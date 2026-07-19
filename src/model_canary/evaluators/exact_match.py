from __future__ import annotations

from typing import Any

from model_canary.core.models import PromptConfig, PromptResult
from model_canary.evaluators.base import BaseEvaluator


class ExactMatchEvaluator(BaseEvaluator):
    @property
    def name(self) -> str:
        return "exact_match"

    @property
    def evaluator_type(self) -> str:
        return "exact_match"

    async def evaluate(
        self,
        prompt: PromptConfig,
        result: PromptResult,
        **kwargs: Any,
    ) -> dict[str, Any]:
        expected = prompt.expected_output or self._config.get("expected", "")
        if not expected:
            return {"passed": True, "score": 1.0, "details": {"note": "No expected output configured"}}

        response = result.response.strip()
        expected_stripped = expected.strip()
        case_sensitive = self._config.get("case_sensitive", True)

        if not case_sensitive:
            match = response.lower() == expected_stripped.lower()
        else:
            match = response == expected_stripped

        return {
            "passed": match,
            "score": 1.0 if match else 0.0,
            "details": {
                "match": match,
                "case_sensitive": case_sensitive,
                "expected_length": len(expected_stripped),
                "response_length": len(response),
            },
        }
