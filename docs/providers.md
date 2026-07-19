# Providers

Model Canary supports 16+ LLM providers out of the box.

## Supported Providers

| Provider | Type Identifier | Auth Method |
|----------|----------------|-------------|
| OpenAI | `openai` | API Key |
| Anthropic | `anthropic` | API Key |
| Google Gemini | `gemini` | API Key |
| Mistral | `mistral` | API Key |
| DeepSeek | `deepseek` | API Key |
| Grok (xAI) | `grok` | API Key |
| Cohere | `cohere` | API Key |
| OpenRouter | `openrouter` | API Key |
| Together AI | `together` | API Key |
| Fireworks AI | `fireworks` | API Key |
| Azure OpenAI | `azure_openai` | API Key + Endpoint |
| Ollama | `ollama` | None (local) |
| vLLM | `vllm` | None (local) |
| LM Studio | `lm_studio` | None (local) |
| LiteLLM | `litellm` | API Key |
| Custom REST | `custom` | Configurable |

## Adding a Custom Provider

Create a class implementing the `Provider` interface and register it via entry points.
