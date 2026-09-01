"""BTC-188: deterministic multi-dimensional parameter sensitivity surfaces."""

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from types import SimpleNamespace

import pytest

from btc_predictor.backtest import (
    ADD_THRESHOLD,
    ARM_ENTRY_ACTION,
    CALMAR_AVAILABLE,
    CALMAR_NO_DRAWDOWN,
    CALMAR_OBJECTIVE,
    CALMAR_UNAVAILABLE_DRAWDOWN,
    DRAWDOWN_AVAILABLE,
    DRAWDOWN_NON_POSITIVE_NAV,
    DRAWDOWN_NO_EQUITY_CURVE,
    ENTRY_CONVICTION,
    EXPECTANCY_OBJECTIVE,
    MEAN_RETURN_OBJECTIVE,
    MINIMUM_SURFACE_DIMENSIONS,
    PARAMETER_SURFACE_FEATURE_ID,
    PARAMETER_SURFACE_POLICY_VERSION,
    PARAMETER_SURFACE_REASON_CODES,
    REWARD_RISK_MINIMUM,
    RISK_BUDGET,
    SCORING_ARCHITECTURE_V1_1_BENCHMARK,
    SCORING_ARCHITECTURE_V1_2,
    SHARPE_AVAILABLE,
    SHARPE_INSUFFICIENT_PERIODS,
    SHARPE_NON_POSITIVE_NAV,
    SHARPE_OBJECTIVE,
    SHARPE_ZERO_DISPERSION,
    STOP_BUFFER,
    STRUCTURE_MINIMUM,
    SURFACE_CALMAR_POLICY_VERSION,
    SURFACE_DRAWDOWN_POLICY_VERSION,
    SURFACE_METRIC_EXPONENT,
    SURFACE_METRIC_POLICY_VERSION,
    SURFACE_OBJECTIVES,
    SURFACE_PARAMETER_STATUS,
    SURFACE_PLATEAU_POLICY_VERSION,
    SURFACE_SHARPE_POLICY_VERSION,
    THRESHOLD_PARAMETER_STATUS,
    THRESHOLD_REVALIDATION_SCOPES,
    BacktestContext,
    BacktestIntent,
    FoldStrategy,
    SurfaceParameterSet,
    TrainingWindow,
    parameter_surface_spec,
    restore_parameter_surface_report,
    run_parameter_surface,
    run_walk_forward,
    surface_axis,
    surface_parameter_sets,
    threshold_sweep_metrics,
    walk_forward_plan,
)
from btc_predictor.backtest.parameter_surfaces import (
    SURFACE_DECIMAL_PRECISION,
    _max_drawdown,
    _period_returns,
    _sharpe,
)
from btc_predictor.config.strategy import ConfigIdentity
from btc_predictor.data import OhlcvBar
from btc_predictor.risk.stop import calculate_initial_stop
from btc_predictor.tests.test_backtest_walk_forward import CONFIG, NAV


UTC = timezone.utc
START = datetime(2024, 1, 1, tzinfo=UTC)

# Three train bars, then four four-bar out-of-sample folds.  The first fold
# rises and then breaks the structural stop, so every traded cell reports a
# real drawdown, one closed trade, an expectancy, and an R-multiple; the later
# folds drift up inside the entry zone so the surface is not uniformly losing.
CLOSES = (
    100000, 100500, 101000,
    101500, 103000, 99000, 92000,
    93000, 95000, 97000, 99000,
    100000, 102000, 104000, 106000,
    107000, 109000, 111000, 113000,
    114000,
)

PARAMETER_PATHS = {
    ENTRY_CONVICTION: "entry_thresholds.valid_trade_min",
    RISK_BUDGET: "risk_schedule.risk_budget_fraction_nav",
    ADD_THRESHOLD: "add_thresholds.add_min",
    STOP_BUFFER: "stops.volatility_buffer_atr_multiplier",
    STRUCTURE_MINIMUM: "entry_thresholds.structure_min",
    REWARD_RISK_MINIMUM: "entry_thresholds.reward_risk_min",
}

