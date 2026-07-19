"""Tests for configuration loading."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from model_canary.config.loader import (
    detect_config_files,
    load_config,
    load_config_from_file,
    merge_configs,
)
from model_canary.core.exceptions import ConfigError, ConfigNotFoundError
from model_canary.core.models import ModelCanaryConfig


def test_detect_config_files_no_files(tmp_path):
    files = detect_config_files(str(tmp_path))
    assert files == []


def test_detect_config_files_yaml(tmp_path):
    config_file = tmp_path / "model-canary.yml"
    config_file.write_text("version: '1'\n")
    files = detect_config_files(str(tmp_path))
    assert len(files) == 1
    assert files[0] == config_file


def test_detect_config_files_json(tmp_path):
    config_file = tmp_path / "model-canary.json"
    config_file.write_text('{"version": "1"}')
    files = detect_config_files(str(tmp_path))
    assert len(files) == 1
    assert files[0] == config_file


def test_load_config_from_file_yaml(tmp_path):
    config = {"version": "1", "project_name": "test"}
    config_file = tmp_path / "config.yml"
    with open(config_file, "w") as f:
        yaml.dump(config, f)
    loaded = load_config_from_file(config_file)
    assert loaded["version"] == "1"
    assert loaded["project_name"] == "test"


def test_load_config_from_file_json(tmp_path):
    config = {"version": "1", "project_name": "test"}
    config_file = tmp_path / "config.json"
    with open(config_file, "w") as f:
        json.dump(config, f)
    loaded = load_config_from_file(config_file)
    assert loaded["version"] == "1"


def test_load_config_from_file_unsupported(tmp_path):
    config_file = tmp_path / "config.txt"
    config_file.write_text("invalid")
    with pytest.raises(ConfigError, match="Unsupported config file format"):
        load_config_from_file(config_file)


def test_merge_configs():
    a = {"version": "1", "providers": [{"name": "test1"}]}
    b = {"project_name": "merged", "providers": [{"name": "test2"}]}
    merged = merge_configs(a, b)
    assert merged["version"] == "1"
    assert merged["project_name"] == "merged"
    assert len(merged["providers"]) == 2


def test_load_config_not_found():
    with pytest.raises(ConfigNotFoundError):
        load_config(path="/nonexistent/path")


def test_load_config_valid(tmp_path):
    import os
    orig_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        config_file = tmp_path / "model-canary.yml"
        config_file.write_text("version: '1'\nproject_name: test\n")
        cfg = load_config()
        assert isinstance(cfg, ModelCanaryConfig)
        assert cfg.version == "1"
        assert cfg.project_name == "test"
    finally:
        os.chdir(orig_cwd)


def test_model_canary_config_defaults():
    config = ModelCanaryConfig()
    assert config.version == "1"
    assert config.project_name == "model-canary"
    assert config.storage.backend == "sqlite"
    assert config.alerting.enabled is True
    assert config.fingerprint_algorithm == "sha256"
    assert config.max_concurrent == 5
