from __future__ import annotations

from typing import Any

from model_canary.core.models import (
    DriftReport,
    DriftSeverity,
    DriftType,
    Fingerprint,
    PromptConfig,
)


class DriftDetectionEngine:
    def __init__(
        self,
        similarity_threshold: float = 0.85,
        drift_threshold: float = 0.1,
        latency_threshold_pct: float = 50.0,
        cost_threshold_pct: float = 50.0,
        token_threshold_pct: float = 30.0,
    ) -> None:
        self._similarity_threshold = similarity_threshold
        self._drift_threshold = drift_threshold
        self._latency_threshold_pct = latency_threshold_pct
        self._cost_threshold_pct = cost_threshold_pct
        self._token_threshold_pct = token_threshold_pct

    async def detect(
        self,
        baseline: Fingerprint,
        current: Fingerprint,
        prompt_config: PromptConfig | None = None,
        **kwargs: Any,
    ) -> list[DriftReport]:
        reports: list[DriftReport] = []

        output_report = self._detect_output_drift(baseline, current)
        if output_report:
            reports.append(output_report)

        semantic_report = await self._detect_semantic_drift(baseline, current)
        if semantic_report:
            reports.append(semantic_report)

        structural_report = self._detect_structural_drift(baseline, current)
        if structural_report:
            reports.append(structural_report)

        latency_report = self._detect_latency_drift(baseline, current)
        if latency_report:
            reports.append(latency_report)

        cost_report = self._detect_cost_drift(baseline, current)
        if cost_report:
            reports.append(cost_report)

        refusal_report = self._detect_refusal_drift(baseline, current)
        if refusal_report:
            reports.append(refusal_report)

        tool_report = self._detect_tool_calling_drift(baseline, current)
        if tool_report:
            reports.append(tool_report)

        json_report = self._detect_json_schema_drift(baseline, current)
        if json_report:
            reports.append(json_report)

        token_report = self._detect_token_usage_drift(baseline, current)
        if token_report:
            reports.append(token_report)

        reasoning_report = self._detect_reasoning_drift(baseline, current)
        if reasoning_report:
            reports.append(reasoning_report)

        return reports

    def _calculate_drift_score(
        self,
        baseline_value: float,
        current_value: float,
        threshold: float = 0.1,
    ) -> tuple[float, float]:
        if baseline_value == 0:
            if current_value == 0:
                return 0.0, 0.0
            return 1.0, float("inf")

        pct_change = abs((current_value - baseline_value) / baseline_value)
        score = min(pct_change / threshold, 1.0) if threshold > 0 else 0.0
        return score, pct_change

    def _classify_severity(
        self, drift_score: float, pct_change: float
    ) -> DriftSeverity:
        if drift_score >= 0.9 or pct_change > 5.0:
            return DriftSeverity.CRITICAL
        if drift_score >= 0.7 or pct_change > 2.0:
            return DriftSeverity.HIGH
        if drift_score >= 0.4 or pct_change > 0.5:
            return DriftSeverity.MEDIUM
        return DriftSeverity.LOW

    def _detect_output_drift(
        self, baseline: Fingerprint, current: Fingerprint
    ) -> DriftReport | None:
        if baseline.sha256_hash != current.sha256_hash:
            similarity = 0.0
            if baseline.embedding and current.embedding:
                from model_canary.fingerprinting.engine import FingerprintingEngine

                engine = FingerprintingEngine()
                similarity = engine.cosine_similarity(
                    baseline.embedding, current.embedding
                )

            drift_score = 1.0 - similarity if similarity > 0 else 1.0
            severity = self._classify_severity(drift_score, 1.0 - similarity)
            return DriftReport(
                run_id=current.run_id,
                prompt_name=current.prompt_name,
                model=current.model,
                provider=current.provider,
                drift_type=DriftType.OUTPUT_DRIFT,
                severity=severity,
                baseline_fingerprint=baseline,
                current_fingerprint=current,
                drift_score=drift_score,
                drift_details={
                    "baseline_hash": baseline.sha256_hash[:16],
                    "current_hash": current.sha256_hash[:16],
                    "cosine_similarity": similarity,
                    "threshold": self._similarity_threshold,
                },
                metrics={"cosine_similarity": similarity},
                previous_value=baseline.sha256_hash[:16],
                current_value=current.sha256_hash[:16],
                threshold=self._similarity_threshold,
                message=f"Output drift detected for '{current.prompt_name}' "
                f"on {current.model} (hash differs)",
            )
        return None

    async def _detect_semantic_drift(
        self, baseline: Fingerprint, current: Fingerprint
    ) -> DriftReport | None:
        if baseline.embedding and current.embedding:
            from model_canary.fingerprinting.engine import FingerprintingEngine

            engine = FingerprintingEngine()
            similarity = engine.cosine_similarity(
                baseline.embedding, current.embedding
            )

            if similarity < self._similarity_threshold * 0.9:
                drift_score = 1.0 - similarity
                severity = self._classify_severity(drift_score, 1.0 - similarity)
                return DriftReport(
                    run_id=current.run_id,
                    prompt_name=current.prompt_name,
                    model=current.model,
                    provider=current.provider,
                    drift_type=DriftType.SEMANTIC_DRIFT,
                    severity=severity,
                    baseline_fingerprint=baseline,
                    current_fingerprint=current,
                    drift_score=drift_score,
                    drift_details={
                        "cosine_similarity": similarity,
                        "threshold": self._similarity_threshold,
                    },
                    metrics={"cosine_similarity": similarity},
                    previous_value=f"{similarity:.4f}",
                    current_value=f"{similarity:.4f}",
                    threshold=self._similarity_threshold,
                    message=f"Semantic drift detected for '{current.prompt_name}' "
                    f"on {current.model} (similarity: {similarity:.4f})",
                )
        return None

    def _detect_structural_drift(
        self, baseline: Fingerprint, current: Fingerprint
    ) -> DriftReport | None:
        if baseline.markdown_structure_hash and current.markdown_structure_hash:
            if baseline.markdown_structure_hash != current.markdown_structure_hash:
                return DriftReport(
                    run_id=current.run_id,
                    prompt_name=current.prompt_name,
                    model=current.model,
                    provider=current.provider,
                    drift_type=DriftType.STRUCTURAL_DRIFT,
                    severity=DriftSeverity.MEDIUM,
                    baseline_fingerprint=baseline,
                    current_fingerprint=current,
                    drift_score=1.0,
                    drift_details={
                        "baseline_structure": baseline.markdown_structure_hash[:16],
                        "current_structure": current.markdown_structure_hash[:16],
                    },
                    previous_value=baseline.markdown_structure_hash[:16],
                    current_value=current.markdown_structure_hash[:16],
                    message=f"Structural drift detected for '{current.prompt_name}' "
                    f"on {current.model}",
                )
        return None

    def _detect_latency_drift(
        self, baseline: Fingerprint, current: Fingerprint
    ) -> DriftReport | None:
        if baseline.latency_ms > 0 and current.latency_ms > 0:
            score, pct_change = self._calculate_drift_score(
                baseline.latency_ms, current.latency_ms, self._latency_threshold_pct / 100.0
            )
            if score > self._drift_threshold:
                severity = self._classify_severity(score, pct_change)
                return DriftReport(
                    run_id=current.run_id,
                    prompt_name=current.prompt_name,
                    model=current.model,
                    provider=current.provider,
                    drift_type=DriftType.LATENCY_SPIKE,
                    severity=severity,
                    baseline_fingerprint=baseline,
                    current_fingerprint=current,
                    drift_score=score,
                    drift_details={
                        "baseline_latency_ms": baseline.latency_ms,
                        "current_latency_ms": current.latency_ms,
                        "pct_change": pct_change * 100,
                    },
                    metrics={
                        "baseline_latency_ms": baseline.latency_ms,
                        "current_latency_ms": current.latency_ms,
                        "pct_change": pct_change * 100,
                    },
                    previous_value=f"{baseline.latency_ms:.1f}ms",
                    current_value=f"{current.latency_ms:.1f}ms",
                    threshold=self._latency_threshold_pct,
                    message=f"Latency spike detected for '{current.prompt_name}' "
                    f"on {current.model} ({pct_change * 100:.1f}% change)",
                )
        return None

    def _detect_cost_drift(
        self, baseline: Fingerprint, current: Fingerprint
    ) -> DriftReport | None:
        if baseline.cost_usd > 0 and current.cost_usd > 0:
            score, pct_change = self._calculate_drift_score(
                baseline.cost_usd, current.cost_usd, self._cost_threshold_pct / 100.0
            )
            if score > self._drift_threshold:
                severity = self._classify_severity(score, pct_change)
                return DriftReport(
                    run_id=current.run_id,
                    prompt_name=current.prompt_name,
                    model=current.model,
                    provider=current.provider,
                    drift_type=DriftType.COST_SPIKE,
                    severity=severity,
                    baseline_fingerprint=baseline,
                    current_fingerprint=current,
                    drift_score=score,
                    drift_details={
                        "baseline_cost": baseline.cost_usd,
                        "current_cost": current.cost_usd,
                        "pct_change": pct_change * 100,
                    },
                    metrics={
                        "baseline_cost_usd": baseline.cost_usd,
                        "current_cost_usd": current.cost_usd,
                        "pct_change": pct_change * 100,
                    },
                    previous_value=f"${baseline.cost_usd:.6f}",
                    current_value=f"${current.cost_usd:.6f}",
                    threshold=self._cost_threshold_pct,
                    message=f"Cost spike detected for '{current.prompt_name}' "
                    f"on {current.model} ({pct_change * 100:.1f}% change)",
                )
        return None

    def _detect_refusal_drift(
        self, baseline: Fingerprint, current: Fingerprint
    ) -> DriftReport | None:
        if baseline.refusal != current.refusal:
            return DriftReport(
                run_id=current.run_id,
                prompt_name=current.prompt_name,
                model=current.model,
                provider=current.provider,
                drift_type=DriftType.REFUSAL_INCREASE,
                severity=DriftSeverity.HIGH if current.refusal else DriftSeverity.LOW,
                baseline_fingerprint=baseline,
                current_fingerprint=current,
                drift_score=1.0 if current.refusal else 0.5,
                drift_details={
                    "baseline_refusal": baseline.refusal,
                    "current_refusal": current.refusal,
                },
                previous_value=str(baseline.refusal),
                current_value=str(current.refusal),
                message=f"Refusal behavior changed for '{current.prompt_name}' "
                f"on {current.model} (baseline: {baseline.refusal}, current: {current.refusal})",
            )
        return None

    def _detect_tool_calling_drift(
        self, baseline: Fingerprint, current: Fingerprint
    ) -> DriftReport | None:
        if baseline.tool_call_count != current.tool_call_count:
            score, pct_change = self._calculate_drift_score(
                float(max(baseline.tool_call_count, 1)),
                float(max(current.tool_call_count, 1)),
            )
            severity = self._classify_severity(score, pct_change)
            return DriftReport(
                run_id=current.run_id,
                prompt_name=current.prompt_name,
                model=current.model,
                provider=current.provider,
                drift_type=DriftType.TOOL_FAILURE,
                severity=severity,
                baseline_fingerprint=baseline,
                current_fingerprint=current,
                drift_score=score,
                drift_details={
                    "baseline_tool_calls": baseline.tool_call_count,
                    "current_tool_calls": current.tool_call_count,
                },
                metrics={
                    "baseline_tool_calls": baseline.tool_call_count,
                    "current_tool_calls": current.tool_call_count,
                },
                previous_value=str(baseline.tool_call_count),
                current_value=str(current.tool_call_count),
                message=f"Tool calling behavior changed for '{current.prompt_name}' "
                f"on {current.model} ({baseline.tool_call_count} -> {current.tool_call_count} calls)",
            )
        return None

    def _detect_json_schema_drift(
        self, baseline: Fingerprint, current: Fingerprint
    ) -> DriftReport | None:
        if baseline.json_schema_hash and current.json_schema_hash:
            if baseline.json_schema_hash != current.json_schema_hash:
                return DriftReport(
                    run_id=current.run_id,
                    prompt_name=current.prompt_name,
                    model=current.model,
                    provider=current.provider,
                    drift_type=DriftType.JSON_FAILURE,
                    severity=DriftSeverity.HIGH,
                    baseline_fingerprint=baseline,
                    current_fingerprint=current,
                    drift_score=1.0,
                    drift_details={
                        "baseline_schema": baseline.json_schema_hash[:16],
                        "current_schema": current.json_schema_hash[:16],
                    },
                    previous_value=baseline.json_schema_hash[:16],
                    current_value=current.json_schema_hash[:16],
                    message=f"JSON schema drift detected for '{current.prompt_name}' "
                    f"on {current.model}",
                )
        return None

    def _detect_token_usage_drift(
        self, baseline: Fingerprint, current: Fingerprint
    ) -> DriftReport | None:
        if baseline.token_count > 0 and current.token_count > 0:
            score, pct_change = self._calculate_drift_score(
                baseline.token_count, current.token_count, self._token_threshold_pct / 100.0
            )
            if score > self._drift_threshold:
                severity = self._classify_severity(score, pct_change)
                return DriftReport(
                    run_id=current.run_id,
                    prompt_name=current.prompt_name,
                    model=current.model,
                    provider=current.provider,
                    drift_type=DriftType.TOKEN_USAGE_DRIFT,
                    severity=severity,
                    baseline_fingerprint=baseline,
                    current_fingerprint=current,
                    drift_score=score,
                    drift_details={
                        "baseline_tokens": baseline.token_count,
                        "current_tokens": current.token_count,
                        "pct_change": pct_change * 100,
                    },
                    metrics={
                        "baseline_tokens": baseline.token_count,
                        "current_tokens": current.token_count,
                        "pct_change": pct_change * 100,
                    },
                    previous_value=str(baseline.token_count),
                    current_value=str(current.token_count),
                    threshold=self._token_threshold_pct,
                    message=f"Token usage drift detected for '{current.prompt_name}' "
                    f"on {current.model} ({pct_change * 100:.1f}% change)",
                )
        return None

    def _detect_reasoning_drift(
        self, baseline: Fingerprint, current: Fingerprint
    ) -> DriftReport | None:
        if baseline.reasoning_length is not None and current.reasoning_length is not None:
            if baseline.reasoning_length > 0 and current.reasoning_length > 0:
                score, pct_change = self._calculate_drift_score(
                    baseline.reasoning_length, current.reasoning_length
                )
                if score > self._drift_threshold:
                    severity = self._classify_severity(score, pct_change)
                    return DriftReport(
                        run_id=current.run_id,
                        prompt_name=current.prompt_name,
                        model=current.model,
                        provider=current.provider,
                        drift_type=DriftType.REASONING_DEGRADATION,
                        severity=severity,
                        baseline_fingerprint=baseline,
                        current_fingerprint=current,
                        drift_score=score,
                        drift_details={
                            "baseline_reasoning_tokens": baseline.reasoning_length,
                            "current_reasoning_tokens": current.reasoning_length,
                            "pct_change": pct_change * 100,
                        },
                        metrics={
                            "baseline_reasoning_tokens": baseline.reasoning_length,
                            "current_reasoning_tokens": current.reasoning_length,
                            "pct_change": pct_change * 100,
                        },
                        previous_value=str(baseline.reasoning_length),
                        current_value=str(current.reasoning_length),
                        message=f"Reasoning drift detected for '{current.prompt_name}' "
                        f"on {current.model} ({pct_change * 100:.1f}% change in reasoning tokens)",
                    )
        return None

    async def detect_all(
        self,
        baseline: Fingerprint,
        current: Fingerprint,
        prompt_config: PromptConfig | None = None,
    ) -> list[DriftReport]:
        return await self.detect(baseline, current, prompt_config)
