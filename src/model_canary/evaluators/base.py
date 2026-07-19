from __future__ import annotations

from abc import abstractmethod
from typing import Any

from model_canary.core.interfaces import Evaluator
from model_canary.core.models import PromptConfig, PromptResult


class BaseEvaluator(Evaluator):
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}

    @property
    def config(self) -> dict[str, Any]:
        return self._config

    @abstractmethod
    async def evaluate(
        self,
        prompt: PromptConfig,
        result: PromptResult,
        **kwargs: Any,
    ) -> dict[str, Any]:
        ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def evaluator_type(self) -> str: ...
