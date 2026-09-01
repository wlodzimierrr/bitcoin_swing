"""Independent correctness and release-gate coverage for BTC-180."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

import btc_predictor.backtest.engine as engine
from btc_predictor.backtest.engine import (
    ADD_ACTION,
    ARM_ENTRY_ACTION,
    EXIT_ACTION,
    TRAIL_ACTION,
    TRIM_ACTION,
    BacktestIntent,
    restore_backtest_result,
    run_backtest,
)
from btc_predictor.config import load_strategy_config
from btc_predictor.data import OhlcvBar
from btc_predictor.portfolio.account import (
    ExecutionCosts,
    execution_costs_from_config,
    open_paper_account,
)
from btc_predictor.portfolio.exit_execution import restore_simulated_exit_execution
from btc_predictor.risk.stop import calculate_initial_stop
from btc_predictor.risk.trailing import (
    HIGHER_LOW,
    calculate_trailing_stop,
    stop_advance_count,
)
from btc_predictor.signals import (
    AddRequirementsInput,
    TrimRuleInput,
    evaluate_add_requirements,
    evaluate_trim_rules,
)


UTC = timezone.utc
START = datetime(2024, 1, 1, tzinfo=UTC)
CONFIG = load_strategy_config()
METADATA = CONFIG.run_metadata()
NAV = Decimal("1000000")
LOWER = Decimal("99000")
UPPER = Decimal("101000")


def market_bar(
    day: int,
    open_: str,
    high: str,
    low: str,
    close: str,
    *,
    ingested_at: datetime | None = None,
    provider: str = "coinbase",
) -> OhlcvBar:
    timestamp = START + timedelta(days=day)
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1d",
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("100"),
        provider=provider,
        ingested_at=ingested_at or timestamp + timedelta(days=1),
    )


RISING = tuple(
    market_bar(index, *values)
    for index, values in enumerate(
        (
            ("100000", "101000", "99000", "100500"),
            ("100500", "102000", "99500", "101500"),
            ("101500", "108000", "101000", "107000"),
            ("107000", "112000", "106000", "111000"),
            ("111000", "115000", "110000", "114000"),
            ("114000", "118000", "113000", "117000"),
            ("117000", "120000", "116000", "119000"),
        )
    )
)

FALLING = (
    market_bar(0, "100000", "101000", "99000", "100500"),
    market_bar(1, "100500", "102000", "99500", "101500"),
    market_bar(2, "101500", "102000", "94000", "94500"),
    market_bar(3, "94500", "95000", "92000", "93000"),
)


def entry(*, direction: str = "long", stop: str = "95000") -> BacktestIntent:
    initial_stop = calculate_initial_stop(
        invalidation_price=stop,
        buffer="0",
        direction=direction,
        entry_price=UPPER,
        config_metadata=METADATA,
    )
    return BacktestIntent(
        action=ARM_ENTRY_ACTION,
        direction=direction,
        entry_zone_lower=LOWER,
        entry_zone_upper=UPPER,
        initial_stop=initial_stop,
        entry_conviction=Decimal("90"),
        source_id=f"entry-{direction}",
    )


def add_requirements(*, accepted: bool = True):
    return evaluate_add_requirements(
        AddRequirementsInput(
            position_profitable=True,
            new_structural_confirmation=True,
            signed_risk_improvement=Decimal("1500"),
            regime_supportive=True,
            flow_supportive=True,
            positioning_healthy=True,
            add_score=Decimal("90" if accepted else "50"),
            projected_risk_at_stop_within_maximum=True,
        ),
        strategy_config=CONFIG,
    )


def trim_signal():
    return evaluate_trim_rules(
        TrimRuleInput(
            position_open=True,
            hold_score=Decimal("45"),
            euphoria_active=False,
            crowding_active=False,
            current_flow_score=Decimal("50"),
            prior_flow_score=Decimal("60"),
        ),
        strategy_config=CONFIG,
    )


def trail(context, *, identifier: str = "hl-1", structure: str = "104000"):
    return calculate_trailing_stop(
        direction=context.lifecycle.direction,
        previous_stop=context.standing_stop,
        structure_price=structure,
        buffer="1000",
        advance_count=stop_advance_count(context.lifecycle),
        current_price=context.bar.close,
        config_metadata=METADATA,
        evaluated_at=context.as_of,
        structure_id=identifier,
        structure_source_feature_id="ENTRY_TRIGGER_HIGHER_LOW",
        structure_type=HIGHER_LOW,
        structure_level_timestamp=context.bar.timestamp,
        structure_detected_at=context.as_of,
        structure_reason_codes=("HIGHER_LOW_CONFIRMED",),
    )


def run(bars=RISING, *, strategy, config=CONFIG, costs=None, account=None):
    return run_backtest(
        bars,
        strategy=strategy,
        starting_nav=None if account is not None else NAV,
        strategy_config=config,
        costs=costs,
        account=account,
        strategy_id="btc180-independent-review-v1",
    )


def enter_first(context):
    return entry() if context.bar.timestamp == RISING[0].timestamp else None


def test_context_clock_is_close_and_ingestion_point_in_time() -> None:
    seen = []

    def strategy(context):
        seen.append(context)
        return None

    run(strategy=strategy)

    assert seen
    for context in seen:
        assert context.as_of >= context.bar.ingested_at
        assert context.as_of >= context.bar.timestamp + timedelta(days=1)
        assert all(item.ingested_at <= context.as_of for item in context.bars)
        assert all(item.timestamp + timedelta(days=1) <= context.as_of for item in context.bars)


def test_decision_bar_touch_cannot_fill_its_own_entry() -> None:
    bars = (
        market_bar(0, "100000", "101000", "99000", "100500"),
        market_bar(1, "120000", "122000", "119000", "121000"),
    )

    result = run(
        bars,
        strategy=lambda context: entry()
        if context.bar.timestamp == bars[0].timestamp
        else None,
    )

    assert result.missed_entries == 1
    assert "BACKTEST_ENTRY_FILLED" not in result.reason_codes


def test_entry_and_stop_touch_on_execution_bar_resolves_adverse_path() -> None:
    bars = (
        market_bar(0, "100000", "101000", "99000", "100500"),
        market_bar(1, "100500", "102000", "94000", "101500"),
    )

    result = run(
        bars,
        strategy=lambda context: entry()
        if context.bar.timestamp == bars[0].timestamp
        else None,
    )

    assert result.stopped_out == 1
    assert result.final_lifecycle.quantity == 0
    assert result.trades[0].opened_at == result.trades[0].closed_at
    assert [fill.action for fill in result.trades[0].fills] == ["ENTER", "EXIT"]
    assert result.total_pnl == result.net_pnl


def test_missing_first_eligible_bar_expires_without_fabricated_fill() -> None:
    bars = (RISING[0], RISING[2], RISING[3])
    result = run(
        bars,
        strategy=lambda context: entry()
        if context.bar.timestamp == bars[0].timestamp
        else None,
    )

    assert "BACKTEST_INTENT_EXPIRED" in result.reason_codes
    assert result.trades == ()


def test_final_bar_intent_is_audited_but_never_executes() -> None:
    result = run(
        strategy=lambda context: entry()
        if context.bar.timestamp == RISING[-1].timestamp
        else None,
    )

    assert "BACKTEST_INTENT_UNEXECUTED_END" in result.reason_codes
    assert result.trades == ()
    assert result.events[-1].status == "UNEXECUTED"


def test_only_one_intent_can_remain_pending() -> None:
    late = START + timedelta(days=5)
    bars = (
        replace(RISING[0], ingested_at=late),
        replace(RISING[1], ingested_at=late),
    )

    with pytest.raises(ValueError, match="second intent"):
        run(
            bars,
            strategy=lambda context: replace(
                entry(),
                source_id=f"entry-{context.bar.timestamp.isoformat()}",
            ),
        )


def test_second_independent_entry_is_refused_while_position_is_open() -> None:
    def strategy(context):
        if context.bar.timestamp == RISING[0].timestamp:
            return entry()
        if context.bar.timestamp == RISING[1].timestamp:
            return replace(entry(), source_id="entry-2")
        return None

    result = run(strategy=strategy)

    assert len(result.trades) == 1
    assert result.trades[0].closed is False
    assert "BACKTEST_INTENT_REFUSED" in result.reason_codes
    assert any("POSITION_ALREADY_OPEN" in event.reason_codes for event in result.events)


@pytest.mark.parametrize("action", [ADD_ACTION, TRIM_ACTION, EXIT_ACTION, TRAIL_ACTION])
def test_resting_stop_makes_queued_position_actions_stale(action: str) -> None:
    def strategy(context):
        if context.bar.timestamp == FALLING[0].timestamp:
            return entry()
        if context.bar.timestamp == FALLING[1].timestamp:
            if action == ADD_ACTION:
                return BacktestIntent(action=action, requirements=add_requirements())
            if action == TRIM_ACTION:
                return BacktestIntent(action=action, trim_signal=trim_signal())
            if action == TRAIL_ACTION:
                return BacktestIntent(action=action, trailing_stop=trail(context))
            return BacktestIntent(action=action, exit_reason="HOLD_SCORE_COLLAPSE")
        return None

    result = run(FALLING, strategy=strategy)

    assert result.stopped_out == 1
    assert len(result.trades) == 1
    assert result.trades[0].exit_reason == "STRUCTURAL_STOP"
    assert "BACKTEST_INTENT_STALE" in result.reason_codes
    assert sum(fill.action == "EXIT" for fill in result.trades[0].fills) == 1


def test_late_add_ledger_refusal_is_an_atomic_economic_noop(monkeypatch) -> None:
    authoritative = engine.apply_position_event

    def refuse_add(lifecycle, **kwargs):
        if kwargs["event"] == "ADD":
            kwargs["price"] = lifecycle.average_entry_price - Decimal("1")
        return authoritative(lifecycle, **kwargs)

    monkeypatch.setattr(engine, "apply_position_event", refuse_add)

    def strategy(context):
        if context.bar.timestamp == RISING[0].timestamp:
            return entry()
        if context.bar.timestamp == RISING[2].timestamp:
            return BacktestIntent(action=ADD_ACTION, requirements=add_requirements())
        return None

    result = run(strategy=strategy)
    before = result.equity_curve[2]
    after = result.equity_curve[3]

    assert after.open_quantity == before.open_quantity
    assert result.account.fees_paid == result.trades[0].fees
    assert "BACKTEST_ADD_REFUSED" in result.reason_codes
    assert any(
        event.event_type == "LEDGER_TRANSITION" and event.status == "REFUSED"
        for event in result.events
    )


def test_exit_and_stop_fees_reconcile_flat_nav_exactly() -> None:
    def discretionary(context):
        if context.bar.timestamp == RISING[0].timestamp:
            return entry()
        if context.bar.timestamp == RISING[3].timestamp:
            return BacktestIntent(action=EXIT_ACTION, exit_reason="RESEARCH_EXIT")
        return None

    for result in (
        run(strategy=discretionary),
        run(
            FALLING,
            strategy=lambda context: (
                entry() if context.bar.timestamp == FALLING[0].timestamp else None
            ),
        ),
    ):
        assert result.final_lifecycle.quantity == 0
        assert result.total_pnl == result.net_pnl
        assert result.account.fees_paid == sum(
            (trade.fees for trade in result.trades), Decimal("0")
        )


def test_multiple_sequential_trades_reconcile_nav_exactly_once() -> None:
    bars = tuple(
        market_bar(index, "100000", "103000", "99000", "102000")
        for index in range(7)
    )

    def strategy(context):
        if context.bar.timestamp == bars[0].timestamp:
            return entry()
        if context.bar.timestamp == bars[2].timestamp:
            return BacktestIntent(action=EXIT_ACTION, exit_reason="RESEARCH_EXIT")
        if context.bar.timestamp == bars[3].timestamp:
            return replace(entry(), source_id="entry-2")
        if context.bar.timestamp == bars[5].timestamp:
            return BacktestIntent(
                action=EXIT_ACTION,
                exit_reason="RESEARCH_EXIT",
                source_id="exit-2",
            )
        return None

    result = run(bars, strategy=strategy)

    assert len(result.trades) == 2
    assert all(trade.closed for trade in result.trades)
    assert result.total_pnl == sum(
        (trade.net_pnl for trade in result.trades), Decimal("0")
    )
    assert result.account.fees_paid == sum(
        (trade.fees for trade in result.trades), Decimal("0")
    )


def test_open_trim_nav_reconciles_realized_and_unrealized_economics() -> None:
    def strategy(context):
        if context.bar.timestamp == RISING[0].timestamp:
            return entry()
        if context.bar.timestamp == RISING[3].timestamp:
            return BacktestIntent(action=TRIM_ACTION, trim_signal=trim_signal())
        return None

    result = run(strategy=strategy)
    last = result.equity_curve[-1]

    assert result.trades[0].closed is False
    assert result.account.realized_pnl == result.trades[0].gross_pnl
    assert result.total_pnl == result.net_pnl + last.unrealized_pnl


def test_funding_is_not_dropped_on_add_trim_or_exit_bars() -> None:
    carried = replace(
        execution_costs_from_config(CONFIG),
        funding_cost_bps_per_day=Decimal("2"),
    )

    def strategy(context):
        if context.bar.timestamp == RISING[0].timestamp:
            return entry()
        if context.bar.timestamp == RISING[2].timestamp:
            return BacktestIntent(action=ADD_ACTION, requirements=add_requirements())
        if context.bar.timestamp == RISING[3].timestamp:
            return BacktestIntent(action=TRIM_ACTION, trim_signal=trim_signal())
        if context.bar.timestamp == RISING[4].timestamp:
            return BacktestIntent(action=EXIT_ACTION, exit_reason="RESEARCH_EXIT")
        return None

    result = run(strategy=strategy, costs=carried)
    trade = result.trades[0]
    execution_bar_timestamps = {
        fill.execution_bar_at for fill in trade.fills if fill.action in ("ADD", "TRIM", "EXIT")
    }
    funding_bar_timestamps = {
        event.effective_at.replace(hour=0, minute=0, second=0, microsecond=0)
        for event in trade.funding_events
    }

    assert trade.funding_events
    assert execution_bar_timestamps <= funding_bar_timestamps
    assert trade.funding == result.account.funding_paid


def test_positive_funding_rate_is_received_by_short_account() -> None:
    short_config = replace(
        CONFIG,
        backtest=replace(CONFIG.backtest, allow_short_trades=True),
    )
    carried = replace(
        execution_costs_from_config(short_config),
        funding_cost_bps_per_day=Decimal("2"),
    )
    bars = tuple(
        market_bar(index, "100000", "102000", "98000", "100000")
        for index in range(5)
    )

    result = run(
        bars,
        config=short_config,
        costs=carried,
        strategy=lambda context: entry(direction="short", stop="105000")
        if context.bar.timestamp == bars[0].timestamp
        else None,
    )

    assert result.account.funding_paid < 0
    assert result.trades[0].funding < 0
    assert result.account.cash > NAV - result.account.fees_paid


def test_late_batch_funding_keeps_economic_time_and_monotonic_audit_time() -> None:
    late = START + timedelta(days=5)
    bars = (
        RISING[0],
        RISING[1],
        replace(RISING[2], ingested_at=late),
        replace(RISING[3], ingested_at=late),
    )
    carried = replace(
        execution_costs_from_config(CONFIG),
        funding_cost_bps_per_day=Decimal("2"),
    )

    def strategy(context):
        if context.bar.timestamp == bars[0].timestamp:
            return entry()
        if context.bar.timestamp == bars[2].timestamp:
            return BacktestIntent(action=EXIT_ACTION, exit_reason="RESEARCH_EXIT")
        return None

    result = run(bars, strategy=strategy, costs=carried)
    funding_events = tuple(
        event for event in result.events if event.event_type == "FUNDING"
    )

    assert funding_events
    assert all(
        event.occurred_at.isoformat() == event.evidence["observed_at"]
        and event.occurred_at >= datetime.fromisoformat(event.evidence["effective_at"])
        for event in funding_events
    )
    assert all(
        current.occurred_at >= previous.occurred_at
        for previous, current in zip(result.events, result.events[1:])
    )


def test_trailing_stop_cannot_use_the_bar_that_installs_it() -> None:
    bars = (
        market_bar(0, "100000", "101000", "99000", "100500"),
        market_bar(1, "100500", "106000", "99500", "105000"),
        market_bar(2, "105000", "109000", "96000", "108000"),
        market_bar(3, "108000", "111000", "100000", "110000"),
        market_bar(4, "110000", "112000", "102000", "104000"),
    )

    def strategy(context):
        if context.bar.timestamp == bars[0].timestamp:
            return entry()
        if context.bar.timestamp == bars[2].timestamp:
            return BacktestIntent(action=TRAIL_ACTION, trailing_stop=trail(context))
        return None

    result = run(bars, strategy=strategy)

    assert result.equity_curve[3].open_quantity > 0
    assert result.equity_curve[4].open_quantity == 0
    assert result.trades[0].exit_reason == "STRUCTURAL_STOP"


def test_reused_structure_identity_cannot_advance_stop_twice() -> None:
    bars = (
        market_bar(0, "100000", "101000", "99000", "100500"),
        market_bar(1, "100500", "103000", "99500", "102000"),
        market_bar(2, "106000", "109000", "105000", "108000"),
        market_bar(3, "109000", "112000", "108000", "111000"),
        market_bar(4, "112000", "115000", "111000", "114000"),
        market_bar(5, "115000", "118000", "114000", "117000"),
        market_bar(6, "118000", "121000", "117000", "120000"),
    )

    def strategy(context):
        if context.bar.timestamp == bars[0].timestamp:
            return entry()
        if context.bar.timestamp == bars[2].timestamp:
            return BacktestIntent(action=TRAIL_ACTION, trailing_stop=trail(context))
        if context.bar.timestamp == bars[4].timestamp:
            return BacktestIntent(
                action=TRAIL_ACTION,
                trailing_stop=trail(context, identifier="hl-1", structure="110000"),
            )
        return None

    result = run(bars, strategy=strategy)

    assert stop_advance_count(result.final_lifecycle) == 1
    assert result.final_lifecycle.stop_price == Decimal("103000")
    assert "BACKTEST_TRAIL_HELD" in result.reason_codes


@pytest.mark.parametrize(
    "bad_bar",
    [
        market_bar(0, "100", "90", "80", "95"),
        market_bar(0, "100", "110", "105", "106"),
        replace(RISING[0], open=Decimal("NaN")),
        replace(RISING[0], volume=Decimal("-1")),
    ],
)
def test_malformed_ohlcv_fails_before_strategy_runs(bad_bar) -> None:
    called = False

    def strategy(_context):
        nonlocal called
        called = True
        return None

    with pytest.raises(ValueError):
        run((bad_bar,), strategy=strategy)
    assert called is False


def test_duplicate_and_unversioned_provider_splice_fail_closed() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        run((RISING[0], RISING[0]), strategy=lambda _context: None)
    with pytest.raises(ValueError, match="provider splicing"):
        run(
            (RISING[0], replace(RISING[1], provider="bitstamp")),
            strategy=lambda _context: None,
        )


def test_strategy_context_mutation_cannot_change_engine_state() -> None:
    def strategy(context):
        context.account.config_metadata["config_version"] = "tampered"
        context.lifecycle.config_metadata["config_version"] = "tampered"
        return entry() if context.bar.timestamp == RISING[0].timestamp else None

    result = run(strategy=strategy)

    assert result.config_metadata == METADATA
    assert result.account.config_metadata == METADATA
    assert result.final_lifecycle.config_metadata == METADATA


def test_account_and_execution_cost_policy_mismatch_fails_fast() -> None:
    configured = execution_costs_from_config(CONFIG)
    account = open_paper_account(
        account_name="review",
        created_at=START,
        starting_nav=NAV,
        costs=configured,
        config=CONFIG,
    )
    free = ExecutionCosts(
        policy_version=configured.policy_version,
        fee_bps=Decimal("0"),
        slippage_bps=Decimal("0"),
        funding_cost_bps_per_day=Decimal("0"),
    )

    with pytest.raises(ValueError, match="costs must be identical"):
        run(strategy=lambda _context: None, account=account, costs=free)


@pytest.mark.parametrize("account_state", ["used", "archived", "created_late"])
def test_run_rejects_account_state_that_cannot_match_a_fresh_lifecycle(
    account_state: str,
) -> None:
    account = open_paper_account(
        account_name="review",
        created_at=START,
        starting_nav=NAV,
        costs=execution_costs_from_config(CONFIG),
        config=CONFIG,
    )
    if account_state == "used":
        account = account.charge_fee(Decimal("1000"))
    elif account_state == "archived":
        account = account.archive()
    else:
        account = replace(account, created_at=START + timedelta(days=1))

    with pytest.raises(ValueError, match="account"):
        run(strategy=lambda _context: None, account=account)


def test_loss_beyond_account_capital_fails_closed_instead_of_returning_capped_nav() -> None:
    bars = (
        market_bar(0, "100000", "101000", "99000", "100500"),
        market_bar(1, "101000", "102000", "101000", "101500"),
        market_bar(2, "1", "2", "0.5", "1"),
    )

    with pytest.raises(ValueError, match="account cash does not reconcile"):
        run(
            bars,
            strategy=lambda context: entry(stop="100999")
            if context.bar.timestamp == bars[0].timestamp
            else None,
        )


def test_result_digest_detects_mutated_economic_or_event_evidence() -> None:
    result = run(strategy=enter_first)
    with pytest.raises(ValueError):
        replace(result, ending_nav=result.ending_nav + Decimal("1")).as_record()

    mutated = run(strategy=enter_first)
    mutated.events[0].evidence["tampered"] = True
    with pytest.raises(ValueError, match="evidence_digest"):
        mutated.as_record()


def test_persisted_result_round_trips_through_validating_restore() -> None:
    record = run(strategy=enter_first).as_record()

    assert restore_backtest_result(record).as_record() == record


@pytest.mark.parametrize("section", ["input_bars", "equity_curve", "events"])
def test_persisted_result_restore_rejects_nested_evidence_tampering(section: str) -> None:
    record = run(strategy=enter_first).as_record()
    tampered = deepcopy(record)
    if section == "input_bars":
        tampered[section][0]["close"] = "1"
    elif section == "equity_curve":
        tampered[section][-1]["nav"] = "1"
    else:
        tampered[section][0]["evidence"]["tampered"] = True

    with pytest.raises(ValueError):
        restore_backtest_result(tampered)


def test_discretionary_exit_record_replays_through_owner_module() -> None:
    def strategy(context):
        if context.bar.timestamp == RISING[0].timestamp:
            return entry()
        if context.bar.timestamp == RISING[3].timestamp:
            return BacktestIntent(action=EXIT_ACTION, exit_reason="RESEARCH_EXIT")
        return None

    result = run(strategy=strategy)
    record = next(
        event.evidence for event in result.events if event.event_type == "EXIT_EXECUTION"
    )

    assert restore_simulated_exit_execution(record).as_record() == record


def test_engine_calls_authoritative_owner_paths(monkeypatch) -> None:
    called = {
        "size": 0,
        "entry": 0,
        "risk": 0,
        "fill": 0,
        "accounting": 0,
        "stop": 0,
    }

    def spy(name):
        original = getattr(engine, name)

        def wrapped(*args, **kwargs):
            called_key = {
                "initial_position_size_for_trade": "size",
                "simulate_next_bar_entry": "entry",
                "calculate_risk_at_stop": "risk",
                "trade_fill_from_execution": "fill",
                "calculate_trade_accounting_for_lifecycle": "accounting",
                "stop_execution_for_position": "stop",
            }[name]
            called[called_key] += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(engine, name, wrapped)

    for name in (
        "initial_position_size_for_trade",
        "simulate_next_bar_entry",
        "calculate_risk_at_stop",
        "trade_fill_from_execution",
        "calculate_trade_accounting_for_lifecycle",
        "stop_execution_for_position",
    ):
        spy(name)

    run(
        FALLING,
        strategy=lambda context: (
            entry() if context.bar.timestamp == FALLING[0].timestamp else None
        ),
    )

    assert all(count > 0 for count in called.values())


def test_appending_future_bars_does_not_change_historical_outputs() -> None:
    prefix = RISING[:4]
    prefix_result = run(prefix, strategy=enter_first)
    full_result = run(strategy=enter_first)

    assert full_result.equity_curve[: len(prefix)] == prefix_result.equity_curve
    cutoff = prefix_result.equity_curve[-1].as_of
    assert tuple(event for event in full_result.events if event.occurred_at <= cutoff) == tuple(
        event for event in prefix_result.events if event.occurred_at <= cutoff
    )
