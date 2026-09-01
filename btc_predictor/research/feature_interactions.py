"""Point-in-time feature interaction research (BTC-186).

An interaction is useful only if it adds information beyond the component
features that form it.  This module therefore compares two nested models in
each BTC-182 walk-forward fold:

``target ~ intercept + component main effects``

and

``target ~ intercept + component main effects + component product``.

Features, the product term, and the target are standardized from the training
rows of that fold only.  The interaction coefficient is consequently a
scale-free effect size, while the change in out-of-sample R-squared measures
incremental predictive information.  Training labels must have become
available by the first test timestamp.  Test labels are used only for
retrospective evaluation.

The same calculation is emitted globally and for every observed regime and
setup.  Missing values are complete-case excluded and are never converted to
zero.  Results are research evidence only; this module has no strategy or
configuration mutation path and records BTC-193 as the required promotion
boundary.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

import numpy as np

from btc_predictor.backtest.walk_forward import (
    WALK_FORWARD_SPLIT_POLICY_VERSION,
    WalkForwardPlan,
    WalkForwardWindow,
    restore_walk_forward_plan,
    walk_forward_plan,
    walk_forward_windows,
)
from btc_predictor.data import require_utc_datetime
from btc_predictor.research.feature_matrix import (
    ForwardTargetMatrix,
    PointInTimeFeatureMatrix,
)


FEATURE_INTERACTION_FEATURE_ID = "FEATURE_INTERACTION_RESEARCH"
FEATURE_INTERACTION_POLICY_VERSION = "FEATURE_INTERACTION_RESEARCH_V1"
INTERACTION_ESTIMATION_POLICY_VERSION = (
    "WALK_FORWARD_STANDARDIZED_OLS_INCREMENTAL_OOS_R2_V1"
)
INTERACTION_MISSING_VALUE_POLICY_VERSION = "COMPLETE_CASE_NO_ZERO_FILL_V1"
INTERACTION_CONTEXT_POLICY_VERSION = "DECISION_TIME_REGIME_SETUP_CONTEXT_V1"
INTERACTION_TARGET_AVAILABILITY_POLICY_VERSION = (
    "TRAIN_LABEL_AVAILABLE_BY_TEST_START_V1"
)
INTERACTION_PROMOTION_POLICY_VERSION = "BTC_193_REQUIRED_V1"
INTERACTION_PRODUCTION_STATUS = "RESEARCH_ONLY_NOT_PRODUCTION"
INTERACTION_PROMOTION_TICKET = "BTC-193"
INTERACTION_METRIC_EXPONENT = Decimal("1E-12")

GLOBAL_SCOPE = "GLOBAL"
REGIME_SCOPE = "REGIME"
SETUP_SCOPE = "SETUP"
INTERACTION_SCOPES = (GLOBAL_SCOPE, REGIME_SCOPE, SETUP_SCOPE)
GLOBAL_SEGMENT = "ALL"

ESTIMATE_AVAILABLE = "AVAILABLE"
ESTIMATE_INSUFFICIENT_TRAIN = "INSUFFICIENT_TRAIN_SAMPLES"
ESTIMATE_INSUFFICIENT_TEST = "INSUFFICIENT_TEST_SAMPLES"
ESTIMATE_ZERO_VARIANCE_FEATURE = "ZERO_VARIANCE_FEATURE"
ESTIMATE_ZERO_VARIANCE_TARGET = "ZERO_VARIANCE_TARGET"
ESTIMATE_RANK_DEFICIENT = "RANK_DEFICIENT_DESIGN"
ESTIMATE_STATUSES = (
    ESTIMATE_AVAILABLE,
    ESTIMATE_INSUFFICIENT_TRAIN,
    ESTIMATE_INSUFFICIENT_TEST,
    ESTIMATE_ZERO_VARIANCE_FEATURE,
    ESTIMATE_ZERO_VARIANCE_TARGET,
    ESTIMATE_RANK_DEFICIENT,
)

INTERACTION_REASON_CODES = (
    "FEATURE_INTERACTION_POINT_IN_TIME_FEATURES",
    "FEATURE_INTERACTION_FORWARD_TARGET_SEPARATED",
    "FEATURE_INTERACTION_TRAIN_LABEL_AVAILABILITY_ENFORCED",
    "FEATURE_INTERACTION_COMPLETE_CASES",
    "FEATURE_INTERACTION_MAIN_EFFECTS_CONTROLLED",
    "FEATURE_INTERACTION_OUT_OF_SAMPLE",
    "FEATURE_INTERACTION_GLOBAL",
    "FEATURE_INTERACTION_REGIME_CONDITIONED",
    "FEATURE_INTERACTION_SETUP_CONDITIONED",
    "FEATURE_INTERACTION_RESEARCH_ONLY",
    "FEATURE_INTERACTION_BTC_193_PROMOTION_REQUIRED",
    "FEATURE_INTERACTION_COMPLETE",
)


@dataclass(frozen=True)
class InteractionDefinition:
    """One explicit candidate product and its point-in-time feature bindings."""

    interaction_id: str
    display_name: str
    feature_names: tuple[str, ...]

    @property
    def formula(self) -> str:
        return " * ".join(f"TRAIN_Z({name})" for name in self.feature_names)

    def as_record(self) -> dict[str, Any]:
        _validate_definition(self)
        return {
            "interaction_id": self.interaction_id,
            "display_name": self.display_name,
            "feature_names": list(self.feature_names),
            "formula": self.formula,
        }


CANDIDATE_INTERACTIONS = (
    InteractionDefinition(
        interaction_id="TREND_X_FLOW",
        display_name="Trend x Flow",
        feature_names=("TREND_SCORE", "FLOW_SCORE"),
    ),
    InteractionDefinition(
        interaction_id="FLOW_X_POSITIONING",
        display_name="Flow x Positioning",
        feature_names=("FLOW_SCORE", "POSITIONING_SCORE"),
    ),
    InteractionDefinition(
        interaction_id="POSITIONING_X_STRUCTURE",
        display_name="Positioning x Structure",
        feature_names=("POSITIONING_SCORE", "STRUCTURE_SCORE"),
    ),
    InteractionDefinition(
        interaction_id="TREND_X_VOLATILITY",
        display_name="Trend x Volatility",
        feature_names=("TREND_SCORE", "VOLATILITY_SCORE"),
    ),
    # These names intentionally describe inputs rather than deriving them from
    # FUNDING_HEALTH/OI_GROWTH_HEALTH/FLOW_ACCEL.  The Rulebook calls for
    # improvement/reset concepts, and BTC-186 must not silently invent their
    # lag or direction semantics.  A source matrix can bind versioned,
    # point-in-time columns with these names explicitly.
    InteractionDefinition(
        interaction_id=(
            "FUNDING_RESET_X_OI_DELEVERAGING_X_FLOW_IMPROVEMENT"
        ),
        display_name="FundingReset x OIDeleveraging x FlowImprovement",
        feature_names=(
            "FUNDING_RESET",
            "OI_DELEVERAGING",
            "FLOW_IMPROVEMENT",
        ),
    ),
)


@dataclass(frozen=True)
class InteractionContext:
    """Regime and setup evidence known at one feature-matrix decision time."""

    decision_timestamp: datetime
    evidence_available_at: datetime
    regime: str
    setup: str
    source_id: str

    def __post_init__(self) -> None:
        decision = require_utc_datetime(
            self.decision_timestamp, field_name="decision_timestamp"
        )
        available = require_utc_datetime(
            self.evidence_available_at, field_name="evidence_available_at"
        )
        if available > decision:
            raise ValueError(
                "interaction context evidence_available_at must be <= decision_timestamp"
            )
        _non_empty(self.regime, "regime")
        _non_empty(self.setup, "setup")
        _non_empty(self.source_id, "source_id")
        object.__setattr__(self, "decision_timestamp", decision)
        object.__setattr__(self, "evidence_available_at", available)

    def as_record(self) -> dict[str, str]:
        return {
            "decision_timestamp": self.decision_timestamp.isoformat(),
            "evidence_available_at": self.evidence_available_at.isoformat(),
            "regime": self.regime,
            "setup": self.setup,
            "source_id": self.source_id,
        }


@dataclass(frozen=True)
class InteractionResearchSpec:
    """Frozen statistical question and walk-forward split."""

    feature_id: str
    policy_version: str
    estimation_policy_version: str
    missing_value_policy_version: str
    context_policy_version: str
    target_availability_policy_version: str
    promotion_policy_version: str
    spec_id: str
    target_name: str
    interactions: tuple[InteractionDefinition, ...]
    plan: WalkForwardPlan
    minimum_train_samples: int
    minimum_test_samples: int

    def as_record(self) -> dict[str, Any]:
        _validate_spec(self)
        payload = _spec_payload(self)
        if _digest(payload) != self.spec_id:
            raise ValueError("feature interaction specification does not match spec_id")
        return {**payload, "spec_id": self.spec_id}


@dataclass(frozen=True)
class InteractionFoldEstimate:
    """One segment's nested-model comparison in one walk-forward fold."""

    fold_number: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    train_sample_size: int
    test_sample_size: int
    status: str
    effect_size: Decimal | None
    baseline_test_mse: Decimal | None
    interaction_test_mse: Decimal | None
    incremental_oos_r2: Decimal | None

    def as_record(self) -> dict[str, Any]:
        _validate_fold_estimate(self)
        return {
            "fold_number": self.fold_number,
            "train_start": self.train_start.isoformat(),
            "train_end": self.train_end.isoformat(),
            "test_start": self.test_start.isoformat(),
            "test_end": self.test_end.isoformat(),
            "train_sample_size": self.train_sample_size,
            "test_sample_size": self.test_sample_size,
            "status": self.status,
            "effect_size": _optional_decimal(self.effect_size),
            "baseline_test_mse": _optional_decimal(self.baseline_test_mse),
            "interaction_test_mse": _optional_decimal(
                self.interaction_test_mse
            ),
            "incremental_oos_r2": _optional_decimal(self.incremental_oos_r2),
        }


