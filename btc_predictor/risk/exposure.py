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
from decimal import Decimal, InvalidOperation
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

    tranche_id: str
    notional: Decimal
    entry_price: Decimal
    signed_loss_fraction: Decimal
    loss_fraction: Decimal
    risk_contribution: Decimal
    profitable_at_stop: bool

    def as_record(self) -> dict[str, Any]:
        tranche_id = _tranche_identifier(self.tranche_id)
        notional = _non_negative_decimal(self.notional, "notional")
        entry = _positive_decimal(self.entry_price, "entry_price")
        signed_loss = _decimal(self.signed_loss_fraction, "signed_loss_fraction")
        loss = _non_negative_decimal(self.loss_fraction, "loss_fraction")
        contribution = _non_negative_decimal(
            self.risk_contribution,
            "risk_contribution",
        )
        if contribution != notional * loss:
            raise ValueError("risk_contribution must equal notional * loss_fraction")
        if not isinstance(self.profitable_at_stop, bool):
            raise TypeError("profitable_at_stop must be a bool")
        return {
            "tranche_id": tranche_id,
            "notional": str(notional),
            "entry_price": str(entry),
            "signed_loss_fraction": str(signed_loss),
            "loss_fraction": str(loss),
            "risk_contribution": str(contribution),
            "profitable_at_stop": self.profitable_at_stop,
        }


@dataclass(frozen=True)
class RiskAtStopResult:
    feature_id: str
    policy_version: str
    parameter_status: str
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
        record = _validate_result(self)
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "parameter_status": self.parameter_status,
            "convention": self.convention,
            "direction": self.direction,
            "stop_price": _optional(record["stop"]),
            "nav": _optional(record["nav"]),
            "risk_at_stop": _optional(record["risk"]),
            "risk_fraction_nav": _optional(record["fraction"]),
            "target_fraction_nav": str(record["target"]),
            "maximum_fraction_nav": str(record["maximum"]),
            "headroom_amount": _optional(record["headroom"]),
            "within_maximum": self.within_maximum,
            "tranches": [item.as_record() for item in self.tranches],
            "config_metadata": record["metadata"],
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
    resolved_config = config if config is not None else load_strategy_config()
    maximum = (
        _fraction_decimal(maximum_fraction_nav, "maximum_fraction_nav")
        if maximum_fraction_nav is not None
        else _configured_maximum(resolved_config)
    )
    if decision_greater(target, maximum):
        raise ValueError("target_fraction_nav must not exceed maximum_fraction_nav")
    metadata = _resolve_config_metadata(resolved_config, config_metadata)
    nav_value = _positive_decimal(nav, "nav") if nav is not None else None
    stop = (
        _positive_decimal(stop_price, "stop_price")
        if stop_price is not None
        else None
    )

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

    resolved = _canonical_tranches(
        tuple(
            _tranche_risk(
                item,
                stop=stop,
                direction=direction,
                convention=convention,
            )
            for item in tranches
        ),
    )
    total = sum((item.risk_contribution for item in resolved), Decimal("0"))
    fraction = total / nav_value
    ceiling_amount = nav_value * maximum
    within = decision_less_equal(fraction, maximum)

    reason_codes = _risk_reason_codes(
        resolved,
        risk=total,
        fraction=fraction,
        target=target,
        within=within,
    )

    result = RiskAtStopResult(
        feature_id=RISK_AT_STOP_FEATURE_ID,
        policy_version=RISK_AT_STOP_POLICY_VERSION,
        parameter_status=RISK_AT_STOP_PARAMETER_STATUS,
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
        reason_codes=reason_codes,
    )
    result.as_record()
    return result


