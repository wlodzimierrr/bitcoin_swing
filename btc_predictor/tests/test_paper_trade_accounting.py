"""BTC-165: closed paper trade accounting."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from btc_predictor.data import OhlcvBar
from btc_predictor.db.portfolio import completed_trades
from btc_predictor.portfolio.accounting import (
    PAPER_TRADE_ACCOUNTING_FEATURE_ID,
    PAPER_TRADE_ACCOUNTING_POLICY_VERSION,
    R_MULTIPLE_CONVENTION,
    TRADE_ACCOUNTING_REASON_CODES,
    TRADE_FILL_ACTIONS,
    PaperTradeAccounting,
    TradeFill,
    calculate_trade_accounting,
    funding_event_from_rate,
)


UTC = timezone.utc
START = datetime(2024, 1, 1, tzinfo=UTC)
STOP = "90000"
CONFIG = {
    "config_version": "strategy_config_v2",
    "strategy_version": "swing_v1.2",
    "parameter_set_id": "default_phase1",
}


def at(days: float) -> datetime:
    return START + timedelta(days=days)


def fill(sequence: int, days: float, action: str, quantity: str, price: str, fee="0"):
    return TradeFill(
        sequence=sequence,
        filled_at=at(days),
        action=action,
        quantity=Decimal(quantity),
        price=Decimal(price),
        fee=Decimal(fee),
        source_event_id=f"fill-{sequence}",
        execution_bar_at=at(days),
        execution_bar_timeframe="1d",
    )


def bar(days: float, high: str, low: str) -> OhlcvBar:
    timestamp = at(days)
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1d",
        open=Decimal(low),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(low),
        volume=Decimal("1"),
        provider="coinbase",
        ingested_at=timestamp + timedelta(hours=1),
    )


SIMPLE_FILLS = (
    fill(1, 0, "ENTER", "2", "100000", "200"),
    fill(2, 20, "EXIT", "2", "120000", "240"),
)
PYRAMIDED_FILLS = (
    fill(1, 0, "ENTER", "2", "100000", "200"),
    fill(2, 10, "ADD", "1", "110000", "110"),
    fill(3, 20, "TRIM", "1", "130000", "130"),
    fill(4, 28, "EXIT", "2", "125000", "250"),
)
BARS = (
    bar(0, "101000", "99000"),
    bar(5, "108000", "95000"),
    bar(12, "135000", "107000"),
    bar(25, "140000", "120000"),
)


def account(fills=SIMPLE_FILLS, **kwargs) -> PaperTradeAccounting:
    base = {
        "symbol": "BTC-USD",
        "direction": "long",
        "initial_stop_price": STOP,
        "initial_stop_source_id": "stop-1",
        "exit_reason": "STRUCTURAL_INVALIDATION",
        "exit_reason_source_id": "exit-signal-1",
        "config_metadata": CONFIG,
    }
    values = {**base, **kwargs}
    funding = values.pop("funding", None)
    if funding is not None and Decimal(funding) > 0:
        midpoint = fills[0].filled_at + (fills[-1].filled_at - fills[0].filled_at) / 2
        held = sum(
            (
                item.quantity if item.action in ("ENTER", "ADD") else -item.quantity
                for item in fills
                if item.filled_at < midpoint
            ),
            Decimal("0"),
        )
        direction = values["direction"]
        signed_rate = Decimal(funding) / (held * Decimal("100000"))
        if direction == "short":
            signed_rate = -signed_rate
        values["funding_events"] = (
            funding_event_from_rate(
                sequence=max(item.sequence for item in fills) + 1,
                event_id="funding-1",
                effective_at=midpoint,
                rate=signed_rate,
                mark_price="100000",
                position_quantity=held,
                direction=direction,
            ),
        )
    elif funding is not None:
        values["funding"] = funding
    return calculate_trade_accounting(fills, **values)


def test_metadata_and_reason_code_catalog_are_stable() -> None:
    assert PAPER_TRADE_ACCOUNTING_FEATURE_ID == "PAPER_TRADE_ACCOUNTING"
    assert PAPER_TRADE_ACCOUNTING_POLICY_VERSION == "PAPER_TRADE_ACCOUNTING_V1"
    assert R_MULTIPLE_CONVENTION == "INITIAL_PLANNED_RISK_V1"
    assert TRADE_FILL_ACTIONS == ("ENTER", "ADD", "TRIM", "EXIT")


def test_every_ticket_field_is_reported() -> None:
    result = account(PYRAMIDED_FILLS, funding="300", excursion_bars=BARS)

    for field in (
        "gross_pnl",
        "net_pnl",
        "fees",
        "funding",
        "r_multiple",
        "maximum_favourable_excursion",
        "maximum_adverse_excursion",
        "holding_days",
        "maximum_quantity",
        "add_count",
        "exit_reason",
    ):
        assert getattr(result, field) is not None, field


# --- P&L ------------------------------------------------------------------


def test_gross_and_net_pnl_on_a_single_entry_and_exit() -> None:
    result = account()

    assert result.gross_pnl == Decimal("40000")
    assert result.fees == Decimal("440")
    assert result.funding == Decimal("0")
    assert result.net_pnl == Decimal("39560")


def test_net_pnl_subtracts_fees_and_funding_exactly_once() -> None:
    result = account(funding="300")

    assert result.net_pnl == result.gross_pnl - result.fees - result.funding
    assert result.net_pnl == Decimal("39260")


def test_a_fully_closed_trade_reconciles_to_its_notionals() -> None:
    result = account(PYRAMIDED_FILLS, funding="300")

    # The identity must hold exactly, not to within a rounding artefact of the
    # weighted average, which is why the final close takes the exact remaining
    # cost basis rather than a second division.
    assert result.entry_notional == Decimal("310000")
    assert result.exit_notional == Decimal("380000")
    assert result.gross_pnl == result.exit_notional - result.entry_notional
    assert result.gross_pnl == Decimal("70000")


def test_a_short_trade_profits_when_price_falls() -> None:
    result = account(
        (
            fill(1, 0, "ENTER", "2", "100000", "200"),
            fill(2, 15, "EXIT", "2", "90000", "180"),
        ),
        direction="short",
        initial_stop_price="110000",
    )

    assert result.gross_pnl == Decimal("20000")
    assert result.net_pnl == Decimal("19620")


def test_costs_reversing_a_gross_profit_is_named() -> None:
    result = account(
        (
            fill(1, 0, "ENTER", "1", "100000", "100"),
            fill(2, 5, "EXIT", "1", "100150", "100"),
        ),
        funding="50",
    )

    # Profitable on price, loss after costs: a distinct outcome, not a plain
    # loss and not a plain win.
    assert result.gross_pnl == Decimal("150")
    assert result.net_pnl == Decimal("-100")
    assert "TRADE_ACCOUNTING_COSTS_REVERSED_A_GROSS_PROFIT" in result.reason_codes
    assert "TRADE_ACCOUNTING_NET_LOSS" in result.reason_codes


@pytest.mark.parametrize(
    ("exit_price", "expected"),
    [("120000", "TRADE_ACCOUNTING_NET_PROFIT"), ("80000", "TRADE_ACCOUNTING_NET_LOSS")],
)
def test_the_outcome_is_classified(exit_price: str, expected: str) -> None:
    result = account(
        (
            fill(1, 0, "ENTER", "2", "100000"),
            fill(2, 20, "EXIT", "2", exit_price),
        )
    )

    assert expected in result.reason_codes


def test_a_flat_trade_is_neither_profit_nor_loss() -> None:
    result = account(
        (
            fill(1, 0, "ENTER", "2", "100000"),
            fill(2, 20, "EXIT", "2", "100000"),
        )
    )

    assert result.net_pnl == Decimal("0")
    assert "TRADE_ACCOUNTING_NET_FLAT" in result.reason_codes


# --- R multiple -----------------------------------------------------------


def test_one_r_is_the_risk_planned_at_entry() -> None:
    result = account()

    # 2 units, entry 100000, initial stop 90000.
    assert result.initial_risk == Decimal("20000")
    assert result.r_multiple == result.net_pnl / result.initial_risk
    assert result.r_multiple == Decimal("1.978")


def test_the_r_denominator_ignores_a_trailed_stop_and_later_adds() -> None:
    plain = account()
    pyramided = account(PYRAMIDED_FILLS)

    # Adding increases P&L but must not retroactively change 1R, or a trade
    # could report a large R having never risked that much.
    assert plain.initial_risk == pyramided.initial_risk == Decimal("20000")
    assert pyramided.initial_quantity == Decimal("2")
    assert pyramided.r_multiple > plain.r_multiple


def test_a_stop_at_the_entry_leaves_r_undefined() -> None:
    result = account(initial_stop_price="100000")

    # Zero planned risk is not an infinite R.
    assert result.initial_risk == Decimal("0")
    assert result.r_multiple is None
    assert result.mfe_r is None
    assert "TRADE_ACCOUNTING_R_UNDEFINED" in result.reason_codes


# --- MFE and MAE ----------------------------------------------------------


def test_excursions_are_signed_peaks_of_total_trade_pnl() -> None:
    result = account(PYRAMIDED_FILLS, excursion_bars=BARS)

    # Day 25 holds 2 units against a 206666.67 basis with 26666.67 realized:
    # 2 * 140000 - 206666.67 + 26666.67 = 100000, exactly.
    assert result.maximum_favourable_excursion == Decimal("100000")
    # Day 5 holds 2 units at 100000 with nothing realized.
    assert result.maximum_adverse_excursion == Decimal("-10000")
    assert result.mfe_r == Decimal("5")
    assert result.mae_r == Decimal("-0.5")


def test_excursions_track_the_position_actually_held_at_each_bar() -> None:
    early_only = account(PYRAMIDED_FILLS, excursion_bars=BARS[:2])
    everything = account(PYRAMIDED_FILLS, excursion_bars=BARS)

    # The day-12 and day-25 bars hold more size than the first two, so adding
    # them can only widen the excursions.
    assert early_only.maximum_favourable_excursion < (
        everything.maximum_favourable_excursion
    )
    assert early_only.maximum_adverse_excursion == (
        everything.maximum_adverse_excursion
    )


def test_a_trade_that_never_went_against_you_reports_a_positive_mae() -> None:
    result = account(
        (
            fill(1, 0, "ENTER", "1", "100000"),
            fill(2, 10, "EXIT", "1", "130000"),
        ),
        excursion_bars=(bar(5, "135000", "125000"),),
    )

    # Reporting excursions as unsigned distances would hide this case entirely.
    assert result.maximum_adverse_excursion == Decimal("25000")
    assert result.maximum_adverse_excursion > 0


def test_bars_outside_the_holding_period_are_ignored() -> None:
    inside = account(excursion_bars=(bar(5, "108000", "95000"),))
    with_outside = account(
        excursion_bars=(
            bar(-3, "200000", "10000"),
            bar(5, "108000", "95000"),
            bar(60, "200000", "10000"),
        ),
    )

    assert with_outside.maximum_favourable_excursion == (
        inside.maximum_favourable_excursion
    )
    assert with_outside.maximum_adverse_excursion == inside.maximum_adverse_excursion


def test_no_bars_leaves_the_excursions_absent_rather_than_zero() -> None:
    result = account()

    assert result.maximum_favourable_excursion is None
    assert result.maximum_adverse_excursion is None
    assert result.mfe_r is None
    assert "TRADE_ACCOUNTING_NO_EXCURSION_BARS" in result.reason_codes


def test_short_excursions_are_mirrored() -> None:
    result = account(
        (
            fill(1, 0, "ENTER", "1", "100000"),
            fill(2, 10, "EXIT", "1", "90000"),
        ),
        direction="short",
        initial_stop_price="110000",
        excursion_bars=(bar(5, "105000", "85000"),),
    )

    # A short profits as price falls, so the low is favourable.
    assert result.maximum_favourable_excursion == Decimal("15000")
    assert result.maximum_adverse_excursion == Decimal("-5000")


# --- size, counts, duration ----------------------------------------------


def test_max_size_is_the_peak_open_position() -> None:
    result = account(PYRAMIDED_FILLS)

    assert result.maximum_quantity == Decimal("3")
    # Cost basis at the peak, carried without dividing so it stays exact.
    assert result.maximum_notional == Decimal("310000")


def test_a_trim_does_not_raise_max_size() -> None:
    trimmed = account(PYRAMIDED_FILLS)
    untrimmed = account(
        (
            fill(1, 0, "ENTER", "2", "100000"),
            fill(2, 10, "ADD", "1", "110000"),
            fill(3, 28, "EXIT", "3", "125000"),
        )
    )

    assert trimmed.maximum_quantity == untrimmed.maximum_quantity


def test_adds_and_trims_are_counted_separately() -> None:
    result = account(PYRAMIDED_FILLS)

    assert result.add_count == 1
    assert result.trim_count == 1
    assert account().add_count == 0


def test_holding_days_spans_first_to_last_fill() -> None:
    assert account().holding_days == Decimal("20")
    assert account(PYRAMIDED_FILLS).holding_days == Decimal("28")


def test_a_partial_day_is_fractional() -> None:
    result = account(
        (
            fill(1, 0, "ENTER", "1", "100000"),
            fill(2, 0.5, "EXIT", "1", "101000"),
        )
    )

    assert result.holding_days == Decimal("0.5")


def test_the_weighted_average_entry_covers_the_whole_trade() -> None:
    result = account(PYRAMIDED_FILLS)

    # 2 at 100000 plus 1 at 110000.
    assert result.average_entry_price == Decimal("310000") / Decimal("3")


def test_the_exit_reason_is_carried_through() -> None:
    result = account(exit_reason="HOLD_SCORE_COLLAPSE")

    assert result.exit_reason == "HOLD_SCORE_COLLAPSE"
    assert result.as_record()["exit_reason"] == "HOLD_SCORE_COLLAPSE"


# --- open positions -------------------------------------------------------


def test_a_position_still_open_is_reported_as_such() -> None:
    result = account(
        (
            fill(1, 0, "ENTER", "2", "100000", "200"),
            fill(2, 10, "TRIM", "1", "120000", "120"),
        ),
        as_of=at(20),
        exit_reason=None,
        exit_reason_source_id=None,
    )

    # The realized part is still accounted; the trade simply is not finished.
    assert result.closed is False
    assert result.gross_pnl == Decimal("20000")
    assert "TRADE_ACCOUNTING_POSITION_STILL_OPEN" in result.reason_codes


def test_an_open_position_is_not_a_completed_trade() -> None:
    result = account(
        (
            fill(1, 0, "ENTER", "2", "100000"),
            fill(2, 10, "TRIM", "1", "120000"),
        ),
        as_of=at(20),
        exit_reason=None,
        exit_reason_source_id=None,
    )

    with pytest.raises(ValueError, match="not a completed trade"):
        result.as_completed_trade_record(account_id=1, position_id=1)


# --- validation -----------------------------------------------------------


@pytest.mark.parametrize(
    ("fills", "match"),
    [
        ((), "at least one fill"),
        ((fill(1, 0, "ADD", "1", "100000"),), "first fill must be an ENTER"),
        (
            (fill(1, 0, "ENTER", "1", "100000"), fill(2, 5, "ENTER", "1", "100000")),
            "exactly one ENTER",
        ),
        (
            (fill(1, 0, "ENTER", "1", "100000"), fill(2, 5, "EXIT", "2", "120000")),
            "cannot exceed the open quantity",
        ),
        (
            (fill(1, 5, "ENTER", "1", "100000"), fill(2, 0, "EXIT", "1", "120000")),
            "non-decreasing time order",
        ),
        (
            (fill(2, 0, "ENTER", "1", "100000"), fill(1, 5, "EXIT", "1", "120000")),
            "sequences must strictly increase",
        ),
        ((fill(1, 0, "SPLIT", "1", "100000"),), "action must be one of"),
        ((fill(1, 0, "ENTER", "0", "100000"),), "quantity must be positive"),
        ((fill(1, 0, "ENTER", "1", "0"),), "price must be positive"),
        ((fill(1, 0, "ENTER", "1", "100000", "-1"),), "fee must be non-negative"),
    ],
)
def test_invalid_fill_sequences_fail_fast(fills, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        account(fills)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"direction": "flat"}, "direction must be one of"),
        ({"symbol": ""}, "symbol must be a non-empty string"),
        ({"exit_reason": "  "}, "exit_reason must be a non-empty string"),
        ({"initial_stop_price": "0"}, "initial_stop_price must be positive"),
        ({"funding": "-1"}, "use funding_events"),
    ],
)
def test_invalid_trade_arguments_fail_fast(kwargs, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        account(**kwargs)


def test_non_fill_objects_are_rejected() -> None:
    with pytest.raises(TypeError, match="TradeFill"):
        account(({"action": "ENTER"},))


# --- persistence ----------------------------------------------------------


def test_record_is_persistable_and_self_consistent() -> None:
    record = account(
        PYRAMIDED_FILLS,
        funding="300",
        excursion_bars=BARS,
        config_metadata=CONFIG,
    ).as_record()

    assert record["feature_id"] == "PAPER_TRADE_ACCOUNTING"
    assert record["r_multiple_convention"] == "INITIAL_PLANNED_RISK_V1"
    assert record["gross_pnl"] == "70000.0000000000000000000000"
    assert record["net_pnl"] == "69010.0000000000000000000000"
    assert record["r_multiple"] == "3.4505000000000000000000"
    # Serialized scale follows from the seconds division; the value is exact.
    assert record["holding_days"] == "28.0"
    assert Decimal(record["holding_days"]) == Decimal("28")
    assert record["add_count"] == 1
    assert len(record["fills"]) == 4
    assert record["config_metadata"] == CONFIG
    assert Decimal(record["net_pnl"]) == (
        Decimal(record["gross_pnl"])
        - Decimal(record["fees"])
        - Decimal(record["funding"])
    )


def test_the_record_rejects_an_inconsistent_net_pnl() -> None:
    result = account()

    with pytest.raises(ValueError, match="replayed evidence"):
        replace(result, net_pnl=Decimal("1")).as_record()


def test_completed_trade_record_matches_the_schema() -> None:
    result = account(PYRAMIDED_FILLS, funding="300")
    record = result.as_completed_trade_record(account_id=7, position_id=3)
    columns = {column.name for column in completed_trades.columns}

    assert set(record) <= columns
    assert record["entry_notional"] == Decimal("310000")
    assert record["exit_notional"] == Decimal("380000")
    assert record["realized_pnl"] == result.net_pnl
    assert record["realized_r"] == result.r_multiple
    assert record["closed_at"] >= record["opened_at"]


@pytest.mark.parametrize(
    ("account_id", "position_id"),
    [(0, 1), (1, 0), (True, 1)],
)
def test_completed_trade_identifiers_are_validated(account_id, position_id) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        account().as_completed_trade_record(
            account_id=account_id,
            position_id=position_id,
        )


def test_reason_codes_are_drawn_from_the_declared_set() -> None:
    results = [
        account(),
        account(PYRAMIDED_FILLS, excursion_bars=BARS),
        account(initial_stop_price="100000"),
        account(
            (
                fill(1, 0, "ENTER", "2", "100000"),
                fill(2, 10, "TRIM", "1", "120000"),
            ),
            as_of=at(20),
            exit_reason=None,
            exit_reason_source_id=None,
        ),
        account(
            (
                fill(1, 0, "ENTER", "1", "100000", "100"),
                fill(2, 5, "EXIT", "1", "100150", "100"),
            ),
            funding="50",
        ),
    ]

    for result in results:
        for code in result.reason_codes:
            assert code in TRADE_ACCOUNTING_REASON_CODES


def test_recomputation_is_deterministic() -> None:
    first = account(PYRAMIDED_FILLS, funding="300", excursion_bars=BARS)
    second = account(PYRAMIDED_FILLS, funding="300", excursion_bars=BARS)

    assert first.as_record() == second.as_record()