@dataclass(frozen=True)
class InteractionEffect:
    """Effect size and cross-fold stability for one conditioning segment."""

    scope: str
    segment: str
    sample_size: int
    tested_sample_size: int
    eligible_fold_count: int
    effect_size: Decimal | None
    effect_size_standard_deviation: Decimal | None
    effect_sign_consistency: Decimal | None
    mean_incremental_oos_r2: Decimal | None
    positive_incremental_fold_fraction: Decimal | None
    folds: tuple[InteractionFoldEstimate, ...]

    def as_record(self) -> dict[str, Any]:
        _validate_effect(self)
        return {
            "scope": self.scope,
            "segment": self.segment,
            "sample_size": self.sample_size,
            "tested_sample_size": self.tested_sample_size,
            "eligible_fold_count": self.eligible_fold_count,
            "effect_size": _optional_decimal(self.effect_size),
            "effect_size_standard_deviation": _optional_decimal(
                self.effect_size_standard_deviation
            ),
            "effect_sign_consistency": _optional_decimal(
                self.effect_sign_consistency
            ),
            "mean_incremental_oos_r2": _optional_decimal(
                self.mean_incremental_oos_r2
            ),
            "positive_incremental_fold_fraction": _optional_decimal(
                self.positive_incremental_fold_fraction
            ),
            "folds": [fold.as_record() for fold in self.folds],
        }


@dataclass(frozen=True)
class InteractionAnalysis:
    """All global and conditioned estimates for one interaction."""

    definition: InteractionDefinition
    effects: tuple[InteractionEffect, ...]

    def effect(self, scope: str, segment: str = GLOBAL_SEGMENT) -> InteractionEffect:
        for item in self.effects:
            if item.scope == scope and item.segment == segment:
                return item
        raise KeyError((scope, segment))

    def as_record(self) -> dict[str, Any]:
        _validate_analysis(self)
        return {
            "definition": self.definition.as_record(),
            "effects": [effect.as_record() for effect in self.effects],
        }


