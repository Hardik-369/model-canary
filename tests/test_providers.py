from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch, ANY

import pytest

# Mock litellm before any provider modules are imported
_litellm_mock = MagicMock()
_litellm_mock.acompletion = AsyncMock()
_litellm_mock.amodel_list = AsyncMock()
sys.modules["litellm"] = _litellm_mock

from model_canary.core.models import (
    Fingerprint,
    ProviderConfig,
    LatencyMetrics,
    DriftReport,
    DriftSeverity,
    DriftType,
    PromptResult,
    TokenUsage,
    CostMetrics,
)
from model_canary.providers.base import BaseProvider
from model_canary.providers.factory import create_provider, get_available_providers
from model_canary.providers.registry import ProviderRegistry, get_provider_registry, register_providers


def _provider_config(name="test", ptype="openai", **kw):
    return ProviderConfig(name=name, type=ptype, **kw)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def provider_config():
    return ProviderConfig(
        name="test-provider",
        type="openai",
        api_key="sk-test-key",
        default_model="gpt-4o",
        base_url="https://api.openai.com/v1",
        organization="test-org",
        timeout=30.0,
        max_retries=3,
        retry_delay=1.0,
    )


@pytest.fixture(autouse=True)
def reset_registry():
    registry = get_provider_registry()
    saved = dict(registry._providers)
    registry._providers.clear()
    yield
    registry._providers.clear()
    registry._providers.update(saved)


@pytest.fixture(autouse=True)
def reset_litellm_mock():
    _litellm_mock.reset_mock()
    _litellm_mock.acompletion = AsyncMock()
    _litellm_mock.amodel_list = AsyncMock()


# =============================================================================
# ProviderRegistry Tests
# =============================================================================

class TestProviderRegistry:
    def test_register_and_get(self):
        registry = ProviderRegistry()
        mock_cls = MagicMock()
        registry.register("test_provider", mock_cls)
        assert registry.get("test_provider") == mock_cls
        assert registry.is_registered("test_provider") is True

    def test_register_lowercase(self):
        registry = ProviderRegistry()
        mock_cls = MagicMock()
        registry.register("MixedCase", mock_cls)
        assert registry.get("mixedcase") == mock_cls
        assert registry.get("MIXEDCASE") == mock_cls

    def test_get_not_found(self):
        registry = ProviderRegistry()
        from model_canary.core.exceptions import PluginNotFoundError
        with pytest.raises(PluginNotFoundError):
            registry.get("nonexistent")

    def test_unregister(self):
        registry = ProviderRegistry()
        mock_cls = MagicMock()
        registry.register("test", mock_cls)
        registry.unregister("test")
        assert registry.is_registered("test") is False

    def test_list(self):
        registry = ProviderRegistry()
        mock_cls = MagicMock()
        registry.register("a", mock_cls)
        registry.register("b", mock_cls)
        items = registry.list()
        assert "a" in items
        assert "b" in items
        assert len(items) == 2

    def test_singleton(self):
        r1 = ProviderRegistry.get_instance()
        r2 = ProviderRegistry.get_instance()
        assert r1 is r2


# =============================================================================
# Provider Factory Tests
# =============================================================================

class TestProviderFactory:
    def test_create_provider_with_registry(self):
        registry = ProviderRegistry()
        mock_cls = MagicMock()
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        registry.register("openai", mock_cls)

        config = _provider_config(name="test", ptype="openai", api_key="sk-test")
        provider = create_provider(config, registry=registry)
        assert provider is mock_instance

    def test_create_provider_default_registry(self, provider_config):
        registry = get_provider_registry()
        mock_cls = MagicMock()
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        registry.register("openai", mock_cls)

        provider = create_provider(provider_config)
        assert provider is mock_instance

    def test_create_provider_error(self):
        registry = ProviderRegistry()
        mock_cls = MagicMock(side_effect=ValueError("creation failed"))
        registry.register("openai", mock_cls)

        config = _provider_config(name="test", ptype="openai", api_key="sk-test")
        from model_canary.core.exceptions import ProviderError
        with pytest.raises(ProviderError, match="Failed to create provider"):
            create_provider(config, registry=registry)

    def test_create_provider_not_found(self):
        config = _provider_config(name="test", ptype="nonexistent", api_key="sk-test")
        from model_canary.core.exceptions import ProviderNotFoundError
        with pytest.raises(ProviderNotFoundError):
            create_provider(config, registry=ProviderRegistry())

    def test_get_available_providers_empty(self):
        registry = get_provider_registry()
        registry._providers.clear()
        avail = get_available_providers()
        assert isinstance(avail, dict)

    def test_get_available_providers_with_registered(self):
        registry = get_provider_registry()
        mock_cls = MagicMock()
        mock_cls.__module__ = "test_module"
        registry.register("openai", mock_cls)
        avail = get_available_providers()
        assert "openai" in avail


