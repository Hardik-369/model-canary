from __future__ import annotations

from model_canary.core.exceptions import PluginNotFoundError, ProviderError, ProviderNotFoundError
from model_canary.core.interfaces import Provider
from model_canary.core.models import ProviderConfig
from model_canary.providers.registry import ProviderRegistry, get_provider_registry


def create_provider(
    config: ProviderConfig,
    registry: ProviderRegistry | None = None,
) -> Provider:
    if registry is None:
        registry = get_provider_registry()

    provider_type = config.provider_type.lower()
    try:
        provider_cls = registry.get(provider_type)
    except PluginNotFoundError:
        provider_cls = _load_plugin_provider(provider_type)

    try:
        return provider_cls(config=config)
    except Exception as e:
        raise ProviderError(
            f"Failed to create provider '{config.name}' (type: {provider_type}): {e}"
        )


def _load_plugin_provider(provider_type: str) -> type[Provider]:
    import importlib.metadata

    for ep in importlib.metadata.entry_points(group="model_canary.providers"):
        if ep.name.lower() == provider_type.lower():
            return ep.load()
    raise ProviderNotFoundError(
        f"Provider '{provider_type}' not found. "
        f"Available built-in providers: openai, anthropic, gemini, mistral, "
        f"deepseek, grok, cohere, openrouter, together, fireworks, "
        f"azure_openai, ollama, vllm, lm_studio, litellm, custom"
    )


def get_available_providers() -> dict[str, str]:
    providers = {}
    registry = get_provider_registry()
    for name, cls in registry.list().items():
        providers[name] = cls.__module__
    try:
        import importlib.metadata

        for ep in importlib.metadata.entry_points(group="model_canary.providers"):
            providers[ep.name] = ep.value
    except Exception:
        pass
    return providers
