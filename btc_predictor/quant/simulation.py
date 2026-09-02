"""Explicitly seeded deterministic simulation primitives."""

from __future__ import annotations

import numpy as np

from btc_predictor.quant.arrays import (
    FloatArray,
    IntArray,
    NumericInputError,
    reject_non_finite_result,
)


UNIFORM_INDEX_POLICY_VERSION = "PCG64_RAW_REJECTION_UNIFORM_INDEX_V1"
PERMUTATION_INDEX_POLICY_VERSION = "PCG64_RAW_FISHER_YATES_PERMUTATION_V1"

_UINT64_RANGE = 1 << 64
_INT64_INDEX_BOUND = 1 << 63


def normal_samples(
    shape: int | tuple[int, ...],
    *,
    seed: int,
    mean: float = 0.0,
    standard_deviation: float = 1.0,
) -> FloatArray:
    """Draw float64 normal samples from an explicitly seeded PCG64 stream."""

    normalized_shape = _validated_shape(shape)
    validated_seed = _validated_seed(seed)
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
    generator = np.random.Generator(np.random.PCG64(validated_seed))
    with np.errstate(over="ignore", invalid="ignore"):
        result = np.asarray(
            generator.normal(parameters[0], parameters[1], size=normalized_shape),
            dtype=np.float64,
        )
    reject_non_finite_result(result, name="normal_samples")
    return result


def uniform_index_samples(
    shape: int | tuple[int, ...],
    *,
    seed: int,
    high: int,
) -> IntArray:
    """Draw uniform integers in ``[0, high)`` from a seeded PCG64 raw stream.

    Indices come from the raw 64-bit PCG64 words with modulo rejection rather
    than from a ``Generator`` convenience method.  The bit-generator stream is
    stable across NumPy versions, while the bounded-integer algorithm layered
    on top of it is not guaranteed to be, and a persisted seeded research
    result must replay identically on a later NumPy.
    """

    normalized_shape = _validated_shape(shape)
    validated_seed = _validated_seed(seed)
    bound = _validated_bound(high)
    total = 1
    for dimension in normalized_shape:
        total *= dimension
    drawn = _bounded_draw(np.random.PCG64(validated_seed), total, bound)
    return drawn.reshape(normalized_shape)


def permutation_index_samples(
    count: int,
    *,
    seed: int,
    size: int,
) -> IntArray:
    """Draw ``count`` independent permutations of ``range(size)`` as rows.

    Fisher-Yates over the same seeded raw stream as
    :func:`uniform_index_samples`, so a resampling policy that reorders the
    observed sample without replacement replays exactly like one that draws
    with replacement.
    """

    rows = _validated_count(count, "count")
    width = _validated_count(size, "size")
    bit_generator = np.random.PCG64(_validated_seed(seed))
    matrix = np.tile(np.arange(width, dtype=np.int64), (rows, 1))
    positions = np.arange(rows)
    for index in range(width - 1, 0, -1):
        targets = _bounded_draw(bit_generator, rows, index + 1)
        selected = matrix[positions, targets].copy()
        matrix[positions, targets] = matrix[:, index]
        matrix[:, index] = selected
    return matrix


def _bounded_draw(
    bit_generator: np.random.PCG64,
    count: int,
    high: int,
) -> IntArray:
    """Return ``count`` unbiased integers in ``[0, high)`` from raw 64-bit words."""

    if count == 0:
        return np.empty(0, dtype=np.int64)
    # Words at or above the largest multiple of ``high`` would make the low
    # residues more likely than the high ones, so they are rejected and redrawn.
    limit = _UINT64_RANGE - (_UINT64_RANGE % high)
    unbiased = limit == _UINT64_RANGE
    drawn = np.empty(count, dtype=np.uint64)
    filled = 0
    while filled < count:
        raw = np.asarray(bit_generator.random_raw(count - filled), dtype=np.uint64)
        if not unbiased:
            raw = raw[raw < np.uint64(limit)]
        drawn[filled : filled + raw.size] = raw
        filled += int(raw.size)
    return (drawn % np.uint64(high)).astype(np.int64)


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


def _validated_seed(seed: int) -> int:
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise NumericInputError("seed must be a non-negative integer")
    return seed


def _validated_bound(high: int) -> int:
    if isinstance(high, bool) or not isinstance(high, int) or high < 1:
        raise NumericInputError("high must be a positive integer")
    if high > _INT64_INDEX_BOUND:
        raise NumericInputError("high must fit in the signed 64-bit index output")
    return high


def _validated_count(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise NumericInputError(f"{name} must be a positive integer")
    return value
