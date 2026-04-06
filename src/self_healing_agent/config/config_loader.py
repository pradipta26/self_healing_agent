from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


_PROJECT_ROOT = Path(__file__).resolve().parents[3]


def load_yaml_config(relative_path: str) -> dict[str, Any]:
    """
    Load a YAML file from the project root using a relative path.

    Example:
        load_yaml_config("self_healing_agent/configs/policies/actions.yaml")
        load_yaml_config("self_healing_agent/configs/env/dev_config.yaml")
    """
    file_path = _PROJECT_ROOT / relative_path

    if not file_path.exists():
        raise FileNotFoundError(f"YAML config file not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError(f"YAML config must load into a dict: {file_path}")

    return data


def load_env_from_config(env: str = "dev", overwrite: bool = False) -> dict[str, str]:
    """
    Load only top-level `env_variables` from configs/env/{env}_config.yaml into os.environ.

    Args:
        overwrite: If True, replace already-set environment variables.

    Returns:
        A dict of environment variables that were written to os.environ.
    """
    config_path = _PROJECT_ROOT / "configs" / "env" / f"{env}_config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        loaded: Any = yaml.safe_load(handle) or {}

    if not isinstance(loaded, dict):
        raise ValueError(
            f"Expected a mapping at top-level in {config_path}, got {type(loaded).__name__}"
        )

    env_variables = loaded.get("env_variables", {})
    if not isinstance(env_variables, dict):
        raise ValueError(
            f"Expected 'env_variables' to be a mapping in {config_path}, "
            f"got {type(env_variables).__name__}"
        )

    written: dict[str, str] = {}
    for key, value in env_variables.items():
        env_key = str(key)
        env_value = "" if value is None else str(value)
        if overwrite or env_key not in os.environ:
            os.environ[env_key] = env_value
            written[env_key] = env_value

    print(f"Loaded environment variables from {config_path}: {list(env_variables.keys())}")
    return written
