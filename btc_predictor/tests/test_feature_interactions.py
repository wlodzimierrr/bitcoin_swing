"""BTC-186: point-in-time feature interaction research."""

import decimal
import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from btc_predictor.backtest.walk_forward import walk_forward_plan
from btc_predictor.research import (
    CANDIDATE_INTERACTIONS,
    ESTIMATE_AVAILABLE,
    ESTIMATE_INSUFFICIENT_TRAIN,
    FEATURE_INTERACTION_FEATURE_ID,
    FEATURE_INTERACTION_POLICY_VERSION,
    GLOBAL_SCOPE,
    GLOBAL_SEGMENT,
    INTERACTION_ESTIMATION_POLICY_VERSION,
    INTERACTION_PRODUCTION_STATUS,
    INTERACTION_PROMOTION_TICKET,
    REGIME_SCOPE,
    SETUP_SCOPE,
    FeatureMatrixDefinition,
    FeatureObservation,
    ForwardTargetObservation,
    InteractionContext,
    InteractionDefinition,
    build_forward_target_matrix,
    build_point_in_time_feature_matrix,
    interaction_research_spec,
    restore_feature_interaction_report,
    run_feature_interaction_research,
)


START = datetime(2024, 1, 1, tzinfo=UTC)
TARGET_NAME = "future_MFE"
FEATURE_NAMES = (
    "TREND_SCORE",
    "FLOW_SCORE",
    "POSITIONING_SCORE",
    "STRUCTURE_SCORE",
    "VOLATILITY_SCORE",
    "FUNDING_RESET",
    "OI_DELEVERAGING",
    "FLOW_IMPROVEMENT",
)
FEATURE_DEFINITION = FeatureMatrixDefinition(
    feature_names=FEATURE_NAMES,
    version="BTC_186_TEST_FEATURES_V1",
)


def _values(index: int) -> dict[str, float]:
    # Deterministic, non-collinear inputs.  The target below has a dominant
    # Trend x Flow term so the incremental model should win out of sample.
    trend = 45.0 + index * 1.3 + (index % 3) * 2.1
    flow = 38.0 + (index % 7) * 4.2 - index * 0.15
    return {
        "TREND_SCORE": trend,
        "FLOW_SCORE": flow,
        "POSITIONING_SCORE": 40.0 + (index % 5) * 6.1 + index * 0.11,
        "STRUCTURE_SCORE": 52.0 + (index % 4) * 5.3 - index * 0.07,
        "VOLATILITY_SCORE": 35.0 + (index % 6) * 4.7 + index * 0.09,
        "FUNDING_RESET": -1.2 + (index % 5) * 0.55 + index * 0.01,
        "OI_DELEVERAGING": 0.2 + (index % 4) * 0.4 - index * 0.005,
        "FLOW_IMPROVEMENT": -0.5 + (index % 6) * 0.3 + index * 0.004,
    }


def _dataset(
    *,
    periods: int = 30,
    missing: tuple[int, str] | None = None,
    late_training_targets: bool = False,
):
    timestamps = tuple(START + timedelta(days=index) for index in range(periods))
    feature_rows = []
    target_rows = []
    contexts = []
    for index, timestamp in enumerate(timestamps):
        values = _values(index)
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
        target_value = (
            0.01 * values["TREND_SCORE"]
            + 0.015 * values["FLOW_SCORE"]
            + 0.0025 * values["TREND_SCORE"] * values["FLOW_SCORE"]
            + (index % 2) * 0.01
        )
        outcome = timestamp + timedelta(hours=12)
        available = (
            START + timedelta(days=periods + 10)
            if late_training_targets
            else outcome
        )
        target_rows.append(
            ForwardTargetObservation(
                target_name=TARGET_NAME,
                value=target_value,
                decision_timestamp=timestamp,
                outcome_time=outcome,
                available_at=available,
                source_id=f"targets-{index}",
            )
        )
        contexts.append(
            InteractionContext(
                decision_timestamp=timestamp,
                evidence_available_at=timestamp,
                regime="BULL" if index % 2 == 0 else "BEAR",
                setup=(
                    "BULL_TREND_CONTINUATION"
                    if index % 2 == 0
                    else "BULLISH_RESET"
                ),
                source_id=f"context-{index}",
            )
        )
    features = build_point_in_time_feature_matrix(
        feature_rows,
        timestamps,
        definition=FEATURE_DEFINITION,
    )
    targets = build_forward_target_matrix(target_rows, timestamps)
    return features, targets, tuple(contexts)


