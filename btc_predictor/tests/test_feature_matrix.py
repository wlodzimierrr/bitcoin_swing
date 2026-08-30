import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone

import numpy as np
import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.quant import weighted_score
from btc_predictor.research import (
    FEATURE_MATRIX_VERSION,
    FORWARD_TARGET_NAMES,
    INITIAL_FEATURE_NAMES,
    FeatureMatrixDefinition,
    FeatureMatrixError,
    FeatureMatrixProvenance,
    FeatureObservation,
    ForwardTargetDefinition,
    ForwardTargetObservation,
    build_forward_target_matrix,
    build_point_in_time_feature_matrix,
    decision_timestamp_range,
)

DAY_1 = datetime(2026, 1, 1, tzinfo=UTC)
DAY_2 = datetime(2026, 1, 2, tzinfo=UTC)
DAY_3 = datetime(2026, 1, 3, tzinfo=UTC)
DAY_4 = datetime(2026, 1, 4, tzinfo=UTC)
SMALL_FEATURE_DEFINITION = FeatureMatrixDefinition(
    feature_names=("TREND_SCORE", "FLOW_SCORE"),
    version="TEST_FEATURES_V1",
)


def feature(
    name: str,
    value: float | None,
    observation_time: datetime,
    available_at: datetime,
    *,
    source_id: str = "feature-run-1",
    revision: int = 0,
) -> FeatureObservation:
    return FeatureObservation(
        feature_name=name,
        value=value,
        observation_time=observation_time,
        available_at=available_at,
        source_id=source_id,
        revision=revision,
    )


def target(
    name: str,
    value: float | bool | None,
    decision_timestamp: datetime,
    outcome_time: datetime,
    available_at: datetime,
    *,
    source_id: str = "target-run-1",
    revision: int = 0,
) -> ForwardTargetObservation:
    return ForwardTargetObservation(
        target_name=name,
        value=value,
        decision_timestamp=decision_timestamp,
        outcome_time=outcome_time,
        available_at=available_at,
        source_id=source_id,
        revision=revision,
    )


def test_default_feature_definition_freezes_initial_names_and_order() -> None:
    definition = FeatureMatrixDefinition()

    assert definition.version == FEATURE_MATRIX_VERSION
    assert definition.feature_names == INITIAL_FEATURE_NAMES
    assert definition.feature_names[:8] == (
        "TREND_SCORE",
        "FLOW_SCORE",
        "POSITIONING_SCORE",
        "VOLATILITY_SCORE",
        "STRUCTURE_SCORE",
        "REGIME_SCORE",
        "REGIME_SMOOTHED_SCORE",
        "ORDERLINESS_SCORE",
    )
    assert definition.fingerprint == FeatureMatrixDefinition().fingerprint
    assert (
        definition.fingerprint
        != FeatureMatrixDefinition(
            feature_names=tuple(reversed(INITIAL_FEATURE_NAMES))
        ).fingerprint
    )
    assert definition.as_record()["feature_names"] == list(INITIAL_FEATURE_NAMES)


def test_default_feature_provenance_tracks_current_strategy_identity() -> None:
    provenance = FeatureMatrixProvenance()
    strategy_metadata = load_strategy_config().run_metadata()

    assert provenance.config_version == strategy_metadata["config_version"]
    assert provenance.strategy_version == strategy_metadata["strategy_version"]
    assert provenance.parameter_set_id == strategy_metadata["parameter_set_id"]


def test_point_in_time_selection_respects_availability_and_late_revisions() -> None:
    observations = [
        feature("TREND_SCORE", 10, DAY_1, DAY_1 + timedelta(hours=1)),
        feature(
            "TREND_SCORE",
            11,
            DAY_1,
            DAY_2 + timedelta(hours=12),
            revision=1,
            source_id="feature-run-1-revision",
        ),
        feature(
            "TREND_SCORE",
            20,
            DAY_3,
            DAY_3 + timedelta(hours=1),
            source_id="feature-run-2",
        ),
        feature("FLOW_SCORE", None, DAY_1, DAY_1 + timedelta(hours=2)),
        feature("FLOW_SCORE", 99, DAY_4, DAY_4 + timedelta(hours=1)),
    ]

    matrix = build_point_in_time_feature_matrix(
        reversed(observations),
        [DAY_4, DAY_2, DAY_3],
        definition=SMALL_FEATURE_DEFINITION,
    )

    assert matrix.decision_timestamps == (DAY_2, DAY_3, DAY_4)
    np.testing.assert_array_equal(
        matrix.values[:, 0],
        [10, 11, 20],
    )
    assert np.all(np.isnan(matrix.values[:, 1]))
    np.testing.assert_array_equal(
        matrix.missing_mask,
        [[False, True], [False, True], [False, True]],
    )
    assert matrix.available_ats[0][0] == DAY_1 + timedelta(hours=1)
    assert matrix.available_ats[1][0] == DAY_2 + timedelta(hours=12)
    assert matrix.observation_times[2][0] == DAY_3
    assert matrix.source_ids[1][0] == "feature-run-1-revision"
    assert matrix.source_ids[0][1] == "feature-run-1"
    assert all(
        available_at is None or available_at <= decision_time
        for decision_time, row in zip(matrix.decision_timestamps, matrix.available_ats)
        for available_at in row
    )


