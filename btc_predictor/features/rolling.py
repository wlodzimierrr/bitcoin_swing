"""Past-only rolling statistics for feature generation."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import TypeAlias

from btc_predictor.data import OhlcvBar


NumericValue: TypeAlias = Decimal | int | float | str
OptionalDecimalSeries: TypeAlias = tuple[Decimal | None, ...]


def rolling_mean(
    values: Sequence[NumericValue],
    *,
    window: int,
    min_periods: int | None = None,
) -> OptionalDecimalSeries:
    """Return trailing rolling means using observations through the current index."""

    decimal_values = _decimal_values(values)
    required = _validate_min_periods(window, min_periods)
    return tuple(
        _mean(window_values) if len(window_values) >= required else None
        for window_values in _inclusive_windows(decimal_values, window)
    )


def rolling_volatility(
    values: Sequence[NumericValue],
    *,
    window: int,
    min_periods: int | None = None,
    sample: bool = False,
) -> OptionalDecimalSeries:
    """Return trailing rolling standard deviation through the current index."""

    decimal_values = _decimal_values(values)
    required = _validate_min_periods(window, min_periods)
    return tuple(
        _standard_deviation(window_values, sample=sample)
        if len(window_values) >= required and _has_enough_degrees_of_freedom(window_values, sample)
        else None
        for window_values in _inclusive_windows(decimal_values, window)
    )


def rolling_zscore(
    values: Sequence[NumericValue],
    *,
    window: int,
    min_periods: int | None = None,
    sample: bool = False,
) -> OptionalDecimalSeries:
    """Score each value against the prior trailing window, excluding itself."""

    decimal_values = _decimal_values(values)
    required = _validate_min_periods(window, min_periods)
    zscores = []
    for index, value in enumerate(decimal_values):
        history = _prior_window(decimal_values, index, window)
        if len(history) < required or not _has_enough_degrees_of_freedom(history, sample):
            zscores.append(None)
            continue
        volatility = _standard_deviation(history, sample=sample)
        if volatility is None or volatility == 0:
            zscores.append(None)
            continue
        zscores.append((value - _mean(history)) / volatility)
    return tuple(zscores)


def rolling_percentile(
    values: Sequence[NumericValue],
    *,
    window: int,
    min_periods: int | None = None,
) -> OptionalDecimalSeries:
    """Return each value's percentile rank against prior observations only."""

    decimal_values = _decimal_values(values)
    required = _validate_min_periods(window, min_periods)
    percentiles = []
    for index, value in enumerate(decimal_values):
        history = _prior_window(decimal_values, index, window)
        if len(history) < required:
            percentiles.append(None)
            continue
        count_less = sum(1 for historical in history if historical < value)
        count_equal = sum(1 for historical in history if historical == value)
        rank = Decimal(count_less) + (Decimal("0.5") * Decimal(count_equal))
        percentiles.append((rank / Decimal(len(history))) * Decimal("100"))
    return tuple(percentiles)


def historical_normalize(
    values: Sequence[NumericValue],
    *,
    window: int,
    min_periods: int | None = None,
    lower: NumericValue = Decimal("0"),
    upper: NumericValue = Decimal("100"),
) -> OptionalDecimalSeries:
    """Normalize each value to a configured range using prior min/max history."""

    decimal_values = _decimal_values(values)
    required = _validate_min_periods(window, min_periods)
    lower_bound = _decimal(lower)
    upper_bound = _decimal(upper)
    if upper_bound <= lower_bound:
        raise ValueError("upper must be greater than lower")

    normalized = []
    for index, value in enumerate(decimal_values):
        history = _prior_window(decimal_values, index, window)
        if len(history) < required:
            normalized.append(None)
            continue
        historical_min = min(history)
        historical_max = max(history)
        if historical_max == historical_min:
            normalized.append(None)
            continue
        fraction = (value - historical_min) / (historical_max - historical_min)
        clipped = min(max(fraction, Decimal("0")), Decimal("1"))
        normalized.append(lower_bound + clipped * (upper_bound - lower_bound))
    return tuple(normalized)


def true_ranges(bars: Sequence[OhlcvBar]) -> tuple[Decimal, ...]:
    """Return true range values using each bar and the previous close only."""

    ordered = tuple(sorted(bars, key=lambda bar: bar.timestamp))
    ranges = []
    previous_close: Decimal | None = None
    for bar in ordered:
        high_low = bar.high - bar.low
        if previous_close is None:
            ranges.append(high_low)
        else:
            ranges.append(
                max(
                    high_low,
                    abs(bar.high - previous_close),
                    abs(bar.low - previous_close),
                )
            )
        previous_close = bar.close
    return tuple(ranges)


def average_true_range(
    bars: Sequence[OhlcvBar],
    *,
    window: int,
    min_periods: int | None = None,
) -> OptionalDecimalSeries:
    """Return trailing ATR from true ranges through the current bar."""

    return rolling_mean(true_ranges(bars), window=window, min_periods=min_periods)


def _inclusive_windows(values: Sequence[Decimal], window: int) -> tuple[tuple[Decimal, ...], ...]:
    _validate_window(window)
    return tuple(
        tuple(values[max(0, index - window + 1) : index + 1])
        for index in range(len(values))
    )


def _prior_window(values: Sequence[Decimal], index: int, window: int) -> tuple[Decimal, ...]:
    _validate_window(window)
    return tuple(values[max(0, index - window) : index])


def _validate_window(window: int) -> None:
    if window < 1:
        raise ValueError("window must be >= 1")


def _validate_min_periods(window: int, min_periods: int | None) -> int:
    _validate_window(window)
    required = window if min_periods is None else min_periods
    if required < 1:
        raise ValueError("min_periods must be >= 1")
    if required > window:
        raise ValueError("min_periods must be <= window")
    return required


def _decimal_values(values: Sequence[NumericValue]) -> tuple[Decimal, ...]:
    return tuple(_decimal(value) for value in values)


def _decimal(value: NumericValue) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _mean(values: Sequence[Decimal]) -> Decimal:
    if not values:
        raise ValueError("values must contain at least one observation")
    return sum(values, Decimal("0")) / Decimal(len(values))


def _standard_deviation(values: Sequence[Decimal], *, sample: bool) -> Decimal | None:
    if not _has_enough_degrees_of_freedom(values, sample):
        return None
    mean = _mean(values)
    denominator = Decimal(len(values) - 1 if sample else len(values))
    variance = sum(((value - mean) ** 2 for value in values), Decimal("0")) / denominator
    return variance.sqrt()


def _has_enough_degrees_of_freedom(values: Sequence[Decimal], sample: bool) -> bool:
    return len(values) >= 2 if sample else len(values) >= 1
