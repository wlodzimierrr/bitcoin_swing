"""Vectorized past-only kernels matching the BTC-041 reference behavior."""

from __future__ import annotations

from typing import Literal, TypeAlias

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from numpy.typing import ArrayLike

from btc_predictor.quant.arrays import (
    FloatArray,
    NanPolicy,
    NumericInputError,
    as_float64_vector,
    reject_infinite_result,
    require_same_shape,
)

RollingNanPolicy: TypeAlias = Literal["raise", "propagate", "omit"]
ROLLING_NAN_POLICIES = ("raise", "propagate", "omit")


def rolling_mean(
    values: ArrayLike,
    *,
    window: int,
    min_periods: int | None = None,
    nan_policy: RollingNanPolicy = "raise",
) -> FloatArray:
    """Return trailing means through the current observation."""

    array = _rolling_array(values, nan_policy)
    required = _validate_window(window, min_periods)
    windows, expected_counts = _inclusive_windows(array, window)
    counts, valid = _window_validity(
        windows,
        expected_counts=expected_counts,
        required=required,
        nan_policy=nan_policy,
    )
    return _checked_output(
        _window_means(windows, counts=counts, valid=valid),
        name="rolling_mean",
    )


def rolling_volatility(
    values: ArrayLike,
    *,
    window: int,
    min_periods: int | None = None,
    sample: bool = False,
    nan_policy: RollingNanPolicy = "raise",
) -> FloatArray:
    """Return trailing standard deviations through the current observation."""

    array = _rolling_array(values, nan_policy)
    required = _validate_window(window, min_periods)
    ddof = _sample_ddof(sample)
    windows, expected_counts = _inclusive_windows(array, window)
    counts, valid = _window_validity(
        windows,
        expected_counts=expected_counts,
        required=required,
        nan_policy=nan_policy,
    )
    valid &= counts > ddof
    return _checked_output(
        _window_standard_deviations(
            windows,
            counts=counts,
            valid=valid,
            ddof=ddof,
        ),
        name="rolling_volatility",
    )


def rolling_zscore(
    values: ArrayLike,
    *,
    window: int,
    min_periods: int | None = None,
    sample: bool = False,
    nan_policy: RollingNanPolicy = "raise",
) -> FloatArray:
    """Score each observation against its prior window, excluding itself."""

    array = _rolling_array(values, nan_policy)
    required = _validate_window(window, min_periods)
    ddof = _sample_ddof(sample)
    windows, expected_counts = _prior_windows(array, window)
    counts, valid = _window_validity(
        windows,
        expected_counts=expected_counts,
        required=required,
        nan_policy=nan_policy,
    )
    valid &= counts > ddof
    means = _window_means(windows, counts=counts, valid=valid)
    deviations = _window_standard_deviations(
        windows,
        counts=counts,
        valid=valid,
        ddof=ddof,
    )
    valid &= ~np.isnan(array) & ~np.isnan(deviations) & (deviations != 0)
    output = np.full(array.shape, np.nan, dtype=np.float64)
    np.divide(array - means, deviations, out=output, where=valid)
    return _checked_output(output, name="rolling_zscore")


def rolling_percentile(
    values: ArrayLike,
    *,
    window: int,
    min_periods: int | None = None,
    nan_policy: RollingNanPolicy = "raise",
) -> FloatArray:
    """Rank each observation against prior values using midpoint ties."""

    array = _rolling_array(values, nan_policy)
    required = _validate_window(window, min_periods)
    windows, expected_counts = _prior_windows(array, window)
    counts, valid = _window_validity(
        windows,
        expected_counts=expected_counts,
        required=required,
        nan_policy=nan_policy,
    )
    valid &= ~np.isnan(array)
    current = array[:, np.newaxis]
    less = np.sum(windows < current, axis=1, dtype=np.int64)
    equal = np.sum(windows == current, axis=1, dtype=np.int64)
    ranks = less.astype(np.float64) + np.float64(0.5) * equal
    output = np.full(array.shape, np.nan, dtype=np.float64)
    np.divide(
        ranks * np.float64(100),
        counts,
        out=output,
        where=valid,
    )
    return _checked_output(output, name="rolling_percentile")


