"""BTC-192: deterministic strategy and parameter-set comparisons."""

import decimal
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.backtest import (
    ARM_ENTRY_ACTION,
    EXIT_ACTION,
    BacktestIntent,
    run_backtest,
)
from btc_predictor.config import load_strategy_config
from btc_predictor.config.strategy import ConfigIdentity
from btc_predictor.data import OhlcvBar
from btc_predictor.portfolio.account import ExecutionCosts
from btc_predictor.portfolio.accounting import TradeFill, calculate_trade_accounting
from btc_predictor.portfolio.lifecycle_persistence import LifecycleProvenance
from btc_predictor.research import (
    CLOSED_TRADE_EXPECTANCY_METRIC,
    DELTA_AVAILABLE,
    DELTA_BOTH_UNAVAILABLE,
    HISTORICAL_BACKTEST,
    PAPER_TRADE,
    STRATEGY_COMPARISON_FEATURE_ID,
    STRATEGY_COMPARISON_POLICY_VERSION,
    STRATEGY_COMPARISON_PRODUCTION_STATUS,
    STRATEGY_COMPARISON_PROMOTION_TICKET,
    TRADE_OUTCOME_AVAILABLE,
    FeatureMatrixDefinition,
    FeatureMatrixProvenance,
    FeatureObservation,
    PaperTradeEntry,
    PaperTradeOutcomeDefinition,
    StrategyComparisonError,
    build_paper_trade_outcome_dataset,
    build_point_in_time_feature_matrix,
    compare_backtest_strategies,
    compare_paper_trade_strategies,
    compare_strategies,
    restore_strategy_comparison_report,
)
from btc_predictor.risk.stop import calculate_initial_stop


START = datetime(2024, 1, 1, tzinfo=UTC)
BASELINE_VERSION = "strategy_v1.0"
BASELINE_PARAMETERS = "baseline"
CANDIDATE_VERSION = "strategy_v1.1_candidate"
CANDIDATE_PARAMETERS = "candidate-a"
FREE_COSTS = ExecutionCosts(
    policy_version="EXECUTION_COST_V1",
    fee_bps=Decimal("0"),
    slippage_bps=Decimal("0"),
    funding_cost_bps_per_day=Decimal("0"),
)


def _bar(day: int, price: str) -> OhlcvBar:
    timestamp = START + timedelta(days=day)
    value = Decimal(price)
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1d",
        open=value,
        high=value + Decimal("1000"),
        low=value - Decimal("1000"),
        close=value,
        volume=Decimal("100"),
        provider="coinbase",
        ingested_at=timestamp + timedelta(days=1),
    )


BARS = tuple(
    _bar(day, price)
    for day, price in enumerate(("100000", "100000", "104000", "108000", "112000"))
)


def _config(strategy_version: str, parameter_set_id: str):
    config = load_strategy_config()
    return replace(
        config,
        identity=ConfigIdentity(
            config_version=f"config-for-{strategy_version}-{parameter_set_id}",
            strategy_version=strategy_version,
            parameter_set_id=parameter_set_id,
        ),
    )


def _result(
    strategy_version: str,
    parameter_set_id: str,
    *,
    exit_day: int = 2,
    bars=BARS,
    costs=FREE_COSTS,
):
    config = _config(strategy_version, parameter_set_id)
    stop = calculate_initial_stop(
        invalidation_price="95000",
        buffer="0",
        direction="long",
        entry_price="101000",
        config_metadata=config.run_metadata(),
    )

    def strategy(context):
        if context.bar.timestamp == bars[0].timestamp:
            return BacktestIntent(
                action=ARM_ENTRY_ACTION,
                entry_zone_lower=Decimal("99000"),
                entry_zone_upper=Decimal("101000"),
                initial_stop=stop,
                entry_conviction=Decimal("90"),
            )
        if context.bar.timestamp == bars[exit_day].timestamp:
            return BacktestIntent(
                action=EXIT_ACTION,
                exit_reason="HOLD_SCORE_COLLAPSE",
            )
        return None

    return run_backtest(
        bars,
        strategy=strategy,
        starting_nav="1000000",
        strategy_config=config,
        costs=costs,
        strategy_id=f"{strategy_version}-{parameter_set_id}",
    )


