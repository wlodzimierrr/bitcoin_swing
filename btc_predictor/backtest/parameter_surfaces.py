"""Deterministic multi-dimensional parameter sensitivity surfaces (BTC-188).

BTC-185 varies exactly one declared scalar threshold.  This layer extends that
research to parameter surfaces such as ``f(EntryThreshold, RiskBudget)``,
``f(AddThreshold, StopBuffer)``, and ``f(StructureMinimum, RRMinimum)``: every
cell of an axis-aligned grid is evaluated as a separate complete BTC-182
out-of-sample walk-forward validation.

The surface layer does not rescore features, alter strategy configuration, or
promote a production parameter.  A caller receives a versioned parameter-set
identity for each cell, builds the corresponding strategy through the existing
owners, and returns that cell's validation.  Net outcome metrics stay owned by
BTC-185; this module adds only the drawdown and risk-adjusted statistics the
ticket requires per cell.

Robustness is reported as connected regions rather than best points.  Cells
whose objective is within an explicit absolute tolerance of the global best
form plateaus when they are grid-adjacent; a best cell with no such neighbour
is flagged as an isolated optimum and potential overfit rather than promoted.
A cell that never traded still returns exactly zero, so the report also
declares when some or all cells produced no trades and a flat region is
absence of evidence rather than robustness.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_EVEN, Context, Decimal, InvalidOperation, localcontext
from itertools import product
from typing import Any

from btc_predictor.backtest.threshold_sweeps import (
    ADD_THRESHOLD,
    ENTRY_CONVICTION,
    EXPECTANCY_OBJECTIVE,
    HOLD_THRESHOLD,
    MEAN_RETURN_OBJECTIVE,
    MEAN_R_OBJECTIVE,
    SCORING_ARCHITECTURE_V1_2,
    STRUCTURE_MINIMUM,
    THRESHOLD_PARAMETERS,
    THRESHOLD_PARAMETER_STATUS,
    THRESHOLD_REVALIDATION_SCOPES,
    ThresholdSweepMetrics,
    comparable_run_signature,
    threshold_config_metadata,
    threshold_parameter_paths,
    threshold_parameter_value,
    threshold_sweep_metrics,
    validate_scoring_architecture,
)
from btc_predictor.backtest.walk_forward import (
    WalkForwardValidation,
    restore_walk_forward_validation,
)


PARAMETER_SURFACE_FEATURE_ID = "PARAMETER_SENSITIVITY_SURFACE"
PARAMETER_SURFACE_POLICY_VERSION = "MULTI_DIMENSIONAL_PARAMETER_SURFACE_V1"
SURFACE_PLATEAU_POLICY_VERSION = "CONNECTED_GRID_GLOBAL_BEST_TOLERANCE_V1"
SURFACE_METRIC_POLICY_VERSION = "OUT_OF_SAMPLE_NET_OUTCOME_METRICS_V1"
SURFACE_DRAWDOWN_POLICY_VERSION = "WORST_FOLD_PEAK_TO_TROUGH_NAV_DRAWDOWN_V1"
SURFACE_SHARPE_POLICY_VERSION = "POOLED_WITHIN_FOLD_PERIOD_RETURN_ZERO_RF_SHARPE_V1"
SURFACE_CALMAR_POLICY_VERSION = "MEAN_FOLD_RETURN_OVER_MAX_DRAWDOWN_V1"
SURFACE_PARAMETER_STATUS = THRESHOLD_PARAMETER_STATUS

SURFACE_METRIC_EXPONENT = Decimal("1E-12")
SURFACE_DECIMAL_PRECISION = 60
MINIMUM_SURFACE_DIMENSIONS = 2

SHARPE_OBJECTIVE = "sharpe_ratio"
CALMAR_OBJECTIVE = "calmar_ratio"
SURFACE_OBJECTIVES = (
    MEAN_RETURN_OBJECTIVE,
    EXPECTANCY_OBJECTIVE,
    MEAN_R_OBJECTIVE,
    SHARPE_OBJECTIVE,
    CALMAR_OBJECTIVE,
)

DRAWDOWN_AVAILABLE = "AVAILABLE"
DRAWDOWN_NO_EQUITY_CURVE = "UNAVAILABLE_NO_EQUITY_CURVE"
DRAWDOWN_NON_POSITIVE_NAV = "UNDEFINED_NON_POSITIVE_NAV"
DRAWDOWN_STATUSES = (
    DRAWDOWN_AVAILABLE,
    DRAWDOWN_NO_EQUITY_CURVE,
    DRAWDOWN_NON_POSITIVE_NAV,
)

SHARPE_AVAILABLE = "AVAILABLE"
SHARPE_INSUFFICIENT_PERIODS = "UNAVAILABLE_INSUFFICIENT_PERIODS"
SHARPE_ZERO_DISPERSION = "UNDEFINED_ZERO_DISPERSION"
SHARPE_NON_POSITIVE_NAV = "UNDEFINED_NON_POSITIVE_NAV"
SHARPE_STATUSES = (
    SHARPE_AVAILABLE,
    SHARPE_INSUFFICIENT_PERIODS,
    SHARPE_ZERO_DISPERSION,
    SHARPE_NON_POSITIVE_NAV,
)

CALMAR_AVAILABLE = "AVAILABLE"
CALMAR_NO_DRAWDOWN = "UNDEFINED_NO_DRAWDOWN"
CALMAR_UNAVAILABLE_DRAWDOWN = "UNAVAILABLE_DRAWDOWN"
CALMAR_STATUSES = (
    CALMAR_AVAILABLE,
    CALMAR_NO_DRAWDOWN,
    CALMAR_UNAVAILABLE_DRAWDOWN,
)

_SCORE_BAND_PARAMETERS = frozenset(
    (ENTRY_CONVICTION, STRUCTURE_MINIMUM, HOLD_THRESHOLD, ADD_THRESHOLD)
)

PARAMETER_SURFACE_REASON_CODES = (
    "SURFACE_MULTI_DIMENSIONAL",
    "SURFACE_OUT_OF_SAMPLE",
    "SURFACE_COMPARABLE_RUNS",
    "SURFACE_PARAMETER_SETS_PERSISTED",
    "SURFACE_SCORE_BAND_SCOPE_EVALUATED",
    "SURFACE_ARCHITECTURE_ISOLATED",
    "SURFACE_RISK_METRICS_UNANNUALIZED",
    "SURFACE_CELLS_WITHOUT_TRADES",
    "SURFACE_NO_TRADES",
    "SURFACE_UNAVAILABLE_CELL_OBJECTIVE",
    "SURFACE_ROBUST_PLATEAU",
    "SURFACE_ISOLATED_OPTIMUM_OVERFIT_RISK",
    "SURFACE_NO_COMPARABLE_OBJECTIVE",
    "SURFACE_COMPLETE",
)


@dataclass(frozen=True)
class SurfaceAxis:
    """One declared grid dimension and the config paths it varies."""

    parameter: str
    candidate_values: tuple[Decimal, ...]
    baseline_value: Decimal
    parameter_paths: tuple[str, ...]
    revalidation_scopes: tuple[str, ...]

    @property
    def length(self) -> int:
        return len(self.candidate_values)

    def as_record(self) -> dict[str, Any]:
        _validate_axis(self)
        return {
            "parameter": self.parameter,
            "candidate_values": [str(value) for value in self.candidate_values],
            "baseline_value": str(self.baseline_value),
            "parameter_paths": list(self.parameter_paths),
            "revalidation_scopes": list(self.revalidation_scopes),
        }


@dataclass(frozen=True)
class ParameterSurfaceSpec:
    """Frozen research question for one multi-dimensional parameter grid."""

    feature_id: str
    policy_version: str
    plateau_policy_version: str
    metric_policy_version: str
    drawdown_policy_version: str
    sharpe_policy_version: str
    calmar_policy_version: str
    parameter_status: str
    surface_id: str
    axes: tuple[SurfaceAxis, ...]
    objective_metric: str
    plateau_tolerance: Decimal
    scoring_architecture_version: str
    base_config_metadata: dict[str, str]

    @property
    def dimensions(self) -> int:
        return len(self.axes)

    @property
    def shape(self) -> tuple[int, ...]:
        return tuple(axis.length for axis in self.axes)

    @property
    def cell_count(self) -> int:
        total = 1
        for axis in self.axes:
            total *= axis.length
        return total

    @property
    def parameters(self) -> tuple[str, ...]:
        return tuple(axis.parameter for axis in self.axes)

    def as_record(self) -> dict[str, Any]:
        _validate_spec(self)
        payload = _spec_payload(self)
        if _digest(payload) != self.surface_id:
            raise ValueError("parameter surface specification does not match surface_id")
        return {**payload, "surface_id": self.surface_id}


@dataclass(frozen=True)
class SurfaceParameterSet:
    """One grid cell and the config identity its run must persist."""

    parameter_set_id: str
    surface_id: str
    ordinal: int
    coordinates: tuple[int, ...]
    parameters: tuple[str, ...]
    values: tuple[Decimal, ...]
    baseline: bool
    parameter_paths: tuple[str, ...]
    scoring_architecture_version: str
    config_metadata: dict[str, str]

    def value(self, parameter: str) -> Decimal:
        for name, value in zip(self.parameters, self.values, strict=True):
            if name == parameter:
                return value
        raise KeyError(parameter)

    def as_record(self) -> dict[str, Any]:
        return {
            "parameter_set_id": self.parameter_set_id,
            "surface_id": self.surface_id,
            "ordinal": self.ordinal,
            "coordinates": list(self.coordinates),
            "parameters": list(self.parameters),
            "values": [str(value) for value in self.values],
            "baseline": self.baseline,
            "parameter_paths": list(self.parameter_paths),
            "scoring_architecture_version": self.scoring_architecture_version,
            "config_metadata": dict(self.config_metadata),
        }


@dataclass(frozen=True)
class SurfaceCellMetrics:
    """Per-cell outcome, drawdown, and risk-adjusted evidence.

    ``outcome`` stays owned by BTC-185.  The drawdown is the worst within-fold
    peak-to-trough NAV decline, because BTC-182 restarts capital per fold and
    no compounded cross-fold equity path exists.  Sharpe pools the per-period
    NAV returns inside folds against a zero per-period risk-free rate, and
    Calmar divides the mean fold return by that drawdown.  Neither ratio is
    annualized: the walk-forward layer declares no periods-per-year factor.
    """

    outcome: ThresholdSweepMetrics
    max_drawdown_fraction: Decimal | None
    max_drawdown_status: str
    period_return_count: int
    sharpe_ratio: Decimal | None
    sharpe_status: str
    calmar_ratio: Decimal | None
    calmar_status: str

    @property
    def fold_count(self) -> int:
        return self.outcome.fold_count

    @property
    def trade_count(self) -> int:
        return self.outcome.trade_count

    @property
    def closed_trade_count(self) -> int:
        return self.outcome.closed_trade_count

    @property
    def mean_return_fraction(self) -> Decimal:
        return self.outcome.mean_return_fraction

    @property
    def closed_trade_expectancy(self) -> Decimal | None:
        return self.outcome.closed_trade_expectancy

    @property
    def mean_r_multiple(self) -> Decimal | None:
        return self.outcome.mean_r_multiple

    def objective(self, name: str) -> Decimal | None:
        if name == SHARPE_OBJECTIVE:
            return self.sharpe_ratio
        if name == CALMAR_OBJECTIVE:
            return self.calmar_ratio
        return self.outcome.objective(name)

    def as_record(self) -> dict[str, Any]:
        _validate_cell_metrics(self)
        return {
            "outcome": self.outcome.as_record(),
            "max_drawdown_fraction": _optional_decimal(self.max_drawdown_fraction),
            "max_drawdown_status": self.max_drawdown_status,
            "period_return_count": self.period_return_count,
            "sharpe_ratio": _optional_decimal(self.sharpe_ratio),
            "sharpe_status": self.sharpe_status,
            "calmar_ratio": _optional_decimal(self.calmar_ratio),
            "calmar_status": self.calmar_status,
        }


@dataclass(frozen=True)
class ParameterSurfaceCell:
    """One persisted grid-cell evaluation."""

    parameter_set: SurfaceParameterSet
    validation: WalkForwardValidation
    metrics: SurfaceCellMetrics

    @property
    def coordinates(self) -> tuple[int, ...]:
        return self.parameter_set.coordinates

    @property
    def values(self) -> tuple[Decimal, ...]:
        return self.parameter_set.values

    @property
    def parameter_set_id(self) -> str:
        return self.parameter_set.parameter_set_id

    @property
    def ordinal(self) -> int:
        return self.parameter_set.ordinal

    def as_record(self) -> dict[str, Any]:
        return {
            "parameter_set": self.parameter_set.as_record(),
            "validation": self.validation.as_record(),
            "metrics": self.metrics.as_record(),
        }


@dataclass(frozen=True)
class SurfaceAxisSpan:
    """The value range one axis takes inside a plateau's bounding box."""

    parameter: str
    lower_value: Decimal
    upper_value: Decimal

    def as_record(self) -> dict[str, Any]:
        return {
            "parameter": self.parameter,
            "lower_value": str(self.lower_value),
            "upper_value": str(self.upper_value),
        }


