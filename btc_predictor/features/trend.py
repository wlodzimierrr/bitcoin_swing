"""Trend feature helpers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from btc_predictor.data import OhlcvBar
from btc_predictor.features.rolling import NumericValue, OptionalDecimalSeries, rolling_mean


TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS = 20
TWENTY_WEEK_MA_DISTANCE_FEATURE_ID = "MA_DISTANCE_20W"
WEEKLY_STRUCTURE_FEATURE_ID = "WEEKLY_STRUCTURE"
WEEKLY_STRUCTURE_LABELS = ("HH_HL", "HL_ONLY", "MIXED", "LH_ONLY", "LH_LL")
WEEKLY_STRUCTURE_SCORES = {
    "HH_HL": Decimal("1.0"),
    "HL_ONLY": Decimal("0.5"),
    "MIXED": Decimal("0.0"),
    "LH_ONLY": Decimal("-0.5"),
    "LH_LL": Decimal("-1.0"),
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