def _comparison():
    baseline = _result(BASELINE_VERSION, BASELINE_PARAMETERS, exit_day=2)
    candidate = _result(CANDIDATE_VERSION, CANDIDATE_PARAMETERS, exit_day=3)
    return compare_backtest_strategies(
        (candidate, baseline),
        baseline_strategy_version=BASELINE_VERSION,
        baseline_parameter_set_id=BASELINE_PARAMETERS,
    )


def _empty_paper_dataset(strategy_version: str, parameter_set_id: str, *, day=30):
    provenance = FeatureMatrixProvenance(
        config_version=f"config-for-{strategy_version}-{parameter_set_id}",
        strategy_version=strategy_version,
        parameter_set_id=parameter_set_id,
    )
    features = build_point_in_time_feature_matrix(
        (), (), definition=FeatureMatrixDefinition(provenance=provenance)
    )
    return build_paper_trade_outcome_dataset(
        (), {}, features, extraction_time=START + timedelta(days=day)
    )


def _paper_dataset(
    strategy_version: str,
    parameter_set_id: str,
    *,
    exit_price: str,
    extra_trades: tuple[tuple[str, str, str], ...] = (),
    outcome_names: tuple[str, ...] = ("net_pnl", "r_multiple"),
):
    metadata = {
        "config_version": f"config-for-{strategy_version}-{parameter_set_id}",
        "strategy_version": strategy_version,
        "parameter_set_id": parameter_set_id,
    }
    provenance = FeatureMatrixProvenance(**metadata)
    definition = FeatureMatrixDefinition(
        feature_names=("TREND_SCORE",), provenance=provenance
    )
    features = build_point_in_time_feature_matrix(
        (
            FeatureObservation(
                feature_name="TREND_SCORE",
                value=Decimal("80"),
                observation_time=START,
                available_at=START,
                source_id="feature-pipeline",
            ),
        ),
        (START,),
        definition=definition,
    )
    legs = (("1", "100000", exit_price), *extra_trades)
    entries = []
    accountings = {}
    for index, (quantity, entry_price, leg_exit_price) in enumerate(legs, start=1):
        reference = f"trade-{strategy_version}-{parameter_set_id}"
        if index > 1:
            reference = f"{reference}-{index}"
        entries.append(
            PaperTradeEntry(
                trade_reference=reference,
                entry_decision_timestamp=START,
                data_available_at=START,
                symbol="BTC-USD",
                direction="long",
                decision="ENTER",
                setup="BULL_TREND_CONTINUATION",
                regime="BULL",
                provenance=LifecycleProvenance(
                    recommendation_id=index,
                    strategy_version=strategy_version,
                    parameter_set_id=parameter_set_id,
                ),
                source_id="paper-campaign",
            )
        )
        fills = (
            TradeFill(
                sequence=1,
                filled_at=START + timedelta(hours=12),
                action="ENTER",
                quantity=Decimal(quantity),
                price=Decimal(entry_price),
                fee=Decimal("0"),
                source_event_id=f"entry-fill-{index}",
                execution_bar_at=START,
                execution_bar_timeframe="1d",
            ),
            TradeFill(
                sequence=2,
                filled_at=START + timedelta(days=2),
                action="EXIT",
                quantity=Decimal(quantity),
                price=Decimal(leg_exit_price),
                fee=Decimal("0"),
                source_event_id=f"exit-fill-{index}",
                execution_bar_at=START + timedelta(days=2),
                execution_bar_timeframe="1d",
            ),
        )
        accountings[reference] = calculate_trade_accounting(
            fills,
            symbol="BTC-USD",
            direction="long",
            initial_stop_price="95000",
            initial_stop_source_id="stop-1",
            exit_reason="HOLD_SCORE_COLLAPSE",
            exit_reason_source_id="exit-1",
            config_metadata=metadata,
        )
    outcome_definition = PaperTradeOutcomeDefinition(
        entry_feature_names=("TREND_SCORE",),
        outcome_names=outcome_names,
    )
    return build_paper_trade_outcome_dataset(
        tuple(entries),
        accountings,
        features,
        extraction_time=START + timedelta(days=30),
        definition=outcome_definition,
    )


