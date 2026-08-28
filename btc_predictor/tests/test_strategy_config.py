from pathlib import Path

import pytest

from btc_predictor.config import StrategyConfigError, load_strategy_config
from btc_predictor.config.strategy import DEFAULT_STRATEGY_CONFIG_PATH


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
    assert config.price_levels.cluster_distance_fraction == 0.025
    assert config.price_levels.minimum_level_strength == 60
    assert config.price_levels.rr_minimum == 2
    assert config.price_levels.breakout_close_buffer_fraction == 0
    assert config.price_levels.reclaim_close_buffer_fraction == 0
    assert config.price_levels.anchored_vwap_price_source == "hlc3"
    assert config.price_levels.volume_profile_price_source == "hlc3"
    assert config.price_levels.volume_profile_bin_size_fraction == 0.01
    assert config.price_levels.volume_profile_value_area_fraction == 0.70
    assert config.price_levels.volume_profile_hvn_volume_fraction == 0.70
    assert config.price_levels.volume_profile_min_bars == 20
    assert config.price_levels.level_strength_touch_count_full == 4
    assert config.price_levels.level_strength_reaction_full_fraction == 0.10
    assert config.price_levels.entry_location_full_score_distance_fraction == 0.01
    assert config.price_levels.entry_location_zero_score_distance_fraction == 0.08
    assert config.price_levels.level_strength_weights == {
        "timeframe": 0.20,
        "touch_count": 0.20,
        "reaction_magnitude": 0.20,
        "volume": 0.20,
        "confluence": 0.20,
    }
    assert config.price_levels.level_strength_timeframe_scores == {
        "1h": 40,
        "1d": 65,
        "1w": 85,
        "1mo": 100,
        "unknown": 50,
    }
    assert config.scoring_weights.entry_conviction["trend"] == 0.2
    assert config.scoring_weights.full_flow["etf_norm_5"] == 0.3
    assert config.scoring_weights.full_flow["spot_dominance"] == 0.1
    assert config.scoring_weights.core_flow["etf_norm_5"] == 0.4
    assert config.scoring_weights.core_regime == {
        "trend": 0.45,
        "flow": 0.25,
        "volatility": 0.15,
        "positioning": 0.15,
    }
    assert config.scoring_weights.full_regime == {
        "trend": 0.35,
        "flow": 0.20,
        "macro": 0.15,
        "onchain": 0.10,
        "volatility": 0.10,
        "liquidity": 0.10,
    }
    assert config.scoring_weights.positioning["funding_health"] == 0.35
    assert config.scoring_weights.positioning["leverage_health"] == 0.15
    assert config.scoring_weights.structure_score == {
        "level_strength": 0.45,
        "entry_location": 0.25,
        "rr_quality": 0.20,
        "confluence": 0.10,
    }
    assert config.regime_smoothing.previous_weight == 0.70
    assert config.regime_smoothing.new_weight == 0.30
    assert config.positioning_flags.crowding.funding_zscore_min == 2.0
    assert config.positioning_flags.crowding.basis_zscore_min == 2.0
    assert config.positioning_flags.crowding.oi_intensity_percentile_min == 90
    assert config.positioning_flags.crowding.entry_quality_penalty == 10
    assert config.volatility_flags.stress.volatility_percentile_min == 95
    assert config.volatility_flags.stress.liquidation_percentile_min == 95
    assert config.volatility_flags.stress.downside_return_min == -0.10
    assert config.volatility_flags.stress.funding_abs_zscore_min == 3.0
    assert config.volatility_flags.stress.basis_abs_zscore_min == 3.0
    assert config.volatility_flags.stress.max_exposure_multiplier == 0.50
    assert config.volatility_flags.stress.block_new_trades is False
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
breakout_close_buffer_fraction = 0
reclaim_close_buffer_fraction = 0
anchored_vwap_price_source = "hlc3"
volume_profile_price_source = "hlc3"
volume_profile_bin_size_fraction = 0.01
volume_profile_value_area_fraction = 0.70
volume_profile_hvn_volume_fraction = 0.70
volume_profile_min_bars = 20
level_strength_touch_count_full = 4
level_strength_reaction_full_fraction = 0.10
entry_location_full_score_distance_fraction = 0.01
entry_location_zero_score_distance_fraction = 0.08
rr_minimum = 2.0
rr_preferred_min = 2.5
rr_preferred_max = 3.0
reward_reference_order = ["prior_local_swing_high"]

[price_levels.level_strength_weights]
timeframe = 0.20
touch_count = 0.20
reaction_magnitude = 0.20
volume = 0.20
confluence = 0.20

[price_levels.level_strength_timeframe_scores]
"1h" = 40
"1d" = 65
"1w" = 85
"1mo" = 100
unknown = 50

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

[scoring_weights.full_regime]
trend = 0.35
flow = 0.20
macro = 0.15
onchain = 0.10
volatility = 0.10
liquidity = 0.10

[scoring_weights.positioning]
funding_health = 0.35
oi_health = 0.30
basis_health = 0.20
leverage_health = 0.15

[scoring_weights.structure_score]
level_strength = 0.45
entry_location = 0.25
rr_quality = 0.20
confluence = 0.10

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


def test_invalid_positioning_weight_keys_fail_fast(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid_positioning_weights.toml"
    config_path.write_text(
        DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8").replace(
            "leverage_health = 0.15",
            "leverage_heath = 0.15",
        ),
        encoding="utf-8",
    )

    with pytest.raises(StrategyConfigError, match="positioning"):
        load_strategy_config(config_path)


