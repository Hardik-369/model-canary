"""Tests for alerting system."""

import pytest
from model_canary.core.models import (
    DriftReport, DriftSeverity, DriftType, Fingerprint, DriftReport,
)


@pytest.fixture
def sample_drift():
    baseline = Fingerprint(prompt_name="test", model="gpt-4", provider="openai")
    current = Fingerprint(prompt_name="test", model="gpt-4", provider="openai")
    return DriftReport(
        run_id="test-run",
        prompt_name="test-prompt",
        model="gpt-4",
        provider="openai",
        drift_type=DriftType.OUTPUT_DRIFT,
        severity=DriftSeverity.HIGH,
        baseline_fingerprint=baseline,
        current_fingerprint=current,
        drift_score=0.85,
        message="Test alert message",
    )


class TestLogAlerter:
    @pytest.mark.asyncio
    async def test_send_alert(self, sample_drift):
        from model_canary.alerting.log import LogAlerter
        alerter = LogAlerter()
        result = await alerter.send_alert(sample_drift)
        assert result is True

    @pytest.mark.asyncio
    async def test_name_and_type(self):
        from model_canary.alerting.log import LogAlerter
        alerter = LogAlerter()
        assert alerter.name == "log"
        assert alerter.alerter_type == "log"


class TestWebhookAlerter:
    @pytest.mark.asyncio
    async def test_missing_url(self):
        from model_canary.alerting.webhook import WebhookAlerter
        from model_canary.core.exceptions import AlertError
        alerter = WebhookAlerter()
        with pytest.raises(AlertError, match="Webhook URL not configured"):
            await alerter.send_alert(self._make_drift())

    @pytest.mark.asyncio
    async def test_invalid_url(self):
        from model_canary.alerting.webhook import WebhookAlerter
        from httpx import ConnectError
        alerter = WebhookAlerter({"url": "http://nonexistent.example.com/webhook"})
        with pytest.raises(ConnectError):
            await alerter.send_alert(self._make_drift())

    def _make_drift(self):
        fp = Fingerprint(prompt_name="test", model="gpt-4", provider="openai")
        return DriftReport(
            run_id="test", prompt_name="test", model="gpt-4", provider="openai",
            drift_type=DriftType.OUTPUT_DRIFT, severity=DriftSeverity.MEDIUM,
            baseline_fingerprint=fp, current_fingerprint=fp, drift_score=0.5,
        )


class TestBaseAlerter:
    @pytest.mark.asyncio
    async def test_format_message(self):
        from model_canary.alerting.log import LogAlerter
        alerter = LogAlerter()
        fp = Fingerprint(prompt_name="test", model="gpt-4", provider="openai")
        drift = DriftReport(
            run_id="test-run", prompt_name="test-prompt", model="gpt-4",
            provider="openai", drift_type=DriftType.OUTPUT_DRIFT,
            severity=DriftSeverity.CRITICAL, baseline_fingerprint=fp,
            current_fingerprint=fp, drift_score=0.95,
            message="Critical drift!",
        )
        msg = alerter._format_message(drift)
        assert "CRITICAL" in msg
        assert "output_drift" in msg
        assert "test-prompt" in msg

    def test_discord_embed(self):
        from model_canary.alerting.log import LogAlerter
        alerter = LogAlerter()
        fp = Fingerprint(prompt_name="test", model="gpt-4", provider="openai")
        drift = DriftReport(
            run_id="test-run", prompt_name="test-prompt", model="gpt-4",
            provider="openai", drift_type=DriftType.LATENCY_SPIKE,
            severity=DriftSeverity.HIGH, baseline_fingerprint=fp,
            current_fingerprint=fp, drift_score=0.8,
        )
        embed = alerter._format_discord_embed(drift)
        assert embed["title"] == "Drift Detected: latency_spike"
        assert embed["color"] == 0xFF0000


class TestFactory:
    def test_create_log_alerter(self):
        from model_canary.alerting.factory import create_alerter
        alerter = create_alerter("log")
        assert alerter.name == "log"

    def test_create_slack_alerter(self):
        from model_canary.alerting.factory import create_alerter
        alerter = create_alerter("slack", {"webhook_url": "https://hooks.slack.com/test"})
        assert alerter.name == "slack"

    def test_create_unknown(self):
        from model_canary.alerting.factory import create_alerter
        with pytest.raises(ValueError, match="Alerter 'unknown' not found"):
            create_alerter("unknown")
