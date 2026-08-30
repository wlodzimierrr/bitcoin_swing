"""Explicitly seeded deterministic simulation primitives."""

from __future__ import annotations

import numpy as np

from btc_predictor.quant.arrays import (
    FloatArray,
    NumericInputError,
    reject_non_finite_result,
)


def normal_samples(
    shape: int | tuple[int, ...],
    *,
    seed: int,
    mean: float = 0.0,
    standard_deviation: float = 1.0,
) -> FloatArray:
    """Draw float64 normal samples from an explicitly seeded PCG64 stream."""

    normalized_shape = _validated_shape(shape)
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise NumericInputError("seed must be a non-negative integer")
    if isinstance(mean, bool) or isinstance(standard_deviation, bool):
        raise NumericInputError("simulation parameters must not be boolean")
    try:
        parameters = np.asarray((mean, standard_deviation), dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise NumericInputError("simulation parameters must be float64 values") from error
    if not np.all(np.isfinite(parameters)):
        raise NumericInputError("simulation parameters must be finite")
    if parameters[1] < 0:
        raise NumericInputError("standard_deviation must be non-negative")
    generator = np.random.Generator(np.random.PCG64(seed))
    with np.errstate(over="ignore", invalid="ignore"):
        result = np.asarray(
            generator.normal(parameters[0], parameters[1], size=normalized_shape),
            dtype=np.float64,
        )
    reject_non_finite_result(result, name="normal_samples")
    return result


def _validated_shape(shape: int | tuple[int, ...]) -> tuple[int, ...]:
    dimensions = (shape,) if isinstance(shape, int) and not isinstance(shape, bool) else shape
    if not isinstance(dimensions, tuple) or not dimensions:
        raise NumericInputError("simulation shape must contain at least one dimension")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 1
        for value in dimensions
    ):
        raise NumericInputError("simulation dimensions must be positive integers")
    return dimensions
