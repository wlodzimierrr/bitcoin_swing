"""BTC-183: deterministic regime performance breakdown."""

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.backtest import (
    ARM_ENTRY_ACTION,
    BEAR_BUCKET,
    BULL_BUCKET,
    ENTRY_CONTEXT_POLICY_VERSION,
    ETF_ERA_BUCKET,
    ETF_ERA_BUCKETS,
    ETF_ERA_DIMENSION,
    ETF_ERA_POLICY_VERSION,
    HIGH_VOL_BUCKET,
    LOW_VOL_BUCKET,
    MARKET_REGIME_BUCKET_POLICY_VERSION,
    MARKET_REGIME_BUCKETS,
    MARKET_REGIME_DIMENSION,
    NEUTRAL_BUCKET,
    OPEN_TRADE_MARK_POLICY_VERSION,
    PRE_ETF_BUCKET,
    REGIME_PERFORMANCE_DIMENSIONS,
    REGIME_PERFORMANCE_FEATURE_ID,
    REGIME_PERFORMANCE_POLICY_VERSION,
    REGIME_PERFORMANCE_REASON_CODES,
    SETUP_BUCKETS,
    SETUP_DIMENSION,
    US_SPOT_BITCOIN_ETF_ERA_START,
    VOLATILITY_BUCKET_POLICY_VERSION,
    VOLATILITY_BUCKETS,
    VOLATILITY_DIMENSION,
    BacktestContext,
    BacktestIntent,
    FoldStrategy,
    TrainingWindow,
    regime_performance_context,
    restore_regime_performance_breakdown,
    run_regime_performance_breakdown,
    run_walk_forward,
    walk_forward_plan,
)
from btc_predictor.config import load_strategy_config
from btc_predictor.data import OhlcvBar
from btc_predictor.features.regime import calculate_regime_classification
from btc_predictor.features.setup import (
    BEARISH_DISTRIBUTION_SETUP,
    BULLISH_RESET_SETUP,
    BULL_TREND_CONTINUATION_SETUP,
    CAPITULATION_REVERSAL_SETUP,
    BearishDistributionInput,
    BullishResetInput,
    BullTrendContinuationInput,
    CapitulationReversalInput,
    detect_bearish_distribution,
    detect_bullish_reset,
    detect_bull_trend_continuation,
    detect_capitulation_reversal,
)
from btc_predictor.features.volatility import (
    VOLATILITY_REGIME_VERSION,
    VolatilityScoreInput,
    calculate_volatility_score,
)
from btc_predictor.risk.stop import calculate_initial_stop


START = datetime(2024, 1, 1, tzinfo=UTC)
CONFIG = load_strategy_config()
METADATA = CONFIG.run_metadata()
NAV = "1000000"


def bar(day: int) -> OhlcvBar:
    timestamp = START + timedelta(days=day)
    base = Decimal(100000 + day * 500)
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1d",
        open=base,
        high=base + Decimal("1500"),
        low=base - Decimal("1000"),
        close=base + Decimal("500"),
        volume=Decimal("100"),
        provider="coinbase",
        ingested_at=timestamp + timedelta(days=1),
    )


BARS = tuple(bar(day) for day in range(12))


def enter_and_hold(context: BacktestContext) -> BacktestIntent | None:
    if context.bar.timestamp != context.bars[0].timestamp:
        return None
    close = context.bar.close
    return BacktestIntent(
        action=ARM_ENTRY_ACTION,
        entry_zone_lower=close * Decimal("0.97"),
        entry_zone_upper=close * Decimal("1.03"),
        initial_stop=calculate_initial_stop(
            invalidation_price=close * Decimal("0.9"),
            buffer=Decimal("0"),
            direction="long",
            entry_price=close,
            config_metadata=METADATA,
        ),
        entry_conviction=Decimal("90"),
        source_id=f"entry-{context.as_of.isoformat()}",
    )


