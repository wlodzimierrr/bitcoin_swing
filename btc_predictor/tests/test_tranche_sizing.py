"""BTC-155: anti-martingale tranche sizing."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.config.strategy import StrategyConfigError
from btc_predictor.portfolio import (
    ADD,
    ENTER,
    PENDING_ENTRY,
    apply_position_event,
    start_position_lifecycle,
)
from btc_predictor.risk import (
    TRANCHE_SCHEDULE_PARAMETER_STATUS,
    TRANCHE_SIZING_FEATURE_ID,
    TRANCHE_SIZING_POLICY_VERSION,
    TRANCHE_SIZING_REASON_CODES,
    TrancheSizingResult,
    calculate_initial_position_size,
    calculate_tranche_size,
    next_tranche_for_position,
    tranche_schedule_from_config,
    validate_tranche_schedule,
)


SYMBOL = "BTC-USD"
START = datetime(2024, 6, 1, tzinfo=timezone.utc)
FINAL_NOTIONAL = "1000000"
ENTRY = "100000"


def at(hours: int) -> datetime:
    return START + timedelta(hours=hours)


def sized(tranche_number: int, **kwargs) -> TrancheSizingResult:
    return calculate_tranche_size(
        tranche_number=tranche_number,
        final_position_notional=FINAL_NOTIONAL,
        entry_price=ENTRY,
        **kwargs,
    )


def test_metadata_is_stable() -> None:
    assert TRANCHE_SIZING_FEATURE_ID == "TRANCHE_SIZING"
    assert TRANCHE_SIZING_POLICY_VERSION == "TRANCHE_SIZING_V1"
    # Rulebook 18: "These percentages are research parameters."
    assert TRANCHE_SCHEDULE_PARAMETER_STATUS == "PROVISIONAL_RESEARCH_CALIBRATABLE"


# --- the rulebook schedule ------------------------------------------------


def test_schedule_matches_the_rulebook_table() -> None:
    assert tranche_schedule_from_config() == (
        Decimal("0.4"),
        Decimal("0.35"),
        Decimal("0.25"),
    )


def test_schedule_is_read_from_config_not_hardcoded() -> None:
    config = load_strategy_config()

    assert tranche_schedule_from_config(config) == tuple(
        Decimal(str(value)) for value in config.risk.tranche_schedule
    )


@pytest.mark.parametrize(
    ("number", "fraction", "cumulative", "remaining", "notional", "quantity"),
    [
        (1, "0.4", "0.4", "0.60", "400000.0", "4.0"),
        (2, "0.35", "0.75", "0.25", "350000.00", "3.50"),
        (3, "0.25", "1.00", "0", "250000.00", "2.50"),
    ],
)
def test_each_stage_allocates_its_share_of_the_final_position(
    number: int,
    fraction: str,
    cumulative: str,
    remaining: str,
    notional: str,
    quantity: str,
) -> None:
    result = sized(number)

    assert result.complete is True
    assert result.reason_codes == ("TRANCHE_SIZING_ASSIGNED",)
    assert result.allocation.fraction_of_final == Decimal(fraction)
    assert result.allocation.cumulative_fraction == Decimal(cumulative)
    assert result.remaining_fraction == Decimal(remaining)
    assert result.allocation.notional == Decimal(notional)
    assert result.allocation.quantity == Decimal(quantity)


def test_the_stages_reconstruct_exactly_one_whole_position() -> None:
    allocations = [sized(number).allocation for number in (1, 2, 3)]

    # BTC-145 sizes the position once; the schedule only decides delivery.
    assert sum(item.fraction_of_final for item in allocations) == Decimal("1.00")
    assert sum(item.notional for item in allocations) == Decimal(FINAL_NOTIONAL)
    assert allocations[-1].cumulative_fraction == Decimal("1.00")


def test_the_schedule_is_anti_martingale() -> None:
    fractions = tranche_schedule_from_config()

    # Rulebook 18: add to winners, never to losers. Adding in growing size is
    # the martingale shape the strategy exists to avoid.
    assert list(fractions) == sorted(fractions, reverse=True)
    assert fractions[0] > fractions[1] > fractions[2]


def test_the_initial_tranche_is_the_largest_single_commitment() -> None:
    initial = sized(1).allocation

    # Rulebook 26 enters small relative to the final position, but no later
    # single add may exceed that first commitment.
    assert initial.fraction_of_final == max(tranche_schedule_from_config())
    assert initial.fraction_of_final < Decimal("1")


# --- schedule exhaustion --------------------------------------------------


@pytest.mark.parametrize("number", [4, 5, 99])
def test_a_tranche_beyond_the_schedule_has_no_allocation(number: int) -> None:
    result = sized(number)

    # BTC-154 decides whether an add is permitted; the schedule decides whether
    # one is allocated. Extrapolating would size risk nothing authorized.
    assert result.complete is False
    assert result.allocation is None
    assert result.remaining_fraction is None
    assert result.reason_codes == ("TRANCHE_SIZING_SCHEDULE_EXHAUSTED",)
    assert result.maximum_tranche_count == 3


def test_the_schedule_length_is_the_add_cap() -> None:
    result = sized(1)

    # Rulebook 18 allows an initial entry and two adds, nothing more.
    assert result.maximum_tranche_count == 3
    assert sized(3).complete is True
    assert sized(4).complete is False


# --- composition with BTC-145 and BTC-150 --------------------------------


def open_position(*, adds: int = 0):
    lifecycle = start_position_lifecycle(symbol=SYMBOL, state=PENDING_ENTRY)
    lifecycle = apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=at(1),
        quantity="4",
        price=ENTRY,
        stop_price="90000",
    )
    for index in range(adds):
        lifecycle = apply_position_event(
            lifecycle,
            event=ADD,
            event_time=at(2 + index),
            quantity="3.5",
            price=ENTRY,
        )
    return lifecycle


def position_size():
    return calculate_initial_position_size(
        nav="1000000",
        risk_fraction_nav="0.005",
        stop_distance_fraction="0.05",
        entry_price=ENTRY,
    )


@pytest.mark.parametrize(
    ("adds", "expected_number", "expected_fraction"),
    [(0, 2, "0.35"), (1, 3, "0.25")],
)
def test_the_next_stage_comes_from_the_ledger_not_a_caller_counter(
    adds: int,
    expected_number: int,
    expected_fraction: str,
) -> None:
    result = next_tranche_for_position(open_position(adds=adds), position_size())

    # tranche_count is what has been filled, so the next stage is count + 1.
    assert result.tranche_number == expected_number
    assert result.allocation.fraction_of_final == Decimal(expected_fraction)


def test_a_fully_pyramided_position_gets_no_further_allocation() -> None:
    result = next_tranche_for_position(open_position(adds=2), position_size())

    assert result.tranche_number == 4
    assert result.complete is False
    assert result.reason_codes == ("TRANCHE_SIZING_SCHEDULE_EXHAUSTED",)


def test_the_first_tranche_is_sized_before_any_fill_exists() -> None:
    lifecycle = start_position_lifecycle(symbol=SYMBOL)

    result = next_tranche_for_position(lifecycle, position_size())

    assert result.tranche_number == 1
    assert result.allocation.fraction_of_final == Decimal("0.4")
    assert result.allocation.notional == Decimal("40000.0")


def test_the_whole_position_size_comes_from_btc145() -> None:
    size = position_size()

    result = next_tranche_for_position(start_position_lifecycle(symbol=SYMBOL), size)

    assert result.final_position_notional == size.position_notional
    assert result.entry_price == Decimal(ENTRY)
    assert (
        result.allocation.notional
        == size.position_notional * Decimal("0.4")
    )


def test_an_incomplete_position_size_yields_no_allocation() -> None:
    unsized = calculate_initial_position_size(
        nav="1000000",
        risk_fraction_nav="0.005",
        stop_distance_fraction=None,
    )

    result = next_tranche_for_position(start_position_lifecycle(symbol=SYMBOL), unsized)

    assert unsized.complete is False
    assert result.complete is False
    assert result.allocation is None
    assert result.reason_codes == ("TRANCHE_SIZING_NO_POSITION_SIZE",)


def test_tranche_notional_matches_the_btc047_kernel() -> None:
    from btc_predictor.quant.portfolio import position_notional

    allocation = sized(2).allocation
    expected = position_notional(
        float(allocation.quantity),
        float(ENTRY),
    )

    assert float(allocation.notional) == pytest.approx(expected)


# --- schedule validation --------------------------------------------------


def test_an_explicit_schedule_overrides_config() -> None:
    result = calculate_tranche_size(
        tranche_number=1,
        final_position_notional=FINAL_NOTIONAL,
        schedule=["0.5", "0.5"],
    )

    assert result.allocation.fraction_of_final == Decimal("0.5")
    assert result.maximum_tranche_count == 2


@pytest.mark.parametrize(
    ("schedule", "match"),
    [
        (["0.4", "0.5", "0.1"], "never increase"),
        (["0.25", "0.35", "0.4"], "never increase"),
        (["0.4", "0.35"], "sum to 1"),
        (["0.5", "0.4", "0.3"], "sum to 1"),
        ([], "must not be empty"),
        (["0.5", "0"], "must be positive"),
        (["0.5", "-0.1"], "must be positive"),
        (["1.5", "0.5"], "between 0 and 1"),
    ],
)
def test_invalid_schedules_are_rejected(schedule, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        validate_tranche_schedule(schedule)


def test_an_equal_split_is_permitted() -> None:
    # Non-increasing, not strictly decreasing: equal tranches are not
    # martingale, so the rule must not reject them.
    assert validate_tranche_schedule(["0.5", "0.5"]) == (
        Decimal("0.5"),
        Decimal("0.5"),
    )


def test_a_single_tranche_schedule_is_permitted() -> None:
    assert validate_tranche_schedule(["1"]) == (Decimal("1"),)


def risk_config_mapping(tranche_schedule: list[float]) -> dict:
    return {
        "schedule": [{"min_entry_conviction": 80, "risk_fraction_nav": 0.0035}],
        "max_risk_at_stop_fraction_nav": 0.01,
        "tranche_schedule": tranche_schedule,
    }


@pytest.mark.parametrize(
    ("tranche_schedule", "match"),
    [
        ([0.25, 0.35, 0.4], "martingale"),
        ([0.4, 0.35], "sum to 1"),
        ([0.4, 0.35, 0.3], "sum to 1"),
        ([1.5, 0.5], "between 0 and 1"),
    ],
)
def test_config_rejects_an_invalid_tranche_schedule(
    tranche_schedule: list[float],
    match: str,
) -> None:
    config = load_strategy_config()

    # Startup is where a bad schedule must be caught; every downstream size
    # would otherwise be wrong in a way no single call could detect.
    with pytest.raises(StrategyConfigError, match=match):
        type(config.risk).from_mapping(risk_config_mapping(tranche_schedule))


def test_config_accepts_the_shipped_schedule() -> None:
    config = load_strategy_config()

    parsed = type(config.risk).from_mapping(risk_config_mapping([0.4, 0.35, 0.25]))

    assert parsed.tranche_schedule == (0.4, 0.35, 0.25)


# --- malformed input ------------------------------------------------------


@pytest.mark.parametrize("number", [0, -1, "2", 1.5, True])
def test_invalid_tranche_numbers_fail_fast(number) -> None:
    with pytest.raises(ValueError, match="tranche_number"):
        calculate_tranche_size(tranche_number=number)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"final_position_notional": "0"}, "final_position_notional must be positive"),
        ({"final_position_notional": "-1"}, "final_position_notional must be positive"),
        ({"final_position_notional": "abc"}, "final_position_notional must be numeric"),
        ({"final_position_notional": "1000", "entry_price": "0"}, "entry_price"),
    ],
)
def test_invalid_amounts_fail_fast(kwargs, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        calculate_tranche_size(tranche_number=1, **kwargs)


def test_a_lifecycle_without_a_tranche_count_is_rejected() -> None:
    with pytest.raises(ValueError, match="tranche_count"):
        next_tranche_for_position(object(), position_size())


def test_a_position_size_of_the_wrong_type_is_rejected() -> None:
    with pytest.raises(TypeError, match="position_size"):
        next_tranche_for_position(start_position_lifecycle(symbol=SYMBOL), object())


# --- determinism and persistence -----------------------------------------


def test_the_schedule_can_be_inspected_without_a_sized_position() -> None:
    result = calculate_tranche_size(tranche_number=2)

    assert result.complete is True
    assert result.allocation.fraction_of_final == Decimal("0.35")
    assert result.allocation.notional is None
    assert result.allocation.quantity is None


def test_recomputation_is_deterministic() -> None:
    assert sized(2).as_record() == sized(2).as_record()


def test_record_is_persistable_and_reconstructable() -> None:
    record = sized(
        2,
        config_metadata={"config_version": "strategy_config_v2"},
    ).as_record()

    assert record == {
        "feature_id": "TRANCHE_SIZING",
        "policy_version": "TRANCHE_SIZING_V1",
        "parameter_status": "PROVISIONAL_RESEARCH_CALIBRATABLE",
        "tranche_number": 2,
        "maximum_tranche_count": 3,
        "schedule": ["0.4", "0.35", "0.25"],
        "allocation": {
            "tranche_number": 2,
            "fraction_of_final": "0.35",
            "cumulative_fraction": "0.75",
            "notional": "350000.00",
            "quantity": "3.50",
        },
        "remaining_fraction": "0.25",
        "final_position_notional": "1000000",
        "entry_price": "100000",
        "config_metadata": {"config_version": "strategy_config_v2"},
        "complete": True,
        "reason_codes": ["TRANCHE_SIZING_ASSIGNED"],
    }
    # The whole schedule is retained, so an allocation is re-derivable.
    assert Decimal(record["allocation"]["notional"]) == Decimal(
        record["final_position_notional"]
    ) * Decimal(record["allocation"]["fraction_of_final"])


def test_a_complete_record_requires_an_allocation() -> None:
    from dataclasses import replace

    with pytest.raises(ValueError, match="requires an allocation"):
        replace(sized(1), allocation=None).as_record()


def test_reason_codes_are_drawn_from_the_declared_set() -> None:
    results = [
        sized(1),
        sized(4),
        next_tranche_for_position(
            start_position_lifecycle(symbol=SYMBOL),
            calculate_initial_position_size(
                nav="1000000",
                risk_fraction_nav="0.005",
                stop_distance_fraction=None,
            ),
        ),
    ]

    for result in results:
        for code in result.reason_codes:
            assert code in TRANCHE_SIZING_REASON_CODES
