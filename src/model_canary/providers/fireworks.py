from __future__ import annotations

from typing import Any

import litellm

from model_canary.core.models import (
    LatencyMetrics,
    ModelInfo,
    PromptResult,
    TokenUsage,
)
from model_canary.providers.base import BaseProvider


class FireworksProvider(BaseProvider):
    @property
    def provider_type(self) -> str:
        return "fireworks"

    def _get_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._config.api_key or ''}"}

    def _get_api_url(self) -> str:
        return self._config.base_url or "https://api.fireworks.ai/inference/v1"

    def _get_litellm_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {
            "api_key": self._config.api_key,
        }
        if self._config.base_url:
            params["api_base"] = self._config.base_url
        if hasattr(self._config, 'extra') and self._config.extra:
            params.update(self._config.extra)
        return params

    async def complete(
        self,
        prompt: str,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> PromptResult:
        import time

        lt_params = self._get_litellm_params()
        model_name = model or self._config.default_model or "fireworks_ai/accounts/fireworks/models/llama-v3p1-8b-instruct"

        start_time = time.perf_counter()
        elapsed = 0.0
        try:
            response = await litellm.acompletion(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                **lt_params,
                **kwargs,
            )
            elapsed = time.perf_counter() - start_time
        except Exception as e:
            return PromptResult(
                prompt_name=kwargs.get("prompt_name", "unknown"),
                prompt_text=prompt,
                model=model_name,
                provider=self.name,
                response="",
                error=str(e),
                latency=LatencyMetrics(total_time=elapsed, total_time_ms=elapsed * 1000),
            )

        choice = response.choices[0] if response.choices else None
        response_text = choice.message.content if choice and choice.message else ""
        finish_reason = choice.finish_reason if choice else None
        refusal = getattr(choice.message, 'refusal', None) if choice and choice.message else None

        token_usage = TokenUsage(
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens if response.usage else 0,
            total_tokens=response.usage.total_tokens if response.usage else 0,
        )

        tool_calls = []
        if choice and choice.message and choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                })

        return PromptResult(
            prompt_name=kwargs.get("prompt_name", "unknown"),
            prompt_text=prompt,
            model=model_name,
            provider=self.name,
            response=response_text,
            finish_reason=finish_reason,
            token_usage=token_usage,
            latency=LatencyMetrics(
                total_time=elapsed,
                total_time_ms=elapsed * 1000,
            ),
            cost=self._calculate_cost(token_usage, model_name),
            tool_calls=tool_calls,
            refusal=bool(refusal),
            refusal_reason=str(refusal) if refusal else None,
            raw_response=response.model_dump() if hasattr(response, 'model_dump') else None,
        )

    async def list_models(self) -> list[ModelInfo]:
        try:
            models = await litellm.amodel_list(
                model=f"fireworks_ai/{self._config.api_key or ''}",
                custom_llm_provider="fireworks_ai",
            )
            return [
                ModelInfo(
                    model_name=m.get("id", ""),
                    provider=self.name,
                )
                for m in (models or [])
            ]
        except Exception:
            return [
                ModelInfo(
                    model_name=self._config.default_model or "fireworks_ai/accounts/fireworks/models/llama-v3p1-8b-instruct",
                    provider=self.name,
                )
            ]
