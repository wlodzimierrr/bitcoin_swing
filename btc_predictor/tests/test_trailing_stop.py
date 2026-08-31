"""BTC-156: trailing stop progression."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from btc_predictor.portfolio import (
    ADD,
    ENTER,
    PENDING_ENTRY,
    STOP_MOVE,
    apply_position_event,
    start_position_lifecycle,
)
from btc_predictor.risk import (
    CONFIRMATION_STOP,
    PROFIT_PROTECTION_TRAIL,
    THESIS_STOP,
    TRAILING_STOP_FEATURE_ID,
    TRAILING_STOP_POLICY_VERSION,
    TRAILING_STOP_REASON_CODES,
    TRAILING_STOP_STAGES,
    calculate_trailing_stop,
    calculate_volatility_buffer,
    stop_advance_count,
    trail_stop_for_position,
)


SYMBOL = "BTC-USD"
START = datetime(2024, 7, 1, tzinfo=timezone.utc)


def at(hours: int) -> datetime:
    return START + timedelta(hours=hours)


def long_trail(**kwargs):
    base = {
        "direction": "long",
        "previous_stop": "90000",
        "structure_price": "98000",
        "buffer": "1500",
    }
    return calculate_trailing_stop(**{**base, **kwargs})


def test_metadata_is_stable() -> None:
    assert TRAILING_STOP_FEATURE_ID == "TRAILING_STOP"
    assert TRAILING_STOP_POLICY_VERSION == "TRAILING_STOP_V1"
    assert TRAILING_STOP_STAGES == (
        "THESIS_STOP",
        "CONFIRMATION_STOP",
        "PROFIT_PROTECTION_TRAIL",
    )


# --- the rulebook formula ------------------------------------------------


def test_long_candidate_is_the_higher_low_less_the_buffer() -> None:
    result = long_trail()

    assert result.candidate_stop == Decimal("96500")
    assert result.stop_price == Decimal("96500")
    assert result.advanced is True
    assert result.reason_codes == ("TRAILING_STOP_ADVANCED",)


def test_short_candidate_is_the_lower_high_plus_the_buffer() -> None:
    result = calculate_trailing_stop(
        direction="short",
        previous_stop="110000",
        structure_price="102000",
        buffer="1500",
    )

    # Mirrored: the buffer sits above the structure and the ratchet takes the
    # minimum instead of the maximum.
    assert result.candidate_stop == Decimal("103500")
    assert result.stop_price == Decimal("103500")
    assert result.advanced is True


def test_a_zero_buffer_places_the_stop_exactly_at_the_structure() -> None:
    result = long_trail(buffer="0")

    assert result.candidate_stop == Decimal("98000")


# --- the ratchet ---------------------------------------------------------


@pytest.mark.parametrize(
    ("structure", "expected_stop", "advanced"),
    [
        ("98000", "96500", True),
        ("95000", "93500", True),
        ("91500", "90000", False),
        ("100000", "98500", True),
    ],
)
def test_the_stop_takes_the_maximum_of_standing_and_candidate(
    structure: str,
    expected_stop: str,
    advanced: bool,
) -> None:
    result = long_trail(structure_price=structure)

    assert result.stop_price == Decimal(expected_stop)
    assert result.advanced is advanced


def test_a_long_stop_can_never_move_lower() -> None:
    result = long_trail(structure_price="80000")

    # The hard invariant. A candidate below the standing stop is discarded,
    # not recorded as a loosened stop.
    assert result.candidate_stop == Decimal("78500")
    assert result.stop_price == Decimal("90000")
    assert result.advanced is False
    assert result.reason_codes == ("TRAILING_STOP_HELD",)


def test_a_short_stop_can_never_move_higher() -> None:
    result = calculate_trailing_stop(
        direction="short",
        previous_stop="105000",
        structure_price="115000",
        buffer="1500",
    )

    assert result.candidate_stop == Decimal("116500")
    assert result.stop_price == Decimal("105000")
    assert result.advanced is False


def test_a_repeated_structure_holds_rather_than_re_advancing() -> None:
    first = long_trail()
    second = long_trail(
        previous_stop=first.stop_price,
        advance_count=first.advance_count,
    )

    assert second.stop_price == first.stop_price
    assert second.advanced is False
    assert second.advance_count == first.advance_count


def test_a_monotonic_sequence_of_higher_lows_never_retreats() -> None:
    stop = Decimal("90000")
    advances = 0
    seen = [stop]
    for structure in ("94000", "93000", "99000", "97000", "105000", "101000"):
        result = calculate_trailing_stop(
            direction="long",
            previous_stop=stop,
            structure_price=structure,
            buffer="1500",
            advance_count=advances,
        )
        stop = result.stop_price
        advances = result.advance_count
        seen.append(stop)

    assert seen == sorted(seen)
    assert stop == Decimal("103500")
    assert advances == 3


def test_the_ratchet_uses_the_shared_decision_tolerance() -> None:
    # A candidate inside DECISION_COMPARISON_V1's tolerance is not an advance,
    # so float noise cannot ratchet the stop.
    result = long_trail(previous_stop="96500", structure_price="98000.0000000000001")

    assert result.advanced is False
    assert result.stop_price == Decimal("96500")


# --- advance only on new confirmed structure ------------------------------


def test_no_new_structure_holds_the_standing_stop() -> None:
    result = calculate_trailing_stop(
        direction="long",
        previous_stop="90000",
        buffer="1500",
    )

    # Rulebook 22: no daily mechanical trailing is required, so a quiet bar is
    # an ordinary hold rather than a failure.
    assert result.stop_price == Decimal("90000")
    assert result.complete is True
    assert result.advanced is False
    assert result.reason_codes == ("TRAILING_STOP_NO_NEW_STRUCTURE",)


def test_no_structure_and_no_standing_stop_is_incomplete() -> None:
    result = calculate_trailing_stop(direction="long", previous_stop=None)

    assert result.complete is False
    assert result.stop_price is None
    assert result.reason_codes == (
        "TRAILING_STOP_NO_NEW_STRUCTURE",
        "TRAILING_STOP_INPUT_MISSING",
    )


def test_an_incomplete_buffer_yields_no_advance() -> None:
    result = long_trail(buffer=None)

    assert result.advanced is False
    assert result.stop_price == Decimal("90000")
    assert result.reason_codes == ("TRAILING_STOP_BUFFER_INCOMPLETE",)


def test_a_first_stop_can_be_established_without_a_standing_one() -> None:
    result = calculate_trailing_stop(
        direction="long",
        previous_stop=None,
        structure_price="98000",
        buffer="1500",
    )

    assert result.stop_price == Decimal("96500")
    assert result.advanced is True
    assert result.previous_stop is None


# --- guards ---------------------------------------------------------------


def test_a_non_positive_candidate_is_refused() -> None:
    result = calculate_trailing_stop(
        direction="long",
        previous_stop="500",
        structure_price="1000",
        buffer="1000",
    )

    assert result.candidate_stop == Decimal("0")
    assert result.stop_price == Decimal("500")
    assert result.reason_codes == ("TRAILING_STOP_CANDIDATE_NON_POSITIVE",)


@pytest.mark.parametrize("current", ["96500", "96000", "90000"])
def test_a_long_candidate_at_or_above_price_is_refused(current: str) -> None:
    result = long_trail(current_price=current)

    # A stop at or above the current price is an immediate exit dressed up as
    # a stop move.
    assert result.advanced is False
    assert result.stop_price == Decimal("90000")
    assert result.reason_codes == ("TRAILING_STOP_CANDIDATE_BEYOND_PRICE",)


def test_a_long_candidate_below_price_is_accepted() -> None:
    result = long_trail(current_price="99000")

    assert result.advanced is True
    assert result.stop_price == Decimal("96500")


def test_a_short_candidate_at_or_below_price_is_refused() -> None:
    result = calculate_trailing_stop(
        direction="short",
        previous_stop="110000",
        structure_price="102000",
        buffer="1500",
        current_price="103500",
    )

    assert result.advanced is False
    assert result.stop_price == Decimal("110000")
    assert result.reason_codes == ("TRAILING_STOP_CANDIDATE_BEYOND_PRICE",)


def test_the_price_guard_is_off_when_no_price_is_supplied() -> None:
    assert long_trail().advanced is True


# --- stages ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("advance_count", "stage"),
    [
        (0, THESIS_STOP),
        (1, CONFIRMATION_STOP),
        (2, PROFIT_PROTECTION_TRAIL),
        (9, PROFIT_PROTECTION_TRAIL),
    ],
)
def test_the_stage_is_derived_from_the_advance_count(
    advance_count: int,
    stage: str,
) -> None:
    result = calculate_trailing_stop(
        direction="long",
        previous_stop="90000",
        advance_count=advance_count,
    )

    assert result.stage == stage


def test_the_stages_progress_in_rulebook_order() -> None:
    thesis = calculate_trailing_stop(direction="long", previous_stop="90000")
    confirmation = long_trail()
    profit = long_trail(
        previous_stop=confirmation.stop_price,
        structure_price="104000",
        advance_count=confirmation.advance_count,
    )

    # Stage 1 is the wide structural stop, stage 2 the first advance under a
    # new higher low, stage 3 every advance after that.
    assert thesis.stage == THESIS_STOP
    assert confirmation.stage == CONFIRMATION_STOP
    assert profit.stage == PROFIT_PROTECTION_TRAIL
    assert profit.advance_count == 2


def test_a_held_stop_does_not_advance_the_stage() -> None:
    result = long_trail(structure_price="80000", advance_count=1)

    assert result.stage == CONFIRMATION_STOP
    assert result.advance_count == 1


# --- composition with BTC-150 and BTC-141 --------------------------------


def open_position(*, stop: str = "90000"):
    lifecycle = start_position_lifecycle(symbol=SYMBOL, state=PENDING_ENTRY)
    return apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=at(1),
        quantity="1",
        price="100000",
        stop_price=stop,
    )


def test_the_entry_stop_is_not_counted_as_an_advance() -> None:
    lifecycle = open_position()

    # The entry establishes the thesis stop; it does not trail it.
    assert stop_advance_count(lifecycle) == 0
    assert trail_stop_for_position(lifecycle).stage == THESIS_STOP


def test_advances_are_counted_from_the_ledger() -> None:
    lifecycle = apply_position_event(
        open_position(), event=STOP_MOVE, event_time=at(2), stop_price="93000"
    )
    assert stop_advance_count(lifecycle) == 1

    lifecycle = apply_position_event(
        lifecycle, event=ADD, event_time=at(3), quantity="1", price="105000",
        stop_price="96000",
    )

    # Rulebook 26 raises the stop as part of an add, which is an advance too.
    assert stop_advance_count(lifecycle) == 2


def test_a_refused_stop_move_does_not_count_as_an_advance() -> None:
    lifecycle = apply_position_event(
        open_position(), event=STOP_MOVE, event_time=at(2), stop_price="80000"
    )

    assert lifecycle.accepted is False
    assert stop_advance_count(lifecycle) == 0


def test_canonical_path_reads_direction_and_stop_from_the_ledger() -> None:
    lifecycle = open_position()

    result = trail_stop_for_position(
        lifecycle,
        structure_price="98000",
        buffer="1500",
    )

    assert result.direction == "long"
    assert result.previous_stop == Decimal("90000")
    assert result.stop_price == Decimal("96500")
    assert result.stage == CONFIRMATION_STOP


def test_canonical_path_stage_follows_the_stop_history() -> None:
    lifecycle = apply_position_event(
        open_position(), event=STOP_MOVE, event_time=at(2), stop_price="93000"
    )

    result = trail_stop_for_position(
        lifecycle,
        structure_price="98000",
        buffer="1500",
    )

    # Already advanced once, so this is stage 3, not stage 2.
    assert result.stage == PROFIT_PROTECTION_TRAIL
    assert result.advance_count == 2


def test_canonical_path_accepts_a_btc141_buffer_result() -> None:
    lifecycle = open_position()
    buffer = calculate_volatility_buffer(atr="5000", level_noise_estimate="1200")

    result = trail_stop_for_position(
        lifecycle,
        structure_price="98000",
        buffer=buffer,
    )

    assert buffer.complete is True
    assert result.buffer == buffer.buffer
    assert result.stop_price == Decimal("98000") - buffer.buffer


def test_canonical_path_holds_on_an_incomplete_buffer() -> None:
    lifecycle = open_position()
    buffer = calculate_volatility_buffer(atr=None)

    result = trail_stop_for_position(
        lifecycle,
        structure_price="98000",
        buffer=buffer,
    )

    assert buffer.complete is False
    assert result.advanced is False
    assert result.stop_price == Decimal("90000")
    assert result.reason_codes == ("TRAILING_STOP_BUFFER_INCOMPLETE",)


def test_an_advanced_stop_is_accepted_by_the_lifecycle() -> None:
    lifecycle = open_position()
    result = trail_stop_for_position(
        lifecycle, structure_price="98000", buffer="1500"
    )

    moved = apply_position_event(
        lifecycle,
        event=STOP_MOVE,
        event_time=at(2),
        stop_price=result.stop_price,
    )

    # BTC-150 owns whether a move is recordable; a ratcheted stop always is.
    assert moved.accepted is True
    assert moved.stop_price == Decimal("96500")


def test_a_held_stop_is_a_no_op_the_lifecycle_also_accepts() -> None:
    lifecycle = open_position()
    result = trail_stop_for_position(
        lifecycle, structure_price="80000", buffer="1500"
    )

    moved = apply_position_event(
        lifecycle,
        event=STOP_MOVE,
        event_time=at(2),
        stop_price=result.stop_price,
    )

    assert result.advanced is False
    assert moved.accepted is True
    assert moved.stop_price == Decimal("90000")


# --- malformed input ------------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"direction": "flat"}, "direction must be one of"),
        ({"previous_stop": "0"}, "previous_stop must be positive"),
        ({"previous_stop": "-1"}, "previous_stop must be positive"),
        ({"structure_price": "0"}, "structure_price must be positive"),
        ({"structure_price": "abc"}, "structure_price must be numeric"),
        ({"buffer": "-1"}, "buffer must be non-negative"),
        ({"current_price": "0"}, "current_price must be positive"),
        ({"advance_count": -1}, "advance_count must not be negative"),
        ({"advance_count": "1"}, "advance_count must be an integer"),
        ({"advance_count": True}, "advance_count must be an integer"),
    ],
)
def test_invalid_inputs_fail_fast(kwargs, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        long_trail(**kwargs)


def test_a_lifecycle_without_a_direction_is_rejected() -> None:
    with pytest.raises(ValueError, match="direction"):
        trail_stop_for_position(object())


def test_an_unusable_buffer_type_is_rejected() -> None:
    with pytest.raises(TypeError, match="buffer must be"):
        trail_stop_for_position(open_position(), structure_price="98000", buffer=object())


# --- persistence ----------------------------------------------------------


def test_record_is_persistable_and_reconstructable() -> None:
    record = long_trail(
        current_price="99000",
        config_metadata={"config_version": "strategy_config_v2"},
    ).as_record()

    assert record == {
        "feature_id": "TRAILING_STOP",
        "policy_version": "TRAILING_STOP_V1",
        "direction": "long",
        "stage": "CONFIRMATION_STOP",
        "advance_count": 1,
        "previous_stop": "90000",
        "structure_price": "98000",
        "buffer": "1500",
        "candidate_stop": "96500",
        "stop_price": "96500",
        "current_price": "99000",
        "advanced": True,
        "config_metadata": {"config_version": "strategy_config_v2"},
        "complete": True,
        "reason_codes": ["TRAILING_STOP_ADVANCED"],
    }
    # The candidate is re-derivable from its own row.
    assert Decimal(record["candidate_stop"]) == Decimal(
        record["structure_price"]
    ) - Decimal(record["buffer"])


def test_the_record_refuses_a_loosened_long_stop() -> None:
    result = long_trail()

    with pytest.raises(ValueError, match="never move lower"):
        replace(result, stop_price=Decimal("85000")).as_record()


def test_the_record_refuses_a_loosened_short_stop() -> None:
    result = calculate_trailing_stop(
        direction="short",
        previous_stop="110000",
        structure_price="102000",
        buffer="1500",
    )

    with pytest.raises(ValueError, match="never move higher"):
        replace(result, stop_price=Decimal("120000")).as_record()


def test_the_record_refuses_a_stage_that_disagrees_with_the_count() -> None:
    result = long_trail()

    with pytest.raises(ValueError, match="stage does not match"):
        replace(result, stage=PROFIT_PROTECTION_TRAIL).as_record()
    with pytest.raises(ValueError, match="stage must be one of"):
        replace(result, stage="TIGHTEN").as_record()


def test_a_complete_record_requires_a_stop_price() -> None:
    result = long_trail()

    with pytest.raises(ValueError, match="requires a stop price"):
        replace(result, stop_price=None).as_record()


def test_recomputation_is_deterministic() -> None:
    assert long_trail().as_record() == long_trail().as_record()


def test_reason_codes_are_drawn_from_the_declared_set() -> None:
    results = [
        long_trail(),
        long_trail(structure_price="80000"),
        long_trail(buffer=None),
        long_trail(current_price="90000"),
        calculate_trailing_stop(direction="long", previous_stop=None),
        calculate_trailing_stop(
            direction="long", previous_stop="500", structure_price="1000",
            buffer="1000",
        ),
    ]

    for result in results:
        for code in result.reason_codes:
            assert code in TRAILING_STOP_REASON_CODES
