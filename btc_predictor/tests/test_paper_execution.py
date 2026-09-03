"""BTC-223 paper execution suite.

The ticket names seven paper-execution scenarios:

    missed entry; gap through stop; multiple tranches; stop move; trim; exit;
    funding and fees

Each already has an owner suite. BTC-161 proves an untouched zone is a terminal
miss, BTC-162 that a gapped stop fills at the open, BTC-163 and BTC-164 that
adds and trims fill at the next bar's open, BTC-165 that eleven figures come
from one walk over the fills. Every one of those suites stubs the others: an
execution test invents a lifecycle, a lifecycle test invents a fill price, and
an accounting test invents both.

What no owner can see is whether a *scenario* survives the whole chain. This
suite therefore drives each named scenario through the real BTC-160 account,
BTC-161 to BTC-164 executions, the BTC-150 ledger, BTC-165 accounting and
BTC-166 persistence, and asserts three things of every one:

- the scenario's defining execution semantics still hold in composition;
- every owner agrees about the same trade -- the same quantity, the same fill,
  the same money -- with no figure recomputed on a second convention; and
- the result is deterministic and replays from its own persisted evidence.

The second is the substantive half. A defect that makes two owners disagree --
a stop sized for the quantity originally entered rather than what a trim left,
an add re-based average entry, a fee counted once in the execution and again in
the accounting -- passes every owner suite and fails here.
"""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from fractions import Fraction

import pytest

from btc_predictor.backtest import cost_profile
from btc_predictor.config import load_strategy_config
from btc_predictor.data import OhlcvBar
from btc_predictor.portfolio import (
    ADD,
    ADD_CANCELLED,
    ADD_FILLED,
    ENTER,
    ENTRY_FILLED,
    ENTRY_MISSED,
    EXIT,
    MISS,
    MISSED,
    OPEN_ADDED,
    OPEN_INITIAL,
    PENDING_ENTRY,
    STOP_FILLED,
    STOP_MOVE,
    STOP_RESTING,
    TRIM,
    TRIM_FILLED,
    AddExecutionIntent,
    EntryExecutionIntent,
    ExitExecutionIntent,
    LifecycleProvenance,
    TrimExecutionIntent,
    apply_position_event,
    build_paper_trade_lifecycle_rows,
    calculate_trade_accounting,
    calculate_trade_accounting_for_lifecycle,
    execution_costs_from_config,
    funding_event_from_rate,
    open_paper_account,
    position_event_records,
    replay_position_event_records,
    restore_position_lifecycle,
    restore_simulated_entry_execution,
    restore_simulated_exit_execution,
    restore_simulated_stop_execution,
    restore_trade_accounting,
    simulate_add_execution,
    simulate_exit_execution,
    simulate_next_bar_entry,
    simulate_trim_execution,
    start_position_lifecycle,
    stop_execution_for_position,
    trade_fill_from_execution,
    verify_lifecycle_rows,
)
from btc_predictor.risk import (
    HIGHER_LOW,
    apply_trailing_stop,
    calculate_risk_at_stop,
    calculate_trailing_stop,
    calculate_tranche_size,
    stop_advance_count,
)
from btc_predictor.signals import (
    AddRequirementsInput,
    ExitRuleInput,
    TrimRuleInput,
    evaluate_add_requirements,
    evaluate_exit_rules,
    evaluate_trim_rules,
)


CONFIG = load_strategy_config()
METADATA = CONFIG.run_metadata()
COSTS = execution_costs_from_config(CONFIG)
STRESS = cost_profile("stress", config=CONFIG)

SYMBOL = "BTC-USD"
TIMEFRAME = "1h"
HOUR = timedelta(hours=1)
START = datetime(2026, 4, 6, tzinfo=UTC)

ACCOUNT_ID = 1
POSITION_ID = 1
RECOMMENDATION_ID = 7
NAV = Decimal("5000000")

# BTC-145's whole-position notional. Every tranche quantity in this suite is
# BTC-155's allocation from it, never a hand-picked size.
FINAL_POSITION_NOTIONAL = Decimal("250000")

ENTRY_ZONE = (Decimal("99000"), Decimal("101000"))
INITIAL_STOP = Decimal("96000")


def at(hours: float) -> datetime:
    return START + timedelta(hours=hours)


def decided(hours: float) -> datetime:
    """A decision taken mid-bar, so the next full bar is the eligible one."""

    return at(hours) + timedelta(minutes=30)


def bar(
    hours: float,
    open_: str,
    *,
    high: str | None = None,
    low: str | None = None,
    close: str | None = None,
) -> OhlcvBar:
    opening = Decimal(open_)
    closing = Decimal(close) if close is not None else opening
    return OhlcvBar(
        timestamp=at(hours),
        exchange="coinbase",
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        open=opening,
        high=Decimal(high) if high is not None else max(opening, closing),
        low=Decimal(low) if low is not None else min(opening, closing),
        close=closing,
        volume=Decimal("5"),
        provider="coinbase",
        ingested_at=at(hours) + HOUR,
    )


def action_bar(hours: float, open_: str) -> OhlcvBar:
    """A bar whose open, high, low and close all differ.

    An add, trim or exit references the open. Keeping the four prices distinct
    means a reference taken from any other field changes the fill.
    """

    opening = Decimal(open_)
    return bar(
        hours,
        open_,
        high=str(opening + 900),
        low=str(opening - 700),
        close=str(opening + 300),
    )


def tranche(number: int, *, entry_price: Decimal):
    """BTC-155's allocation for one stage of the schedule."""

    return calculate_tranche_size(
        tranche_number=number,
        final_position_notional=FINAL_POSITION_NOTIONAL,
        entry_price=entry_price,
        config=CONFIG,
        config_metadata=METADATA,
    )


def entry_intent(
    *,
    hours: float = 0,
    direction: str = "long",
    quantity: Decimal | None = None,
    execution_id: str = "entry-1",
) -> EntryExecutionIntent:
    return EntryExecutionIntent(
        execution_id=execution_id,
        recommendation_id=RECOMMENDATION_ID,
        symbol=SYMBOL,
        direction=direction,
        decision_at=decided(hours),
        timeframe=TIMEFRAME,
        entry_zone_lower=ENTRY_ZONE[0],
        entry_zone_upper=ENTRY_ZONE[1],
        entry_zone_available_at=decided(hours) - timedelta(minutes=5),
        entry_zone_id="cluster-1",
        requested_quantity=(
            quantity
            if quantity is not None
            else tranche(1, entry_price=Decimal("100000")).allocation.quantity
        ),
        config_metadata=METADATA,
    )


def entry_bar(hours: float = 1, **overrides) -> OhlcvBar:
    base = {
        "open_": "100000",
        "high": "100800",
        "low": "99500",
        "close": "100600",
    }
    return bar(hours, **{**base, **overrides})


def enter(*, costs=COSTS, intent=None, execution_bar=None):
    """BTC-161 fill of the standard in-zone entry."""

    return simulate_next_bar_entry(
        intent if intent is not None else entry_intent(),
        execution_bar if execution_bar is not None else entry_bar(),
        costs=costs,
    )


def opened(execution, *, stop_price: Decimal = INITIAL_STOP):
    """Record a BTC-161 fill in the BTC-150 ledger."""

    lifecycle = start_position_lifecycle(
        symbol=SYMBOL,
        direction=execution.intent.direction,
        state=PENDING_ENTRY,
        config_metadata=METADATA,
    )
    result = apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=execution.resolved_at,
        quantity=execution.filled_quantity,
        price=execution.average_fill_price,
        stop_price=stop_price,
        reason_codes=execution.reason_codes,
        source_feature_id=execution.feature_id,
        source_record_id=execution.intent.execution_id,
    )
    assert result.accepted
    return result


def add_requirements(**overrides):
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
    if overrides:
        base = replace(base, **overrides)
    return evaluate_add_requirements(base, strategy_config=CONFIG)


def add(
    lifecycle,
    *,
    hours: float,
    open_: str,
    execution_id: str,
    requirements=None,
    costs=COSTS,
):
    """BTC-163 add, sized by BTC-155 at the price the bar actually offers."""

    reference = Decimal(open_)
    intent = AddExecutionIntent(
        execution_id=execution_id,
        position_id=POSITION_ID,
        recommendation_id=RECOMMENDATION_ID,
        symbol=SYMBOL,
        direction=lifecycle.direction,
        timeframe=TIMEFRAME,
        decision_at=decided(hours),
        average_entry_price=lifecycle.average_entry_price,
        config_metadata=METADATA,
    )
    return simulate_add_execution(
        intent,
        action_bar(hours + 1, open_),
        requirements=requirements if requirements is not None else add_requirements(),
        tranche=tranche(lifecycle.tranche_count + 1, entry_price=reference),
        costs=costs,
    )


def record_add(lifecycle, execution):
    result = apply_position_event(
        lifecycle,
        event=ADD,
        event_time=execution.resolved_at,
        quantity=execution.filled_quantity,
        price=execution.average_fill_price,
        reason_codes=execution.reason_codes,
        source_feature_id=execution.feature_id,
        source_record_id=execution.intent.execution_id,
    )
    assert result.accepted
    return result


def trim_signal(**overrides):
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


