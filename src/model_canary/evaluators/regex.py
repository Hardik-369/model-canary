from __future__ import annotations

import re
from typing import Any

from model_canary.core.models import PromptConfig, PromptResult
from model_canary.evaluators.base import BaseEvaluator


class RegexEvaluator(BaseEvaluator):
    @property
    def name(self) -> str:
        return "regex"

    @property
    def evaluator_type(self) -> str:
        return "regex"

    async def evaluate(
        self,
        prompt: PromptConfig,
        result: PromptResult,
        **kwargs: Any,
    ) -> dict[str, Any]:
        patterns = self._config.get("patterns", [])
        if not patterns:
            return {"passed": True, "score": 1.0, "details": {"note": "No patterns configured"}}

        response = result.response
        results = []
        all_passed = True

        for pattern in patterns:
            flags = 0
            if pattern.get("ignore_case", True):
                flags |= re.IGNORECASE
            if pattern.get("multiline", False):
                flags |= re.MULTILINE
            if pattern.get("dotall", False):
                flags |= re.DOTALL

            try:
                compiled = re.compile(pattern["pattern"], flags)
                match = compiled.search(response)
                passed = match is not None
                if pattern.get("negate", False):
                    passed = not passed
                results.append({
                    "pattern": pattern["pattern"],
                    "passed": passed,
                    "matched": match.group() if match else None,
                })
                if not passed:
                    all_passed = False
            except re.error as e:
                results.append({
                    "pattern": pattern["pattern"],
                    "passed": False,
                    "error": str(e),
                })
                all_passed = False

        return {
            "passed": all_passed,
            "score": sum(1 for r in results if r["passed"]) / max(len(results), 1),
            "details": {"results": results},
        }