def test_framework_compares_explicit_baseline_and_candidate_deterministically() -> None:
    report = _comparison()

    assert report.feature_id == STRATEGY_COMPARISON_FEATURE_ID
    assert report.policy_version == STRATEGY_COMPARISON_POLICY_VERSION
    assert report.evidence_mode == HISTORICAL_BACKTEST
    assert report.baseline.variant_id == f"{BASELINE_VERSION}:{BASELINE_PARAMETERS}"
    assert [item.variant.variant_id for item in report.arms] == [
        f"{BASELINE_VERSION}:{BASELINE_PARAMETERS}",
        f"{CANDIDATE_VERSION}:{CANDIDATE_PARAMETERS}",
    ]
    assert report == _comparison()


def test_metrics_use_closed_btc_165_outcomes_and_persist_absolute_deltas() -> None:
    report = _comparison()
    baseline = report.baseline_arm.metrics
    candidate = report.arm(CANDIDATE_VERSION, CANDIDATE_PARAMETERS).metrics
    delta = report.comparison(
        CANDIDATE_VERSION, CANDIDATE_PARAMETERS
    ).delta(CLOSED_TRADE_EXPECTANCY_METRIC)

    assert baseline.closed_trade_count == candidate.closed_trade_count == 1
    assert baseline.closed_trade_expectancy == report.arms[0].source.trades[0].net_pnl
    assert candidate.closed_trade_expectancy == report.arms[1].source.trades[0].net_pnl
    assert candidate.closed_trade_expectancy > baseline.closed_trade_expectancy
    assert delta.status == DELTA_AVAILABLE
    assert delta.absolute_delta == (
        candidate.closed_trade_expectancy - baseline.closed_trade_expectancy
    )
    assert baseline.mean_r_multiple == report.arms[0].source.trades[0].r_multiple


def test_same_strategy_version_can_compare_distinct_parameter_sets() -> None:
    baseline = _result(BASELINE_VERSION, BASELINE_PARAMETERS)
    candidate = _result(BASELINE_VERSION, "wider-exit", exit_day=3)
    report = compare_backtest_strategies(
        (baseline, candidate),
        baseline_strategy_version=BASELINE_VERSION,
        baseline_parameter_set_id=BASELINE_PARAMETERS,
    )

    assert "STRATEGY_COMPARISON_PARAMETER_SETS" in report.reason_codes
    assert "STRATEGY_COMPARISON_STRATEGY_VERSIONS" not in report.reason_codes
    assert report.arm(BASELINE_VERSION, "wider-exit").variant.parameter_set_id == (
        "wider-exit"
    )


def test_empty_backtests_do_not_zero_fill_unavailable_quality_metrics() -> None:
    baseline = run_backtest(
        (),
        strategy=lambda context: None,
        strategy_config=_config(BASELINE_VERSION, BASELINE_PARAMETERS),
        costs=FREE_COSTS,
        starting_nav="1000000",
        strategy_id="empty-baseline",
    )
    candidate = run_backtest(
        (),
        strategy=lambda context: None,
        strategy_config=_config(CANDIDATE_VERSION, CANDIDATE_PARAMETERS),
        costs=FREE_COSTS,
        starting_nav="1000000",
        strategy_id="empty-candidate",
    )
    report = compare_backtest_strategies(
        (candidate, baseline),
        baseline_strategy_version=BASELINE_VERSION,
        baseline_parameter_set_id=BASELINE_PARAMETERS,
    )
    expectancy = report.comparisons[0].delta(CLOSED_TRADE_EXPECTANCY_METRIC)

    assert report.baseline_arm.metrics.summed_net_pnl is None
    assert report.baseline_arm.metrics.mean_r_multiple is None
    assert expectancy.status == DELTA_BOTH_UNAVAILABLE
    assert expectancy.absolute_delta is None
    assert "STRATEGY_COMPARISON_NO_TRADES" in report.reason_codes


