from pathlib import Path

import pytest

from btc_predictor.config import StrategyConfigError, load_strategy_config


def test_loads_default_strategy_config() -> None:
    config = load_strategy_config()

    assert config.identity.config_version == "strategy_config_v1"
    assert config.identity.strategy_version == "swing_v1.0"
    assert config.identity.parameter_set_id == "default_phase1"
    assert config.entry_thresholds.valid_trade_min == 80
    assert config.hold_thresholds.possible_add_min == 85
    assert config.add_thresholds.no_average_down is True
    assert config.risk.max_risk_at_stop_fraction_nav == 0.01
    assert config.stop_buffers.atr_period == 20
    assert config.setup_requirements.supported_setups == (
        "bull_trend_continuation",
        "bullish_reset",
    )
    assert config.regime_thresholds.bull_min == 65
    assert config.price_levels.rr_minimum == 2
    assert config.scoring_weights.entry_conviction["trend"] == 0.2
    assert config.scoring_weights.core_flow["etf_norm_5"] == 0.4
    assert config.backtest.max_trades_per_year == 24


def test_strategy_config_exposes_run_metadata() -> None:
    config = load_strategy_config()

    assert config.run_metadata() == {
        "config_version": "strategy_config_v1",
        "strategy_version": "swing_v1.0",
        "parameter_set_id": "default_phase1",
    }


def test_invalid_strategy_config_fails_fast(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid.toml"
    config_path.write_text(
        """
[identity]
config_version = "strategy_config_v1"
strategy_version = "swing_v1.0"
parameter_set_id = "broken"

[entry_thresholds]
ignore_below = 70
watch_min = 70
valid_trade_min = 60
strong_setup_min = 85
exceptional_min = 90
short_valid_trade_min = 85
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(StrategyConfigError, match="entry_thresholds"):
        load_strategy_config(config_path)


def test_missing_strategy_section_fails_fast(tmp_path: Path) -> None:
    config_path = tmp_path / "missing.toml"
    config_path.write_text(
        """
[identity]
config_version = "strategy_config_v1"
strategy_version = "swing_v1.0"
parameter_set_id = "broken"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(StrategyConfigError, match="entry_thresholds"):
        load_strategy_config(config_path)