def enter_then_exit(context: BacktestContext) -> BacktestIntent | None:
    if context.bar.timestamp == context.bars[0].timestamp:
        close = context.bar.close
        return BacktestIntent(
            action=ARM_ENTRY_ACTION,
            entry_zone_lower=close * Decimal("0.97"),
            entry_zone_upper=close * Decimal("1.03"),
            initial_stop=calculate_initial_stop(
                invalidation_price=close * Decimal("0.9"),
                buffer=Decimal("0"),
                direction="long",
                entry_price=close,
                config_metadata=METADATA,
            ),
            entry_conviction=Decimal("90"),
            source_id=f"entry-{context.as_of.isoformat()}",
        )
    if context.position_open and context.bar.timestamp == context.bars[1].timestamp:
        return BacktestIntent(
            action="EXIT",
            exit_reason="TEST_EXIT",
            source_id=f"exit-{context.as_of.isoformat()}",
        )
    return None


def stand_aside(context: BacktestContext) -> BacktestIntent | None:
    return None


def factory(strategy=enter_and_hold):
    def select(window: TrainingWindow) -> FoldStrategy:
        return FoldStrategy(strategy=strategy, strategy_id="btc183-test-rule")

    return select


def validation(strategy=enter_and_hold, *, bars=BARS, test_periods=2):
    plan = walk_forward_plan(
        CONFIG,
        train_periods=3,
        test_periods=test_periods,
        step_periods=test_periods,
    )
    return run_walk_forward(
        bars,
        strategy_factory=factory(strategy),
        plan=plan,
        starting_nav=NAV,
        strategy_config=CONFIG,
    )


def setup_result(setup=BULL_TREND_CONTINUATION_SETUP):
    if setup == BULL_TREND_CONTINUATION_SETUP:
        return detect_bull_trend_continuation(
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
        )
    if setup == BULLISH_RESET_SETUP:
        return detect_bullish_reset(
            BullishResetInput(
                regime_score=Decimal("70"),
                trend_score=Decimal("70"),
                correction_from_local_high_fraction=Decimal("0.10"),
                funding_health_history=tuple(Decimal(value) for value in range(8)),
                oi_health_history=(Decimal("70"),) * 8,
                flow_accel_history=tuple(Decimal(value) for value in range(6)),
                structure_score=Decimal("80"),
                entry_trigger_confirmed=True,
                entry_conviction_score=Decimal("90"),
                risk_reward=Decimal("3"),
            ),
            config_metadata=METADATA,
        )
    if setup == CAPITULATION_REVERSAL_SETUP:
        return detect_capitulation_reversal(
            CapitulationReversalInput(
                capitulation_flagged=True,
                capitulation_detected_at=START,
                confirmation_triggered=True,
                confirmation_at=START + timedelta(days=1),
                structure_score=Decimal("70"),
                entry_conviction_score=Decimal("90"),
                risk_reward=Decimal("3"),
            ),
            config_metadata=METADATA,
        )
    if setup == BEARISH_DISTRIBUTION_SETUP:
        return detect_bearish_distribution(
            BearishDistributionInput(
                regime_score=Decimal("30"),
                trend_score=Decimal("30"),
                flow_score=Decimal("30"),
                positioning_score=Decimal("30"),
                structure_score=Decimal("40"),
                entry_conviction_score=Decimal("90"),
                risk_reward=Decimal("3"),
                distribution_flagged=True,
                short_trigger_confirmed=True,
                stress_flagged=False,
            ),
            config_metadata=METADATA,
        )
    raise ValueError(setup)


def feature_context(
    *,
    fold_number: int = 1,
    source_id: str = "entry-source",
    decision_at: datetime = START,
    score: str = "70",
    volatility_percentile: str = "50",
    setup: str = BULL_TREND_CONTINUATION_SETUP,
):
    return regime_performance_context(
        fold_number=fold_number,
        entry_source_id=source_id,
        decision_at=decision_at,
        evidence_available_at=decision_at,
        regime=calculate_regime_classification(
            Decimal(score), config_metadata=METADATA
        ),
        volatility=calculate_volatility_score(
            VolatilityScoreInput(
                compression_ratio=Decimal("1"),
                orderliness_score=Decimal("100"),
                volatility_percentile=Decimal(volatility_percentile),
            ),
            config_metadata=METADATA,
        ),
        setup=setup_result(setup),
    )


def contexts_for(source_validation, classifications=None):
    values = classifications or (("70", "50"),) * source_validation.fold_count
    contexts = []
    for fold, (score, percentile) in zip(source_validation.folds, values, strict=True):
        trade = fold.result.trades[0]
        source_id = trade.fills[0].source_event_id
        event = next(
            item
            for item in fold.result.events
            if item.event_type == "INTENT"
            and item.action == ARM_ENTRY_ACTION
            and item.status == "QUEUED"
            and item.source_id == source_id
        )
        contexts.append(
            feature_context(
                fold_number=fold.fold_number,
                source_id=source_id,
                decision_at=event.occurred_at,
                score=score,
                volatility_percentile=percentile,
            )
        )
    return tuple(contexts)