# =============================================================================
# BaseProvider Tests (using a concrete subclass)
# =============================================================================

class TestBaseProvider:
    @pytest.fixture
    def mock_provider_cls(self):
        class ConcreteProvider(BaseProvider):
            @property
            def provider_type(self) -> str:
                return "concrete"

            def _get_headers(self) -> dict[str, str]:
                return {"Authorization": "Bearer test"}

            def _get_api_url(self) -> str:
                return "https://api.test.com/v1"

            async def complete(self, prompt, model=None, max_tokens=None, temperature=None, **kwargs):
                return PromptResult(
                    prompt_name=kwargs.get("prompt_name", "test"),
                    prompt_text=prompt,
                    model=model or "test-model",
                    provider=self.name,
                    response="test response",
                    latency=LatencyMetrics(total_time=0.5, total_time_ms=500.0),
                    token_usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
                    cost=CostMetrics(total_cost=0.001, cost_per_prompt_token=0.0001, cost_per_completion_token=0.00005),
                )

            async def list_models(self):
                return []

        return ConcreteProvider

    @pytest.fixture
    def provider(self, mock_provider_cls, provider_config):
        return mock_provider_cls(config=provider_config)

    def test_provider_name(self, provider):
        assert provider.name == "test-provider"

    def test_provider_config(self, provider):
        assert provider.config.default_model == "gpt-4o"

    def test_get_api_url(self, provider):
        assert provider._get_api_url() == "https://api.test.com/v1"

    def test_get_headers(self, provider):
        assert provider._get_headers() == {"Authorization": "Bearer test"}

    @pytest.mark.asyncio
    async def test_complete(self, provider):
        result = await provider.complete("Hello", model="gpt-4o", prompt_name="test-prompt")
        assert result.response == "test response"
        assert result.model == "gpt-4o"
        assert result.prompt_name == "test-prompt"

    @pytest.mark.asyncio
    async def test_check_health_success(self, provider, mock_provider_cls):
        with patch.object(mock_provider_cls, 'list_models', new=AsyncMock(return_value=[MagicMock()])):
            healthy = await provider.check_health()
            assert healthy is True

    @pytest.mark.asyncio
    async def test_check_health_failure(self, provider, mock_provider_cls):
        from model_canary.core.exceptions import ProviderError
        with patch.object(mock_provider_cls, 'list_models', new=AsyncMock(side_effect=ProviderError("fail"))):
            healthy = await provider.check_health()
            assert healthy is False

    @pytest.mark.asyncio
    async def test_close(self, provider):
        await provider.close()
        assert provider._client is None

    @pytest.mark.asyncio
    async def test_make_request_success(self, provider):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "test", "choices": []}

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)

        with patch.object(provider, '_get_client', new=AsyncMock(return_value=mock_client)):
            result = await provider._make_request("POST", "/chat/completions", {"model": "test"})
            assert result == {"id": "test", "choices": []}

    @pytest.mark.asyncio
    async def test_make_request_auth_error(self, provider):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)

        from model_canary.core.exceptions import ProviderAuthError
        with patch.object(provider, '_get_client', new=AsyncMock(return_value=mock_client)):
            with pytest.raises(ProviderAuthError, match="Authentication failed"):
                await provider._make_request("GET", "/models")

    @pytest.mark.asyncio
    async def test_make_request_rate_limit(self, provider):
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limited"

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)

        from model_canary.core.exceptions import ProviderRateLimitError
        with patch.object(provider, '_get_client', new=AsyncMock(return_value=mock_client)):
            with pytest.raises(ProviderRateLimitError, match="Rate limited"):
                await provider._make_request("GET", "/models")

    @pytest.mark.asyncio
    async def test_make_request_timeout_retry(self, provider):
        from httpx import TimeoutException

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=[
            TimeoutException("timeout"),
            TimeoutException("timeout"),
            TimeoutException("timeout"),
        ])

        from model_canary.core.exceptions import ProviderTimeoutError
        with patch.object(provider, '_get_client', new=AsyncMock(return_value=mock_client)):
            with pytest.raises(ProviderTimeoutError, match="timed out"):
                await provider._make_request("GET", "/models")

    @pytest.mark.asyncio
    async def test_make_request_http_error_retry(self, provider):
        from httpx import HTTPStatusError

        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=[
            HTTPStatusError("rate limit", request=MagicMock(), response=rate_limit_response),
            HTTPStatusError("rate limit", request=MagicMock(), response=rate_limit_response),
            HTTPStatusError("rate limit", request=MagicMock(), response=rate_limit_response),
        ])

        from model_canary.core.exceptions import ProviderError
        with patch.object(provider, '_get_client', new=AsyncMock(return_value=mock_client)):
            with pytest.raises(ProviderError, match="HTTP error"):
                await provider._make_request("GET", "/models")


