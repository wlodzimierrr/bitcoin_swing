"""Single-component ablation of a composite score (BTC-189).

A weight is only justified if removing the thing it weighs makes the strategy
worse.  This module asks that question one component at a time.

Each variant removes exactly one direct component from a declared BTC-129
composite and renormalizes the remaining declared weights proportionally, so
the surviving components keep their relative importance and their sum stays
one.  Nothing else moves: component definitions, thresholds, filters, sizing,
costs, the schedule, and the walk-forward split are identical across variants,
which is what makes a measured difference attributable to the removed
component rather than to a refit of unrelated rules.

Like BTC-185 and BTC-188, this layer does not rescore features or mutate
configuration.  A caller receives a versioned parameter-set identity for every
variant, builds that strategy through the existing owners, and returns a
complete BTC-182 out-of-sample validation.  Comparable runs are enforced
before anything is compared.

Every variant reports its trade-decision overlap with the baseline, and the
change in expectancy, average R, and drawdown.  Net outcome metrics stay owned
by BTC-185 and the drawdown by BTC-188; a change whose baseline or variant
value is undefined is declared undefined rather than reported as zero.

Results are research evidence only; this module has no strategy or
configuration mutation path and records BTC-193 as the required promotion
boundary.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from typing import Any

from btc_predictor.backtest.parameter_surfaces import (
    DRAWDOWN_AVAILABLE,
    DRAWDOWN_STATUSES,
    SURFACE_DRAWDOWN_POLICY_VERSION,
    walk_forward_max_drawdown,
)
from btc_predictor.backtest.threshold_sweeps import (
    SCORING_ARCHITECTURE_V1_1_BENCHMARK,
    SCORING_ARCHITECTURE_V1_2,
    THRESHOLD_METRIC_POLICY_VERSION,
    THRESHOLD_PARAMETER_STATUS,
    ThresholdSweepMetrics,
    comparable_run_signature,
    threshold_config_metadata,
    threshold_parameter_paths,
    threshold_sweep_metrics,
    validate_scoring_architecture,
)
from btc_predictor.backtest.walk_forward import (
    WalkForwardValidation,
    restore_walk_forward_validation,
)
from btc_predictor.features.scoring_contracts import (
    MECHANICAL_VS_EMPIRICAL_NOTE,
    RETIRED_SCORING_CONTRACTS_VERSION,
    SCORING_CONTRACTS_VERSION,
    SCORING_GRAPH_V1_1,
    SCORING_GRAPH_V1_2,
    audit_factor_overlap,
)


COMPONENT_ABLATION_FEATURE_ID = "COMPONENT_ABLATION"
COMPONENT_ABLATION_POLICY_VERSION = "SINGLE_COMPONENT_ABLATION_V1"
ABLATION_WEIGHT_POLICY_VERSION = (
    "PROPORTIONAL_RENORMALIZATION_OF_REMAINING_COMPONENTS_V1"
)
ABLATION_ISOLATION_POLICY_VERSION = "UNRELATED_RULES_UNCHANGED_V1"
ABLATION_OVERLAP_POLICY_VERSION = "FOLD_ENTRY_TIMESTAMP_TRADE_OVERLAP_V1"
ABLATION_METRIC_POLICY_VERSION = THRESHOLD_METRIC_POLICY_VERSION
ABLATION_DRAWDOWN_POLICY_VERSION = SURFACE_DRAWDOWN_POLICY_VERSION
ABLATION_PROMOTION_POLICY_VERSION = "BTC_193_REQUIRED_V1"
ABLATION_PRODUCTION_STATUS = "RESEARCH_ONLY_NOT_PRODUCTION"
ABLATION_PROMOTION_TICKET = "BTC-193"
ABLATION_PARAMETER_STATUS = THRESHOLD_PARAMETER_STATUS

# The declared scoring architecture selects the BTC-129 graph and contracts
# version the study reads; the weights are never restated here.
ABLATION_ARCHITECTURES = {
    SCORING_ARCHITECTURE_V1_2: (SCORING_GRAPH_V1_2, SCORING_CONTRACTS_VERSION),
    SCORING_ARCHITECTURE_V1_1_BENCHMARK: (
        SCORING_GRAPH_V1_1,
        RETIRED_SCORING_CONTRACTS_VERSION,
    ),
}

ABLATION_METRIC_EXPONENT = Decimal("1E-12")
ABLATION_WEIGHT_TOLERANCE = Decimal("1E-11")
ABLATION_DECIMAL_PRECISION = 60

OVERLAP_AVAILABLE = "AVAILABLE"
OVERLAP_NO_ENTRIES = "NO_ENTRIES"
OVERLAP_STATUSES = (OVERLAP_AVAILABLE, OVERLAP_NO_ENTRIES)

CHANGE_AVAILABLE = "AVAILABLE"
CHANGE_BASELINE_UNDEFINED = "BASELINE_UNDEFINED"
CHANGE_VARIANT_UNDEFINED = "VARIANT_UNDEFINED"
CHANGE_BOTH_UNDEFINED = "BOTH_UNDEFINED"
CHANGE_STATUSES = (
    CHANGE_AVAILABLE,
    CHANGE_BASELINE_UNDEFINED,
    CHANGE_VARIANT_UNDEFINED,
    CHANGE_BOTH_UNDEFINED,
)

COMPONENT_ABLATION_REASON_CODES = (
    "COMPONENT_ABLATION_SINGLE_COMPONENT_REMOVED",
    "COMPONENT_ABLATION_REMAINING_WEIGHTS_RENORMALIZED",
    "COMPONENT_ABLATION_UNRELATED_RULES_UNCHANGED",
    "COMPONENT_ABLATION_OUT_OF_SAMPLE",
    "COMPONENT_ABLATION_COMPARABLE_RUNS",
    "COMPONENT_ABLATION_TRADE_DECISION_OVERLAP_REPORTED",
    "COMPONENT_ABLATION_EXPECTANCY_REPORTED",
    "COMPONENT_ABLATION_MEAN_R_REPORTED",
    "COMPONENT_ABLATION_DRAWDOWN_REPORTED",
    "COMPONENT_ABLATION_MECHANICALLY_CLEAN",
    "COMPONENT_ABLATION_MECHANICAL_NESTING_DETECTED",
    "COMPONENT_ABLATION_VARIANTS_WITHOUT_TRADES",
    "COMPONENT_ABLATION_NO_TRADES",
    "COMPONENT_ABLATION_RESEARCH_ONLY",
    "COMPONENT_ABLATION_BTC_193_PROMOTION_REQUIRED",
    "COMPONENT_ABLATION_COMPLETE",
)


class ComponentAblationError(ValueError):
    """Raised when ablation inputs violate the BTC-189 contract."""


@dataclass(frozen=True)
class ComponentWeight:
    """One component's weight inside a composite score."""

    component: str
    weight: Decimal

    def as_record(self) -> dict[str, str]:
        _non_empty(self.component, "component")
        if not isinstance(self.weight, Decimal) or not self.weight.is_finite():
            raise ComponentAblationError("weight must be a finite Decimal")
        if self.weight < 0:
            raise ComponentAblationError("weight must be non-negative")
        return {"component": self.component, "weight": str(self.weight)}