@dataclass(frozen=True)
class FeatureInteractionReport:
    """Replayable, research-only evidence for the BTC-186 candidates."""

    report_id: str
    evidence_digest: str
    spec: InteractionResearchSpec
    feature_definition: dict[str, Any]
    target_definition: dict[str, Any]
    feature_definition_fingerprint: str
    target_definition_fingerprint: str
    input_digest: str
    context_digest: str
    production_status: str
    promotion_ticket: str
    analyses: tuple[InteractionAnalysis, ...]
    reason_codes: tuple[str, ...]

    def analysis(self, interaction_id: str) -> InteractionAnalysis:
        for item in self.analyses:
            if item.definition.interaction_id == interaction_id:
                return item
        raise KeyError(interaction_id)

    def as_record(self) -> dict[str, Any]:
        _validate_report(self)
        payload = _report_payload(self)
        if _digest(payload) != self.evidence_digest:
            raise ValueError("feature interaction evidence does not match digest")
        return {**payload, "evidence_digest": self.evidence_digest}


def interaction_research_spec(
    *,
    target_name: str,
    interactions: Sequence[InteractionDefinition] = CANDIDATE_INTERACTIONS,
    plan: WalkForwardPlan | None = None,
    minimum_train_samples: int = 8,
    minimum_test_samples: int = 2,
) -> InteractionResearchSpec:
    """Create a deterministic BTC-186 research specification."""

    definitions = tuple(interactions)
    resolved = plan if plan is not None else walk_forward_plan()
    spec = InteractionResearchSpec(
        feature_id=FEATURE_INTERACTION_FEATURE_ID,
        policy_version=FEATURE_INTERACTION_POLICY_VERSION,
        estimation_policy_version=INTERACTION_ESTIMATION_POLICY_VERSION,
        missing_value_policy_version=INTERACTION_MISSING_VALUE_POLICY_VERSION,
        context_policy_version=INTERACTION_CONTEXT_POLICY_VERSION,
        target_availability_policy_version=(
            INTERACTION_TARGET_AVAILABILITY_POLICY_VERSION
        ),
        promotion_policy_version=INTERACTION_PROMOTION_POLICY_VERSION,
        spec_id="",
        target_name=target_name,
        interactions=definitions,
        plan=resolved,
        minimum_train_samples=minimum_train_samples,
        minimum_test_samples=minimum_test_samples,
    )
    _validate_spec(spec, allow_empty_id=True)
    return replace(spec, spec_id=_digest(_spec_payload(spec)))


def run_feature_interaction_research(
    features: PointInTimeFeatureMatrix,
    targets: ForwardTargetMatrix,
    contexts: Sequence[InteractionContext],
    *,
    spec: InteractionResearchSpec,
) -> FeatureInteractionReport:
    """Evaluate all declared interactions globally and by regime/setup."""

    if not isinstance(features, PointInTimeFeatureMatrix):
        raise TypeError("features must be a PointInTimeFeatureMatrix")
    if not isinstance(targets, ForwardTargetMatrix):
        raise TypeError("targets must be a ForwardTargetMatrix")
    if not isinstance(spec, InteractionResearchSpec):
        raise TypeError("spec must be an InteractionResearchSpec")
    spec.as_record()
    _validate_inputs(features, targets, contexts, spec)
    ordered_contexts = tuple(contexts)
    windows = walk_forward_windows(features.decision_timestamps, plan=spec.plan)
    target_column = targets.definition.target_names.index(spec.target_name)
    target_values = targets.values[:, target_column]
    target_available_ats = tuple(
        row[target_column] for row in targets.available_ats
    )
    regimes = tuple(sorted({item.regime for item in ordered_contexts}))
    setups = tuple(sorted({item.setup for item in ordered_contexts}))
    segments = (
        (GLOBAL_SCOPE, GLOBAL_SEGMENT, np.ones(len(ordered_contexts), dtype=bool)),
        *(
            (
                REGIME_SCOPE,
                regime,
                np.asarray(
                    [item.regime == regime for item in ordered_contexts], dtype=bool
                ),
            )
            for regime in regimes
        ),
        *(
            (
                SETUP_SCOPE,
                setup,
                np.asarray(
                    [item.setup == setup for item in ordered_contexts], dtype=bool
                ),
            )
            for setup in setups
        ),
    )
    feature_indexes = {
        name: index for index, name in enumerate(features.definition.feature_names)
    }
    analyses = tuple(
        InteractionAnalysis(
            definition=definition,
            effects=tuple(
                _effect(
                    scope=scope,
                    segment=segment,
                    segment_mask=segment_mask,
                    definition=definition,
                    feature_indexes=feature_indexes,
                    feature_values=features.values,
                    target_values=target_values,
                    target_available_ats=target_available_ats,
                    windows=windows,
                    spec=spec,
                )
                for scope, segment, segment_mask in segments
            ),
        )
        for definition in spec.interactions
    )
    context_records = [item.as_record() for item in ordered_contexts]
    context_digest = _digest({"contexts": context_records})
    input_digest = _digest(
        {
            "features": features.as_record(),
            "targets": targets.as_record(),
            "contexts": context_records,
        }
    )
    report = FeatureInteractionReport(
        report_id="",
        evidence_digest="",
        spec=spec,
        feature_definition=features.definition.as_record(),
        target_definition=targets.definition.as_record(),
        feature_definition_fingerprint=features.definition.fingerprint,
        target_definition_fingerprint=targets.definition.fingerprint,
        input_digest=input_digest,
        context_digest=context_digest,
        production_status=INTERACTION_PRODUCTION_STATUS,
        promotion_ticket=INTERACTION_PROMOTION_TICKET,
        analyses=analyses,
        reason_codes=INTERACTION_REASON_CODES,
    )
    report = replace(report, report_id=_report_id(report))
    _validate_report(report)
    return replace(report, evidence_digest=_digest(_report_payload(report)))


