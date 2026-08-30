"""Named vectorized weighted scoring with explicit missing-input masks."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TypeAlias

import numpy as np
from numpy.typing import ArrayLike, NDArray

from btc_predictor.quant.arrays import (
    FloatArray,
    NumericInputError,
    as_float64_array,
    as_float64_vector,
    reject_infinite_result,
    stable_row_sum,
)

WeightInput: TypeAlias = Mapping[str, float] | ArrayLike
ScoreOutput: TypeAlias = float | FloatArray
CompleteOutput: TypeAlias = bool | NDArray[np.bool_]


@dataclass(frozen=True)
class WeightedScoreResult:
    """Numerical score output aligned to an immutable component-name order."""

    component_names: tuple[str, ...]
    weights: FloatArray
    scores: ScoreOutput
    contributions: FloatArray
    missing_mask: NDArray[np.bool_]
    complete_mask: CompleteOutput
    single_row: bool


def weighted_score(
    values: ArrayLike,
    weights: WeightInput,
    *,
    component_names: Sequence[str] | None = None,
    expected_weight_total: float | None = 1.0,
    weight_tolerance: float = 1e-6,
) -> WeightedScoreResult:
    """Calculate ``S = Xw`` without replacing missing components with zero."""

    matrix, single_row = _observation_matrix(values)
    names, weight_values = _named_weights(weights, component_names=component_names)
    if matrix.shape[1] != weight_values.size:
        raise NumericInputError(
            "observation component count must match the number of weights"
        )
    _validate_weight_policy(
        weight_values,
        expected_total=expected_weight_total,
        tolerance=weight_tolerance,
    )

    missing = np.isnan(matrix)
    with np.errstate(over="ignore", invalid="ignore"):
        contributions = np.asarray(matrix * weight_values, dtype=np.float64)
    reject_infinite_result(contributions, name="score_contributions")
    score_values = stable_row_sum(
        contributions,
        nan_policy="propagate",
        name="weighted_scores",
    )
    scores = np.asarray(score_values, dtype=np.float64)
    complete = np.asarray(~np.any(missing, axis=1), dtype=np.bool_)
    if single_row:
        score_output: ScoreOutput = float(scores[0])
        contribution_output = np.array(
            contributions[0],
            dtype=np.float64,
            order="C",
            copy=True,
        )
        missing_output = np.array(missing[0], dtype=np.bool_, order="C", copy=True)
        complete_output: CompleteOutput = bool(complete[0])
    else:
        score_output = np.array(scores, dtype=np.float64, order="C", copy=True)
        contribution_output = np.array(
            contributions,
            dtype=np.float64,
            order="C",
            copy=True,
        )
        missing_output = np.array(missing, dtype=np.bool_, order="C", copy=True)
        complete_output = np.array(complete, dtype=np.bool_, order="C", copy=True)
    return WeightedScoreResult(
        component_names=names,
        weights=np.array(weight_values, dtype=np.float64, order="C", copy=True),
        scores=score_output,
        contributions=contribution_output,
        missing_mask=missing_output,
        complete_mask=complete_output,
        single_row=single_row,
    )


def _observation_matrix(values: ArrayLike) -> tuple[FloatArray, bool]:
    array = as_float64_array(values, allow_empty=True, nan_policy="propagate")
    if array.ndim == 1:
        if array.size == 0:
            raise NumericInputError(
                "an observation row must contain at least one component"
            )
        return array[np.newaxis, :], True
    if array.ndim != 2:
        raise NumericInputError(
            "score observations must be a one-dimensional row or matrix"
        )
    if array.shape[1] == 0:
        raise NumericInputError(
            "score observations must contain at least one component"
        )
    return array, False


def _named_weights(
    weights: WeightInput,
    *,
    component_names: Sequence[str] | None,
) -> tuple[tuple[str, ...], FloatArray]:
    if isinstance(weights, Mapping):
        mapping_names = _component_names(tuple(weights))
        names = (
            mapping_names
            if component_names is None
            else _component_names(component_names)
        )
        missing = set(names) - set(mapping_names)
        extra = set(mapping_names) - set(names)
        if missing or extra:
            raise NumericInputError(
                "weight names must exactly match component_names; "
                f"missing={sorted(missing)}, extra={sorted(extra)}"
            )
        ordered = [weights[name] for name in names]
        return names, as_float64_vector(ordered)

    if component_names is None:
        raise NumericInputError("component_names are required for array weights")
    names = _component_names(component_names)
    weight_values = as_float64_vector(weights)
    if weight_values.size != len(names):
        raise NumericInputError(
            "component_names count must match the number of weights"
        )
    return names, weight_values


def _component_names(names: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(names)
    if not normalized:
        raise NumericInputError("component_names must not be empty")
    if any(not isinstance(name, str) or not name.strip() for name in normalized):
        raise NumericInputError("component names must be non-empty strings")
    if len(set(normalized)) != len(normalized):
        raise NumericInputError("component names must be unique")
    return normalized


def _validate_weight_policy(
    weights: FloatArray,
    *,
    expected_total: float | None,
    tolerance: float,
) -> None:
    if np.any(weights < 0):
        raise NumericInputError("weights must be non-negative")
    total = stable_row_sum(weights, name="weights")
    assert isinstance(total, float)
    if total <= 0:
        raise NumericInputError("weights must have a positive total")
    tolerance_value = _non_negative_scalar(tolerance, name="weight_tolerance")
    if expected_total is None:
        return
    expected = _positive_scalar(expected_total, name="expected_weight_total")
    if not np.isclose(total, expected, rtol=0, atol=tolerance_value):
        raise NumericInputError(
            f"weights must sum to {float(expected)} within {float(tolerance_value)}"
        )


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
