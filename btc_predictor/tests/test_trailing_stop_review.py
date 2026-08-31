"""Independent correctness review coverage for BTC-156."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.portfolio import (
    ADD,
    DEFEND,
    ENTER,
    EXIT,
    HOLD,
    PENDING_ENTRY,
    STOP_MOVE,
    TRIM,
    apply_position_event,
    position_event_records,
    replay_position_event_records,
    restore_position_lifecycle,
    start_position_lifecycle,
)
from btc_predictor.risk import (
    CONFIRMATION_STOP,
    HIGHER_LOW,
    LOWER_HIGH,
    PROFIT_PROTECTION_TRAIL,
    THESIS_STOP,
    TRAILING_STOP_FEATURE_ID,
    ConfirmedTrailingStructure,
    apply_trailing_stop,
    calculate_trailing_stop,
    calculate_volatility_buffer,
    stop_advance_count,
    trail_stop_for_position,
    trailing_stop_from_record,
    used_trailing_structure_ids,
)


START = datetime(2024, 8, 1, tzinfo=timezone.utc)
METADATA = load_strategy_config().run_metadata()


def at(hours: int) -> datetime:
    return START + timedelta(hours=hours)


def open_position(*, direction: str = "long", stop: str = "90"):
    lifecycle = start_position_lifecycle(
        symbol="BTC-USD",
        direction=direction,
        state=PENDING_ENTRY,
        config_metadata=METADATA,
    )
    return apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=at(1),
        quantity="1",
        price="100",
        stop_price=stop,
    )


def structure(
    identifier: str,
    price: str,
    *,
    direction: str = "long",
    level_at: datetime | None = None,
    detected_at: datetime | None = None,
) -> ConfirmedTrailingStructure:
    return ConfirmedTrailingStructure(
        structure_id=identifier,
        source_feature_id=(
            "ENTRY_TRIGGER_HIGHER_LOW"
            if direction == "long"
            else "ENTRY_TRIGGER_LOWER_HIGH"
        ),
        direction=direction,
        structure_type=HIGHER_LOW if direction == "long" else LOWER_HIGH,
        price=Decimal(price),
        level_timestamp=level_at or at(1),
        detected_at=detected_at or at(2),
        config_metadata=METADATA,
        reason_codes=(
            "HIGHER_LOW_CONFIRMED" if direction == "long" else "LOWER_HIGH_CONFIRMED",
        ),
    )


def buffer(*, atr: str = "10", noise: str = "0"):
    return calculate_volatility_buffer(
        atr=atr,
        level_noise_estimate=noise,
        config_metadata=METADATA,
    )


def persisted_result(**changes):
    inputs = {
        "direction": "long",
        "previous_stop": "90",
        "structure_price": "100",
        "buffer": "3",
        "current_price": "110",
        "config_metadata": METADATA,
        "evaluated_at": at(3),
        "structure_id": "hl-1",
        "structure_source_feature_id": "ENTRY_TRIGGER_HIGHER_LOW",
        "structure_type": HIGHER_LOW,
        "structure_level_timestamp": at(1),
        "structure_detected_at": at(2),
        "structure_reason_codes": ("HIGHER_LOW_CONFIRMED",),
    }
    return calculate_trailing_stop(**{**inputs, **changes})


def test_independent_long_and_short_formula_examples() -> None:
    long_advance = calculate_trailing_stop(
        direction="long", previous_stop="90", structure_price="100", buffer="3"
    )
    long_hold = calculate_trailing_stop(
        direction="long", previous_stop="97", structure_price="96", buffer="3"
    )
    short_advance = calculate_trailing_stop(
        direction="short", previous_stop="110", structure_price="102", buffer="3"
    )
    short_hold = calculate_trailing_stop(
        direction="short", previous_stop="105", structure_price="105", buffer="3"
    )

    assert (long_advance.candidate_stop, long_advance.stop_price) == (
        Decimal("97"),
        Decimal("97"),
    )
    assert (long_hold.candidate_stop, long_hold.stop_price) == (
        Decimal("93"),
        Decimal("97"),
    )
    assert (short_advance.candidate_stop, short_advance.stop_price) == (
        Decimal("105"),
        Decimal("105"),
    )
    assert (short_hold.candidate_stop, short_hold.stop_price) == (
        Decimal("108"),
        Decimal("105"),
    )


@pytest.mark.parametrize(
    ("direction", "initial", "candidates"),
    [
        ("long", "90", ("95", "94", "98", "97", "101")),
        ("short", "110", ("105", "106", "102", "103", "99")),
    ],
)
def test_ratchet_is_monotonic_over_independent_candidate_sequences(
    direction: str,
    initial: str,
    candidates: tuple[str, ...],
) -> None:
    stop = Decimal(initial)
    observed = [stop]
    for candidate in candidates:
        result = calculate_trailing_stop(
            direction=direction,
            previous_stop=stop,
            structure_price=candidate,
            buffer="0",
        )
        stop = result.stop_price
        observed.append(stop)

    expected = (
        [Decimal(value) for value in ("90", "95", "95", "98", "98", "101")]
        if direction == "long"
        else [Decimal(value) for value in ("110", "105", "105", "102", "102", "99")]
    )
    assert observed == expected


@pytest.mark.parametrize(
    ("direction", "candidate", "advanced"),
    [
        ("long", "100", False),
        ("long", "100.00000000005", False),
        ("long", "100.0000000001", False),
        ("long", "100.0000000002", True),
        ("long", "99.9999999998", False),
        ("short", "100", False),
        ("short", "99.99999999995", False),
        ("short", "99.9999999999", False),
        ("short", "99.9999999998", True),
        ("short", "100.0000000002", False),
    ],
)
def test_decision_tolerance_boundary_is_symmetric(
    direction: str,
    candidate: str,
    advanced: bool,
) -> None:
    result = calculate_trailing_stop(
        direction=direction,
        previous_stop="100",
        structure_price=candidate,
        buffer="0",
    )
    assert result.advanced is advanced


@pytest.mark.parametrize(
    ("direction", "candidate", "current", "accepted"),
    [
        ("long", "100", "100", False),
        ("long", "100", "100.00000000005", False),
        ("long", "100", "100.0000000002", True),
        ("short", "100", "100", False),
        ("short", "100", "99.99999999995", False),
        ("short", "100", "99.9999999998", True),
    ],
)
def test_current_price_guard_uses_the_same_boundary_policy(
    direction: str,
    candidate: str,
    current: str,
    accepted: bool,
) -> None:
    previous = "90" if direction == "long" else "110"
    result = calculate_trailing_stop(
        direction=direction,
        previous_stop=previous,
        structure_price=candidate,
        buffer="0",
        current_price=current,
    )
    assert result.advanced is accepted
    if not accepted:
        assert result.reason_codes == ("TRAILING_STOP_CANDIDATE_BEYOND_PRICE",)


@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-Infinity"])
@pytest.mark.parametrize("field", ["previous_stop", "structure_price", "buffer"])
def test_non_finite_inputs_fail_fast(field: str, bad: str) -> None:
    inputs = {
        "direction": "long",
        "previous_stop": "90",
        "structure_price": "100",
        "buffer": "3",
    }
    inputs[field] = bad
    with pytest.raises(ValueError, match="finite"):
        calculate_trailing_stop(**inputs)


def test_missing_structure_preserves_and_persists_the_standing_stop() -> None:
    result = calculate_trailing_stop(
        direction="long",
        previous_stop="90",
        buffer="999",
        config_metadata=METADATA,
        evaluated_at=at(3),
    )
    record = result.as_record()

    assert result.complete is True
    assert result.stop_price == Decimal("90")
    assert result.reason_codes == ("TRAILING_STOP_NO_NEW_STRUCTURE",)
    assert record["stop_price"] == "90"
    assert trailing_stop_from_record(record) == result


def test_incomplete_btc141_buffer_preserves_stop_but_marks_candidate_incomplete() -> None:
    result = trail_stop_for_position(
        open_position(),
        structure=structure("hl-1", "100"),
        buffer=calculate_volatility_buffer(atr=None, config_metadata=METADATA),
        as_of=at(3),
    )

    assert result.stop_price == Decimal("90")
    assert result.complete is False
    assert result.buffer is None
    assert result.buffer_feature_id == "VOLATILITY_BUFFER"
    assert result.buffer_reason_codes == ("VOLATILITY_BUFFER_INPUT_MISSING",)
    assert trailing_stop_from_record(result.as_record()) == result


def test_future_structure_is_rejected_and_boundary_equality_is_available() -> None:
    lifecycle = open_position()
    future = structure("hl-future", "100", detected_at=at(4))
    boundary = structure("hl-boundary", "100", detected_at=at(3))

    with pytest.raises(ValueError, match="available by as_of"):
        trail_stop_for_position(
            lifecycle,
            structure=future,
            buffer=buffer(),
            as_of=at(3),
        )
    assert trail_stop_for_position(
        lifecycle,
        structure=boundary,
        buffer=buffer(),
        as_of=at(3),
    ).advanced


def test_applied_structure_identity_prevents_retrigger_after_buffer_shrink() -> None:
    lifecycle = open_position()
    confirmed = structure("hl-1", "100")
    first = trail_stop_for_position(
        lifecycle,
        structure=confirmed,
        buffer=buffer(atr="10"),
        as_of=at(3),
    )
    moved = apply_trailing_stop(lifecycle, first, event_time=at(3))
    repeated = trail_stop_for_position(
        moved,
        structure=confirmed,
        buffer=buffer(atr="1"),
        as_of=at(4),
    )

    assert used_trailing_structure_ids(moved) == ("hl-1",)
    assert repeated.stop_price == Decimal("97")
    assert repeated.advanced is False
    assert repeated.structure_already_used is True
    assert repeated.reason_codes == ("TRAILING_STOP_STRUCTURE_ALREADY_USED",)
    assert stop_advance_count(moved) == 1


def test_pure_re_evaluation_is_deterministic_until_application() -> None:
    lifecycle = open_position()
    inputs = {
        "structure": structure("hl-1", "100"),
        "buffer": buffer(),
        "as_of": at(3),
    }

    first = trail_stop_for_position(lifecycle, **inputs)
    second = trail_stop_for_position(lifecycle, **inputs)

    assert first.as_record() == second.as_record()
    assert lifecycle.stop_price == Decimal("90")
    assert stop_advance_count(lifecycle) == 0


def test_advance_count_requires_an_actual_accepted_tightening() -> None:
    lifecycle = open_position()
    same_move = apply_position_event(
        lifecycle, event=STOP_MOVE, event_time=at(2), stop_price="90"
    )
    same_add = apply_position_event(
        same_move,
        event=ADD,
        event_time=at(3),
        quantity="1",
        price="105",
        stop_price="90",
    )
    tighter_add = apply_position_event(
        same_add,
        event=ADD,
        event_time=at(4),
        quantity="1",
        price="110",
        stop_price="95",
    )
    refused = apply_position_event(
        tighter_add, event=STOP_MOVE, event_time=at(5), stop_price="80"
    )

    assert stop_advance_count(same_move) == 0
    assert stop_advance_count(same_add) == 0
    assert stop_advance_count(tighter_add) == 1
    assert stop_advance_count(refused) == 1


def test_realistic_lifecycle_replays_with_identical_count_stage_and_identity() -> None:
    lifecycle = open_position()
    first = trail_stop_for_position(
        lifecycle,
        structure=structure("hl-1", "96"),
        buffer=buffer(atr="10"),
        as_of=at(3),
    )
    lifecycle = apply_trailing_stop(lifecycle, first, event_time=at(3))
    lifecycle = apply_position_event(
        lifecycle,
        event=ADD,
        event_time=at(4),
        quantity="1",
        price="105",
        stop_price="94",
    )
    lifecycle = apply_position_event(lifecycle, event=DEFEND, event_time=at(5))
    lifecycle = apply_position_event(lifecycle, event=HOLD, event_time=at(6))
    second = trail_stop_for_position(
        lifecycle,
        structure=structure("hl-2", "99", detected_at=at(7)),
        buffer=buffer(atr="10", noise="4"),
        as_of=at(7),
    )
    lifecycle = apply_trailing_stop(lifecycle, second, event_time=at(7))
    refused = apply_position_event(
        lifecycle, event=STOP_MOVE, event_time=at(8), stop_price="80"
    )
    lifecycle = apply_position_event(
        refused, event=TRIM, event_time=at(9), quantity="0.5", price="108"
    )

    snapshot = restore_position_lifecycle(lifecycle.as_record())
    db_replay = replay_position_event_records(
        position_event_records(lifecycle),
        symbol="BTC-USD",
        config_metadata=METADATA,
    )

    for version in (lifecycle, snapshot, db_replay):
        assert version.stop_price == Decimal("95")
        assert stop_advance_count(version) == 3
        assert used_trailing_structure_ids(version) == ("hl-1", "hl-2")
        assert trail_stop_for_position(version, as_of=at(10)).stage == (
            PROFIT_PROTECTION_TRAIL
        )


def test_defensive_position_accepts_a_tighter_structural_stop() -> None:
    lifecycle = apply_position_event(
        open_position(), event=DEFEND, event_time=at(2)
    )
    result = trail_stop_for_position(
        lifecycle,
        structure=structure("hl-defensive", "100"),
        buffer=buffer(),
        as_of=at(3),
    )
    moved = apply_trailing_stop(lifecycle, result, event_time=at(3))

    assert moved.accepted is True
    assert moved.state == "DEFENSIVE"
    assert moved.stop_price == Decimal("97")


def test_btc141_final_buffer_and_provenance_are_consumed() -> None:
    lifecycle = open_position()
    atr_bound = trail_stop_for_position(
        lifecycle,
        structure=structure("hl-atr", "100"),
        buffer=buffer(atr="20", noise="2"),
        as_of=at(3),
    )
    noise_bound = trail_stop_for_position(
        lifecycle,
        structure=structure("hl-noise", "100"),
        buffer=buffer(atr="10", noise="7"),
        as_of=at(3),
    )

    assert (atr_bound.buffer, atr_bound.candidate_stop) == (
        Decimal("6.00"),
        Decimal("94.00"),
    )
    assert (noise_bound.buffer, noise_bound.candidate_stop) == (
        Decimal("7"),
        Decimal("93"),
    )
    assert atr_bound.buffer_feature_id == noise_bound.buffer_feature_id == (
        "VOLATILITY_BUFFER"
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("feature_id", "OTHER"),
        ("policy_version", "TRAILING_STOP_V0"),
        ("direction", "short"),
        ("candidate_stop", "96"),
        ("stop_price", "90"),
        ("advanced", False),
        ("advance_count", 2),
        ("stage", PROFIT_PROTECTION_TRAIL),
        ("buffer", "4"),
        ("reason_codes", ["TRAILING_STOP_HELD"]),
        ("current_price", "96"),
        ("structure_detected_at", at(4).isoformat()),
        ("structure_id", ""),
    ],
)
def test_persisted_record_tampering_is_rejected(field: str, value: object) -> None:
    record = persisted_result().as_record()
    record[field] = value

    with pytest.raises((TypeError, ValueError)):
        trailing_stop_from_record(record)


def test_held_record_cannot_claim_a_changed_stop() -> None:
    held = persisted_result(previous_stop="97", structure_price="96")
    tampered = held.as_record()
    tampered["stop_price"] = "98"

    with pytest.raises(ValueError, match="stop_price does not match"):
        trailing_stop_from_record(tampered)


def test_persisted_buffer_source_identity_cannot_be_rewritten() -> None:
    tampered = persisted_result().as_record()
    tampered["buffer_feature_id"] = "OTHER_BUFFER"
    tampered["buffer_policy_version"] = "OTHER_BUFFER_V1"

    with pytest.raises(ValueError, match="source identity is not supported"):
        trailing_stop_from_record(tampered)


def test_application_rejects_a_stale_calculation_atomically() -> None:
    lifecycle = open_position()
    result = trail_stop_for_position(
        lifecycle,
        structure=structure("hl-1", "100"),
        buffer=buffer(),
        as_of=at(3),
    )
    changed = apply_position_event(
        lifecycle, event=STOP_MOVE, event_time=at(2), stop_price="95"
    )

    with pytest.raises(ValueError, match="previous_stop does not match"):
        apply_trailing_stop(changed, result, event_time=at(3))
    assert changed.stop_price == Decimal("95")
    assert stop_advance_count(changed) == 1


def test_low_level_trailing_cannot_replace_btc142_initial_stop() -> None:
    with pytest.raises(ValueError, match="previous_stop must be numeric"):
        calculate_trailing_stop(
            direction="long",
            previous_stop=None,
            structure_price="100",
            buffer="3",
        )


def test_stage_is_interpretation_only_and_does_not_change_arithmetic() -> None:
    first = calculate_trailing_stop(
        direction="long",
        previous_stop="90",
        structure_price="100",
        buffer="3",
        advance_count=0,
    )
    later = calculate_trailing_stop(
        direction="long",
        previous_stop="90",
        structure_price="100",
        buffer="3",
        advance_count=7,
    )

    assert first.stage == CONFIRMATION_STOP
    assert later.stage == PROFIT_PROTECTION_TRAIL
    assert first.candidate_stop == later.candidate_stop == Decimal("97")
    assert first.stop_price == later.stop_price == Decimal("97")


def test_realistic_long_progression_matches_the_rulebook_scenario() -> None:
    lifecycle = open_position()
    first = trail_stop_for_position(
        lifecycle,
        structure=structure("hl-1", "96"),
        buffer=buffer(atr="10"),
        as_of=at(3),
    )
    lifecycle = apply_trailing_stop(lifecycle, first, event_time=at(3))
    quiet = trail_stop_for_position(lifecycle, as_of=at(4))
    second = trail_stop_for_position(
        lifecycle,
        structure=structure("hl-2", "99", detected_at=at(5)),
        buffer=buffer(atr="10", noise="4"),
        as_of=at(5),
    )
    lifecycle = apply_trailing_stop(lifecycle, second, event_time=at(5))
    retreat = trail_stop_for_position(
        lifecycle,
        structure=structure("hl-3", "100", detected_at=at(6)),
        buffer=buffer(atr="10", noise="7"),
        as_of=at(6),
    )

    assert (first.stop_price, first.advance_count, first.stage) == (
        Decimal("93.00"),
        1,
        CONFIRMATION_STOP,
    )
    assert (quiet.stop_price, quiet.advance_count, quiet.complete) == (
        Decimal("93.00"),
        1,
        True,
    )
    assert (second.stop_price, second.advance_count, second.stage) == (
        Decimal("95"),
        2,
        PROFIT_PROTECTION_TRAIL,
    )
    assert (retreat.candidate_stop, retreat.stop_price, retreat.advance_count) == (
        Decimal("93"),
        Decimal("95"),
        2,
    )
    assert retreat.reason_codes == ("TRAILING_STOP_HELD",)


def test_full_replay_preserves_pre_exit_trailing_state() -> None:
    lifecycle = open_position()
    first = trail_stop_for_position(
        lifecycle,
        structure=structure("hl-1", "96"),
        buffer=buffer(),
        as_of=at(3),
    )
    lifecycle = apply_trailing_stop(lifecycle, first, event_time=at(3))
    lifecycle = apply_position_event(
        lifecycle,
        event=ADD,
        event_time=at(4),
        quantity="1",
        price="105",
        stop_price="94",
    )
    lifecycle = apply_position_event(lifecycle, event=DEFEND, event_time=at(5))
    lifecycle = apply_position_event(lifecycle, event=HOLD, event_time=at(6))
    second = trail_stop_for_position(
        lifecycle,
        structure=structure("hl-2", "100", detected_at=at(7)),
        buffer=buffer(),
        as_of=at(7),
    )
    lifecycle = apply_trailing_stop(lifecycle, second, event_time=at(7))
    lifecycle = apply_position_event(
        lifecycle, event=TRIM, event_time=at(8), quantity="0.5", price="108"
    )
    before_exit = replay_position_event_records(
        position_event_records(lifecycle),
        symbol="BTC-USD",
        config_metadata=METADATA,
    )
    exited = apply_position_event(
        lifecycle, event=EXIT, event_time=at(9), price="110"
    )
    replayed_exit = replay_position_event_records(
        position_event_records(exited),
        symbol="BTC-USD",
        config_metadata=METADATA,
    )

    assert before_exit.stop_price == lifecycle.stop_price == Decimal("97.00")
    assert stop_advance_count(before_exit) == stop_advance_count(lifecycle) == 3
    assert replayed_exit.state == exited.state == "CLOSED"
    assert stop_advance_count(replayed_exit) == 3
    assert used_trailing_structure_ids(replayed_exit) == ("hl-1", "hl-2")


def test_initial_stop_stage_is_thesis_before_any_post_entry_advance() -> None:
    lifecycle = open_position()
    result = trail_stop_for_position(lifecycle, as_of=at(2))

    assert stop_advance_count(lifecycle) == 0
    assert result.stage == THESIS_STOP


def test_manual_widening_is_independently_refused_by_btc150() -> None:
    refused = apply_position_event(
        open_position(), event=STOP_MOVE, event_time=at(2), stop_price="80"
    )

    assert refused.accepted is False
    assert refused.stop_price == Decimal("90")
    assert "POSITION_STATE_STOP_WOULD_WIDEN" in refused.reason_codes


def test_transition_source_identity_must_be_complete() -> None:
    with pytest.raises(ValueError, match="supplied together"):
        apply_position_event(
            open_position(),
            event=STOP_MOVE,
            event_time=at(2),
            stop_price="95",
            source_feature_id=TRAILING_STOP_FEATURE_ID,
        )


def test_result_object_tamper_cannot_widen_a_stop() -> None:
    result = persisted_result()
    widened = replace(result, stop_price=Decimal("80"))

    with pytest.raises(ValueError, match="never move lower"):
        widened.as_record()
