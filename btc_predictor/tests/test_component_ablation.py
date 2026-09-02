"""BTC-189: single-component ablation of a composite score."""

from dataclasses import replace
from decimal import Decimal

import pytest

from btc_predictor.backtest import (
    ARM_ENTRY_ACTION,
    SCORING_ARCHITECTURE_V1_1_BENCHMARK,
    SCORING_ARCHITECTURE_V1_2,
    THRESHOLD_METRIC_POLICY_VERSION,
    THRESHOLD_PARAMETER_STATUS,
    BacktestContext,
    BacktestIntent,
    FoldStrategy,
    run_walk_forward,
    threshold_sweep_metrics,
    walk_forward_max_drawdown,
    walk_forward_plan,
)
from btc_predictor.config.strategy import ConfigIdentity
from btc_predictor.features.scoring_contracts import (
    ENTRY_CONVICTION_WEIGHTS_V1_2,
    MECHANICAL_VS_EMPIRICAL_NOTE,
    RETIRED_SCORING_CONTRACTS_VERSION,
    SCORING_CONTRACTS_VERSION,
)
from btc_predictor.research import (
    ABLATION_DRAWDOWN_POLICY_VERSION,
    ABLATION_ISOLATION_POLICY_VERSION,
    ABLATION_METRIC_POLICY_VERSION,
    ABLATION_PARAMETER_STATUS,
    ABLATION_PRODUCTION_STATUS,
    ABLATION_PROMOTION_TICKET,
    ABLATION_WEIGHT_POLICY_VERSION,
    CHANGE_AVAILABLE,
    CHANGE_VARIANT_UNDEFINED,
    COMPONENT_ABLATION_FEATURE_ID,
    COMPONENT_ABLATION_POLICY_VERSION,
    OVERLAP_AVAILABLE,
    OVERLAP_NO_ENTRIES,
    AblationVariant,
    ComponentAblationError,
    ablation_variants,
    component_ablation_spec,
    restore_component_ablation_report,
    run_component_ablation,
)
from btc_predictor.risk.stop import calculate_initial_stop
from btc_predictor.tests.test_backtest_walk_forward import BARS, CONFIG, NAV


PATHS = ("scoring_weights.entry_conviction",)
COMPONENTS = tuple(sorted(ENTRY_CONVICTION_WEIGHTS_V1_2))


def spec(**overrides):
    values = {
        "base_config_metadata": CONFIG.run_metadata(),
        "parameter_paths": PATHS,
        **overrides,
    }
    return component_ablation_spec(**values)


def variant_config(variant: AblationVariant):
    return replace(
        CONFIG,
        identity=ConfigIdentity(
            config_version=variant.config_metadata["config_version"],
            strategy_version=variant.config_metadata["strategy_version"],
            parameter_set_id=variant.parameter_set_id,
        ),
    )


def entering_strategy(variant: AblationVariant):
    def strategy(context: BacktestContext) -> BacktestIntent | None:
        if context.bar.timestamp != context.bars[0].timestamp:
            return None
        close = context.bar.close
        return BacktestIntent(
            action=ARM_ENTRY_ACTION,
            entry_zone_lower=close * Decimal("0.97"),
            entry_zone_upper=close * Decimal("1.03"),
            initial_stop=calculate_initial_stop(
                # A tight structural stop so folds close their trades and
                # expectancy and average R are defined.
                invalidation_price=close * Decimal("0.995"),
                buffer=Decimal("0"),
                direction="long",
                entry_price=close,
                config_metadata=variant.config_metadata,
            ),
            entry_conviction=Decimal("90"),
            source_id=f"entry-{context.as_of.isoformat()}",
        )

    return strategy


def evaluator(
    *,
    partial: tuple[str, ...] = (),
    silent: tuple[str, ...] = (),
    altered: tuple[str, ...] = (),
    trading: bool = True,
):
    """Build one comparable walk-forward run per ablation variant.

    ``partial`` variants skip the first fold's entry, so their trade decisions
    overlap the baseline's without matching them.
    """

    def evaluate(variant: AblationVariant):
        config = variant_config(variant)
        removed = variant.removed_component

        def factory(window):
            quiet = (
                not trading
                or removed in silent
                or (removed in partial and window.window.fold_number == 1)
            )
            return FoldStrategy(
                strategy=(
                    (lambda _context: None)
                    if quiet
                    else entering_strategy(variant)
                ),
                strategy_id=f"btc189-{variant.parameter_set_id}",
            )

        bars = BARS
        if removed in altered:
            changed = replace(
                bars[4],
                open=bars[4].open + Decimal("1"),
                high=bars[4].high + Decimal("1"),
                low=bars[4].low + Decimal("1"),
                close=bars[4].close + Decimal("1"),
            )
            bars = (*bars[:4], changed, *bars[5:])
        return run_walk_forward(
            bars,
            strategy_factory=factory,
            plan=walk_forward_plan(
                config,
                train_periods=3,
                test_periods=2,
                step_periods=2,
            ),
            starting_nav=NAV,
            strategy_config=config,
        )

    return evaluate