def risk_at_stop_from_record(record: Mapping[str, Any]) -> RiskAtStopResult:
    """Reconstruct and verify a persisted aggregate risk-at-stop result."""

    if not isinstance(record, Mapping):
        raise TypeError("record must be a mapping")
    source = dict(record)
    raw_tranches = source.get("tranches")
    if not isinstance(raw_tranches, list):
        raise ValueError("tranches must be a list")
    result = RiskAtStopResult(
        feature_id=_record_string(source.get("feature_id"), "feature_id"),
        policy_version=_record_string(source.get("policy_version"), "policy_version"),
        parameter_status=_record_string(
            source.get("parameter_status"),
            "parameter_status",
        ),
        convention=_record_string(source.get("convention"), "convention"),
        direction=_record_string(source.get("direction"), "direction"),
        stop_price=_record_optional_decimal(source.get("stop_price"), "stop_price"),
        nav=_record_optional_decimal(source.get("nav"), "nav"),
        risk_at_stop=_record_optional_decimal(
            source.get("risk_at_stop"),
            "risk_at_stop",
        ),
        risk_fraction_nav=_record_optional_decimal(
            source.get("risk_fraction_nav"),
            "risk_fraction_nav",
        ),
        target_fraction_nav=_decimal(
            source.get("target_fraction_nav"),
            "target_fraction_nav",
        ),
        maximum_fraction_nav=_decimal(
            source.get("maximum_fraction_nav"),
            "maximum_fraction_nav",
        ),
        headroom_amount=_record_optional_decimal(
            source.get("headroom_amount"),
            "headroom_amount",
        ),
        within_maximum=_record_bool(
            source.get("within_maximum"),
            "within_maximum",
        ),
        tranches=tuple(
            _tranche_risk_from_record(item) for item in raw_tranches
        ),
        config_metadata=_validate_config_metadata(
            source.get("config_metadata", {}),
        ),
        complete=_record_bool(source.get("complete"), "complete"),
        reason_codes=_record_reason_codes(source.get("reason_codes")),
    )
    if result.as_record() != source:
        raise ValueError("record does not match reconstructed risk-at-stop result")
    return result


def _tranche_risk_from_record(source: Any) -> TrancheRisk:
    if not isinstance(source, Mapping):
        raise TypeError("tranche records must be mappings")
    return TrancheRisk(
        tranche_id=_tranche_identifier(source.get("tranche_id")),
        notional=_non_negative_decimal(source.get("notional"), "notional"),
        entry_price=_positive_decimal(source.get("entry_price"), "entry_price"),
        signed_loss_fraction=_decimal(
            source.get("signed_loss_fraction"),
            "signed_loss_fraction",
        ),
        loss_fraction=_non_negative_decimal(
            source.get("loss_fraction"),
            "loss_fraction",
        ),
        risk_contribution=_non_negative_decimal(
            source.get("risk_contribution"),
            "risk_contribution",
        ),
        profitable_at_stop=_record_bool(
            source.get("profitable_at_stop"),
            "profitable_at_stop",
        ),
    )


def _tranche_risk(
    tranche: Any,
    *,
    stop: Decimal,
    direction: str,
    convention: str,
) -> TrancheRisk:
    record = _as_record(tranche, "tranche")
    tranche_id = _tranche_identifier(
        record.get("tranche_id")
        if record.get("tranche_id") is not None
        else record.get("tranche_number"),
    )
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
        (entry - stop) / entry
        if direction == LONG_DIRECTION
        else (stop - entry) / entry
    )
    profitable = decision_less(signed_loss, 0)
    if convention == FLOORED_AT_ZERO:
        loss_fraction = max(signed_loss, Decimal("0"))
    else:
        loss_fraction = abs(signed_loss)
    return TrancheRisk(
        tranche_id=tranche_id,
        notional=notional,
        entry_price=entry,
        signed_loss_fraction=signed_loss,
        loss_fraction=loss_fraction,
        risk_contribution=notional * loss_fraction,
        profitable_at_stop=profitable,
    )


def _configured_maximum(config: StrategyConfig) -> Decimal:
    return Decimal(str(config.risk.max_risk_at_stop_fraction_nav))


def _resolve_config_metadata(
    config: StrategyConfig,
    supplied: Mapping[str, str] | None,
) -> dict[str, str]:
    expected = _validate_config_metadata(config.run_metadata())
    if supplied is None:
        return expected
    actual = _validate_config_metadata(supplied)
    if actual != expected:
        raise ValueError("config_metadata must match the supplied strategy config")
    return actual


