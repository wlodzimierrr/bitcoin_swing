"""Initial position sizing (BTC-145).

Rulebook 17:

    PositionNotional = NAV * RiskBudget / StopDistance%

The arithmetic is BTC-047's ``max_allowed_notional``. This module is the
Decimal-facing domain boundary over it, composing the BTC-144 risk budget with
the BTC-142 stop so the three inputs cannot be assembled inconsistently.

A zero stop distance is rejected rather than divided by. That case is not a
very large position, it is an undefined one, and BTC-047 already refuses it in
the quantitative kernel.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from btc_predictor.quant.comparisons import decision_greater, decision_less_equal


INITIAL_POSITION_SIZE_FEATURE_ID = "INITIAL_POSITION_SIZE"
INITIAL_POSITION_SIZE_POLICY_VERSION = "INITIAL_POSITION_SIZE_V1"

INITIAL_POSITION_SIZE_REASON_CODES = (
    "INITIAL_POSITION_SIZE_ASSIGNED",
    "INITIAL_POSITION_SIZE_INPUT_MISSING",
    "INITIAL_POSITION_SIZE_NO_RISK_BUDGET",
    "INITIAL_POSITION_SIZE_ZERO_STOP_DISTANCE",
    "INITIAL_POSITION_SIZE_CAPPED_AT_MAXIMUM",
)


@dataclass(frozen=True)
class InitialPositionSizeResult:
    feature_id: str
    policy_version: str
    nav: Decimal | None
    risk_fraction_nav: Decimal | None
    risk_budget_amount: Decimal | None
    stop_distance_fraction: Decimal | None
    entry_price: Decimal | None
    position_notional: Decimal | None
    position_quantity: Decimal | None
    notional_fraction_nav: Decimal | None
    maximum_notional_fraction_nav: Decimal | None
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        if self.complete and self.position_notional is None:
            raise ValueError("a complete position size requires a notional")
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "nav": _optional(self.nav),
            "risk_fraction_nav": _optional(self.risk_fraction_nav),
            "risk_budget_amount": _optional(self.risk_budget_amount),
            "stop_distance_fraction": _optional(self.stop_distance_fraction),
            "entry_price": _optional(self.entry_price),
            "position_notional": _optional(self.position_notional),
            "position_quantity": _optional(self.position_quantity),
            "notional_fraction_nav": _optional(self.notional_fraction_nav),
            "maximum_notional_fraction_nav": _optional(
                self.maximum_notional_fraction_nav,
            ),
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def calculate_initial_position_size(
    *,
    nav: Any | None,
    risk_fraction_nav: Any | None,
    stop_distance_fraction: Any | None,
    entry_price: Any | None = None,
    maximum_notional_fraction_nav: Any | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> InitialPositionSizeResult:
    """Return ``NAV * RiskBudget / StopDistance%``.

    ``entry_price`` is optional and yields the position in units as well as in
    notional. ``maximum_notional_fraction_nav`` is an optional exposure ceiling;
    it is off by default because no calibrated leverage limit exists yet, but
    the realised ``notional_fraction_nav`` is always reported so leverage stays
    visible.
    """

    metadata = dict(config_metadata or {})
    maximum = (
        _positive_decimal(
            maximum_notional_fraction_nav,
            "maximum_notional_fraction_nav",
        )
        if maximum_notional_fraction_nav is not None
        else None
    )
    nav_value = _positive_decimal(nav, "nav") if nav is not None else None
    fraction = (
        _fraction_decimal(risk_fraction_nav, "risk_fraction_nav")
        if risk_fraction_nav is not None
        else None
    )
    distance = (
        _non_negative_decimal(stop_distance_fraction, "stop_distance_fraction")
        if stop_distance_fraction is not None
        else None
    )
    entry = (
        _positive_decimal(entry_price, "entry_price")
        if entry_price is not None
        else None
    )

    if nav_value is None or fraction is None or distance is None:
        return _no_size(
            nav=nav_value,
            fraction=fraction,
            distance=distance,
            entry=entry,
            maximum=maximum,
            metadata=metadata,
            reason_codes=("INITIAL_POSITION_SIZE_INPUT_MISSING",),
        )

    if decision_less_equal(distance, 0):
        # Undefined, not unbounded: dividing here would invent exposure.
        return _no_size(
            nav=nav_value,
            fraction=fraction,
            distance=distance,
            entry=entry,
            maximum=maximum,
            metadata=metadata,
            reason_codes=("INITIAL_POSITION_SIZE_ZERO_STOP_DISTANCE",),
        )

    budget_amount = nav_value * fraction
    notional = budget_amount / distance
    reason_codes = ["INITIAL_POSITION_SIZE_ASSIGNED"]
    if maximum is not None and decision_greater(notional, nav_value * maximum):
        notional = nav_value * maximum
        reason_codes.append("INITIAL_POSITION_SIZE_CAPPED_AT_MAXIMUM")

    return InitialPositionSizeResult(
        feature_id=INITIAL_POSITION_SIZE_FEATURE_ID,
        policy_version=INITIAL_POSITION_SIZE_POLICY_VERSION,
        nav=nav_value,
        risk_fraction_nav=fraction,
        risk_budget_amount=budget_amount,
        stop_distance_fraction=distance,
        entry_price=entry,
        position_notional=notional,
        position_quantity=None if entry is None else notional / entry,
        notional_fraction_nav=notional / nav_value,
        maximum_notional_fraction_nav=maximum,
        config_metadata=metadata,
        complete=True,
        reason_codes=tuple(reason_codes),
    )


def initial_position_size_for_trade(
    risk_budget: Any,
    stop: Any,
    *,
    maximum_notional_fraction_nav: Any | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> InitialPositionSizeResult:
    """Canonical path: size from a BTC-144 budget and a BTC-142 stop.

    NAV and the risk fraction come from the budget, and the stop distance and
    entry price from the stop, so no consumer restates the trade geometry.
    """

    budget_record = _as_record(risk_budget, "risk_budget")
    stop_record = _as_record(stop, "stop")
    metadata = dict(config_metadata or {})

    reason_codes = []
    if not budget_record.get("complete"):
        reason_codes.append("INITIAL_POSITION_SIZE_NO_RISK_BUDGET")
    if not stop_record.get("complete"):
        reason_codes.append("INITIAL_POSITION_SIZE_INPUT_MISSING")
    if reason_codes:
        return _no_size(
            nav=None,
            fraction=None,
            distance=None,
            entry=None,
            maximum=None,
            metadata=metadata,
            reason_codes=tuple(reason_codes),
        )

    return calculate_initial_position_size(
        nav=budget_record.get("nav"),
        risk_fraction_nav=budget_record.get("risk_fraction_nav"),
        stop_distance_fraction=stop_record.get("stop_distance_fraction"),
        entry_price=stop_record.get("entry_price"),
        maximum_notional_fraction_nav=maximum_notional_fraction_nav,
        config_metadata=metadata,
    )


def _no_size(
    *,
    nav: Decimal | None,
    fraction: Decimal | None,
    distance: Decimal | None,
    entry: Decimal | None,
    maximum: Decimal | None,
    metadata: dict[str, str],
    reason_codes: tuple[str, ...],
) -> InitialPositionSizeResult:
    return InitialPositionSizeResult(
        feature_id=INITIAL_POSITION_SIZE_FEATURE_ID,
        policy_version=INITIAL_POSITION_SIZE_POLICY_VERSION,
        nav=nav,
        risk_fraction_nav=fraction,
        risk_budget_amount=(
            None if nav is None or fraction is None else nav * fraction
        ),
        stop_distance_fraction=distance,
        entry_price=entry,
        position_notional=None,
        position_quantity=None,
        notional_fraction_nav=None,
        maximum_notional_fraction_nav=maximum,
        config_metadata=metadata,
        complete=False,
        reason_codes=reason_codes,
    )


def _as_record(source: Any, name: str) -> Mapping[str, Any]:
    if isinstance(source, Mapping):
        return source
    as_record = getattr(source, "as_record", None)
    if callable(as_record):
        return as_record()
    raise TypeError(f"{name} must be a mapping or expose as_record()")


def _optional(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _decimal(value: Any, name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception as error:  # noqa: BLE001 - surfaced as a domain error
        raise ValueError(f"{name} must be numeric") from error


def _positive_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if decision_less_equal(result, 0):
        raise ValueError(f"{name} must be positive")
    return result


def _non_negative_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


def _fraction_decimal(value: Any, name: str) -> Decimal:
    result = _non_negative_decimal(value, name)
    if decision_greater(result, Decimal("1")):
        raise ValueError(f"{name} must be between 0 and 1")
    return result


__all__ = [
    "INITIAL_POSITION_SIZE_FEATURE_ID",
    "INITIAL_POSITION_SIZE_POLICY_VERSION",
    "INITIAL_POSITION_SIZE_REASON_CODES",
    "InitialPositionSizeResult",
    "calculate_initial_position_size",
    "initial_position_size_for_trade",
]