def _spec(
    *,
    interactions=CANDIDATE_INTERACTIONS,
    minimum_train_samples: int = 5,
    minimum_test_samples: int = 2,
):
    plan = walk_forward_plan(
        train_periods=10,
        test_periods=5,
        step_periods=5,
        embargo_periods=0,
    )
    return interaction_research_spec(
        target_name=TARGET_NAME,
        interactions=interactions,
        plan=plan,
        minimum_train_samples=minimum_train_samples,
        minimum_test_samples=minimum_test_samples,
    )


def _report(**dataset_kwargs):
    features, targets, contexts = _dataset(**dataset_kwargs)
    return run_feature_interaction_research(
        features,
        targets,
        contexts,
        spec=_spec(),
    )


def test_candidate_vocabulary_persists_all_five_ticket_interactions() -> None:
    assert tuple(item.interaction_id for item in CANDIDATE_INTERACTIONS) == (
        "TREND_X_FLOW",
        "FLOW_X_POSITIONING",
        "POSITIONING_X_STRUCTURE",
        "TREND_X_VOLATILITY",
        "FUNDING_RESET_X_OI_DELEVERAGING_X_FLOW_IMPROVEMENT",
    )
    assert CANDIDATE_INTERACTIONS[-1].feature_names == (
        "FUNDING_RESET",
        "OI_DELEVERAGING",
        "FLOW_IMPROVEMENT",
    )
    assert CANDIDATE_INTERACTIONS[0].formula == (
        "TRAIN_Z(TRAIN_Z(TREND_SCORE) * TRAIN_Z(FLOW_SCORE))"
    )


def test_spec_is_versioned_deterministic_and_uses_btc182_split_policy() -> None:
    first = _spec()
    second = _spec()

    assert first == second
    assert first.feature_id == FEATURE_INTERACTION_FEATURE_ID
    assert first.policy_version == FEATURE_INTERACTION_POLICY_VERSION
    assert first.estimation_policy_version == INTERACTION_ESTIMATION_POLICY_VERSION
    assert first.plan.split_policy_version == "TRAIN_STRICTLY_BEFORE_TEST_V1"
    assert len(first.spec_id) == 64


def test_interactions_report_effect_size_stability_and_oos_increment() -> None:
    report = _report()
    global_effect = report.analysis("TREND_X_FLOW").effect(
        GLOBAL_SCOPE, GLOBAL_SEGMENT
    )

    assert global_effect.sample_size == 30
    assert global_effect.tested_sample_size == 20
    assert global_effect.eligible_fold_count == 4
    assert global_effect.effect_size is not None
    assert global_effect.effect_size > 0
    assert global_effect.effect_size_standard_deviation is not None
    assert global_effect.effect_sign_consistency == 1
    assert global_effect.mean_incremental_oos_r2 is not None
    assert global_effect.mean_incremental_oos_r2 > 0
    assert global_effect.positive_incremental_fold_fraction == 1
    assert all(fold.status == ESTIMATE_AVAILABLE for fold in global_effect.folds)


def test_main_effects_are_controlled_before_incremental_interaction_is_measured() -> None:
    features, targets, contexts = _dataset()
    trend = features.definition.feature_names.index("TREND_SCORE")
    flow = features.definition.feature_names.index("FLOW_SCORE")
    target = targets.definition.target_names.index(TARGET_NAME)
    values = targets.to_numpy()
    values[:, target] = (
        0.3 * features.values[:, trend] + 0.7 * features.values[:, flow]
    )
    additive_targets = replace(
        targets,
        values=values,
        missing_mask=np.isnan(values),
    )
    report = run_feature_interaction_research(
        features,
        additive_targets,
        contexts,
        spec=_spec(interactions=(CANDIDATE_INTERACTIONS[0],)),
    )
    effect = report.analysis("TREND_X_FLOW").effect(GLOBAL_SCOPE)

    assert effect.effect_size is not None
    assert abs(effect.effect_size) <= 1e-10