def test_policy_vocabularies_are_versioned_and_research_only() -> None:
    assert COMPONENT_ABLATION_FEATURE_ID == "COMPONENT_ABLATION"
    assert COMPONENT_ABLATION_POLICY_VERSION.endswith("_V1")
    assert ABLATION_WEIGHT_POLICY_VERSION.endswith("_V1")
    assert ABLATION_ISOLATION_POLICY_VERSION.endswith("_V1")
    assert ABLATION_METRIC_POLICY_VERSION == THRESHOLD_METRIC_POLICY_VERSION
    assert ABLATION_DRAWDOWN_POLICY_VERSION.endswith("_V1")
    assert ABLATION_PARAMETER_STATUS == THRESHOLD_PARAMETER_STATUS
    report = run_component_ablation(spec(), evaluator=evaluator())
    assert report.production_status == ABLATION_PRODUCTION_STATUS
    assert report.promotion_ticket == ABLATION_PROMOTION_TICKET
    assert "COMPONENT_ABLATION_RESEARCH_ONLY" in report.reason_codes
    assert "COMPONENT_ABLATION_BTC_193_PROMOTION_REQUIRED" in report.reason_codes
    assert report.reason_codes[-1] == "COMPONENT_ABLATION_COMPLETE"


def test_specification_reads_the_scoring_contract_owner() -> None:
    declared = spec()
    assert declared.composite == "entry_conviction"
    assert declared.contracts_version == SCORING_CONTRACTS_VERSION
    assert tuple(item.component for item in declared.baseline_weights) == COMPONENTS
    assert declared.ablated_components == COMPONENTS
    for item in declared.baseline_weights:
        assert item.weight == ENTRY_CONVICTION_WEIGHTS_V1_2[item.component].quantize(
            Decimal("1E-12")
        )
    assert declared == spec()
    assert declared.spec_id == spec().spec_id
    assert declared.spec_id != spec(composite="hold_score").spec_id


def test_one_component_is_removed_at_a_time_and_the_rest_are_renormalized() -> None:
    variants = ablation_variants(spec())
    assert len(variants) == 1 + len(COMPONENTS)
    baseline, *ablations = variants
    assert baseline.baseline is True
    assert baseline.removed_component is None
    assert baseline.weight_total == Decimal("1.000000000000")
    for variant, component in zip(ablations, COMPONENTS, strict=True):
        assert variant.baseline is False
        assert variant.removed_component == component
        names = tuple(item.component for item in variant.weights)
        assert component not in names
        assert set(names) == set(COMPONENTS) - {component}
        assert abs(variant.weight_total - Decimal("1")) <= Decimal("1E-11")


def test_ablation_preserves_the_relative_weights_of_untouched_components() -> None:
    baseline, *ablations = ablation_variants(spec())
    removed = next(
        item for item in ablations if item.removed_component == "volatility"
    )
    survivors = tuple(item.component for item in removed.weights)
    for first, second in zip(survivors, survivors[1:], strict=False):
        declared_ratio = (
            ENTRY_CONVICTION_WEIGHTS_V1_2[first]
            / ENTRY_CONVICTION_WEIGHTS_V1_2[second]
        )
        ablated_ratio = removed.weight(first) / removed.weight(second)
        assert abs(ablated_ratio - declared_ratio) < Decimal("1E-9")
    assert removed.weight("trend") > baseline.weight("trend")


def test_unrelated_run_identity_is_unchanged_across_variants() -> None:
    variants = ablation_variants(spec())
    identifiers = {item.parameter_set_id for item in variants}
    assert len(identifiers) == len(variants)
    for variant in variants:
        assert variant.config_metadata["parameter_set_id"] == variant.parameter_set_id
        assert variant.parameter_paths == PATHS
        assert variant.scoring_architecture_version == SCORING_ARCHITECTURE_V1_2
        rest = {
            key: value
            for key, value in variant.config_metadata.items()
            if key != "parameter_set_id"
        }
        expected = {
            key: value
            for key, value in CONFIG.run_metadata().items()
            if key != "parameter_set_id"
        }
        assert rest == expected


