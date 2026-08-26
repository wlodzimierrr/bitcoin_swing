"""Momentum feature helpers."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from btc_predictor.data import OhlcvBar
from btc_predictor.features.rolling import NumericValue, OptionalDecimalSeries


FOUR_WEEK_MOMENTUM_LOOKBACK_DAYS = 28
FOUR_WEEK_MOMENTUM_FEATURE_ID = "MOMENTUM_4W"


def four_week_momentum(
    prices: Sequence[NumericValue],
    *,
    lookback_periods: int = FOUR_WEEK_MOMENTUM_LOOKBACK_DAYS,
) -> OptionalDecimalSeries:
    """Calculate 4-week momentum as P_t / P_t-28 - 1."""

    if lookback_periods < 1:
        raise ValueError("lookback_periods must be >= 1")

    decimal_prices = tuple(_decimal(price) for price in prices)
    momentum = []
    for index, price in enumerate(decimal_prices):
        if index < lookback_periods:
            momentum.append(None)
            continue
        prior_price = decimal_prices[index - lookback_periods]
        momentum.append(None if prior_price == 0 else (price / prior_price) - Decimal("1"))
    return tuple(momentum)


def four_week_momentum_from_daily_bars(
    bars: Sequence[OhlcvBar],
) -> OptionalDecimalSeries:
    """Calculate 4-week momentum from canonical daily close prices."""

    ordered = tuple(sorted(bars, key=lambda bar: bar.timestamp))
    for bar in ordered:
        if bar.timeframe != "1d":
            raise ValueError("four_week_momentum_from_daily_bars requires 1d bars")
    return four_week_momentum([bar.close for bar in ordered])


def _decimal(value: NumericValue) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
