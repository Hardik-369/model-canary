from __future__ import annotations

from model_canary.core.exceptions import PluginNotFoundError
from model_canary.core.interfaces import Provider


class ProviderRegistry:
    _instance: ProviderRegistry | None = None

    def __init__(self) -> None:
        self._providers: dict[str, type[Provider]] = {}

    @classmethod
    def get_instance(cls) -> ProviderRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, name: str, provider_cls: type[Provider]) -> None:
        self._providers[name.lower()] = provider_cls

    def unregister(self, name: str) -> None:
        self._providers.pop(name.lower(), None)

    def get(self, name: str) -> type[Provider]:
        key = name.lower()
        if key not in self._providers:
            raise PluginNotFoundError(
                f"Provider '{name}' not found. Available: {', '.join(self._providers)}"
            )
        return self._providers[key]

    def list(self) -> dict[str, type[Provider]]:
        return dict(self._providers)

    def is_registered(self, name: str) -> bool:
        return name.lower() in self._providers


def get_provider_registry() -> ProviderRegistry:
    return ProviderRegistry.get_instance()


def register_providers() -> None:
    registry = get_provider_registry()
    try:
        from model_canary.providers.openai import OpenAIProvider

        registry.register("openai", OpenAIProvider)
    except ImportError:
        pass
    try:
        from model_canary.providers.anthropic import AnthropicProvider

        registry.register("anthropic", AnthropicProvider)
    except ImportError:
        pass
    try:
        from model_canary.providers.gemini import GeminiProvider

        registry.register("gemini", GeminiProvider)
    except ImportError:
        pass
    try:
        from model_canary.providers.mistral import MistralProvider

        registry.register("mistral", MistralProvider)
    except ImportError:
        pass
    try:
        from model_canary.providers.deepseek import DeepSeekProvider

        registry.register("deepseek", DeepSeekProvider)
    except ImportError:
        pass
    try:
        from model_canary.providers.openrouter import OpenRouterProvider

        registry.register("openrouter", OpenRouterProvider)
    except ImportError:
        pass
    try:
        from model_canary.providers.ollama import OllamaProvider

        registry.register("ollama", OllamaProvider)
    except ImportError:
        pass
    try:
        from model_canary.providers.litellm import LiteLLMProvider

        registry.register("litellm", LiteLLMProvider)
    except ImportError:
        pass
    try:
        from model_canary.providers.grok import GrokProvider

        registry.register("grok", GrokProvider)
    except ImportError:
        pass
    try:
        from model_canary.providers.cohere import CohereProvider

        registry.register("cohere", CohereProvider)
    except ImportError:
        pass
    try:
        from model_canary.providers.together import TogetherProvider

        registry.register("together", TogetherProvider)
    except ImportError:
        pass
    try:
        from model_canary.providers.fireworks import FireworksProvider

        registry.register("fireworks", FireworksProvider)
    except ImportError:
        pass
    try:
        from model_canary.providers.azure_openai import AzureOpenAIProvider

        registry.register("azure_openai", AzureOpenAIProvider)
    except ImportError:
        pass
    try:
        from model_canary.providers.vllm import VLLMProvider

        registry.register("vllm", VLLMProvider)
    except ImportError:
        pass
    try:
        from model_canary.providers.lm_studio import LMStudioProvider

        registry.register("lm_studio", LMStudioProvider)
    except ImportError:
        pass
    try:
        from model_canary.providers.mistral import MistralProvider

        registry.register("mistral", MistralProvider)
    except ImportError:
        pass
    try:
        from model_canary.providers.custom import CustomProvider

        registry.register("custom", CustomProvider)
    except ImportError:
        pass