def _validate_config_metadata(metadata: Mapping[str, Any]) -> dict[str, str]:
    required = ("config_version", "strategy_version", "parameter_set_id")
    if not isinstance(metadata, Mapping):
        raise TypeError("config_metadata must be a mapping")
    if set(metadata) != set(required):
        raise ValueError("config_metadata must exactly match strategy run metadata")
    normalized = {}
    for key in required:
        value = metadata[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"config_metadata.{key} must be a non-empty string")
        normalized[key] = value
    return normalized


def _tranche_identifier(value: Any) -> str:
    if isinstance(value, bool) or value is None:
        raise ValueError("tranche must supply a unique tranche identifier")
    if isinstance(value, int):
        if value < 1:
            raise ValueError("numeric tranche identifiers must be positive")
        return str(value)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            raise ValueError("tranche identifier must be non-empty")
        return normalized
    raise TypeError("tranche identifier must be a string or integer")


def _canonical_tranches(
    tranches: tuple[TrancheRisk, ...],
) -> tuple[TrancheRisk, ...]:
    identifiers = tuple(item.tranche_id for item in tranches)
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("tranche identifiers must be unique")
    return tuple(sorted(tranches, key=lambda item: item.tranche_id))


def _validate_result(result: RiskAtStopResult) -> dict[str, Any]:
    if result.feature_id != RISK_AT_STOP_FEATURE_ID:
        raise ValueError("feature_id must be RISK_AT_STOP")
    if result.policy_version != RISK_AT_STOP_POLICY_VERSION:
        raise ValueError(f"policy_version must be {RISK_AT_STOP_POLICY_VERSION}")
    if result.parameter_status != RISK_AT_STOP_PARAMETER_STATUS:
        raise ValueError(f"parameter_status must be {RISK_AT_STOP_PARAMETER_STATUS}")
    if result.convention not in RISK_AT_STOP_CONVENTIONS:
        raise ValueError(f"convention must be one of {RISK_AT_STOP_CONVENTIONS}")
    if result.direction not in INVALIDATION_DIRECTIONS:
        raise ValueError(f"direction must be one of {INVALIDATION_DIRECTIONS}")
    if not isinstance(result.complete, bool):
        raise TypeError("complete must be a bool")
    if not isinstance(result.within_maximum, bool):
        raise TypeError("within_maximum must be a bool")

    target = _fraction_decimal(result.target_fraction_nav, "target_fraction_nav")
    maximum = _fraction_decimal(result.maximum_fraction_nav, "maximum_fraction_nav")
    if decision_greater(target, maximum):
        raise ValueError("target_fraction_nav must not exceed maximum_fraction_nav")
    metadata = _validate_config_metadata(result.config_metadata)
    stop = (
        _positive_decimal(result.stop_price, "stop_price")
        if result.stop_price is not None
        else None
    )
    nav = _positive_decimal(result.nav, "nav") if result.nav is not None else None

    if not result.complete:
        if stop is not None and nav is not None:
            raise ValueError("incomplete risk-at-stop must have a missing stop or NAV")
        if any(
            value is not None
            for value in (
                result.risk_at_stop,
                result.risk_fraction_nav,
                result.headroom_amount,
            )
        ):
            raise ValueError("incomplete risk-at-stop cannot contain derived amounts")
        if result.within_maximum or result.tranches:
            raise ValueError(
                "incomplete risk-at-stop cannot contain a verdict or tranches",
            )
        if result.reason_codes != ("RISK_AT_STOP_INPUT_MISSING",):
            raise ValueError(
                "incomplete risk-at-stop requires its missing-input reason",
            )
        return {
            "stop": stop,
            "nav": nav,
            "risk": None,
            "fraction": None,
            "target": target,
            "maximum": maximum,
            "headroom": None,
            "metadata": metadata,
        }

    if stop is None or nav is None:
        raise ValueError("complete risk-at-stop requires a stop and NAV")
    if result.risk_at_stop is None or result.risk_fraction_nav is None:
        raise ValueError("complete risk-at-stop requires risk amounts")
    if result.headroom_amount is None:
        raise ValueError("complete risk-at-stop requires headroom")

    risk = _non_negative_decimal(result.risk_at_stop, "risk_at_stop")
    fraction = _non_negative_decimal(result.risk_fraction_nav, "risk_fraction_nav")
    headroom = _non_negative_decimal(result.headroom_amount, "headroom_amount")
    canonical = _canonical_tranches(result.tranches)
    if canonical != result.tranches:
        raise ValueError("tranches must use canonical tranche-identifier ordering")
    expected_tranches = tuple(
        _tranche_risk(
            {
                "tranche_id": tranche.tranche_id,
                "notional": tranche.notional,
                "entry_price": tranche.entry_price,
            },
            stop=stop,
            direction=result.direction,
            convention=result.convention,
        )
        for tranche in result.tranches
    )
    if expected_tranches != result.tranches:
        raise ValueError("tranche contributions do not match the shared-stop geometry")
    expected_risk = sum(
        (tranche.risk_contribution for tranche in result.tranches),
        Decimal("0"),
    )
    if risk != expected_risk:
        raise ValueError("risk_at_stop must equal the sum of tranche contributions")
    expected_fraction = risk / nav
    if fraction != expected_fraction:
        raise ValueError("risk_fraction_nav must equal risk_at_stop / nav")
    expected_within = decision_less_equal(fraction, maximum)
    if result.within_maximum != expected_within:
        raise ValueError("within_maximum does not match the configured ceiling")
    expected_headroom = max(nav * maximum - risk, Decimal("0"))
    if headroom != expected_headroom:
        raise ValueError("headroom_amount does not match remaining ceiling capacity")
    expected_reasons = _risk_reason_codes(
        result.tranches,
        risk=risk,
        fraction=fraction,
        target=target,
        within=expected_within,
    )
    if result.reason_codes != expected_reasons:
        raise ValueError("reason_codes do not match risk-at-stop state")
    return {
        "stop": stop,
        "nav": nav,
        "risk": risk,
        "fraction": fraction,
        "target": target,
        "maximum": maximum,
        "headroom": headroom,
        "metadata": metadata,
    }


