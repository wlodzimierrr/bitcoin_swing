"""EPIC S integration audit: BTC-180 through BTC-185 composed.

The ticket suites each prove their own module. These tests ask the epic
question instead: whether the backtest engine, the cost ladder, walk-forward
validation, and the two out-of-sample reports still agree once they are
stacked on top of one another.
"""

from __future__ import annotations

import copy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.backtest import (
    ADD_ACTION,
    ARM_ENTRY_ACTION,
    BACKTEST_RECONCILIATION_TOLERANCE,
    COST_PROFILES,
    EXIT_ACTION,
    SETUP_DIMENSION,
    TRIM_ACTION,
    BacktestContext,
    BacktestIntent,
    FoldStrategy,
    TrainingWindow,
    regime_performance_context,
    restore_setup_performance_report,
    run_backtest,
    run_setup_performance_report,
    run_walk_forward,
    walk_forward_plan,
)
from btc_predictor.config import load_strategy_config
from btc_predictor.config.strategy import ConfigIdentity
from btc_predictor.data import OhlcvBar
from btc_predictor.features.regime import calculate_regime_classification
from btc_predictor.features.setup import (
    BullTrendContinuationInput,
    detect_bull_trend_continuation,
)
from btc_predictor.features.volatility import (
    VolatilityScoreInput,
    calculate_volatility_score,
)
from btc_predictor.portfolio.account import execution_costs_from_config
from btc_predictor.risk.stop import calculate_initial_stop
from btc_predictor.signals import (
    AddRequirementsInput,
    TrimRuleInput,
    evaluate_add_requirements,
    evaluate_trim_rules,
)


START = datetime(2024, 1, 1, tzinfo=UTC)
CONFIG = load_strategy_config()
METADATA = CONFIG.run_metadata()
NAV = "1000000"

FOREIGN_CONFIG = replace(
    CONFIG,
    identity=ConfigIdentity(
        config_version=CONFIG.identity.config_version,
        strategy_version=CONFIG.identity.strategy_version,
        parameter_set_id="btc185-candidate-007",
    ),
)


def bar(day: int, *, rising: bool = True, ingested_days: int | None = None) -> OhlcvBar:
    timestamp = START + timedelta(days=day)
    step = 500 if rising else -500
    base = Decimal(100000 + day * step)
    ingested = timestamp + timedelta(days=1 if ingested_days is None else 0)
    if ingested_days is not None:
        ingested = START + timedelta(days=ingested_days)
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1d",
        open=base,
        high=base + 1500,
        low=base - 1000,
        close=base + step,
        volume=Decimal("100"),
        provider="coinbase",
        ingested_at=ingested,
    )


RISING = tuple(bar(day) for day in range(21))


def arm(context: BacktestContext, *, direction: str = "long", tag: str = "a") -> BacktestIntent:
    close = context.bar.close
    invalidation = close * (Decimal("0.9") if direction == "long" else Decimal("1.1"))
    return BacktestIntent(
        action=ARM_ENTRY_ACTION,
        direction=direction,
        entry_zone_lower=close * Decimal("0.97"),
        entry_zone_upper=close * Decimal("1.03"),
        initial_stop=calculate_initial_stop(
            invalidation_price=invalidation,
            buffer=Decimal("0"),
            direction=direction,
            entry_price=close,
            config_metadata=METADATA,
        ),
        entry_conviction=Decimal("90"),
        source_id=f"entry-{tag}-{context.bar.timestamp.date()}",
    )


def enter_on_first_bar(context: BacktestContext) -> BacktestIntent | None:
    if context.bar.timestamp != context.bars[0].timestamp:
        return None
    return arm(context)


def add_requirements(*, config=CONFIG):
    return evaluate_add_requirements(
        AddRequirementsInput(
            position_profitable=True,
            new_structural_confirmation=True,
            signed_risk_improvement=Decimal("1500"),
            regime_supportive=True,
            flow_supportive=True,
            positioning_healthy=True,
            add_score=Decimal("90"),
            projected_risk_at_stop_within_maximum=True,
        ),
        strategy_config=config,
    )


