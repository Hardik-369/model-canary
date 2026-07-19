# Model Canary — Agent Instructions

## Useful Commands

```bash
# Setup development environment
uv sync --dev

# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src/model_canary --cov-report=term-missing

# Run a specific test file
uv run pytest tests/test_engine.py

# Lint
uv run ruff check src/
uv run ruff format src/

# Type check
uv run mypy src/

# Build package
uv build

# Run CLI locally
uv run model-canary --help
uv run model-canary doctor
uv run model-canary config --validate

# Start API server
uv run python -c "import uvicorn; from model_canary.api.app import create_app; uvicorn.run(create_app(), host='127.0.0.1', port=8311)"
```

## Architecture Notes

- All providers extend `BaseProvider` from `providers/base.py`
- All evaluators extend `BaseEvaluator` from `evaluators/base.py`
- The engine is in `engine.py` — this is the main orchestrator
- Storage backends implement `StorageBackend` interface
- Alerters implement `Alerter` interface
- Plugin system uses Python entry points

## Testing

- Unit tests in `tests/`
- Use `pytest-asyncio` for async tests
- Use `syrupy` for snapshot testing
- Use `respx` for HTTP mocking
- Test files should follow `tests/test_*.py` naming

## Coding Standards

- Python 3.13+
- All functions must have type annotations
- Use `from __future__ import annotations` at top of files
- Max line length: 100
- Use Ruff for linting and formatting
- Follow conventional commits for commit messages