def test_appending_future_observations_does_not_change_historical_matrix() -> None:
    historical = [
        feature("TREND_SCORE", 60, DAY_1, DAY_1 + timedelta(hours=1)),
        feature("FLOW_SCORE", 55, DAY_1, DAY_1 + timedelta(hours=2)),
    ]
    first = build_point_in_time_feature_matrix(
        historical,
        [DAY_2, DAY_3],
        definition=SMALL_FEATURE_DEFINITION,
    )
    second = build_point_in_time_feature_matrix(
        [
            *historical,
            feature("TREND_SCORE", 90, DAY_4, DAY_4 + timedelta(hours=1)),
            feature("FLOW_SCORE", 95, DAY_4, DAY_4 + timedelta(hours=1)),
        ],
        [DAY_2, DAY_3],
        definition=SMALL_FEATURE_DEFINITION,
    )

    np.testing.assert_array_equal(first.values, second.values)
    np.testing.assert_array_equal(first.missing_mask, second.missing_mask)
    assert first.observation_times == second.observation_times
    assert first.available_ats == second.available_ats


def test_decision_range_and_date_filtering_are_inclusive_and_deterministic() -> None:
    timestamps = decision_timestamp_range(DAY_1, DAY_4, step=timedelta(days=1))
    matrix = build_point_in_time_feature_matrix(
        [feature("TREND_SCORE", 50, DAY_1, DAY_1)],
        reversed(timestamps),
        definition=SMALL_FEATURE_DEFINITION,
        start=DAY_2,
        end=DAY_3,
    )

    assert timestamps == (DAY_1, DAY_2, DAY_3, DAY_4)
    assert matrix.decision_timestamps == (DAY_2, DAY_3)
    assert matrix.values.shape == (2, 2)
    np.testing.assert_array_equal(matrix.values[:, 0], [50, 50])


def test_matrix_is_read_only_but_exposes_an_owned_numpy_consumer_copy() -> None:
    matrix = build_point_in_time_feature_matrix(
        [
            feature("TREND_SCORE", 80, DAY_1, DAY_1),
            feature("FLOW_SCORE", 60, DAY_1, DAY_1),
        ],
        [DAY_2],
        definition=SMALL_FEATURE_DEFINITION,
    )

    with pytest.raises(ValueError, match="read-only"):
        matrix.values[0, 0] = 1
    consumer_values = matrix.to_numpy()
    consumer_values[0, 0] = 1
    assert matrix.values[0, 0] == 80
    assert matrix.to_numpy(copy=False) is matrix.values
    assert matrix.values.dtype == np.float64
    score = weighted_score(
        matrix.to_numpy(),
        {"TREND_SCORE": 0.5, "FLOW_SCORE": 0.5},
        component_names=matrix.definition.feature_names,
    )
    np.testing.assert_array_equal(score.scores, [70])


def test_matrix_record_is_json_compatible_and_retains_missing_provenance() -> None:
    matrix = build_point_in_time_feature_matrix(
        [
            feature("TREND_SCORE", 70, DAY_1, DAY_1),
            feature("FLOW_SCORE", None, DAY_1, DAY_1 + timedelta(hours=1)),
        ],
        [DAY_2],
        definition=SMALL_FEATURE_DEFINITION,
    )

    record = matrix.as_record()

    json.dumps(record, sort_keys=True)
    assert record["values"] == [[70.0, None]]
    assert record["missing_mask"] == [[False, True]]
    assert record["available_ats"] == [
        [DAY_1.isoformat(), (DAY_1 + timedelta(hours=1)).isoformat()]
    ]
    assert record["definition"] == SMALL_FEATURE_DEFINITION.as_record()


def test_empty_date_selection_retains_reproducible_column_shape() -> None:
    matrix = build_point_in_time_feature_matrix(
        [],
        [DAY_1],
        definition=SMALL_FEATURE_DEFINITION,
        start=DAY_2,
    )

    assert matrix.decision_timestamps == ()
    assert matrix.values.shape == (0, 2)
    assert matrix.missing_mask.shape == (0, 2)
    assert matrix.definition.feature_names == ("TREND_SCORE", "FLOW_SCORE")