def historical_normalize(
    values: ArrayLike,
    *,
    window: int,
    min_periods: int | None = None,
    lower: float = 0.0,
    upper: float = 100.0,
    nan_policy: RollingNanPolicy = "raise",
) -> FloatArray:
    """Normalize each value from prior-window extrema into `[lower, upper]`."""

    array = _rolling_array(values, nan_policy)
    required = _validate_window(window, min_periods)
    lower_value, upper_value = _validate_bounds(lower, upper)
    windows, expected_counts = _prior_windows(array, window)
    _, valid = _window_validity(
        windows,
        expected_counts=expected_counts,
        required=required,
        nan_policy=nan_policy,
    )
    finite = ~np.isnan(windows)
    historical_min = np.min(np.where(finite, windows, np.inf), axis=1)
    historical_max = np.max(np.where(finite, windows, -np.inf), axis=1)
    with np.errstate(over="ignore", invalid="ignore"):
        widths = historical_max - historical_min
    valid &= ~np.isnan(array) & (widths != 0)
    fractions = np.full(array.shape, np.nan, dtype=np.float64)
    np.divide(array - historical_min, widths, out=fractions, where=valid)
    np.clip(fractions, 0, 1, out=fractions)
    return _checked_output(
        np.asarray(
            lower_value + fractions * (upper_value - lower_value),
            dtype=np.float64,
        ),
        name="historical_normalize",
    )


def simple_returns(
    prices: ArrayLike,
    *,
    nan_policy: NanPolicy = "raise",
) -> FloatArray:
    """Return consecutive close-to-close returns without synthetic padding."""

    values = as_float64_vector(prices, allow_empty=True, nan_policy=nan_policy)
    finite = values[~np.isnan(values)]
    if np.any(finite <= 0):
        raise NumericInputError("return inputs must be strictly positive")
    if values.size < 2:
        return np.empty(0, dtype=np.float64)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        output = np.asarray(
            values[1:] / values[:-1] - np.float64(1),
            dtype=np.float64,
        )
    return _checked_output(output, name="simple_returns")


def true_range(
    high: ArrayLike,
    low: ArrayLike,
    close: ArrayLike,
    *,
    nan_policy: NanPolicy = "raise",
) -> FloatArray:
    """Return true ranges using the current high/low and previous close."""

    highs = as_float64_vector(high, allow_empty=True, nan_policy=nan_policy)
    lows = as_float64_vector(low, allow_empty=True, nan_policy=nan_policy)
    closes = as_float64_vector(close, allow_empty=True, nan_policy=nan_policy)
    require_same_shape(highs, lows, closes)
    comparable = ~np.isnan(highs) & ~np.isnan(lows)
    if np.any(highs[comparable] < lows[comparable]):
        raise NumericInputError(
            "high values must be greater than or equal to low values"
        )
    if highs.size == 0:
        return np.empty(0, dtype=np.float64)
    high_low = highs - lows
    previous_close = np.concatenate((np.asarray((np.nan,)), closes[:-1]))
    candidates = np.stack(
        (
            high_low,
            np.abs(highs - previous_close),
            np.abs(lows - previous_close),
        ),
        axis=0,
    )
    output = np.max(candidates, axis=0)
    output[0] = high_low[0]
    return _checked_output(np.asarray(output, dtype=np.float64), name="true_range")


def average_true_range(
    high: ArrayLike,
    low: ArrayLike,
    close: ArrayLike,
    *,
    window: int,
    min_periods: int | None = None,
    nan_policy: NanPolicy = "raise",
) -> FloatArray:
    """Return the trailing arithmetic mean of true range."""

    ranges = true_range(high, low, close, nan_policy=nan_policy)
    return rolling_mean(
        ranges,
        window=window,
        min_periods=min_periods,
        nan_policy=nan_policy,
    )


def realized_volatility(
    prices: ArrayLike,
    *,
    window: int,
    annualization_periods: int = 365,
    min_periods: int | None = None,
    sample: bool = False,
    nan_policy: NanPolicy = "raise",
) -> FloatArray:
    """Return annualized trailing volatility of simple close-to-close returns."""

    _validate_annualization_periods(annualization_periods)
    values = as_float64_vector(prices, allow_empty=True, nan_policy=nan_policy)
    if values.size == 0:
        _validate_window(window, min_periods)
        return np.empty(0, dtype=np.float64)
    returns = simple_returns(values, nan_policy=nan_policy)
    return_volatility = rolling_volatility(
        returns,
        window=window,
        min_periods=min_periods,
        sample=sample,
        nan_policy=nan_policy,
    )
    output = np.full(values.shape, np.nan, dtype=np.float64)
    output[1:] = return_volatility * np.sqrt(np.float64(annualization_periods))
    return _checked_output(output, name="realized_volatility")


def _checked_output(values: FloatArray, *, name: str) -> FloatArray:
    reject_infinite_result(values, name=name)
    return values


