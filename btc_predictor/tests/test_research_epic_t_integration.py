"""EPIC T integration: BTC-190, BTC-191, BTC-192 and BTC-193 composed.

Each ticket is separately covered by its own focused suite.  These tests pin
the invariants that only exist between them: that the decision-date store and
the paper-trade dataset label the same trade identically, that a revision
published after a decision reaches neither of them, that a short trade keeps
its sign all the way into the comparison metrics, that the comparison's summed
net P&L reconciles with the backtest NAV it came from, and that BTC-191
evidence survives byte-identically into a BTC-193 promotion packet that
mutates no configuration.
"""

import decimal
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.portfolio.account import ExecutionCosts
from btc_predictor.portfolio.accounting import TradeFill, calculate_trade_accounting
from btc_predictor.portfolio.lifecycle_persistence import LifecycleProvenance
from btc_predictor.research import (
    NOT_TRADED,
    PAPER_TRADE,
    SCORE_AVAILABLE,
    TRADE_OUTCOME_AVAILABLE,
    TRADED,
    DecisionStateDefinition,
    DecisionStateObservation,
    FeatureMatrixDefinition,
    FeatureMatrixProvenance,
    FeatureObservation,
    ForwardTargetDefinition,
    ForwardTargetObservation,
    PaperTradeEntry,
    PaperTradeOutcomeDefinition,
    build_decision_state_store,
    build_forward_target_matrix,
    build_paper_trade_outcome_dataset,
    build_point_in_time_feature_matrix,
    compare_backtest_strategies,
    compare_paper_trade_strategies,
)
from btc_predictor.tests.test_strategy_comparison import (
    BASELINE_PARAMETERS,
    BASELINE_VERSION,
    CANDIDATE_PARAMETERS,
    CANDIDATE_VERSION,
    _result,
)


START = datetime(2024, 1, 1, tzinfo=UTC)
GRID = (START, START + timedelta(days=1))
EXTRACTION = START + timedelta(days=120)
STRATEGY_VERSION = "swing_v1.2"
PARAMETER_SET_ID = "epic-t"
TRADE_REFERENCE = "paper-trade-1"
FEATURE_SOURCE = "feature-pipeline"
TARGET_SOURCE = "target-pipeline"
METADATA = {
    "config_version": "config-for-epic-t",
    "strategy_version": STRATEGY_VERSION,
    "parameter_set_id": PARAMETER_SET_ID,
}
PROVENANCE = FeatureMatrixProvenance(**METADATA)
SCORE_NAMES = ("TREND_SCORE", "FLOW_SCORE")
OUTCOME_NAMES = ("future_1w_return",)


def _features(observations):
    return build_point_in_time_feature_matrix(
        observations,
        GRID,
        definition=FeatureMatrixDefinition(
            feature_names=SCORE_NAMES, provenance=PROVENANCE
        ),
    )


def _score(name, value, timestamp, *, available_at=None, revision=0):
    return FeatureObservation(
        feature_name=name,
        value=Decimal(value),
        observation_time=timestamp,
        available_at=available_at or timestamp,
        source_id=FEATURE_SOURCE,
        revision=revision,
    )


def _declared_scores(*, late_revision: bool = False):
    observations = [
        _score(name, value, timestamp)
        for timestamp, values in zip(GRID, (("70", "60"), ("40", "30")), strict=True)
        for name, value in zip(SCORE_NAMES, values, strict=True)
    ]
    if late_revision:
        # The same cell, restated after the decision it would have informed.
        observations.append(
            _score(
                "TREND_SCORE",
                "99",
                GRID[0],
                available_at=GRID[0] + timedelta(hours=6),
                revision=1,
            )
        )
    return tuple(observations)


def _targets():
    definition = ForwardTargetDefinition(target_names=OUTCOME_NAMES)
    observations = tuple(
        ForwardTargetObservation(
            target_name="future_1w_return",
            value=Decimal(value),
            decision_timestamp=timestamp,
            outcome_time=timestamp + timedelta(weeks=1),
            available_at=timestamp + timedelta(weeks=1),
            source_id=TARGET_SOURCE,
        )
        for timestamp, value in zip(GRID, ("0.08", "-0.02"), strict=True)
    )
    return build_forward_target_matrix(
        observations,
        GRID,
        definition=definition,
        data_available_at=EXTRACTION,
    )