@dataclass(frozen=True)
class AblationVariant:
    """One run identity: the baseline, or the composite minus one component."""

    parameter_set_id: str
    spec_id: str
    ordinal: int
    baseline: bool
    composite: str
    removed_component: str | None
    weights: tuple[ComponentWeight, ...]
    weight_total: Decimal
    parameter_paths: tuple[str, ...]
    scoring_architecture_version: str
    config_metadata: dict[str, str]

    def weight(self, component: str) -> Decimal:
        for item in self.weights:
            if item.component == component:
                return item.weight
        raise KeyError(component)

    def as_record(self) -> dict[str, Any]:
        _validate_variant(self)
        return {
            "parameter_set_id": self.parameter_set_id,
            "spec_id": self.spec_id,
            "ordinal": self.ordinal,
            "baseline": self.baseline,
            "composite": self.composite,
            "removed_component": self.removed_component,
            "weights": [item.as_record() for item in self.weights],
            "weight_total": str(self.weight_total),
            "parameter_paths": list(self.parameter_paths),
            "scoring_architecture_version": self.scoring_architecture_version,
            "config_metadata": dict(self.config_metadata),
        }


@dataclass(frozen=True)
class AblationMetrics:
    """Comparable outcomes for one variant, from its BTC-182 evidence."""

    outcome: ThresholdSweepMetrics
    max_drawdown_fraction: Decimal | None
    max_drawdown_status: str

    @property
    def trade_count(self) -> int:
        return self.outcome.trade_count

    @property
    def closed_trade_expectancy(self) -> Decimal | None:
        return self.outcome.closed_trade_expectancy

    @property
    def mean_r_multiple(self) -> Decimal | None:
        return self.outcome.mean_r_multiple

    def as_record(self) -> dict[str, Any]:
        _validate_metrics(self)
        return {
            "outcome": self.outcome.as_record(),
            "max_drawdown_fraction": _optional_decimal(self.max_drawdown_fraction),
            "max_drawdown_status": self.max_drawdown_status,
        }


@dataclass(frozen=True)
class TradeDecisionOverlap:
    """How many of the baseline's entries the ablated run still took."""

    status: str
    baseline_entry_count: int
    variant_entry_count: int
    shared_entry_count: int
    baseline_only_entry_count: int
    variant_only_entry_count: int
    overlap_fraction: Decimal | None

    def as_record(self) -> dict[str, Any]:
        _validate_overlap(self)
        return {
            "status": self.status,
            "baseline_entry_count": self.baseline_entry_count,
            "variant_entry_count": self.variant_entry_count,
            "shared_entry_count": self.shared_entry_count,
            "baseline_only_entry_count": self.baseline_only_entry_count,
            "variant_only_entry_count": self.variant_only_entry_count,
            "overlap_fraction": _optional_decimal(self.overlap_fraction),
        }


@dataclass(frozen=True)
class AblationChange:
    """What removing one component changed, relative to the baseline run."""

    trade_count_change: int
    closed_trade_count_change: int
    mean_return_fraction_change: Decimal
    closed_trade_expectancy_change: Decimal | None
    expectancy_change_status: str
    mean_r_multiple_change: Decimal | None
    mean_r_change_status: str
    max_drawdown_change: Decimal | None
    drawdown_change_status: str

    def as_record(self) -> dict[str, Any]:
        _validate_change(self)
        return {
            "trade_count_change": self.trade_count_change,
            "closed_trade_count_change": self.closed_trade_count_change,
            "mean_return_fraction_change": str(self.mean_return_fraction_change),
            "closed_trade_expectancy_change": _optional_decimal(
                self.closed_trade_expectancy_change
            ),
            "expectancy_change_status": self.expectancy_change_status,
            "mean_r_multiple_change": _optional_decimal(
                self.mean_r_multiple_change
            ),
            "mean_r_change_status": self.mean_r_change_status,
            "max_drawdown_change": _optional_decimal(self.max_drawdown_change),
            "drawdown_change_status": self.drawdown_change_status,
        }


@dataclass(frozen=True)
class AblationResult:
    """One persisted variant evaluation."""

    variant: AblationVariant
    validation: WalkForwardValidation
    metrics: AblationMetrics
    overlap: TradeDecisionOverlap | None
    change: AblationChange | None

    @property
    def removed_component(self) -> str | None:
        return self.variant.removed_component

    @property
    def parameter_set_id(self) -> str:
        return self.variant.parameter_set_id

    def as_record(self) -> dict[str, Any]:
        return {
            "variant": self.variant.as_record(),
            "validation": self.validation.as_record(),
            "metrics": self.metrics.as_record(),
            "overlap": None if self.overlap is None else self.overlap.as_record(),
            "change": None if self.change is None else self.change.as_record(),
        }


@dataclass(frozen=True)
class ComponentAblationSpec:
    """Frozen ablation question for one declared composite score."""

    feature_id: str
    policy_version: str
    weight_policy_version: str
    isolation_policy_version: str
    overlap_policy_version: str
    metric_policy_version: str
    drawdown_policy_version: str
    promotion_policy_version: str
    parameter_status: str
    spec_id: str
    composite: str
    contracts_version: str
    baseline_weights: tuple[ComponentWeight, ...]
    ablated_components: tuple[str, ...]
    parameter_paths: tuple[str, ...]
    scoring_architecture_version: str
    base_config_metadata: dict[str, str]

    def as_record(self) -> dict[str, Any]:
        _validate_spec(self)
        payload = _spec_payload(self)
        if _digest(payload) != self.spec_id:
            raise ComponentAblationError(
                "component ablation specification does not match spec_id"
            )
        return {**payload, "spec_id": self.spec_id}


