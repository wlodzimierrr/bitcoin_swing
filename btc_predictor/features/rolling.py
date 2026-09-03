"""Past-only rolling statistics for feature generation."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import TypeAlias

import numpy as np

from btc_predictor.data import OhlcvBar, next_bar_timestamp
from btc_predictor.quant.rolling import (
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


def true_ranges(bars: Sequence[OhlcvBar]) -> OptionalDecimalSeries:
    """Return true range values using each bar and the previous close only.

    The range of a bar whose preceding session is absent from the series is
    ``None`` rather than a measurement taken against an older close.
    """

    ordered, gaps = _ordered_bar_series(bars)
    return _optional_decimals(_bar_true_ranges(ordered, gaps))


def average_true_range(
    bars: Sequence[OhlcvBar],
    *,
    window: int,
    min_periods: int | None = None,
) -> OptionalDecimalSeries:
    """Return trailing ATR from true ranges through the current bar.

    A window that spans an absent session has no defined mean true range and
    is reported as ``None``.
    """

    ordered, gaps = _ordered_bar_series(bars)
    return _optional_decimals(
        quant_rolling_mean(
            _bar_true_ranges(ordered, gaps),
            window=window,
            min_periods=min_periods,
            nan_policy="propagate",
        )
    )


def _ordered_bar_series(
    bars: Sequence[OhlcvBar],
) -> tuple[tuple[OhlcvBar, ...], tuple[int, ...]]:
    """Order bars in time and report which of them follow an absent session.

    True range reads the preceding element as the preceding period. A canonical
    BTC-040 market-bar series legitimately omits an incomplete bucket, so a
    series handed to BTC-041 can be regularly spaced or can carry an outage.
    The outage stays visible as an undefined observation instead of being
    absorbed into a range measured against a close several periods older.
    A series that is not one regularly spaced timeframe at all — mixed
    timeframes, a repeated timestamp, or an off-cadence timestamp — has no such
    reading and is refused.
    """

    ordered = tuple(sorted(bars, key=lambda bar: bar.timestamp))
    if not ordered:
        return ordered, ()
    timeframes = {bar.timeframe for bar in ordered}
    if len(timeframes) > 1:
        raise ValueError(
            "true range requires one bar timeframe; received: "
            f"{', '.join(sorted(timeframes))}"
        )
    timeframe = ordered[0].timeframe
    gaps = []
    for index, (previous, current) in enumerate(zip(ordered, ordered[1:]), start=1):
        expected = next_bar_timestamp(previous.timestamp, timeframe)
        if current.timestamp == expected:
            continue
        if current.timestamp < expected:
            raise ValueError(
                "true range requires one regularly spaced bar series; "
                f"{previous.timestamp.isoformat()} is followed by "
                f"{current.timestamp.isoformat()} rather than "
                f"{expected.isoformat()}"
            )
        gaps.append(index)
    return ordered, tuple(gaps)


def _bar_true_ranges(
    bars: Sequence[OhlcvBar],
    gaps: Sequence[int],
) -> np.ndarray:
    highs, lows, closes = _bar_arrays(bars)
    ranges = quant_true_range(highs, lows, closes)
    for index in gaps:
        ranges[index] = np.nan
    return ranges


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


def _float_decimal(value: np.float64) -> Decimal:
    return Decimal("0") if value == 0 else Decimal(str(float(value)))