def trim_signal(*, config=CONFIG):
    return evaluate_trim_rules(
        TrimRuleInput(
            position_open=True,
            hold_score=Decimal("45"),
            euphoria_active=False,
            crowding_active=False,
            current_flow_score=Decimal("50"),
            prior_flow_score=Decimal("60"),
        ),
        strategy_config=config,
    )


# --- BTC-180 holds every strategy-supplied decision to the run's identity ---


@pytest.mark.parametrize(
    ("action", "field", "builder", "message"),
    [
        (ADD_ACTION, "requirements", add_requirements, "add requirements"),
        (TRIM_ACTION, "trim_signal", trim_signal, "trim signal"),
    ],
)
def test_a_decision_from_another_parameter_set_cannot_authorise_a_mutation(
    action: str, field: str, builder, message: str
) -> None:
    """BTC-185 varies add and hold thresholds through ``parameter_set_id``.

    A BTC-154 or BTC-157 result fitted under one parameter set must not book
    an economic mutation inside a run that declares another, or a sweep would
    compare candidates that all traded on the same evidence.
    """

    def strategy(context: BacktestContext) -> BacktestIntent | None:
        if context.bar.timestamp == RISING[0].timestamp:
            return arm(context)
        if context.bar.timestamp == RISING[2].timestamp:
            return BacktestIntent(
                action=action,
                source_id="foreign-decision",
                **{field: builder(config=FOREIGN_CONFIG)},
            )
        return None

    with pytest.raises(ValueError, match=f"{message} config_metadata"):
        run_backtest(
            RISING[:6],
            strategy=strategy,
            starting_nav=NAV,
            strategy_config=CONFIG,
        )


@pytest.mark.parametrize(
    ("action", "field", "builder"),
    [
        (ADD_ACTION, "requirements", add_requirements),
        (TRIM_ACTION, "trim_signal", trim_signal),
    ],
)
def test_the_same_decision_from_the_run_s_own_parameter_set_executes(
    action: str, field: str, builder
) -> None:
    def strategy(context: BacktestContext) -> BacktestIntent | None:
        if context.bar.timestamp == RISING[0].timestamp:
            return arm(context)
        if context.bar.timestamp == RISING[2].timestamp:
            return BacktestIntent(
                action=action,
                source_id="own-decision",
                **{field: builder()},
            )
        return None

    result = run_backtest(
        RISING[:6],
        strategy=strategy,
        starting_nav=NAV,
        strategy_config=CONFIG,
    )

    assert result.trades[0].add_count + result.trades[0].trim_count == 1


# --- a decision's identity is unique per decision, not per availability ----


def test_a_backfilled_dataset_gives_every_decision_a_distinct_identity() -> None:
    """``derive_ohlcv_bars`` stamps one ingestion time on a whole backfill.

    Every bar then becomes decision-available at the same instant, so an
    identity minted from that instant collides across unrelated decisions.
    ``source_id`` is the key BTC-165 carries on every fill and the key BTC-183
    joins entry contexts on, so BTC-180 mints it from the decision bar, which
    the bar contract keeps strictly increasing.
    """

    bars = tuple(bar(day, ingested_days=6) for day in range(6))
    assert len({item.ingested_at for item in bars}) == 1

    result = run_backtest(
        bars,
        strategy=lambda _context: BacktestIntent(
            action=EXIT_ACTION, exit_reason="RESEARCH_EXIT"
        ),
        starting_nav=NAV,
        strategy_config=CONFIG,
    )

    refusals = [
        event
        for event in result.events
        if event.event_type == "INTENT" and event.status == "REFUSED"
    ]
    assert len(refusals) == len(bars)
    assert len({event.source_id for event in refusals}) == len(bars)
    assert [event.source_id for event in refusals] == [
        f"exit-{item.timestamp.isoformat()}" for item in bars
    ]


def test_a_backfilled_dataset_says_why_no_decision_can_execute() -> None:
    """The cause is the dataset's availability, not the strategy's bookkeeping."""

    bars = tuple(bar(day, ingested_days=6) for day in range(6))

    with pytest.raises(ValueError, match="never reaches"):
        run_backtest(
            bars,
            strategy=lambda context: arm(context, tag=str(context.bar.timestamp.date())),
            starting_nav=NAV,
            strategy_config=CONFIG,
        )


