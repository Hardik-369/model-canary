from __future__ import annotations

from typing import Any

from model_canary.core.interfaces import Evaluator


def load_evaluator(
    name: str, config: dict[str, Any] | None = None
) -> Evaluator:
    import importlib.metadata

    evaluator_map: dict[str, str] = {
        "json": "model_canary.evaluators.json_validator:JSONValidatorEvaluator",
        "json_validator": "model_canary.evaluators.json_validator:JSONValidatorEvaluator",
        "regex": "model_canary.evaluators.regex:RegexEvaluator",
        "similarity": "model_canary.evaluators.similarity:SimilarityEvaluator",
        "exact_match": "model_canary.evaluators.exact_match:ExactMatchEvaluator",
        "contains": "model_canary.evaluators.contains:ContainsEvaluator",
        "python": "model_canary.evaluators.python_executor:PythonEvaluator",
        "llm_judge": "model_canary.evaluators.llm_judge:LLMJudgeEvaluator",
        "bleu": "model_canary.evaluators.bleu:BLEUEvaluator",
        "rouge": "model_canary.evaluators.rouge:ROUGEEvaluator",
    }

    if name in evaluator_map:
        module_path, class_name = evaluator_map[name].split(":")
        import importlib

        module = importlib.import_module(module_path)
        cls: type[Evaluator] = getattr(module, class_name)
        return cls(config)

    for ep in importlib.metadata.entry_points(group="model_canary.evaluators"):
        if ep.name == name:
            cls = ep.load()
            return cls(config)

    raise ValueError(
        f"Evaluator '{name}' not found. Built-in evaluators: {', '.join(evaluator_map)}"
    )
