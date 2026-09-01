"""BTC-185: deterministic one-dimensional threshold robustness sweeps."""

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal

import pytest

from btc_predictor.backtest import (
    ADD_THRESHOLD,
    ARM_ENTRY_ACTION,
    ENTRY_CONVICTION,
    EXPECTANCY_OBJECTIVE,
    FLOW_MINIMUM,
    HOLD_THRESHOLD,
    MEAN_RETURN_OBJECTIVE,
    POSITIONING_MINIMUM,
    REWARD_RISK_MINIMUM,
    RISK_BUDGET,
    SCORING_ARCHITECTURE_V1_1_BENCHMARK,
    SCORING_ARCHITECTURE_V1_2,
    STOP_BUFFER,
    STRUCTURE_MINIMUM,
    THRESHOLD_METRIC_POLICY_VERSION,
    THRESHOLD_PARAMETER_STATUS,
    THRESHOLD_PLATEAU_POLICY_VERSION,
    THRESHOLD_REVALIDATION_SCOPES,
    THRESHOLD_SWEEP_FEATURE_ID,
    THRESHOLD_SWEEP_POLICY_VERSION,
    THRESHOLD_SWEEP_REASON_CODES,
    TREND_MINIMUM,
    BacktestContext,
    BacktestIntent,
    FoldStrategy,
    ThresholdParameterSet,
    restore_threshold_sweep_report,
    run_threshold_sweep,
    run_walk_forward,
    threshold_parameter_sets,
    threshold_sweep_spec,
    walk_forward_plan,
)
from btc_predictor.config.strategy import ConfigIdentity
from btc_predictor.risk.stop import calculate_initial_stop
from btc_predictor.tests.test_backtest_walk_forward import BARS, CONFIG, NAV


PATH = "entry_thresholds.valid_trade_min"


def spec(**overrides):
    values = {
        "parameter": ENTRY_CONVICTION,
        "candidate_values": (75, 80, 85),
        "baseline_value": 80,
        "parameter_paths": (PATH,),
        "base_config_metadata": CONFIG.run_metadata(),
        "objective_metric": MEAN_RETURN_OBJECTIVE,
        "plateau_tolerance": Decimal("0"),
        **overrides,
    }
    return threshold_sweep_spec(**values)


def candidate_config(parameter_set: ThresholdParameterSet):
    return replace(
        CONFIG,
        identity=ConfigIdentity(
            config_version=parameter_set.config_metadata["config_version"],
            strategy_version=parameter_set.config_metadata["strategy_version"],
            parameter_set_id=parameter_set.parameter_set_id,
        ),
    )


def entering_strategy(parameter_set: ThresholdParameterSet):
    def strategy(context: BacktestContext) -> BacktestIntent | None:
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
                config_metadata=parameter_set.config_metadata,
            ),
            entry_conviction=Decimal("90"),
            source_id=f"entry-{context.as_of.isoformat()}",
        )

    return strategy


def evaluator(predicate=lambda _value: True, *, shorten_value=None, alter_value=None):
    def evaluate(parameter_set: ThresholdParameterSet):
        config = candidate_config(parameter_set)
        selected = (
            entering_strategy(parameter_set)
            if predicate(parameter_set.value)
            else (lambda _context: None)
        )

        def factory(_window):
            return FoldStrategy(
                strategy=selected,
                strategy_id=f"btc185-{parameter_set.parameter_set_id}",
            )

        bars = (
            BARS[:-1]
            if shorten_value is not None and parameter_set.value == shorten_value
            else BARS
        )
        if alter_value is not None and parameter_set.value == alter_value:
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


