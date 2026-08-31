"""BTC-164: deterministic simulated trims."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.data import OhlcvBar
from btc_predictor.db.portfolio import paper_orders
from btc_predictor.portfolio import (
    DEFAULT_TRIM_FRACTION,
    TRIM_ACTION,
    TRIM_CANCELLED,
    TRIM_EXECUTION_FEATURE_ID,
    TRIM_EXECUTION_POLICY_VERSION,
    TRIM_EXECUTION_REASON_CODES,
    TRIM_EXECUTION_STATUSES,
    TRIM_FILLED,
    TRIM_SIZING_PARAMETER_STATUS,
    ExecutionCosts,
    TrimExecutionIntent,
    execution_costs_from_config,
    open_paper_account,
    simulate_trim_execution,
)
from btc_predictor.signals import TrimRuleInput, evaluate_trim_rules


UTC = timezone.utc
DECISION_AT = datetime(2024, 11, 1, 12, tzinfo=UTC)
CONFIG = load_strategy_config()
CONFIG_METADATA = CONFIG.run_metadata()
AVERAGE_ENTRY = Decimal("100000")


def signal(**overrides):
    base = TrimRuleInput(
        position_open=True,
        hold_score=Decimal("45"),
        euphoria_active=False,
        crowding_active=False,
        current_flow_score=Decimal("50"),
        prior_flow_score=Decimal("60"),
    )
    if overrides:
        base = replace(base, **overrides)
    return evaluate_trim_rules(base, strategy_config=CONFIG)


def quiet_signal():
    return signal(
        hold_score=Decimal("80"),
        current_flow_score=Decimal("70"),
    )


def intent(**kwargs) -> TrimExecutionIntent:
    base = {
        "execution_id": "trim-001",
        "position_id": 3,
        "recommendation_id": None,
        "symbol": "BTC-USD",
        "direction": "long",
        "timeframe": "1h",
        "decision_at": DECISION_AT,
        "average_entry_price": AVERAGE_ENTRY,
        "open_quantity": Decimal("3"),
        "config_metadata": CONFIG_METADATA,
    }
    return TrimExecutionIntent(**{**base, **kwargs})


def bar(**kwargs) -> OhlcvBar:
    base = {
        "timestamp": DECISION_AT,
        "exchange": "coinbase",
        "symbol": "BTC-USD",
        "timeframe": "1h",
        "open": Decimal("120000"),
        "high": Decimal("121000"),
        "low": Decimal("119000"),
        "close": Decimal("120500"),
        "volume": Decimal("4"),
        "provider": "coinbase",
        "ingested_at": DECISION_AT + timedelta(hours=1, seconds=5),
    }
    return OhlcvBar(**{**base, **kwargs})


def losing_bar() -> OhlcvBar:
    return bar(
        open=Decimal("90000"),
        high=Decimal("91000"),
        low=Decimal("89000"),
        close=Decimal("90500"),
    )


def costs() -> ExecutionCosts:
    return execution_costs_from_config()


def execute(**kwargs):
    return simulate_trim_execution(
        kwargs.pop("trim_intent", intent()),
        kwargs.pop("execution_bar", bar()),
        signal=kwargs.pop("trim_signal", signal()),
        costs=kwargs.pop("execution_costs", costs()),
    )


def test_metadata_and_reason_code_catalog_are_stable() -> None:
    assert TRIM_EXECUTION_FEATURE_ID == "SIMULATED_TRIM_EXECUTION"
    assert TRIM_EXECUTION_POLICY_VERSION == "SIMULATED_TRIM_EXECUTION_V1"
    assert TRIM_EXECUTION_STATUSES == ("filled", "cancelled")
    assert set(TRIM_EXECUTION_REASON_CODES) == {
        "TRIM_EXECUTION_NOT_SIGNALLED",
        "TRIM_EXECUTION_NOT_PARTIAL",
        "TRIM_EXECUTION_REFERENCE_BAR_OPEN",
        "TRIM_EXECUTION_COSTS_APPLIED",
        "TRIM_EXECUTION_REALIZED_PROFIT",
        "TRIM_EXECUTION_REALIZED_LOSS",
        "TRIM_EXECUTION_FILLED",
        "TRIM_EXECUTION_CANCELLED",
    }


def test_the_trim_size_is_declared_provisional() -> None:
    # Rulebook 20 and 23 say "trim" without saying how much, so this is a
    # placeholder rather than a calibrated parameter.
    assert DEFAULT_TRIM_FRACTION == Decimal("0.33")
    assert TRIM_SIZING_PARAMETER_STATUS == "PROVISIONAL_RESEARCH_CALIBRATABLE"
    assert intent().as_record()["trim_sizing_parameter_status"] == (
        TRIM_SIZING_PARAMETER_STATUS
    )


# --- the fill -------------------------------------------------------------


def test_a_signalled_trim_fills_at_the_next_bar_open() -> None:
    result = execute()

    assert result.status == TRIM_FILLED
    assert result.action == TRIM_ACTION
    assert result.reference_price == Decimal("120000")
    assert "TRIM_EXECUTION_REFERENCE_BAR_OPEN" in result.reason_codes


def test_a_long_trim_sells_and_slips_lower() -> None:
    result = execute()

    # Reducing a long sells, the opposite side to an add in the same direction.
    assert result.intent.side == "sell"
    assert result.average_fill_price == Decimal("119940.00000")
    assert result.average_fill_price < result.reference_price


def test_a_short_trim_buys_and_slips_higher() -> None:
    result = execute(
        trim_intent=intent(direction="short"),
        execution_bar=losing_bar(),
    )

    assert result.intent.side == "buy"
    assert result.average_fill_price == Decimal("90045.00000")
    assert result.average_fill_price > result.reference_price


def test_the_quantity_is_the_configured_fraction_of_what_is_open() -> None:
    result = execute()

    assert result.requested_quantity == Decimal("0.99")
    assert result.filled_quantity == Decimal("0.99")
    assert result.filled_quantity == Decimal("3") * DEFAULT_TRIM_FRACTION


def test_the_fraction_is_overridable_per_call() -> None:
    half = execute(trim_intent=intent(trim_fraction=Decimal("0.5")))

    assert half.filled_quantity == Decimal("1.5")
    assert half.remaining_quantity == Decimal("1.5")
    assert half.as_record()["intent"]["trim_fraction"] == "0.5"


def test_fee_and_slippage_are_reported_separately() -> None:
    result = execute()

    reference_notional = result.requested_quantity * result.reference_price
    assert result.notional == result.filled_quantity * result.average_fill_price
    assert result.slippage_cost == abs(result.notional - reference_notional)
    assert result.fee == result.notional * Decimal("0.001")


def test_notional_matches_the_btc047_kernel() -> None:
    from btc_predictor.quant.portfolio import position_notional

    result = execute()
    expected = position_notional(
        float(result.filled_quantity),
        float(result.average_fill_price),
    )

    assert float(result.notional) == pytest.approx(expected)


# --- a trim realizes part of the position --------------------------------


def test_a_profitable_trim_locks_in_a_signed_gain() -> None:
    result = execute()

    gross = result.filled_quantity * (result.average_fill_price - AVERAGE_ENTRY)
    assert result.realized_pnl == gross - result.fee
    assert result.realized_pnl == Decimal("19621.859400000000")
    assert "TRIM_EXECUTION_REALIZED_PROFIT" in result.reason_codes


def test_a_defensive_trim_locks_in_a_loss_and_says_so() -> None:
    result = execute(execution_bar=losing_bar())

    # The 40-50 Hold band trims into weakness. Calling that "profit taken"
    # would misreport the trade.
    assert result.realized_pnl == Decimal("-10033.605450000000")
    assert result.realized_pnl < 0
    assert "TRIM_EXECUTION_REALIZED_LOSS" in result.reason_codes
    assert "TRIM_EXECUTION_REALIZED_PROFIT" not in result.reason_codes


def test_costs_alone_can_turn_a_flat_trim_into_a_loss() -> None:
    flat = bar(
        open=AVERAGE_ENTRY,
        high=Decimal("101000"),
        low=Decimal("99000"),
        close=Decimal("100500"),
    )

    result = execute(execution_bar=flat)

    # Exiting at the entry price is not breakeven once the fill slips and the
    # fee is charged.
    assert result.realized_pnl < 0
    assert "TRIM_EXECUTION_REALIZED_LOSS" in result.reason_codes


def test_realized_pnl_settles_onto_the_paper_account() -> None:
    account = open_paper_account(
        account_name="paper-trim",
        created_at=DECISION_AT,
        starting_nav="100000",
    )
    result = execute()

    settled = account.settle_realized_pnl(result.realized_pnl)

    # BTC-160 consumes this figure directly; no second convention is invented.
    assert settled.realized_pnl == result.realized_pnl
    assert settled.cash == Decimal("100000") + result.realized_pnl


def test_zero_cost_assumptions_realize_the_raw_price_difference() -> None:
    free = ExecutionCosts(
        policy_version="EXECUTION_COST_V1",
        fee_bps=Decimal("0"),
        slippage_bps=Decimal("0"),
        funding_cost_bps_per_day=Decimal("0"),
    )

    result = execute(execution_costs=free)

    assert result.average_fill_price == Decimal("120000")
    assert result.realized_pnl == Decimal("0.99") * Decimal("20000")


# --- a trim must stay partial --------------------------------------------


def test_the_position_is_reduced_not_closed() -> None:
    result = execute()

    assert result.remaining_quantity == Decimal("2.01")
    assert result.remaining_quantity > 0
    assert (
        result.filled_quantity + result.remaining_quantity
        == result.intent.open_quantity
    )


def test_a_full_reduction_is_refused_rather_than_becoming_an_exit() -> None:
    result = execute(trim_intent=intent(trim_fraction=Decimal("1")))

    # Removing everything is BTC-158's decision with its own rules, and the
    # BTC-150 ledger rejects it as a trim.
    assert result.status == TRIM_CANCELLED
    assert result.filled_quantity == Decimal("0")
    assert result.remaining_quantity == Decimal("3")
    assert result.reason_codes == (
        "TRIM_EXECUTION_NOT_PARTIAL",
        "TRIM_EXECUTION_CANCELLED",
    )


@pytest.mark.parametrize("fraction", ["0.999", "0.5", "0.01"])
def test_any_partial_fraction_leaves_something_open(fraction: str) -> None:
    result = execute(trim_intent=intent(trim_fraction=Decimal(fraction)))

    assert result.status == TRIM_FILLED
    assert result.remaining_quantity > 0


# --- the BTC-157 gate -----------------------------------------------------


def test_an_unsignalled_trim_never_fills() -> None:
    result = execute(trim_signal=quiet_signal())

    assert quiet_signal().signal is False
    assert result.status == TRIM_CANCELLED
    assert result.filled_quantity == Decimal("0")
    assert result.realized_pnl is None
    assert result.average_fill_price is None


def test_a_refusal_keeps_the_signals_own_explanation() -> None:
    result = execute(trim_signal=quiet_signal())

    assert result.reason_codes == (
        "TRIM_EXECUTION_NOT_SIGNALLED",
        "TRIM_NOT_TRIGGERED",
        "TRIM_EXECUTION_CANCELLED",
    )


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        ({"euphoria_active": True}, "TRIM_EUPHORIA_ACTIVE"),
        ({"crowding_active": True}, "TRIM_CROWDING_ACTIVE"),
    ],
)
def test_each_trim_trigger_reaches_execution(override: dict, expected: str) -> None:
    triggering = signal(
        hold_score=Decimal("80"),
        current_flow_score=Decimal("70"),
        **override,
    )

    result = execute(trim_signal=triggering)

    assert triggering.signal is True
    assert expected in triggering.reason_codes
    assert result.status == TRIM_FILLED


def test_the_signal_is_checked_before_the_size() -> None:
    result = execute(
        trim_signal=quiet_signal(),
        trim_intent=intent(trim_fraction=Decimal("1")),
    )

    # A trim that was never signalled was never a sizing question.
    assert result.reason_codes[0] == "TRIM_EXECUTION_NOT_SIGNALLED"


# --- validation -----------------------------------------------------------


@pytest.mark.parametrize(
    ("bad_intent", "match"),
    [
        (intent(direction="flat"), "direction must be one of"),
        (intent(open_quantity=Decimal("0")), "open_quantity must be positive"),
        (intent(trim_fraction=Decimal("0")), "trim_fraction must be positive"),
        (intent(trim_fraction=Decimal("1.5")), "trim_fraction must be between 0 and 1"),
        (intent(average_entry_price=Decimal("0")), "average_entry_price must be"),
        (intent(config_metadata={}), "config_metadata must exactly contain"),
    ],
)
def test_invalid_intents_fail_fast(bad_intent: TrimExecutionIntent, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        execute(trim_intent=bad_intent)


@pytest.mark.parametrize(
    ("execution_bar", "match"),
    [
        (bar(symbol="ETH-USD"), "symbol must match"),
        (bar(low=Decimal("122000")), "impossible OHLC"),
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


def test_the_signal_must_be_the_real_thing() -> None:
    with pytest.raises(TypeError, match="signal must expose"):
        execute(trim_signal=object())


# --- persistence ----------------------------------------------------------


def test_record_carries_the_upstream_decision() -> None:
    record = execute().as_record()

    assert record["signal"]["signal"] is True
    assert record["action"] == "TRIM"
    assert record["order_type"] == "market"
    assert record["filled_quantity"] == "0.99"
    assert record["remaining_quantity"] == "2.01"
    assert record["realized_pnl"] == "19621.859400000000"
    assert record["intent"]["trim_quantity"] == "0.99"


def test_mutated_result_fields_are_rejected_by_the_record() -> None:
    result = execute()

    with pytest.raises(ValueError, match="do not match replayed evidence"):
        replace(result, realized_pnl=Decimal("1")).as_record()
    with pytest.raises(ValueError, match="do not match replayed evidence"):
        replace(result, remaining_quantity=Decimal("0")).as_record()


def test_order_record_matches_the_schema_for_a_fill() -> None:
    order = execute().as_order_record(account_id=7)
    columns = {column.name for column in paper_orders.columns}

    assert set(order) <= columns
    assert order["action"] == "TRIM"
    assert order["side"] == "sell"
    assert order["status"] == "filled"
    assert order["filled_quantity"] == Decimal("0.99")
    assert order["filled_at"] == DECISION_AT + timedelta(hours=1, seconds=5)
    assert order["position_id"] == 3


def test_order_record_marks_a_refusal_cancelled_not_missed() -> None:
    order = execute(trim_signal=quiet_signal()).as_order_record(account_id=7)

    assert order["status"] == "cancelled"
    assert order["filled_at"] is None
    assert order["submitted_at"] is None
    assert order["average_fill_price"] is None
    assert order["requested_quantity"] == Decimal("0.99")


def test_reason_codes_are_drawn_from_the_declared_sets() -> None:
    from btc_predictor.signals import TRIM_REASON_CODES

    permitted = set(TRIM_EXECUTION_REASON_CODES) | set(TRIM_REASON_CODES)
    results = [
        execute(),
        execute(execution_bar=losing_bar()),
        execute(trim_signal=quiet_signal()),
        execute(trim_intent=intent(trim_fraction=Decimal("1"))),
    ]

    for result in results:
        for code in result.reason_codes:
            assert code in permitted


def test_same_evidence_produces_the_same_result() -> None:
    assert execute().as_record() == execute().as_record()
