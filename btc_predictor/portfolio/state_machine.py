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

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
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
POSITION_TRANSITION_RECORD_VERSION = "PAPER_POSITION_TRANSITION_V1"

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
    "POSITION_STATE_STOP_NOT_APPLICABLE",
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
        _validate_tranche(self)
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
    requested_quantity: Decimal | None
    quantity_delta: Decimal | None
    price: Decimal | None
    stop_price: Decimal | None
    reason_codes: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        _validate_transition(self)
        return {
            "record_version": POSITION_TRANSITION_RECORD_VERSION,
            "sequence": self.sequence,
            "event": self.event,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "event_time": self.event_time.isoformat(),
            "accepted": self.accepted,
            "persisted_action": self.persisted_action,
            "requested_quantity": _optional(self.requested_quantity),
            "quantity_delta": _optional(self.quantity_delta),
            "price": _optional(self.price),
            "stop_price": _optional(self.stop_price),
            "reason_codes": list(self.reason_codes),
        }

    def as_position_event_record(self) -> dict[str, Any] | None:
        """Return the schema-compatible portion of an accepted DB event row.

        Account, position, and recommendation identifiers belong to the caller.
        The versioned transition payload lives in ``notes`` because the legacy
        action enum is deliberately coarser than the lifecycle event enum.
        """

        record = self.as_record()
        if self.persisted_action is None:
            return None
        quantity = self.requested_quantity
        if quantity is None and self.quantity_delta is not None:
            quantity = abs(self.quantity_delta)
        return {
            "event_time": self.event_time,
            "action": self.persisted_action,
            "quantity": quantity,
            "price": self.price,
            "notes": json.dumps(record, sort_keys=True, separators=(",", ":")),
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
        _validate_lifecycle(self)
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

    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("symbol must not be empty")
    if direction not in INVALIDATION_DIRECTIONS:
        raise ValueError(f"direction must be one of {INVALIDATION_DIRECTIONS}")
    if state not in PRE_POSITION_STATES:
        raise ValueError(f"a lifecycle must start in one of {PRE_POSITION_STATES}")

    result = PositionLifecycle(
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
        config_metadata=_config_metadata(config_metadata or {}),
        accepted=True,
        reason_codes=("POSITION_STATE_LIFECYCLE_STARTED",),
    )
    _validate_lifecycle(result)
    return result


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
    _validate_lifecycle(lifecycle)
    if event not in POSITION_EVENTS:
        raise ValueError(f"event must be one of {POSITION_EVENTS}")
    moment = _parse_utc(event_time, "event_time")
    supplied = _reason_codes(reason_codes)

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
            codes=_merge_reason_codes(
                ("POSITION_STATE_EVENT_OUT_OF_ORDER",),
                supplied,
            ),
        )

    if lifecycle.is_terminal:
        return _refuse(
            lifecycle,
            event=event,
            event_time=moment,
            quantity=quantity_value,
            price=price_value,
            stop_price=stop_value,
            codes=_merge_reason_codes(
                (
                    "POSITION_STATE_TERMINAL",
                    "POSITION_STATE_TRANSITION_NOT_PERMITTED",
                ),
                supplied,
            ),
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
            codes=_merge_reason_codes(codes, supplied),
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
            codes=_merge_reason_codes(guard, supplied),
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
    """Rebuild a lifecycle from commands or authoritative transition records.

    Records emitted by :meth:`PositionTransition.as_record` are verified
    field-for-field while replaying. Database rows produced by
    :func:`position_event_records` are accepted through their versioned
    ``notes`` payload. Action-only rows are intentionally insufficient because
    ``HOLD`` cannot distinguish HOLD, DEFEND, and RECOVER.
    """

    lifecycle = start_position_lifecycle(
        symbol=symbol,
        direction=direction,
        state=state,
        config_metadata=config_metadata,
    )
    for entry in events:
        record = _as_mapping(entry, "event")
        transition_record = _persisted_transition_record(record)
        if transition_record is not None:
            lifecycle = _replay_transition_record(lifecycle, transition_record)
            continue
        lifecycle = apply_position_event(
            lifecycle,
            event=record["event"],
            event_time=_parse_utc(record["event_time"], "event_time"),
            quantity=record.get("quantity"),
            price=record.get("price"),
            stop_price=record.get("stop_price"),
            reason_codes=record.get("reason_codes", ()),
        )
    return lifecycle


def restore_position_lifecycle(record: Mapping[str, Any]) -> PositionLifecycle:
    """Restore and verify a complete lifecycle snapshot from ``as_record()``."""

    source = _as_mapping(record, "lifecycle record")
    transitions = source.get("transitions")
    if not isinstance(transitions, list):
        raise ValueError("transitions must be a list")
    if transitions:
        first = _as_mapping(transitions[0], "transition")
        initial_state = first.get("from_state")
    else:
        initial_state = source.get("state")
    if initial_state not in PRE_POSITION_STATES:
        raise ValueError("persisted lifecycle must begin in a pre-position state")
    lifecycle = replay_position_lifecycle(
        transitions,
        symbol=_required_string(source, "symbol"),
        direction=_required_string(source, "direction"),
        state=initial_state,
        config_metadata=_config_metadata(source.get("config_metadata", {})),
    )
    if lifecycle.as_record() != dict(source):
        raise ValueError("persisted lifecycle does not match replayed transitions")
    return lifecycle


def position_event_records(
    lifecycle: PositionLifecycle,
) -> tuple[dict[str, Any], ...]:
    """Return transition rows compatible with ``position_events``.

    Accepted pre-position transitions have no schema action and remain in the
    authoritative lifecycle snapshot. Refusals persist as schema-valid HOLD
    rows whose versioned payload keeps ``accepted = false`` and the attempted
    event. Rows are rebased to a contiguous replay sequence because accepted
    pre-position transitions have no ``positions`` row.
    """

    _validate_lifecycle(lifecycle)
    records = []
    sequence = 1
    for transition in lifecycle.transitions:
        row = transition.as_position_event_record()
        if row is None:
            continue
        payload = json.loads(row["notes"])
        payload["sequence"] = sequence
        row["notes"] = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )
        records.append(row)
        sequence += 1
    return tuple(records)