def test_policy_parameter_and_revalidation_vocabularies_are_versioned() -> None:
    assert THRESHOLD_SWEEP_FEATURE_ID == "THRESHOLD_SWEEP"
    assert THRESHOLD_SWEEP_POLICY_VERSION.endswith("_V1")
    assert THRESHOLD_PLATEAU_POLICY_VERSION.endswith("_V1")
    assert THRESHOLD_METRIC_POLICY_VERSION.endswith("_V1")
    assert THRESHOLD_PARAMETER_STATUS == "PROVISIONAL_RESEARCH_CALIBRATABLE"
    assert THRESHOLD_REVALIDATION_SCOPES[ENTRY_CONVICTION] == (
        "ENTRY_CONVICTION_ACTION_BANDS",
    )
    assert "STRUCTURE_HARD_REJECT_BANDS" in THRESHOLD_REVALIDATION_SCOPES[
        STRUCTURE_MINIMUM
    ]
    assert THRESHOLD_REVALIDATION_SCOPES[HOLD_THRESHOLD] == (
        "HOLD_SCORE_ACTION_BANDS",
    )
    assert THRESHOLD_REVALIDATION_SCOPES[ADD_THRESHOLD] == (
        "ADD_SCORE_THRESHOLD",
    )


@pytest.mark.parametrize(
    ("parameter", "values"),
    [
        (ENTRY_CONVICTION, (75, 80)),
        (TREND_MINIMUM, (55, 70)),
        (FLOW_MINIMUM, (50, 55)),
        (POSITIONING_MINIMUM, (55, 60)),
        (STRUCTURE_MINIMUM, (60, 70)),
        (REWARD_RISK_MINIMUM, (Decimal("1.5"), Decimal("2"))),
        (STOP_BUFFER, (Decimal("0.25"), Decimal("0.5"))),
        (HOLD_THRESHOLD, (65, 70)),
        (ADD_THRESHOLD, (80, 85)),
        (RISK_BUDGET, (Decimal("0.0035"), Decimal("0.005"))),
    ],
)
def test_all_ticket_dimensions_produce_ordered_versioned_parameter_sets(
    parameter, values
) -> None:
    declared = spec(
        parameter=parameter,
        candidate_values=tuple(reversed(values)),
        baseline_value=values[0],
        parameter_paths=(f"research.{parameter}",),
    )

    points = threshold_parameter_sets(declared)

    assert tuple(point.value for point in points) == tuple(sorted(values))
    assert len({point.parameter_set_id for point in points}) == len(values)
    assert sum(point.baseline for point in points) == 1
    assert all(
        point.config_metadata["parameter_set_id"] == point.parameter_set_id
        for point in points
    )
    assert declared.revalidation_scopes == THRESHOLD_REVALIDATION_SCOPES[parameter]


def test_report_uses_out_of_sample_metrics_and_finds_adjacent_plateau() -> None:
    report = run_threshold_sweep(spec(), evaluator=evaluator(lambda value: value <= 80))

    assert tuple(point.value for point in report.points) == (
        Decimal("75"),
        Decimal("80"),
        Decimal("85"),
    )
    assert report.baseline.value == Decimal("80")
    assert report.best is not None and report.best.value == Decimal("75")
    assert len(report.plateaus) == 1
    plateau = report.plateaus[0]
    assert (plateau.lower_value, plateau.upper_value) == (
        Decimal("75"),
        Decimal("80"),
    )
    assert plateau.point_count == 2
    assert not report.isolated_optimum
    assert report.points[0].metrics.trade_count > 0
    assert report.points[2].metrics.trade_count == 0
    assert report.points[2].metrics.closed_trade_expectancy is None
    assert "THRESHOLD_SWEEP_ROBUST_PLATEAU" in report.reason_codes
    assert "THRESHOLD_SWEEP_SCORE_BAND_SCOPE_EVALUATED" in report.reason_codes
    assert set(report.reason_codes).issubset(THRESHOLD_SWEEP_REASON_CODES)


def test_a_lone_best_candidate_is_flagged_instead_of_promoted() -> None:
    report = run_threshold_sweep(spec(), evaluator=evaluator(lambda value: value == 80))

    assert report.best is not None and report.best.value == Decimal("80")
    assert report.plateaus == ()
    assert report.isolated_optimum
    assert "THRESHOLD_SWEEP_ISOLATED_OPTIMUM" in report.reason_codes
    assert report.parameter_status == THRESHOLD_PARAMETER_STATUS


