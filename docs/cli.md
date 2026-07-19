# CLI Reference

Model Canary features a beautiful CLI powered by Typer and Rich.

## Usage

```bash
model-canary [OPTIONS] COMMAND [ARGS]...
```

## Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize a new project |
| `run` | Run canary test suites |
| `list` | List providers and suites |
| `compare` | Compare fingerprints across providers |
| `report` | Generate drift reports |
| `dashboard` | Start the web dashboard |
| `history` | Show fingerprint/drift history |
| `inspect` | Inspect a specific fingerprint |
| `doctor` | Check system health |
| `benchmark` | Benchmark models |
| `config` | View or validate configuration |
| `providers` | List available providers |
| `models` | List models for a provider |
| `alerts` | View alert configuration |
| `diff` | Compare two runs |
| `prompts` | Manage prompts |
| `watch` | Continuous watch mode |
