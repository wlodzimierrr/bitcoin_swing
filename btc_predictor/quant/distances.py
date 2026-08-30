"""Price-distance and volatility-normalized distance kernels."""

from __future__ import annotations

from typing import Literal, TypeAlias

import numpy as np
from numpy.typing import ArrayLike

from btc_predictor.quant.arrays import (
    FloatArray,
    NanPolicy,
    NumericInputError,
    as_float64_array,
    as_float64_vector,
)


DistanceInput: TypeAlias = float | ArrayLike
DistanceOutput: TypeAlias = float | FloatArray
ClusterDistanceMode: TypeAlias = Literal["absolute", "static", "fractional", "atr"]
CLUSTER_DISTANCE_MODES = ("absolute", "static", "fractional", "atr")


def pairwise_price_distance(
    first: DistanceInput,
    second: DistanceInput,
    *,
    nan_policy: NanPolicy = "raise",
) -> DistanceOutput:
    """Return absolute elementwise distances with explicit scalar expansion."""

    left, right, scalar = _aligned_inputs(first, second, nan_policy=nan_policy)
    _validate_prices(left, name="first")
    _validate_prices(right, name="second")
    return _restore_output(np.abs(left - right), scalar=scalar)


def atr_normalized_distance(
    first: DistanceInput,
    second: DistanceInput,
    atr: DistanceInput | None,
    *,
    nan_policy: NanPolicy = "raise",
) -> DistanceOutput:
    """Return absolute price distance measured in ATR units."""

    if atr is None:
        raise NumericInputError("atr is required for ATR-normalized distance")
    left, right, scalar = _aligned_inputs(first, second, nan_policy=nan_policy)
    _validate_prices(left, name="first")
    _validate_prices(right, name="second")
    atr_values = _aligned_atr(atr, shape=left.shape, nan_policy=nan_policy)
    result = np.abs(left - right) / atr_values
    return _restore_output(result, scalar=scalar)


def distance_to_support(
    prices: DistanceInput,
    support_levels: ArrayLike,
    *,
    atr: DistanceInput | None = None,
    nan_policy: NanPolicy = "raise",
) -> DistanceOutput:
    """Return distance to the nearest support at or below each price."""

    return _distance_to_directional_level(
        prices,
        support_levels,
        direction="support",
        atr=atr,
        nan_policy=nan_policy,
    )


def distance_to_resistance(
    prices: DistanceInput,
    resistance_levels: ArrayLike,
    *,
    atr: DistanceInput | None = None,
    nan_policy: NanPolicy = "raise",
) -> DistanceOutput:
    """Return distance to the nearest resistance at or above each price."""

    return _distance_to_directional_level(
        prices,
        resistance_levels,
        direction="resistance",
        atr=atr,
        nan_policy=nan_policy,
    )


def cluster_distance_matrix(
    prices: ArrayLike,
    *,
    mode: ClusterDistanceMode = "fractional",
    atr: float | None = None,
    nan_policy: NanPolicy = "raise",
) -> FloatArray:
    """Return a deterministic symmetric pairwise matrix for level clustering."""

    values = as_float64_vector(prices, allow_empty=True, nan_policy=nan_policy)
    _validate_prices(values, name="prices")
    _validate_cluster_mode(mode)
    distances = np.abs(np.subtract.outer(values, values))
    if mode == "fractional":
        distances = distances / np.minimum.outer(values, values)
    elif mode == "atr":
        if atr is None:
            raise NumericInputError("atr is required when mode is 'atr'")
        atr_value = _positive_scalar(atr, name="atr")
        distances = distances / atr_value
    elif atr is not None:
        raise NumericInputError("atr is only valid when mode is 'atr'")
    return np.array(distances, dtype=np.float64, order="C", copy=True)


def entry_distance_score(
    entry_prices: DistanceInput,
    support_prices: DistanceInput,
    *,
    full_score_distance: float,
    zero_score_distance: float,
    mode: ClusterDistanceMode = "fractional",
    atr: DistanceInput | None = None,
    nan_policy: NanPolicy = "raise",
) -> DistanceOutput:
    """Score long-entry proximity to support from 100 near support to zero far away."""

    entries, supports, scalar = _aligned_inputs(
        entry_prices,
        support_prices,
        nan_policy=nan_policy,
    )
    _validate_prices(entries, name="entry_prices")
    _validate_prices(supports, name="support_prices")
    _validate_cluster_mode(mode)
    full_distance = _non_negative_scalar(
        full_score_distance,
        name="full_score_distance",
    )
    zero_distance = _positive_scalar(
        zero_score_distance,
        name="zero_score_distance",
    )
    if zero_distance <= full_distance:
        raise NumericInputError("zero_score_distance must be greater than full_score_distance")

    distances = np.maximum(entries - supports, np.float64(0))
    if mode == "fractional":
        distances = distances / entries
    elif mode == "atr":
        if atr is None:
            raise NumericInputError("atr is required when mode is 'atr'")
        distances = distances / _aligned_atr(
            atr,
            shape=entries.shape,
            nan_policy=nan_policy,
        )
    elif atr is not None:
        raise NumericInputError("atr is only valid when mode is 'atr'")

    position = (distances - full_distance) / (zero_distance - full_distance)
    scores = np.float64(100) * (np.float64(1) - np.clip(position, 0, 1))
    return _restore_output(scores, scalar=scalar)


