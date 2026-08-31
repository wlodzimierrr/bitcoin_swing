"""BTC-163: deterministic simulated adds."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.data import OhlcvBar
from btc_predictor.db.portfolio import paper_orders
from btc_predictor.portfolio import (
    ADD_ACTION,
    ADD_CANCELLED,
    ADD_EXECUTION_FEATURE_ID,
    ADD_EXECUTION_POLICY_VERSION,
    ADD_EXECUTION_REASON_CODES,
    ADD_EXECUTION_STATUSES,
    ADD_FILLED,
    AddExecutionIntent,
    ExecutionCosts,
    execution_costs_from_config,
    simulate_add_execution,
)
from btc_predictor.risk import calculate_tranche_size
from btc_predictor.signals import AddRequirementsInput, evaluate_add_requirements


UTC = timezone.utc
DECISION_AT = datetime(2024, 10, 1, 12, tzinfo=UTC)
CONFIG = load_strategy_config()
CONFIG_METADATA = CONFIG.run_metadata()
AVERAGE_ENTRY = Decimal("100000")


def requirements(**overrides):
    base = AddRequirementsInput(
        position_profitable=True,
        new_structural_confirmation=True,
        signed_risk_improvement=Decimal("1500"),
        regime_supportive=True,
        flow_supportive=True,
        positioning_healthy=True,
        add_score=Decimal("90"),
        projected_risk_at_stop_within_maximum=True,
    )
    strategy_config = overrides.pop("strategy_config", CONFIG)
    if overrides:
        base = replace(base, **overrides)
    return evaluate_add_requirements(base, strategy_config=strategy_config)


def tranche(number: int = 2):
    return calculate_tranche_size(
        tranche_number=number,
        final_position_notional="1000000",
        entry_price="100000",
    )


def intent(**kwargs) -> AddExecutionIntent:
    base = {
        "execution_id": "add-001",
        "position_id": 3,
        "recommendation_id": 9,
        "symbol": "BTC-USD",
        "direction": "long",
        "timeframe": "1h",
        "decision_at": DECISION_AT,
        "average_entry_price": AVERAGE_ENTRY,
        "config_metadata": CONFIG_METADATA,
    }
    return AddExecutionIntent(**{**base, **kwargs})


def bar(**kwargs) -> OhlcvBar:
    base = {
        "timestamp": DECISION_AT,
        "exchange": "coinbase",
        "symbol": "BTC-USD",
        "timeframe": "1h",
        "open": Decimal("110000"),
        "high": Decimal("112000"),
        "low": Decimal("109000"),
        "close": Decimal("111000"),
        "volume": Decimal("5"),
        "provider": "coinbase",
        "ingested_at": DECISION_AT + timedelta(hours=1, seconds=5),
    }
    return OhlcvBar(**{**base, **kwargs})


def costs() -> ExecutionCosts:
    return execution_costs_from_config()


def execute(**kwargs):
    return simulate_add_execution(
        kwargs.pop("add_intent", intent()),
        kwargs.pop("execution_bar", bar()),
        requirements=kwargs.pop("add_requirements", requirements()),
        tranche=kwargs.pop("tranche_size", tranche()),
        costs=kwargs.pop("execution_costs", costs()),
    )


def test_metadata_and_reason_code_catalog_are_stable() -> None:
    assert ADD_EXECUTION_FEATURE_ID == "SIMULATED_ADD_EXECUTION"
    assert ADD_EXECUTION_POLICY_VERSION == "SIMULATED_ADD_EXECUTION_V1"
    assert ADD_EXECUTION_STATUSES == ("filled", "cancelled")
    assert set(ADD_EXECUTION_REASON_CODES) == {
        "ADD_EXECUTION_BLOCKED_BY_REQUIREMENTS",
        "ADD_EXECUTION_NO_TRANCHE_ALLOCATION",
        "ADD_EXECUTION_NO_LONGER_PROFITABLE",
        "ADD_EXECUTION_REFERENCE_BAR_OPEN",
        "ADD_EXECUTION_COSTS_APPLIED",
        "ADD_EXECUTION_FILLED",
        "ADD_EXECUTION_CANCELLED",
    }


# --- the fill -------------------------------------------------------------


def test_a_permitted_add_fills_at_the_next_bar_open() -> None:
    result = execute()

    # An add is triggered by conditions, not by price reaching a zone, so the
    # first price actually available is the next bar's open.
    assert result.status == ADD_FILLED
    assert result.action == ADD_ACTION
    assert result.reference_price == Decimal("110000")
    assert "ADD_EXECUTION_REFERENCE_BAR_OPEN" in result.reason_codes


def test_the_fill_is_adverse_to_the_reference() -> None:
    result = execute()

    # Adding to a long buys, so slippage fills higher than the open.
    assert result.intent.side == "buy"
    assert result.average_fill_price == Decimal("110055.00000")
    assert result.average_fill_price > result.reference_price


def test_fee_and_slippage_are_reported_separately() -> None:
    result = execute()

    reference_notional = result.requested_quantity * result.reference_price
    assert result.notional == result.filled_quantity * result.average_fill_price
    assert result.slippage_cost == abs(result.notional - reference_notional)
    assert result.fee == result.notional * Decimal("0.001")


def test_zero_cost_assumptions_fill_exactly_at_the_open() -> None:
    free = ExecutionCosts(
        policy_version="EXECUTION_COST_V1",
        fee_bps=Decimal("0"),
        slippage_bps=Decimal("0"),
        funding_cost_bps_per_day=Decimal("0"),
    )

    result = execute(execution_costs=free)

    assert result.average_fill_price == Decimal("110000")
    assert result.fee == Decimal("0.00000")
    assert result.slippage_cost == Decimal("0")


def test_notional_matches_the_btc047_kernel() -> None:
    from btc_predictor.quant.portfolio import position_notional

    result = execute()
    expected = position_notional(
        float(result.filled_quantity),
        float(result.average_fill_price),
    )

    assert float(result.notional) == pytest.approx(expected)


# --- the BTC-154 gate -----------------------------------------------------


def test_a_refused_add_never_fills() -> None:
    result = execute(
        add_requirements=requirements(
            add_score=Decimal("50"),
            signed_risk_improvement=Decimal("0"),
        ),
    )

    assert result.status == ADD_CANCELLED
    assert result.filled_quantity == Decimal("0")
    assert result.average_fill_price is None
    assert result.notional == Decimal("0")


def test_a_refusal_keeps_the_gates_own_explanation() -> None:
    result = execute(
        add_requirements=requirements(
            add_score=Decimal("50"),
            signed_risk_improvement=Decimal("0"),
        ),
    )

    # Every reason the add was refused survives, rather than being flattened
    # into a single opaque "cancelled".
    assert result.reason_codes == (
        "ADD_EXECUTION_BLOCKED_BY_REQUIREMENTS",
        "ADD_REQUIREMENTS_STOP_CANNOT_IMPROVE",
        "ADD_REQUIREMENTS_ADD_SCORE_BELOW_MINIMUM",
        "ADD_EXECUTION_CANCELLED",
    )


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        ({"position_profitable": False}, "ADD_REQUIREMENTS_POSITION_NOT_PROFITABLE"),
        ({"new_structural_confirmation": False}, "ADD_REQUIREMENTS_NO_NEW_STRUCTURE"),
        ({"regime_supportive": False}, "ADD_REQUIREMENTS_REGIME_UNSUPPORTIVE"),
        (
            {"projected_risk_at_stop_within_maximum": False},
            "ADD_REQUIREMENTS_RISK_AT_STOP_EXCEEDED",
        ),
        ({"add_score": None}, "ADD_REQUIREMENTS_INPUT_MISSING"),
    ],
)
def test_every_unmet_requirement_cancels_the_add(override: dict, expected: str) -> None:
    result = execute(add_requirements=requirements(**override))

    assert result.status == ADD_CANCELLED
    assert expected in result.reason_codes


# --- the BTC-155 allocation ----------------------------------------------


def test_the_quantity_comes_from_the_tranche_schedule() -> None:
    second = execute(tranche_size=tranche(2))
    third = execute(tranche_size=tranche(3))

    # 35% then 25% of a 1,000,000 position at 100,000 per unit.
    assert second.tranche_number == 2
    assert second.requested_quantity == Decimal("3.50")
    assert third.tranche_number == 3
    assert third.requested_quantity == Decimal("2.50")
    assert third.requested_quantity < second.requested_quantity


def test_an_exhausted_schedule_cancels_the_add_even_when_permitted() -> None:
    result = execute(tranche_size=tranche(4))

    # BTC-154 says whether an add is permitted, BTC-155 whether one is
    # allocated. Both must say yes.
    assert result.status == ADD_CANCELLED
    assert result.tranche_number is None
    assert result.requested_quantity is None
    assert result.reason_codes == (
        "ADD_EXECUTION_NO_TRANCHE_ALLOCATION",
        "TRANCHE_SIZING_SCHEDULE_EXHAUSTED",
        "ADD_EXECUTION_CANCELLED",
    )


def test_an_unsized_schedule_entry_cancels_the_add() -> None:
    unsized = calculate_tranche_size(tranche_number=2)

    result = execute(tranche_size=unsized)

    # The stage exists but carries no notional, so there is nothing to buy.
    assert unsized.complete is True
    assert result.status == ADD_CANCELLED
    assert "ADD_EXECUTION_NO_TRANCHE_ALLOCATION" in result.reason_codes


def test_the_gate_is_checked_before_the_allocation() -> None:
    result = execute(
        add_requirements=requirements(add_score=Decimal("50")),
        tranche_size=tranche(4),
    )

    # Both refuse; the requirement failure is the one reported, because an add
    # that was never permitted was never a sizing question.
    assert result.reason_codes[0] == "ADD_EXECUTION_BLOCKED_BY_REQUIREMENTS"


# --- the re-check at the fill price --------------------------------------


def test_an_add_that_goes_underwater_before_the_fill_is_cancelled() -> None:
    result = execute(
        execution_bar=bar(
            open=Decimal("99000"),
            high=Decimal("99500"),
            low=Decimal("97000"),
            close=Decimal("98000"),
        ),
    )

    # BTC-154 judged profitability at the decision; price gapped below the
    # average entry before the fill. Rulebook 32 rule 2 is absolute.
    assert result.status == ADD_CANCELLED
    assert result.reason_codes == (
        "ADD_EXECUTION_NO_LONGER_PROFITABLE",
        "ADD_EXECUTION_CANCELLED",
    )


def test_slippage_cannot_rescue_an_add_the_market_already_sank() -> None:
    marginal = bar(
        open=Decimal("99990"),
        high=Decimal("100500"),
        low=Decimal("99500"),
        close=Decimal("100100"),
    )

    result = execute(execution_bar=marginal)

    # Buying slips the fill up to 100039.995, above the 100000 average entry.
    # Checking that number instead of the market would let adverse slippage
    # make a losing add look profitable, so the check is on the bar's open.
    assert costs().fill_price(Decimal("99990"), side="buy") > AVERAGE_ENTRY
    assert result.status == ADD_CANCELLED
    assert "ADD_EXECUTION_NO_LONGER_PROFITABLE" in result.reason_codes


@pytest.mark.parametrize(
    ("open_price", "status"),
    [("100001", ADD_FILLED), ("100000", ADD_CANCELLED), ("99999", ADD_CANCELLED)],
)
def test_breakeven_at_the_fill_is_not_profitable(
    open_price: str,
    status: str,
) -> None:
    result = execute(
        execution_bar=bar(
            open=Decimal(open_price),
            high=Decimal("101000"),
            low=Decimal("99000"),
            close=Decimal("100500"),
        ),
    )

    # BTC-154 requires strict profitability, so the same standard applies here.
    assert result.status == status


def test_a_short_add_is_cancelled_when_price_rose_past_the_entry() -> None:
    result = execute(
        add_intent=intent(direction="short"),
        execution_bar=bar(
            open=Decimal("101000"),
            high=Decimal("102000"),
            low=Decimal("100500"),
            close=Decimal("101500"),
        ),
    )

    assert result.status == ADD_CANCELLED
    assert "ADD_EXECUTION_NO_LONGER_PROFITABLE" in result.reason_codes


def test_a_short_add_fills_when_price_is_below_the_entry() -> None:
    result = execute(
        add_intent=intent(direction="short"),
        execution_bar=bar(
            open=Decimal("95000"),
            high=Decimal("96000"),
            low=Decimal("94000"),
            close=Decimal("95500"),
        ),
    )

    assert result.status == ADD_FILLED
    assert result.intent.side == "sell"
    # Adding to a short sells, so slippage fills lower.
    assert result.average_fill_price == Decimal("94952.50000")


def test_the_never_average_down_invariant_survives_a_disabled_gate() -> None:
    relaxed = replace(
        CONFIG,
        add_thresholds=replace(
            CONFIG.add_thresholds,
            existing_position_must_be_profitable=False,
        ),
    )
    permitted = requirements(position_profitable=False, strategy_config=relaxed)
    assert permitted.permitted is True

    losing = execute(
        add_requirements=permitted,
        execution_bar=bar(
            open=Decimal("95000"),
            high=Decimal("96000"),
            low=Decimal("94000"),
            close=Decimal("95500"),
        ),
    )
    breakeven = execute(
        add_requirements=permitted,
        execution_bar=bar(
            open=Decimal("100000"),
            high=Decimal("101000"),
            low=Decimal("99000"),
            close=Decimal("100500"),
        ),
    )

    # BTC-151's rule cannot be switched off, so a losing fill is still refused;
    # breakeven is not losing, so with the stricter gate disabled it fills.
    assert losing.status == ADD_CANCELLED
    assert "ADD_EXECUTION_NO_LONGER_PROFITABLE" in losing.reason_codes
    assert breakeven.status == ADD_FILLED


# --- validation -----------------------------------------------------------


@pytest.mark.parametrize(
    ("bad_intent", "match"),
    [
        (intent(direction="flat"), "direction must be one of"),
        (intent(average_entry_price=Decimal("0")), "average_entry_price must be"),
        (intent(config_metadata={}), "config_metadata must exactly contain"),
        (intent(execution_id=""), "execution_id must be a non-empty string"),
        (intent(position_id=0), "position_id must be a positive integer"),
    ],
)
def test_invalid_intents_fail_fast(bad_intent: AddExecutionIntent, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        execute(add_intent=bad_intent)


@pytest.mark.parametrize(
    ("execution_bar", "match"),
    [
        (bar(symbol="ETH-USD"), "symbol must match"),
        (bar(timeframe="1d"), "timeframe must match intent timeframe"),
        (bar(high=Decimal("109500")), "impossible OHLC"),
        (
            bar(timestamp=DECISION_AT + timedelta(hours=1)),
            "must be the intent's first eligible full bar",
        ),
    ],
)
def test_invalid_execution_bars_fail_fast(execution_bar: OhlcvBar, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        execute(execution_bar=execution_bar)


def test_unknown_cost_policy_is_rejected() -> None:
    incompatible = replace(costs(), policy_version="EXECUTION_COST_V2")

    with pytest.raises(ValueError, match="costs.policy_version"):
        execute(execution_costs=incompatible)


def test_upstream_results_must_be_the_real_things() -> None:
    with pytest.raises(TypeError, match="requirements must expose"):
        execute(add_requirements=object())
    with pytest.raises(TypeError, match="tranche must expose"):
        execute(tranche_size=object())


# --- persistence ----------------------------------------------------------


def test_record_carries_both_upstream_decisions() -> None:
    record = execute().as_record()

    # A refusal can be explained later without re-running the engines that
    # produced it.
    assert record["requirements"]["reason_codes"] == ["ADD_REQUIREMENTS_SATISFIED"]
    assert record["tranche"]["allocation"]["fraction_of_final"] == "0.35"
    assert record["action"] == "ADD"
    assert record["order_type"] == "market"
    assert record["tranche_number"] == 2
    assert record["average_fill_price"] == "110055.00000"


def test_mutated_result_fields_are_rejected_by_the_record() -> None:
    result = execute()

    with pytest.raises(ValueError, match="do not match replayed evidence"):
        replace(result, filled_quantity=Decimal("99")).as_record()
    with pytest.raises(ValueError, match="do not match replayed evidence"):
        replace(result, status=ADD_CANCELLED).as_record()


def test_order_record_matches_the_schema_for_a_fill() -> None:
    order = execute().as_order_record(account_id=7)
    columns = {column.name for column in paper_orders.columns}

    assert set(order) <= columns
    assert order["action"] == "ADD"
    assert order["side"] == "buy"
    assert order["order_type"] == "market"
    assert order["status"] == "filled"
    assert order["filled_quantity"] == Decimal("3.50")
    assert order["filled_at"] == DECISION_AT + timedelta(hours=1, seconds=5)
    assert order["position_id"] == 3
    assert order["recommendation_id"] == 9


def test_order_record_marks_a_refusal_cancelled_not_missed() -> None:
    order = execute(
        add_requirements=requirements(add_score=Decimal("50")),
    ).as_order_record(account_id=7)

    # Nothing about the market prevented the add; the system declined it.
    assert order["status"] == "cancelled"
    assert order["submitted_at"] is None
    assert order["filled_at"] is None
    assert order["filled_quantity"] == Decimal("0")
    assert order["average_fill_price"] is None
    # The size that would have been bought is still recorded.
    assert order["requested_quantity"] == Decimal("3.50")


def test_reason_codes_are_drawn_from_the_declared_sets() -> None:
    from btc_predictor.risk import TRANCHE_SIZING_REASON_CODES
    from btc_predictor.signals import ADD_REQUIREMENTS_REASON_CODES

    permitted = set(ADD_EXECUTION_REASON_CODES)
    permitted |= set(ADD_REQUIREMENTS_REASON_CODES)
    permitted |= set(TRANCHE_SIZING_REASON_CODES)
    results = [
        execute(),
        execute(add_requirements=requirements(add_score=Decimal("50"))),
        execute(tranche_size=tranche(4)),
        execute(
            execution_bar=bar(
                open=Decimal("99000"),
                high=Decimal("99500"),
                low=Decimal("97000"),
                close=Decimal("98000"),
            ),
        ),
    ]

    for result in results:
        for code in result.reason_codes:
            assert code in permitted


def test_same_evidence_produces_the_same_result() -> None:
    first = execute()
    second = execute()

    assert first.as_record() == second.as_record()
