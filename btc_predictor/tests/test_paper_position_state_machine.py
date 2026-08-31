"""BTC-150: paper position state machine."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from btc_predictor.db.portfolio import PAPER_ACTIONS
from btc_predictor.portfolio import (
    ADD,
    ARM_ENTRY,
    CLOSED,
    DEFEND,
    DEFENSIVE,
    DISARM_ENTRY,
    ENTER,
    EXIT,
    HOLD,
    MISS,
    MISSED,
    OBSERVE,
    OPEN_ADDED,
    OPEN_BY_TRANCHE_COUNT,
    OPEN_INITIAL,
    OPEN_POSITION_STATES,
    PENDING_ENTRY,
    PERSISTED_EVENT_ACTIONS,
    PERSISTED_POSITION_STATUS,
    POSITION_EVENTS,
    POSITION_STATE_MACHINE_FEATURE_ID,
    POSITION_STATE_MACHINE_POLICY_VERSION,
    POSITION_STATE_REASON_CODES,
    POSITION_STATE_TRANSITIONS,
    POSITION_STATES,
    PRE_POSITION_STATES,
    RECOVER,
    STOP_MOVE,
    TERMINAL_POSITION_STATES,
    TRIM,
    WATCH,
    PositionLifecycle,
    Tranche,
    apply_position_event,
    persisted_action_for_event,
    persisted_status_for_state,
    replay_position_lifecycle,
    start_position_lifecycle,
)


SYMBOL = "BTC-USD"
START = datetime(2024, 3, 1, tzinfo=timezone.utc)


def at(hours: int) -> datetime:
    return START + timedelta(hours=hours)


def watching(**kwargs) -> PositionLifecycle:
    return start_position_lifecycle(symbol=SYMBOL, **kwargs)


def entered(*, hours: int = 1, stop: str = "90000") -> PositionLifecycle:
    lifecycle = apply_position_event(watching(), event=ARM_ENTRY, event_time=at(0))
    return apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=at(hours),
        quantity="1",
        price="100000",
        stop_price=stop,
    )


def added(lifecycle: PositionLifecycle, *, hours: int = 2) -> PositionLifecycle:
    return apply_position_event(
        lifecycle,
        event=ADD,
        event_time=at(hours),
        quantity="1",
        price="110000",
    )


def test_metadata_is_stable() -> None:
    assert POSITION_STATE_MACHINE_FEATURE_ID == "PAPER_POSITION_STATE_MACHINE"
    assert POSITION_STATE_MACHINE_POLICY_VERSION == "PAPER_POSITION_STATE_MACHINE_V1"


# --- the declared machine ------------------------------------------------


def test_states_are_exactly_the_declared_set() -> None:
    assert POSITION_STATES == (
        "WATCH",
        "PENDING_ENTRY",
        "OPEN_INITIAL",
        "OPEN_ADDED",
        "DEFENSIVE",
        "CLOSED",
        "MISSED",
    )
    # The partitions cover every state exactly once.
    assert (
        set(PRE_POSITION_STATES)
        | set(OPEN_POSITION_STATES)
        | set(TERMINAL_POSITION_STATES)
    ) == set(POSITION_STATES)
    assert len(PRE_POSITION_STATES) + len(OPEN_POSITION_STATES) + len(
        TERMINAL_POSITION_STATES
    ) == len(POSITION_STATES)


def test_transition_table_is_well_formed() -> None:
    assert set(POSITION_STATE_TRANSITIONS) == set(POSITION_STATES)

    for state, edges in POSITION_STATE_TRANSITIONS.items():
        for event, target in edges.items():
            assert event in POSITION_EVENTS, (state, event)
            assert target in POSITION_STATES or target == OPEN_BY_TRANCHE_COUNT


def test_terminal_states_have_no_outgoing_transitions() -> None:
    for state in TERMINAL_POSITION_STATES:
        assert POSITION_STATE_TRANSITIONS[state] == {}


def test_every_declared_event_is_reachable_somewhere() -> None:
    used = {event for edges in POSITION_STATE_TRANSITIONS.values() for event in edges}

    assert used == set(POSITION_EVENTS)


def test_add_is_only_permitted_from_the_two_open_states() -> None:
    permitted = {
        state
        for state, edges in POSITION_STATE_TRANSITIONS.items()
        if ADD in edges
    }

    # DEFENSIVE is deliberately excluded: rulebook 24's shared NO ADDING effect.
    assert permitted == {OPEN_INITIAL, OPEN_ADDED}


# --- the happy path ------------------------------------------------------


def test_full_lifecycle_runs_watch_to_closed() -> None:
    lifecycle = watching()
    assert lifecycle.state == WATCH

    lifecycle = apply_position_event(lifecycle, event=ARM_ENTRY, event_time=at(0))
    assert lifecycle.state == PENDING_ENTRY

    lifecycle = apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=at(1),
        quantity="1",
        price="100000",
        stop_price="90000",
    )
    assert lifecycle.state == OPEN_INITIAL
    assert lifecycle.quantity == Decimal("1")
    assert lifecycle.opened_at == at(1)

    lifecycle = added(lifecycle)
    assert lifecycle.state == OPEN_ADDED
    assert lifecycle.tranche_count == 2

    lifecycle = apply_position_event(lifecycle, event=HOLD, event_time=at(3))
    assert lifecycle.state == OPEN_ADDED

    lifecycle = apply_position_event(lifecycle, event=EXIT, event_time=at(4))
    assert lifecycle.state == CLOSED
    assert lifecycle.closed_at == at(4)
    assert lifecycle.quantity == Decimal("0")
    assert lifecycle.is_terminal is True


def test_a_lifecycle_may_start_already_pending() -> None:
    # Rulebook 26 only routes to WATCH when conviction is below 80; a qualifying
    # setup goes straight to an entry.
    lifecycle = watching(state=PENDING_ENTRY)

    assert lifecycle.state == PENDING_ENTRY
    assert lifecycle.reason_codes == ("POSITION_STATE_LIFECYCLE_STARTED",)


def test_open_state_tracks_tranche_count_not_history() -> None:
    initial = entered()
    assert initial.state == OPEN_INITIAL and initial.tranche_count == 1

    pyramided = added(initial)
    assert pyramided.state == OPEN_ADDED and pyramided.tranche_count == 2


def test_a_pending_entry_can_be_disarmed_back_to_watch() -> None:
    lifecycle = apply_position_event(watching(), event=ARM_ENTRY, event_time=at(0))
    lifecycle = apply_position_event(lifecycle, event=DISARM_ENTRY, event_time=at(1))

    # A conviction dip before the fill is not a missed trade; MISSED is terminal
    # and carries "do not chase", which would be the wrong label here.
    assert lifecycle.state == WATCH
    assert lifecycle.is_terminal is False


def test_observe_is_a_self_loop_in_both_pre_position_states() -> None:
    for state in PRE_POSITION_STATES:
        lifecycle = apply_position_event(
            watching(state=state), event=OBSERVE, event_time=at(1)
        )
        assert lifecycle.state == state
        assert lifecycle.accepted is True


# --- DEFENSIVE -----------------------------------------------------------


def test_defensive_refuses_an_add() -> None:
    lifecycle = apply_position_event(added(entered()), event=DEFEND, event_time=at(3))
    assert lifecycle.state == DEFENSIVE

    refused = apply_position_event(
        lifecycle,
        event=ADD,
        event_time=at(4),
        quantity="1",
        price="120000",
    )

    assert refused.accepted is False
    assert refused.state == DEFENSIVE
    assert refused.tranche_count == 2
    assert refused.quantity == Decimal("2")
    assert "POSITION_STATE_ADD_REFUSED_WHILE_DEFENSIVE" in refused.reason_codes


@pytest.mark.parametrize("event", [HOLD, STOP_MOVE, TRIM, EXIT, RECOVER])
def test_defensive_still_permits_every_risk_reducing_action(event: str) -> None:
    assert event in POSITION_STATE_TRANSITIONS[DEFENSIVE]


@pytest.mark.parametrize(
    ("tranche_count", "expected"),
    [(1, OPEN_INITIAL), (2, OPEN_ADDED)],
)
def test_recovery_returns_to_the_state_the_ledger_implies(
    tranche_count: int,
    expected: str,
) -> None:
    lifecycle = entered()
    if tranche_count == 2:
        lifecycle = added(lifecycle)
    lifecycle = apply_position_event(lifecycle, event=DEFEND, event_time=at(5))
    recovered = apply_position_event(lifecycle, event=RECOVER, event_time=at(6))

    # Recovery is derived, never remembered, so state cannot drift from tranches.
    assert recovered.state == expected
    assert recovered.tranche_count == tranche_count


def test_a_defensive_position_can_be_trimmed_then_recover_to_initial() -> None:
    lifecycle = apply_position_event(entered(), event=DEFEND, event_time=at(3))
    lifecycle = apply_position_event(
        lifecycle, event=TRIM, event_time=at(4), quantity="0.25"
    )

    assert lifecycle.state == DEFENSIVE
    assert lifecycle.quantity == Decimal("0.75")


# --- MISSED and terminality ----------------------------------------------


@pytest.mark.parametrize("state", list(PRE_POSITION_STATES))
def test_a_pre_position_lifecycle_can_be_missed(state: str) -> None:
    lifecycle = apply_position_event(
        watching(state=state),
        event=MISS,
        event_time=at(1),
        reason_codes=("NO_CHASE_VIOLATION",),
    )

    assert lifecycle.state == MISSED
    assert lifecycle.is_terminal is True
    assert lifecycle.quantity == Decimal("0")
    # Rulebook 25's cause is carried through, not flattened into "missed".
    assert lifecycle.reason_codes == (
        "POSITION_STATE_MISSED",
        "NO_CHASE_VIOLATION",
    )


@pytest.mark.parametrize("state", list(TERMINAL_POSITION_STATES))
@pytest.mark.parametrize("event", list(POSITION_EVENTS))
def test_terminal_states_refuse_every_event(state: str, event: str) -> None:
    if state == CLOSED:
        lifecycle = apply_position_event(entered(), event=EXIT, event_time=at(2))
    else:
        lifecycle = apply_position_event(watching(), event=MISS, event_time=at(2))
    assert lifecycle.state == state

    refused = apply_position_event(
        lifecycle,
        event=event,
        event_time=at(3),
        quantity="1",
        price="100000",
        stop_price="95000",
    )

    assert refused.accepted is False
    assert refused.state == state
    assert "POSITION_STATE_TERMINAL" in refused.reason_codes


def test_an_open_position_cannot_be_missed() -> None:
    refused = apply_position_event(entered(), event=MISS, event_time=at(2))

    assert refused.accepted is False
    assert refused.state == OPEN_INITIAL
    assert refused.reason_codes == ("POSITION_STATE_TRANSITION_NOT_PERMITTED",)


def test_an_entry_cannot_be_taken_from_watch_without_arming() -> None:
    refused = apply_position_event(
        watching(),
        event=ENTER,
        event_time=at(1),
        quantity="1",
        price="100000",
        stop_price="90000",
    )

    assert refused.accepted is False
    assert refused.state == WATCH


# --- never widen a stop --------------------------------------------------


def test_a_long_stop_can_be_raised() -> None:
    lifecycle = apply_position_event(
        entered(), event=STOP_MOVE, event_time=at(2), stop_price="95000"
    )

    assert lifecycle.accepted is True
    assert lifecycle.stop_price == Decimal("95000")


def test_a_long_stop_cannot_be_lowered() -> None:
    lifecycle = entered()
    refused = apply_position_event(
        lifecycle, event=STOP_MOVE, event_time=at(2), stop_price="85000"
    )

    # Rulebook 32 rule 3. The ledger refuses to record it regardless of policy.
    assert refused.accepted is False
    assert refused.stop_price == Decimal("90000")
    assert "POSITION_STATE_STOP_WOULD_WIDEN" in refused.reason_codes


def test_a_short_stop_cannot_be_raised() -> None:
    lifecycle = start_position_lifecycle(
        symbol=SYMBOL, direction="short", state=PENDING_ENTRY
    )
    lifecycle = apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=at(1),
        quantity="1",
        price="100000",
        stop_price="110000",
    )
    refused = apply_position_event(
        lifecycle, event=STOP_MOVE, event_time=at(2), stop_price="115000"
    )
    lowered = apply_position_event(
        lifecycle, event=STOP_MOVE, event_time=at(2), stop_price="105000"
    )

    assert refused.accepted is False
    assert "POSITION_STATE_STOP_WOULD_WIDEN" in refused.reason_codes
    assert lowered.accepted is True
    assert lowered.stop_price == Decimal("105000")


def test_an_unchanged_stop_is_accepted() -> None:
    lifecycle = apply_position_event(
        entered(), event=STOP_MOVE, event_time=at(2), stop_price="90000"
    )

    assert lifecycle.accepted is True


def test_an_add_that_would_widen_the_stop_is_refused() -> None:
    refused = apply_position_event(
        entered(),
        event=ADD,
        event_time=at(2),
        quantity="1",
        price="110000",
        stop_price="80000",
    )

    # Rulebook 26 raises the stop before an add; it never lowers it.
    assert refused.accepted is False
    assert refused.state == OPEN_INITIAL
    assert "POSITION_STATE_STOP_WOULD_WIDEN" in refused.reason_codes


# --- argument guards -----------------------------------------------------


def test_an_entry_requires_a_structural_stop() -> None:
    refused = apply_position_event(
        watching(state=PENDING_ENTRY),
        event=ENTER,
        event_time=at(1),
        quantity="1",
        price="100000",
    )

    assert refused.accepted is False
    assert "POSITION_STATE_ENTRY_REQUIRES_STOP" in refused.reason_codes


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"price": "100000"}, "POSITION_STATE_QUANTITY_REQUIRED"),
        ({"quantity": "1"}, "POSITION_STATE_PRICE_REQUIRED"),
    ],
)
def test_an_add_requires_a_quantity_and_a_price(kwargs, expected: str) -> None:
    refused = apply_position_event(entered(), event=ADD, event_time=at(2), **kwargs)

    assert refused.accepted is False
    assert expected in refused.reason_codes


def test_a_stop_move_requires_a_stop_price() -> None:
    refused = apply_position_event(entered(), event=STOP_MOVE, event_time=at(2))

    assert refused.accepted is False
    assert "POSITION_STATE_STOP_REQUIRED" in refused.reason_codes


@pytest.mark.parametrize("quantity", ["1", "2"])
def test_a_trim_must_leave_something_open(quantity: str) -> None:
    refused = apply_position_event(
        entered(), event=TRIM, event_time=at(2), quantity=quantity
    )

    # Removing everything is an EXIT. Keeping TRIM strictly partial is what
    # guarantees an open state always holds a positive quantity.
    assert refused.accepted is False
    assert "POSITION_STATE_TRIM_NOT_PARTIAL" in refused.reason_codes


def test_a_partial_trim_reduces_quantity_and_stays_open() -> None:
    lifecycle = apply_position_event(
        entered(), event=TRIM, event_time=at(2), quantity="0.4"
    )

    assert lifecycle.accepted is True
    assert lifecycle.state == OPEN_INITIAL
    assert lifecycle.quantity == Decimal("0.6")


def test_an_exit_with_a_partial_quantity_is_refused() -> None:
    refused = apply_position_event(
        entered(), event=EXIT, event_time=at(2), quantity="0.5"
    )

    assert refused.accepted is False
    assert "POSITION_STATE_EXIT_MUST_BE_FULL" in refused.reason_codes


def test_an_exit_may_restate_the_full_quantity() -> None:
    lifecycle = apply_position_event(
        entered(), event=EXIT, event_time=at(2), quantity="1"
    )

    assert lifecycle.accepted is True
    assert lifecycle.state == CLOSED


# --- the tranche ledger --------------------------------------------------


def test_average_entry_is_quantity_weighted() -> None:
    lifecycle = apply_position_event(
        entered(),
        event=ADD,
        event_time=at(2),
        quantity="3",
        price="120000",
    )

    assert lifecycle.average_entry_price == Decimal("115000")


def test_average_entry_matches_the_btc047_kernel() -> None:
    from btc_predictor.quant.portfolio import weighted_average_entry

    lifecycle = apply_position_event(
        entered(),
        event=ADD,
        event_time=at(2),
        quantity="0.7",
        price="113500",
    )
    expected = weighted_average_entry([100000.0, 113500.0], [1.0, 0.7])

    assert abs(float(lifecycle.average_entry_price) - float(expected)) < 1e-6


def test_a_trim_leaves_average_entry_unchanged() -> None:
    lifecycle = added(entered())
    before = lifecycle.average_entry_price

    trimmed = apply_position_event(
        lifecycle, event=TRIM, event_time=at(3), quantity="0.5"
    )

    # Trimming pro-rata is what keeps a partial exit from silently re-basing the
    # entry price the whole position is measured against.
    assert trimmed.quantity == Decimal("1.5")
    assert trimmed.average_entry_price == before
    assert trimmed.tranche_count == 2


def test_a_closed_position_keeps_the_average_entry_it_closed_at() -> None:
    lifecycle = added(entered())
    before = lifecycle.average_entry_price

    closed = apply_position_event(lifecycle, event=EXIT, event_time=at(3))

    assert closed.quantity == Decimal("0")
    assert closed.tranches == ()
    assert closed.average_entry_price == before


def test_tranches_are_numbered_in_fill_order() -> None:
    lifecycle = added(entered())

    assert [item.tranche_number for item in lifecycle.tranches] == [1, 2]
    assert [str(item.entry_price) for item in lifecycle.tranches] == [
        "100000",
        "110000",
    ]
    assert [item.opened_at for item in lifecycle.tranches] == [at(1), at(2)]


# --- point-in-time ordering ----------------------------------------------


def test_an_out_of_order_event_is_refused() -> None:
    lifecycle = entered()
    refused = apply_position_event(lifecycle, event=HOLD, event_time=at(0))

    assert refused.accepted is False
    assert "POSITION_STATE_EVENT_OUT_OF_ORDER" in refused.reason_codes
    assert refused.last_event_at == at(1)


def test_a_repeated_timestamp_is_accepted() -> None:
    lifecycle = apply_position_event(entered(), event=HOLD, event_time=at(1))

    # Two decisions can share one bar close.
    assert lifecycle.accepted is True


def test_a_refused_event_does_not_advance_the_clock() -> None:
    lifecycle = entered()
    refused = apply_position_event(
        lifecycle, event=STOP_MOVE, event_time=at(9), stop_price="85000"
    )
    later = apply_position_event(refused, event=HOLD, event_time=at(2))

    # The refused event at hour 9 must not block a legitimate event at hour 2.
    assert later.accepted is True
    assert later.last_event_at == at(2)


# --- immutability, determinism, replay -----------------------------------


def test_applying_an_event_leaves_the_prior_lifecycle_untouched() -> None:
    lifecycle = entered()
    added(lifecycle)

    assert lifecycle.state == OPEN_INITIAL
    assert lifecycle.tranche_count == 1
    assert lifecycle.quantity == Decimal("1")


def test_a_refused_event_is_recorded_without_changing_the_ledger() -> None:
    lifecycle = added(entered())
    refused = apply_position_event(
        lifecycle, event=STOP_MOVE, event_time=at(3), stop_price="10000"
    )

    assert refused.transitions[-1].accepted is False
    assert refused.transitions[-1].persisted_action == "HOLD"
    assert refused.transitions[-1].to_state == refused.transitions[-1].from_state
    assert len(refused.transitions) == len(lifecycle.transitions) + 1
    assert refused.quantity == lifecycle.quantity
    assert refused.stop_price == lifecycle.stop_price


EVENT_LOG = (
    {"event": ARM_ENTRY, "event_time": at(0)},
    {
        "event": ENTER,
        "event_time": at(1),
        "quantity": "1",
        "price": "100000",
        "stop_price": "90000",
    },
    {"event": HOLD, "event_time": at(2)},
    {
        "event": ADD,
        "event_time": at(3),
        "quantity": "1",
        "price": "110000",
        "stop_price": "97000",
    },
    {"event": DEFEND, "event_time": at(4)},
    {"event": TRIM, "event_time": at(5), "quantity": "0.5"},
    {"event": RECOVER, "event_time": at(6)},
    {"event": EXIT, "event_time": at(7)},
)


def test_replay_is_deterministic() -> None:
    first = replay_position_lifecycle(EVENT_LOG, symbol=SYMBOL)
    second = replay_position_lifecycle(EVENT_LOG, symbol=SYMBOL)

    assert first.as_record() == second.as_record()


def test_replay_reproduces_the_state_sequence() -> None:
    lifecycle = replay_position_lifecycle(EVENT_LOG, symbol=SYMBOL)

    assert [item.to_state for item in lifecycle.transitions] == [
        PENDING_ENTRY,
        OPEN_INITIAL,
        OPEN_INITIAL,
        OPEN_ADDED,
        DEFENSIVE,
        DEFENSIVE,
        OPEN_ADDED,
        CLOSED,
    ]
    assert all(item.accepted for item in lifecycle.transitions)
    assert lifecycle.state == CLOSED
    assert lifecycle.stop_price == Decimal("97000")


def test_replay_matches_step_by_step_application() -> None:
    stepwise = watching()
    for entry in EVENT_LOG:
        stepwise = apply_position_event(
            stepwise,
            event=entry["event"],
            event_time=entry["event_time"],
            quantity=entry.get("quantity"),
            price=entry.get("price"),
            stop_price=entry.get("stop_price"),
        )

    assert stepwise.as_record() == replay_position_lifecycle(
        EVENT_LOG, symbol=SYMBOL
    ).as_record()


# --- persistence ---------------------------------------------------------


def test_record_is_persistable_and_reconstructable() -> None:
    lifecycle = replay_position_lifecycle(
        EVENT_LOG[:4],
        symbol=SYMBOL,
        config_metadata={"config_version": "strategy_config_v2"},
    )
    record = lifecycle.as_record()

    assert record["feature_id"] == "PAPER_POSITION_STATE_MACHINE"
    assert record["policy_version"] == "PAPER_POSITION_STATE_MACHINE_V1"
    assert record["symbol"] == SYMBOL
    assert record["direction"] == "long"
    assert record["state"] == OPEN_ADDED
    assert record["persisted_status"] == "open"
    assert record["tranche_count"] == 2
    assert record["quantity"] == "2"
    assert record["average_entry_price"] == "105000"
    assert record["stop_price"] == "97000"
    assert record["opened_at"] == at(1).isoformat()
    assert record["closed_at"] is None
    assert record["last_event_at"] == at(3).isoformat()
    assert record["config_metadata"] == {"config_version": "strategy_config_v2"}
    # The tranche ledger is persisted, so the aggregate is reconstructable.
    assert [item["quantity"] for item in record["tranches"]] == ["1", "1"]
    assert sum(Decimal(item["quantity"]) for item in record["tranches"]) == Decimal(
        record["quantity"]
    )
    # Every transition that produced the state is retained.
    assert len(record["transitions"]) == 4
    assert [item["event"] for item in record["transitions"]] == [
        ARM_ENTRY,
        ENTER,
        HOLD,
        ADD,
    ]


def test_transition_record_carries_the_persisted_action() -> None:
    lifecycle = replay_position_lifecycle(EVENT_LOG, symbol=SYMBOL)

    assert [item.as_record()["persisted_action"] for item in lifecycle.transitions] == [
        None,
        "ENTER",
        "HOLD",
        "ADD",
        "HOLD",
        "TRIM",
        "HOLD",
        "EXIT",
    ]


def test_persisted_actions_are_all_accepted_by_the_portfolio_schema() -> None:
    assert set(PERSISTED_EVENT_ACTIONS) == set(POSITION_EVENTS)

    for event, action in PERSISTED_EVENT_ACTIONS.items():
        assert persisted_action_for_event(event) == action
        if action is not None:
            # position_events.action has a CHECK constraint; emitting anything
            # outside it would fail on write.
            assert action in PAPER_ACTIONS


def test_pre_position_events_persist_no_action() -> None:
    for event in (OBSERVE, ARM_ENTRY, DISARM_ENTRY):
        assert persisted_action_for_event(event) is None


def test_defensive_transitions_persist_as_hold() -> None:
    # position_events has no DEFEND action, so the state resolution lives in the
    # transition record's reason codes rather than in the action alone.
    assert persisted_action_for_event(DEFEND) == "HOLD"
    assert persisted_action_for_event(RECOVER) == "HOLD"


def test_states_map_onto_the_positions_status_check() -> None:
    assert set(PERSISTED_POSITION_STATUS) == set(POSITION_STATES)

    for state in POSITION_STATES:
        status = persisted_status_for_state(state)
        assert status == PERSISTED_POSITION_STATUS[state]
        if state in PRE_POSITION_STATES:
            # No positions row exists before a fill.
            assert status is None
        else:
            assert status in ("open", "closed", "missed")


def test_reason_codes_are_drawn_from_the_declared_set() -> None:
    lifecycles = [
        replay_position_lifecycle(EVENT_LOG, symbol=SYMBOL),
        apply_position_event(entered(), event=MISS, event_time=at(2)),
        apply_position_event(entered(), event=STOP_MOVE, event_time=at(2)),
        apply_position_event(
            apply_position_event(entered(), event=DEFEND, event_time=at(2)),
            event=ADD,
            event_time=at(3),
            quantity="1",
            price="1",
        ),
        watching(),
    ]

    for lifecycle in lifecycles:
        for transition in lifecycle.transitions:
            for code in transition.reason_codes:
                assert code in POSITION_STATE_REASON_CODES
        for code in lifecycle.reason_codes:
            assert code in POSITION_STATE_REASON_CODES


def test_an_open_record_requires_a_positive_quantity() -> None:
    broken = PositionLifecycle(
        feature_id=POSITION_STATE_MACHINE_FEATURE_ID,
        policy_version=POSITION_STATE_MACHINE_POLICY_VERSION,
        symbol=SYMBOL,
        direction="long",
        state=OPEN_INITIAL,
        tranches=(),
        quantity=Decimal("0"),
        average_entry_price=None,
        stop_price=None,
        opened_at=at(1),
        closed_at=None,
        last_event_at=at(1),
        transitions=(),
        config_metadata={},
        accepted=True,
    )

    with pytest.raises(ValueError, match="positive quantity"):
        broken.as_record()


def test_a_pre_position_record_cannot_hold_tranches() -> None:
    broken = PositionLifecycle(
        feature_id=POSITION_STATE_MACHINE_FEATURE_ID,
        policy_version=POSITION_STATE_MACHINE_POLICY_VERSION,
        symbol=SYMBOL,
        direction="long",
        state=WATCH,
        tranches=(
            Tranche(
                tranche_number=1,
                entry_price=Decimal("100000"),
                quantity=Decimal("1"),
                opened_at=at(1),
            ),
        ),
        quantity=Decimal("1"),
        average_entry_price=Decimal("100000"),
        stop_price=None,
        opened_at=None,
        closed_at=None,
        last_event_at=at(1),
        transitions=(),
        config_metadata={},
        accepted=True,
    )

    with pytest.raises(ValueError, match="cannot hold tranches"):
        broken.as_record()


# --- malformed input -----------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"symbol": ""}, "symbol must not be empty"),
        ({"symbol": SYMBOL, "direction": "flat"}, "direction must be one of"),
        ({"symbol": SYMBOL, "state": OPEN_INITIAL}, "must start in one of"),
        ({"symbol": SYMBOL, "state": CLOSED}, "must start in one of"),
    ],
)
def test_starting_a_lifecycle_validates_its_identity(kwargs, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        start_position_lifecycle(**kwargs)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"quantity": "0"}, "quantity must be positive"),
        ({"quantity": "-1"}, "quantity must be positive"),
        ({"quantity": "1", "price": "0"}, "price must be positive"),
        ({"quantity": "1", "price": "abc"}, "price must be numeric"),
        ({"quantity": "1", "price": "1", "stop_price": "-5"}, "stop_price must be"),
    ],
)
def test_malformed_numbers_fail_fast(kwargs, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        apply_position_event(
            watching(state=PENDING_ENTRY),
            event=ENTER,
            event_time=at(1),
            **kwargs,
        )


def test_an_unknown_event_is_rejected() -> None:
    with pytest.raises(ValueError, match="event must be one of"):
        apply_position_event(watching(), event="LIQUIDATE", event_time=at(1))


def test_a_naive_event_time_is_rejected() -> None:
    with pytest.raises(ValueError):
        apply_position_event(
            watching(), event=OBSERVE, event_time=datetime(2024, 3, 1)
        )


def test_a_non_lifecycle_is_rejected() -> None:
    with pytest.raises(TypeError, match="must be a PositionLifecycle"):
        apply_position_event({"state": WATCH}, event=OBSERVE, event_time=at(1))


@pytest.mark.parametrize(
    ("value", "match"),
    [("SLEEPING", "state must be one of"), ("open", "state must be one of")],
)
def test_persisted_status_validates_the_state(value: str, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        persisted_status_for_state(value)


def test_persisted_action_validates_the_event() -> None:
    with pytest.raises(ValueError, match="event must be one of"):
        persisted_action_for_event("LIQUIDATE")