@dataclass(frozen=True)
class ComponentAblationReport:
    """Replayable, research-only BTC-189 ablation evidence."""

    feature_id: str
    policy_version: str
    report_id: str
    evidence_digest: str
    spec: ComponentAblationSpec
    results: tuple[AblationResult, ...]
    factor_overlap_audit: dict[str, Any]
    production_status: str
    promotion_ticket: str
    config_metadata: dict[str, str]
    reason_codes: tuple[str, ...]

    @property
    def baseline(self) -> AblationResult:
        return next(item for item in self.results if item.variant.baseline)

    def result(self, removed_component: str) -> AblationResult:
        for item in self.results:
            if item.removed_component == removed_component:
                return item
        raise KeyError(removed_component)

    def as_record(self) -> dict[str, Any]:
        _validate_report(self)
        payload = _report_payload(self)
        if _digest(payload) != self.evidence_digest:
            raise ComponentAblationError(
                "component ablation evidence does not match digest"
            )
        return {**payload, "evidence_digest": self.evidence_digest}


AblationEvaluator = Callable[[AblationVariant], WalkForwardValidation]


def component_ablation_spec(
    *,
    base_config_metadata: Mapping[str, str],
    parameter_paths: Sequence[str],
    composite: str = "entry_conviction",
    ablated_components: Sequence[str] | None = None,
    scoring_architecture_version: str = SCORING_ARCHITECTURE_V1_2,
) -> ComponentAblationSpec:
    """Declare one ablation study over a composite's direct components."""

    architecture = _non_empty(
        scoring_architecture_version, "scoring_architecture_version"
    )
    if architecture not in ABLATION_ARCHITECTURES:
        raise ComponentAblationError(
            f"scoring_architecture_version must be one of "
            f"{tuple(ABLATION_ARCHITECTURES)}"
        )
    graph, contracts_version = ABLATION_ARCHITECTURES[architecture]
    _non_empty(composite, "composite")
    if composite not in graph:
        raise ComponentAblationError(f"unknown composite: {composite}")
    declared = graph[composite]
    if not declared:
        raise ComponentAblationError("a composite must declare component weights")
    weights = tuple(
        ComponentWeight(component=name, weight=_quantize(_weight(declared[name], name)))
        for name in sorted(declared)
    )
    components = (
        tuple(sorted(declared))
        if ablated_components is None
        else tuple(_non_empty(item, "ablated_component") for item in ablated_components)
    )
    if not components:
        raise ComponentAblationError("at least one component must be ablated")
    if len(set(components)) != len(components):
        raise ComponentAblationError("ablated components must be unique")
    unknown = sorted(set(components) - set(declared))
    if unknown:
        raise ComponentAblationError(
            "ablated components must be declared components: " + ", ".join(unknown)
        )
    metadata = threshold_config_metadata(base_config_metadata)
    validate_scoring_architecture(metadata["strategy_version"], architecture)
    provisional = ComponentAblationSpec(
        feature_id=COMPONENT_ABLATION_FEATURE_ID,
        policy_version=COMPONENT_ABLATION_POLICY_VERSION,
        weight_policy_version=ABLATION_WEIGHT_POLICY_VERSION,
        isolation_policy_version=ABLATION_ISOLATION_POLICY_VERSION,
        overlap_policy_version=ABLATION_OVERLAP_POLICY_VERSION,
        metric_policy_version=ABLATION_METRIC_POLICY_VERSION,
        drawdown_policy_version=ABLATION_DRAWDOWN_POLICY_VERSION,
        promotion_policy_version=ABLATION_PROMOTION_POLICY_VERSION,
        parameter_status=ABLATION_PARAMETER_STATUS,
        spec_id="",
        composite=composite,
        contracts_version=contracts_version,
        baseline_weights=weights,
        ablated_components=tuple(sorted(components)),
        parameter_paths=threshold_parameter_paths(parameter_paths),
        scoring_architecture_version=architecture,
        base_config_metadata=metadata,
    )
    _validate_spec(provisional, allow_empty_id=True)
    spec = replace(provisional, spec_id=_digest(_spec_payload(provisional)))
    spec.as_record()
    return spec


def ablation_variants(spec: ComponentAblationSpec) -> tuple[AblationVariant, ...]:
    """Return the baseline and every single-component ablation, in order.

    Removing one component redistributes its weight across the survivors in
    proportion to their declared weights.  No survivor's relative importance
    changes, and no rule outside this composite's weight vector is touched.
    """

    if not isinstance(spec, ComponentAblationSpec):
        raise TypeError("spec must be a ComponentAblationSpec")
    spec.as_record()
    variants = [_variant(spec, ordinal=0, removed=None)]
    for ordinal, component in enumerate(spec.ablated_components, start=1):
        variants.append(_variant(spec, ordinal=ordinal, removed=component))
    return tuple(variants)


def run_component_ablation(
    spec: ComponentAblationSpec,
    *,
    evaluator: AblationEvaluator,
) -> ComponentAblationReport:
    """Evaluate the baseline and every ablation as comparable runs."""

    if not isinstance(spec, ComponentAblationSpec):
        raise TypeError("spec must be a ComponentAblationSpec")
    spec.as_record()
    if not callable(evaluator):
        raise TypeError("evaluator must be callable")
    validations: list[WalkForwardValidation] = []
    for variant in ablation_variants(spec):
        validation = evaluator(variant)
        if not isinstance(validation, WalkForwardValidation):
            raise TypeError("evaluator must return a WalkForwardValidation")
        validation.as_record()
        if validation.config_metadata != variant.config_metadata:
            raise ComponentAblationError(
                "variant validation config_metadata must match its parameter set"
            )
        validations.append(validation)
    return _build_report(spec, tuple(validations))


def restore_component_ablation_report(
    record: Mapping[str, Any],
) -> ComponentAblationReport:
    """Restore persisted ablation evidence and reject derived drift."""

    source = _mapping(record, "record")
    spec = _spec_from_record(_mapping(source.get("spec"), "spec"))
    validations = tuple(
        restore_walk_forward_validation(
            _mapping(_mapping(item, "result").get("validation"), "validation")
        )
        for item in _sequence(source.get("results"), "results")
    )
    report = _build_report(spec, validations)
    if report.as_record() != dict(source):
        raise ComponentAblationError(
            "record does not match reconstructed component ablation"
        )
    return report


