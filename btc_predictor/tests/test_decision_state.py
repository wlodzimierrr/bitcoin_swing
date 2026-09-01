"""BTC-190: market state stored for every decision date."""

import json
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from btc_predictor.research import (
    DECISION_STATE_FEATURE_ID,
    DECISION_STATE_OUTCOME_NAMES,
    DECISION_STATE_POLICY_VERSION,
    DECISION_STATE_PRODUCTION_STATUS,
    DECISION_STATE_PROMOTION_TICKET,
    DECISION_STATE_REASON_CODES,
    DECISION_STATE_SCORE_NAMES,
    NO_SETUP,
    NOT_TRADED,
    OUTCOME_AVAILABLE,
    OUTCOME_MISSING_VALUE,
    OUTCOME_NOT_RECORDED,
    OUTCOME_PENDING_HORIZON,
    SCORE_AVAILABLE,
    SCORE_MISSING_VALUE,
    SCORE_NOT_OBSERVED,
    TRADED,
    UNCLASSIFIED_REGIME,
    DecisionStateDefinition,
    DecisionStateError,
    DecisionStateObservation,
    FeatureMatrixDefinition,
    FeatureMatrixProvenance,
    FeatureObservation,
    ForwardTargetObservation,
    build_decision_state_store,
    build_forward_target_matrix,
    build_point_in_time_feature_matrix,
    decision_timestamp_range,
    restore_decision_state_store,
)
from btc_predictor.signals.data_quality import RecommendationReasonCode


START = datetime(2024, 1, 1, tzinfo=UTC)
DAY = timedelta(days=1)
GRID = decision_timestamp_range(START, START + 3 * DAY, step=DAY)
LATE_EXTRACTION = GRID[-1] + timedelta(weeks=8) + DAY
EARLY_EXTRACTION = GRID[-1] + timedelta(weeks=2, days=1)
EXCURSION_WINDOW = timedelta(days=14)
FIXED_HORIZONS = {
    "future_1w_return": timedelta(weeks=1),
    "future_2w_return": timedelta(weeks=2),
    "future_4w_return": timedelta(weeks=4),
    "future_8w_return": timedelta(weeks=8),
}
SCORE_SOURCE = "feature_pipeline"
OUTCOME_SOURCE = "outcome_pipeline"
DECISION_SOURCE = "paper_advisory"


def _score_value(index: int, score_name: str) -> float:
    return round(40.0 + index * 1.5 + len(score_name) * 0.25, 6)


def _outcome_value(index: int, outcome_name: str) -> float:
    sign = -1.0 if outcome_name == "future_MAE" else 1.0
    return round(sign * (0.01 + index * 0.005 + len(outcome_name) * 0.001), 6)


def _feature_observations(
    *,
    omit: tuple[tuple[int, str], ...] = (),
    none_valued: tuple[tuple[int, str], ...] = (),
) -> tuple[FeatureObservation, ...]:
    rows: list[FeatureObservation] = []
    for index, decision_time in enumerate(GRID):
        for score_name in DECISION_STATE_SCORE_NAMES:
            if (index, score_name) in omit:
                continue
            value = (
                None
                if (index, score_name) in none_valued
                else _score_value(index, score_name)
            )
            rows.append(
                FeatureObservation(
                    feature_name=score_name,
                    value=value,
                    observation_time=decision_time,
                    available_at=decision_time,
                    source_id=SCORE_SOURCE,
                )
            )
    return tuple(rows)


def _target_observations(
    *,
    omit: tuple[tuple[int, str], ...] = (),
    none_valued: tuple[tuple[int, str], ...] = (),
) -> tuple[ForwardTargetObservation, ...]:
    rows: list[ForwardTargetObservation] = []
    for index, decision_time in enumerate(GRID):
        for outcome_name in DECISION_STATE_OUTCOME_NAMES:
            if (index, outcome_name) in omit:
                continue
            horizon = FIXED_HORIZONS.get(outcome_name, EXCURSION_WINDOW)
            outcome_time = decision_time + horizon
            value = (
                None
                if (index, outcome_name) in none_valued
                else _outcome_value(index, outcome_name)
            )
            rows.append(
                ForwardTargetObservation(
                    target_name=outcome_name,
                    value=value,
                    decision_timestamp=decision_time,
                    outcome_time=outcome_time,
                    available_at=outcome_time,
                    source_id=OUTCOME_SOURCE,
                )
            )
    return tuple(rows)


