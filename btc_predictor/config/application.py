"""Application configuration loaded at startup."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from btc_predictor.config.runtime import RuntimeConfig, load_runtime_config
from btc_predictor.config.strategy import StrategyConfig, load_strategy_config


@dataclass(frozen=True)
class ApplicationConfig:
    runtime: RuntimeConfig
    strategy: StrategyConfig


def load_application_config(
    environment: str | None = None,
    runtime_config_dir: Path | None = None,
    strategy_config_path: Path | None = None,
) -> ApplicationConfig:
    """Load and validate all startup configuration."""

    return ApplicationConfig(
        runtime=load_runtime_config(
            environment=environment,
            config_dir=runtime_config_dir,
        ),
        strategy=load_strategy_config(strategy_config_path),
    )
