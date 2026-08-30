"""Volatility feature helpers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from btc_predictor.data import OhlcvBar, require_utc_datetime
from btc_predictor.features._scoring import (
    decimal_bounded_linear,
    decimal_weighted_score,
)
from btc_predictor.quant.comparisons import decision_greater_equal, decision_less_equal
from btc_predictor.quant.rolling import realized_volatility as quant_realized_volatility


RV_7_FEATURE_ID = "RV_7"
RV_20_FEATURE_ID = "RV_20"
RV_60_FEATURE_ID = "RV_60"
VOLATILITY_COMPRESSION_RATIO_FEATURE_ID = "VOL_COMPRESSION_RATIO"
VOLATILITY_PERCENTILE_FEATURE_ID = "VOL_PERCENTILE_2Y"
COMPRESSION_SCORE_FEATURE_ID = "COMPRESSION_SCORE"
VOLATILITY_SCORE_FEATURE_ID = "VOLATILITY_SCORE"
ORDERLINESS_SCORE_FEATURE_ID = "ORDERLINESS_SCORE"
STRESS_FLAG_FEATURE_ID = "STRESS"
CAPITULATION_FLAG_FEATURE_ID = "CAPITULATION"
EUPHORIA_FLAG_FEATURE_ID = "EUPHORIA"
STRESS_FLAG_EFFECTS = (
    "NO_ADD",
    "REDUCE_MAX_EXPOSURE",
    "OPTIONALLY_BLOCK_NEW_TRADES",
)
CAPITULATION_FLAG_EFFECTS = (
    "REQUIRE_REVERSAL_CONFIRMATION",
    "NO_ADD_UNTIL_CONFIRMATION",
)
EUPHORIA_FLAG_EFFECTS = (
    "NO_ADD",
    "REDUCE_ENTRY_QUALITY",
    "TIGHTEN_PROFIT_PROTECTION",
)
ORDERLINESS_SCORE_COMPONENT_IDS = (
    "extreme_range",
    "disorderly_downside",
    "liquidation_cascade",
    "volatility_spike",
)
DEFAULT_ORDERLINESS_SCORE_WEIGHTS = {
    "extreme_range": Decimal("0.25"),
    "disorderly_downside": Decimal("0.25"),
    "liquidation_cascade": Decimal("0.25"),
    "volatility_spike": Decimal("0.25"),
}
VOLATILITY_SCORE_COMPONENT_IDS = (
    "compression",
    "orderliness",
)
DEFAULT_VOLATILITY_SCORE_WEIGHTS = {
    "compression": Decimal("0.5"),
    "orderliness": Decimal("0.5"),
}
VOLATILITY_REGIMES = (
    "COMPRESSED",
    "NORMAL",
    "ELEVATED",
    "STRESSED",
)
REALIZED_VOLATILITY_WINDOWS = (7, 20, 60)
REALIZED_VOLATILITY_FEATURE_IDS = {
    7: RV_7_FEATURE_ID,
    20: RV_20_FEATURE_ID,
    60: RV_60_FEATURE_ID,
}
VOLATILITY_COMPRESSION_RATIO_REASON_CODES = (
    "VOL_COMPRESSION_INPUT_MISSING",
    "VOL_COMPRESSION_ZERO_DENOMINATOR",
)
VOLATILITY_PERCENTILE_REASON_CODES = (
    "VOL_PERCENTILE_INPUT_MISSING",
    "VOL_PERCENTILE_INSUFFICIENT_HISTORY",
)
ORDERLINESS_SCORE_REASON_CODES = (
    "ORDERLINESS_INPUT_MISSING",
    "ORDERLINESS_EXTREME_RANGE",
    "ORDERLINESS_DISORDERLY_DOWNSIDE",
    "ORDERLINESS_LIQUIDATION_CASCADE",
    "ORDERLINESS_VOLATILITY_SPIKE",
)
VOLATILITY_SCORE_REASON_CODES = (
    "VOLATILITY_SCORE_INPUT_MISSING",
    "VOLATILITY_SCORE_COMPLETE",
    "VOLATILITY_COMPRESSED",
    "VOLATILITY_EXPANDING",
    "VOLATILITY_DISORDERLY",
    "VOLATILITY_REGIME_UNKNOWN",
)
STRESS_FLAG_REASON_CODES = (
    "STRESS_INPUT_MISSING",
    "STRESS_EXTREME_VOLATILITY",
    "STRESS_LIQUIDATION_CASCADE",
    "STRESS_DISORDERLY_DOWNSIDE",
    "STRESS_ABNORMAL_FUNDING",
    "STRESS_ABNORMAL_BASIS",
    "STRESS_SYSTEMIC_MARKET_SHOCK",
)
CAPITULATION_FLAG_REASON_CODES = (
    "CAPITULATION_INPUT_MISSING",
    "CAPITULATION_DISORDERLY_DOWNSIDE",
    "CAPITULATION_EXTREME_RANGE",
    "CAPITULATION_LIQUIDATION_CASCADE",
    "CAPITULATION_VOLATILITY_SPIKE",
    "CAPITULATION_NEGATIVE_FUNDING_FLUSH",
    "CAPITULATION_SYSTEMIC_MARKET_SHOCK",
    "CAPITULATION_CONFIRMATION_MISSING",
)
EUPHORIA_FLAG_REASON_CODES = (
    "EUPHORIA_INPUT_MISSING",
    "EUPHORIA_UPSIDE_EXTENSION",
    "EUPHORIA_EXTREME_RANGE",
    "EUPHORIA_FUNDING_OVERHEATED",
    "EUPHORIA_BASIS_OVERHEATED",
    "EUPHORIA_OI_INTENSITY_EXTREME",
    "EUPHORIA_VOLATILITY_SPIKE",
    "EUPHORIA_SYSTEMIC_MARKET_EUPHORIA",
    "EUPHORIA_CONFIRMATION_MISSING",
)
REALIZED_VOLATILITY_REASON_CODES = (
    "REALIZED_VOLATILITY_INPUT_MISSING",
    "REALIZED_VOLATILITY_INSUFFICIENT_HISTORY",
    "REALIZED_VOLATILITY_NON_POSITIVE_CLOSE",
)
DEFAULT_REALIZED_VOLATILITY_ANNUALIZATION_PERIODS = 365
DEFAULT_VOLATILITY_PERCENTILE_WINDOW_DAYS = 730
DEFAULT_VOLATILITY_PERCENTILE_MIN_OBSERVATIONS = 365
# --- COMPRESSION_SCORE_V1 -----------------------------------------------
# PROVISIONAL. The rulebook states the preference "RV7 / RV60 < 1" but does not
# derive the ramp endpoints, so 0.70 and 1.30 are a deterministic Phase-1
# specification chosen symmetrically about that neutral boundary. They are
# research-calibratable and are exposed here as an explicit versioned contract
# so BTC-185 parameter-robustness work can vary them. They must not be treated
# as empirically validated.
COMPRESSION_SCORE_VERSION = "COMPRESSION_SCORE_V1"
DEFAULT_COMPRESSION_FULL_SCORE_RATIO = Decimal("0.70")
DEFAULT_COMPRESSION_NEUTRAL_RATIO = Decimal("1.00")
DEFAULT_COMPRESSION_ZERO_SCORE_RATIO = Decimal("1.30")
COMPRESSION_SCORE_V1_PARAMETERS = {
    "full_compression_ratio": DEFAULT_COMPRESSION_FULL_SCORE_RATIO,
    "neutral_ratio": DEFAULT_COMPRESSION_NEUTRAL_RATIO,
    "zero_compression_ratio": DEFAULT_COMPRESSION_ZERO_SCORE_RATIO,
}
COMPRESSION_SCORE_PARAMETER_STATUS = "PROVISIONAL_RESEARCH_CALIBRATABLE"

# --- VOLATILITY_REGIME_V1 -----------------------------------------------
# PROVISIONAL contextual classification over the 2-year RV20 percentile. The
# stressed boundary reuses the already-authoritative
# DEFAULT_STRESS_VOLATILITY_PERCENTILE_MIN; the compressed/normal boundaries are
# a deterministic Phase-1 quartile split and are research-calibratable.
VOLATILITY_REGIME_VERSION = "VOLATILITY_REGIME_V1"
DEFAULT_VOLATILITY_REGIME_COMPRESSED_MAX = Decimal("25")
DEFAULT_VOLATILITY_REGIME_NORMAL_MAX = Decimal("75")
DEFAULT_VOLATILITY_REGIME_ELEVATED_MAX = Decimal("95")
VOLATILITY_REGIME_V1_PARAMETERS = {
    "compressed_percentile_max": DEFAULT_VOLATILITY_REGIME_COMPRESSED_MAX,
    "normal_percentile_max": DEFAULT_VOLATILITY_REGIME_NORMAL_MAX,
    "elevated_percentile_max": DEFAULT_VOLATILITY_REGIME_ELEVATED_MAX,
}
VOLATILITY_REGIME_PARAMETER_STATUS = "PROVISIONAL_RESEARCH_CALIBRATABLE"
# Diagnostics-only context. None of these is a weighted Volatility Score
# component; BTC-129 factor-nesting audits can rely on this separation.
VOLATILITY_SCORE_DIAGNOSTIC_IDS = (
    "compression_ratio",
    "volatility_percentile",
)
DEFAULT_ORDERLINESS_SCORE_DISORDERLY_MAX = Decimal("60")
DEFAULT_ORDERLINESS_RANGE_PERCENTILE_MAX = Decimal("90")
DEFAULT_ORDERLINESS_DOWNSIDE_RETURN_MIN = Decimal("-0.08")
DEFAULT_ORDERLINESS_LIQUIDATION_PERCENTILE_MAX = Decimal("90")
DEFAULT_ORDERLINESS_VOLATILITY_PERCENTILE_MAX = Decimal("90")
DEFAULT_STRESS_VOLATILITY_PERCENTILE_MIN = Decimal("95")
DEFAULT_STRESS_LIQUIDATION_PERCENTILE_MIN = Decimal("95")
DEFAULT_STRESS_DOWNSIDE_RETURN_MIN = Decimal("-0.10")
DEFAULT_STRESS_FUNDING_ABS_ZSCORE_MIN = Decimal("3")
DEFAULT_STRESS_BASIS_ABS_ZSCORE_MIN = Decimal("3")
DEFAULT_STRESS_MAX_EXPOSURE_MULTIPLIER = Decimal("0.50")
DEFAULT_STRESS_BLOCK_NEW_TRADES = False
DEFAULT_CAPITULATION_RANGE_PERCENTILE_MIN = Decimal("95")
DEFAULT_CAPITULATION_DOWNSIDE_RETURN_MIN = Decimal("-0.12")
DEFAULT_CAPITULATION_LIQUIDATION_PERCENTILE_MIN = Decimal("95")
DEFAULT_CAPITULATION_VOLATILITY_PERCENTILE_MIN = Decimal("95")
DEFAULT_CAPITULATION_FUNDING_ZSCORE_MAX = Decimal("-2")
DEFAULT_EUPHORIA_RANGE_PERCENTILE_MIN = Decimal("95")
DEFAULT_EUPHORIA_UPSIDE_RETURN_MIN = Decimal("0.12")
DEFAULT_EUPHORIA_FUNDING_ZSCORE_MIN = Decimal("2")
DEFAULT_EUPHORIA_BASIS_ZSCORE_MIN = Decimal("2")
DEFAULT_EUPHORIA_OI_INTENSITY_PERCENTILE_MIN = Decimal("95")
DEFAULT_EUPHORIA_VOLATILITY_PERCENTILE_MIN = Decimal("95")


@dataclass(frozen=True)
class RealizedVolatilityResult:
    feature_id: str
    observation_time: datetime
    window_days: int
    annualization_periods: int
    realized_volatility: Decimal | None
    return_count: int
    source_bar_count: int
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "observation_time": require_utc_datetime(
                self.observation_time,
                "observation_time",
            ).isoformat(),
            "window_days": self.window_days,
            "annualization_periods": self.annualization_periods,
            "realized_volatility": (
                str(self.realized_volatility)
                if self.realized_volatility is not None
                else None
            ),
            "return_count": self.return_count,
            "source_bar_count": self.source_bar_count,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class VolatilityCompressionRatioInput:
    rv_7: Decimal | None
    rv_60: Decimal | None

    def as_record(self) -> dict[str, str | None]:
        return {
            "rv_7": str(self.rv_7) if self.rv_7 is not None else None,
            "rv_60": str(self.rv_60) if self.rv_60 is not None else None,
        }


@dataclass(frozen=True)
class VolatilityCompressionRatioResult:
    feature_id: str
    numerator_feature_id: str
    denominator_feature_id: str
    compression_ratio: Decimal | None
    inputs: VolatilityCompressionRatioInput
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "numerator_feature_id": self.numerator_feature_id,
            "denominator_feature_id": self.denominator_feature_id,
            "compression_ratio": (
                str(self.compression_ratio)
                if self.compression_ratio is not None
                else None
            ),
            "inputs": self.inputs.as_record(),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class VolatilityPercentileResult:
    feature_id: str
    observation_time: datetime
    source_feature_id: str
    percentile_window_days: int
    min_percentile_observations: int
    realized_volatility: Decimal | None
    volatility_percentile: Decimal | None
    history_observation_count: int
    source_result_count: int
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "observation_time": require_utc_datetime(
                self.observation_time,
                "observation_time",
            ).isoformat(),
            "source_feature_id": self.source_feature_id,
            "percentile_window_days": self.percentile_window_days,
            "min_percentile_observations": self.min_percentile_observations,
            "realized_volatility": (
                str(self.realized_volatility)
                if self.realized_volatility is not None
                else None
            ),
            "volatility_percentile": (
                str(self.volatility_percentile)
                if self.volatility_percentile is not None
                else None
            ),
            "history_observation_count": self.history_observation_count,
            "source_result_count": self.source_result_count,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class OrderlinessScoreInput:
    range_percentile: Decimal | None
    downside_return: Decimal | None
    liquidation_percentile: Decimal | None
    volatility_percentile: Decimal | None

    def as_record(self) -> dict[str, str | None]:
        return {
            "range_percentile": (
                str(self.range_percentile)
                if self.range_percentile is not None
                else None
            ),
            "downside_return": (
                str(self.downside_return)
                if self.downside_return is not None
                else None
            ),
            "liquidation_percentile": (
                str(self.liquidation_percentile)
                if self.liquidation_percentile is not None
                else None
            ),
            "volatility_percentile": (
                str(self.volatility_percentile)
                if self.volatility_percentile is not None
                else None
            ),
        }


@dataclass(frozen=True)
class OrderlinessScoreResult:
    feature_id: str
    score: Decimal | None
    interpretation: str | None
    inputs: OrderlinessScoreInput
    weights: dict[str, Decimal]
    thresholds: dict[str, Decimal]
    penalties: dict[str, Decimal | None]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "score": str(self.score) if self.score is not None else None,
            "interpretation": self.interpretation,
            "inputs": self.inputs.as_record(),
            "weights": {key: str(value) for key, value in self.weights.items()},
            "thresholds": {key: str(value) for key, value in self.thresholds.items()},
            "penalties": {
                key: str(value) if value is not None else None
                for key, value in self.penalties.items()
            },
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class VolatilityScoreInput:
    """Explicit Volatility Score inputs.

    ``volatility_percentile`` is the 2-year percentile of RV20. It does not
    enter the weighted composite; it classifies the volatility regime so a
    setup-specific interpretation stays possible.
    """

    compression_ratio: Decimal | None
    orderliness_score: Decimal | None
    volatility_percentile: Decimal | None = None

    def as_record(self) -> dict[str, str | None]:
        return {
            "compression_ratio": (
                str(self.compression_ratio)
                if self.compression_ratio is not None
                else None
            ),
            "orderliness_score": (
                str(self.orderliness_score)
                if self.orderliness_score is not None
                else None
            ),
            "volatility_percentile": (
                str(self.volatility_percentile)
                if self.volatility_percentile is not None
                else None
            ),
        }


@dataclass(frozen=True)
class VolatilityScoreResult:
    feature_id: str
    score: Decimal | None
    interpretation: str | None
    volatility_regime: str | None
    compression_score: Decimal | None
    inputs: VolatilityScoreInput
    weights: dict[str, Decimal]
    thresholds: dict[str, Decimal]
    contributions: dict[str, Decimal | None]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()
    compression_score_version: str = COMPRESSION_SCORE_VERSION
    volatility_regime_version: str = VOLATILITY_REGIME_VERSION
    diagnostics: dict[str, Decimal | None] = field(default_factory=dict)

    def as_record(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "score": str(self.score) if self.score is not None else None,
            "interpretation": self.interpretation,
            "compression_score_version": self.compression_score_version,
            "volatility_regime_version": self.volatility_regime_version,
            "volatility_regime": self.volatility_regime,
            "compression_score": (
                str(self.compression_score)
                if self.compression_score is not None
                else None
            ),
            "inputs": self.inputs.as_record(),
            "weights": {key: str(value) for key, value in self.weights.items()},
            "thresholds": {key: str(value) for key, value in self.thresholds.items()},
            "contributions": {
                key: str(value) if value is not None else None
                for key, value in self.contributions.items()
            },
            "diagnostics": {
                key: str(value) if value is not None else None
                for key, value in self.diagnostics.items()
            },
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class StressFlagInput:
    volatility_percentile: Decimal | None
    liquidation_percentile: Decimal | None
    downside_return: Decimal | None
    funding_zscore: Decimal | None
    basis_zscore: Decimal | None
    systemic_shock: bool | None

    def as_record(self) -> dict[str, str | bool | None]:
        return {
            "volatility_percentile": (
                str(self.volatility_percentile)
                if self.volatility_percentile is not None
                else None
            ),
            "liquidation_percentile": (
                str(self.liquidation_percentile)
                if self.liquidation_percentile is not None
                else None
            ),
            "downside_return": (
                str(self.downside_return)
                if self.downside_return is not None
                else None
            ),
            "funding_zscore": (
                str(self.funding_zscore) if self.funding_zscore is not None else None
            ),
            "basis_zscore": (
                str(self.basis_zscore) if self.basis_zscore is not None else None
            ),
            "systemic_shock": self.systemic_shock,
        }


@dataclass(frozen=True)
class CapitulationFlagInput:
    range_percentile: Decimal | None
    downside_return: Decimal | None
    liquidation_percentile: Decimal | None
    volatility_percentile: Decimal | None
    funding_zscore: Decimal | None
    systemic_shock: bool | None

    def as_record(self) -> dict[str, str | bool | None]:
        return {
            "range_percentile": (
                str(self.range_percentile)
                if self.range_percentile is not None
                else None
            ),
            "downside_return": (
                str(self.downside_return)
                if self.downside_return is not None
                else None
            ),
            "liquidation_percentile": (
                str(self.liquidation_percentile)
                if self.liquidation_percentile is not None
                else None
            ),
            "volatility_percentile": (
                str(self.volatility_percentile)
                if self.volatility_percentile is not None
                else None
            ),
            "funding_zscore": (
                str(self.funding_zscore) if self.funding_zscore is not None else None
            ),
            "systemic_shock": self.systemic_shock,
        }


@dataclass(frozen=True)
class EuphoriaFlagInput:
    range_percentile: Decimal | None
    upside_return: Decimal | None
    funding_zscore: Decimal | None
    basis_zscore: Decimal | None
    oi_intensity_percentile: Decimal | None
    volatility_percentile: Decimal | None
    systemic_euphoria: bool | None

    def as_record(self) -> dict[str, str | bool | None]:
        return {
            "range_percentile": (
                str(self.range_percentile)
                if self.range_percentile is not None
                else None
            ),
            "upside_return": (
                str(self.upside_return) if self.upside_return is not None else None
            ),
            "funding_zscore": (
                str(self.funding_zscore) if self.funding_zscore is not None else None
            ),
            "basis_zscore": (
                str(self.basis_zscore) if self.basis_zscore is not None else None
            ),
            "oi_intensity_percentile": (
                str(self.oi_intensity_percentile)
                if self.oi_intensity_percentile is not None
                else None
            ),
            "volatility_percentile": (
                str(self.volatility_percentile)
                if self.volatility_percentile is not None
                else None
            ),
            "systemic_euphoria": self.systemic_euphoria,
        }


@dataclass(frozen=True)
class StressFlagResult:
    feature_id: str
    flagged: bool
    effects: tuple[str, ...]
    max_exposure_multiplier: Decimal
    block_new_trades: bool
    inputs: StressFlagInput
    thresholds: dict[str, Decimal]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "flagged": self.flagged,
            "effects": list(self.effects),
            "max_exposure_multiplier": str(self.max_exposure_multiplier),
            "block_new_trades": self.block_new_trades,
            "inputs": self.inputs.as_record(),
            "thresholds": {key: str(value) for key, value in self.thresholds.items()},
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class CapitulationFlagResult:
    feature_id: str
    flagged: bool
    effects: tuple[str, ...]
    inputs: CapitulationFlagInput
    thresholds: dict[str, Decimal]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "flagged": self.flagged,
            "effects": list(self.effects),
            "inputs": self.inputs.as_record(),
            "thresholds": {key: str(value) for key, value in self.thresholds.items()},
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class EuphoriaFlagResult:
    feature_id: str
    flagged: bool
    effects: tuple[str, ...]
    inputs: EuphoriaFlagInput
    thresholds: dict[str, Decimal]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "flagged": self.flagged,
            "effects": list(self.effects),
            "inputs": self.inputs.as_record(),
            "thresholds": {key: str(value) for key, value in self.thresholds.items()},
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def realized_volatility_from_daily_bars(
    bars: Sequence[OhlcvBar],
    *,
    as_of: datetime,
    window_days: int,
    annualization_periods: int = DEFAULT_REALIZED_VOLATILITY_ANNUALIZATION_PERIODS,
) -> RealizedVolatilityResult:
    """Calculate annualized realized volatility from daily close-to-close returns."""

    signal_time = require_utc_datetime(as_of, "as_of")
    _validate_realized_volatility_parameters(
        window_days=window_days,
        annualization_periods=annualization_periods,
    )
    _validate_daily_bars(bars)
    available_bars = _available_daily_bars(bars, signal_time=signal_time)
    observation_time = available_bars[-1].timestamp if available_bars else signal_time
    reason_codes = []
    if not available_bars:
        reason_codes.append("REALIZED_VOLATILITY_INPUT_MISSING")

    selected_bars = available_bars[-(window_days + 1) :]
    if available_bars and len(selected_bars) < window_days + 1:
        reason_codes.append("REALIZED_VOLATILITY_INSUFFICIENT_HISTORY")

    realized_volatility = None
    returns: tuple[Decimal, ...] = ()
    if len(selected_bars) == window_days + 1:
        closes = tuple(bar.close for bar in selected_bars)
        if any(close <= 0 for close in closes):
            reason_codes.append("REALIZED_VOLATILITY_NON_POSITIVE_CLOSE")
        else:
            returns = tuple(
                (current / previous) - Decimal("1")
                for previous, current in zip(closes, closes[1:])
            )
            quant_values = quant_realized_volatility(
                tuple(float(close) for close in closes),
                window=window_days,
                annualization_periods=annualization_periods,
            )
            quant_value = quant_values[-1]
            realized_volatility = (
                Decimal("0")
                if quant_value == 0
                else Decimal(str(float(quant_value)))
            )

    reason_codes = _dedupe_reason_codes(reason_codes)
    return RealizedVolatilityResult(
        feature_id=_realized_volatility_feature_id(window_days),
        observation_time=observation_time,
        window_days=window_days,
        annualization_periods=annualization_periods,
        realized_volatility=realized_volatility,
        return_count=len(returns),
        source_bar_count=len(available_bars),
        complete=not reason_codes,
        reason_codes=reason_codes,
    )


def calculate_stress_flag(
    inputs: StressFlagInput,
    *,
    volatility_percentile_min: Any = DEFAULT_STRESS_VOLATILITY_PERCENTILE_MIN,
    liquidation_percentile_min: Any = DEFAULT_STRESS_LIQUIDATION_PERCENTILE_MIN,
    downside_return_min: Any = DEFAULT_STRESS_DOWNSIDE_RETURN_MIN,
    funding_abs_zscore_min: Any = DEFAULT_STRESS_FUNDING_ABS_ZSCORE_MIN,
    basis_abs_zscore_min: Any = DEFAULT_STRESS_BASIS_ABS_ZSCORE_MIN,
    max_exposure_multiplier: Any = DEFAULT_STRESS_MAX_EXPOSURE_MULTIPLIER,
    block_new_trades: bool = DEFAULT_STRESS_BLOCK_NEW_TRADES,
    config_metadata: dict[str, str] | None = None,
) -> StressFlagResult:
    """Flag hard stress conditions that override ordinary scoring."""

    thresholds = _stress_flag_thresholds(
        volatility_percentile_min=volatility_percentile_min,
        liquidation_percentile_min=liquidation_percentile_min,
        downside_return_min=downside_return_min,
        funding_abs_zscore_min=funding_abs_zscore_min,
        basis_abs_zscore_min=basis_abs_zscore_min,
        max_exposure_multiplier=max_exposure_multiplier,
    )
    if not isinstance(block_new_trades, bool):
        raise ValueError("block_new_trades must be bool")

    input_values = _stress_flag_input_values(inputs)
    reason_codes = []
    if any(value is None for value in input_values.values()):
        reason_codes.append("STRESS_INPUT_MISSING")
    if (
        input_values["volatility_percentile"] is not None
        and decision_greater_equal(
            input_values["volatility_percentile"],
            thresholds["volatility_percentile_min"],
        )
    ):
        reason_codes.append("STRESS_EXTREME_VOLATILITY")
    if (
        input_values["liquidation_percentile"] is not None
        and decision_greater_equal(
            input_values["liquidation_percentile"],
            thresholds["liquidation_percentile_min"],
        )
    ):
        reason_codes.append("STRESS_LIQUIDATION_CASCADE")
    if (
        input_values["downside_return"] is not None
        and decision_less_equal(
            input_values["downside_return"],
            thresholds["downside_return_min"],
        )
    ):
        reason_codes.append("STRESS_DISORDERLY_DOWNSIDE")
    if (
        input_values["funding_zscore"] is not None
        and decision_greater_equal(
            abs(input_values["funding_zscore"]),
            thresholds["funding_abs_zscore_min"],
        )
    ):
        reason_codes.append("STRESS_ABNORMAL_FUNDING")
    if (
        input_values["basis_zscore"] is not None
        and decision_greater_equal(
            abs(input_values["basis_zscore"]),
            thresholds["basis_abs_zscore_min"],
        )
    ):
        reason_codes.append("STRESS_ABNORMAL_BASIS")
    if input_values["systemic_shock"] is True:
        reason_codes.append("STRESS_SYSTEMIC_MARKET_SHOCK")

    reason_codes = _dedupe_reason_codes(reason_codes)
    flagged = any(
        reason_code != "STRESS_INPUT_MISSING" for reason_code in reason_codes
    )
    exposure_multiplier = (
        thresholds["max_exposure_multiplier"] if flagged else Decimal("1")
    )
    return StressFlagResult(
        feature_id=STRESS_FLAG_FEATURE_ID,
        flagged=flagged,
        effects=STRESS_FLAG_EFFECTS if flagged else (),
        max_exposure_multiplier=exposure_multiplier,
        block_new_trades=block_new_trades if flagged else False,
        inputs=inputs,
        thresholds={
            key: value
            for key, value in thresholds.items()
            if key != "max_exposure_multiplier"
        },
        config_metadata=dict(config_metadata or {}),
        complete="STRESS_INPUT_MISSING" not in reason_codes,
        reason_codes=reason_codes,
    )


def calculate_capitulation_flag(
    inputs: CapitulationFlagInput,
    *,
    range_percentile_min: Any = DEFAULT_CAPITULATION_RANGE_PERCENTILE_MIN,
    downside_return_min: Any = DEFAULT_CAPITULATION_DOWNSIDE_RETURN_MIN,
    liquidation_percentile_min: Any = DEFAULT_CAPITULATION_LIQUIDATION_PERCENTILE_MIN,
    volatility_percentile_min: Any = DEFAULT_CAPITULATION_VOLATILITY_PERCENTILE_MIN,
    funding_zscore_max: Any = DEFAULT_CAPITULATION_FUNDING_ZSCORE_MAX,
    config_metadata: dict[str, str] | None = None,
) -> CapitulationFlagResult:
    """Flag a downside washout only after severe selling has confirmation."""

    thresholds = _capitulation_flag_thresholds(
        range_percentile_min=range_percentile_min,
        downside_return_min=downside_return_min,
        liquidation_percentile_min=liquidation_percentile_min,
        volatility_percentile_min=volatility_percentile_min,
        funding_zscore_max=funding_zscore_max,
    )
    input_values = _capitulation_flag_input_values(inputs)

    reason_codes = []
    if any(value is None for value in input_values.values()):
        reason_codes.append("CAPITULATION_INPUT_MISSING")
    if (
        input_values["downside_return"] is not None
        and decision_less_equal(
            input_values["downside_return"],
            thresholds["downside_return_min"],
        )
    ):
        reason_codes.append("CAPITULATION_DISORDERLY_DOWNSIDE")
    if (
        input_values["range_percentile"] is not None
        and decision_greater_equal(
            input_values["range_percentile"],
            thresholds["range_percentile_min"],
        )
    ):
        reason_codes.append("CAPITULATION_EXTREME_RANGE")
    if (
        input_values["liquidation_percentile"] is not None
        and decision_greater_equal(
            input_values["liquidation_percentile"],
            thresholds["liquidation_percentile_min"],
        )
    ):
        reason_codes.append("CAPITULATION_LIQUIDATION_CASCADE")
    if (
        input_values["volatility_percentile"] is not None
        and decision_greater_equal(
            input_values["volatility_percentile"],
            thresholds["volatility_percentile_min"],
        )
    ):
        reason_codes.append("CAPITULATION_VOLATILITY_SPIKE")
    if (
        input_values["funding_zscore"] is not None
        and decision_less_equal(
            input_values["funding_zscore"],
            thresholds["funding_zscore_max"],
        )
    ):
        reason_codes.append("CAPITULATION_NEGATIVE_FUNDING_FLUSH")
    if input_values["systemic_shock"] is True:
        reason_codes.append("CAPITULATION_SYSTEMIC_MARKET_SHOCK")

    reason_codes = _dedupe_reason_codes(reason_codes)
    systemic_shock = "CAPITULATION_SYSTEMIC_MARKET_SHOCK" in reason_codes
    downside_triggered = "CAPITULATION_DISORDERLY_DOWNSIDE" in reason_codes
    confirmation_triggered = any(
        reason_code in reason_codes
        for reason_code in (
            "CAPITULATION_EXTREME_RANGE",
            "CAPITULATION_LIQUIDATION_CASCADE",
            "CAPITULATION_VOLATILITY_SPIKE",
            "CAPITULATION_NEGATIVE_FUNDING_FLUSH",
        )
    )
    flagged = systemic_shock or (downside_triggered and confirmation_triggered)
    if downside_triggered and not confirmation_triggered and not systemic_shock:
        reason_codes = (*reason_codes, "CAPITULATION_CONFIRMATION_MISSING")

    return CapitulationFlagResult(
        feature_id=CAPITULATION_FLAG_FEATURE_ID,
        flagged=flagged,
        effects=CAPITULATION_FLAG_EFFECTS if flagged else (),
        inputs=inputs,
        thresholds=thresholds,
        config_metadata=dict(config_metadata or {}),
        complete="CAPITULATION_INPUT_MISSING" not in reason_codes,
        reason_codes=reason_codes,
    )


def calculate_euphoria_flag(
    inputs: EuphoriaFlagInput,
    *,
    range_percentile_min: Any = DEFAULT_EUPHORIA_RANGE_PERCENTILE_MIN,
    upside_return_min: Any = DEFAULT_EUPHORIA_UPSIDE_RETURN_MIN,
    funding_zscore_min: Any = DEFAULT_EUPHORIA_FUNDING_ZSCORE_MIN,
    basis_zscore_min: Any = DEFAULT_EUPHORIA_BASIS_ZSCORE_MIN,
    oi_intensity_percentile_min: Any = DEFAULT_EUPHORIA_OI_INTENSITY_PERCENTILE_MIN,
    volatility_percentile_min: Any = DEFAULT_EUPHORIA_VOLATILITY_PERCENTILE_MIN,
    config_metadata: dict[str, str] | None = None,
) -> EuphoriaFlagResult:
    """Flag upside euphoria only after extension has overheating confirmation."""

    thresholds = _euphoria_flag_thresholds(
        range_percentile_min=range_percentile_min,
        upside_return_min=upside_return_min,
        funding_zscore_min=funding_zscore_min,
        basis_zscore_min=basis_zscore_min,
        oi_intensity_percentile_min=oi_intensity_percentile_min,
        volatility_percentile_min=volatility_percentile_min,
    )
    input_values = _euphoria_flag_input_values(inputs)

    reason_codes = []
    if any(value is None for value in input_values.values()):
        reason_codes.append("EUPHORIA_INPUT_MISSING")
    if (
        input_values["upside_return"] is not None
        and decision_greater_equal(
            input_values["upside_return"],
            thresholds["upside_return_min"],
        )
    ):
        reason_codes.append("EUPHORIA_UPSIDE_EXTENSION")
    if (
        input_values["range_percentile"] is not None
        and decision_greater_equal(
            input_values["range_percentile"],
            thresholds["range_percentile_min"],
        )
    ):
        reason_codes.append("EUPHORIA_EXTREME_RANGE")
    if (
        input_values["funding_zscore"] is not None
        and decision_greater_equal(
            input_values["funding_zscore"],
            thresholds["funding_zscore_min"],
        )
    ):
        reason_codes.append("EUPHORIA_FUNDING_OVERHEATED")
    if (
        input_values["basis_zscore"] is not None
        and decision_greater_equal(
            input_values["basis_zscore"],
            thresholds["basis_zscore_min"],
        )
    ):
        reason_codes.append("EUPHORIA_BASIS_OVERHEATED")
    if (
        input_values["oi_intensity_percentile"] is not None
        and decision_greater_equal(
            input_values["oi_intensity_percentile"],
            thresholds["oi_intensity_percentile_min"],
        )
    ):
        reason_codes.append("EUPHORIA_OI_INTENSITY_EXTREME")
    if (
        input_values["volatility_percentile"] is not None
        and decision_greater_equal(
            input_values["volatility_percentile"],
            thresholds["volatility_percentile_min"],
        )
    ):
        reason_codes.append("EUPHORIA_VOLATILITY_SPIKE")
    if input_values["systemic_euphoria"] is True:
        reason_codes.append("EUPHORIA_SYSTEMIC_MARKET_EUPHORIA")

    reason_codes = _dedupe_reason_codes(reason_codes)
    systemic_euphoria = "EUPHORIA_SYSTEMIC_MARKET_EUPHORIA" in reason_codes
    upside_triggered = "EUPHORIA_UPSIDE_EXTENSION" in reason_codes
    confirmation_triggered = any(
        reason_code in reason_codes
        for reason_code in (
            "EUPHORIA_EXTREME_RANGE",
            "EUPHORIA_FUNDING_OVERHEATED",
            "EUPHORIA_BASIS_OVERHEATED",
            "EUPHORIA_OI_INTENSITY_EXTREME",
            "EUPHORIA_VOLATILITY_SPIKE",
        )
    )
    flagged = systemic_euphoria or (upside_triggered and confirmation_triggered)
    if upside_triggered and not confirmation_triggered and not systemic_euphoria:
        reason_codes = (*reason_codes, "EUPHORIA_CONFIRMATION_MISSING")

    return EuphoriaFlagResult(
        feature_id=EUPHORIA_FLAG_FEATURE_ID,
        flagged=flagged,
        effects=EUPHORIA_FLAG_EFFECTS if flagged else (),
        inputs=inputs,
        thresholds=thresholds,
        config_metadata=dict(config_metadata or {}),
        complete="EUPHORIA_INPUT_MISSING" not in reason_codes,
        reason_codes=reason_codes,
    )


def calculate_orderliness_score(
    inputs: OrderlinessScoreInput,
    *,
    weights: dict[str, Any] | None = None,
    range_percentile_max: Any = DEFAULT_ORDERLINESS_RANGE_PERCENTILE_MAX,
    downside_return_min: Any = DEFAULT_ORDERLINESS_DOWNSIDE_RETURN_MIN,
    liquidation_percentile_max: Any = DEFAULT_ORDERLINESS_LIQUIDATION_PERCENTILE_MAX,
    volatility_percentile_max: Any = DEFAULT_ORDERLINESS_VOLATILITY_PERCENTILE_MAX,
    config_metadata: dict[str, str] | None = None,
) -> OrderlinessScoreResult:
    """Score whether volatility is orderly enough to trade."""

    selected_weights = _orderliness_score_weights(weights)
    thresholds = _orderliness_thresholds(
        range_percentile_max=range_percentile_max,
        downside_return_min=downside_return_min,
        liquidation_percentile_max=liquidation_percentile_max,
        volatility_percentile_max=volatility_percentile_max,
    )
    input_values = _orderliness_score_input_values(inputs)

    reason_codes = []
    if any(value is None for value in input_values.values()):
        reason_codes.append("ORDERLINESS_INPUT_MISSING")
    if (
        input_values["range_percentile"] is not None
        and decision_greater_equal(
            input_values["range_percentile"],
            thresholds["range_percentile_max"],
        )
    ):
        reason_codes.append("ORDERLINESS_EXTREME_RANGE")
    if (
        input_values["downside_return"] is not None
        and decision_less_equal(
            input_values["downside_return"],
            thresholds["downside_return_min"],
        )
    ):
        reason_codes.append("ORDERLINESS_DISORDERLY_DOWNSIDE")
    if (
        input_values["liquidation_percentile"] is not None
        and decision_greater_equal(
            input_values["liquidation_percentile"],
            thresholds["liquidation_percentile_max"],
        )
    ):
        reason_codes.append("ORDERLINESS_LIQUIDATION_CASCADE")
    if (
        input_values["volatility_percentile"] is not None
        and decision_greater_equal(
            input_values["volatility_percentile"],
            thresholds["volatility_percentile_max"],
        )
    ):
        reason_codes.append("ORDERLINESS_VOLATILITY_SPIKE")

    reason_codes = _dedupe_reason_codes(reason_codes)
    penalty_inputs = {
        component_id: (
            Decimal("100")
            if _orderliness_component_triggered(component_id, reason_codes)
            else Decimal("0")
        )
        if input_values[component_id] is not None
        else None
        for component_id in ORDERLINESS_SCORE_COMPONENT_IDS
    }
    weighted = decimal_weighted_score(
        penalty_inputs,
        selected_weights,
        component_ids=ORDERLINESS_SCORE_COMPONENT_IDS,
    )
    penalties = {
        component_id: (
            Decimal("0")
            if penalty_inputs[component_id] == Decimal("0")
            else weighted.contributions[component_id]
        )
        for component_id in ORDERLINESS_SCORE_COMPONENT_IDS
    }
    missing_inputs = "ORDERLINESS_INPUT_MISSING" in reason_codes
    score = (
        max(
            Decimal("0"),
            Decimal("100") - weighted.score,
        )
        if not missing_inputs and weighted.score is not None
        else None
    )
    return OrderlinessScoreResult(
        feature_id=ORDERLINESS_SCORE_FEATURE_ID,
        score=score,
        interpretation=_orderliness_score_interpretation(score),
        inputs=inputs,
        weights=selected_weights,
        thresholds=thresholds,
        penalties=penalties,
        config_metadata=dict(config_metadata or {}),
        complete=score is not None,
        reason_codes=reason_codes,
    )


def volatility_percentile(
    results: Sequence[RealizedVolatilityResult],
    *,
    as_of: datetime,
    source_feature_id: str = RV_20_FEATURE_ID,
    percentile_window_days: int = DEFAULT_VOLATILITY_PERCENTILE_WINDOW_DAYS,
    min_percentile_observations: int = DEFAULT_VOLATILITY_PERCENTILE_MIN_OBSERVATIONS,
) -> VolatilityPercentileResult:
    """Calculate current realized volatility percentile against prior history."""

    signal_time = require_utc_datetime(as_of, "as_of")
    _validate_volatility_percentile_parameters(
        source_feature_id=source_feature_id,
        percentile_window_days=percentile_window_days,
        min_percentile_observations=min_percentile_observations,
    )
    source_results = _available_realized_volatility_results(
        results,
        source_feature_id=source_feature_id,
        signal_time=signal_time,
    )
    current_result = source_results[-1] if source_results else None
    observation_time = (
        current_result.observation_time if current_result is not None else signal_time
    )
    realized_volatility = (
        _non_negative_decimal(current_result.realized_volatility, "realized_volatility")
        if current_result is not None and current_result.realized_volatility is not None
        else None
    )
    history = _realized_volatility_history(
        source_results,
        observation_time=observation_time,
        percentile_window_days=percentile_window_days,
    )

    reason_codes = []
    if realized_volatility is None:
        reason_codes.append("VOL_PERCENTILE_INPUT_MISSING")

    volatility_percentile = None
    if realized_volatility is not None:
        if len(history) < min_percentile_observations:
            reason_codes.append("VOL_PERCENTILE_INSUFFICIENT_HISTORY")
        else:
            volatility_percentile = _percentile_rank(realized_volatility, history)

    reason_codes = _dedupe_reason_codes(reason_codes)
    return VolatilityPercentileResult(
        feature_id=VOLATILITY_PERCENTILE_FEATURE_ID,
        observation_time=observation_time,
        source_feature_id=source_feature_id,
        percentile_window_days=percentile_window_days,
        min_percentile_observations=min_percentile_observations,
        realized_volatility=realized_volatility,
        volatility_percentile=volatility_percentile,
        history_observation_count=len(history),
        source_result_count=len(source_results),
        complete=not reason_codes,
        reason_codes=reason_codes,
    )


def compression_score_from_ratio(
    compression_ratio: Any | None,
    *,
    full_score_ratio: Any = DEFAULT_COMPRESSION_FULL_SCORE_RATIO,
    zero_score_ratio: Any = DEFAULT_COMPRESSION_ZERO_SCORE_RATIO,
) -> Decimal | None:
    """Convert RV7/RV60 into a bounded 0-100 compression score.

    Compression is favourable for a swing entry, so the score decreases as the
    ratio rises. It is a clamped linear ramp: full score at or below
    ``full_score_ratio``, zero at or above ``zero_score_ratio``. The defaults
    are symmetric about the rulebook's ``RV7 / RV60 < 1`` boundary, so an
    exactly neutral ratio of 1 scores 50.
    """

    thresholds = _compression_score_thresholds(
        full_score_ratio=full_score_ratio,
        zero_score_ratio=zero_score_ratio,
    )
    if compression_ratio is None:
        return None
    ratio = _non_negative_decimal(compression_ratio, "compression_ratio")
    return decimal_bounded_linear(
        ratio,
        input_minimum=thresholds["compression_full_score_ratio"],
        input_maximum=thresholds["compression_zero_score_ratio"],
        output_at_minimum=Decimal("100"),
        output_at_maximum=Decimal("0"),
    )


def calculate_volatility_score(
    inputs: VolatilityScoreInput,
    *,
    weights: dict[str, Any] | None = None,
    full_score_ratio: Any = DEFAULT_COMPRESSION_FULL_SCORE_RATIO,
    zero_score_ratio: Any = DEFAULT_COMPRESSION_ZERO_SCORE_RATIO,
    compressed_percentile_max: Any = DEFAULT_VOLATILITY_REGIME_COMPRESSED_MAX,
    normal_percentile_max: Any = DEFAULT_VOLATILITY_REGIME_NORMAL_MAX,
    elevated_percentile_max: Any = DEFAULT_VOLATILITY_REGIME_ELEVATED_MAX,
    disorderly_score_max: Any = DEFAULT_ORDERLINESS_SCORE_DISORDERLY_MAX,
    config_metadata: dict[str, str] | None = None,
) -> VolatilityScoreResult:
    """Combine compression and orderliness into the Phase 1 Volatility Score.

    ``VolatilityScore = 0.5 * CompressionScore + 0.5 * OrderlinessScore``.
    """

    selected_weights = _volatility_score_weights(weights)
    thresholds = _volatility_score_thresholds(
        full_score_ratio=full_score_ratio,
        zero_score_ratio=zero_score_ratio,
        compressed_percentile_max=compressed_percentile_max,
        normal_percentile_max=normal_percentile_max,
        elevated_percentile_max=elevated_percentile_max,
        disorderly_score_max=disorderly_score_max,
    )
    inputs.as_record()
    compression_score = compression_score_from_ratio(
        inputs.compression_ratio,
        full_score_ratio=thresholds["compression_full_score_ratio"],
        zero_score_ratio=thresholds["compression_zero_score_ratio"],
    )
    orderliness_score = (
        _score_decimal(inputs.orderliness_score, "orderliness_score")
        if inputs.orderliness_score is not None
        else None
    )
    volatility_percentile_value = (
        _score_decimal(inputs.volatility_percentile, "volatility_percentile")
        if inputs.volatility_percentile is not None
        else None
    )
    volatility_regime = _volatility_regime(volatility_percentile_value, thresholds)

    components = {
        "compression": compression_score,
        "orderliness": orderliness_score,
    }
    weighted = decimal_weighted_score(
        components,
        selected_weights,
        component_ids=VOLATILITY_SCORE_COMPONENT_IDS,
    )

    reason_codes = []
    if any(value is None for value in components.values()):
        reason_codes.append("VOLATILITY_SCORE_INPUT_MISSING")
    if compression_score is not None and inputs.compression_ratio is not None:
        ratio = _non_negative_decimal(inputs.compression_ratio, "compression_ratio")
        if decision_less_equal(ratio, thresholds["compression_full_score_ratio"]):
            reason_codes.append("VOLATILITY_COMPRESSED")
        elif decision_greater_equal(ratio, thresholds["compression_zero_score_ratio"]):
            reason_codes.append("VOLATILITY_EXPANDING")
    if orderliness_score is not None and decision_less_equal(
        orderliness_score,
        thresholds["orderliness_disorderly_score_max"],
    ):
        reason_codes.append("VOLATILITY_DISORDERLY")
    if volatility_regime is None:
        reason_codes.append("VOLATILITY_REGIME_UNKNOWN")
    if weighted.score is not None:
        reason_codes.append("VOLATILITY_SCORE_COMPLETE")

    return VolatilityScoreResult(
        feature_id=VOLATILITY_SCORE_FEATURE_ID,
        diagnostics={
            "compression_ratio": (
                _non_negative_decimal(inputs.compression_ratio, "compression_ratio")
                if inputs.compression_ratio is not None
                else None
            ),
            "volatility_percentile": volatility_percentile_value,
        },
        score=weighted.score,
        interpretation=_volatility_score_interpretation(weighted.score),
        volatility_regime=volatility_regime,
        compression_score=compression_score,
        inputs=inputs,
        weights=selected_weights,
        thresholds=thresholds,
        contributions=weighted.contributions,
        config_metadata=dict(config_metadata or {}),
        complete=weighted.score is not None,
        reason_codes=_dedupe_reason_codes(reason_codes),
    )


def calculate_volatility_score_from_results(
    compression_result: VolatilityCompressionRatioResult,
    orderliness_result: OrderlinessScoreResult,
    *,
    percentile_result: VolatilityPercentileResult | None = None,
    weights: dict[str, Any] | None = None,
    config_metadata: dict[str, str] | None = None,
    **thresholds: Any,
) -> VolatilityScoreResult:
    """Calculate the Volatility Score from persisted upstream feature results."""

    return calculate_volatility_score(
        VolatilityScoreInput(
            compression_ratio=compression_result.compression_ratio,
            orderliness_score=orderliness_result.score,
            volatility_percentile=(
                percentile_result.volatility_percentile
                if percentile_result is not None
                else None
            ),
        ),
        weights=weights,
        config_metadata=config_metadata,
        **thresholds,
    )


def volatility_compression_ratio(
    inputs: VolatilityCompressionRatioInput,
) -> VolatilityCompressionRatioResult:
    """Calculate volatility compression as RV7 / RV60."""

    input_values = _compression_input_values(inputs)
    reason_codes = []
    if any(value is None for value in input_values.values()):
        reason_codes.append("VOL_COMPRESSION_INPUT_MISSING")
    if input_values["rv_60"] == 0:
        reason_codes.append("VOL_COMPRESSION_ZERO_DENOMINATOR")

    compression_ratio = (
        input_values["rv_7"] / input_values["rv_60"]
        if not reason_codes
        else None
    )
    reason_codes = _dedupe_reason_codes(reason_codes)
    return VolatilityCompressionRatioResult(
        feature_id=VOLATILITY_COMPRESSION_RATIO_FEATURE_ID,
        numerator_feature_id=RV_7_FEATURE_ID,
        denominator_feature_id=RV_60_FEATURE_ID,
        compression_ratio=compression_ratio,
        inputs=inputs,
        complete=compression_ratio is not None,
        reason_codes=reason_codes,
    )


def volatility_compression_ratio_from_results(
    results: Sequence[RealizedVolatilityResult],
) -> VolatilityCompressionRatioResult:
    """Calculate compression from persisted RV feature results."""

    results_by_feature_id = {result.feature_id: result for result in results}
    return volatility_compression_ratio(
        VolatilityCompressionRatioInput(
            rv_7=(
                results_by_feature_id[RV_7_FEATURE_ID].realized_volatility
                if RV_7_FEATURE_ID in results_by_feature_id
                else None
            ),
            rv_60=(
                results_by_feature_id[RV_60_FEATURE_ID].realized_volatility
                if RV_60_FEATURE_ID in results_by_feature_id
                else None
            ),
        )
    )


def rv_7_20_60_from_daily_bars(
    bars: Sequence[OhlcvBar],
    *,
    as_of: datetime,
    annualization_periods: int = DEFAULT_REALIZED_VOLATILITY_ANNUALIZATION_PERIODS,
) -> tuple[RealizedVolatilityResult, RealizedVolatilityResult, RealizedVolatilityResult]:
    """Calculate RV7, RV20, and RV60 from point-in-time daily bars."""

    return tuple(
        realized_volatility_from_daily_bars(
            bars,
            as_of=as_of,
            window_days=window_days,
            annualization_periods=annualization_periods,
        )
        for window_days in REALIZED_VOLATILITY_WINDOWS
    )


def _validate_realized_volatility_parameters(
    *,
    window_days: int,
    annualization_periods: int,
) -> None:
    if window_days < 1:
        raise ValueError("window_days must be >= 1")
    if annualization_periods < 1:
        raise ValueError("annualization_periods must be >= 1")


def _validate_daily_bars(bars: Sequence[OhlcvBar]) -> None:
    for bar in bars:
        if bar.timeframe != "1d":
            raise ValueError("realized volatility requires canonical 1d bars")


def _stress_flag_thresholds(
    *,
    volatility_percentile_min: Any,
    liquidation_percentile_min: Any,
    downside_return_min: Any,
    funding_abs_zscore_min: Any,
    basis_abs_zscore_min: Any,
    max_exposure_multiplier: Any,
) -> dict[str, Decimal]:
    downside_threshold = Decimal(str(downside_return_min))
    if downside_threshold >= 0:
        raise ValueError("downside_return_min must be < 0")
    exposure_multiplier = Decimal(str(max_exposure_multiplier))
    if exposure_multiplier < 0 or exposure_multiplier > 1:
        raise ValueError("max_exposure_multiplier must be between 0 and 1")
    return {
        "volatility_percentile_min": _score_decimal(
            volatility_percentile_min,
            "volatility_percentile_min",
        ),
        "liquidation_percentile_min": _score_decimal(
            liquidation_percentile_min,
            "liquidation_percentile_min",
        ),
        "downside_return_min": downside_threshold,
        "funding_abs_zscore_min": _non_negative_decimal(
            funding_abs_zscore_min,
            "funding_abs_zscore_min",
        ),
        "basis_abs_zscore_min": _non_negative_decimal(
            basis_abs_zscore_min,
            "basis_abs_zscore_min",
        ),
        "max_exposure_multiplier": exposure_multiplier,
    }


def _stress_flag_input_values(
    inputs: StressFlagInput,
) -> dict[str, Decimal | bool | None]:
    if inputs.systemic_shock is not None and not isinstance(inputs.systemic_shock, bool):
        raise ValueError("systemic_shock must be bool")
    return {
        "volatility_percentile": (
            _score_decimal(inputs.volatility_percentile, "volatility_percentile")
            if inputs.volatility_percentile is not None
            else None
        ),
        "liquidation_percentile": (
            _score_decimal(inputs.liquidation_percentile, "liquidation_percentile")
            if inputs.liquidation_percentile is not None
            else None
        ),
        "downside_return": (
            Decimal(str(inputs.downside_return))
            if inputs.downside_return is not None
            else None
        ),
        "funding_zscore": (
            Decimal(str(inputs.funding_zscore))
            if inputs.funding_zscore is not None
            else None
        ),
        "basis_zscore": (
            Decimal(str(inputs.basis_zscore))
            if inputs.basis_zscore is not None
            else None
        ),
        "systemic_shock": inputs.systemic_shock,
    }


def _capitulation_flag_thresholds(
    *,
    range_percentile_min: Any,
    downside_return_min: Any,
    liquidation_percentile_min: Any,
    volatility_percentile_min: Any,
    funding_zscore_max: Any,
) -> dict[str, Decimal]:
    downside_threshold = Decimal(str(downside_return_min))
    if downside_threshold >= 0:
        raise ValueError("downside_return_min must be < 0")
    funding_threshold = Decimal(str(funding_zscore_max))
    if funding_threshold >= 0:
        raise ValueError("funding_zscore_max must be < 0")
    return {
        "range_percentile_min": _score_decimal(
            range_percentile_min,
            "range_percentile_min",
        ),
        "downside_return_min": downside_threshold,
        "liquidation_percentile_min": _score_decimal(
            liquidation_percentile_min,
            "liquidation_percentile_min",
        ),
        "volatility_percentile_min": _score_decimal(
            volatility_percentile_min,
            "volatility_percentile_min",
        ),
        "funding_zscore_max": funding_threshold,
    }


def _capitulation_flag_input_values(
    inputs: CapitulationFlagInput,
) -> dict[str, Decimal | bool | None]:
    if inputs.systemic_shock is not None and not isinstance(inputs.systemic_shock, bool):
        raise ValueError("systemic_shock must be bool")
    return {
        "range_percentile": (
            _score_decimal(inputs.range_percentile, "range_percentile")
            if inputs.range_percentile is not None
            else None
        ),
        "downside_return": (
            Decimal(str(inputs.downside_return))
            if inputs.downside_return is not None
            else None
        ),
        "liquidation_percentile": (
            _score_decimal(inputs.liquidation_percentile, "liquidation_percentile")
            if inputs.liquidation_percentile is not None
            else None
        ),
        "volatility_percentile": (
            _score_decimal(inputs.volatility_percentile, "volatility_percentile")
            if inputs.volatility_percentile is not None
            else None
        ),
        "funding_zscore": (
            Decimal(str(inputs.funding_zscore))
            if inputs.funding_zscore is not None
            else None
        ),
        "systemic_shock": inputs.systemic_shock,
    }


def _euphoria_flag_thresholds(
    *,
    range_percentile_min: Any,
    upside_return_min: Any,
    funding_zscore_min: Any,
    basis_zscore_min: Any,
    oi_intensity_percentile_min: Any,
    volatility_percentile_min: Any,
) -> dict[str, Decimal]:
    upside_threshold = Decimal(str(upside_return_min))
    if upside_threshold <= 0:
        raise ValueError("upside_return_min must be > 0")
    return {
        "range_percentile_min": _score_decimal(
            range_percentile_min,
            "range_percentile_min",
        ),
        "upside_return_min": upside_threshold,
        "funding_zscore_min": _non_negative_decimal(
            funding_zscore_min,
            "funding_zscore_min",
        ),
        "basis_zscore_min": _non_negative_decimal(
            basis_zscore_min,
            "basis_zscore_min",
        ),
        "oi_intensity_percentile_min": _score_decimal(
            oi_intensity_percentile_min,
            "oi_intensity_percentile_min",
        ),
        "volatility_percentile_min": _score_decimal(
            volatility_percentile_min,
            "volatility_percentile_min",
        ),
    }


def _euphoria_flag_input_values(
    inputs: EuphoriaFlagInput,
) -> dict[str, Decimal | bool | None]:
    if inputs.systemic_euphoria is not None and not isinstance(
        inputs.systemic_euphoria,
        bool,
    ):
        raise ValueError("systemic_euphoria must be bool")
    return {
        "range_percentile": (
            _score_decimal(inputs.range_percentile, "range_percentile")
            if inputs.range_percentile is not None
            else None
        ),
        "upside_return": (
            Decimal(str(inputs.upside_return))
            if inputs.upside_return is not None
            else None
        ),
        "funding_zscore": (
            Decimal(str(inputs.funding_zscore))
            if inputs.funding_zscore is not None
            else None
        ),
        "basis_zscore": (
            Decimal(str(inputs.basis_zscore))
            if inputs.basis_zscore is not None
            else None
        ),
        "oi_intensity_percentile": (
            _score_decimal(
                inputs.oi_intensity_percentile,
                "oi_intensity_percentile",
            )
            if inputs.oi_intensity_percentile is not None
            else None
        ),
        "volatility_percentile": (
            _score_decimal(inputs.volatility_percentile, "volatility_percentile")
            if inputs.volatility_percentile is not None
            else None
        ),
        "systemic_euphoria": inputs.systemic_euphoria,
    }


def _orderliness_score_weights(weights: dict[str, Any] | None) -> dict[str, Decimal]:
    selected_weights = DEFAULT_ORDERLINESS_SCORE_WEIGHTS if weights is None else weights
    missing_keys = [
        component_id
        for component_id in ORDERLINESS_SCORE_COMPONENT_IDS
        if component_id not in selected_weights
    ]
    extra_keys = [
        component_id
        for component_id in selected_weights
        if component_id not in ORDERLINESS_SCORE_COMPONENT_IDS
    ]
    if missing_keys or extra_keys:
        raise ValueError("weights must match orderliness score component IDs")

    decimal_weights = {
        component_id: _non_negative_decimal(selected_weights[component_id], component_id)
        for component_id in ORDERLINESS_SCORE_COMPONENT_IDS
    }
    total_weight = sum(decimal_weights.values(), Decimal("0"))
    if total_weight != Decimal("1"):
        raise ValueError("weights must sum to 1")
    return decimal_weights


def _orderliness_thresholds(
    *,
    range_percentile_max: Any,
    downside_return_min: Any,
    liquidation_percentile_max: Any,
    volatility_percentile_max: Any,
) -> dict[str, Decimal]:
    downside_threshold = Decimal(str(downside_return_min))
    if downside_threshold >= 0:
        raise ValueError("downside_return_min must be < 0")
    return {
        "range_percentile_max": _score_decimal(
            range_percentile_max,
            "range_percentile_max",
        ),
        "downside_return_min": downside_threshold,
        "liquidation_percentile_max": _score_decimal(
            liquidation_percentile_max,
            "liquidation_percentile_max",
        ),
        "volatility_percentile_max": _score_decimal(
            volatility_percentile_max,
            "volatility_percentile_max",
        ),
    }


def _orderliness_score_input_values(
    inputs: OrderlinessScoreInput,
) -> dict[str, Decimal | None]:
    return {
        "extreme_range": (
            _score_decimal(inputs.range_percentile, "range_percentile")
            if inputs.range_percentile is not None
            else None
        ),
        "disorderly_downside": (
            Decimal(str(inputs.downside_return))
            if inputs.downside_return is not None
            else None
        ),
        "liquidation_cascade": (
            _score_decimal(inputs.liquidation_percentile, "liquidation_percentile")
            if inputs.liquidation_percentile is not None
            else None
        ),
        "volatility_spike": (
            _score_decimal(inputs.volatility_percentile, "volatility_percentile")
            if inputs.volatility_percentile is not None
            else None
        ),
        "range_percentile": (
            _score_decimal(inputs.range_percentile, "range_percentile")
            if inputs.range_percentile is not None
            else None
        ),
        "downside_return": (
            Decimal(str(inputs.downside_return))
            if inputs.downside_return is not None
            else None
        ),
        "liquidation_percentile": (
            _score_decimal(inputs.liquidation_percentile, "liquidation_percentile")
            if inputs.liquidation_percentile is not None
            else None
        ),
        "volatility_percentile": (
            _score_decimal(inputs.volatility_percentile, "volatility_percentile")
            if inputs.volatility_percentile is not None
            else None
        ),
    }


def _orderliness_component_triggered(
    component_id: str,
    reason_codes: Sequence[str],
) -> bool:
    reason_by_component = {
        "extreme_range": "ORDERLINESS_EXTREME_RANGE",
        "disorderly_downside": "ORDERLINESS_DISORDERLY_DOWNSIDE",
        "liquidation_cascade": "ORDERLINESS_LIQUIDATION_CASCADE",
        "volatility_spike": "ORDERLINESS_VOLATILITY_SPIKE",
    }
    return reason_by_component[component_id] in reason_codes


def _volatility_score_weights(weights: dict[str, Any] | None) -> dict[str, Decimal]:
    if weights is None:
        return dict(DEFAULT_VOLATILITY_SCORE_WEIGHTS)
    missing = [key for key in VOLATILITY_SCORE_COMPONENT_IDS if key not in weights]
    if missing:
        raise ValueError(f"volatility score weights missing components: {missing}")
    unexpected = [key for key in weights if key not in VOLATILITY_SCORE_COMPONENT_IDS]
    if unexpected:
        raise ValueError(f"unknown volatility score weights: {unexpected}")
    selected = {
        key: _non_negative_decimal(weights[key], f"weights.{key}")
        for key in VOLATILITY_SCORE_COMPONENT_IDS
    }
    total = sum(selected.values(), Decimal("0"))
    if total <= 0:
        raise ValueError("volatility score weights must have a positive total")
    return selected


def _compression_score_thresholds(
    *,
    full_score_ratio: Any,
    zero_score_ratio: Any,
) -> dict[str, Decimal]:
    full = _non_negative_decimal(full_score_ratio, "full_score_ratio")
    zero = _non_negative_decimal(zero_score_ratio, "zero_score_ratio")
    if decision_greater_equal(full, zero):
        raise ValueError(
            "compression full_score_ratio must be less than zero_score_ratio",
        )
    return {
        "compression_full_score_ratio": full,
        "compression_zero_score_ratio": zero,
    }


def _volatility_score_thresholds(
    *,
    full_score_ratio: Any,
    zero_score_ratio: Any,
    compressed_percentile_max: Any,
    normal_percentile_max: Any,
    elevated_percentile_max: Any,
    disorderly_score_max: Any,
) -> dict[str, Decimal]:
    compressed = _score_decimal(compressed_percentile_max, "compressed_percentile_max")
    normal = _score_decimal(normal_percentile_max, "normal_percentile_max")
    elevated = _score_decimal(elevated_percentile_max, "elevated_percentile_max")
    if not (
        decision_less_equal(compressed, normal)
        and decision_less_equal(normal, elevated)
    ):
        raise ValueError(
            "volatility regime percentile bounds must be non-decreasing",
        )
    return {
        **_compression_score_thresholds(
            full_score_ratio=full_score_ratio,
            zero_score_ratio=zero_score_ratio,
        ),
        "regime_compressed_percentile_max": compressed,
        "regime_normal_percentile_max": normal,
        "regime_elevated_percentile_max": elevated,
        "orderliness_disorderly_score_max": _score_decimal(
            disorderly_score_max,
            "disorderly_score_max",
        ),
    }


def _volatility_regime(
    volatility_percentile_value: Decimal | None,
    thresholds: dict[str, Decimal],
) -> str | None:
    if volatility_percentile_value is None:
        return None
    if decision_less_equal(
        volatility_percentile_value,
        thresholds["regime_compressed_percentile_max"],
    ):
        return "COMPRESSED"
    if decision_less_equal(
        volatility_percentile_value,
        thresholds["regime_normal_percentile_max"],
    ):
        return "NORMAL"
    if decision_less_equal(
        volatility_percentile_value,
        thresholds["regime_elevated_percentile_max"],
    ):
        return "ELEVATED"
    return "STRESSED"


def _volatility_score_interpretation(score: Decimal | None) -> str | None:
    if score is None:
        return None
    if decision_greater_equal(score, Decimal("80")):
        return "FAVORABLE"
    if decision_greater_equal(score, Decimal("60")):
        return "ACCEPTABLE"
    if decision_greater_equal(score, Decimal("40")):
        return "MARGINAL"
    return "UNFAVORABLE"


def _orderliness_score_interpretation(score: Decimal | None) -> str | None:
    if score is None:
        return None
    if decision_greater_equal(score, Decimal("80")):
        return "ORDERLY"
    if decision_greater_equal(score, Decimal("60")):
        return "MIXED"
    if decision_greater_equal(score, Decimal("40")):
        return "DISORDERLY"
    return "STRESSED"


def _validate_volatility_percentile_parameters(
    *,
    source_feature_id: str,
    percentile_window_days: int,
    min_percentile_observations: int,
) -> None:
    if not source_feature_id.strip():
        raise ValueError("source_feature_id must be non-empty")
    if percentile_window_days < 1:
        raise ValueError("percentile_window_days must be >= 1")
    if min_percentile_observations < 1:
        raise ValueError("min_percentile_observations must be >= 1")
    if min_percentile_observations > percentile_window_days:
        raise ValueError("min_percentile_observations must be <= percentile_window_days")


def _compression_input_values(
    inputs: VolatilityCompressionRatioInput,
) -> dict[str, Decimal | None]:
    return {
        "rv_7": _non_negative_decimal(inputs.rv_7, "rv_7")
        if inputs.rv_7 is not None
        else None,
        "rv_60": _non_negative_decimal(inputs.rv_60, "rv_60")
        if inputs.rv_60 is not None
        else None,
    }


def _available_realized_volatility_results(
    results: Sequence[RealizedVolatilityResult],
    *,
    source_feature_id: str,
    signal_time: datetime,
) -> tuple[RealizedVolatilityResult, ...]:
    available_results = []
    for result in results:
        observation_time = require_utc_datetime(
            result.observation_time,
            "observation_time",
        )
        if (
            result.feature_id == source_feature_id
            and observation_time <= signal_time
        ):
            available_results.append(result)
    return tuple(sorted(available_results, key=lambda result: result.observation_time))


def _realized_volatility_history(
    results: Sequence[RealizedVolatilityResult],
    *,
    observation_time: datetime,
    percentile_window_days: int,
) -> tuple[Decimal, ...]:
    window_start = observation_time - timedelta(days=percentile_window_days)
    return tuple(
        _non_negative_decimal(result.realized_volatility, "realized_volatility")
        for result in results
        if result.realized_volatility is not None
        and window_start <= result.observation_time < observation_time
    )


def _available_daily_bars(
    bars: Sequence[OhlcvBar],
    *,
    signal_time: datetime,
) -> tuple[OhlcvBar, ...]:
    available_bars = []
    for bar in bars:
        record = bar.as_record()
        if record["ingested_at"] <= signal_time and record["timestamp"] <= signal_time:
            available_bars.append(bar)
    return tuple(sorted(available_bars, key=lambda bar: bar.timestamp))


def _realized_volatility_feature_id(window_days: int) -> str:
    return REALIZED_VOLATILITY_FEATURE_IDS.get(window_days, f"RV_{window_days}")


def _non_negative_decimal(value: Any, name: str) -> Decimal:
    decimal_value = Decimal(str(value))
    if decimal_value < 0:
        raise ValueError(f"{name} must be >= 0")
    return decimal_value


def _score_decimal(value: Any, name: str) -> Decimal:
    decimal_value = Decimal(str(value))
    if decimal_value < 0 or decimal_value > 100:
        raise ValueError(f"{name} must be between 0 and 100")
    return decimal_value


def _percentile_rank(value: Decimal, history: Sequence[Decimal]) -> Decimal:
    if not history:
        raise ValueError("history must contain at least one observation")
    less_count = sum(1 for item in history if item < value)
    equal_count = sum(1 for item in history if item == value)
    rank = Decimal(less_count) + (Decimal("0.5") * Decimal(equal_count))
    return (rank / Decimal(len(history))) * Decimal("100")


def _dedupe_reason_codes(reason_codes: Sequence[str]) -> tuple[str, ...]:
    deduped = []
    for reason_code in reason_codes:
        if reason_code not in deduped:
            deduped.append(reason_code)
    return tuple(deduped)
