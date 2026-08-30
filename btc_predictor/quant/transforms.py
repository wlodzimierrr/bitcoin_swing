"""Deterministic nonlinear transforms for domain feature engines."""

from __future__ import annotations

from typing import Literal, TypeAlias

import numpy as np
from numpy.typing import ArrayLike
from scipy.special import expit, ndtr

from btc_predictor.quant.arrays import (
    FloatArray,
    NanPolicy,
    NumericInputError,
    as_float64_array,
    reject_infinite_result,
)

TransformInput: TypeAlias = float | ArrayLike
TransformOutput: TypeAlias = float | FloatArray
PenaltyDirection: TypeAlias = Literal["above", "below"]
PENALTY_DIRECTIONS = ("above", "below")


def gaussian_health(
    values: TransformInput,
    *,
    preferred: float = 0.0,
    width: float = 1.0,
    maximum: float = 100.0,
    nan_policy: NanPolicy = "raise",
) -> TransformOutput:
    """Map distance from a preferred value to a Gaussian-shaped score."""

    array, scalar = _coerce_input(values, nan_policy=nan_policy)
    center = _finite_scalar(preferred, name="preferred")
    scale = _positive_scalar(width, name="width")
    peak = _non_negative_scalar(maximum, name="maximum")
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        distance = (
            array.astype(np.longdouble) - np.longdouble(center)
        ) / np.longdouble(scale)
        magnitude = np.abs(distance)
        decay = np.zeros(array.shape, dtype=np.longdouble)
        moderate = magnitude <= np.longdouble(40)
        decay[moderate] = np.exp(
            -np.longdouble("0.5") * np.square(distance[moderate])
        )
        decay[np.isnan(distance)] = np.nan
        result = np.asarray(np.longdouble(peak) * decay, dtype=np.float64)
    return _restore_output(
        result,
        scalar=scalar,
        expected_nan=np.isnan(array),
    )


def sigmoid(
    values: TransformInput,
    *,
    midpoint: float = 0.0,
    steepness: float = 1.0,
    lower: float = 0.0,
    upper: float = 1.0,
    nan_policy: NanPolicy = "raise",
) -> TransformOutput:
    """Apply a numerically stable logistic transform between fixed bounds."""

    array, scalar = _coerce_input(values, nan_policy=nan_policy)
    center = _finite_scalar(midpoint, name="midpoint")
    slope = _non_zero_scalar(steepness, name="steepness")
    floor, ceiling = _ordered_bounds(lower, upper, names=("lower", "upper"))
    with np.errstate(over="ignore", invalid="ignore"):
        argument = np.longdouble(slope) * (
            array.astype(np.longdouble) - np.longdouble(center)
        )
        probabilities = expit(
            np.asarray(
                np.clip(argument, -np.finfo(np.float64).max, np.finfo(np.float64).max),
                dtype=np.float64,
            )
        )
        result = _stable_interpolate(floor, ceiling, probabilities)
    return _restore_output(
        result,
        scalar=scalar,
        expected_nan=np.isnan(array),
    )


def normal_cdf_score(
    values: TransformInput,
    *,
    mean: float = 0.0,
    standard_deviation: float = 1.0,
    minimum: float = 0.0,
    maximum: float = 100.0,
    nan_policy: NanPolicy = "raise",
) -> TransformOutput:
    """Convert values through a normal CDF and scale them to score bounds."""

    array, scalar = _coerce_input(values, nan_policy=nan_policy)
    center = _finite_scalar(mean, name="mean")
    scale = _positive_scalar(standard_deviation, name="standard_deviation")
    floor, ceiling = _ordered_bounds(
        minimum,
        maximum,
        names=("minimum", "maximum"),
    )
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        standardized = (
            array.astype(np.longdouble) - np.longdouble(center)
        ) / np.longdouble(scale)
        probabilities = ndtr(
            np.asarray(
                np.clip(
                    standardized,
                    -np.finfo(np.float64).max,
                    np.finfo(np.float64).max,
                ),
                dtype=np.float64,
            )
        )
        result = _stable_interpolate(floor, ceiling, probabilities)
    return _restore_output(
        result,
        scalar=scalar,
        expected_nan=np.isnan(array),
    )