PARAMETER_VALUES = {
    ENTRY_CONVICTION: (75, 80, 85),
    RISK_BUDGET: (Decimal("0.0035"), Decimal("0.005")),
    ADD_THRESHOLD: (80, 85),
    STOP_BUFFER: (Decimal("0.25"), Decimal("0.5")),
    STRUCTURE_MINIMUM: (60, 70),
    REWARD_RISK_MINIMUM: (Decimal("1.5"), Decimal("2")),
}


def bar(day: int, close: int) -> OhlcvBar:
    """One replayable daily bar; only the path has to be deterministic."""

    timestamp = START + timedelta(days=day)
    value = Decimal(str(close))
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1d",
        open=value - Decimal("200"),
        high=value + Decimal("800"),
        low=value - Decimal("900"),
        close=value,
        volume=Decimal("100"),
        provider="coinbase",
        ingested_at=timestamp + timedelta(days=1),
    )


BARS = tuple(bar(day, close) for day, close in enumerate(CLOSES))


def axis(parameter: str, **overrides):
    values = {
        "parameter": parameter,
        "candidate_values": PARAMETER_VALUES[parameter],
        "baseline_value": PARAMETER_VALUES[parameter][-1],
        "parameter_paths": (PARAMETER_PATHS[parameter],),
        **overrides,
    }
    return surface_axis(**values)


def spec(**overrides):
    values = {
        "axes": (axis(ENTRY_CONVICTION), axis(RISK_BUDGET)),
        "base_config_metadata": CONFIG.run_metadata(),
        "objective_metric": MEAN_RETURN_OBJECTIVE,
        "plateau_tolerance": Decimal("0"),
        **overrides,
    }
    return parameter_surface_spec(**values)


def candidate_config(parameter_set: SurfaceParameterSet):
    return replace(
        CONFIG,
        identity=ConfigIdentity(
            config_version=parameter_set.config_metadata["config_version"],
            strategy_version=parameter_set.config_metadata["strategy_version"],
            parameter_set_id=parameter_set.parameter_set_id,
        ),
    )


def entering_strategy(parameter_set: SurfaceParameterSet, stop_fraction: Decimal):
    def strategy(context: BacktestContext) -> BacktestIntent | None:
        if context.bar.timestamp != context.bars[0].timestamp:
            return None
        close = context.bar.close
        return BacktestIntent(
            action=ARM_ENTRY_ACTION,
            entry_zone_lower=close * Decimal("0.97"),
            entry_zone_upper=close * Decimal("1.03"),
            initial_stop=calculate_initial_stop(
                invalidation_price=close * stop_fraction,
                buffer=Decimal("0"),
                direction="long",
                entry_price=close,
                config_metadata=parameter_set.config_metadata,
            ),
            entry_conviction=Decimal("90"),
            source_id=f"entry-{context.as_of.isoformat()}",
        )

    return strategy


def evaluator(
    predicate=lambda _parameter_set: True,
    *,
    stop=lambda _parameter_set: Decimal("0.95"),
    shorten_at=None,
    alter_at=None,
    test_periods=4,
    step_periods=4,
):
    """Run one comparable walk-forward per grid cell."""

    def evaluate(parameter_set: SurfaceParameterSet):
        config = candidate_config(parameter_set)
        selected = (
            entering_strategy(parameter_set, stop(parameter_set))
            if predicate(parameter_set)
            else (lambda _context: None)
        )

        def factory(_window):
            return FoldStrategy(
                strategy=selected,
                strategy_id=f"btc188-{parameter_set.parameter_set_id}",
            )

        bars = BARS
        if shorten_at is not None and parameter_set.coordinates == shorten_at:
            bars = BARS[:-1]
        if alter_at is not None and parameter_set.coordinates == alter_at:
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
                test_periods=test_periods,
                step_periods=step_periods,
            ),
            starting_nav=NAV,
            strategy_config=config,
        )

    return evaluate


