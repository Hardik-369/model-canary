# Troubleshooting

## Common Issues

### "No configuration found"

Run `model-canary init` to create a configuration file, or create a `model-canary.yml` manually.

### "Provider not found"

Check that the provider type is correct. Run `model-canary providers` to list available providers. For custom providers, ensure they are installed and registered via entry points.

### "API key not set"

Set the appropriate environment variable (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) or configure it in the YAML file.

### "Connection refused" for local providers

Ensure Ollama/vLLM/LM Studio is running on the expected port. Default ports:
- Ollama: `http://localhost:11434`
- vLLM: `http://localhost:8000`
- LM Studio: `http://localhost:1234`

### "Database locked"

SQLite may lock under concurrent access. For production, switch to PostgreSQL.

## Debug Mode

```bash
export MODEL_CANARY_LOG_LEVEL=DEBUG
model-canary run
```

## Health Check

```bash
model-canary doctor
```