def restore_feature_interaction_report(
    record: Mapping[str, Any],
) -> FeatureInteractionReport:
    """Restore persisted BTC-186 evidence and reject drift or tampering."""

    source = _mapping(record, "record")
    spec = _spec_from_record(_mapping(source.get("spec"), "spec"))
    analyses = tuple(
        _analysis_from_record(_mapping(item, "analysis"))
        for item in _sequence(source.get("analyses"), "analyses")
    )
    report = FeatureInteractionReport(
        report_id=_string(source.get("report_id"), "report_id"),
        evidence_digest=_string(source.get("evidence_digest"), "evidence_digest"),
        spec=spec,
        feature_definition=dict(
            _mapping(source.get("feature_definition"), "feature_definition")
        ),
        target_definition=dict(
            _mapping(source.get("target_definition"), "target_definition")
        ),
        feature_definition_fingerprint=_string(
            source.get("feature_definition_fingerprint"),
            "feature_definition_fingerprint",
        ),
        target_definition_fingerprint=_string(
            source.get("target_definition_fingerprint"),
            "target_definition_fingerprint",
        ),
        input_digest=_string(source.get("input_digest"), "input_digest"),
        context_digest=_string(source.get("context_digest"), "context_digest"),
        production_status=_string(
            source.get("production_status"), "production_status"
        ),
        promotion_ticket=_string(source.get("promotion_ticket"), "promotion_ticket"),
        analyses=analyses,
        reason_codes=_string_tuple(source.get("reason_codes"), "reason_codes"),
    )
    if report.as_record() != dict(source):
        raise ValueError("record does not match reconstructed feature interactions")
    return report


def _effect(
    *,
    scope: str,
    segment: str,
    segment_mask: np.ndarray[Any, np.dtype[np.bool_]],
    definition: InteractionDefinition,
    feature_indexes: Mapping[str, int],
    feature_values: np.ndarray[Any, np.dtype[np.float64]],
    target_values: np.ndarray[Any, np.dtype[np.float64]],
    target_available_ats: tuple[Any, ...],
    windows: tuple[WalkForwardWindow, ...],
    spec: InteractionResearchSpec,
) -> InteractionEffect:
    indexes = [feature_indexes[name] for name in definition.feature_names]
    components = feature_values[:, indexes]
    complete = segment_mask & np.all(np.isfinite(components), axis=1) & np.isfinite(
        target_values
    )
    folds = tuple(
        _fold_estimate(
            window=window,
            components=components,
            target_values=target_values,
            target_available_ats=target_available_ats,
            complete=complete,
            spec=spec,
        )
        for window in windows
    )
    available = tuple(item for item in folds if item.status == ESTIMATE_AVAILABLE)
    weights = tuple(item.test_sample_size for item in available)
    effects = tuple(item.effect_size for item in available)
    assert all(item is not None for item in effects)
    effect_size = _weighted_mean(effects, weights)
    effect_std = _population_std(effects) if len(effects) >= 2 else None
    sign_consistency = _sign_consistency(effects, effect_size)
    r2_rows = tuple(
        (item.incremental_oos_r2, item.test_sample_size)
        for item in available
        if item.incremental_oos_r2 is not None
    )
    mean_r2 = _weighted_mean(
        tuple(item[0] for item in r2_rows),
        tuple(item[1] for item in r2_rows),
    )
    positive_fraction = (
        None
        if not r2_rows
        else _metric(
            sum(1 for value, _ in r2_rows if value is not None and value > 0)
            / len(r2_rows)
        )
    )
    effect = InteractionEffect(
        scope=scope,
        segment=segment,
        sample_size=int(np.count_nonzero(complete)),
        tested_sample_size=sum(item.test_sample_size for item in available),
        eligible_fold_count=len(available),
        effect_size=effect_size,
        effect_size_standard_deviation=effect_std,
        effect_sign_consistency=sign_consistency,
        mean_incremental_oos_r2=mean_r2,
        positive_incremental_fold_fraction=positive_fraction,
        folds=folds,
    )
    _validate_effect(effect)
    return effect