def recalibrating_evaluator(recalibrated_at):
    """Refit one cell per fold while every other cell keeps a constant rule."""

    def evaluate(parameter_set: SurfaceParameterSet):
        config = candidate_config(parameter_set)
        strategy = entering_strategy(parameter_set, Decimal("0.95"))
        refit = parameter_set.coordinates == recalibrated_at

        def factory(training: TrainingWindow):
            fold_number = training.window.fold_number
            return FoldStrategy(
                strategy=strategy,
                strategy_id=(
                    f"btc188-{parameter_set.parameter_set_id}-fold{fold_number}"
                    if refit
                    else f"btc188-{parameter_set.parameter_set_id}"
                ),
                calibration={"refit_fold": fold_number} if refit else None,
            )

        return run_walk_forward(
            BARS,
            strategy_factory=factory,
            plan=walk_forward_plan(
                config, train_periods=3, test_periods=4, step_periods=4
            ),
            starting_nav=NAV,
            strategy_config=config,
        )

    return evaluate


def declining_stop(parameter_set: SurfaceParameterSet) -> Decimal:
    """A tighter structural stop the further the cell sits from the origin."""

    return Decimal("0.95") - Decimal(sum(parameter_set.coordinates)) * Decimal("0.005")


def derived_drawdown(validation) -> Decimal:
    """Independently recompute the worst within-fold NAV decline."""

    with localcontext(Context(prec=SURFACE_DECIMAL_PRECISION)):
        worst = Decimal("0")
        for fold in validation.folds:
            peak = fold.starting_nav
            for point in fold.result.equity_curve:
                peak = max(peak, point.nav)
                worst = max(worst, (peak - point.nav) / peak)
        return worst.quantize(SURFACE_METRIC_EXPONENT, rounding=ROUND_HALF_EVEN)


def derived_sharpe(validation) -> Decimal:
    """Independently recompute the pooled within-fold period-return Sharpe."""

    with localcontext(Context(prec=SURFACE_DECIMAL_PRECISION)):
        returns: list[Decimal] = []
        for fold in validation.folds:
            previous = fold.starting_nav
            for point in fold.result.equity_curve:
                returns.append((point.nav - previous) / previous)
                previous = point.nav
        count = Decimal(len(returns))
        mean = sum(returns, Decimal("0")) / count
        variance = sum(
            ((value - mean) ** 2 for value in returns), Decimal("0")
        ) / (count - Decimal("1"))
        return (mean / variance.sqrt()).quantize(
            SURFACE_METRIC_EXPONENT, rounding=ROUND_HALF_EVEN
        )


def test_policy_vocabularies_are_versioned_and_reuse_btc185_parameters() -> None:
    assert PARAMETER_SURFACE_FEATURE_ID == "PARAMETER_SENSITIVITY_SURFACE"
    assert PARAMETER_SURFACE_POLICY_VERSION.endswith("_V1")
    assert SURFACE_PLATEAU_POLICY_VERSION.endswith("_V1")
    assert SURFACE_METRIC_POLICY_VERSION.endswith("_V1")
    assert SURFACE_DRAWDOWN_POLICY_VERSION.endswith("_V1")
    assert SURFACE_SHARPE_POLICY_VERSION.endswith("_V1")
    assert SURFACE_CALMAR_POLICY_VERSION.endswith("_V1")
    assert SURFACE_PARAMETER_STATUS == THRESHOLD_PARAMETER_STATUS
    assert MINIMUM_SURFACE_DIMENSIONS == 2
    assert SHARPE_OBJECTIVE in SURFACE_OBJECTIVES
    assert CALMAR_OBJECTIVE in SURFACE_OBJECTIVES
    assert MEAN_RETURN_OBJECTIVE in SURFACE_OBJECTIVES