def _features(
    *,
    omit: tuple[tuple[int, str], ...] = (),
    none_valued: tuple[tuple[int, str], ...] = (),
    definition: FeatureMatrixDefinition | None = None,
    timestamps: tuple[datetime, ...] = GRID,
):
    return build_point_in_time_feature_matrix(
        _feature_observations(omit=omit, none_valued=none_valued),
        timestamps,
        definition=definition,
    )


def _targets(
    *,
    omit: tuple[tuple[int, str], ...] = (),
    none_valued: tuple[tuple[int, str], ...] = (),
    data_available_at: datetime | None = None,
    timestamps: tuple[datetime, ...] = GRID,
):
    return build_forward_target_matrix(
        _target_observations(omit=omit, none_valued=none_valued),
        timestamps,
        definition=None,
        data_available_at=data_available_at,
    )


def _observation(
    index: int,
    *,
    decision: str = "NO_TRADE",
    setup: str = NO_SETUP,
    regime: str = "NEUTRAL",
    execution_status: str = NOT_TRADED,
    trade_reference: str | None = None,
    reason_codes: tuple[RecommendationReasonCode, ...] = (),
) -> DecisionStateObservation:
    return DecisionStateObservation(
        decision_timestamp=GRID[index],
        data_available_at=GRID[index],
        decision=decision,
        setup=setup,
        regime=regime,
        execution_status=execution_status,
        source_id=DECISION_SOURCE,
        trade_reference=trade_reference,
        reason_codes=reason_codes,
    )


REJECTION_REASON = RecommendationReasonCode(
    code="ENTRY_CONVICTION_BELOW_VALID",
    source_component="entry_action",
    severity="warning",
    detail="Entry conviction below the valid-trade threshold.",
)


def _observations() -> tuple[DecisionStateObservation, ...]:
    return (
        _observation(0, reason_codes=(REJECTION_REASON,)),
        _observation(
            1,
            decision="WATCH",
            setup="BULLISH_RESET",
            regime="MILD_BULL",
            reason_codes=(REJECTION_REASON,),
        ),
        _observation(
            2,
            decision="ENTER",
            setup="BULL_TREND_CONTINUATION",
            regime="BULL",
            execution_status=TRADED,
            trade_reference="trade-0001",
        ),
        _observation(3, decision="HOLD", regime=UNCLASSIFIED_REGIME),
    )


def _store(**kwargs):
    return build_decision_state_store(
        kwargs.pop("observations", _observations()),
        kwargs.pop("features", _features()),
        kwargs.pop("targets", _targets()),
        extraction_time=kwargs.pop("extraction_time", LATE_EXTRACTION),
        **kwargs,
    )


def test_store_covers_every_decision_date_not_only_traded_dates() -> None:
    store = _store()

    assert store.decision_timestamps == GRID
    assert store.coverage.decision_date_count == len(GRID)
    assert store.coverage.traded_count == 1
    assert store.coverage.not_traded_count == 3
    assert store.coverage.decision_counts["NO_TRADE"] == 1
    assert store.coverage.decision_counts["WATCH"] == 1
    assert store.coverage.decision_counts["ENTER"] == 1
    assert store.coverage.decision_counts["TRIM"] == 0
    assert store.coverage.setup_counts[NO_SETUP] == 2
    assert store.coverage.regime_counts[UNCLASSIFIED_REGIME] == 1
    assert tuple(row.decision_timestamp for row in store.rejected_rows()) == (
        GRID[0],
        GRID[1],
        GRID[3],
    )
    assert tuple(row.decision_timestamp for row in store.traded_rows()) == (GRID[2],)
    assert store.row(GRID[2]).trade_reference == "trade-0001"


def test_rejected_rows_retain_scores_outcomes_and_reason_codes() -> None:
    store = _store()

    rejected = store.row(GRID[1])
    assert rejected.decision == "WATCH"
    assert rejected.setup == "BULLISH_RESET"
    assert not rejected.traded
    assert rejected.trade_reference is None
    assert rejected.score("TREND_SCORE").value == _score_value(1, "TREND_SCORE")
    assert rejected.score("TREND_SCORE").status == SCORE_AVAILABLE
    assert rejected.outcome("future_4w_return").value == _outcome_value(
        1, "future_4w_return"
    )
    assert rejected.outcome("future_MAE").value == _outcome_value(1, "future_MAE")
    assert rejected.reason_codes == (REJECTION_REASON,)


def test_scores_and_outcomes_keep_point_in_time_provenance() -> None:
    store = _store()

    row = store.row(GRID[2])
    score = row.score("FLOW_SCORE")
    assert score.source_id == SCORE_SOURCE
    assert score.observation_time == GRID[2]
    assert score.available_at == GRID[2]
    assert score.revision == 0
    outcome = row.outcome("future_8w_return")
    assert outcome.source_id == OUTCOME_SOURCE
    assert outcome.outcome_time == GRID[2] + timedelta(weeks=8)
    assert outcome.available_at == outcome.outcome_time
    assert outcome.status == OUTCOME_AVAILABLE