@dataclass(frozen=True)
class SurfacePlateau:
    """A grid-connected region within tolerance of the global best cell.

    ``axis_spans`` is the region's bounding box, not a claim that every cell
    inside that box belongs to the plateau; ``parameter_set_ids`` is the exact
    membership.
    """

    plateau_id: str
    cell_count: int
    coordinates: tuple[tuple[int, ...], ...]
    parameter_set_ids: tuple[str, ...]
    axis_spans: tuple[SurfaceAxisSpan, ...]
    best_parameter_set_id: str
    best_objective_value: Decimal
    worst_objective_value: Decimal
    contains_global_best: bool

    def as_record(self) -> dict[str, Any]:
        return {
            "plateau_id": self.plateau_id,
            "cell_count": self.cell_count,
            "coordinates": [list(item) for item in self.coordinates],
            "parameter_set_ids": list(self.parameter_set_ids),
            "axis_spans": [span.as_record() for span in self.axis_spans],
            "best_parameter_set_id": self.best_parameter_set_id,
            "best_objective_value": str(self.best_objective_value),
            "worst_objective_value": str(self.worst_objective_value),
            "contains_global_best": self.contains_global_best,
        }


@dataclass(frozen=True)
class ParameterSurfaceReport:
    """Replayable BTC-188 evidence for one multi-dimensional surface."""

    feature_id: str
    policy_version: str
    plateau_policy_version: str
    metric_policy_version: str
    drawdown_policy_version: str
    sharpe_policy_version: str
    calmar_policy_version: str
    parameter_status: str
    report_id: str
    evidence_digest: str
    spec: ParameterSurfaceSpec
    cells: tuple[ParameterSurfaceCell, ...]
    plateaus: tuple[SurfacePlateau, ...]
    best_parameter_set_id: str | None
    best_plateau_id: str | None
    isolated_optimum: bool
    config_metadata: dict[str, str]
    reason_codes: tuple[str, ...]

    @property
    def parameters(self) -> tuple[str, ...]:
        return self.spec.parameters

    @property
    def shape(self) -> tuple[int, ...]:
        return self.spec.shape

    @property
    def baseline(self) -> ParameterSurfaceCell:
        return next(cell for cell in self.cells if cell.parameter_set.baseline)

    @property
    def best(self) -> ParameterSurfaceCell | None:
        if self.best_parameter_set_id is None:
            return None
        return self.cell(self.best_parameter_set_id)

    def cell(self, parameter_set_id: str) -> ParameterSurfaceCell:
        for item in self.cells:
            if item.parameter_set_id == parameter_set_id:
                return item
        raise KeyError(parameter_set_id)

    def cell_at(self, coordinates: Sequence[int]) -> ParameterSurfaceCell:
        wanted = tuple(coordinates)
        for item in self.cells:
            if item.coordinates == wanted:
                return item
        raise KeyError(wanted)

    def as_record(self) -> dict[str, Any]:
        _validate_report(self)
        payload = _report_payload(self)
        if _digest(payload) != self.evidence_digest:
            raise ValueError("parameter surface evidence does not match digest")
        return {**payload, "evidence_digest": self.evidence_digest}