def bucket(report, dimension, name):
    return next(
        item for item in report.breakdown(dimension).buckets if item.bucket == name
    )


def test_policy_and_bucket_vocabularies_are_versioned() -> None:
    assert REGIME_PERFORMANCE_FEATURE_ID == "REGIME_PERFORMANCE_BREAKDOWN"
    assert REGIME_PERFORMANCE_POLICY_VERSION == "REGIME_PERFORMANCE_BREAKDOWN_V1"
    assert ENTRY_CONTEXT_POLICY_VERSION == "FILLED_ENTRY_DECISION_CONTEXT_V1"
    assert MARKET_REGIME_BUCKET_POLICY_VERSION.endswith("_V1")
    assert VOLATILITY_BUCKET_POLICY_VERSION.endswith("_V1")
    assert ETF_ERA_POLICY_VERSION.endswith("_V1")
    assert OPEN_TRADE_MARK_POLICY_VERSION == "FOLD_END_MARK_TO_MARKET_V1"
    assert US_SPOT_BITCOIN_ETF_ERA_START == datetime(2024, 1, 11, tzinfo=UTC)
    assert MARKET_REGIME_BUCKETS == (BULL_BUCKET, BEAR_BUCKET, NEUTRAL_BUCKET)
    assert VOLATILITY_BUCKETS == (HIGH_VOL_BUCKET, LOW_VOL_BUCKET)
    assert ETF_ERA_BUCKETS == (PRE_ETF_BUCKET, ETF_ERA_BUCKET)
    assert REGIME_PERFORMANCE_DIMENSIONS == (
        MARKET_REGIME_DIMENSION,
        VOLATILITY_DIMENSION,
        ETF_ERA_DIMENSION,
        SETUP_DIMENSION,
    )


@pytest.mark.parametrize(
    ("score", "expected_regime", "expected_bucket"),
    [
        ("90", "STRONG_BULL", BULL_BUCKET),
        ("70", "BULL", BULL_BUCKET),
        ("60", "MILD_BULL", BULL_BUCKET),
        ("50", "NEUTRAL", NEUTRAL_BUCKET),
        ("40", "MILD_BEAR", BEAR_BUCKET),
        ("30", "BEAR", BEAR_BUCKET),
        ("10", "STRONG_BEAR", BEAR_BUCKET),
    ],
)
def test_rulebook_regimes_collapse_without_rescoring(
    score: str,
    expected_regime: str,
    expected_bucket: str,
) -> None:
    context = feature_context(score=score)

    assert context.regime == expected_regime
    assert context.market_regime_bucket == expected_bucket
    assert context.regime_record["score"] == score


@pytest.mark.parametrize(
    ("percentile", "expected_regime", "expected_bucket"),
    [
        ("10", "COMPRESSED", LOW_VOL_BUCKET),
        ("50", "NORMAL", LOW_VOL_BUCKET),
        ("80", "ELEVATED", HIGH_VOL_BUCKET),
        ("99", "STRESSED", HIGH_VOL_BUCKET),
    ],
)
def test_existing_volatility_regimes_collapse_at_the_normal_elevated_boundary(
    percentile: str,
    expected_regime: str,
    expected_bucket: str,
) -> None:
    context = feature_context(volatility_percentile=percentile)

    assert context.volatility_regime == expected_regime
    assert context.volatility_bucket == expected_bucket
    assert (
        context.volatility_record["volatility_regime_version"]
        == VOLATILITY_REGIME_VERSION
    )


def test_etf_era_uses_the_entry_decision_timestamp_boundary() -> None:
    before = feature_context(decision_at=US_SPOT_BITCOIN_ETF_ERA_START - timedelta(seconds=1))
    boundary = feature_context(decision_at=US_SPOT_BITCOIN_ETF_ERA_START)

    assert before.etf_era_bucket == PRE_ETF_BUCKET
    assert boundary.etf_era_bucket == ETF_ERA_BUCKET


