"""Versioned strategy configuration schema and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Any, Self


DEFAULT_STRATEGY_CONFIG_PATH = Path(__file__).parent / "strategy" / "default.toml"
PERCENT_FRACTION_MIN = 0.0
PERCENT_FRACTION_MAX = 1.0
SCORE_MIN = 0.0
SCORE_MAX = 100.0
FULL_FLOW_WEIGHT_KEYS = (
    "etf_norm_5",
    "etf_norm_20",
    "flow_accel",
    "cvd_spread",
    "spot_dominance",
)
CORE_FLOW_WEIGHT_KEYS = ("etf_norm_5", "etf_norm_20", "flow_accel")
CORE_REGIME_WEIGHT_KEYS = ("trend", "flow", "volatility", "positioning")
FULL_REGIME_WEIGHT_KEYS = (
    "trend",
    "flow",
    "macro",
    "onchain",
    "volatility",
    "liquidity",
)
POSITIONING_WEIGHT_KEYS = (
    "funding_health",
    "oi_health",
    "basis_health",
    "leverage_health",
)
STRUCTURE_SCORE_WEIGHT_KEYS = (
    "level_strength",
    "entry_location",
    "rr_quality",
    "confluence",
)
ANCHORED_VWAP_PRICE_SOURCES = ("hlc3", "close")
VOLUME_PROFILE_PRICE_SOURCES = ("hlc3", "close")
LEVEL_STRENGTH_WEIGHT_KEYS = (
    "timeframe",
    "touch_count",
    "reaction_magnitude",
    "volume",
    "confluence",
)
LEVEL_STRENGTH_TIMEFRAME_SCORE_KEYS = ("1h", "1d", "1w", "1mo", "unknown")


class StrategyConfigError(ValueError):
    """Raised when strategy configuration is missing or invalid."""


@dataclass(frozen=True)
class ConfigIdentity:
    config_version: str
    strategy_version: str
    parameter_set_id: str

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        return cls(
            config_version=_required_string(data, "config_version"),
            strategy_version=_required_string(data, "strategy_version"),
            parameter_set_id=_required_string(data, "parameter_set_id"),
        )


@dataclass(frozen=True)
class EntryThresholds:
    ignore_below: float
    watch_min: float
    valid_trade_min: float
    strong_setup_min: float
    exceptional_min: float
    short_valid_trade_min: float

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        thresholds = cls(
            ignore_below=_required_score(data, "ignore_below"),
            watch_min=_required_score(data, "watch_min"),
            valid_trade_min=_required_score(data, "valid_trade_min"),
            strong_setup_min=_required_score(data, "strong_setup_min"),
            exceptional_min=_required_score(data, "exceptional_min"),
            short_valid_trade_min=_required_score(data, "short_valid_trade_min"),
        )
        if thresholds.watch_min < thresholds.ignore_below:
            raise StrategyConfigError(
                "entry_thresholds.watch_min must be >= entry_thresholds.ignore_below",
            )
        _require_strictly_increasing(
            [
                thresholds.watch_min,
                thresholds.valid_trade_min,
                thresholds.strong_setup_min,
                thresholds.exceptional_min,
            ],
            "entry_thresholds",
        )
        return thresholds


@dataclass(frozen=True)
class HoldThresholds:
    possible_add_min: float
    hold_min: float
    no_add_min: float
    defensive_min: float
    trim_min: float
    exit_below: float

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        thresholds = cls(
            possible_add_min=_required_score(data, "possible_add_min"),
            hold_min=_required_score(data, "hold_min"),
            no_add_min=_required_score(data, "no_add_min"),
            defensive_min=_required_score(data, "defensive_min"),
            trim_min=_required_score(data, "trim_min"),
            exit_below=_required_score(data, "exit_below"),
        )
        _require_strictly_decreasing(
            [
                thresholds.possible_add_min,
                thresholds.hold_min,
                thresholds.no_add_min,
                thresholds.defensive_min,
                thresholds.trim_min,
            ],
            "hold_thresholds",
        )
        if thresholds.exit_below > thresholds.trim_min:
            raise StrategyConfigError(
                "hold_thresholds.exit_below must be <= hold_thresholds.trim_min",
            )
        return thresholds


@dataclass(frozen=True)
class AddThresholds:
    add_min: float
    existing_position_must_be_profitable: bool
    stop_must_improve: bool
    no_average_down: bool

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        return cls(
            add_min=_required_score(data, "add_min"),
            existing_position_must_be_profitable=_required_bool(
                data,
                "existing_position_must_be_profitable",
            ),
            stop_must_improve=_required_bool(data, "stop_must_improve"),
            no_average_down=_required_bool(data, "no_average_down"),
        )


@dataclass(frozen=True)
class RiskBand:
    min_entry_conviction: float
    max_entry_conviction: float | None
    risk_fraction_nav: float

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        max_value = data.get("max_entry_conviction")
        if max_value is not None:
            max_value = _score(max_value, "max_entry_conviction")

        band = cls(
            min_entry_conviction=_required_score(data, "min_entry_conviction"),
            max_entry_conviction=max_value,
            risk_fraction_nav=_required_fraction(data, "risk_fraction_nav"),
        )
        if (
            band.max_entry_conviction is not None
            and band.max_entry_conviction <= band.min_entry_conviction
        ):
            raise StrategyConfigError(
                "risk_schedule band max_entry_conviction must be greater than "
                "min_entry_conviction",
            )
        return band


@dataclass(frozen=True)
class RiskConfig:
    schedule: tuple[RiskBand, ...]
    max_risk_at_stop_fraction_nav: float

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        raw_schedule = data.get("schedule")
        if not isinstance(raw_schedule, list) or not raw_schedule:
            raise StrategyConfigError("risk.schedule must be a non-empty list")

        schedule = tuple(_risk_band(item) for item in raw_schedule)
        _validate_risk_schedule(schedule)
        return cls(
            schedule=schedule,
            max_risk_at_stop_fraction_nav=_required_fraction(
                data,
                "max_risk_at_stop_fraction_nav",
            ),
        )


@dataclass(frozen=True)
class StopBufferConfig:
    atr_period: int
    atr_multiplier: float
    minimum_level_noise_multiplier: float
    sweep_atr_multipliers: tuple[float, ...]

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        config = cls(
            atr_period=_required_positive_int(data, "atr_period"),
            atr_multiplier=_required_positive_float(data, "atr_multiplier"),
            minimum_level_noise_multiplier=_required_positive_float(
                data,
                "minimum_level_noise_multiplier",
            ),
            sweep_atr_multipliers=_required_positive_float_tuple(
                data,
                "sweep_atr_multipliers",
            ),
        )
        if config.atr_multiplier not in config.sweep_atr_multipliers:
            raise StrategyConfigError(
                "stop_buffers.atr_multiplier must be included in "
                "stop_buffers.sweep_atr_multipliers",
            )
        return config


@dataclass(frozen=True)
class SetupRequirements:
    bull_trend_continuation: dict[str, float | bool]
    bullish_reset: dict[str, float | int | bool]
    capitulation_reversal: dict[str, float | int | bool]
    bearish_distribution: dict[str, float | bool]
    supported_setups: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        supported_setups = _required_string_tuple(data, "supported_setups")
        if not supported_setups:
            raise StrategyConfigError("setup_requirements.supported_setups cannot be empty")

        bull_trend = _required_mapping(data, "bull_trend_continuation")
        bullish_reset = _required_mapping(data, "bullish_reset")
        capitulation_reversal = _required_mapping(data, "capitulation_reversal")
        bearish_distribution = _required_mapping(data, "bearish_distribution")
        requirements = cls(
            supported_setups=supported_setups,
            bull_trend_continuation={
                "regime_min": _required_score(bull_trend, "regime_min"),
                "trend_min": _required_score(bull_trend, "trend_min"),
                "flow_min": _required_score(bull_trend, "flow_min"),
                "positioning_min": _required_score(bull_trend, "positioning_min"),
                "structure_min": _required_score(bull_trend, "structure_min"),
                "minimum_rr": _required_positive_float(bull_trend, "minimum_rr"),
                "entry_conviction_min": _required_score(
                    bull_trend,
                    "entry_conviction_min",
                ),
                "require_no_stress": _required_bool(bull_trend, "require_no_stress"),
                "require_no_severe_crowding": _required_bool(
                    bull_trend,
                    "require_no_severe_crowding",
                ),
            },
            bullish_reset={
                "regime_min": _required_score(bullish_reset, "regime_min"),
                "trend_min": _required_score(bullish_reset, "trend_min"),
                "correction_min_fraction": _required_fraction(
                    bullish_reset,
                    "correction_min_fraction",
                ),
                "correction_max_fraction": _required_fraction(
                    bullish_reset,
                    "correction_max_fraction",
                ),
                "funding_health_improving_days": _required_positive_int(
                    bullish_reset,
                    "funding_health_improving_days",
                ),
                "oi_health_stable_days": _required_positive_int(
                    bullish_reset,
                    "oi_health_stable_days",
                ),
                "flow_accel_improving_days": _required_positive_int(
                    bullish_reset,
                    "flow_accel_improving_days",
                ),
                "structure_min": _required_score(bullish_reset, "structure_min"),
                "entry_trigger_required": _required_bool(
                    bullish_reset,
                    "entry_trigger_required",
                ),
                "entry_conviction_min": _required_score(
                    bullish_reset,
                    "entry_conviction_min",
                ),
                "minimum_rr": _required_positive_float(bullish_reset, "minimum_rr"),
            },
            capitulation_reversal={
                "capitulation_required": _required_bool(
                    capitulation_reversal,
                    "capitulation_required",
                ),
                "confirmation_required": _required_bool(
                    capitulation_reversal,
                    "confirmation_required",
                ),
                "confirmation_must_follow_capitulation": _required_bool(
                    capitulation_reversal,
                    "confirmation_must_follow_capitulation",
                ),
                "max_confirmation_lag_days": _required_positive_int(
                    capitulation_reversal,
                    "max_confirmation_lag_days",
                ),
                "structure_min": _required_score(
                    capitulation_reversal,
                    "structure_min",
                ),
                "entry_conviction_min": _required_score(
                    capitulation_reversal,
                    "entry_conviction_min",
                ),
                "minimum_rr": _required_positive_float(
                    capitulation_reversal,
                    "minimum_rr",
                ),
            },
            bearish_distribution={
                "regime_max": _required_score(bearish_distribution, "regime_max"),
                "trend_max": _required_score(bearish_distribution, "trend_max"),
                "flow_max": _required_score(bearish_distribution, "flow_max"),
                "positioning_max": _required_score(
                    bearish_distribution,
                    "positioning_max",
                ),
                "structure_max": _required_score(
                    bearish_distribution,
                    "structure_max",
                ),
                "entry_conviction_min": _required_score(
                    bearish_distribution,
                    "entry_conviction_min",
                ),
                "minimum_rr": _required_positive_float(
                    bearish_distribution,
                    "minimum_rr",
                ),
                "distribution_required": _required_bool(
                    bearish_distribution,
                    "distribution_required",
                ),
                "short_trigger_required": _required_bool(
                    bearish_distribution,
                    "short_trigger_required",
                ),
                "require_no_stress": _required_bool(
                    bearish_distribution,
                    "require_no_stress",
                ),
            },
        )
        if (
            requirements.bullish_reset["correction_max_fraction"]
            <= requirements.bullish_reset["correction_min_fraction"]
        ):
            raise StrategyConfigError(
                "setup_requirements.bullish_reset correction_max_fraction must be "
                "> correction_min_fraction",
            )
        return requirements


@dataclass(frozen=True)
class RegimeThresholds:
    strong_bull_min: float
    bull_min: float
    mild_bull_min: float
    neutral_min: float
    mild_bear_min: float
    bear_min: float

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        thresholds = cls(
            strong_bull_min=_required_score(data, "strong_bull_min"),
            bull_min=_required_score(data, "bull_min"),
            mild_bull_min=_required_score(data, "mild_bull_min"),
            neutral_min=_required_score(data, "neutral_min"),
            mild_bear_min=_required_score(data, "mild_bear_min"),
            bear_min=_required_score(data, "bear_min"),
        )
        _require_strictly_decreasing(
            [
                thresholds.strong_bull_min,
                thresholds.bull_min,
                thresholds.mild_bull_min,
                thresholds.neutral_min,
                thresholds.mild_bear_min,
                thresholds.bear_min,
            ],
            "regime_thresholds",
        )
        return thresholds


@dataclass(frozen=True)
class PriceLevelParameters:
    swing_window_weeks: int
    swing_window_months: int
    cluster_distance_fraction: float
    minimum_level_strength: float
    breakout_close_buffer_fraction: float
    reclaim_close_buffer_fraction: float
    anchored_vwap_price_source: str
    volume_profile_price_source: str
    volume_profile_bin_size_fraction: float
    volume_profile_value_area_fraction: float
    volume_profile_hvn_volume_fraction: float
    volume_profile_min_bars: int
    level_strength_weights: dict[str, float]
    level_strength_timeframe_scores: dict[str, float]
    level_strength_touch_count_full: int
    level_strength_reaction_full_fraction: float
    entry_location_full_score_distance_fraction: float
    entry_location_zero_score_distance_fraction: float
    rr_minimum: float
    rr_preferred_min: float
    rr_preferred_max: float
    reward_reference_order: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        parameters = cls(
            swing_window_weeks=_required_positive_int(data, "swing_window_weeks"),
            swing_window_months=_required_positive_int(data, "swing_window_months"),
            cluster_distance_fraction=_required_fraction(data, "cluster_distance_fraction"),
            minimum_level_strength=_required_score(data, "minimum_level_strength"),
            breakout_close_buffer_fraction=_required_fraction(
                data,
                "breakout_close_buffer_fraction",
            ),
            reclaim_close_buffer_fraction=_required_fraction(
                data,
                "reclaim_close_buffer_fraction",
            ),
            anchored_vwap_price_source=_required_choice(
                data,
                "anchored_vwap_price_source",
                ANCHORED_VWAP_PRICE_SOURCES,
            ),
            volume_profile_price_source=_required_choice(
                data,
                "volume_profile_price_source",
                VOLUME_PROFILE_PRICE_SOURCES,
            ),
            volume_profile_bin_size_fraction=_required_positive_fraction(
                data,
                "volume_profile_bin_size_fraction",
            ),
            volume_profile_value_area_fraction=_required_positive_fraction(
                data,
                "volume_profile_value_area_fraction",
            ),
            volume_profile_hvn_volume_fraction=_required_positive_fraction(
                data,
                "volume_profile_hvn_volume_fraction",
            ),
            volume_profile_min_bars=_required_positive_int(
                data,
                "volume_profile_min_bars",
            ),
            level_strength_weights=_required_weight_mapping(
                data,
                "level_strength_weights",
                expected_keys=LEVEL_STRENGTH_WEIGHT_KEYS,
            ),
            level_strength_timeframe_scores=_required_score_mapping(
                data,
                "level_strength_timeframe_scores",
                expected_keys=LEVEL_STRENGTH_TIMEFRAME_SCORE_KEYS,
            ),
            level_strength_touch_count_full=_required_positive_int(
                data,
                "level_strength_touch_count_full",
            ),
            level_strength_reaction_full_fraction=_required_positive_fraction(
                data,
                "level_strength_reaction_full_fraction",
            ),
            entry_location_full_score_distance_fraction=_required_positive_fraction(
                data,
                "entry_location_full_score_distance_fraction",
            ),
            entry_location_zero_score_distance_fraction=_required_positive_fraction(
                data,
                "entry_location_zero_score_distance_fraction",
            ),
            rr_minimum=_required_positive_float(data, "rr_minimum"),
            rr_preferred_min=_required_positive_float(data, "rr_preferred_min"),
            rr_preferred_max=_required_positive_float(data, "rr_preferred_max"),
            reward_reference_order=_required_string_tuple(
                data,
                "reward_reference_order",
            ),
        )
        if parameters.rr_preferred_min < parameters.rr_minimum:
            raise StrategyConfigError(
                "price_levels.rr_preferred_min must be >= price_levels.rr_minimum",
            )
        if parameters.rr_preferred_max < parameters.rr_preferred_min:
            raise StrategyConfigError(
                "price_levels.rr_preferred_max must be >= price_levels.rr_preferred_min",
            )
        if (
            parameters.entry_location_zero_score_distance_fraction
            <= parameters.entry_location_full_score_distance_fraction
        ):
            raise StrategyConfigError(
                "price_levels.entry_location_zero_score_distance_fraction "
                "must be > entry_location_full_score_distance_fraction",
            )
        return parameters


@dataclass(frozen=True)
class ReclaimTriggerConfig:
    confirmation_bars: int
    hold_buffer_fraction: float
    close_buffer_fraction: float

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        return cls(
            confirmation_bars=_required_positive_int(data, "confirmation_bars"),
            hold_buffer_fraction=_required_fraction(data, "hold_buffer_fraction"),
            close_buffer_fraction=_required_fraction(data, "close_buffer_fraction"),
        )


@dataclass(frozen=True)
class EntryTriggerConfig:
    reclaim: ReclaimTriggerConfig

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        return cls(
            reclaim=ReclaimTriggerConfig.from_mapping(
                _required_mapping(data, "reclaim"),
            ),
        )


@dataclass(frozen=True)
class CrowdingFlagConfig:
    funding_zscore_min: float
    basis_zscore_min: float
    oi_intensity_percentile_min: float
    entry_quality_penalty: float

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        return cls(
            funding_zscore_min=_required_non_negative_float(
                data,
                "funding_zscore_min",
            ),
            basis_zscore_min=_required_non_negative_float(data, "basis_zscore_min"),
            oi_intensity_percentile_min=_required_score(
                data,
                "oi_intensity_percentile_min",
            ),
            entry_quality_penalty=_required_score(data, "entry_quality_penalty"),
        )


@dataclass(frozen=True)
class PositioningFlagConfig:
    crowding: CrowdingFlagConfig

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        return cls(
            crowding=CrowdingFlagConfig.from_mapping(
                _required_mapping(data, "crowding"),
            ),
        )


@dataclass(frozen=True)
class StressFlagConfig:
    volatility_percentile_min: float
    liquidation_percentile_min: float
    downside_return_min: float
    funding_abs_zscore_min: float
    basis_abs_zscore_min: float
    max_exposure_multiplier: float
    block_new_trades: bool

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        downside_return_min = _required_float(data, "downside_return_min")
        if downside_return_min >= 0:
            raise StrategyConfigError("downside_return_min must be negative")
        return cls(
            volatility_percentile_min=_required_score(
                data,
                "volatility_percentile_min",
            ),
            liquidation_percentile_min=_required_score(
                data,
                "liquidation_percentile_min",
            ),
            downside_return_min=downside_return_min,
            funding_abs_zscore_min=_required_non_negative_float(
                data,
                "funding_abs_zscore_min",
            ),
            basis_abs_zscore_min=_required_non_negative_float(
                data,
                "basis_abs_zscore_min",
            ),
            max_exposure_multiplier=_required_fraction(
                data,
                "max_exposure_multiplier",
            ),
            block_new_trades=_required_bool(data, "block_new_trades"),
        )


@dataclass(frozen=True)
class CapitulationFlagConfig:
    range_percentile_min: float
    downside_return_min: float
    liquidation_percentile_min: float
    volatility_percentile_min: float
    funding_zscore_max: float

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        downside_return_min = _required_float(data, "downside_return_min")
        if downside_return_min >= 0:
            raise StrategyConfigError("downside_return_min must be negative")
        funding_zscore_max = _required_float(data, "funding_zscore_max")
        if funding_zscore_max >= 0:
            raise StrategyConfigError("funding_zscore_max must be negative")
        return cls(
            range_percentile_min=_required_score(data, "range_percentile_min"),
            downside_return_min=downside_return_min,
            liquidation_percentile_min=_required_score(
                data,
                "liquidation_percentile_min",
            ),
            volatility_percentile_min=_required_score(
                data,
                "volatility_percentile_min",
            ),
            funding_zscore_max=funding_zscore_max,
        )


@dataclass(frozen=True)
class EuphoriaFlagConfig:
    range_percentile_min: float
    upside_return_min: float
    funding_zscore_min: float
    basis_zscore_min: float
    oi_intensity_percentile_min: float
    volatility_percentile_min: float

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        upside_return_min = _required_float(data, "upside_return_min")
        if upside_return_min <= 0:
            raise StrategyConfigError("upside_return_min must be positive")
        return cls(
            range_percentile_min=_required_score(data, "range_percentile_min"),
            upside_return_min=upside_return_min,
            funding_zscore_min=_required_non_negative_float(
                data,
                "funding_zscore_min",
            ),
            basis_zscore_min=_required_non_negative_float(
                data,
                "basis_zscore_min",
            ),
            oi_intensity_percentile_min=_required_score(
                data,
                "oi_intensity_percentile_min",
            ),
            volatility_percentile_min=_required_score(
                data,
                "volatility_percentile_min",
            ),
        )


@dataclass(frozen=True)
class VolatilityFlagConfig:
    stress: StressFlagConfig
    capitulation: CapitulationFlagConfig
    euphoria: EuphoriaFlagConfig

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        return cls(
            stress=StressFlagConfig.from_mapping(
                _required_mapping(data, "stress"),
            ),
            capitulation=CapitulationFlagConfig.from_mapping(
                _required_mapping(data, "capitulation"),
            ),
            euphoria=EuphoriaFlagConfig.from_mapping(
                _required_mapping(data, "euphoria"),
            ),
        )


@dataclass(frozen=True)
class RegimeSmoothingConfig:
    previous_weight: float
    new_weight: float

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        config = cls(
            previous_weight=_required_fraction(data, "previous_weight"),
            new_weight=_required_fraction(data, "new_weight"),
        )
        if abs(config.previous_weight + config.new_weight - 1.0) > 0.000001:
            raise StrategyConfigError("regime_smoothing weights must sum to 1.0")
        return config


@dataclass(frozen=True)
class ScoringWeights:
    entry_conviction: dict[str, float]
    hold_score: dict[str, float]
    add_score: dict[str, float]
    full_flow: dict[str, float]
    core_flow: dict[str, float]
    core_regime: dict[str, float]
    full_regime: dict[str, float]
    positioning: dict[str, float]
    structure_score: dict[str, float]

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        return cls(
            entry_conviction=_required_weight_mapping(data, "entry_conviction"),
            hold_score=_required_weight_mapping(data, "hold_score"),
            add_score=_required_weight_mapping(data, "add_score"),
            full_flow=_required_weight_mapping(
                data,
                "full_flow",
                expected_keys=FULL_FLOW_WEIGHT_KEYS,
            ),
            core_flow=_required_weight_mapping(
                data,
                "core_flow",
                expected_keys=CORE_FLOW_WEIGHT_KEYS,
            ),
            core_regime=_required_weight_mapping(
                data,
                "core_regime",
                expected_keys=CORE_REGIME_WEIGHT_KEYS,
            ),
            full_regime=_required_weight_mapping(
                data,
                "full_regime",
                expected_keys=FULL_REGIME_WEIGHT_KEYS,
            ),
            positioning=_required_weight_mapping(
                data,
                "positioning",
                expected_keys=POSITIONING_WEIGHT_KEYS,
            ),
            structure_score=_required_weight_mapping(
                data,
                "structure_score",
                expected_keys=STRUCTURE_SCORE_WEIGHT_KEYS,
            ),
        )


@dataclass(frozen=True)
class BacktestAssumptions:
    initial_cash: float
    fee_bps: float
    slippage_bps: float
    funding_cost_bps_per_day: float
    max_trades_per_year: int
    allow_short_trades: bool
    execution_timing: str

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        return cls(
            initial_cash=_required_positive_float(data, "initial_cash"),
            fee_bps=_required_non_negative_float(data, "fee_bps"),
            slippage_bps=_required_non_negative_float(data, "slippage_bps"),
            funding_cost_bps_per_day=_required_non_negative_float(
                data,
                "funding_cost_bps_per_day",
            ),
            max_trades_per_year=_required_positive_int(data, "max_trades_per_year"),
            allow_short_trades=_required_bool(data, "allow_short_trades"),
            execution_timing=_required_string(data, "execution_timing"),
        )


@dataclass(frozen=True)
class StrategyConfig:
    identity: ConfigIdentity
    entry_thresholds: EntryThresholds
    hold_thresholds: HoldThresholds
    add_thresholds: AddThresholds
    risk: RiskConfig
    stop_buffers: StopBufferConfig
    setup_requirements: SetupRequirements
    regime_thresholds: RegimeThresholds
    price_levels: PriceLevelParameters
    entry_triggers: EntryTriggerConfig
    scoring_weights: ScoringWeights
    regime_smoothing: RegimeSmoothingConfig
    positioning_flags: PositioningFlagConfig
    volatility_flags: VolatilityFlagConfig
    backtest: BacktestAssumptions

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        return cls(
            identity=ConfigIdentity.from_mapping(_required_mapping(data, "identity")),
            entry_thresholds=EntryThresholds.from_mapping(
                _required_mapping(data, "entry_thresholds"),
            ),
            hold_thresholds=HoldThresholds.from_mapping(
                _required_mapping(data, "hold_thresholds"),
            ),
            add_thresholds=AddThresholds.from_mapping(
                _required_mapping(data, "add_thresholds"),
            ),
            risk=RiskConfig.from_mapping(_required_mapping(data, "risk")),
            stop_buffers=StopBufferConfig.from_mapping(
                _required_mapping(data, "stop_buffers"),
            ),
            setup_requirements=SetupRequirements.from_mapping(
                _required_mapping(data, "setup_requirements"),
            ),
            regime_thresholds=RegimeThresholds.from_mapping(
                _required_mapping(data, "regime_thresholds"),
            ),
            price_levels=PriceLevelParameters.from_mapping(
                _required_mapping(data, "price_levels"),
            ),
            entry_triggers=EntryTriggerConfig.from_mapping(
                _required_mapping(data, "entry_triggers"),
            ),
            scoring_weights=ScoringWeights.from_mapping(
                _required_mapping(data, "scoring_weights"),
            ),
            regime_smoothing=RegimeSmoothingConfig.from_mapping(
                _required_mapping(data, "regime_smoothing"),
            ),
            positioning_flags=PositioningFlagConfig.from_mapping(
                _required_mapping(data, "positioning_flags"),
            ),
            volatility_flags=VolatilityFlagConfig.from_mapping(
                _required_mapping(data, "volatility_flags"),
            ),
            backtest=BacktestAssumptions.from_mapping(_required_mapping(data, "backtest")),
        )

    def run_metadata(self) -> dict[str, str]:
        """Return the immutable config identity every persisted run should store."""

        return {
            "config_version": self.identity.config_version,
            "strategy_version": self.identity.strategy_version,
            "parameter_set_id": self.identity.parameter_set_id,
        }


def load_strategy_config(path: Path | None = None) -> StrategyConfig:
    """Load and validate the versioned strategy configuration."""

    config_path = path or DEFAULT_STRATEGY_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(f"Strategy config file not found: {config_path}")

    with config_path.open("rb") as config_file:
        data = tomllib.load(config_file)

    if not isinstance(data, dict):
        raise StrategyConfigError("Strategy config must be a TOML table")

    return StrategyConfig.from_mapping(data)


def _risk_band(data: Any) -> RiskBand:
    if not isinstance(data, dict):
        raise StrategyConfigError("risk.schedule entries must be tables")
    return RiskBand.from_mapping(data)


def _validate_risk_schedule(schedule: tuple[RiskBand, ...]) -> None:
    ordered = sorted(schedule, key=lambda band: band.min_entry_conviction)
    if tuple(ordered) != schedule:
        raise StrategyConfigError(
            "risk.schedule must be ordered by min_entry_conviction",
        )

    for previous, current in zip(schedule, schedule[1:]):
        if previous.max_entry_conviction is None:
            raise StrategyConfigError("only the final risk.schedule band may be open-ended")
        if current.min_entry_conviction <= previous.min_entry_conviction:
            raise StrategyConfigError(
                "risk.schedule min_entry_conviction values must increase",
            )


def _required_mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise StrategyConfigError(f"{key} must be a table")
    return value


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise StrategyConfigError(f"{key} must be a non-empty string")
    return value


def _required_choice(data: dict[str, Any], key: str, choices: tuple[str, ...]) -> str:
    value = _required_string(data, key)
    if value not in choices:
        raise StrategyConfigError(f"{key} must be one of {choices}")
    return value


def _required_string_tuple(data: dict[str, Any], key: str) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        raise StrategyConfigError(f"{key} must be a non-empty list of strings")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise StrategyConfigError(f"{key} must contain only non-empty strings")
    return tuple(value)


def _required_bool(data: dict[str, Any], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise StrategyConfigError(f"{key} must be a boolean")
    return value


def _required_weight_mapping(
    data: dict[str, Any],
    key: str,
    *,
    expected_keys: tuple[str, ...] | None = None,
) -> dict[str, float]:
    mapping = _required_mapping(data, key)
    if expected_keys is not None:
        missing = set(expected_keys) - set(mapping)
        extra = set(mapping) - set(expected_keys)
        if missing or extra:
            raise StrategyConfigError(
                f"{key} weights must exactly match {expected_keys}; "
                f"missing={sorted(missing)}, extra={sorted(extra)}"
            )
    weights: dict[str, float] = {}
    for weight_name, value in mapping.items():
        weights[weight_name] = _required_fraction(mapping, weight_name)

    total_weight = sum(weights.values())
    if abs(total_weight - 1.0) > 0.000001:
        raise StrategyConfigError(f"{key} weights must sum to 1.0")

    return weights


def _required_score_mapping(
    data: dict[str, Any],
    key: str,
    *,
    expected_keys: tuple[str, ...] | None = None,
) -> dict[str, float]:
    mapping = _required_mapping(data, key)
    if expected_keys is not None:
        missing = set(expected_keys) - set(mapping)
        extra = set(mapping) - set(expected_keys)
        if missing or extra:
            raise StrategyConfigError(
                f"{key} scores must exactly match {expected_keys}; "
                f"missing={sorted(missing)}, extra={sorted(extra)}"
            )
    return {score_name: _required_score(mapping, score_name) for score_name in mapping}


def _required_positive_int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise StrategyConfigError(f"{key} must be a positive integer")
    return value


def _required_non_negative_float(data: dict[str, Any], key: str) -> float:
    value = data.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool) or value < 0:
        raise StrategyConfigError(f"{key} must be a non-negative number")
    return float(value)


def _required_positive_float(data: dict[str, Any], key: str) -> float:
    value = _required_non_negative_float(data, key)
    if value <= 0:
        raise StrategyConfigError(f"{key} must be positive")
    return value


def _required_float(data: dict[str, Any], key: str) -> float:
    value = data.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise StrategyConfigError(f"{key} must be numeric")
    return float(value)


def _required_score(data: dict[str, Any], key: str) -> float:
    return _score(data.get(key), key)


def _score(value: Any, key: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise StrategyConfigError(f"{key} must be a numeric score")
    numeric_value = float(value)
    if not SCORE_MIN <= numeric_value <= SCORE_MAX:
        raise StrategyConfigError(f"{key} must be between 0 and 100")
    return numeric_value


def _required_fraction(data: dict[str, Any], key: str) -> float:
    value = data.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise StrategyConfigError(f"{key} must be a numeric fraction")
    numeric_value = float(value)
    if not PERCENT_FRACTION_MIN <= numeric_value <= PERCENT_FRACTION_MAX:
        raise StrategyConfigError(f"{key} must be between 0 and 1")
    return numeric_value


def _required_positive_fraction(data: dict[str, Any], key: str) -> float:
    value = _required_fraction(data, key)
    if value <= 0:
        raise StrategyConfigError(f"{key} must be > 0 and <= 1")
    return value


def _required_positive_float_tuple(data: dict[str, Any], key: str) -> tuple[float, ...]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        raise StrategyConfigError(f"{key} must be a non-empty list of numbers")
    return tuple(_positive_float(item, key) for item in value)


def _positive_float(value: Any, key: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool) or value <= 0:
        raise StrategyConfigError(f"{key} must contain only positive numbers")
    return float(value)


def _require_strictly_increasing(values: list[float], section: str) -> None:
    for previous, current in zip(values, values[1:]):
        if current <= previous:
            raise StrategyConfigError(f"{section} values must be strictly increasing")


def _require_strictly_decreasing(values: list[float], section: str) -> None:
    for previous, current in zip(values, values[1:]):
        if current >= previous:
            raise StrategyConfigError(f"{section} values must be strictly decreasing")