def trim(
    lifecycle,
    *,
    hours: float,
    open_: str,
    execution_id: str,
    signal=None,
    trim_fraction=None,
    costs=COSTS,
):
    intent = TrimExecutionIntent(
        execution_id=execution_id,
        position_id=POSITION_ID,
        recommendation_id=RECOMMENDATION_ID,
        symbol=SYMBOL,
        direction=lifecycle.direction,
        timeframe=TIMEFRAME,
        decision_at=decided(hours),
        average_entry_price=lifecycle.average_entry_price,
        open_quantity=lifecycle.quantity,
        config_metadata=METADATA,
        **({} if trim_fraction is None else {"trim_fraction": trim_fraction}),
    )
    return simulate_trim_execution(
        intent,
        action_bar(hours + 1, open_),
        signal=signal if signal is not None else trim_signal(),
        costs=costs,
    )


def record_trim(lifecycle, execution):
    result = apply_position_event(
        lifecycle,
        event=TRIM,
        event_time=execution.resolved_at,
        quantity=execution.filled_quantity,
        price=execution.average_fill_price,
        reason_codes=execution.reason_codes,
        source_feature_id=execution.feature_id,
        source_record_id=execution.intent.execution_id,
    )
    assert result.accepted
    return result


def exit_signal(lifecycle, *, current_price: str, hold_score: str, hours: float):
    return evaluate_exit_rules(
        ExitRuleInput(
            position_open=lifecycle.is_open,
            direction=lifecycle.direction,
            standing_stop=lifecycle.stop_price,
            current_price=Decimal(current_price),
            hold_score=Decimal(hold_score),
            regime_invalidated=False,
            data_risk_exit_required=False,
            manual_research_override=False,
        ),
        strategy_config=CONFIG,
        evaluated_at=decided(hours),
    )


def close_out(lifecycle, *, hours: float, open_: str, signal, execution_id: str, costs=COSTS):
    """BTC-158 signal executed through the shared BTC-180 exit boundary."""

    intent = ExitExecutionIntent(
        execution_id=execution_id,
        position_id=POSITION_ID,
        recommendation_id=RECOMMENDATION_ID,
        symbol=SYMBOL,
        direction=lifecycle.direction,
        timeframe=TIMEFRAME,
        decision_at=decided(hours),
        open_quantity=lifecycle.quantity,
        exit_reason=signal.exit_reasons[0],
        exit_reason_source_id=execution_id,
        config_metadata=METADATA,
    )
    return simulate_exit_execution(intent, action_bar(hours + 1, open_), costs=costs)


def record_exit(lifecycle, execution, *, reason: str):
    result = apply_position_event(
        lifecycle,
        event=EXIT,
        event_time=execution.resolved_at,
        quantity=execution.filled_quantity,
        price=execution.average_fill_price,
        reason_codes=(reason,) + execution.reason_codes,
        source_feature_id=execution.feature_id,
        source_record_id=execution.intent.execution_id,
    )
    assert result.accepted
    return result


def fills(*executions):
    return tuple(
        trade_fill_from_execution(execution, sequence=index)
        for index, execution in enumerate(executions, start=1)
    )


def account(*, costs=COSTS):
    return open_paper_account(
        account_name="btc223-paper",
        created_at=START,
        starting_nav=NAV,
        costs=costs,
        config=CONFIG,
    )


def settle(accounting, executions, *, funding_events=(), costs=COSTS):
    """Walk one trade onto a BTC-160 account exactly as BTC-180 does.

    Every leg pays its own fee, every funding event is applied signed, and the
    trade settles its gross P&L once. Nothing here recomputes a figure the
    executions already own.
    """

    paper = account(costs=costs)
    for execution in executions:
        paper = paper.charge_fee(execution.notional)
    for event in funding_events:
        paper = paper.apply_funding_cost(event.funding_cost)
    return paper.settle_realized_pnl(accounting.gross_pnl)


def provenance():
    return LifecycleProvenance.from_config(
        CONFIG,
        recommendation_id=RECOMMENDATION_ID,
    )


def ledger_risk(lifecycle, *, nav=NAV):
    return calculate_risk_at_stop(
        [
            {
                "tranche_id": str(item.tranche_number),
                "quantity": item.quantity,
                "entry_price": item.entry_price,
            }
            for item in lifecycle.tranches
        ],
        stop_price=lifecycle.stop_price,
        nav=nav,
        direction=lifecycle.direction,
        config=CONFIG,
    )


# --- shared execution timing ---------------------------------------------


def test_every_leg_fills_on_the_first_bar_after_its_decision_at_that_open() -> None:
    # Rulebook 32 rule 12 at the execution boundary: a decision taken inside a
    # forming bar can only be executed on the next full bar, and the first
    # price that bar offers is its open. Every scenario in this suite depends
    # on that, and each of the four legs is stated here once.
    entry_execution = enter()
    lifecycle = opened(entry_execution)
    addition = add(lifecycle, hours=2, open_="105000", execution_id="add-1")
    lifecycle = record_add(lifecycle, addition)
    reduction = trim(lifecycle, hours=4, open_="110000", execution_id="trim-1")
    lifecycle = record_trim(lifecycle, reduction)
    signal = exit_signal(lifecycle, current_price="112000", hold_score="35", hours=6)
    closing = close_out(
        lifecycle,
        hours=6,
        open_="112000",
        signal=signal,
        execution_id="exit-1",
    )

    for execution, reference, side, decision_hour in (
        (entry_execution, Decimal("100000"), "buy", 0),
        (addition, Decimal("105000"), "buy", 2),
        (reduction, Decimal("110000"), "sell", 4),
        (closing, Decimal("112000"), "sell", 6),
    ):
        execution_bar = execution.execution_bar
        assert execution.intent.decision_at == decided(decision_hour)
        assert execution.intent.decision_at < execution_bar.timestamp
        assert execution_bar.timestamp == at(decision_hour + 1)
        assert execution_bar.timestamp == execution.intent.eligible_bar_at

        # Every other price the bar offered is a different number, so a fill
        # taken from the close, the high or the low would not survive this.
        assert execution.reference_price == reference == execution_bar.open
        assert len(
            {
                execution_bar.open,
                execution_bar.high,
                execution_bar.low,
                execution_bar.close,
            }
        ) == 4
        assert execution.average_fill_price == COSTS.fill_price(reference, side=side)
        assert execution.intent.side == side
        assert execution.resolved_at == execution_bar.timestamp + HOUR


# --- scenario 1: missed entry --------------------------------------------


def missed_entry():
    """The one eligible bar trades entirely above the zone."""

    return simulate_next_bar_entry(
        entry_intent(),
        bar(1, "102000", high="103000", low="101500", close="102500"),
        costs=COSTS,
    )


def test_a_missed_entry_fills_nothing_and_costs_the_account_nothing() -> None:
    # Rulebook 25 lets the system miss trades. The composition property is that
    # a miss is free: with no fill there is no notional, so no fee, no slippage
    # and no cash movement anywhere in BTC-160.
    execution = missed_entry()

    assert execution.status == ENTRY_MISSED
    assert execution.reason_codes == (
        "ENTRY_ZONE_NOT_TOUCHED",
        "ENTRY_EXECUTION_MISSED",
        "ENTRY_DO_NOT_CHASE",
    )
    assert execution.average_fill_price is None
    assert execution.reference_price is None
    assert execution.filled_quantity == 0
    assert execution.notional == 0
    assert execution.fee == 0
    assert execution.slippage_cost == 0

    paper = account().charge_fee(execution.notional)
    assert paper.cash == NAV
    assert paper.fees_paid == 0
    assert paper.available_cash == NAV


def test_a_missed_entry_leaves_no_position_and_no_completed_trade() -> None:
    execution = missed_entry()
    lifecycle = apply_position_event(
        start_position_lifecycle(
            symbol=SYMBOL,
            direction="long",
            state=PENDING_ENTRY,
            config_metadata=METADATA,
        ),
        event=MISS,
        event_time=execution.resolved_at,
        reason_codes=execution.reason_codes,
        source_feature_id=execution.feature_id,
        source_record_id=execution.intent.execution_id,
    )

    assert lifecycle.accepted
    assert lifecycle.state == MISSED
    assert lifecycle.is_terminal
    assert lifecycle.tranches == ()
    assert lifecycle.quantity == 0
    assert lifecycle.average_entry_price is None
    assert lifecycle.persisted_status == "missed"

    # There is no trade to account for, and BTC-165 says so rather than
    # inventing a zero-quantity one.
    with pytest.raises(ValueError, match="at least one fill"):
        calculate_trade_accounting(
            (),
            symbol=SYMBOL,
            direction="long",
            initial_stop_price=INITIAL_STOP,
            initial_stop_source_id="entry-1",
            exit_reason=None,
            config_metadata=METADATA,
        )

    rows = build_paper_trade_lifecycle_rows(
        provenance=provenance(),
        account_id=ACCOUNT_ID,
        position_id=POSITION_ID,
        executions=(execution,),
        lifecycle=lifecycle,
    )
    verify_lifecycle_rows(rows)

    assert rows.complete is False
    assert "LIFECYCLE_PERSISTENCE_TRADE_NOT_CLOSED" in rows.reason_codes
    assert rows.completed_trade is None
    order = rows.orders[0]
    assert order["status"] == ENTRY_MISSED
    assert order["action"] == "MISSED"
    assert order["filled_at"] is None
    assert order["filled_quantity"] == 0
    assert order["average_fill_price"] is None
    assert order["requested_quantity"] == execution.intent.requested_quantity
    assert [row["action"] for row in rows.events] == ["MISSED"]