def test_forward_targets_are_separate_and_support_the_frozen_target_schema() -> None:
    observations = [
        target(
            "future_1w_return",
            0.10,
            DAY_1,
            DAY_1 + timedelta(weeks=1),
            DAY_1 + timedelta(weeks=1, minutes=1),
        ),
        target(
            "hit_2R_before_1R",
            True,
            DAY_1,
            DAY_1 + timedelta(days=3),
            DAY_1 + timedelta(days=3, minutes=1),
        ),
    ]

    targets = build_forward_target_matrix(observations, [DAY_1])
    features = build_point_in_time_feature_matrix([], [DAY_1])

    assert targets.definition.target_names == FORWARD_TARGET_NAMES
    assert targets.values.shape == (1, 7)
    assert targets.values[0, 0] == pytest.approx(0.10)
    assert targets.values[0, 6] == 1.0
    assert np.count_nonzero(targets.missing_mask) == 5
    assert not set(FORWARD_TARGET_NAMES).intersection(features.definition.feature_names)
    assert "outcome_times" in targets.as_record()
    assert "outcome_times" not in features.as_record()


def test_target_extraction_cutoff_exposes_only_available_revision() -> None:
    outcome_time = DAY_1 + timedelta(weeks=1)
    original_available = outcome_time + timedelta(minutes=1)
    revised_available = outcome_time + timedelta(days=1)
    observations = [
        target(
            "future_1w_return",
            0.10,
            DAY_1,
            outcome_time,
            original_available,
        ),
        target(
            "future_1w_return",
            0.12,
            DAY_1,
            outcome_time,
            revised_available,
            revision=1,
            source_id="target-run-1-revision",
        ),
    ]

    as_known = build_forward_target_matrix(
        reversed(observations),
        [DAY_1],
        data_available_at=original_available,
    )
    latest = build_forward_target_matrix(observations, [DAY_1])

    assert as_known.values[0, 0] == pytest.approx(0.10)
    assert latest.values[0, 0] == pytest.approx(0.12)
    assert latest.source_ids[0][0] == "target-run-1-revision"
    assert as_known.revisions[0][0] == 0
    assert latest.revisions[0][0] == 1
    assert as_known.as_record()["data_available_at"] == original_available.isoformat()
    assert latest.as_record()["revisions"][0][0] == 1


def test_fixed_target_horizon_is_enforced() -> None:
    invalid = target(
        "future_8w_return",
        0.1,
        DAY_1,
        DAY_1 + timedelta(hours=1),
        DAY_1 + timedelta(hours=1),
    )

    with pytest.raises(FeatureMatrixError, match="4838400 seconds"):
        build_forward_target_matrix([invalid], [DAY_1])


def test_material_target_semantics_change_target_fingerprint() -> None:
    original = ForwardTargetDefinition(target_names=("future_8w_return",))
    changed_specification = replace(
        original.target_specifications[0],
        horizon=timedelta(weeks=8, microseconds=1),
    )
    changed = ForwardTargetDefinition(
        target_names=("future_8w_return",),
        target_specifications=(changed_specification,),
    )

    assert original.fingerprint != changed.fingerprint
    assert original.fingerprint == ForwardTargetDefinition(
        target_names=("future_8w_return",)
    ).fingerprint
    assert original.as_record()["target_specifications"][0][
        "horizon_seconds"
    ] == int(timedelta(weeks=8).total_seconds())
    assert original.as_record()["target_specifications"][0][
        "horizon_microseconds"
    ] == 8 * 7 * 86_400 * 1_000_000


def test_material_feature_provenance_changes_feature_fingerprint() -> None:
    original = FeatureMatrixDefinition(feature_names=("TREND_SCORE",))
    changed_parameter_set = FeatureMatrixDefinition(
        feature_names=("TREND_SCORE",),
        provenance=replace(original.provenance, parameter_set_id="challenger_v2"),
    )
    changed_price_policy = FeatureMatrixDefinition(
        feature_names=("TREND_SCORE",),
        provenance=replace(
            original.provenance,
            price_source_policy_version="PRICE_SOURCE_POLICY_V2",
        ),
    )

    assert original.fingerprint != changed_parameter_set.fingerprint
    assert original.fingerprint != changed_price_policy.fingerprint
    assert original.fingerprint == FeatureMatrixDefinition(
        feature_names=("TREND_SCORE",),
        provenance=FeatureMatrixProvenance(),
    ).fingerprint


def test_selected_feature_revision_survives_serialization() -> None:
    revised = feature(
        "TREND_SCORE",
        71,
        DAY_1,
        DAY_1 + timedelta(hours=1),
        revision=3,
        source_id="feature-run-revision-3",
    )

    matrix = build_point_in_time_feature_matrix(
        [revised],
        [DAY_2],
        definition=SMALL_FEATURE_DEFINITION,
    )

    assert matrix.revisions[0][0] == 3
    assert matrix.as_record()["revisions"][0][0] == 3
    assert matrix.revisions[0][1] is None