def test_paper_trade_comparison_requires_and_persists_declared_scope() -> None:
    baseline = _empty_paper_dataset(BASELINE_VERSION, BASELINE_PARAMETERS)
    candidate = _empty_paper_dataset(CANDIDATE_VERSION, CANDIDATE_PARAMETERS)
    report = compare_paper_trade_strategies(
        (candidate, baseline),
        comparison_scope_id="paper-campaign-2024-q1",
        baseline_strategy_version=BASELINE_VERSION,
        baseline_parameter_set_id=BASELINE_PARAMETERS,
    )

    assert report.evidence_mode == PAPER_TRADE
    assert report.comparison_scope_id == "paper-campaign-2024-q1"
    assert "STRATEGY_COMPARISON_PAPER_SCOPE_DECLARED" in report.reason_codes
    with pytest.raises(StrategyComparisonError, match="comparison_scope_id"):
        compare_strategies(
            (baseline, candidate),
            baseline_strategy_version=BASELINE_VERSION,
            baseline_parameter_set_id=BASELINE_PARAMETERS,
        )


def test_paper_trade_metrics_are_read_from_btc_191_outcome_cells() -> None:
    baseline = _paper_dataset(
        BASELINE_VERSION, BASELINE_PARAMETERS, exit_price="105000"
    )
    candidate = _paper_dataset(
        CANDIDATE_VERSION, CANDIDATE_PARAMETERS, exit_price="110000"
    )
    report = compare_paper_trade_strategies(
        (candidate, baseline),
        comparison_scope_id="paper-campaign-2024-q1",
        baseline_strategy_version=BASELINE_VERSION,
        baseline_parameter_set_id=BASELINE_PARAMETERS,
    )

    baseline_metrics = report.baseline_arm.metrics
    candidate_metrics = report.arm(
        CANDIDATE_VERSION, CANDIDATE_PARAMETERS
    ).metrics
    assert baseline_metrics.closed_trade_expectancy == Decimal("5000.000000000000")
    assert candidate_metrics.closed_trade_expectancy == Decimal("10000.000000000000")
    assert baseline_metrics.mean_r_multiple == Decimal("1.000000000000")
    assert candidate_metrics.mean_r_multiple == Decimal("2.000000000000")


def test_paper_trade_comparison_rejects_inconsistent_extraction_scope() -> None:
    baseline = _empty_paper_dataset(BASELINE_VERSION, BASELINE_PARAMETERS)
    candidate = _empty_paper_dataset(
        CANDIDATE_VERSION, CANDIDATE_PARAMETERS, day=31
    )

    with pytest.raises(StrategyComparisonError, match="extraction time"):
        compare_paper_trade_strategies(
            (baseline, candidate),
            comparison_scope_id="paper-campaign-2024-q1",
            baseline_strategy_version=BASELINE_VERSION,
            baseline_parameter_set_id=BASELINE_PARAMETERS,
        )


def test_historical_comparison_rejects_non_comparable_runs() -> None:
    baseline = _result(BASELINE_VERSION, BASELINE_PARAMETERS)
    changed_bars = (*BARS[:-1], _bar(4, "113000"))
    candidate = _result(
        CANDIDATE_VERSION, CANDIDATE_PARAMETERS, bars=changed_bars
    )

    with pytest.raises(StrategyComparisonError, match="share bars"):
        compare_backtest_strategies(
            (baseline, candidate),
            baseline_strategy_version=BASELINE_VERSION,
            baseline_parameter_set_id=BASELINE_PARAMETERS,
        )


def test_modes_cannot_be_blended_and_baseline_must_exist() -> None:
    baseline = _result(BASELINE_VERSION, BASELINE_PARAMETERS)
    candidate = _result(CANDIDATE_VERSION, CANDIDATE_PARAMETERS)
    paper = _empty_paper_dataset(CANDIDATE_VERSION, "paper")

    with pytest.raises(StrategyComparisonError, match="one evidence mode"):
        compare_strategies(
            (baseline, paper),
            comparison_scope_id="mixed",
            baseline_strategy_version=BASELINE_VERSION,
            baseline_parameter_set_id=BASELINE_PARAMETERS,
        )
    with pytest.raises(StrategyComparisonError, match="is not present"):
        compare_backtest_strategies(
            (baseline, candidate),
            baseline_strategy_version="unknown",
            baseline_parameter_set_id="unknown",
        )


