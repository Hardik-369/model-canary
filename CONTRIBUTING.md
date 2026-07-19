# Contributing to Model Canary

We love your input! We want to make contributing to Model Canary as easy and transparent as possible.

## Development Process

1. Fork the repo and create your branch from `main`
2. Install dependencies: `uv sync --dev`
3. Make your changes
4. Run tests: `uv run pytest`
5. Run linter: `uv run ruff check src/`
6. Run type checker: `uv run mypy src/`
7. Submit a pull request

## Development Setup

```bash
# Clone the repository
git clone https://github.com/model-canary/model-canary.git
cd model-canary

# Install uv if you don't have it
pip install uv

# Create virtual environment and install dependencies
uv sync --dev

# Run tests
uv run pytest

# Run linting
uv run ruff check src/
uv run ruff format src/

# Run type checking
uv run mypy src/
```

## Project Structure

```
src/model_canary/
    core/           # Core models, interfaces, exceptions
    providers/      # LLM provider implementations
    evaluators/     # Output evaluators
    fingerprinting/ # Fingerprinting engine
    drift/          # Drift detection engine
    storage/        # Storage backends
    alerting/       # Alerting channels
    plugins/        # Plugin system
    cli/            # CLI using Typer + Rich
    api/            # FastAPI REST API
    scheduler/      # Job scheduler
    reporting/      # Report generation
    config/         # Configuration loading
    metrics/        # Prometheus metrics
    benchmark/      # Benchmark runner
    utils/          # Shared utilities
```

## Pull Request Process

1. Update the README.md or docs with details of changes if needed
2. Update the CHANGELOG.md with your changes
3. The PR will be merged once you have the sign-off of maintainers

## Coding Standards

- **Python 3.13+** — Use modern Python features
- **Type Hints** — All functions must have type annotations
- **Tests** — Aim for 95%+ coverage
- **Conventional Commits** — Use `feat:`, `fix:`, `docs:`, etc.
- **Documentation** — Docstrings for all public APIs

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.