def _variant(
    spec: ComponentAblationSpec, *, ordinal: int, removed: str | None
) -> AblationVariant:
    if removed is None:
        weights = spec.baseline_weights
    else:
        declared = {item.component: item.weight for item in spec.baseline_weights}
        removed_weight = declared.pop(removed)
        with localcontext(Context(prec=ABLATION_DECIMAL_PRECISION)):
            remaining = sum(declared.values(), Decimal("0"))
            if remaining <= 0:
                raise ComponentAblationError(
                    f"removing {removed!r} leaves no weighted component behind"
                )
            if removed_weight < 0:
                raise ComponentAblationError(
                    "component weights must be non-negative"
                )
            weights = tuple(
                ComponentWeight(
                    component=name,
                    weight=_quantize(declared[name] / remaining),
                )
                for name in sorted(declared)
            )
    total = _weight_total(weights)
    token = _digest(
        {
            "spec_id": spec.spec_id,
            "ordinal": ordinal,
            "composite": spec.composite,
            "removed_component": removed,
        }
    )[:16]
    parameter_set_id = (
        f"btc189-{spec.composite.replace('_', '-')}-{ordinal:03d}-{token}"
    )
    variant = AblationVariant(
        parameter_set_id=parameter_set_id,
        spec_id=spec.spec_id,
        ordinal=ordinal,
        baseline=removed is None,
        composite=spec.composite,
        removed_component=removed,
        weights=weights,
        weight_total=total,
        parameter_paths=spec.parameter_paths,
        scoring_architecture_version=spec.scoring_architecture_version,
        config_metadata={
            **spec.base_config_metadata,
            "parameter_set_id": parameter_set_id,
        },
    )
    _validate_variant(variant)
    return variant


def _build_report(
    spec: ComponentAblationSpec,
    validations: tuple[WalkForwardValidation, ...],
) -> ComponentAblationReport:
    variants = ablation_variants(spec)
    if len(validations) != len(variants):
        raise ComponentAblationError(
            "one validation is required for the baseline and every ablation"
        )
    for variant, validation in zip(variants, validations, strict=True):
        validation.as_record()
        if validation.config_metadata != variant.config_metadata:
            raise ComponentAblationError(
                "variant validation config_metadata must match its parameter set"
            )
    _validate_comparability(validations)
    metrics = tuple(_metrics(validation) for validation in validations)
    baseline_validation = validations[0]
    baseline_metrics = metrics[0]
    baseline_entries = _entry_keys(baseline_validation)
    results: list[AblationResult] = []
    for index, (variant, validation) in enumerate(
        zip(variants, validations, strict=True)
    ):
        if variant.baseline:
            results.append(
                AblationResult(
                    variant=variant,
                    validation=validation,
                    metrics=metrics[index],
                    overlap=None,
                    change=None,
                )
            )
            continue
        results.append(
            AblationResult(
                variant=variant,
                validation=validation,
                metrics=metrics[index],
                overlap=_overlap(baseline_entries, _entry_keys(validation)),
                change=_change(baseline_metrics, metrics[index]),
            )
        )
    resolved = tuple(results)
    graph, contracts_version = ABLATION_ARCHITECTURES[
        spec.scoring_architecture_version
    ]
    audit = audit_factor_overlap(
        spec.composite, graph, contracts_version=contracts_version
    )
    report = ComponentAblationReport(
        feature_id=COMPONENT_ABLATION_FEATURE_ID,
        policy_version=COMPONENT_ABLATION_POLICY_VERSION,
        report_id="",
        evidence_digest="",
        spec=spec,
        results=resolved,
        factor_overlap_audit=audit.as_record(),
        production_status=ABLATION_PRODUCTION_STATUS,
        promotion_ticket=ABLATION_PROMOTION_TICKET,
        config_metadata=dict(spec.base_config_metadata),
        reason_codes=_reason_codes(resolved, audit.mechanically_clean),
    )
    report = replace(report, report_id=_report_id(report))
    _validate_report(report)
    return replace(report, evidence_digest=_digest(_report_payload(report)))


def _metrics(validation: WalkForwardValidation) -> AblationMetrics:
    drawdown, status = walk_forward_max_drawdown(validation)
    metrics = AblationMetrics(
        outcome=threshold_sweep_metrics(validation),
        max_drawdown_fraction=drawdown,
        max_drawdown_status=status,
    )
    _validate_metrics(metrics)
    return metrics


def _entry_keys(validation: WalkForwardValidation) -> Counter[tuple[int, str]]:
    """Identify each entry by its fold and the bar the position opened on.

    Two comparable runs replay the same schedule, so an entry taken on the
    same fold and the same bar is the same trade decision.  Run-local
    identifiers such as event IDs are not comparable across runs.
    """

    return Counter(
        (fold.fold_number, trade.opened_at.isoformat())
        for fold in validation.folds
        for trade in fold.result.trades
    )


def _overlap(
    baseline: Counter[tuple[int, str]],
    variant: Counter[tuple[int, str]],
) -> TradeDecisionOverlap:
    shared = sum((baseline & variant).values())
    baseline_count = sum(baseline.values())
    variant_count = sum(variant.values())
    union = baseline_count + variant_count - shared
    overlap = TradeDecisionOverlap(
        status=OVERLAP_AVAILABLE if union else OVERLAP_NO_ENTRIES,
        baseline_entry_count=baseline_count,
        variant_entry_count=variant_count,
        shared_entry_count=shared,
        baseline_only_entry_count=baseline_count - shared,
        variant_only_entry_count=variant_count - shared,
        overlap_fraction=_overlap_fraction(shared, union),
    )
    _validate_overlap(overlap)
    return overlap