@pytest.mark.parametrize(
    ("first", "second"),
    [
        (ENTRY_CONVICTION, RISK_BUDGET),
        (ADD_THRESHOLD, STOP_BUFFER),
        (STRUCTURE_MINIMUM, REWARD_RISK_MINIMUM),
    ],
)
def test_ticket_surfaces_produce_ordered_versioned_parameter_sets(
    first, second
) -> None:
    declared = spec(axes=(axis(second), axis(first)))

    cells = surface_parameter_sets(declared)

    assert declared.parameters == tuple(sorted((first, second)))
    assert declared.dimensions == 2
    assert len(cells) == declared.cell_count == len(PARAMETER_VALUES[first]) * len(
        PARAMETER_VALUES[second]
    )
    assert len({cell.parameter_set_id for cell in cells}) == len(cells)
    assert sum(cell.baseline for cell in cells) == 1
    assert all(
        cell.config_metadata["parameter_set_id"] == cell.parameter_set_id
        for cell in cells
    )
    assert all(len(cell.parameter_set_id) <= 64 for cell in cells)
    for declared_axis in declared.axes:
        assert (
            declared_axis.revalidation_scopes
            == THRESHOLD_REVALIDATION_SCOPES[declared_axis.parameter]
        )


def test_axis_declaration_order_does_not_change_the_surface_identity() -> None:
    forward = spec(axes=(axis(ENTRY_CONVICTION), axis(RISK_BUDGET)))
    reversed_axes = spec(axes=(axis(RISK_BUDGET), axis(ENTRY_CONVICTION)))

    assert forward.surface_id == reversed_axes.surface_id
    assert surface_parameter_sets(forward) == surface_parameter_sets(reversed_axes)


def test_grids_beyond_two_dimensions_are_supported() -> None:
    declared = spec(
        axes=(axis(ENTRY_CONVICTION), axis(RISK_BUDGET), axis(STOP_BUFFER))
    )

    cells = surface_parameter_sets(declared)

    assert declared.dimensions == 3
    assert declared.shape == (3, 2, 2)
    assert len(cells) == 12
    assert cells[0].coordinates == (0, 0, 0)
    assert cells[-1].coordinates == (2, 1, 1)
    assert all(len(cell.values) == 3 for cell in cells)
    assert cells[5].value(RISK_BUDGET) == Decimal("0.0035")


def test_every_cell_reports_the_required_out_of_sample_metrics() -> None:
    report = run_parameter_surface(spec(), evaluator=evaluator())

    assert len(report.cells) == 6
    for cell in report.cells:
        metrics = cell.metrics
        assert metrics.trade_count == 4
        assert metrics.closed_trade_count == 1
        assert metrics.closed_trade_expectancy is not None
        assert metrics.mean_r_multiple is not None
        assert metrics.max_drawdown_status == DRAWDOWN_AVAILABLE
        assert metrics.max_drawdown_fraction > 0
        assert metrics.sharpe_status == SHARPE_AVAILABLE
        assert metrics.sharpe_ratio is not None
        assert metrics.calmar_status == CALMAR_AVAILABLE
        assert metrics.calmar_ratio is not None
        assert metrics.period_return_count == 16
        assert metrics.outcome == threshold_sweep_metrics(cell.validation)


def test_cell_risk_metrics_match_independently_derived_evidence() -> None:
    report = run_parameter_surface(spec(), evaluator=evaluator(stop=declining_stop))

    for cell in report.cells:
        metrics = cell.metrics
        assert metrics.max_drawdown_fraction == derived_drawdown(cell.validation)
        assert metrics.sharpe_ratio == derived_sharpe(cell.validation)
        with localcontext(Context(prec=SURFACE_DECIMAL_PRECISION)):
            expected_calmar = (
                metrics.mean_return_fraction / metrics.max_drawdown_fraction
            ).quantize(SURFACE_METRIC_EXPONENT, rounding=ROUND_HALF_EVEN)
        assert metrics.calmar_ratio == expected_calmar
    # A tighter structural stop sizes a smaller position, so the surface is
    # not flat in either the outcome or the drawdown it accepted.
    assert len({cell.metrics.max_drawdown_fraction for cell in report.cells}) == 4
    assert len({cell.metrics.mean_return_fraction for cell in report.cells}) == 4


