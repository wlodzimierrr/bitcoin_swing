"""Past-only rolling statistics for feature generation."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import TypeAlias

import numpy as np

from btc_predictor.data import OhlcvBar
from btc_predictor.quant.rolling import (
    average_true_range as quant_average_true_range,
    historical_normalize as quant_historical_normalize,
    rolling_mean as quant_rolling_mean,
    rolling_percentile as quant_rolling_percentile,
    rolling_volatility as quant_rolling_volatility,
    rolling_zscore as quant_rolling_zscore,
    true_range as quant_true_range,
)


NumericValue: TypeAlias = Decimal | int | float | str
OptionalDecimalSeries: TypeAlias = tuple[Decimal | None, ...]


def rolling_mean(
    values: Sequence[NumericValue],
    *,
    window: int,
    min_periods: int | None = None,
) -> OptionalDecimalSeries:
    """Return trailing rolling means using observations through the current index."""

    return _optional_decimals(
        quant_rolling_mean(
            _float_values(values),
            window=window,
            min_periods=min_periods,
        )
    )


def rolling_volatility(
    values: Sequence[NumericValue],
    *,
    window: int,
    min_periods: int | None = None,
    sample: bool = False,
) -> OptionalDecimalSeries:
    """Return trailing rolling standard deviation through the current index."""

    return _optional_decimals(
        quant_rolling_volatility(
            _float_values(values),
            window=window,
            min_periods=min_periods,
            sample=sample,
        )
    )


def rolling_zscore(
    values: Sequence[NumericValue],
    *,
    window: int,
    min_periods: int | None = None,
    sample: bool = False,
) -> OptionalDecimalSeries:
    """Score each value against the prior trailing window, excluding itself."""

    return _optional_decimals(
        quant_rolling_zscore(
            _float_values(values),
            window=window,
            min_periods=min_periods,
            sample=sample,
        )
    )


def rolling_percentile(
    values: Sequence[NumericValue],
    *,
    window: int,
    min_periods: int | None = None,
) -> OptionalDecimalSeries:
    """Return each value's percentile rank against prior observations only."""

    return _optional_decimals(
        quant_rolling_percentile(
            _float_values(values),
            window=window,
            min_periods=min_periods,
        )
    )


def historical_normalize(
    values: Sequence[NumericValue],
    *,
    window: int,
    min_periods: int | None = None,
    lower: NumericValue = Decimal("0"),
    upper: NumericValue = Decimal("100"),
) -> OptionalDecimalSeries:
    """Normalize each value to a configured range using prior min/max history."""

    lower_bound = _decimal(lower)
    upper_bound = _decimal(upper)
    if upper_bound <= lower_bound:
        raise ValueError("upper must be greater than lower")
    return _optional_decimals(
        quant_historical_normalize(
            _float_values(values),
            window=window,
            min_periods=min_periods,
            lower=float(lower_bound),
            upper=float(upper_bound),
        )
    )


def true_ranges(bars: Sequence[OhlcvBar]) -> tuple[Decimal, ...]:
    """Return true range values using each bar and the previous close only."""

    ordered = tuple(sorted(bars, key=lambda bar: bar.timestamp))
    highs, lows, closes = _bar_arrays(ordered)
    return _decimals(quant_true_range(highs, lows, closes))


def average_true_range(
    bars: Sequence[OhlcvBar],
    *,
    window: int,
    min_periods: int | None = None,
) -> OptionalDecimalSeries:
    """Return trailing ATR from true ranges through the current bar."""

    ordered = tuple(sorted(bars, key=lambda bar: bar.timestamp))
    highs, lows, closes = _bar_arrays(ordered)
    return _optional_decimals(
        quant_average_true_range(
            highs,
            lows,
            closes,
            window=window,
            min_periods=min_periods,
        )
    )


def _float_values(values: Sequence[NumericValue]) -> tuple[float, ...]:
    return tuple(float(_decimal(value)) for value in values)


def _decimal(value: NumericValue) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _bar_arrays(
    bars: Sequence[OhlcvBar],
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    return (
        tuple(float(bar.high) for bar in bars),
        tuple(float(bar.low) for bar in bars),
        tuple(float(bar.close) for bar in bars),
    )


def _optional_decimals(values: np.ndarray) -> OptionalDecimalSeries:
    return tuple(None if np.isnan(value) else _float_decimal(value) for value in values)


def _decimals(values: np.ndarray) -> tuple[Decimal, ...]:
    return tuple(_float_decimal(value) for value in values)


def _float_decimal(value: np.float64) -> Decimal:
    return Decimal("0") if value == 0 else Decimal(str(float(value)))
