"""Vectorized position-risk mathematics for shared execution consumers."""

from __future__ import annotations

from typing import Literal, TypeAlias

import numpy as np
from numpy.typing import ArrayLike

from btc_predictor.quant.arrays import (
    FloatArray,
    NanPolicy,
    NumericInputError,
    as_float64_array,
    reject_infinite_result,
    stable_row_sum,
)

PositionSide: TypeAlias = Literal["long", "short"]
RiskInput: TypeAlias = float | ArrayLike
RiskOutput: TypeAlias = float | FloatArray
POSITION_SIDES = ("long", "short")


def stop_distance(
    entry_prices: RiskInput,
    stop_prices: RiskInput,
    *,
    side: PositionSide,
    nan_policy: NanPolicy = "raise",
) -> RiskOutput:
    """Return directional stop-loss distance as a non-negative entry fraction."""

    entries, stops, scalar = _aligned_inputs(
        entry_prices,
        stop_prices,
        nan_policy=nan_policy,
    )
    _validate_positive(entries, name="entry_prices")
    _validate_positive(stops, name="stop_prices")
    _validate_side(side)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        if side == "long":
            distances = (entries - stops) / entries
        else:
            distances = (stops - entries) / entries
        result = np.maximum(distances, np.float64(0))
    reject_infinite_result(result, name="stop_distance")
    return _restore_output(result, scalar=scalar)


def reward_risk_ratio(
    entry_prices: RiskInput,
    stop_prices: RiskInput,
    target_prices: RiskInput,
    *,
    side: PositionSide,
    nan_policy: NanPolicy = "raise",
) -> RiskOutput:
    """Return directional reward divided by risk, or NaN for invalid geometry."""

    entries, stops, targets, scalar = _aligned_inputs(
        entry_prices,
        stop_prices,
        target_prices,
        nan_policy=nan_policy,
    )
    _validate_positive(entries, name="entry_prices")
    _validate_positive(stops, name="stop_prices")
    _validate_positive(targets, name="target_prices")
    _validate_side(side)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        if side == "long":
            risk = entries - stops
            reward = targets - entries
        else:
            risk = stops - entries
            reward = entries - targets
        valid = (risk > 0) & (reward > 0)
        result = np.full(entries.shape, np.nan, dtype=np.float64)
        np.divide(reward, risk, out=result, where=valid)
    reject_infinite_result(result, name="reward_risk_ratio")
    return _restore_output(result, scalar=scalar)


def capital_at_risk(
    net_asset_values: RiskInput,
    risk_fractions: RiskInput,
    *,
    nan_policy: NanPolicy = "raise",
) -> RiskOutput:
    """Return capital risk budget as NAV multiplied by a fraction in [0, 1]."""

    nav, fractions, scalar = _aligned_inputs(
        net_asset_values,
        risk_fractions,
        nan_policy=nan_policy,
    )
    _validate_non_negative(nav, name="net_asset_values")
    _validate_fractions(fractions, name="risk_fractions")
    with np.errstate(over="ignore", invalid="ignore"):
        result = nav * fractions
    reject_infinite_result(result, name="capital_at_risk")
    return _restore_output(result, scalar=scalar)


def risk_contribution_by_tranche(
    notionals: RiskInput,
    entry_prices: RiskInput,
    stop_prices: RiskInput,
    *,
    side: PositionSide,
    nan_policy: NanPolicy = "raise",
) -> RiskOutput:
    """Return each tranche's non-negative loss contribution at its stop."""

    notional_values, entries, stops, scalar = _aligned_inputs(
        notionals,
        entry_prices,
        stop_prices,
        nan_policy=nan_policy,
    )
    _validate_non_negative(notional_values, name="notionals")
    _validate_positive(entries, name="entry_prices")
    _validate_positive(stops, name="stop_prices")
    _validate_side(side)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        if side == "long":
            loss_fractions = (entries - stops) / entries
        else:
            loss_fractions = (stops - entries) / entries
        contributions = notional_values * np.maximum(
            loss_fractions,
            np.float64(0),
        )
    reject_infinite_result(contributions, name="risk_contribution_by_tranche")
    return _restore_output(contributions, scalar=scalar)


def risk_at_stop(
    notionals: RiskInput,
    entry_prices: RiskInput,
    stop_prices: RiskInput,
    *,
    side: PositionSide,
    nan_policy: NanPolicy = "raise",
) -> RiskOutput:
    """Return total risk for one tranche vector or each row of a tranche matrix."""

    contributions = risk_contribution_by_tranche(
        notionals,
        entry_prices,
        stop_prices,
        side=side,
        nan_policy=nan_policy,
    )
    if isinstance(contributions, float):
        return contributions
    return stable_row_sum(
        contributions,
        nan_policy="propagate",
        name="risk_at_stop",
    )