def _change(
    baseline: AblationMetrics, variant: AblationMetrics
) -> AblationChange:
    expectancy, expectancy_status = _difference(
        baseline.outcome.closed_trade_expectancy,
        variant.outcome.closed_trade_expectancy,
    )
    mean_r, mean_r_status = _difference(
        baseline.outcome.mean_r_multiple, variant.outcome.mean_r_multiple
    )
    drawdown, drawdown_status = _difference(
        baseline.max_drawdown_fraction
        if baseline.max_drawdown_status == DRAWDOWN_AVAILABLE
        else None,
        variant.max_drawdown_fraction
        if variant.max_drawdown_status == DRAWDOWN_AVAILABLE
        else None,
    )
    change = AblationChange(
        trade_count_change=(
            variant.outcome.trade_count - baseline.outcome.trade_count
        ),
        closed_trade_count_change=(
            variant.outcome.closed_trade_count - baseline.outcome.closed_trade_count
        ),
        mean_return_fraction_change=_subtract(
            baseline.outcome.mean_return_fraction,
            variant.outcome.mean_return_fraction,
        ),
        closed_trade_expectancy_change=expectancy,
        expectancy_change_status=expectancy_status,
        mean_r_multiple_change=mean_r,
        mean_r_change_status=mean_r_status,
        max_drawdown_change=drawdown,
        drawdown_change_status=drawdown_status,
    )
    _validate_change(change)
    return change


def _difference(
    baseline: Decimal | None, variant: Decimal | None
) -> tuple[Decimal | None, str]:
    """Subtract two metrics, declaring rather than zero-filling absent ones."""

    if baseline is None and variant is None:
        return None, CHANGE_BOTH_UNDEFINED
    if baseline is None:
        return None, CHANGE_BASELINE_UNDEFINED
    if variant is None:
        return None, CHANGE_VARIANT_UNDEFINED
    return _subtract(baseline, variant), CHANGE_AVAILABLE


def _reason_codes(
    results: tuple[AblationResult, ...], mechanically_clean: bool
) -> tuple[str, ...]:
    codes = [
        "COMPONENT_ABLATION_SINGLE_COMPONENT_REMOVED",
        "COMPONENT_ABLATION_REMAINING_WEIGHTS_RENORMALIZED",
        "COMPONENT_ABLATION_UNRELATED_RULES_UNCHANGED",
        "COMPONENT_ABLATION_OUT_OF_SAMPLE",
        "COMPONENT_ABLATION_COMPARABLE_RUNS",
        "COMPONENT_ABLATION_TRADE_DECISION_OVERLAP_REPORTED",
        "COMPONENT_ABLATION_EXPECTANCY_REPORTED",
        "COMPONENT_ABLATION_MEAN_R_REPORTED",
        "COMPONENT_ABLATION_DRAWDOWN_REPORTED",
    ]
    codes.append(
        "COMPONENT_ABLATION_MECHANICALLY_CLEAN"
        if mechanically_clean
        else "COMPONENT_ABLATION_MECHANICAL_NESTING_DETECTED"
    )
    counts = tuple(item.metrics.outcome.trade_count for item in results)
    if any(value == 0 for value in counts):
        codes.append("COMPONENT_ABLATION_VARIANTS_WITHOUT_TRADES")
    if all(value == 0 for value in counts):
        codes.append("COMPONENT_ABLATION_NO_TRADES")
    codes.extend(
        (
            "COMPONENT_ABLATION_RESEARCH_ONLY",
            "COMPONENT_ABLATION_BTC_193_PROMOTION_REQUIRED",
            "COMPONENT_ABLATION_COMPLETE",
        )
    )
    return tuple(codes)


def _validate_variant(variant: AblationVariant) -> None:
    _non_empty(variant.parameter_set_id, "parameter_set_id")
    _non_empty(variant.spec_id, "spec_id")
    _non_empty(variant.composite, "composite")
    _non_negative_integer(variant.ordinal, "ordinal")
    if not isinstance(variant.baseline, bool):
        raise ComponentAblationError("baseline must be a boolean")
    if variant.baseline != (variant.removed_component is None):
        raise ComponentAblationError(
            "exactly the baseline variant removes no component"
        )
    if not variant.weights:
        raise ComponentAblationError("a variant must retain weighted components")
    names = tuple(item.component for item in variant.weights)
    for item in variant.weights:
        item.as_record()
    if len(set(names)) != len(names):
        raise ComponentAblationError("variant components must be unique")
    if tuple(sorted(names)) != names:
        raise ComponentAblationError("variant components must be sorted by name")
    if variant.removed_component is not None:
        _non_empty(variant.removed_component, "removed_component")
        if variant.removed_component in names:
            raise ComponentAblationError(
                "an ablated component must not keep a weight"
            )
    total = _weight_total(variant.weights)
    if variant.weight_total != total:
        raise ComponentAblationError("weight_total does not match the weights")
    if abs(total - Decimal("1")) > ABLATION_WEIGHT_TOLERANCE:
        raise ComponentAblationError(
            "renormalized component weights must sum to one"
        )
    if not variant.parameter_paths:
        raise ComponentAblationError("a variant must declare its config paths")
    _string_tuple(variant.parameter_paths, "parameter_paths")
    _non_empty(
        variant.scoring_architecture_version, "scoring_architecture_version"
    )
    metadata = _string_mapping(variant.config_metadata, "config_metadata")
    if metadata.get("parameter_set_id") != variant.parameter_set_id:
        raise ComponentAblationError(
            "variant config_metadata must carry its own parameter_set_id"
        )


def _validate_metrics(metrics: AblationMetrics) -> None:
    if not isinstance(metrics.outcome, ThresholdSweepMetrics):
        raise ComponentAblationError("outcome must be a ThresholdSweepMetrics")
    metrics.outcome.as_record()
    if metrics.max_drawdown_status not in DRAWDOWN_STATUSES:
        raise ComponentAblationError(
            f"max_drawdown_status must be one of {DRAWDOWN_STATUSES}"
        )
    available = metrics.max_drawdown_status == DRAWDOWN_AVAILABLE
    if available != (metrics.max_drawdown_fraction is not None):
        raise ComponentAblationError(
            "a drawdown value is present exactly when the drawdown is available"
        )
    if metrics.max_drawdown_fraction is not None and (
        metrics.max_drawdown_fraction < 0
    ):
        raise ComponentAblationError("max_drawdown_fraction must be non-negative")