def test_a_tolerance_region_is_reported_as_a_connected_plateau() -> None:
    report = run_parameter_surface(
        spec(plateau_tolerance=Decimal("0.000012")),
        evaluator=evaluator(stop=declining_stop),
    )

    assert report.best is not None and report.best.coordinates == (0, 0)
    assert len(report.plateaus) == 1
    plateau = report.plateaus[0]
    assert plateau.cell_count == 3
    assert plateau.coordinates == ((0, 0), (0, 1), (1, 0))
    assert plateau.contains_global_best
    assert report.best_plateau_id == plateau.plateau_id
    assert not report.isolated_optimum
    # The bounding box spans four cells; membership stays exact.
    spans = {span.parameter: span for span in plateau.axis_spans}
    assert spans[ENTRY_CONVICTION].lower_value == Decimal("75")
    assert spans[ENTRY_CONVICTION].upper_value == Decimal("80")
    assert spans[RISK_BUDGET].lower_value == Decimal("0.0035")
    assert spans[RISK_BUDGET].upper_value == Decimal("0.005")
    assert plateau.best_objective_value >= plateau.worst_objective_value
    assert "SURFACE_ROBUST_PLATEAU" in report.reason_codes
    assert "SURFACE_ISOLATED_OPTIMUM_OVERFIT_RISK" not in report.reason_codes
    assert set(report.reason_codes).issubset(PARAMETER_SURFACE_REASON_CODES)


def test_equal_best_cells_that_are_not_grid_adjacent_are_not_one_plateau() -> None:
    corners = {(0, 0), (2, 1)}

    report = run_parameter_surface(
        spec(),
        evaluator=evaluator(lambda cell: cell.coordinates in corners),
    )

    assert report.best is not None and report.best.coordinates == (0, 0)
    assert report.plateaus == ()
    assert report.isolated_optimum
    assert report.best_plateau_id is None
    assert "SURFACE_ISOLATED_OPTIMUM_OVERFIT_RISK" in report.reason_codes


def test_a_lone_best_cell_is_flagged_as_potential_overfit_not_promoted() -> None:
    report = run_parameter_surface(
        spec(), evaluator=evaluator(stop=declining_stop)
    )

    assert report.best is not None and report.best.coordinates == (0, 0)
    assert report.plateaus == ()
    assert report.isolated_optimum
    assert report.parameter_status == SURFACE_PARAMETER_STATUS
    assert "SURFACE_ISOLATED_OPTIMUM_OVERFIT_RISK" in report.reason_codes


def test_unavailable_cell_objectives_break_plateau_connectivity() -> None:
    # (1, 1) is the only grid neighbour joining (0, 1) to (2, 1); leaving it
    # without a comparable objective must split the region rather than bridge it.
    traded = {(0, 0), (0, 1), (2, 1)}

    report = run_parameter_surface(
        spec(objective_metric=EXPECTANCY_OBJECTIVE),
        evaluator=evaluator(lambda cell: cell.coordinates in traded),
    )

    assert [
        cell.metrics.closed_trade_expectancy is None for cell in report.cells
    ] == [False, False, True, True, True, False]
    assert len(report.plateaus) == 1
    plateau = report.plateaus[0]
    assert plateau.coordinates == ((0, 0), (0, 1))
    assert report.best is not None and report.best.coordinates == (0, 0)
    assert not report.isolated_optimum
    assert "SURFACE_UNAVAILABLE_CELL_OBJECTIVE" in report.reason_codes
    assert "SURFACE_CELLS_WITHOUT_TRADES" in report.reason_codes


