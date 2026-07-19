from __future__ import annotations

from typing import Any

from model_canary.core.models import (
    LatencyMetrics,
    ModelInfo,
    PromptResult,
    TokenUsage,
)
from model_canary.providers.base import BaseProvider


class CustomProvider(BaseProvider):
    @property
    def provider_type(self) -> str:
        return "custom"

    def _get_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._config.api_key:
            auth_type = "Bearer"
            if hasattr(self._config, 'extra') and self._config.extra:
                auth_type = self._config.extra.get("auth_type", "Bearer")
            headers["Authorization"] = f"{auth_type} {self._config.api_key}"
        if hasattr(self._config, 'extra') and self._config.extra:
            extra_headers = self._config.extra.get("headers", {})
            if isinstance(extra_headers, dict):
                headers.update(extra_headers)
        return headers

    def _get_api_url(self) -> str:
        return self._config.base_url or "http://localhost:8000/v1"

    def _get_request_body(
        self,
        prompt: str,
        model: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        if temperature is not None:
            body["temperature"] = temperature
        if hasattr(self._config, 'extra') and self._config.extra:
            extra_body = {
                k: v
                for k, v in self._config.extra.items()
                if k not in ("headers", "auth_type")
            }
            body.update(extra_body)
        body.update(kwargs)
        return body

    async def complete(
        self,
        prompt: str,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> PromptResult:
        import time

        model_name = model or self._config.default_model or "default"
        body = self._get_request_body(prompt, model_name, max_tokens, temperature, **kwargs)

        start_time = time.perf_counter()
        elapsed = 0.0
        try:
            data = await self._make_request("POST", "/chat/completions", json_data=body)
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

        choice = data.get("choices", [{}])[0] if data.get("choices") else {}
        message = choice.get("message", {})
        response_text = message.get("content", "")
        finish_reason = choice.get("finish_reason")

        usage = data.get("usage", {})
        token_usage = TokenUsage(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
        )

        tool_calls = []
        raw_tool_calls = message.get("tool_calls", [])
        for tc in raw_tool_calls:
            tool_calls.append({
                "id": tc.get("id", ""),
                "type": tc.get("type", "function"),
                "function": tc.get("function", {}),
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
            refusal=bool(message.get("refusal", False)),
            refusal_reason=str(message.get("refusal")) if message.get("refusal") else None,
            raw_response=data,
        )

    async def list_models(self) -> list[ModelInfo]:
        try:
            data = await self._make_request("GET", "/models")
            model_list = data.get("data", []) if isinstance(data, dict) else data if isinstance(data, list) else []
            return [
                ModelInfo(
                    model_name=m.get("id", "") if isinstance(m, dict) else str(m),
                    provider=self.name,
                )
                for m in model_list
            ]
        except Exception:
            return [
                ModelInfo(
                    model_name=self._config.default_model or "default",
                    provider=self.name,
                )
            ]