def test_a_fill_is_never_stamped_ahead_of_bars_the_run_still_replays() -> None:
    """A dataset whose execution bar arrives after the following bar's start.

    The engine cannot place that fill in the replay's own timeline, and it
    must not open a position on it. It fails closed inside the BTC-162 stop
    owner rather than carrying a position through bars that precede it.
    """

    bars = (
        bar(0, ingested_days=1),
        bar(1, ingested_days=4),
        bar(2, ingested_days=4),
        bar(3, ingested_days=4),
        bar(4, ingested_days=5),
    )

    with pytest.raises(ValueError, match="first eligible bar"):
        run_backtest(
            bars,
            strategy=enter_on_first_bar,
            starting_nav=NAV,
            strategy_config=CONFIG,
        )


# --- BTC-181 reprices a run without reordering the ladder -----------------


def test_the_cost_ladder_never_makes_a_dearer_rung_look_cheaper() -> None:
    totals = {
        profile: run_backtest(
            RISING[:10],
            strategy=enter_on_first_bar,
            starting_nav=NAV,
            strategy_config=CONFIG,
            cost_profile=profile,
        ).total_pnl
        for profile in COST_PROFILES
    }

    assert totals["optimistic"] > totals["base"] > totals["stress"]


# --- BTC-182 windows do not move when history is appended ------------------


def test_appending_future_bars_leaves_every_earlier_fold_identical() -> None:
    plan = walk_forward_plan(CONFIG, train_periods=4, test_periods=4, step_periods=4)

    def factory(_window: TrainingWindow) -> FoldStrategy:
        return FoldStrategy(strategy=enter_on_first_bar, strategy_id="epic-s-fixed")

    shorter = run_walk_forward(
        RISING[:16], strategy_factory=factory, plan=plan,
        starting_nav=NAV, strategy_config=CONFIG,
    )
    longer = run_walk_forward(
        RISING, strategy_factory=factory, plan=plan,
        starting_nav=NAV, strategy_config=CONFIG,
    )

    assert longer.fold_count > shorter.fold_count
    assert [fold.as_record() for fold in longer.folds][: shorter.fold_count] == [
        fold.as_record() for fold in shorter.folds
    ]


# --- BTC-180..184 composed -------------------------------------------------


def mixed_fold_strategy(context: BacktestContext) -> BacktestIntent | None:
    """Close one trade inside a fold, then leave a second one open."""

    index = len(context.bars) - 1
    if index == 0:
        return arm(context, tag="a")
    if index == 2 and context.position_open:
        return BacktestIntent(
            action=EXIT_ACTION,
            exit_reason="RESEARCH_EXIT",
            source_id=f"exit-{context.bar.timestamp.date()}",
        )
    if index == 4 and not context.position_open:
        return arm(context, tag="b")
    return None


def mixed_validation():
    plan = walk_forward_plan(CONFIG, train_periods=4, test_periods=8, step_periods=8)

    def factory(_window: TrainingWindow) -> FoldStrategy:
        return FoldStrategy(strategy=mixed_fold_strategy, strategy_id="epic-s-mixed")

    return run_walk_forward(
        RISING, strategy_factory=factory, plan=plan,
        starting_nav=NAV, strategy_config=CONFIG,
    )


def entry_contexts(validation):
    contexts = []
    for fold in validation.folds:
        for trade in fold.result.trades:
            entry_source_id = trade.fills[0].source_event_id
            queued = next(
                event
                for event in fold.result.events
                if event.event_type == "INTENT"
                and event.action == ARM_ENTRY_ACTION
                and event.status == "QUEUED"
                and event.source_id == entry_source_id
            )
            contexts.append(
                regime_performance_context(
                    fold_number=fold.fold_number,
                    entry_source_id=entry_source_id,
                    decision_at=queued.occurred_at,
                    evidence_available_at=queued.occurred_at,
                    regime=calculate_regime_classification(
                        Decimal("70"), config_metadata=METADATA
                    ),
                    volatility=calculate_volatility_score(
                        VolatilityScoreInput(
                            compression_ratio=Decimal("1"),
                            orderliness_score=Decimal("100"),
                            volatility_percentile=Decimal("50"),
                        ),
                        config_metadata=METADATA,
                    ),
                    setup=detect_bull_trend_continuation(
                        BullTrendContinuationInput(
                            regime_score=Decimal("70"),
                            trend_score=Decimal("80"),
                            flow_score=Decimal("70"),
                            positioning_score=Decimal("70"),
                            structure_score=Decimal("80"),
                            stress_flagged=False,
                            severe_crowding_flagged=False,
                            risk_reward=Decimal("3"),
                        ),
                        config_metadata=METADATA,
                    ),
                )
            )
    return contexts


