from __future__ import annotations

from typing import Any

import httpx

from model_canary.alerting.base import BaseAlerter
from model_canary.core.exceptions import AlertError
from model_canary.core.models import DriftReport


class GitHubAlerter(BaseAlerter):
    @property
    def name(self) -> str:
        return "github"

    @property
    def alerter_type(self) -> str:
        return "github"

    async def send_alert(
        self,
        report: DriftReport,
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> bool:
        cfg = {**self._config, **(config or {})}
        token = cfg.get("token")
        repo = cfg.get("repo")
        if not token or not repo:
            raise AlertError("GitHub token and repo required")

        title = f"[Model Canary] {report.drift_type.value}: {report.prompt_name} ({report.severity.value})"
        body = (
            f"## Drift Detected\n\n"
            f"**Type:** {report.drift_type.value}\n"
            f"**Severity:** {report.severity.value}\n"
            f"**Prompt:** {report.prompt_name}\n"
            f"**Model:** {report.model}\n"
            f"**Provider:** {report.provider}\n"
            f"**Score:** {report.drift_score:.4f}\n\n"
            f"**Message:** {report.message}\n\n"
            f"**Details:**\n```json\n{report.drift_details}\n```\n"
            f"**Run ID:** {report.run_id}"
        )

        labels = cfg.get("labels", ["model-canary", "drift"])
        if report.severity.value == "critical":
            labels.append("critical")

        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
            }
            response = await client.post(
                f"https://api.github.com/repos/{repo}/issues",
                headers=headers,
                json={"title": title, "body": body, "labels": labels},
            )
            if response.status_code >= 400:
                raise AlertError(f"GitHub alert failed: {response.status_code} {response.text}")
            return True