@pytest.mark.parametrize("setup", SETUP_BUCKETS)
def test_each_phase_one_setup_type_is_retained_verbatim(setup: str) -> None:
    context = feature_context(setup=setup)

    assert context.setup == setup
    assert context.setup_record["setup"] == setup
    assert context.setup_record["detected"] is True


def test_entry_context_rejects_future_or_incomplete_evidence() -> None:
    complete_volatility = calculate_volatility_score(
        VolatilityScoreInput(
            compression_ratio=Decimal("1"),
            orderliness_score=Decimal("100"),
            volatility_percentile=Decimal("50"),
        ),
        config_metadata=METADATA,
    )
    with pytest.raises(ValueError, match="complete regime"):
        regime_performance_context(
            fold_number=1,
            entry_source_id="entry",
            decision_at=START,
            evidence_available_at=START,
            regime=calculate_regime_classification(None, config_metadata=METADATA),
            volatility=complete_volatility,
            setup=setup_result(),
        )
    with pytest.raises(ValueError, match="point-in-time|must not follow"):
        regime_performance_context(
            fold_number=1,
            entry_source_id="entry",
            decision_at=START,
            evidence_available_at=START + timedelta(seconds=1),
            regime=calculate_regime_classification(
                Decimal("70"), config_metadata=METADATA
            ),
            volatility=complete_volatility,
            setup=setup_result(),
        )


def test_report_attributes_all_four_axes_and_reconciles_open_marks() -> None:
    source = validation()
    contexts = contexts_for(
        source,
        (("90", "10"), ("50", "80"), ("30", "99"), ("70", "50")),
    )

    report = run_regime_performance_breakdown(source, contexts)

    assert report.trade_count == 4
    assert report.overall.open_trade_count == 4
    assert report.overall.closed_trade_count == 0
    assert report.overall.marked_unrealized_pnl != 0
    assert report.overall.total_pnl == sum(
        (fold.total_pnl for fold in source.folds), Decimal("0")
    )
    assert bucket(report, MARKET_REGIME_DIMENSION, BULL_BUCKET).trade_count == 2
    assert bucket(report, MARKET_REGIME_DIMENSION, BEAR_BUCKET).trade_count == 1
    assert bucket(report, MARKET_REGIME_DIMENSION, NEUTRAL_BUCKET).trade_count == 1
    assert bucket(report, VOLATILITY_DIMENSION, HIGH_VOL_BUCKET).trade_count == 2
    assert bucket(report, VOLATILITY_DIMENSION, LOW_VOL_BUCKET).trade_count == 2
    assert bucket(report, ETF_ERA_DIMENSION, PRE_ETF_BUCKET).trade_count == 3
    assert bucket(report, ETF_ERA_DIMENSION, ETF_ERA_BUCKET).trade_count == 1
    assert bucket(
        report, SETUP_DIMENSION, BULL_TREND_CONTINUATION_SETUP
    ).trade_count == 4
    assert tuple(
        item.bucket for item in report.breakdown(SETUP_DIMENSION).buckets
    ) == SETUP_BUCKETS
    for breakdown in report.breakdowns:
        assert sum(item.trade_count for item in breakdown.buckets) == 4
        assert sum(
            (item.total_pnl for item in breakdown.buckets), Decimal("0")
        ) == report.overall.total_pnl
    assert "REGIME_PERFORMANCE_OPEN_TRADES_MARKED" in report.reason_codes


def test_closed_trade_metrics_use_net_pnl_and_realized_r() -> None:
    source = validation(
        enter_then_exit,
        bars=tuple(bar(day) for day in range(11)),
        test_periods=4,
    )
    report = run_regime_performance_breakdown(source, contexts_for(source))

    assert report.trade_count == 2
    assert report.overall.closed_trade_count == 2
    assert report.overall.open_trade_count == 0
    assert report.overall.winning_closed_trades == 2
    assert report.overall.losing_closed_trades == 0
    assert report.overall.closed_trade_win_rate == Decimal("1.000000000000")
    assert report.overall.r_multiple_count == 2
    assert report.overall.mean_r_multiple is not None
    assert report.overall.marked_unrealized_pnl == 0
    assert report.overall.total_pnl == report.overall.realized_net_pnl
    assert "REGIME_PERFORMANCE_OPEN_TRADES_MARKED" not in report.reason_codes