def _fold_estimate(
    *,
    window: WalkForwardWindow,
    components: np.ndarray[Any, np.dtype[np.float64]],
    target_values: np.ndarray[Any, np.dtype[np.float64]],
    target_available_ats: tuple[Any, ...],
    complete: np.ndarray[Any, np.dtype[np.bool_]],
    spec: InteractionResearchSpec,
) -> InteractionFoldEstimate:
    train_positions = np.arange(window.train_start_index, window.train_stop_index)
    test_positions = np.arange(window.test_start_index, window.test_stop_index)
    train = tuple(
        int(index)
        for index in train_positions
        if complete[index]
        and target_available_ats[index] is not None
        and target_available_ats[index] <= window.test_start
    )
    test = tuple(int(index) for index in test_positions if complete[index])
    base = {
        "fold_number": window.fold_number,
        "train_start": window.train_start,
        "train_end": window.train_end,
        "test_start": window.test_start,
        "test_end": window.test_end,
        "train_sample_size": len(train),
        "test_sample_size": len(test),
    }
    if len(train) < spec.minimum_train_samples:
        return InteractionFoldEstimate(
            **base,
            status=ESTIMATE_INSUFFICIENT_TRAIN,
            effect_size=None,
            baseline_test_mse=None,
            interaction_test_mse=None,
            incremental_oos_r2=None,
        )
    if len(test) < spec.minimum_test_samples:
        return InteractionFoldEstimate(
            **base,
            status=ESTIMATE_INSUFFICIENT_TEST,
            effect_size=None,
            baseline_test_mse=None,
            interaction_test_mse=None,
            incremental_oos_r2=None,
        )
    x_train = components[list(train), :]
    x_test = components[list(test), :]
    x_mean = np.mean(x_train, axis=0)
    x_scale = np.std(x_train, axis=0)
    if np.any(x_scale <= 0) or not np.all(np.isfinite(x_scale)):
        return _unavailable_fold(base, ESTIMATE_ZERO_VARIANCE_FEATURE)
    z_train = (x_train - x_mean) / x_scale
    z_test = (x_test - x_mean) / x_scale
    product_train = np.prod(z_train, axis=1)
    product_test = np.prod(z_test, axis=1)
    product_mean = float(np.mean(product_train))
    product_scale = float(np.std(product_train))
    if product_scale <= 0 or not np.isfinite(product_scale):
        return _unavailable_fold(base, ESTIMATE_ZERO_VARIANCE_FEATURE)
    interaction_train = (product_train - product_mean) / product_scale
    interaction_test = (product_test - product_mean) / product_scale
    y_train = target_values[list(train)]
    y_test = target_values[list(test)]
    y_mean = float(np.mean(y_train))
    y_scale = float(np.std(y_train))
    if y_scale <= 0 or not np.isfinite(y_scale):
        return _unavailable_fold(base, ESTIMATE_ZERO_VARIANCE_TARGET)
    zy_train = (y_train - y_mean) / y_scale
    zy_test = (y_test - y_mean) / y_scale
    baseline_train = np.column_stack((np.ones(len(train)), z_train))
    baseline_test = np.column_stack((np.ones(len(test)), z_test))
    full_train = np.column_stack((baseline_train, interaction_train))
    full_test = np.column_stack((baseline_test, interaction_test))
    baseline_rank = int(np.linalg.matrix_rank(baseline_train))
    full_rank = int(np.linalg.matrix_rank(full_train))
    if baseline_rank != baseline_train.shape[1] or full_rank != full_train.shape[1]:
        return _unavailable_fold(base, ESTIMATE_RANK_DEFICIENT)
    baseline_beta = np.linalg.lstsq(baseline_train, zy_train, rcond=None)[0]
    full_beta = np.linalg.lstsq(full_train, zy_train, rcond=None)[0]
    baseline_errors = zy_test - baseline_test @ baseline_beta
    interaction_errors = zy_test - full_test @ full_beta
    baseline_sse = float(np.sum(baseline_errors**2))
    interaction_sse = float(np.sum(interaction_errors**2))
    test_sst = float(np.sum((zy_test - np.mean(zy_test)) ** 2))
    return InteractionFoldEstimate(
        **base,
        status=ESTIMATE_AVAILABLE,
        effect_size=_metric(float(full_beta[-1])),
        baseline_test_mse=_metric(baseline_sse / len(test)),
        interaction_test_mse=_metric(interaction_sse / len(test)),
        incremental_oos_r2=(
            None
            if test_sst <= 0
            else _metric((baseline_sse - interaction_sse) / test_sst)
        ),
    )


def _unavailable_fold(
    base: Mapping[str, Any], status: str
) -> InteractionFoldEstimate:
    return InteractionFoldEstimate(
        **base,
        status=status,
        effect_size=None,
        baseline_test_mse=None,
        interaction_test_mse=None,
        incremental_oos_r2=None,
    )


def _validate_inputs(
    features: PointInTimeFeatureMatrix,
    targets: ForwardTargetMatrix,
    contexts: Sequence[InteractionContext],
    spec: InteractionResearchSpec,
) -> None:
    if features.decision_timestamps != targets.decision_timestamps:
        raise ValueError("feature and target decision timestamps must match exactly")
    if spec.target_name not in targets.definition.target_names:
        raise ValueError(f"target matrix does not contain {spec.target_name!r}")
    available_features = set(features.definition.feature_names)
    required = {name for item in spec.interactions for name in item.feature_names}
    missing = sorted(required - available_features)
    if missing:
        raise ValueError(
            "feature matrix does not contain interaction inputs: " + ", ".join(missing)
        )
    ordered_contexts = tuple(contexts)
    if any(not isinstance(item, InteractionContext) for item in ordered_contexts):
        raise TypeError("contexts must contain InteractionContext values")
    context_timestamps = tuple(item.decision_timestamp for item in ordered_contexts)
    if context_timestamps != features.decision_timestamps:
        raise ValueError(
            "contexts must match feature decision timestamps exactly and in order"
        )
    provenance = features.definition.provenance
    metadata = spec.plan.config_metadata
    expected_metadata = {
        "config_version": provenance.config_version,
        "strategy_version": provenance.strategy_version,
        "parameter_set_id": provenance.parameter_set_id,
    }
    for name, expected in expected_metadata.items():
        if metadata.get(name) != expected:
            raise ValueError(
                f"walk-forward plan {name} must match feature provenance"
            )
    target_specification = targets.definition.specification(spec.target_name)
    if (
        target_specification.price_source_policy_version
        != provenance.price_source_policy_version
    ):
        raise ValueError(
            "target price-source policy must match feature-matrix provenance"
        )


def _validate_definition(definition: InteractionDefinition) -> None:
    if not isinstance(definition, InteractionDefinition):
        raise TypeError("interaction must be an InteractionDefinition")
    _non_empty(definition.interaction_id, "interaction_id")
    _non_empty(definition.display_name, "display_name")
    if len(definition.feature_names) not in (2, 3):
        raise ValueError("an interaction must bind two or three feature names")
    if len(set(definition.feature_names)) != len(definition.feature_names):
        raise ValueError("interaction feature names must be unique")
    for name in definition.feature_names:
        _non_empty(name, "feature_name")