def test_feature_and_target_observation_types_cannot_be_mixed() -> None:
    target_row = target(
        "future_1w_return",
        0.1,
        DAY_1,
        DAY_1 + timedelta(weeks=1),
        DAY_1 + timedelta(weeks=1, minutes=1),
    )
    feature_row = feature("TREND_SCORE", 70, DAY_1, DAY_1)

    with pytest.raises(FeatureMatrixError, match="FeatureObservation"):
        build_point_in_time_feature_matrix(
            [target_row],  # type: ignore[list-item]
            [DAY_1],
            definition=SMALL_FEATURE_DEFINITION,
        )
    with pytest.raises(FeatureMatrixError, match="ForwardTargetObservation"):
        build_forward_target_matrix(
            [feature_row],  # type: ignore[list-item]
            [DAY_1],
        )


@pytest.mark.parametrize(
    "call,match",
    [
        (
            lambda: FeatureMatrixDefinition(feature_names=("A", "A")),
            "unique",
        ),
        (
            lambda: FeatureMatrixDefinition(feature_names=()),
            "at least one",
        ),
        (
            lambda: FeatureObservation(
                "A",
                np.inf,
                DAY_1,
                DAY_1,
                "source",
            ),
            "finite",
        ),
        (
            lambda: FeatureObservation("A", True, DAY_1, DAY_1, "source"),
            "boolean",
        ),
        (
            lambda: FeatureObservation("A", 1, DAY_2, DAY_1, "source"),
            "available_at",
        ),
        (
            lambda: FeatureObservation(
                "A",
                1,
                DAY_1.replace(tzinfo=None),
                DAY_1,
                "source",
            ),
            "timezone-aware UTC",
        ),
        (
            lambda: FeatureObservation(
                "A",
                1,
                DAY_1.astimezone(timezone(timedelta(hours=1))),
                DAY_1,
                "source",
            ),
            "must be UTC",
        ),
        (
            lambda: target("hit_2R_before_1R", 0.5, DAY_1, DAY_2, DAY_2),
            "binary",
        ),
        (
            lambda: target("future_1w_return", 0.1, DAY_1, DAY_1, DAY_2),
            "after decision",
        ),
        (
            lambda: decision_timestamp_range(DAY_2, DAY_1),
            "end must be",
        ),
        (
            lambda: decision_timestamp_range(DAY_1, DAY_2, step=timedelta(0)),
            "positive timedelta",
        ),
    ],
)
def test_invalid_matrix_inputs_fail_fast(call, match) -> None:
    with pytest.raises(FeatureMatrixError, match=match):
        call()


def test_duplicate_observation_identities_and_decision_times_fail_fast() -> None:
    row = feature("TREND_SCORE", 70, DAY_1, DAY_1)

    with pytest.raises(FeatureMatrixError, match="duplicate feature"):
        build_point_in_time_feature_matrix(
            [row, row],
            [DAY_2],
            definition=SMALL_FEATURE_DEFINITION,
        )
    with pytest.raises(FeatureMatrixError, match="decision timestamps must be unique"):
        build_point_in_time_feature_matrix(
            [row],
            [DAY_2, DAY_2],
            definition=SMALL_FEATURE_DEFINITION,
        )


def test_unrequested_features_are_ignored_without_changing_requested_schema() -> None:
    matrix = build_point_in_time_feature_matrix(
        [
            feature("TREND_SCORE", 70, DAY_1, DAY_1),
            feature("EXPERIMENTAL_ONLY", 999, DAY_1, DAY_1),
        ],
        [DAY_2],
        definition=SMALL_FEATURE_DEFINITION,
    )

    assert matrix.definition.feature_names == ("TREND_SCORE", "FLOW_SCORE")
    assert matrix.values.shape == (1, 2)
    assert matrix.values[0, 0] == 70
    assert np.isnan(matrix.values[0, 1])


def test_custom_target_order_is_preserved_reproducibly() -> None:
    definition = ForwardTargetDefinition(
        target_names=("future_MAE", "future_MFE"),
        version="PATH_TARGETS_V1",
    )
    targets = build_forward_target_matrix(
        [
            target("future_MFE", 0.25, DAY_1, DAY_4, DAY_4),
            target("future_MAE", -0.10, DAY_1, DAY_4, DAY_4),
        ],
        [DAY_1],
        definition=definition,
    )

    assert targets.definition.target_names == ("future_MAE", "future_MFE")
    np.testing.assert_array_equal(targets.values, [[-0.10, 0.25]])
    assert targets.definition.fingerprint == definition.fingerprint
