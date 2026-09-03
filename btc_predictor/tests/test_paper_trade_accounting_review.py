"""Independent BTC-165 accounting review regressions."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from fractions import Fraction

import pytest

from btc_predictor.data import OhlcvBar
from btc_predictor.db.portfolio import completed_trades
from btc_predictor.portfolio.accounting import (
    EXCURSION_CONVENTION,
    FUNDING_CONVENTION,
    MAXIMUM_SIZE_CONVENTION,
    FundingEvent,
    TradeFill,
    calculate_trade_accounting,
    calculate_trade_accounting_for_lifecycle,
    funding_event_from_rate,
    restore_trade_accounting,
    trade_fill_from_execution,
)
from btc_predictor.portfolio.account import ExecutionCosts
from btc_predictor.portfolio.stop_execution import (
    StopExecutionIntent,
    simulate_stop_execution,
)
from btc_predictor.portfolio.state_machine import (
    ENTER,
    EXIT,
    PENDING_ENTRY,
    apply_position_event,
    start_position_lifecycle,
)


START = datetime(2026, 1, 1, tzinfo=UTC)
CONFIG = {
    "config_version": "strategy_config_v2",
    "strategy_version": "swing_v1.2",
    "parameter_set_id": "default_phase1",
}


def at(hours: int) -> datetime:
    return START + timedelta(hours=hours)


def fill(
    sequence: int,
    hours: int,
    action: str,
    quantity: str,
    price: str,
    *,
    fee: str = "0",
    event_id: str | None = None,
) -> TradeFill:
    return TradeFill(
        sequence=sequence,
        filled_at=at(hours),
        action=action,
        quantity=Decimal(quantity),
        price=Decimal(price),
        fee=Decimal(fee),
        source_event_id=event_id or f"fill-{sequence}",
        execution_bar_at=at(hours),
        execution_bar_timeframe="1h",
    )


def bar(hours: int, *, open_: str, high: str, low: str, close: str) -> OhlcvBar:
    timestamp = at(hours)
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1h",
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("1"),
        provider="coinbase",
        ingested_at=timestamp + timedelta(hours=1),
    )


def account(fills, **kwargs):
    values = {
        "symbol": "BTC-USD",
        "direction": "long",
        "initial_stop_price": "90",
        "initial_stop_source_id": "stop-1",
        "exit_reason": "STRUCTURAL_STOP",
        "exit_reason_source_id": "exit-signal-1",
        "config_metadata": CONFIG,
    }
    return calculate_trade_accounting(fills, **{**values, **kwargs})


def test_execution_bars_cannot_inflate_excursions() -> None:
    result = account(
        (
            fill(1, 0, "ENTER", "1", "100"),
            fill(2, 2, "ADD", "1", "110"),
            fill(3, 4, "TRIM", "1", "120"),
            fill(4, 6, "EXIT", "1", "115"),
        ),
        excursion_bars=(
            bar(0, open_="100", high="1000", low="1", close="100"),
            bar(1, open_="100", high="108", low="95", close="105"),
            bar(2, open_="110", high="2000", low="2", close="110"),
            bar(3, open_="110", high="125", low="105", close="120"),
            bar(4, open_="120", high="3000", low="3", close="120"),
            bar(5, open_="120", high="122", low="112", close="115"),
            bar(6, open_="115", high="4000", low="4", close="115"),
        ),
    )

    # Full execution-bar OHLC is unknowably before/after each fill and is
    # excluded. Exact non-entry fill prices are still eligible endpoints.
    assert result.maximum_favourable_excursion == Decimal("40")
    assert result.maximum_adverse_excursion == Decimal("-5")
    assert result.gross_pnl == Decimal("25")
    assert result.maximum_adverse_excursion <= result.gross_pnl
    assert result.gross_pnl <= result.maximum_favourable_excursion


def test_gap_stop_uses_exact_fill_without_post_exit_high() -> None:
    result = account(
        (fill(1, 0, "ENTER", "1", "100"), fill(2, 2, "EXIT", "1", "80")),
        excursion_bars=(
            bar(1, open_="100", high="105", low="95", close="100"),
            bar(2, open_="80", high="500", low="70", close="400"),
        ),
    )

    assert result.maximum_favourable_excursion == Decimal("5")
    assert result.maximum_adverse_excursion == Decimal("-20")
    assert result.gross_pnl == Decimal("-20")


@pytest.mark.parametrize(
    ("direction", "expected"),
    [("long", "83"), ("short", "87")],
)
def test_interleaved_add_trim_add_trim_exit_reconciles_cash_flows(
    direction: str,
    expected: str,
) -> None:
    prices = (
        ("100", "101", "110", "90", "95", "120")
        if direction == "long"
        else ("100", "101", "90", "110", "105", "80")
    )
    fills = (
        fill(1, 0, "ENTER", "3", prices[0]),
        fill(2, 1, "ADD", "2", prices[1]),
        fill(3, 2, "TRIM", "2", prices[2]),
        fill(4, 3, "ADD", "1", prices[3]),
        fill(5, 4, "TRIM", "1", prices[4]),
        fill(6, 5, "EXIT", "3", prices[5]),
    )
    kwargs = {"direction": direction}
    if direction == "short":
        kwargs["initial_stop_price"] = "110"

    result = account(fills, **kwargs)

    entries = sum(
        item.notional for item in fills if item.action in ("ENTER", "ADD")
    )
    exits = sum(item.notional for item in fills if item.action in ("TRIM", "EXIT"))
    independent_cash_flow = exits - entries if direction == "long" else entries - exits
    assert independent_cash_flow == Decimal(expected)
    assert result.gross_pnl == independent_cash_flow
    assert result.entry_notional == entries
    assert result.exit_notional == exits


def test_decimal_property_grid_preserves_exact_close_identity() -> None:
    for case in range(1, 51):
        entry = Decimal("100") + Decimal(case) / Decimal("7")
        add = Decimal("90") + Decimal(case) / Decimal("11")
        trim = Decimal("105") + Decimal(case) / Decimal("13")
        exit_price = Decimal("110") + Decimal(case) / Decimal("17")
        fills = (
            fill(1, 0, "ENTER", "3", str(entry)),
            fill(2, 1, "ADD", "2", str(add)),
            fill(3, 2, "TRIM", "2", str(trim)),
            fill(4, 3, "EXIT", "3", str(exit_price)),
        )
        result = account(fills)
        buys = Decimal("3") * entry + Decimal("2") * add
        sells = Decimal("2") * trim + Decimal("3") * exit_price

        assert result.gross_pnl == sells - buys
        assert result.entry_notional == buys
        assert result.exit_notional == sells


def test_non_terminating_quantity_grid_preserves_exact_close_identity() -> None:
    """The axis that used to break: a quantity that fills the Decimal context.

    The grid above varies prices, which BTC-165 could always absorb because a
    price never enters the pro-rata basis divisor. An open quantity does, and
    BTC-155 produces non-terminating ones routinely by dividing a notional by
    a price. Every expectation here is rational, because a Decimal expression
    would round exactly the digits under test.
    """

    non_terminating = 0
    for case in range(1, 51):
        entry_quantity = Decimal(case) / Decimal("7")
        add_quantity = Decimal(case) / Decimal("11")
        open_quantity = entry_quantity + add_quantity
        trim_quantity = Decimal(case) / Decimal("13")
        exit_quantity = open_quantity - trim_quantity
        if open_quantity != open_quantity.quantize(Decimal("1e-20")):
            non_terminating += 1
        for direction, opening, closing in (
            ("long", ("ENTER", "ADD"), ("TRIM", "EXIT")),
            ("short", ("ENTER", "ADD"), ("TRIM", "EXIT")),
        ):
            prices = (
                ("100", "104", "112", "118")
                if direction == "long"
                else ("118", "112", "104", "100")
            )
            fills = (
                fill(1, 0, opening[0], str(entry_quantity), prices[0]),
                fill(2, 1, opening[1], str(add_quantity), prices[1]),
                fill(3, 2, closing[0], str(trim_quantity), prices[2]),
                fill(4, 3, closing[1], str(exit_quantity), prices[3]),
            )
            stop = "80" if direction == "long" else "140"
            result = account(fills, direction=direction, initial_stop_price=stop)

            buys = Fraction(fills[0].notional) + Fraction(fills[1].notional)
            sells = Fraction(fills[2].notional) + Fraction(fills[3].notional)
            expected = sells - buys if direction == "long" else buys - sells

            signed = (
                result.exit_notional - result.entry_notional
                if direction == "long"
                else result.entry_notional - result.exit_notional
            )
            assert result.closed is True
            assert Fraction(result.entry_notional) == buys
            assert Fraction(result.exit_notional) == sells
            assert Fraction(result.gross_pnl) == expected
            assert result.gross_pnl == signed

    # The grid is only evidence if most of it really does repeat.
    assert non_terminating >= 45


def test_excursion_inputs_require_execution_bar_provenance() -> None:
    fills = (
        replace(
            fill(1, 0, "ENTER", "1", "100"),
            execution_bar_at=None,
            execution_bar_timeframe=None,
        ),
        fill(2, 2, "EXIT", "1", "110"),
    )

    with pytest.raises(ValueError, match="execution-bar provenance"):
        account(fills, excursion_bars=(bar(1, open_="100", high="110", low="90", close="105"),))


def test_signed_funding_mirrors_long_and_short() -> None:
    long_event = funding_event_from_rate(
        sequence=2,
        event_id="funding-1",
        effective_at=at(1),
        rate="0.01",
        mark_price="100",
        position_quantity="1",
        direction="long",
    )
    short_event = funding_event_from_rate(
        sequence=2,
        event_id="funding-1",
        effective_at=at(1),
        rate="0.01",
        mark_price="100",
        position_quantity="1",
        direction="short",
    )
    fills = (fill(1, 0, "ENTER", "1", "100"), fill(3, 2, "EXIT", "1", "100"))

    long_result = account(fills, funding_events=(long_event,))
    short_result = account(
        fills,
        direction="short",
        initial_stop_price="110",
        funding_events=(short_event,),
    )

    assert long_result.funding == Decimal("1")
    assert long_result.net_pnl == Decimal("-1")
    assert short_result.funding == Decimal("-1")
    assert short_result.net_pnl == Decimal("1")


def test_funding_quantity_must_match_the_position_at_each_event() -> None:
    fills = (
        fill(1, 0, "ENTER", "2", "100"),
        fill(3, 2, "TRIM", "1", "110"),
        fill(5, 4, "EXIT", "1", "120"),
    )
    event = funding_event_from_rate(
        sequence=4,
        event_id="funding-after-trim",
        effective_at=at(3),
        rate="0.01",
        mark_price="110",
        position_quantity="2",
        direction="long",
    )

    with pytest.raises(ValueError, match="position quantity"):
        account(fills, funding_events=(event,))


def test_same_timestamp_funding_uses_explicit_event_sequence() -> None:
    fills = (
        fill(1, 0, "ENTER", "1", "100"),
        fill(3, 1, "ADD", "1", "110"),
        fill(5, 2, "EXIT", "2", "120"),
    )
    before_add = funding_event_from_rate(
        sequence=2,
        event_id="funding-before-add",
        effective_at=at(1),
        rate="0.01",
        mark_price="100",
        position_quantity="1",
        direction="long",
    )
    after_add = funding_event_from_rate(
        sequence=4,
        event_id="funding-after-add",
        effective_at=at(1),
        rate="0.01",
        mark_price="100",
        position_quantity="2",
        direction="long",
    )

    result = account(fills, funding_events=(before_add, after_add))

    assert result.funding == Decimal("3")
    assert [event.event_id for event in result.funding_events] == [
        "funding-before-add",
        "funding-after-add",
    ]


@pytest.mark.parametrize("hour", [0, 2, 3])
def test_funding_outside_the_open_interval_is_rejected(hour: int) -> None:
    fills = (fill(1, 0, "ENTER", "1", "100"), fill(3, 2, "EXIT", "1", "100"))
    event = funding_event_from_rate(
        sequence=2,
        event_id=f"funding-{hour}",
        effective_at=at(hour),
        rate="0.01",
        mark_price="100",
        position_quantity="1",
        direction="long",
    )

    with pytest.raises(ValueError, match="open holding interval"):
        account(fills, funding_events=(event,))


def test_aggregate_funding_is_not_accepted_without_event_provenance() -> None:
    fills = (fill(1, 0, "ENTER", "1", "100"), fill(2, 2, "EXIT", "1", "100"))

    with pytest.raises(ValueError, match="funding_events"):
        account(fills, funding="1")


def test_open_trade_uses_explicit_as_of_and_has_no_final_exit_or_r() -> None:
    result = account(
        (fill(1, 0, "ENTER", "2", "100"), fill(2, 2, "TRIM", "1", "110")),
        as_of=at(5),
        exit_reason=None,
        exit_reason_source_id=None,
    )

    assert result.closed is False
    assert result.closed_at is None
    assert result.as_of == at(5)
    assert result.holding_days == Decimal("5") / Decimal("24")
    assert result.exit_reason is None
    assert result.r_multiple is None


def test_open_trade_without_as_of_is_rejected() -> None:
    with pytest.raises(ValueError, match="as_of is required"):
        account(
            (fill(1, 0, "ENTER", "1", "100"),),
            exit_reason=None,
            exit_reason_source_id=None,
        )


def test_duplicate_fill_and_funding_event_ids_are_rejected() -> None:
    duplicate_fills = (
        fill(1, 0, "ENTER", "1", "100", event_id="same"),
        fill(2, 2, "EXIT", "1", "110", event_id="same"),
    )
    with pytest.raises(ValueError, match="source_event_id"):
        account(duplicate_fills)

    fills = (fill(1, 0, "ENTER", "1", "100"), fill(4, 3, "EXIT", "1", "100"))
    event = funding_event_from_rate(
        sequence=2,
        event_id="same-funding",
        effective_at=at(1),
        rate="0.01",
        mark_price="100",
        position_quantity="1",
        direction="long",
    )
    duplicate = replace(event, sequence=3, effective_at=at(2))
    with pytest.raises(ValueError, match="funding event IDs"):
        account(fills, funding_events=(event, duplicate))


def test_record_replay_rejects_tampering_of_any_derived_metric() -> None:
    result = account(
        (fill(1, 0, "ENTER", "1", "100"), fill(2, 2, "EXIT", "1", "120")),
        excursion_bars=(bar(1, open_="100", high="125", low="95", close="120"),),
    )
    record = result.as_record()

    assert restore_trade_accounting(record).as_record() == record
    for field, replacement in (
        ("gross_pnl", "999"),
        ("initial_risk", "999"),
        ("maximum_favourable_excursion", "999"),
        ("add_count", 99),
        ("exit_reason", "MANUAL_RESEARCH_OVERRIDE"),
    ):
        tampered = {**record, field: replacement}
        with pytest.raises(ValueError, match="replayed evidence"):
            restore_trade_accounting(tampered)


def test_as_record_recomputes_instead_of_trusting_a_replaced_dataclass() -> None:
    result = account(
        (fill(1, 0, "ENTER", "1", "100"), fill(2, 2, "EXIT", "1", "120")),
    )

    with pytest.raises(ValueError, match="replayed evidence"):
        replace(result, gross_pnl=Decimal("999")).as_record()


def test_completed_trade_row_persists_every_accounting_metric_and_policy() -> None:
    result = account(
        (fill(1, 0, "ENTER", "1", "100"), fill(2, 2, "EXIT", "1", "120")),
        excursion_bars=(bar(1, open_="100", high="125", low="95", close="120"),),
    )
    row = result.as_completed_trade_record(account_id=7, position_id=9)
    columns = {column.name for column in completed_trades.columns}

    assert set(row) <= columns
    assert row["gross_pnl"] == result.gross_pnl
    assert row["fees"] == result.fees
    assert row["funding"] == result.funding
    assert row["mfe"] == result.maximum_favourable_excursion
    assert row["mae"] == result.maximum_adverse_excursion
    assert row["holding_days"] == result.holding_days
    assert row["maximum_quantity"] == result.maximum_quantity
    assert row["maximum_entry_notional"] == result.maximum_entry_notional
    assert row["exit_reason"] == "STRUCTURAL_STOP"
    assert row["initial_stop_source_id"] == "stop-1"
    assert row["exit_reason_source_id"] == "exit-signal-1"
    assert row["accounting_evidence_digest"] == result.evidence_digest
    assert row["accounting_policy_version"] == "PAPER_TRADE_ACCOUNTING_V1"
    assert row["funding_convention"] == FUNDING_CONVENTION
    assert row["excursion_convention"] == EXCURSION_CONVENTION
    assert row["maximum_size_convention"] == MAXIMUM_SIZE_CONVENTION
    assert row["accounting_record"] == result.as_record()


def test_config_and_authoritative_source_identity_are_required() -> None:
    fills = (fill(1, 0, "ENTER", "1", "100"), fill(2, 2, "EXIT", "1", "110"))

    with pytest.raises(ValueError, match="config_metadata"):
        account(fills, config_metadata={"config_version": "v1"})
    with pytest.raises(ValueError, match="initial_stop_source_id"):
        account(fills, initial_stop_source_id="")
    with pytest.raises(ValueError, match="exit_reason_source_id"):
        account(fills, exit_reason_source_id="")


def test_policy_names_make_units_and_signs_unambiguous() -> None:
    assert FUNDING_CONVENTION == "SIGNED_ACCOUNT_FUNDING_COST_V1"
    assert EXCURSION_CONVENTION == "SIGNED_GROSS_PNL_FULL_BARS_AND_FILL_ENDPOINTS_V1"
    assert MAXIMUM_SIZE_CONVENTION == "MAX_OPEN_ENTRY_COST_BASIS_V1"
    assert FundingEvent.__doc__


def test_canonical_lifecycle_path_derives_stop_and_exit_provenance() -> None:
    lifecycle = start_position_lifecycle(
        symbol="BTC-USD",
        direction="long",
        state=PENDING_ENTRY,
        config_metadata=CONFIG,
    )
    lifecycle = apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=at(0),
        quantity="1",
        price="100",
        stop_price="90",
        source_feature_id="SIMULATED_ENTRY_EXECUTION",
        source_record_id="entry-execution-1",
    )
    lifecycle = apply_position_event(
        lifecycle,
        event=EXIT,
        event_time=at(2),
        price="120",
        reason_codes=("STRUCTURAL_STOP",),
        source_feature_id="EXIT_SIGNAL",
        source_record_id="exit-signal-1",
    )
    fills = (
        fill(1, 0, "ENTER", "1", "100", event_id="entry-execution-1"),
        fill(2, 2, "EXIT", "1", "120", event_id="exit-signal-1"),
    )

    result = calculate_trade_accounting_for_lifecycle(lifecycle, fills)

    assert result.initial_stop_price == Decimal("90")
    assert result.initial_stop_source_id == "entry-execution-1"
    assert result.exit_reason == "STRUCTURAL_STOP"
    assert result.exit_reason_source_id == "exit-signal-1"


def test_canonical_lifecycle_path_rejects_a_fill_not_in_the_ledger() -> None:
    lifecycle = start_position_lifecycle(
        symbol="BTC-USD",
        direction="long",
        state=PENDING_ENTRY,
        config_metadata=CONFIG,
    )
    lifecycle = apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=at(0),
        quantity="1",
        price="100",
        stop_price="90",
        source_feature_id="SIMULATED_ENTRY_EXECUTION",
        source_record_id="entry-execution-1",
    )
    lifecycle = apply_position_event(
        lifecycle,
        event=EXIT,
        event_time=at(2),
        price="120",
        reason_codes=("STRUCTURAL_STOP",),
        source_feature_id="EXIT_SIGNAL",
        source_record_id="exit-signal-1",
    )
    fills = (
        fill(1, 0, "ENTER", "1", "100", event_id="entry-execution-1"),
        fill(2, 2, "EXIT", "1", "119", event_id="exit-signal-1"),
    )

    with pytest.raises(ValueError, match="authoritative lifecycle transition"):
        calculate_trade_accounting_for_lifecycle(lifecycle, fills)


@pytest.mark.parametrize(
    ("standing_stop", "bar_open", "expected_gross"),
    [("95", "80", "-20"), ("110", "115", "10")],
)
def test_btc_162_stop_fill_reconciles_to_final_trade_accounting(
    standing_stop: str,
    bar_open: str,
    expected_gross: str,
) -> None:
    costs = ExecutionCosts(
        policy_version="EXECUTION_COST_V1",
        fee_bps=Decimal("0"),
        slippage_bps=Decimal("0"),
        funding_cost_bps_per_day=Decimal("0"),
    )
    intent = StopExecutionIntent(
        execution_id="stop-execution-1",
        position_id=1,
        symbol="BTC-USD",
        direction="long",
        timeframe="1h",
        stop_price=Decimal(standing_stop),
        stop_placed_at=at(0),
        average_entry_price=Decimal("100"),
        open_quantity=Decimal("1"),
        config_metadata=CONFIG,
    )
    execution_bar = bar(
        0,
        open_=bar_open,
        high="500",
        low="70" if Decimal(standing_stop) < 100 else "109",
        close=bar_open,
    )
    execution = simulate_stop_execution(intent, execution_bar, costs=costs)
    exit_fill = trade_fill_from_execution(execution, sequence=2)
    entry_fill = TradeFill(
        sequence=1,
        filled_at=at(-1),
        action="ENTER",
        quantity=Decimal("1"),
        price=Decimal("100"),
        source_event_id="entry-execution-1",
        execution_bar_at=at(-2),
        execution_bar_timeframe="1h",
    )

    result = account(
        (entry_fill, exit_fill),
        excursion_bars=(execution_bar,),
        as_of=exit_fill.filled_at,
        exit_reason_source_id="stop-execution-1",
    )

    assert execution.gross_pnl == Decimal(expected_gross)
    assert result.gross_pnl == execution.gross_pnl
    assert result.maximum_favourable_excursion == result.gross_pnl
    assert result.maximum_adverse_excursion == result.gross_pnl
