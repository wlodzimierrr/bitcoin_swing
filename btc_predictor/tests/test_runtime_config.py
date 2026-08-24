from pathlib import Path

import pytest

from btc_predictor.config import RuntimeConfig, load_runtime_config


def test_loads_default_dev_runtime_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BTC_PREDICTOR_ENV", raising=False)

    config = load_runtime_config()

    assert config == RuntimeConfig(
        environment="dev",
        app_name="bitcoin-swing-predictor",
        log_level="DEBUG",
        log_format="json",
    )


def test_loads_named_environment_override() -> None:
    config = load_runtime_config(environment="test")

    assert config.environment == "test"
    assert config.log_level == "WARNING"


def test_loads_environment_from_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BTC_PREDICTOR_ENV", "test")

    config = load_runtime_config()

    assert config.environment == "test"
    assert config.log_level == "WARNING"


def test_missing_environment_config_fails_fast(tmp_path: Path) -> None:
    (tmp_path / "base.toml").write_text(
        """
[app]
name = "bitcoin-swing-predictor"

[logging]
level = "INFO"
format = "json"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError):
        load_runtime_config(environment="missing", config_dir=tmp_path)