SurfaceEvaluator = Callable[[SurfaceParameterSet], WalkForwardValidation]


def surface_axis(
    *,
    parameter: str,
    candidate_values: Sequence[Any],
    baseline_value: Any,
    parameter_paths: Sequence[str],
) -> SurfaceAxis:
    """Declare one grid dimension over the BTC-185 parameter vocabulary."""

    if parameter not in THRESHOLD_PARAMETERS:
        raise ValueError(f"parameter must be one of {THRESHOLD_PARAMETERS}")
    values = tuple(sorted(_candidate_values(candidate_values, parameter)))
    baseline = threshold_parameter_value(
        baseline_value, parameter, name="baseline_value"
    )
    if baseline not in values:
        raise ValueError("baseline_value must be one of candidate_values")
    axis = SurfaceAxis(
        parameter=parameter,
        candidate_values=values,
        baseline_value=baseline,
        parameter_paths=threshold_parameter_paths(parameter_paths),
        revalidation_scopes=THRESHOLD_REVALIDATION_SCOPES[parameter],
    )
    axis.as_record()
    return axis


def parameter_surface_spec(
    *,
    axes: Sequence[SurfaceAxis],
    base_config_metadata: Mapping[str, str],
    objective_metric: str = MEAN_RETURN_OBJECTIVE,
    plateau_tolerance: Any = Decimal("0"),
    scoring_architecture_version: str = SCORING_ARCHITECTURE_V1_2,
) -> ParameterSurfaceSpec:
    """Declare one surface question without changing production config."""

    ordered = _axes(axes)
    metadata = threshold_config_metadata(base_config_metadata)
    objective = _choice(objective_metric, SURFACE_OBJECTIVES, "objective_metric")
    tolerance = _non_negative_decimal(plateau_tolerance, "plateau_tolerance")
    architecture = _string(
        scoring_architecture_version, "scoring_architecture_version"
    )
    validate_scoring_architecture(metadata["strategy_version"], architecture)
    provisional = ParameterSurfaceSpec(
        feature_id=PARAMETER_SURFACE_FEATURE_ID,
        policy_version=PARAMETER_SURFACE_POLICY_VERSION,
        plateau_policy_version=SURFACE_PLATEAU_POLICY_VERSION,
        metric_policy_version=SURFACE_METRIC_POLICY_VERSION,
        drawdown_policy_version=SURFACE_DRAWDOWN_POLICY_VERSION,
        sharpe_policy_version=SURFACE_SHARPE_POLICY_VERSION,
        calmar_policy_version=SURFACE_CALMAR_POLICY_VERSION,
        parameter_status=SURFACE_PARAMETER_STATUS,
        surface_id="",
        axes=ordered,
        objective_metric=objective,
        plateau_tolerance=tolerance,
        scoring_architecture_version=architecture,
        base_config_metadata=metadata,
    )
    spec = replace(provisional, surface_id=_digest(_spec_payload(provisional)))
    spec.as_record()
    return spec


