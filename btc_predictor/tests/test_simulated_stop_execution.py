"""BTC-162: deterministic simulated stop execution."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.data import OhlcvBar
from btc_predictor.db.portfolio import paper_orders
from btc_predictor.portfolio import (
    ADD,
    ENTER,
    EXIT_ACTION,
    PENDING_ENTRY,
    STOP_EXECUTION_FEATURE_ID,
    STOP_EXECUTION_POLICY_VERSION,
    STOP_EXECUTION_REASON_CODES,
    STOP_EXECUTION_STATUSES,
    STOP_FILLED,
    STOP_ORDER,
    STOP_RESTING,
    TRIM,
    ExecutionCosts,
    StopExecutionIntent,
    apply_position_event,
    execution_costs_from_config,
    restore_simulated_stop_execution,
    simulate_stop_execution,
    start_position_lifecycle,
    stop_execution_for_position,
)


UTC = timezone.utc
PLACED_AT = datetime(2024, 9, 2, 12, tzinfo=UTC)
CONFIG_METADATA = load_strategy_config().run_metadata()


def intent(**kwargs) -> StopExecutionIntent:
    base = {
        "execution_id": "stop-001",
        "position_id": 3,
        "symbol": "BTC-USD",
        "direction": "long",
        "timeframe": "1h",
        "stop_price": Decimal("95000"),
        "stop_placed_at": PLACED_AT,
        "average_entry_price": Decimal("100000"),
        "open_quantity": Decimal("2"),
        "config_metadata": CONFIG_METADATA,
    }
    return StopExecutionIntent(**{**base, **kwargs})


def bar(**kwargs) -> OhlcvBar:
    base = {
        "timestamp": PLACED_AT,
        "exchange": "coinbase",
        "symbol": "BTC-USD",
        "timeframe": "1h",
        "open": Decimal("99000"),
        "high": Decimal("99500"),
        "low": Decimal("94000"),
        "close": Decimal("94500"),
        "volume": Decimal("10"),
        "provider": "coinbase",
        "ingested_at": PLACED_AT + timedelta(hours=1, seconds=5),
    }
    return OhlcvBar(**{**base, **kwargs})


def costs() -> ExecutionCosts:
    return execution_costs_from_config()


def execute(**kwargs):
    return simulate_stop_execution(
        kwargs.pop("stop_intent", intent()),
        kwargs.pop("execution_bar", bar()),
        costs=kwargs.pop("execution_costs", costs()),
    )


def test_metadata_and_reason_code_catalog_are_stable() -> None:
    assert STOP_EXECUTION_FEATURE_ID == "SIMULATED_STOP_EXECUTION"
    assert STOP_EXECUTION_POLICY_VERSION == "SIMULATED_STOP_EXECUTION_V1"
    assert STOP_EXECUTION_STATUSES == ("filled", "submitted")
    assert set(STOP_EXECUTION_REASON_CODES) == {
        "STOP_NOT_TOUCHED",
        "STOP_TOUCHED",
        "STOP_FILL_AT_STOP_PRICE",
        "STOP_FILL_AT_GAP_OPEN",
        "STOP_EXECUTION_COSTS_APPLIED",
        "STOP_EXECUTION_FILLED",
        "STOP_EXECUTION_RESTING",
        "STOP_LOSS_EXCEEDED_PLANNED_RISK",
    }


# --- stop touch -----------------------------------------------------------


def test_a_long_stop_fills_when_the_bar_trades_through_it() -> None:
    result = execute()

    # Opened at 99000, above the stop, then traded down to 94000: the stop
    # price was reachable inside the bar.
    assert result.triggered is True
    assert result.gapped is False
    assert result.status == STOP_FILLED
    assert result.action == EXIT_ACTION
    assert result.reference_price == Decimal("95000")
    assert "STOP_FILL_AT_STOP_PRICE" in result.reason_codes


def test_an_untouched_stop_stays_resting_rather_than_being_missed() -> None:
    result = execute(
        execution_bar=bar(low=Decimal("96000"), close=Decimal("99200")),
    )

    # Unlike a BTC-161 entry, a stop that is not hit is not terminal; it is
    # still working on the next bar.
    assert result.triggered is False
    assert result.status == STOP_RESTING
    assert result.action is None
    assert result.filled_quantity == Decimal("0")
    assert result.realized_loss is None
    assert result.reason_codes == ("STOP_NOT_TOUCHED", "STOP_EXECUTION_RESTING")


@pytest.mark.parametrize(
    ("low", "triggered"),
    [("95000", True), ("94999.99", True), ("95000.01", False)],
)
def test_the_long_stop_touch_boundary_is_inclusive(low: str, triggered: bool) -> None:
    result = execute(
        execution_bar=bar(low=Decimal(low), close=Decimal("99200")),
    )

    assert result.triggered is triggered


def test_a_short_stop_fills_when_the_bar_trades_up_through_it() -> None:
    result = execute(
        stop_intent=intent(
            direction="short",
            stop_price=Decimal("105000"),
            average_entry_price=Decimal("100000"),
        ),
        execution_bar=bar(
            open=Decimal("101000"),
            high=Decimal("106000"),
            low=Decimal("100500"),
            close=Decimal("105500"),
        ),
    )

    assert result.triggered is True
    assert result.gapped is False
    assert result.reference_price == Decimal("105000")
    # Exiting a short buys, so slippage fills higher.
    assert result.average_fill_price == Decimal("105052.50000")


@pytest.mark.parametrize(
    ("high", "triggered"),
    [("105000", True), ("105000.01", True), ("104999.99", False)],
)
def test_the_short_stop_touch_boundary_is_inclusive(
    high: str,
    triggered: bool,
) -> None:
    result = execute(
        stop_intent=intent(direction="short", stop_price=Decimal("105000")),
        execution_bar=bar(
            open=Decimal("101000"),
            high=Decimal(high),
            low=Decimal("100500"),
            close=Decimal("101500"),
        ),
    )

    assert result.triggered is triggered


# --- gaps -----------------------------------------------------------------


def test_a_gap_through_a_long_stop_fills_at_the_open() -> None:
    result = execute(
        execution_bar=bar(
            open=Decimal("90000"),
            high=Decimal("91000"),
            low=Decimal("88000"),
            close=Decimal("90500"),
        ),
    )

    # The bar opened below the stop, so the stop price was never offered.
    assert result.gapped is True
    assert result.reference_price == Decimal("90000")
    assert result.average_fill_price == Decimal("89955.00000")
    assert "STOP_FILL_AT_GAP_OPEN" in result.reason_codes


def test_a_gap_through_a_short_stop_fills_at_the_open() -> None:
    result = execute(
        stop_intent=intent(direction="short", stop_price=Decimal("105000")),
        execution_bar=bar(
            open=Decimal("112000"),
            high=Decimal("113000"),
            low=Decimal("111000"),
            close=Decimal("112500"),
        ),
    )

    assert result.gapped is True
    assert result.reference_price == Decimal("112000")


def test_the_gap_test_is_on_the_open_not_the_low() -> None:
    through = execute()
    gapped = execute(
        execution_bar=bar(
            open=Decimal("90000"),
            high=Decimal("91000"),
            low=Decimal("88000"),
            close=Decimal("90500"),
        ),
    )

    # Both bars traded far below the stop. Only where the bar *opened* decides
    # whether the stop price was reachable.
    assert through.execution_bar.low < through.intent.stop_price
    assert gapped.execution_bar.low < gapped.intent.stop_price
    assert through.gapped is False
    assert gapped.gapped is True


def test_a_gap_costs_far_more_than_the_planned_risk() -> None:
    through = execute()
    gapped = execute(
        execution_bar=bar(
            open=Decimal("90000"),
            high=Decimal("91000"),
            low=Decimal("88000"),
            close=Decimal("90500"),
        ),
    )

    # BTC-146 sized this position against a 10,000 loss. The gap more than
    # doubles it, and the record says so rather than absorbing it silently.
    assert through.planned_downside_risk == Decimal("10000")
    assert gapped.planned_downside_risk == Decimal("10000")
    assert gapped.realized_loss == Decimal("20269.9100000000")
    assert gapped.realized_loss > 2 * gapped.planned_downside_risk
    assert gapped.excess_loss == (
        gapped.realized_loss - gapped.planned_downside_risk
    )
    assert "STOP_LOSS_EXCEEDED_PLANNED_RISK" in gapped.reason_codes


def test_planned_downside_is_the_floored_risk_at_stop_formula() -> None:
    stop = intent()

    # BTC-146: protected profit is floored at zero downside rather than turned
    # back into an absolute-distance loss.
    assert stop.planned_downside_risk == stop.open_quantity * max(
        stop.average_entry_price - stop.stop_price,
        Decimal("0"),
    )
    assert stop.planned_downside_risk == Decimal("10000")


# --- slippage -------------------------------------------------------------


def test_slippage_is_adverse_on_the_exit_side() -> None:
    result = execute()

    # Exiting a long sells, so the fill is below the stop price.
    assert result.intent.side == "sell"
    assert result.average_fill_price == Decimal("94952.50000")
    assert result.average_fill_price < result.reference_price


def test_slippage_cost_and_fee_are_reported_separately() -> None:
    result = execute()

    reference_notional = result.intent.open_quantity * result.reference_price
    assert result.notional == Decimal("2") * Decimal("94952.50000")
    assert result.slippage_cost == abs(result.notional - reference_notional)
    assert result.fee == result.notional * Decimal("0.001")
    assert result.realized_loss == (
        result.intent.open_quantity
        * (result.intent.average_entry_price - result.average_fill_price)
    ) + result.fee


def test_zero_cost_assumptions_fill_exactly_at_the_stop() -> None:
    free = ExecutionCosts(
        policy_version="EXECUTION_COST_V1",
        fee_bps=Decimal("0"),
        slippage_bps=Decimal("0"),
        funding_cost_bps_per_day=Decimal("0"),
    )

    result = execute(execution_costs=free)

    # With no costs the realized loss is exactly the planned loss, which is the
    # only condition under which the BTC-146 assumption holds exactly.
    assert result.average_fill_price == Decimal("95000")
    assert result.realized_loss == result.planned_downside_risk
    assert result.excess_loss == Decimal("0")
    assert "STOP_LOSS_EXCEEDED_PLANNED_RISK" not in result.reason_codes


def test_notional_matches_the_btc047_kernel() -> None:
    from btc_predictor.quant.portfolio import position_notional

    result = execute()
    expected = position_notional(
        float(result.filled_quantity),
        float(result.average_fill_price),
    )

    assert float(result.notional) == pytest.approx(expected)


# --- partial position state ----------------------------------------------


def test_a_trimmed_position_is_stopped_out_for_what_remains() -> None:
    full = execute()
    trimmed = execute(stop_intent=intent(open_quantity=Decimal("0.5")))

    # BTC-157 may have reduced the position; the stop covers the remainder,
    # never the size originally entered.
    assert full.filled_quantity == Decimal("2")
    assert trimmed.filled_quantity == Decimal("0.5")
    assert trimmed.planned_downside_risk == Decimal("2500")
    assert trimmed.notional == full.notional / 4


def test_the_stop_is_all_or_nothing_on_the_remaining_quantity() -> None:
    result = execute(stop_intent=intent(open_quantity=Decimal("1.75")))

    # Intrabar liquidity is unknowable from OHLCV, so no partial fill of the
    # stop order itself is invented.
    assert result.filled_quantity == result.intent.open_quantity
    assert result.filled_quantity == Decimal("1.75")


def open_position(*, adds: int = 0, trim: str | None = None):
    lifecycle = start_position_lifecycle(
        symbol="BTC-USD",
        state=PENDING_ENTRY,
        config_metadata=CONFIG_METADATA,
    )
    lifecycle = apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=PLACED_AT - timedelta(hours=3),
        quantity="2",
        price="100000",
        stop_price="95000",
    )
    for index in range(adds):
        lifecycle = apply_position_event(
            lifecycle,
            event=ADD,
            event_time=PLACED_AT - timedelta(hours=2 - index),
            quantity="2",
            price="110000",
        )
    if trim is not None:
        lifecycle = apply_position_event(
            lifecycle,
            event=TRIM,
            event_time=PLACED_AT - timedelta(minutes=30),
            quantity=trim,
        )
    return lifecycle


def test_canonical_path_reads_the_ledger_rather_than_restating_it() -> None:
    lifecycle = open_position()

    result = stop_execution_for_position(
        lifecycle,
        bar(),
        costs=costs(),
        execution_id="stop-canonical",
        position_id=3,
    )

    assert result.intent.direction == "long"
    assert result.intent.stop_price == Decimal("95000")
    assert result.intent.average_entry_price == Decimal("100000")
    assert result.filled_quantity == Decimal("2")


def test_canonical_path_uses_the_trimmed_quantity_and_weighted_entry() -> None:
    lifecycle = open_position(adds=1, trim="1")
    assert lifecycle.quantity == Decimal("3")
    assert lifecycle.average_entry_price == Decimal("105000")

    result = stop_execution_for_position(
        lifecycle,
        bar(),
        costs=costs(),
        execution_id="stop-canonical",
    )

    # Two tranches averaging 105000, trimmed from 4 to 3 units. Both numbers
    # come from the ledger, so neither can be restated inconsistently.
    assert result.intent.average_entry_price == Decimal("105000")
    assert result.filled_quantity == Decimal("3")
    assert result.planned_downside_risk == Decimal("30000")


def test_canonical_path_requires_a_stop_and_an_average_entry() -> None:
    flat = start_position_lifecycle(symbol="BTC-USD")

    with pytest.raises(ValueError, match="stop price"):
        stop_execution_for_position(
            flat,
            bar(),
            costs=costs(),
            execution_id="stop-1",
            stop_placed_at=PLACED_AT,
        )


# --- point-in-time and validation ----------------------------------------


def test_a_bar_before_the_stop_was_placed_cannot_fill_it() -> None:
    early = bar(
        timestamp=PLACED_AT - timedelta(hours=1),
        ingested_at=PLACED_AT + timedelta(seconds=5),
    )

    with pytest.raises(ValueError, match="must not precede"):
        execute(execution_bar=early)


def test_a_later_bar_can_still_fill_a_resting_stop() -> None:
    later = bar(
        timestamp=PLACED_AT + timedelta(hours=5),
        ingested_at=PLACED_AT + timedelta(hours=6, seconds=5),
    )

    result = execute(execution_bar=later)

    assert result.triggered is True
    assert result.resolved_at == PLACED_AT + timedelta(hours=6, seconds=5)


@pytest.mark.parametrize(
    ("bad_intent", "match"),
    [
        (intent(direction="flat"), "direction must be one of"),
        (intent(open_quantity=Decimal("0")), "open_quantity must be positive"),
        (intent(stop_price=Decimal("0")), "stop_price must be positive"),
        (intent(config_metadata={}), "config_metadata must exactly contain"),
    ],
)
def test_invalid_intents_fail_fast(bad_intent: StopExecutionIntent, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        execute(stop_intent=bad_intent)


@pytest.mark.parametrize(
    ("execution_bar", "match"),
    [
        (bar(symbol="ETH-USD"), "symbol must match"),
        (bar(timeframe="1d"), "timeframe must match"),
        (bar(high=Decimal("93000")), "impossible OHLC"),
        (bar(volume=Decimal("-1")), "volume must be non-negative"),
    ],
)
def test_invalid_execution_bars_fail_fast(execution_bar: OhlcvBar, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        execute(execution_bar=execution_bar)


def test_unknown_cost_policy_is_rejected() -> None:
    incompatible = replace(costs(), policy_version="EXECUTION_COST_V2")

    with pytest.raises(ValueError, match="costs.policy_version"):
        execute(execution_costs=incompatible)


# --- persistence ----------------------------------------------------------


def test_record_round_trip_retains_all_provenance() -> None:
    result = execute()
    record = result.as_record()

    assert restore_simulated_stop_execution(record) == result
    assert record["order_type"] == STOP_ORDER
    assert record["gapped"] is False
    assert record["planned_downside_risk"] == "10000"
    assert record["planned_gross_pnl"] == "-10000"
    assert record["realized_loss"] == "10284.9050000000"
    assert record["excess_loss"] == "284.9050000000"


def test_tampered_record_is_rejected_by_replay() -> None:
    record = execute().as_record()
    record["realized_loss"] = "1"

    with pytest.raises(ValueError, match="does not match reconstructed"):
        restore_simulated_stop_execution(record)


def test_mutated_result_fields_are_rejected_by_the_record() -> None:
    result = execute()

    with pytest.raises(ValueError, match="do not match replayed evidence"):
        replace(result, gapped=True).as_record()


def test_order_record_matches_the_schema_for_a_fill() -> None:
    order = execute().as_order_record(account_id=7)
    columns = {column.name for column in paper_orders.columns}

    assert set(order) <= columns
    assert order["action"] == "EXIT"
    assert order["side"] == "sell"
    assert order["order_type"] == "stop"
    assert order["status"] == "filled"
    assert order["stop_price"] == Decimal("95000")
    assert order["filled_at"] == PLACED_AT + timedelta(hours=1, seconds=5)
    assert order["filled_quantity"] == Decimal("2")


def test_order_record_keeps_an_untouched_stop_working() -> None:
    order = execute(
        execution_bar=bar(low=Decimal("96000"), close=Decimal("99200")),
    ).as_order_record(account_id=7)

    # Submitted, not cancelled and not missed: the stop is still live.
    assert order["status"] == "submitted"
    assert order["filled_at"] is None
    assert order["average_fill_price"] is None
    assert order["filled_quantity"] == Decimal("0")


def test_order_record_defaults_the_position_id_from_the_intent() -> None:
    assert execute().as_order_record(account_id=7)["position_id"] == 3
    assert (
        execute(stop_intent=intent(position_id=None)).as_order_record(account_id=7)[
            "position_id"
        ]
        is None
    )


def test_reason_codes_are_drawn_from_the_declared_set() -> None:
    results = [
        execute(),
        execute(execution_bar=bar(low=Decimal("96000"), close=Decimal("99200"))),
        execute(
            execution_bar=bar(
                open=Decimal("90000"),
                high=Decimal("91000"),
                low=Decimal("88000"),
                close=Decimal("90500"),
            ),
        ),
    ]

    for result in results:
        for code in result.reason_codes:
            assert code in STOP_EXECUTION_REASON_CODES


def test_same_evidence_produces_the_same_result() -> None:
    first = execute()
    second = execute()

    assert first == second
    assert first.as_record() == second.as_record()
