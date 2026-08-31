"""Paper position state machine (BTC-150).

The seven declared states are:

    WATCH  PENDING_ENTRY  OPEN_INITIAL  OPEN_ADDED  DEFENSIVE  CLOSED  MISSED

They are finer-grained than ``portfolio.positions.status``, which only
distinguishes ``open`` / ``closed`` / ``missed``. The extra resolution is what
the lifecycle needs to make decisions:

``WATCH`` / ``PENDING_ENTRY``
    Pre-position states with no ``positions`` row yet. ``PENDING_ENTRY`` is the
    order-lifecycle state, not a score state: an entry order exists and has not
    filled. Rulebook 25 says the system is allowed to miss trades, so
    ``MISSED`` is the terminal for a pre-position lifecycle that never filled.

``OPEN_INITIAL`` / ``OPEN_ADDED``
    Distinguished purely by tranche count, so the state can never disagree with
    the tranche ledger. Rulebook 26 enters small and only then pyramids.

``DEFENSIVE``
    Rulebook 20 maps a Hold Score of 50-60 to "Defensive; tighten / consider
    trim", and rulebook 24 gives STRESS / CROWDING / EUPHORIA the shared effect
    ``NO ADDING``. That is the operative content of this state: **ADD is
    refused while defensive**. It is recoverable, because Hold Score is
    recomputed every cycle, and recovery returns to the state implied by the
    tranche count rather than to a remembered one.

Illegal transitions are recorded as rejected transitions carrying a reason
code, not raised. A refused ADD is exactly the audit trail paper trading needs.
Malformed input (a negative quantity, a naive datetime) still raises, matching
the rest of the risk and feature layers.

Scope. This module owns the position ledger and its invariants. It does not
decide *when* to act: Hold Score (BTC-152), Add Score (BTC-153), add
requirements (BTC-154), tranche sizing (BTC-155), trailing stop progression
(BTC-156), trim rules (BTC-157) and exit rules (BTC-158) supply the decisions
this machine then validates and records. The no-average-down invariant is
BTC-151 and is deliberately not enforced here; ``average_entry_price`` is
tracked so that ticket can bolt onto this state without restating the ledger.

One invariant is enforced here because it belongs to the ledger rather than to
any stop policy: rulebook 32 rule 3, "Never widen a stop after entry". BTC-156
decides where a stop goes; this module refuses to record one that moved the
wrong way.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from btc_predictor.data import require_utc_datetime
from btc_predictor.quant.comparisons import (
    decision_compare,
    decision_greater,
    decision_less,
    decision_less_equal,
)
from btc_predictor.risk.invalidation import (
    INVALIDATION_DIRECTIONS,
    LONG_DIRECTION,
)


POSITION_STATE_MACHINE_FEATURE_ID = "PAPER_POSITION_STATE_MACHINE"
POSITION_STATE_MACHINE_POLICY_VERSION = "PAPER_POSITION_STATE_MACHINE_V1"

WATCH = "WATCH"
PENDING_ENTRY = "PENDING_ENTRY"
OPEN_INITIAL = "OPEN_INITIAL"
OPEN_ADDED = "OPEN_ADDED"
DEFENSIVE = "DEFENSIVE"
CLOSED = "CLOSED"
MISSED = "MISSED"

POSITION_STATES = (
    WATCH,
    PENDING_ENTRY,
    OPEN_INITIAL,
    OPEN_ADDED,
    DEFENSIVE,
    CLOSED,
    MISSED,
)
PRE_POSITION_STATES = (WATCH, PENDING_ENTRY)
OPEN_POSITION_STATES = (OPEN_INITIAL, OPEN_ADDED, DEFENSIVE)
TERMINAL_POSITION_STATES = (CLOSED, MISSED)

OBSERVE = "OBSERVE"
ARM_ENTRY = "ARM_ENTRY"
DISARM_ENTRY = "DISARM_ENTRY"
ENTER = "ENTER"
HOLD = "HOLD"
ADD = "ADD"
STOP_MOVE = "STOP_MOVE"
TRIM = "TRIM"
DEFEND = "DEFEND"
RECOVER = "RECOVER"
EXIT = "EXIT"
MISS = "MISS"

POSITION_EVENTS = (
    OBSERVE,
    ARM_ENTRY,
    DISARM_ENTRY,
    ENTER,
    HOLD,
    ADD,
    STOP_MOVE,
    TRIM,
    DEFEND,
    RECOVER,
    EXIT,
    MISS,
)

# RECOVER cannot name a fixed target: leaving DEFENSIVE returns to whichever
# open state the tranche ledger implies. The sentinel keeps the table below
# declarative instead of hiding that rule in branching code.
OPEN_BY_TRANCHE_COUNT = "OPEN_BY_TRANCHE_COUNT"

POSITION_STATE_TRANSITIONS: dict[str, dict[str, str]] = {
    WATCH: {
        OBSERVE: WATCH,
        ARM_ENTRY: PENDING_ENTRY,
        MISS: MISSED,
    },
    PENDING_ENTRY: {
        OBSERVE: PENDING_ENTRY,
        DISARM_ENTRY: WATCH,
        ENTER: OPEN_INITIAL,
        MISS: MISSED,
    },
    OPEN_INITIAL: {
        HOLD: OPEN_INITIAL,
        STOP_MOVE: OPEN_INITIAL,
        TRIM: OPEN_INITIAL,
        ADD: OPEN_ADDED,
        DEFEND: DEFENSIVE,
        EXIT: CLOSED,
    },
    OPEN_ADDED: {
        HOLD: OPEN_ADDED,
        STOP_MOVE: OPEN_ADDED,
        TRIM: OPEN_ADDED,
        ADD: OPEN_ADDED,
        DEFEND: DEFENSIVE,
        EXIT: CLOSED,
    },
    DEFENSIVE: {
        HOLD: DEFENSIVE,
        STOP_MOVE: DEFENSIVE,
        TRIM: DEFENSIVE,
        RECOVER: OPEN_BY_TRANCHE_COUNT,
        EXIT: CLOSED,
    },
    CLOSED: {},
    MISSED: {},
}

# ``position_events.action`` accepts only these seven values. Pre-position
# events have no row to write, and DEFEND / RECOVER have no dedicated action,
# so they persist as HOLD (the position continues, unchanged in size) with the
# state carried by the transition record's reason codes. Replaying actions
# alone would lose DEFENSIVE; replaying the transition records does not.
PERSISTED_EVENT_ACTIONS: dict[str, str | None] = {
    OBSERVE: None,
    ARM_ENTRY: None,
    DISARM_ENTRY: None,
    ENTER: "ENTER",
    HOLD: "HOLD",
    ADD: "ADD",
    STOP_MOVE: "STOP_MOVE",
    TRIM: "TRIM",
    DEFEND: "HOLD",
    RECOVER: "HOLD",
    EXIT: "EXIT",
    MISS: "MISSED",
}

# ``positions.status`` values. The pre-position states map to no row at all.
PERSISTED_POSITION_STATUS: dict[str, str | None] = {
    WATCH: None,
    PENDING_ENTRY: None,
    OPEN_INITIAL: "open",
    OPEN_ADDED: "open",
    DEFENSIVE: "open",
    CLOSED: "closed",
    MISSED: "missed",
}

POSITION_STATE_REASON_CODES = (
    "POSITION_STATE_LIFECYCLE_STARTED",
    "POSITION_STATE_OBSERVED",
    "POSITION_STATE_ENTRY_ARMED",
    "POSITION_STATE_ENTRY_DISARMED",
    "POSITION_STATE_ENTERED",
    "POSITION_STATE_HELD",
    "POSITION_STATE_ADDED",
    "POSITION_STATE_STOP_MOVED",
    "POSITION_STATE_TRIMMED",
    "POSITION_STATE_DEFENSIVE",
    "POSITION_STATE_RECOVERED",
    "POSITION_STATE_CLOSED",
    "POSITION_STATE_MISSED",
    "POSITION_STATE_TRANSITION_NOT_PERMITTED",
    "POSITION_STATE_ADD_REFUSED_WHILE_DEFENSIVE",
    "POSITION_STATE_TERMINAL",
    "POSITION_STATE_EVENT_OUT_OF_ORDER",
    "POSITION_STATE_ENTRY_REQUIRES_STOP",
    "POSITION_STATE_STOP_REQUIRED",
    "POSITION_STATE_QUANTITY_REQUIRED",
    "POSITION_STATE_PRICE_REQUIRED",
    "POSITION_STATE_STOP_WOULD_WIDEN",
    "POSITION_STATE_TRIM_NOT_PARTIAL",
    "POSITION_STATE_EXIT_MUST_BE_FULL",
)

_ACCEPTED_REASON_CODES: dict[str, str] = {
    OBSERVE: "POSITION_STATE_OBSERVED",
    ARM_ENTRY: "POSITION_STATE_ENTRY_ARMED",
    DISARM_ENTRY: "POSITION_STATE_ENTRY_DISARMED",
    ENTER: "POSITION_STATE_ENTERED",
    HOLD: "POSITION_STATE_HELD",
    ADD: "POSITION_STATE_ADDED",
    STOP_MOVE: "POSITION_STATE_STOP_MOVED",
    TRIM: "POSITION_STATE_TRIMMED",
    DEFEND: "POSITION_STATE_DEFENSIVE",
    RECOVER: "POSITION_STATE_RECOVERED",
    EXIT: "POSITION_STATE_CLOSED",
    MISS: "POSITION_STATE_MISSED",
}


@dataclass(frozen=True)
class Tranche:
    """One filled entry tranche, in ledger order."""

    tranche_number: int
    entry_price: Decimal
    quantity: Decimal
    opened_at: datetime

    def as_record(self) -> dict[str, Any]:
        return {
            "tranche_number": self.tranche_number,
            "entry_price": str(self.entry_price),
            "quantity": str(self.quantity),
            "opened_at": self.opened_at.isoformat(),
        }


@dataclass(frozen=True)
class PositionTransition:
    """One applied or refused lifecycle event."""

    sequence: int
    event: str
    from_state: str
    to_state: str
    event_time: datetime
    accepted: bool
    persisted_action: str | None
    quantity_delta: Decimal | None
    price: Decimal | None
    stop_price: Decimal | None
    reason_codes: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "event": self.event,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "event_time": self.event_time.isoformat(),
            "accepted": self.accepted,
            "persisted_action": self.persisted_action,
            "quantity_delta": _optional(self.quantity_delta),
            "price": _optional(self.price),
            "stop_price": _optional(self.stop_price),
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class PositionLifecycle:
    """Immutable paper position state plus the transitions that produced it."""

    feature_id: str
    policy_version: str
    symbol: str
    direction: str
    state: str
    tranches: tuple[Tranche, ...]
    quantity: Decimal
    average_entry_price: Decimal | None
    stop_price: Decimal | None
    opened_at: datetime | None
    closed_at: datetime | None
    last_event_at: datetime | None
    transitions: tuple[PositionTransition, ...]
    config_metadata: dict[str, str]
    accepted: bool
    reason_codes: tuple[str, ...] = ()

    @property
    def tranche_count(self) -> int:
        return len(self.tranches)

    @property
    def is_open(self) -> bool:
        return self.state in OPEN_POSITION_STATES

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_POSITION_STATES

    @property
    def persisted_status(self) -> str | None:
        return PERSISTED_POSITION_STATUS[self.state]

    def as_record(self) -> dict[str, Any]:
        if self.is_open and decision_less_equal(self.quantity, 0):
            raise ValueError("an open position requires a positive quantity")
        if self.state in PRE_POSITION_STATES and self.tranches:
            raise ValueError("a pre-position state cannot hold tranches")
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "symbol": self.symbol,
            "direction": self.direction,
            "state": self.state,
            "persisted_status": self.persisted_status,
            "tranche_count": self.tranche_count,
            "tranches": [tranche.as_record() for tranche in self.tranches],
            "quantity": str(self.quantity),
            "average_entry_price": _optional(self.average_entry_price),
            "stop_price": _optional(self.stop_price),
            "opened_at": _optional_time(self.opened_at),
            "closed_at": _optional_time(self.closed_at),
            "last_event_at": _optional_time(self.last_event_at),
            "transitions": [item.as_record() for item in self.transitions],
            "config_metadata": dict(self.config_metadata),
            "accepted": self.accepted,
            "reason_codes": list(self.reason_codes),
        }


def start_position_lifecycle(
    *,
    symbol: str,
    direction: str = LONG_DIRECTION,
    state: str = WATCH,
    config_metadata: Mapping[str, str] | None = None,
) -> PositionLifecycle:
    """Open a lifecycle in a pre-position state.

    Rulebook 26 reaches ``WATCH`` when conviction is below 80 and goes straight
    to an entry otherwise, so a lifecycle may legitimately begin at either
    ``WATCH`` or ``PENDING_ENTRY``.
    """

    if not symbol:
        raise ValueError("symbol must not be empty")
    if direction not in INVALIDATION_DIRECTIONS:
        raise ValueError(f"direction must be one of {INVALIDATION_DIRECTIONS}")
    if state not in PRE_POSITION_STATES:
        raise ValueError(f"a lifecycle must start in one of {PRE_POSITION_STATES}")

    return PositionLifecycle(
        feature_id=POSITION_STATE_MACHINE_FEATURE_ID,
        policy_version=POSITION_STATE_MACHINE_POLICY_VERSION,
        symbol=symbol,
        direction=direction,
        state=state,
        tranches=(),
        quantity=Decimal("0"),
        average_entry_price=None,
        stop_price=None,
        opened_at=None,
        closed_at=None,
        last_event_at=None,
        transitions=(),
        config_metadata=dict(config_metadata or {}),
        accepted=True,
        reason_codes=("POSITION_STATE_LIFECYCLE_STARTED",),
    )


def apply_position_event(
    lifecycle: PositionLifecycle,
    *,
    event: str,
    event_time: datetime,
    quantity: Any | None = None,
    price: Any | None = None,
    stop_price: Any | None = None,
    reason_codes: Iterable[str] = (),
) -> PositionLifecycle:
    """Return the lifecycle after applying (or refusing) one event."""

    if not isinstance(lifecycle, PositionLifecycle):
        raise TypeError("lifecycle must be a PositionLifecycle")
    if event not in POSITION_EVENTS:
        raise ValueError(f"event must be one of {POSITION_EVENTS}")
    moment = require_utc_datetime(event_time, "event_time")
    supplied = tuple(reason_codes)

    quantity_value = (
        _positive_decimal(quantity, "quantity") if quantity is not None else None
    )
    price_value = _positive_decimal(price, "price") if price is not None else None
    stop_value = (
        _positive_decimal(stop_price, "stop_price") if stop_price is not None else None
    )

    if lifecycle.last_event_at is not None and moment < lifecycle.last_event_at:
        return _refuse(
            lifecycle,
            event=event,
            event_time=moment,
            quantity=quantity_value,
            price=price_value,
            stop_price=stop_value,
            codes=("POSITION_STATE_EVENT_OUT_OF_ORDER",) + supplied,
        )

    if lifecycle.is_terminal:
        return _refuse(
            lifecycle,
            event=event,
            event_time=moment,
            quantity=quantity_value,
            price=price_value,
            stop_price=stop_value,
            codes=(
                "POSITION_STATE_TERMINAL",
                "POSITION_STATE_TRANSITION_NOT_PERMITTED",
            )
            + supplied,
        )

    permitted = POSITION_STATE_TRANSITIONS[lifecycle.state]
    if event not in permitted:
        codes: tuple[str, ...] = ("POSITION_STATE_TRANSITION_NOT_PERMITTED",)
        if event == ADD and lifecycle.state == DEFENSIVE:
            # The whole point of DEFENSIVE: rulebook 24's shared NO ADDING
            # effect, made explicit rather than left to the caller.
            codes = ("POSITION_STATE_ADD_REFUSED_WHILE_DEFENSIVE",) + codes
        return _refuse(
            lifecycle,
            event=event,
            event_time=moment,
            quantity=quantity_value,
            price=price_value,
            stop_price=stop_value,
            codes=codes + supplied,
        )

    guard = _guard_event(
        lifecycle,
        event=event,
        quantity=quantity_value,
        price=price_value,
        stop_price=stop_value,
    )
    if guard is not None:
        return _refuse(
            lifecycle,
            event=event,
            event_time=moment,
            quantity=quantity_value,
            price=price_value,
            stop_price=stop_value,
            codes=guard + supplied,
        )

    target = permitted[event]
    return _accept(
        lifecycle,
        event=event,
        target=target,
        event_time=moment,
        quantity=quantity_value,
        price=price_value,
        stop_price=stop_value,
        supplied=supplied,
    )


def replay_position_lifecycle(
    events: Iterable[Mapping[str, Any]],
    *,
    symbol: str,
    direction: str = LONG_DIRECTION,
    state: str = WATCH,
    config_metadata: Mapping[str, str] | None = None,
) -> PositionLifecycle:
    """Rebuild a lifecycle from an ordered event log.

    Replaying the same log always yields the same state, which is what makes a
    persisted paper position reproducible.
    """

    lifecycle = start_position_lifecycle(
        symbol=symbol,
        direction=direction,
        state=state,
        config_metadata=config_metadata,
    )
    for entry in events:
        lifecycle = apply_position_event(
            lifecycle,
            event=entry["event"],
            event_time=entry["event_time"],
            quantity=entry.get("quantity"),
            price=entry.get("price"),
            stop_price=entry.get("stop_price"),
            reason_codes=entry.get("reason_codes", ()),
        )
    return lifecycle


def persisted_action_for_event(event: str) -> str | None:
    """Return the ``position_events.action`` value an event persists as."""

    if event not in POSITION_EVENTS:
        raise ValueError(f"event must be one of {POSITION_EVENTS}")
    return PERSISTED_EVENT_ACTIONS[event]


def persisted_status_for_state(state: str) -> str | None:
    """Return the ``positions.status`` value a state persists as, if any."""

    if state not in POSITION_STATES:
        raise ValueError(f"state must be one of {POSITION_STATES}")
    return PERSISTED_POSITION_STATUS[state]


def _guard_event(
    lifecycle: PositionLifecycle,
    *,
    event: str,
    quantity: Decimal | None,
    price: Decimal | None,
    stop_price: Decimal | None,
) -> tuple[str, ...] | None:
    """Return refusal codes for a permitted transition with bad arguments."""

    codes: list[str] = []

    if event in (ENTER, ADD, TRIM) and quantity is None:
        codes.append("POSITION_STATE_QUANTITY_REQUIRED")
    if event in (ENTER, ADD) and price is None:
        codes.append("POSITION_STATE_PRICE_REQUIRED")
    if event == ENTER and stop_price is None:
        # Rulebook 26 gates entry on a valid structural stop, and rulebook 32
        # rule 5 makes structure decide it. An entry without one is not sizeable.
        codes.append("POSITION_STATE_ENTRY_REQUIRES_STOP")
    if event == STOP_MOVE and stop_price is None:
        codes.append("POSITION_STATE_STOP_REQUIRED")

    if event == TRIM and quantity is not None:
        if not decision_less(quantity, lifecycle.quantity):
            # Removing the whole position is an EXIT; keeping TRIM partial is
            # what preserves "an open state always holds a positive quantity".
            codes.append("POSITION_STATE_TRIM_NOT_PARTIAL")

    if event == EXIT and quantity is not None:
        if decision_compare(quantity, lifecycle.quantity) != 0:
            codes.append("POSITION_STATE_EXIT_MUST_BE_FULL")

    if stop_price is not None and _stop_would_widen(lifecycle, stop_price):
        codes.append("POSITION_STATE_STOP_WOULD_WIDEN")

    return tuple(codes) if codes else None


def _stop_would_widen(lifecycle: PositionLifecycle, stop_price: Decimal) -> bool:
    """Rulebook 32 rule 3: never widen a stop after entry."""

    if lifecycle.stop_price is None:
        return False
    if lifecycle.direction == LONG_DIRECTION:
        return decision_less(stop_price, lifecycle.stop_price)
    return decision_greater(stop_price, lifecycle.stop_price)


def _accept(
    lifecycle: PositionLifecycle,
    *,
    event: str,
    target: str,
    event_time: datetime,
    quantity: Decimal | None,
    price: Decimal | None,
    stop_price: Decimal | None,
    supplied: tuple[str, ...],
) -> PositionLifecycle:
    tranches = lifecycle.tranches
    total = lifecycle.quantity
    delta: Decimal | None = None
    opened_at = lifecycle.opened_at
    closed_at = lifecycle.closed_at

    if event in (ENTER, ADD):
        if quantity is None or price is None:
            raise ValueError("an entry or add requires a quantity and a price")
        tranches = tranches + (
            Tranche(
                tranche_number=len(tranches) + 1,
                entry_price=price,
                quantity=quantity,
                opened_at=event_time,
            ),
        )
        total = total + quantity
        delta = quantity
        if event == ENTER:
            opened_at = event_time
    elif event == TRIM:
        if quantity is None:
            raise ValueError("a trim requires a quantity")
        remaining = total - quantity
        # Pro-rata across open tranches, so a partial exit leaves the weighted
        # average entry unchanged instead of silently re-basing it.
        factor = remaining / total
        tranches = tuple(
            Tranche(
                tranche_number=tranche.tranche_number,
                entry_price=tranche.entry_price,
                quantity=tranche.quantity * factor,
                opened_at=tranche.opened_at,
            )
            for tranche in tranches
        )
        total = remaining
        delta = -quantity
    elif event == EXIT:
        delta = -total
        total = Decimal("0")
        tranches = ()
        closed_at = event_time
    elif event == MISS:
        closed_at = event_time

    if target == OPEN_BY_TRANCHE_COUNT:
        target = OPEN_ADDED if len(tranches) > 1 else OPEN_INITIAL

    # A closed position keeps the average entry it was closed at; the open
    # tranche ledger is empty because nothing remains open.
    average_entry = (
        lifecycle.average_entry_price if event == EXIT else _average_entry(tranches)
    )

    transition = PositionTransition(
        sequence=len(lifecycle.transitions) + 1,
        event=event,
        from_state=lifecycle.state,
        to_state=target,
        event_time=event_time,
        accepted=True,
        persisted_action=PERSISTED_EVENT_ACTIONS[event],
        quantity_delta=delta,
        price=price,
        stop_price=stop_price,
        reason_codes=(_ACCEPTED_REASON_CODES[event],) + supplied,
    )

    return PositionLifecycle(
        feature_id=lifecycle.feature_id,
        policy_version=lifecycle.policy_version,
        symbol=lifecycle.symbol,
        direction=lifecycle.direction,
        state=target,
        tranches=tranches,
        quantity=total,
        average_entry_price=average_entry,
        stop_price=stop_price if stop_price is not None else lifecycle.stop_price,
        opened_at=opened_at,
        closed_at=closed_at,
        last_event_at=event_time,
        transitions=lifecycle.transitions + (transition,),
        config_metadata=dict(lifecycle.config_metadata),
        accepted=True,
        reason_codes=transition.reason_codes,
    )


def _refuse(
    lifecycle: PositionLifecycle,
    *,
    event: str,
    event_time: datetime,
    quantity: Decimal | None,
    price: Decimal | None,
    stop_price: Decimal | None,
    codes: tuple[str, ...],
) -> PositionLifecycle:
    """Record a refused event without advancing state or the ledger."""

    transition = PositionTransition(
        sequence=len(lifecycle.transitions) + 1,
        event=event,
        from_state=lifecycle.state,
        to_state=lifecycle.state,
        event_time=event_time,
        accepted=False,
        persisted_action=None,
        quantity_delta=None,
        price=price,
        stop_price=stop_price,
        reason_codes=codes,
    )
    return PositionLifecycle(
        feature_id=lifecycle.feature_id,
        policy_version=lifecycle.policy_version,
        symbol=lifecycle.symbol,
        direction=lifecycle.direction,
        state=lifecycle.state,
        tranches=lifecycle.tranches,
        quantity=lifecycle.quantity,
        average_entry_price=lifecycle.average_entry_price,
        stop_price=lifecycle.stop_price,
        opened_at=lifecycle.opened_at,
        closed_at=lifecycle.closed_at,
        # A refused event never becomes the point-in-time watermark, so it
        # cannot advance the clock past a legitimate later event.
        last_event_at=lifecycle.last_event_at,
        transitions=lifecycle.transitions + (transition,),
        config_metadata=dict(lifecycle.config_metadata),
        accepted=False,
        reason_codes=codes,
    )


def _average_entry(tranches: tuple[Tranche, ...]) -> Decimal | None:
    """Weighted average entry, pinned to BTC-047 ``weighted_average_entry``."""

    if not tranches:
        return None
    total = sum((tranche.quantity for tranche in tranches), Decimal("0"))
    if total == 0:
        return None
    numerator = sum(
        (tranche.entry_price * tranche.quantity for tranche in tranches),
        Decimal("0"),
    )
    return numerator / total


def _optional(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _optional_time(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _positive_decimal(value: Any, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as error:  # noqa: BLE001 - surfaced as a domain error
        raise ValueError(f"{name} must be numeric") from error
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    if decision_less_equal(result, 0):
        raise ValueError(f"{name} must be positive")
    return result


__all__ = [
    "ADD",
    "ARM_ENTRY",
    "CLOSED",
    "DEFEND",
    "DEFENSIVE",
    "DISARM_ENTRY",
    "ENTER",
    "EXIT",
    "HOLD",
    "MISS",
    "MISSED",
    "OBSERVE",
    "OPEN_ADDED",
    "OPEN_BY_TRANCHE_COUNT",
    "OPEN_INITIAL",
    "OPEN_POSITION_STATES",
    "PENDING_ENTRY",
    "PERSISTED_EVENT_ACTIONS",
    "PERSISTED_POSITION_STATUS",
    "POSITION_EVENTS",
    "POSITION_STATES",
    "POSITION_STATE_MACHINE_FEATURE_ID",
    "POSITION_STATE_MACHINE_POLICY_VERSION",
    "POSITION_STATE_REASON_CODES",
    "POSITION_STATE_TRANSITIONS",
    "PRE_POSITION_STATES",
    "RECOVER",
    "STOP_MOVE",
    "TERMINAL_POSITION_STATES",
    "TRIM",
    "WATCH",
    "PositionLifecycle",
    "PositionTransition",
    "Tranche",
    "apply_position_event",
    "persisted_action_for_event",
    "persisted_status_for_state",
    "replay_position_lifecycle",
    "start_position_lifecycle",
]