def test_scores_ignore_values_published_after_the_decision_time() -> None:
    late = FeatureObservation(
        feature_name="TREND_SCORE",
        value=99.0,
        observation_time=GRID[0],
        available_at=GRID[0] + DAY,
        source_id="late_revision",
        revision=1,
    )
    features = build_point_in_time_feature_matrix(
        (*_feature_observations(omit=((1, "TREND_SCORE"),)), late),
        GRID,
    )
    store = _store(features=features)

    first = store.row(GRID[0]).score("TREND_SCORE")
    assert first.value == _score_value(0, "TREND_SCORE")
    assert first.source_id == SCORE_SOURCE
    assert first.available_at == GRID[0]
    revised = store.row(GRID[1]).score("TREND_SCORE")
    assert revised.value == 99.0
    assert revised.source_id == "late_revision"
    assert revised.available_at == GRID[1]


def test_unavailable_horizons_are_pending_and_never_zero_filled() -> None:
    store = _store(
        targets=_targets(data_available_at=EARLY_EXTRACTION),
        extraction_time=EARLY_EXTRACTION,
    )

    row = store.row(GRID[0])
    assert row.outcome("future_1w_return").status == OUTCOME_AVAILABLE
    assert row.outcome("future_2w_return").status == OUTCOME_AVAILABLE
    for outcome_name in ("future_4w_return", "future_8w_return"):
        outcome = row.outcome(outcome_name)
        assert outcome.status == OUTCOME_PENDING_HORIZON
        assert outcome.value is None
        assert outcome.outcome_time is None
        assert outcome.available_at is None
        assert outcome.source_id is None
        assert outcome.revision is None
    assert store.coverage.outcome_status_counts["future_8w_return"] == {
        OUTCOME_AVAILABLE: 0,
        OUTCOME_MISSING_VALUE: 0,
        OUTCOME_PENDING_HORIZON: 4,
        OUTCOME_NOT_RECORDED: 0,
    }


def test_elapsed_but_unrecorded_outcomes_are_not_recorded() -> None:
    store = _store(
        targets=_targets(omit=((0, "future_1w_return"), (1, "future_MFE"))),
    )

    assert store.row(GRID[0]).outcome("future_1w_return").status == (
        OUTCOME_NOT_RECORDED
    )
    assert store.row(GRID[0]).outcome("future_1w_return").value is None
    assert store.row(GRID[1]).outcome("future_MFE").status == OUTCOME_NOT_RECORDED
    assert store.coverage.outcome_status_counts["future_1w_return"] == {
        OUTCOME_AVAILABLE: 3,
        OUTCOME_MISSING_VALUE: 0,
        OUTCOME_PENDING_HORIZON: 0,
        OUTCOME_NOT_RECORDED: 1,
    }


def test_recorded_but_valueless_cells_keep_provenance_and_missing_status() -> None:
    store = _store(
        features=_features(none_valued=((1, "FLOW_SCORE"),)),
        targets=_targets(none_valued=((2, "future_MFE"),)),
    )

    score = store.row(GRID[1]).score("FLOW_SCORE")
    assert score.status == SCORE_MISSING_VALUE
    assert score.value is None
    assert score.source_id == SCORE_SOURCE
    outcome = store.row(GRID[2]).outcome("future_MFE")
    assert outcome.status == OUTCOME_MISSING_VALUE
    assert outcome.value is None
    assert outcome.outcome_time == GRID[2] + EXCURSION_WINDOW


def test_unobserved_scores_carry_no_provenance() -> None:
    store = _store(features=_features(omit=((0, "STRUCTURE_SCORE"),)))

    score = store.row(GRID[0]).score("STRUCTURE_SCORE")
    assert score.status == SCORE_NOT_OBSERVED
    assert score.value is None
    assert score.source_id is None
    assert score.observation_time is None
    assert store.coverage.score_status_counts["STRUCTURE_SCORE"] == {
        SCORE_AVAILABLE: 3,
        SCORE_MISSING_VALUE: 0,
        SCORE_NOT_OBSERVED: 1,
    }


def test_missing_decision_state_for_a_decision_date_fails_closed() -> None:
    observations = tuple(item for item in _observations() if item.decision_timestamp != GRID[1])

    with pytest.raises(DecisionStateError, match="every decision date"):
        _store(observations=observations)