def risk_improvement(
    current_risk: RiskInput,
    proposed_risk: RiskInput,
    *,
    nan_policy: NanPolicy = "raise",
) -> RiskOutput:
    """Return aggregate risk reduction for one portfolio or each matrix row."""

    current, proposed, _ = _aligned_inputs(
        current_risk,
        proposed_risk,
        nan_policy=nan_policy,
    )
    _validate_non_negative(current, name="current_risk")
    _validate_non_negative(proposed, name="proposed_risk")
    current_total = stable_row_sum(
        current,
        nan_policy="propagate",
        name="current_risk",
    )
    proposed_total = stable_row_sum(
        proposed,
        nan_policy="propagate",
        name="proposed_risk",
    )
    with np.errstate(over="ignore", invalid="ignore"):
        improvements = np.maximum(
            np.asarray(current_total) - np.asarray(proposed_total),
            np.float64(0),
        )
    reject_infinite_result(improvements, name="risk_improvement")
    if improvements.ndim == 0:
        return float(improvements)
    return np.array(improvements, dtype=np.float64, order="C", copy=True)


def max_allowed_notional(
    net_asset_values: RiskInput,
    risk_fractions: RiskInput,
    stop_distance_fractions: RiskInput,
    *,
    nan_policy: NanPolicy = "raise",
) -> RiskOutput:
    """Return maximum notional permitted by NAV risk budget and stop distance."""

    nav, fractions, distances, scalar = _aligned_inputs(
        net_asset_values,
        risk_fractions,
        stop_distance_fractions,
        nan_policy=nan_policy,
    )
    _validate_non_negative(nav, name="net_asset_values")
    _validate_fractions(fractions, name="risk_fractions")
    _validate_positive(distances, name="stop_distance_fractions")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        result = nav * fractions / distances
    reject_infinite_result(result, name="max_allowed_notional")
    return _restore_output(result, scalar=scalar)


def _aligned_inputs(
    *inputs: RiskInput,
    nan_policy: NanPolicy,
) -> tuple[FloatArray | bool, ...]:
    arrays = []
    scalar_flags = []
    target_shape: tuple[int, ...] | None = None
    for values in inputs:
        array, scalar = _coerce_input(values, nan_policy=nan_policy)
        arrays.append(array)
        scalar_flags.append(scalar)
        if not scalar:
            if target_shape is None:
                target_shape = array.shape
            elif array.shape != target_shape:
                raise NumericInputError(
                    "risk arrays must have identical shapes; only scalar expansion is supported"
                )
    all_scalar = all(scalar_flags)
    if target_shape is not None:
        arrays = [
            np.full(target_shape, array[0], dtype=np.float64) if scalar else array
            for array, scalar in zip(arrays, scalar_flags)
        ]
    return (*arrays, all_scalar)


def _coerce_input(
    values: RiskInput,
    *,
    nan_policy: NanPolicy,
) -> tuple[FloatArray, bool]:
    try:
        candidate = np.asarray(values)
    except (TypeError, ValueError, OverflowError) as error:
        raise NumericInputError("values must form a regular numeric array") from error
    scalar = candidate.ndim == 0
    if candidate.ndim > 2:
        raise NumericInputError("risk inputs must be scalars, vectors, or matrices")
    prepared = [values] if scalar else values
    return (
        as_float64_array(
            prepared,
            allow_empty=True,
            nan_policy=nan_policy,
        ),
        scalar,
    )


def _validate_side(side: PositionSide) -> None:
    if side not in POSITION_SIDES:
        raise NumericInputError(f"side must be one of {POSITION_SIDES}")


def _validate_positive(values: FloatArray, *, name: str) -> None:
    finite = values[~np.isnan(values)]
    if np.any(finite <= 0):
        raise NumericInputError(f"{name} must be strictly positive")


def _validate_non_negative(values: FloatArray, *, name: str) -> None:
    finite = values[~np.isnan(values)]
    if np.any(finite < 0):
        raise NumericInputError(f"{name} must be non-negative")


def _validate_fractions(values: FloatArray, *, name: str) -> None:
    finite = values[~np.isnan(values)]
    if np.any((finite < 0) | (finite > 1)):
        raise NumericInputError(f"{name} must be between 0 and 1")


def _restore_output(values: ArrayLike, *, scalar: bool) -> RiskOutput:
    array = np.array(values, dtype=np.float64, order="C", copy=True)
    return float(array[0]) if scalar else array
