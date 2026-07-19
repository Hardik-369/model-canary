from __future__ import annotations

import json
from pathlib import Path

_MODEL_PRICING: dict[str, dict[str, float]] | None = None
_DEFAULT_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00, "unit": "per_million"},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "unit": "per_million"},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00, "unit": "per_million"},
    "gpt-4": {"input": 30.00, "output": 60.00, "unit": "per_million"},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50, "unit": "per_million"},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00, "unit": "per_million"},
    "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00, "unit": "per_million"},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25, "unit": "per_million"},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00, "unit": "per_million"},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00, "unit": "per_million"},
    "gemini/gemini-pro": {"input": 0.50, "output": 1.50, "unit": "per_million"},
    "gemini/gemini-ultra": {"input": 2.00, "output": 6.00, "unit": "per_million"},
    "gemini/gemini-1.5-pro": {"input": 1.25, "output": 5.00, "unit": "per_million"},
    "gemini/gemini-1.5-flash": {"input": 0.075, "output": 0.30, "unit": "per_million"},
    "mistral/mistral-large-latest": {"input": 2.00, "output": 6.00, "unit": "per_million"},
    "mistral/mistral-medium": {"input": 2.70, "output": 8.10, "unit": "per_million"},
    "mistral/mistral-small": {"input": 1.00, "output": 3.00, "unit": "per_million"},
    "deepseek/deepseek-chat": {"input": 0.14, "output": 0.28, "unit": "per_million"},
    "deepseek/deepseek-reasoner": {"input": 0.55, "output": 1.10, "unit": "per_million"},
}


def _load_pricing() -> dict[str, dict[str, float]]:
    global _MODEL_PRICING
    if _MODEL_PRICING is not None:
        return _MODEL_PRICING

    pricing = dict(_DEFAULT_PRICING)
    custom_path = Path.cwd() / "model-canary-pricing.json"
    if custom_path.exists():
        try:
            with open(custom_path) as f:
                custom_pricing = json.load(f)
                pricing.update(custom_pricing)
        except Exception:
            pass

    _MODEL_PRICING = pricing
    return pricing


def get_model_pricing(model: str) -> dict[str, float] | None:
    pricing = _load_pricing()
    return pricing.get(model)


def estimate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    provider: str = "",
) -> float:
    pricing = _load_pricing()

    pricing_model = pricing.get(model)
    if pricing_model:
        unit_mult = 1_000_000 if pricing_model.get("unit") == "per_million" else 1_000
        input_cost = (prompt_tokens / unit_mult) * pricing_model.get("input", 0)
        output_cost = (completion_tokens / unit_mult) * pricing_model.get("output", 0)
        return input_cost + output_cost

    base_model = model.rsplit("/", maxsplit=1)[-1] if "/" in model else model
    pricing_model = pricing.get(base_model)
    if pricing_model:
        unit_mult = 1_000_000 if pricing_model.get("unit") == "per_million" else 1_000
        input_cost = (prompt_tokens / unit_mult) * pricing_model.get("input", 0)
        output_cost = (completion_tokens / unit_mult) * pricing_model.get("output", 0)
        return input_cost + output_cost

    return (prompt_tokens * 0.0000015) + (completion_tokens * 0.000006)