def test_missing_closed_outcomes_remain_unavailable_not_zero_filled() -> None:
    report = run_parameter_surface(
        spec(objective_metric=EXPECTANCY_OBJECTIVE),
        evaluator=evaluator(lambda _cell: False),
    )

    assert report.best is None
    assert report.plateaus == ()
    assert report.best_plateau_id is None
    assert not report.isolated_optimum
    assert all(
        cell.metrics.closed_trade_expectancy is None for cell in report.cells
    )
    assert all(cell.metrics.mean_r_multiple is None for cell in report.cells)
    assert "SURFACE_NO_COMPARABLE_OBJECTIVE" in report.reason_codes
    assert "SURFACE_UNAVAILABLE_CELL_OBJECTIVE" not in report.reason_codes


def test_a_flat_surface_without_trades_is_declared_absence_of_evidence() -> None:
    report = run_parameter_surface(spec(), evaluator=evaluator(lambda _cell: False))

    assert all(cell.metrics.trade_count == 0 for cell in report.cells)
    assert all(
        cell.metrics.mean_return_fraction == Decimal("0") for cell in report.cells
    )
    # An untraded cell returns exactly zero, so the tie still forms one
    # connected region; the report must not let that read as robustness.
    assert len(report.plateaus) == 1
    assert report.plateaus[0].cell_count == len(report.cells)
    assert "SURFACE_NO_TRADES" in report.reason_codes
    assert "SURFACE_CELLS_WITHOUT_TRADES" not in report.reason_codes
    # A flat NAV path has no dispersion and no decline; neither ratio is
    # reported as zero.
    for cell in report.cells:
        assert cell.metrics.max_drawdown_fraction == Decimal("0")
        assert cell.metrics.sharpe_ratio is None
        assert cell.metrics.sharpe_status == SHARPE_ZERO_DISPERSION
        assert cell.metrics.calmar_ratio is None
        assert cell.metrics.calmar_status == CALMAR_NO_DRAWDOWN
    assert restore_parameter_surface_report(report.as_record()) == report


def test_cells_that_never_traded_are_named_in_a_partly_traded_surface() -> None:
    report = run_parameter_surface(
        spec(), evaluator=evaluator(lambda cell: cell.coordinates[0] == 0)
    )

    assert [cell.metrics.trade_count > 0 for cell in report.cells] == [
        True,
        True,
        False,
        False,
        False,
        False,
    ]
    assert "SURFACE_CELLS_WITHOUT_TRADES" in report.reason_codes
    assert "SURFACE_NO_TRADES" not in report.reason_codes


def test_a_fully_traded_surface_declares_no_missing_trade_evidence() -> None:
    report = run_parameter_surface(spec(), evaluator=evaluator())

    assert all(cell.metrics.trade_count > 0 for cell in report.cells)
    assert "SURFACE_NO_TRADES" not in report.reason_codes
    assert "SURFACE_CELLS_WITHOUT_TRADES" not in report.reason_codes
    assert "SURFACE_RISK_METRICS_UNANNUALIZED" in report.reason_codes
    assert "SURFACE_SCORE_BAND_SCOPE_EVALUATED" in report.reason_codes


def test_runs_are_deterministic_replayable_and_persist_nested_evidence() -> None:
    declared = spec(plateau_tolerance=Decimal("0.000012"))

    first = run_parameter_surface(declared, evaluator=evaluator(stop=declining_stop))
    second = run_parameter_surface(declared, evaluator=evaluator(stop=declining_stop))

    assert first == second
    assert first.report_id == second.report_id
    assert first.evidence_digest == second.evidence_digest
    assert restore_parameter_surface_report(first.as_record()) == first
    assert all(
        cell.validation.config_metadata == cell.parameter_set.config_metadata
        for cell in first.cells
    )
    assert first.config_metadata == CONFIG.run_metadata()


