"""Trend feature helpers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from btc_predictor.data import OhlcvBar
from btc_predictor.features.rolling import NumericValue, OptionalDecimalSeries, rolling_mean
from btc_predictor.quant.transforms import normal_cdf_score


TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS = 20
TWENTY_WEEK_MA_DISTANCE_FEATURE_ID = "MA_DISTANCE_20W"
FIFTY_TWO_WEEK_HIGH_DISTANCE_LOOKBACK_WEEKS = 52
FIFTY_TWO_WEEK_HIGH_DISTANCE_FEATURE_ID = "HIGH_DISTANCE_52W"
TREND_SCORE_FEATURE_ID = "TREND_SCORE"
TREND_SCORE_COMPONENT_IDS = ("Z_M4", "Z_M12", "Z_20W", "S_STRUCTURE", "Z_52H")
WEEKLY_STRUCTURE_FEATURE_ID = "WEEKLY_STRUCTURE"
WEEKLY_STRUCTURE_LABELS = ("HH_HL", "HL_ONLY", "MIXED", "LH_ONLY", "LH_LL")
WEEKLY_STRUCTURE_SCORES = {
    "HH_HL": Decimal("1.0"),
    "HL_ONLY": Decimal("0.5"),
    "MIXED": Decimal("0.0"),
    "LH_ONLY": Decimal("-0.5"),
    "LH_LL": Decimal("-1.0"),
}
DEFAULT_TREND_SCORE_WEIGHTS = {
    "Z_M4": Decimal("0.30"),
    "Z_M12": Decimal("0.30"),
    "Z_20W": Decimal("0.20"),
    "S_STRUCTURE": Decimal("0.15"),
    "Z_52H": Decimal("0.05"),
}


@dataclass(frozen=True)
class WeeklyStructureClassification:
    timestamp_index: int
    label: str
    raw_score: Decimal
    higher_high: bool
    higher_low: bool
    lower_high: bool
    lower_low: bool

    @property
    def reason_code(self) -> str:
        return f"{WEEKLY_STRUCTURE_FEATURE_ID}_{self.label}"


@dataclass(frozen=True)
class TrendScoreInput:
    z_m4: Decimal
    z_m12: Decimal
    z_20w: Decimal
    structure_score: Decimal
    z_52h: Decimal

    def as_record(self) -> dict[str, str]:
        return {
            "Z_M4": str(self.z_m4),
            "Z_M12": str(self.z_m12),
            "Z_20W": str(self.z_20w),
            "S_STRUCTURE": str(self.structure_score),
            "Z_52H": str(self.z_52h),
        }


@dataclass(frozen=True)
class TrendScoreResult:
    feature_id: str
    raw_score: Decimal
    score: Decimal
    interpretation: str
    inputs: TrendScoreInput
    weights: dict[str, Decimal]
    contributions: dict[str, Decimal]

    @property
    def reason_code(self) -> str:
        return f"{self.feature_id}_{self.interpretation}"

    def as_record(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "raw_score": str(self.raw_score),
            "score": str(self.score),
            "interpretation": self.interpretation,
            "reason_code": self.reason_code,
            "inputs": self.inputs.as_record(),
            "weights": {key: str(value) for key, value in self.weights.items()},
            "contributions": {key: str(value) for key, value in self.contributions.items()},
        }


def moving_average_distance(
    prices: Sequence[NumericValue],
    *,
    window: int,
) -> OptionalDecimalSeries:
    """Calculate distance from trailing moving average as (P_t - MA) / MA."""

    moving_average = rolling_mean(prices, window=window)
    decimal_prices = tuple(_decimal(price) for price in prices)
    distances = []
    for price, average in zip(decimal_prices, moving_average):
        distances.append(None if average is None or average == 0 else (price - average) / average)
    return tuple(distances)


def calculate_trend_score(
    inputs: TrendScoreInput,
    *,
    weights: dict[str, NumericValue] | None = None,
) -> TrendScoreResult:
    """Calculate the rulebook trend score as 100 * Phi(weighted trend raw)."""

    selected_weights = _trend_score_weights(weights)
    input_values = _trend_score_input_values(inputs)
    contributions = {
        component_id: selected_weights[component_id] * input_values[component_id]
        for component_id in TREND_SCORE_COMPONENT_IDS
    }
    raw_score = sum(contributions.values(), Decimal("0"))
    score = _standard_normal_score(raw_score)
    return TrendScoreResult(
        feature_id=TREND_SCORE_FEATURE_ID,
        raw_score=raw_score,
        score=score,
        interpretation=_trend_score_interpretation(score),
        inputs=inputs,
        weights=selected_weights,
        contributions=contributions,
    )


def twenty_week_ma_distance(
    prices: Sequence[NumericValue],
    *,
    window: int = TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS,
) -> OptionalDecimalSeries:
    """Calculate 20-week MA distance as (P_t - MA_20W) / MA_20W."""

    return moving_average_distance(prices, window=window)


def twenty_week_ma_distance_from_weekly_bars(
    bars: Sequence[OhlcvBar],
) -> OptionalDecimalSeries:
    """Calculate 20-week MA distance from canonical weekly close prices."""

    ordered = tuple(sorted(bars, key=lambda bar: bar.timestamp))
    for bar in ordered:
        if bar.timeframe != "1w":
            raise ValueError("twenty_week_ma_distance_from_weekly_bars requires 1w bars")
    return twenty_week_ma_distance([bar.close for bar in ordered])


def rolling_high_distance(
    prices: Sequence[NumericValue],
    highs: Sequence[NumericValue],
    *,
    window: int,
) -> OptionalDecimalSeries:
    """Calculate distance from trailing high as (P_t - H) / H."""

    if len(prices) != len(highs):
        raise ValueError("prices and highs must have the same length")
    if window < 1:
        raise ValueError("window must be >= 1")

    decimal_prices = tuple(_decimal(price) for price in prices)
    decimal_highs = tuple(_decimal(high) for high in highs)
    distances = []
    for index, price in enumerate(decimal_prices):
        if index < window - 1:
            distances.append(None)
            continue
        trailing_high = max(decimal_highs[index - window + 1 : index + 1])
        distances.append(None if trailing_high == 0 else (price - trailing_high) / trailing_high)
    return tuple(distances)


def fifty_two_week_high_distance(
    prices: Sequence[NumericValue],
    highs: Sequence[NumericValue] | None = None,
    *,
    window: int = FIFTY_TWO_WEEK_HIGH_DISTANCE_LOOKBACK_WEEKS,
) -> OptionalDecimalSeries:
    """Calculate 52-week high distance as (P_t - H_52W) / H_52W."""

    high_values = prices if highs is None else highs
    return rolling_high_distance(prices, high_values, window=window)


def fifty_two_week_high_distance_from_weekly_bars(
    bars: Sequence[OhlcvBar],
) -> OptionalDecimalSeries:
    """Calculate 52-week high distance from canonical weekly bars."""

    ordered = tuple(sorted(bars, key=lambda bar: bar.timestamp))
    for bar in ordered:
        if bar.timeframe != "1w":
            raise ValueError("fifty_two_week_high_distance_from_weekly_bars requires 1w bars")
    return fifty_two_week_high_distance(
        prices=[bar.close for bar in ordered],
        highs=[bar.high for bar in ordered],
    )


def classify_weekly_structure(
    highs: Sequence[NumericValue],
    lows: Sequence[NumericValue],
) -> tuple[WeeklyStructureClassification | None, ...]:
    """Classify weekly high/low structure against the previous observation."""

    if len(highs) != len(lows):
        raise ValueError("highs and lows must have the same length")

    decimal_highs = tuple(_decimal(high) for high in highs)
    decimal_lows = tuple(_decimal(low) for low in lows)
    for high, low in zip(decimal_highs, decimal_lows):
        if high < low:
            raise ValueError("weekly high must be >= weekly low")

    classifications: list[WeeklyStructureClassification | None] = []
    for index, (high, low) in enumerate(zip(decimal_highs, decimal_lows)):
        if index == 0:
            classifications.append(None)
            continue

        previous_high = decimal_highs[index - 1]
        previous_low = decimal_lows[index - 1]
        higher_high = high > previous_high
        higher_low = low > previous_low
        lower_high = high < previous_high
        lower_low = low < previous_low
        label = _weekly_structure_label(
            higher_high=higher_high,
            higher_low=higher_low,
            lower_high=lower_high,
            lower_low=lower_low,
        )
        classifications.append(
            WeeklyStructureClassification(
                timestamp_index=index,
                label=label,
                raw_score=WEEKLY_STRUCTURE_SCORES[label],
                higher_high=higher_high,
                higher_low=higher_low,
                lower_high=lower_high,
                lower_low=lower_low,
            )
        )
    return tuple(classifications)


def classify_weekly_structure_from_weekly_bars(
    bars: Sequence[OhlcvBar],
) -> tuple[WeeklyStructureClassification | None, ...]:
    """Classify weekly structure from canonical weekly bars in timestamp order."""

    ordered = tuple(sorted(bars, key=lambda bar: bar.timestamp))
    for bar in ordered:
        if bar.timeframe != "1w":
            raise ValueError("classify_weekly_structure_from_weekly_bars requires 1w bars")
    return classify_weekly_structure(
        highs=[bar.high for bar in ordered],
        lows=[bar.low for bar in ordered],
    )


def _trend_score_weights(weights: dict[str, NumericValue] | None) -> dict[str, Decimal]:
    if weights is None:
        return dict(DEFAULT_TREND_SCORE_WEIGHTS)

    missing = set(TREND_SCORE_COMPONENT_IDS) - set(weights)
    extra = set(weights) - set(TREND_SCORE_COMPONENT_IDS)
    if missing or extra:
        raise ValueError(
            f"trend score weights must exactly match {TREND_SCORE_COMPONENT_IDS}; "
            f"missing={sorted(missing)}, extra={sorted(extra)}"
        )
    decimal_weights = {component_id: _decimal(weights[component_id]) for component_id in TREND_SCORE_COMPONENT_IDS}
    if any(weight < 0 for weight in decimal_weights.values()):
        raise ValueError("trend score weights must be non-negative")
    if sum(decimal_weights.values(), Decimal("0")) == 0:
        raise ValueError("trend score weights must have positive total weight")
    return decimal_weights


def _trend_score_input_values(inputs: TrendScoreInput) -> dict[str, Decimal]:
    return {
        "Z_M4": inputs.z_m4,
        "Z_M12": inputs.z_m12,
        "Z_20W": inputs.z_20w,
        "S_STRUCTURE": inputs.structure_score,
        "Z_52H": inputs.z_52h,
    }


def _standard_normal_score(raw_score: Decimal) -> Decimal:
    return Decimal(str(normal_cdf_score(float(raw_score))))


def _trend_score_interpretation(score: Decimal) -> str:
    if score >= Decimal("80"):
        return "STRONG_BULLISH"
    if score >= Decimal("65"):
        return "BULLISH"
    if score >= Decimal("45"):
        return "MIXED"
    if score >= Decimal("25"):
        return "BEARISH"
    return "STRONG_BEARISH"


def _weekly_structure_label(
    *,
    higher_high: bool,
    higher_low: bool,
    lower_high: bool,
    lower_low: bool,
) -> str:
    if higher_high and higher_low:
        return "HH_HL"
    if higher_low and not higher_high:
        return "HL_ONLY"
    if lower_high and lower_low:
        return "LH_LL"
    if lower_high and not lower_low:
        return "LH_ONLY"
    return "MIXED"


def _decimal(value: NumericValue) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