def _store(features):
    observations = (
        DecisionStateObservation(
            decision_timestamp=GRID[0],
            data_available_at=GRID[0],
            decision="ENTER",
            setup="BULL_TREND_CONTINUATION",
            regime="BULL",
            execution_status=TRADED,
            trade_reference=TRADE_REFERENCE,
            source_id="advisory-run",
        ),
        DecisionStateObservation(
            decision_timestamp=GRID[1],
            data_available_at=GRID[1],
            decision="NO_TRADE",
            setup="NO_SETUP",
            regime="BULL",
            execution_status=NOT_TRADED,
            source_id="advisory-run",
        ),
    )
    return build_decision_state_store(
        observations,
        features,
        _targets(),
        extraction_time=EXTRACTION,
        definition=DecisionStateDefinition(
            score_names=SCORE_NAMES, outcome_names=OUTCOME_NAMES
        ),
    )


def _paper_dataset(features, *, direction="long", exit_price="110000"):
    entry = PaperTradeEntry(
        trade_reference=TRADE_REFERENCE,
        entry_decision_timestamp=GRID[0],
        data_available_at=GRID[0],
        symbol="BTC-USD",
        direction=direction,
        decision="ENTER",
        setup="BULL_TREND_CONTINUATION",
        regime="BULL",
        provenance=LifecycleProvenance(
            recommendation_id=1,
            strategy_version=STRATEGY_VERSION,
            parameter_set_id=PARAMETER_SET_ID,
        ),
        source_id="paper-campaign",
    )
    fills = (
        TradeFill(
            sequence=1,
            filled_at=GRID[0] + timedelta(hours=12),
            action="ENTER",
            quantity=Decimal("1"),
            price=Decimal("100000"),
            fee=Decimal("0"),
            source_event_id="entry-fill",
            execution_bar_at=GRID[0],
            execution_bar_timeframe="1d",
        ),
        TradeFill(
            sequence=2,
            filled_at=GRID[1] + timedelta(hours=12),
            action="EXIT",
            quantity=Decimal("1"),
            price=Decimal(exit_price),
            fee=Decimal("0"),
            source_event_id="exit-fill",
            execution_bar_at=GRID[1],
            execution_bar_timeframe="1d",
        ),
    )
    accounting = calculate_trade_accounting(
        fills,
        symbol="BTC-USD",
        direction=direction,
        initial_stop_price="95000" if direction == "long" else "105000",
        initial_stop_source_id="stop-1",
        exit_reason="HOLD_SCORE_COLLAPSE",
        exit_reason_source_id="exit-1",
        config_metadata=METADATA,
    )
    return build_paper_trade_outcome_dataset(
        (entry,),
        {TRADE_REFERENCE: accounting},
        features,
        extraction_time=EXTRACTION,
        definition=PaperTradeOutcomeDefinition(
            entry_feature_names=SCORE_NAMES,
            outcome_names=("net_pnl", "r_multiple", "initial_risk"),
        ),
    )


def test_store_and_dataset_label_the_same_trade_identically() -> None:
    features = _features(_declared_scores())
    store = _store(features)
    dataset = _paper_dataset(features)

    traded = store.traded_rows()
    rejected = store.rejected_rows()
    assert len(traded) == 1
    assert len(rejected) == 1
    assert store.coverage.decision_date_count == len(GRID)

    row = dataset.row(TRADE_REFERENCE)
    assert traded[0].trade_reference == row.trade_reference
    assert (traded[0].decision, traded[0].setup, traded[0].regime) == (
        row.decision,
        row.setup,
        row.regime,
    )
    # The rejected date exists only in the BTC-190 store; BTC-191 holds trades.
    assert rejected[0].decision_timestamp not in [
        item.entry_decision_timestamp for item in dataset.rows
    ]
    assert dataset.config_metadata["strategy_version"] == (
        store.config_metadata["strategy_version"]
    )
    assert dataset.config_metadata["parameter_set_id"] == (
        store.config_metadata["parameter_set_id"]
    )


def test_a_revision_published_after_the_decision_reaches_neither_layer() -> None:
    features = _features(_declared_scores())
    revised = _features(_declared_scores(late_revision=True))

    store = _store(features)
    revised_store = _store(revised)
    dataset = _paper_dataset(features)
    revised_dataset = _paper_dataset(revised)

    decided = store.row(GRID[0]).score("TREND_SCORE")
    assert decided.status == SCORE_AVAILABLE
    assert decided.value == 70.0
    assert revised_store.row(GRID[0]).score("TREND_SCORE") == decided
    assert revised_store.as_record() == store.as_record()

    entry_state = dataset.row(TRADE_REFERENCE).entry_feature("TREND_SCORE")
    assert entry_state.value == 70.0
    assert revised_dataset.row(TRADE_REFERENCE).entry_feature("TREND_SCORE") == (
        entry_state
    )
    assert revised_dataset.as_record() == dataset.as_record()


