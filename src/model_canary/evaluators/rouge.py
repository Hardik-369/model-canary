from __future__ import annotations

from typing import Any

from model_canary.core.models import PromptConfig, PromptResult
from model_canary.evaluators.base import BaseEvaluator


class ROUGEEvaluator(BaseEvaluator):
    @property
    def name(self) -> str:
        return "rouge"

    @property
    def evaluator_type(self) -> str:
        return "rouge"

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
        rouge_type = self._config.get("rouge_type", "rouge-l")

        response = result.response.lower()
        reference = expected.lower()

        response_sentences = self._split_sentences(response)
        reference_sentences = self._split_sentences(reference)

        if rouge_type == "rouge-1":
            score = self._rouge_n(response_sentences, reference_sentences, 1)
        elif rouge_type == "rouge-2":
            score = self._rouge_n(response_sentences, reference_sentences, 2)
        else:
            score = self._rouge_l(response_sentences, reference_sentences)

        passed = score >= threshold

        return {
            "passed": passed,
            "score": score,
            "details": {
                "rouge_type": rouge_type,
                "score": score,
                "threshold": threshold,
            },
        }

    def _split_sentences(self, text: str) -> list:
        import re
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _rouge_n(self, response_sents: list, ref_sents: list, n: int) -> float:
        response_ngrams = self._get_ngrams_from_sentences(response_sents, n)
        ref_ngrams = self._get_ngrams_from_sentences(ref_sents, n)

        if not response_ngrams or not ref_ngrams:
            return 0.0

        overlap = len(response_ngrams & ref_ngrams)
        precision = overlap / max(len(response_ngrams), 1)
        recall = overlap / max(len(ref_ngrams), 1)

        if precision + recall == 0:
            return 0.0
        f1 = 2 * precision * recall / (precision + recall)
        return f1

    def _rouge_l(self, response_sents: list, ref_sents: list) -> float:
        response_tokens = [t for s in response_sents for t in s.split()]
        ref_tokens = [t for s in ref_sents for t in s.split()]

        if not response_tokens or not ref_tokens:
            return 0.0

        lcs_len = self._lcs_length(response_tokens, ref_tokens)
        precision = lcs_len / max(len(response_tokens), 1)
        recall = lcs_len / max(len(ref_tokens), 1)

        if precision + recall == 0:
            return 0.0
        f1 = 2 * precision * recall / (precision + recall)
        return f1

    def _get_ngrams_from_sentences(self, sentences: list, n: int) -> set:
        ngrams = set()
        for sentence in sentences:
            tokens = sentence.split()
            for i in range(len(tokens) - n + 1):
                ngrams.add(tuple(tokens[i:i + n]))
        return ngrams

    def _lcs_length(self, a: list, b: list) -> int:
        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if a[i - 1] == b[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        return dp[m][n]