def test_duplicate_decision_state_is_rejected() -> None:
    observations = (*_observations(), _observation(2, execution_status=NOT_TRADED))

    with pytest.raises(DecisionStateError, match="unique"):
        _store(observations=observations)


def test_decision_state_outside_the_decision_grid_is_rejected() -> None:
    outside = DecisionStateObservation(
        decision_timestamp=GRID[-1] + DAY,
        data_available_at=GRID[-1] + DAY,
        decision="NO_TRADE",
        setup=NO_SETUP,
        regime="NEUTRAL",
        execution_status=NOT_TRADED,
        source_id=DECISION_SOURCE,
    )

    with pytest.raises(DecisionStateError, match="outside the decision grid"):
        _store(observations=(*_observations(), outside))


def test_feature_and_target_grids_must_match() -> None:
    shifted = GRID[:-1]

    with pytest.raises(DecisionStateError, match="must match exactly"):
        _store(targets=_targets(timestamps=shifted))


def test_observations_are_ordered_by_decision_timestamp() -> None:
    shuffled = tuple(reversed(_observations()))

    store = _store(observations=shuffled)

    assert store.decision_timestamps == GRID


def test_outcomes_published_after_the_extraction_time_are_rejected() -> None:
    with pytest.raises(DecisionStateError, match="after the extraction time"):
        _store(extraction_time=EARLY_EXTRACTION)


def test_target_cutoff_must_equal_the_extraction_time() -> None:
    with pytest.raises(DecisionStateError, match="data_available_at must equal"):
        _store(
            targets=_targets(data_available_at=EARLY_EXTRACTION),
            extraction_time=LATE_EXTRACTION,
        )


def test_extraction_time_must_not_precede_the_last_decision_date() -> None:
    with pytest.raises(DecisionStateError, match="extraction_time must be >="):
        _store(extraction_time=GRID[0])


def test_missing_score_columns_are_rejected() -> None:
    definition = FeatureMatrixDefinition(
        feature_names=("TREND_SCORE", "FLOW_SCORE"),
    )

    with pytest.raises(DecisionStateError, match="does not contain scores"):
        _store(features=_features(definition=definition))


def test_outcome_price_source_policy_must_match_feature_provenance() -> None:
    definition = FeatureMatrixDefinition(
        provenance=FeatureMatrixProvenance(
            price_source_policy_version="OTHER_PRICE_SOURCE_POLICY_V9",
        ),
    )

    with pytest.raises(DecisionStateError, match="price-source policy"):
        _store(features=_features(definition=definition))


def test_traded_rows_require_a_trade_reference() -> None:
    with pytest.raises(DecisionStateError, match="requires a trade_reference"):
        _observation(0, decision="ENTER", execution_status=TRADED)

    with pytest.raises(DecisionStateError, match="must not carry a trade_reference"):
        _observation(0, trade_reference="trade-0002")


def test_decision_state_rejects_unknown_vocabularies() -> None:
    with pytest.raises(DecisionStateError, match="decision must be one of"):
        _observation(0, decision="BUY_THE_DIP")
    with pytest.raises(DecisionStateError, match="setup must be one of"):
        _observation(0, setup="SETUP_E")
    with pytest.raises(DecisionStateError, match="regime must be one of"):
        _observation(0, regime="SIDEWAYS")
    with pytest.raises(DecisionStateError, match="execution_status must be one of"):
        _observation(0, execution_status="MAYBE")


def test_decision_state_evidence_must_be_available_by_the_decision_time() -> None:
    with pytest.raises(DecisionStateError, match="data_available_at must be <="):
        DecisionStateObservation(
            decision_timestamp=GRID[0],
            data_available_at=GRID[0] + DAY,
            decision="NO_TRADE",
            setup=NO_SETUP,
            regime="NEUTRAL",
            execution_status=NOT_TRADED,
            source_id=DECISION_SOURCE,
        )


def test_store_matrices_expose_missing_values_as_nan() -> None:
    store = _store(
        features=_features(omit=((0, "STRUCTURE_SCORE"),)),
        targets=_targets(omit=((0, "future_1w_return"),)),
    )

    scores, score_mask = store.score_matrix()
    outcomes, outcome_mask = store.outcome_matrix()

    assert scores.shape == (len(GRID), len(DECISION_STATE_SCORE_NAMES))
    assert outcomes.shape == (len(GRID), len(DECISION_STATE_OUTCOME_NAMES))
    assert not scores.flags.writeable
    assert not outcomes.flags.writeable
    structure = DECISION_STATE_SCORE_NAMES.index("STRUCTURE_SCORE")
    first_return = DECISION_STATE_OUTCOME_NAMES.index("future_1w_return")
    assert bool(score_mask[0, structure])
    assert bool(np.isnan(scores[0, structure]))
    assert bool(outcome_mask[0, first_return])
    assert score_mask.sum() == 1
    assert outcome_mask.sum() == 1
    assert scores[1, DECISION_STATE_SCORE_NAMES.index("TREND_SCORE")] == _score_value(
        1, "TREND_SCORE"
    )