def _validate_spec(
    spec: InteractionResearchSpec, *, allow_empty_id: bool = False
) -> None:
    expected_versions = {
        "feature_id": FEATURE_INTERACTION_FEATURE_ID,
        "policy_version": FEATURE_INTERACTION_POLICY_VERSION,
        "estimation_policy_version": INTERACTION_ESTIMATION_POLICY_VERSION,
        "missing_value_policy_version": INTERACTION_MISSING_VALUE_POLICY_VERSION,
        "context_policy_version": INTERACTION_CONTEXT_POLICY_VERSION,
        "target_availability_policy_version": (
            INTERACTION_TARGET_AVAILABILITY_POLICY_VERSION
        ),
        "promotion_policy_version": INTERACTION_PROMOTION_POLICY_VERSION,
    }
    for name, expected in expected_versions.items():
        if getattr(spec, name) != expected:
            raise ValueError(f"{name} must be {expected!r}")
    if not allow_empty_id:
        _non_empty(spec.spec_id, "spec_id")
    _non_empty(spec.target_name, "target_name")
    if not isinstance(spec.plan, WalkForwardPlan):
        raise TypeError("plan must be a WalkForwardPlan")
    spec.plan.as_record()
    if not spec.interactions:
        raise ValueError("interactions must not be empty")
    for item in spec.interactions:
        _validate_definition(item)
    ids = tuple(item.interaction_id for item in spec.interactions)
    if len(set(ids)) != len(ids):
        raise ValueError("interaction IDs must be unique")
    _positive_integer(spec.minimum_train_samples, "minimum_train_samples")
    _positive_integer(spec.minimum_test_samples, "minimum_test_samples")
    required_train = max(len(item.feature_names) + 2 for item in spec.interactions)
    if spec.minimum_train_samples < required_train:
        raise ValueError(
            "minimum_train_samples must exceed every full model's parameter count"
        )


def _validate_fold_estimate(item: InteractionFoldEstimate) -> None:
    _positive_integer(item.fold_number, "fold_number")
    for name in ("train_start", "train_end", "test_start", "test_end"):
        require_utc_datetime(getattr(item, name), field_name=name)
    if item.train_end >= item.test_start or item.test_start > item.test_end:
        raise ValueError("fold estimate timestamps are not ordered")
    _non_negative_integer(item.train_sample_size, "train_sample_size")
    _non_negative_integer(item.test_sample_size, "test_sample_size")
    if item.status not in ESTIMATE_STATUSES:
        raise ValueError(f"unknown interaction estimate status {item.status!r}")
    metrics = (
        item.effect_size,
        item.baseline_test_mse,
        item.interaction_test_mse,
    )
    if item.status == ESTIMATE_AVAILABLE and any(value is None for value in metrics):
        raise ValueError("available fold estimates require effect and MSE metrics")
    if item.status != ESTIMATE_AVAILABLE and any(
        value is not None
        for value in (*metrics, item.incremental_oos_r2)
    ):
        raise ValueError("unavailable fold estimates cannot persist metrics")


def _validate_effect(effect: InteractionEffect) -> None:
    if effect.scope not in INTERACTION_SCOPES:
        raise ValueError(f"scope must be one of {INTERACTION_SCOPES}")
    _non_empty(effect.segment, "segment")
    if effect.scope == GLOBAL_SCOPE and effect.segment != GLOBAL_SEGMENT:
        raise ValueError("global interaction effect must use ALL segment")
    _non_negative_integer(effect.sample_size, "sample_size")
    _non_negative_integer(effect.tested_sample_size, "tested_sample_size")
    _non_negative_integer(effect.eligible_fold_count, "eligible_fold_count")
    if not effect.folds:
        raise ValueError("interaction effect must persist every walk-forward fold")
    for fold in effect.folds:
        _validate_fold_estimate(fold)
    available = tuple(fold for fold in effect.folds if fold.status == ESTIMATE_AVAILABLE)
    if effect.eligible_fold_count != len(available):
        raise ValueError("eligible_fold_count does not match available folds")
    if effect.tested_sample_size != sum(fold.test_sample_size for fold in available):
        raise ValueError("tested_sample_size does not match available folds")
    metrics = (
        effect.effect_size,
        effect.effect_sign_consistency,
    )
    if available and any(value is None for value in metrics):
        raise ValueError("available interaction effects require aggregate metrics")
    if not available and any(
        value is not None
        for value in (
            effect.effect_size,
            effect.effect_size_standard_deviation,
            effect.effect_sign_consistency,
            effect.mean_incremental_oos_r2,
            effect.positive_incremental_fold_fraction,
        )
    ):
        raise ValueError("unavailable interaction effects cannot persist metrics")
    if len(available) < 2 and effect.effect_size_standard_deviation is not None:
        raise ValueError("effect-size dispersion requires at least two folds")
    for name in ("effect_sign_consistency", "positive_incremental_fold_fraction"):
        value = getattr(effect, name)
        if value is not None and not Decimal("0") <= value <= Decimal("1"):
            raise ValueError(f"{name} must be in [0, 1]")


def _validate_analysis(analysis: InteractionAnalysis) -> None:
    _validate_definition(analysis.definition)
    if not analysis.effects:
        raise ValueError("interaction analysis must not be empty")
    keys = tuple((item.scope, item.segment) for item in analysis.effects)
    if len(keys) != len(set(keys)):
        raise ValueError("interaction analysis segments must be unique")
    if (GLOBAL_SCOPE, GLOBAL_SEGMENT) not in keys:
        raise ValueError("interaction analysis must include a global effect")
    if not any(item.scope == REGIME_SCOPE for item in analysis.effects):
        raise ValueError("interaction analysis must include regime effects")
    if not any(item.scope == SETUP_SCOPE for item in analysis.effects):
        raise ValueError("interaction analysis must include setup effects")
    for effect in analysis.effects:
        _validate_effect(effect)


