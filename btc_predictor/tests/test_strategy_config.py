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
    assert config.scoring_weights.full_flow["etf_norm_5"] == 0.3
    assert config.scoring_weights.full_flow["spot_dominance"] == 0.1
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


def test_invalid_flow_weight_keys_fail_fast(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid_flow_weights.toml"
    config_path.write_text(
        """
[identity]
config_version = "strategy_config_v1"
strategy_version = "swing_v1.0"
parameter_set_id = "broken"

[entry_thresholds]
ignore_below = 70
watch_min = 70
valid_trade_min = 80
strong_setup_min = 85
exceptional_min = 90
short_valid_trade_min = 85

[hold_thresholds]
possible_add_min = 85
hold_min = 70
no_add_min = 60
defensive_min = 50
trim_min = 40
exit_below = 40

[add_thresholds]
add_min = 85
existing_position_must_be_profitable = true
stop_must_improve = true
no_average_down = true

[risk]
max_risk_at_stop_fraction_nav = 0.01

[[risk.schedule]]
min_entry_conviction = 80
risk_fraction_nav = 0.0035

[stop_buffers]
atr_period = 20
atr_multiplier = 0.3
minimum_level_noise_multiplier = 1.0
sweep_atr_multipliers = [0.3]

[setup_requirements]
supported_setups = ["bull_trend_continuation", "bullish_reset"]

[setup_requirements.bull_trend_continuation]
regime_min = 65
trend_min = 70
flow_min = 55
positioning_min = 60
structure_min = 70
minimum_rr = 2.0
entry_conviction_min = 80
require_no_stress = true
require_no_severe_crowding = true

[setup_requirements.bullish_reset]
regime_min = 55
trend_min = 55
correction_min_fraction = 0.08
correction_max_fraction = 0.25
funding_health_improving_days = 7
oi_health_stable_days = 7
flow_accel_improving_days = 5
structure_min = 70
entry_trigger_required = true
entry_conviction_min = 80
minimum_rr = 2.0

[regime_thresholds]
strong_bull_min = 80
bull_min = 65
mild_bull_min = 55
neutral_min = 45
mild_bear_min = 35
bear_min = 20

[price_levels]
swing_window_weeks = 3
swing_window_months = 2
cluster_distance_fraction = 0.025
minimum_level_strength = 60
rr_minimum = 2.0
rr_preferred_min = 2.5
rr_preferred_max = 3.0
reward_reference_order = ["prior_local_swing_high"]

[scoring_weights.entry_conviction]
trend = 1.0

[scoring_weights.hold_score]
trend = 1.0

[scoring_weights.add_score]
trend = 1.0

[scoring_weights.full_flow]
etf_norm_5 = 0.30
etf_norm_20 = 0.25
flow_accel = 0.20
cvd_spred = 0.15
spot_dominance = 0.10

[scoring_weights.core_flow]
etf_norm_5 = 0.40
etf_norm_20 = 0.35
flow_accel = 0.25

[scoring_weights.core_regime]
trend = 1.0

[backtest]
initial_cash = 100000
fee_bps = 10
slippage_bps = 5
funding_cost_bps_per_day = 0
max_trades_per_year = 24
allow_short_trades = false
execution_timing = "next_bar"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(StrategyConfigError, match="full_flow"):
        load_strategy_config(config_path)
