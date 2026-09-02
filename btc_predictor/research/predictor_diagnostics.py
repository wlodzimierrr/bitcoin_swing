"""Statistical predictor diagnostics for features and scores (BTC-189).

A weight is only evidence-backed if someone measured what the thing it weighs
actually predicted.  This module measures exactly that, and nothing else: it
reads BTC-048 point-in-time feature rows as the predictors ``X``, reads the
separately versioned BTC-048 forward targets as the outcomes ``Y``, and reports

* Pearson and Spearman information coefficients with seeded bootstrap
  percentile intervals and the sample size behind every number;
* equal-count predictor buckets with their conditional expectancy, and whether
  higher predictor values are monotonically associated with better outcomes;
* the direct-component Pearson and rank correlation matrices, and the
  eigenvalue concentration / effective rank those matrices imply;
* the analytical v1.1 nested versus v1.2 de-nested effective-weight
  decomposition, taken verbatim from the BTC-129 scoring-contract owner; and
* forward MFE/MAE relationships across the same buckets.

Every statistic is also emitted per observed regime and per observed setup, so
regime- and setup-conditioned stability is a measurement rather than an
assertion.

Two separations are load-bearing.  Forward targets never enter ``X``: they are
retrospective evaluation labels only, and nothing here is fitted, so no target
value can influence a predictor value.  And *empirical correlation* is not
*mechanical nesting*: the correlation matrices here measure the former, while
the latter stays a structural question answered by BTC-129's declared scoring
graph, which this module reports beside them without conflating the two.

Missing values are complete-case excluded and are never converted to zero.
Results are research evidence only; this module has no strategy or
configuration mutation path and records BTC-193 as the required promotion
boundary.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

import numpy as np

from btc_predictor.data import require_utc_datetime
from btc_predictor.features.scoring_contracts import (
    MECHANICAL_VS_EMPIRICAL_NOTE,
    RETIRED_SCORING_CONTRACTS_VERSION,
    SCORING_CONTRACTS_VERSION,
    SCORING_PARAMETER_STATUS,
    effective_weight_report,
)
from btc_predictor.quant.simulation import (
    UNIFORM_INDEX_POLICY_VERSION,
    uniform_index_samples,
)
from btc_predictor.research.feature_interactions import (
    GLOBAL_SCOPE,
    GLOBAL_SEGMENT,
    INTERACTION_CONTEXT_POLICY_VERSION,
    REGIME_SCOPE,
    SETUP_SCOPE,
    InteractionContext,
)
from btc_predictor.research.feature_matrix import (
    ForwardTargetMatrix,
    PointInTimeFeatureMatrix,
)
from btc_predictor.research.monte_carlo_risk import (
    MONTE_CARLO_PERCENTILE_POLICY_VERSION,
    nearest_rank,
)


PREDICTOR_DIAGNOSTICS_FEATURE_ID = "PREDICTOR_DIAGNOSTICS"
PREDICTOR_DIAGNOSTICS_POLICY_VERSION = "STATISTICAL_PREDICTOR_DIAGNOSTICS_V1"
IC_POLICY_VERSION = "COMPLETE_CASE_CONTEMPORANEOUS_X_FORWARD_Y_IC_V1"
RANK_POLICY_VERSION = "AVERAGE_TIE_RANK_SPEARMAN_V1"
BOOTSTRAP_POLICY_VERSION = "SEEDED_IID_PERCENTILE_BOOTSTRAP_V1"
BOOTSTRAP_INDEX_POLICY_VERSION = UNIFORM_INDEX_POLICY_VERSION
BOOTSTRAP_PERCENTILE_POLICY_VERSION = MONTE_CARLO_PERCENTILE_POLICY_VERSION
BUCKET_POLICY_VERSION = "EQUAL_COUNT_SORTED_POSITION_BUCKETS_V1"
MONOTONICITY_POLICY_VERSION = "BUCKET_MEAN_RANK_CORRELATION_MONOTONICITY_V1"
STABILITY_POLICY_VERSION = "SEGMENT_WEIGHTED_RANK_IC_STABILITY_V1"
CONCENTRATION_POLICY_VERSION = "CORRELATION_EIGENVALUE_ENTROPY_EFFECTIVE_RANK_V1"
EXCURSION_POLICY_VERSION = "PAIRED_FORWARD_EXCURSION_BUCKET_RELATIONSHIP_V1"
EFFECTIVE_WEIGHT_POLICY_VERSION = "BTC_129_ANALYTICAL_EFFECTIVE_WEIGHTS_V1"
DIAGNOSTICS_MISSING_VALUE_POLICY_VERSION = "COMPLETE_CASE_NO_ZERO_FILL_V1"
DIAGNOSTICS_CONTEXT_POLICY_VERSION = INTERACTION_CONTEXT_POLICY_VERSION
TARGET_SEPARATION_POLICY_VERSION = "FORWARD_TARGETS_RETROSPECTIVE_ONLY_V1"
DIAGNOSTICS_PROMOTION_POLICY_VERSION = "BTC_193_REQUIRED_V1"
DIAGNOSTICS_PRODUCTION_STATUS = "RESEARCH_ONLY_NOT_PRODUCTION"
DIAGNOSTICS_PROMOTION_TICKET = "BTC-193"
DIAGNOSTIC_METRIC_EXPONENT = Decimal("1E-12")

# BTC-186 owns the decision-time regime/setup context contract; BTC-189 reads
# exactly the same evidence, so it reuses that type instead of declaring a
# second vocabulary for the same thing.
DiagnosticContext = InteractionContext

DIAGNOSTIC_SCOPES = (GLOBAL_SCOPE, REGIME_SCOPE, SETUP_SCOPE)

COMPOSITE_SCORE_PREDICTOR = "COMPOSITE_SCORE"
RAW_FEATURE_PREDICTOR = "RAW_FEATURE"
PREDICTOR_KINDS = (COMPOSITE_SCORE_PREDICTOR, RAW_FEATURE_PREDICTOR)

PEARSON_METHOD = "PEARSON"
SPEARMAN_METHOD = "SPEARMAN"
CORRELATION_METHODS = (PEARSON_METHOD, SPEARMAN_METHOD)

DIAGNOSTIC_AVAILABLE = "AVAILABLE"
DIAGNOSTIC_INSUFFICIENT_SAMPLES = "INSUFFICIENT_SAMPLES"
DIAGNOSTIC_ZERO_VARIANCE_PREDICTOR = "ZERO_VARIANCE_PREDICTOR"
DIAGNOSTIC_ZERO_VARIANCE_TARGET = "ZERO_VARIANCE_TARGET"
DIAGNOSTIC_STATUSES = (
    DIAGNOSTIC_AVAILABLE,
    DIAGNOSTIC_INSUFFICIENT_SAMPLES,
    DIAGNOSTIC_ZERO_VARIANCE_PREDICTOR,
    DIAGNOSTIC_ZERO_VARIANCE_TARGET,
)

INTERVAL_AVAILABLE = "AVAILABLE"
INTERVAL_UNDEFINED_RESAMPLES = "UNDEFINED_IN_EVERY_RESAMPLE"
INTERVAL_NOT_ESTIMATED = "NOT_ESTIMATED"
INTERVAL_STATUSES = (
    INTERVAL_AVAILABLE,
    INTERVAL_UNDEFINED_RESAMPLES,
    INTERVAL_NOT_ESTIMATED,
)

BUCKET_AVAILABLE = "AVAILABLE"
BUCKET_INSUFFICIENT_SAMPLES = "INSUFFICIENT_SAMPLES"
BUCKET_STATUSES = (BUCKET_AVAILABLE, BUCKET_INSUFFICIENT_SAMPLES)

MONOTONICITY_AVAILABLE = "AVAILABLE"
MONOTONICITY_INSUFFICIENT_BUCKETS = "INSUFFICIENT_BUCKETS"
MONOTONICITY_CONSTANT_BUCKET_MEANS = "CONSTANT_BUCKET_MEANS"
MONOTONICITY_STATUSES = (
    MONOTONICITY_AVAILABLE,
    MONOTONICITY_INSUFFICIENT_BUCKETS,
    MONOTONICITY_CONSTANT_BUCKET_MEANS,
)

MATRIX_AVAILABLE = "AVAILABLE"
MATRIX_INSUFFICIENT_SAMPLES = "INSUFFICIENT_SAMPLES"
MATRIX_STATUSES = (MATRIX_AVAILABLE, MATRIX_INSUFFICIENT_SAMPLES)

CONCENTRATION_AVAILABLE = "AVAILABLE"
CONCENTRATION_INSUFFICIENT_SAMPLES = "INSUFFICIENT_SAMPLES"
CONCENTRATION_ZERO_VARIANCE_COMPONENT = "ZERO_VARIANCE_COMPONENT"
CONCENTRATION_STATUSES = (
    CONCENTRATION_AVAILABLE,
    CONCENTRATION_INSUFFICIENT_SAMPLES,
    CONCENTRATION_ZERO_VARIANCE_COMPONENT,
)

STABILITY_AVAILABLE = "AVAILABLE"
STABILITY_NO_EVALUATED_SEGMENTS = "NO_EVALUATED_SEGMENTS"
STABILITY_STATUSES = (STABILITY_AVAILABLE, STABILITY_NO_EVALUATED_SEGMENTS)

PREDICTOR_DIAGNOSTICS_REASON_CODES = (
    "PREDICTOR_DIAGNOSTICS_POINT_IN_TIME_FEATURES",
    "PREDICTOR_DIAGNOSTICS_FORWARD_TARGETS_SEPARATED",
    "PREDICTOR_DIAGNOSTICS_RETROSPECTIVE_EVALUATION_ONLY",
    "PREDICTOR_DIAGNOSTICS_COMPLETE_CASES",
    "PREDICTOR_DIAGNOSTICS_SAMPLE_SIZE_REPORTED",
    "PREDICTOR_DIAGNOSTICS_BOOTSTRAP_UNCERTAINTY_REPORTED",
    "PREDICTOR_DIAGNOSTICS_RAW_AND_COMPOSITE_PREDICTORS_COMPARED",
    "PREDICTOR_DIAGNOSTICS_BUCKET_CONDITIONAL_EXPECTANCY",
    "PREDICTOR_DIAGNOSTICS_CONVICTION_MONOTONICITY",
    "PREDICTOR_DIAGNOSTICS_REGIME_CONDITIONED_STABILITY",
    "PREDICTOR_DIAGNOSTICS_SETUP_CONDITIONED_STABILITY",
    "PREDICTOR_DIAGNOSTICS_EMPIRICAL_CORRELATION_MEASURED",
    "PREDICTOR_DIAGNOSTICS_MECHANICAL_NESTING_REPORTED_SEPARATELY",
    "PREDICTOR_DIAGNOSTICS_EFFECTIVE_WEIGHTS_V1_1_VERSUS_V1_2",
    "PREDICTOR_DIAGNOSTICS_FACTOR_CONCENTRATION",
    "PREDICTOR_DIAGNOSTICS_FORWARD_EXCURSION_RELATIONSHIPS",
    "PREDICTOR_DIAGNOSTICS_RESEARCH_ONLY",
    "PREDICTOR_DIAGNOSTICS_BTC_193_PROMOTION_REQUIRED",
    "PREDICTOR_DIAGNOSTICS_COMPLETE",
)


class PredictorDiagnosticsError(ValueError):
    """Raised when diagnostic inputs violate the BTC-189 contract."""


@dataclass(frozen=True)
class PredictorDefinition:
    """One declared predictor column and whether it is raw or composite."""

    predictor_name: str
    predictor_kind: str
    display_name: str

    def as_record(self) -> dict[str, str]:
        _validate_predictor_definition(self)
        return {
            "predictor_name": self.predictor_name,
            "predictor_kind": self.predictor_kind,
            "display_name": self.display_name,
        }


@dataclass(frozen=True)
class CorrelationEstimate:
    """One information coefficient with its sample size and uncertainty."""

    method: str
    sample_size: int
    status: str
    coefficient: Decimal | None
    confidence: Decimal
    interval_status: str
    lower_bound: Decimal | None
    upper_bound: Decimal | None
    resample_count: int
    defined_resample_count: int

    def as_record(self) -> dict[str, Any]:
        _validate_correlation_estimate(self)
        return {
            "method": self.method,
            "sample_size": self.sample_size,
            "status": self.status,
            "coefficient": _optional_decimal(self.coefficient),
            "confidence": str(self.confidence),
            "interval_status": self.interval_status,
            "lower_bound": _optional_decimal(self.lower_bound),
            "upper_bound": _optional_decimal(self.upper_bound),
            "resample_count": self.resample_count,
            "defined_resample_count": self.defined_resample_count,
        }


@dataclass(frozen=True)
class BucketStatistics:
    """One equal-count predictor bucket and the outcomes observed inside it."""

    ordinal: int
    sample_size: int
    lower_predictor_value: Decimal
    upper_predictor_value: Decimal
    mean_predictor_value: Decimal
    mean_target_value: Decimal
    positive_target_fraction: Decimal

    def as_record(self) -> dict[str, Any]:
        _validate_bucket(self)
        return {
            "ordinal": self.ordinal,
            "sample_size": self.sample_size,
            "lower_predictor_value": str(self.lower_predictor_value),
            "upper_predictor_value": str(self.upper_predictor_value),
            "mean_predictor_value": str(self.mean_predictor_value),
            "mean_target_value": str(self.mean_target_value),
            "positive_target_fraction": str(self.positive_target_fraction),
        }


@dataclass(frozen=True)
class MonotonicityAssessment:
    """Whether higher predictor buckets carried better outcomes."""

    status: str
    bucket_count: int
    rank_correlation: Decimal | None
    increasing_step_count: int
    decreasing_step_count: int
    monotonic_increasing: bool
    monotonic_decreasing: bool

    def as_record(self) -> dict[str, Any]:
        _validate_monotonicity(self)
        return {
            "status": self.status,
            "bucket_count": self.bucket_count,
            "rank_correlation": _optional_decimal(self.rank_correlation),
            "increasing_step_count": self.increasing_step_count,
            "decreasing_step_count": self.decreasing_step_count,
            "monotonic_increasing": self.monotonic_increasing,
            "monotonic_decreasing": self.monotonic_decreasing,
        }


@dataclass(frozen=True)
class PredictorTargetDiagnostic:
    """Every statistic for one predictor, target, and conditioning segment."""

    scope: str
    segment: str
    predictor_name: str
    predictor_kind: str
    target_name: str
    observed_row_count: int
    sample_size: int
    status: str
    pearson: CorrelationEstimate
    spearman: CorrelationEstimate
    bucket_status: str
    tied_bucket_boundaries: bool
    buckets: tuple[BucketStatistics, ...]
    monotonicity: MonotonicityAssessment

    def as_record(self) -> dict[str, Any]:
        _validate_diagnostic(self)
        return {
            "scope": self.scope,
            "segment": self.segment,
            "predictor_name": self.predictor_name,
            "predictor_kind": self.predictor_kind,
            "target_name": self.target_name,
            "observed_row_count": self.observed_row_count,
            "sample_size": self.sample_size,
            "status": self.status,
            "pearson": self.pearson.as_record(),
            "spearman": self.spearman.as_record(),
            "bucket_status": self.bucket_status,
            "tied_bucket_boundaries": self.tied_bucket_boundaries,
            "buckets": [item.as_record() for item in self.buckets],
            "monotonicity": self.monotonicity.as_record(),
        }


@dataclass(frozen=True)
class PredictorAnalysis:
    """All diagnostics emitted for one declared predictor."""

    definition: PredictorDefinition
    diagnostics: tuple[PredictorTargetDiagnostic, ...]

    def diagnostic(
        self,
        target_name: str,
        *,
        scope: str = GLOBAL_SCOPE,
        segment: str = GLOBAL_SEGMENT,
    ) -> PredictorTargetDiagnostic:
        for item in self.diagnostics:
            if (
                item.target_name == target_name
                and item.scope == scope
                and item.segment == segment
            ):
                return item
        raise KeyError((target_name, scope, segment))

    def as_record(self) -> dict[str, Any]:
        _validate_analysis(self)
        return {
            "definition": self.definition.as_record(),
            "diagnostics": [item.as_record() for item in self.diagnostics],
        }


@dataclass(frozen=True)
class StabilitySummary:
    """Cross-segment dispersion of one predictor's rank IC in one scope."""

    scope: str
    predictor_name: str
    target_name: str
    status: str
    segment_count: int
    evaluated_segment_count: int
    evaluated_sample_size: int
    mean_coefficient: Decimal | None
    coefficient_standard_deviation: Decimal | None
    minimum_coefficient: Decimal | None
    maximum_coefficient: Decimal | None
    sign_consistency: Decimal | None

    def as_record(self) -> dict[str, Any]:
        _validate_stability(self)
        return {
            "scope": self.scope,
            "predictor_name": self.predictor_name,
            "target_name": self.target_name,
            "status": self.status,
            "segment_count": self.segment_count,
            "evaluated_segment_count": self.evaluated_segment_count,
            "evaluated_sample_size": self.evaluated_sample_size,
            "mean_coefficient": _optional_decimal(self.mean_coefficient),
            "coefficient_standard_deviation": _optional_decimal(
                self.coefficient_standard_deviation
            ),
            "minimum_coefficient": _optional_decimal(self.minimum_coefficient),
            "maximum_coefficient": _optional_decimal(self.maximum_coefficient),
            "sign_consistency": _optional_decimal(self.sign_consistency),
        }