def surface_parameter_sets(
    spec: ParameterSurfaceSpec,
) -> tuple[SurfaceParameterSet, ...]:
    """Return deterministic config identities for every ordered grid cell."""

    if not isinstance(spec, ParameterSurfaceSpec):
        raise TypeError("spec must be a ParameterSurfaceSpec")
    spec.as_record()
    parameters = spec.parameters
    paths = tuple(
        sorted(path for axis in spec.axes for path in axis.parameter_paths)
    )
    baseline_values = tuple(axis.baseline_value for axis in spec.axes)
    cells: list[SurfaceParameterSet] = []
    ordinal = 0
    for coordinates in product(*(range(axis.length) for axis in spec.axes)):
        values = tuple(
            axis.candidate_values[index]
            for axis, index in zip(spec.axes, coordinates, strict=True)
        )
        token = _digest(
            {
                "surface_id": spec.surface_id,
                "ordinal": ordinal,
                "coordinates": list(coordinates),
                "parameters": list(parameters),
                "values": [str(value) for value in values],
            }
        )[:16]
        # Provenance columns bound a parameter-set identity to 64 characters,
        # so the identity stays compact and the axes it means are recorded.
        parameter_set_id = f"btc188-{ordinal:04d}-{token}"
        cells.append(
            SurfaceParameterSet(
                parameter_set_id=parameter_set_id,
                surface_id=spec.surface_id,
                ordinal=ordinal,
                coordinates=tuple(coordinates),
                parameters=parameters,
                values=values,
                baseline=values == baseline_values,
                parameter_paths=paths,
                scoring_architecture_version=spec.scoring_architecture_version,
                config_metadata={
                    **spec.base_config_metadata,
                    "parameter_set_id": parameter_set_id,
                },
            )
        )
        ordinal += 1
    return tuple(cells)


def run_parameter_surface(
    spec: ParameterSurfaceSpec,
    *,
    evaluator: SurfaceEvaluator,
) -> ParameterSurfaceReport:
    """Evaluate every grid cell as a separate comparable walk-forward run."""

    if not isinstance(spec, ParameterSurfaceSpec):
        raise TypeError("spec must be a ParameterSurfaceSpec")
    spec.as_record()
    if not callable(evaluator):
        raise TypeError("evaluator must be callable")
    validations: list[WalkForwardValidation] = []
    for parameter_set in surface_parameter_sets(spec):
        validation = evaluator(parameter_set)
        if not isinstance(validation, WalkForwardValidation):
            raise TypeError("evaluator must return a WalkForwardValidation")
        validation.as_record()
        if validation.config_metadata != parameter_set.config_metadata:
            raise ValueError(
                "cell validation config_metadata must match its parameter set"
            )
        validations.append(validation)
    return _build_report(spec, tuple(validations))


def restore_parameter_surface_report(
    record: Mapping[str, Any],
) -> ParameterSurfaceReport:
    """Restore persisted surface evidence and reject derived or nested drift."""

    source = _mapping(record, "record")
    spec = _restore_spec(_mapping(source.get("spec"), "spec"))
    raw_cells = _record_sequence(source.get("cells"), "cells")
    validations = tuple(
        restore_walk_forward_validation(
            _mapping(_mapping(item, "cell").get("validation"), "validation")
        )
        for item in raw_cells
    )
    report = _build_report(spec, validations)
    if report.as_record() != dict(source):
        raise ValueError("record does not match reconstructed parameter surface")
    return report


def _build_report(
    spec: ParameterSurfaceSpec,
    validations: tuple[WalkForwardValidation, ...],
) -> ParameterSurfaceReport:
    parameter_sets = surface_parameter_sets(spec)
    if len(validations) != len(parameter_sets):
        raise ValueError("one validation is required for every surface cell")
    cells: list[ParameterSurfaceCell] = []
    for parameter_set, validation in zip(parameter_sets, validations, strict=True):
        validation.as_record()
        if validation.config_metadata != parameter_set.config_metadata:
            raise ValueError(
                "cell validation config_metadata must match its parameter set"
            )
        cells.append(
            ParameterSurfaceCell(
                parameter_set=parameter_set,
                validation=validation,
                metrics=_cell_metrics(validation),
            )
        )
    resolved = tuple(cells)
    _validate_comparability(resolved)
    best_id, plateaus, best_plateau_id, isolated = _plateau_analysis(spec, resolved)
    report = ParameterSurfaceReport(
        feature_id=PARAMETER_SURFACE_FEATURE_ID,
        policy_version=PARAMETER_SURFACE_POLICY_VERSION,
        plateau_policy_version=SURFACE_PLATEAU_POLICY_VERSION,
        metric_policy_version=SURFACE_METRIC_POLICY_VERSION,
        drawdown_policy_version=SURFACE_DRAWDOWN_POLICY_VERSION,
        sharpe_policy_version=SURFACE_SHARPE_POLICY_VERSION,
        calmar_policy_version=SURFACE_CALMAR_POLICY_VERSION,
        parameter_status=SURFACE_PARAMETER_STATUS,
        report_id="",
        evidence_digest="",
        spec=spec,
        cells=resolved,
        plateaus=plateaus,
        best_parameter_set_id=best_id,
        best_plateau_id=best_plateau_id,
        isolated_optimum=isolated,
        config_metadata=dict(spec.base_config_metadata),
        reason_codes=_reason_codes(spec, resolved, best_id, plateaus, isolated),
    )
    report = replace(report, report_id=_report_id(report))
    _validate_report(report)
    return replace(report, evidence_digest=_digest(_report_payload(report)))