def test_appending_future_rows_does_not_change_earlier_fold_effects() -> None:
    short_features, short_targets, short_contexts = _dataset(periods=25)
    long_features, long_targets, long_contexts = _dataset(periods=30)
    spec = _spec(interactions=(CANDIDATE_INTERACTIONS[0],))
    short = run_feature_interaction_research(
        short_features,
        short_targets,
        short_contexts,
        spec=spec,
    )
    long = run_feature_interaction_research(
        long_features,
        long_targets,
        long_contexts,
        spec=spec,
    )

    short_folds = short.analysis("TREND_X_FLOW").effect(GLOBAL_SCOPE).folds
    long_folds = long.analysis("TREND_X_FLOW").effect(GLOBAL_SCOPE).folds
    assert short_folds == long_folds[: len(short_folds)]


def test_every_interaction_is_tested_globally_by_regime_and_by_setup() -> None:
    report = _report()

    for analysis in report.analyses:
        keys = {(effect.scope, effect.segment) for effect in analysis.effects}
        assert (GLOBAL_SCOPE, GLOBAL_SEGMENT) in keys
        assert (REGIME_SCOPE, "BULL") in keys
        assert (REGIME_SCOPE, "BEAR") in keys
        assert (SETUP_SCOPE, "BULL_TREND_CONTINUATION") in keys
        assert (SETUP_SCOPE, "BULLISH_RESET") in keys
        assert all(effect.sample_size > 0 for effect in analysis.effects)


def test_missing_feature_values_are_complete_case_excluded_not_zero_filled() -> None:
    baseline = _report()
    missing = _report(missing=(17, "TREND_SCORE"))

    baseline_effect = baseline.analysis("TREND_X_FLOW").effect(GLOBAL_SCOPE)
    missing_effect = missing.analysis("TREND_X_FLOW").effect(GLOBAL_SCOPE)
    unaffected = missing.analysis("FLOW_X_POSITIONING").effect(GLOBAL_SCOPE)

    assert missing_effect.sample_size == baseline_effect.sample_size - 1
    assert missing_effect.tested_sample_size == baseline_effect.tested_sample_size - 1
    assert unaffected.sample_size == baseline_effect.sample_size
    assert missing_effect.effect_size is not None


def test_training_targets_unavailable_at_test_start_are_not_used() -> None:
    report = _report(late_training_targets=True)
    global_effect = report.analysis("TREND_X_FLOW").effect(GLOBAL_SCOPE)

    assert global_effect.sample_size == 30
    assert global_effect.eligible_fold_count == 0
    assert global_effect.tested_sample_size == 0
    assert global_effect.effect_size is None
    assert all(
        fold.status == ESTIMATE_INSUFFICIENT_TRAIN
        and fold.train_sample_size == 0
        for fold in global_effect.folds
    )


def test_context_evidence_must_be_point_in_time() -> None:
    with pytest.raises(ValueError, match="must be <= decision_timestamp"):
        InteractionContext(
            decision_timestamp=START,
            evidence_available_at=START + timedelta(seconds=1),
            regime="BULL",
            setup="BULLISH_RESET",
            source_id="future-context",
        )


def test_contexts_and_targets_must_align_exactly_with_feature_rows() -> None:
    features, targets, contexts = _dataset()

    with pytest.raises(ValueError, match="contexts must match"):
        run_feature_interaction_research(
            features,
            targets,
            tuple(reversed(contexts)),
            spec=_spec(),
        )


def test_target_name_and_feature_provenance_fail_closed() -> None:
    features, targets, contexts = _dataset()
    unknown_target = interaction_research_spec(
        target_name="future_unknown",
        interactions=(CANDIDATE_INTERACTIONS[0],),
        plan=_spec().plan,
        minimum_train_samples=5,
        minimum_test_samples=2,
    )
    with pytest.raises(ValueError, match="does not contain"):
        run_feature_interaction_research(
            features,
            targets,
            contexts,
            spec=unknown_target,
        )

    changed_definition = replace(
        features.definition,
        provenance=replace(
            features.definition.provenance,
            parameter_set_id="different-parameter-set",
        ),
    )
    changed_features = replace(features, definition=changed_definition)
    with pytest.raises(ValueError, match="parameter_set_id"):
        run_feature_interaction_research(
            changed_features,
            targets,
            contexts,
            spec=_spec(),
        )
    with pytest.raises(ValueError, match="decision timestamps must match"):
        run_feature_interaction_research(
            features,
            replace(
                targets,
                decision_timestamps=tuple(
                    timestamp - timedelta(hours=1)
                    for timestamp in targets.decision_timestamps
                ),
            ),
            contexts,
            spec=_spec(),
        )


