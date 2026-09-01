"""BTC-180: event-driven backtest engine."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from btc_predictor.backtest.engine import (
    ADD_ACTION,
    ARM_ENTRY_ACTION,
    BACKTEST_ACTIONS,
    BACKTEST_ENGINE_FEATURE_ID,
    BACKTEST_ENGINE_POLICY_VERSION,
    BACKTEST_REASON_CODES,
    EXIT_ACTION,
    SHARED_CALCULATION_SOURCES,
    TRAIL_ACTION,
    TRIM_ACTION,
    BacktestContext,
    BacktestIntent,
    run_backtest,
)
from btc_predictor.config import load_strategy_config
from btc_predictor.data import OhlcvBar
from btc_predictor.portfolio.account import ExecutionCosts, execution_costs_from_config
from btc_predictor.risk.budget import calculate_risk_budget
from btc_predictor.risk.sizing import calculate_initial_position_size
from btc_predictor.risk.tranches import calculate_tranche_size
from btc_predictor.signals import (
    AddRequirementsInput,
    TrimRuleInput,
    evaluate_add_requirements,
    evaluate_trim_rules,
)


UTC = timezone.utc
START = datetime(2024, 1, 1, tzinfo=UTC)
CONFIG = load_strategy_config()
NAV = "1000000"
ZONE_LOWER = Decimal("99000")
ZONE_UPPER = Decimal("101000")
STOP = Decimal("95000")


def bar(day: int, open_: str, high: str, low: str, close: str) -> OhlcvBar:
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
        provider="coinbase",
        ingested_at=timestamp + timedelta(days=1),
    )


RISING = (
    bar(0, "100000", "101000", "99000", "100500"),
    bar(1, "100500", "102000", "99500", "101500"),
    bar(2, "101500", "108000", "101000", "107000"),
    bar(3, "107000", "112000", "106000", "111000"),
    bar(4, "111000", "115000", "110000", "114000"),
    bar(5, "114000", "118000", "113000", "117000"),
    bar(6, "117000", "120000", "116000", "119000"),
)
FALLING = (
    bar(0, "100000", "101000", "99000", "100500"),
    bar(1, "100500", "102000", "99500", "101500"),
    bar(2, "101500", "102000", "94000", "94500"),
    bar(3, "94500", "95000", "92000", "93000"),
)


def entry_intent(**kwargs) -> BacktestIntent:
    base = {
        "action": ARM_ENTRY_ACTION,
        "entry_zone_lower": ZONE_LOWER,
        "entry_zone_upper": ZONE_UPPER,
        "stop_price": STOP,
        "entry_conviction": Decimal("90"),
    }
    return BacktestIntent(**{**base, **kwargs})


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


def only_entry_on_first_bar(bars=RISING):
    def strategy(context: BacktestContext) -> BacktestIntent | None:
        if context.as_of == bars[0].timestamp:
            return entry_intent()
        return None

    return strategy


def run(bars=RISING, strategy=None, **kwargs):
    return run_backtest(
        bars,
        strategy=strategy or only_entry_on_first_bar(bars),
        starting_nav=NAV,
        strategy_config=CONFIG,
        **kwargs,
    )


def test_metadata_and_action_vocabulary_are_stable() -> None:
    assert BACKTEST_ENGINE_FEATURE_ID == "EVENT_DRIVEN_BACKTEST"
    assert BACKTEST_ENGINE_POLICY_VERSION == "EVENT_DRIVEN_BACKTEST_V1"
    assert BACKTEST_ACTIONS == ("ARM_ENTRY", "ADD", "TRIM", "TRAIL", "EXIT")


# --- the shared-formula requirement --------------------------------------


def test_the_engine_declares_every_module_it_delegates_to() -> None:
    import btc_predictor.backtest.engine as engine

    source = (engine.__file__ and open(engine.__file__).read()) or ""
    for module in SHARED_CALCULATION_SOURCES:
        assert f"from {module} import" in source, module


def test_position_size_matches_the_shared_sizing_chain() -> None:
    result = run()

    # Recomputed independently through BTC-144, BTC-145 and BTC-155. If the
    # engine kept its own sizing formula this would drift.
    distance = abs(ZONE_UPPER - STOP) / ZONE_UPPER
    budget = calculate_risk_budget(
        entry_conviction="90",
        nav=NAV,
        config=CONFIG,
    )
    size = calculate_initial_position_size(
        nav=budget.nav,
        risk_fraction_nav=budget.risk_fraction_nav,
        stop_distance_fraction=distance,
        entry_price=ZONE_UPPER,
    )
    tranche = calculate_tranche_size(
        tranche_number=1,
        final_position_notional=size.position_notional,
        entry_price=ZONE_UPPER,
        config=CONFIG,
    )

    assert result.trades or result.equity_curve
    assert result.equity_curve[1].open_quantity == tranche.allocation.quantity


def test_conviction_below_the_lowest_band_produces_no_position() -> None:
    def strategy(context):
        if context.as_of == RISING[0].timestamp:
            return entry_intent(entry_conviction=Decimal("70"))
        return None

    result = run(strategy=strategy)

    # BTC-144 issues no budget below 80, so the engine cannot size a trade.
    assert "BACKTEST_ENTRY_UNSIZED" in result.reason_codes
    assert result.trades == ()


# --- point in time --------------------------------------------------------


def test_a_strategy_never_sees_a_bar_beyond_its_decision_point() -> None:
    seen: list[tuple[datetime, datetime]] = []

    def strategy(context):
        seen.append((context.as_of, context.bars[-1].timestamp))
        assert all(item.ingested_at <= context.bar.ingested_at for item in context.bars)
        return None

    run(strategy=strategy)

    assert seen
    for as_of, latest in seen:
        assert latest <= as_of


def test_a_decision_cannot_execute_on_the_bar_that_produced_it() -> None:
    result = run()

    # Armed on bar 0; the position exists only from bar 1 onward. Filling on
    # bar 0 would use information the decision could not have had.
    assert result.equity_curve[0].open_quantity == Decimal("0")
    assert result.equity_curve[1].open_quantity > 0


def test_bars_must_be_ordered_and_consistent() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        run(bars=(RISING[1], RISING[0]))
    with pytest.raises(ValueError, match="one timeframe"):
        run(bars=(RISING[0], replace(RISING[1], timeframe="1h")))
    with pytest.raises(ValueError, match="backtest symbol"):
        run(bars=(replace(RISING[0], symbol="ETH-USD"),))


def test_an_empty_run_is_reported_rather_than_failing() -> None:
    result = run(bars=())

    assert result.bar_count == 0
    assert result.reason_codes == ("BACKTEST_NO_BARS",)
    assert result.trades == ()


# --- entry zones and missed entries --------------------------------------


def test_an_entry_fills_when_the_zone_is_touched() -> None:
    result = run()

    assert "BACKTEST_ENTRY_FILLED" in result.reason_codes
    assert result.missed_entries == 0
    assert result.equity_curve[1].open_quantity > 0


def test_an_entry_whose_zone_is_never_touched_is_missed() -> None:
    away = (
        bar(0, "100000", "101000", "99000", "100500"),
        bar(1, "120000", "122000", "119000", "121000"),
        bar(2, "121000", "123000", "120000", "122000"),
    )

    result = run(bars=away, strategy=only_entry_on_first_bar(away))

    # Rulebook 25: the system is allowed to miss trades.
    assert result.missed_entries == 1
    assert "BACKTEST_ENTRY_MISSED" in result.reason_codes
    assert result.trades == ()


def test_a_short_entry_is_refused_when_config_forbids_shorts() -> None:
    def strategy(context):
        if context.as_of == RISING[0].timestamp:
            return entry_intent(direction="short", stop_price=Decimal("105000"))
        return None

    result = run(strategy=strategy)

    assert CONFIG.backtest.allow_short_trades is False
    assert "BACKTEST_SHORTS_NOT_PERMITTED" in result.reason_codes
    assert result.trades == ()


# --- structural stops -----------------------------------------------------


def test_a_structural_stop_closes_the_position_and_books_the_trade() -> None:
    result = run(bars=FALLING, strategy=only_entry_on_first_bar(FALLING))

    assert result.stopped_out == 1
    assert "BACKTEST_STOPPED_OUT" in result.reason_codes
    assert len(result.trades) == 1
    assert result.trades[0].exit_reason == "STRUCTURAL_STOP"
    assert result.trades[0].net_pnl < 0


def test_the_stop_is_checked_before_any_queued_order() -> None:
    def strategy(context):
        if context.as_of == FALLING[0].timestamp:
            return entry_intent()
        if context.position_open:
            # An exit queued on the bar before the stop-out bar. The stop is
            # adverse and OHLCV cannot order them, so the stop wins.
            return BacktestIntent(action=EXIT_ACTION, exit_reason="HOLD_SCORE_COLLAPSE")
        return None

    result = run(bars=FALLING, strategy=strategy)

    assert result.trades[0].exit_reason == "STRUCTURAL_STOP"
    assert result.stopped_out == 1


def test_a_stopped_out_trade_reports_r_against_the_planned_risk() -> None:
    result = run(bars=FALLING, strategy=only_entry_on_first_bar(FALLING))
    trade = result.trades[0]

    # A stop-out should be about -1R before costs; the gap and fees make it
    # slightly worse, which is exactly what BTC-162 and BTC-165 report.
    assert trade.r_multiple < 0
    assert trade.r_multiple > Decimal("-2")


# --- adds, trims, trailing stops -----------------------------------------


def full_lifecycle_strategy(context):
    if context.as_of == RISING[0].timestamp:
        return entry_intent()
    if context.as_of == RISING[2].timestamp:
        return BacktestIntent(action=ADD_ACTION, requirements=add_requirements())
    if context.as_of == RISING[3].timestamp:
        return BacktestIntent(
            action=TRAIL_ACTION,
            structure_price=Decimal("104000"),
            buffer=Decimal("1000"),
        )
    if context.as_of == RISING[4].timestamp:
        return BacktestIntent(action=TRIM_ACTION, trim_signal=trim_signal())
    if context.as_of == RISING[5].timestamp:
        return BacktestIntent(action=EXIT_ACTION, exit_reason="HOLD_SCORE_COLLAPSE")
    return None


def test_a_full_lifecycle_routes_through_every_shared_module() -> None:
    result = run(strategy=full_lifecycle_strategy)

    assert result.reason_codes == (
        "BACKTEST_ENTRY_FILLED",
        "BACKTEST_ADDED",
        "BACKTEST_STOP_TRAILED",
        "BACKTEST_TRIMMED",
        "BACKTEST_EXITED",
        "BACKTEST_COMPLETE",
    )
    trade = result.trades[0]
    assert trade.add_count == 1
    assert trade.trim_count == 1


def test_an_add_increases_size_from_the_same_tranche_schedule() -> None:
    result = run(strategy=full_lifecycle_strategy)

    before = result.equity_curve[2].open_quantity
    after = result.equity_curve[3].open_quantity
    assert after > before


def test_a_refused_add_leaves_the_position_untouched() -> None:
    def strategy(context):
        if context.as_of == RISING[0].timestamp:
            return entry_intent()
        if context.as_of == RISING[2].timestamp:
            return BacktestIntent(
                action=ADD_ACTION,
                requirements=add_requirements(add_score=Decimal("50")),
            )
        return None

    result = run(strategy=strategy)

    # BTC-154 refused; the engine must not add anyway.
    assert "BACKTEST_ADD_REFUSED" in result.reason_codes
    assert result.equity_curve[2].open_quantity == result.equity_curve[3].open_quantity


def test_a_trim_reduces_size_without_closing_the_position() -> None:
    result = run(strategy=full_lifecycle_strategy)

    before = result.equity_curve[4].open_quantity
    after = result.equity_curve[5].open_quantity
    assert 0 < after < before


def test_trailing_the_stop_reduces_risk_at_stop() -> None:
    result = run(strategy=full_lifecycle_strategy)

    before = result.equity_curve[3].risk_at_stop
    after = result.equity_curve[4].risk_at_stop
    # The whole point of raising a stop under new structure.
    assert after < before


def test_a_trail_that_would_loosen_the_stop_is_ignored() -> None:
    def strategy(context):
        if context.as_of == RISING[0].timestamp:
            return entry_intent()
        if context.as_of == RISING[3].timestamp:
            return BacktestIntent(
                action=TRAIL_ACTION,
                structure_price=Decimal("80000"),
                buffer=Decimal("1000"),
            )
        return None

    result = run(strategy=strategy)

    assert "BACKTEST_STOP_TRAILED" not in result.reason_codes
    assert result.equity_curve[4].risk_at_stop == result.equity_curve[3].risk_at_stop


# --- costs, NAV, risk at stop --------------------------------------------


def test_fees_and_slippage_are_charged_through_the_shared_cost_policy() -> None:
    result = run()

    assert result.account.fees_paid > 0
    # The entry filled above the bar open because a buy slips adversely.
    assert result.equity_curve[1].unrealized_pnl < (
        result.equity_curve[1].open_quantity
        * (RISING[1].close - RISING[1].open)
    )


def test_zero_cost_assumptions_leave_no_fees() -> None:
    free = ExecutionCosts(
        policy_version="EXECUTION_COST_V1",
        fee_bps=Decimal("0"),
        slippage_bps=Decimal("0"),
        funding_cost_bps_per_day=Decimal("0"),
    )

    result = run(costs=free)

    assert result.account.fees_paid == Decimal("0")
    assert result.account.funding_paid == Decimal("0")


def test_funding_accrues_daily_on_the_open_position() -> None:
    carried = replace(
        execution_costs_from_config(CONFIG),
        funding_cost_bps_per_day=Decimal("2"),
    )

    flat = run()
    charged = run(costs=carried)

    assert flat.account.funding_paid == Decimal("0")
    assert charged.account.funding_paid > 0
    # Funding is a real cost of holding, so it lowers ending NAV.
    assert charged.ending_nav < flat.ending_nav


def test_the_account_uses_the_engines_cost_policy_not_its_own() -> None:
    free = ExecutionCosts(
        policy_version="EXECUTION_COST_V1",
        fee_bps=Decimal("0"),
        slippage_bps=Decimal("0"),
        funding_cost_bps_per_day=Decimal("0"),
    )

    result = run(costs=free)

    # PaperAccount.charge_fee prices from the account's own costs. Opening the
    # account from config while executing under an override would charge the
    # configured 10 bps against zero-cost fills.
    assert result.account.costs == free
    assert result.account.fees_paid == Decimal("0")


def test_funding_is_recorded_as_replayable_events() -> None:
    carried = replace(
        execution_costs_from_config(CONFIG),
        funding_cost_bps_per_day=Decimal("2"),
    )

    result = run(strategy=full_lifecycle_strategy, costs=carried)
    trade = result.trades[0]

    # An aggregate total cannot be re-derived from evidence, so the accounting
    # layer requires the individual settlements.
    assert trade.funding > 0
    assert trade.funding == result.account.funding_paid


def test_nav_is_cash_plus_unrealized_at_every_point() -> None:
    result = run()

    for point in result.equity_curve:
        assert point.nav == point.cash + point.unrealized_pnl


def test_risk_at_stop_is_reported_only_while_a_position_is_open() -> None:
    result = run(strategy=full_lifecycle_strategy)

    for point in result.equity_curve:
        if point.open_quantity > 0:
            assert point.risk_at_stop is not None
            assert point.risk_fraction_nav is not None
        else:
            assert point.risk_at_stop is None


def test_risk_at_stop_stays_within_the_configured_ceiling() -> None:
    result = run(strategy=full_lifecycle_strategy)
    ceiling = Decimal(str(CONFIG.risk.max_risk_at_stop_fraction_nav))

    for point in result.equity_curve:
        if point.risk_fraction_nav is not None:
            assert point.risk_fraction_nav <= ceiling


# --- results --------------------------------------------------------------


def test_an_open_position_at_the_end_is_closed_and_flagged() -> None:
    result = run()

    assert "BACKTEST_POSITION_OPEN_AT_END" in result.reason_codes
    assert len(result.trades) == 1


def test_the_equity_curve_covers_every_bar() -> None:
    result = run()

    assert len(result.equity_curve) == len(RISING) == result.bar_count
    assert [point.as_of for point in result.equity_curve] == [
        item.timestamp for item in RISING
    ]


def test_record_is_persistable() -> None:
    record = run(strategy=full_lifecycle_strategy).as_record()

    assert record["feature_id"] == "EVENT_DRIVEN_BACKTEST"
    assert record["policy_version"] == "EVENT_DRIVEN_BACKTEST_V1"
    assert record["symbol"] == "BTC-USD"
    assert record["bar_count"] == len(RISING)
    assert record["trade_count"] == 1
    assert len(record["equity_curve"]) == len(RISING)
    assert record["config_metadata"]["strategy_version"] == "swing_v1.2"


def test_reason_codes_are_drawn_from_the_declared_set() -> None:
    results = [
        run(),
        run(strategy=full_lifecycle_strategy),
        run(bars=FALLING, strategy=only_entry_on_first_bar(FALLING)),
        run(bars=()),
    ]

    for result in results:
        for code in result.reason_codes:
            assert code in BACKTEST_REASON_CODES


def test_replaying_the_same_bars_is_deterministic() -> None:
    first = run(strategy=full_lifecycle_strategy)
    second = run(strategy=full_lifecycle_strategy)

    assert first.as_record() == second.as_record()


# --- validation -----------------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"action": "LIQUIDATE"}, "action must be one of"),
        ({"action": ARM_ENTRY_ACTION, "stop_price": None}, "requires stop_price"),
        (
            {"action": ARM_ENTRY_ACTION, "entry_conviction": None},
            "requires entry_conviction",
        ),
        ({"action": ADD_ACTION}, "requires a BTC-154 requirements result"),
        ({"action": TRIM_ACTION}, "requires a BTC-157 signal"),
        ({"action": TRAIL_ACTION}, "requires structure_price"),
        ({"action": EXIT_ACTION}, "requires exit_reason"),
    ],
)
def test_malformed_intents_fail_fast(kwargs, match: str) -> None:
    base = {
        "entry_zone_lower": ZONE_LOWER,
        "entry_zone_upper": ZONE_UPPER,
        "stop_price": STOP,
        "entry_conviction": Decimal("90"),
    }
    if kwargs["action"] != ARM_ENTRY_ACTION:
        base = {}

    with pytest.raises(ValueError, match=match):
        BacktestIntent(**{**base, **kwargs})


def test_a_strategy_returning_the_wrong_type_is_rejected() -> None:
    with pytest.raises(TypeError, match="BacktestIntent"):
        run(strategy=lambda context: "ENTER")


def test_a_non_callable_strategy_is_rejected() -> None:
    with pytest.raises(TypeError, match="strategy must be callable"):
        run_backtest(RISING, strategy=None)


def test_a_non_config_is_rejected() -> None:
    with pytest.raises(TypeError, match="StrategyConfig"):
        run_backtest(RISING, strategy=only_entry_on_first_bar(), strategy_config={})