def test_store_persists_configuration_versions_and_reason_codes() -> None:
    store = _store()

    assert store.feature_id == DECISION_STATE_FEATURE_ID
    assert store.policy_version == DECISION_STATE_POLICY_VERSION
    assert store.production_status == DECISION_STATE_PRODUCTION_STATUS
    assert store.promotion_ticket == DECISION_STATE_PROMOTION_TICKET
    assert store.reason_codes == DECISION_STATE_REASON_CODES
    assert store.config_metadata["strategy_version"] == "swing_v1.2"
    assert store.config_metadata["config_version"] == "strategy_config_v2"
    assert store.config_metadata["parameter_set_id"] == "default_phase1"
    record = store.as_record()
    assert record["definition"]["score_names"] == list(DECISION_STATE_SCORE_NAMES)
    assert record["definition"]["outcome_names"] == list(DECISION_STATE_OUTCOME_NAMES)
    assert record["rows"][1]["reason_codes"] == [
        {
            "code": REJECTION_REASON.code,
            "source_component": REJECTION_REASON.source_component,
            "severity": REJECTION_REASON.severity,
            "detail": REJECTION_REASON.detail,
        }
    ]


def test_store_is_deterministic_and_json_serializable() -> None:
    first = _store()
    second = _store()

    assert first.store_id == second.store_id
    assert first.evidence_digest == second.evidence_digest
    assert first.as_record() == second.as_record()
    assert json.loads(json.dumps(first.as_record())) == first.as_record()


def test_store_round_trips_through_its_record() -> None:
    store = _store()

    restored = restore_decision_state_store(
        json.loads(json.dumps(store.as_record()))
    )

    assert restored == store
    assert restored.as_record() == store.as_record()
    assert restored.rejected_rows() == store.rejected_rows()


def test_restore_rejects_tampered_values() -> None:
    store = _store()
    record = json.loads(json.dumps(store.as_record()))
    record["rows"][0]["scores"][0]["value"] = 1.0

    with pytest.raises(DecisionStateError, match="does not match"):
        restore_decision_state_store(record)


def test_restore_rejects_tampered_coverage() -> None:
    store = _store()
    record = json.loads(json.dumps(store.as_record()))
    record["coverage"]["traded_count"] = 4

    with pytest.raises(DecisionStateError, match="coverage does not match"):
        restore_decision_state_store(record)


def test_restore_rejects_a_dropped_decision_date() -> None:
    store = _store()
    record = json.loads(json.dumps(store.as_record()))
    del record["rows"][0]

    with pytest.raises(DecisionStateError, match="coverage does not match"):
        restore_decision_state_store(record)


def test_definition_fingerprint_tracks_declared_columns() -> None:
    default = DecisionStateDefinition()
    narrowed = DecisionStateDefinition(score_names=("TREND_SCORE", "FLOW_SCORE"))

    assert default.fingerprint != narrowed.fingerprint
    assert default.as_record()["fingerprint"] == default.fingerprint
    assert DecisionStateDefinition().fingerprint == default.fingerprint


def test_definition_columns_change_the_store_identity() -> None:
    definition = DecisionStateDefinition(
        score_names=("TREND_SCORE", "FLOW_SCORE"),
        outcome_names=("future_1w_return", "future_MFE"),
    )

    store = _store(definition=definition)

    assert store.definition.score_names == ("TREND_SCORE", "FLOW_SCORE")
    assert tuple(item.outcome_name for item in store.rows[0].outcomes) == (
        "future_1w_return",
        "future_MFE",
    )
    assert store.store_id != _store().store_id


def test_definition_rejects_policy_version_drift() -> None:
    with pytest.raises(DecisionStateError, match="version must be"):
        DecisionStateDefinition(version="DECISION_STATE_STORE_V2")
    with pytest.raises(DecisionStateError, match="coverage_policy_version must be"):
        DecisionStateDefinition(coverage_policy_version="ANY_DECISION_DATE_V1")


def test_restore_rejects_unknown_columns() -> None:
    store = _store()
    record = json.loads(json.dumps(store.as_record()))
    record["rows"][0]["scores"][0]["score_name"] = "SENTIMENT_SCORE"

    with pytest.raises(DecisionStateError, match="definition order"):
        restore_decision_state_store(record)