def _cell_metrics(validation: WalkForwardValidation) -> SurfaceCellMetrics:
    outcome = threshold_sweep_metrics(validation)
    with localcontext(Context(prec=SURFACE_DECIMAL_PRECISION)):
        drawdown, drawdown_status = _max_drawdown(validation)
        returns, return_status = _period_returns(validation)
        sharpe, sharpe_status = _sharpe(returns, return_status)
        calmar, calmar_status = _calmar(
            outcome.mean_return_fraction, drawdown, drawdown_status
        )
    return SurfaceCellMetrics(
        outcome=outcome,
        max_drawdown_fraction=drawdown,
        max_drawdown_status=drawdown_status,
        period_return_count=len(returns),
        sharpe_ratio=sharpe,
        sharpe_status=sharpe_status,
        calmar_ratio=calmar,
        calmar_status=calmar_status,
    )


def _max_drawdown(
    validation: WalkForwardValidation,
) -> tuple[Decimal | None, str]:
    """Worst within-fold peak-to-trough NAV decline across the validation.

    BTC-182 restarts each fold from the same capital, so there is no
    compounded cross-fold equity path to draw down; stitching folds would
    invent one.  A fold that never declined contributes exactly zero, which
    is a measurement rather than a missing value.
    """

    observed = False
    worst = Decimal("0")
    for fold in validation.folds:
        peak = fold.starting_nav
        if peak <= 0:
            return None, DRAWDOWN_NON_POSITIVE_NAV
        for point in fold.result.equity_curve:
            observed = True
            if point.nav > peak:
                peak = point.nav
            if peak <= 0:
                return None, DRAWDOWN_NON_POSITIVE_NAV
            decline = (peak - point.nav) / peak
            if decline > worst:
                worst = decline
    if not observed:
        return None, DRAWDOWN_NO_EQUITY_CURVE
    return _quantize(worst), DRAWDOWN_AVAILABLE


def _period_returns(
    validation: WalkForwardValidation,
) -> tuple[tuple[Decimal, ...], str]:
    """Per-period NAV returns pooled inside folds, never across a fold break."""

    pooled: list[Decimal] = []
    for fold in validation.folds:
        previous = fold.starting_nav
        for point in fold.result.equity_curve:
            if previous <= 0:
                return (), SHARPE_NON_POSITIVE_NAV
            pooled.append((point.nav - previous) / previous)
            previous = point.nav
    return tuple(pooled), SHARPE_AVAILABLE


def _sharpe(
    returns: tuple[Decimal, ...],
    status: str,
) -> tuple[Decimal | None, str]:
    """Unannualized mean over sample standard deviation, zero risk-free rate."""

    if status != SHARPE_AVAILABLE:
        return None, status
    if len(returns) < 2:
        return None, SHARPE_INSUFFICIENT_PERIODS
    count = Decimal(len(returns))
    mean = sum(returns, Decimal("0")) / count
    variance = sum(
        ((value - mean) ** 2 for value in returns), Decimal("0")
    ) / (count - Decimal("1"))
    if variance <= 0:
        return None, SHARPE_ZERO_DISPERSION
    deviation = variance.sqrt()
    if deviation == 0:
        return None, SHARPE_ZERO_DISPERSION
    return _quantize(mean / deviation), SHARPE_AVAILABLE


def _calmar(
    mean_return_fraction: Decimal,
    drawdown: Decimal | None,
    drawdown_status: str,
) -> tuple[Decimal | None, str]:
    """Mean fold return over the reported drawdown, unannualized."""

    if drawdown is None or drawdown_status != DRAWDOWN_AVAILABLE:
        return None, CALMAR_UNAVAILABLE_DRAWDOWN
    if drawdown == 0:
        return None, CALMAR_NO_DRAWDOWN
    return _quantize(mean_return_fraction / drawdown), CALMAR_AVAILABLE


def _plateau_analysis(
    spec: ParameterSurfaceSpec,
    cells: tuple[ParameterSurfaceCell, ...],
) -> tuple[str | None, tuple[SurfacePlateau, ...], str | None, bool]:
    objective = spec.objective_metric
    comparable = tuple(
        (cell, cell.metrics.objective(objective))
        for cell in cells
        if cell.metrics.objective(objective) is not None
    )
    if not comparable:
        return None, (), None, False
    best_cell, best_value = max(
        comparable,
        key=lambda item: (item[1], -item[0].ordinal),
    )
    assert best_value is not None
    eligible = {
        cell.coordinates: cell
        for cell, value in comparable
        if value is not None and best_value - value <= spec.plateau_tolerance
    }
    plateaus: list[SurfacePlateau] = []
    seen: set[tuple[int, ...]] = set()
    for cell in cells:
        if cell.coordinates not in eligible or cell.coordinates in seen:
            continue
        component = _connected_component(cell.coordinates, eligible, seen)
        if len(component) < 2:
            continue
        members = tuple(
            sorted(
                (eligible[coordinates] for coordinates in component),
                key=lambda item: item.ordinal,
            )
        )
        plateaus.append(_plateau(spec, members, best_cell.parameter_set_id))
    best_id = best_cell.parameter_set_id
    best_plateau_id = next(
        (item.plateau_id for item in plateaus if best_id in item.parameter_set_ids),
        None,
    )
    return best_id, tuple(plateaus), best_plateau_id, best_plateau_id is None


