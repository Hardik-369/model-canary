# Architecture

Model Canary follows a clean, modular architecture with separation of concerns.

```mermaid
graph TD
    subgraph "Interface Layer"
        CLI
        REST_API
        GitHub_Action
    end
    
    subgraph "Core Engine"
        CanaryEngine
        FingerprintingEngine
        DriftDetectionEngine
    end
    
    subgraph "Providers"
        OpenAI
        Anthropic
        Gemini
        Mistral
        DeepSeek
        Ollama
    end
    
    subgraph "Storage"
        SQLite
        Postgres
        DuckDB
        LocalJSON
    end
    
    subgraph "Alerting"
        Slack
        Discord
        GitHub
        Webhook
        Log
    end
    
    subgraph "Plugin System"
        CustomProviders
        CustomEvaluators
        CustomAlerters
    end
    
    CLI --> CanaryEngine
    REST_API --> CanaryEngine
    GitHub_Action --> CanaryEngine
    CanaryEngine --> FingerprintingEngine
    CanaryEngine --> DriftDetectionEngine
    CanaryEngine --> Providers
    CanaryEngine --> Storage
    CanaryEngine --> Alerting
    PluginSystem --> CanaryEngine
```

## Design Principles

- **Modular** — Each component is independent and replaceable
- **Provider Agnostic** — Add any LLM provider via one interface
- **Plugin Based** — Extend functionality without modifying core
- **Privacy First** — All data stays local by default
- **Production Ready** — Built for real-world deployment