def test_a_missed_entry_is_never_chased_by_a_later_bar_or_a_later_entry() -> None:
    # Rulebook 32 rule 8. The miss is terminal in both owners: the execution
    # refuses a bar that is not its one eligible bar, and the ledger refuses a
    # later fill of the position the miss closed.
    intent = entry_intent()
    with pytest.raises(ValueError, match="first eligible full bar"):
        simulate_next_bar_entry(intent, entry_bar(3), costs=COSTS)

    execution = missed_entry()
    lifecycle = apply_position_event(
        start_position_lifecycle(
            symbol=SYMBOL,
            direction="long",
            state=PENDING_ENTRY,
            config_metadata=METADATA,
        ),
        event=MISS,
        event_time=execution.resolved_at,
    )
    chased = apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=at(4),
        quantity="1",
        price="100000",
        stop_price=INITIAL_STOP,
    )

    assert chased.accepted is False
    assert "POSITION_STATE_TERMINAL" in chased.reason_codes
    assert chased.state == MISSED
    assert chased.tranches == ()
    assert chased.quantity == 0


def test_entry_and_stop_answer_touch_under_the_same_comparison_policy() -> None:
    """One "did price reach this level" question, one policy across the epic.

    BTC-162's review moved stop touch and gap boundaries onto
    ``DECISION_COMPARISON_V1``. An entry zone asks the identical question, so
    a high inside the decision band of the zone boundary must be a touch here
    too -- otherwise the same tick is a fill for a stop and a terminal miss
    for an entry. A real cent is still outside the band and still a miss.
    """

    zone_lower = ENTRY_ZONE[0]
    # Inside the band: 1e-12 relative at 99,000 is about 1e-7 of a dollar.
    inside_band = zone_lower - Decimal("0.00000001")
    a_cent_below = zone_lower - Decimal("0.01")

    touched = enter(
        execution_bar=entry_bar(
            1, open_="98950", high=str(inside_band), low="98900", close="98960"
        )
    )
    missed = enter(
        execution_bar=entry_bar(
            1, open_="98950", high=str(a_cent_below), low="98900", close="98960"
        )
    )

    assert touched.filled is True
    assert "ENTRY_ZONE_TOUCHED" in touched.reason_codes
    assert missed.missed is True
    assert "ENTRY_ZONE_NOT_TOUCHED" in missed.reason_codes

    # The mirrored stop boundary, resolved by the same policy.
    position = opened(enter())
    stop_touched = stop_execution_for_position(
        position,
        bar(
            2,
            "97000",
            high="97200",
            low=str(INITIAL_STOP + Decimal("0.00000001")),
            close="97100",
        ),
        costs=COSTS,
        execution_id="stop-band",
        position_id=POSITION_ID,
    )
    stop_resting = stop_execution_for_position(
        position,
        bar(
            2,
            "97000",
            high="97200",
            low=str(INITIAL_STOP + Decimal("0.01")),
            close="97100",
        ),
        costs=COSTS,
        execution_id="stop-cent",
        position_id=POSITION_ID,
    )

    assert stop_touched.filled is True
    assert stop_resting.resting is True


def test_a_missed_entry_is_deterministic_and_replays_from_its_record() -> None:
    first = missed_entry()
    second = missed_entry()

    assert first.as_record() == second.as_record()
    assert restore_simulated_entry_execution(first.as_record()) == first


# --- scenario 2: gap through stop ----------------------------------------


def stopped_out(execution_bar, *, execution_id: str, entry=None, lifecycle=None):
    """Run one stop-out end to end: execution, ledger closure, accounting."""

    entry_execution = entry if entry is not None else enter()
    position = lifecycle if lifecycle is not None else opened(entry_execution)
    stop = stop_execution_for_position(
        position,
        execution_bar,
        costs=COSTS,
        execution_id=execution_id,
        position_id=POSITION_ID,
    )
    closed = apply_position_event(
        position,
        event=EXIT,
        event_time=stop.resolved_at,
        quantity=stop.filled_quantity,
        price=stop.average_fill_price,
        reason_codes=("STRUCTURAL_STOP",) + stop.reason_codes,
        source_feature_id=stop.feature_id,
        source_record_id=stop.intent.execution_id,
    )
    assert closed.accepted
    accounting = calculate_trade_accounting_for_lifecycle(
        closed,
        fills(entry_execution, stop),
    )
    return entry_execution, stop, closed, accounting


def test_a_gapped_stop_fills_at_the_open_and_a_touched_stop_at_the_stop() -> None:
    # BTC-162 decides this on the bar's open, not its low. Both bars trade
    # below the stop; only the gapped one never offered the stop price.
    _, touched, _, _ = stopped_out(
        bar(3, "97000", high="97500", low="95000", close="95500"),
        execution_id="stop-touched",
    )
    _, gapped, _, _ = stopped_out(
        bar(3, "92000", high="92500", low="91000", close="91500"),
        execution_id="stop-gapped",
    )

    assert touched.gapped is False
    assert touched.reference_price == INITIAL_STOP
    assert "STOP_FILL_AT_STOP_PRICE" in touched.reason_codes

    assert gapped.gapped is True
    assert gapped.reference_price == Decimal("92000")
    assert "STOP_FILL_AT_GAP_OPEN" in gapped.reason_codes
    assert gapped.average_fill_price < touched.average_fill_price


def test_a_gap_through_the_stop_reaches_the_final_r_multiple() -> None:
    # BTC-146 sized this position assuming a fill at the stop, so 1R of loss is
    # the plan. The composition property is that the breach is not absorbed
    # anywhere: the gap's extra loss shows up in the trade's realized R.
    _, touched, _, touched_accounting = stopped_out(
        bar(3, "97000", high="97500", low="95000", close="95500"),
        execution_id="stop-touched",
    )
    _, gapped, _, gapped_accounting = stopped_out(
        bar(3, "92000", high="92500", low="91000", close="91500"),
        execution_id="stop-gapped",
    )

    # The R denominator BTC-165 uses is the risk BTC-162 planned at the stop.
    assert touched_accounting.initial_risk == touched.planned_downside_risk
    assert gapped_accounting.initial_risk == gapped.planned_downside_risk

    assert touched_accounting.r_multiple < -1
    assert gapped_accounting.r_multiple < touched_accounting.r_multiple
    assert gapped_accounting.r_multiple < -2

    # Costs alone already breach a plan measured at the stop price, and a gap
    # breaches it far more; both say so rather than reporting a clean -1R.
    for execution in (touched, gapped):
        assert "STOP_LOSS_EXCEEDED_PLANNED_RISK" in execution.reason_codes
        assert execution.excess_loss == execution.realized_loss - execution.planned_downside_risk


def test_a_stop_out_reconciles_execution_ledger_accounting_and_cash() -> None:
    entry_execution, stop, closed, accounting = stopped_out(
        bar(3, "92000", high="92500", low="91000", close="91500"),
        execution_id="stop-gapped",
    )

    assert closed.state == "CLOSED"
    assert closed.quantity == 0
    assert closed.closed_at == stop.resolved_at

    # One trade, one set of numbers: the execution's own P&L is the accounting's
    # gross, and the accounting's net is that less the entry fee it also paid.
    assert accounting.gross_pnl == stop.gross_pnl
    assert accounting.net_pnl == stop.net_pnl - entry_execution.fee
    assert accounting.fees == entry_execution.fee + stop.fee
    assert accounting.funding == 0
    assert accounting.exit_notional == stop.filled_quantity * stop.average_fill_price
    assert accounting.gross_pnl == accounting.exit_notional - accounting.entry_notional

    # The stop's own reason codes reach the persisted exit reason rather than
    # being summarised into one opaque label.
    assert accounting.exit_reason.startswith("STRUCTURAL_STOP|")
    assert "STOP_FILL_AT_GAP_OPEN" in accounting.exit_reason
    assert accounting.exit_reason_source_id == "stop-gapped"

    paper = settle(accounting, (entry_execution, stop))
    assert paper.fees_paid == accounting.fees
    assert paper.cash == NAV + accounting.net_pnl
    assert paper.realized_pnl == accounting.gross_pnl


def test_an_untouched_stop_keeps_resting_and_changes_nothing() -> None:
    # Unlike a missed entry, an untouched stop is not terminal: it still works.
    entry_execution = enter()
    lifecycle = opened(entry_execution)
    resting = stop_execution_for_position(
        lifecycle,
        bar(3, "101000", high="101500", low="99000", close="100200"),
        costs=COSTS,
        execution_id="stop-resting",
        position_id=POSITION_ID,
    )

    assert resting.status == STOP_RESTING
    assert resting.triggered is False
    assert resting.filled_quantity == 0
    assert resting.fee == 0
    assert resting.gross_pnl is None
    assert "STOP_EXECUTION_RESTING" in resting.reason_codes

    order = resting.as_order_record(account_id=ACCOUNT_ID, position_id=POSITION_ID)
    assert order["status"] == STOP_RESTING
    assert order["filled_at"] is None

    paper = account().charge_fee(resting.notional)
    assert paper.cash == NAV
    assert lifecycle.state == OPEN_INITIAL
    assert lifecycle.quantity == entry_execution.filled_quantity