def _validate_report(report: FeatureInteractionReport) -> None:
    report.spec.as_record()
    _non_empty(report.report_id, "report_id")
    _non_empty(report.evidence_digest, "evidence_digest", allow_empty=True)
    for name in (
        "feature_definition_fingerprint",
        "target_definition_fingerprint",
        "input_digest",
        "context_digest",
    ):
        value = _non_empty(getattr(report, name), name)
        if len(value) != 64:
            raise ValueError(f"{name} must be a SHA-256 digest")
    if report.feature_definition.get("fingerprint") != report.feature_definition_fingerprint:
        raise ValueError("feature definition fingerprint does not match definition")
    if report.target_definition.get("fingerprint") != report.target_definition_fingerprint:
        raise ValueError("target definition fingerprint does not match definition")
    if report.production_status != INTERACTION_PRODUCTION_STATUS:
        raise ValueError("feature interaction report must remain research-only")
    if report.promotion_ticket != INTERACTION_PROMOTION_TICKET:
        raise ValueError("feature interaction report must require BTC-193 promotion")
    if tuple(item.definition for item in report.analyses) != report.spec.interactions:
        raise ValueError("analyses must match the declared interactions and order")
    for analysis in report.analyses:
        _validate_analysis(analysis)
    if report.reason_codes != INTERACTION_REASON_CODES:
        raise ValueError("feature interaction reason codes do not match policy")
    if report.report_id != _report_id(report):
        raise ValueError("feature interaction report does not match report_id")


def _spec_payload(spec: InteractionResearchSpec) -> dict[str, Any]:
    return {
        "feature_id": spec.feature_id,
        "policy_version": spec.policy_version,
        "estimation_policy_version": spec.estimation_policy_version,
        "missing_value_policy_version": spec.missing_value_policy_version,
        "context_policy_version": spec.context_policy_version,
        "target_availability_policy_version": (
            spec.target_availability_policy_version
        ),
        "promotion_policy_version": spec.promotion_policy_version,
        "target_name": spec.target_name,
        "interactions": [item.as_record() for item in spec.interactions],
        "plan": spec.plan.as_record(),
        "minimum_train_samples": spec.minimum_train_samples,
        "minimum_test_samples": spec.minimum_test_samples,
    }


def _report_id(report: FeatureInteractionReport) -> str:
    return _digest(
        {
            "feature_id": report.spec.feature_id,
            "policy_version": report.spec.policy_version,
            "spec_id": report.spec.spec_id,
            "input_digest": report.input_digest,
        }
    )


def _report_payload(report: FeatureInteractionReport) -> dict[str, Any]:
    return {
        "report_id": report.report_id,
        "spec": report.spec.as_record(),
        "feature_definition": report.feature_definition,
        "target_definition": report.target_definition,
        "feature_definition_fingerprint": report.feature_definition_fingerprint,
        "target_definition_fingerprint": report.target_definition_fingerprint,
        "input_digest": report.input_digest,
        "context_digest": report.context_digest,
        "production_status": report.production_status,
        "promotion_ticket": report.promotion_ticket,
        "analyses": [item.as_record() for item in report.analyses],
        "reason_codes": list(report.reason_codes),
    }


def _spec_from_record(record: Mapping[str, Any]) -> InteractionResearchSpec:
    interactions = tuple(
        _definition_from_record(_mapping(item, "interaction"))
        for item in _sequence(record.get("interactions"), "interactions")
    )
    spec = InteractionResearchSpec(
        feature_id=_string(record.get("feature_id"), "feature_id"),
        policy_version=_string(record.get("policy_version"), "policy_version"),
        estimation_policy_version=_string(
            record.get("estimation_policy_version"), "estimation_policy_version"
        ),
        missing_value_policy_version=_string(
            record.get("missing_value_policy_version"),
            "missing_value_policy_version",
        ),
        context_policy_version=_string(
            record.get("context_policy_version"), "context_policy_version"
        ),
        target_availability_policy_version=_string(
            record.get("target_availability_policy_version"),
            "target_availability_policy_version",
        ),
        promotion_policy_version=_string(
            record.get("promotion_policy_version"), "promotion_policy_version"
        ),
        spec_id=_string(record.get("spec_id"), "spec_id"),
        target_name=_string(record.get("target_name"), "target_name"),
        interactions=interactions,
        plan=restore_walk_forward_plan(_mapping(record.get("plan"), "plan")),
        minimum_train_samples=_positive_integer(
            record.get("minimum_train_samples"), "minimum_train_samples"
        ),
        minimum_test_samples=_positive_integer(
            record.get("minimum_test_samples"), "minimum_test_samples"
        ),
    )
    if spec.as_record() != dict(record):
        raise ValueError("record does not match reconstructed interaction spec")
    return spec


def _definition_from_record(record: Mapping[str, Any]) -> InteractionDefinition:
    definition = InteractionDefinition(
        interaction_id=_string(record.get("interaction_id"), "interaction_id"),
        display_name=_string(record.get("display_name"), "display_name"),
        feature_names=_string_tuple(record.get("feature_names"), "feature_names"),
    )
    if definition.as_record() != dict(record):
        raise ValueError("record does not match interaction definition")
    return definition


def _analysis_from_record(record: Mapping[str, Any]) -> InteractionAnalysis:
    analysis = InteractionAnalysis(
        definition=_definition_from_record(
            _mapping(record.get("definition"), "definition")
        ),
        effects=tuple(
            _effect_from_record(_mapping(item, "effect"))
            for item in _sequence(record.get("effects"), "effects")
        ),
    )
    if analysis.as_record() != dict(record):
        raise ValueError("record does not match interaction analysis")
    return analysis


def _effect_from_record(record: Mapping[str, Any]) -> InteractionEffect:
    effect = InteractionEffect(
        scope=_string(record.get("scope"), "scope"),
        segment=_string(record.get("segment"), "segment"),
        sample_size=_non_negative_integer(record.get("sample_size"), "sample_size"),
        tested_sample_size=_non_negative_integer(
            record.get("tested_sample_size"), "tested_sample_size"
        ),
        eligible_fold_count=_non_negative_integer(
            record.get("eligible_fold_count"), "eligible_fold_count"
        ),
        effect_size=_decimal_or_none(record.get("effect_size"), "effect_size"),
        effect_size_standard_deviation=_decimal_or_none(
            record.get("effect_size_standard_deviation"),
            "effect_size_standard_deviation",
        ),
        effect_sign_consistency=_decimal_or_none(
            record.get("effect_sign_consistency"), "effect_sign_consistency"
        ),
        mean_incremental_oos_r2=_decimal_or_none(
            record.get("mean_incremental_oos_r2"), "mean_incremental_oos_r2"
        ),
        positive_incremental_fold_fraction=_decimal_or_none(
            record.get("positive_incremental_fold_fraction"),
            "positive_incremental_fold_fraction",
        ),
        folds=tuple(
            _fold_from_record(_mapping(item, "fold"))
            for item in _sequence(record.get("folds"), "folds")
        ),
    )
    if effect.as_record() != dict(record):
        raise ValueError("record does not match interaction effect")
    return effect


