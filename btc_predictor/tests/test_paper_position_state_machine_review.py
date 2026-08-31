"""Independent BTC-150 lifecycle and persistence regressions."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.db.portfolio import PAPER_ACTIONS, position_events
from btc_predictor.portfolio import (
    ADD,
    ARM_ENTRY,
    CLOSED,
    DEFEND,
    DEFENSIVE,
    ENTER,
    EXIT,
    HOLD,
    MISS,
    MISSED,
    OPEN_ADDED,
    OPEN_INITIAL,
    PENDING_ENTRY,
    RECOVER,
    STOP_MOVE,
    TRIM,
    WATCH,
    apply_position_event,
    persisted_status_for_state,
    position_event_records,
    replay_position_event_records,
    replay_position_lifecycle,
    restore_position_lifecycle,
    start_position_lifecycle,
)
from btc_predictor.quant.portfolio import weighted_average_entry


START = datetime(2026, 8, 31, tzinfo=UTC)


def at(hours: int) -> datetime:
    return START + timedelta(hours=hours)


def pending(*, direction: str = "long"):
    return start_position_lifecycle(
        symbol="BTC-USD",
        direction=direction,
        state=PENDING_ENTRY,
        config_metadata={"config_version": "strategy_config_v2"},
    )


def entered(*, direction: str = "long"):
    stop = "110" if direction == "short" else "90"
    return apply_position_event(
        pending(direction=direction),
        event=ENTER,
        event_time=at(1),
        quantity="1",
        price="100",
        stop_price=stop,
    )


def economics(lifecycle):
    return (
        lifecycle.state,
        lifecycle.tranches,
        lifecycle.quantity,
        lifecycle.average_entry_price,
        lifecycle.stop_price,
        lifecycle.opened_at,
        lifecycle.closed_at,
        lifecycle.last_event_at,
    )


def realistic_lifecycle():
    lifecycle = start_position_lifecycle(
        symbol="BTC-USD",
        config_metadata={"config_version": "strategy_config_v2"},
    )
    commands = (
        {"event": ARM_ENTRY, "event_time": at(0)},
        {
            "event": ENTER,
            "event_time": at(1),
            "quantity": "1",
            "price": "100",
            "stop_price": "90",
        },
        {
            "event": ADD,
            "event_time": at(2),
            "quantity": "1",
            "price": "110",
            "stop_price": "95",
        },
        {"event": DEFEND, "event_time": at(3)},
        {
            "event": ADD,
            "event_time": at(4),
            "quantity": "2",
            "price": "120",
            "reason_codes": ("CROWDING_WARNING",),
        },
        {"event": TRIM, "event_time": at(5), "quantity": "0.5"},
        {"event": RECOVER, "event_time": at(6)},
        {"event": STOP_MOVE, "event_time": at(7), "stop_price": "100"},
        {"event": EXIT, "event_time": at(8)},
    )
    for command in commands:
        lifecycle = apply_position_event(lifecycle, **command)
    return lifecycle


def test_full_snapshot_round_trips_from_serialized_transition_records() -> None:
    lifecycle = realistic_lifecycle()
    serialized = json.loads(json.dumps(lifecycle.as_record()))

    restored = restore_position_lifecycle(serialized)

    assert restored == lifecycle
    assert restored.state == CLOSED
    assert restored.quantity == 0
    assert restored.transitions[4].accepted is False
    assert restored.transitions[4].requested_quantity == Decimal("2")


def test_transition_records_replay_directly_with_iso_timestamps() -> None:
    lifecycle = realistic_lifecycle()

    replayed = replay_position_lifecycle(
        [item.as_record() for item in lifecycle.transitions],
        symbol="BTC-USD",
        config_metadata={"config_version": "strategy_config_v2"},
    )

    assert replayed == lifecycle


def test_refused_guard_record_retains_requested_quantity_for_replay() -> None:
    lifecycle = entered()
    refused = apply_position_event(
        lifecycle,
        event=TRIM,
        event_time=at(2),
        quantity="1",
    )
    record = refused.transitions[-1].as_record()

    assert record["requested_quantity"] == "1"
    replayed = replay_position_lifecycle(
        [item.as_record() for item in refused.transitions],
        symbol="BTC-USD",
        state=PENDING_ENTRY,
        config_metadata={"config_version": "strategy_config_v2"},
    )
    assert replayed == refused
    rows = position_event_records(refused)
    assert rows[-1]["action"] == "HOLD"
    assert json.loads(rows[-1]["notes"])["accepted"] is False
    assert replay_position_event_records(
        rows,
        symbol="BTC-USD",
        config_metadata={"config_version": "strategy_config_v2"},
    ) == refused


def test_database_compatible_rows_preserve_defensive_state_identity() -> None:
    lifecycle = entered()
    lifecycle = apply_position_event(lifecycle, event=DEFEND, event_time=at(2))
    rows = position_event_records(lifecycle)

    assert [row["action"] for row in rows] == ["ENTER", "HOLD"]
    assert set(rows[0]) <= set(position_events.c.keys())
    assert all(row["action"] in PAPER_ACTIONS for row in rows)
    assert all(row["quantity"] is None or row["quantity"] >= 0 for row in rows)
    replayed = replay_position_event_records(
        rows,
        symbol="BTC-USD",
        config_metadata={"config_version": "strategy_config_v2"},
    )
    assert replayed.state == DEFENSIVE
    assert [item.event for item in replayed.transitions] == [ENTER, DEFEND]


def test_database_rows_preserve_recover_distinct_from_hold() -> None:
    lifecycle = entered()
    lifecycle = apply_position_event(lifecycle, event=DEFEND, event_time=at(2))
    lifecycle = apply_position_event(lifecycle, event=RECOVER, event_time=at(3))

    replayed = replay_position_event_records(
        position_event_records(lifecycle),
        symbol="BTC-USD",
        config_metadata={"config_version": "strategy_config_v2"},
    )

    assert [item.persisted_action for item in replayed.transitions] == [
        "ENTER",
        "HOLD",
        "HOLD",
    ]
    assert [item.event for item in replayed.transitions] == [ENTER, DEFEND, RECOVER]
    assert replayed.state == OPEN_INITIAL


def test_action_only_database_rows_are_explicitly_insufficient_for_replay() -> None:
    rows = position_event_records(entered())
    action_only = [{key: value for key, value in rows[0].items() if key != "notes"}]

    with pytest.raises(ValueError, match="lifecycle transition payload"):
        replay_position_event_records(action_only, symbol="BTC-USD")


@pytest.mark.parametrize("event", [HOLD, DEFEND])
def test_state_only_events_cannot_silently_move_the_stop(event: str) -> None:
    lifecycle = entered()
    before = economics(lifecycle)

    refused = apply_position_event(
        lifecycle,
        event=event,
        event_time=at(2),
        stop_price="95",
    )

    assert refused.accepted is False
    assert refused.reason_codes == ("POSITION_STATE_STOP_NOT_APPLICABLE",)
    assert economics(refused) == before


def test_recover_cannot_silently_move_the_stop() -> None:
    lifecycle = apply_position_event(entered(), event=DEFEND, event_time=at(2))
    before = economics(lifecycle)

    refused = apply_position_event(
        lifecycle,
        event=RECOVER,
        event_time=at(3),
        stop_price="95",
    )

    assert refused.accepted is False
    assert economics(refused) == before


@pytest.mark.parametrize(
    "mutation,match",
    [
        ({"quantity": Decimal("99")}, "tranche ledger"),
        ({"average_entry_price": Decimal("1")}, "average entry"),
    ],
)
def test_persistence_rejects_economic_ledger_drift(mutation, match: str) -> None:
    lifecycle = replace(entered(), **mutation)

    with pytest.raises(ValueError, match=match):
        lifecycle.as_record()
    with pytest.raises(ValueError, match=match):
        apply_position_event(lifecycle, event=HOLD, event_time=at(2))


def test_persistence_rejects_state_drift_from_tranche_count() -> None:
    lifecycle = apply_position_event(
        entered(),
        event=ADD,
        event_time=at(2),
        quantity="1",
        price="110",
    )

    with pytest.raises(ValueError, match="OPEN_INITIAL"):
        replace(lifecycle, state=OPEN_INITIAL).as_record()


def test_persistence_rejects_noncontiguous_tranche_identity() -> None:
    lifecycle = entered()
    bad_tranche = replace(lifecycle.tranches[0], tranche_number=2)

    with pytest.raises(ValueError, match="contiguous"):
        replace(lifecycle, tranches=(bad_tranche,)).as_record()


def test_snapshot_tampering_is_detected_by_replay_comparison() -> None:
    record = realistic_lifecycle().as_record()
    record["stop_price"] = "99"

    with pytest.raises(ValueError, match="does not match replayed transitions"):
        restore_position_lifecycle(record)


def test_database_outer_fields_must_match_the_transition_payload() -> None:
    row = dict(position_event_records(entered())[0])
    row["quantity"] = Decimal("2")

    with pytest.raises(ValueError, match="quantity does not match"):
        replay_position_event_records([row], symbol="BTC-USD")


def test_missed_state_is_position_free_and_schema_timestamp_compatible() -> None:
    lifecycle = apply_position_event(
        pending(),
        event=MISS,
        event_time=at(1),
        reason_codes=("NO_CHASE_VIOLATION",),
    )

    assert lifecycle.state == MISSED
    assert lifecycle.quantity == 0
    assert lifecycle.tranches == ()
    assert lifecycle.average_entry_price is None
    assert lifecycle.opened_at == lifecycle.closed_at == at(1)
    assert lifecycle.persisted_status == "missed"
    assert restore_position_lifecycle(lifecycle.as_record()) == lifecycle


def test_status_mapping_is_exhaustive_and_never_persists_rich_state_names() -> None:
    expected = {
        WATCH: None,
        PENDING_ENTRY: None,
        OPEN_INITIAL: "open",
        OPEN_ADDED: "open",
        DEFENSIVE: "open",
        CLOSED: "closed",
        MISSED: "missed",
    }

    assert {state: persisted_status_for_state(state) for state in expected} == expected


def test_unequal_three_tranche_trim_is_exactly_pro_rata() -> None:
    lifecycle = apply_position_event(
        pending(),
        event=ENTER,
        event_time=at(1),
        quantity="40",
        price="100",
        stop_price="90",
    )
    lifecycle = apply_position_event(
        lifecycle,
        event=ADD,
        event_time=at(2),
        quantity="35",
        price="110",
    )
    lifecycle = apply_position_event(
        lifecycle,
        event=ADD,
        event_time=at(3),
        quantity="25",
        price="120",
    )
    before_average = lifecycle.average_entry_price

    trimmed = apply_position_event(
        lifecycle,
        event=TRIM,
        event_time=at(4),
        quantity="20",
    )

    assert [item.quantity for item in trimmed.tranches] == [
        Decimal("32.0"),
        Decimal("28.00"),
        Decimal("20.00"),
    ]
    assert trimmed.quantity == Decimal("80")
    assert trimmed.average_entry_price == before_average == Decimal("108.5")
    assert float(trimmed.average_entry_price) == pytest.approx(
        weighted_average_entry([100, 110, 120], [40, 35, 25]),
    )


@pytest.mark.parametrize("direction", ["long", "short"])
def test_add_trim_exit_ledger_mechanics_are_side_symmetric(direction: str) -> None:
    lifecycle = entered(direction=direction)
    lifecycle = apply_position_event(
        lifecycle,
        event=ADD,
        event_time=at(2),
        quantity="3",
        price="120",
    )
    assert lifecycle.average_entry_price == Decimal("115")
    lifecycle = apply_position_event(
        lifecycle,
        event=TRIM,
        event_time=at(3),
        quantity="1",
    )
    assert lifecycle.quantity == Decimal("3")
    assert lifecycle.average_entry_price == Decimal("115")
    lifecycle = apply_position_event(lifecycle, event=EXIT, event_time=at(4))
    assert lifecycle.state == CLOSED
    assert lifecycle.quantity == 0
    assert lifecycle.tranches == ()


def test_no_average_down_policy_has_not_leaked_into_btc150() -> None:
    lifecycle = apply_position_event(
        entered(),
        event=ADD,
        event_time=at(2),
        quantity="1",
        price="90",
    )

    assert lifecycle.accepted is True
    assert lifecycle.state == OPEN_ADDED
    assert lifecycle.average_entry_price == Decimal("95")


def test_repeated_partial_trims_never_leave_zero_quantity_open() -> None:
    lifecycle = entered()
    lifecycle = apply_position_event(
        lifecycle,
        event=TRIM,
        event_time=at(2),
        quantity="0.9",
    )
    lifecycle = apply_position_event(
        lifecycle,
        event=TRIM,
        event_time=at(3),
        quantity="0.09",
    )

    assert lifecycle.state == OPEN_INITIAL
    assert lifecycle.quantity == Decimal("0.01")
    assert lifecycle.tranches[0].quantity == Decimal("0.01")


def test_reason_code_pass_through_is_ordered_and_deduplicated() -> None:
    lifecycle = apply_position_event(
        pending(),
        event=MISS,
        event_time=at(1),
        reason_codes=("NO_CHASE_VIOLATION", "NO_CHASE_VIOLATION", "SETUP_DECAYED"),
    )

    assert lifecycle.reason_codes == (
        "POSITION_STATE_MISSED",
        "NO_CHASE_VIOLATION",
        "SETUP_DECAYED",
    )


@pytest.mark.parametrize(
    "direction,equal,tighter,wider",
    [
        ("long", "90", "95", "85"),
        ("short", "110", "105", "115"),
    ],
)
def test_stop_monotonicity_exactly_handles_equal_tighter_and_wider(
    direction: str,
    equal: str,
    tighter: str,
    wider: str,
) -> None:
    lifecycle = entered(direction=direction)
    same = apply_position_event(
        lifecycle,
        event=STOP_MOVE,
        event_time=at(2),
        stop_price=equal,
    )
    improved = apply_position_event(
        lifecycle,
        event=STOP_MOVE,
        event_time=at(2),
        stop_price=tighter,
    )
    refused = apply_position_event(
        lifecycle,
        event=STOP_MOVE,
        event_time=at(2),
        stop_price=wider,
    )

    assert same.accepted is True
    assert improved.accepted is True
    assert refused.accepted is False
    assert refused.stop_price == lifecycle.stop_price


def test_duplicate_add_commands_are_not_claimed_to_be_idempotent() -> None:
    lifecycle = entered()
    command = {
        "event": ADD,
        "event_time": at(2),
        "quantity": "1",
        "price": "110",
    }

    once = apply_position_event(lifecycle, **command)
    twice = apply_position_event(once, **command)

    assert once.quantity == Decimal("2")
    assert twice.quantity == Decimal("3")
    assert twice.tranche_count == 3
