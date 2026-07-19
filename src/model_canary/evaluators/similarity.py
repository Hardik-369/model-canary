from __future__ import annotations

from typing import Any

from model_canary.core.models import PromptConfig, PromptResult
from model_canary.evaluators.base import BaseEvaluator


class SimilarityEvaluator(BaseEvaluator):
    @property
    def name(self) -> str:
        return "similarity"

    @property
    def evaluator_type(self) -> str:
        return "similarity"

    async def evaluate(
        self,
        prompt: PromptConfig,
        result: PromptResult,
        **kwargs: Any,
    ) -> dict[str, Any]:
        expected = prompt.expected_output or self._config.get("expected", "")
        if not expected:
            return {"passed": True, "score": 1.0, "details": {"note": "No expected output configured"}}

        threshold = self._config.get("threshold", 0.8)
        response = result.response

        try:
            from sentence_transformers import SentenceTransformer
            embedder = SentenceTransformer(self._config.get("model", "all-MiniLM-L6-v2"))
            emb1 = embedder.encode(expected, normalize_embeddings=True)
            emb2 = embedder.encode(response, normalize_embeddings=True)
            import numpy as np
            similarity = float(np.dot(emb1, emb2))
        except ImportError:
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, expected.lower(), response.lower()).ratio()

        passed = similarity >= threshold

        return {
            "passed": passed,
            "score": similarity,
            "details": {
                "similarity": similarity,
                "threshold": threshold,
                "expected_preview": expected[:100],
                "response_preview": response[:100],
            },
        }
