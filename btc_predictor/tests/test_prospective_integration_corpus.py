"""POSTP1-001 pre-data protocol tests for ``PROSPECTIVE_INTEGRATION_CORPUS_V1``.

Every fixture here is synthetic.  No test collects a qualifying observation, no
test produces a real Stage-B aggregate, and a suite-level audit hook proves the
whole module opens nothing under ``data/`` and nothing on a sealed 2015-2019
path.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from decimal import Context, Decimal, localcontext
from pathlib import Path

import pytest

from btc_predictor.research import prospective_integration_corpus as corpus
from btc_predictor.research.prospective_integration_corpus import (
    CANDIDATE_TRACK,
    COLLECTION_AUTHORIZED,
    CONTROL_TRACK,
    CURRENT_LIFECYCLE_STATE,
    EVENT_CROSS_MARKET,
    EVENT_ISOLATED_VENUE,
    EVENT_NONE,
    EVENT_NOT_CLASSIFIABLE,
    FINAL_CLASSIFICATION,
    GAP_THROUGH_EVENT,
    GAP_THROUGH_NOT_EVALUABLE,
    GAP_THROUGH_NOT_PRESENT,
    LIFECYCLE_COLLECTING,
    LIFECYCLE_FROZEN,
    OUTPUT_NAMESPACE,
    PROTOCOL_STATUS,
    PROTOCOL_VERSION,
    REPORTABLE_NOT_CERTIFIABLE,
    RISK_SIZE_METRIC,
    STOP_EVENT_METRICS,
    STOP_HOURLY_CADENCE,
    STRATEGY_DAILY_CADENCE,
    TARGET_METRICS,
    UNDEFINED_INSUFFICIENT_EVIDENCE,
    CollectionNotAuthorizedError,
    ProspectiveCorpusError,
    ProviderObservation,
    StopEvaluationSlot,
    aggregate_stage_b_metric,
    assert_collection_not_authorized,
    assert_lifecycle_transition,
    classify_stop_event,
    decision_time_for,
    evidence_sufficiency_contract,
    historical_gate_authority,
    metric_evidence_contracts,
    nearest_rank_percentile,
    portfolio_track_contract,
    protocol_definition,
    protocol_hashes,
    restore_artifacts,
    risk_size_p95,
    scheduled_decision_slots,
    semantic_diff_from_v5_blockers,
    stop_event_taxonomy,
    verify_protocol_definition,
    write_artifacts,
)
from btc_predictor.research.reference_composite_v2 import V2_APPROVAL_GATES


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPOSITORY_ROOT / OUTPUT_NAMESPACE
SLOT_TIME = datetime(2026, 3, 2, 14, tzinfo=UTC)
PRIOR_TIME = SLOT_TIME - timedelta(hours=1)


def _observation(
    provider_id: str,
    *,
    low: str = "100",
    high: str = "110",
    open_: str = "105",
    close: str = "106",
    available_at: datetime | None = None,
    observation_time: datetime = SLOT_TIME,
) -> ProviderObservation:
    return ProviderObservation(
        provider_id=provider_id,
        observation_time=observation_time,
        available_at=available_at
        or decision_time_for(observation_time, STOP_HOURLY_CADENCE),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def _slot(
    providers: tuple[ProviderObservation, ...],
    *,
    stop: str = "99",
    direction: str = "long",
    track: str = CANDIDATE_TRACK,
    prior_price: str | None = "105",
    prior_time: datetime | None = PRIOR_TIME,
) -> StopEvaluationSlot:
    return StopEvaluationSlot(
        observation_time=SLOT_TIME,
        track=track,
        direction=direction,
        active_stop=Decimal(stop),
        providers=providers,
        prior_observable_price=None if prior_price is None else Decimal(prior_price),
        prior_observable_observation_time=None if prior_price is None else prior_time,
    )


# =============================================================================
# 1. historical-gate parity
# =============================================================================


def test_all_eight_gates_keep_their_frozen_threshold_direction_and_hard_role() -> None:
    frozen = {
        gate.metric: (gate.threshold, gate.direction, gate.hard, gate.rationale)
        for gate in V2_APPROVAL_GATES
        if gate.metric in TARGET_METRICS
    }
    assert set(frozen) == set(TARGET_METRICS)
    contracts = metric_evidence_contracts()["contracts"]
    for metric, (threshold, direction, hard, rationale) in frozen.items():
        contract = contracts[metric]
        assert contract["threshold"] == threshold
        assert contract["direction"] == direction
        assert contract["hard"] is hard is True
        assert contract["historical_definition"] == rationale


def test_the_semantic_diff_proves_zero_gate_value_changes() -> None:
    diff = semantic_diff_from_v5_blockers()
    assert diff["threshold_change_count"] == 0
    assert diff["direction_change_count"] == 0
    assert diff["hard_role_change_count"] == 0
    assert diff["metric_intent_change_count"] == 0
    assert diff["btc019_reopened"] is False
    for metric in TARGET_METRICS:
        assert diff["rows"][metric]["unchanged"] == {
            "definition": True,
            "direction": True,
            "hard": True,
            "threshold": True,
        }


def test_the_prospective_gates_match_the_v5_unresolved_stage_b_census() -> None:
    persisted = json.loads(
        (
            REPOSITORY_ROOT
            / "research_artifacts/btc019_v5_certification_pipeline/stage_ownership.json"
        ).read_text()
    )
    assert tuple(sorted(persisted["unresolved_stage_b_hard_gates"])) == TARGET_METRICS
    rows = {row["metric"]: row for row in persisted["rows"]}
    authority = historical_gate_authority()
    for metric in TARGET_METRICS:
        assert rows[metric]["threshold"] == authority[metric]["threshold"]
        assert rows[metric]["direction"] == authority[metric]["direction"]
        assert rows[metric]["hard"] is True


def test_this_protocol_authors_no_threshold() -> None:
    protocol = protocol_definition()
    assert protocol["no_threshold_authored"] is True
    assert protocol["status"] == PROTOCOL_STATUS
    thresholds = {
        metric: row["threshold"] for metric, row in protocol["historical_gate_authority"].items()
    }
    assert thresholds == {
        gate.metric: gate.threshold
        for gate in V2_APPROVAL_GATES
        if gate.metric in TARGET_METRICS
    }


# =============================================================================
# 2. decision universe, PIT and missing data
# =============================================================================


def test_the_scheduled_slot_census_is_deterministic_and_outcome_independent() -> None:
    start = datetime(2026, 3, 1, tzinfo=UTC)
    end = datetime(2026, 3, 5, tzinfo=UTC)
    daily = scheduled_decision_slots(start, end, cadence=STRATEGY_DAILY_CADENCE)
    assert len(daily) == 5
    assert daily == scheduled_decision_slots(start, end, cadence=STRATEGY_DAILY_CADENCE)
    assert [row["decision_time"] for row in daily] == [
        "2026-03-02T00:05:00+00:00",
        "2026-03-03T00:05:00+00:00",
        "2026-03-04T00:05:00+00:00",
        "2026-03-05T00:05:00+00:00",
        "2026-03-06T00:05:00+00:00",
    ]
    hourly = scheduled_decision_slots(
        start, start + timedelta(hours=3), cadence=STOP_HOURLY_CADENCE
    )
    assert [row["decision_time"] for row in hourly] == [
        "2026-03-01T01:05:00+00:00",
        "2026-03-01T02:05:00+00:00",
        "2026-03-01T03:05:00+00:00",
        "2026-03-01T04:05:00+00:00",
    ]


def test_no_universe_predicate_may_read_a_comparison_outcome() -> None:
    universes = corpus.decision_universe_contract()["universes"]
    assert set(universes) == set(corpus.DECISION_UNIVERSES)
    for name, row in universes.items():
        text = row["definition"].lower()
        assert "agree" not in text, name
        assert "disagree" not in text, name
    assert "never enter or leave a denominator" in (
        corpus.decision_universe_contract()["denominator_independence_rule"]
    )


def test_an_input_that_was_not_available_at_the_decision_time_is_refused() -> None:
    late = _observation(
        "bitstamp",
        available_at=decision_time_for(SLOT_TIME, STOP_HOURLY_CADENCE)
        + timedelta(seconds=1),
    )
    slot = _slot((late, _observation("coinbase"), _observation("bitfinex")))
    with pytest.raises(ProspectiveCorpusError, match="not available at the decision time"):
        classify_stop_event(slot)


def test_an_input_available_exactly_at_the_decision_time_is_admitted() -> None:
    boundary = _observation(
        "bitstamp", available_at=decision_time_for(SLOT_TIME, STOP_HOURLY_CADENCE)
    )
    record = classify_stop_event(
        _slot((boundary, _observation("coinbase"), _observation("bitfinex")))
    )
    assert record["available_provider_ids"] == ["bitstamp", "coinbase", "bitfinex"]


def test_a_missing_provider_stays_explicit_and_is_never_imputed() -> None:
    record = classify_stop_event(
        _slot((_observation("bitstamp", low="98"), _observation("coinbase", low="98")))
    )
    assert record["missing_provider_ids"] == ["bitfinex"]
    assert "REQUIRED_PROVIDER_MISSING" in record["reason_codes"]
    assert record["classification"] == EVENT_CROSS_MARKET


def test_a_duplicate_observation_for_one_provider_is_refused() -> None:
    with pytest.raises(ProspectiveCorpusError, match="duplicate observation"):
        classify_stop_event(
            _slot((_observation("bitstamp"), _observation("bitstamp", low="90")))
        )


def test_a_revision_is_a_new_append_only_row_not_an_overwrite() -> None:
    schema = corpus.data_schema_contract()
    snapshot = schema["tables"]["prospective_source_input_snapshot"]
    assert snapshot["append_only"] is True
    assert "revision" in snapshot["primary_key"]
    assert snapshot["primary_key"] == [
        "run_id",
        "source_family",
        "source_key",
        "observation_time",
        "revision",
    ]
    assert corpus.REVISION_POLICY == "APPEND_A_NEW_REVISION_ROW_NEVER_OVERWRITE"
    assert set(corpus.PROVENANCE_DETECTION_REQUIREMENTS) == {
        "deletion",
        "duplicate observation",
        "late arrival",
        "mutation",
        "revision",
        "source replacement",
    }


def test_the_daily_cadence_refuses_a_non_session_observation_time() -> None:
    with pytest.raises(ProspectiveCorpusError, match="canonical session start"):
        decision_time_for(datetime(2026, 3, 2, 9, tzinfo=UTC), STRATEGY_DAILY_CADENCE)
    with pytest.raises(ProspectiveCorpusError, match="exact UTC hour"):
        decision_time_for(
            datetime(2026, 3, 2, 9, 30, tzinfo=UTC), STOP_HOURLY_CADENCE
        )


# =============================================================================
# 3. stop-event classification
# =============================================================================


def test_two_confirming_venues_make_a_cross_market_confirmed_stop_event() -> None:
    record = classify_stop_event(
        _slot(
            (
                _observation("bitstamp", low="98"),
                _observation("coinbase", low="98.5"),
                _observation("bitfinex", low="101"),
            )
        )
    )
    assert record["classification"] == EVENT_CROSS_MARKET
    assert record["touching_provider_ids"] == ["bitstamp", "coinbase"]
    assert record["consensus_stop_extreme"] == "98.5"


def test_one_reaching_venue_makes_an_isolated_venue_stop_event() -> None:
    record = classify_stop_event(
        _slot(
            (
                _observation("bitstamp", low="98"),
                _observation("coinbase", low="101"),
                _observation("bitfinex", low="102"),
            )
        )
    )
    assert record["classification"] == EVENT_ISOLATED_VENUE
    assert record["touching_provider_ids"] == ["bitstamp"]
    assert "CONFIRMATION_QUORUM_ABSENT" in record["reason_codes"]


def test_no_reaching_venue_is_no_stop_event() -> None:
    record = classify_stop_event(_slot((
        _observation("bitstamp", low="101"),
        _observation("coinbase", low="102"),
        _observation("bitfinex", low="103"),
    )))
    assert record["classification"] == EVENT_NONE
    assert record["touching_provider_ids"] == []


def test_below_the_provider_quorum_a_slot_enters_no_denominator() -> None:
    record = classify_stop_event(_slot((_observation("bitstamp", low="90"),)))
    assert record["classification"] == EVENT_NOT_CLASSIFIABLE
    assert record["gap_through_state"] == GAP_THROUGH_NOT_EVALUABLE
    assert record["consensus_stop_outcome"] == corpus.STOP_OUTCOME_UNDEFINED
    assert record["consensus_stop_extreme"] is None
    assert "PROVIDER_QUORUM_ABSENT" in record["reason_codes"]


def test_a_stop_touched_exactly_counts_as_reached() -> None:
    record = classify_stop_event(
        _slot(
            (
                _observation("bitstamp", low="99"),
                _observation("coinbase", low="99"),
                _observation("bitfinex", low="120"),
            )
        )
    )
    assert record["classification"] == EVENT_CROSS_MARKET


def test_a_crossing_that_opens_beyond_the_stop_is_a_gap_through_event() -> None:
    record = classify_stop_event(
        _slot(
            (
                _observation("bitstamp", low="90", open_="95"),
                _observation("coinbase", low="90", open_="95"),
                _observation("bitfinex", low="90", open_="95"),
            ),
            prior_price="105",
        )
    )
    assert record["gap_through_state"] == GAP_THROUGH_EVENT
    assert record["consensus_stop_outcome"] == corpus.STOP_OUTCOME_TRIGGERED
    assert record["provider_stop_outcomes"] == {
        "bitfinex": corpus.STOP_OUTCOME_TRIGGERED,
        "bitstamp": corpus.STOP_OUTCOME_TRIGGERED,
        "coinbase": corpus.STOP_OUTCOME_TRIGGERED,
    }
    assert record["classification"] == EVENT_CROSS_MARKET


def test_trading_down_through_a_stop_inside_the_bar_is_not_a_gap_through() -> None:
    record = classify_stop_event(
        _slot(
            (
                _observation("bitstamp", low="90", open_="105"),
                _observation("coinbase", low="90", open_="105"),
                _observation("bitfinex", low="90", open_="105"),
            ),
            prior_price="105",
        )
    )
    assert record["gap_through_state"] == GAP_THROUGH_NOT_PRESENT
    assert record["consensus_stop_outcome"] == corpus.STOP_OUTCOME_NOT_TRIGGERED


def test_a_missing_session_only_widens_the_prior_observable_interval() -> None:
    """A REFERENCE_UNAVAILABLE run is handled by the same rule, not a new one."""

    record = classify_stop_event(
        _slot(
            (
                _observation("bitstamp", low="90", open_="95"),
                _observation("coinbase", low="90", open_="95"),
            ),
            prior_price="105",
            prior_time=SLOT_TIME - timedelta(hours=9),
        )
    )
    assert record["gap_through_state"] == GAP_THROUGH_EVENT
    assert record["prior_observable_observation_time"] == (
        (SLOT_TIME - timedelta(hours=9)).isoformat()
    )


def test_without_a_prior_observable_price_a_gap_through_is_not_evaluable() -> None:
    record = classify_stop_event(
        _slot(
            (
                _observation("bitstamp", low="90", open_="95"),
                _observation("coinbase", low="90", open_="95"),
            ),
            prior_price=None,
            prior_time=None,
        )
    )
    assert record["gap_through_state"] == GAP_THROUGH_NOT_EVALUABLE
    assert "NO_PRIOR_OBSERVABLE_REFERENCE_PRICE" in record["reason_codes"]


def test_a_short_stop_reads_the_high_side() -> None:
    record = classify_stop_event(
        _slot(
            (
                _observation("bitstamp", high="121"),
                _observation("coinbase", high="122"),
                _observation("bitfinex", high="105"),
            ),
            stop="120",
            direction="short",
            prior_price="100",
        )
    )
    assert record["stop_relevant_field"] == "high"
    assert record["classification"] == EVENT_CROSS_MARKET
    assert record["touching_provider_ids"] == ["bitstamp", "coinbase"]


def test_classification_is_invariant_to_provider_order() -> None:
    rows = (
        _observation("bitstamp", low="98"),
        _observation("coinbase", low="98.5"),
        _observation("bitfinex", low="101"),
    )
    first = classify_stop_event(_slot(rows))
    second = classify_stop_event(_slot(tuple(reversed(rows))))
    assert first == second


def test_classification_is_invariant_to_the_ambient_decimal_context() -> None:
    rows = (
        _observation("bitstamp", low="98.123456789012345678901234567890"),
        _observation("coinbase", low="98.5"),
        _observation("bitfinex", low="101"),
    )
    baseline = classify_stop_event(_slot(rows))
    with localcontext(Context(prec=4)):
        narrowed = classify_stop_event(_slot(rows))
    assert narrowed == baseline


def test_the_taxonomy_replaces_the_hand_picked_development_event_list() -> None:
    taxonomy = stop_event_taxonomy()
    assert taxonomy["hand_picked_development_events_used"] is False
    assert taxonomy["classifier"]["semantic_definition"][
        "manual_timestamp_selection_required"
    ] is False
    assert taxonomy["predecessor_replaced"].endswith("KNOWN_DEVELOPMENT_EVENTS")
    assert taxonomy["classifier"]["semantic_definition"]["candidate_neutral"] is True


# =============================================================================
# 4. numerators, denominators and insufficiency
# =============================================================================


@pytest.mark.parametrize("metric", TARGET_METRICS)
def test_every_metric_declares_owner_universe_numerator_and_denominator(
    metric: str,
) -> None:
    contract = metric_evidence_contracts()["contracts"][metric]
    for field in ("evidence_owner", "universe", "numerator", "denominator", "statistic"):
        assert isinstance(contract[field], str) and contract[field].strip(), field
    assert contract["universe"] in corpus.DECISION_UNIVERSES
    assert contract["zero_denominator"] == UNDEFINED_INSUFFICIENT_EVIDENCE
    assert contract["reason_vocabulary"] == list(corpus.OBSERVATION_REASON_VOCABULARY)


def test_trade_eligibility_denominator_excludes_only_non_evaluable_slots() -> None:
    contract = metric_evidence_contracts()["contracts"][
        "trade_eligibility_disagreement_rate"
    ]
    composition = contract["eligibility_composition"]
    for veto in ("regime_or_setup_veto", "risk_capacity_veto", "reward_risk_veto"):
        assert "not an exclusion" in composition[veto], veto
    assert "NOT_COMPARABLE" in composition["reference_unavailable"]
    assert "add path" in composition["already_in_position"]
    assert contract["universe"] == corpus.UNIVERSE_ELIGIBILITY_EVALUABLE


def test_setup_disagreement_compares_the_whole_detector_vector() -> None:
    contract = metric_evidence_contracts()["contracts"][
        "setup_classification_disagreement_rate"
    ]
    assert contract["comparison_field"] == "authoritative_setup_detector_state_vector"
    assert len(contract["vocabulary"]["detectors"]) == 4
    assert "NO_TRADE" in contract["numerator"]
    assert "precedence" in contract["numerator"]


def test_regime_disagreement_compares_the_categorical_label() -> None:
    contract = metric_evidence_contracts()["contracts"][
        "regime_classification_disagreement_rate"
    ]
    assert contract["comparison_field"] == "categorical_regime_state"
    assert contract["vocabulary_owner"].endswith("REGIME_CLASSIFICATION_LABELS")
    assert "never the compared field" in contract["numerator"]


def test_trade_action_uses_the_repository_action_vocabulary() -> None:
    contract = metric_evidence_contracts()["contracts"]["trade_action_disagreement_rate"]
    from btc_predictor.signals.data_quality import RECOMMENDATION_ACTIONS

    assert contract["vocabulary"] == list(RECOMMENDATION_ACTIONS)
    assert contract["vocabulary_owner"].endswith("RECOMMENDATION_ACTIONS")
    assert contract["universe"] == corpus.UNIVERSE_ACTION_EVALUABLE


def test_the_risk_size_statistic_is_nearest_rank_over_the_control_baseline() -> None:
    contract = metric_evidence_contracts()["contracts"][RISK_SIZE_METRIC]
    derivation = contract["derived_interpretation"]
    assert derivation["unique_interpretation"] is True
    assert set(derivation["refused_derivations"]) == {
        "interpolated_p95",
        "max_denominator",
        "nav_normalized_difference",
        "position_quantity_basis",
        "symmetric_mean_denominator",
    }
    assert contract["quantity"] == "position_notional"
    result = risk_size_p95(
        [Decimal("110"), Decimal("100"), Decimal("104")],
        [Decimal("100"), Decimal("100"), Decimal("100")],
    )
    # nearest rank at p95 over [0, 0.04, 0.1] -> ceil(0.95 * 3) = 3 -> 0.1
    assert result["value"] == "0.1"
    assert result["denominator"] == 3


def test_the_risk_size_percentile_is_nearest_rank_not_interpolated() -> None:
    values = [Decimal(index) for index in range(1, 21)]
    assert nearest_rank_percentile(values, Decimal("0.95")) == Decimal(19)
    # A linear-interpolation reading of the same vector returns 19.05.
    assert nearest_rank_percentile([Decimal("1"), Decimal("2")], Decimal("0.95")) == (
        Decimal("2")
    )


def test_the_risk_size_universe_refuses_a_non_positive_control_notional() -> None:
    with pytest.raises(ProspectiveCorpusError, match="strictly positive control"):
        risk_size_p95([Decimal("1")], [Decimal("0")])


def test_an_empty_sizing_universe_is_insufficient_evidence_not_zero() -> None:
    result = risk_size_p95([], [])
    assert result["value"] is None
    assert result["undefined_reason"] == UNDEFINED_INSUFFICIENT_EVIDENCE


@pytest.mark.parametrize("metric", TARGET_METRICS)
def test_a_zero_event_denominator_is_insufficient_and_never_a_pass(metric: str) -> None:
    result = aggregate_stage_b_metric(
        metric, numerator=0, denominator=0, synthetic=True
    )
    assert result["value"] is None
    assert result["undefined_reason"] == UNDEFINED_INSUFFICIENT_EVIDENCE
    absent = aggregate_stage_b_metric(
        metric, numerator=None, denominator=None, synthetic=True
    )
    assert absent["undefined_reason"] == UNDEFINED_INSUFFICIENT_EVIDENCE


def test_a_synthetic_rate_composes_exactly() -> None:
    result = aggregate_stage_b_metric(
        STOP_EVENT_METRICS[0], numerator=3, denominator=4, synthetic=True
    )
    assert result["value"] == "0.75"
    with pytest.raises(ProspectiveCorpusError, match="0 <= numerator <= denominator"):
        aggregate_stage_b_metric(
            STOP_EVENT_METRICS[0], numerator=5, denominator=4, synthetic=True
        )


# =============================================================================
# 5. portfolio tracks
# =============================================================================


def test_both_tracks_start_from_one_frozen_initial_state() -> None:
    contract = portfolio_track_contract()
    assert contract["tracks"][CANDIDATE_TRACK]["starts_from_initial_state"] is True
    assert contract["tracks"][CONTROL_TRACK]["starts_from_initial_state"] is True
    assert contract["initial_state"]["open_positions"] == []
    assert contract["initial_state"]["pending_orders"] == []
    assert contract["initial_state"]["realized_pnl"] == "0"
    assert corpus._digest(contract["initial_state"]) == contract["initial_state_sha256"]


def test_state_divergence_is_preserved_and_resynchronization_is_forbidden() -> None:
    contract = portfolio_track_contract()
    assert contract["divergence_policy"] == "ALLOW_NATURAL_STATE_DIVERGENCE"
    assert contract["resynchronization_policy"] == "FORBIDDEN"
    for field in (
        "first_divergence_decision_time",
        "divergence_cause_metric",
        "later_comparison_state",
    ):
        assert field in contract["divergence_evidence_fields"], field
    assert "resynchronize the two portfolio tracks" in (
        protocol_definition()["post_hoc_contamination"][
            "prohibited_after_collection_starts"
        ]
    )


def test_every_exogenous_input_is_shared_between_the_two_tracks() -> None:
    contract = portfolio_track_contract()
    shared = set(contract["shared_exogenous_input_families"])
    assert set(corpus.NON_PRICE_INPUT_SOURCES) <= shared
    for family in (
        "clock",
        "cost_slippage_model",
        "execution_model",
        "fees",
        "risk_limits",
        "strategy_configuration",
        "volatility_configuration",
    ):
        assert family in shared, family
    assert "raw_provider_ohlcv" not in shared
    assert contract["exogenous_divergence_reason"] == "EXOGENOUS_INPUT_DIVERGED"


def test_the_raw_corpus_stays_candidate_neutral() -> None:
    contract = portfolio_track_contract()
    assert contract["reference_identity_state"] == (
        "SUPPLIED_BY_SEPARATELY_FROZEN_EVALUATION_CONTRACT"
    )
    schema = corpus.data_schema_contract()["tables"]
    for name in corpus._APPEND_ONLY_RAW_TABLES:
        assert schema[name]["layer"] == "RAW"
        assert schema[name]["append_only"] is True
        assert "reference_identity" not in schema[name]["columns"], name
    assert schema["prospective_reference_evaluation"]["layer"] == "DERIVED"
    boundary = protocol_definition()["collector_boundary"]["interface"]
    assert boundary["CAPTURE"]["reads_reference_identity"] is False


def test_derived_records_hash_bind_the_raw_snapshot_and_prior_state() -> None:
    schema = corpus.data_schema_contract()["tables"]
    for name in (
        "prospective_strategy_evaluation",
        "prospective_risk_evaluation",
        "prospective_reference_evaluation",
    ):
        assert "input_snapshot_sha256" in schema[name]["columns"], name
        assert "output_sha256" in schema[name]["columns"], name
    assert "prior_portfolio_state_sha256" in (
        schema["prospective_trade_action"]["columns"]
    )
    assert "prior_state_sha256" in schema["prospective_portfolio_state"]["columns"]
    identity = protocol_definition()["evidence_identity_fields"]
    for field in (
        "corpus_protocol_sha256",
        "decision_time",
        "input_snapshot_sha256",
        "output_sha256",
        "prior_portfolio_state_sha256",
        "raw_source_identities",
        "reference_identity",
    ):
        assert field in identity, field


# =============================================================================
# 6. evidence sufficiency and horizon
# =============================================================================


def test_no_certification_minimum_is_guessed_and_stage_c_is_not_imported() -> None:
    sufficiency = evidence_sufficiency_contract()
    assert sufficiency["minimums_selected_from_observed_outcomes"] is False
    assert sufficiency["collection_horizon"]["calendar_minimum_days"] is None
    assert "90" in sufficiency["collection_horizon"]["calendar_minimum_rationale"]
    for metric in TARGET_METRICS:
        row = sufficiency["metrics"][metric]
        assert row["certification_sufficiency_state"] == REPORTABLE_NOT_CERTIFIABLE
        assert row["minimum_denominator_chosen_here"] is None
        assert row["zero_denominator_passes"] is False
        assert row["evaluability_minimum"]["minimum_comparable_denominator"] == 1
        assert row["evaluability_minimum"]["complete_slot_census_required"] is True


def test_the_v3_wilson_rule_is_not_carried_outside_its_declared_scope() -> None:
    sufficiency = evidence_sufficiency_contract()
    note = sufficiency["scoped_out_authority"]["per_pair_wilson_upper_bound_v1"]
    assert "only its own declared scope" in note


# =============================================================================
# 7. collection safety
# =============================================================================


def test_this_revision_is_a_pre_data_protocol_and_authorizes_no_collection() -> None:
    assert COLLECTION_AUTHORIZED is False
    assert CURRENT_LIFECYCLE_STATE == LIFECYCLE_FROZEN
    assert_collection_not_authorized()
    protocol = protocol_definition()
    assert protocol["collection_authorized"] is False
    assert protocol["safety"] == {
        "btc019_sealed_data_accessed": False,
        "new_market_evidence_collected": False,
        "qualifying_observations_collected": False,
        "real_stage_b_outcomes_evaluated": False,
    }


def test_entering_collecting_requires_the_independent_review_first() -> None:
    with pytest.raises(CollectionNotAuthorizedError, match="INDEPENDENT_XHIGH_REVIEW"):
        assert_lifecycle_transition(LIFECYCLE_FROZEN, LIFECYCLE_COLLECTING)
    with pytest.raises(ProspectiveCorpusError, match="may not transition"):
        assert_lifecycle_transition("DRAFT", "EVALUATED")


@pytest.mark.parametrize("metric", TARGET_METRICS)
def test_no_real_stage_b_aggregate_is_reachable_before_the_freeze_is_reviewed(
    metric: str,
) -> None:
    with pytest.raises(CollectionNotAuthorizedError, match="no real Stage-B aggregate"):
        aggregate_stage_b_metric(metric, numerator=1, denominator=2, synthetic=False)


def test_a_stage_b_pass_here_does_not_open_the_btc019_sealed_sample() -> None:
    protocol = protocol_definition()
    assert protocol["btc019"] == {
        "reopened": False,
        "sealed_sample_collected": False,
        "sealed_sample_opened": False,
        "successor_of_btc019": False,
        "terminal_classification": (
            "BTC019_TERMINALLY_BLOCKED_BY_MISSING_INTEGRATION_EVIDENCE"
        ),
    }
    assert protocol["sealed_sample_dependency"]["opens_btc019_on_stage_b_pass"] is False
    assert protocol["relationship_to_epic_t"] == {
        "epic_t_authority_change_required": False,
        "epic_t_modified": False,
        "epic_t_state": "CLOSED / PASS WITH NON-BLOCKING FINDINGS",
    }
    assert protocol["relationship_to_phase_1"]["btc019_historical_reference_research"] == (
        "TERMINALLY_BLOCKED"
    )


# =============================================================================
# 8. protocol hash integrity
# =============================================================================


def test_the_protocol_binds_every_material_child_hash() -> None:
    protocol = protocol_definition()
    hashes = protocol_hashes()
    assert set(hashes) == set(protocol["child_definition_sha256"]) | {"corpus_protocol"}
    assert len(protocol["child_definition_sha256"]) == 9
    for name, digest in protocol["child_definition_sha256"].items():
        assert corpus._is_sha256(digest), name
    verify_protocol_definition(protocol)


@pytest.mark.parametrize(
    "path",
    [
        ("status",),
        ("collection_authorized",),
        ("target_metrics",),
        ("historical_gate_authority", "risk_size_p95_relative_difference", "threshold"),
        ("child_definition_sha256", "stop_event_taxonomy"),
        ("post_hoc_contamination", "successor_protocol"),
        ("lifecycle", "current_state"),
    ],
)
def test_a_semantic_mutation_moves_the_protocol_hash_and_is_refused(
    path: tuple[str, ...],
) -> None:
    protocol = protocol_definition()
    tampered = json.loads(json.dumps(protocol))
    cursor = tampered
    for key in path[:-1]:
        cursor = cursor[key]
    current = cursor[path[-1]]
    if isinstance(current, bool):
        cursor[path[-1]] = not current
    elif isinstance(current, str):
        cursor[path[-1]] = f"{current}_TAMPERED"
    else:
        cursor[path[-1]] = [*current, "TAMPERED"]
    tampered.pop("definition_sha256")
    assert corpus._digest(tampered) != protocol["definition_sha256"]
    tampered["definition_sha256"] = corpus._digest(tampered)
    with pytest.raises(ProspectiveCorpusError, match="does not reproduce"):
        verify_protocol_definition(tampered)


def test_the_protocol_hash_is_invariant_to_the_ambient_decimal_context() -> None:
    baseline = protocol_definition()["definition_sha256"]
    with localcontext(Context(prec=3)):
        assert protocol_definition()["definition_sha256"] == baseline
    with localcontext(Context(prec=200)):
        assert protocol_definition()["definition_sha256"] == baseline


def test_the_protocol_hash_is_invariant_to_hash_seed_and_working_directory(
    tmp_path: Path,
) -> None:
    expected = protocol_definition()["definition_sha256"]
    script = (
        "import json, sys;"
        "from btc_predictor.research import prospective_integration_corpus as c;"
        "print(json.dumps(c.protocol_hashes()))"
    )
    for seed, cwd in (("0", REPOSITORY_ROOT), ("12345", tmp_path), ("7", tmp_path)):
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            cwd=cwd,
            env={
                **os.environ,
                "PYTHONHASHSEED": seed,
                "PYTHONPATH": str(REPOSITORY_ROOT),
            },
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["corpus_protocol"] == expected


# =============================================================================
# 9. persisted artifacts
# =============================================================================


def test_this_program_persists_nothing_inside_the_frozen_v5_json_census() -> None:
    """The V5 terminal assessment hashes every JSON under ``data/`` and
    ``research_artifacts/``, so one new artifact in either tree would move a
    frozen hash. This program's artifacts stay outside that census, and V5 must
    still recompute to its frozen value.

    The recomputation runs in a child interpreter because the V5 census opens
    every collected artifact under ``data/``; keeping it out of this process
    lets the suite-level audit hook below still prove that *this* protocol
    touches none of them.
    """

    assert not corpus.OUTPUT_NAMESPACE.startswith("research_artifacts/")
    assert not corpus.OUTPUT_NAMESPACE.startswith("data/")
    assert list(ARTIFACT_DIR.glob("*.json"))
    script = (
        "from pathlib import Path;"
        "from btc_predictor.research import reference_composite_v5 as v5;"
        "print(v5.v5_protocol_definition(Path('.'))['definition_sha256'])"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        cwd=REPOSITORY_ROOT,
        env={**os.environ, "PYTHONPATH": str(REPOSITORY_ROOT)},
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == corpus.FROZEN_V5_DEFINITION_SHA256


def test_the_persisted_artifacts_reproduce_from_the_module() -> None:
    protocol = restore_artifacts(ARTIFACT_DIR)
    assert protocol["definition_sha256"] == protocol_definition()["definition_sha256"]
    assert protocol["protocol_version"] == PROTOCOL_VERSION
    assert protocol["final_classification"] == FINAL_CLASSIFICATION


def test_writing_the_artifacts_is_deterministic(tmp_path: Path) -> None:
    write_artifacts(tmp_path)
    first = {path.name: path.read_bytes() for path in sorted(tmp_path.iterdir())}
    write_artifacts(tmp_path)
    second = {path.name: path.read_bytes() for path in sorted(tmp_path.iterdir())}
    assert first == second
    persisted = {path.name: path.read_bytes() for path in sorted(ARTIFACT_DIR.iterdir())}
    assert persisted == first


def test_a_tampered_child_artifact_is_refused(tmp_path: Path) -> None:
    write_artifacts(tmp_path)
    target = tmp_path / corpus.STOP_EVENT_TAXONOMY_FILENAME
    payload = json.loads(target.read_text())
    payload["classifier"]["semantic_definition"]["provider_quorum"] = 1
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ProspectiveCorpusError, match="does not reproduce"):
        restore_artifacts(tmp_path)


def test_the_report_states_the_final_classification_and_zero_gate_changes() -> None:
    report = (ARTIFACT_DIR / corpus.REPORT_FILENAME).read_text()
    assert FINAL_CLASSIFICATION in report
    assert "Threshold changes: `0`" in report
    assert "Direction changes: `0`" in report
    assert "Hard-role changes: `0`" in report
    assert "BTC-019 sealed sample collected / opened: no / no" in report


def test_the_digest_is_invariant_to_dictionary_insertion_order() -> None:
    protocol = protocol_definition()
    shuffled = {key: protocol[key] for key in reversed(list(protocol))}
    assert corpus._canonical_json(shuffled) == corpus._canonical_json(protocol)
    verify_protocol_definition(shuffled)


def test_diverged_track_stops_classify_independently_without_resynchronization() -> None:
    """Once an action disagreement moves one track's stop, the two tracks keep
    their own event universes.  Nothing here equalises them."""

    providers = (
        _observation("bitstamp", low="98"),
        _observation("coinbase", low="98.5"),
        _observation("bitfinex", low="101"),
    )
    candidate = classify_stop_event(
        _slot(providers, stop="99", track=CANDIDATE_TRACK)
    )
    control = classify_stop_event(
        _slot(providers, stop="97", track=CONTROL_TRACK)
    )
    assert candidate["classification"] == EVENT_CROSS_MARKET
    assert control["classification"] == EVENT_NONE
    assert candidate["event_id"] != control["event_id"]
    assert candidate["track"] == CANDIDATE_TRACK
    assert control["track"] == CONTROL_TRACK
    # The same slot with the same stop is one event per track, so a later
    # comparison can name which track's universe an event came from.
    assert (
        classify_stop_event(_slot(providers, stop="99", track=CANDIDATE_TRACK))
        == candidate
    )


# =============================================================================
# 10. suite-level instrumentation: this module opens no sealed or collected path
# =============================================================================

_AUDIT_CHILD_ENV = "PROSPECTIVE_CORPUS_AUDIT_CHILD"

_AUDIT_DRIVER = """
import os
import sys