@pytest.mark.parametrize(
    ("direction", "exit_price", "profitable"),
    (
        ("long", "110000", True),
        ("long", "90000", False),
        ("short", "90000", True),
        ("short", "110000", False),
    ),
)
def test_long_and_short_outcomes_keep_their_sign_into_the_comparison(
    direction: str, exit_price: str, profitable: bool
) -> None:
    features = _features(_declared_scores())
    arm = _paper_dataset(features, direction=direction, exit_price=exit_price)

    row = arm.row(TRADE_REFERENCE)
    net = row.outcome("net_pnl")
    r_multiple = row.outcome("r_multiple")
    assert net.status == TRADE_OUTCOME_AVAILABLE
    assert r_multiple.status == TRADE_OUTCOME_AVAILABLE
    assert (net.value > 0) is profitable
    assert (r_multiple.value > 0) is profitable

    report = compare_paper_trade_strategies(
        (arm, _mirror_baseline(features)),
        comparison_scope_id="epic-t-campaign",
        baseline_strategy_version=STRATEGY_VERSION,
        baseline_parameter_set_id="epic-t-baseline",
    )
    metrics = report.arm(STRATEGY_VERSION, PARAMETER_SET_ID).metrics
    assert metrics.summed_net_pnl == net.value
    assert metrics.mean_r_multiple is not None
    assert metrics.winning_closed_trades == (1 if profitable else 0)
    assert metrics.losing_closed_trades == (0 if profitable else 1)
    assert report.evidence_mode == PAPER_TRADE


def _mirror_baseline(features):
    """A second arm with its own identity, so a comparison has two variants."""

    baseline_metadata = {**METADATA, "parameter_set_id": "epic-t-baseline"}
    baseline_features = build_point_in_time_feature_matrix(
        _declared_scores(),
        GRID,
        definition=FeatureMatrixDefinition(
            feature_names=SCORE_NAMES,
            provenance=FeatureMatrixProvenance(**baseline_metadata),
        ),
    )
    entry = PaperTradeEntry(
        trade_reference="paper-trade-baseline",
        entry_decision_timestamp=GRID[0],
        data_available_at=GRID[0],
        symbol="BTC-USD",
        direction="long",
        decision="ENTER",
        setup="BULL_TREND_CONTINUATION",
        regime="BULL",
        provenance=LifecycleProvenance(
            recommendation_id=1,
            strategy_version=STRATEGY_VERSION,
            parameter_set_id="epic-t-baseline",
        ),
        source_id="paper-campaign",
    )
    fills = (
        TradeFill(
            sequence=1,
            filled_at=GRID[0] + timedelta(hours=12),
            action="ENTER",
            quantity=Decimal("1"),
            price=Decimal("100000"),
            fee=Decimal("0"),
            source_event_id="entry-fill",
            execution_bar_at=GRID[0],
            execution_bar_timeframe="1d",
        ),
        TradeFill(
            sequence=2,
            filled_at=GRID[1] + timedelta(hours=12),
            action="EXIT",
            quantity=Decimal("1"),
            price=Decimal("101000"),
            fee=Decimal("0"),
            source_event_id="exit-fill",
            execution_bar_at=GRID[1],
            execution_bar_timeframe="1d",
        ),
    )
    accounting = calculate_trade_accounting(
        fills,
        symbol="BTC-USD",
        direction="long",
        initial_stop_price="95000",
        initial_stop_source_id="stop-1",
        exit_reason="HOLD_SCORE_COLLAPSE",
        exit_reason_source_id="exit-1",
        config_metadata=baseline_metadata,
    )
    return build_paper_trade_outcome_dataset(
        (entry,),
        {"paper-trade-baseline": accounting},
        baseline_features,
        extraction_time=EXTRACTION,
        definition=PaperTradeOutcomeDefinition(
            entry_feature_names=SCORE_NAMES,
            outcome_names=("net_pnl", "r_multiple", "initial_risk"),
        ),
    )


