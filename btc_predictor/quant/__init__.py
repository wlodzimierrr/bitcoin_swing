"""Typed NumPy/SciPy quantitative-core conventions."""

from btc_predictor.quant.arrays import (
    DEFAULT_TOLERANCE,
    FLOAT_DTYPE,
    NAN_POLICIES,
    QUANT_POLICY_VERSION,
    FloatArray,
    NanPolicy,
    NumericInputError,
    NumericTolerance,
    as_float64_array,
    as_float64_matrix,
    as_float64_vector,
    is_effectively_zero,
    require_probability,
    require_same_shape,
)
from btc_predictor.quant.simulation import normal_samples


__all__ = [
    "DEFAULT_TOLERANCE",
    "FLOAT_DTYPE",
    "NAN_POLICIES",
    "QUANT_POLICY_VERSION",
    "FloatArray",
    "NanPolicy",
    "NumericInputError",
    "NumericTolerance",
    "as_float64_array",
    "as_float64_matrix",
    "as_float64_vector",
    "is_effectively_zero",
    "normal_samples",
    "require_probability",
    "require_same_shape",
]
