"""Anti-martingale tranche sizing (BTC-155).

Rulebook 18 gives the research schedule as shares of the **final** position:

    Initial   40%
    Add #1   +35%
    Add #2   +25%

Two things follow from "Relative Final Position" that a bare percentage list
does not make obvious.

The shares sum to one, because BTC-145 sizes the whole position once from the
risk budget and this schedule only decides how that single size is delivered.
A schedule summing to anything else would silently re-size the position.

The shares never increase, because rulebook 18's anti-martingale principle is
"add to winners, never to losers". Adding in growing size is the martingale
shape the strategy exists to avoid, so a schedule that grows is rejected by
configuration rather than merely discouraged in prose.

The schedule is also a hard cap on how many adds exist. BTC-154 decides whether
an add is *permitted*; this module decides whether one is *allocated*, and a
fourth tranche has no allocation at all rather than an extrapolated one.

These percentages are research parameters, so the schedule lives in versioned
configuration and carries ``PROVISIONAL_RESEARCH_CALIBRATABLE``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from btc_predictor.config.strategy import StrategyConfig, load_strategy_config
from btc_predictor.quant.comparisons import decision_greater, decision_less_equal


TRANCHE_SIZING_FEATURE_ID = "TRANCHE_SIZING"
TRANCHE_SIZING_POLICY_VERSION = "TRANCHE_SIZING_V1"
TRANCHE_SCHEDULE_PARAMETER_STATUS = "PROVISIONAL_RESEARCH_CALIBRATABLE"
TRANCHE_FRACTION_SUM_TOLERANCE = Decimal("0.000001")

TRANCHE_SIZING_REASON_CODES = (
    "TRANCHE_SIZING_ASSIGNED",
    "TRANCHE_SIZING_SCHEDULE_EXHAUSTED",
    "TRANCHE_SIZING_NO_POSITION_SIZE",
    "TRANCHE_SIZING_INPUT_MISSING",
)


@dataclass(frozen=True)
class TrancheAllocation:
    """One stage of the schedule, as an increment and as a running total."""

    tranche_number: int
    fraction_of_final: Decimal
    cumulative_fraction: Decimal
    notional: Decimal | None
    quantity: Decimal | None

    def as_record(self) -> dict[str, Any]:
        return {
            "tranche_number": self.tranche_number,
            "fraction_of_final": str(self.fraction_of_final),
            "cumulative_fraction": str(self.cumulative_fraction),
            "notional": _optional(self.notional),
            "quantity": _optional(self.quantity),
        }


@dataclass(frozen=True)
class TrancheSizingResult:
    feature_id: str
    policy_version: str
    parameter_status: str
    tranche_number: int
    schedule: tuple[Decimal, ...]
    allocation: TrancheAllocation | None
    remaining_fraction: Decimal | None
    final_position_notional: Decimal | None
    entry_price: Decimal | None
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    @property
    def maximum_tranche_count(self) -> int:
        return len(self.schedule)

    def as_record(self) -> dict[str, Any]:
        if self.complete and self.allocation is None:
            raise ValueError("a complete tranche sizing requires an allocation")
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "parameter_status": self.parameter_status,
            "tranche_number": self.tranche_number,
            "maximum_tranche_count": self.maximum_tranche_count,
            "schedule": [str(value) for value in self.schedule],
            "allocation": (
                self.allocation.as_record() if self.allocation is not None else None
            ),
            "remaining_fraction": _optional(self.remaining_fraction),
            "final_position_notional": _optional(self.final_position_notional),
            "entry_price": _optional(self.entry_price),
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def tranche_schedule_from_config(
    config: StrategyConfig | None = None,
) -> tuple[Decimal, ...]:
    """Return the configured schedule as exact Decimal shares."""

    resolved = config if config is not None else load_strategy_config()
    if not isinstance(resolved, StrategyConfig):
        raise TypeError("config must be a StrategyConfig")
    return validate_tranche_schedule(resolved.risk.tranche_schedule)


def validate_tranche_schedule(schedule: Sequence[Any]) -> tuple[Decimal, ...]:
    """Return a schedule that is positive, non-increasing, and sums to one."""

    if not isinstance(schedule, Sequence) or isinstance(schedule, (str, bytes)):
        raise TypeError("schedule must be a sequence of fractions")
    fractions = tuple(
        _fraction_decimal(value, f"schedule[{index}]")
        for index, value in enumerate(schedule)
    )
    if not fractions:
        raise ValueError("tranche schedule must not be empty")
    for index, (previous, current) in enumerate(zip(fractions, fractions[1:])):
        if decision_greater(current, previous):
            raise ValueError(
                f"tranche schedule must never increase; schedule[{index + 1}] "
                "is larger than the tranche before it",
            )
    total = sum(fractions, Decimal("0"))
    if abs(total - Decimal("1")) > TRANCHE_FRACTION_SUM_TOLERANCE:
        raise ValueError("tranche schedule must sum to 1")
    return fractions


def calculate_tranche_size(
    *,
    tranche_number: int,
    final_position_notional: Any | None = None,
    entry_price: Any | None = None,
    schedule: Sequence[Any] | None = None,
    config: StrategyConfig | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> TrancheSizingResult:
    """Return the allocation for one stage of the schedule.

    ``final_position_notional`` is BTC-145's whole-position size. It is
    optional, so the schedule can be inspected without a sized position, and
    ``entry_price`` additionally yields the tranche in units.
    """

    number = _tranche_number(tranche_number)
    fractions = (
        validate_tranche_schedule(schedule)
        if schedule is not None
        else tranche_schedule_from_config(config)
    )
    metadata = dict(config_metadata or {})
    notional = (
        _positive_decimal(final_position_notional, "final_position_notional")
        if final_position_notional is not None
        else None
    )
    entry = (
        _positive_decimal(entry_price, "entry_price")
        if entry_price is not None
        else None
    )

    if number > len(fractions):
        # The schedule caps the number of adds. There is no allocation for a
        # further tranche, and inventing one would size a position the risk
        # budget never authorized.
        return _no_allocation(
            number=number,
            fractions=fractions,
            notional=notional,
            entry=entry,
            metadata=metadata,
            reason_codes=("TRANCHE_SIZING_SCHEDULE_EXHAUSTED",),
        )

    fraction = fractions[number - 1]
    cumulative = sum(fractions[:number], Decimal("0"))
    remaining = sum(fractions[number:], Decimal("0"))
    allocation = TrancheAllocation(
        tranche_number=number,
        fraction_of_final=fraction,
        cumulative_fraction=cumulative,
        notional=None if notional is None else notional * fraction,
        quantity=(
            None
            if notional is None or entry is None
            else (notional * fraction) / entry
        ),
    )
    return TrancheSizingResult(
        feature_id=TRANCHE_SIZING_FEATURE_ID,
        policy_version=TRANCHE_SIZING_POLICY_VERSION,
        parameter_status=TRANCHE_SCHEDULE_PARAMETER_STATUS,
        tranche_number=number,
        schedule=fractions,
        allocation=allocation,
        remaining_fraction=remaining,
        final_position_notional=notional,
        entry_price=entry,
        config_metadata=metadata,
        complete=True,
        reason_codes=("TRANCHE_SIZING_ASSIGNED",),
    )


def next_tranche_for_position(
    lifecycle: Any,
    position_size: Any,
    *,
    entry_price: Any | None = None,
    schedule: Sequence[Any] | None = None,
    config: StrategyConfig | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> TrancheSizingResult:
    """Canonical path: size the next tranche from the ledger and BTC-145.

    The stage number comes from the BTC-150 tranche count rather than from a
    caller's own counter, and the whole-position size from the BTC-145 result,
    so neither the off-by-one nor the position size can be restated.
    """

    size_record = _as_record(position_size, "position_size")
    filled = _tranche_count(lifecycle)
    metadata = dict(config_metadata or {})

    if not size_record.get("complete"):
        fractions = (
            validate_tranche_schedule(schedule)
            if schedule is not None
            else tranche_schedule_from_config(config)
        )
        return _no_allocation(
            number=filled + 1,
            fractions=fractions,
            notional=None,
            entry=None,
            metadata=metadata,
            reason_codes=("TRANCHE_SIZING_NO_POSITION_SIZE",),
        )

    return calculate_tranche_size(
        tranche_number=filled + 1,
        final_position_notional=size_record.get("position_notional"),
        entry_price=(
            entry_price if entry_price is not None else size_record.get("entry_price")
        ),
        schedule=schedule,
        config=config,
        config_metadata=metadata,
    )


def _no_allocation(
    *,
    number: int,
    fractions: tuple[Decimal, ...],
    notional: Decimal | None,
    entry: Decimal | None,
    metadata: dict[str, str],
    reason_codes: tuple[str, ...],
) -> TrancheSizingResult:
    return TrancheSizingResult(
        feature_id=TRANCHE_SIZING_FEATURE_ID,
        policy_version=TRANCHE_SIZING_POLICY_VERSION,
        parameter_status=TRANCHE_SCHEDULE_PARAMETER_STATUS,
        tranche_number=number,
        schedule=fractions,
        allocation=None,
        remaining_fraction=None,
        final_position_notional=notional,
        entry_price=entry,
        config_metadata=metadata,
        complete=False,
        reason_codes=reason_codes,
    )


def _tranche_count(lifecycle: Any) -> int:
    count = getattr(lifecycle, "tranche_count", None)
    if count is None and isinstance(lifecycle, Mapping):
        count = lifecycle.get("tranche_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("lifecycle must expose a non-negative tranche_count")
    return count


def _as_record(source: Any, name: str) -> Mapping[str, Any]:
    if isinstance(source, Mapping):
        return source
    as_record = getattr(source, "as_record", None)
    if callable(as_record):
        return as_record()
    raise TypeError(f"{name} must be a mapping or expose as_record()")


def _tranche_number(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("tranche_number must be an integer")
    if value < 1:
        raise ValueError("tranche_number must be 1 or greater")
    return value


def _optional(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    try:
        result = Decimal(str(value))
    except Exception as error:  # noqa: BLE001 - surfaced as a domain error
        raise ValueError(f"{name} must be numeric") from error
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    return result


def _positive_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if decision_less_equal(result, 0):
        raise ValueError(f"{name} must be positive")
    return result


def _fraction_decimal(value: Any, name: str) -> Decimal:
    result = _positive_decimal(value, name)
    if decision_greater(result, Decimal("1")):
        raise ValueError(f"{name} must be between 0 and 1")
    return result


__all__ = [
    "TRANCHE_FRACTION_SUM_TOLERANCE",
    "TRANCHE_SCHEDULE_PARAMETER_STATUS",
    "TRANCHE_SIZING_FEATURE_ID",
    "TRANCHE_SIZING_POLICY_VERSION",
    "TRANCHE_SIZING_REASON_CODES",
    "TrancheAllocation",
    "TrancheSizingResult",
    "calculate_tranche_size",
    "next_tranche_for_position",
    "tranche_schedule_from_config",
    "validate_tranche_schedule",
]
