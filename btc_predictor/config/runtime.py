"""Runtime configuration loading for the application shell."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tomllib
from typing import Any

ENV_VAR_NAME = "BTC_PREDICTOR_ENV"
DEFAULT_ENVIRONMENT = "dev"


@dataclass(frozen=True)
class RuntimeConfig:
    """Application-level runtime settings.

    Strategy parameters are intentionally excluded from this object; BTC-002
    will introduce the versioned strategy configuration schema.
    """

    environment: str
    app_name: str
    log_level: str
    log_format: str


def load_runtime_config(
    environment: str | None = None,
    config_dir: Path | None = None,
) -> RuntimeConfig:
    """Load base runtime config and apply an environment-specific override."""

    selected_environment = environment or os.getenv(ENV_VAR_NAME, DEFAULT_ENVIRONMENT)
    selected_environment = selected_environment.strip().lower()
    if not selected_environment:
        selected_environment = DEFAULT_ENVIRONMENT

    root = config_dir or Path(__file__).parent / "environments"
    base_config = _load_toml(root / "base.toml")
    environment_config = _load_toml(root / f"{selected_environment}.toml")
    merged = _deep_merge(base_config, environment_config)

    app = merged.get("app", {})
    logging = merged.get("logging", {})

    return RuntimeConfig(
        environment=selected_environment,
        app_name=_required_string(app, "name"),
        log_level=_required_string(logging, "level").upper(),
        log_format=_required_string(logging, "format"),
    )


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Runtime config file not found: {path}")

    with path.open("rb") as config_file:
        data = tomllib.load(config_file)

    if not isinstance(data, dict):
        raise ValueError(f"Runtime config must be a TOML table: {path}")

    return data


def _deep_merge(
    base: dict[str, Any],
    override: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _required_string(section: dict[str, Any], key: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Runtime config value must be a non-empty string: {key}")
    return value
