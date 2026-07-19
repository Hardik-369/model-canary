from __future__ import annotations

import logging
from typing import Any

from model_canary.alerting.base import BaseAlerter
from model_canary.core.models import DriftReport

logger = logging.getLogger("model_canary.alerting")


class LogAlerter(BaseAlerter):
    @property
    def name(self) -> str:
        return "log"

    @property
    def alerter_type(self) -> str:
        return "log"

    async def send_alert(
        self,
        report: DriftReport,
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> bool:
        level_map = {
            "low": logging.INFO,
            "medium": logging.WARNING,
            "high": logging.ERROR,
            "critical": logging.CRITICAL,
        }
        level = level_map.get(report.severity.value, logging.WARNING)
        logger.log(level, "Drift detected: %s - %s (score: %.4f, severity: %s)",
                    report.drift_type.value, report.message, report.drift_score, report.severity.value)
        return True