def _validate_overlap(overlap: TradeDecisionOverlap) -> None:
    if overlap.status not in OVERLAP_STATUSES:
        raise ComponentAblationError(f"status must be one of {OVERLAP_STATUSES}")
    for name in (
        "baseline_entry_count",
        "variant_entry_count",
        "shared_entry_count",
        "baseline_only_entry_count",
        "variant_only_entry_count",
    ):
        _non_negative_integer(getattr(overlap, name), name)
    if overlap.shared_entry_count > min(
        overlap.baseline_entry_count, overlap.variant_entry_count
    ):
        raise ComponentAblationError(
            "shared entries cannot exceed either run's entries"
        )
    if overlap.baseline_only_entry_count != (
        overlap.baseline_entry_count - overlap.shared_entry_count
    ):
        raise ComponentAblationError("baseline-only entries do not reconcile")
    if overlap.variant_only_entry_count != (
        overlap.variant_entry_count - overlap.shared_entry_count
    ):
        raise ComponentAblationError("variant-only entries do not reconcile")
    available = overlap.status == OVERLAP_AVAILABLE
    if available != (overlap.overlap_fraction is not None):
        raise ComponentAblationError(
            "an overlap fraction is present exactly when entries were observed"
        )
    if not available and (
        overlap.baseline_entry_count or overlap.variant_entry_count
    ):
        raise ComponentAblationError(
            "an overlap without entries cannot report entry counts"
        )
    if overlap.overlap_fraction is not None and not (
        Decimal("0") <= overlap.overlap_fraction <= Decimal("1")
    ):
        raise ComponentAblationError("overlap_fraction must fall in [0, 1]")


def _validate_change(change: AblationChange) -> None:
    for name in ("trade_count_change", "closed_trade_count_change"):
        value = getattr(change, name)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ComponentAblationError(f"{name} must be an integer")
    if not isinstance(change.mean_return_fraction_change, Decimal) or not (
        change.mean_return_fraction_change.is_finite()
    ):
        raise ComponentAblationError(
            "mean_return_fraction_change must be a finite Decimal"
        )
    pairs = (
        (
            "closed_trade_expectancy_change",
            change.closed_trade_expectancy_change,
            change.expectancy_change_status,
        ),
        (
            "mean_r_multiple_change",
            change.mean_r_multiple_change,
            change.mean_r_change_status,
        ),
        (
            "max_drawdown_change",
            change.max_drawdown_change,
            change.drawdown_change_status,
        ),
    )
    for name, value, status in pairs:
        if status not in CHANGE_STATUSES:
            raise ComponentAblationError(
                f"{name} status must be one of {CHANGE_STATUSES}"
            )
        if (status == CHANGE_AVAILABLE) != (value is not None):
            raise ComponentAblationError(
                f"{name} is present exactly when both runs defined the metric"
            )
        if value is not None and not value.is_finite():
            raise ComponentAblationError(f"{name} must be finite")


def _validate_spec(
    spec: ComponentAblationSpec, *, allow_empty_id: bool = False
) -> None:
    expected_versions = {
        "feature_id": COMPONENT_ABLATION_FEATURE_ID,
        "policy_version": COMPONENT_ABLATION_POLICY_VERSION,
        "weight_policy_version": ABLATION_WEIGHT_POLICY_VERSION,
        "isolation_policy_version": ABLATION_ISOLATION_POLICY_VERSION,
        "overlap_policy_version": ABLATION_OVERLAP_POLICY_VERSION,
        "metric_policy_version": ABLATION_METRIC_POLICY_VERSION,
        "drawdown_policy_version": ABLATION_DRAWDOWN_POLICY_VERSION,
        "promotion_policy_version": ABLATION_PROMOTION_POLICY_VERSION,
        "parameter_status": ABLATION_PARAMETER_STATUS,
    }
    for name, expected in expected_versions.items():
        if getattr(spec, name) != expected:
            raise ComponentAblationError(f"{name} must be {expected!r}")
    if not allow_empty_id:
        _non_empty(spec.spec_id, "spec_id")
    _non_empty(spec.composite, "composite")
    architecture = _non_empty(
        spec.scoring_architecture_version, "scoring_architecture_version"
    )
    if architecture not in ABLATION_ARCHITECTURES:
        raise ComponentAblationError(
            "scoring_architecture_version must name a declared BTC-129 architecture"
        )
    graph, contracts_version = ABLATION_ARCHITECTURES[architecture]
    if spec.contracts_version != contracts_version:
        raise ComponentAblationError(
            "contracts_version must match the declared scoring architecture"
        )
    if spec.composite not in graph:
        raise ComponentAblationError(
            "the composite must be declared by the scoring architecture"
        )
    if not spec.baseline_weights:
        raise ComponentAblationError("baseline weights are required")
    for item in spec.baseline_weights:
        item.as_record()
    names = tuple(item.component for item in spec.baseline_weights)
    if tuple(sorted(names)) != names or len(set(names)) != len(names):
        raise ComponentAblationError(
            "baseline components must be unique and sorted by name"
        )
    if names != tuple(sorted(graph[spec.composite])):
        raise ComponentAblationError(
            "baseline weights must be the composite's declared components"
        )
    for item in spec.baseline_weights:
        declared = _quantize(_weight(graph[spec.composite][item.component], "weight"))
        if item.weight != declared:
            raise ComponentAblationError(
                "baseline weights must match the declared scoring contract"
            )
    total = _weight_total(spec.baseline_weights)
    if abs(total - Decimal("1")) > ABLATION_WEIGHT_TOLERANCE:
        raise ComponentAblationError("baseline component weights must sum to one")
    components = _string_tuple(spec.ablated_components, "ablated_components")
    if not components:
        raise ComponentAblationError("at least one component must be ablated")
    if tuple(sorted(components)) != components or len(set(components)) != len(
        components
    ):
        raise ComponentAblationError(
            "ablated components must be unique and sorted by name"
        )
    if set(components) - set(names):
        raise ComponentAblationError(
            "ablated components must be declared components"
        )
    if len(names) < 2:
        raise ComponentAblationError(
            "ablation requires a composite with at least two components"
        )
    if not spec.parameter_paths:
        raise ComponentAblationError("the composite weight config paths are required")
    _string_tuple(spec.parameter_paths, "parameter_paths")
    metadata = threshold_config_metadata(spec.base_config_metadata)
    if metadata != dict(spec.base_config_metadata):
        raise ComponentAblationError("base_config_metadata is not canonical")
    validate_scoring_architecture(metadata["strategy_version"], architecture)