def test_variant_runs_must_carry_their_own_parameter_set_identity() -> None:
    def wrong(variant: AblationVariant):
        return evaluator()(ablation_variants(spec())[0])

    with pytest.raises(ComponentAblationError, match="config_metadata"):
        run_component_ablation(spec(), evaluator=wrong)


def test_incomparable_runs_are_rejected_before_anything_is_compared() -> None:
    with pytest.raises(ComponentAblationError, match="must share schedule"):
        run_component_ablation(spec(), evaluator=evaluator(altered=("trend",)))


def test_trade_decision_overlap_is_reported_for_every_ablation() -> None:
    report = run_component_ablation(
        spec(), evaluator=evaluator(partial=("flow",), silent=("structure",))
    )
    identical = report.result("trend").overlap
    assert identical is not None
    assert identical.status == OVERLAP_AVAILABLE
    assert identical.baseline_entry_count > 0
    assert identical.shared_entry_count == identical.baseline_entry_count
    assert identical.variant_only_entry_count == 0
    assert identical.overlap_fraction == Decimal("1.000000000000")

    partial = report.result("flow").overlap
    assert partial is not None
    assert partial.shared_entry_count > 0
    assert partial.baseline_only_entry_count > 0
    assert partial.variant_only_entry_count == 0
    assert partial.overlap_fraction is not None
    assert Decimal("0") < partial.overlap_fraction < Decimal("1")

    silent = report.result("structure").overlap
    assert silent is not None
    assert silent.variant_entry_count == 0
    assert silent.baseline_only_entry_count == silent.baseline_entry_count
    assert silent.overlap_fraction == Decimal("0E-12")
    assert "COMPONENT_ABLATION_VARIANTS_WITHOUT_TRADES" in report.reason_codes


def test_an_ablation_without_any_entries_declares_absence_of_evidence() -> None:
    report = run_component_ablation(spec(), evaluator=evaluator(trading=False))
    overlap = report.result("trend").overlap
    assert overlap is not None
    assert overlap.status == OVERLAP_NO_ENTRIES
    assert overlap.overlap_fraction is None
    assert overlap.baseline_entry_count == 0
    assert "COMPONENT_ABLATION_NO_TRADES" in report.reason_codes


def test_expectancy_average_r_and_drawdown_changes_are_reported() -> None:
    report = run_component_ablation(spec(), evaluator=evaluator(silent=("flow",)))
    baseline = report.baseline
    assert baseline.overlap is None
    assert baseline.change is None
    assert baseline.metrics.outcome == threshold_sweep_metrics(baseline.validation)
    drawdown, status = walk_forward_max_drawdown(baseline.validation)
    assert baseline.metrics.max_drawdown_fraction == drawdown
    assert baseline.metrics.max_drawdown_status == status

    unchanged = report.result("trend").change
    assert unchanged is not None
    assert unchanged.trade_count_change == 0
    assert unchanged.mean_return_fraction_change == Decimal("0E-12")
    assert unchanged.expectancy_change_status == CHANGE_AVAILABLE
    assert unchanged.closed_trade_expectancy_change == Decimal("0E-12")
    assert unchanged.mean_r_change_status == CHANGE_AVAILABLE
    assert unchanged.mean_r_multiple_change == Decimal("0E-12")
    assert unchanged.drawdown_change_status == CHANGE_AVAILABLE

    removed = report.result("flow").change
    assert removed is not None
    assert removed.trade_count_change == -baseline.metrics.outcome.trade_count
    assert (
        "COMPONENT_ABLATION_EXPECTANCY_REPORTED" in report.reason_codes
    )
    assert "COMPONENT_ABLATION_MEAN_R_REPORTED" in report.reason_codes
    assert "COMPONENT_ABLATION_DRAWDOWN_REPORTED" in report.reason_codes


def test_an_undefined_metric_change_is_declared_rather_than_zero() -> None:
    report = run_component_ablation(spec(), evaluator=evaluator(silent=("flow",)))
    removed = report.result("flow")
    assert removed.metrics.outcome.closed_trade_expectancy is None
    assert removed.change is not None
    assert removed.change.expectancy_change_status == CHANGE_VARIANT_UNDEFINED
    assert removed.change.closed_trade_expectancy_change is None
    assert removed.change.mean_r_change_status == CHANGE_VARIANT_UNDEFINED
    assert removed.change.mean_r_multiple_change is None