def test_results_link_back_to_parameter_set_ids() -> None:
    report = run_parameter_surface(
        spec(plateau_tolerance=Decimal("0.000012")),
        evaluator=evaluator(stop=declining_stop),
    )

    plateau = report.plateaus[0]
    for parameter_set_id in plateau.parameter_set_ids:
        cell = report.cell(parameter_set_id)
        assert cell.parameter_set.surface_id == report.spec.surface_id
        assert cell.validation.config_metadata["parameter_set_id"] == parameter_set_id
    assert report.cell(plateau.best_parameter_set_id).coordinates in plateau.coordinates
    assert report.best_parameter_set_id is not None
    assert report.cell_at((0, 1)).parameter_set.ordinal == 1
    assert report.baseline.values == (Decimal("85"), Decimal("0.005"))


def test_cell_runs_must_share_schedule_split_costs_and_assumptions() -> None:
    with pytest.raises(ValueError, match="must share schedule"):
        run_parameter_surface(spec(), evaluator=evaluator(shorten_at=(2, 1)))

    with pytest.raises(ValueError, match="must share schedule"):
        run_parameter_surface(spec(), evaluator=evaluator(alter_at=(2, 1)))


def test_cells_must_share_one_fitting_procedure() -> None:
    with pytest.raises(ValueError, match="fitting procedure"):
        run_parameter_surface(spec(), evaluator=recalibrating_evaluator((2, 1)))


def test_v11_benchmark_and_v12_scoring_cannot_mix_in_one_surface() -> None:
    nested_metadata = {**CONFIG.run_metadata(), "strategy_version": "swing_v1.1"}
    benchmark = spec(
        base_config_metadata=nested_metadata,
        scoring_architecture_version=SCORING_ARCHITECTURE_V1_1_BENCHMARK,
    )

    assert (
        benchmark.scoring_architecture_version == SCORING_ARCHITECTURE_V1_1_BENCHMARK
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
        lambda row: row["cells"][0]["metrics"].__setitem__("sharpe_ratio", "9"),
        lambda row: row["cells"][0]["metrics"].__setitem__(
            "max_drawdown_status", DRAWDOWN_NON_POSITIVE_NAV
        ),
        lambda row: row["cells"][0]["metrics"]["outcome"].__setitem__(
            "trade_count", 999
        ),
        lambda row: row["cells"][0]["parameter_set"].__setitem__(
            "values", ["99", "0.005"]
        ),
        lambda row: row["cells"][0]["validation"].__setitem__(
            "evidence_digest", "changed"
        ),
        lambda row: row["plateaus"][0].__setitem__("cell_count", 999),
        lambda row: row["plateaus"][0].__setitem__("contains_global_best", False),
        lambda row: row.__setitem__("best_parameter_set_id", "changed"),
        lambda row: row.__setitem__("isolated_optimum", True),
        lambda row: row["spec"].__setitem__("scoring_architecture_version", "mixed"),
        lambda row: row["spec"]["axes"][0].__setitem__("revalidation_scopes", []),
    ],
)
def test_restore_rejects_derived_identity_and_nested_tampering(mutate) -> None:
    report = run_parameter_surface(
        spec(plateau_tolerance=Decimal("0.000012")),
        evaluator=evaluator(stop=declining_stop),
    )
    record = deepcopy(report.as_record())
    mutate(record)

    with pytest.raises((TypeError, ValueError, KeyError)):
        restore_parameter_surface_report(record)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"axes": (axis(ENTRY_CONVICTION),)}, "at least 2 axes"),
        (
            {"axes": (axis(ENTRY_CONVICTION), axis(ENTRY_CONVICTION))},
            "distinct parameters",
        ),
        (
            {
                "axes": (
                    axis(ENTRY_CONVICTION),
                    axis(
                        RISK_BUDGET,
                        parameter_paths=(PARAMETER_PATHS[ENTRY_CONVICTION],),
                    ),
                )
            },
            "share configuration paths",
        ),
        ({"plateau_tolerance": -1}, "non-negative"),
        ({"objective_metric": "profit"}, "must be one of"),
    ],
)
def test_invalid_or_ambiguous_surface_definitions_fail_closed(
    overrides, message
) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        spec(**overrides)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"candidate_values": (80,), "baseline_value": 80}, "at least two"),
        ({"candidate_values": (80, 80), "baseline_value": 80}, "unique"),
        ({"candidate_values": (75, 80), "baseline_value": 85}, "must be one"),
        ({"candidate_values": (75, float("nan"))}, "must be finite"),
        ({"candidate_values": (75, 180)}, "between 0 and 100"),
        ({"parameter_paths": ()}, "unique paths"),
        ({"parameter_paths": ("not_dotted",)}, "dotted"),
    ],
)
def test_invalid_axis_definitions_fail_closed(overrides, message) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        axis(ENTRY_CONVICTION, **overrides)