def _connected_component(
    start: tuple[int, ...],
    eligible: Mapping[tuple[int, ...], ParameterSurfaceCell],
    seen: set[tuple[int, ...]],
) -> tuple[tuple[int, ...], ...]:
    """Grid-connected cells reachable by single steps along one axis."""

    component: list[tuple[int, ...]] = []
    queue = [start]
    seen.add(start)
    while queue:
        current = queue.pop(0)
        component.append(current)
        for neighbour in _neighbours(current):
            if neighbour in eligible and neighbour not in seen:
                seen.add(neighbour)
                queue.append(neighbour)
    return tuple(component)


def _neighbours(coordinates: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
    found: list[tuple[int, ...]] = []
    for axis_index in range(len(coordinates)):
        for step in (-1, 1):
            moved = coordinates[axis_index] + step
            if moved < 0:
                continue
            found.append(
                coordinates[:axis_index] + (moved,) + coordinates[axis_index + 1 :]
            )
    return tuple(found)


def _plateau(
    spec: ParameterSurfaceSpec,
    members: tuple[ParameterSurfaceCell, ...],
    best_parameter_set_id: str,
) -> SurfacePlateau:
    objective = spec.objective_metric
    values = tuple(cell.metrics.objective(objective) for cell in members)
    if any(value is None for value in values):
        raise ValueError("plateau objective values must be available")
    available = tuple(value for value in values if value is not None)
    best_member = max(
        members,
        key=lambda cell: (cell.metrics.objective(objective), -cell.ordinal),
    )
    spans = tuple(
        SurfaceAxisSpan(
            parameter=axis.parameter,
            lower_value=min(cell.values[axis_index] for cell in members),
            upper_value=max(cell.values[axis_index] for cell in members),
        )
        for axis_index, axis in enumerate(spec.axes)
    )
    parameter_set_ids = tuple(cell.parameter_set_id for cell in members)
    return SurfacePlateau(
        plateau_id=_digest(
            {
                "policy": SURFACE_PLATEAU_POLICY_VERSION,
                "surface_id": spec.surface_id,
                "objective_metric": objective,
                "parameter_set_ids": list(parameter_set_ids),
            }
        ),
        cell_count=len(members),
        coordinates=tuple(cell.coordinates for cell in members),
        parameter_set_ids=parameter_set_ids,
        axis_spans=spans,
        best_parameter_set_id=best_member.parameter_set_id,
        best_objective_value=max(available),
        worst_objective_value=min(available),
        contains_global_best=best_parameter_set_id in parameter_set_ids,
    )


def _validate_comparability(cells: tuple[ParameterSurfaceCell, ...]) -> None:
    if not cells:
        raise ValueError("parameter surface must contain candidate cells")
    first = comparable_run_signature(cells[0].validation)
    for cell in cells[1:]:
        if comparable_run_signature(cell.validation) != first:
            raise ValueError(
                "cell validations must share schedule, split, capital, costs, "
                "fitting procedure, and scoring-independent run assumptions"
            )


def _reason_codes(
    spec: ParameterSurfaceSpec,
    cells: tuple[ParameterSurfaceCell, ...],
    best_id: str | None,
    plateaus: tuple[SurfacePlateau, ...],
    isolated: bool,
) -> tuple[str, ...]:
    codes = [
        "SURFACE_MULTI_DIMENSIONAL",
        "SURFACE_OUT_OF_SAMPLE",
        "SURFACE_COMPARABLE_RUNS",
        "SURFACE_PARAMETER_SETS_PERSISTED",
    ]
    if any(axis.parameter in _SCORE_BAND_PARAMETERS for axis in spec.axes):
        codes.append("SURFACE_SCORE_BAND_SCOPE_EVALUATED")
    codes.append("SURFACE_ARCHITECTURE_ISOLATED")
    codes.append("SURFACE_RISK_METRICS_UNANNUALIZED")
    traded = tuple(cell for cell in cells if cell.metrics.trade_count > 0)
    if not traded:
        # A cell that never traded still returns exactly zero, so a flat
        # surface would otherwise read as a robust plateau on no evidence.
        codes.append("SURFACE_NO_TRADES")
    elif len(traded) != len(cells):
        codes.append("SURFACE_CELLS_WITHOUT_TRADES")
    unavailable = sum(
        1
        for cell in cells
        if cell.metrics.objective(spec.objective_metric) is None
    )
    if 0 < unavailable < len(cells):
        # Unavailable cells are holes in the grid; they break connectivity
        # instead of being read as neighbours of the best cell.
        codes.append("SURFACE_UNAVAILABLE_CELL_OBJECTIVE")
    if best_id is None:
        codes.append("SURFACE_NO_COMPARABLE_OBJECTIVE")
    if plateaus:
        codes.append("SURFACE_ROBUST_PLATEAU")
    if isolated:
        codes.append("SURFACE_ISOLATED_OPTIMUM_OVERFIT_RISK")
    codes.append("SURFACE_COMPLETE")
    return tuple(codes)


def _validate_axis(axis: SurfaceAxis) -> None:
    if axis.parameter not in THRESHOLD_PARAMETERS:
        raise ValueError(f"parameter must be one of {THRESHOLD_PARAMETERS}")
    if tuple(sorted(axis.candidate_values)) != axis.candidate_values:
        raise ValueError("candidate_values must be in ascending order")
    if len(axis.candidate_values) < 2 or len(set(axis.candidate_values)) != len(
        axis.candidate_values
    ):
        raise ValueError("candidate_values must contain at least two unique values")
    for value in axis.candidate_values:
        threshold_parameter_value(value, axis.parameter, name="candidate_value")
    if axis.baseline_value not in axis.candidate_values:
        raise ValueError("baseline_value must be one of candidate_values")
    if axis.parameter_paths != threshold_parameter_paths(axis.parameter_paths):
        raise ValueError("parameter_paths must be canonical")
    if axis.revalidation_scopes != THRESHOLD_REVALIDATION_SCOPES[axis.parameter]:
        raise ValueError("revalidation_scopes do not match the axis parameter")


def _validate_spec(spec: ParameterSurfaceSpec) -> None:
    if spec.feature_id != PARAMETER_SURFACE_FEATURE_ID:
        raise ValueError(f"feature_id must be {PARAMETER_SURFACE_FEATURE_ID}")
    if spec.policy_version != PARAMETER_SURFACE_POLICY_VERSION:
        raise ValueError(f"policy_version must be {PARAMETER_SURFACE_POLICY_VERSION}")
    if spec.plateau_policy_version != SURFACE_PLATEAU_POLICY_VERSION:
        raise ValueError("unexpected plateau_policy_version")
    if spec.metric_policy_version != SURFACE_METRIC_POLICY_VERSION:
        raise ValueError("unexpected metric_policy_version")
    if spec.drawdown_policy_version != SURFACE_DRAWDOWN_POLICY_VERSION:
        raise ValueError("unexpected drawdown_policy_version")
    if spec.sharpe_policy_version != SURFACE_SHARPE_POLICY_VERSION:
        raise ValueError("unexpected sharpe_policy_version")
    if spec.calmar_policy_version != SURFACE_CALMAR_POLICY_VERSION:
        raise ValueError("unexpected calmar_policy_version")
    if spec.parameter_status != SURFACE_PARAMETER_STATUS:
        raise ValueError(f"parameter_status must be {SURFACE_PARAMETER_STATUS}")
    _validate_axes(spec.axes)
    _choice(spec.objective_metric, SURFACE_OBJECTIVES, "objective_metric")
    _non_negative_decimal(spec.plateau_tolerance, "plateau_tolerance")
    metadata = threshold_config_metadata(spec.base_config_metadata)
    validate_scoring_architecture(
        metadata["strategy_version"], spec.scoring_architecture_version
    )


def _validate_cell_metrics(metrics: SurfaceCellMetrics) -> None:
    if not isinstance(metrics.outcome, ThresholdSweepMetrics):
        raise TypeError("outcome must be a ThresholdSweepMetrics")
    _choice(metrics.max_drawdown_status, DRAWDOWN_STATUSES, "max_drawdown_status")
    _choice(metrics.sharpe_status, SHARPE_STATUSES, "sharpe_status")
    _choice(metrics.calmar_status, CALMAR_STATUSES, "calmar_status")
    if (metrics.max_drawdown_fraction is None) != (
        metrics.max_drawdown_status != DRAWDOWN_AVAILABLE
    ):
        raise ValueError("max_drawdown_fraction must agree with its status")
    if (
        metrics.max_drawdown_fraction is not None
        and metrics.max_drawdown_fraction < 0
    ):
        raise ValueError("max_drawdown_fraction must be non-negative")
    if (metrics.sharpe_ratio is None) != (metrics.sharpe_status != SHARPE_AVAILABLE):
        raise ValueError("sharpe_ratio must agree with its status")
    if (metrics.calmar_ratio is None) != (metrics.calmar_status != CALMAR_AVAILABLE):
        raise ValueError("calmar_ratio must agree with its status")
    if metrics.period_return_count < 0:
        raise ValueError("period_return_count must be non-negative")


def _validate_report(report: ParameterSurfaceReport) -> None:
    if report.feature_id != PARAMETER_SURFACE_FEATURE_ID:
        raise ValueError(f"feature_id must be {PARAMETER_SURFACE_FEATURE_ID}")
    if report.policy_version != PARAMETER_SURFACE_POLICY_VERSION:
        raise ValueError(f"policy_version must be {PARAMETER_SURFACE_POLICY_VERSION}")
    if report.plateau_policy_version != SURFACE_PLATEAU_POLICY_VERSION:
        raise ValueError("unexpected plateau_policy_version")
    if report.metric_policy_version != SURFACE_METRIC_POLICY_VERSION:
        raise ValueError("unexpected metric_policy_version")
    if report.drawdown_policy_version != SURFACE_DRAWDOWN_POLICY_VERSION:
        raise ValueError("unexpected drawdown_policy_version")
    if report.sharpe_policy_version != SURFACE_SHARPE_POLICY_VERSION:
        raise ValueError("unexpected sharpe_policy_version")
    if report.calmar_policy_version != SURFACE_CALMAR_POLICY_VERSION:
        raise ValueError("unexpected calmar_policy_version")
    if report.parameter_status != SURFACE_PARAMETER_STATUS:
        raise ValueError("unexpected parameter_status")
    report.spec.as_record()
    if report.config_metadata != report.spec.base_config_metadata:
        raise ValueError("report config_metadata must match the surface base")
    expected_sets = surface_parameter_sets(report.spec)
    if tuple(cell.parameter_set for cell in report.cells) != expected_sets:
        raise ValueError("report cells do not match the declared grid")
    for cell in report.cells:
        cell.validation.as_record()
        if cell.validation.config_metadata != cell.parameter_set.config_metadata:
            raise ValueError("cell validation does not match its parameter set")
        if cell.metrics != _cell_metrics(cell.validation):
            raise ValueError("cell metrics do not match validation evidence")
    _validate_comparability(report.cells)
    best, plateaus, best_plateau, isolated = _plateau_analysis(
        report.spec, report.cells
    )
    if (
        report.best_parameter_set_id != best
        or report.plateaus != plateaus
        or report.best_plateau_id != best_plateau
        or report.isolated_optimum != isolated
    ):
        raise ValueError("plateau analysis does not match cell evidence")
    if report.reason_codes != _reason_codes(
        report.spec, report.cells, best, plateaus, isolated
    ):
        raise ValueError("reason codes do not describe the parameter surface")
    if report.report_id != _report_id(report):
        raise ValueError("parameter surface inputs do not match report_id")


def _report_id(report: ParameterSurfaceReport) -> str:
    return _digest(
        {
            "policy": PARAMETER_SURFACE_POLICY_VERSION,
            "plateau_policy": SURFACE_PLATEAU_POLICY_VERSION,
            "metric_policy": SURFACE_METRIC_POLICY_VERSION,
            "drawdown_policy": SURFACE_DRAWDOWN_POLICY_VERSION,
            "sharpe_policy": SURFACE_SHARPE_POLICY_VERSION,
            "calmar_policy": SURFACE_CALMAR_POLICY_VERSION,
            "surface_id": report.spec.surface_id,
            "validation_ids": [
                cell.validation.validation_id for cell in report.cells
            ],
        }
    )


def _report_payload(report: ParameterSurfaceReport) -> dict[str, Any]:
    return {
        "feature_id": report.feature_id,
        "policy_version": report.policy_version,
        "plateau_policy_version": report.plateau_policy_version,
        "metric_policy_version": report.metric_policy_version,
        "drawdown_policy_version": report.drawdown_policy_version,
        "sharpe_policy_version": report.sharpe_policy_version,
        "calmar_policy_version": report.calmar_policy_version,
        "parameter_status": report.parameter_status,
        "report_id": report.report_id,
        "spec": report.spec.as_record(),
        "cells": [cell.as_record() for cell in report.cells],
        "plateaus": [plateau.as_record() for plateau in report.plateaus],
        "best_parameter_set_id": report.best_parameter_set_id,
        "best_plateau_id": report.best_plateau_id,
        "isolated_optimum": report.isolated_optimum,
        "config_metadata": dict(report.config_metadata),
        "reason_codes": list(report.reason_codes),
    }


def _spec_payload(spec: ParameterSurfaceSpec) -> dict[str, Any]:
    return {
        "feature_id": spec.feature_id,
        "policy_version": spec.policy_version,
        "plateau_policy_version": spec.plateau_policy_version,
        "metric_policy_version": spec.metric_policy_version,
        "drawdown_policy_version": spec.drawdown_policy_version,
        "sharpe_policy_version": spec.sharpe_policy_version,
        "calmar_policy_version": spec.calmar_policy_version,
        "parameter_status": spec.parameter_status,
        "axes": [axis.as_record() for axis in spec.axes],
        "objective_metric": spec.objective_metric,
        "plateau_tolerance": str(spec.plateau_tolerance),
        "scoring_architecture_version": spec.scoring_architecture_version,
        "base_config_metadata": dict(spec.base_config_metadata),
    }


def _restore_spec(source: Mapping[str, Any]) -> ParameterSurfaceSpec:
    axes = tuple(
        _restore_axis(_mapping(item, "spec.axis"))
        for item in _record_sequence(source.get("axes"), "spec.axes")
    )
    spec = parameter_surface_spec(
        axes=axes,
        base_config_metadata=_mapping(
            source.get("base_config_metadata"), "spec.base_config_metadata"
        ),
        objective_metric=_string(
            source.get("objective_metric"), "spec.objective_metric"
        ),
        plateau_tolerance=source.get("plateau_tolerance"),
        scoring_architecture_version=_string(
            source.get("scoring_architecture_version"),
            "spec.scoring_architecture_version",
        ),
    )
    if spec.as_record() != dict(source):
        raise ValueError("record does not match reconstructed parameter surface spec")
    return spec


def _restore_axis(source: Mapping[str, Any]) -> SurfaceAxis:
    axis = surface_axis(
        parameter=_string(source.get("parameter"), "axis.parameter"),
        candidate_values=_record_sequence(
            source.get("candidate_values"), "axis.candidate_values"
        ),
        baseline_value=source.get("baseline_value"),
        parameter_paths=_string_tuple(
            source.get("parameter_paths"), "axis.parameter_paths"
        ),
    )
    if axis.as_record() != dict(source):
        raise ValueError("record does not match reconstructed surface axis")
    return axis


def _axes(values: Sequence[SurfaceAxis]) -> tuple[SurfaceAxis, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise TypeError("axes must be a sequence")
    for axis in values:
        if not isinstance(axis, SurfaceAxis):
            raise TypeError("axes must contain SurfaceAxis values")
    # Canonical axis order keeps one research question to one surface_id
    # however the caller happened to declare its dimensions.
    ordered = tuple(sorted(values, key=lambda axis: axis.parameter))
    _validate_axes(ordered)
    return ordered


def _validate_axes(axes: tuple[SurfaceAxis, ...]) -> None:
    if len(axes) < MINIMUM_SURFACE_DIMENSIONS:
        raise ValueError(
            f"a surface requires at least {MINIMUM_SURFACE_DIMENSIONS} axes"
        )
    parameters = tuple(axis.parameter for axis in axes)
    if len(set(parameters)) != len(parameters):
        raise ValueError("axes must declare distinct parameters")
    if tuple(sorted(parameters)) != parameters:
        raise ValueError("axes must be ordered by parameter")
    paths: set[str] = set()
    for axis in axes:
        _validate_axis(axis)
        if paths & set(axis.parameter_paths):
            # Two axes writing one configuration path would confound the
            # measured effect of each dimension.
            raise ValueError("axes must not share configuration paths")
        paths.update(axis.parameter_paths)


def _candidate_values(values: Sequence[Any], parameter: str) -> tuple[Decimal, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise TypeError("candidate_values must be a sequence")
    converted = tuple(
        threshold_parameter_value(value, parameter, name="candidate_value")
        for value in values
    )
    if len(converted) < 2 or len(set(converted)) != len(converted):
        raise ValueError("candidate_values must contain at least two unique values")
    return converted


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(SURFACE_METRIC_EXPONENT, rounding=ROUND_HALF_EVEN)


def _decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a finite decimal")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise TypeError(f"{name} must be a finite decimal") from exc
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    return result


def _non_negative_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


def _choice(value: Any, choices: tuple[str, ...], name: str) -> str:
    result = _string(value, name)
    if result not in choices:
        raise ValueError(f"{name} must be one of {choices}")
    return result


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"{name} must be a non-empty string")
    return value


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    return value


def _record_sequence(value: Any, name: str) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{name} must be a sequence")
    return tuple(value)


def _string_tuple(value: Any, name: str) -> tuple[str, ...]:
    return tuple(_string(item, name) for item in _record_sequence(value, name))


def _optional_decimal(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
