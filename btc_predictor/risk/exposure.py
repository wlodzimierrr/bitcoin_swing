"""Portfolio risk-at-stop constraint (BTC-146).

Rulebook 19 defines risk-at-stop as an **aggregate across tranches** sharing one
stop, not a per-trade quantity:

    RiskAtStop = sum_i  Q_i * |Entry_i - Stop|
               = sum_i  N_i * |(Entry_i - Stop) / Entry_i|

with an optional floored variant for longs in which already-profitable tranches
contribute zero downside:

    RiskAtStop = sum_i  N_i * max((Entry_i - Stop) / Entry_i, 0)

The rulebook requires that "the exact convention used for pre-entry risk,
current portfolio risk, and realized locked-in profit must be explicit and
consistent across advisory, paper trading, and backtesting". That convention is
therefore a versioned identity here rather than an implicit choice, and it is
persisted with every result.

The constraint exists to serve one objective, quoted from the rulebook:

    Notional exposure can increase while total downside risk stays bounded.

That is only true under the floored convention, which is why it is the default
and why BTC-047's kernels implement it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from btc_predictor.config.strategy import StrategyConfig, load_strategy_config
from btc_predictor.quant.comparisons import (
    decision_greater,
    decision_greater_equal,
    decision_less,
    decision_less_equal,
)
from btc_predictor.risk.invalidation import (
    INVALIDATION_DIRECTIONS,
    LONG_DIRECTION,
)


RISK_AT_STOP_FEATURE_ID = "RISK_AT_STOP"
RISK_AT_STOP_POLICY_VERSION = "RISK_AT_STOP_V1"

# The two rulebook conventions. FLOORED_AT_ZERO lets a profitable tranche
# contribute no downside, which is what allows notional to grow while risk
# stays bounded. ABSOLUTE_DISTANCE keeps the unsigned distance for every
# tranche and is retained for audit and comparison.
FLOORED_AT_ZERO = "FLOORED_AT_ZERO"
ABSOLUTE_DISTANCE = "ABSOLUTE_DISTANCE"
RISK_AT_STOP_CONVENTIONS = (FLOORED_AT_ZERO, ABSOLUTE_DISTANCE)
DEFAULT_RISK_AT_STOP_CONVENTION = FLOORED_AT_ZERO

# Rulebook 19 suggests a Phase-1 maximum somewhere in 0.75%-1.00% of NAV. The
# hard ceiling is the configured max_risk_at_stop_fraction_nav; the lower end of
# the band is a soft target that warns rather than blocks.
DEFAULT_RISK_AT_STOP_TARGET_FRACTION = Decimal("0.0075")
RISK_AT_STOP_PARAMETER_STATUS = "PROVISIONAL_PENDING_BTC_185"

RISK_AT_STOP_REASON_CODES = (
    "RISK_AT_STOP_WITHIN_TARGET",
    "RISK_AT_STOP_ABOVE_TARGET",
    "RISK_AT_STOP_EXCEEDS_MAXIMUM",
    "RISK_AT_STOP_NO_OPEN_RISK",
    "RISK_AT_STOP_INPUT_MISSING",
)


@dataclass(frozen=True)
class TrancheRisk:
    """One tranche's contribution to aggregate risk at the shared stop."""

    tranche_id: str | None
    notional: Decimal
    entry_price: Decimal
    loss_fraction: Decimal
    risk_contribution: Decimal
    profitable_at_stop: bool

    def as_record(self) -> dict[str, Any]:
        return {
            "tranche_id": self.tranche_id,
            "notional": str(self.notional),
            "entry_price": str(self.entry_price),
            "loss_fraction": str(self.loss_fraction),
            "risk_contribution": str(self.risk_contribution),
            "profitable_at_stop": self.profitable_at_stop,
        }