@dataclass(frozen=True)
class CorrelationMatrix:
    """One empirical correlation matrix over the declared direct components.

    This is a measurement of how the components co-moved.  It is deliberately
    not a statement about mechanical nesting, which stays a structural
    property of the BTC-129 scoring graph reported alongside it.
    """

    method: str
    component_names: tuple[str, ...]
    sample_size: int
    status: str
    coefficients: tuple[tuple[Decimal | None, ...], ...]
    empirical_note: str

    def coefficient(self, row_name: str, column_name: str) -> Decimal | None:
        row = self.component_names.index(row_name)
        column = self.component_names.index(column_name)
        return self.coefficients[row][column]

    def as_record(self) -> dict[str, Any]:
        _validate_correlation_matrix(self)
        return {
            "method": self.method,
            "component_names": list(self.component_names),
            "sample_size": self.sample_size,
            "status": self.status,
            "coefficients": [
                [_optional_decimal(value) for value in row]
                for row in self.coefficients
            ],
            "empirical_note": self.empirical_note,
        }


@dataclass(frozen=True)
class FactorConcentration:
    """Eigenvalue concentration and effective rank of the component set."""

    method: str
    component_names: tuple[str, ...]
    sample_size: int
    status: str
    eigenvalues: tuple[Decimal, ...]
    largest_eigenvalue_share: Decimal | None
    effective_rank: Decimal | None

    def as_record(self) -> dict[str, Any]:
        _validate_concentration(self)
        return {
            "method": self.method,
            "component_names": list(self.component_names),
            "sample_size": self.sample_size,
            "status": self.status,
            "eigenvalues": [str(value) for value in self.eigenvalues],
            "largest_eigenvalue_share": _optional_decimal(
                self.largest_eigenvalue_share
            ),
            "effective_rank": _optional_decimal(self.effective_rank),
        }


@dataclass(frozen=True)
class ExcursionBucket:
    """Paired forward favourable and adverse excursion inside one bucket."""

    ordinal: int
    sample_size: int
    lower_predictor_value: Decimal
    upper_predictor_value: Decimal
    mean_favourable_excursion: Decimal
    mean_adverse_excursion: Decimal

    def as_record(self) -> dict[str, Any]:
        _validate_excursion_bucket(self)
        return {
            "ordinal": self.ordinal,
            "sample_size": self.sample_size,
            "lower_predictor_value": str(self.lower_predictor_value),
            "upper_predictor_value": str(self.upper_predictor_value),
            "mean_favourable_excursion": str(self.mean_favourable_excursion),
            "mean_adverse_excursion": str(self.mean_adverse_excursion),
        }


@dataclass(frozen=True)
class ExcursionRelationship:
    """How one predictor related to paired forward MFE and MAE outcomes."""

    scope: str
    segment: str
    predictor_name: str
    favourable_target_name: str
    adverse_target_name: str
    sample_size: int
    status: str
    bucket_status: str
    buckets: tuple[ExcursionBucket, ...]
    favourable_rank_ic: CorrelationEstimate
    adverse_rank_ic: CorrelationEstimate
    excursion_rank_correlation: CorrelationEstimate

    def as_record(self) -> dict[str, Any]:
        _validate_excursion(self)
        return {
            "scope": self.scope,
            "segment": self.segment,
            "predictor_name": self.predictor_name,
            "favourable_target_name": self.favourable_target_name,
            "adverse_target_name": self.adverse_target_name,
            "sample_size": self.sample_size,
            "status": self.status,
            "bucket_status": self.bucket_status,
            "buckets": [item.as_record() for item in self.buckets],
            "favourable_rank_ic": self.favourable_rank_ic.as_record(),
            "adverse_rank_ic": self.adverse_rank_ic.as_record(),
            "excursion_rank_correlation": (
                self.excursion_rank_correlation.as_record()
            ),
        }


@dataclass(frozen=True)
class PredictorDiagnosticsSpec:
    """Frozen statistical question, predictor set, and estimator policy."""

    feature_id: str
    policy_version: str
    ic_policy_version: str
    rank_policy_version: str
    bootstrap_policy_version: str
    bootstrap_index_policy_version: str
    bootstrap_percentile_policy_version: str
    bucket_policy_version: str
    monotonicity_policy_version: str
    stability_policy_version: str
    concentration_policy_version: str
    excursion_policy_version: str
    effective_weight_policy_version: str
    missing_value_policy_version: str
    context_policy_version: str
    target_separation_policy_version: str
    promotion_policy_version: str
    spec_id: str
    predictors: tuple[PredictorDefinition, ...]
    target_names: tuple[str, ...]
    component_predictors: tuple[str, ...]
    conviction_predictor: str
    favourable_target_name: str
    adverse_target_name: str
    bucket_count: int
    minimum_sample_size: int
    bootstrap_resamples: int
    bootstrap_confidence: Decimal
    seed: int

    def predictor(self, predictor_name: str) -> PredictorDefinition:
        for item in self.predictors:
            if item.predictor_name == predictor_name:
                return item
        raise KeyError(predictor_name)

    def as_record(self) -> dict[str, Any]:
        _validate_spec(self)
        payload = _spec_payload(self)
        if _digest(payload) != self.spec_id:
            raise PredictorDiagnosticsError(
                "predictor diagnostics specification does not match spec_id"
            )
        return {**payload, "spec_id": self.spec_id}


@dataclass(frozen=True)
class PredictorDiagnosticsReport:
    """Replayable, research-only BTC-189 evidence for one predictor set."""

    report_id: str
    evidence_digest: str
    spec: PredictorDiagnosticsSpec
    feature_definition: dict[str, Any]
    target_definition: dict[str, Any]
    feature_definition_fingerprint: str
    target_definition_fingerprint: str
    input_digest: str
    context_digest: str
    production_status: str
    promotion_ticket: str
    observed_regimes: tuple[str, ...]
    observed_setups: tuple[str, ...]
    analyses: tuple[PredictorAnalysis, ...]
    stability: tuple[StabilitySummary, ...]
    correlation_matrices: tuple[CorrelationMatrix, ...]
    concentration: FactorConcentration
    effective_weight_decomposition: dict[str, Any]
    excursions: tuple[ExcursionRelationship, ...]
    reason_codes: tuple[str, ...]

    def analysis(self, predictor_name: str) -> PredictorAnalysis:
        for item in self.analyses:
            if item.definition.predictor_name == predictor_name:
                return item
        raise KeyError(predictor_name)

    def analyses_of_kind(self, predictor_kind: str) -> tuple[PredictorAnalysis, ...]:
        """Return the analyses whose predictor carries one declared kind."""

        _require_member(predictor_kind, PREDICTOR_KINDS, "predictor_kind")
        return tuple(
            item
            for item in self.analyses
            if item.definition.predictor_kind == predictor_kind
        )

    def conviction_monotonicity(
        self,
        target_name: str,
        *,
        scope: str = GLOBAL_SCOPE,
        segment: str = GLOBAL_SEGMENT,
    ) -> MonotonicityAssessment:
        """Return whether higher declared conviction carried better outcomes."""

        analysis = self.analysis(self.spec.conviction_predictor)
        return analysis.diagnostic(
            target_name, scope=scope, segment=segment
        ).monotonicity

    def correlation_matrix(self, method: str) -> CorrelationMatrix:
        for item in self.correlation_matrices:
            if item.method == method:
                return item
        raise KeyError(method)

    def stability_summary(
        self, predictor_name: str, target_name: str, *, scope: str
    ) -> StabilitySummary:
        for item in self.stability:
            if (
                item.predictor_name == predictor_name
                and item.target_name == target_name
                and item.scope == scope
            ):
                return item
        raise KeyError((predictor_name, target_name, scope))

    def excursion(
        self,
        predictor_name: str,
        *,
        scope: str = GLOBAL_SCOPE,
        segment: str = GLOBAL_SEGMENT,
    ) -> ExcursionRelationship:
        for item in self.excursions:
            if (
                item.predictor_name == predictor_name
                and item.scope == scope
                and item.segment == segment
            ):
                return item
        raise KeyError((predictor_name, scope, segment))

    def as_record(self) -> dict[str, Any]:
        _validate_report(self)
        payload = _report_payload(self)
        if _digest(payload) != self.evidence_digest:
            raise PredictorDiagnosticsError(
                "predictor diagnostics evidence does not match digest"
            )
        return {**payload, "evidence_digest": self.evidence_digest}


def predictor_diagnostics_spec(
    *,
    predictors: Sequence[PredictorDefinition],
    target_names: Sequence[str],
    component_predictors: Sequence[str],
    conviction_predictor: str,
    favourable_target_name: str,
    adverse_target_name: str,
    bucket_count: int = 5,
    minimum_sample_size: int = 20,
    bootstrap_resamples: int = 1000,
    bootstrap_confidence: Any = Decimal("95"),
    seed: int = 0,
) -> PredictorDiagnosticsSpec:
    """Create a deterministic BTC-189 diagnostics specification."""

    provisional = PredictorDiagnosticsSpec(
        feature_id=PREDICTOR_DIAGNOSTICS_FEATURE_ID,
        policy_version=PREDICTOR_DIAGNOSTICS_POLICY_VERSION,
        ic_policy_version=IC_POLICY_VERSION,
        rank_policy_version=RANK_POLICY_VERSION,
        bootstrap_policy_version=BOOTSTRAP_POLICY_VERSION,
        bootstrap_index_policy_version=BOOTSTRAP_INDEX_POLICY_VERSION,
        bootstrap_percentile_policy_version=BOOTSTRAP_PERCENTILE_POLICY_VERSION,
        bucket_policy_version=BUCKET_POLICY_VERSION,
        monotonicity_policy_version=MONOTONICITY_POLICY_VERSION,
        stability_policy_version=STABILITY_POLICY_VERSION,
        concentration_policy_version=CONCENTRATION_POLICY_VERSION,
        excursion_policy_version=EXCURSION_POLICY_VERSION,
        effective_weight_policy_version=EFFECTIVE_WEIGHT_POLICY_VERSION,
        missing_value_policy_version=DIAGNOSTICS_MISSING_VALUE_POLICY_VERSION,
        context_policy_version=DIAGNOSTICS_CONTEXT_POLICY_VERSION,
        target_separation_policy_version=TARGET_SEPARATION_POLICY_VERSION,
        promotion_policy_version=DIAGNOSTICS_PROMOTION_POLICY_VERSION,
        spec_id="",
        predictors=tuple(predictors),
        target_names=tuple(target_names),
        component_predictors=tuple(component_predictors),
        conviction_predictor=conviction_predictor,
        favourable_target_name=favourable_target_name,
        adverse_target_name=adverse_target_name,
        bucket_count=bucket_count,
        minimum_sample_size=minimum_sample_size,
        bootstrap_resamples=bootstrap_resamples,
        bootstrap_confidence=_confidence(bootstrap_confidence),
        seed=seed,
    )
    _validate_spec(provisional, allow_empty_id=True)
    spec = replace(provisional, spec_id=_digest(_spec_payload(provisional)))
    spec.as_record()
    return spec


