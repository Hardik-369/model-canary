from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

from model_canary.core.exceptions import ConfigError, ConfigNotFoundError
from model_canary.core.models import ModelCanaryConfig


def detect_config_files(path: str | None = None) -> list[Path]:
    if path:
        resolved = Path(path).resolve()
        if resolved.is_file():
            return [resolved]

    search_paths = [Path.cwd()]
    if path:
        search_paths.append(resolved)

    config_files = []
    for base in search_paths:
        for filename in [
            "model-canary.yml",
            "model-canary.yaml",
            "model-canary.json",
            "model-canary.toml",
            ".model-canary.yml",
            ".model-canary.yaml",
            ".model-canary.json",
        ]:
            candidate = base / filename
            if candidate.exists():
                config_files.append(candidate)
    return config_files


def load_config_from_file(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    try:
        if suffix in (".yml", ".yaml"):
            with open(path) as f:
                return yaml.safe_load(f) or {}
        elif suffix == ".json":
            with open(path) as f:
                return json.load(f)
        elif suffix == ".toml":
            try:
                import tomli

                with open(path, "rb") as f:
                    return tomli.load(f)
            except ImportError:
                import tomllib

                with open(path, "rb") as f:
                    return tomllib.load(f)
        else:
            raise ConfigError(f"Unsupported config file format: {suffix}")
    except Exception as e:
        raise ConfigError(f"Failed to load config from {path}: {e}")


def load_config_from_env() -> dict[str, Any]:
    env_config: dict[str, Any] = {}

    providers_env = os.environ.get("MODEL_CANARY_PROVIDERS")
    if providers_env:
        import json as _json

        try:
            env_config["providers"] = _json.loads(providers_env)
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid MODEL_CANARY_PROVIDERS env: {e}")

    prefix = "MODEL_CANARY_"
    for key, value in os.environ.items():
        if key.startswith(prefix) and key not in ("MODEL_CANARY_PROVIDERS",):
            config_key = key[len(prefix) :].lower()
            env_config[config_key] = value

    return env_config


def merge_configs(
    *configs: dict[str, Any],
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for config in configs:
        for key, value in config.items():
            if key in ("providers", "plugins") and key in merged:
                if isinstance(merged[key], list) and isinstance(value, list):
                    merged[key].extend(value)
                    continue
            merged[key] = value
    return merged


def load_config(
    path: str | None = None,
    from_env: bool = True,
    validate: bool = True,
) -> ModelCanaryConfig:
    config_dict: dict[str, Any] = {}

    config_files = detect_config_files(path)
    for cf in config_files:
        file_config = load_config_from_file(cf)
        config_dict = merge_configs(config_dict, file_config)

    if from_env:
        env_config = load_config_from_env()
        config_dict = merge_configs(config_dict, env_config)

    if not config_dict:
        raise ConfigNotFoundError(
            "No configuration found. Create a model-canary.yml "
            "or set MODEL_CANARY_* environment variables."
        )

    if validate:
        try:
            return ModelCanaryConfig(**config_dict)
        except Exception as e:
            raise ConfigError(f"Configuration validation failed: {e}")

    return ModelCanaryConfig(**config_dict)