@dataclass(frozen=True)
class RiskAtStopResult:
    feature_id: str
    policy_version: str
    convention: str
    direction: str
    stop_price: Decimal | None
    nav: Decimal | None
    risk_at_stop: Decimal | None
    risk_fraction_nav: Decimal | None
    target_fraction_nav: Decimal
    maximum_fraction_nav: Decimal
    headroom_amount: Decimal | None
    within_maximum: bool
    tranches: tuple[TrancheRisk, ...]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        if self.complete and self.risk_at_stop is None:
            raise ValueError("a complete risk-at-stop requires an amount")
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "convention": self.convention,
            "direction": self.direction,
            "stop_price": _optional(self.stop_price),
            "nav": _optional(self.nav),
            "risk_at_stop": _optional(self.risk_at_stop),
            "risk_fraction_nav": _optional(self.risk_fraction_nav),
            "target_fraction_nav": str(self.target_fraction_nav),
            "maximum_fraction_nav": str(self.maximum_fraction_nav),
            "headroom_amount": _optional(self.headroom_amount),
            "within_maximum": self.within_maximum,
            "tranches": [item.as_record() for item in self.tranches],
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def calculate_risk_at_stop(
    tranches: Sequence[Any],
    *,
    stop_price: Any | None,
    nav: Any | None,
    direction: str = LONG_DIRECTION,
    convention: str = DEFAULT_RISK_AT_STOP_CONVENTION,
    target_fraction_nav: Any = DEFAULT_RISK_AT_STOP_TARGET_FRACTION,
    maximum_fraction_nav: Any | None = None,
    config: StrategyConfig | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> RiskAtStopResult:
    """Aggregate risk at a shared stop and test it against the NAV ceiling.

    Each tranche supplies an ``entry_price`` and either a ``notional`` or a
    ``quantity``; the two rulebook forms are equivalent and both are accepted.
    """

    if direction not in INVALIDATION_DIRECTIONS:
        raise ValueError(f"direction must be one of {INVALIDATION_DIRECTIONS}")
    if convention not in RISK_AT_STOP_CONVENTIONS:
        raise ValueError(f"convention must be one of {RISK_AT_STOP_CONVENTIONS}")
    target = _fraction_decimal(target_fraction_nav, "target_fraction_nav")
    maximum = (
        _fraction_decimal(maximum_fraction_nav, "maximum_fraction_nav")
        if maximum_fraction_nav is not None
        else _configured_maximum(config)
    )
    if decision_greater(target, maximum):
        raise ValueError("target_fraction_nav must not exceed maximum_fraction_nav")
    metadata = dict(config_metadata or {})
    nav_value = _positive_decimal(nav, "nav") if nav is not None else None
    stop = _positive_decimal(stop_price, "stop_price") if stop_price is not None else None

    if stop is None or nav_value is None:
        return _incomplete(
            convention=convention,
            direction=direction,
            stop=stop,
            nav=nav_value,
            target=target,
            maximum=maximum,
            metadata=metadata,
        )

    resolved = tuple(
        _tranche_risk(item, stop=stop, direction=direction, convention=convention)
        for item in tranches
    )
    total = sum((item.risk_contribution for item in resolved), Decimal("0"))
    fraction = total / nav_value
    ceiling_amount = nav_value * maximum
    within = decision_less_equal(fraction, maximum)

    reason_codes = []
    if not resolved or decision_less_equal(total, 0):
        reason_codes.append("RISK_AT_STOP_NO_OPEN_RISK")
    if not within:
        reason_codes.append("RISK_AT_STOP_EXCEEDS_MAXIMUM")
    elif decision_greater(fraction, target):
        reason_codes.append("RISK_AT_STOP_ABOVE_TARGET")
    else:
        reason_codes.append("RISK_AT_STOP_WITHIN_TARGET")

    return RiskAtStopResult(
        feature_id=RISK_AT_STOP_FEATURE_ID,
        policy_version=RISK_AT_STOP_POLICY_VERSION,
        convention=convention,
        direction=direction,
        stop_price=stop,
        nav=nav_value,
        risk_at_stop=total,
        risk_fraction_nav=fraction,
        target_fraction_nav=target,
        maximum_fraction_nav=maximum,
        headroom_amount=max(ceiling_amount - total, Decimal("0")),
        within_maximum=within,
        tranches=resolved,
        config_metadata=metadata,
        complete=True,
        reason_codes=tuple(dict.fromkeys(reason_codes)),
    )


def _tranche_risk(
    tranche: Any,
    *,
    stop: Decimal,
    direction: str,
    convention: str,
) -> TrancheRisk:
    record = _as_record(tranche, "tranche")
    entry = _positive_decimal(record.get("entry_price"), "entry_price")
    notional = record.get("notional")
    if notional is None:
        quantity = record.get("quantity")
        if quantity is None:
            raise ValueError("tranche must supply notional or quantity")
        notional = _non_negative_decimal(quantity, "quantity") * entry
    else:
        notional = _non_negative_decimal(notional, "notional")

    signed_loss = (
        (entry - stop) / entry if direction == LONG_DIRECTION else (stop - entry) / entry
    )
    profitable = decision_less(signed_loss, 0)
    if convention == FLOORED_AT_ZERO:
        loss_fraction = max(signed_loss, Decimal("0"))
    else:
        loss_fraction = abs(signed_loss)
    return TrancheRisk(
        tranche_id=record.get("tranche_id"),
        notional=notional,
        entry_price=entry,
        loss_fraction=loss_fraction,
        risk_contribution=notional * loss_fraction,
        profitable_at_stop=profitable,
    )


def _configured_maximum(config: StrategyConfig | None) -> Decimal:
    resolved = config if config is not None else load_strategy_config()
    return Decimal(str(resolved.risk.max_risk_at_stop_fraction_nav))


def _incomplete(
    *,
    convention: str,
    direction: str,
    stop: Decimal | None,
    nav: Decimal | None,
    target: Decimal,
    maximum: Decimal,
    metadata: dict[str, str],
) -> RiskAtStopResult:
    return RiskAtStopResult(
        feature_id=RISK_AT_STOP_FEATURE_ID,
        policy_version=RISK_AT_STOP_POLICY_VERSION,
        convention=convention,
        direction=direction,
        stop_price=stop,
        nav=nav,
        risk_at_stop=None,
        risk_fraction_nav=None,
        target_fraction_nav=target,
        maximum_fraction_nav=maximum,
        headroom_amount=None,
        within_maximum=False,
        tranches=(),
        config_metadata=metadata,
        complete=False,
        reason_codes=("RISK_AT_STOP_INPUT_MISSING",),
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
    if decision_greater_equal(result, Decimal("1")) and result != Decimal("1"):
        raise ValueError(f"{name} must be between 0 and 1")
    return result


__all__ = [
    "ABSOLUTE_DISTANCE",
    "DEFAULT_RISK_AT_STOP_CONVENTION",
    "DEFAULT_RISK_AT_STOP_TARGET_FRACTION",
    "FLOORED_AT_ZERO",
    "RISK_AT_STOP_CONVENTIONS",
    "RISK_AT_STOP_FEATURE_ID",
    "RISK_AT_STOP_PARAMETER_STATUS",
    "RISK_AT_STOP_POLICY_VERSION",
    "RISK_AT_STOP_REASON_CODES",
    "RiskAtStopResult",
    "TrancheRisk",
    "calculate_risk_at_stop",
]