def _validate_comparability(
    validations: tuple[WalkForwardValidation, ...],
) -> None:
    if not validations:
        raise ComponentAblationError("an ablation study requires validations")
    first = comparable_run_signature(validations[0])
    for validation in validations[1:]:
        if comparable_run_signature(validation) != first:
            raise ComponentAblationError(
                "variant validations must share schedule, split, capital, costs, "
                "fitting procedure, and scoring-independent run assumptions"
            )


def _validate_report(report: ComponentAblationReport) -> None:
    if report.feature_id != COMPONENT_ABLATION_FEATURE_ID:
        raise ComponentAblationError(
            f"feature_id must be {COMPONENT_ABLATION_FEATURE_ID}"
        )
    if report.policy_version != COMPONENT_ABLATION_POLICY_VERSION:
        raise ComponentAblationError(
            f"policy_version must be {COMPONENT_ABLATION_POLICY_VERSION}"
        )
    report.spec.as_record()
    _non_empty(report.report_id, "report_id")
    if report.production_status != ABLATION_PRODUCTION_STATUS:
        raise ComponentAblationError(
            "component ablation evidence must remain research-only"
        )
    if report.promotion_ticket != ABLATION_PROMOTION_TICKET:
        raise ComponentAblationError(
            "component ablation evidence must require BTC-193 promotion"
        )
    expected = ablation_variants(report.spec)
    if tuple(item.variant for item in report.results) != expected:
        raise ComponentAblationError(
            "results must cover the baseline and every ablation, in order"
        )
    baselines = tuple(item for item in report.results if item.variant.baseline)
    if len(baselines) != 1 or report.results[0] is not baselines[0]:
        raise ComponentAblationError(
            "an ablation report needs exactly one leading baseline run"
        )
    for result in report.results:
        _validate_metrics(result.metrics)
        if result.variant.baseline:
            if result.overlap is not None or result.change is not None:
                raise ComponentAblationError(
                    "the baseline run cannot be compared against itself"
                )
            continue
        if result.overlap is None or result.change is None:
            raise ComponentAblationError(
                "every ablation must report its overlap and its changes"
            )
        _validate_overlap(result.overlap)
        _validate_change(result.change)
        if result.overlap.baseline_entry_count != sum(
            _entry_keys(report.baseline.validation).values()
        ):
            raise ComponentAblationError(
                "overlap baseline entries do not match the baseline run"
            )
    audit = _mapping(report.factor_overlap_audit, "factor_overlap_audit")
    if audit.get("composite") != report.spec.composite:
        raise ComponentAblationError(
            "the factor-overlap audit must cover the ablated composite"
        )
    if audit.get("contracts_version") != report.spec.contracts_version:
        raise ComponentAblationError(
            "the factor-overlap audit must match the declared contracts version"
        )
    if audit.get("mechanical_vs_empirical") != MECHANICAL_VS_EMPIRICAL_NOTE:
        raise ComponentAblationError(
            "the factor-overlap audit must keep the mechanical-versus-empirical note"
        )
    if not isinstance(audit.get("mechanically_clean"), bool):
        raise ComponentAblationError(
            "the factor-overlap audit must declare mechanical cleanliness"
        )
    if report.config_metadata != dict(report.spec.base_config_metadata):
        raise ComponentAblationError(
            "report config_metadata must match the declared base identity"
        )
    _validate_reason_codes(report.reason_codes)
    if report.report_id != _report_id(report):
        raise ComponentAblationError(
            "component ablation report does not match report_id"
        )


def _validate_reason_codes(codes: tuple[str, ...]) -> None:
    if not codes:
        raise ComponentAblationError("reason codes are required")
    if len(set(codes)) != len(codes):
        raise ComponentAblationError("reason codes must be unique")
    unknown = sorted(set(codes) - set(COMPONENT_ABLATION_REASON_CODES))
    if unknown:
        raise ComponentAblationError(
            "unknown ablation reason codes: " + ", ".join(unknown)
        )
    ordered = tuple(
        code for code in COMPONENT_ABLATION_REASON_CODES if code in set(codes)
    )
    if ordered != codes:
        raise ComponentAblationError("reason codes must follow the declared order")
    if codes[-1] != "COMPONENT_ABLATION_COMPLETE":
        raise ComponentAblationError(
            "an ablation report must end with COMPONENT_ABLATION_COMPLETE"
        )


def _spec_payload(spec: ComponentAblationSpec) -> dict[str, Any]:
    return {
        "feature_id": spec.feature_id,
        "policy_version": spec.policy_version,
        "weight_policy_version": spec.weight_policy_version,
        "isolation_policy_version": spec.isolation_policy_version,
        "overlap_policy_version": spec.overlap_policy_version,
        "metric_policy_version": spec.metric_policy_version,
        "drawdown_policy_version": spec.drawdown_policy_version,
        "promotion_policy_version": spec.promotion_policy_version,
        "parameter_status": spec.parameter_status,
        "composite": spec.composite,
        "contracts_version": spec.contracts_version,
        "baseline_weights": [item.as_record() for item in spec.baseline_weights],
        "ablated_components": list(spec.ablated_components),
        "parameter_paths": list(spec.parameter_paths),
        "scoring_architecture_version": spec.scoring_architecture_version,
        "base_config_metadata": dict(spec.base_config_metadata),
    }


def _report_id(report: ComponentAblationReport) -> str:
    return _digest(
        {
            "feature_id": report.feature_id,
            "policy_version": report.policy_version,
            "spec_id": report.spec.spec_id,
            "validation_ids": [
                item.validation.validation_id for item in report.results
            ],
        }
    )


def _report_payload(report: ComponentAblationReport) -> dict[str, Any]:
    return {
        "feature_id": report.feature_id,
        "policy_version": report.policy_version,
        "report_id": report.report_id,
        "spec": report.spec.as_record(),
        "results": [item.as_record() for item in report.results],
        "factor_overlap_audit": report.factor_overlap_audit,
        "production_status": report.production_status,
        "promotion_ticket": report.promotion_ticket,
        "config_metadata": dict(report.config_metadata),
        "reason_codes": list(report.reason_codes),
    }