def test_duplicate_variant_identity_is_rejected() -> None:
    first = _result(BASELINE_VERSION, BASELINE_PARAMETERS, exit_day=2)
    second = _result(BASELINE_VERSION, BASELINE_PARAMETERS, exit_day=3)

    with pytest.raises(StrategyComparisonError, match="must be unique"):
        compare_backtest_strategies(
            (first, second),
            baseline_strategy_version=BASELINE_VERSION,
            baseline_parameter_set_id=BASELINE_PARAMETERS,
        )


def test_record_round_trip_is_deterministic_and_rejects_tampering() -> None:
    report = _comparison()
    record = report.as_record()

    assert json.dumps(record, sort_keys=True) == json.dumps(
        report.as_record(), sort_keys=True
    )
    assert restore_strategy_comparison_report(record) == report

    tampered = json.loads(json.dumps(record))
    tampered["comparisons"][0]["deltas"][1]["absolute_delta"] = "999"
    with pytest.raises(StrategyComparisonError, match="does not match"):
        restore_strategy_comparison_report(tampered)


def test_comparison_is_research_only_and_cannot_imply_promotion() -> None:
    report = _comparison()

    assert report.production_status == STRATEGY_COMPARISON_PRODUCTION_STATUS
    assert report.promotion_ticket == STRATEGY_COMPARISON_PROMOTION_TICKET
    assert "STRATEGY_COMPARISON_RESEARCH_ONLY" in report.reason_codes
    assert "STRATEGY_COMPARISON_BTC_193_PROMOTION_REQUIRED" in report.reason_codes


def test_metrics_do_not_depend_on_the_ambient_decimal_context() -> None:
    # EPIC T integration review.  ``_ratio`` pinned an explicit 60-digit
    # context, but the profit factor took the magnitude of the gross loss with
    # ``abs`` in the caller's ambient context first, so one set of BTC-191
    # outcomes produced two profit factors and two evidence digests.
    baseline = _paper_dataset(
        BASELINE_VERSION,
        BASELINE_PARAMETERS,
        exit_price="300000.77",
        extra_trades=(("7", "100000.13", "12345.11"),),
    )
    candidate = _paper_dataset(
        CANDIDATE_VERSION,
        CANDIDATE_PARAMETERS,
        exit_price="400000.31",
        extra_trades=(("7", "100000.13", "9876.55"),),
    )

    def compare():
        return compare_paper_trade_strategies(
            (baseline, candidate),
            comparison_scope_id="paper-campaign-2024-q1",
            baseline_strategy_version=BASELINE_VERSION,
            baseline_parameter_set_id=BASELINE_PARAMETERS,
        )

    report = compare()
    record = report.as_record()
    assert report.baseline_arm.metrics.gross_loss == Decimal("-613585.14")
    assert report.baseline_arm.metrics.profit_factor is not None

    for precision in (14, 10, 8, 6):
        with decimal.localcontext() as context:
            context.prec = precision
            assert compare().as_record() == record
            assert restore_strategy_comparison_report(record) == report


def test_paper_evidence_must_declare_the_outcome_columns_the_metrics_read() -> None:
    # EPIC T integration review.  A BTC-191 dataset may narrow its declared
    # outcome columns.  Reading an undeclared column as ``None`` reported every
    # closed trade as an outcome BTC-165 could not measure, without the BTC-165
    # reason code BTC-191 requires such a claim to cite.
    baseline = _paper_dataset(
        BASELINE_VERSION, BASELINE_PARAMETERS, exit_price="105000"
    )
    narrowed = _paper_dataset(
        CANDIDATE_VERSION,
        CANDIDATE_PARAMETERS,
        exit_price="110000",
        outcome_names=("holding_days",),
    )

    assert narrowed.rows[0].outcome("holding_days").status == TRADE_OUTCOME_AVAILABLE
    with pytest.raises(StrategyComparisonError, match="net_pnl, r_multiple"):
        compare_paper_trade_strategies(
            (baseline, narrowed),
            comparison_scope_id="paper-campaign-2024-q1",
            baseline_strategy_version=BASELINE_VERSION,
            baseline_parameter_set_id=BASELINE_PARAMETERS,
        )
