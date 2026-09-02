"""BTC-203: deterministic Model Paper versus Human Actual comparison."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext

import pytest

from btc_predictor.journal import (
    ACTUAL_TRADE_FEATURE_ID,
    ACTUAL_TRADE_POLICY_VERSION,
    DECISION_JOURNAL_POLICY_VERSION,
    DISCRETIONARY_REASON_POLICY_VERSION,
    FOLLOWED,
    MANUAL_ONLY,
    OVERRIDDEN,
    ActualTradeEntry,
)
from btc_predictor.portfolio.accounting import TradeFill, calculate_trade_accounting
from btc_predictor.portfolio.lifecycle_persistence import LifecycleProvenance
from btc_predictor.reporting import (
    DRAWDOWN_AVAILABLE,
    DRAWDOWN_NO_CLOSED_TRADES,
    HUMAN_ACTUAL,
    MODEL_HUMAN_ACTUAL_RETURN_POLICY_VERSION,
    MODEL_HUMAN_ARMS,
    MODEL_HUMAN_COMPARISON_FEATURE_ID,
    MODEL_HUMAN_COMPARISON_POLICY_VERSION,
    MODEL_HUMAN_COMPARISON_REASON_CODES,
    MODEL_HUMAN_DRAWDOWN_POLICY_VERSION,
    MODEL_HUMAN_PAPER_RETURN_POLICY_VERSION,
    MODEL_HUMAN_SHARPE_POLICY_VERSION,
    MODEL_PAPER,
    MODEL_PLUS_HUMAN,
    PROFIT_FACTOR_AVAILABLE,
    PROFIT_FACTOR_NO_MEASURED_TRADES,
    R_MISSING_INITIAL_STOP,
    R_NON_ADVERSE_INITIAL_STOP,
    SHARPE_INSUFFICIENT_TRADES,
    ModelHumanComparisonError,
    build_model_human_comparison,
    restore_model_human_comparison,
)
from btc_predictor.research import (
    FeatureMatrixDefinition,
    FeatureMatrixProvenance,
    FeatureObservation,
    PaperTradeEntry,
    PaperTradeOutcomeDefinition,
    build_paper_trade_outcome_dataset,
    build_point_in_time_feature_matrix,
)


START = datetime(2026, 1, 1, tzinfo=UTC)
EXTRACTION = START + timedelta(days=30)
SYMBOL = "BTC-USD"
CONFIG = {
    "config_version": "strategy_config_v2",
    "strategy_version": "swing_v1.2",
    "parameter_set_id": "default_phase1",
}
RATE = Decimal("1E-12")


def _fill(
    sequence: int,
    filled_at: datetime,
    action: str,
    price: str,
) -> TradeFill:
    return TradeFill(
        sequence=sequence,
        filled_at=filled_at,
        action=action,
        quantity=Decimal("1"),
        price=Decimal(price),
        source_event_id=f"fill-{sequence}-{filled_at.isoformat()}",
        execution_bar_at=filled_at,
        execution_bar_timeframe="1d",
    )


def _paper_dataset(
    specs: tuple[tuple[int, str, str, str], ...] = (
        (1, "100", "110", "90"),
        (2, "100", "90", "90"),
    ),
):
    provenance = FeatureMatrixProvenance(**CONFIG)
    definition = FeatureMatrixDefinition(
        feature_names=("TREND_SCORE",), provenance=provenance
    )
    decision_times = tuple(START + timedelta(days=index) for index, *_ in specs)
    features = build_point_in_time_feature_matrix(
        tuple(
            FeatureObservation(
                feature_name="TREND_SCORE",
                value=Decimal("80") + Decimal(index),
                observation_time=decision_time,
                available_at=decision_time,
                source_id="feature-pipeline",
            )
            for (index, *_), decision_time in zip(
                specs, decision_times, strict=True
            )
        ),
        decision_times,
        definition=definition,
    )
    entries: list[PaperTradeEntry] = []
    accountings = {}
    for (recommendation_id, entry_price, exit_price, stop), decision_time in zip(
        specs, decision_times, strict=True
    ):
        reference = f"paper-{recommendation_id}"
        entry_time = decision_time + timedelta(hours=1)
        exit_time = START + timedelta(days=recommendation_id + 3)
        entries.append(
            PaperTradeEntry(
                trade_reference=reference,
                entry_decision_timestamp=decision_time,
                data_available_at=decision_time,
                symbol=SYMBOL,
                direction="long",
                decision="ENTER",
                setup="BULL_TREND_CONTINUATION",
                regime="BULL",
                provenance=LifecycleProvenance(
                    recommendation_id=recommendation_id,
                    strategy_version=CONFIG["strategy_version"],
                    parameter_set_id=CONFIG["parameter_set_id"],
                ),
                source_id="paper-campaign",
            )
        )
        accountings[reference] = calculate_trade_accounting(
            (
                _fill(1, entry_time, "ENTER", entry_price),
                _fill(2, exit_time, "EXIT", exit_price),
            ),
            symbol=SYMBOL,
            direction="long",
            initial_stop_price=stop,
            initial_stop_source_id=f"stop-{recommendation_id}",
            exit_reason="HOLD_SCORE_COLLAPSE",
            exit_reason_source_id=f"exit-{recommendation_id}",
            config_metadata=CONFIG,
        )
    return build_paper_trade_outcome_dataset(
        tuple(entries),
        accountings,
        features,
        extraction_time=EXTRACTION,
        definition=PaperTradeOutcomeDefinition(
            entry_feature_names=("TREND_SCORE",),
            outcome_names=("net_pnl", "entry_notional", "r_multiple"),
        ),
    )


def _actual(
    *,
    recommendation_id: int | None = 1,
    entry_day: int = 2,
    exit_day: int | None = 6,
    entry_price: str = "100",
    exit_price: str | None = "120",
    stop: str | None = "90",
    direction: str = "long",
    manual_decision: str | None = None,
) -> ActualTradeEntry:
    linked = recommendation_id is not None
    decision = manual_decision or (FOLLOWED if linked else MANUAL_ONLY)
    entry_time = START + timedelta(days=entry_day)
    exit_time = None if exit_day is None else START + timedelta(days=exit_day)
    journaled_at = (exit_time or entry_time) + timedelta(hours=1)
    overridden = decision == OVERRIDDEN
    return ActualTradeEntry(
        feature_id=ACTUAL_TRADE_FEATURE_ID,
        policy_version=ACTUAL_TRADE_POLICY_VERSION,
        recommendation_id=recommendation_id,
        strategy_version=CONFIG["strategy_version"] if linked else None,
        parameter_set_id=CONFIG["parameter_set_id"] if linked else None,
        config_version=CONFIG["config_version"] if linked else None,
        decision_journal_policy_version=(
            DECISION_JOURNAL_POLICY_VERSION if linked else None
        ),
        decision_decided_at=entry_time - timedelta(hours=1) if linked else None,
        decision_reason_codes=(
            (
                "DECISION_JOURNAL_RECORDED",
                "DECISION_JOURNAL_MODIFIED"
                if overridden
                else "DECISION_JOURNAL_APPROVED",
            )
            if linked
            else None
        ),
        discretionary_reason_policy_version=(
            DISCRETIONARY_REASON_POLICY_VERSION if linked else None
        ),
        discretionary_reason_codes=(
            ("MODEL_DISAGREEMENT",) if overridden else ()
        )
        if linked
        else None,
        symbol=SYMBOL,
        direction=direction,
        journaled_at=journaled_at,
        manual_decision=decision,
        override_reason="Changed model execution." if overridden else None,
        actual_entry_time=entry_time,
        actual_entry_price=Decimal(entry_price),
        actual_size=Decimal("1"),
        actual_size_unit="BTC",
        actual_stop=None if stop is None else Decimal(stop),
        actual_exit_time=exit_time,
        actual_exit_price=None if exit_price is None else Decimal(exit_price),
        notes=None,
    )


def _report():
    return build_model_human_comparison(
        _paper_dataset(),
        (
            _actual(),
            _actual(
                recommendation_id=None,
                entry_day=3,
                exit_day=7,
                exit_price="90",
            ),
        ),
    )


def _q(value: str) -> Decimal:
    return Decimal(value).quantize(RATE, rounding=ROUND_HALF_EVEN)


def test_three_arms_have_the_declared_model_and_human_meanings() -> None:
    report = _report()

    assert report.feature_id == MODEL_HUMAN_COMPARISON_FEATURE_ID
    assert report.policy_version == MODEL_HUMAN_COMPARISON_POLICY_VERSION
    assert tuple(arm.arm_id for arm in report.arms) == MODEL_HUMAN_ARMS
    assert report.model_paper.metrics.trade_count == 2
    assert report.human_actual.metrics.trade_count == 2
    assert report.model_plus_human.metrics.trade_count == 1
    assert report.model_plus_human.trades[0].recommendation_id == 1
    assert report.model_plus_human.trades[0] in report.human_actual.trades


def test_all_required_metrics_use_normalized_closed_trade_returns() -> None:
    report = _report()
    model = report.arm(MODEL_PAPER).metrics
    human = report.arm(HUMAN_ACTUAL).metrics

    assert model.closed_trade_count == human.closed_trade_count == 2
    assert model.win_rate == human.win_rate == Decimal("0.500000000000")
    assert model.average_r == Decimal("0E-12")
    assert human.average_r == Decimal("0.500000000000")
    assert model.profit_factor == Decimal("1.000000000000")
    assert human.profit_factor == Decimal("2.000000000000")
    assert model.profit_factor_status == human.profit_factor_status == (
        PROFIT_FACTOR_AVAILABLE
    )
    assert model.max_drawdown == human.max_drawdown == Decimal("0.100000000000")
    assert model.max_drawdown_status == human.max_drawdown_status == (
        DRAWDOWN_AVAILABLE
    )
    assert model.return_per_trade == Decimal("0E-12")
    assert human.return_per_trade == Decimal("0.050000000000")


def test_sharpe_is_unannualized_sample_return_sharpe() -> None:
    report = _report()
    model = report.model_paper.metrics
    human = report.human_actual.metrics

    assert model.sharpe == Decimal("0E-12")
    with localcontext(Context(prec=60)):
        returns = (Decimal("0.2"), Decimal("-0.1"))
        mean = sum(returns) / Decimal("2")
        variance = sum((value - mean) ** 2 for value in returns)
        expected = (mean / variance.sqrt()).quantize(
            RATE, rounding=ROUND_HALF_EVEN
        )
    assert human.sharpe == expected
    assert report.model_plus_human.metrics.sharpe is None
    assert report.model_plus_human.metrics.sharpe_status == (
        SHARPE_INSUFFICIENT_TRADES
    )


def test_metric_and_cost_conventions_are_versioned_and_visible() -> None:
    report = _report()

    assert MODEL_HUMAN_PAPER_RETURN_POLICY_VERSION in report.paper_return_policy_version
    assert "NET_PNL" in report.paper_return_policy_version
    assert MODEL_HUMAN_ACTUAL_RETURN_POLICY_VERSION.endswith("_V1")
    assert "NO_RECORDED_COSTS" in report.actual_return_policy_version
    assert report.drawdown_policy_version == MODEL_HUMAN_DRAWDOWN_POLICY_VERSION
    assert report.sharpe_policy_version == MODEL_HUMAN_SHARPE_POLICY_VERSION
    assert report.reason_codes == MODEL_HUMAN_COMPARISON_REASON_CODES
    assert "MODEL_HUMAN_ACTUAL_RETURNS_EXCLUDE_UNRECORDED_COSTS" in (
        report.reason_codes
    )


def test_actual_short_return_and_r_are_direction_aware() -> None:
    short = _actual(
        recommendation_id=None,
        direction="short",
        entry_price="100",
        exit_price="80",
        stop="110",
    )
    report = build_model_human_comparison(_paper_dataset(), (short,))
    outcome = report.human_actual.trades[0]

    assert outcome.return_fraction == Decimal("0.200000000000")
    assert outcome.r_multiple == Decimal("2.000000000000")


@pytest.mark.parametrize(
    ("stop", "status"),
    (
        (None, R_MISSING_INITIAL_STOP),
        ("110", R_NON_ADVERSE_INITIAL_STOP),
    ),
)
def test_missing_or_non_adverse_actual_stop_does_not_zero_fill_r(
    stop: str | None,
    status: str,
) -> None:
    report = build_model_human_comparison(
        _paper_dataset(),
        (_actual(recommendation_id=None, stop=stop),),
    )
    outcome = report.human_actual.trades[0]

    assert outcome.r_multiple is None
    assert outcome.r_status == status
    assert report.human_actual.metrics.measured_r_count == 0
    assert report.human_actual.metrics.average_r is None


def test_open_actual_trade_is_counted_but_excluded_from_quality_metrics() -> None:
    opened = _actual(exit_day=None, exit_price=None)
    report = build_model_human_comparison(_paper_dataset(), (opened,))
    human = report.human_actual.metrics

    assert human.trade_count == 1
    assert human.closed_trade_count == 0
    assert human.open_trade_count == 1
    assert human.measured_return_count == 0
    assert human.win_rate is None
    assert human.return_per_trade is None
    assert human.profit_factor_status == PROFIT_FACTOR_NO_MEASURED_TRADES
    assert human.max_drawdown_status == DRAWDOWN_NO_CLOSED_TRADES


def test_paper_undefined_r_remains_missing_while_return_is_measured() -> None:
    dataset = _paper_dataset(((1, "100", "110", "100"),))
    report = build_model_human_comparison(dataset, ())
    outcome = report.model_paper.trades[0]

    assert outcome.return_fraction == Decimal("0.100000000000")
    assert outcome.r_multiple is None
    assert report.model_paper.metrics.measured_return_count == 1
    assert report.model_paper.metrics.measured_r_count == 0
    assert report.model_paper.metrics.average_r is None


def test_empty_evidence_has_explicit_unavailable_metrics() -> None:
    dataset = _paper_dataset(())
    report = build_model_human_comparison(dataset, ())

    for arm in report.arms:
        assert arm.metrics.trade_count == 0
        assert arm.metrics.win_rate is None
        assert arm.metrics.average_r is None
        assert arm.metrics.return_per_trade is None
        assert arm.metrics.profit_factor_status == PROFIT_FACTOR_NO_MEASURED_TRADES
        assert arm.metrics.max_drawdown_status == DRAWDOWN_NO_CLOSED_TRADES
        assert arm.metrics.sharpe_status == SHARPE_INSUFFICIENT_TRADES


def test_input_order_and_record_inputs_do_not_change_the_report() -> None:
    dataset = _paper_dataset()
    linked = _actual()
    manual = _actual(
        recommendation_id=None, entry_day=3, exit_day=7, exit_price="90"
    )

    first = build_model_human_comparison(dataset, (linked, manual))
    second = build_model_human_comparison(
        dataset.as_record(), (manual.as_record(), linked.as_record())
    )

    assert first == second
    assert first.as_record() == second.as_record()
    assert first.comparison_id == second.comparison_id
    assert first.evidence_digest == second.evidence_digest


def test_round_trip_replays_all_source_evidence() -> None:
    report = _report()
    serialized = json.loads(json.dumps(report.as_record(), sort_keys=True))

    restored = restore_model_human_comparison(serialized)

    assert restored == report
    assert restored.as_record() == report.as_record()
    assert restored.actual_trades[0].discretionary_reason_codes == ()


@pytest.mark.parametrize(
    "tamper",
    (
        lambda row: row["arms"][0]["metrics"].__setitem__("win_rate", "0.9"),
        lambda row: row.__setitem__("actual_return_policy_version", "COSTS_GUESSED"),
        lambda row: row["actual_trades"][0].__setitem__("actual_exit_price", "999"),
        lambda row: row["paper_dataset"].__setitem__("evidence_digest", "0" * 64),
        lambda row: row["reason_codes"].append("INVENTED"),
    ),
)
def test_restore_rejects_policy_source_metric_and_reason_tampering(tamper) -> None:
    record = _report().as_record()
    tamper(record)

    with pytest.raises(ValueError):
        restore_model_human_comparison(record)


def test_linked_actual_must_exist_in_the_paper_campaign() -> None:
    with pytest.raises(ModelHumanComparisonError, match="absent from the paper"):
        build_model_human_comparison(
            _paper_dataset(), (_actual(recommendation_id=999),)
        )


def test_linked_actual_must_match_paper_config_symbol_and_direction() -> None:
    mismatched = replace(_actual(), config_version="other-config")

    with pytest.raises(ModelHumanComparisonError, match="configuration must match"):
        build_model_human_comparison(_paper_dataset(), (mismatched,))


def test_manual_only_actual_must_share_the_paper_campaign_symbol() -> None:
    other_symbol = replace(
        _actual(recommendation_id=None),
        symbol="ETH-USD",
    )

    with pytest.raises(ModelHumanComparisonError, match="campaign symbol"):
        build_model_human_comparison(_paper_dataset(), (other_symbol,))


def test_actual_journal_must_be_point_in_time_at_extraction() -> None:
    after_cutoff = replace(
        _actual(), journaled_at=EXTRACTION + timedelta(seconds=1)
    )

    with pytest.raises(ModelHumanComparisonError, match="after the paper extraction"):
        build_model_human_comparison(_paper_dataset(), (after_cutoff,))


def test_duplicate_actual_records_and_linked_recommendations_fail_closed() -> None:
    linked = _actual()
    with pytest.raises(ModelHumanComparisonError, match="records must be unique"):
        build_model_human_comparison(_paper_dataset(), (linked, linked))

    distinct_duplicate_link = replace(linked, actual_size=Decimal("2"))
    with pytest.raises(ModelHumanComparisonError, match="at most one actual"):
        build_model_human_comparison(
            _paper_dataset(), (linked, distinct_duplicate_link)
        )


def test_modified_decision_reasons_are_persisted_in_human_outcomes() -> None:
    modified = _actual(manual_decision=OVERRIDDEN)
    report = build_model_human_comparison(_paper_dataset(), (modified,))
    outcome = report.model_plus_human.trades[0]

    assert outcome.manual_decision == OVERRIDDEN
    assert outcome.discretionary_reason_codes == ("MODEL_DISAGREEMENT",)
    assert report.actual_trades[0].discretionary_reason_policy_version == (
        DISCRETIONARY_REASON_POLICY_VERSION
    )


def test_missing_required_paper_outcomes_fail_closed() -> None:
    dataset = _paper_dataset()
    narrowed = replace(
        dataset.definition,
        outcome_names=("net_pnl", "r_multiple"),
    )

    with pytest.raises(ModelHumanComparisonError, match="entry_notional"):
        build_model_human_comparison(replace(dataset, definition=narrowed), ())


def test_decimal_results_are_independent_of_ambient_context() -> None:
    dataset = _paper_dataset()
    actual_trades = (
        _actual(),
        _actual(
            recommendation_id=None, entry_day=3, exit_day=7, exit_price="90"
        ),
    )
    expected = build_model_human_comparison(dataset, actual_trades).as_record()

    with localcontext(Context(prec=7)):
        actual = build_model_human_comparison(dataset, actual_trades).as_record()

    assert actual == expected
    assert _q("0.05") == Decimal(actual["arms"][1]["metrics"]["return_per_trade"])
