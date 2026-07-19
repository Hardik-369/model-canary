from __future__ import annotations

import json
from typing import Any

from model_canary.core.models import PromptConfig, PromptResult
from model_canary.evaluators.base import BaseEvaluator


class JSONValidatorEvaluator(BaseEvaluator):
    @property
    def name(self) -> str:
        return "json_validator"

    @property
    def evaluator_type(self) -> str:
        return "json"

    async def evaluate(
        self,
        prompt: PromptConfig,
        result: PromptResult,
        **kwargs: Any,
    ) -> dict[str, Any]:
        response = result.response.strip()

        # Try to extract JSON from markdown code blocks
        json_str = response
        if "```json" in response:
            import re
            match = re.search(r"```json\n(.*?)\n```", response, re.DOTALL)
            if match:
                json_str = match.group(1)
        elif "```" in response:
            import re
            match = re.search(r"```\n?(.*?)\n?```", response, re.DOTALL)
            if match:
                json_str = match.group(1)

        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as e:
            return {
                "passed": False,
                "score": 0.0,
                "details": {
                    "error": f"Invalid JSON: {e}",
                    "response_preview": response[:200],
                },
            }

        # Validate against required schema if provided
        schema_valid = True
        schema_errors = []
        if prompt.required_json_schema:
            schema = prompt.required_json_schema
            if isinstance(parsed, dict):
                for key, expected_type in schema.items():
                    if key not in parsed:
                        schema_errors.append(f"Missing key: {key}")
                        schema_valid = False
                    elif expected_type and not isinstance(parsed[key], self._resolve_type(expected_type)):
                        schema_errors.append(
                            f"Key '{key}' expected {expected_type}, got {type(parsed[key]).__name__}"
                        )
                        schema_valid = False

        return {
            "passed": schema_valid,
            "score": 1.0 if schema_valid else 0.5,
            "details": {
                "is_valid_json": True,
                "schema_valid": schema_valid,
                "schema_errors": schema_errors,
                "parsed_type": type(parsed).__name__,
            },
        }

    def _resolve_type(self, type_name: str) -> type:
        type_map = {
            "str": str,
            "string": str,
            "int": int,
            "integer": int,
            "float": float,
            "number": float,
            "bool": bool,
            "boolean": bool,
            "list": list,
            "dict": dict,
            "object": dict,
            "array": list,
            "any": object,
        }
        return type_map.get(type_name.lower(), object)