def run_predictor_diagnostics(
    features: PointInTimeFeatureMatrix,
    targets: ForwardTargetMatrix,
    contexts: Sequence[DiagnosticContext],
    *,
    spec: PredictorDiagnosticsSpec,
) -> PredictorDiagnosticsReport:
    """Measure every declared diagnostic globally and by regime and setup."""

    if not isinstance(features, PointInTimeFeatureMatrix):
        raise TypeError("features must be a PointInTimeFeatureMatrix")
    if not isinstance(targets, ForwardTargetMatrix):
        raise TypeError("targets must be a ForwardTargetMatrix")
    if not isinstance(spec, PredictorDiagnosticsSpec):
        raise TypeError("spec must be a PredictorDiagnosticsSpec")
    spec.as_record()
    ordered_contexts = tuple(contexts)
    _validate_inputs(features, targets, ordered_contexts, spec)
    predictor_columns = {
        definition.predictor_name: features.values[
            :, features.definition.feature_names.index(definition.predictor_name)
        ]
        for definition in spec.predictors
    }
    target_columns = {
        name: targets.values[:, targets.definition.target_names.index(name)]
        for name in spec.target_names
    }
    regimes = tuple(sorted({item.regime for item in ordered_contexts}))
    setups = tuple(sorted({item.setup for item in ordered_contexts}))
    segments = _segments(ordered_contexts, regimes, setups)
    analyses = tuple(
        PredictorAnalysis(
            definition=definition,
            diagnostics=tuple(
                _diagnostic(
                    scope=scope,
                    segment=segment,
                    segment_mask=mask,
                    definition=definition,
                    predictor_values=predictor_columns[definition.predictor_name],
                    target_name=target_name,
                    target_values=target_columns[target_name],
                    spec=spec,
                )
                for scope, segment, mask in segments
                for target_name in spec.target_names
            ),
        )
        for definition in spec.predictors
    )
    stability = tuple(
        _stability(
            scope=scope,
            analysis=analysis,
            target_name=target_name,
            segment_count=count,
        )
        for analysis in analyses
        for target_name in spec.target_names
        for scope, count in ((REGIME_SCOPE, len(regimes)), (SETUP_SCOPE, len(setups)))
    )
    matrices = tuple(
        _correlation_matrix(
            method=method,
            component_names=spec.component_predictors,
            predictor_columns=predictor_columns,
            spec=spec,
        )
        for method in CORRELATION_METHODS
    )
    concentration = _concentration(
        matrix=next(item for item in matrices if item.method == PEARSON_METHOD),
        spec=spec,
    )
    excursions = _excursions(
        spec=spec,
        segments=segments,
        predictor_columns=predictor_columns,
        targets=targets,
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
    report = PredictorDiagnosticsReport(
        report_id="",
        evidence_digest="",
        spec=spec,
        feature_definition=features.definition.as_record(),
        target_definition=targets.definition.as_record(),
        feature_definition_fingerprint=features.definition.fingerprint,
        target_definition_fingerprint=targets.definition.fingerprint,
        input_digest=input_digest,
        context_digest=context_digest,
        production_status=DIAGNOSTICS_PRODUCTION_STATUS,
        promotion_ticket=DIAGNOSTICS_PROMOTION_TICKET,
        observed_regimes=regimes,
        observed_setups=setups,
        analyses=analyses,
        stability=stability,
        correlation_matrices=matrices,
        concentration=concentration,
        effective_weight_decomposition=_effective_weight_decomposition(),
        excursions=excursions,
        reason_codes=PREDICTOR_DIAGNOSTICS_REASON_CODES,
    )
    report = replace(report, report_id=_report_id(report))
    _validate_report(report)
    return replace(report, evidence_digest=_digest(_report_payload(report)))


def restore_predictor_diagnostics_report(
    record: Mapping[str, Any],
) -> PredictorDiagnosticsReport:
    """Restore persisted BTC-189 evidence and reject drift or tampering."""

    source = _mapping(record, "record")
    report = PredictorDiagnosticsReport(
        report_id=_string(source.get("report_id"), "report_id"),
        evidence_digest=_string(source.get("evidence_digest"), "evidence_digest"),
        spec=_spec_from_record(_mapping(source.get("spec"), "spec")),
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
        observed_regimes=_string_tuple(
            source.get("observed_regimes"), "observed_regimes"
        ),
        observed_setups=_string_tuple(
            source.get("observed_setups"), "observed_setups"
        ),
        analyses=tuple(
            _analysis_from_record(_mapping(item, "analysis"))
            for item in _sequence(source.get("analyses"), "analyses")
        ),
        stability=tuple(
            _stability_from_record(_mapping(item, "stability"))
            for item in _sequence(source.get("stability"), "stability")
        ),
        correlation_matrices=tuple(
            _matrix_from_record(_mapping(item, "correlation_matrix"))
            for item in _sequence(
                source.get("correlation_matrices"), "correlation_matrices"
            )
        ),
        concentration=_concentration_from_record(
            _mapping(source.get("concentration"), "concentration")
        ),
        effective_weight_decomposition=dict(
            _mapping(
                source.get("effective_weight_decomposition"),
                "effective_weight_decomposition",
            )
        ),
        excursions=tuple(
            _excursion_from_record(_mapping(item, "excursion"))
            for item in _sequence(source.get("excursions"), "excursions")
        ),
        reason_codes=_string_tuple(source.get("reason_codes"), "reason_codes"),
    )
    if report.as_record() != dict(source):
        raise PredictorDiagnosticsError(
            "record does not match reconstructed predictor diagnostics"
        )
    return report


def _segments(
    contexts: tuple[DiagnosticContext, ...],
    regimes: tuple[str, ...],
    setups: tuple[str, ...],
) -> tuple[tuple[str, str, np.ndarray[Any, np.dtype[np.bool_]]], ...]:
    return (
        (GLOBAL_SCOPE, GLOBAL_SEGMENT, np.ones(len(contexts), dtype=bool)),
        *(
            (
                REGIME_SCOPE,
                regime,
                np.asarray(
                    [item.regime == regime for item in contexts], dtype=bool
                ),
            )
            for regime in regimes
        ),
        *(
            (
                SETUP_SCOPE,
                setup,
                np.asarray([item.setup == setup for item in contexts], dtype=bool),
            )
            for setup in setups
        ),
    )


def _diagnostic(
    *,
    scope: str,
    segment: str,
    segment_mask: np.ndarray[Any, np.dtype[np.bool_]],
    definition: PredictorDefinition,
    predictor_values: np.ndarray[Any, np.dtype[np.float64]],
    target_name: str,
    target_values: np.ndarray[Any, np.dtype[np.float64]],
    spec: PredictorDiagnosticsSpec,
) -> PredictorTargetDiagnostic:
    complete = (
        segment_mask
        & np.isfinite(predictor_values)
        & np.isfinite(target_values)
    )
    xs = predictor_values[complete]
    ys = target_values[complete]
    key = {
        "scope": scope,
        "segment": segment,
        "predictor": definition.predictor_name,
        "target": target_name,
    }
    pearson = _correlation_estimate(
        method=PEARSON_METHOD, xs=xs, ys=ys, spec=spec, seed_key=key
    )
    spearman = _correlation_estimate(
        method=SPEARMAN_METHOD, xs=xs, ys=ys, spec=spec, seed_key=key
    )
    buckets, bucket_status, tied = _buckets(xs, ys, spec=spec)
    diagnostic = PredictorTargetDiagnostic(
        scope=scope,
        segment=segment,
        predictor_name=definition.predictor_name,
        predictor_kind=definition.predictor_kind,
        target_name=target_name,
        observed_row_count=int(np.count_nonzero(segment_mask)),
        sample_size=int(xs.size),
        status=pearson.status,
        pearson=pearson,
        spearman=spearman,
        bucket_status=bucket_status,
        tied_bucket_boundaries=tied,
        buckets=buckets,
        monotonicity=_monotonicity(buckets, bucket_status),
    )
    _validate_diagnostic(diagnostic)
    return diagnostic


def _correlation_estimate(
    *,
    method: str,
    xs: np.ndarray[Any, np.dtype[np.float64]],
    ys: np.ndarray[Any, np.dtype[np.float64]],
    spec: PredictorDiagnosticsSpec,
    seed_key: Mapping[str, Any],
) -> CorrelationEstimate:
    """Estimate one IC and bootstrap its percentile interval.

    The interval resamples the observed complete-case pairs with replacement
    from the seeded BTC-049 index stream, so the reported uncertainty replays
    exactly.  A resample whose predictor or target is constant leaves the
    statistic undefined and is excluded rather than counted as zero.
    """

    size = int(xs.size)
    if size < spec.minimum_sample_size:
        return _unestimated(method, size, DIAGNOSTIC_INSUFFICIENT_SAMPLES, spec)
    if not _has_variance(xs):
        return _unestimated(method, size, DIAGNOSTIC_ZERO_VARIANCE_PREDICTOR, spec)
    if not _has_variance(ys):
        return _unestimated(method, size, DIAGNOSTIC_ZERO_VARIANCE_TARGET, spec)
    coefficient = _statistic(method, xs, ys)
    if coefficient is None:
        raise PredictorDiagnosticsError(
            "a varying complete-case sample must produce a defined coefficient"
        )
    indices = np.asarray(
        uniform_index_samples(
            (spec.bootstrap_resamples, size),
            seed=_estimate_seed(spec, {**dict(seed_key), "method": method}),
            high=size,
        )
    )
    resampled = _row_statistic(method, xs[indices], ys[indices])
    defined = np.sort(resampled[np.isfinite(resampled)])
    if defined.size == 0:
        return CorrelationEstimate(
            method=method,
            sample_size=size,
            status=DIAGNOSTIC_AVAILABLE,
            coefficient=_metric(coefficient),
            confidence=spec.bootstrap_confidence,
            interval_status=INTERVAL_UNDEFINED_RESAMPLES,
            lower_bound=None,
            upper_bound=None,
            resample_count=spec.bootstrap_resamples,
            defined_resample_count=0,
        )
    tail = (Decimal("100") - spec.bootstrap_confidence) / Decimal("2")
    lower_rank = nearest_rank(tail, int(defined.size))
    upper_rank = nearest_rank(Decimal("100") - tail, int(defined.size))
    estimate = CorrelationEstimate(
        method=method,
        sample_size=size,
        status=DIAGNOSTIC_AVAILABLE,
        coefficient=_metric(coefficient),
        confidence=spec.bootstrap_confidence,
        interval_status=INTERVAL_AVAILABLE,
        lower_bound=_metric(float(defined[lower_rank - 1])),
        upper_bound=_metric(float(defined[upper_rank - 1])),
        resample_count=spec.bootstrap_resamples,
        defined_resample_count=int(defined.size),
    )
    _validate_correlation_estimate(estimate)
    return estimate


def _unestimated(
    method: str,
    size: int,
    status: str,
    spec: PredictorDiagnosticsSpec,
) -> CorrelationEstimate:
    return CorrelationEstimate(
        method=method,
        sample_size=size,
        status=status,
        coefficient=None,
        confidence=spec.bootstrap_confidence,
        interval_status=INTERVAL_NOT_ESTIMATED,
        lower_bound=None,
        upper_bound=None,
        resample_count=0,
        defined_resample_count=0,
    )


def _buckets(
    xs: np.ndarray[Any, np.dtype[np.float64]],
    ys: np.ndarray[Any, np.dtype[np.float64]],
    *,
    spec: PredictorDiagnosticsSpec,
) -> tuple[tuple[BucketStatistics, ...], str, bool]:
    """Split complete cases into equal-count buckets by sorted predictor rank.

    Buckets are cut by sorted position rather than by value, so their counts
    differ by at most one.  Tied predictor values can therefore straddle a
    boundary; the boundary values are persisted and a straddle is declared
    rather than hidden.
    """

    size = int(xs.size)
    if size < spec.minimum_sample_size or size < spec.bucket_count:
        return (), BUCKET_INSUFFICIENT_SAMPLES, False
    order = np.argsort(xs, kind="stable")
    edges = [
        (index * size) // spec.bucket_count
        for index in range(spec.bucket_count + 1)
    ]
    buckets: list[BucketStatistics] = []
    for ordinal in range(spec.bucket_count):
        positions = order[edges[ordinal] : edges[ordinal + 1]]
        values = xs[positions]
        outcomes = ys[positions]
        buckets.append(
            BucketStatistics(
                ordinal=ordinal + 1,
                sample_size=int(positions.size),
                lower_predictor_value=_metric(float(values[0])),
                upper_predictor_value=_metric(float(values[-1])),
                mean_predictor_value=_metric(float(np.mean(values))),
                mean_target_value=_metric(float(np.mean(outcomes))),
                positive_target_fraction=_metric(
                    float(np.count_nonzero(outcomes > 0)) / float(outcomes.size)
                ),
            )
        )
    tied = any(
        current.upper_predictor_value == following.lower_predictor_value
        for current, following in zip(buckets, buckets[1:])
    )
    return tuple(buckets), BUCKET_AVAILABLE, tied


def _monotonicity(
    buckets: tuple[BucketStatistics, ...],
    bucket_status: str,
) -> MonotonicityAssessment:
    if bucket_status != BUCKET_AVAILABLE or len(buckets) < 2:
        return MonotonicityAssessment(
            status=MONOTONICITY_INSUFFICIENT_BUCKETS,
            bucket_count=len(buckets),
            rank_correlation=None,
            increasing_step_count=0,
            decreasing_step_count=0,
            monotonic_increasing=False,
            monotonic_decreasing=False,
        )
    means = [item.mean_target_value for item in buckets]
    increasing = sum(
        1 for current, following in zip(means, means[1:]) if following > current
    )
    decreasing = sum(
        1 for current, following in zip(means, means[1:]) if following < current
    )
    if increasing == 0 and decreasing == 0:
        return MonotonicityAssessment(
            status=MONOTONICITY_CONSTANT_BUCKET_MEANS,
            bucket_count=len(buckets),
            rank_correlation=None,
            increasing_step_count=0,
            decreasing_step_count=0,
            monotonic_increasing=False,
            monotonic_decreasing=False,
        )
    ordinals = np.asarray(
        [float(item.ordinal) for item in buckets], dtype=np.float64
    )
    values = np.asarray([float(value) for value in means], dtype=np.float64)
    coefficient = _statistic(SPEARMAN_METHOD, ordinals, values)
    if coefficient is None:
        raise PredictorDiagnosticsError(
            "varying bucket means must produce a defined rank correlation"
        )
    steps = len(buckets) - 1
    assessment = MonotonicityAssessment(
        status=MONOTONICITY_AVAILABLE,
        bucket_count=len(buckets),
        rank_correlation=_metric(coefficient),
        increasing_step_count=increasing,
        decreasing_step_count=decreasing,
        monotonic_increasing=increasing == steps,
        monotonic_decreasing=decreasing == steps,
    )
    _validate_monotonicity(assessment)
    return assessment


def _stability(
    *,
    scope: str,
    analysis: PredictorAnalysis,
    target_name: str,
    segment_count: int,
) -> StabilitySummary:
    """Summarize one predictor's rank IC dispersion across a scope's segments.

    Rank IC is the stability statistic because it is the estimate least
    sensitive to a single extreme outcome inside a thin segment.
    """

    selected = tuple(
        item
        for item in analysis.diagnostics
        if item.scope == scope and item.target_name == target_name
    )
    evaluated = tuple(
        item for item in selected if item.spearman.status == DIAGNOSTIC_AVAILABLE
    )
    coefficients = tuple(item.spearman.coefficient for item in evaluated)
    weights = tuple(item.spearman.sample_size for item in evaluated)
    if not evaluated:
        summary = StabilitySummary(
            scope=scope,
            predictor_name=analysis.definition.predictor_name,
            target_name=target_name,
            status=STABILITY_NO_EVALUATED_SEGMENTS,
            segment_count=segment_count,
            evaluated_segment_count=0,
            evaluated_sample_size=0,
            mean_coefficient=None,
            coefficient_standard_deviation=None,
            minimum_coefficient=None,
            maximum_coefficient=None,
            sign_consistency=None,
        )
        _validate_stability(summary)
        return summary
    mean = _weighted_mean(coefficients, weights)
    summary = StabilitySummary(
        scope=scope,
        predictor_name=analysis.definition.predictor_name,
        target_name=target_name,
        status=STABILITY_AVAILABLE,
        segment_count=segment_count,
        evaluated_segment_count=len(evaluated),
        evaluated_sample_size=sum(weights),
        mean_coefficient=mean,
        coefficient_standard_deviation=(
            _population_std(coefficients) if len(coefficients) >= 2 else None
        ),
        minimum_coefficient=min(item for item in coefficients if item is not None),
        maximum_coefficient=max(item for item in coefficients if item is not None),
        sign_consistency=_sign_consistency(coefficients, mean),
    )
    _validate_stability(summary)
    return summary


def _correlation_matrix(
    *,
    method: str,
    component_names: tuple[str, ...],
    predictor_columns: Mapping[str, np.ndarray[Any, np.dtype[np.float64]]],
    spec: PredictorDiagnosticsSpec,
) -> CorrelationMatrix:
    """Correlate the declared direct components on jointly complete rows.

    One shared complete-case mask is used for every pair.  Pairwise deletion
    would build a matrix whose entries come from different samples, which can
    be non-positive-semidefinite and would make the concentration diagnostic
    below meaningless.
    """

    columns = [predictor_columns[name] for name in component_names]
    stacked = np.column_stack(columns)
    complete = np.all(np.isfinite(stacked), axis=1)
    rows = stacked[complete, :]
    size = int(rows.shape[0])
    if size < spec.minimum_sample_size:
        matrix = CorrelationMatrix(
            method=method,
            component_names=component_names,
            sample_size=size,
            status=MATRIX_INSUFFICIENT_SAMPLES,
            coefficients=(),
            empirical_note=MECHANICAL_VS_EMPIRICAL_NOTE,
        )
        _validate_correlation_matrix(matrix)
        return matrix
    if method == SPEARMAN_METHOD:
        rows = np.column_stack(
            [_average_ranks(rows[:, index]) for index in range(rows.shape[1])]
        )
    coefficients = tuple(
        tuple(
            _optional_metric(_pearson(rows[:, row], rows[:, column]))
            for column in range(rows.shape[1])
        )
        for row in range(rows.shape[1])
    )
    matrix = CorrelationMatrix(
        method=method,
        component_names=component_names,
        sample_size=size,
        status=MATRIX_AVAILABLE,
        coefficients=coefficients,
        empirical_note=MECHANICAL_VS_EMPIRICAL_NOTE,
    )
    _validate_correlation_matrix(matrix)
    return matrix


def _concentration(
    *,
    matrix: CorrelationMatrix,
    spec: PredictorDiagnosticsSpec,
) -> FactorConcentration:
    """Report how much of the component set is one repeated direction.

    Eigenvalues of the component correlation matrix sum to the component
    count.  The largest share says how much variance one direction carries;
    the effective rank is the exponential of the eigenvalue-share entropy, so
    ``k`` orthogonal components score ``k`` and one repeated direction scores
    ``1``.
    """

    names = matrix.component_names
    if matrix.status != MATRIX_AVAILABLE:
        return _unavailable_concentration(
            matrix, CONCENTRATION_INSUFFICIENT_SAMPLES
        )
    if any(value is None for row in matrix.coefficients for value in row):
        return _unavailable_concentration(
            matrix, CONCENTRATION_ZERO_VARIANCE_COMPONENT
        )
    values = np.asarray(
        [[float(value) for value in row] for row in matrix.coefficients],
        dtype=np.float64,
    )
    raw = np.sort(np.linalg.eigvalsh((values + values.T) / 2.0))[::-1]
    # A correlation matrix is positive semidefinite; tiny negative eigenvalues
    # are float64 rounding around an exact zero, not observed variance.
    eigenvalues = np.clip(raw, 0.0, None)
    total = float(np.sum(eigenvalues))
    if total <= 0:
        return _unavailable_concentration(
            matrix, CONCENTRATION_ZERO_VARIANCE_COMPONENT
        )
    shares = eigenvalues / total
    positive = shares[shares > 0]
    entropy = float(-np.sum(positive * np.log(positive)))
    # ``exp(entropy)`` is mathematically bounded by [1, k]; float64 rounding can
    # step a few ulps outside that domain, so it is clamped rather than
    # persisted as an impossible rank.
    rank = min(float(len(names)), max(1.0, float(np.exp(entropy))))
    concentration = FactorConcentration(
        method=matrix.method,
        component_names=names,
        sample_size=matrix.sample_size,
        status=CONCENTRATION_AVAILABLE,
        eigenvalues=tuple(_metric(float(value)) for value in eigenvalues),
        largest_eigenvalue_share=_metric(float(shares[0])),
        effective_rank=_metric(rank),
    )
    _validate_concentration(concentration)
    return concentration


def _unavailable_concentration(
    matrix: CorrelationMatrix, status: str
) -> FactorConcentration:
    concentration = FactorConcentration(
        method=matrix.method,
        component_names=matrix.component_names,
        sample_size=matrix.sample_size,
        status=status,
        eigenvalues=(),
        largest_eigenvalue_share=None,
        effective_rank=None,
    )
    _validate_concentration(concentration)
    return concentration


def _excursions(
    *,
    spec: PredictorDiagnosticsSpec,
    segments: tuple[tuple[str, str, np.ndarray[Any, np.dtype[np.bool_]]], ...],
    predictor_columns: Mapping[str, np.ndarray[Any, np.dtype[np.float64]]],
    targets: ForwardTargetMatrix,
) -> tuple[ExcursionRelationship, ...]:
    favourable = targets.values[
        :, targets.definition.target_names.index(spec.favourable_target_name)
    ]
    adverse = targets.values[
        :, targets.definition.target_names.index(spec.adverse_target_name)
    ]
    return tuple(
        _excursion(
            scope=scope,
            segment=segment,
            segment_mask=mask,
            predictor_name=definition.predictor_name,
            predictor_values=predictor_columns[definition.predictor_name],
            favourable=favourable,
            adverse=adverse,
            spec=spec,
        )
        for definition in spec.predictors
        for scope, segment, mask in segments
    )


def _excursion(
    *,
    scope: str,
    segment: str,
    segment_mask: np.ndarray[Any, np.dtype[np.bool_]],
    predictor_name: str,
    predictor_values: np.ndarray[Any, np.dtype[np.float64]],
    favourable: np.ndarray[Any, np.dtype[np.float64]],
    adverse: np.ndarray[Any, np.dtype[np.float64]],
    spec: PredictorDiagnosticsSpec,
) -> ExcursionRelationship:
    """Relate one predictor to paired forward favourable/adverse excursions.

    The two excursions are measured on the same rows, so a bucket's upside and
    downside are comparable rather than drawn from two different samples.
    """

    complete = (
        segment_mask
        & np.isfinite(predictor_values)
        & np.isfinite(favourable)
        & np.isfinite(adverse)
    )
    xs = predictor_values[complete]
    highs = favourable[complete]
    lows = adverse[complete]
    key = {"scope": scope, "segment": segment, "predictor": predictor_name}
    favourable_ic = _correlation_estimate(
        method=SPEARMAN_METHOD,
        xs=xs,
        ys=highs,
        spec=spec,
        seed_key={**key, "pair": "PREDICTOR_FAVOURABLE"},
    )
    adverse_ic = _correlation_estimate(
        method=SPEARMAN_METHOD,
        xs=xs,
        ys=lows,
        spec=spec,
        seed_key={**key, "pair": "PREDICTOR_ADVERSE"},
    )
    paired = _correlation_estimate(
        method=SPEARMAN_METHOD,
        xs=highs,
        ys=lows,
        spec=spec,
        seed_key={**key, "pair": "FAVOURABLE_ADVERSE"},
    )
    buckets, bucket_status = _excursion_buckets(xs, highs, lows, spec=spec)
    relationship = ExcursionRelationship(
        scope=scope,
        segment=segment,
        predictor_name=predictor_name,
        favourable_target_name=spec.favourable_target_name,
        adverse_target_name=spec.adverse_target_name,
        sample_size=int(xs.size),
        status=(
            DIAGNOSTIC_AVAILABLE
            if xs.size >= spec.minimum_sample_size
            else DIAGNOSTIC_INSUFFICIENT_SAMPLES
        ),
        bucket_status=bucket_status,
        buckets=buckets,
        favourable_rank_ic=favourable_ic,
        adverse_rank_ic=adverse_ic,
        excursion_rank_correlation=paired,
    )
    _validate_excursion(relationship)
    return relationship


def _excursion_buckets(
    xs: np.ndarray[Any, np.dtype[np.float64]],
    highs: np.ndarray[Any, np.dtype[np.float64]],
    lows: np.ndarray[Any, np.dtype[np.float64]],
    *,
    spec: PredictorDiagnosticsSpec,
) -> tuple[tuple[ExcursionBucket, ...], str]:
    size = int(xs.size)
    if size < spec.minimum_sample_size or size < spec.bucket_count:
        return (), BUCKET_INSUFFICIENT_SAMPLES
    order = np.argsort(xs, kind="stable")
    edges = [
        (index * size) // spec.bucket_count
        for index in range(spec.bucket_count + 1)
    ]
    buckets: list[ExcursionBucket] = []
    for ordinal in range(spec.bucket_count):
        positions = order[edges[ordinal] : edges[ordinal + 1]]
        values = xs[positions]
        buckets.append(
            ExcursionBucket(
                ordinal=ordinal + 1,
                sample_size=int(positions.size),
                lower_predictor_value=_metric(float(values[0])),
                upper_predictor_value=_metric(float(values[-1])),
                mean_favourable_excursion=_metric(float(np.mean(highs[positions]))),
                mean_adverse_excursion=_metric(float(np.mean(lows[positions]))),
            )
        )
    return tuple(buckets), BUCKET_AVAILABLE


def _effective_weight_decomposition() -> dict[str, Any]:
    """Persist the BTC-129 v1.1 versus v1.2 decomposition verbatim.

    The weights, their expansion, and the mechanical-nesting audit are owned
    by the scoring-contract module; this layer reports them beside the
    empirical correlations without recomputing or reinterpreting them.
    """

    report = effective_weight_report()
    decomposition = {
        "policy_version": EFFECTIVE_WEIGHT_POLICY_VERSION,
        "contracts_version": SCORING_CONTRACTS_VERSION,
        "retired_contracts_version": RETIRED_SCORING_CONTRACTS_VERSION,
        "parameter_status": SCORING_PARAMETER_STATUS,
        "report": report,
    }
    _validate_effective_weights(decomposition)
    return decomposition


def _has_variance(values: np.ndarray[Any, np.dtype[np.float64]]) -> bool:
    return values.size > 0 and float(np.min(values)) != float(np.max(values))


def _pearson(
    xs: np.ndarray[Any, np.dtype[np.float64]],
    ys: np.ndarray[Any, np.dtype[np.float64]],
) -> float | None:
    centred_x = xs - float(np.mean(xs))
    centred_y = ys - float(np.mean(ys))
    scale_x = float(np.sqrt(np.sum(centred_x * centred_x)))
    scale_y = float(np.sqrt(np.sum(centred_y * centred_y)))
    if scale_x <= 0 or scale_y <= 0:
        return None
    value = float(np.sum(centred_x * centred_y)) / (scale_x * scale_y)
    if not np.isfinite(value):
        return None
    # Float64 rounding can push an exact +/-1 a few ulps outside the domain.
    return min(1.0, max(-1.0, value))


def _average_ranks(
    values: np.ndarray[Any, np.dtype[np.float64]],
) -> np.ndarray[Any, np.dtype[np.float64]]:
    """Rank ascending, giving every tied group its shared average rank."""

    return _row_average_ranks(values.reshape(1, values.size))[0]


def _row_average_ranks(
    matrix: np.ndarray[Any, np.dtype[np.float64]],
) -> np.ndarray[Any, np.dtype[np.float64]]:
    rows, width = matrix.shape
    order = np.argsort(matrix, axis=1, kind="stable")
    ordered = np.take_along_axis(matrix, order, axis=1)
    starts = np.ones((rows, width), dtype=bool)
    starts[:, 1:] = ordered[:, 1:] != ordered[:, :-1]
    groups = np.cumsum(starts, axis=1) - 1
    flattened = (groups + (np.arange(rows) * width)[:, None]).ravel()
    positions = np.broadcast_to(
        np.arange(1, width + 1, dtype=np.float64), (rows, width)
    ).ravel()
    sums = np.bincount(flattened, weights=positions, minlength=rows * width)
    counts = np.bincount(flattened, minlength=rows * width)
    averages = np.zeros(rows * width, dtype=np.float64)
    observed = counts > 0
    averages[observed] = sums[observed] / counts[observed]
    ranked = averages[flattened].reshape(rows, width)
    result = np.empty_like(ranked)
    np.put_along_axis(result, order, ranked, axis=1)
    return result


def _statistic(
    method: str,
    xs: np.ndarray[Any, np.dtype[np.float64]],
    ys: np.ndarray[Any, np.dtype[np.float64]],
) -> float | None:
    if method == PEARSON_METHOD:
        return _pearson(xs, ys)
    if method == SPEARMAN_METHOD:
        return _pearson(_average_ranks(xs), _average_ranks(ys))
    raise PredictorDiagnosticsError(f"unknown correlation method {method!r}")


def _row_statistic(
    method: str,
    xs: np.ndarray[Any, np.dtype[np.float64]],
    ys: np.ndarray[Any, np.dtype[np.float64]],
) -> np.ndarray[Any, np.dtype[np.float64]]:
    """Evaluate one statistic for every resampled row at once."""

    if method == SPEARMAN_METHOD:
        xs = _row_average_ranks(xs)
        ys = _row_average_ranks(ys)
    elif method != PEARSON_METHOD:
        raise PredictorDiagnosticsError(f"unknown correlation method {method!r}")
    centred_x = xs - np.mean(xs, axis=1, keepdims=True)
    centred_y = ys - np.mean(ys, axis=1, keepdims=True)
    scale_x = np.sqrt(np.sum(centred_x * centred_x, axis=1))
    scale_y = np.sqrt(np.sum(centred_y * centred_y, axis=1))
    defined = (scale_x > 0) & (scale_y > 0)
    result = np.full(xs.shape[0], np.nan, dtype=np.float64)
    covariance = np.sum(centred_x * centred_y, axis=1)
    result[defined] = covariance[defined] / (scale_x[defined] * scale_y[defined])
    finite = np.isfinite(result)
    result[finite] = np.clip(result[finite], -1.0, 1.0)
    return result


def _weighted_mean(
    values: Sequence[Decimal | None], weights: Sequence[int]
) -> Decimal | None:
    if not values:
        return None
    if any(value is None for value in values) or len(values) != len(weights):
        raise PredictorDiagnosticsError("weighted mean inputs are inconsistent")
    total_weight = sum(weights)
    if total_weight <= 0:
        return None
    total = sum(
        (
            value * weight
            for value, weight in zip(values, weights)
            if value is not None
        ),
        Decimal("0"),
    )
    return (total / total_weight).quantize(
        DIAGNOSTIC_METRIC_EXPONENT, rounding=ROUND_HALF_EVEN
    )


def _population_std(values: Sequence[Decimal | None]) -> Decimal | None:
    if len(values) < 2 or any(value is None for value in values):
        return None
    array = np.asarray(
        [float(value) for value in values if value is not None], dtype=np.float64
    )
    return _metric(float(np.std(array)))


def _sign_consistency(
    values: Sequence[Decimal | None], mean: Decimal | None
) -> Decimal | None:
    if not values or mean is None:
        return None
    matching = sum(
        1
        for value in values
        if value is not None
        and (
            (mean > 0 and value > 0)
            or (mean < 0 and value < 0)
            or (mean == 0 and value == 0)
        )
    )
    return _metric(matching / len(values))


def _estimate_seed(
    spec: PredictorDiagnosticsSpec, key: Mapping[str, Any]
) -> int:
    """Derive one estimate's stream from the spec and its own identity.

    Deriving from the identity rather than from an incrementing counter keeps
    each interval reproducible on its own and independent of how many other
    segments happened to be evaluated first.
    """

    token = _digest({"spec_id": spec.spec_id, "seed": spec.seed, "key": dict(key)})
    return int(token[:16], 16)


def _metric(value: float | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        resolved = value
    else:
        if not np.isfinite(value):
            raise PredictorDiagnosticsError("diagnostic metric must be finite")
        resolved = Decimal(str(value))
    if not resolved.is_finite():
        raise PredictorDiagnosticsError("diagnostic metric must be finite")
    return resolved.quantize(
        DIAGNOSTIC_METRIC_EXPONENT, rounding=ROUND_HALF_EVEN
    )


def _optional_metric(value: float | None) -> Decimal | None:
    return None if value is None else _metric(value)


def _optional_decimal(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _confidence(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        resolved = value
    elif isinstance(value, int) and not isinstance(value, bool):
        resolved = Decimal(value)
    elif isinstance(value, str):
        resolved = Decimal(value)
    else:
        raise PredictorDiagnosticsError(
            "bootstrap_confidence must be a Decimal, integer, or decimal string"
        )
    if not resolved.is_finite() or resolved <= 0 or resolved >= 100:
        raise PredictorDiagnosticsError(
            "bootstrap_confidence must fall strictly inside (0, 100)"
        )
    return resolved




def _validate_predictor_definition(definition: PredictorDefinition) -> None:
    if not isinstance(definition, PredictorDefinition):
        raise TypeError("predictor must be a PredictorDefinition")
    _non_empty(definition.predictor_name, "predictor_name")
    _non_empty(definition.display_name, "display_name")
    _require_member(definition.predictor_kind, PREDICTOR_KINDS, "predictor_kind")


def _validate_correlation_estimate(estimate: CorrelationEstimate) -> None:
    _require_member(estimate.method, CORRELATION_METHODS, "method")
    _require_member(estimate.status, DIAGNOSTIC_STATUSES, "status")
    _require_member(estimate.interval_status, INTERVAL_STATUSES, "interval_status")
    _non_negative_integer(estimate.sample_size, "sample_size")
    _non_negative_integer(estimate.resample_count, "resample_count")
    _non_negative_integer(estimate.defined_resample_count, "defined_resample_count")
    _confidence(estimate.confidence)
    available = estimate.status == DIAGNOSTIC_AVAILABLE
    if available != (estimate.coefficient is not None):
        raise PredictorDiagnosticsError(
            "a coefficient must be present exactly when the estimate is available"
        )
    for name in ("coefficient", "lower_bound", "upper_bound"):
        value = getattr(estimate, name)
        if value is not None and not Decimal("-1") <= value <= Decimal("1"):
            raise PredictorDiagnosticsError(f"{name} must fall in [-1, 1]")
    if not available:
        if estimate.interval_status != INTERVAL_NOT_ESTIMATED:
            raise PredictorDiagnosticsError(
                "an unavailable estimate must not persist an interval status"
            )
        if estimate.resample_count or estimate.defined_resample_count:
            raise PredictorDiagnosticsError(
                "an unavailable estimate must not persist resample counts"
            )
        if estimate.lower_bound is not None or estimate.upper_bound is not None:
            raise PredictorDiagnosticsError(
                "an unavailable estimate must not persist interval bounds"
            )
        return
    if estimate.interval_status == INTERVAL_NOT_ESTIMATED:
        raise PredictorDiagnosticsError(
            "an available estimate must report its bootstrap interval status"
        )
    if estimate.resample_count < 1:
        raise PredictorDiagnosticsError(
            "an available estimate must persist its resample count"
        )
    if estimate.defined_resample_count > estimate.resample_count:
        raise PredictorDiagnosticsError(
            "defined resamples cannot exceed the resample count"
        )
    bounded = estimate.interval_status == INTERVAL_AVAILABLE
    if bounded != (estimate.lower_bound is not None):
        raise PredictorDiagnosticsError(
            "interval bounds must be present exactly when the interval is available"
        )
    if bounded != (estimate.upper_bound is not None):
        raise PredictorDiagnosticsError(
            "interval bounds must be present exactly when the interval is available"
        )
    if bounded:
        assert estimate.lower_bound is not None
        assert estimate.upper_bound is not None
        if estimate.defined_resample_count < 1:
            raise PredictorDiagnosticsError(
                "an available interval requires at least one defined resample"
            )
        if estimate.lower_bound > estimate.upper_bound:
            raise PredictorDiagnosticsError("interval bounds are not ordered")
    elif estimate.defined_resample_count:
        raise PredictorDiagnosticsError(
            "an undefined interval cannot report defined resamples"
        )


def _validate_bucket(bucket: BucketStatistics) -> None:
    _positive_integer(bucket.ordinal, "ordinal")
    _positive_integer(bucket.sample_size, "sample_size")
    for name in (
        "lower_predictor_value",
        "upper_predictor_value",
        "mean_predictor_value",
        "mean_target_value",
        "positive_target_fraction",
    ):
        value = getattr(bucket, name)
        if not isinstance(value, Decimal) or not value.is_finite():
            raise PredictorDiagnosticsError(f"{name} must be a finite Decimal")
    if bucket.lower_predictor_value > bucket.upper_predictor_value:
        raise PredictorDiagnosticsError("bucket predictor bounds are not ordered")
    if not (
        bucket.lower_predictor_value
        <= bucket.mean_predictor_value
        <= bucket.upper_predictor_value
    ):
        raise PredictorDiagnosticsError(
            "the mean predictor value must fall inside the bucket bounds"
        )
    if not Decimal("0") <= bucket.positive_target_fraction <= Decimal("1"):
        raise PredictorDiagnosticsError("positive_target_fraction must be in [0, 1]")


def _validate_monotonicity(assessment: MonotonicityAssessment) -> None:
    _require_member(assessment.status, MONOTONICITY_STATUSES, "status")
    _non_negative_integer(assessment.bucket_count, "bucket_count")
    _non_negative_integer(assessment.increasing_step_count, "increasing_step_count")
    _non_negative_integer(assessment.decreasing_step_count, "decreasing_step_count")
    for name in ("monotonic_increasing", "monotonic_decreasing"):
        if not isinstance(getattr(assessment, name), bool):
            raise PredictorDiagnosticsError(f"{name} must be a boolean")
    available = assessment.status == MONOTONICITY_AVAILABLE
    if available != (assessment.rank_correlation is not None):
        raise PredictorDiagnosticsError(
            "a rank correlation is present exactly when monotonicity is available"
        )
    if assessment.rank_correlation is not None and not (
        Decimal("-1") <= assessment.rank_correlation <= Decimal("1")
    ):
        raise PredictorDiagnosticsError("rank_correlation must fall in [-1, 1]")
    steps = max(assessment.bucket_count - 1, 0)
    if assessment.increasing_step_count + assessment.decreasing_step_count > steps:
        raise PredictorDiagnosticsError("step counts exceed the available steps")
    if assessment.monotonic_increasing and assessment.increasing_step_count != steps:
        raise PredictorDiagnosticsError(
            "a monotonic increase requires every step to increase"
        )
    if assessment.monotonic_decreasing and assessment.decreasing_step_count != steps:
        raise PredictorDiagnosticsError(
            "a monotonic decrease requires every step to decrease"
        )
    if not available and (
        assessment.increasing_step_count or assessment.decreasing_step_count
    ):
        raise PredictorDiagnosticsError(
            "an unavailable monotonicity assessment cannot report steps"
        )
    if not available and (
        assessment.monotonic_increasing or assessment.monotonic_decreasing
    ):
        raise PredictorDiagnosticsError(
            "an unavailable monotonicity assessment cannot claim monotonicity"
        )


def _validate_diagnostic(diagnostic: PredictorTargetDiagnostic) -> None:
    _require_member(diagnostic.scope, DIAGNOSTIC_SCOPES, "scope")
    _non_empty(diagnostic.segment, "segment")
    if diagnostic.scope == GLOBAL_SCOPE and diagnostic.segment != GLOBAL_SEGMENT:
        raise PredictorDiagnosticsError(
            f"a global diagnostic must use the {GLOBAL_SEGMENT} segment"
        )
    _non_empty(diagnostic.predictor_name, "predictor_name")
    _non_empty(diagnostic.target_name, "target_name")
    _require_member(diagnostic.predictor_kind, PREDICTOR_KINDS, "predictor_kind")
    _non_negative_integer(diagnostic.observed_row_count, "observed_row_count")
    _non_negative_integer(diagnostic.sample_size, "sample_size")
    if diagnostic.sample_size > diagnostic.observed_row_count:
        raise PredictorDiagnosticsError(
            "complete cases cannot exceed the rows observed in the segment"
        )
    _require_member(diagnostic.status, DIAGNOSTIC_STATUSES, "status")
    for estimate, method in (
        (diagnostic.pearson, PEARSON_METHOD),
        (diagnostic.spearman, SPEARMAN_METHOD),
    ):
        _validate_correlation_estimate(estimate)
        if estimate.method != method:
            raise PredictorDiagnosticsError(f"estimate method must be {method}")
        if estimate.sample_size != diagnostic.sample_size:
            raise PredictorDiagnosticsError(
                "estimate sample size must match the diagnostic sample size"
            )
        if estimate.status != diagnostic.status:
            raise PredictorDiagnosticsError(
                "both estimates share the diagnostic availability status"
            )
    _require_member(diagnostic.bucket_status, BUCKET_STATUSES, "bucket_status")
    if not isinstance(diagnostic.tied_bucket_boundaries, bool):
        raise PredictorDiagnosticsError("tied_bucket_boundaries must be a boolean")
    if diagnostic.bucket_status == BUCKET_AVAILABLE:
        if not diagnostic.buckets:
            raise PredictorDiagnosticsError(
                "available buckets must persist every bucket"
            )
        _validate_bucket_sequence(diagnostic.buckets, diagnostic.sample_size)
    elif diagnostic.buckets or diagnostic.tied_bucket_boundaries:
        raise PredictorDiagnosticsError(
            "unavailable buckets cannot persist buckets or boundary ties"
        )
    expected_ties = any(
        current.upper_predictor_value == following.lower_predictor_value
        for current, following in zip(diagnostic.buckets, diagnostic.buckets[1:])
    )
    if diagnostic.tied_bucket_boundaries != expected_ties:
        raise PredictorDiagnosticsError(
            "tied_bucket_boundaries does not match the persisted bucket bounds"
        )
    _validate_monotonicity(diagnostic.monotonicity)
    if diagnostic.monotonicity != _monotonicity(
        diagnostic.buckets, diagnostic.bucket_status
    ):
        raise PredictorDiagnosticsError(
            "monotonicity does not match the persisted bucket evidence"
        )


def _validate_bucket_sequence(
    buckets: Sequence[BucketStatistics] | Sequence[ExcursionBucket],
    sample_size: int,
) -> None:
    for index, bucket in enumerate(buckets):
        if bucket.ordinal != index + 1:
            raise PredictorDiagnosticsError("bucket ordinals must be sequential")
    if sum(bucket.sample_size for bucket in buckets) != sample_size:
        raise PredictorDiagnosticsError(
            "buckets must partition every complete case exactly once"
        )
    bounds = [
        (bucket.lower_predictor_value, bucket.upper_predictor_value)
        for bucket in buckets
    ]
    for (_, upper), (lower, _) in zip(bounds, bounds[1:]):
        if lower < upper:
            raise PredictorDiagnosticsError(
                "buckets must be ordered by ascending predictor value"
            )


def _validate_analysis(analysis: PredictorAnalysis) -> None:
    _validate_predictor_definition(analysis.definition)
    if not analysis.diagnostics:
        raise PredictorDiagnosticsError("a predictor analysis must not be empty")
    keys = tuple(
        (item.scope, item.segment, item.target_name) for item in analysis.diagnostics
    )
    if len(keys) != len(set(keys)):
        raise PredictorDiagnosticsError("diagnostic segments must be unique")
    for item in analysis.diagnostics:
        _validate_diagnostic(item)
        if item.predictor_name != analysis.definition.predictor_name:
            raise PredictorDiagnosticsError(
                "every diagnostic must name its own predictor"
            )
        if item.predictor_kind != analysis.definition.predictor_kind:
            raise PredictorDiagnosticsError(
                "every diagnostic must carry the declared predictor kind"
            )


def _validate_stability(summary: StabilitySummary) -> None:
    _require_member(summary.scope, (REGIME_SCOPE, SETUP_SCOPE), "scope")
    _non_empty(summary.predictor_name, "predictor_name")
    _non_empty(summary.target_name, "target_name")
    _require_member(summary.status, STABILITY_STATUSES, "status")
    _non_negative_integer(summary.segment_count, "segment_count")
    _non_negative_integer(
        summary.evaluated_segment_count, "evaluated_segment_count"
    )
    _non_negative_integer(summary.evaluated_sample_size, "evaluated_sample_size")
    if summary.evaluated_segment_count > summary.segment_count:
        raise PredictorDiagnosticsError(
            "evaluated segments cannot exceed the observed segments"
        )
    metrics = (
        summary.mean_coefficient,
        summary.minimum_coefficient,
        summary.maximum_coefficient,
        summary.sign_consistency,
    )
    if summary.status == STABILITY_AVAILABLE:
        if summary.evaluated_segment_count < 1:
            raise PredictorDiagnosticsError(
                "an available stability summary requires an evaluated segment"
            )
        if any(value is None for value in metrics):
            raise PredictorDiagnosticsError(
                "an available stability summary requires its aggregate metrics"
            )
        assert summary.minimum_coefficient is not None
        assert summary.maximum_coefficient is not None
        if summary.minimum_coefficient > summary.maximum_coefficient:
            raise PredictorDiagnosticsError(
                "stability coefficient bounds are not ordered"
            )
        if (summary.evaluated_segment_count >= 2) != (
            summary.coefficient_standard_deviation is not None
        ):
            raise PredictorDiagnosticsError(
                "coefficient dispersion requires at least two evaluated segments"
            )
    else:
        if summary.evaluated_segment_count or summary.evaluated_sample_size:
            raise PredictorDiagnosticsError(
                "an unevaluated stability summary cannot report evaluated segments"
            )
        if any(value is not None for value in metrics) or (
            summary.coefficient_standard_deviation is not None
        ):
            raise PredictorDiagnosticsError(
                "an unevaluated stability summary cannot persist metrics"
            )
    for name in ("mean_coefficient", "minimum_coefficient", "maximum_coefficient"):
        value = getattr(summary, name)
        if value is not None and not Decimal("-1") <= value <= Decimal("1"):
            raise PredictorDiagnosticsError(f"{name} must fall in [-1, 1]")
    if summary.sign_consistency is not None and not (
        Decimal("0") <= summary.sign_consistency <= Decimal("1")
    ):
        raise PredictorDiagnosticsError("sign_consistency must fall in [0, 1]")
    if summary.coefficient_standard_deviation is not None and (
        summary.coefficient_standard_deviation < 0
    ):
        raise PredictorDiagnosticsError(
            "coefficient_standard_deviation must be non-negative"
        )


def _validate_correlation_matrix(matrix: CorrelationMatrix) -> None:
    _require_member(matrix.method, CORRELATION_METHODS, "method")
    _require_member(matrix.status, MATRIX_STATUSES, "status")
    _non_negative_integer(matrix.sample_size, "sample_size")
    names = matrix.component_names
    if not names:
        raise PredictorDiagnosticsError("a correlation matrix requires components")
    if len(set(names)) != len(names):
        raise PredictorDiagnosticsError("component names must be unique")
    if matrix.empirical_note != MECHANICAL_VS_EMPIRICAL_NOTE:
        raise PredictorDiagnosticsError(
            "a correlation matrix must carry the empirical-versus-mechanical note"
        )
    if matrix.status != MATRIX_AVAILABLE:
        if matrix.coefficients:
            raise PredictorDiagnosticsError(
                "an unavailable correlation matrix cannot persist coefficients"
            )
        return
    if len(matrix.coefficients) != len(names) or any(
        len(row) != len(names) for row in matrix.coefficients
    ):
        raise PredictorDiagnosticsError(
            "an available correlation matrix must be square over its components"
        )
    for row_index, row in enumerate(matrix.coefficients):
        for column_index, value in enumerate(row):
            if value is None:
                continue
            if not isinstance(value, Decimal) or not value.is_finite():
                raise PredictorDiagnosticsError(
                    "correlation coefficients must be finite Decimals"
                )
            if not Decimal("-1") <= value <= Decimal("1"):
                raise PredictorDiagnosticsError(
                    "correlation coefficients must fall in [-1, 1]"
                )
            if value != matrix.coefficients[column_index][row_index]:
                raise PredictorDiagnosticsError(
                    "a correlation matrix must be symmetric"
                )


def _validate_concentration(concentration: FactorConcentration) -> None:
    _require_member(concentration.method, CORRELATION_METHODS, "method")
    _require_member(concentration.status, CONCENTRATION_STATUSES, "status")
    _non_negative_integer(concentration.sample_size, "sample_size")
    names = concentration.component_names
    if not names:
        raise PredictorDiagnosticsError("a concentration report requires components")
    if concentration.status != CONCENTRATION_AVAILABLE:
        if (
            concentration.eigenvalues
            or concentration.largest_eigenvalue_share is not None
            or concentration.effective_rank is not None
        ):
            raise PredictorDiagnosticsError(
                "an unavailable concentration report cannot persist metrics"
            )
        return
    if len(concentration.eigenvalues) != len(names):
        raise PredictorDiagnosticsError(
            "one eigenvalue is required for every declared component"
        )
    previous: Decimal | None = None
    for value in concentration.eigenvalues:
        if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
            raise PredictorDiagnosticsError(
                "eigenvalues must be finite and non-negative"
            )
        if previous is not None and value > previous:
            raise PredictorDiagnosticsError("eigenvalues must be descending")
        previous = value
    share = concentration.largest_eigenvalue_share
    rank = concentration.effective_rank
    if share is None or rank is None:
        raise PredictorDiagnosticsError(
            "an available concentration report requires its metrics"
        )
    if not Decimal("0") < share <= Decimal("1"):
        raise PredictorDiagnosticsError(
            "largest_eigenvalue_share must fall in (0, 1]"
        )
    if not Decimal("1") <= rank <= Decimal(len(names)):
        raise PredictorDiagnosticsError(
            "effective_rank must fall between one and the component count"
        )


def _validate_excursion_bucket(bucket: ExcursionBucket) -> None:
    _positive_integer(bucket.ordinal, "ordinal")
    _positive_integer(bucket.sample_size, "sample_size")
    for name in (
        "lower_predictor_value",
        "upper_predictor_value",
        "mean_favourable_excursion",
        "mean_adverse_excursion",
    ):
        value = getattr(bucket, name)
        if not isinstance(value, Decimal) or not value.is_finite():
            raise PredictorDiagnosticsError(f"{name} must be a finite Decimal")
    if bucket.lower_predictor_value > bucket.upper_predictor_value:
        raise PredictorDiagnosticsError("bucket predictor bounds are not ordered")


def _validate_excursion(relationship: ExcursionRelationship) -> None:
    _require_member(relationship.scope, DIAGNOSTIC_SCOPES, "scope")
    _non_empty(relationship.segment, "segment")
    if (
        relationship.scope == GLOBAL_SCOPE
        and relationship.segment != GLOBAL_SEGMENT
    ):
        raise PredictorDiagnosticsError(
            f"a global excursion must use the {GLOBAL_SEGMENT} segment"
        )
    _non_empty(relationship.predictor_name, "predictor_name")
    _non_empty(relationship.favourable_target_name, "favourable_target_name")
    _non_empty(relationship.adverse_target_name, "adverse_target_name")
    if relationship.favourable_target_name == relationship.adverse_target_name:
        raise PredictorDiagnosticsError(
            "favourable and adverse excursion targets must differ"
        )
    _non_negative_integer(relationship.sample_size, "sample_size")
    _require_member(
        relationship.status,
        (DIAGNOSTIC_AVAILABLE, DIAGNOSTIC_INSUFFICIENT_SAMPLES),
        "status",
    )
    _require_member(relationship.bucket_status, BUCKET_STATUSES, "bucket_status")
    for estimate in (
        relationship.favourable_rank_ic,
        relationship.adverse_rank_ic,
        relationship.excursion_rank_correlation,
    ):
        _validate_correlation_estimate(estimate)
        if estimate.method != SPEARMAN_METHOD:
            raise PredictorDiagnosticsError(
                "excursion relationships are measured as rank correlations"
            )
        if estimate.sample_size != relationship.sample_size:
            raise PredictorDiagnosticsError(
                "excursion estimates must share the paired sample size"
            )
    if relationship.bucket_status == BUCKET_AVAILABLE:
        if not relationship.buckets:
            raise PredictorDiagnosticsError(
                "available excursion buckets must be persisted"
            )
        for bucket in relationship.buckets:
            _validate_excursion_bucket(bucket)
        _validate_bucket_sequence(relationship.buckets, relationship.sample_size)
    elif relationship.buckets:
        raise PredictorDiagnosticsError(
            "unavailable excursion buckets cannot persist buckets"
        )


def _validate_effective_weights(decomposition: Mapping[str, Any]) -> None:
    expected = {
        "policy_version": EFFECTIVE_WEIGHT_POLICY_VERSION,
        "contracts_version": SCORING_CONTRACTS_VERSION,
        "retired_contracts_version": RETIRED_SCORING_CONTRACTS_VERSION,
        "parameter_status": SCORING_PARAMETER_STATUS,
    }
    for name, value in expected.items():
        if decomposition.get(name) != value:
            raise PredictorDiagnosticsError(
                f"effective weight decomposition {name} must be {value!r}"
            )
    report = decomposition.get("report")
    if not isinstance(report, Mapping):
        raise PredictorDiagnosticsError(
            "the effective weight decomposition must carry its BTC-129 report"
        )
    if report.get("mechanical_vs_empirical") != MECHANICAL_VS_EMPIRICAL_NOTE:
        raise PredictorDiagnosticsError(
            "the effective weight report must keep the mechanical-versus-empirical note"
        )
    composites = report.get("composites")
    if not isinstance(composites, Mapping) or not composites:
        raise PredictorDiagnosticsError(
            "the effective weight report must decompose at least one composite"
        )
    for name, entry in composites.items():
        if not isinstance(entry, Mapping):
            raise PredictorDiagnosticsError(
                f"composite {name!r} must carry a decomposition mapping"
            )
        for key in (
            "v1_1_declared_weights",
            "v1_1_effective_weights",
            "v1_2_declared_weights",
            "v1_2_effective_weights",
        ):
            if not isinstance(entry.get(key), Mapping) or not entry.get(key):
                raise PredictorDiagnosticsError(
                    f"composite {name!r} must report {key}"
                )
        for key in ("v1_1_mechanically_clean", "v1_2_mechanically_clean"):
            if not isinstance(entry.get(key), bool):
                raise PredictorDiagnosticsError(
                    f"composite {name!r} must declare {key}"
                )
    if set(decomposition) != {*expected, "report"}:
        raise PredictorDiagnosticsError(
            "the effective weight decomposition carries unknown keys"
        )


def _validate_spec(
    spec: PredictorDiagnosticsSpec, *, allow_empty_id: bool = False
) -> None:
    expected_versions = {
        "feature_id": PREDICTOR_DIAGNOSTICS_FEATURE_ID,
        "policy_version": PREDICTOR_DIAGNOSTICS_POLICY_VERSION,
        "ic_policy_version": IC_POLICY_VERSION,
        "rank_policy_version": RANK_POLICY_VERSION,
        "bootstrap_policy_version": BOOTSTRAP_POLICY_VERSION,
        "bootstrap_index_policy_version": BOOTSTRAP_INDEX_POLICY_VERSION,
        "bootstrap_percentile_policy_version": (
            BOOTSTRAP_PERCENTILE_POLICY_VERSION
        ),
        "bucket_policy_version": BUCKET_POLICY_VERSION,
        "monotonicity_policy_version": MONOTONICITY_POLICY_VERSION,
        "stability_policy_version": STABILITY_POLICY_VERSION,
        "concentration_policy_version": CONCENTRATION_POLICY_VERSION,
        "excursion_policy_version": EXCURSION_POLICY_VERSION,
        "effective_weight_policy_version": EFFECTIVE_WEIGHT_POLICY_VERSION,
        "missing_value_policy_version": DIAGNOSTICS_MISSING_VALUE_POLICY_VERSION,
        "context_policy_version": DIAGNOSTICS_CONTEXT_POLICY_VERSION,
        "target_separation_policy_version": TARGET_SEPARATION_POLICY_VERSION,
        "promotion_policy_version": DIAGNOSTICS_PROMOTION_POLICY_VERSION,
    }
    for name, expected in expected_versions.items():
        if getattr(spec, name) != expected:
            raise PredictorDiagnosticsError(f"{name} must be {expected!r}")
    if not allow_empty_id:
        _non_empty(spec.spec_id, "spec_id")
    if not spec.predictors:
        raise PredictorDiagnosticsError("at least one predictor is required")
    for definition in spec.predictors:
        _validate_predictor_definition(definition)
    names = tuple(item.predictor_name for item in spec.predictors)
    if len(set(names)) != len(names):
        raise PredictorDiagnosticsError("predictor names must be unique")
    kinds = {item.predictor_kind for item in spec.predictors}
    if kinds != set(PREDICTOR_KINDS):
        raise PredictorDiagnosticsError(
            "a diagnostics report must declare both raw features and composite "
            "scores so the two can be compared"
        )
    targets = _string_tuple(spec.target_names, "target_names")
    if not targets:
        raise PredictorDiagnosticsError("at least one target is required")
    if len(set(targets)) != len(targets):
        raise PredictorDiagnosticsError("target names must be unique")
    components = _string_tuple(spec.component_predictors, "component_predictors")
    if not components:
        raise PredictorDiagnosticsError("at least one direct component is required")
    if len(set(components)) != len(components):
        raise PredictorDiagnosticsError("component predictors must be unique")
    missing = sorted(set(components) - set(names))
    if missing:
        raise PredictorDiagnosticsError(
            "component predictors must be declared predictors: " + ", ".join(missing)
        )
    if spec.conviction_predictor not in names:
        raise PredictorDiagnosticsError(
            "conviction_predictor must be a declared predictor"
        )
    if spec.predictor(spec.conviction_predictor).predictor_kind != (
        COMPOSITE_SCORE_PREDICTOR
    ):
        raise PredictorDiagnosticsError(
            "conviction_predictor must be a declared composite score"
        )
    for name in ("favourable_target_name", "adverse_target_name"):
        value = _non_empty(getattr(spec, name), name)
        if value not in targets:
            raise PredictorDiagnosticsError(f"{name} must be a declared target")
    if spec.favourable_target_name == spec.adverse_target_name:
        raise PredictorDiagnosticsError(
            "the favourable and adverse excursion targets must differ"
        )
    _positive_integer(spec.bucket_count, "bucket_count")
    if spec.bucket_count < 2:
        raise PredictorDiagnosticsError("bucket_count must be at least two")
    _positive_integer(spec.minimum_sample_size, "minimum_sample_size")
    if spec.minimum_sample_size < max(3, spec.bucket_count):
        raise PredictorDiagnosticsError(
            "minimum_sample_size must cover at least three rows and every bucket"
        )
    _positive_integer(spec.bootstrap_resamples, "bootstrap_resamples")
    _confidence(spec.bootstrap_confidence)
    _non_negative_integer(spec.seed, "seed")


def _validate_inputs(
    features: PointInTimeFeatureMatrix,
    targets: ForwardTargetMatrix,
    contexts: tuple[DiagnosticContext, ...],
    spec: PredictorDiagnosticsSpec,
) -> None:
    if not features.decision_timestamps:
        raise PredictorDiagnosticsError("the feature matrix must contain rows")
    if features.decision_timestamps != targets.decision_timestamps:
        raise PredictorDiagnosticsError(
            "feature and target decision timestamps must match exactly"
        )
    feature_names = set(features.definition.feature_names)
    missing = sorted(
        {item.predictor_name for item in spec.predictors} - feature_names
    )
    if missing:
        raise PredictorDiagnosticsError(
            "feature matrix does not contain declared predictors: "
            + ", ".join(missing)
        )
    target_names = set(targets.definition.target_names)
    missing_targets = sorted(set(spec.target_names) - target_names)
    if missing_targets:
        raise PredictorDiagnosticsError(
            "target matrix does not contain declared targets: "
            + ", ".join(missing_targets)
        )
    overlap = sorted(feature_names & target_names)
    if overlap:
        raise PredictorDiagnosticsError(
            "forward targets must stay outside the contemporaneous feature "
            "matrix: " + ", ".join(overlap)
        )
    if any(not isinstance(item, DiagnosticContext) for item in contexts):
        raise TypeError("contexts must contain DiagnosticContext values")
    if tuple(item.decision_timestamp for item in contexts) != (
        features.decision_timestamps
    ):
        raise PredictorDiagnosticsError(
            "contexts must match feature decision timestamps exactly and in order"
        )
    provenance = features.definition.provenance
    for name in spec.target_names:
        specification = targets.definition.specification(name)
        if (
            specification.price_source_policy_version
            != provenance.price_source_policy_version
        ):
            raise PredictorDiagnosticsError(
                "target price-source policy must match feature-matrix provenance"
            )


def _validate_report(report: PredictorDiagnosticsReport) -> None:
    report.spec.as_record()
    _non_empty(report.report_id, "report_id")
    for name in (
        "feature_definition_fingerprint",
        "target_definition_fingerprint",
        "input_digest",
        "context_digest",
    ):
        value = _non_empty(getattr(report, name), name)
        if len(value) != 64:
            raise PredictorDiagnosticsError(f"{name} must be a SHA-256 digest")
    if report.feature_definition.get("fingerprint") != (
        report.feature_definition_fingerprint
    ):
        raise PredictorDiagnosticsError(
            "feature definition fingerprint does not match the definition"
        )
    if report.target_definition.get("fingerprint") != (
        report.target_definition_fingerprint
    ):
        raise PredictorDiagnosticsError(
            "target definition fingerprint does not match the definition"
        )
    if report.production_status != DIAGNOSTICS_PRODUCTION_STATUS:
        raise PredictorDiagnosticsError(
            "predictor diagnostics must remain research-only"
        )
    if report.promotion_ticket != DIAGNOSTICS_PROMOTION_TICKET:
        raise PredictorDiagnosticsError(
            "predictor diagnostics must require BTC-193 promotion"
        )
    regimes = _string_tuple(report.observed_regimes, "observed_regimes")
    setups = _string_tuple(report.observed_setups, "observed_setups")
    for name, values in (("observed_regimes", regimes), ("observed_setups", setups)):
        if not values:
            raise PredictorDiagnosticsError(f"{name} must not be empty")
        if tuple(sorted(set(values))) != values:
            raise PredictorDiagnosticsError(f"{name} must be sorted and unique")
    if tuple(item.definition for item in report.analyses) != report.spec.predictors:
        raise PredictorDiagnosticsError(
            "analyses must match the declared predictors and order"
        )
    expected_segments = (
        (GLOBAL_SCOPE, GLOBAL_SEGMENT),
        *((REGIME_SCOPE, value) for value in regimes),
        *((SETUP_SCOPE, value) for value in setups),
    )
    expected_keys = tuple(
        (scope, segment, target)
        for scope, segment in expected_segments
        for target in report.spec.target_names
    )
    for analysis in report.analyses:
        _validate_analysis(analysis)
        keys = tuple(
            (item.scope, item.segment, item.target_name)
            for item in analysis.diagnostics
        )
        if keys != expected_keys:
            raise PredictorDiagnosticsError(
                "every predictor must report every observed segment and target"
            )
    expected_stability = tuple(
        (scope, definition.predictor_name, target)
        for definition in report.spec.predictors
        for target in report.spec.target_names
        for scope in (REGIME_SCOPE, SETUP_SCOPE)
    )
    stability_keys = tuple(
        (item.scope, item.predictor_name, item.target_name)
        for item in report.stability
    )
    if stability_keys != expected_stability:
        raise PredictorDiagnosticsError(
            "regime and setup stability must cover every predictor and target"
        )
    for summary in report.stability:
        _validate_stability(summary)
        expected_count = (
            len(regimes) if summary.scope == REGIME_SCOPE else len(setups)
        )
        if summary.segment_count != expected_count:
            raise PredictorDiagnosticsError(
                "a stability summary must count every observed segment"
            )
    if tuple(item.method for item in report.correlation_matrices) != (
        CORRELATION_METHODS
    ):
        raise PredictorDiagnosticsError(
            "both the direct-component and rank correlation matrices are required"
        )
    for matrix in report.correlation_matrices:
        _validate_correlation_matrix(matrix)
        if matrix.component_names != report.spec.component_predictors:
            raise PredictorDiagnosticsError(
                "correlation matrices must cover the declared components"
            )
    _validate_concentration(report.concentration)
    if report.concentration.method != PEARSON_METHOD:
        raise PredictorDiagnosticsError(
            "factor concentration is measured on the direct-component matrix"
        )
    if report.concentration.component_names != report.spec.component_predictors:
        raise PredictorDiagnosticsError(
            "factor concentration must cover the declared components"
        )
    _validate_effective_weights(report.effective_weight_decomposition)
    expected_excursions = tuple(
        (definition.predictor_name, scope, segment)
        for definition in report.spec.predictors
        for scope, segment in expected_segments
    )
    excursion_keys = tuple(
        (item.predictor_name, item.scope, item.segment) for item in report.excursions
    )
    if excursion_keys != expected_excursions:
        raise PredictorDiagnosticsError(
            "excursion relationships must cover every predictor and segment"
        )
    for relationship in report.excursions:
        _validate_excursion(relationship)
        if (
            relationship.favourable_target_name != report.spec.favourable_target_name
            or relationship.adverse_target_name != report.spec.adverse_target_name
        ):
            raise PredictorDiagnosticsError(
                "excursion relationships must use the declared excursion targets"
            )
    if report.reason_codes != PREDICTOR_DIAGNOSTICS_REASON_CODES:
        raise PredictorDiagnosticsError(
            "predictor diagnostics reason codes do not match policy"
        )
    if report.report_id != _report_id(report):
        raise PredictorDiagnosticsError(
            "predictor diagnostics report does not match report_id"
        )


def _spec_payload(spec: PredictorDiagnosticsSpec) -> dict[str, Any]:
    return {
        "feature_id": spec.feature_id,
        "policy_version": spec.policy_version,
        "ic_policy_version": spec.ic_policy_version,
        "rank_policy_version": spec.rank_policy_version,
        "bootstrap_policy_version": spec.bootstrap_policy_version,
        "bootstrap_index_policy_version": spec.bootstrap_index_policy_version,
        "bootstrap_percentile_policy_version": (
            spec.bootstrap_percentile_policy_version
        ),
        "bucket_policy_version": spec.bucket_policy_version,
        "monotonicity_policy_version": spec.monotonicity_policy_version,
        "stability_policy_version": spec.stability_policy_version,
        "concentration_policy_version": spec.concentration_policy_version,
        "excursion_policy_version": spec.excursion_policy_version,
        "effective_weight_policy_version": spec.effective_weight_policy_version,
        "missing_value_policy_version": spec.missing_value_policy_version,
        "context_policy_version": spec.context_policy_version,
        "target_separation_policy_version": spec.target_separation_policy_version,
        "promotion_policy_version": spec.promotion_policy_version,
        "predictors": [item.as_record() for item in spec.predictors],
        "target_names": list(spec.target_names),
        "component_predictors": list(spec.component_predictors),
        "conviction_predictor": spec.conviction_predictor,
        "favourable_target_name": spec.favourable_target_name,
        "adverse_target_name": spec.adverse_target_name,
        "bucket_count": spec.bucket_count,
        "minimum_sample_size": spec.minimum_sample_size,
        "bootstrap_resamples": spec.bootstrap_resamples,
        "bootstrap_confidence": str(spec.bootstrap_confidence),
        "seed": spec.seed,
    }


def _report_id(report: PredictorDiagnosticsReport) -> str:
    return _digest(
        {
            "feature_id": report.spec.feature_id,
            "policy_version": report.spec.policy_version,
            "spec_id": report.spec.spec_id,
            "input_digest": report.input_digest,
        }
    )


def _report_payload(report: PredictorDiagnosticsReport) -> dict[str, Any]:
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
        "observed_regimes": list(report.observed_regimes),
        "observed_setups": list(report.observed_setups),
        "analyses": [item.as_record() for item in report.analyses],
        "stability": [item.as_record() for item in report.stability],
        "correlation_matrices": [
            item.as_record() for item in report.correlation_matrices
        ],
        "concentration": report.concentration.as_record(),
        "effective_weight_decomposition": report.effective_weight_decomposition,
        "excursions": [item.as_record() for item in report.excursions],
        "reason_codes": list(report.reason_codes),
    }


def _spec_from_record(record: Mapping[str, Any]) -> PredictorDiagnosticsSpec:
    spec = PredictorDiagnosticsSpec(
        feature_id=_string(record.get("feature_id"), "feature_id"),
        policy_version=_string(record.get("policy_version"), "policy_version"),
        ic_policy_version=_string(
            record.get("ic_policy_version"), "ic_policy_version"
        ),
        rank_policy_version=_string(
            record.get("rank_policy_version"), "rank_policy_version"
        ),
        bootstrap_policy_version=_string(
            record.get("bootstrap_policy_version"), "bootstrap_policy_version"
        ),
        bootstrap_index_policy_version=_string(
            record.get("bootstrap_index_policy_version"),
            "bootstrap_index_policy_version",
        ),
        bootstrap_percentile_policy_version=_string(
            record.get("bootstrap_percentile_policy_version"),
            "bootstrap_percentile_policy_version",
        ),
        bucket_policy_version=_string(
            record.get("bucket_policy_version"), "bucket_policy_version"
        ),
        monotonicity_policy_version=_string(
            record.get("monotonicity_policy_version"), "monotonicity_policy_version"
        ),
        stability_policy_version=_string(
            record.get("stability_policy_version"), "stability_policy_version"
        ),
        concentration_policy_version=_string(
            record.get("concentration_policy_version"),
            "concentration_policy_version",
        ),
        excursion_policy_version=_string(
            record.get("excursion_policy_version"), "excursion_policy_version"
        ),
        effective_weight_policy_version=_string(
            record.get("effective_weight_policy_version"),
            "effective_weight_policy_version",
        ),
        missing_value_policy_version=_string(
            record.get("missing_value_policy_version"),
            "missing_value_policy_version",
        ),
        context_policy_version=_string(
            record.get("context_policy_version"), "context_policy_version"
        ),
        target_separation_policy_version=_string(
            record.get("target_separation_policy_version"),
            "target_separation_policy_version",
        ),
        promotion_policy_version=_string(
            record.get("promotion_policy_version"), "promotion_policy_version"
        ),
        spec_id=_string(record.get("spec_id"), "spec_id"),
        predictors=tuple(
            _predictor_from_record(_mapping(item, "predictor"))
            for item in _sequence(record.get("predictors"), "predictors")
        ),
        target_names=_string_tuple(record.get("target_names"), "target_names"),
        component_predictors=_string_tuple(
            record.get("component_predictors"), "component_predictors"
        ),
        conviction_predictor=_string(
            record.get("conviction_predictor"), "conviction_predictor"
        ),
        favourable_target_name=_string(
            record.get("favourable_target_name"), "favourable_target_name"
        ),
        adverse_target_name=_string(
            record.get("adverse_target_name"), "adverse_target_name"
        ),
        bucket_count=_positive_integer(record.get("bucket_count"), "bucket_count"),
        minimum_sample_size=_positive_integer(
            record.get("minimum_sample_size"), "minimum_sample_size"
        ),
        bootstrap_resamples=_positive_integer(
            record.get("bootstrap_resamples"), "bootstrap_resamples"
        ),
        bootstrap_confidence=_decimal_from_record(
            record.get("bootstrap_confidence"), "bootstrap_confidence"
        ),
        seed=_non_negative_integer(record.get("seed"), "seed"),
    )
    if spec.as_record() != dict(record):
        raise PredictorDiagnosticsError(
            "record does not match the reconstructed diagnostics specification"
        )
    return spec


def _predictor_from_record(record: Mapping[str, Any]) -> PredictorDefinition:
    definition = PredictorDefinition(
        predictor_name=_string(record.get("predictor_name"), "predictor_name"),
        predictor_kind=_string(record.get("predictor_kind"), "predictor_kind"),
        display_name=_string(record.get("display_name"), "display_name"),
    )
    if definition.as_record() != dict(record):
        raise PredictorDiagnosticsError("record does not match predictor definition")
    return definition


def _estimate_from_record(record: Mapping[str, Any]) -> CorrelationEstimate:
    estimate = CorrelationEstimate(
        method=_string(record.get("method"), "method"),
        sample_size=_non_negative_integer(record.get("sample_size"), "sample_size"),
        status=_string(record.get("status"), "status"),
        coefficient=_decimal_or_none(record.get("coefficient"), "coefficient"),
        confidence=_decimal_from_record(record.get("confidence"), "confidence"),
        interval_status=_string(
            record.get("interval_status"), "interval_status"
        ),
        lower_bound=_decimal_or_none(record.get("lower_bound"), "lower_bound"),
        upper_bound=_decimal_or_none(record.get("upper_bound"), "upper_bound"),
        resample_count=_non_negative_integer(
            record.get("resample_count"), "resample_count"
        ),
        defined_resample_count=_non_negative_integer(
            record.get("defined_resample_count"), "defined_resample_count"
        ),
    )
    if estimate.as_record() != dict(record):
        raise PredictorDiagnosticsError("record does not match correlation estimate")
    return estimate


def _bucket_from_record(record: Mapping[str, Any]) -> BucketStatistics:
    bucket = BucketStatistics(
        ordinal=_positive_integer(record.get("ordinal"), "ordinal"),
        sample_size=_positive_integer(record.get("sample_size"), "sample_size"),
        lower_predictor_value=_decimal_from_record(
            record.get("lower_predictor_value"), "lower_predictor_value"
        ),
        upper_predictor_value=_decimal_from_record(
            record.get("upper_predictor_value"), "upper_predictor_value"
        ),
        mean_predictor_value=_decimal_from_record(
            record.get("mean_predictor_value"), "mean_predictor_value"
        ),
        mean_target_value=_decimal_from_record(
            record.get("mean_target_value"), "mean_target_value"
        ),
        positive_target_fraction=_decimal_from_record(
            record.get("positive_target_fraction"), "positive_target_fraction"
        ),
    )
    if bucket.as_record() != dict(record):
        raise PredictorDiagnosticsError("record does not match bucket statistics")
    return bucket


def _monotonicity_from_record(
    record: Mapping[str, Any],
) -> MonotonicityAssessment:
    assessment = MonotonicityAssessment(
        status=_string(record.get("status"), "status"),
        bucket_count=_non_negative_integer(
            record.get("bucket_count"), "bucket_count"
        ),
        rank_correlation=_decimal_or_none(
            record.get("rank_correlation"), "rank_correlation"
        ),
        increasing_step_count=_non_negative_integer(
            record.get("increasing_step_count"), "increasing_step_count"
        ),
        decreasing_step_count=_non_negative_integer(
            record.get("decreasing_step_count"), "decreasing_step_count"
        ),
        monotonic_increasing=_boolean(
            record.get("monotonic_increasing"), "monotonic_increasing"
        ),
        monotonic_decreasing=_boolean(
            record.get("monotonic_decreasing"), "monotonic_decreasing"
        ),
    )
    if assessment.as_record() != dict(record):
        raise PredictorDiagnosticsError(
            "record does not match the monotonicity assessment"
        )
    return assessment


def _diagnostic_from_record(
    record: Mapping[str, Any],
) -> PredictorTargetDiagnostic:
    diagnostic = PredictorTargetDiagnostic(
        scope=_string(record.get("scope"), "scope"),
        segment=_string(record.get("segment"), "segment"),
        predictor_name=_string(record.get("predictor_name"), "predictor_name"),
        predictor_kind=_string(record.get("predictor_kind"), "predictor_kind"),
        target_name=_string(record.get("target_name"), "target_name"),
        observed_row_count=_non_negative_integer(
            record.get("observed_row_count"), "observed_row_count"
        ),
        sample_size=_non_negative_integer(record.get("sample_size"), "sample_size"),
        status=_string(record.get("status"), "status"),
        pearson=_estimate_from_record(_mapping(record.get("pearson"), "pearson")),
        spearman=_estimate_from_record(_mapping(record.get("spearman"), "spearman")),
        bucket_status=_string(record.get("bucket_status"), "bucket_status"),
        tied_bucket_boundaries=_boolean(
            record.get("tied_bucket_boundaries"), "tied_bucket_boundaries"
        ),
        buckets=tuple(
            _bucket_from_record(_mapping(item, "bucket"))
            for item in _sequence(record.get("buckets"), "buckets")
        ),
        monotonicity=_monotonicity_from_record(
            _mapping(record.get("monotonicity"), "monotonicity")
        ),
    )
    if diagnostic.as_record() != dict(record):
        raise PredictorDiagnosticsError("record does not match the diagnostic")
    return diagnostic


def _analysis_from_record(record: Mapping[str, Any]) -> PredictorAnalysis:
    analysis = PredictorAnalysis(
        definition=_predictor_from_record(
            _mapping(record.get("definition"), "definition")
        ),
        diagnostics=tuple(
            _diagnostic_from_record(_mapping(item, "diagnostic"))
            for item in _sequence(record.get("diagnostics"), "diagnostics")
        ),
    )
    if analysis.as_record() != dict(record):
        raise PredictorDiagnosticsError("record does not match predictor analysis")
    return analysis


def _stability_from_record(record: Mapping[str, Any]) -> StabilitySummary:
    summary = StabilitySummary(
        scope=_string(record.get("scope"), "scope"),
        predictor_name=_string(record.get("predictor_name"), "predictor_name"),
        target_name=_string(record.get("target_name"), "target_name"),
        status=_string(record.get("status"), "status"),
        segment_count=_non_negative_integer(
            record.get("segment_count"), "segment_count"
        ),
        evaluated_segment_count=_non_negative_integer(
            record.get("evaluated_segment_count"), "evaluated_segment_count"
        ),
        evaluated_sample_size=_non_negative_integer(
            record.get("evaluated_sample_size"), "evaluated_sample_size"
        ),
        mean_coefficient=_decimal_or_none(
            record.get("mean_coefficient"), "mean_coefficient"
        ),
        coefficient_standard_deviation=_decimal_or_none(
            record.get("coefficient_standard_deviation"),
            "coefficient_standard_deviation",
        ),
        minimum_coefficient=_decimal_or_none(
            record.get("minimum_coefficient"), "minimum_coefficient"
        ),
        maximum_coefficient=_decimal_or_none(
            record.get("maximum_coefficient"), "maximum_coefficient"
        ),
        sign_consistency=_decimal_or_none(
            record.get("sign_consistency"), "sign_consistency"
        ),
    )
    if summary.as_record() != dict(record):
        raise PredictorDiagnosticsError("record does not match stability summary")
    return summary


def _matrix_from_record(record: Mapping[str, Any]) -> CorrelationMatrix:
    matrix = CorrelationMatrix(
        method=_string(record.get("method"), "method"),
        component_names=_string_tuple(
            record.get("component_names"), "component_names"
        ),
        sample_size=_non_negative_integer(record.get("sample_size"), "sample_size"),
        status=_string(record.get("status"), "status"),
        coefficients=tuple(
            tuple(
                _decimal_or_none(value, "coefficient")
                for value in _sequence(row, "coefficient_row")
            )
            for row in _sequence(record.get("coefficients"), "coefficients")
        ),
        empirical_note=_string(record.get("empirical_note"), "empirical_note"),
    )
    if matrix.as_record() != dict(record):
        raise PredictorDiagnosticsError("record does not match correlation matrix")
    return matrix


def _concentration_from_record(record: Mapping[str, Any]) -> FactorConcentration:
    concentration = FactorConcentration(
        method=_string(record.get("method"), "method"),
        component_names=_string_tuple(
            record.get("component_names"), "component_names"
        ),
        sample_size=_non_negative_integer(record.get("sample_size"), "sample_size"),
        status=_string(record.get("status"), "status"),
        eigenvalues=tuple(
            _decimal_from_record(value, "eigenvalue")
            for value in _sequence(record.get("eigenvalues"), "eigenvalues")
        ),
        largest_eigenvalue_share=_decimal_or_none(
            record.get("largest_eigenvalue_share"), "largest_eigenvalue_share"
        ),
        effective_rank=_decimal_or_none(
            record.get("effective_rank"), "effective_rank"
        ),
    )
    if concentration.as_record() != dict(record):
        raise PredictorDiagnosticsError("record does not match factor concentration")
    return concentration


def _excursion_bucket_from_record(record: Mapping[str, Any]) -> ExcursionBucket:
    bucket = ExcursionBucket(
        ordinal=_positive_integer(record.get("ordinal"), "ordinal"),
        sample_size=_positive_integer(record.get("sample_size"), "sample_size"),
        lower_predictor_value=_decimal_from_record(
            record.get("lower_predictor_value"), "lower_predictor_value"
        ),
        upper_predictor_value=_decimal_from_record(
            record.get("upper_predictor_value"), "upper_predictor_value"
        ),
        mean_favourable_excursion=_decimal_from_record(
            record.get("mean_favourable_excursion"), "mean_favourable_excursion"
        ),
        mean_adverse_excursion=_decimal_from_record(
            record.get("mean_adverse_excursion"), "mean_adverse_excursion"
        ),
    )
    if bucket.as_record() != dict(record):
        raise PredictorDiagnosticsError("record does not match excursion bucket")
    return bucket


def _excursion_from_record(record: Mapping[str, Any]) -> ExcursionRelationship:
    relationship = ExcursionRelationship(
        scope=_string(record.get("scope"), "scope"),
        segment=_string(record.get("segment"), "segment"),
        predictor_name=_string(record.get("predictor_name"), "predictor_name"),
        favourable_target_name=_string(
            record.get("favourable_target_name"), "favourable_target_name"
        ),
        adverse_target_name=_string(
            record.get("adverse_target_name"), "adverse_target_name"
        ),
        sample_size=_non_negative_integer(record.get("sample_size"), "sample_size"),
        status=_string(record.get("status"), "status"),
        bucket_status=_string(record.get("bucket_status"), "bucket_status"),
        buckets=tuple(
            _excursion_bucket_from_record(_mapping(item, "excursion_bucket"))
            for item in _sequence(record.get("buckets"), "buckets")
        ),
        favourable_rank_ic=_estimate_from_record(
            _mapping(record.get("favourable_rank_ic"), "favourable_rank_ic")
        ),
        adverse_rank_ic=_estimate_from_record(
            _mapping(record.get("adverse_rank_ic"), "adverse_rank_ic")
        ),
        excursion_rank_correlation=_estimate_from_record(
            _mapping(
                record.get("excursion_rank_correlation"),
                "excursion_rank_correlation",
            )
        ),
    )
    if relationship.as_record() != dict(record):
        raise PredictorDiagnosticsError(
            "record does not match the excursion relationship"
        )
    return relationship


def _non_empty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PredictorDiagnosticsError(f"{name} must be a non-empty string")
    return value


def _string(value: Any, name: str) -> str:
    return _non_empty(value, name)


def _require_member(value: Any, allowed: Sequence[str], name: str) -> str:
    text = _non_empty(value, name)
    if text not in allowed:
        raise PredictorDiagnosticsError(f"{name} must be one of {tuple(allowed)}")
    return text


def _boolean(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise PredictorDiagnosticsError(f"{name} must be a boolean")
    return value


def _positive_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PredictorDiagnosticsError(f"{name} must be a positive integer")
    return value


def _non_negative_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PredictorDiagnosticsError(f"{name} must be a non-negative integer")
    return value


def _decimal_from_record(value: Any, name: str) -> Decimal:
    if not isinstance(value, str):
        raise PredictorDiagnosticsError(f"{name} must be a decimal string")
    try:
        result = Decimal(value)
    except ArithmeticError as error:
        raise PredictorDiagnosticsError(f"{name} must be a decimal string") from error
    if not result.is_finite():
        raise PredictorDiagnosticsError(f"{name} must be finite")
    return result


def _decimal_or_none(value: Any, name: str) -> Decimal | None:
    return None if value is None else _decimal_from_record(value, name)


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PredictorDiagnosticsError(f"{name} must be a mapping")
    return value


def _sequence(value: Any, name: str) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise PredictorDiagnosticsError(f"{name} must be a sequence")
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
    "BOOTSTRAP_INDEX_POLICY_VERSION",
    "BOOTSTRAP_PERCENTILE_POLICY_VERSION",
    "BOOTSTRAP_POLICY_VERSION",
    "BUCKET_AVAILABLE",
    "BUCKET_INSUFFICIENT_SAMPLES",
    "BUCKET_POLICY_VERSION",
    "BUCKET_STATUSES",
    "COMPOSITE_SCORE_PREDICTOR",
    "CONCENTRATION_AVAILABLE",
    "CONCENTRATION_INSUFFICIENT_SAMPLES",
    "CONCENTRATION_POLICY_VERSION",
    "CONCENTRATION_STATUSES",
    "CONCENTRATION_ZERO_VARIANCE_COMPONENT",
    "CORRELATION_METHODS",
    "DIAGNOSTICS_CONTEXT_POLICY_VERSION",
    "DIAGNOSTICS_MISSING_VALUE_POLICY_VERSION",
    "DIAGNOSTICS_PRODUCTION_STATUS",
    "DIAGNOSTICS_PROMOTION_POLICY_VERSION",
    "DIAGNOSTICS_PROMOTION_TICKET",
    "DIAGNOSTIC_SCOPES",
    "DIAGNOSTIC_STATUSES",
    "EFFECTIVE_WEIGHT_POLICY_VERSION",
    "DIAGNOSTIC_AVAILABLE",
    "DIAGNOSTIC_INSUFFICIENT_SAMPLES",
    "DIAGNOSTIC_ZERO_VARIANCE_PREDICTOR",
    "DIAGNOSTIC_ZERO_VARIANCE_TARGET",
    "EXCURSION_POLICY_VERSION",
    "GLOBAL_SCOPE",
    "GLOBAL_SEGMENT",
    "IC_POLICY_VERSION",
    "INTERVAL_AVAILABLE",
    "INTERVAL_NOT_ESTIMATED",
    "INTERVAL_STATUSES",
    "INTERVAL_UNDEFINED_RESAMPLES",
    "MATRIX_AVAILABLE",
    "MATRIX_INSUFFICIENT_SAMPLES",
    "MATRIX_STATUSES",
    "MONOTONICITY_AVAILABLE",
    "MONOTONICITY_CONSTANT_BUCKET_MEANS",
    "MONOTONICITY_INSUFFICIENT_BUCKETS",
    "MONOTONICITY_POLICY_VERSION",
    "MONOTONICITY_STATUSES",
    "PEARSON_METHOD",
    "PREDICTOR_DIAGNOSTICS_FEATURE_ID",
    "PREDICTOR_DIAGNOSTICS_POLICY_VERSION",
    "PREDICTOR_DIAGNOSTICS_REASON_CODES",
    "PREDICTOR_KINDS",
    "RANK_POLICY_VERSION",
    "RAW_FEATURE_PREDICTOR",
    "REGIME_SCOPE",
    "SETUP_SCOPE",
    "SPEARMAN_METHOD",
    "STABILITY_AVAILABLE",
    "STABILITY_NO_EVALUATED_SEGMENTS",
    "STABILITY_POLICY_VERSION",
    "STABILITY_STATUSES",
    "TARGET_SEPARATION_POLICY_VERSION",
    "BucketStatistics",
    "CorrelationEstimate",
    "CorrelationMatrix",
    "DiagnosticContext",
    "ExcursionBucket",
    "ExcursionRelationship",
    "FactorConcentration",
    "MonotonicityAssessment",
    "PredictorAnalysis",
    "PredictorDefinition",
    "PredictorDiagnosticsError",
    "PredictorDiagnosticsReport",
    "PredictorDiagnosticsSpec",
    "PredictorTargetDiagnostic",
    "StabilitySummary",
    "predictor_diagnostics_spec",
    "restore_predictor_diagnostics_report",
    "run_predictor_diagnostics",
]
