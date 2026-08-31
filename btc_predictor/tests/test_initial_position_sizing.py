"""BTC-145: initial position sizing."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from btc_predictor.risk import (
    BULL_TREND_CONTINUATION_SETUP,
    INITIAL_POSITION_SIZE_FEATURE_ID,
    INITIAL_POSITION_SIZE_POLICY_VERSION,
    INITIAL_POSITION_SIZE_REASON_CODES,
    InitialPositionSizeResult,
    calculate_initial_position_size,
    calculate_risk_budget,
    initial_position_size_for_trade,
    initial_stop_for_setup,
    select_structural_invalidation,
    volatility_buffer_for_invalidation,
)

AS_OF = datetime(2026, 6, 1, tzinfo=UTC)
DETECTED = datetime(2026, 1, 1, tzinfo=UTC)


def test_metadata_is_stable() -> None:
    assert INITIAL_POSITION_SIZE_FEATURE_ID == "INITIAL_POSITION_SIZE"
    assert INITIAL_POSITION_SIZE_POLICY_VERSION == "INITIAL_POSITION_SIZE_V1"


# --- the formula ---------------------------------------------------------


def test_notional_is_nav_times_budget_over_stop_distance() -> None:
    result = calculate_initial_position_size(
        nav="1000000",
        risk_fraction_nav="0.005",
        stop_distance_fraction="0.05",
    )

    # 1,000,000 * 0.005 = 5,000 risked; 5,000 / 0.05 = 100,000 notional.
    assert result.risk_budget_amount == Decimal("5000.000")
    assert result.position_notional == Decimal("100000.0")
    assert result.complete is True


@pytest.mark.parametrize(
    ("distance", "expected"),
    [
        ("0.10", Decimal("50000")),
        ("0.05", Decimal("100000")),
        ("0.025", Decimal("200000")),
        ("0.01", Decimal("500000")),
    ],
)
def test_a_tighter_stop_permits_a_larger_position(
    distance: str,
    expected: Decimal,
) -> None:
    result = calculate_initial_position_size(
        nav="1000000", risk_fraction_nav="0.005", stop_distance_fraction=distance
    )

    assert result.position_notional == expected


def test_risk_at_stop_is_invariant_across_stop_distances() -> None:
    """Whatever the stop distance, the amount risked is the budget."""

    for distance in ("0.01", "0.05", "0.20"):
        result = calculate_initial_position_size(
            nav="1000000",
            risk_fraction_nav="0.005",
            stop_distance_fraction=distance,
        )
        assert (
            result.position_notional * Decimal(distance)
            == result.risk_budget_amount
        )


def test_matches_the_btc047_quant_kernel() -> None:
    from btc_predictor.quant.risk import max_allowed_notional

    for nav, fraction, distance in (
        ("1000000", "0.005", "0.05"),
        ("250000", "0.0035", "0.08"),
        ("5000000", "0.006", "0.12"),
    ):
        result = calculate_initial_position_size(
            nav=nav, risk_fraction_nav=fraction, stop_distance_fraction=distance
        )
        expected = max_allowed_notional(
            float(nav), float(fraction), float(distance)
        )
        assert abs(float(result.position_notional) - float(expected)) < 1e-6


def test_entry_price_yields_a_quantity() -> None:
    result = calculate_initial_position_size(
        nav="1000000",
        risk_fraction_nav="0.005",
        stop_distance_fraction="0.05",
        entry_price="100000",
    )

    assert result.position_quantity == Decimal("1")
    assert result.entry_price == Decimal("100000")


def test_entry_price_is_optional() -> None:
    result = calculate_initial_position_size(
        nav="1000000", risk_fraction_nav="0.005", stop_distance_fraction="0.05"
    )

    assert result.complete is True
    assert result.position_quantity is None


# --- the division guard --------------------------------------------------


def test_a_zero_stop_distance_is_rejected_not_divided_by() -> None:
    result = calculate_initial_position_size(
        nav="1000000", risk_fraction_nav="0.005", stop_distance_fraction="0"
    )

    # Undefined, not unbounded: dividing here would invent exposure.
    assert result.complete is False
    assert result.position_notional is None
    assert result.reason_codes == ("INITIAL_POSITION_SIZE_ZERO_STOP_DISTANCE",)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"nav": "0"}, "nav must be positive"),
        ({"nav": "-1"}, "nav must be positive"),
        ({"risk_fraction_nav": "-0.01"}, "must be non-negative"),
        ({"risk_fraction_nav": "1.5"}, "must be between 0 and 1"),
        ({"stop_distance_fraction": "-0.05"}, "must be non-negative"),
        ({"entry_price": "0"}, "entry_price must be positive"),
    ],
)
def test_invalid_inputs_fail_fast(kwargs, match: str) -> None:
    base = {
        "nav": "1000000",
        "risk_fraction_nav": "0.005",
        "stop_distance_fraction": "0.05",
        "entry_price": "100000",
    }
    with pytest.raises(ValueError, match=match):
        calculate_initial_position_size(**{**base, **kwargs})


@pytest.mark.parametrize(
    "missing", ["nav", "risk_fraction_nav", "stop_distance_fraction"]
)
def test_a_missing_input_yields_no_size(missing: str) -> None:
    values = {
        "nav": "1000000",
        "risk_fraction_nav": "0.005",
        "stop_distance_fraction": "0.05",
    }
    values[missing] = None

    result = calculate_initial_position_size(**values)

    assert result.complete is False
    assert result.position_notional is None
    assert result.reason_codes == ("INITIAL_POSITION_SIZE_INPUT_MISSING",)


# --- exposure visibility -------------------------------------------------


def test_leverage_is_always_reported() -> None:
    tight = calculate_initial_position_size(
        nav="1000000", risk_fraction_nav="0.006", stop_distance_fraction="0.002"
    )

    # A very tight stop implies 3x NAV exposure; that must be visible.
    assert tight.position_notional == Decimal("3000000")
    assert tight.notional_fraction_nav == Decimal("3")


def test_an_optional_exposure_cap_binds_when_supplied() -> None:
    result = calculate_initial_position_size(
        nav="1000000",
        risk_fraction_nav="0.006",
        stop_distance_fraction="0.002",
        maximum_notional_fraction_nav="1",
    )

    assert result.position_notional == Decimal("1000000")
    assert result.notional_fraction_nav == Decimal("1")
    assert "INITIAL_POSITION_SIZE_CAPPED_AT_MAXIMUM" in result.reason_codes


def test_the_cap_is_off_by_default() -> None:
    result = calculate_initial_position_size(
        nav="1000000", risk_fraction_nav="0.006", stop_distance_fraction="0.002"
    )

    # No calibrated leverage limit exists yet, so none is invented.
    assert result.maximum_notional_fraction_nav is None
    assert "INITIAL_POSITION_SIZE_CAPPED_AT_MAXIMUM" not in result.reason_codes


def test_a_cap_that_does_not_bind_leaves_the_size_untouched() -> None:
    result = calculate_initial_position_size(
        nav="1000000",
        risk_fraction_nav="0.005",
        stop_distance_fraction="0.05",
        maximum_notional_fraction_nav="1",
    )

    assert result.position_notional == Decimal("100000.0")
    assert "INITIAL_POSITION_SIZE_CAPPED_AT_MAXIMUM" not in result.reason_codes


# --- canonical path ------------------------------------------------------


def support_zone(lower: str, upper: str) -> dict[str, object]:
    return {
        "feature_id": "LEVEL_CLUSTER",
        "cluster_id": "z",
        "zone_type": "support",
        "lower_bound": lower,
        "upper_bound": upper,
        "center_price": str((Decimal(lower) + Decimal(upper)) / 2),
        "confluence_score": "75",
        "member_count": 3,
        "detected_at": DETECTED,
    }


def trade_chain(conviction: str = "87", nav: str = "1000000"):
    invalidation = select_structural_invalidation(
        [support_zone("94000", "94400")],
        setup=BULL_TREND_CONTINUATION_SETUP,
        entry_price="100000",
        as_of=AS_OF,
    )
    buffer = volatility_buffer_for_invalidation(invalidation, atr="2000")
    stop = initial_stop_for_setup(invalidation, buffer)
    budget = calculate_risk_budget(entry_conviction=conviction, nav=nav)
    return budget, stop


def test_canonical_path_sizes_from_a_budget_and_a_stop() -> None:
    budget, stop = trade_chain()

    result = initial_position_size_for_trade(budget, stop)

    # stop 94000 - 600 = 93400, so distance is 6.6% of a 100,000 entry.
    assert stop.stop_price == Decimal("93400")
    assert stop.stop_distance_fraction == Decimal("0.066")
    assert budget.risk_fraction_nav == Decimal("0.005")
    assert result.position_notional == Decimal("75757.57575757575757575757576")
    assert result.complete is True


def test_canonical_path_risks_exactly_the_budget_at_the_stop() -> None:
    budget, stop = trade_chain()

    result = initial_position_size_for_trade(budget, stop)
    risked = result.position_notional * stop.stop_distance_fraction

    # The whole point of the chain: loss at the stop equals the budget.
    assert abs(risked - budget.risk_budget_amount) < Decimal("0.0000001")


def test_higher_conviction_sizes_larger_for_the_same_stop() -> None:
    modest, stop = trade_chain(conviction="80")
    strong, _ = trade_chain(conviction="90")

    modest_size = initial_position_size_for_trade(modest, stop)
    strong_size = initial_position_size_for_trade(strong, stop)

    assert modest.risk_fraction_nav == Decimal("0.0035")
    assert strong.risk_fraction_nav == Decimal("0.006")
    assert strong_size.position_notional > modest_size.position_notional


def test_canonical_path_accepts_persisted_records() -> None:
    budget, stop = trade_chain()

    assert (
        initial_position_size_for_trade(budget, stop).as_record()
        == initial_position_size_for_trade(
            budget.as_record(), stop.as_record()
        ).as_record()
    )


def test_a_sub_threshold_conviction_produces_no_position() -> None:
    _, stop = trade_chain()
    budget = calculate_risk_budget(entry_conviction="70", nav="1000000")

    result = initial_position_size_for_trade(budget, stop)

    # No risk budget below 80, so there is no position to size.
    assert budget.complete is False
    assert result.complete is False
    assert result.position_notional is None
    assert "INITIAL_POSITION_SIZE_NO_RISK_BUDGET" in result.reason_codes


def test_an_incomplete_stop_produces_no_position() -> None:
    empty = select_structural_invalidation(
        [], setup=BULL_TREND_CONTINUATION_SETUP, entry_price="100000", as_of=AS_OF
    )
    buffer = volatility_buffer_for_invalidation(empty, atr="2000")
    stop = initial_stop_for_setup(empty, buffer)
    budget = calculate_risk_budget(entry_conviction="87", nav="1000000")

    result = initial_position_size_for_trade(budget, stop)

    assert result.complete is False
    assert "INITIAL_POSITION_SIZE_INPUT_MISSING" in result.reason_codes


# --- determinism and persistence ----------------------------------------


def test_recomputation_is_deterministic() -> None:
    budget, stop = trade_chain()

    first = initial_position_size_for_trade(budget, stop)
    second = initial_position_size_for_trade(budget, stop)

    assert first.as_record() == second.as_record()


def test_record_is_persistable_and_reconstructable() -> None:
    result = calculate_initial_position_size(
        nav="1000000",
        risk_fraction_nav="0.005",
        stop_distance_fraction="0.05",
        entry_price="100000",
        config_metadata={"config_version": "strategy_config_v2"},
    )
    record = result.as_record()

    assert isinstance(result, InitialPositionSizeResult)
    assert record["feature_id"] == "INITIAL_POSITION_SIZE"
    assert record["position_notional"] == "100000.0"
    assert record["position_quantity"] == "1.0"
    assert record["notional_fraction_nav"] == "0.1"
    assert record["config_metadata"] == {"config_version": "strategy_config_v2"}
    # Every input to the formula is stored, so the size is re-derivable.
    assert (
        Decimal(record["nav"]) * Decimal(record["risk_fraction_nav"])
        / Decimal(record["stop_distance_fraction"])
        == Decimal(record["position_notional"])
    )


def test_reason_codes_are_drawn_from_the_declared_set() -> None:
    budget, stop = trade_chain()
    results = [
        initial_position_size_for_trade(budget, stop),
        calculate_initial_position_size(
            nav="1000000", risk_fraction_nav="0.005", stop_distance_fraction="0"
        ),
        calculate_initial_position_size(
            nav=None, risk_fraction_nav="0.005", stop_distance_fraction="0.05"
        ),
        calculate_initial_position_size(
            nav="1000000",
            risk_fraction_nav="0.006",
            stop_distance_fraction="0.002",
            maximum_notional_fraction_nav="1",
        ),
    ]

    for result in results:
        for code in result.reason_codes:
            assert code in INITIAL_POSITION_SIZE_REASON_CODES