def _spec_from_record(record: Mapping[str, Any]) -> ComponentAblationSpec:
    spec = ComponentAblationSpec(
        feature_id=_string(record.get("feature_id"), "feature_id"),
        policy_version=_string(record.get("policy_version"), "policy_version"),
        weight_policy_version=_string(
            record.get("weight_policy_version"), "weight_policy_version"
        ),
        isolation_policy_version=_string(
            record.get("isolation_policy_version"), "isolation_policy_version"
        ),
        overlap_policy_version=_string(
            record.get("overlap_policy_version"), "overlap_policy_version"
        ),
        metric_policy_version=_string(
            record.get("metric_policy_version"), "metric_policy_version"
        ),
        drawdown_policy_version=_string(
            record.get("drawdown_policy_version"), "drawdown_policy_version"
        ),
        promotion_policy_version=_string(
            record.get("promotion_policy_version"), "promotion_policy_version"
        ),
        parameter_status=_string(
            record.get("parameter_status"), "parameter_status"
        ),
        spec_id=_string(record.get("spec_id"), "spec_id"),
        composite=_string(record.get("composite"), "composite"),
        contracts_version=_string(
            record.get("contracts_version"), "contracts_version"
        ),
        baseline_weights=tuple(
            _weight_from_record(_mapping(item, "component_weight"))
            for item in _sequence(record.get("baseline_weights"), "baseline_weights")
        ),
        ablated_components=_string_tuple(
            record.get("ablated_components"), "ablated_components"
        ),
        parameter_paths=_string_tuple(
            record.get("parameter_paths"), "parameter_paths"
        ),
        scoring_architecture_version=_string(
            record.get("scoring_architecture_version"),
            "scoring_architecture_version",
        ),
        base_config_metadata=_string_mapping(
            record.get("base_config_metadata"), "base_config_metadata"
        ),
    )
    if spec.as_record() != dict(record):
        raise ComponentAblationError(
            "record does not match the reconstructed ablation specification"
        )
    return spec


def _weight_from_record(record: Mapping[str, Any]) -> ComponentWeight:
    weight = ComponentWeight(
        component=_string(record.get("component"), "component"),
        weight=_decimal_from_record(record.get("weight"), "weight"),
    )
    if weight.as_record() != dict(record):
        raise ComponentAblationError("record does not match a component weight")
    return weight


def _weight(value: Any, name: str) -> Decimal:
    if isinstance(value, Decimal):
        resolved = value
    elif isinstance(value, int) and not isinstance(value, bool):
        resolved = Decimal(value)
    elif isinstance(value, str):
        resolved = Decimal(value)
    else:
        raise ComponentAblationError(f"{name} must be a Decimal weight")
    if not resolved.is_finite() or resolved < 0:
        raise ComponentAblationError(f"{name} must be finite and non-negative")
    return resolved


def _weight_total(weights: Sequence[ComponentWeight]) -> Decimal:
    """Sum component weights in the pinned context the weights were built in."""

    with localcontext(Context(prec=ABLATION_DECIMAL_PRECISION)):
        return sum((item.weight for item in weights), Decimal("0"))


def _overlap_fraction(shared: int, union: int) -> Decimal | None:
    if not union:
        return None
    with localcontext(Context(prec=ABLATION_DECIMAL_PRECISION)):
        return _quantize(Decimal(shared) / Decimal(union))


def _subtract(baseline: Decimal, variant: Decimal) -> Decimal:
    with localcontext(Context(prec=ABLATION_DECIMAL_PRECISION)):
        return _quantize(variant - baseline)


def _quantize(value: Decimal) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ComponentAblationError("ablation metrics must be finite Decimals")
    with localcontext(Context(prec=ABLATION_DECIMAL_PRECISION)):
        return value.quantize(ABLATION_METRIC_EXPONENT, rounding=ROUND_HALF_EVEN)


def _optional_decimal(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _non_empty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ComponentAblationError(f"{name} must be a non-empty string")
    return value


def _string(value: Any, name: str) -> str:
    return _non_empty(value, name)


def _non_negative_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ComponentAblationError(f"{name} must be a non-negative integer")
    return value


def _decimal_from_record(value: Any, name: str) -> Decimal:
    if not isinstance(value, str):
        raise ComponentAblationError(f"{name} must be a decimal string")
    try:
        result = Decimal(value)
    except ArithmeticError as error:
        raise ComponentAblationError(f"{name} must be a decimal string") from error
    if not result.is_finite():
        raise ComponentAblationError(f"{name} must be finite")
    return result


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ComponentAblationError(f"{name} must be a mapping")
    return value


def _string_mapping(value: Any, name: str) -> dict[str, str]:
    source = _mapping(value, name)
    return {
        _non_empty(key, f"{name} key"): _non_empty(item, f"{name} value")
        for key, item in source.items()
    }


def _sequence(value: Any, name: str) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ComponentAblationError(f"{name} must be a sequence")
    return tuple(value)


def _string_tuple(value: Any, name: str) -> tuple[str, ...]:
    return tuple(_non_empty(item, name) for item in _sequence(value, name))


def _digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "ABLATION_ARCHITECTURES",
    "ABLATION_DRAWDOWN_POLICY_VERSION",
    "ABLATION_ISOLATION_POLICY_VERSION",
    "ABLATION_METRIC_POLICY_VERSION",
    "ABLATION_OVERLAP_POLICY_VERSION",
    "ABLATION_PARAMETER_STATUS",
    "ABLATION_PRODUCTION_STATUS",
    "ABLATION_PROMOTION_POLICY_VERSION",
    "ABLATION_PROMOTION_TICKET",
    "ABLATION_WEIGHT_POLICY_VERSION",
    "CHANGE_AVAILABLE",
    "CHANGE_BASELINE_UNDEFINED",
    "CHANGE_BOTH_UNDEFINED",
    "CHANGE_STATUSES",
    "CHANGE_VARIANT_UNDEFINED",
    "COMPONENT_ABLATION_FEATURE_ID",
    "COMPONENT_ABLATION_POLICY_VERSION",
    "COMPONENT_ABLATION_REASON_CODES",
    "OVERLAP_AVAILABLE",
    "OVERLAP_NO_ENTRIES",
    "OVERLAP_STATUSES",
    "AblationChange",
    "AblationEvaluator",
    "AblationMetrics",
    "AblationResult",
    "AblationVariant",
    "ComponentAblationError",
    "ComponentAblationReport",
    "ComponentAblationSpec",
    "ComponentWeight",
    "TradeDecisionOverlap",
    "ablation_variants",
    "component_ablation_spec",
    "restore_component_ablation_report",
    "run_component_ablation",
]