def bounded_linear(
    values: TransformInput,
    *,
    input_minimum: float,
    input_maximum: float,
    output_minimum: float = 0.0,
    output_maximum: float = 100.0,
    clip: bool = True,
    nan_policy: NanPolicy = "raise",
) -> TransformOutput:
    """Linearly map one ordered interval to another, optionally clipping."""

    array, scalar = _coerce_input(values, nan_policy=nan_policy)
    source_min, source_max = _ordered_bounds(
        input_minimum,
        input_maximum,
        names=("input_minimum", "input_maximum"),
    )
    target_min, target_max = _ordered_bounds(
        output_minimum,
        output_maximum,
        names=("output_minimum", "output_maximum"),
    )
    _require_bool(clip, name="clip")
    position = _stable_interval_position(array, source_min, source_max)
    if clip:
        position = np.clip(position, np.float64(0), np.float64(1))
    result = _stable_interpolate(target_min, target_max, position)
    return _restore_output(
        result,
        scalar=scalar,
        expected_nan=np.isnan(array),
    )


def smooth_penalty(
    values: TransformInput,
    *,
    threshold: float,
    width: float,
    maximum: float = 100.0,
    direction: PenaltyDirection = "above",
    nan_policy: NanPolicy = "raise",
) -> TransformOutput:
    """Ramp from zero to a maximum penalty using cubic smoothstep."""

    array, scalar = _coerce_input(values, nan_policy=nan_policy)
    onset = _finite_scalar(threshold, name="threshold")
    transition = _positive_scalar(width, name="width")
    peak = _non_negative_scalar(maximum, name="maximum")
    if direction not in PENALTY_DIRECTIONS:
        raise NumericInputError(f"direction must be one of {PENALTY_DIRECTIONS}")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        values_long = array.astype(np.longdouble)
        distance = (
            values_long - np.longdouble(onset)
            if direction == "above"
            else np.longdouble(onset) - values_long
        )
        position = np.asarray(
            np.clip(distance / np.longdouble(transition), 0, 1),
            dtype=np.float64,
        )
        result = peak * np.square(position) * (
            np.float64(3) - np.float64(2) * position
        )
    return _restore_output(
        result,
        scalar=scalar,
        expected_nan=np.isnan(array),
    )


def exponential_decay(
    distances: TransformInput,
    *,
    initial: float = 1.0,
    decay_rate: float = 1.0,
    nan_policy: NanPolicy = "raise",
) -> TransformOutput:
    """Apply ``initial * exp(-decay_rate * distance)`` to non-negative distances."""

    array, scalar = _coerce_input(distances, nan_policy=nan_policy)
    start = _non_negative_scalar(initial, name="initial")
    rate = _non_negative_scalar(decay_rate, name="decay_rate")
    finite = array[~np.isnan(array)]
    if np.any(finite < 0):
        raise NumericInputError("distances must be non-negative")
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        exponent = np.longdouble(rate) * array.astype(np.longdouble)
        exponent = np.asarray(
            np.clip(exponent, 0, np.finfo(np.float64).max),
            dtype=np.float64,
        )
        result = start * np.exp(-exponent)
    return _restore_output(
        result,
        scalar=scalar,
        expected_nan=np.isnan(array),
    )


def clip_score(
    values: TransformInput,
    *,
    minimum: float = 0.0,
    maximum: float = 100.0,
    nan_policy: NanPolicy = "raise",
) -> TransformOutput:
    """Clip numeric scores to an explicit ordered interval."""

    array, scalar = _coerce_input(values, nan_policy=nan_policy)
    floor, ceiling = _ordered_bounds(
        minimum,
        maximum,
        names=("minimum", "maximum"),
    )
    result = np.clip(array, floor, ceiling)
    return _restore_output(
        result,
        scalar=scalar,
        expected_nan=np.isnan(array),
    )


def percentile_to_health(
    percentiles: TransformInput,
    *,
    higher_is_healthier: bool = False,
    nan_policy: NanPolicy = "raise",
) -> TransformOutput:
    """Map percentiles in [0, 100] to health scores in [0, 100]."""

    array, scalar = _coerce_input(percentiles, nan_policy=nan_policy)
    _require_bool(higher_is_healthier, name="higher_is_healthier")
    finite = array[~np.isnan(array)]
    if np.any((finite < 0) | (finite > 100)):
        raise NumericInputError("percentiles must be between 0 and 100")
    result = array if higher_is_healthier else np.float64(100) - array
    return _restore_output(
        result,
        scalar=scalar,
        expected_nan=np.isnan(array),
    )


