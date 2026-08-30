"""Vectorized position and portfolio accounting mathematics."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeAlias

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
from btc_predictor.quant.risk import POSITION_SIDES, PositionSide

PortfolioInput: TypeAlias = float | ArrayLike
PortfolioOutput: TypeAlias = float | FloatArray
SideInput: TypeAlias = (
    PositionSide | Sequence[PositionSide] | Sequence[Sequence[PositionSide]]
)


def position_notional(
    quantities: PortfolioInput,
    prices: PortfolioInput,
    *,
    nan_policy: NanPolicy = "raise",
) -> PortfolioOutput:
    """Return unsigned position notional as quantity multiplied by price."""

    quantity_values, price_values, scalar = _aligned_inputs(
        quantities,
        prices,
        nan_policy=nan_policy,
    )
    _validate_non_negative(quantity_values, name="quantities")
    _validate_positive(price_values, name="prices")
    with np.errstate(over="ignore", invalid="ignore"):
        result = quantity_values * price_values
    reject_infinite_result(result, name="position_notional")
    return _restore_output(result, scalar=scalar)


def weighted_average_entry(
    entry_prices: PortfolioInput,
    quantities: PortfolioInput,
    *,
    nan_policy: NanPolicy = "raise",
) -> PortfolioOutput:
    """Return weighted entry for one tranche vector or each tranche-matrix row."""

    entries, quantity_values, _ = _aligned_inputs(
        entry_prices,
        quantities,
        nan_policy=nan_policy,
    )
    _validate_positive(entries, name="entry_prices")
    _validate_non_negative(quantity_values, name="quantities")
    with np.errstate(over="ignore", invalid="ignore"):
        weighted_entries = entries * quantity_values
    reject_infinite_result(weighted_entries, name="weighted_entry_numerator")
    total_quantity = stable_row_sum(
        quantity_values,
        nan_policy="propagate",
        name="total_quantity",
    )
    weighted_total = stable_row_sum(
        weighted_entries,
        nan_policy="propagate",
        name="weighted_entry_numerator",
    )
    totals = np.asarray(total_quantity, dtype=np.float64)
    numerators = np.asarray(weighted_total, dtype=np.float64)
    result = np.full(totals.shape, np.nan, dtype=np.float64)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        np.divide(numerators, totals, out=result, where=totals != 0)
    reject_infinite_result(result, name="weighted_average_entry")
    if result.ndim == 0:
        return float(result)
    return np.array(result, dtype=np.float64, order="C", copy=True)


def unrealized_pnl(
    entry_prices: PortfolioInput,
    current_prices: PortfolioInput,
    quantities: PortfolioInput,
    *,
    side: PositionSide,
    nan_policy: NanPolicy = "raise",
) -> PortfolioOutput:
    """Return signed mark-to-market P&L for long or short positions."""

    return _position_pnl(
        entry_prices,
        current_prices,
        quantities,
        side=side,
        nan_policy=nan_policy,
    )


def realized_pnl(
    entry_prices: PortfolioInput,
    exit_prices: PortfolioInput,
    quantities: PortfolioInput,
    *,
    side: PositionSide,
    nan_policy: NanPolicy = "raise",
) -> PortfolioOutput:
    """Return signed realized P&L for long or short closes."""

    return _position_pnl(
        entry_prices,
        exit_prices,
        quantities,
        side=side,
        nan_policy=nan_policy,
    )


def gross_exposure(
    notionals: PortfolioInput,
    *,
    nan_policy: NanPolicy = "raise",
) -> PortfolioOutput:
    """Return gross exposure for one portfolio vector or each matrix row."""

    values, _ = _coerce_input(notionals, nan_policy=nan_policy)
    _validate_non_negative(values, name="notionals")
    return stable_row_sum(
        values,
        nan_policy="propagate",
        name="gross_exposure",
    )


def net_exposure(
    notionals: PortfolioInput,
    sides: SideInput,
    *,
    nan_policy: NanPolicy = "raise",
) -> PortfolioOutput:
    """Return net exposure for one portfolio vector or each matrix row."""

    values, scalar = _coerce_input(notionals, nan_policy=nan_policy)
    _validate_non_negative(values, name="notionals")
    signs = _side_signs(sides, shape=values.shape, scalar=scalar)
    signed_values = values * signs
    return stable_row_sum(
        signed_values,
        nan_policy="propagate",
        name="net_exposure",
    )


def _position_pnl(
    entry_prices: PortfolioInput,
    mark_prices: PortfolioInput,
    quantities: PortfolioInput,
    *,
    side: PositionSide,
    nan_policy: NanPolicy,
) -> PortfolioOutput:
    entries, marks, quantity_values, scalar = _aligned_inputs(
        entry_prices,
        mark_prices,
        quantities,
        nan_policy=nan_policy,
    )
    _validate_positive(entries, name="entry_prices")
    _validate_positive(marks, name="mark_prices")
    _validate_non_negative(quantity_values, name="quantities")
    _validate_side(side)
    with np.errstate(over="ignore", invalid="ignore"):
        price_changes = marks - entries if side == "long" else entries - marks
        result = quantity_values * price_changes
    reject_infinite_result(result, name="position_pnl")
    return _restore_output(result, scalar=scalar)


def _aligned_inputs(
    *inputs: PortfolioInput,
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
                    "portfolio arrays must have identical shapes; "
                    "only scalar expansion is supported"
                )
    all_scalar = all(scalar_flags)
    if target_shape is not None:
        arrays = [
            np.full(target_shape, array[0], dtype=np.float64) if scalar else array
            for array, scalar in zip(arrays, scalar_flags)
        ]
    return (*arrays, all_scalar)


def _coerce_input(
    values: PortfolioInput,
    *,
    nan_policy: NanPolicy,
) -> tuple[FloatArray, bool]:
    try:
        candidate = np.asarray(values)
    except (TypeError, ValueError, OverflowError) as error:
        raise NumericInputError("values must form a regular numeric array") from error
    scalar = candidate.ndim == 0
    if candidate.ndim > 2:
        raise NumericInputError(
            "portfolio inputs must be scalars, vectors, or matrices"
        )
    prepared = [values] if scalar else values
    return (
        as_float64_array(
            prepared,
            allow_empty=True,
            nan_policy=nan_policy,
        ),
        scalar,
    )


def _side_signs(
    sides: SideInput,
    *,
    shape: tuple[int, ...],
    scalar: bool,
) -> FloatArray:
    if isinstance(sides, str):
        _validate_side(sides)
        return np.full(shape, 1 if sides == "long" else -1, dtype=np.float64)
    side_values = np.asarray(tuple(sides), dtype=object)
    if scalar or side_values.shape != shape:
        raise NumericInputError(
            "sides must match the notional shape or be one side string"
        )
    signs = np.empty(shape, dtype=np.float64)
    for index, side in np.ndenumerate(side_values):
        _validate_side(side)
        signs[index] = 1 if side == "long" else -1
    return signs


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


def _restore_output(values: ArrayLike, *, scalar: bool) -> PortfolioOutput:
    array = np.array(values, dtype=np.float64, order="C", copy=True)
    return float(array[0]) if scalar else array
