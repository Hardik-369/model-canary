from __future__ import annotations

from typing import Any

import httpx

from model_canary.alerting.base import BaseAlerter
from model_canary.core.exceptions import AlertError
from model_canary.core.models import DriftReport


class DiscordAlerter(BaseAlerter):
    @property
    def name(self) -> str:
        return "discord"

    @property
    def alerter_type(self) -> str:
        return "discord"

    async def send_alert(
        self,
        report: DriftReport,
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> bool:
        cfg = {**self._config, **(config or {})}
        webhook_url = cfg.get("webhook_url") or cfg.get("url")
        if not webhook_url:
            raise AlertError("Discord webhook URL not configured")

        embed = self._format_discord_embed(report)
        payload = {"embeds": [embed]}

        if cfg.get("content"):
            payload["content"] = cfg["content"]

        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload)
            if response.status_code >= 400:
                raise AlertError(f"Discord alert failed: {response.status_code} {response.text}")
            return True
