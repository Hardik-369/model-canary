from __future__ import annotations

from typing import Any

from model_canary.core.models import PromptConfig, PromptResult
from model_canary.evaluators.base import BaseEvaluator


class BLEUEvaluator(BaseEvaluator):
    @property
    def name(self) -> str:
        return "bleu"

    @property
    def evaluator_type(self) -> str:
        return "bleu"

    async def evaluate(
        self,
        prompt: PromptConfig,
        result: PromptResult,
        **kwargs: Any,
    ) -> dict[str, Any]:
        expected = prompt.expected_output or self._config.get("expected", "")
        if not expected:
            return {"passed": True, "score": 1.0, "details": {"note": "No expected output configured"}}

        threshold = self._config.get("threshold", 0.5)
        max_n = self._config.get("max_n", 4)

        response_tokens = result.response.lower().split()
        expected_tokens = expected.lower().split()

        if not response_tokens or not expected_tokens:
            return {
                "passed": False,
                "score": 0.0,
                "details": {"error": "Empty response or reference"},
            }

        precisions = []
        for n in range(1, max_n + 1):
            response_ngrams = self._get_ngrams(response_tokens, n)
            expected_ngrams = self._get_ngrams(expected_tokens, n)
            if not expected_ngrams:
                continue
            count = sum(1 for ng in response_ngrams if ng in expected_ngrams)
            total = len(response_ngrams)
            precisions.append(count / max(total, 1))

        if not precisions:
            return {"passed": False, "score": 0.0, "details": {"error": "No n-grams computed"}}

        import math
        bp = min(1.0, math.exp(1 - len(expected_tokens) / max(len(response_tokens), 1)))
        safe_precisions = [max(p, 1e-10) for p in precisions]
        avg_precision = math.exp(sum(math.log(p) for p in safe_precisions) / len(safe_precisions))
        bleu_score = bp * avg_precision

        passed = bleu_score >= threshold

        return {
            "passed": passed,
            "score": bleu_score,
            "details": {
                "bleu_score": bleu_score,
                "brevity_penalty": bp,
                "precisions": precisions,
                "threshold": threshold,
            },
        }

    def _get_ngrams(self, tokens: list, n: int) -> list:
        return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]