def winsorize(
    values: TransformInput,
    *,
    lower_quantile: float = 0.05,
    upper_quantile: float = 0.95,
    nan_policy: NanPolicy = "raise",
) -> TransformOutput:
    """Clip values to deterministic linear-interpolation quantile bounds."""

    array, scalar = _coerce_input(values, nan_policy=nan_policy)
    if array.size == 0:
        raise NumericInputError("winsorize requires at least one observation")
    lower = _probability(lower_quantile, name="lower_quantile")
    upper = _probability(upper_quantile, name="upper_quantile")
    if lower > upper:
        raise NumericInputError("lower_quantile must be <= upper_quantile")
    if np.any(np.isnan(array)):
        result = np.full(array.shape, np.nan, dtype=np.float64)
    else:
        with np.errstate(over="ignore", invalid="ignore"):
            bounds = np.asarray(
                np.quantile(
                    array.astype(np.longdouble),
                    (lower, upper),
                    method="linear",
                ),
                dtype=np.float64,
            )
        result = np.clip(array, bounds[0], bounds[1])
    expected_nan = (
        np.ones(array.shape, dtype=np.bool_)
        if np.any(np.isnan(array))
        else np.zeros(array.shape, dtype=np.bool_)
    )
    return _restore_output(result, scalar=scalar, expected_nan=expected_nan)


def _coerce_input(
    values: TransformInput,
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


def _restore_output(
    values: ArrayLike,
    *,
    scalar: bool,
    expected_nan: np.ndarray,
) -> TransformOutput:
    with np.errstate(over="ignore", invalid="ignore"):
        array = np.array(values, dtype=np.float64, order="C", copy=True)
    reject_infinite_result(array, name="transform_result")
    if expected_nan.shape != array.shape:
        raise NumericInputError("transform NaN expectation shape mismatch")
    if np.any(np.isnan(array) & ~expected_nan):
        raise NumericInputError("transform_result produced an unexpected NaN")
    return float(array[0]) if scalar else array


def _stable_interval_position(
    values: FloatArray,
    lower: np.float64,
    upper: np.float64,
) -> FloatArray:
    scale = np.longdouble(max(abs(lower), abs(upper)))
    if scale == 0:
        raise NumericInputError("interval scale must be non-zero")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        lower_scaled = np.longdouble(lower) / scale
        upper_scaled = np.longdouble(upper) / scale
        values_scaled = values.astype(np.longdouble) / scale
        position = (values_scaled - lower_scaled) / (
            upper_scaled - lower_scaled
        )
        return np.asarray(position, dtype=np.float64)


def _stable_interpolate(
    lower: np.float64,
    upper: np.float64,
    positions: ArrayLike,
) -> FloatArray:
    values = np.asarray(positions, dtype=np.longdouble)
    with np.errstate(over="ignore", invalid="ignore"):
        result = (
            (np.longdouble(1) - values) * np.longdouble(lower)
            + values * np.longdouble(upper)
        )
        return np.asarray(result, dtype=np.float64)


def _finite_scalar(value: float, *, name: str) -> np.float64:
    if isinstance(value, (bool, np.bool_)):
        raise NumericInputError(f"{name} must not be boolean")
    try:
        candidate = np.asarray(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise NumericInputError(f"{name} must be a finite float64 scalar") from error
    if (
        candidate.ndim != 0
        or np.iscomplexobj(candidate)
        or candidate.dtype.kind in ("S", "U")
    ):
        raise NumericInputError(f"{name} must be a finite float64 scalar")
    try:
        result = np.float64(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise NumericInputError(f"{name} must be a finite float64 scalar") from error
    if not np.isfinite(result):
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


def _non_zero_scalar(value: float, *, name: str) -> np.float64:
    result = _finite_scalar(value, name=name)
    if result == 0:
        raise NumericInputError(f"{name} must be non-zero")
    return result


def _ordered_bounds(
    lower: float,
    upper: float,
    *,
    names: tuple[str, str],
) -> tuple[np.float64, np.float64]:
    floor = _finite_scalar(lower, name=names[0])
    ceiling = _finite_scalar(upper, name=names[1])
    if ceiling <= floor:
        raise NumericInputError(f"{names[1]} must be greater than {names[0]}")
    return floor, ceiling


def _probability(value: float, *, name: str) -> np.float64:
    result = _finite_scalar(value, name=name)
    if result < 0 or result > 1:
        raise NumericInputError(f"{name} must be between 0 and 1")
    return result


def _require_bool(value: bool, *, name: str) -> None:
    if not isinstance(value, (bool, np.bool_)):
        raise NumericInputError(f"{name} must be boolean")