def replay_position_event_records(
    records: Iterable[Mapping[str, Any]],
    *,
    symbol: str,
    direction: str = LONG_DIRECTION,
    config_metadata: Mapping[str, str] | None = None,
) -> PositionLifecycle:
    """Rebuild post-fill state from rows emitted by ``position_event_records``."""

    rows = tuple(_as_mapping(item, "position event") for item in records)
    if not rows:
        raise ValueError("position event replay requires at least one row")
    first = _persisted_transition_record(rows[0])
    if first is None:
        raise ValueError("position event row lacks a lifecycle transition payload")
    initial_state = first.get("from_state")
    if initial_state not in PRE_POSITION_STATES:
        raise ValueError("position event replay must begin before a position fill")
    return replay_position_lifecycle(
        rows,
        symbol=symbol,
        direction=direction,
        state=initial_state,
        config_metadata=config_metadata,
    )


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
    if stop_price is not None and event not in (ENTER, ADD, STOP_MOVE):
        codes.append("POSITION_STATE_STOP_NOT_APPLICABLE")

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
        # ``positions.status = missed`` is schema-valid but ``opened_at`` is
        # non-nullable. For an unfilled lifecycle this timestamp marks creation
        # of the terminal missed row, not an execution fill.
        opened_at = event_time
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
        requested_quantity=quantity,
        quantity_delta=delta,
        price=price,
        stop_price=stop_price,
        reason_codes=_merge_reason_codes(
            (_ACCEPTED_REASON_CODES[event],),
            supplied,
        ),
    )

    result = PositionLifecycle(
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
    _validate_lifecycle(result)
    return result


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
        # The schema has no REFUSED action. HOLD truthfully records that the
        # ledger did not change; the versioned notes payload retains the
        # attempted event and ``accepted = false`` for authoritative replay.
        persisted_action="HOLD",
        requested_quantity=quantity,
        quantity_delta=None,
        price=price,
        stop_price=stop_price,
        reason_codes=codes,
    )
    result = PositionLifecycle(
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
    _validate_lifecycle(result)
    return result


def _persisted_transition_record(
    record: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    if "event" in record and "accepted" in record:
        return record
    if "action" not in record or "notes" not in record:
        return None
    notes = record.get("notes")
    if not isinstance(notes, str) or not notes:
        raise ValueError("position event row lacks a lifecycle transition payload")
    try:
        payload = json.loads(notes)
    except json.JSONDecodeError as error:
        raise ValueError("position event notes are not valid lifecycle JSON") from error
    payload = _as_mapping(payload, "position event lifecycle payload")
    transition = _transition_from_record(payload)
    if record.get("action") != transition.persisted_action:
        raise ValueError("position event action does not match lifecycle payload")
    if _parse_utc(record.get("event_time"), "event_time") != transition.event_time:
        raise ValueError("position event time does not match lifecycle payload")
    outer_quantity = _optional_positive_decimal(record.get("quantity"), "quantity")
    expected_quantity = transition.requested_quantity
    if expected_quantity is None and transition.quantity_delta is not None:
        expected_quantity = abs(transition.quantity_delta)
    if outer_quantity != expected_quantity:
        raise ValueError("position event quantity does not match lifecycle payload")
    outer_price = _optional_positive_decimal(record.get("price"), "price")
    if outer_price != transition.price:
        raise ValueError("position event price does not match lifecycle payload")
    return payload


def _replay_transition_record(
    lifecycle: PositionLifecycle,
    record: Mapping[str, Any],
) -> PositionLifecycle:
    expected = _transition_from_record(record)
    if expected.sequence != len(lifecycle.transitions) + 1:
        raise ValueError("transition sequence is not contiguous")
    if expected.from_state != lifecycle.state:
        raise ValueError("transition from_state does not match replay state")

    kwargs = {
        "event": expected.event,
        "event_time": expected.event_time,
        "quantity": expected.requested_quantity,
        "price": expected.price,
        "stop_price": expected.stop_price,
    }
    probe = apply_position_event(lifecycle, **kwargs)
    base_codes = probe.transitions[-1].reason_codes
    if expected.reason_codes[: len(base_codes)] != base_codes:
        raise ValueError("transition reason codes do not match replayed event")
    supplied = expected.reason_codes[len(base_codes) :]
    replayed = apply_position_event(lifecycle, reason_codes=supplied, **kwargs)
    if replayed.transitions[-1] != expected:
        raise ValueError("transition record does not match replayed event")
    return replayed


def _transition_from_record(record: Mapping[str, Any]) -> PositionTransition:
    source = _as_mapping(record, "transition")
    if source.get("record_version") != POSITION_TRANSITION_RECORD_VERSION:
        raise ValueError(
            f"record_version must be {POSITION_TRANSITION_RECORD_VERSION}",
        )
    try:
        sequence = int(source["sequence"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("transition sequence must be an integer") from error
    accepted = source.get("accepted")
    if not isinstance(accepted, bool):
        raise ValueError("transition accepted must be a bool")
    persisted_action = source.get("persisted_action")
    if persisted_action is not None and not isinstance(persisted_action, str):
        raise ValueError("persisted_action must be a string or null")
    transition = PositionTransition(
        sequence=sequence,
        event=_required_string(source, "event"),
        from_state=_required_string(source, "from_state"),
        to_state=_required_string(source, "to_state"),
        event_time=_parse_utc(source.get("event_time"), "event_time"),
        accepted=accepted,
        persisted_action=persisted_action,
        requested_quantity=_optional_positive_decimal(
            source.get("requested_quantity"),
            "requested_quantity",
        ),
        quantity_delta=_optional_decimal(
            source.get("quantity_delta"),
            "quantity_delta",
        ),
        price=_optional_positive_decimal(source.get("price"), "price"),
        stop_price=_optional_positive_decimal(
            source.get("stop_price"),
            "stop_price",
        ),
        reason_codes=_reason_codes(source.get("reason_codes", ())),
    )
    _validate_transition(transition)
    return transition


def _validate_lifecycle(lifecycle: PositionLifecycle) -> None:
    if lifecycle.feature_id != POSITION_STATE_MACHINE_FEATURE_ID:
        raise ValueError(f"feature_id must be {POSITION_STATE_MACHINE_FEATURE_ID}")
    if lifecycle.policy_version != POSITION_STATE_MACHINE_POLICY_VERSION:
        raise ValueError(
            f"policy_version must be {POSITION_STATE_MACHINE_POLICY_VERSION}",
        )
    _required_string({"symbol": lifecycle.symbol}, "symbol")
    if lifecycle.direction not in INVALIDATION_DIRECTIONS:
        raise ValueError(f"direction must be one of {INVALIDATION_DIRECTIONS}")
    if lifecycle.state not in POSITION_STATES:
        raise ValueError(f"state must be one of {POSITION_STATES}")
    if not isinstance(lifecycle.accepted, bool):
        raise ValueError("accepted must be a bool")
    _config_metadata(lifecycle.config_metadata)
    quantity = _non_negative_decimal(lifecycle.quantity, "quantity")
    average = _optional_positive_decimal(
        lifecycle.average_entry_price,
        "average_entry_price",
    )
    stop = _optional_positive_decimal(lifecycle.stop_price, "stop_price")
    opened = _optional_utc(lifecycle.opened_at, "opened_at")
    closed = _optional_utc(lifecycle.closed_at, "closed_at")
    last_event = _optional_utc(lifecycle.last_event_at, "last_event_at")
    reasons = _reason_codes(lifecycle.reason_codes)
    if reasons != lifecycle.reason_codes:
        raise ValueError("reason_codes must be unique and canonically ordered")

    if not isinstance(lifecycle.tranches, tuple):
        raise TypeError("tranches must be a tuple")
    for expected_number, tranche in enumerate(lifecycle.tranches, start=1):
        _validate_tranche(tranche)
        if tranche.tranche_number != expected_number:
            raise ValueError("tranche numbers must be contiguous in ledger order")
    ledger_quantity = sum(
        (item.quantity for item in lifecycle.tranches),
        Decimal("0"),
    )

    if lifecycle.state in PRE_POSITION_STATES:
        if lifecycle.tranches or quantity != 0:
            raise ValueError("a pre-position state cannot hold tranches or quantity")
        if any(value is not None for value in (average, stop, opened, closed)):
            raise ValueError("a pre-position state cannot hold position economics")
    elif lifecycle.state in OPEN_POSITION_STATES:
        if quantity <= 0 or not lifecycle.tranches:
            raise ValueError(
                "an open position requires a positive quantity and tranche ledger",
            )
        if quantity != ledger_quantity:
            raise ValueError("position quantity must equal the tranche ledger")
        expected_average = _average_entry(lifecycle.tranches)
        if average != expected_average:
            raise ValueError("average entry must equal the tranche ledger")
        if stop is None or opened is None or closed is not None:
            raise ValueError("an open position requires its stop and open time")
        if lifecycle.state == OPEN_INITIAL and len(lifecycle.tranches) != 1:
            raise ValueError("OPEN_INITIAL requires exactly one tranche")
        if lifecycle.state == OPEN_ADDED and len(lifecycle.tranches) <= 1:
            raise ValueError("OPEN_ADDED requires more than one tranche")
        if opened != lifecycle.tranches[0].opened_at:
            raise ValueError("opened_at must match the initial tranche")
        if last_event is not None and any(
            item.opened_at < opened or item.opened_at > last_event
            for item in lifecycle.tranches
        ):
            raise ValueError("tranche times must fall within the accepted lifecycle")
    elif lifecycle.state == CLOSED:
        if lifecycle.tranches or quantity != 0:
            raise ValueError("CLOSED cannot retain open quantity")
        if any(value is None for value in (average, stop, opened, closed)):
            raise ValueError("CLOSED requires its final position economics")
        if closed < opened:
            raise ValueError("closed_at must not precede opened_at")
    else:
        if lifecycle.tranches or quantity != 0 or average is not None or stop is not None:
            raise ValueError("MISSED must remain position-free")
        if opened is None or closed is None or opened != closed:
            raise ValueError("MISSED requires one schema-compatible terminal time")

    _validate_transition_chain(lifecycle, last_event)
    if lifecycle.state in TERMINAL_POSITION_STATES and closed != last_event:
        raise ValueError("terminal time must match the terminal transition")


def _validate_transition_chain(
    lifecycle: PositionLifecycle,
    last_event: datetime | None,
) -> None:
    if not isinstance(lifecycle.transitions, tuple):
        raise TypeError("transitions must be a tuple")
    if not lifecycle.transitions:
        if last_event is not None:
            raise ValueError("last_event_at requires at least one transition")
        if lifecycle.state not in PRE_POSITION_STATES:
            raise ValueError("a position state requires transition history")
        if not lifecycle.accepted or lifecycle.reason_codes != (
            "POSITION_STATE_LIFECYCLE_STARTED",
        ):
            raise ValueError("a new lifecycle requires its start reason")
        return

    state = lifecycle.transitions[0].from_state
    if state not in PRE_POSITION_STATES:
        raise ValueError("transition history must begin before a position fill")
    accepted_time: datetime | None = None
    for sequence, transition in enumerate(lifecycle.transitions, start=1):
        _validate_transition(transition)
        if transition.sequence != sequence:
            raise ValueError("transition sequence must be contiguous")
        if transition.from_state != state:
            raise ValueError("transition state chain is discontinuous")
        if transition.accepted:
            if accepted_time is not None and transition.event_time < accepted_time:
                raise ValueError("accepted transition times must be non-decreasing")
            accepted_time = transition.event_time
        state = transition.to_state
    last = lifecycle.transitions[-1]
    if lifecycle.state != state:
        raise ValueError("lifecycle state must match the transition chain")
    if last_event != accepted_time:
        raise ValueError("last_event_at must match the latest accepted transition")
    if lifecycle.accepted != last.accepted or lifecycle.reason_codes != last.reason_codes:
        raise ValueError("lifecycle outcome must match its latest transition")


def _validate_transition(transition: PositionTransition) -> None:
    if isinstance(transition.sequence, bool) or not isinstance(
        transition.sequence,
        int,
    ):
        raise TypeError("transition sequence must be an integer")
    if transition.sequence < 1:
        raise ValueError("transition sequence must be positive")
    if transition.event not in POSITION_EVENTS:
        raise ValueError(f"event must be one of {POSITION_EVENTS}")
    if transition.from_state not in POSITION_STATES:
        raise ValueError("transition from_state is invalid")
    if transition.to_state not in POSITION_STATES:
        raise ValueError("transition to_state is invalid")
    _parse_utc(transition.event_time, "event_time")
    if not isinstance(transition.accepted, bool):
        raise ValueError("transition accepted must be a bool")
    expected_action = PERSISTED_EVENT_ACTIONS[transition.event]
    if transition.accepted:
        if transition.event not in POSITION_STATE_TRANSITIONS[transition.from_state]:
            raise ValueError("accepted transition is not permitted from its state")
        target = POSITION_STATE_TRANSITIONS[transition.from_state][transition.event]
        if target == OPEN_BY_TRANCHE_COUNT:
            if transition.to_state not in (OPEN_INITIAL, OPEN_ADDED):
                raise ValueError("RECOVER must return to an open ledger state")
        elif transition.to_state != target:
            raise ValueError("accepted transition target is invalid")
        if transition.persisted_action != expected_action:
            raise ValueError("persisted action does not match accepted event")
        if not transition.reason_codes or transition.reason_codes[0] != (
            _ACCEPTED_REASON_CODES[transition.event]
        ):
            raise ValueError("accepted transition requires its lifecycle reason")
        _validate_applied_transition_economics(transition)
    else:
        if transition.to_state != transition.from_state:
            raise ValueError("refused transition cannot change state")
        if transition.persisted_action != "HOLD" or transition.quantity_delta is not None:
            raise ValueError("refused transition cannot contain applied economics")
    _optional_positive_decimal(
        transition.requested_quantity,
        "requested_quantity",
    )
    _optional_decimal(transition.quantity_delta, "quantity_delta")
    _optional_positive_decimal(transition.price, "price")
    _optional_positive_decimal(transition.stop_price, "stop_price")
    if not _reason_codes(transition.reason_codes):
        raise ValueError("transition requires at least one reason code")


def _validate_applied_transition_economics(transition: PositionTransition) -> None:
    quantity = transition.requested_quantity
    delta = transition.quantity_delta
    if transition.event in (ENTER, ADD):
        if quantity is None or delta != quantity or transition.price is None:
            raise ValueError("entry/add transition economics are inconsistent")
    elif transition.event == TRIM:
        if quantity is None or delta != -quantity:
            raise ValueError("trim transition economics are inconsistent")
    elif transition.event == EXIT:
        if delta is None or not decision_less(delta, 0):
            raise ValueError("exit transition requires a negative quantity delta")
        if quantity is not None and delta != -quantity:
            raise ValueError("exit transition quantity does not match its delta")
    elif quantity is not None or delta is not None:
        raise ValueError("state-only transition cannot apply quantity economics")

    if transition.event in (ENTER, STOP_MOVE) and transition.stop_price is None:
        raise ValueError("entry/stop transition requires a stop price")
    if transition.event not in (ENTER, ADD, STOP_MOVE) and (
        transition.stop_price is not None
    ):
        raise ValueError("transition event cannot apply a stop price")


def _validate_tranche(tranche: Tranche) -> None:
    if not isinstance(tranche, Tranche):
        raise TypeError("tranches must contain Tranche values")
    if isinstance(tranche.tranche_number, bool) or not isinstance(
        tranche.tranche_number,
        int,
    ):
        raise TypeError("tranche_number must be an integer")
    if tranche.tranche_number < 1:
        raise ValueError("tranche_number must be positive")
    _positive_decimal(tranche.entry_price, "entry_price")
    _positive_decimal(tranche.quantity, "quantity")
    _parse_utc(tranche.opened_at, "opened_at")


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


def _as_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    return value


def _required_string(record: Mapping[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _config_metadata(value: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise TypeError("config_metadata must be a mapping")
    normalized = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("config_metadata keys must be non-empty strings")
        if not isinstance(item, str) or not item.strip():
            raise ValueError("config_metadata values must be non-empty strings")
        normalized[key] = item
    return normalized


def _reason_codes(values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, str):
        raise TypeError("reason_codes must be an iterable of strings, not a string")
    normalized = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("reason codes must be non-empty strings")
        if value not in normalized:
            normalized.append(value)
    return tuple(normalized)


def _merge_reason_codes(
    generated: Iterable[str],
    supplied: Iterable[str],
) -> tuple[str, ...]:
    return _reason_codes((*generated, *supplied))


def _parse_utc(value: Any, name: str) -> datetime:
    if isinstance(value, datetime):
        return require_utc_datetime(value, name)
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a datetime or ISO datetime string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{name} must be a valid ISO datetime string") from error
    return require_utc_datetime(parsed, name)


def _optional_utc(value: Any, name: str) -> datetime | None:
    return None if value is None else _parse_utc(value, name)


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
    if decision_less(result, 0):
        raise ValueError(f"{name} must be non-negative")
    return result


def _optional_decimal(value: Any, name: str) -> Decimal | None:
    return None if value is None else _decimal(value, name)


def _optional_positive_decimal(value: Any, name: str) -> Decimal | None:
    return None if value is None else _positive_decimal(value, name)


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
    "POSITION_TRANSITION_RECORD_VERSION",
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
    "position_event_records",
    "replay_position_lifecycle",
    "replay_position_event_records",
    "restore_position_lifecycle",
    "start_position_lifecycle",
]