def test_no_trade_validation_returns_declared_empty_buckets() -> None:
    source = validation(stand_aside)
    report = run_regime_performance_breakdown(source, ())

    assert report.trade_count == 0
    assert report.overall.total_pnl == 0
    assert report.overall.mean_r_multiple is None
    assert report.overall.closed_trade_win_rate is None
    assert all(
        bucket.trade_count == 0
        for breakdown in report.breakdowns
        for bucket in breakdown.buckets
    )
    assert "REGIME_PERFORMANCE_NO_TRADES" in report.reason_codes
    assert report.reason_codes[-1] == "REGIME_PERFORMANCE_COMPLETE"


def test_every_filled_trade_requires_exactly_one_context() -> None:
    source = validation()
    contexts = contexts_for(source)

    with pytest.raises(ValueError, match="every filled trade requires"):
        run_regime_performance_breakdown(source, contexts[:-1])
    with pytest.raises(ValueError, match="must not repeat"):
        run_regime_performance_breakdown(source, contexts + (contexts[0],))
    extra = feature_context(
        fold_number=1,
        source_id="not-a-filled-entry",
        decision_at=contexts[0].decision_at,
    )
    with pytest.raises(ValueError, match="filled trades only"):
        run_regime_performance_breakdown(source, contexts + (extra,))


def test_context_must_match_the_queued_entry_decision_time() -> None:
    source = validation()
    contexts = list(contexts_for(source))
    original = contexts[0]
    contexts[0] = feature_context(
        fold_number=original.fold_number,
        source_id=original.entry_source_id,
        decision_at=original.decision_at - timedelta(seconds=1),
    )

    with pytest.raises(ValueError, match="must match queued intent"):
        run_regime_performance_breakdown(source, contexts)


def test_report_persists_source_evidence_policies_and_config_identity() -> None:
    source = validation()
    report = run_regime_performance_breakdown(source, contexts_for(source))
    record = report.as_record()

    assert record["validation_id"] == source.validation_id
    assert record["validation"] == source.as_record()
    assert record["config_metadata"] == METADATA
    assert record["etf_era_start"] == "2024-01-11T00:00:00+00:00"
    assert record["contexts"][0]["regime_record"]["feature_id"] == "REGIME_CLASSIFICATION"
    assert (
        record["contexts"][0]["volatility_record"]["volatility_regime_version"]
        == VOLATILITY_REGIME_VERSION
    )
    assert record["contexts"][0]["setup_record"]["detected"] is True
    assert set(report.reason_codes).issubset(REGIME_PERFORMANCE_REASON_CODES)


def test_report_is_deterministic_and_restores_exactly() -> None:
    source = validation()
    contexts = contexts_for(source)
    first = run_regime_performance_breakdown(source, contexts)
    second = run_regime_performance_breakdown(source, contexts)
    reordered = run_regime_performance_breakdown(source, tuple(reversed(contexts)))

    assert first == second
    assert reordered == first
    assert first.report_id == second.report_id
    assert first.evidence_digest == second.evidence_digest
    assert restore_regime_performance_breakdown(first.as_record()) == first


@pytest.mark.parametrize(
    "mutate",
    [
        lambda row: row["overall"].__setitem__("total_pnl", "999"),
        lambda row: row["breakdowns"][0]["buckets"][0].__setitem__(
            "trade_count", 999
        ),
        lambda row: row["contexts"][0].__setitem__("regime", "BEAR"),
        lambda row: row.__setitem__("etf_era_start", "2024-01-12T00:00:00+00:00"),
        lambda row: row["validation"].__setitem__("validation_id", "tampered"),
    ],
)
def test_restore_rejects_tampering(mutate) -> None:
    source = validation()
    report = run_regime_performance_breakdown(source, contexts_for(source))
    record = deepcopy(report.as_record())
    mutate(record)

    with pytest.raises(ValueError):
        restore_regime_performance_breakdown(record)


def test_context_record_rejects_nested_source_drift() -> None:
    context = feature_context()

    with pytest.raises(ValueError, match="does not match volatility_regime"):
        replace(
            context,
            volatility_record={
                **context.volatility_record,
                "volatility_regime": "STRESSED",
            },
        ).as_record()


def test_breakdown_lookup_rejects_an_unknown_dimension() -> None:
    source = validation(stand_aside)
    report = run_regime_performance_breakdown(source, ())

    with pytest.raises(KeyError):
        report.breakdown("not-a-dimension")
