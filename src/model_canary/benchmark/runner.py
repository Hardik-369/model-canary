from __future__ import annotations

import asyncio
import time
from typing import Any

from model_canary.core.models import ModelCanaryConfig, ProviderConfig
from model_canary.providers.factory import create_provider
from model_canary.providers.registry import register_providers


class BenchmarkRunner:
    def __init__(self, config: ModelCanaryConfig | None = None) -> None:
        self._config = config
        self._providers: dict[str, Any] = {}

    async def run(
        self,
        prompt: str,
        models: list[str],
        providers: list[str] | None = None,
        iterations: int = 3,
    ) -> dict[str, Any]:
        register_providers()
        provider_list = providers or ["openai", "anthropic", "gemini"]

        results: dict[str, Any] = {}
        tasks = []

        for provider_name in provider_list:
            provider_cfg = None
            if self._config:
                for p in self._config.providers:
                    if p.name == provider_name or p.provider_type == provider_name:
                        provider_cfg = p
                        break

            if not provider_cfg:
                provider_cfg = ProviderConfig(
                    name=provider_name,
                    type=provider_name,
                )

            if provider_name not in self._providers:
                self._providers[provider_name] = create_provider(provider_cfg)

            provider = self._providers[provider_name]

            for model in models:
                for i in range(iterations):
                    tasks.append(self._benchmark_single(provider, model, prompt, i))

        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result_data in all_results:
            if isinstance(result_data, Exception):
                continue
            key = f"{result_data['provider']}/{result_data['model']}"
            if key not in results:
                results[key] = {
                    "provider": result_data["provider"],
                    "model": result_data["model"],
                    "iterations": [],
                }
            results[key]["iterations"].append(result_data)

        for key in results:
            data = results[key]
            latencies = [i.get("latency_ms", 0) for i in data["iterations"]]
            costs = [i.get("cost_usd", 0) for i in data["iterations"]]
            tokens = [i.get("total_tokens", 0) for i in data["iterations"]]

            data["avg_latency_ms"] = sum(latencies) / max(len(latencies), 1)
            data["min_latency_ms"] = min(latencies) if latencies else 0
            data["max_latency_ms"] = max(latencies) if latencies else 0
            data["avg_cost_usd"] = sum(costs) / max(len(costs), 1)
            data["avg_tokens"] = sum(tokens) / max(len(tokens), 1)
            data["total_cost_usd"] = sum(costs)

            responses = [i.get("response", "") for i in data["iterations"]]
            if responses:
                data["latest_response"] = responses[-1][:500]

            del data["iterations"]

        return results

    async def _benchmark_single(
        self, provider: Any, model: str, prompt: str, iteration: int
    ) -> dict[str, Any]:
        start = time.perf_counter()
        try:
            result = await provider.complete(prompt=prompt, model=model)
            elapsed = (time.perf_counter() - start) * 1000
            return {
                "provider": provider.name,
                "model": model,
                "iteration": iteration,
                "latency_ms": elapsed,
                "cost_usd": result.cost.total_cost,
                "total_tokens": result.token_usage.total_tokens,
                "prompt_tokens": result.token_usage.prompt_tokens,
                "completion_tokens": result.token_usage.completion_tokens,
                "refusal": result.refusal,
                "finish_reason": result.finish_reason,
                "response": result.response,
                "error": None,
            }
        except Exception as e:
            return {
                "provider": provider.name,
                "model": model,
                "iteration": iteration,
                "latency_ms": 0,
                "cost_usd": 0,
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "refusal": False,
                "finish_reason": None,
                "response": "",
                "error": str(e),
            }

    async def close(self) -> None:
        for provider in self._providers.values():
            try:
                await provider.close()
            except Exception:
                pass
