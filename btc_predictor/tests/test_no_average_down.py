"""BTC-151 no-average-down invariant tests."""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.portfolio import (
    ADD,
    ENTER,
    NO_AVERAGE_DOWN_POLICY_VERSION,
    OPEN_ADDED,
    OPEN_INITIAL,
    PENDING_ENTRY,
    TRIM,
    apply_position_event,
    position_event_records,
    position_is_losing_at_price,
    replay_position_event_records,
    restore_position_lifecycle,
    start_position_lifecycle,
)


START = datetime(2026, 8, 31, tzinfo=UTC)
REFUSAL = "POSITION_STATE_ADD_REFUSED_AVERAGE_DOWN"


def at(hours: int) -> datetime:
    return START + timedelta(hours=hours)


def entered(*, direction: str = "long"):
    lifecycle = start_position_lifecycle(
        symbol="BTC-USD",
        direction=direction,
        state=PENDING_ENTRY,
        config_metadata={"config_version": "strategy_config_v2"},
    )
    return apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=at(1),
        quantity="1",
        price="100",
        stop_price="90" if direction == "long" else "110",
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
    )


def test_policy_version_is_explicit() -> None:
    assert NO_AVERAGE_DOWN_POLICY_VERSION == "NO_AVERAGE_DOWN_V1"


@pytest.mark.parametrize(
    "direction,current_price,expected",
    [
        ("long", "99.999", True),
        ("long", "100", False),
        ("long", "100.001", False),
        ("short", "100.001", True),
        ("short", "100", False),
        ("short", "99.999", False),
    ],
)
def test_losing_position_detection_is_side_aware(
    direction: str,
    current_price: str,
    expected: bool,
) -> None:
    assert position_is_losing_at_price(
        direction=direction,
        average_entry_price="100",
        current_price=current_price,
    ) is expected


@pytest.mark.parametrize(
    "kwargs,match",
    [
        (
            {
                "direction": "flat",
                "average_entry_price": "100",
                "current_price": "100",
            },
            "direction",
        ),
        (
            {
                "direction": "long",
                "average_entry_price": "0",
                "current_price": "100",
            },
            "average_entry_price",
        ),
        (
            {
                "direction": "long",
                "average_entry_price": "100",
                "current_price": "NaN",
            },
            "current_price",
        ),
    ],
)
def test_losing_position_detection_rejects_invalid_inputs(kwargs, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        position_is_losing_at_price(**kwargs)


@pytest.mark.parametrize(
    "direction,add_price",
    [("long", "99"), ("short", "101")],
)
def test_losing_add_is_refused_without_mutating_economics(
    direction: str,
    add_price: str,
) -> None:
    lifecycle = entered(direction=direction)
    before = economics(lifecycle)

    refused = apply_position_event(
        lifecycle,
        event=ADD,
        event_time=at(2),
        quantity="2",
        price=add_price,
        reason_codes=("ADD_SCORE_VALID",),
    )

    assert refused.accepted is False
    assert refused.reason_codes == (REFUSAL, "ADD_SCORE_VALID")
    assert economics(refused) == before
    transition = refused.transitions[-1]
    assert transition.accepted is False
    assert transition.requested_quantity == Decimal("2")
    assert transition.price == Decimal(add_price)
    assert transition.persisted_action == "HOLD"


@pytest.mark.parametrize("direction", ["long", "short"])
def test_breakeven_add_is_allowed_by_btc151(direction: str) -> None:
    lifecycle = apply_position_event(
        entered(direction=direction),
        event=ADD,
        event_time=at(2),
        quantity="1",
        price="100",
    )

    assert lifecycle.accepted is True
    assert lifecycle.state == OPEN_ADDED
    assert lifecycle.average_entry_price == Decimal("100")


@pytest.mark.parametrize(
    "direction,add_price,expected_average",
    [("long", "110", "105"), ("short", "90", "95")],
)
def test_profitable_add_is_allowed(
    direction: str,
    add_price: str,
    expected_average: str,
) -> None:
    lifecycle = apply_position_event(
        entered(direction=direction),
        event=ADD,
        event_time=at(2),
        quantity="1",
        price=add_price,
    )

    assert lifecycle.accepted is True
    assert lifecycle.average_entry_price == Decimal(expected_average)


def test_guard_uses_weighted_average_after_multiple_tranches_and_trim() -> None:
    lifecycle = apply_position_event(
        entered(),
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
    assert lifecycle.average_entry_price == Decimal("115")

    refused = apply_position_event(
        lifecycle,
        event=ADD,
        event_time=at(4),
        quantity="1",
        price="114.999",
    )
    accepted = apply_position_event(
        lifecycle,
        event=ADD,
        event_time=at(4),
        quantity="1",
        price="115",
    )

    assert refused.accepted is False
    assert refused.reason_codes == (REFUSAL,)
    assert accepted.accepted is True


def test_refusal_round_trips_through_snapshot_and_database_records() -> None:
    lifecycle = apply_position_event(
        entered(),
        event=ADD,
        event_time=at(2),
        quantity="2",
        price="90",
    )

    assert restore_position_lifecycle(lifecycle.as_record()) == lifecycle
    rows = position_event_records(lifecycle)
    payload = json.loads(rows[-1]["notes"])
    assert rows[-1]["action"] == "HOLD"
    assert payload["accepted"] is False
    assert payload["reason_codes"] == [REFUSAL]
    assert payload["requested_quantity"] == "2"
    assert payload["price"] == "90"
    assert replay_position_event_records(
        rows,
        symbol="BTC-USD",
        config_metadata={"config_version": "strategy_config_v2"},
    ) == lifecycle


def test_repeated_refusals_are_deterministic() -> None:
    lifecycle = entered()
    first = apply_position_event(
        lifecycle,
        event=ADD,
        event_time=at(2),
        quantity="1",
        price="99",
    )
    second = apply_position_event(
        lifecycle,
        event=ADD,
        event_time=at(2),
        quantity="1",
        price="99",
    )

    assert first == second