def _distance_to_directional_level(
    prices: DistanceInput,
    levels: ArrayLike,
    *,
    direction: Literal["support", "resistance"],
    atr: DistanceInput | None,
    nan_policy: NanPolicy,
) -> DistanceOutput:
    price_values, scalar = _coerce_input(prices, nan_policy=nan_policy)
    level_values = as_float64_vector(levels, allow_empty=True, nan_policy=nan_policy)
    _validate_prices(price_values, name="prices")
    _validate_prices(level_values, name="levels")
    if level_values.size == 0 or np.any(np.isnan(level_values)):
        result = np.full(price_values.shape, np.nan, dtype=np.float64)
    else:
        flat_prices = price_values.reshape(-1)
        if direction == "support":
            candidates = flat_prices[:, np.newaxis] - level_values[np.newaxis, :]
        else:
            candidates = level_values[np.newaxis, :] - flat_prices[:, np.newaxis]
        valid = candidates >= 0
        nearest = np.min(np.where(valid, candidates, np.inf), axis=1)
        nearest[np.isinf(nearest)] = np.nan
        result = nearest.reshape(price_values.shape)
    if atr is not None:
        result = result / _aligned_atr(
            atr,
            shape=price_values.shape,
            nan_policy=nan_policy,
        )
    return _restore_output(result, scalar=scalar)


def _aligned_inputs(
    first: DistanceInput,
    second: DistanceInput,
    *,
    nan_policy: NanPolicy,
) -> tuple[FloatArray, FloatArray, bool]:
    left, left_scalar = _coerce_input(first, nan_policy=nan_policy)
    right, right_scalar = _coerce_input(second, nan_policy=nan_policy)
    scalar = left_scalar and right_scalar
    if left_scalar and not right_scalar:
        left = np.full(right.shape, left[0], dtype=np.float64)
    elif right_scalar and not left_scalar:
        right = np.full(left.shape, right[0], dtype=np.float64)
    elif left.shape != right.shape:
        raise NumericInputError(
            "distance arrays must have identical shapes; only scalar expansion is supported"
        )
    return left, right, scalar


def _aligned_atr(
    atr: DistanceInput,
    *,
    shape: tuple[int, ...],
    nan_policy: NanPolicy,
) -> FloatArray:
    values, scalar = _coerce_input(atr, nan_policy=nan_policy)
    if scalar:
        values = np.full(shape, values[0], dtype=np.float64)
    elif values.shape != shape:
        raise NumericInputError(
            "atr must be scalar or have the same shape as the distance inputs"
        )
    finite = values[~np.isnan(values)]
    if np.any(finite <= 0):
        raise NumericInputError("atr must be strictly positive")
    return values


def _coerce_input(
    values: DistanceInput,
    *,
    nan_policy: NanPolicy,
) -> tuple[FloatArray, bool]:
    try:
        candidate = np.asarray(values)
    except (TypeError, ValueError, OverflowError) as error:
        raise NumericInputError("values must form a regular numeric array") from error
    scalar = candidate.ndim == 0
    prepared = [values] if scalar else values
    array = as_float64_array(
        prepared,
        allow_empty=True,
        nan_policy=nan_policy,
    )
    return array, scalar


def _validate_prices(values: FloatArray, *, name: str) -> None:
    finite = values[~np.isnan(values)]
    if np.any(finite <= 0):
        raise NumericInputError(f"{name} must contain strictly positive prices")


def _validate_cluster_mode(mode: ClusterDistanceMode) -> None:
    if mode not in CLUSTER_DISTANCE_MODES:
        raise NumericInputError(f"mode must be one of {CLUSTER_DISTANCE_MODES}")


def _finite_scalar(value: float, *, name: str) -> np.float64:
    if isinstance(value, (bool, np.bool_)):
        raise NumericInputError(f"{name} must not be boolean")
    try:
        candidate = np.asarray(value)
        result = np.float64(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise NumericInputError(f"{name} must be a finite float64 scalar") from error
    if (
        candidate.ndim != 0
        or np.iscomplexobj(candidate)
        or candidate.dtype.kind in ("S", "U")
        or not np.isfinite(result)
    ):
        raise NumericInputError(f"{name} must be a finite float64 scalar")
    return result


def _positive_scalar(value: float, *, name: str) -> np.float64:
    result = _finite_scalar(value, name=name)
    if result <= 0:
        raise NumericInputError(f"{name} must be positive")
    return result


def _non_negative_scalar(value: float, *, name: str) -> np.float64:
    result = _finite_scalar(value, name=name)
    if result < 0:
        raise NumericInputError(f"{name} must be non-negative")
    return result


def _restore_output(values: ArrayLike, *, scalar: bool) -> DistanceOutput:
    array = np.array(values, dtype=np.float64, order="C", copy=True)
    return float(array[0]) if scalar else array
