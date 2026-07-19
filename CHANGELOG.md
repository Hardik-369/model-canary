# Changelog

## [0.1.0] - 2026-07-19

### Added
- Initial release of Model Canary
- Multi-provider support (OpenAI, Anthropic, Gemini, Mistral, DeepSeek, Grok, Cohere, OpenRouter, Together, Fireworks, Azure, Ollama, vLLM, LM Studio, LiteLLM, Custom)
- Prompt test suites with categories (coding, JSON, reasoning, agents, RAG, security)
- Fingerprinting engine (SHA256, embeddings, cosine similarity, structure hashing)
- Drift detection engine (output, semantic, structural, latency, cost, refusal, tool, JSON, token, reasoning)
- 11 evaluators (JSON, regex, similarity, exact match, contains, Python, LLM judge, BLEU, ROUGE)
- 4 storage backends (SQLite, Postgres, DuckDB, Local JSON)
- 5 alerters (Slack, Discord, GitHub Issues, Webhook, Log)
- Rich CLI with 18+ commands
- FastAPI REST API with Swagger docs
- Built-in HTML dashboard
- Plugin system
- Benchmark mode
- Docker & Docker Compose support
- Kubernetes manifests
- GitHub Actions CI/CD
- Documentation site with MkDocs
