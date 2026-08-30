"""BTC-142: initial structural stop."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from btc_predictor.risk import (
    BEARISH_DISTRIBUTION_SETUP,
    BULL_TREND_CONTINUATION_SETUP,
    INITIAL_STOP_FEATURE_ID,
    INITIAL_STOP_POLICY_VERSION,
    INITIAL_STOP_REASON_CODES,
    InitialStopResult,
    calculate_initial_stop,
    initial_stop_for_setup,
    select_structural_invalidation,
    volatility_buffer_for_invalidation,
)

AS_OF = datetime(2026, 6, 1, tzinfo=UTC)


def zone(
    cluster_id: str,
    lower: str,
    upper: str,
    *,
    zone_type: str = "support",
) -> dict[str, object]:
    return {
        "feature_id": "LEVEL_CLUSTER",
        "cluster_id": cluster_id,
        "zone_type": zone_type,
        "lower_bound": lower,
        "upper_bound": upper,
        "center_price": str((Decimal(lower) + Decimal(upper)) / 2),
        "confluence_score": "75",
        "member_count": 3,
        "detected_at": datetime(2026, 1, 1, tzinfo=UTC),
    }


def long_chain(atr: str = "500", entry: str = "10000"):
    invalidation = select_structural_invalidation(
        [zone("z", "9000", "9600")],
        setup=BULL_TREND_CONTINUATION_SETUP,
        entry_price=entry,
        as_of=AS_OF,
    )
    return invalidation, volatility_buffer_for_invalidation(invalidation, atr=atr)


def short_chain(atr: str = "500", entry: str = "10000"):
    invalidation = select_structural_invalidation(
        [zone("r", "10400", "10600", zone_type="resistance")],
        setup=BEARISH_DISTRIBUTION_SETUP,
        entry_price=entry,
        as_of=AS_OF,
    )
    return invalidation, volatility_buffer_for_invalidation(invalidation, atr=atr)


def test_metadata_is_stable() -> None:
    assert INITIAL_STOP_FEATURE_ID == "INITIAL_STOP"
    assert INITIAL_STOP_POLICY_VERSION == "INITIAL_STOP_V1"


# --- the two rulebook formulas ------------------------------------------


def test_long_stop_subtracts_the_buffer_from_the_invalidation() -> None:
    result = calculate_initial_stop(
        invalidation_price="9000",
        buffer="300",
        direction="long",
    )

    assert result.stop_price == Decimal("8700")
    assert result.complete is True
    assert result.reason_codes == ("INITIAL_STOP_COMPLETE",)


def test_short_stop_adds_the_buffer_to_the_invalidation() -> None:
    result = calculate_initial_stop(
        invalidation_price="10600",
        buffer="150",
        direction="short",
    )

    assert result.stop_price == Decimal("10750")
    assert result.complete is True


def test_the_two_directions_are_mirror_images() -> None:
    long_stop = calculate_initial_stop(
        invalidation_price="10000", buffer="250", direction="long"
    )
    short_stop = calculate_initial_stop(
        invalidation_price="10000", buffer="250", direction="short"
    )

    assert long_stop.stop_price == Decimal("9750")
    assert short_stop.stop_price == Decimal("10250")
    assert (
        Decimal("10000") - long_stop.stop_price
        == short_stop.stop_price - Decimal("10000")
    )


def test_a_zero_buffer_places_the_stop_at_the_invalidation() -> None:
    result = calculate_initial_stop(
        invalidation_price="9000", buffer="0", direction="long"
    )

    assert result.stop_price == Decimal("9000")
    assert result.complete is True


@pytest.mark.parametrize("buffer_value", ["1", "50", "300", "1234.56"])
def test_buffer_width_moves_the_stop_one_for_one(buffer_value: str) -> None:
    result = calculate_initial_stop(
        invalidation_price="9000", buffer=buffer_value, direction="long"
    )

    assert result.stop_price == Decimal("9000") - Decimal(buffer_value)


# --- stop geometry -------------------------------------------------------


def test_stop_distance_is_derived_when_entry_is_supplied() -> None:
    result = calculate_initial_stop(
        invalidation_price="9000",
        buffer="300",
        direction="long",
        entry_price="10000",
    )

    # BTC-145 consumes this as StopDistance%.
    assert result.stop_distance == Decimal("1300")
    assert result.stop_distance_fraction == Decimal("0.13")


def test_short_stop_distance_is_measured_the_same_way() -> None:
    result = calculate_initial_stop(
        invalidation_price="10600",
        buffer="150",
        direction="short",
        entry_price="10000",
    )

    assert result.stop_distance == Decimal("750")
    assert result.stop_distance_fraction == Decimal("0.075")


def test_entry_price_is_optional() -> None:
    result = calculate_initial_stop(
        invalidation_price="9000", buffer="300", direction="long"
    )

    assert result.complete is True
    assert result.entry_price is None
    assert result.stop_distance is None
    assert result.stop_distance_fraction is None


# --- guards --------------------------------------------------------------


def test_a_long_stop_at_or_above_entry_is_rejected() -> None:
    result = calculate_initial_stop(
        invalidation_price="10000",
        buffer="0",
        direction="long",
        entry_price="10000",
    )

    # A long stop must sit below entry or it is not a stop.
    assert result.complete is False
    assert result.stop_price is None
    assert result.reason_codes == ("INITIAL_STOP_WRONG_SIDE_OF_ENTRY",)


def test_a_short_stop_at_or_below_entry_is_rejected() -> None:
    result = calculate_initial_stop(
        invalidation_price="9000",
        buffer="100",
        direction="short",
        entry_price="10000",
    )

    assert result.complete is False
    assert result.reason_codes == ("INITIAL_STOP_WRONG_SIDE_OF_ENTRY",)


def test_a_buffer_that_drives_the_stop_to_zero_is_rejected() -> None:
    result = calculate_initial_stop(
        invalidation_price="100", buffer="100", direction="long"
    )

    assert result.complete is False
    assert result.stop_price is None
    assert result.reason_codes == ("INITIAL_STOP_NON_POSITIVE",)


def test_a_buffer_wider_than_the_invalidation_is_rejected() -> None:
    result = calculate_initial_stop(
        invalidation_price="100", buffer="250", direction="long"
    )

    assert result.complete is False
    assert result.reason_codes == ("INITIAL_STOP_NON_POSITIVE",)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"direction": "sideways"}, "direction must be one of"),
        ({"invalidation_price": "0"}, "invalidation_price must be positive"),
        ({"buffer": "-1"}, "buffer must be non-negative"),
        ({"entry_price": "0"}, "entry_price must be positive"),
    ],
)
def test_invalid_inputs_fail_fast(kwargs, match: str) -> None:
    base = {
        "invalidation_price": "9000",
        "buffer": "300",
        "direction": "long",
        "entry_price": "10000",
    }
    with pytest.raises(ValueError, match=match):
        calculate_initial_stop(**{**base, **kwargs})


@pytest.mark.parametrize(
    ("missing", "other"),
    [("invalidation_price", "buffer"), ("buffer", "invalidation_price")],
)
def test_a_missing_term_yields_no_stop(missing: str, other: str) -> None:
    values = {"invalidation_price": "9000", "buffer": "300"}
    values[missing] = None

    result = calculate_initial_stop(direction="long", **values)

    # A stop is never produced from a partial pair.
    assert result.complete is False
    assert result.stop_price is None
    assert result.reason_codes == ("INITIAL_STOP_INPUT_MISSING",)


# --- canonical path ------------------------------------------------------


def test_canonical_path_composes_btc140_and_btc141_for_a_long() -> None:
    invalidation, buffer = long_chain()

    result = initial_stop_for_setup(invalidation, buffer)

    # invalidation 9000 - buffer 300 (half of the 600-wide zone)
    assert invalidation.invalidation_price == Decimal("9000")
    assert buffer.buffer == Decimal("300")
    assert result.stop_price == Decimal("8700")
    assert result.direction == "long"
    assert result.entry_price == Decimal("10000")
    assert result.complete is True


def test_canonical_path_composes_btc140_and_btc141_for_a_short() -> None:
    invalidation, buffer = short_chain()

    result = initial_stop_for_setup(invalidation, buffer)

    assert result.direction == "short"
    assert result.stop_price == Decimal("10750.00")
    assert result.stop_price > result.entry_price


def test_canonical_path_takes_direction_from_the_selection() -> None:
    """The trade side cannot be restated inconsistently downstream."""

    long_invalidation, long_buffer = long_chain()
    short_invalidation, short_buffer = short_chain()

    assert initial_stop_for_setup(long_invalidation, long_buffer).direction == "long"
    assert (
        initial_stop_for_setup(short_invalidation, short_buffer).direction == "short"
    )


def test_canonical_path_accepts_persisted_records() -> None:
    invalidation, buffer = long_chain()

    from_objects = initial_stop_for_setup(invalidation, buffer)
    from_records = initial_stop_for_setup(
        invalidation.as_record(), buffer.as_record()
    )

    assert from_objects.as_record() == from_records.as_record()


def test_incomplete_invalidation_propagates_without_a_stop() -> None:
    empty = select_structural_invalidation(
        [], setup=BULL_TREND_CONTINUATION_SETUP, entry_price="10000", as_of=AS_OF
    )
    buffer = volatility_buffer_for_invalidation(empty, atr="500")

    result = initial_stop_for_setup(empty, buffer)

    assert empty.complete is False
    assert result.complete is False
    assert result.stop_price is None
    assert "INITIAL_STOP_INVALIDATION_INCOMPLETE" in result.reason_codes


def test_incomplete_buffer_propagates_without_a_stop() -> None:
    invalidation, _ = long_chain()
    buffer = volatility_buffer_for_invalidation(invalidation, atr=None)

    result = initial_stop_for_setup(invalidation, buffer)

    assert buffer.complete is False
    assert result.complete is False
    assert result.stop_price is None
    assert "INITIAL_STOP_BUFFER_INCOMPLETE" in result.reason_codes


def test_both_upstream_failures_are_reported_together() -> None:
    empty = select_structural_invalidation(
        [], setup=BULL_TREND_CONTINUATION_SETUP, entry_price="10000", as_of=AS_OF
    )
    buffer = volatility_buffer_for_invalidation(empty, atr=None)

    result = initial_stop_for_setup(empty, buffer)

    assert set(result.reason_codes) == {
        "INITIAL_STOP_INVALIDATION_INCOMPLETE",
        "INITIAL_STOP_BUFFER_INCOMPLETE",
    }


def test_a_wider_atr_widens_the_stop_through_the_chain() -> None:
    _, narrow_buffer = long_chain(atr="500")
    invalidation, wide_buffer = long_chain(atr="5000")

    narrow = initial_stop_for_setup(invalidation, narrow_buffer)
    wide = initial_stop_for_setup(invalidation, wide_buffer)

    # 0.3 * 5000 = 1500 now beats the 300 zone-noise term.
    assert wide_buffer.buffer == Decimal("1500.0")
    assert narrow.stop_price == Decimal("8700")
    assert wide.stop_price == Decimal("7500.0")


# --- determinism and persistence ----------------------------------------


def test_recomputation_is_deterministic() -> None:
    invalidation, buffer = long_chain()

    first = initial_stop_for_setup(invalidation, buffer)
    second = initial_stop_for_setup(invalidation, buffer)

    assert first.as_record() == second.as_record()


def test_record_is_persistable_and_reconstructable() -> None:
    invalidation, buffer = long_chain()

    result = initial_stop_for_setup(
        invalidation,
        buffer,
        config_metadata={"config_version": "strategy_config_v2"},
    )
    record = result.as_record()

    assert isinstance(result, InitialStopResult)
    assert record["feature_id"] == "INITIAL_STOP"
    assert record["policy_version"] == "INITIAL_STOP_V1"
    assert record["direction"] == "long"
    # Both inputs stay on the record, so the stop can be re-derived from it.
    assert record["invalidation_price"] == "9000"
    assert record["buffer"] == "300"
    assert record["stop_price"] == "8700"
    assert record["entry_price"] == "10000"
    assert record["stop_distance"] == "1300"
    assert record["stop_distance_fraction"] == "0.13"
    assert record["config_metadata"] == {"config_version": "strategy_config_v2"}
    assert record["complete"] is True
    assert (
        Decimal(record["invalidation_price"]) - Decimal(record["buffer"])
        == Decimal(record["stop_price"])
    )


def test_reason_codes_are_drawn_from_the_declared_set() -> None:
    invalidation, buffer = long_chain()
    results = [
        initial_stop_for_setup(invalidation, buffer),
        calculate_initial_stop(
            invalidation_price=None, buffer="300", direction="long"
        ),
        calculate_initial_stop(
            invalidation_price="100", buffer="250", direction="long"
        ),
        calculate_initial_stop(
            invalidation_price="10000",
            buffer="0",
            direction="long",
            entry_price="10000",
        ),
    ]

    for result in results:
        for code in result.reason_codes:
            assert code in INITIAL_STOP_REASON_CODES