def test_comparison_net_pnl_reconciles_with_the_backtest_nav_it_summarizes() -> None:
    costs = ExecutionCosts(
        policy_version="EXECUTION_COST_V1",
        fee_bps=Decimal("12"),
        slippage_bps=Decimal("7"),
        funding_cost_bps_per_day=Decimal("3"),
    )
    baseline = _result(
        BASELINE_VERSION, BASELINE_PARAMETERS, exit_day=2, costs=costs
    )
    candidate = _result(
        CANDIDATE_VERSION, CANDIDATE_PARAMETERS, exit_day=3, costs=costs
    )
    report = compare_backtest_strategies(
        (candidate, baseline),
        baseline_strategy_version=BASELINE_VERSION,
        baseline_parameter_set_id=BASELINE_PARAMETERS,
    )

    for result, arm in ((baseline, report.arms[0]), (candidate, report.arms[1])):
        assert result.final_lifecycle.state == "CLOSED"
        assert arm.metrics.open_trade_count == 0
        # A flat portfolio with no external cash flow: the summed closed-trade
        # net P&L is the whole NAV change, fees, slippage and funding included.
        assert arm.metrics.summed_net_pnl == result.ending_nav - result.starting_nav


def test_promotion_packet_carries_paper_evidence_and_mutates_no_config() -> None:
    strategy_promotion = pytest.importorskip(
        "btc_predictor.tests.test_strategy_promotion"
    )
    evidence = {
        "current_production": strategy_promotion.CURRENT,
        "candidate": strategy_promotion.CANDIDATE,
        "paper_trade_comparison": compare_paper_trade_strategies(
            (
                strategy_promotion._paper_dataset(
                    "swing_v1.2", "candidate", exit_price="110000"
                ),
                strategy_promotion._paper_dataset(
                    "swing_v1.2", "current", exit_price="105000"
                ),
            ),
            comparison_scope_id="promotion-shadow-campaign",
            baseline_strategy_version="swing_v1.2",
            baseline_parameter_set_id="current",
        ),
        "predictor_diagnostics": strategy_promotion._diagnostics(),
        "component_ablation": strategy_promotion._ablation(),
        "historical_backtest_comparison": compare_backtest_strategies(
            (
                strategy_promotion._result("swing_v1.2", "candidate", exit_day=3),
                strategy_promotion._result("swing_v1.2", "current", exit_day=2),
            ),
            baseline_strategy_version="swing_v1.2",
            baseline_parameter_set_id="current",
        ),
        "walk_forward_validation": strategy_promotion._walk_forward(),
        "robustness_sweeps": (strategy_promotion._robustness_sweep(),),
    }
    packet = strategy_promotion.prepare_strategy_promotion(**evidence)
    record = packet.as_record()

    paper = evidence["paper_trade_comparison"]
    candidate_arm = paper.arm("swing_v1.2", "candidate")
    assert record["paper_trade_comparison"] == paper.as_record()
    assert record["paper_trade_comparison"]["arms"][1]["source"] == (
        candidate_arm.source.as_record()
    )
    assert packet.status == strategy_promotion.AWAITING_MANUAL_APPROVAL

    decision = strategy_promotion.record_manual_promotion_decision(
        packet,
        decision=strategy_promotion.PROMOTION_APPROVE,
        approver_id="risk-owner",
        decided_at=strategy_promotion.DECIDED_AT,
        rationale="Evidence chain reviewed end to end.",
    )
    final = strategy_promotion.finalize_strategy_promotion(packet, decision)
    assert final.config_mutation_performed is False
    assert final.resulting_production == strategy_promotion.CANDIDATE
    assert strategy_promotion.restore_strategy_promotion_record(
        final.as_record()
    ) == final


def test_the_epic_is_reproducible_under_a_narrowed_decimal_context() -> None:
    # Every EPIC T record is research evidence a later session must be able to
    # rebuild.  The epic's own layers must add no dependence on the caller's
    # ambient precision.  BTC-165 owns the trade figures BTC-191 carries and
    # pins their arithmetic itself, so this fixture keeps them exact and the
    # assertion below stays about EPIC T rather than about its dependency.
    features = _features(_declared_scores())
    store = _store(features)
    dataset = _paper_dataset(features)
    report = compare_paper_trade_strategies(
        (dataset, _mirror_baseline(features)),
        comparison_scope_id="epic-t-campaign",
        baseline_strategy_version=STRATEGY_VERSION,
        baseline_parameter_set_id="epic-t-baseline",
    )
    assert dataset.row(TRADE_REFERENCE).outcome("r_multiple").value == Decimal("2")
    expected = (store.as_record(), dataset.as_record(), report.as_record())

    for precision in (14, 10, 8, 6):
        with decimal.localcontext() as context:
            context.prec = precision
            assert _store(features).as_record() == expected[0]
            assert _paper_dataset(features).as_record() == expected[1]
            assert (
                compare_paper_trade_strategies(
                    (dataset, _mirror_baseline(features)),
                    comparison_scope_id="epic-t-campaign",
                    baseline_strategy_version=STRATEGY_VERSION,
                    baseline_parameter_set_id="epic-t-baseline",
                ).as_record()
                == expected[2]
            )
