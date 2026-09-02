"""BTC-189: statistical predictor diagnostics for features and scores."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.features.scoring_contracts import (
    MECHANICAL_VS_EMPIRICAL_NOTE,
    SCORING_CONTRACTS_VERSION,
    effective_weight_report,
)
from btc_predictor.research import (
    BUCKET_AVAILABLE,
    BUCKET_INSUFFICIENT_SAMPLES,
    COMPOSITE_SCORE_PREDICTOR,
    CONCENTRATION_AVAILABLE,
    DIAGNOSTIC_AVAILABLE,
    DIAGNOSTIC_INSUFFICIENT_SAMPLES,
    DIAGNOSTIC_ZERO_VARIANCE_PREDICTOR,
    DIAGNOSTIC_ZERO_VARIANCE_TARGET,
    DIAGNOSTICS_PRODUCTION_STATUS,
    DIAGNOSTICS_PROMOTION_TICKET,
    EFFECTIVE_WEIGHT_POLICY_VERSION,
    GLOBAL_SCOPE,
    GLOBAL_SEGMENT,
    INTERVAL_AVAILABLE,
    INTERVAL_NOT_ESTIMATED,
    MATRIX_AVAILABLE,
    MONOTONICITY_AVAILABLE,
    PEARSON_METHOD,
    PREDICTOR_DIAGNOSTICS_FEATURE_ID,
    PREDICTOR_DIAGNOSTICS_POLICY_VERSION,
    PREDICTOR_DIAGNOSTICS_REASON_CODES,
    RAW_FEATURE_PREDICTOR,
    REGIME_SCOPE,
    SETUP_SCOPE,
    SPEARMAN_METHOD,
    STABILITY_AVAILABLE,
    DiagnosticContext,
    FeatureMatrixDefinition,
    FeatureObservation,
    ForwardTargetObservation,
    PredictorDefinition,
    PredictorDiagnosticsError,
    build_forward_target_matrix,
    build_point_in_time_feature_matrix,
    predictor_diagnostics_spec,
    restore_predictor_diagnostics_report,
    run_predictor_diagnostics,
)


START = datetime(2024, 1, 1, tzinfo=UTC)
CONVICTION = "ENTRY_CONVICTION_SCORE"
FEATURE_NAMES = (
    CONVICTION,
    "TREND_SCORE",
    "FLOW_SCORE",
    "MOMENTUM_4W",
)
FEATURE_DEFINITION = FeatureMatrixDefinition(
    feature_names=FEATURE_NAMES,
    version="BTC_189_TEST_FEATURES_V1",
)
RETURN_TARGET = "future_4w_return"
FAVOURABLE_TARGET = "future_MFE"
ADVERSE_TARGET = "future_MAE"
TARGET_HORIZONS = {
    RETURN_TARGET: timedelta(weeks=4),
    FAVOURABLE_TARGET: timedelta(days=7),
    ADVERSE_TARGET: timedelta(days=7),
}
PREDICTORS = (
    PredictorDefinition(CONVICTION, COMPOSITE_SCORE_PREDICTOR, "Entry Conviction"),
    PredictorDefinition("TREND_SCORE", COMPOSITE_SCORE_PREDICTOR, "Trend"),
    PredictorDefinition("FLOW_SCORE", COMPOSITE_SCORE_PREDICTOR, "Flow"),
    PredictorDefinition("MOMENTUM_4W", RAW_FEATURE_PREDICTOR, "4-week momentum"),
)
PERIODS = 40


def _feature_values(index: int) -> dict[str, float]:
    # Trend rises linearly, flow repeats five unevenly spaced levels, and the
    # raw momentum feature is a strictly increasing *non-linear* transform of
    # conviction, so rank and linear statistics are genuinely different.
    trend = 40.0 + index * 1.0
    flow = 30.0 + ((index % 5) ** 2) * 3.0
    conviction = 0.5 * trend + 0.5 * flow
    return {
        CONVICTION: conviction,
        "TREND_SCORE": trend,
        "FLOW_SCORE": flow,
        "MOMENTUM_4W": (conviction / 100.0) ** 3,
    }


def _dataset(
    *,
    periods: int = PERIODS,
    missing: tuple[int, str] | None = None,
    constant_predictor: str | None = None,
    constant_target: str | None = None,
    scrambled: bool = False,
    duplicate_flow: bool = False,
    late_feature: tuple[int, str, float] | None = None,
    price_source_policy_version: str | None = None,
    regimes: tuple[str, ...] = ("BULL", "BEAR"),
):
    timestamps = tuple(START + timedelta(days=index) for index in range(periods))
    feature_rows: list[FeatureObservation] = []
    target_rows: list[ForwardTargetObservation] = []
    contexts: list[DiagnosticContext] = []
    for index, timestamp in enumerate(timestamps):
        values = _feature_values(index)
        if duplicate_flow:
            values["FLOW_SCORE"] = values["TREND_SCORE"]
        if constant_predictor is not None:
            values[constant_predictor] = 50.0
        for name in FEATURE_NAMES:
            value = None if missing == (index, name) else values[name]
            feature_rows.append(
                FeatureObservation(
                    feature_name=name,
                    value=value,
                    observation_time=timestamp,
                    available_at=timestamp,
                    source_id=f"features-{index}",
                )
            )
        if late_feature is not None and late_feature[0] == index:
            _, name, revised = late_feature
            feature_rows.append(
                FeatureObservation(
                    feature_name=name,
                    value=revised,
                    observation_time=timestamp,
                    available_at=timestamp + timedelta(days=1),
                    source_id=f"late-{index}",
                    revision=1,
                )
            )
        conviction = values[CONVICTION]
        outcomes = {
            RETURN_TARGET: (
                0.001 * (((index * 17) % periods) - periods / 2)
                if scrambled
                else 0.001 * conviction - 0.05
            ),
            FAVOURABLE_TARGET: 0.002 * conviction,
            ADVERSE_TARGET: -0.001 * (120.0 - conviction),
        }
        if constant_target is not None:
            outcomes[constant_target] = 0.02
        for name, value in outcomes.items():
            outcome_time = timestamp + TARGET_HORIZONS[name]
            target_rows.append(
                ForwardTargetObservation(
                    target_name=name,
                    value=value,
                    decision_timestamp=timestamp,
                    outcome_time=outcome_time,
                    available_at=outcome_time,
                    source_id=f"targets-{index}",
                )
            )
        contexts.append(
            DiagnosticContext(
                decision_timestamp=timestamp,
                evidence_available_at=timestamp,
                regime=regimes[index % len(regimes)],
                setup=(
                    "BULL_TREND_CONTINUATION" if index % 2 == 0 else "BULLISH_RESET"
                ),
                source_id=f"context-{index}",
            )
        )
    definition = FEATURE_DEFINITION
    if price_source_policy_version is not None:
        definition = FeatureMatrixDefinition(
            feature_names=FEATURE_NAMES,
            version=FEATURE_DEFINITION.version,
            provenance=replace(
                FEATURE_DEFINITION.provenance,
                price_source_policy_version=price_source_policy_version,
            ),
        )
    features = build_point_in_time_feature_matrix(
        feature_rows, timestamps, definition=definition
    )
    targets = build_forward_target_matrix(target_rows, timestamps)
    return features, targets, tuple(contexts)


def _spec(**overrides):
    values = {
        "predictors": PREDICTORS,
        "target_names": (RETURN_TARGET, FAVOURABLE_TARGET, ADVERSE_TARGET),
        "component_predictors": ("FLOW_SCORE", "TREND_SCORE"),
        "conviction_predictor": CONVICTION,
        "favourable_target_name": FAVOURABLE_TARGET,
        "adverse_target_name": ADVERSE_TARGET,
        "bucket_count": 4,
        "minimum_sample_size": 8,
        "bootstrap_resamples": 120,
        "bootstrap_confidence": Decimal("90"),
        "seed": 11,
        **overrides,
    }
    return predictor_diagnostics_spec(**values)


def _report(*, spec=None, **dataset):
    features, targets, contexts = _dataset(**dataset)
    return run_predictor_diagnostics(
        features, targets, contexts, spec=spec if spec is not None else _spec()
    )


def test_policy_vocabularies_are_versioned_and_research_only() -> None:
    assert PREDICTOR_DIAGNOSTICS_FEATURE_ID == "PREDICTOR_DIAGNOSTICS"
    assert PREDICTOR_DIAGNOSTICS_POLICY_VERSION.endswith("_V1")
    assert DIAGNOSTICS_PRODUCTION_STATUS == "RESEARCH_ONLY_NOT_PRODUCTION"
    assert DIAGNOSTICS_PROMOTION_TICKET == "BTC-193"
    report = _report()
    assert report.production_status == DIAGNOSTICS_PRODUCTION_STATUS
    assert report.promotion_ticket == DIAGNOSTICS_PROMOTION_TICKET
    assert report.reason_codes == PREDICTOR_DIAGNOSTICS_REASON_CODES
    assert "PREDICTOR_DIAGNOSTICS_RESEARCH_ONLY" in report.reason_codes
    assert (
        "PREDICTOR_DIAGNOSTICS_BTC_193_PROMOTION_REQUIRED" in report.reason_codes
    )


def test_research_evidence_exposes_no_strategy_mutation_path() -> None:
    report = _report()
    with pytest.raises(Exception):
        report.production_status = "PRODUCTION"  # type: ignore[misc]
    with pytest.raises(Exception):
        report.spec.predictors = ()  # type: ignore[misc]


def test_specification_is_deterministic_and_content_addressed() -> None:
    first = _spec()
    assert first == _spec()
    assert first.spec_id == _spec().spec_id
    assert first.spec_id != _spec(bucket_count=5).spec_id
    assert first.spec_id != _spec(seed=12).spec_id
    assert first.as_record()["spec_id"] == first.spec_id


def test_information_coefficients_report_sample_size_and_uncertainty() -> None:
    report = _report()
    diagnostic = report.analysis(CONVICTION).diagnostic(RETURN_TARGET)
    assert diagnostic.status == DIAGNOSTIC_AVAILABLE
    assert diagnostic.sample_size == PERIODS
    assert diagnostic.observed_row_count == PERIODS
    assert diagnostic.pearson.method == PEARSON_METHOD
    assert diagnostic.spearman.method == SPEARMAN_METHOD
    # The outcome is an increasing affine function of conviction.
    assert diagnostic.pearson.coefficient == Decimal("1.000000000000")
    assert diagnostic.spearman.coefficient == Decimal("1.000000000000")
    for estimate in (diagnostic.pearson, diagnostic.spearman):
        assert estimate.sample_size == PERIODS
        assert estimate.interval_status == INTERVAL_AVAILABLE
        assert estimate.confidence == Decimal("90")
        assert estimate.resample_count == 120
        assert estimate.defined_resample_count <= estimate.resample_count
        assert estimate.lower_bound is not None
        assert estimate.upper_bound is not None
        assert estimate.lower_bound <= estimate.upper_bound


def test_rank_and_linear_coefficients_separate_under_a_monotone_transform() -> None:
    report = _report()
    diagnostic = report.analysis("MOMENTUM_4W").diagnostic(RETURN_TARGET)
    # The raw feature is a strictly increasing cubic transform of conviction,
    # so the rank IC is perfect while the linear IC is not.
    assert diagnostic.spearman.coefficient == Decimal("1.000000000000")
    assert diagnostic.pearson.coefficient is not None
    assert diagnostic.pearson.coefficient < Decimal("1")


def test_bootstrap_intervals_replay_from_the_seed_and_move_with_it() -> None:
    features, targets, contexts = _dataset()
    spec = _spec()
    first = run_predictor_diagnostics(features, targets, contexts, spec=spec)
    again = run_predictor_diagnostics(features, targets, contexts, spec=spec)
    assert again.as_record() == first.as_record()
    reseeded = run_predictor_diagnostics(
        features, targets, contexts, spec=_spec(seed=99)
    )
    baseline = first.analysis("FLOW_SCORE").diagnostic(RETURN_TARGET).pearson
    moved = reseeded.analysis("FLOW_SCORE").diagnostic(RETURN_TARGET).pearson
    assert baseline.coefficient == moved.coefficient
    assert (baseline.lower_bound, baseline.upper_bound) != (
        moved.lower_bound,
        moved.upper_bound,
    )


def test_missing_values_are_excluded_rather_than_zero_filled() -> None:
    report = _report(missing=(5, "FLOW_SCORE"))
    flow = report.analysis("FLOW_SCORE").diagnostic(RETURN_TARGET)
    assert flow.sample_size == PERIODS - 1
    assert flow.observed_row_count == PERIODS
    assert sum(bucket.sample_size for bucket in flow.buckets) == PERIODS - 1
    trend = report.analysis("TREND_SCORE").diagnostic(RETURN_TARGET)
    assert trend.sample_size == PERIODS
    matrix = report.correlation_matrix(PEARSON_METHOD)
    assert matrix.sample_size == PERIODS - 1


def test_thin_segments_report_insufficient_samples_without_metrics() -> None:
    report = _report(spec=_spec(minimum_sample_size=25))
    regime = report.analysis(CONVICTION).diagnostic(
        RETURN_TARGET, scope=REGIME_SCOPE, segment="BULL"
    )
    assert regime.sample_size == PERIODS // 2
    assert regime.status == DIAGNOSTIC_INSUFFICIENT_SAMPLES
    assert regime.pearson.coefficient is None
    assert regime.pearson.interval_status == INTERVAL_NOT_ESTIMATED
    assert regime.pearson.resample_count == 0
    assert regime.buckets == ()
    assert regime.bucket_status == BUCKET_INSUFFICIENT_SAMPLES


def test_zero_variance_inputs_are_declared_rather_than_estimated() -> None:
    flat_predictor = _report(constant_predictor="MOMENTUM_4W")
    diagnostic = flat_predictor.analysis("MOMENTUM_4W").diagnostic(RETURN_TARGET)
    assert diagnostic.status == DIAGNOSTIC_ZERO_VARIANCE_PREDICTOR
    assert diagnostic.pearson.coefficient is None
    flat_target = _report(constant_target=RETURN_TARGET)
    constant = flat_target.analysis(CONVICTION).diagnostic(RETURN_TARGET)
    assert constant.status == DIAGNOSTIC_ZERO_VARIANCE_TARGET
    assert constant.spearman.coefficient is None


def test_buckets_partition_the_sample_and_carry_conditional_expectancy() -> None:
    report = _report()
    diagnostic = report.analysis(CONVICTION).diagnostic(RETURN_TARGET)
    assert diagnostic.bucket_status == BUCKET_AVAILABLE
    assert [bucket.ordinal for bucket in diagnostic.buckets] == [1, 2, 3, 4]
    assert [bucket.sample_size for bucket in diagnostic.buckets] == [10, 10, 10, 10]
    assert sum(bucket.sample_size for bucket in diagnostic.buckets) == PERIODS
    means = [bucket.mean_target_value for bucket in diagnostic.buckets]
    assert means == sorted(means)
    for bucket in diagnostic.buckets:
        assert bucket.lower_predictor_value <= bucket.mean_predictor_value
        assert bucket.mean_predictor_value <= bucket.upper_predictor_value
        assert Decimal("0") <= bucket.positive_target_fraction <= Decimal("1")


def test_tied_predictor_values_declare_a_straddled_bucket_boundary() -> None:
    report = _report()
    flow = report.analysis("FLOW_SCORE").diagnostic(RETURN_TARGET)
    # FLOW_SCORE repeats five levels, so equal-count buckets straddle a tie.
    assert flow.tied_bucket_boundaries is True
    conviction = report.analysis(CONVICTION).diagnostic(RETURN_TARGET)
    assert conviction.tied_bucket_boundaries is False


def test_conviction_monotonicity_is_measured_and_can_fail() -> None:
    monotone = _report().conviction_monotonicity(RETURN_TARGET)
    assert monotone.status == MONOTONICITY_AVAILABLE
    assert monotone.monotonic_increasing is True
    assert monotone.increasing_step_count == 3
    assert monotone.rank_correlation == Decimal("1.000000000000")
    scrambled = _report(scrambled=True).conviction_monotonicity(RETURN_TARGET)
    assert scrambled.monotonic_increasing is False
    assert scrambled.monotonic_decreasing is False
    assert scrambled.increasing_step_count + scrambled.decreasing_step_count == 3


def test_raw_features_and_composite_scores_are_comparable() -> None:
    report = _report()
    composites = report.analyses_of_kind(COMPOSITE_SCORE_PREDICTOR)
    raws = report.analyses_of_kind(RAW_FEATURE_PREDICTOR)
    assert {item.definition.predictor_name for item in composites} == {
        CONVICTION,
        "TREND_SCORE",
        "FLOW_SCORE",
    }
    assert [item.definition.predictor_name for item in raws] == ["MOMENTUM_4W"]
    composite_ic = report.analysis(CONVICTION).diagnostic(RETURN_TARGET).spearman
    raw_ic = report.analysis("MOMENTUM_4W").diagnostic(RETURN_TARGET).spearman
    assert composite_ic.coefficient is not None
    assert raw_ic.coefficient is not None
    assert (
        "PREDICTOR_DIAGNOSTICS_RAW_AND_COMPOSITE_PREDICTORS_COMPARED"
        in report.reason_codes
    )


def test_a_single_predictor_kind_cannot_answer_the_comparison_question() -> None:
    with pytest.raises(PredictorDiagnosticsError, match="raw features"):
        _spec(predictors=PREDICTORS[:3])


def test_regime_and_setup_conditioned_stability_is_reported() -> None:
    report = _report()
    assert report.observed_regimes == ("BEAR", "BULL")
    assert report.observed_setups == ("BULLISH_RESET", "BULL_TREND_CONTINUATION")
    for segment in report.observed_regimes:
        conditioned = report.analysis(CONVICTION).diagnostic(
            RETURN_TARGET, scope=REGIME_SCOPE, segment=segment
        )
        assert conditioned.sample_size == PERIODS // 2
        assert conditioned.status == DIAGNOSTIC_AVAILABLE
    summary = report.stability_summary(CONVICTION, RETURN_TARGET, scope=REGIME_SCOPE)
    assert summary.status == STABILITY_AVAILABLE
    assert summary.segment_count == 2
    assert summary.evaluated_segment_count == 2
    assert summary.evaluated_sample_size == PERIODS
    assert summary.sign_consistency == Decimal("1.000000000000")
    assert summary.minimum_coefficient == Decimal("1.000000000000")
    assert summary.maximum_coefficient == Decimal("1.000000000000")
    assert summary.coefficient_standard_deviation == Decimal("0E-12")
    setup_summary = report.stability_summary(
        CONVICTION, RETURN_TARGET, scope=SETUP_SCOPE
    )
    assert setup_summary.scope == SETUP_SCOPE
    assert setup_summary.segment_count == 2


def test_stability_declares_segments_it_could_not_evaluate() -> None:
    report = _report(
        spec=_spec(minimum_sample_size=25), regimes=("BULL", "BEAR", "NEUTRAL")
    )
    summary = report.stability_summary(CONVICTION, RETURN_TARGET, scope=REGIME_SCOPE)
    assert summary.segment_count == 3
    assert summary.evaluated_segment_count == 0
    assert summary.mean_coefficient is None
    assert summary.sign_consistency is None


def test_component_correlation_matrices_are_empirical_measurements() -> None:
    report = _report()
    pearson = report.correlation_matrix(PEARSON_METHOD)
    spearman = report.correlation_matrix(SPEARMAN_METHOD)
    assert pearson.status == MATRIX_AVAILABLE
    assert pearson.component_names == ("FLOW_SCORE", "TREND_SCORE")
    assert pearson.sample_size == PERIODS
    assert pearson.coefficient("TREND_SCORE", "TREND_SCORE") == Decimal(
        "1.000000000000"
    )
    assert pearson.coefficient("TREND_SCORE", "FLOW_SCORE") == pearson.coefficient(
        "FLOW_SCORE", "TREND_SCORE"
    )
    assert spearman.coefficient("TREND_SCORE", "FLOW_SCORE") != pearson.coefficient(
        "TREND_SCORE", "FLOW_SCORE"
    )
    assert pearson.empirical_note == MECHANICAL_VS_EMPIRICAL_NOTE
    assert (
        "PREDICTOR_DIAGNOSTICS_EMPIRICAL_CORRELATION_MEASURED"
        in report.reason_codes
    )


def test_empirical_correlation_is_distinguished_from_mechanical_nesting() -> None:
    report = _report(duplicate_flow=True)
    pearson = report.correlation_matrix(PEARSON_METHOD)
    # Perfectly correlated components are an empirical observation, not a
    # structural defect, and the report says so beside the structural audit.
    assert pearson.coefficient("TREND_SCORE", "FLOW_SCORE") == Decimal(
        "1.000000000000"
    )
    decomposition = report.effective_weight_decomposition
    entry = decomposition["report"]["composites"]["entry_conviction"]
    assert entry["v1_1_mechanically_clean"] is False
    assert "regime" in entry["v1_1_declared_weights"]
    assert entry["v1_2_mechanically_clean"] is True
    assert "regime" not in entry["v1_2_declared_weights"]
    assert (
        "PREDICTOR_DIAGNOSTICS_MECHANICAL_NESTING_REPORTED_SEPARATELY"
        in report.reason_codes
    )


def test_effective_weight_decomposition_reuses_the_scoring_contract_owner() -> None:
    report = _report()
    decomposition = report.effective_weight_decomposition
    assert decomposition["policy_version"] == EFFECTIVE_WEIGHT_POLICY_VERSION
    assert decomposition["contracts_version"] == SCORING_CONTRACTS_VERSION
    assert decomposition["report"] == effective_weight_report()
    entry = decomposition["report"]["composites"]["entry_conviction"]
    assert entry["v1_2_effective_weights"]["trend"] == "0.25"
    assert entry["v1_1_effective_weights"]["trend"] == "0.2900"


def test_factor_concentration_separates_repeated_and_distinct_components() -> None:
    distinct = _report().concentration
    assert distinct.status == CONCENTRATION_AVAILABLE
    assert distinct.method == PEARSON_METHOD
    assert len(distinct.eigenvalues) == 2
    assert distinct.effective_rank is not None
    assert distinct.effective_rank > Decimal("1.9")
    duplicated = _report(duplicate_flow=True).concentration
    assert duplicated.effective_rank == Decimal("1.000000000000")
    assert duplicated.largest_eigenvalue_share == Decimal("1.000000000000")


def test_forward_excursion_relationships_pair_mfe_and_mae() -> None:
    report = _report()
    relationship = report.excursion(CONVICTION)
    assert relationship.favourable_target_name == FAVOURABLE_TARGET
    assert relationship.adverse_target_name == ADVERSE_TARGET
    assert relationship.sample_size == PERIODS
    assert relationship.bucket_status == BUCKET_AVAILABLE
    assert sum(item.sample_size for item in relationship.buckets) == PERIODS
    favourable = [item.mean_favourable_excursion for item in relationship.buckets]
    adverse = [item.mean_adverse_excursion for item in relationship.buckets]
    assert favourable == sorted(favourable)
    assert adverse == sorted(adverse)
    assert relationship.favourable_rank_ic.coefficient == Decimal("1.000000000000")
    assert relationship.excursion_rank_correlation.coefficient == Decimal(
        "1.000000000000"
    )
    assert (
        "PREDICTOR_DIAGNOSTICS_FORWARD_EXCURSION_RELATIONSHIPS"
        in report.reason_codes
    )


def test_excursions_are_reported_for_every_conditioning_segment() -> None:
    report = _report()
    conditioned = report.excursion(CONVICTION, scope=REGIME_SCOPE, segment="BULL")
    assert conditioned.sample_size == PERIODS // 2
    assert conditioned.scope == REGIME_SCOPE


def test_point_in_time_selection_ignores_a_later_revision() -> None:
    plain = _report()
    revised = _report(late_feature=(3, "TREND_SCORE", 999.0))
    assert revised.as_record()["analyses"] == plain.as_record()["analyses"]


def test_contexts_must_align_with_the_feature_decision_grid() -> None:
    features, targets, contexts = _dataset()
    with pytest.raises(PredictorDiagnosticsError, match="exactly and in order"):
        run_predictor_diagnostics(
            features, targets, contexts[:-1], spec=_spec()
        )
    reordered = (contexts[1], contexts[0], *contexts[2:])
    with pytest.raises(PredictorDiagnosticsError, match="exactly and in order"):
        run_predictor_diagnostics(features, targets, reordered, spec=_spec())


def test_forward_targets_must_stay_outside_the_feature_matrix() -> None:
    features, targets, contexts = _dataset()
    leaking = FeatureMatrixDefinition(
        feature_names=(*FEATURE_NAMES, RETURN_TARGET),
        version=FEATURE_DEFINITION.version,
    )
    rows = [
        FeatureObservation(
            feature_name=name,
            value=1.0 * index,
            observation_time=timestamp,
            available_at=timestamp,
            source_id="leak",
        )
        for index, timestamp in enumerate(features.decision_timestamps)
        for name in leaking.feature_names
    ]
    leaked = build_point_in_time_feature_matrix(
        rows, features.decision_timestamps, definition=leaking
    )
    with pytest.raises(PredictorDiagnosticsError, match="outside the contemporaneous"):
        run_predictor_diagnostics(leaked, targets, contexts, spec=_spec())


def test_target_price_source_policy_must_match_feature_provenance() -> None:
    features, targets, contexts = _dataset(
        price_source_policy_version="OTHER_PRICE_SOURCE_POLICY_V9"
    )
    with pytest.raises(PredictorDiagnosticsError, match="price-source policy"):
        run_predictor_diagnostics(features, targets, contexts, spec=_spec())


def test_undeclared_predictors_and_targets_fail_closed() -> None:
    features, targets, contexts = _dataset()
    absent = _spec(
        predictors=(
            *PREDICTORS,
            PredictorDefinition("NOT_A_COLUMN", RAW_FEATURE_PREDICTOR, "Absent"),
        )
    )
    with pytest.raises(PredictorDiagnosticsError, match="declared predictors"):
        run_predictor_diagnostics(features, targets, contexts, spec=absent)


def test_specification_rejects_incoherent_research_questions() -> None:
    with pytest.raises(PredictorDiagnosticsError, match="composite score"):
        _spec(conviction_predictor="MOMENTUM_4W")
    with pytest.raises(PredictorDiagnosticsError, match="declared predictor"):
        _spec(conviction_predictor="ABSENT")
    with pytest.raises(PredictorDiagnosticsError, match="must differ"):
        _spec(adverse_target_name=FAVOURABLE_TARGET)
    with pytest.raises(PredictorDiagnosticsError, match="at least two"):
        _spec(bucket_count=1)
    with pytest.raises(PredictorDiagnosticsError, match="minimum_sample_size"):
        _spec(bucket_count=6, minimum_sample_size=5)
    with pytest.raises(PredictorDiagnosticsError, match="declared predictors"):
        _spec(component_predictors=("ABSENT",))
    with pytest.raises(PredictorDiagnosticsError, match="declared target"):
        _spec(favourable_target_name="future_1w_return")


def test_evidence_round_trips_through_its_persistence_record() -> None:
    report = _report()
    record = report.as_record()
    assert record["evidence_digest"] == report.evidence_digest
    assert record["report_id"] == report.report_id
    restored = restore_predictor_diagnostics_report(record)
    assert restored == report
    assert restored.as_record() == record


def test_tampered_evidence_is_rejected_on_restore() -> None:
    report = _report()
    record = report.as_record()

    edited = {**record}
    edited["analyses"] = [dict(item) for item in record["analyses"]]
    first = [dict(item) for item in edited["analyses"][0]["diagnostics"]]
    first[0] = {
        **first[0],
        "pearson": {**first[0]["pearson"], "coefficient": "0.100000000000"},
    }
    edited["analyses"][0] = {**edited["analyses"][0], "diagnostics": first}
    with pytest.raises(PredictorDiagnosticsError):
        restore_predictor_diagnostics_report(edited)

    dropped = {**record, "analyses": record["analyses"][:-1]}
    with pytest.raises(PredictorDiagnosticsError):
        restore_predictor_diagnostics_report(dropped)

    relabelled = {**record, "production_status": "PRODUCTION"}
    with pytest.raises(PredictorDiagnosticsError):
        restore_predictor_diagnostics_report(relabelled)

    recoded = {**record, "reason_codes": [*record["reason_codes"], "EXTRA"]}
    with pytest.raises(PredictorDiagnosticsError):
        restore_predictor_diagnostics_report(recoded)

    reweighted = {
        **record,
        "effective_weight_decomposition": {
            **record["effective_weight_decomposition"],
            "contracts_version": "SCORING_CONTRACTS_V9",
        },
    }
    with pytest.raises(PredictorDiagnosticsError):
        restore_predictor_diagnostics_report(reweighted)


def test_every_predictor_reports_every_segment_and_target() -> None:
    report = _report()
    expected = 1 + len(report.observed_regimes) + len(report.observed_setups)
    for analysis in report.analyses:
        assert len(analysis.diagnostics) == expected * len(report.spec.target_names)
    assert len(report.excursions) == len(report.spec.predictors) * expected
    assert len(report.stability) == len(report.spec.predictors) * len(
        report.spec.target_names
    ) * 2
    global_diagnostic = report.analysis(CONVICTION).diagnostic(
        RETURN_TARGET, scope=GLOBAL_SCOPE, segment=GLOBAL_SEGMENT
    )
    assert global_diagnostic.segment == GLOBAL_SEGMENT
