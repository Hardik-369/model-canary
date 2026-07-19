from __future__ import annotations

from typing import Any

import httpx

from model_canary.alerting.base import BaseAlerter
from model_canary.core.exceptions import AlertError
from model_canary.core.models import DriftReport


class WebhookAlerter(BaseAlerter):
    @property
    def name(self) -> str:
        return "webhook"

    @property
    def alerter_type(self) -> str:
        return "webhook"

    async def send_alert(
        self,
        report: DriftReport,
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> bool:
        cfg = {**self._config, **(config or {})}
        url = cfg.get("url")
        if not url:
            raise AlertError("Webhook URL not configured")

        method = cfg.get("method", "POST").upper()
        headers = cfg.get("headers", {"Content-Type": "application/json"})
        secret = cfg.get("secret")

        payload = {
            "event": "drift_detected",
            "report": report.model_dump(mode='json'),
            "source": "model-canary",
        }

        if secret:
            import hashlib
            import hmac
            import json as _json
            body = _json.dumps(payload)
            signature = hmac.new(
                secret.encode(), body.encode(), hashlib.sha256
            ).hexdigest()
            headers["X-Model-Canary-Signature"] = signature

        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, json=payload, headers=headers)
            if response.status_code >= 400:
                raise AlertError(f"Webhook alert failed: {response.status_code} {response.text}")
            return True
