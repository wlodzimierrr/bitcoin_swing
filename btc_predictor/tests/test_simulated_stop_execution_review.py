"""Independent BTC-162 correctness and integration review regressions."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.data import OhlcvBar
from btc_predictor.portfolio import (
    ADD,
    ENTER,
    EXIT,
    PENDING_ENTRY,
    STOP_MOVE,
    ExecutionCosts,
    apply_position_event,
    execution_costs_from_config,
    restore_simulated_stop_execution,
    simulate_stop_execution,
    start_position_lifecycle,
    stop_execution_for_position,
)
from btc_predictor.portfolio.stop_execution import (
    STOP_RISK_CONVENTION,
    StopExecutionIntent,
    StopExecutionTranche,
)
from btc_predictor.risk import (
    apply_trailing_stop,
    calculate_risk_at_stop,
    calculate_trailing_stop,
)


UTC = timezone.utc
START = datetime(2024, 9, 2, 12, tzinfo=UTC)
METADATA = load_strategy_config().run_metadata()


def free_costs() -> ExecutionCosts:
    return ExecutionCosts(
        policy_version="EXECUTION_COST_V1",
        fee_bps=Decimal("0"),
        slippage_bps=Decimal("0"),
        funding_cost_bps_per_day=Decimal("0"),
    )


def intent(**kwargs) -> StopExecutionIntent:
    values = {
        "execution_id": "review-stop-1",
        "position_id": 10,
        "symbol": "BTC-USD",
        "direction": "long",
        "timeframe": "1h",
        "stop_price": Decimal("95"),
        "stop_placed_at": START,
        "average_entry_price": Decimal("100"),
        "open_quantity": Decimal("100"),
        "config_metadata": METADATA,
    }
    return StopExecutionIntent(**{**values, **kwargs})


def bar(**kwargs) -> OhlcvBar:
    values = {
        "timestamp": START,
        "exchange": "coinbase",
        "symbol": "BTC-USD",
        "timeframe": "1h",
        "open": Decimal("100"),
        "high": Decimal("102"),
        "low": Decimal("94"),
        "close": Decimal("96"),
        "volume": Decimal("1000"),
        "provider": "coinbase",
        "ingested_at": START + timedelta(hours=1, seconds=5),
    }
    return OhlcvBar(**{**values, **kwargs})


def execute(
    *,
    stop_intent: StopExecutionIntent | None = None,
    execution_bar: OhlcvBar | None = None,
    costs: ExecutionCosts | None = None,
):
    return simulate_stop_execution(
        stop_intent or intent(),
        execution_bar or bar(),
        costs=costs or execution_costs_from_config(),
    )


def test_open_equal_to_stop_is_a_normal_touch_not_a_gap() -> None:
    result = execute(
        execution_bar=bar(
            open=Decimal("95"),
            high=Decimal("97"),
            low=Decimal("94"),
            close=Decimal("96"),
        ),
        costs=free_costs(),
    )

    assert result.triggered is True
    assert result.gapped is False
    assert result.reference_price == Decimal("95")
    assert "STOP_FILL_AT_STOP_PRICE" in result.reason_codes


def test_gap_and_touch_use_the_central_decision_tolerance() -> None:
    nearly_equal = Decimal("0.00000000001")
    near_gap = execute(
        stop_intent=intent(stop_price=Decimal("100")),
        execution_bar=bar(
            open=Decimal("100") - nearly_equal,
            high=Decimal("101"),
            low=Decimal("100") - nearly_equal,
            close=Decimal("100.5"),
        ),
        costs=free_costs(),
    )
    near_touch = execute(
        stop_intent=intent(stop_price=Decimal("100")),
        execution_bar=bar(
            open=Decimal("100.5"),
            high=Decimal("101"),
            low=Decimal("100") + nearly_equal,
            close=Decimal("100.5"),
        ),
        costs=free_costs(),
    )

    assert near_gap.triggered is True
    assert near_gap.gapped is False
    assert near_gap.reference_price == Decimal("100")
    assert near_touch.triggered is True


def test_zero_cost_normal_and_gap_fills_are_exact_for_both_directions() -> None:
    cases = (
        (intent(), bar(), Decimal("95")),
        (
            intent(),
            bar(open=Decimal("90"), high=Decimal("92"), low=Decimal("88"), close=Decimal("91")),
            Decimal("90"),
        ),
        (
            intent(direction="short", stop_price=Decimal("105")),
            bar(open=Decimal("100"), high=Decimal("106"), low=Decimal("99"), close=Decimal("104")),
            Decimal("105"),
        ),
        (
            intent(direction="short", stop_price=Decimal("105")),
            bar(open=Decimal("110"), high=Decimal("112"), low=Decimal("108"), close=Decimal("111")),
            Decimal("110"),
        ),
    )

    for stop_intent, execution_bar, expected in cases:
        result = execute(
            stop_intent=stop_intent,
            execution_bar=execution_bar,
            costs=free_costs(),
        )
        assert result.reference_price == expected
        assert result.average_fill_price == expected
        assert result.fee == result.slippage_cost == 0


def test_valid_profitable_long_trailing_stop_executes_with_signed_pnl() -> None:
    result = execute(
        stop_intent=intent(stop_price=Decimal("110")),
        execution_bar=bar(
            open=Decimal("115"),
            high=Decimal("116"),
            low=Decimal("109"),
            close=Decimal("111"),
        ),
    )

    assert result.average_fill_price == Decimal("109.9450")
    assert result.planned_downside_risk == 0
    assert result.planned_gross_pnl == Decimal("1000")
    assert result.gross_pnl == Decimal("994.5000")
    assert result.fee == Decimal("10.99450000")
    assert result.net_pnl == Decimal("983.50550000")
    assert result.realized_loss == 0
    assert result.execution_shortfall == Decimal("16.49450000")
    assert result.excess_loss == 0
    assert "STOP_LOSS_EXCEEDED_PLANNED_RISK" not in result.reason_codes


def test_valid_profitable_short_trailing_stop_executes_with_signed_pnl() -> None:
    result = execute(
        stop_intent=intent(direction="short", stop_price=Decimal("90")),
        execution_bar=bar(
            open=Decimal("85"),
            high=Decimal("91"),
            low=Decimal("84"),
            close=Decimal("88"),
        ),
    )

    assert result.intent.side == "buy"
    assert result.average_fill_price == Decimal("90.0450")
    assert result.planned_downside_risk == 0
    assert result.net_pnl == Decimal("986.49550000")
    assert result.realized_loss == 0
    assert "STOP_LOSS_EXCEEDED_PLANNED_RISK" not in result.reason_codes


def test_mixed_tranches_keep_downside_risk_separate_from_signed_pnl() -> None:
    mixed = intent(
        stop_price=Decimal("100"),
        tranches=(
            StopExecutionTranche("A", Decimal("90"), Decimal("1")),
            StopExecutionTranche("B", Decimal("110"), Decimal("1")),
        ),
        open_quantity=Decimal("2"),
    )
    result = execute(
        stop_intent=mixed,
        execution_bar=bar(
            open=Decimal("105"),
            high=Decimal("106"),
            low=Decimal("99"),
            close=Decimal("100"),
        ),
        costs=free_costs(),
    )

    # A locks in +10, B risks -10. BTC-146 floors A at zero for downside-risk
    # purposes, while signed position P&L correctly nets the two tranches.
    assert result.planned_downside_risk == Decimal("10")
    assert result.planned_gross_pnl == Decimal("0")
    assert result.gross_pnl == result.net_pnl == Decimal("0")
    assert result.realized_loss == result.excess_loss == Decimal("0")
    assert result.intent.as_record()["risk_at_stop_convention"] == STOP_RISK_CONVENTION
    btc146 = calculate_risk_at_stop(
        [
            {"tranche_id": "A", "entry_price": "90", "quantity": "1"},
            {"tranche_id": "B", "entry_price": "110", "quantity": "1"},
        ],
        stop_price="100",
        nav="1000",
        direction="long",
        config_metadata=METADATA,
    )
    assert result.planned_downside_risk == btc146.risk_at_stop


@pytest.mark.parametrize(
    "bad_tranches",
    [
        (StopExecutionTranche("A", Decimal("100"), Decimal("99")),),
        (
            StopExecutionTranche("A", Decimal("90"), Decimal("50")),
            StopExecutionTranche("A", Decimal("110"), Decimal("50")),
        ),
    ],
)
def test_tranche_snapshots_must_reconcile_with_the_position(
    bad_tranches: tuple[StopExecutionTranche, ...],
) -> None:
    with pytest.raises(ValueError, match="tranche|average"):
        execute(stop_intent=intent(tranches=bad_tranches), costs=free_costs())


def test_gap_loss_reconciles_from_first_principles_without_double_counting() -> None:
    result = execute(
        execution_bar=bar(
            open=Decimal("90"),
            high=Decimal("91"),
            low=Decimal("88"),
            close=Decimal("90.5"),
        ),
    )

    # 100 units: 95 stop -> 90 gap open -> 89.955 adverse sell fill.
    assert result.planned_downside_risk == Decimal("500")
    assert result.reference_price == Decimal("90")
    assert result.average_fill_price == Decimal("89.9550")
    assert result.slippage_cost == Decimal("4.5000")
    assert result.gross_pnl == Decimal("-1004.5000")
    assert result.fee == Decimal("8.99550000")
    assert result.net_pnl == Decimal("-1013.49550000")
    assert result.realized_loss == Decimal("1013.49550000")
    assert result.excess_loss == Decimal("513.49550000")
    assert result.execution_shortfall == Decimal("513.49550000")


def test_an_untouched_stop_can_fill_on_a_later_bar() -> None:
    untouched = execute(
        execution_bar=bar(low=Decimal("96"), close=Decimal("100")),
        costs=free_costs(),
    )
    later = execute(
        execution_bar=replace(
            bar(),
            timestamp=START + timedelta(hours=1),
            ingested_at=START + timedelta(hours=2),
        ),
        costs=free_costs(),
    )

    assert untouched.resting is True and untouched.action is None
    assert later.filled is True and later.filled_quantity == Decimal("100")


def test_a_stop_placed_mid_bar_cannot_use_that_partial_bar() -> None:
    placed_mid_bar = intent(stop_placed_at=START + timedelta(minutes=5))

    with pytest.raises(ValueError, match="first eligible bar"):
        execute(stop_intent=placed_mid_bar, execution_bar=bar(), costs=free_costs())

    next_full_bar = replace(
        bar(),
        timestamp=START + timedelta(hours=1),
        ingested_at=START + timedelta(hours=2),
    )
    assert execute(
        stop_intent=placed_mid_bar,
        execution_bar=next_full_bar,
        costs=free_costs(),
    ).filled


def open_lifecycle(*, entry: str = "100", stop: str = "90"):
    lifecycle = start_position_lifecycle(
        symbol="BTC-USD",
        state=PENDING_ENTRY,
        config_metadata=METADATA,
    )
    return apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=START - timedelta(hours=3),
        quantity="1",
        price=entry,
        stop_price=stop,
    )


def trailing_result(
    *,
    previous_stop: str,
    structure_price: str,
    buffer: str,
    advance_count: int,
    evaluated_at: datetime,
    structure_id: str,
):
    return calculate_trailing_stop(
        direction="long",
        previous_stop=previous_stop,
        structure_price=structure_price,
        buffer=buffer,
        advance_count=advance_count,
        current_price="115",
        config_metadata=METADATA,
        evaluated_at=evaluated_at,
        structure_id=structure_id,
        structure_source_feature_id="ENTRY_TRIGGER_HIGHER_LOW",
        structure_type="HIGHER_LOW",
        structure_level_timestamp=evaluated_at - timedelta(hours=2),
        structure_detected_at=evaluated_at - timedelta(hours=1),
        structure_reason_codes=("HIGHER_LOW_CONFIRMED",),
    )


def lifecycle_with_profitable_btc156_stop():
    lifecycle = open_lifecycle()
    first_time = START - timedelta(hours=2)
    first = trailing_result(
        previous_stop="90",
        structure_price="97",
        buffer="2",
        advance_count=0,
        evaluated_at=first_time,
        structure_id="hl-1",
    )
    lifecycle = apply_trailing_stop(lifecycle, first, event_time=first_time)
    second_time = START
    second = trailing_result(
        previous_stop="95",
        structure_price="112",
        buffer="2",
        advance_count=1,
        evaluated_at=second_time,
        structure_id="hl-2",
    )
    assert second.stage == "PROFIT_PROTECTION_TRAIL"
    return apply_trailing_stop(lifecycle, second, event_time=second_time)


def test_btc156_profit_protection_stop_executes_and_closes_btc150() -> None:
    lifecycle = lifecycle_with_profitable_btc156_stop()
    result = stop_execution_for_position(
        lifecycle,
        bar(open=Decimal("115"), high=Decimal("116"), low=Decimal("109"), close=Decimal("111")),
        costs=free_costs(),
        execution_id="profit-stop",
    )

    assert result.intent.stop_price == Decimal("110")
    assert result.intent.stop_placed_at == START
    assert result.net_pnl == Decimal("10")
    closed = apply_position_event(
        lifecycle,
        event=EXIT,
        event_time=result.resolved_at,
        quantity=result.filled_quantity,
        price=result.average_fill_price,
        reason_codes=result.reason_codes,
        source_feature_id=result.feature_id,
        source_record_id=result.intent.execution_id,
    )
    assert closed.state == "CLOSED"
    assert closed.quantity == 0

    repeated = apply_position_event(
        closed,
        event=EXIT,
        event_time=result.resolved_at,
        quantity=result.filled_quantity,
        price=result.average_fill_price,
        source_feature_id=result.feature_id,
        source_record_id=result.intent.execution_id,
    )
    assert repeated.accepted is False
    assert repeated.quantity == 0


def test_initial_entry_bracket_can_resolve_on_the_entry_execution_bar() -> None:
    lifecycle = start_position_lifecycle(
        symbol="BTC-USD",
        state=PENDING_ENTRY,
        config_metadata=METADATA,
    )
    lifecycle = apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=START + timedelta(hours=1, seconds=5),
        quantity="1",
        price="100",
        stop_price="95",
    )

    result = stop_execution_for_position(
        lifecycle,
        bar(),
        costs=free_costs(),
        execution_id="entry-bracket-stop",
        entry_bracket_placed_at=START,
    )

    assert result.filled is True
    assert result.intent.stop_placed_at == START


def test_entry_bracket_override_cannot_restate_a_later_trailing_stop() -> None:
    lifecycle = lifecycle_with_profitable_btc156_stop()

    with pytest.raises(ValueError, match="initial ENTER stop"):
        stop_execution_for_position(
            lifecycle,
            bar(open=Decimal("115"), high=Decimal("116"), low=Decimal("109"), close=Decimal("111")),
            costs=free_costs(),
            execution_id="invalid-trailing-bracket",
            entry_bracket_placed_at=START - timedelta(hours=4),
        )


def test_newly_raised_stop_cannot_trigger_retroactively() -> None:
    lifecycle = lifecycle_with_profitable_btc156_stop()
    earlier = replace(
        bar(),
        timestamp=START - timedelta(hours=1),
        ingested_at=START,
    )

    with pytest.raises(ValueError, match="must not precede"):
        stop_execution_for_position(
            lifecycle,
            earlier,
            costs=free_costs(),
            execution_id="retroactive-stop",
        )


def test_canonical_path_rejects_restatement_of_stop_time_or_config() -> None:
    lifecycle = open_lifecycle()

    with pytest.raises(ValueError, match="stop transition"):
        stop_execution_for_position(
            lifecycle,
            bar(),
            costs=free_costs(),
            execution_id="stale-time",
            stop_placed_at=START,
        )
    with pytest.raises(ValueError, match="config_metadata must match"):
        stop_execution_for_position(
            lifecycle,
            bar(),
            costs=free_costs(),
            execution_id="wrong-config",
            config_metadata={**METADATA, "parameter_set_id": "other"},
        )


def test_canonical_path_requires_a_real_btc150_lifecycle() -> None:
    with pytest.raises(TypeError, match="PositionLifecycle"):
        stop_execution_for_position(
            object(),
            bar(),
            costs=free_costs(),
            execution_id="not-a-ledger",
        )


def test_order_record_cannot_restate_a_known_position_id() -> None:
    result = execute()

    with pytest.raises(ValueError, match="must match the execution intent"):
        result.as_order_record(account_id=1, position_id=999)


def test_canonical_mixed_tranche_snapshot_survives_trim_and_replay() -> None:
    lifecycle = open_lifecycle(entry="90", stop="80")
    lifecycle = apply_position_event(
        lifecycle,
        event=ADD,
        event_time=START - timedelta(hours=2),
        quantity="1",
        price="110",
    )
    lifecycle = apply_position_event(
        lifecycle,
        event=STOP_MOVE,
        event_time=START,
        stop_price="100",
    )
    result = stop_execution_for_position(
        lifecycle,
        bar(open=Decimal("105"), high=Decimal("106"), low=Decimal("99"), close=Decimal("100")),
        costs=free_costs(),
        execution_id="mixed-stop",
    )

    assert len(result.intent.tranches) == 2
    assert result.planned_downside_risk == Decimal("10")
    assert result.net_pnl == Decimal("0")
    assert restore_simulated_stop_execution(result.as_record()) == result


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("triggered", False),
        ("gapped", True),
        ("reference_price", "1"),
        ("average_fill_price", "1"),
        ("filled_quantity", "1"),
        ("fee", "1"),
        ("gross_pnl", "1"),
        ("net_pnl", "1"),
        ("planned_downside_risk", "1"),
        ("reason_codes", []),
    ],
)
def test_restore_rejects_tampered_execution_fields(field: str, bad_value) -> None:
    record = execute().as_record()
    record[field] = bad_value

    with pytest.raises(ValueError, match="does not match reconstructed"):
        restore_simulated_stop_execution(record)


def test_negative_execution_rates_are_rejected() -> None:
    bad = replace(execution_costs_from_config(), slippage_bps=Decimal("-1"))

    with pytest.raises(ValueError, match="slippage_bps must be non-negative"):
        execute(costs=bad)