def test_invalid_crowding_flag_config_fails_fast(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid_crowding_flag.toml"
    config_path.write_text(
        DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8").replace(
            "oi_intensity_percentile_min = 90",
            "oi_intensity_percentile_min = 120",
        ),
        encoding="utf-8",
    )

    with pytest.raises(StrategyConfigError, match="oi_intensity_percentile_min"):
        load_strategy_config(config_path)


def test_invalid_price_level_breakout_config_fails_fast(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid_price_level_breakout.toml"
    config_path.write_text(
        DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8").replace(
            "breakout_close_buffer_fraction = 0",
            "breakout_close_buffer_fraction = -0.01",
        ),
        encoding="utf-8",
    )

    with pytest.raises(StrategyConfigError, match="breakout_close_buffer_fraction"):
        load_strategy_config(config_path)


def test_invalid_anchored_vwap_price_source_fails_fast(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid_anchored_vwap.toml"
    config_path.write_text(
        DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8").replace(
            'anchored_vwap_price_source = "hlc3"',
            'anchored_vwap_price_source = "ohlc4"',
        ),
        encoding="utf-8",
    )

    with pytest.raises(StrategyConfigError, match="anchored_vwap_price_source"):
        load_strategy_config(config_path)


def test_invalid_volume_profile_config_fails_fast(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid_volume_profile.toml"
    config_path.write_text(
        DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8").replace(
            "volume_profile_value_area_fraction = 0.70",
            "volume_profile_value_area_fraction = 0",
        ),
        encoding="utf-8",
    )

    with pytest.raises(StrategyConfigError, match="volume_profile_value_area_fraction"):
        load_strategy_config(config_path)


def test_invalid_volume_profile_price_source_fails_fast(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid_volume_profile_price_source.toml"
    config_path.write_text(
        DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8").replace(
            'volume_profile_price_source = "hlc3"',
            'volume_profile_price_source = "ohlc4"',
        ),
        encoding="utf-8",
    )

    with pytest.raises(StrategyConfigError, match="volume_profile_price_source"):
        load_strategy_config(config_path)


def test_invalid_level_strength_weight_config_fails_fast(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid_level_strength_weights.toml"
    config_path.write_text(
        DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8").replace(
            "confluence = 0.20",
            "confluence = 0.10",
        ),
        encoding="utf-8",
    )

    with pytest.raises(StrategyConfigError, match="level_strength_weights"):
        load_strategy_config(config_path)


def test_invalid_level_strength_timeframe_scores_fail_fast(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid_level_strength_timeframes.toml"
    config_path.write_text(
        DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8").replace(
            '"1mo" = 100',
            '"1mo" = 101',
        ),
        encoding="utf-8",
    )

    with pytest.raises(StrategyConfigError, match="1mo"):
        load_strategy_config(config_path)


def test_invalid_entry_location_distance_config_fails_fast(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid_entry_location_distance.toml"
    config_path.write_text(
        DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8").replace(
            "entry_location_zero_score_distance_fraction = 0.08",
            "entry_location_zero_score_distance_fraction = 0.01",
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        StrategyConfigError,
        match="entry_location_zero_score_distance_fraction",
    ):
        load_strategy_config(config_path)


def test_invalid_structure_score_weights_fail_fast(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid_structure_score_weights.toml"
    config_path.write_text(
        DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8").replace(
            "rr_quality = 0.20",
            "rr_quality = 0.10",
        ),
        encoding="utf-8",
    )

    with pytest.raises(StrategyConfigError, match="structure_score"):
        load_strategy_config(config_path)


def test_invalid_full_regime_weights_fail_fast(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid_full_regime_weights.toml"
    config_path.write_text(
        DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8").replace(
            "liquidity = 0.10",
            "liquidity = 0.05",
        ),
        encoding="utf-8",
    )

    with pytest.raises(StrategyConfigError, match="full_regime"):
        load_strategy_config(config_path)


def test_invalid_regime_smoothing_weights_fail_fast(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid_regime_smoothing_weights.toml"
    config_path.write_text(
        DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8").replace(
            "new_weight = 0.30",
            "new_weight = 0.20",
        ),
        encoding="utf-8",
    )

    with pytest.raises(StrategyConfigError, match="regime_smoothing"):
        load_strategy_config(config_path)


def test_invalid_regime_smoothing_fraction_fails_fast(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid_regime_smoothing_fraction.toml"
    config_path.write_text(
        DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8").replace(
            "previous_weight = 0.70",
            "previous_weight = 1.20",
        ),
        encoding="utf-8",
    )

    with pytest.raises(StrategyConfigError, match="previous_weight"):
        load_strategy_config(config_path)


def test_invalid_stress_flag_config_fails_fast(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid_stress_flag.toml"
    config_path.write_text(
        DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8").replace(
            "volatility_percentile_min = 95",
            "volatility_percentile_min = 120",
        ),
        encoding="utf-8",
    )

    with pytest.raises(StrategyConfigError, match="volatility_percentile_min"):
        load_strategy_config(config_path)


def test_invalid_stress_downside_threshold_fails_fast(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid_stress_downside.toml"
    config_path.write_text(
        DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8").replace(
            "downside_return_min = -0.10",
            "downside_return_min = 0.10",
        ),
        encoding="utf-8",
    )

    with pytest.raises(StrategyConfigError, match="downside_return_min"):
        load_strategy_config(config_path)