def test_the_reports_reconcile_to_the_sum_of_independent_fold_nav_changes() -> None:
    validation = mixed_validation()
    report = run_setup_performance_report(validation, entry_contexts(validation))
    breakdown = report.source_breakdown

    closed = sum(1 for fold in validation.folds for trade in fold.result.trades if trade.closed)
    still_open = sum(
        1 for fold in validation.folds for trade in fold.result.trades if not trade.closed
    )
    assert closed and still_open

    # BTC-180 states the tolerance the marked NAV path reconciles within; the
    # attribution keeps digits the Decimal context drops out of a NAV subtraction.
    fold_total = sum((fold.total_pnl for fold in validation.folds), Decimal("0"))
    assert abs(breakdown.overall.total_pnl - fold_total) <= BACKTEST_RECONCILIATION_TOLERANCE

    setups = breakdown.breakdown(SETUP_DIMENSION)
    assert sum(bucket.trade_count for bucket in setups.buckets) == breakdown.trade_count
    assert sum((row.total_pnl for row in report.setups), Decimal("0")) == (
        breakdown.overall.total_pnl
    )
    assert sum((row.realized_net_pnl for row in report.setups), Decimal("0")) == sum(
        (trade.net_pnl for fold in validation.folds for trade in fold.result.trades),
        Decimal("0"),
    )


def test_the_composed_report_replays_and_rejects_tampering_in_nested_evidence() -> None:
    validation = mixed_validation()
    report = run_setup_performance_report(validation, entry_contexts(validation))
    record = report.as_record()

    assert restore_setup_performance_report(copy.deepcopy(record)) == report

    edited_trade = copy.deepcopy(record)
    folds = edited_trade["source_breakdown"]["validation"]["folds"]
    folds[0]["result"]["trades"][0]["net_pnl"] = "999999"
    with pytest.raises(ValueError):
        restore_setup_performance_report(edited_trade)

    edited_mark = copy.deepcopy(record)
    curve = edited_mark["source_breakdown"]["validation"]["folds"][0]["result"]["equity_curve"]
    curve[-1]["unrealized_pnl"] = str(
        Decimal(curve[-1]["unrealized_pnl"]) + Decimal("1000")
    )
    with pytest.raises(ValueError):
        restore_setup_performance_report(edited_mark)


# --- long/short mirror through the shared owners ---------------------------


def test_a_mirrored_short_pays_the_opposite_carry_and_profits_as_price_falls() -> None:
    short_config = replace(
        CONFIG, backtest=replace(CONFIG.backtest, allow_short_trades=True)
    )
    carried = replace(
        execution_costs_from_config(short_config),
        funding_cost_bps_per_day=Decimal("4"),
    )
    falling = tuple(bar(day, rising=False) for day in range(10))
    rising = tuple(bar(day) for day in range(10))

    short_run = run_backtest(
        falling,
        strategy=lambda context: arm(context, direction="short")
        if context.bar.timestamp == falling[0].timestamp
        else None,
        starting_nav=NAV,
        strategy_config=short_config,
        costs=carried,
    )
    long_run = run_backtest(
        rising,
        strategy=enter_on_first_bar,
        starting_nav=NAV,
        strategy_config=short_config,
        costs=carried,
    )

    assert short_run.account.funding_paid < 0 < long_run.account.funding_paid
    assert short_run.total_pnl > 0 and long_run.total_pnl > 0
    assert short_run.final_lifecycle.direction == "short"
    assert short_run.final_lifecycle.stop_price > falling[0].close
    assert long_run.final_lifecycle.stop_price < rising[0].close
