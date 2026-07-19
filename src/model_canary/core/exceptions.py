from __future__ import annotations


class ModelCanaryError(Exception):
    """Base exception for all Model Canary errors."""

    def __init__(self, message: str = "", details: str = "") -> None:
        self.details = details
        super().__init__(message)


class ProviderError(ModelCanaryError):
    """Base exception for provider-related errors."""


class ProviderAuthError(ProviderError):
    """Authentication failed with the provider."""


class ProviderRateLimitError(ProviderError):
    """Rate limited by the provider."""


class ProviderTimeoutError(ProviderError):
    """Provider request timed out."""


class ProviderNotFoundError(ProviderError):
    """Provider not found or not configured."""


class ProviderUnavailableError(ProviderError):
    """Provider is temporarily unavailable."""


class EvaluationError(ModelCanaryError):
    """Error during prompt evaluation."""


class StorageError(ModelCanaryError):
    """Error in storage backend operations."""


class FingerprintError(ModelCanaryError):
    """Error during fingerprinting."""


class DriftDetectionError(ModelCanaryError):
    """Error during drift detection."""


class AlertError(ModelCanaryError):
    """Error sending alert."""


class PluginError(ModelCanaryError):
    """Error in plugin system."""


class PluginNotFoundError(PluginError):
    """Plugin not found."""


class PluginLoadError(PluginError):
    """Failed to load plugin."""


class ConfigError(ModelCanaryError):
    """Configuration error."""


class ConfigValidationError(ConfigError):
    """Configuration validation failed."""


class ConfigNotFoundError(ConfigError):
    """Configuration file not found."""


class ValidationError(ModelCanaryError):
    """Validation error."""


class ScheduleError(ModelCanaryError):
    """Scheduler error."""


class MetricsError(ModelCanaryError):
    """Metrics collection error."""


class ReportError(ModelCanaryError):
    """Report generation error."""


class BenchmarkError(ModelCanaryError):
    """Benchmark error."""
