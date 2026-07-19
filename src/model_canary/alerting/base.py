from __future__ import annotations

from typing import Any

from model_canary.core.interfaces import Alerter
from model_canary.core.models import DriftReport, DriftSeverity


class BaseAlerter(Alerter):
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}

    @property
    def config(self) -> dict[str, Any]:
        return self._config

    def _format_message(self, report: DriftReport) -> str:
        emoji_map = {
            DriftSeverity.LOW: " INFO",
            DriftSeverity.MEDIUM: " WARN",
            DriftSeverity.HIGH: " HIGH",
            DriftSeverity.CRITICAL: " CRITICAL",
        }
        emoji = emoji_map.get(report.severity, " INFO")
        return (
            f"{emoji} Drift Detected: {report.drift_type.value}\n"
            f"Prompt: {report.prompt_name}\n"
            f"Model: {report.model}\n"
            f"Provider: {report.provider}\n"
            f"Severity: {report.severity.value}\n"
            f"Score: {report.drift_score:.4f}\n"
            f"Message: {report.message}\n"
            f"Run: {report.run_id}"
        )

    def _format_discord_embed(self, report: DriftReport) -> dict[str, Any]:
        color_map = {
            DriftSeverity.LOW: 0xFFFF00,
            DriftSeverity.MEDIUM: 0xFFA500,
            DriftSeverity.HIGH: 0xFF0000,
            DriftSeverity.CRITICAL: 0x800000,
        }
        return {
            "title": f"Drift Detected: {report.drift_type.value}",
            "description": report.message,
            "color": color_map.get(report.severity, 0xFFFF00),
            "fields": [
                {"name": "Prompt", "value": report.prompt_name, "inline": True},
                {"name": "Model", "value": report.model, "inline": True},
                {"name": "Provider", "value": report.provider, "inline": True},
                {"name": "Severity", "value": report.severity.value, "inline": True},
                {"name": "Drift Score", "value": f"{report.drift_score:.4f}", "inline": True},
                {"name": "Run ID", "value": report.run_id, "inline": False},
            ],
            "timestamp": report.timestamp.isoformat(),
        }