def test_a_stop_out_is_deterministic_and_replays_from_its_record() -> None:
    execution_bar = bar(3, "92000", high="92500", low="91000", close="91500")
    _, first, _, first_accounting = stopped_out(execution_bar, execution_id="stop-gapped")
    _, second, _, second_accounting = stopped_out(execution_bar, execution_id="stop-gapped")

    assert first.as_record() == second.as_record()
    assert first_accounting.as_record() == second_accounting.as_record()
    assert restore_simulated_stop_execution(first.as_record()) == first


# --- scenario 3: multiple tranches ---------------------------------------


def pyramided():
    """ENTER plus the two adds BTC-155's schedule allows, in ledger order."""

    entry_execution = enter()
    lifecycle = opened(entry_execution)
    first = add(lifecycle, hours=2, open_="105000", execution_id="add-1")
    lifecycle = record_add(lifecycle, first)
    second = add(lifecycle, hours=4, open_="120000", execution_id="add-2")
    lifecycle = record_add(lifecycle, second)
    return (entry_execution, first, second), lifecycle


def test_every_tranche_is_sized_by_the_schedule_and_fills_above_the_average() -> None:
    entry_execution = enter()
    lifecycle = opened(entry_execution)
    averages = [lifecycle.average_entry_price]

    assert entry_execution.status == ENTRY_FILLED
    assert entry_execution.filled_quantity == tranche(
        1,
        entry_price=Decimal("100000"),
    ).allocation.quantity

    for index, price in enumerate(("105000", "120000"), start=1):
        execution = add(
            lifecycle,
            hours=index * 2,
            open_=price,
            execution_id=f"add-{index}",
        )
        assert execution.status == ADD_FILLED
        # BTC-155 owns the size; the execution never invents one.
        allocation = tranche(
            lifecycle.tranche_count + 1,
            entry_price=Decimal(price),
        ).allocation
        assert execution.tranche_number == allocation.tranche_number
        assert execution.filled_quantity == allocation.quantity
        # Rulebook 32 rule 2 at the fill, not only at the decision.
        assert execution.average_fill_price > lifecycle.average_entry_price
        lifecycle = record_add(lifecycle, execution)
        averages.append(lifecycle.average_entry_price)

    assert lifecycle.tranche_count == 3
    assert lifecycle.state == OPEN_ADDED
    assert averages == sorted(averages)


def test_the_schedule_caps_the_book_and_a_refused_add_costs_nothing() -> None:
    _, lifecycle = pyramided()
    before = (
        lifecycle.state,
        lifecycle.tranches,
        lifecycle.quantity,
        lifecycle.average_entry_price,
    )

    refused = add(lifecycle, hours=6, open_="125000", execution_id="add-3")

    assert refused.status == ADD_CANCELLED
    assert refused.reason_codes == (
        "ADD_EXECUTION_NO_TRANCHE_ALLOCATION",
        "TRANCHE_SIZING_SCHEDULE_EXHAUSTED",
        "ADD_EXECUTION_CANCELLED",
    )
    assert refused.filled_quantity == 0
    assert refused.notional == 0
    assert refused.fee == 0
    assert account().charge_fee(refused.notional).cash == NAV

    assert (
        lifecycle.state,
        lifecycle.tranches,
        lifecycle.quantity,
        lifecycle.average_entry_price,
    ) == before


def test_a_gate_blocked_add_records_the_allocation_it_declined() -> None:
    # BTC-154 refuses; BTC-155 had already sized the tranche. The execution
    # keeps both facts -- the gate's own reason codes and the quantity that
    # would have been bought -- while filling nothing and moving no cash.
    entry_execution = enter()
    lifecycle = opened(entry_execution)
    before = (lifecycle.state, lifecycle.tranches, lifecycle.quantity)

    blocked = add(
        lifecycle,
        hours=2,
        open_="105000",
        execution_id="add-blocked",
        requirements=add_requirements(new_structural_confirmation=False),
    )

    assert blocked.status == ADD_CANCELLED
    assert blocked.reason_codes[0] == "ADD_EXECUTION_BLOCKED_BY_REQUIREMENTS"
    assert blocked.reason_codes[-1] == "ADD_EXECUTION_CANCELLED"
    assert "ADD_REQUIREMENTS_NO_NEW_STRUCTURE" in blocked.reason_codes

    # The allocation is reported, and none of it was bought.
    assert blocked.requested_quantity == tranche(
        2,
        entry_price=Decimal("105000"),
    ).allocation.quantity
    assert blocked.filled_quantity == 0
    assert blocked.average_fill_price is None
    assert blocked.notional == 0
    assert blocked.fee == 0
    assert account().charge_fee(blocked.notional).cash == NAV

    order = blocked.as_order_record(account_id=ACCOUNT_ID, position_id=POSITION_ID)
    assert order["status"] == ADD_CANCELLED
    assert order["filled_quantity"] == 0
    assert order["requested_quantity"] == blocked.requested_quantity
    assert order["filled_at"] is None

    assert (lifecycle.state, lifecycle.tranches, lifecycle.quantity) == before


def test_the_stop_covers_the_whole_book_not_the_tranche_that_opened_it() -> None:
    executions, lifecycle = pyramided()
    entry_execution = executions[0]

    stop = stop_execution_for_position(
        lifecycle,
        bar(6, "97000", high="97500", low="95000", close="95500"),
        costs=COSTS,
        execution_id="stop-1",
        position_id=POSITION_ID,
    )

    assert stop.intent.open_quantity == lifecycle.quantity
    assert stop.intent.open_quantity > entry_execution.filled_quantity
    assert len(stop.intent.tranches) == 3
    assert stop.filled_quantity == lifecycle.quantity

    # Risk at the stop is the per-tranche sum, and BTC-146 reading the same
    # ledger agrees with the execution that carries it.
    expected = sum(
        (
            item.quantity * max(item.entry_price - INITIAL_STOP, Decimal("0"))
            for item in lifecycle.tranches
        ),
        Decimal("0"),
    )
    risk = ledger_risk(lifecycle)
    assert stop.planned_downside_risk == expected
    assert risk.risk_at_stop == expected
    assert risk.within_maximum is True


def test_a_pyramided_trade_accounts_for_every_tranche_once() -> None:
    executions, lifecycle = pyramided()
    entry_execution, first, second = executions

    stop = stop_execution_for_position(
        lifecycle,
        bar(6, "97000", high="97500", low="95000", close="95500"),
        costs=COSTS,
        execution_id="stop-1",
        position_id=POSITION_ID,
    )
    closed = apply_position_event(
        lifecycle,
        event=EXIT,
        event_time=stop.resolved_at,
        quantity=stop.filled_quantity,
        price=stop.average_fill_price,
        reason_codes=("STRUCTURAL_STOP",) + stop.reason_codes,
        source_feature_id=stop.feature_id,
        source_record_id=stop.intent.execution_id,
    )
    accounting = calculate_trade_accounting_for_lifecycle(
        closed,
        fills(entry_execution, first, second, stop),
    )

    assert accounting.add_count == 2
    assert accounting.trim_count == 0
    assert accounting.maximum_quantity == lifecycle.quantity
    assert accounting.average_entry_price == lifecycle.average_entry_price
    assert accounting.entry_notional == sum(
        (item.quantity * item.entry_price for item in lifecycle.tranches),
        Decimal("0"),
    )
    assert accounting.maximum_entry_notional == accounting.entry_notional
    assert accounting.fees == entry_execution.fee + first.fee + second.fee + stop.fee
    assert accounting.gross_pnl == accounting.exit_notional - accounting.entry_notional

    # BTC-162 marks the whole quantity against the weighted average entry;
    # BTC-165 differences the exact cash flows. With three tranches the average
    # does not terminate, so the two agree to Decimal's context precision
    # rather than bit-for-bit. The exact identity is pinned on the
    # single-tranche stop-out, where the average is a fill price.
    assert abs(accounting.gross_pnl - stop.gross_pnl) < Decimal("0.000000001")

    paper = settle(accounting, (entry_execution, first, second, stop))
    assert paper.fees_paid == accounting.fees
    assert paper.cash == NAV + accounting.net_pnl


# --- scenario 4: stop move -----------------------------------------------


def trail(
    lifecycle,
    *,
    structure_price: str,
    hours: float,
    structure_id: str,
    current_price: str = "103000",
):
    """One BTC-156 evaluation against the ledger's own standing stop."""

    return calculate_trailing_stop(
        direction=lifecycle.direction,
        previous_stop=lifecycle.stop_price,
        structure_price=structure_price,
        buffer=Decimal("500"),
        advance_count=stop_advance_count(lifecycle),
        current_price=Decimal(current_price),
        config_metadata=METADATA,
        evaluated_at=decided(hours),
        structure_id=structure_id,
        structure_source_feature_id="ENTRY_TRIGGER_HIGHER_LOW",
        structure_type=HIGHER_LOW,
        structure_level_timestamp=at(hours),
        structure_detected_at=decided(hours),
    )


