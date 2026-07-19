from __future__ import annotations

from typing import Any

from model_canary.core.models import PromptConfig, PromptResult
from model_canary.evaluators.base import BaseEvaluator


class LLMJudgeEvaluator(BaseEvaluator):
    @property
    def name(self) -> str:
        return "llm_judge"

    @property
    def evaluator_type(self) -> str:
        return "llm_judge"

    async def evaluate(
        self,
        prompt: PromptConfig,
        result: PromptResult,
        **kwargs: Any,
    ) -> dict[str, Any]:
        judge_prompt = self._config.get("judge_prompt", "")
        if not judge_prompt:
            return {"passed": True, "score": 1.0, "details": {"note": "No judge prompt configured"}}

        criteria = self._config.get("criteria", "quality")
        judge_model = self._config.get("judge_model", "gpt-4o")

        final_prompt = judge_prompt.format(
            prompt=prompt.prompt,
            response=result.response,
            expected=prompt.expected_output or "N/A",
            criteria=criteria,
        )

        try:
            import litellm

            judge_response = await litellm.acompletion(
                model=judge_model,
                messages=[{"role": "user", "content": final_prompt}],
                temperature=0.0,
            )
            judge_text = judge_response.choices[0].message.content or ""

            import re
            score_match = re.search(r"(?i)(?:score|rating):\s*(\d+(?:\.\d+)?)\s*(?:/10|/100|%)?", judge_text)
            if score_match:
                score = float(score_match.group(1))
                if score > 10:
                    score = score / 10.0 if score > 10 else score
                score = max(0.0, min(1.0, score / 10.0))
            else:
                score = 0.5

            passed = score >= self._config.get("threshold", 0.7)

            return {
                "passed": passed,
                "score": score,
                "details": {
                    "judge_model": judge_model,
                    "criteria": criteria,
                    "judge_response": judge_text[:500],
                },
            }
        except Exception as e:
            return {
                "passed": False,
                "score": 0.0,
                "details": {
                    "error": f"LLM judge failed: {e}",
                },
            }