def test_missing_closed_outcomes_remain_unavailable_not_zero_filled() -> None:
    declared = spec(objective_metric=EXPECTANCY_OBJECTIVE)

    report = run_threshold_sweep(declared, evaluator=evaluator(lambda _value: False))

    assert report.best is None
    assert report.plateaus == ()
    assert not report.isolated_optimum
    assert all(point.metrics.closed_trade_expectancy is None for point in report.points)
    assert "THRESHOLD_SWEEP_NO_COMPARABLE_OBJECTIVE" in report.reason_codes


def test_runs_are_deterministic_replayable_and_persist_nested_evidence() -> None:
    declared = spec()

    first = run_threshold_sweep(
        declared, evaluator=evaluator(lambda value: value <= 80)
    )
    second = run_threshold_sweep(
        declared, evaluator=evaluator(lambda value: value <= 80)
    )

    assert first == second
    assert first.report_id == second.report_id
    assert first.evidence_digest == second.evidence_digest
    assert restore_threshold_sweep_report(first.as_record()) == first
    assert all(
        point.validation.config_metadata == point.parameter_set.config_metadata
        for point in first.points
    )
    assert first.config_metadata == CONFIG.run_metadata()


def test_candidate_runs_must_share_schedule_split_costs_and_assumptions() -> None:
    with pytest.raises(ValueError, match="must share schedule"):
        run_threshold_sweep(spec(), evaluator=evaluator(shorten_value=85))

    with pytest.raises(ValueError, match="must share schedule"):
        run_threshold_sweep(spec(), evaluator=evaluator(alter_value=85))


def test_v11_benchmark_and_v12_scoring_cannot_mix_in_one_specification() -> None:
    nested_metadata = {
        **CONFIG.run_metadata(),
        "strategy_version": "swing_v1.1",
    }
    benchmark = spec(
        base_config_metadata=nested_metadata,
        scoring_architecture_version=SCORING_ARCHITECTURE_V1_1_BENCHMARK,
    )

    assert (
        benchmark.scoring_architecture_version
        == SCORING_ARCHITECTURE_V1_1_BENCHMARK
    )
    with pytest.raises(ValueError, match="must isolate"):
        spec(scoring_architecture_version=SCORING_ARCHITECTURE_V1_1_BENCHMARK)
    with pytest.raises(ValueError, match="must isolate"):
        spec(
            base_config_metadata=nested_metadata,
            scoring_architecture_version=SCORING_ARCHITECTURE_V1_2,
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda row: row["points"][0]["metrics"].__setitem__("trade_count", 999),
        lambda row: row["points"][0]["parameter_set"].__setitem__("value", "99"),
        lambda row: row["points"][0]["validation"].__setitem__(
            "evidence_digest", "changed"
        ),
        lambda row: row["plateaus"][0].__setitem__("point_count", 999),
        lambda row: row.__setitem__("best_parameter_set_id", "changed"),
        lambda row: row["spec"].__setitem__("scoring_architecture_version", "mixed"),
    ],
)
def test_restore_rejects_derived_identity_and_nested_tampering(mutate) -> None:
    report = run_threshold_sweep(spec(), evaluator=evaluator(lambda value: value <= 80))
    record = deepcopy(report.as_record())
    mutate(record)

    with pytest.raises((TypeError, ValueError)):
        restore_threshold_sweep_report(record)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"candidate_values": (80,), "baseline_value": 80}, "at least two"),
        ({"candidate_values": (80, 80), "baseline_value": 80}, "unique"),
        ({"candidate_values": (75, 80), "baseline_value": 85}, "must be one"),
        ({"candidate_values": (75, float("nan"))}, "must be finite"),
        ({"parameter_paths": ()}, "unique paths"),
        ({"parameter_paths": ("not_dotted",)}, "dotted"),
        ({"plateau_tolerance": -1}, "non-negative"),
        ({"objective_metric": "profit"}, "must be one of"),
    ],
)
def test_invalid_or_ambiguous_sweep_definitions_fail_closed(overrides, message) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        spec(**overrides)


def test_report_lookup_rejects_an_unknown_parameter_set() -> None:
    report = run_threshold_sweep(spec(), evaluator=evaluator())

    with pytest.raises(KeyError):
        report.point("unknown")