def trailed():
    """Enter, then ratchet the stop above the entry mid-bar."""

    entry_execution = enter()
    lifecycle = opened(entry_execution)
    result = trail(lifecycle, structure_price="101500", hours=3, structure_id="hl-1")
    moved = apply_trailing_stop(lifecycle, result, event_time=decided(3))
    return entry_execution, result, moved


def test_the_stop_execution_reads_the_stop_the_ledger_now_carries() -> None:
    entry_execution, result, moved = trailed()

    assert result.advanced is True
    assert result.stop_price == Decimal("101000")
    assert moved.stop_price == result.stop_price
    assert stop_advance_count(moved) == 1

    stop = stop_execution_for_position(
        moved,
        bar(4, "101500", high="102000", low="100800", close="101200"),
        costs=COSTS,
        execution_id="stop-1",
        position_id=POSITION_ID,
    )

    # Not the entry stop, and not a stop the caller restated.
    assert stop.intent.stop_price == moved.stop_price
    assert stop.intent.stop_price != INITIAL_STOP
    assert stop.intent.average_entry_price == entry_execution.average_fill_price
    assert stop.reference_price == moved.stop_price
    assert stop.status == STOP_FILLED


def test_a_stop_moved_during_a_bar_cannot_fill_on_that_bar() -> None:
    # The move is timed at 03:30. The 03:00 bar's low is already history, so
    # letting the new stop fill on it would be a retroactive execution.
    _, _, moved = trailed()

    with pytest.raises(ValueError, match="must not precede the stop's first eligible bar"):
        stop_execution_for_position(
            moved,
            bar(3, "101500", high="102000", low="100500", close="101800"),
            costs=COSTS,
            execution_id="stop-early",
            position_id=POSITION_ID,
        )


def test_a_loosening_trail_is_held_and_the_tighter_stop_still_governs() -> None:
    _, _, moved = trailed()

    loosening = trail(moved, structure_price="97000", hours=5, structure_id="hl-2")
    held = apply_trailing_stop(moved, loosening, event_time=decided(5))

    assert loosening.advanced is False
    assert loosening.stop_price == moved.stop_price
    assert "TRAILING_STOP_HELD" in loosening.reason_codes
    assert held is moved

    stop = stop_execution_for_position(
        held,
        bar(6, "101500", high="102000", low="100800", close="101200"),
        costs=COSTS,
        execution_id="stop-1",
        position_id=POSITION_ID,
    )
    assert stop.intent.stop_price == Decimal("101000")


def test_a_ratcheted_stop_protects_profit_without_inflating_r() -> None:
    # Rulebook 22 lets the stop ratchet into profit; BTC-165's
    # INITIAL_PLANNED_RISK_V1 keeps 1R the risk actually taken at entry. A
    # trade that never risked more than 4050 must not report a large R because
    # its stop travelled.
    entry_execution, _, moved = trailed()
    stop = stop_execution_for_position(
        moved,
        bar(4, "101500", high="102000", low="100800", close="101200"),
        costs=COSTS,
        execution_id="stop-1",
        position_id=POSITION_ID,
    )
    closed = apply_position_event(
        moved,
        event=EXIT,
        event_time=stop.resolved_at,
        quantity=stop.filled_quantity,
        price=stop.average_fill_price,
        reason_codes=("STRUCTURAL_STOP",) + stop.reason_codes,
        source_feature_id=stop.feature_id,
        source_record_id=stop.intent.execution_id,
    )
    accounting = calculate_trade_accounting_for_lifecycle(
        closed,
        fills(entry_execution, stop),
    )

    # A stop above the entry cannot lose: BTC-146's floored convention reports
    # zero downside, and the planned outcome is a gain.
    assert stop.planned_downside_risk == 0
    assert stop.planned_gross_pnl > 0
    assert "STOP_LOSS_EXCEEDED_PLANNED_RISK" not in stop.reason_codes

    assert accounting.r_multiple_convention == "INITIAL_PLANNED_RISK_V1"
    assert accounting.initial_stop_price == INITIAL_STOP
    assert accounting.initial_risk == entry_execution.filled_quantity * (
        entry_execution.average_fill_price - INITIAL_STOP
    )
    assert accounting.gross_pnl == stop.gross_pnl
    assert accounting.net_pnl == stop.net_pnl - entry_execution.fee
    assert accounting.net_pnl > 0
    assert accounting.r_multiple == accounting.net_pnl / accounting.initial_risk
    assert accounting.r_multiple < 1

    paper = settle(accounting, (entry_execution, stop))
    assert paper.cash == NAV + accounting.net_pnl


def test_a_refused_stop_move_leaves_the_standing_stop_untouched() -> None:
    _, _, moved = trailed()
    before = moved.stop_price

    widened = apply_position_event(
        moved,
        event=STOP_MOVE,
        event_time=at(5),
        stop_price="99000",
    )

    assert widened.accepted is False
    assert "POSITION_STATE_STOP_WOULD_WIDEN" in widened.reason_codes
    assert widened.stop_price == before
    assert stop_advance_count(widened) == 1


# --- scenario 5: trim ----------------------------------------------------


def test_a_trim_realizes_the_same_money_the_accounting_attributes_to_it() -> None:
    # BTC-164 marks the trimmed quantity against the ledger's average entry;
    # BTC-165 removes the pro-rata cost basis. On one tranche the two are the
    # same arithmetic, and a trim that re-based the average would break it.
    entry_execution = enter()
    lifecycle = opened(entry_execution)

    execution = trim(lifecycle, hours=3, open_="110000", execution_id="trim-1")
    trimmed = record_trim(lifecycle, execution)
    accounting = calculate_trade_accounting_for_lifecycle(
        trimmed,
        fills(entry_execution, execution),
        as_of=execution.resolved_at,
    )

    assert execution.status == TRIM_FILLED
    assert "TRIM_EXECUTION_REALIZED_PROFIT" in execution.reason_codes
    assert accounting.trim_count == 1
    assert accounting.gross_pnl == execution.realized_pnl + execution.fee
    assert "TRADE_ACCOUNTING_POSITION_STILL_OPEN" in accounting.reason_codes


def test_a_trim_leaves_the_average_entry_and_the_tranche_ledger_alone() -> None:
    entry_execution = enter()
    lifecycle = opened(entry_execution)
    first = add(lifecycle, hours=2, open_="105000", execution_id="add-1")
    lifecycle = record_add(lifecycle, first)
    before = lifecycle.average_entry_price

    execution = trim(lifecycle, hours=4, open_="110000", execution_id="trim-1")
    trimmed = record_trim(lifecycle, execution)

    # Pro-rata across both tranches: less of each, at the price each opened.
    assert trimmed.average_entry_price == before
    assert trimmed.tranche_count == 2
    assert [item.entry_price for item in trimmed.tranches] == [
        item.entry_price for item in lifecycle.tranches
    ]
    assert trimmed.quantity == execution.remaining_quantity
    assert trimmed.quantity < lifecycle.quantity
    assert trimmed.state == OPEN_ADDED


def test_after_a_trim_the_stop_covers_only_what_is_left() -> None:
    # The partial-position property: a stop sized for what was entered would
    # sell quantity the position no longer holds.
    entry_execution = enter()
    lifecycle = opened(entry_execution)
    execution = trim(lifecycle, hours=3, open_="110000", execution_id="trim-1")
    trimmed = record_trim(lifecycle, execution)

    stop = stop_execution_for_position(
        trimmed,
        bar(5, "97000", high="97500", low="95000", close="95500"),
        costs=COSTS,
        execution_id="stop-1",
        position_id=POSITION_ID,
    )

    assert stop.intent.open_quantity == execution.remaining_quantity
    assert stop.intent.open_quantity < entry_execution.filled_quantity
    assert stop.filled_quantity == execution.remaining_quantity
    assert stop.planned_downside_risk == execution.remaining_quantity * (
        entry_execution.average_fill_price - INITIAL_STOP
    )


def test_a_trim_may_never_become_a_full_exit() -> None:
    # BTC-158 owns the decision to close, with its own rules. Both owners
    # refuse to let a trim quietly become one.
    entry_execution = enter()
    lifecycle = opened(entry_execution)

    whole = trim(
        lifecycle,
        hours=3,
        open_="110000",
        execution_id="trim-whole",
        trim_fraction=Decimal("1"),
    )
    assert whole.status == "cancelled"
    assert whole.reason_codes == (
        "TRIM_EXECUTION_NOT_PARTIAL",
        "TRIM_EXECUTION_CANCELLED",
    )
    assert whole.filled_quantity == 0
    assert whole.remaining_quantity == lifecycle.quantity

    refused = apply_position_event(
        lifecycle,
        event=TRIM,
        event_time=at(4),
        quantity=lifecycle.quantity,
        price="110000",
    )
    assert refused.accepted is False
    assert "POSITION_STATE_TRIM_NOT_PARTIAL" in refused.reason_codes
    assert refused.quantity == lifecycle.quantity


def test_an_unsignalled_trim_never_fills_and_costs_nothing() -> None:
    entry_execution = enter()
    lifecycle = opened(entry_execution)

    execution = trim(
        lifecycle,
        hours=3,
        open_="110000",
        execution_id="trim-quiet",
        signal=trim_signal(
            hold_score=Decimal("80"),
            current_flow_score=Decimal("70"),
        ),
    )

    assert execution.status == "cancelled"
    assert "TRIM_EXECUTION_NOT_SIGNALLED" in execution.reason_codes
    assert execution.filled_quantity == 0
    assert execution.fee == 0
    assert account().charge_fee(execution.notional).cash == NAV


