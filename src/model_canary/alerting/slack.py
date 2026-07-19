from __future__ import annotations

from typing import Any

import httpx

from model_canary.alerting.base import BaseAlerter
from model_canary.core.exceptions import AlertError
from model_canary.core.models import DriftReport


class SlackAlerter(BaseAlerter):
    @property
    def name(self) -> str:
        return "slack"

    @property
    def alerter_type(self) -> str:
        return "slack"

    async def send_alert(
        self,
        report: DriftReport,
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> bool:
        cfg = {**self._config, **(config or {})}
        webhook_url = cfg.get("webhook_url") or cfg.get("url")
        if not webhook_url:
            raise AlertError("Slack webhook URL not configured")

        channel = cfg.get("channel", "#model-canary-alerts")
        message = self._format_message(report)

        payload = {
            "channel": channel,
            "username": "Model Canary",
            "icon_emoji": ":canary:",
            "text": message,
            "attachments": [
                {
                    "color": "danger" if report.severity.value in ("high", "critical") else "warning",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": f"*{report.drift_type.value}*\n{report.message}"},
                        },
                        {
                            "type": "section",
                            "fields": [
                                {"type": "mrkdwn", "text": f"*Prompt:*\n{report.prompt_name}"},
                                {"type": "mrkdwn", "text": f"*Model:*\n{report.model}"},
                                {"type": "mrkdwn", "text": f"*Severity:*\n{report.severity.value}"},
                                {"type": "mrkdwn", "text": f"*Score:*\n{report.drift_score:.4f}"},
                            ],
                        },
                    ],
                }
            ],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload)
            if response.status_code >= 400:
                raise AlertError(f"Slack alert failed: {response.status_code} {response.text}")
            return True