def test_unknown_axis_parameters_are_rejected() -> None:
    with pytest.raises(ValueError, match="must be one of"):
        surface_axis(
            parameter="unknown_threshold",
            candidate_values=(1, 2),
            baseline_value=1,
            parameter_paths=("research.unknown",),
        )


def test_report_lookup_rejects_unknown_cells() -> None:
    report = run_parameter_surface(spec(), evaluator=evaluator())

    with pytest.raises(KeyError):
        report.cell("unknown")
    with pytest.raises(KeyError):
        report.cell_at((9, 9))
    with pytest.raises(KeyError):
        report.cells[0].parameter_set.value(STOP_BUFFER)


def test_undefined_risk_statistics_are_never_silently_zero_filled() -> None:
    ruined = SimpleNamespace(
        folds=(
            SimpleNamespace(
                starting_nav=Decimal("0"),
                result=SimpleNamespace(
                    equity_curve=(SimpleNamespace(nav=Decimal("10")),)
                ),
            ),
        )
    )
    no_bars = SimpleNamespace(
        folds=(
            SimpleNamespace(
                starting_nav=Decimal("1000"),
                result=SimpleNamespace(equity_curve=()),
            ),
        )
    )

    assert _max_drawdown(ruined) == (None, DRAWDOWN_NON_POSITIVE_NAV)
    assert _period_returns(ruined) == ((), SHARPE_NON_POSITIVE_NAV)
    assert _max_drawdown(no_bars) == (None, DRAWDOWN_NO_EQUITY_CURVE)
    assert _period_returns(no_bars) == ((), SHARPE_AVAILABLE)
    assert _sharpe((), SHARPE_NON_POSITIVE_NAV) == (None, SHARPE_NON_POSITIVE_NAV)
    assert _sharpe((Decimal("0.01"),), SHARPE_AVAILABLE) == (
        None,
        SHARPE_INSUFFICIENT_PERIODS,
    )
    assert _sharpe(
        (Decimal("0.01"), Decimal("0.01")), SHARPE_AVAILABLE
    ) == (None, SHARPE_ZERO_DISPERSION)


def test_calmar_stays_unavailable_when_the_drawdown_is_unavailable() -> None:
    from btc_predictor.backtest.parameter_surfaces import _calmar

    assert _calmar(Decimal("0.1"), None, DRAWDOWN_NON_POSITIVE_NAV) == (
        None,
        CALMAR_UNAVAILABLE_DRAWDOWN,
    )
    assert _calmar(Decimal("0.1"), Decimal("0"), DRAWDOWN_AVAILABLE) == (
        None,
        CALMAR_NO_DRAWDOWN,
    )
    assert _calmar(Decimal("0.1"), Decimal("0.5"), DRAWDOWN_AVAILABLE) == (
        Decimal("0.200000000000"),
        CALMAR_AVAILABLE,
    )