def _risk_reason_codes(
    tranches: tuple[TrancheRisk, ...],
    *,
    risk: Decimal,
    fraction: Decimal,
    target: Decimal,
    within: bool,
) -> tuple[str, ...]:
    reasons = []
    if not tranches or decision_less_equal(risk, 0):
        reasons.append("RISK_AT_STOP_NO_OPEN_RISK")
    if not within:
        reasons.append("RISK_AT_STOP_EXCEEDS_MAXIMUM")
    elif decision_greater(fraction, target):
        reasons.append("RISK_AT_STOP_ABOVE_TARGET")
    else:
        reasons.append("RISK_AT_STOP_WITHIN_TARGET")
    return tuple(reasons)


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
    result = RiskAtStopResult(
        feature_id=RISK_AT_STOP_FEATURE_ID,
        policy_version=RISK_AT_STOP_POLICY_VERSION,
        parameter_status=RISK_AT_STOP_PARAMETER_STATUS,
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
    result.as_record()
    return result


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
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(f"{name} must be numeric") from error
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    return result


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


def _record_optional_decimal(value: Any, name: str) -> Decimal | None:
    return None if value is None else _decimal(value, name)


def _record_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _record_bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be a bool")
    return value


def _record_reason_codes(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError("reason_codes must be a sequence")
    reasons = tuple(value)
    if any(not isinstance(code, str) or not code.strip() for code in reasons):
        raise ValueError("reason_codes must contain non-empty strings")
    if len(reasons) != len(set(reasons)):
        raise ValueError("reason_codes must not contain duplicates")
    return reasons


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
    "risk_at_stop_from_record",
]