def test_a_defensive_trim_settles_the_loss_it_actually_locked_in() -> None:
    # Rulebook 20's 40-50 band trims a position that is losing. Reporting that
    # as profit taken would misstate the trade, and the account must receive
    # the negative figure, not its magnitude.
    entry_execution = enter()
    lifecycle = opened(entry_execution)

    execution = trim(lifecycle, hours=3, open_="97000", execution_id="trim-loss")

    assert execution.status == TRIM_FILLED
    assert "TRIM_EXECUTION_REALIZED_LOSS" in execution.reason_codes
    assert execution.realized_pnl < 0

    paper = account().charge_fee(execution.notional)
    paper = paper.settle_realized_pnl(execution.realized_pnl + execution.fee)
    assert paper.realized_pnl == execution.realized_pnl + execution.fee
    assert paper.cash == NAV + execution.realized_pnl


def test_a_trimmed_trade_closes_with_both_reductions_in_one_accounting() -> None:
    entry_execution = enter()
    lifecycle = opened(entry_execution)
    reduction = trim(lifecycle, hours=3, open_="110000", execution_id="trim-1")
    trimmed = record_trim(lifecycle, reduction)

    signal = exit_signal(trimmed, current_price="108000", hold_score="35", hours=5)
    closing = close_out(
        trimmed,
        hours=5,
        open_="108000",
        signal=signal,
        execution_id="exit-1",
    )
    closed = record_exit(trimmed, closing, reason=signal.exit_reasons[0])
    accounting = calculate_trade_accounting_for_lifecycle(
        closed,
        fills(entry_execution, reduction, closing),
    )

    assert accounting.closed is True
    assert accounting.trim_count == 1
    assert accounting.exit_notional == (
        reduction.filled_quantity * reduction.average_fill_price
        + closing.filled_quantity * closing.average_fill_price
    )
    assert accounting.gross_pnl == accounting.exit_notional - accounting.entry_notional
    assert accounting.fees == entry_execution.fee + reduction.fee + closing.fee
    assert accounting.maximum_quantity == entry_execution.filled_quantity

    paper = settle(accounting, (entry_execution, reduction, closing))
    assert paper.cash == NAV + accounting.net_pnl


# --- scenario 6: exit ----------------------------------------------------


def signalled_exit(*, hours: float = 3, open_: str = "108000"):
    entry_execution = enter()
    lifecycle = opened(entry_execution)
    signal = exit_signal(
        lifecycle,
        current_price=open_,
        hold_score="35",
        hours=hours,
    )
    execution = close_out(
        lifecycle,
        hours=hours,
        open_=open_,
        signal=signal,
        execution_id="exit-1",
    )
    closed = record_exit(lifecycle, execution, reason=signal.exit_reasons[0])
    accounting = calculate_trade_accounting_for_lifecycle(
        closed,
        fills(entry_execution, execution),
    )
    return entry_execution, signal, execution, closed, accounting


def test_the_exit_reason_travels_from_the_signal_to_the_completed_trade() -> None:
    entry_execution, signal, execution, closed, accounting = signalled_exit()

    assert signal.exit_reasons == ("HOLD_SCORE_COLLAPSE",)
    assert execution.intent.exit_reason == "HOLD_SCORE_COLLAPSE"
    assert closed.state == "CLOSED"

    # BTC-165 derives the reason from the ledger transition, so the signal's
    # own label leads and the execution's evidence follows it.
    assert accounting.exit_reason.startswith("HOLD_SCORE_COLLAPSE|")
    assert "EXIT_EXECUTION_FILLED" in accounting.exit_reason
    assert accounting.exit_reason_source_id == execution.intent.execution_id

    row = accounting.as_completed_trade_record(
        account_id=ACCOUNT_ID,
        position_id=POSITION_ID,
    )
    assert row["exit_reason"] == accounting.exit_reason
    assert row["exit_reason_source_id"] == "exit-1"
    assert row["initial_stop_source_id"] == entry_execution.intent.execution_id
    assert row["realized_pnl"] == accounting.net_pnl
    assert row["realized_r"] == accounting.r_multiple
    assert row["config_version"] == METADATA["config_version"]


def test_a_signalled_exit_closes_the_whole_position_and_balances() -> None:
    entry_execution, _, execution, closed, accounting = signalled_exit()

    assert execution.filled_quantity == entry_execution.filled_quantity
    assert closed.quantity == 0
    assert closed.tranches == ()
    assert closed.average_entry_price == entry_execution.average_fill_price

    assert accounting.closed is True
    assert accounting.add_count == 0
    assert accounting.trim_count == 0
    assert accounting.gross_pnl == accounting.exit_notional - accounting.entry_notional
    assert accounting.fees == entry_execution.fee + execution.fee
    assert accounting.net_pnl == accounting.gross_pnl - accounting.fees
    assert accounting.r_multiple == accounting.net_pnl / accounting.initial_risk
    assert "TRADE_ACCOUNTING_COMPLETE" in accounting.reason_codes

    paper = settle(accounting, (entry_execution, execution))
    assert paper.fees_paid == accounting.fees
    assert paper.cash == NAV + accounting.net_pnl


def test_an_exit_must_close_everything_at_both_owners() -> None:
    entry_execution = enter()
    lifecycle = opened(entry_execution)

    partial = apply_position_event(
        lifecycle,
        event=EXIT,
        event_time=at(4),
        quantity=entry_execution.filled_quantity / 2,
        price="108000",
    )
    assert partial.accepted is False
    assert "POSITION_STATE_EXIT_MUST_BE_FULL" in partial.reason_codes
    assert partial.quantity == entry_execution.filled_quantity

    entry_fill, exit_fill = fills(
        entry_execution,
        close_out(
            lifecycle,
            hours=3,
            open_="108000",
            signal=exit_signal(
                lifecycle,
                current_price="108000",
                hold_score="35",
                hours=3,
            ),
            execution_id="exit-1",
        ),
    )
    with pytest.raises(ValueError, match="EXIT must close the full open quantity"):
        calculate_trade_accounting(
            (entry_fill, replace(exit_fill, quantity=exit_fill.quantity / 2)),
            symbol=SYMBOL,
            direction="long",
            initial_stop_price=INITIAL_STOP,
            initial_stop_source_id=entry_execution.intent.execution_id,
            exit_reason="HOLD_SCORE_COLLAPSE",
            exit_reason_source_id="exit-1",
            config_metadata=METADATA,
        )


def test_a_closed_trade_persists_every_row_with_one_provenance() -> None:
    # The stop-out path, where every execution shapes its own order row.
    entry_execution, stop, closed, accounting = stopped_out(
        bar(3, "97000", high="97500", low="95000", close="95500"),
        execution_id="stop-1",
    )

    rows = build_paper_trade_lifecycle_rows(
        provenance=provenance(),
        account_id=ACCOUNT_ID,
        position_id=POSITION_ID,
        executions=(entry_execution, stop),
        lifecycle=closed,
        accounting=accounting,
    )
    verify_lifecycle_rows(rows)

    assert rows.complete is True
    assert rows.reason_codes == ("LIFECYCLE_PERSISTENCE_COMPLETE",)
    assert len(rows.orders) == 2
    assert [row["action"] for row in rows.events] == ["ENTER", "EXIT"]
    assert rows.completed_trade is not None

    for _, row in rows.all_rows:
        assert row["recommendation_id"] == RECOMMENDATION_ID
        assert row["strategy_version"] == METADATA["strategy_version"]
        assert row["parameter_set_id"] == METADATA["parameter_set_id"]
        assert row["account_id"] == ACCOUNT_ID


def test_a_discretionary_exit_is_attributed_through_its_ledger_event() -> None:
    # BTC-161 through BTC-164 each shape a ``paper_orders`` row, and BTC-162's
    # stop does too. The BTC-180 discretionary-exit boundary does not, so a
    # signalled exit contributes no closing order row. The exit is still fully
    # attributed -- the BTC-150 EXIT transition persists as an event row and
    # the trade as a completed_trades row, both carrying the triple. The gap is
    # recorded as an observation on the ticket rather than closed here, because
    # adding an order mapping is BTC-166 and BTC-180 scope, not BTC-223's.
    entry_execution, _, execution, closed, accounting = signalled_exit()

    rows = build_paper_trade_lifecycle_rows(
        provenance=provenance(),
        account_id=ACCOUNT_ID,
        position_id=POSITION_ID,
        executions=(entry_execution,),
        lifecycle=closed,
        accounting=accounting,
    )
    verify_lifecycle_rows(rows)

    assert [row["action"] for row in rows.events] == ["ENTER", "EXIT"]
    exit_event = rows.events[-1]
    assert exit_event["quantity"] == execution.filled_quantity
    assert exit_event["price"] == execution.average_fill_price
    assert exit_event["event_time"] == execution.resolved_at
    assert exit_event["recommendation_id"] == RECOMMENDATION_ID
    assert rows.completed_trade["exit_reason_source_id"] == "exit-1"
    assert not hasattr(execution, "as_order_record")