def test_the_structural_nesting_audit_is_reported_beside_the_outcomes() -> None:
    report = run_component_ablation(spec(), evaluator=evaluator())
    audit = report.factor_overlap_audit
    assert audit["composite"] == "entry_conviction"
    assert audit["contracts_version"] == SCORING_CONTRACTS_VERSION
    assert audit["mechanically_clean"] is True
    assert audit["mechanical_vs_empirical"] == MECHANICAL_VS_EMPIRICAL_NOTE
    assert "COMPONENT_ABLATION_MECHANICALLY_CLEAN" in report.reason_codes


def test_the_retired_v1_1_benchmark_is_reported_as_mechanically_nested() -> None:
    benchmark = spec(
        base_config_metadata={
            **CONFIG.run_metadata(),
            "strategy_version": "swing_v1.1",
        },
        scoring_architecture_version=SCORING_ARCHITECTURE_V1_1_BENCHMARK,
    )
    assert benchmark.contracts_version == RETIRED_SCORING_CONTRACTS_VERSION
    assert "regime" in tuple(item.component for item in benchmark.baseline_weights)
    report = run_component_ablation(benchmark, evaluator=evaluator())
    assert report.factor_overlap_audit["mechanically_clean"] is False
    assert "COMPONENT_ABLATION_MECHANICAL_NESTING_DETECTED" in report.reason_codes


def test_mixing_architectures_with_the_strategy_version_is_rejected() -> None:
    with pytest.raises(ValueError, match="isolate swing_v1.2"):
        spec(scoring_architecture_version=SCORING_ARCHITECTURE_V1_1_BENCHMARK)
    with pytest.raises(ComponentAblationError, match="scoring_architecture_version"):
        spec(scoring_architecture_version="NESTED_SCORING_V0_9")


def test_specifications_reject_undeclared_composites_and_components() -> None:
    with pytest.raises(ComponentAblationError, match="unknown composite"):
        spec(composite="not_a_score")
    with pytest.raises(ComponentAblationError, match="declared components"):
        spec(ablated_components=("liquidity",))
    with pytest.raises(ComponentAblationError, match="unique"):
        spec(ablated_components=("trend", "trend"))
    with pytest.raises(ComponentAblationError, match="at least one component"):
        spec(ablated_components=())


def test_a_subset_of_components_can_be_ablated() -> None:
    narrowed = spec(ablated_components=("flow", "trend"))
    variants = ablation_variants(narrowed)
    assert len(variants) == 3
    assert [item.removed_component for item in variants] == [None, "flow", "trend"]


def test_evidence_round_trips_through_its_persistence_record() -> None:
    report = run_component_ablation(spec(), evaluator=evaluator(partial=("flow",)))
    record = report.as_record()
    assert record["evidence_digest"] == report.evidence_digest
    restored = restore_component_ablation_report(record)
    assert restored == report
    assert restored.as_record() == record


def test_tampered_ablation_evidence_is_rejected_on_restore() -> None:
    report = run_component_ablation(spec(), evaluator=evaluator(partial=("flow",)))
    record = report.as_record()

    edited = {**record}
    results = [dict(item) for item in record["results"]]
    results[1] = {
        **results[1],
        "overlap": {
            **results[1]["overlap"],
            "shared_entry_count": results[1]["overlap"]["shared_entry_count"] + 1,
        },
    }
    edited["results"] = results
    with pytest.raises(ComponentAblationError):
        restore_component_ablation_report(edited)

    dropped = {**record, "results": record["results"][:-1]}
    with pytest.raises(ComponentAblationError):
        restore_component_ablation_report(dropped)

    relabelled = {**record, "production_status": "PRODUCTION"}
    with pytest.raises(ComponentAblationError):
        restore_component_ablation_report(relabelled)

    recoded = {**record, "reason_codes": [*record["reason_codes"], "EXTRA"]}
    with pytest.raises(ComponentAblationError):
        restore_component_ablation_report(recoded)


def test_reports_are_deterministic_for_the_same_evidence() -> None:
    first = run_component_ablation(spec(), evaluator=evaluator(partial=("flow",)))
    second = run_component_ablation(spec(), evaluator=evaluator(partial=("flow",)))
    assert second.as_record() == first.as_record()
    assert second.report_id == first.report_id