def _rolling_array(values: ArrayLike, nan_policy: RollingNanPolicy) -> FloatArray:
    if nan_policy not in ROLLING_NAN_POLICIES:
        raise NumericInputError(f"nan_policy must be one of {ROLLING_NAN_POLICIES}")
    boundary_policy: NanPolicy = "raise" if nan_policy == "raise" else "propagate"
    return as_float64_vector(
        values,
        allow_empty=True,
        nan_policy=boundary_policy,
    )


def _inclusive_windows(
    values: FloatArray, window: int
) -> tuple[FloatArray, FloatArray]:
    if values.size == 0:
        return np.empty((0, window), dtype=np.float64), np.empty(0, dtype=np.float64)
    padded = np.pad(values, (window - 1, 0), constant_values=np.nan)
    windows = sliding_window_view(padded, window)
    counts = np.minimum(np.arange(1, values.size + 1), window).astype(np.float64)
    return np.asarray(windows, dtype=np.float64), counts


def _prior_windows(values: FloatArray, window: int) -> tuple[FloatArray, FloatArray]:
    if values.size == 0:
        return np.empty((0, window), dtype=np.float64), np.empty(0, dtype=np.float64)
    padded = np.pad(values, (window, 0), constant_values=np.nan)
    windows = sliding_window_view(padded, window)[: values.size]
    counts = np.minimum(np.arange(values.size), window).astype(np.float64)
    return np.asarray(windows, dtype=np.float64), counts


def _window_validity(
    windows: FloatArray,
    *,
    expected_counts: FloatArray,
    required: int,
    nan_policy: RollingNanPolicy,
) -> tuple[FloatArray, np.ndarray]:
    counts = np.sum(~np.isnan(windows), axis=1, dtype=np.int64).astype(np.float64)
    valid = counts >= required
    if nan_policy == "propagate":
        valid &= counts == expected_counts
    return counts, valid


def _window_means(
    windows: FloatArray,
    *,
    counts: FloatArray,
    valid: np.ndarray,
) -> FloatArray:
    with np.errstate(over="ignore", invalid="ignore"):
        sums = np.sum(
            np.where(np.isnan(windows), 0, windows),
            axis=1,
            dtype=np.float64,
        )
    output = np.full(counts.shape, np.nan, dtype=np.float64)
    np.divide(sums, counts, out=output, where=valid)
    return output


def _window_standard_deviations(
    windows: FloatArray,
    *,
    counts: FloatArray,
    valid: np.ndarray,
    ddof: int,
) -> FloatArray:
    means = _window_means(windows, counts=counts, valid=counts > 0)
    with np.errstate(over="ignore", invalid="ignore"):
        centered = np.where(np.isnan(windows), 0, windows - means[:, np.newaxis])
        sums_of_squares = np.sum(centered * centered, axis=1, dtype=np.float64)
    output = np.full(counts.shape, np.nan, dtype=np.float64)
    np.divide(sums_of_squares, counts - ddof, out=output, where=valid)
    np.sqrt(output, out=output)
    return output


def _validate_window(window: int, min_periods: int | None) -> int:
    if isinstance(window, bool) or not isinstance(window, int) or window < 1:
        raise NumericInputError("window must be an integer >= 1")
    required = window if min_periods is None else min_periods
    if isinstance(required, bool) or not isinstance(required, int) or required < 1:
        raise NumericInputError("min_periods must be an integer >= 1")
    if required > window:
        raise NumericInputError("min_periods must be <= window")
    return required


def _sample_ddof(sample: bool) -> int:
    if not isinstance(sample, bool):
        raise NumericInputError("sample must be boolean")
    return 1 if sample else 0


def _validate_bounds(lower: float, upper: float) -> tuple[np.float64, np.float64]:
    if isinstance(lower, bool) or isinstance(upper, bool):
        raise NumericInputError("normalization bounds must not be boolean")
    try:
        bounds = np.asarray((lower, upper), dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise NumericInputError(
            "normalization bounds must be float64 values"
        ) from error
    if not np.all(np.isfinite(bounds)):
        raise NumericInputError("normalization bounds must be finite")
    if bounds[1] <= bounds[0]:
        raise NumericInputError("upper must be greater than lower")
    return np.float64(bounds[0]), np.float64(bounds[1])


def _validate_annualization_periods(annualization_periods: int) -> None:
    if (
        isinstance(annualization_periods, bool)
        or not isinstance(annualization_periods, int)
        or annualization_periods < 1
    ):
        raise NumericInputError("annualization_periods must be an integer >= 1")