def test_undefined_reset_proxies_are_not_silently_substituted() -> None:
    features, targets, contexts = _dataset()
    reduced_definition = FeatureMatrixDefinition(
        feature_names=FEATURE_NAMES[:-3],
        version="BTC_186_WITHOUT_RESET_BINDINGS_V1",
    )
    reduced = replace(
        features,
        definition=reduced_definition,
        values=features.values[:, :-3],
        missing_mask=features.missing_mask[:, :-3],
        observation_times=tuple(row[:-3] for row in features.observation_times),
        available_ats=tuple(row[:-3] for row in features.available_ats),
        source_ids=tuple(row[:-3] for row in features.source_ids),
        revisions=tuple(row[:-3] for row in features.revisions),
    )

    with pytest.raises(ValueError, match="FUNDING_RESET"):
        run_feature_interaction_research(
            reduced,
            targets,
            contexts,
            spec=_spec(),
        )


def test_report_is_research_only_and_requires_btc193_promotion() -> None:
    report = _report()

    assert report.production_status == INTERACTION_PRODUCTION_STATUS
    assert report.promotion_ticket == INTERACTION_PROMOTION_TICKET == "BTC-193"
    assert "FEATURE_INTERACTION_RESEARCH_ONLY" in report.reason_codes
    assert "FEATURE_INTERACTION_BTC_193_PROMOTION_REQUIRED" in report.reason_codes


def test_report_is_deterministic_json_replayable_and_tamper_evident() -> None:
    first = _report()
    second = _report()
    record = first.as_record()

    assert first == second
    assert len(first.report_id) == 64
    assert len(first.evidence_digest) == 64
    json.dumps(record, sort_keys=True)
    assert restore_feature_interaction_report(record) == first

    changed = json.loads(json.dumps(record))
    changed["analyses"][0]["effects"][0]["sample_size"] += 1
    with pytest.raises(ValueError, match="evidence does not match digest"):
        restore_feature_interaction_report(changed)

    changed = json.loads(json.dumps(record))
    changed["analyses"][0]["effects"][0]["effect_size"] = "999.000000000000"
    payload = {key: value for key, value in changed.items() if key != "evidence_digest"}
    changed["evidence_digest"] = hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    with pytest.raises(ValueError, match="aggregates do not match fold evidence"):
        restore_feature_interaction_report(changed)


@pytest.mark.parametrize(
    ("interaction", "message"),
    [
        (
            InteractionDefinition("ONE", "one", ("TREND_SCORE",)),
            "two or three",
        ),
        (
            InteractionDefinition(
                "DUPLICATE", "duplicate", ("TREND_SCORE", "TREND_SCORE")
            ),
            "must be unique",
        ),
    ],
)
def test_invalid_interaction_definitions_fail_closed(
    interaction: InteractionDefinition, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        interaction.as_record()


def test_minimum_train_samples_must_identify_estimable_full_models() -> None:
    with pytest.raises(ValueError, match="full model"):
        _spec(minimum_train_samples=4)


def test_constant_features_surface_unavailable_status_instead_of_fake_effect() -> None:
    features, targets, contexts = _dataset()
    trend = features.definition.feature_names.index("TREND_SCORE")
    values = features.to_numpy()
    values[:, trend] = 50.0
    constant = replace(features, values=values, missing_mask=np.isnan(values))
    report = run_feature_interaction_research(
        constant,
        targets,
        contexts,
        spec=_spec(),
    )
    effect = report.analysis("TREND_X_FLOW").effect(GLOBAL_SCOPE)

    assert effect.effect_size is None
    assert effect.eligible_fold_count == 0
    assert {fold.status for fold in effect.folds} == {"ZERO_VARIANCE_FEATURE"}


def test_evidence_does_not_depend_on_the_ambient_decimal_context() -> None:
    # EPIC S2 integration review.  BTC-187 and BTC-188 pin an explicit decimal
    # context so persisted evidence replays whatever the caller's context is.
    # BTC-186 did not, so a reduced ambient precision silently changed the
    # report and made a valid record fail restore as though it were tampered.
    report = _report()
    record = report.as_record()

    for precision in (14, 10, 6, 2):
        with decimal.localcontext() as context:
            context.prec = precision
            assert _report().as_record() == record
            assert restore_feature_interaction_report(record).as_record() == record
