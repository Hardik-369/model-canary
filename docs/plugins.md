# Plugin System

Model Canary features a plugin system based on Python entry points.

## Plugin Types

| Type | Interface | Entry Point Group |
|------|-----------|------------------|
| Provider | `Provider` | `model_canary.providers` |
| Evaluator | `Evaluator` | `model_canary.evaluators` |
| Alerter | `Alerter` | `model_canary.alerters` |
| Storage | `StorageBackend` | `model_canary.storage` |

## Creating a Plugin

```python
from model_canary.core.interfaces import Provider, PluginType
from model_canary.core.models import PromptResult, ProviderConfig

class MyCustomProvider(Provider):
    @property
    def name(self) -> str:
        return "my-provider"
    
    @property
    def provider_type(self) -> str:
        return "my_custom"
    
    async def complete(self, prompt, model=None, **kwargs):
        # Your implementation
        pass
    
    async def list_models(self):
        return []
    
    async def check_health(self):
        return True
```

Register in `pyproject.toml`:

```toml
[project.entry-points."model_canary.providers"]
my_custom = "my_package.providers:MyCustomProvider"
```
