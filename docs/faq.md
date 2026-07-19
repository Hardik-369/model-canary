# FAQ

## What is Model Canary?

Model Canary is an open-source monitoring platform that continuously fingerprints AI models and alerts you when meaningful behavioral changes occur.

## How is this different from standard LLM evaluation?

Standard evaluation is one-time. Model Canary continuously monitors over time, detecting drift by comparing current fingerprints against baselines.

## Does it store my prompts?

Prompts are stored locally by default. Enable `privacy_mode` to prevent any prompt storage.

## What providers are supported?

OpenAI, Anthropic, Google Gemini, Mistral, DeepSeek, Grok, Cohere, OpenRouter, Together AI, Fireworks AI, Azure OpenAI, Ollama, vLLM, LM Studio, LiteLLM, and custom REST APIs.

## Can I use it offline?

Yes. Use local providers like Ollama, vLLM, or LM Studio for fully offline operation.

## How much does it cost?

Model Canary itself is free and open-source. You only pay for the LLM API calls you make.

## How is this different from Langfuse/Helicone/etc.?

Those are observability platforms. Model Canary focuses specifically on drift detection — comparing model behavior over time to catch regressions.

## Can I run it in CI/CD?

Yes. Use the CLI, API, or GitHub Action for CI/CD integration.

## Do I need a database?

SQLite is included and requires no setup. For production, use PostgreSQL.
