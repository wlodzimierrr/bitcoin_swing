"""Deterministic one-dimensional threshold robustness research (BTC-185).

The sweep layer does not rescore features, alter strategy configuration, or
choose a production parameter.  A caller receives a versioned parameter-set
identity for each candidate, builds the corresponding strategy through the
existing owners, and returns a complete BTC-182 out-of-sample validation.

Every candidate in one report therefore shares the same historical schedule,
walk-forward split, capital, costs, strategy version, and scoring architecture.
Only the declared scalar parameter may vary.  Adjacent candidates whose
objective is within an explicit absolute tolerance of the best result are
reported as robust plateaus; a lone best candidate is called out as an
isolated optimum rather than promoted.  A candidate that never traded returns
exactly zero rather than nothing, so the report also declares when some or all
candidates produced no trades and a flat region is absence of evidence.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import Any

from btc_predictor.backtest.walk_forward import (
    WalkForwardValidation,
    restore_walk_forward_validation,
)


THRESHOLD_SWEEP_FEATURE_ID = "THRESHOLD_SWEEP"
THRESHOLD_SWEEP_POLICY_VERSION = "ONE_DIMENSIONAL_THRESHOLD_SWEEP_V1"
THRESHOLD_PLATEAU_POLICY_VERSION = "ADJACENT_GLOBAL_BEST_TOLERANCE_V1"
THRESHOLD_METRIC_POLICY_VERSION = "OUT_OF_SAMPLE_NET_OUTCOME_METRICS_V1"
THRESHOLD_PARAMETER_STATUS = "PROVISIONAL_RESEARCH_CALIBRATABLE"
SCORING_ARCHITECTURE_V1_2 = "DIRECT_NON_NESTED_SCORING_V1_2"
SCORING_ARCHITECTURE_V1_1_BENCHMARK = "NESTED_SCORING_V1_1"
THRESHOLD_METRIC_EXPONENT = Decimal("1E-12")

ENTRY_CONVICTION = "entry_conviction"
TREND_MINIMUM = "trend_minimum"
FLOW_MINIMUM = "flow_minimum"
POSITIONING_MINIMUM = "positioning_minimum"
STRUCTURE_MINIMUM = "structure_minimum"
REWARD_RISK_MINIMUM = "reward_risk_minimum"
STOP_BUFFER = "stop_buffer_atr_multiplier"
HOLD_THRESHOLD = "hold_threshold"
ADD_THRESHOLD = "add_threshold"
RISK_BUDGET = "risk_budget_fraction_nav"

THRESHOLD_PARAMETERS = (
    ENTRY_CONVICTION,
    TREND_MINIMUM,
    FLOW_MINIMUM,
    POSITIONING_MINIMUM,
    STRUCTURE_MINIMUM,
    REWARD_RISK_MINIMUM,
    STOP_BUFFER,
    HOLD_THRESHOLD,
    ADD_THRESHOLD,
    RISK_BUDGET,
)

MEAN_RETURN_OBJECTIVE = "mean_return_fraction"
EXPECTANCY_OBJECTIVE = "closed_trade_expectancy"
MEAN_R_OBJECTIVE = "mean_r_multiple"
THRESHOLD_OBJECTIVES = (
    MEAN_RETURN_OBJECTIVE,
    EXPECTANCY_OBJECTIVE,
    MEAN_R_OBJECTIVE,
)

_SCORE_PARAMETERS = frozenset(
    (
        ENTRY_CONVICTION,
        TREND_MINIMUM,
        FLOW_MINIMUM,
        POSITIONING_MINIMUM,
        STRUCTURE_MINIMUM,
        HOLD_THRESHOLD,
        ADD_THRESHOLD,
    )
)

THRESHOLD_REVALIDATION_SCOPES = {
    ENTRY_CONVICTION: ("ENTRY_CONVICTION_ACTION_BANDS",),
    TREND_MINIMUM: ("TREND_MINIMUM",),
    FLOW_MINIMUM: ("FLOW_MINIMUM",),
    POSITIONING_MINIMUM: ("POSITIONING_MINIMUM",),
    STRUCTURE_MINIMUM: (
        "STRUCTURE_MINIMUM",
        "STRUCTURE_HARD_REJECT_BANDS",
    ),
    REWARD_RISK_MINIMUM: ("REWARD_RISK_HARD_FILTER",),
    STOP_BUFFER: ("STRUCTURAL_STOP_VOLATILITY_BUFFER",),
    HOLD_THRESHOLD: ("HOLD_SCORE_ACTION_BANDS",),
    ADD_THRESHOLD: ("ADD_SCORE_THRESHOLD",),
    RISK_BUDGET: ("RISK_PER_TRADE_SCHEDULE",),
}

THRESHOLD_SWEEP_REASON_CODES = (
    "THRESHOLD_SWEEP_ONE_DIMENSIONAL",
    "THRESHOLD_SWEEP_OUT_OF_SAMPLE",
    "THRESHOLD_SWEEP_COMPARABLE_RUNS",
    "THRESHOLD_SWEEP_PARAMETER_SETS_PERSISTED",
    "THRESHOLD_SWEEP_SCORE_BAND_SCOPE_EVALUATED",
    "THRESHOLD_SWEEP_ARCHITECTURE_ISOLATED",
    "THRESHOLD_SWEEP_CANDIDATES_WITHOUT_TRADES",
    "THRESHOLD_SWEEP_NO_TRADES",
    "THRESHOLD_SWEEP_ROBUST_PLATEAU",
    "THRESHOLD_SWEEP_ISOLATED_OPTIMUM",
    "THRESHOLD_SWEEP_NO_COMPARABLE_OBJECTIVE",
    "THRESHOLD_SWEEP_COMPLETE",
)


@dataclass(frozen=True)
class ThresholdSweepSpec:
    """Frozen research question for one scalar strategy parameter."""

    feature_id: str
    policy_version: str
    plateau_policy_version: str
    metric_policy_version: str
    parameter_status: str
    sweep_id: str
    parameter: str
    candidate_values: tuple[Decimal, ...]
    baseline_value: Decimal
    parameter_paths: tuple[str, ...]
    revalidation_scopes: tuple[str, ...]
    objective_metric: str
    plateau_tolerance: Decimal
    scoring_architecture_version: str
    base_config_metadata: dict[str, str]

    def as_record(self) -> dict[str, Any]:
        _validate_spec(self)
        payload = _spec_payload(self)
        if _digest(payload) != self.sweep_id:
            raise ValueError("threshold sweep specification does not match sweep_id")
        return {**payload, "sweep_id": self.sweep_id}


@dataclass(frozen=True)
class ThresholdParameterSet:
    """One candidate value and the config identity its run must persist."""

    parameter_set_id: str
    sweep_id: str
    ordinal: int
    parameter: str
    value: Decimal
    baseline: bool
    parameter_paths: tuple[str, ...]
    scoring_architecture_version: str
    config_metadata: dict[str, str]

    def as_record(self) -> dict[str, Any]:
        return {
            "parameter_set_id": self.parameter_set_id,
            "sweep_id": self.sweep_id,
            "ordinal": self.ordinal,
            "parameter": self.parameter,
            "value": str(self.value),
            "baseline": self.baseline,
            "parameter_paths": list(self.parameter_paths),
            "scoring_architecture_version": self.scoring_architecture_version,
            "config_metadata": dict(self.config_metadata),
        }


@dataclass(frozen=True)
class ThresholdSweepMetrics:
    """Comparable net outcomes derived from one BTC-182 validation."""

    fold_count: int
    trade_count: int
    closed_trade_count: int
    summed_total_pnl: Decimal
    summed_net_pnl: Decimal
    mean_return_fraction: Decimal
    worst_fold_return_fraction: Decimal
    best_fold_return_fraction: Decimal
    closed_trade_expectancy: Decimal | None
    r_multiple_count: int
    mean_r_multiple: Decimal | None

    def objective(self, name: str) -> Decimal | None:
        if name == MEAN_RETURN_OBJECTIVE:
            return self.mean_return_fraction
        if name == EXPECTANCY_OBJECTIVE:
            return self.closed_trade_expectancy
        if name == MEAN_R_OBJECTIVE:
            return self.mean_r_multiple
        raise KeyError(name)

    def as_record(self) -> dict[str, Any]:
        return {
            "fold_count": self.fold_count,
            "trade_count": self.trade_count,
            "closed_trade_count": self.closed_trade_count,
            "summed_total_pnl": str(self.summed_total_pnl),
            "summed_net_pnl": str(self.summed_net_pnl),
            "mean_return_fraction": str(self.mean_return_fraction),
            "worst_fold_return_fraction": str(self.worst_fold_return_fraction),
            "best_fold_return_fraction": str(self.best_fold_return_fraction),
            "closed_trade_expectancy": _optional_decimal(
                self.closed_trade_expectancy
            ),
            "r_multiple_count": self.r_multiple_count,
            "mean_r_multiple": _optional_decimal(self.mean_r_multiple),
        }


@dataclass(frozen=True)
class ThresholdSweepPoint:
    """One persisted candidate evaluation."""

    parameter_set: ThresholdParameterSet
    validation: WalkForwardValidation
    metrics: ThresholdSweepMetrics

    @property
    def value(self) -> Decimal:
        return self.parameter_set.value

    @property
    def parameter_set_id(self) -> str:
        return self.parameter_set.parameter_set_id

    def as_record(self) -> dict[str, Any]:
        return {
            "parameter_set": self.parameter_set.as_record(),
            "validation": self.validation.as_record(),
            "metrics": self.metrics.as_record(),
        }


@dataclass(frozen=True)
class ThresholdPlateau:
    """A contiguous region close to the global best objective value."""

    plateau_id: str
    first_ordinal: int
    last_ordinal: int
    lower_value: Decimal
    upper_value: Decimal
    point_count: int
    parameter_set_ids: tuple[str, ...]
    best_parameter_set_id: str
    best_objective_value: Decimal
    worst_objective_value: Decimal

    def as_record(self) -> dict[str, Any]:
        return {
            "plateau_id": self.plateau_id,
            "first_ordinal": self.first_ordinal,
            "last_ordinal": self.last_ordinal,
            "lower_value": str(self.lower_value),
            "upper_value": str(self.upper_value),
            "point_count": self.point_count,
            "parameter_set_ids": list(self.parameter_set_ids),
            "best_parameter_set_id": self.best_parameter_set_id,
            "best_objective_value": str(self.best_objective_value),
            "worst_objective_value": str(self.worst_objective_value),
        }


@dataclass(frozen=True)
class ThresholdSweepReport:
    """Replayable BTC-185 evidence for one one-dimensional sweep."""

    feature_id: str
    policy_version: str
    plateau_policy_version: str
    metric_policy_version: str
    parameter_status: str
    report_id: str
    evidence_digest: str
    spec: ThresholdSweepSpec
    points: tuple[ThresholdSweepPoint, ...]
    plateaus: tuple[ThresholdPlateau, ...]
    best_parameter_set_id: str | None
    isolated_optimum: bool
    config_metadata: dict[str, str]
    reason_codes: tuple[str, ...]

    @property
    def parameter(self) -> str:
        return self.spec.parameter

    @property
    def baseline(self) -> ThresholdSweepPoint:
        return next(point for point in self.points if point.parameter_set.baseline)

    @property
    def best(self) -> ThresholdSweepPoint | None:
        if self.best_parameter_set_id is None:
            return None
        return self.point(self.best_parameter_set_id)

    def point(self, parameter_set_id: str) -> ThresholdSweepPoint:
        for point in self.points:
            if point.parameter_set_id == parameter_set_id:
                return point
        raise KeyError(parameter_set_id)

    def as_record(self) -> dict[str, Any]:
        _validate_report(self)
        payload = _report_payload(self)
        if _digest(payload) != self.evidence_digest:
            raise ValueError("threshold sweep evidence does not match digest")
        return {**payload, "evidence_digest": self.evidence_digest}


ThresholdEvaluator = Callable[[ThresholdParameterSet], WalkForwardValidation]


def threshold_sweep_spec(
    *,
    parameter: str,
    candidate_values: Sequence[Any],
    baseline_value: Any,
    parameter_paths: Sequence[str],
    base_config_metadata: Mapping[str, str],
    objective_metric: str = MEAN_RETURN_OBJECTIVE,
    plateau_tolerance: Any = Decimal("0"),
    scoring_architecture_version: str = SCORING_ARCHITECTURE_V1_2,
) -> ThresholdSweepSpec:
    """Declare one threshold question without changing production config."""

    if parameter not in THRESHOLD_PARAMETERS:
        raise ValueError(f"parameter must be one of {THRESHOLD_PARAMETERS}")
    values = tuple(sorted(_candidate_values(candidate_values, parameter)))
    baseline = _parameter_value(baseline_value, parameter, "baseline_value")
    if baseline not in values:
        raise ValueError("baseline_value must be one of candidate_values")
    paths = _paths(parameter_paths)
    metadata = _config_metadata(base_config_metadata)
    objective = _choice(objective_metric, THRESHOLD_OBJECTIVES, "objective_metric")
    tolerance = _non_negative_decimal(plateau_tolerance, "plateau_tolerance")
    architecture = _string(
        scoring_architecture_version, "scoring_architecture_version"
    )
    _validate_architecture(metadata["strategy_version"], architecture)
    provisional = ThresholdSweepSpec(
        feature_id=THRESHOLD_SWEEP_FEATURE_ID,
        policy_version=THRESHOLD_SWEEP_POLICY_VERSION,
        plateau_policy_version=THRESHOLD_PLATEAU_POLICY_VERSION,
        metric_policy_version=THRESHOLD_METRIC_POLICY_VERSION,
        parameter_status=THRESHOLD_PARAMETER_STATUS,
        sweep_id="",
        parameter=parameter,
        candidate_values=values,
        baseline_value=baseline,
        parameter_paths=paths,
        revalidation_scopes=THRESHOLD_REVALIDATION_SCOPES[parameter],
        objective_metric=objective,
        plateau_tolerance=tolerance,
        scoring_architecture_version=architecture,
        base_config_metadata=metadata,
    )
    spec = replace(provisional, sweep_id=_digest(_spec_payload(provisional)))
    spec.as_record()
    return spec


def threshold_parameter_sets(
    spec: ThresholdSweepSpec,
) -> tuple[ThresholdParameterSet, ...]:
    """Return deterministic config identities for every ordered candidate."""

    if not isinstance(spec, ThresholdSweepSpec):
        raise TypeError("spec must be a ThresholdSweepSpec")
    spec.as_record()
    points: list[ThresholdParameterSet] = []
    for ordinal, value in enumerate(spec.candidate_values):
        token = _digest(
            {
                "sweep_id": spec.sweep_id,
                "ordinal": ordinal,
                "parameter": spec.parameter,
                "value": str(value),
            }
        )[:16]
        parameter_set_id = (
            f"btc185-{spec.parameter.replace('_', '-')}-{ordinal:03d}-{token}"
        )
        metadata = {
            **spec.base_config_metadata,
            "parameter_set_id": parameter_set_id,
        }
        points.append(
            ThresholdParameterSet(
                parameter_set_id=parameter_set_id,
                sweep_id=spec.sweep_id,
                ordinal=ordinal,
                parameter=spec.parameter,
                value=value,
                baseline=value == spec.baseline_value,
                parameter_paths=spec.parameter_paths,
                scoring_architecture_version=spec.scoring_architecture_version,
                config_metadata=metadata,
            )
        )
    return tuple(points)


def run_threshold_sweep(
    spec: ThresholdSweepSpec,
    *,
    evaluator: ThresholdEvaluator,
) -> ThresholdSweepReport:
    """Evaluate every candidate as a separate comparable walk-forward run."""

    if not isinstance(spec, ThresholdSweepSpec):
        raise TypeError("spec must be a ThresholdSweepSpec")
    spec.as_record()
    if not callable(evaluator):
        raise TypeError("evaluator must be callable")
    validations: list[WalkForwardValidation] = []
    for parameter_set in threshold_parameter_sets(spec):
        validation = evaluator(parameter_set)
        if not isinstance(validation, WalkForwardValidation):
            raise TypeError("evaluator must return a WalkForwardValidation")
        validation.as_record()
        if validation.config_metadata != parameter_set.config_metadata:
            raise ValueError(
                "candidate validation config_metadata must match its parameter set"
            )
        validations.append(validation)
    return _build_report(spec, tuple(validations))


def restore_threshold_sweep_report(
    record: Mapping[str, Any],
) -> ThresholdSweepReport:
    """Restore persisted sweep evidence and reject derived or nested drift."""

    source = _mapping(record, "record")
    spec = _restore_spec(_mapping(source.get("spec"), "spec"))
    raw_points = _record_sequence(source.get("points"), "points")
    validations = tuple(
        restore_walk_forward_validation(
            _mapping(_mapping(item, "point").get("validation"), "validation")
        )
        for item in raw_points
    )
    report = _build_report(spec, validations)
    if report.as_record() != dict(source):
        raise ValueError("record does not match reconstructed threshold sweep")
    return report


def _build_report(
    spec: ThresholdSweepSpec,
    validations: tuple[WalkForwardValidation, ...],
) -> ThresholdSweepReport:
    parameter_sets = threshold_parameter_sets(spec)
    if len(validations) != len(parameter_sets):
        raise ValueError("one validation is required for every candidate value")
    points: list[ThresholdSweepPoint] = []
    for parameter_set, validation in zip(parameter_sets, validations, strict=True):
        validation.as_record()
        if validation.config_metadata != parameter_set.config_metadata:
            raise ValueError(
                "candidate validation config_metadata must match its parameter set"
            )
        points.append(
            ThresholdSweepPoint(
                parameter_set=parameter_set,
                validation=validation,
                metrics=_metrics(validation),
            )
        )
    _validate_comparability(tuple(points))
    best_id, plateaus, isolated = _plateau_analysis(spec, tuple(points))
    report = ThresholdSweepReport(
        feature_id=THRESHOLD_SWEEP_FEATURE_ID,
        policy_version=THRESHOLD_SWEEP_POLICY_VERSION,
        plateau_policy_version=THRESHOLD_PLATEAU_POLICY_VERSION,
        metric_policy_version=THRESHOLD_METRIC_POLICY_VERSION,
        parameter_status=THRESHOLD_PARAMETER_STATUS,
        report_id="",
        evidence_digest="",
        spec=spec,
        points=tuple(points),
        plateaus=plateaus,
        best_parameter_set_id=best_id,
        isolated_optimum=isolated,
        config_metadata=dict(spec.base_config_metadata),
        reason_codes=_reason_codes(
            spec, tuple(points), best_id, plateaus, isolated
        ),
    )
    report = replace(report, report_id=_report_id(report))
    _validate_report(report)
    return replace(report, evidence_digest=_digest(_report_payload(report)))


def _metrics(validation: WalkForwardValidation) -> ThresholdSweepMetrics:
    trades = tuple(
        trade for fold in validation.folds for trade in fold.result.trades
    )
    closed = tuple(trade for trade in trades if trade.closed)
    r_values = tuple(
        trade.r_multiple
        for trade in closed
        if trade.r_multiple is not None
    )
    closed_expectancy = (
        _mean(tuple(trade.net_pnl for trade in closed)) if closed else None
    )
    mean_r = _mean(r_values) if r_values else None
    return ThresholdSweepMetrics(
        fold_count=validation.fold_count,
        trade_count=len(trades),
        closed_trade_count=len(closed),
        summed_total_pnl=sum(
            (fold.total_pnl for fold in validation.folds), Decimal("0")
        ),
        summed_net_pnl=validation.summed_net_pnl,
        mean_return_fraction=validation.mean_return_fraction,
        worst_fold_return_fraction=validation.worst_fold.return_fraction,
        best_fold_return_fraction=validation.best_fold.return_fraction,
        closed_trade_expectancy=closed_expectancy,
        r_multiple_count=len(r_values),
        mean_r_multiple=mean_r,
    )


def _plateau_analysis(
    spec: ThresholdSweepSpec,
    points: tuple[ThresholdSweepPoint, ...],
) -> tuple[str | None, tuple[ThresholdPlateau, ...], bool]:
    comparable = tuple(
        (point, point.metrics.objective(spec.objective_metric))
        for point in points
        if point.metrics.objective(spec.objective_metric) is not None
    )
    if not comparable:
        return None, (), False
    best_point, best_value = max(
        comparable,
        key=lambda item: (item[1], -item[0].parameter_set.ordinal),
    )
    assert best_value is not None
    eligible_ordinals = {
        point.parameter_set.ordinal
        for point, value in comparable
        if value is not None and best_value - value <= spec.plateau_tolerance
    }
    segments: list[list[ThresholdSweepPoint]] = []
    current: list[ThresholdSweepPoint] = []
    for point in points:
        if point.parameter_set.ordinal in eligible_ordinals:
            current.append(point)
        else:
            if len(current) >= 2:
                segments.append(current)
            current = []
    if len(current) >= 2:
        segments.append(current)

    plateaus: list[ThresholdPlateau] = []
    for segment in segments:
        objective_values = tuple(
            point.metrics.objective(spec.objective_metric) for point in segment
        )
        if any(value is None for value in objective_values):
            raise ValueError("plateau objective values must be available")
        values = tuple(value for value in objective_values if value is not None)
        segment_best = max(
            segment,
            key=lambda point: (
                point.metrics.objective(spec.objective_metric),
                -point.parameter_set.ordinal,
            ),
        )
        plateau_id = _digest(
            {
                "policy": THRESHOLD_PLATEAU_POLICY_VERSION,
                "sweep_id": spec.sweep_id,
                "parameter_set_ids": [item.parameter_set_id for item in segment],
            }
        )
        plateaus.append(
            ThresholdPlateau(
                plateau_id=plateau_id,
                first_ordinal=segment[0].parameter_set.ordinal,
                last_ordinal=segment[-1].parameter_set.ordinal,
                lower_value=segment[0].value,
                upper_value=segment[-1].value,
                point_count=len(segment),
                parameter_set_ids=tuple(item.parameter_set_id for item in segment),
                best_parameter_set_id=segment_best.parameter_set_id,
                best_objective_value=max(values),
                worst_objective_value=min(values),
            )
        )
    best_id = best_point.parameter_set_id
    isolated = not any(best_id in item.parameter_set_ids for item in plateaus)
    return best_id, tuple(plateaus), isolated


def _validate_comparability(points: tuple[ThresholdSweepPoint, ...]) -> None:
    if not points:
        raise ValueError("threshold sweep must contain candidate points")
    first = _comparison_signature(points[0].validation)
    for point in points[1:]:
        if _comparison_signature(point.validation) != first:
            raise ValueError(
                "candidate validations must share schedule, split, capital, costs, "
                "fitting procedure, and scoring-independent run assumptions"
            )


def _comparison_signature(validation: WalkForwardValidation) -> dict[str, Any]:
    plan = validation.plan
    return {
        "symbol": validation.symbol,
        "schedule_digest": validation.schedule_digest,
        "scheme": plan.scheme,
        "train_periods": plan.train_periods,
        "test_periods": plan.test_periods,
        "step_periods": plan.step_periods,
        "embargo_periods": plan.embargo_periods,
        "starting_nav": str(validation.starting_nav),
        "costs": validation.effective_costs.as_record(),
        "cost_profile": (
            validation.cost_profile.as_record()
            if validation.cost_profile is not None
            else None
        ),
        "scheduled_periods": validation.scheduled_periods,
        "tested_periods": validation.tested_periods,
        "untested_leading_periods": validation.untested_leading_periods,
        "untested_gap_periods": validation.untested_gap_periods,
        "untested_trailing_periods": validation.untested_trailing_periods,
        "out_of_sample_input_digests": [
            fold.result.input_digest for fold in validation.folds
        ],
        "config_version": validation.config_metadata.get("config_version"),
        "strategy_version": validation.config_metadata.get("strategy_version"),
        "strategy_declaration": (
            "WALK_FORWARD_STRATEGY_RECALIBRATED"
            if "WALK_FORWARD_STRATEGY_RECALIBRATED" in validation.reason_codes
            else "WALK_FORWARD_STRATEGY_CONSTANT"
        ),
    }


def _reason_codes(
    spec: ThresholdSweepSpec,
    points: tuple[ThresholdSweepPoint, ...],
    best_id: str | None,
    plateaus: tuple[ThresholdPlateau, ...],
    isolated: bool,
) -> tuple[str, ...]:
    codes = [
        "THRESHOLD_SWEEP_ONE_DIMENSIONAL",
        "THRESHOLD_SWEEP_OUT_OF_SAMPLE",
        "THRESHOLD_SWEEP_COMPARABLE_RUNS",
        "THRESHOLD_SWEEP_PARAMETER_SETS_PERSISTED",
    ]
    if spec.parameter in (
        ENTRY_CONVICTION,
        STRUCTURE_MINIMUM,
        HOLD_THRESHOLD,
        ADD_THRESHOLD,
    ):
        codes.append("THRESHOLD_SWEEP_SCORE_BAND_SCOPE_EVALUATED")
    codes.append("THRESHOLD_SWEEP_ARCHITECTURE_ISOLATED")
    traded = tuple(point for point in points if point.metrics.trade_count > 0)
    if not traded:
        # A candidate that never traded still returns exactly zero, so a flat
        # sweep would otherwise read as a robust plateau built on no evidence.
        codes.append("THRESHOLD_SWEEP_NO_TRADES")
    elif len(traded) != len(points):
        codes.append("THRESHOLD_SWEEP_CANDIDATES_WITHOUT_TRADES")
    if best_id is None:
        codes.append("THRESHOLD_SWEEP_NO_COMPARABLE_OBJECTIVE")
    if plateaus:
        codes.append("THRESHOLD_SWEEP_ROBUST_PLATEAU")
    if isolated:
        codes.append("THRESHOLD_SWEEP_ISOLATED_OPTIMUM")
    codes.append("THRESHOLD_SWEEP_COMPLETE")
    return tuple(codes)


def _validate_spec(spec: ThresholdSweepSpec) -> None:
    if spec.feature_id != THRESHOLD_SWEEP_FEATURE_ID:
        raise ValueError(f"feature_id must be {THRESHOLD_SWEEP_FEATURE_ID}")
    if spec.policy_version != THRESHOLD_SWEEP_POLICY_VERSION:
        raise ValueError(f"policy_version must be {THRESHOLD_SWEEP_POLICY_VERSION}")
    if spec.plateau_policy_version != THRESHOLD_PLATEAU_POLICY_VERSION:
        raise ValueError(
            f"plateau_policy_version must be {THRESHOLD_PLATEAU_POLICY_VERSION}"
        )
    if spec.metric_policy_version != THRESHOLD_METRIC_POLICY_VERSION:
        raise ValueError(
            f"metric_policy_version must be {THRESHOLD_METRIC_POLICY_VERSION}"
        )
    if spec.parameter_status != THRESHOLD_PARAMETER_STATUS:
        raise ValueError(f"parameter_status must be {THRESHOLD_PARAMETER_STATUS}")
    if spec.parameter not in THRESHOLD_PARAMETERS:
        raise ValueError(f"parameter must be one of {THRESHOLD_PARAMETERS}")
    if tuple(sorted(spec.candidate_values)) != spec.candidate_values:
        raise ValueError("candidate_values must be in ascending order")
    if len(spec.candidate_values) < 2 or len(set(spec.candidate_values)) != len(
        spec.candidate_values
    ):
        raise ValueError("candidate_values must contain at least two unique values")
    for value in spec.candidate_values:
        _parameter_value(value, spec.parameter, "candidate_value")
    if spec.baseline_value not in spec.candidate_values:
        raise ValueError("baseline_value must be one of candidate_values")
    if spec.parameter_paths != _paths(spec.parameter_paths):
        raise ValueError("parameter_paths must be canonical")
    if spec.revalidation_scopes != THRESHOLD_REVALIDATION_SCOPES[spec.parameter]:
        raise ValueError("revalidation_scopes do not match the threshold parameter")
    _choice(spec.objective_metric, THRESHOLD_OBJECTIVES, "objective_metric")
    _non_negative_decimal(spec.plateau_tolerance, "plateau_tolerance")
    metadata = _config_metadata(spec.base_config_metadata)
    _validate_architecture(
        metadata["strategy_version"], spec.scoring_architecture_version
    )


def _validate_report(report: ThresholdSweepReport) -> None:
    if report.feature_id != THRESHOLD_SWEEP_FEATURE_ID:
        raise ValueError(f"feature_id must be {THRESHOLD_SWEEP_FEATURE_ID}")
    if report.policy_version != THRESHOLD_SWEEP_POLICY_VERSION:
        raise ValueError(f"policy_version must be {THRESHOLD_SWEEP_POLICY_VERSION}")
    if report.plateau_policy_version != THRESHOLD_PLATEAU_POLICY_VERSION:
        raise ValueError("unexpected plateau_policy_version")
    if report.metric_policy_version != THRESHOLD_METRIC_POLICY_VERSION:
        raise ValueError("unexpected metric_policy_version")
    if report.parameter_status != THRESHOLD_PARAMETER_STATUS:
        raise ValueError("unexpected parameter_status")
    report.spec.as_record()
    if report.config_metadata != report.spec.base_config_metadata:
        raise ValueError("report config_metadata must match the sweep base")
    expected_sets = threshold_parameter_sets(report.spec)
    if tuple(point.parameter_set for point in report.points) != expected_sets:
        raise ValueError("report points do not match the declared candidates")
    for point in report.points:
        point.validation.as_record()
        if point.validation.config_metadata != point.parameter_set.config_metadata:
            raise ValueError("point validation does not match its parameter set")
        if point.metrics != _metrics(point.validation):
            raise ValueError("point metrics do not match validation evidence")
    _validate_comparability(report.points)
    best, plateaus, isolated = _plateau_analysis(report.spec, report.points)
    if (
        report.best_parameter_set_id != best
        or report.plateaus != plateaus
        or report.isolated_optimum != isolated
    ):
        raise ValueError("plateau analysis does not match point evidence")
    if report.reason_codes != _reason_codes(
        report.spec, report.points, best, plateaus, isolated
    ):
        raise ValueError("reason codes do not describe the threshold sweep")
    if report.report_id != _report_id(report):
        raise ValueError("threshold sweep inputs do not match report_id")


def _report_id(report: ThresholdSweepReport) -> str:
    return _digest(
        {
            "policy": THRESHOLD_SWEEP_POLICY_VERSION,
            "plateau_policy": THRESHOLD_PLATEAU_POLICY_VERSION,
            "metric_policy": THRESHOLD_METRIC_POLICY_VERSION,
            "sweep_id": report.spec.sweep_id,
            "validation_ids": [
                point.validation.validation_id for point in report.points
            ],
        }
    )


def _report_payload(report: ThresholdSweepReport) -> dict[str, Any]:
    return {
        "feature_id": report.feature_id,
        "policy_version": report.policy_version,
        "plateau_policy_version": report.plateau_policy_version,
        "metric_policy_version": report.metric_policy_version,
        "parameter_status": report.parameter_status,
        "report_id": report.report_id,
        "spec": report.spec.as_record(),
        "points": [point.as_record() for point in report.points],
        "plateaus": [plateau.as_record() for plateau in report.plateaus],
        "best_parameter_set_id": report.best_parameter_set_id,
        "isolated_optimum": report.isolated_optimum,
        "config_metadata": dict(report.config_metadata),
        "reason_codes": list(report.reason_codes),
    }


def _spec_payload(spec: ThresholdSweepSpec) -> dict[str, Any]:
    return {
        "feature_id": spec.feature_id,
        "policy_version": spec.policy_version,
        "plateau_policy_version": spec.plateau_policy_version,
        "metric_policy_version": spec.metric_policy_version,
        "parameter_status": spec.parameter_status,
        "parameter": spec.parameter,
        "candidate_values": [str(value) for value in spec.candidate_values],
        "baseline_value": str(spec.baseline_value),
        "parameter_paths": list(spec.parameter_paths),
        "revalidation_scopes": list(spec.revalidation_scopes),
        "objective_metric": spec.objective_metric,
        "plateau_tolerance": str(spec.plateau_tolerance),
        "scoring_architecture_version": spec.scoring_architecture_version,
        "base_config_metadata": dict(spec.base_config_metadata),
    }


def _restore_spec(source: Mapping[str, Any]) -> ThresholdSweepSpec:
    spec = threshold_sweep_spec(
        parameter=_string(source.get("parameter"), "spec.parameter"),
        candidate_values=_record_sequence(
            source.get("candidate_values"), "spec.candidate_values"
        ),
        baseline_value=source.get("baseline_value"),
        parameter_paths=_string_tuple(
            source.get("parameter_paths"), "spec.parameter_paths"
        ),
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
        raise ValueError("record does not match reconstructed threshold sweep spec")
    return spec


def _candidate_values(values: Sequence[Any], parameter: str) -> tuple[Decimal, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise TypeError("candidate_values must be a sequence")
    converted = tuple(
        _parameter_value(value, parameter, "candidate_value") for value in values
    )
    if len(converted) < 2 or len(set(converted)) != len(converted):
        raise ValueError("candidate_values must contain at least two unique values")
    return converted


def _parameter_value(value: Any, parameter: str, name: str) -> Decimal:
    result = _decimal(value, name)
    if parameter in _SCORE_PARAMETERS and not Decimal("0") <= result <= Decimal("100"):
        raise ValueError(f"{name} must be between 0 and 100 for {parameter}")
    if parameter in (REWARD_RISK_MINIMUM, RISK_BUDGET) and result <= 0:
        raise ValueError(f"{name} must be positive for {parameter}")
    if parameter == RISK_BUDGET and result >= 1:
        raise ValueError(f"{name} must be below 1 for {parameter}")
    if parameter == STOP_BUFFER and result <= 0:
        raise ValueError(f"{name} must be positive for {parameter}")
    return result


def _paths(values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise TypeError("parameter_paths must be a sequence")
    paths = tuple(sorted(_string(value, "parameter_path") for value in values))
    if not paths or len(set(paths)) != len(paths):
        raise ValueError("parameter_paths must contain unique paths")
    if any(
        "." not in path or path.startswith(".") or path.endswith(".")
        for path in paths
    ):
        raise ValueError("parameter_paths must be dotted configuration paths")
    return paths


def _config_metadata(value: Mapping[str, str]) -> dict[str, str]:
    source = _mapping(value, "base_config_metadata")
    expected = ("config_version", "strategy_version", "parameter_set_id")
    if set(source) != set(expected):
        raise ValueError(f"base_config_metadata must contain exactly {expected}")
    return {
        key: _string(source.get(key), f"base_config_metadata.{key}")
        for key in expected
    }


def _validate_architecture(strategy_version: str, architecture: str) -> None:
    _string(architecture, "scoring_architecture_version")
    allowed_pairs = {
        ("swing_v1.2", SCORING_ARCHITECTURE_V1_2),
        ("swing_v1.1", SCORING_ARCHITECTURE_V1_1_BENCHMARK),
    }
    if (strategy_version, architecture) not in allowed_pairs:
        raise ValueError(
            "threshold sweeps must isolate swing_v1.2 direct scoring from the "
            "swing_v1.1 nested benchmark architecture"
        )


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    return (sum(values, Decimal("0")) / Decimal(len(values))).quantize(
        THRESHOLD_METRIC_EXPONENT,
        rounding=ROUND_HALF_EVEN,
    )


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