violations = []
observed = []
module_path = sys.argv[1]
data_root = os.path.abspath(sys.argv[2])
repository_root = os.path.abspath(sys.argv[3])
patterns = ('2015', '2016', '2017', '2018', '2019')


def _hook(event, args):
    if event != 'open' or not args:
        return
    name = args[0]
    if not isinstance(name, (str, bytes)):
        return
    text = name.decode('utf-8', 'replace') if isinstance(name, bytes) else name
    observed.append(text)
    resolved = os.path.abspath(text)
    if resolved != repository_root and not resolved.startswith(
        repository_root + os.sep
    ):
        return
    base = os.path.basename(resolved)
    if base.endswith('.pyc'):
        return
    under_data = resolved == data_root or resolved.startswith(data_root + os.sep)
    dated = any(pattern in base for pattern in patterns)
    if not under_data and not dated:
        return
    if os.path.isfile(resolved):
        violations.append(text)


sys.addaudithook(_hook)

import pytest

code = pytest.main(['-q', '-p', 'no:cacheprovider', module_path])
marker = 'PROSPECTIVE' + '_AUDIT'
print(marker + '_OPENS', len(observed))
print(marker + '_BEGIN')
for path in sorted(set(violations)):
    print(path)
print(marker + '_END')
sys.exit(int(code))
"""


@pytest.mark.skipif(
    os.environ.get(_AUDIT_CHILD_ENV) == "1",
    reason="the audit child must not re-enter its own driver",
)
def test_the_whole_suite_opens_no_sealed_or_collected_path(tmp_path: Path) -> None:
    """Run this entire module under an audit hook on every ``open``.

    A pre-data protocol must be provable, not merely asserted: nothing in this
    suite may reach the BTC-019 sealed window or any collected market data.
    """

    driver = tmp_path / "audit_driver.py"
    driver.write_text(_AUDIT_DRIVER, encoding="ascii")
    result = subprocess.run(
        [
            sys.executable,
            str(driver),
            str(Path(__file__).resolve()),
            str(REPOSITORY_ROOT / "data"),
            str(REPOSITORY_ROOT),
        ],
        capture_output=True,
        cwd=REPOSITORY_ROOT,
        env={**os.environ, _AUDIT_CHILD_ENV: "1"},
        text=True,
    )
    tail = result.stdout[-8000:] + result.stderr[-8000:]
    assert result.returncode == 0, tail
    marker = "PROSPECTIVE" + "_AUDIT"
    assert f"{marker}_BEGIN" in result.stdout, tail
    body = result.stdout.rsplit(f"{marker}_BEGIN", 1)[1]
    violations = [
        line for line in body.rsplit(f"{marker}_END", 1)[0].splitlines() if line.strip()
    ]
    assert violations == [], f"the suite opened sealed or collected paths: {violations}"
    observed = int(
        next(
            line
            for line in result.stdout.splitlines()
            if line.startswith(f"{marker}_OPENS ")
        ).split()[1]
    )
    assert observed > 100, f"the audit hook observed only {observed} opens"
