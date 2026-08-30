"""Tolerance-aware comparisons for deterministic hard-decision boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal, TypeAlias

import numpy as np

from btc_predictor.quant.arrays import NumericInputError, PARITY_TOLERANCE

DecisionValue: TypeAlias = Decimal | float | int | str | np.floating | np.integer
ComparisonResult: TypeAlias = Literal[-1, 0, 1]
DECISION_COMPARISON_POLICY_VERSION = "DECISION_COMPARISON_V1"


def _decimal(value: DecisionValue, *, name: str) -> Decimal:
    if isinstance(value, (bool, np.bool_)):
        raise NumericInputError(f"{name} must not be boolean")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise NumericInputError(f"{name} must be a finite numeric value") from error
    if not result.is_finite():
        raise NumericInputError(f"{name} must be a finite numeric value")
    return result


@dataclass(frozen=True)
class DecisionTolerance:
    """Absolute and relative tolerance used only at hard-decision boundaries."""

    absolute: Decimal = Decimal(str(PARITY_TOLERANCE.absolute))
    relative: Decimal = Decimal(str(PARITY_TOLERANCE.relative))

    def __post_init__(self) -> None:
        absolute = _decimal(self.absolute, name="absolute")
        relative = _decimal(self.relative, name="relative")
        if absolute < 0 or relative < 0:
            raise NumericInputError("decision tolerances must be non-negative")
        object.__setattr__(self, "absolute", absolute)
        object.__setattr__(self, "relative", relative)


DEFAULT_DECISION_TOLERANCE = DecisionTolerance()


def decision_compare(
    left: DecisionValue,
    right: DecisionValue,
    *,
    tolerance: DecisionTolerance = DEFAULT_DECISION_TOLERANCE,
) -> ComparisonResult:
    """Compare two finite values after collapsing the configured tolerance band."""

    if not isinstance(tolerance, DecisionTolerance):
        raise NumericInputError("tolerance must be a DecisionTolerance")
    left_value = _decimal(left, name="left")
    right_value = _decimal(right, name="right")
    difference = left_value - right_value
    allowed = max(
        tolerance.absolute,
        tolerance.relative * max(abs(left_value), abs(right_value)),
    )
    if abs(difference) <= allowed:
        return 0
    return -1 if difference < 0 else 1


def decision_equal(left: DecisionValue, right: DecisionValue) -> bool:
    """Return whether two values are equivalent under the decision policy."""

    return decision_compare(left, right) == 0


def decision_greater(left: DecisionValue, right: DecisionValue) -> bool:
    """Implement strict ``>`` outside the decision-equivalence band."""

    return decision_compare(left, right) > 0


def decision_greater_equal(left: DecisionValue, right: DecisionValue) -> bool:
    """Implement ``>=`` with boundary-equivalent values included."""

    return decision_compare(left, right) >= 0


def decision_less(left: DecisionValue, right: DecisionValue) -> bool:
    """Implement strict ``<`` outside the decision-equivalence band."""

    return decision_compare(left, right) < 0


def decision_less_equal(left: DecisionValue, right: DecisionValue) -> bool:
    """Implement ``<=`` with boundary-equivalent values included."""

    return decision_compare(left, right) <= 0
