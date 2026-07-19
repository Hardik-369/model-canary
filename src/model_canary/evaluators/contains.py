from __future__ import annotations

from typing import Any

from model_canary.core.models import PromptConfig, PromptResult
from model_canary.evaluators.base import BaseEvaluator


class ContainsEvaluator(BaseEvaluator):
    @property
    def name(self) -> str:
        return "contains"

    @property
    def evaluator_type(self) -> str:
        return "contains"

    async def evaluate(
        self,
        prompt: PromptConfig,
        result: PromptResult,
        **kwargs: Any,
    ) -> dict[str, Any]:
        required: list[str] = self._config.get("required", prompt.acceptable_outputs or [])
        forbidden: list[str] = self._config.get("forbidden", [])
        case_sensitive = self._config.get("case_sensitive", False)

        response = result.response
        if not case_sensitive:
            response_lower = response.lower()
            required = [r.lower() for r in required]
            forbidden = [f.lower() for f in forbidden]
        else:
            response_lower = response

        found = []
        missing = []
        for item in required:
            if (response_lower if not case_sensitive else response).find(item) >= 0:
                found.append(item)
            else:
                missing.append(item)

        found_forbidden = []
        for item in forbidden:
            if (response_lower if not case_sensitive else response).find(item) >= 0:
                found_forbidden.append(item)

        all_required_found = len(missing) == 0
        no_forbidden_found = len(found_forbidden) == 0
        passed = all_required_found and no_forbidden_found

        return {
            "passed": passed,
            "score": (len(found) / max(len(required), 1)) if required else 1.0,
            "details": {
                "required_found": found,
                "required_missing": missing,
                "forbidden_found": found_forbidden,
                "forbidden_not_found": [f for f in forbidden if f not in found_forbidden],
            },
        }