def test_an_exit_is_deterministic_and_replays_from_its_record() -> None:
    first = signalled_exit()
    second = signalled_exit()

    assert first[2].as_record() == second[2].as_record()
    assert first[4].as_record() == second[4].as_record()
    assert restore_simulated_exit_execution(first[2].as_record()) == first[2]
    assert first[3].as_record() == second[3].as_record()


# --- scenario 7: funding and fees ----------------------------------------


HOUR_IN_DAYS = Decimal("1") / Decimal("24")


def funding_at(hours: float, *, sequence: int, mark: str, quantity, direction: str, costs):
    """One bar's carry, from the configured rate rather than an invented one."""

    return funding_event_from_rate(
        sequence=sequence,
        event_id=f"funding-{hours}",
        effective_at=at(hours),
        rate=costs.funding_rate(days=HOUR_IN_DAYS),
        mark_price=Decimal(mark),
        position_quantity=quantity,
        direction=direction,
    )


def carried_long():
    """A stress-profile long whose costs outweigh a small gross profit."""

    costs = STRESS.costs
    entry_execution = enter(costs=costs)
    lifecycle = opened(entry_execution)
    signal = exit_signal(lifecycle, current_price="100600", hold_score="35", hours=5)
    closing = close_out(
        lifecycle,
        hours=5,
        open_="100600",
        signal=signal,
        execution_id="exit-1",
        costs=costs,
    )
    closed = record_exit(lifecycle, closing, reason=signal.exit_reasons[0])
    events = tuple(
        funding_at(
            hours,
            sequence=sequence,
            mark=mark,
            quantity=lifecycle.quantity,
            direction="long",
            costs=costs,
        )
        for sequence, hours, mark in ((2, 3, "100500"), (3, 5, "100600"))
    )
    accounting = calculate_trade_accounting_for_lifecycle(
        closed,
        (
            trade_fill_from_execution(entry_execution, sequence=1),
            trade_fill_from_execution(closing, sequence=4),
        ),
        funding_events=events,
    )
    return costs, entry_execution, closing, closed, events, accounting


def test_every_leg_pays_the_configured_fee_on_its_own_slipped_notional() -> None:
    costs, entry_execution, closing, _, _, accounting = carried_long()

    for execution in (entry_execution, closing):
        assert execution.notional == execution.filled_quantity * execution.average_fill_price
        assert execution.fee == costs.fee(execution.notional)
        assert execution.slippage_cost == abs(
            execution.notional
            - execution.filled_quantity * execution.reference_price
        )

    assert accounting.fees == entry_execution.fee + closing.fee
    assert costs.fee_bps > COSTS.fee_bps


@pytest.mark.parametrize(
    ("direction", "opening_side", "closing_side"),
    [("long", "buy", "sell"), ("short", "sell", "buy")],
)
def test_slippage_is_adverse_on_every_leg_of_the_trade(
    direction: str,
    opening_side: str,
    closing_side: str,
) -> None:
    # There is no configuration under which a paper fill is better than the
    # reference price, in either direction and at either end of the trade.
    costs = STRESS.costs
    entry_execution = enter(
        costs=costs,
        intent=entry_intent(direction=direction, execution_id="entry-1"),
    )
    lifecycle = opened(
        entry_execution,
        stop_price=INITIAL_STOP if direction == "long" else Decimal("104000"),
    )
    signal = exit_signal(
        lifecycle,
        current_price="100600" if direction == "long" else "98000",
        hold_score="35",
        hours=5,
    )
    closing = close_out(
        lifecycle,
        hours=5,
        open_="100600" if direction == "long" else "98000",
        signal=signal,
        execution_id="exit-1",
        costs=costs,
    )

    assert entry_execution.intent.side == opening_side
    assert closing.intent.side == closing_side
    for execution, side in ((entry_execution, opening_side), (closing, closing_side)):
        if side == "buy":
            assert execution.average_fill_price > execution.reference_price
        else:
            assert execution.average_fill_price < execution.reference_price
        assert execution.slippage_cost > 0


def test_a_long_pays_funding_and_it_can_reverse_a_gross_profit() -> None:
    costs, entry_execution, closing, _, events, accounting = carried_long()

    assert costs.funding_cost_bps_per_day > 0
    assert all(event.funding_cost > 0 for event in events)
    assert accounting.funding == sum(
        (event.funding_cost for event in events),
        Decimal("0"),
    )
    assert accounting.funding_convention == "SIGNED_ACCOUNT_FUNDING_COST_V1"

    assert accounting.gross_pnl > 0
    assert accounting.net_pnl < 0
    assert accounting.net_pnl == accounting.gross_pnl - accounting.fees - accounting.funding
    assert "TRADE_ACCOUNTING_COSTS_REVERSED_A_GROSS_PROFIT" in accounting.reason_codes

    paper = settle(
        accounting,
        (entry_execution, closing),
        funding_events=events,
        costs=costs,
    )
    assert paper.fees_paid == accounting.fees
    assert paper.funding_paid == accounting.funding
    assert paper.cash == NAV + accounting.net_pnl
    assert paper.cash < NAV


def test_a_short_receives_funding_and_the_account_takes_the_signed_figure() -> None:
    costs = STRESS.costs
    entry_execution = enter(
        costs=costs,
        intent=entry_intent(direction="short", execution_id="entry-1"),
    )
    lifecycle = opened(entry_execution, stop_price=Decimal("104000"))
    signal = exit_signal(lifecycle, current_price="98000", hold_score="35", hours=5)
    closing = close_out(
        lifecycle,
        hours=5,
        open_="98000",
        signal=signal,
        execution_id="exit-1",
        costs=costs,
    )
    closed = record_exit(lifecycle, closing, reason=signal.exit_reasons[0])
    events = (
        funding_at(
            3,
            sequence=2,
            mark="99000",
            quantity=lifecycle.quantity,
            direction="short",
            costs=costs,
        ),
    )
    accounting = calculate_trade_accounting_for_lifecycle(
        closed,
        (
            trade_fill_from_execution(entry_execution, sequence=1),
            trade_fill_from_execution(closing, sequence=3),
        ),
        funding_events=events,
    )

    assert accounting.direction == "short"
    assert events[0].funding_cost < 0
    assert accounting.funding < 0
    # Received carry increases net P&L; it is never absorbed as a smaller cost.
    assert accounting.net_pnl > accounting.gross_pnl - accounting.fees

    paper = settle(
        accounting,
        (entry_execution, closing),
        funding_events=events,
        costs=costs,
    )
    assert paper.funding_paid == accounting.funding
    assert paper.cash == NAV + accounting.net_pnl


def test_funding_is_reconciled_to_the_quantity_the_ledger_held() -> None:
    costs, entry_execution, closing, closed, events, _ = carried_long()
    inflated = replace(
        events[0],
        position_quantity=events[0].position_quantity * 2,
        funding_cost=events[0].funding_cost * 2,
    )

    with pytest.raises(ValueError, match="does not match the ledger"):
        calculate_trade_accounting_for_lifecycle(
            closed,
            (
                trade_fill_from_execution(entry_execution, sequence=1),
                trade_fill_from_execution(closing, sequence=4),
            ),
            funding_events=(inflated, events[1]),
        )


def test_the_shipped_profile_prices_funding_at_a_configured_zero() -> None:
    # Zero is a calibration with a version behind it, not a missing input. The
    # base profile therefore produces no funding events at all, and BTC-165
    # still refuses an aggregate figure with no point-in-time evidence.
    assert COSTS.funding_cost_bps_per_day == 0
    assert COSTS.funding_rate(days=10) == 0
    assert COSTS.policy_version == "EXECUTION_COST_V1"
    assert STRESS.parameter_status == "PROVISIONAL_RESEARCH_CALIBRATABLE"

    entry_execution, _, _, _, accounting = signalled_exit()
    assert accounting.funding == 0
    assert accounting.funding_events == ()

    with pytest.raises(ValueError, match="aggregate funding is not replayable"):
        calculate_trade_accounting(
            accounting.fills,
            symbol=SYMBOL,
            direction="long",
            initial_stop_price=INITIAL_STOP,
            initial_stop_source_id=entry_execution.intent.execution_id,
            exit_reason="HOLD_SCORE_COLLAPSE",
            exit_reason_source_id="exit-1",
            funding=Decimal("5"),
            config_metadata=METADATA,
        )


# --- the seven scenarios composed into one trade -------------------------