def _fold_from_record(record: Mapping[str, Any]) -> InteractionFoldEstimate:
    item = InteractionFoldEstimate(
        fold_number=_positive_integer(record.get("fold_number"), "fold_number"),
        train_start=_utc_from_record(record.get("train_start"), "train_start"),
        train_end=_utc_from_record(record.get("train_end"), "train_end"),
        test_start=_utc_from_record(record.get("test_start"), "test_start"),
        test_end=_utc_from_record(record.get("test_end"), "test_end"),
        train_sample_size=_non_negative_integer(
            record.get("train_sample_size"), "train_sample_size"
        ),
        test_sample_size=_non_negative_integer(
            record.get("test_sample_size"), "test_sample_size"
        ),
        status=_string(record.get("status"), "status"),
        effect_size=_decimal_or_none(record.get("effect_size"), "effect_size"),
        baseline_test_mse=_decimal_or_none(
            record.get("baseline_test_mse"), "baseline_test_mse"
        ),
        interaction_test_mse=_decimal_or_none(
            record.get("interaction_test_mse"), "interaction_test_mse"
        ),
        incremental_oos_r2=_decimal_or_none(
            record.get("incremental_oos_r2"), "incremental_oos_r2"
        ),
    )
    if item.as_record() != dict(record):
        raise ValueError("record does not match fold estimate")
    return item


def _weighted_mean(
    values: Sequence[Decimal | None], weights: Sequence[int]
) -> Decimal | None:
    if not values:
        return None
    if any(value is None for value in values) or len(values) != len(weights):
        raise ValueError("weighted mean inputs are inconsistent")
    total_weight = sum(weights)
    if total_weight <= 0:
        return None
    total = sum(
        (value * weight for value, weight in zip(values, weights) if value is not None),
        Decimal("0"),
    )
    return (total / total_weight).quantize(
        INTERACTION_METRIC_EXPONENT, rounding=ROUND_HALF_EVEN
    )


def _population_std(values: Sequence[Decimal | None]) -> Decimal | None:
    if len(values) < 2 or any(value is None for value in values):
        return None
    array = np.asarray([float(value) for value in values if value is not None])
    return _metric(float(np.std(array)))


def _sign_consistency(
    values: Sequence[Decimal | None], mean: Decimal | None
) -> Decimal | None:
    if not values or mean is None:
        return None
    direction = Decimal("1") if mean > 0 else Decimal("-1") if mean < 0 else Decimal("0")
    matching = sum(
        1
        for value in values
        if value is not None
        and (
            (direction > 0 and value > 0)
            or (direction < 0 and value < 0)
            or (direction == 0 and value == 0)
        )
    )
    return _metric(matching / len(values))


def _metric(value: float) -> Decimal:
    if not np.isfinite(value):
        raise ValueError("interaction metric must be finite")
    return Decimal(str(value)).quantize(
        INTERACTION_METRIC_EXPONENT, rounding=ROUND_HALF_EVEN
    )


def _optional_decimal(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _decimal_or_none(value: Any, name: str) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a decimal string or None")
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    return result


def _utc_from_record(value: Any, name: str) -> datetime:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO-8601 datetime") from exc
    return require_utc_datetime(parsed, field_name=name)


def _non_empty(value: Any, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _string(value: Any, name: str) -> str:
    return _non_empty(value, name)


def _positive_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _non_negative_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    return value


def _sequence(value: Any, name: str) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{name} must be a sequence")
    return tuple(value)


def _string_tuple(value: Any, name: str) -> tuple[str, ...]:
    result = _sequence(value, name)
    if any(not isinstance(item, str) or not item.strip() for item in result):
        raise ValueError(f"{name} must contain non-empty strings")
    return tuple(result)


def _digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "CANDIDATE_INTERACTIONS",
    "ESTIMATE_AVAILABLE",
    "ESTIMATE_INSUFFICIENT_TEST",
    "ESTIMATE_INSUFFICIENT_TRAIN",
    "ESTIMATE_RANK_DEFICIENT",
    "ESTIMATE_STATUSES",
    "ESTIMATE_ZERO_VARIANCE_FEATURE",
    "ESTIMATE_ZERO_VARIANCE_TARGET",
    "FEATURE_INTERACTION_FEATURE_ID",
    "FEATURE_INTERACTION_POLICY_VERSION",
    "GLOBAL_SCOPE",
    "GLOBAL_SEGMENT",
    "INTERACTION_CONTEXT_POLICY_VERSION",
    "INTERACTION_ESTIMATION_POLICY_VERSION",
    "INTERACTION_MISSING_VALUE_POLICY_VERSION",
    "INTERACTION_PRODUCTION_STATUS",
    "INTERACTION_PROMOTION_POLICY_VERSION",
    "INTERACTION_PROMOTION_TICKET",
    "INTERACTION_REASON_CODES",
    "INTERACTION_SCOPES",
    "INTERACTION_TARGET_AVAILABILITY_POLICY_VERSION",
    "REGIME_SCOPE",
    "SETUP_SCOPE",
    "FeatureInteractionReport",
    "InteractionAnalysis",
    "InteractionContext",
    "InteractionDefinition",
    "InteractionEffect",
    "InteractionFoldEstimate",
    "InteractionResearchSpec",
    "interaction_research_spec",
    "restore_feature_interaction_report",
    "run_feature_interaction_research",
]
