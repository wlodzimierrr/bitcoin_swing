"""Array coercion and validation for the quantitative core."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

import numpy as np
from numpy.typing import ArrayLike, NDArray


FloatArray: TypeAlias = NDArray[np.float64]
NanPolicy: TypeAlias = Literal["raise", "propagate"]
NAN_POLICIES = ("raise", "propagate")
FLOAT_DTYPE = np.dtype(np.float64)
QUANT_POLICY_VERSION = "FLOAT64_V1"


class NumericInputError(ValueError):
    """Raised when a value violates the frozen quantitative input policy."""


@dataclass(frozen=True)
class NumericTolerance:
    """Absolute and relative tolerances used for numeric boundary checks."""

    absolute: float = 1e-12
    relative: float = 1e-12

    def __post_init__(self) -> None:
        if isinstance(self.absolute, bool) or isinstance(self.relative, bool):
            raise NumericInputError("numeric tolerances must not be boolean")
        try:
            values = np.asarray((self.absolute, self.relative), dtype=np.float64)
        except (TypeError, ValueError, OverflowError) as error:
            raise NumericInputError("numeric tolerances must be float64 values") from error
        if not np.all(np.isfinite(values)) or np.any(values < 0):
            raise NumericInputError("numeric tolerances must be finite and non-negative")
        object.__setattr__(self, "absolute", float(values[0]))
        object.__setattr__(self, "relative", float(values[1]))


DEFAULT_TOLERANCE = NumericTolerance()


def as_float64_array(
    values: ArrayLike,
    *,
    ndim: int | None = None,
    allow_empty: bool = False,
    nan_policy: NanPolicy = "raise",
) -> FloatArray:
    """Return an owned C-contiguous float64 array after policy validation."""

    _validate_nan_policy(nan_policy)
    try:
        candidate = np.asarray(values)
    except (TypeError, ValueError, OverflowError) as error:
        raise NumericInputError("values must form a regular numeric array") from error
    if np.iscomplexobj(candidate):
        raise NumericInputError("complex numeric inputs are not supported")
    if candidate.dtype.kind == "b":
        raise NumericInputError("boolean arrays are not numeric observations")
    if candidate.dtype.kind in ("S", "U"):
        raise NumericInputError("string arrays are not numeric observations")
    try:
        array = np.asarray(values, dtype=np.float64, order="C")
    except (TypeError, ValueError, OverflowError) as error:
        raise NumericInputError("values must be coercible to float64") from error
    if ndim is not None and array.ndim != ndim:
        raise NumericInputError(f"array must have exactly {ndim} dimensions")
    if not allow_empty and array.size == 0:
        raise NumericInputError("array must contain at least one observation")
    if np.any(np.isinf(array)):
        raise NumericInputError("infinite numeric inputs are never permitted")
    if nan_policy == "raise" and np.any(np.isnan(array)):
        raise NumericInputError("NaN input requires an explicit propagation policy")
    return np.array(array, dtype=np.float64, order="C", copy=True)


def as_float64_vector(
    values: ArrayLike,
    *,
    allow_empty: bool = False,
    nan_policy: NanPolicy = "raise",
) -> FloatArray:
    """Return a validated one-dimensional float64 array."""

    return as_float64_array(
        values,
        ndim=1,
        allow_empty=allow_empty,
        nan_policy=nan_policy,
    )


def as_float64_matrix(
    values: ArrayLike,
    *,
    allow_empty: bool = False,
    nan_policy: NanPolicy = "raise",
) -> FloatArray:
    """Return a validated two-dimensional float64 array."""

    return as_float64_array(
        values,
        ndim=2,
        allow_empty=allow_empty,
        nan_policy=nan_policy,
    )


def require_same_shape(*arrays: FloatArray) -> tuple[int, ...]:
    """Require exact shape equality; quantitative helpers do not broadcast."""

    if not arrays:
        raise NumericInputError("at least one array is required")
    shape = arrays[0].shape
    if any(array.shape != shape for array in arrays[1:]):
        raise NumericInputError("arrays must have identical shapes; broadcasting is disabled")
    return shape


def require_probability(value: float, *, name: str = "probability") -> np.float64:
    """Return a finite probability in the closed interval [0, 1]."""

    if isinstance(value, (bool, np.bool_)):
        raise NumericInputError(f"{name} must not be boolean")
    try:
        probability = np.float64(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise NumericInputError(f"{name} must be a float64 value") from error
    if not np.isfinite(probability) or not 0 <= probability <= 1:
        raise NumericInputError(f"{name} must be finite and between 0 and 1")
    return probability


def is_effectively_zero(
    values: ArrayLike,
    *,
    tolerance: NumericTolerance = DEFAULT_TOLERANCE,
) -> NDArray[np.bool_]:
    """Return a mask using the frozen absolute and relative tolerances."""

    array = as_float64_array(values)
    return np.isclose(
        array,
        np.float64(0),
        atol=tolerance.absolute,
        rtol=tolerance.relative,
    )


def _validate_nan_policy(nan_policy: NanPolicy) -> None:
    if nan_policy not in NAN_POLICIES:
        raise NumericInputError(f"nan_policy must be one of {NAN_POLICIES}")