def complete_trade():
    """One stress-profile trade that uses every mechanic the ticket names.

    Entry, a pyramided add, a trim, a ratcheted stop, carried funding and a
    signalled exit, in ledger order, through the real owners.
    """

    costs = STRESS.costs
    entry_execution = enter(costs=costs)
    lifecycle = opened(entry_execution)

    addition = add(
        lifecycle,
        hours=2,
        open_="112000",
        execution_id="add-1",
        costs=costs,
    )
    lifecycle = record_add(lifecycle, addition)
    carried_quantity = lifecycle.quantity

    reduction = trim(
        lifecycle,
        hours=4,
        open_="116000",
        execution_id="trim-1",
        costs=costs,
    )
    lifecycle = record_trim(lifecycle, reduction)

    advance = trail(
        lifecycle,
        structure_price="114000",
        hours=6,
        structure_id="hl-1",
        current_price="117000",
    )
    lifecycle = apply_trailing_stop(lifecycle, advance, event_time=decided(6))

    signal = exit_signal(lifecycle, current_price="118000", hold_score="35", hours=7)
    closing = close_out(
        lifecycle,
        hours=7,
        open_="118000",
        signal=signal,
        execution_id="exit-1",
        costs=costs,
    )
    closed = record_exit(lifecycle, closing, reason=signal.exit_reasons[0])

    executions = (entry_execution, addition, reduction, closing)
    trade_fills = tuple(
        trade_fill_from_execution(execution, sequence=sequence)
        for execution, sequence in zip(executions, (1, 2, 4, 6))
    )
    # Carry is charged on the quantity the ledger actually held at each event:
    # the whole book before the trim, and only what remained after it.
    events = (
        funding_at(
            5,
            sequence=3,
            mark="115000",
            quantity=carried_quantity,
            direction="long",
            costs=costs,
        ),
        funding_at(
            7,
            sequence=5,
            mark="117000",
            quantity=closing.filled_quantity,
            direction="long",
            costs=costs,
        ),
    )
    accounting = calculate_trade_accounting_for_lifecycle(
        closed,
        trade_fills,
        funding_events=events,
    )
    return costs, executions, advance, closed, events, accounting


def test_the_whole_lifecycle_reconciles_across_every_owner() -> None:
    costs, executions, advance, closed, events, accounting = complete_trade()
    entry_execution, addition, reduction, closing = executions

    states = [
        transition.to_state for transition in closed.transitions if transition.accepted
    ]
    assert states == [OPEN_INITIAL, OPEN_ADDED, OPEN_ADDED, OPEN_ADDED, "CLOSED"]
    assert [transition.event for transition in closed.transitions] == [
        ENTER,
        ADD,
        TRIM,
        STOP_MOVE,
        EXIT,
    ]
    assert closed.stop_price == advance.stop_price
    assert closed.quantity == 0

    # Every ledger transition names the execution that produced it.
    sources = {
        transition.event: transition.source_record_id
        for transition in closed.transitions
        if transition.source_record_id is not None
    }
    assert sources[ENTER] == "entry-1"
    assert sources[ADD] == "add-1"
    assert sources[TRIM] == "trim-1"
    assert sources[EXIT] == "exit-1"

    assert accounting.add_count == 1
    assert accounting.trim_count == 1
    assert accounting.closed is True
    assert accounting.exit_reason.startswith("HOLD_SCORE_COLLAPSE|")
    assert accounting.fees == sum(
        (execution.fee for execution in executions),
        Decimal("0"),
    )
    assert accounting.funding == sum(
        (event.funding_cost for event in events),
        Decimal("0"),
    )
    assert accounting.gross_pnl == accounting.exit_notional - accounting.entry_notional
    assert accounting.net_pnl == accounting.gross_pnl - accounting.fees - accounting.funding
    # The ratchet protected profit; R is still measured at the entry stop.
    assert accounting.initial_stop_price == INITIAL_STOP
    assert accounting.r_multiple == accounting.net_pnl / accounting.initial_risk
    assert accounting.r_multiple > 0

    paper = settle(accounting, executions, funding_events=events, costs=costs)
    assert paper.fees_paid == accounting.fees
    assert paper.funding_paid == accounting.funding
    assert paper.cash == NAV + accounting.net_pnl


def test_the_whole_lifecycle_persists_and_replays_unchanged() -> None:
    _, executions, _, closed, _, accounting = complete_trade()
    entry_execution, addition, reduction, _ = executions

    rows = build_paper_trade_lifecycle_rows(
        provenance=provenance(),
        account_id=ACCOUNT_ID,
        position_id=POSITION_ID,
        executions=(entry_execution, addition, reduction),
        lifecycle=closed,
        accounting=accounting,
    )
    verify_lifecycle_rows(rows)

    assert rows.complete is True
    assert [row["action"] for row in rows.orders] == [ENTER, ADD, TRIM]
    assert [row["action"] for row in rows.events] == [
        "ENTER",
        "ADD",
        "TRIM",
        "STOP_MOVE",
        "EXIT",
    ]
    assert rows.completed_trade["accounting_record"] == accounting.as_record()
    for _, row in rows.all_rows:
        assert row["strategy_version"] == METADATA["strategy_version"]
        assert row["parameter_set_id"] == METADATA["parameter_set_id"]

    restored = restore_position_lifecycle(closed.as_record())
    assert restored == closed
    replayed = replay_position_event_records(
        position_event_records(closed),
        symbol=SYMBOL,
        direction=closed.direction,
        config_metadata=METADATA,
    )
    assert replayed.state == closed.state
    assert replayed.quantity == closed.quantity
    assert replayed.stop_price == closed.stop_price
    assert replayed.average_entry_price == closed.average_entry_price


def test_the_whole_lifecycle_is_reproducible_from_the_same_inputs() -> None:
    _, first_executions, _, first_closed, _, first_accounting = complete_trade()
    _, second_executions, _, second_closed, _, second_accounting = complete_trade()

    assert [execution.as_record() for execution in first_executions] == [
        execution.as_record() for execution in second_executions
    ]
    assert first_closed.as_record() == second_closed.as_record()
    assert first_accounting.as_record() == second_accounting.as_record()
    assert first_accounting.evidence_digest == second_accounting.evidence_digest
    assert restore_trade_accounting(first_accounting.as_record()) == first_accounting


# --- a composition limit this suite used to surface ----------------------


def test_a_trim_on_a_non_terminating_tranche_accounts_exactly() -> None:
    """An ordinary add-then-trim trade must reach a closed accounting.

    Removing a trim's cost basis pro rata is ``cost_basis * quantity / open``.
    BTC-155 produces open quantities that do not terminate in Decimal's
    28-digit context routinely, because it divides a notional by a price, so
    that removal used to round and the closed trade used to miss the exact
    cash-flow identity by about 1e-23 -- which BTC-165 refused outright. An
    add at 105,000 is an ordinary tranche and a trade that adds and then trims
    is an ordinary trade, so this was a reachable failure of BTC-160..166 in
    composition rather than a pathological fixture.

    The EPIC Q integration review made the position walk rational, so the
    removal now cancels exactly. This pins the trade that used to fail.
    """

    costs = STRESS.costs
    entry_execution = enter(costs=costs)
    lifecycle = opened(entry_execution)
    addition = add(
        lifecycle,
        hours=2,
        open_="105000",
        execution_id="add-1",
        costs=costs,
    )
    lifecycle = record_add(lifecycle, addition)

    # BTC-155's own allocation, not a contrived quantity: a notional divided
    # by a price, which here repeats and fills the Decimal context.
    allocation = tranche(2, entry_price=Decimal("105000")).allocation
    assert addition.filled_quantity == allocation.quantity
    assert allocation.quantity != allocation.quantity.quantize(Decimal("1e-20"))

    reduction = trim(
        lifecycle,
        hours=4,
        open_="116000",
        execution_id="trim-1",
        costs=costs,
    )
    lifecycle = record_trim(lifecycle, reduction)
    signal = exit_signal(lifecycle, current_price="118000", hold_score="35", hours=7)
    closing = close_out(
        lifecycle,
        hours=7,
        open_="118000",
        signal=signal,
        execution_id="exit-1",
        costs=costs,
    )
    closed = record_exit(lifecycle, closing, reason=signal.exit_reasons[0])
    executions = (entry_execution, addition, reduction, closing)

    accounting = calculate_trade_accounting_for_lifecycle(
        closed,
        tuple(
            trade_fill_from_execution(execution, sequence=sequence)
            for execution, sequence in zip(executions, (1, 2, 3, 4))
        ),
    )

    assert accounting.closed is True
    assert accounting.add_count == 1
    assert accounting.trim_count == 1
    # The identity holds exactly, not to a tolerance.
    assert accounting.gross_pnl == (
        accounting.exit_notional - accounting.entry_notional
    )
    # Independently: gross P&L is every sale less every purchase, at the
    # quantities and fill prices the executions actually produced. The
    # expectation is rational because a Decimal expression would round the
    # very digits this test exists to protect.
    def exact(*executions) -> Fraction:
        return sum(
            (
                Fraction(execution.filled_quantity * execution.average_fill_price)
                for execution in executions
            ),
            Fraction(0),
        )

    assert Fraction(accounting.entry_notional) == exact(entry_execution, addition)
    assert Fraction(accounting.exit_notional) == exact(reduction, closing)
    assert Fraction(accounting.gross_pnl) == exact(reduction, closing) - exact(
        entry_execution, addition
    )
    assert accounting.net_pnl == accounting.gross_pnl - accounting.fees
    assert restore_trade_accounting(accounting.as_record()) == accounting

    # Every leg's notional is the exact product of its quantity and its fill
    # price, so the fee each leg pays is charged on the same figure BTC-165
    # books. A float64 detour in one execution would show up here as a fee
    # that no longer matches the notional the accounting walked.
    for execution in executions:
        assert execution.notional == (
            execution.filled_quantity * execution.average_fill_price
        )
        assert execution.fee == costs.fee(execution.notional)
    assert accounting.fees == sum(
        (execution.fee for execution in executions),
        Decimal("0"),
    )

    # The account reaches the same money the accounting reports.
    paper = settle(accounting, executions, funding_events=(), costs=costs)
    assert paper.cash == NAV + accounting.net_pnl
