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
    if side == "long":
        distances = (entries - stops) / entries
    else:
        distances = (stops - entries) / entries
    return _restore_output(np.maximum(distances, np.float64(0)), scalar=scalar)


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
    if side == "long":
        risk = entries - stops
        reward = targets - entries
    else:
        risk = stops - entries
        reward = entries - targets
    valid = (risk > 0) & (reward > 0)
    result = np.full(entries.shape, np.nan, dtype=np.float64)
    np.divide(reward, risk, out=result, where=valid)
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
    return _restore_output(nav * fractions, scalar=scalar)


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
    if side == "long":
        loss_fractions = (entries - stops) / entries
    else:
        loss_fractions = (stops - entries) / entries
    contributions = notional_values * np.maximum(loss_fractions, np.float64(0))
    return _restore_output(contributions, scalar=scalar)


def risk_at_stop(
    notionals: RiskInput,
    entry_prices: RiskInput,
    stop_prices: RiskInput,
    *,
    side: PositionSide,
    nan_policy: NanPolicy = "raise",
) -> float:
    """Return total downside capital risk at stop across arbitrary tranches."""

    contributions = risk_contribution_by_tranche(
        notionals,
        entry_prices,
        stop_prices,
        side=side,
        nan_policy=nan_policy,
    )
    return float(np.sum(contributions, dtype=np.float64))


def risk_improvement(
    current_risk: RiskInput,
    proposed_risk: RiskInput,
    *,
    nan_policy: NanPolicy = "raise",
) -> RiskOutput:
    """Return the non-negative reduction from current to proposed risk."""

    current, proposed, scalar = _aligned_inputs(
        current_risk,
        proposed_risk,
        nan_policy=nan_policy,
    )
    _validate_non_negative(current, name="current_risk")
    _validate_non_negative(proposed, name="proposed_risk")
    improvements = np.maximum(current - proposed, np.float64(0))
    return _restore_output(improvements, scalar=scalar)


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
    result = nav * fractions / distances
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
