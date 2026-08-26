"""Trend feature helpers."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from btc_predictor.data import OhlcvBar
from btc_predictor.features.rolling import NumericValue, OptionalDecimalSeries, rolling_mean


TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS = 20
TWENTY_WEEK_MA_DISTANCE_FEATURE_ID = "MA_DISTANCE_20W"


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


def _decimal(value: NumericValue) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