# =============================================================================
# Litellm-based Provider Tests
# =============================================================================

class TestLitellmProviders:
    @pytest.fixture
    def provider_config(self):
        return ProviderConfig(
            name="test-llm",
            type="openai",
            api_key="sk-test",
            default_model="gpt-4o",
        )

    @pytest.fixture
    def mock_openai_response(self):
        msg = MagicMock()
        msg.content = "Hello! How can I help you?"
        msg.tool_calls = None
        msg.refusal = None

        choice = MagicMock()
        choice.message = msg
        choice.finish_reason = "stop"

        usage = MagicMock()
        usage.prompt_tokens = 10
        usage.completion_tokens = 20
        usage.total_tokens = 30

        response = MagicMock()
        response.choices = [choice]
        response.usage = usage
        response.model_dump.return_value = {"id": "test", "choices": [], "usage": {"prompt_tokens": 10}}
        return response

    def _import_provider(self, module_path, class_name):
        import importlib
        mod = importlib.import_module(module_path)
        return getattr(mod, class_name)

    @pytest.mark.asyncio
    async def test_openai_complete(self, provider_config, mock_openai_response):
        _litellm_mock.acompletion = AsyncMock(return_value=mock_openai_response)
        OpenAIProvider = self._import_provider("model_canary.providers.openai", "OpenAIProvider")
        provider = OpenAIProvider(config=provider_config)

        result = await provider.complete("Hello", prompt_name="test-prompt")
        assert result.response == "Hello! How can I help you?"
        assert result.model == "gpt-4o"
        assert result.finish_reason == "stop"
        assert result.token_usage.total_tokens == 30
        assert result.refusal is False
        assert result.success is True

    @pytest.mark.asyncio
    async def test_openai_complete_error(self, provider_config):
        _litellm_mock.acompletion = AsyncMock(side_effect=Exception("API error"))
        OpenAIProvider = self._import_provider("model_canary.providers.openai", "OpenAIProvider")
        provider = OpenAIProvider(config=provider_config)

        result = await provider.complete("Hello", prompt_name="test-prompt")
        assert result.error == "API error"
        assert result.response == ""
        assert result.success is False

    @pytest.mark.asyncio
    async def test_openai_list_models(self, provider_config):
        _litellm_mock.amodel_list = AsyncMock(return_value=[{"id": "gpt-4o"}])
        OpenAIProvider = self._import_provider("model_canary.providers.openai", "OpenAIProvider")
        provider = OpenAIProvider(config=provider_config)

        models = await provider.list_models()
        assert len(models) == 1
        assert models[0].model_name == "gpt-4o"

    @pytest.mark.asyncio
    async def test_openai_list_models_error(self, provider_config):
        _litellm_mock.amodel_list = AsyncMock(side_effect=Exception("list error"))
        OpenAIProvider = self._import_provider("model_canary.providers.openai", "OpenAIProvider")
        provider = OpenAIProvider(config=provider_config)

        models = await provider.list_models()
        assert len(models) == 1
        assert models[0].model_name == "gpt-4o"

    @pytest.mark.asyncio
    async def test_openai_with_base_url(self, provider_config):
        provider_config.base_url = "https://custom.openai.com/v1"
        provider_config.organization = "custom-org"
        provider_config.extra = {"custom_param": "value"}

        _litellm_mock.acompletion = MagicMock()
        OpenAIProvider = self._import_provider("model_canary.providers.openai", "OpenAIProvider")
        provider = OpenAIProvider(config=provider_config)

        params = provider._get_litellm_params()
        assert params["api_base"] == "https://custom.openai.com/v1"
        assert params["organization"] == "custom-org"
        assert params["custom_param"] == "value"

    @pytest.mark.asyncio
    async def test_anthropic_provider(self, provider_config, mock_openai_response):
        provider_config.provider_type = "anthropic"
        provider_config.default_model = "claude-3-5-sonnet-20241022"
        _litellm_mock.acompletion = AsyncMock(return_value=mock_openai_response)
        AnthropicProvider = self._import_provider("model_canary.providers.anthropic", "AnthropicProvider")
        provider = AnthropicProvider(config=provider_config)

        assert provider.provider_type == "anthropic"
        result = await provider.complete("Hi", prompt_name="test")
        assert result.response == "Hello! How can I help you?"

    @pytest.mark.asyncio
    async def test_gemini_provider(self, provider_config, mock_openai_response):
        provider_config.provider_type = "gemini"
        provider_config.default_model = "gemini-2.0-flash"
        _litellm_mock.acompletion = AsyncMock(return_value=mock_openai_response)
        GeminiProvider = self._import_provider("model_canary.providers.gemini", "GeminiProvider")
        provider = GeminiProvider(config=provider_config)

        assert provider.provider_type == "gemini"
        result = await provider.complete("Hi", prompt_name="test")
        assert result.response == "Hello! How can I help you?"

    @pytest.mark.asyncio
    async def test_mistral_provider(self, provider_config, mock_openai_response):
        provider_config.provider_type = "mistral"
        provider_config.default_model = "mistral-large-latest"
        _litellm_mock.acompletion = AsyncMock(return_value=mock_openai_response)
        MistralProvider = self._import_provider("model_canary.providers.mistral", "MistralProvider")
        provider = MistralProvider(config=provider_config)

        assert provider.provider_type == "mistral"
        result = await provider.complete("Hi", prompt_name="test")
        assert result.response == "Hello! How can I help you?"

    @pytest.mark.asyncio
    async def test_deepseek_provider(self, provider_config, mock_openai_response):
        provider_config.provider_type = "deepseek"
        provider_config.default_model = "deepseek-chat"
        _litellm_mock.acompletion = AsyncMock(return_value=mock_openai_response)
        DeepSeekProvider = self._import_provider("model_canary.providers.deepseek", "DeepSeekProvider")
        provider = DeepSeekProvider(config=provider_config)

        assert provider.provider_type == "deepseek"
        result = await provider.complete("Hi", prompt_name="test")
        assert result.response == "Hello! How can I help you?"

    @pytest.mark.asyncio
    async def test_openrouter_provider(self, provider_config, mock_openai_response):
        provider_config.provider_type = "openrouter"
        provider_config.default_model = "openai/gpt-4o"
        _litellm_mock.acompletion = AsyncMock(return_value=mock_openai_response)
        OpenRouterProvider = self._import_provider("model_canary.providers.openrouter", "OpenRouterProvider")
        provider = OpenRouterProvider(config=provider_config)

        assert provider.provider_type == "openrouter"
        result = await provider.complete("Hi", prompt_name="test")
        assert result.response == "Hello! How can I help you?"

    @pytest.mark.asyncio
    async def test_ollama_provider(self, provider_config, mock_openai_response):
        provider_config.provider_type = "ollama"
        provider_config.default_model = "llama3.2"
        provider_config.base_url = "http://localhost:11434"
        _litellm_mock.acompletion = AsyncMock(return_value=mock_openai_response)
        OllamaProvider = self._import_provider("model_canary.providers.ollama", "OllamaProvider")
        provider = OllamaProvider(config=provider_config)

        assert provider.provider_type == "ollama"
        result = await provider.complete("Hi", prompt_name="test")
        assert result.response == "Hello! How can I help you?"

    @pytest.mark.asyncio
    async def test_grok_provider(self, provider_config, mock_openai_response):
        provider_config.provider_type = "grok"
        provider_config.default_model = "grok-2"
        _litellm_mock.acompletion = AsyncMock(return_value=mock_openai_response)
        GrokProvider = self._import_provider("model_canary.providers.grok", "GrokProvider")
        provider = GrokProvider(config=provider_config)

        assert provider.provider_type == "grok"
        result = await provider.complete("Hi", prompt_name="test")
        assert result.response == "Hello! How can I help you?"

    @pytest.mark.asyncio
    async def test_cohere_provider(self, provider_config, mock_openai_response):
        provider_config.provider_type = "cohere"
        provider_config.default_model = "command-r-plus"
        _litellm_mock.acompletion = AsyncMock(return_value=mock_openai_response)
        CohereProvider = self._import_provider("model_canary.providers.cohere", "CohereProvider")
        provider = CohereProvider(config=provider_config)

        assert provider.provider_type == "cohere"
        result = await provider.complete("Hi", prompt_name="test")
        assert result.response == "Hello! How can I help you?"

    @pytest.mark.asyncio
    async def test_together_provider(self, provider_config, mock_openai_response):
        provider_config.provider_type = "together"
        provider_config.default_model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
        _litellm_mock.acompletion = AsyncMock(return_value=mock_openai_response)
        TogetherProvider = self._import_provider("model_canary.providers.together", "TogetherProvider")
        provider = TogetherProvider(config=provider_config)

        assert provider.provider_type == "together"
        result = await provider.complete("Hi", prompt_name="test")
        assert result.response == "Hello! How can I help you?"

    @pytest.mark.asyncio
    async def test_fireworks_provider(self, provider_config, mock_openai_response):
        provider_config.provider_type = "fireworks"
        provider_config.default_model = "accounts/fireworks/models/llama-v3p1-70b-instruct"
        _litellm_mock.acompletion = AsyncMock(return_value=mock_openai_response)
        FireworksProvider = self._import_provider("model_canary.providers.fireworks", "FireworksProvider")
        provider = FireworksProvider(config=provider_config)

        assert provider.provider_type == "fireworks"
        result = await provider.complete("Hi", prompt_name="test")
        assert result.response == "Hello! How can I help you?"

    @pytest.mark.asyncio
    async def test_vllm_provider(self, provider_config, mock_openai_response):
        provider_config.provider_type = "vllm"
        provider_config.default_model = "microsoft/phi-4"
        provider_config.base_url = "http://localhost:8000"
        _litellm_mock.acompletion = AsyncMock(return_value=mock_openai_response)
        VLLMProvider = self._import_provider("model_canary.providers.vllm", "VLLMProvider")
        provider = VLLMProvider(config=provider_config)

        assert provider.provider_type == "vllm"
        result = await provider.complete("Hi", prompt_name="test")
        assert result.response == "Hello! How can I help you?"

    @pytest.mark.asyncio
    async def test_lm_studio_provider(self, provider_config, mock_openai_response):
        provider_config.provider_type = "lm_studio"
        provider_config.default_model = "local-model"
        provider_config.base_url = "http://localhost:1234/v1"
        _litellm_mock.acompletion = AsyncMock(return_value=mock_openai_response)
        LMStudioProvider = self._import_provider("model_canary.providers.lm_studio", "LMStudioProvider")
        provider = LMStudioProvider(config=provider_config)

        assert provider.provider_type == "lm_studio"
        result = await provider.complete("Hi", prompt_name="test")
        assert result.response == "Hello! How can I help you?"

    @pytest.mark.asyncio
    async def test_azure_openai_provider(self, provider_config, mock_openai_response):
        provider_config.provider_type = "azure_openai"
        provider_config.default_model = "gpt-4o"
        provider_config.base_url = "https://my-resource.openai.azure.com"
        _litellm_mock.acompletion = AsyncMock(return_value=mock_openai_response)
        AzureOpenAIProvider = self._import_provider("model_canary.providers.azure_openai", "AzureOpenAIProvider")
        provider = AzureOpenAIProvider(config=provider_config)

        assert provider.provider_type == "azure_openai"
        result = await provider.complete("Hi", prompt_name="test")
        assert result.response == "Hello! How can I help you?"

    @pytest.mark.asyncio
    async def test_litellm_provider(self, provider_config, mock_openai_response):
        provider_config.provider_type = "litellm"
        provider_config.default_model = "gpt-4o"
        _litellm_mock.acompletion = AsyncMock(return_value=mock_openai_response)
        LiteLLMProvider = self._import_provider("model_canary.providers.litellm", "LiteLLMProvider")
        provider = LiteLLMProvider(config=provider_config)

        assert provider.provider_type == "litellm"
        result = await provider.complete("Hi", prompt_name="test")
        assert result.response == "Hello! How can I help you?"

    @pytest.mark.asyncio
    async def test_custom_provider(self, provider_config):
        provider_config.provider_type = "custom"
        provider_config.default_model = "my-custom-model"
        CustomProvider = self._import_provider("model_canary.providers.custom", "CustomProvider")
        provider = CustomProvider(config=provider_config)

        mock_data = {
            "choices": [{"message": {"content": "Hello! How can I help you?"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }
        provider._make_request = AsyncMock(return_value=mock_data)

        assert provider.provider_type == "custom"
        result = await provider.complete("Hi", prompt_name="test")
        assert result.response == "Hello! How can I help you?"

    @pytest.mark.asyncio
    async def test_provider_registers_all(self):
        register_providers()
        registry = get_provider_registry()
        # Most providers should be registered since we mocked litellm
        assert registry.is_registered("openai") is True
        assert registry.is_registered("anthropic") is True
        assert registry.is_registered("gemini") is True
        assert registry.is_registered("deepseek") is True
        assert registry.is_registered("custom") is True

    def test_anthropic_headers(self, provider_config):
        AnthropicProvider = self._import_provider("model_canary.providers.anthropic", "AnthropicProvider")
        provider_config.api_key = "sk-ant-test"
        provider = AnthropicProvider(config=provider_config)
        headers = provider._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer sk-ant-test"

    def test_azure_headers(self, provider_config):
        AzureOpenAIProvider = self._import_provider("model_canary.providers.azure_openai", "AzureOpenAIProvider")
        provider_config.api_key = "azure-key"
        provider = AzureOpenAIProvider(config=provider_config)
        headers = provider._get_headers()
        assert "api-key" in headers
        assert headers["api-key"] == "azure-key"


# =============================================================================
# Token/Cost Extraction Tests
# =============================================================================

class TestTokenCostExtraction:
    def test_extract_token_usage(self, provider_config):
        from model_canary.providers.base import BaseProvider

        class MinimalProvider(BaseProvider):
            @property
            def provider_type(self) -> str:
                return "minimal"

            def _get_headers(self) -> dict[str, str]:
                return {}

            def _get_api_url(self) -> str:
                return "https://test.com"

            async def complete(self, prompt, model=None, max_tokens=None, temperature=None, **kwargs):
                pass

            async def list_models(self):
                return []

        provider = MinimalProvider(config=provider_config)
        usage = provider._extract_token_usage({
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "reasoning_tokens": 10,
            }
        })
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150
        assert usage.reasoning_tokens == 10

    def test_extract_token_usage_empty(self, provider_config):
        from model_canary.providers.base import BaseProvider

        class MinimalProvider(BaseProvider):
            @property
            def provider_type(self) -> str:
                return "minimal"

            def _get_headers(self) -> dict[str, str]:
                return {}

            def _get_api_url(self) -> str:
                return "https://test.com"

            async def complete(self, prompt, model=None, max_tokens=None, temperature=None, **kwargs):
                pass

            async def list_models(self):
                return []

        provider = MinimalProvider(config=provider_config)
        usage = provider._extract_token_usage({})
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0
        assert usage.reasoning_tokens is None
