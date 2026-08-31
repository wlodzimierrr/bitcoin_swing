"""Trailing stop progression (BTC-156).

Rulebook 22, for a long:

    CandidateStop_t = NewHigherLow - VolatilityBuffer
    Stop_t          = max(Stop_{t-1}, CandidateStop_t)

and mirrored for a short, where the candidate sits a buffer *above* a new lower
high and the stop takes the minimum. The hard invariant follows from the ratchet
rather than being bolted on beside it: a long stop may never move lower, and a
short stop may never move higher. It is enforced when the stop is computed and
again when the result is persisted.

Two things the formula alone does not say.

"Trailing stops should advance only when new confirmed structure forms", and
"no daily mechanical trailing is required". So an absent structure price is not
an error and not a reason to hold at some decayed level; it simply produces no
advance. A candidate that fails to beat the standing stop likewise holds, which
is the ordinary case rather than a fault.

The three stages are derived, never asserted. Stage 1 is the wide structural
invalidation stop from BTC-142 before anything has advanced, Stage 2 is the
first advance under a new higher low, and Stage 3 is every advance after that.
Deriving the stage from the advance count means it cannot disagree with the
stop history, in the same way BTC-150 derives OPEN_ADDED from its tranche count.

Scope. This decides where the stop goes. BTC-150 owns whether the move is
recordable and refuses one that widens; BTC-141 owns the buffer; BTC-140 and
BTC-142 own the initial structural stop this progression starts from.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from btc_predictor.quant.comparisons import (
    decision_greater,
    decision_greater_equal,
    decision_less,
    decision_less_equal,
)
from btc_predictor.risk.invalidation import (
    INVALIDATION_DIRECTIONS,
    LONG_DIRECTION,
    SHORT_DIRECTION,
)


TRAILING_STOP_FEATURE_ID = "TRAILING_STOP"
TRAILING_STOP_POLICY_VERSION = "TRAILING_STOP_V1"

THESIS_STOP = "THESIS_STOP"
CONFIRMATION_STOP = "CONFIRMATION_STOP"
PROFIT_PROTECTION_TRAIL = "PROFIT_PROTECTION_TRAIL"
TRAILING_STOP_STAGES = (THESIS_STOP, CONFIRMATION_STOP, PROFIT_PROTECTION_TRAIL)

TRAILING_STOP_REASON_CODES = (
    "TRAILING_STOP_ADVANCED",
    "TRAILING_STOP_HELD",
    "TRAILING_STOP_NO_NEW_STRUCTURE",
    "TRAILING_STOP_INPUT_MISSING",
    "TRAILING_STOP_BUFFER_INCOMPLETE",
    "TRAILING_STOP_CANDIDATE_NON_POSITIVE",
    "TRAILING_STOP_CANDIDATE_BEYOND_PRICE",
)


@dataclass(frozen=True)
class TrailingStopResult:
    feature_id: str
    policy_version: str
    direction: str
    stage: str
    advance_count: int
    previous_stop: Decimal | None
    structure_price: Decimal | None
    buffer: Decimal | None
    candidate_stop: Decimal | None
    stop_price: Decimal | None
    current_price: Decimal | None
    advanced: bool
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        if self.stage not in TRAILING_STOP_STAGES:
            raise ValueError(f"stage must be one of {TRAILING_STOP_STAGES}")
        if self.advance_count < 0:
            raise ValueError("advance_count must not be negative")
        if self.stage != _stage_for(self.advance_count):
            raise ValueError("stage does not match advance_count")
        if self.complete and self.stop_price is None:
            raise ValueError("a complete trailing stop requires a stop price")
        # The hard invariant, re-checked at the persistence boundary so a
        # hand-built or mutated record cannot record a loosened stop.
        if self.previous_stop is not None and self.stop_price is not None:
            if _moves_backwards(
                direction=self.direction,
                previous_stop=self.previous_stop,
                stop_price=self.stop_price,
            ):
                raise ValueError(
                    "a long stop may never move lower and a short stop may "
                    "never move higher",
                )
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "direction": self.direction,
            "stage": self.stage,
            "advance_count": self.advance_count,
            "previous_stop": _optional(self.previous_stop),
            "structure_price": _optional(self.structure_price),
            "buffer": _optional(self.buffer),
            "candidate_stop": _optional(self.candidate_stop),
            "stop_price": _optional(self.stop_price),
            "current_price": _optional(self.current_price),
            "advanced": self.advanced,
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def calculate_trailing_stop(
    *,
    direction: str,
    previous_stop: Any | None,
    structure_price: Any | None = None,
    buffer: Any | None = None,
    advance_count: int = 0,
    current_price: Any | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> TrailingStopResult:
    """Advance a stop under new confirmed structure, or hold it.

    ``structure_price`` is the new higher low for a long and the new lower high
    for a short. Omitting it means no new structure has formed, which holds the
    standing stop rather than failing. ``current_price``, when supplied, refuses
    a candidate that has already been passed by price and would stop the
    position out on placement.
    """

    if direction not in INVALIDATION_DIRECTIONS:
        raise ValueError(f"direction must be one of {INVALIDATION_DIRECTIONS}")
    if not isinstance(advance_count, int) or isinstance(advance_count, bool):
        raise ValueError("advance_count must be an integer")
    if advance_count < 0:
        raise ValueError("advance_count must not be negative")

    metadata = dict(config_metadata or {})
    standing = (
        _positive_decimal(previous_stop, "previous_stop")
        if previous_stop is not None
        else None
    )
    structure = (
        _positive_decimal(structure_price, "structure_price")
        if structure_price is not None
        else None
    )
    buffer_value = (
        _non_negative_decimal(buffer, "buffer") if buffer is not None else None
    )
    price = (
        _positive_decimal(current_price, "current_price")
        if current_price is not None
        else None
    )

    def held(reason_codes: tuple[str, ...], candidate: Decimal | None = None):
        return TrailingStopResult(
            feature_id=TRAILING_STOP_FEATURE_ID,
            policy_version=TRAILING_STOP_POLICY_VERSION,
            direction=direction,
            stage=_stage_for(advance_count),
            advance_count=advance_count,
            previous_stop=standing,
            structure_price=structure,
            buffer=buffer_value,
            candidate_stop=candidate,
            stop_price=standing,
            current_price=price,
            advanced=False,
            config_metadata=metadata,
            complete=standing is not None,
            reason_codes=reason_codes,
        )

    if structure is None:
        # Rulebook 22: advance only when new confirmed structure forms. No
        # structure is the ordinary quiet case, not a failure.
        return held(
            ("TRAILING_STOP_NO_NEW_STRUCTURE",)
            if standing is not None
            else ("TRAILING_STOP_NO_NEW_STRUCTURE", "TRAILING_STOP_INPUT_MISSING")
        )
    if buffer_value is None:
        return held(("TRAILING_STOP_BUFFER_INCOMPLETE",))

    candidate = (
        structure - buffer_value
        if direction == LONG_DIRECTION
        else structure + buffer_value
    )
    if decision_less_equal(candidate, 0):
        return held(("TRAILING_STOP_CANDIDATE_NON_POSITIVE",), candidate=candidate)
    if price is not None and _beyond_price(
        direction=direction,
        candidate=candidate,
        current_price=price,
    ):
        # A long stop at or above the current price is an immediate exit
        # dressed up as a stop move.
        return held(("TRAILING_STOP_CANDIDATE_BEYOND_PRICE",), candidate=candidate)

    if standing is not None and not _improves(
        direction=direction,
        candidate=candidate,
        previous_stop=standing,
    ):
        # max(Stop_{t-1}, Candidate) for a long: the standing stop wins.
        return held(("TRAILING_STOP_HELD",), candidate=candidate)

    return TrailingStopResult(
        feature_id=TRAILING_STOP_FEATURE_ID,
        policy_version=TRAILING_STOP_POLICY_VERSION,
        direction=direction,
        stage=_stage_for(advance_count + 1),
        advance_count=advance_count + 1,
        previous_stop=standing,
        structure_price=structure,
        buffer=buffer_value,
        candidate_stop=candidate,
        stop_price=candidate,
        current_price=price,
        advanced=True,
        config_metadata=metadata,
        complete=True,
        reason_codes=("TRAILING_STOP_ADVANCED",),
    )


def trail_stop_for_position(
    lifecycle: Any,
    *,
    structure_price: Any | None = None,
    buffer: Any | None = None,
    current_price: Any | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> TrailingStopResult:
    """Canonical path: advance the stop a BTC-150 position already carries.

    Direction, the standing stop, and the advance count all come from the
    ledger, so the stage cannot disagree with the stop history and no caller
    restates the stop it is trailing. ``buffer`` accepts a BTC-141 result
    directly; an incomplete one yields no advance.
    """

    direction = getattr(lifecycle, "direction", None)
    if direction is None:
        raise ValueError("lifecycle must expose a direction")

    return calculate_trailing_stop(
        direction=direction,
        previous_stop=getattr(lifecycle, "stop_price", None),
        structure_price=structure_price,
        buffer=_buffer_value(buffer),
        advance_count=stop_advance_count(lifecycle),
        current_price=current_price,
        config_metadata=config_metadata,
    )


def stop_advance_count(lifecycle: Any) -> int:
    """Count the stop moves a lifecycle has already recorded.

    The entry establishes the thesis stop rather than advancing it, so only
    accepted transitions that carried a stop after the entry are counted.
    """

    transitions = getattr(lifecycle, "transitions", None)
    if transitions is None:
        raise ValueError("lifecycle must expose transitions")
    count = 0
    entered = False
    for transition in transitions:
        if not getattr(transition, "accepted", False):
            continue
        if not entered:
            entered = getattr(transition, "event", None) == "ENTER"
            continue
        if getattr(transition, "stop_price", None) is not None:
            count += 1
    return count


def _stage_for(advance_count: int) -> str:
    if advance_count <= 0:
        return THESIS_STOP
    if advance_count == 1:
        return CONFIRMATION_STOP
    return PROFIT_PROTECTION_TRAIL


def _improves(
    *,
    direction: str,
    candidate: Decimal,
    previous_stop: Decimal,
) -> bool:
    if direction == LONG_DIRECTION:
        return decision_greater(candidate, previous_stop)
    return decision_less(candidate, previous_stop)


def _moves_backwards(
    *,
    direction: str,
    previous_stop: Decimal,
    stop_price: Decimal,
) -> bool:
    if direction == LONG_DIRECTION:
        return decision_less(stop_price, previous_stop)
    return decision_greater(stop_price, previous_stop)


def _beyond_price(
    *,
    direction: str,
    candidate: Decimal,
    current_price: Decimal,
) -> bool:
    if direction == LONG_DIRECTION:
        return decision_greater_equal(candidate, current_price)
    return decision_less_equal(candidate, current_price)


def _buffer_value(buffer: Any | None) -> Decimal | None:
    if buffer is None:
        return None
    if isinstance(buffer, (Decimal, int, float, str)):
        return _non_negative_decimal(buffer, "buffer")
    record = getattr(buffer, "as_record", None)
    source: Mapping[str, Any]
    if isinstance(buffer, Mapping):
        source = buffer
    elif callable(record):
        source = record()
    else:
        raise TypeError("buffer must be numeric, a mapping, or expose as_record()")
    if not source.get("complete"):
        return None
    value = source.get("buffer")
    return None if value is None else _non_negative_decimal(value, "buffer")


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


def _non_negative_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


__all__ = [
    "CONFIRMATION_STOP",
    "PROFIT_PROTECTION_TRAIL",
    "THESIS_STOP",
    "TRAILING_STOP_FEATURE_ID",
    "TRAILING_STOP_POLICY_VERSION",
    "TRAILING_STOP_REASON_CODES",
    "TRAILING_STOP_STAGES",
    "TrailingStopResult",
    "calculate_trailing_stop",
    "stop_advance_count",
    "trail_stop_for_position",
]
