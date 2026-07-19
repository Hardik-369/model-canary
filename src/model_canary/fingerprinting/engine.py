from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import numpy as np

from model_canary.core.exceptions import FingerprintError
from model_canary.core.models import Fingerprint, PromptResult, ProviderInfo


class FingerprintingEngine:
    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.85,
    ) -> None:
        self._embedding_model_name = embedding_model
        self._similarity_threshold = similarity_threshold
        self._embedder: Any | None = None

    def _get_embedder(self):
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._embedder = SentenceTransformer(self._embedding_model_name)
            except Exception:
                self._embedder = None
        return self._embedder

    def _compute_sha256(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _compute_embedding(self, text: str) -> list[float] | None:
        embedder = self._get_embedder()
        if embedder is None:
            return None
        try:
            embedding = embedder.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception:
            return None

    def _compute_json_schema_hash(
        self, text: str
    ) -> str | None:
        json_pattern = re.compile(
            r"\{[^{}]*\}|\[[^\[\]]*\]", re.DOTALL
        )
        matches = json_pattern.findall(text)
        if not matches:
            return None
        try:
            schemas = []
            for match in matches:
                try:
                    parsed = json.loads(match)
                    schema = self._extract_json_schema(parsed)
                    schemas.append(schema)
                except (json.JSONDecodeError, ValueError):
                    continue
            if schemas:
                return self._compute_sha256(json.dumps(schemas, sort_keys=True))
        except Exception:
            pass
        return None

    def _extract_json_schema(self, obj: Any) -> dict[str, Any]:
        schema: dict[str, Any] = {"type": type(obj).__name__}
        if isinstance(obj, dict):
            schema["properties"] = {
                k: self._extract_json_schema(v) for k, v in obj.items()
            }
        elif isinstance(obj, list):
            if obj:
                schema["items"] = self._extract_json_schema(obj[0])
            else:
                schema["items"] = {"type": "null"}
        elif isinstance(obj, bool):
            schema["type"] = "boolean"
        elif isinstance(obj, int):
            schema["type"] = "integer"
        elif isinstance(obj, float):
            schema["type"] = "number"
        elif isinstance(obj, str):
            schema["type"] = "string"
        return schema

    def _compute_markdown_structure_hash(
        self, text: str
    ) -> str | None:
        heading_pattern = re.compile(r"^#{1,6}\s+.*$", re.MULTILINE)
        list_pattern = re.compile(r"^[\s]*[-*+]\s+.*$", re.MULTILINE)
        code_pattern = re.compile(r"```[\s\S]*?```", re.MULTILINE)
        table_pattern = re.compile(r"\|[^\n]+\|", re.MULTILINE)

        structure = []
        for match in heading_pattern.finditer(text):
            structure.append(("heading", match.group()))
        for match in list_pattern.finditer(text):
            structure.append(("list", match.group()))
        for match in code_pattern.finditer(text):
            structure.append(("code", match.group()[:50]))
        for match in table_pattern.finditer(text):
            structure.append(("table", match.group()[:50]))

        if not structure:
            return None
        return self._compute_sha256(json.dumps(structure, sort_keys=True))

    def _is_refusal(self, result: PromptResult) -> bool:
        if result.refusal:
            return True

        refusal_patterns = [
            r"(?i)i(?:'m| am) sorry",
            r"(?i)i cannot",
            r"(?i)i can'?t",
            r"(?i)i apologize",
            r"(?i)unable to (?:complete|fulfill|process|answer)",
            r"(?i)as an ai (?:assistant|language model)",
            r"(?i)i don'?t (?:think|believe|have)",
            r"(?i)not (?:able|allowed|permitted) to",
            r"(?i)against (?:my|our) (?:policy|guidelines|principles)",
            r"(?i)sorry,? but",
        ]
        for pattern in refusal_patterns:
            if re.search(pattern, result.response[:200]):
                return True
        return False

    async def fingerprint(
        self,
        result: PromptResult,
        **kwargs: Any,
    ) -> Fingerprint:
        try:
            response_text = result.response or ""

            provider_info = None
            if result.raw_response:
                provider_info = ProviderInfo(
                    provider_name=result.provider,
                    provider_type=result.provider,
                )

            embedding = self._compute_embedding(response_text)
            json_schema_hash = self._compute_json_schema_hash(response_text)
            markdown_hash = self._compute_markdown_structure_hash(response_text)

            return Fingerprint(
                prompt_name=result.prompt_name,
                model=result.model,
                provider=result.provider,
                sha256_hash=self._compute_sha256(response_text),
                embedding=embedding,
                token_count=result.token_usage.total_tokens,
                latency_ms=result.latency.total_time_ms,
                cost_usd=result.cost.total_cost,
                refusal=self._is_refusal(result),
                stop_reason=result.stop_reason,
                finish_reason=result.finish_reason,
                json_schema_hash=json_schema_hash,
                markdown_structure_hash=markdown_hash,
                tool_call_count=len(result.tool_calls),
                function_call_count=len(result.function_calls),
                reasoning_length=result.token_usage.reasoning_tokens,
                response_length=result.response_length,
                response_hash=self._compute_sha256(response_text),
                provider_info=provider_info,
                prompt_result_id=result.id,
                run_id=result.run_id,
                extra=result.extra,
            )
        except Exception as e:
            raise FingerprintError(f"Failed to fingerprint result: {e}") from e

    def cosine_similarity(
        self,
        embedding_a: list[float],
        embedding_b: list[float],
    ) -> float:
        a = np.array(embedding_a, dtype=np.float64)
        b = np.array(embedding_b, dtype=np.float64)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
