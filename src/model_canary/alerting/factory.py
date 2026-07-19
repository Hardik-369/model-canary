from __future__ import annotations

from typing import Any

from model_canary.core.interfaces import Alerter


def create_alerter(
    name: str, config: dict[str, Any] | None = None
) -> Alerter:
    name = name.lower()

    alerters: dict[str, str] = {
        "log": "model_canary.alerting.log:LogAlerter",
        "slack": "model_canary.alerting.slack:SlackAlerter",
        "discord": "model_canary.alerting.discord:DiscordAlerter",
        "github": "model_canary.alerting.github:GitHubAlerter",
        "webhook": "model_canary.alerting.webhook:WebhookAlerter",
    }

    if name in alerters:
        module_path, class_name = alerters[name].split(":")
        import importlib

        module = importlib.import_module(module_path)
        cls: type[Alerter] = getattr(module, class_name)
        return cls(config or {})

    import importlib.metadata

    for ep in importlib.metadata.entry_points(group="model_canary.alerters"):
        if ep.name == name:
            cls = ep.load()
            return cls(config or {})

    raise ValueError(
        f"Alerter '{name}' not found. Built-in alerters: {', '.join(alerters)}"
    )
