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
from typing import Any

import pytest

from btc_predictor.data import derivatives, generic_series
from btc_predictor.data.ohlcv import OhlcvBar
from btc_predictor.features import flow, positioning, volatility
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
    track: str = CONTROL_TRACK,
    prior_price: str | None = "105",
    prior_time: datetime | None = PRIOR_TIME,
    prior_providers: tuple[ProviderObservation, ...] | None = None,
    candidate_position_state: str = "OPEN_INITIAL",
    first_divergence_decision_time: datetime | None = None,
) -> StopEvaluationSlot:
    if prior_providers is None:
        prior_providers = (
            ()
            if prior_price is None or prior_time is None
            else tuple(
                _observation(
                    provider_id,
                    observation_time=prior_time,
                    open_=prior_price,
                    high=prior_price,
                    low=prior_price,
                    close=prior_price,
                )
                for provider_id in corpus.REQUIRED_PROVIDER_IDS
            )
        )
    return StopEvaluationSlot(
        observation_time=SLOT_TIME,
        track=track,
        direction=direction,
        active_stop=Decimal(stop),
        active_stop_identity="synthetic-control-stop-v1",
        control_position_state="OPEN_INITIAL",
        candidate_position_state=candidate_position_state,
        providers=providers,
        prior_providers=prior_providers,
        first_divergence_decision_time=first_divergence_decision_time,
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


def test_liquidations_are_a_complete_required_pit_capture_family() -> None:
    contract = corpus.input_snapshot_schema()
    liquidation = contract["non_price_input_sources"]["liquidations"]
    assert liquidation["raw_table"] == "raw.liquidations"
    assert liquidation["observation_time_field"] == "observation_time"
    assert liquidation["available_at_field"] == "available_at"
    assert liquidation["ingested_at_field"] == "ingested_at"
    assert liquidation["revision_policy"] == (
        "APPEND_ONLY_NEW_REVISION_ROW_PER_RESTATEMENT"
    )
    assert "ORDERLINESS_SCORE" in liquidation["consuming_features"]
    assert "liquidation_cascade" in liquidation["consumer_path"]
    assert "liquidations" not in contract["excluded_input_families"]
    assert liquidation["prospective_acquisition_contract"] == (
        "PROSPECTIVE_LIQUIDATION_CAPTURE_V1"
    )
    assert (
        liquidation["existing_aggregate_distinguishes_missing_from_empty"] is False
    )


def test_every_frozen_phase_1_feature_has_complete_input_closure() -> None:
    coverage = corpus.feature_input_coverage_contract()
    assert coverage["all_frozen_features_covered"] is True
    assert coverage["feature_inventory"] == list(corpus.INITIAL_FEATURE_NAMES)
    assert set(coverage["rows"]) == set(corpus.INITIAL_FEATURE_NAMES)
    assert "liquidations" in coverage["required_raw_input_families"]
    for row in coverage["rows"].values():
        assert row["raw_input_families"]
        assert set(row["capture_contract_count_by_family"].values()) == {1}
        assert row["zero_fill_permitted"] is False
        assert row["missing_value_default"] is None
        assert row["future_information_reconstruction_permitted"] is False


def test_cvd_capture_cadence_is_new_pre_data_governance_not_inherited() -> None:
    cvd = corpus.NON_PRICE_INPUT_SOURCES["spot_perp_cvd"]
    governance = cvd["cadence_governance"]
    assert cvd["observation_cadence"] == "1h"
    assert cvd["observation_time_alignment"] == "exact UTC hour"
    assert cvd["zscore_window_periods"] == 20
    assert cvd["capture_state"].startswith("REQUIRES_NEW_COLLECTOR")
    assert cvd["prospective_acquisition_contract"] == "PROSPECTIVE_CVD_ACQUISITION_V1"
    assert governance["historically_inherited"] is False
    assert governance["selected_by_new_pre_data_governance"] is True
    assert governance["unit_tests_used_as_cadence_authority"] is False
    assert "cadence_derivation" not in cvd


def test_an_incomplete_cvd_cadence_governance_block_blocks_the_protocol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    governance = corpus.NON_PRICE_INPUT_SOURCES["spot_perp_cvd"][
        "cadence_governance"
    ]
    monkeypatch.setitem(governance, "historically_inherited", True)
    with pytest.raises(
        ProspectiveCorpusError,
        match="PROSPECTIVE_INPUT_GOVERNANCE_STILL_INCOMPLETE",
    ):
        protocol_definition()


def test_all_feature_warmups_are_machine_bound_before_collection() -> None:
    warmup = corpus.warmup_history_contract()
    assert warmup["all_feature_warmups_frozen"] is True
    assert set(warmup["rows"]) == set(corpus.INITIAL_FEATURE_NAMES)
    assert warmup["elapsed_time_is_an_evaluability_test"] is False
    for name, row in warmup["rows"].items():
        assert row["owner"], name
        assert row["rolling_window_span"], name
        assert row["minimum_observation_count"], name
        assert row["upstream_initialization"], name
        assert row["calendar_or_session_rule"], name
        assert row["evaluability_predicate"], name
        estimate = row["minimum_contiguous_history_to_first_evaluable"]
        if estimate is not None:
            assert estimate["planning_estimate_only"] is True
            assert estimate["label"] == (
                "PLANNING_ESTIMATE_NOT_EVALUABILITY_AUTHORITY"
            )
    assert warmup["rows"]["CVD_SPREAD"][
        "minimum_contiguous_history_to_first_evaluable"
    ]["value"] == 21
    assert "WARMUP_HISTORY_INCOMPLETE" in warmup["pre_warmup_behavior"]
    universe = corpus.decision_universe_contract()
    assert universe["warmup_history"]["definition_sha256"] == warmup[
        "definition_sha256"
    ]


def test_a_warmup_incomplete_slot_enters_no_evaluable_metric_universe() -> None:
    warmup = corpus.warmup_history_contract()
    assert "enters no evaluable metric universe" in warmup["pre_warmup_behavior"]
    assert "WARMUP_HISTORY_INCOMPLETE" in corpus.NOT_EVALUABLE_REASONS
    assert corpus.stage_b_evaluation_contract()["warmup_entry_requirement"].startswith(
        "WARMUP_HISTORY_COMPLETE"
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
    assert record["non_touching_provider_ids"] == ["coinbase", "bitfinex"]


def test_one_touch_one_non_touch_and_one_missing_is_not_isolated() -> None:
    record = classify_stop_event(
        _slot(
            (
                _observation("bitstamp", low="98"),
                _observation("coinbase", low="101"),
            )
        )
    )
    assert record["classification"] == EVENT_NOT_CLASSIFIABLE
    assert "ISOLATION_NOT_ESTABLISHED_MISSING_PROVIDER" in record["reason_codes"]


def test_no_touch_with_a_missing_provider_is_not_silently_called_no_event() -> None:
    record = classify_stop_event(
        _slot(
            (
                _observation("bitstamp", low="101"),
                _observation("coinbase", low="102"),
            )
        )
    )
    assert record["classification"] == EVENT_NOT_CLASSIFIABLE


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


def test_a_stale_prior_hour_is_refused_instead_of_widening_the_interval() -> None:
    with pytest.raises(ProspectiveCorpusError, match="exact contiguous hourly session"):
        classify_stop_event(
        _slot(
            (
                _observation("bitstamp", low="90", open_="95"),
                _observation("coinbase", low="90", open_="95"),
            ),
            prior_price="105",
            prior_time=SLOT_TIME - timedelta(hours=9),
        )
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
    assert "PRIOR_REFERENCE_SESSION_MISSING" in record["reason_codes"]


def test_gap_through_has_one_frozen_candidate_neutral_prior_derivation() -> None:
    derivation = corpus.GAP_THROUGH_DERIVATION
    assert derivation["unique_interpretation"] is True
    assert derivation["accepted_interpretation"] == corpus.PRIOR_OBSERVABLE_OWNER
    accepted = [row for row in derivation["rows"] if row["accepted"]]
    assert len(accepted) == 1
    assert accepted[0]["candidate_neutral"] is True
    assert accepted[0]["track_dependent"] is False
    assert derivation["maximum_staleness_seconds"] == 3600
    assert derivation["prior_timestamp_identity"].endswith("exactly one hour")


def test_an_ambiguous_gap_derivation_blocks_the_protocol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        corpus.GAP_THROUGH_DERIVATION,
        "unique_interpretation",
        False,
    )
    with pytest.raises(
        ProspectiveCorpusError,
        match="PROSPECTIVE_PROTOCOL_BLOCKED_BY_AMBIGUOUS_FROZEN_METRIC",
    ):
        protocol_definition()


def test_gap_through_numerator_states_consensus_is_triggered_by_construction() -> None:
    contract = metric_evidence_contracts()["contracts"][
        "gap_through_stop_consensus_agreement_rate"
    ]
    assert "consensus is TRIGGERED by construction" in contract["numerator"]
    assert contract["gap_through_derivation"]["unique_interpretation"] is True


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
    assert taxonomy["stop_universe_derivation"]["unique_interpretation"] is True
    assert taxonomy["gap_through_derivation"]["unique_interpretation"] is True


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
    from btc_predictor.db.portfolio import PAPER_ACTIONS
    from btc_predictor.signals.data_quality import RECOMMENDATION_ACTIONS

    assert set(contract["vocabulary"]) == set(RECOMMENDATION_ACTIONS + PAPER_ACTIONS)
    assert contract["evidence_owner"] == corpus.TRADE_ACTION_COMPARISON_OWNER
    assert "render_recommendation" not in contract["evidence_owner"]
    assert contract["owner_contract"]["renderer_role"] == (
        "PRESENTATION_ONLY_NOT_SCIENTIFIC_AUTHORITY"
    )
    assert "lifecycle-event identity" in contract["numerator"]
    assert contract["universe"] == corpus.UNIVERSE_ACTION_EVALUABLE


def test_trade_eligibility_uses_the_full_permission_composite() -> None:
    contract = metric_evidence_contracts()["contracts"][
        "trade_eligibility_disagreement_rate"
    ]
    owner = contract["owner_contract"]
    assert contract["evidence_owner"] == corpus.TRADE_ELIGIBILITY_COMPOSITE_OWNER
    assert "features.entry.classify_entry_action" not in contract["evidence_owner"]
    assert set(owner["authoritative_inputs"]) == {
        "setup_eligibility",
        "entry_conviction",
        "regime_context",
        "reward_risk",
        "hard_veto",
        "data_quality",
        "no_chase",
        "lifecycle_state",
        "risk_capacity",
        "reference_availability",
    }
    assert owner["output_vocabulary"] == [
        "PERMITTED",
        "NOT_PERMITTED",
        "NOT_COMPARABLE",
    ]


def test_action_and_eligibility_flat_vs_position_asymmetry_is_resolved() -> None:
    contracts = metric_evidence_contracts()["contracts"]
    action = contracts["trade_action_disagreement_rate"]
    eligibility = contracts["trade_eligibility_disagreement_rate"]
    assert "Flat-vs-position slots remain comparable" in action["denominator"]
    assert "Flat-vs-position" in eligibility["denominator"]
    assert "lifecycle state is a permission input" in eligibility["denominator"]


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
        assert row["evaluability_minimum"]["certification_minimum_selected_here"] is None
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
    authorization = protocol["collection_authorization_semantics"]
    assert authorization["all_requirements_must_pass"] is True
    assert authorization["corpus_protocol_independently_certified"] is False
    assert authorization["sufficiency_governance_independently_certified"] is False
    assert authorization["postp1_004_implementation_independently_certified"] is False
    assert authorization["warmup_or_nonqualifying_capture_exception"] is False


def test_sufficiency_governance_and_review_precede_postp1_004_and_collection() -> None:
    workflow = list(corpus.FUTURE_WORKFLOW)
    protocol_review = workflow.index(
        "REPEAT INDEPENDENT XHIGH REVIEW OF EXACT CORRECTED PROTOCOL HASH"
    )
    governance = workflow.index(
        "POSTP1-003 PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1"
    )
    governance_review = workflow.index(
        "INDEPENDENT XHIGH REVIEW OF EXACT SUFFICIENCY-GOVERNANCE HASH"
    )
    collectors = workflow.index(
        "POSTP1-004 SCHEMA + COLLECTORS + DECISION SNAPSHOT IMPLEMENTATION"
    )
    authorization = workflow.index("COLLECTION AUTHORIZATION")
    assert protocol_review < governance < governance_review < collectors < authorization
    sequence = evidence_sufficiency_contract()["pre_collection_sequence"]
    assert sequence["postp1_003_independent_review_required"] is True
    assert sequence["postp1_004_blocked_until_postp1_003_review_passes"] is True
    assert sequence["sufficiency_minima_selected_here"] is False


def test_all_three_failed_protocol_hashes_are_retained_as_explicit_lineage() -> None:
    lineage = protocol_definition()["lineage"]
    failed = lineage["failed_prospective_protocols"]
    assert lineage["failed_prospective_protocol_count"] == 3
    assert [row["definition_sha256"] for row in failed] == [
        "aaa05c7288971ecb60e331c750fa728db13a3f2046cd597ffe4957a2f3d37326",
        "0d4f14370c2d17359fa3e5d36ce545f00e00da1a360a66ad3151a37d0cf45a9e",
        "40e37067fdddee467ea6c8f0094a2498573e3ff379d35f0fdd5586af423c9862",
    ]
    assert [row["implementation_commit"] for row in failed] == [
        "b38f387f822da713aa06489e6643c9d6909de32a",
        "8af223d708ee03b09bca6e43c204620aba44ecab",
        "9b2f23acc793457b0e8683387d8382f06472fdd4",
    ]
    assert [row["review_classification"] for row in failed] == [
        "PROSPECTIVE_PROTOCOL_REQUIRES_FIX",
        "PROSPECTIVE_PROTOCOL_BLOCKED_BY_AMBIGUOUS_FROZEN_INPUT",
        "PROSPECTIVE_PROTOCOL_REQUIRES_FIX",
    ]
    for row in failed:
        assert row["retained"] is True
        assert row["authoritative"] is False
        assert row["qualifying_observations_collected"] is False
        assert row["superseded_before_collection"] is True
    corrected = protocol_definition()["definition_sha256"]
    assert corrected not in {row["definition_sha256"] for row in failed}
    assert lineage["protocol_version_retained_rationale"]


def test_entering_collecting_requires_both_governance_reviews_and_implementation_review() -> None:
    with pytest.raises(CollectionNotAuthorizedError, match="SUFFICIENCY_GOVERNANCE"):
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
    assert len(protocol["child_definition_sha256"]) == 15
    for name in (
        "prospective_btc_market_cap_acquisition",
        "prospective_cvd_acquisition",
        "prospective_liquidation_capture",
        "prospective_liquidation_percentile_adapter",
    ):
        assert name in protocol["child_definition_sha256"]
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


def test_candidate_state_cannot_shrink_the_control_anchored_stop_denominator() -> None:
    providers = (
        _observation("bitstamp", low="98"),
        _observation("coinbase", low="98.5"),
        _observation("bitfinex", low="101"),
    )
    divergence = SLOT_TIME - timedelta(days=1)
    candidate_open = classify_stop_event(
        _slot(
            providers,
            stop="99",
            candidate_position_state="OPEN_INITIAL",
            first_divergence_decision_time=divergence,
        )
    )
    candidate_closed = classify_stop_event(
        _slot(
            providers,
            stop="99",
            candidate_position_state="CLOSED",
            first_divergence_decision_time=divergence,
        )
    )
    assert candidate_open["classification"] == EVENT_CROSS_MARKET
    assert candidate_closed["classification"] == EVENT_CROSS_MARKET
    assert candidate_open["event_id"] == candidate_closed["event_id"]
    assert candidate_closed["candidate_position_state"] == "CLOSED"
    assert candidate_closed["control_position_state"] == "OPEN_INITIAL"
    assert candidate_closed["first_divergence_decision_time"] == divergence.isoformat()
    assert candidate_closed["universe_anchor"] == corpus.STOP_EVENT_UNIVERSE_ANCHOR


def test_a_candidate_track_stop_cannot_define_the_event_universe() -> None:
    with pytest.raises(ProspectiveCorpusError, match="anchored to the control"):
        classify_stop_event(
            _slot(
                (_observation("bitstamp"), _observation("coinbase")),
                track=CANDIDATE_TRACK,
            )
        )


def test_post_divergence_stop_semantics_are_frozen_and_exogenous() -> None:
    derivation = corpus.STOP_EVENT_UNIVERSE_DERIVATION
    assert derivation["accepted_interpretation"] == (
        "CONTROL_REFERENCE_TRACK_ACTIVE_STOP"
    )
    assert derivation["unique_interpretation"] is True
    assert sum(row["accepted"] for row in derivation["rows"]) == 1
    candidate = next(
        row
        for row in derivation["rows"]
        if row["interpretation"] == "candidate-track-specific stop"
    )
    assert candidate["accepted"] is False
    assert "shrink its own denominator" in candidate["bias_or_provenance_consequence"]
    post = corpus.POST_DIVERGENCE_STOP_SEMANTICS
    assert post["hidden_denominator_shrinkage_permitted"] is False
    assert "candidate portfolio state differs" in post["comparison_disposition"]


def test_an_ambiguous_stop_anchor_blocks_the_protocol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        corpus.STOP_EVENT_UNIVERSE_DERIVATION,
        "unique_interpretation",
        False,
    )
    with pytest.raises(
        ProspectiveCorpusError,
        match="PROSPECTIVE_PROTOCOL_BLOCKED_BY_AMBIGUOUS_FROZEN_METRIC",
    ):
        protocol_definition()


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


# =============================================================================
# 12. POSTP1-001R3 -- corrected prospective source and coverage semantics
# =============================================================================
#
# Every fixture below is synthetic.  Nothing here collects a qualifying
# observation, evaluates a real Stage-B aggregate, or reads a sealed path.


def _cvd(
    market_type: str,
    observation_time: datetime,
    value: str,
    *,
    available_at: datetime | None = None,
) -> flow.CvdObservation:
    return flow.CvdObservation(
        observation_time=observation_time,
        market_type=market_type,
        cvd_usd=Decimal(value),
        provider="synthetic",
        available_at=available_at or observation_time,
    )


def _hourly_cvd_series(
    count: int,
    *,
    start: datetime = datetime(2026, 1, 1, tzinfo=UTC),
    skip_spot_hours: tuple[int, ...] = (),
) -> tuple[flow.CvdObservation, ...]:
    observations: list[flow.CvdObservation] = []
    for index in range(count):
        stamp = start + timedelta(hours=index)
        if index not in skip_spot_hours:
            observations.append(_cvd("spot", stamp, str(100 + (index % 7) * 3)))
        observations.append(_cvd("perp", stamp, str(90 + (index % 5) * 2)))
    return tuple(observations)


def _prospective_cvd(
    market_type: str,
    observation_time: datetime,
    value: str,
    *,
    available_at: datetime | None = None,
    revision: int = 1,
) -> corpus.ProspectiveCvdAggregateObservation:
    return corpus.ProspectiveCvdAggregateObservation(
        observation_time=observation_time,
        market_type=market_type,
        cvd_usd=Decimal(value),
        provider=corpus.CVD_PROVIDER_BY_MARKET_TYPE[market_type],
        instrument=corpus.CVD_INSTRUMENT_BY_MARKET_TYPE[market_type],
        available_at=available_at or observation_time + timedelta(hours=1),
        revision=revision,
        interval_complete=True,
        completion_evidence_sha256="2" * 64,
    )


def _market_cap(
    observation_time: datetime,
    value: str,
    *,
    available_at: datetime | None = None,
) -> positioning.MarketCapObservation:
    return positioning.MarketCapObservation(
        observation_time=observation_time,
        market_cap_usd=Decimal(value),
        provider=corpus.MARKET_CAP_PROVIDER_ID,
        available_at=available_at or observation_time,
    )


def _prospective_market_cap(
    observation_time: datetime,
    value: str,
    *,
    available_at: datetime,
    revision: str = "1",
) -> corpus.ProspectiveMarketCapObservation:
    return corpus.ProspectiveMarketCapObservation(
        observation_time=observation_time,
        market_cap_usd=Decimal(value),
        series_id=corpus.MARKET_CAP_SERIES_ID,
        series_type=corpus.MARKET_CAP_SERIES_TYPE,
        unit=corpus.MARKET_CAP_SERIES_UNIT,
        provider=corpus.MARKET_CAP_PROVIDER_ID,
        source=corpus.MARKET_CAP_PROVIDER_SOURCE,
        revision=revision,
        raw_response_sha256="1" * 64,
        available_at=available_at,
        ingested_at=available_at + timedelta(seconds=1),
    )


def _open_interest(
    observation_time: datetime,
    value: str,
    *,
    available_at: datetime | None = None,
) -> derivatives.OpenInterest:
    return derivatives.OpenInterest(
        observation_time=observation_time,
        exchange="synthetic",
        symbol="BTC-PERP",
        instrument="perpetual",
        open_interest=Decimal(value),
        open_interest_unit="usd",
        provider="synthetic",
        source="synthetic",
        available_at=available_at or observation_time,
        ingested_at=available_at or observation_time,
    )


def _complete_liquidation_interval_kwargs() -> dict[str, Any]:
    start = datetime(2026, 1, 1, 12, tzinfo=UTC)
    return {
        "provider": corpus.LIQUIDATION_PROVIDER_ID,
        "instrument": corpus.LIQUIDATION_INSTRUMENT,
        "observation_time": start,
        "available_at": start + timedelta(hours=1, seconds=30),
        "decision_time": start + timedelta(hours=1, minutes=5),
        "subscription_acknowledged_at": start - timedelta(minutes=1),
        "coverage_started_at": start - timedelta(minutes=1),
        "coverage_ended_at": start + timedelta(hours=1, seconds=1),
        "websocket_continuous": True,
        "heartbeat_continuous": True,
        "sequence_gap_detected": False,
        "invalid_event_detected": False,
        "conflicting_source_id": False,
        "event_count": 0,
        "long_liquidation_notional_usd": Decimal("0"),
        "short_liquidation_notional_usd": Decimal("0"),
        "source_record_ids": (),
    }


def _daily_bar(index: int, *, start: datetime) -> OhlcvBar:
    stamp = start + timedelta(days=index)
    close = Decimal("30000") + Decimal(index % 7) * Decimal("13")
    return OhlcvBar(
        timestamp=stamp,
        exchange="synthetic",
        symbol="BTC/USD",
        timeframe="1d",
        open=close,
        high=close + Decimal("9"),
        low=close - Decimal("9"),
        close=close,
        volume=Decimal("1"),
        provider="synthetic",
        ingested_at=stamp + timedelta(days=1),
    )


def _rv20_results(sessions: int, *, start: datetime) -> tuple[Any, ...]:
    bars = [_daily_bar(index, start=start) for index in range(sessions)]
    results = []
    for index in range(len(bars)):
        signal_time = bars[index].timestamp + timedelta(days=1)
        result = volatility.realized_volatility_from_daily_bars(
            bars[: index + 1],
            as_of=signal_time,
            window_days=20,
        )
        if result.realized_volatility is not None:
            results.append(result)
    return tuple(results)


# -----------------------------------------------------------------------------
# 12.1 the honesty boundary between feature and acquisition semantics
# -----------------------------------------------------------------------------


def test_every_new_acquisition_contract_declares_itself_new_pre_data_governance() -> None:
    governance = corpus.prospective_acquisition_governance()
    assert governance["ticket"] == "POSTP1-001R3"
    assert governance["phase_1_authority_claimed_for_new_rules"] is False
    assert governance["distinguishes_feature_semantics_from_acquisition_semantics"]
    assert sorted(governance["contract_versions"]) == [
        "PROSPECTIVE_BTC_MARKET_CAP_ACQUISITION_V1",
        "PROSPECTIVE_CVD_ACQUISITION_V1",
        "PROSPECTIVE_LIQUIDATION_CAPTURE_V1",
        "PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_V1",
    ]
    for version, contract in governance["contracts"].items():
        provenance = contract["acquisition_governance"]
        assert provenance["governance_class"] == (
            "NEW_PROSPECTIVE_PRE_DATA_ACQUISITION_GOVERNANCE"
        ), version
        assert provenance["historically_inherited"] is False, version
        assert provenance["claimed_historically_implicit"] is False, version
        assert provenance["frozen_before_collection"] is True, version
        assert provenance["stage_b_outcomes_inspected"] is False, version
        assert provenance["qualifying_observations_inspected"] is False, version
        assert provenance["phase_1_feature_semantics_changed"] is False, version
        assert corpus._is_sha256(contract["definition_sha256"]), version


def test_a_contract_claiming_inherited_authority_blocks_the_protocol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        corpus.ACQUISITION_GOVERNANCE_PROVENANCE,
        "historically_inherited",
        True,
    )
    with pytest.raises(
        ProspectiveCorpusError, match="new pre-data governance"
    ):
        corpus.prospective_acquisition_governance()


# -----------------------------------------------------------------------------
# 12.2 CVD
# -----------------------------------------------------------------------------


def test_the_cvd_contract_labels_its_cadence_as_new_prospective_governance() -> None:
    contract = corpus.prospective_cvd_acquisition_contract()
    selection = contract["cadence_selection"]
    assert contract["version"] == "PROSPECTIVE_CVD_ACQUISITION_V1"
    assert selection["selected_cadence"] == "1h"
    assert selection["selected_by_new_pre_data_governance"] is True
    assert selection["historically_inherited"] is False
    assert selection["stage_b_disagreement_outcomes_inspected"] is False
    assert selection["empirically_optimized_against_target_gates"] is False
    assert selection["rationale"]
    for cadence in ("1h", "4h", "1d"):
        assert cadence in selection["candidates"]
        assert set(selection["criteria"]) <= set(
            selection["candidates"][cadence]["assessment"]
        )
    rejected = [
        cadence
        for cadence, row in selection["candidates"].items()
        if not row["selected"]
    ]
    assert sorted(rejected) == ["1d", "4h"]
    for cadence in rejected:
        assert selection["candidates"][cadence]["rejected_because"]


def test_the_historical_cvd_owner_specifies_no_cadence() -> None:
    contract = corpus.prospective_cvd_acquisition_contract()
    owner = contract["historical_feature_owner"]
    assert owner["specifies_cadence"] is False
    assert owner["specifies_window"] == "20 prior common observations"
    assert owner["unit_tests_are_cadence_authority"] is False
    assert owner["owner"] == "btc_predictor.features.flow.spot_perp_cvd_spread"

    # The owner really does accept arbitrary, non-hourly common timestamps: it
    # is observation-count based, which is exactly why a cadence has to be
    # frozen prospectively rather than claimed as inherited.
    start = datetime(2026, 1, 1, tzinfo=UTC)
    irregular = []
    stamp = start
    for index in range(21):
        stamp = stamp + timedelta(minutes=7 + index)
        irregular.append(_cvd("spot", stamp, str(100 + index)))
        irregular.append(_cvd("perp", stamp, str(90 + (index % 4))))
    result = flow.spot_perp_cvd_spread(
        tuple(irregular),
        as_of=stamp + timedelta(hours=1),
    )
    assert result.complete is True
    assert result.cvd_spread is not None


def test_cvd_source_contract_binds_exact_provider_instrument_and_taker_units() -> None:
    contract = corpus.prospective_cvd_acquisition_contract()
    universe = contract["market_universe"]
    assert universe["spot"]["provider"] == (
        "kraken_spot_websocket_v2_trade"
    )
    assert universe["spot"]["instrument"] == "BTC/USD"
    assert universe["perpetual"]["provider"] == (
        "kraken_futures_websocket_v1_trade"
    )
    assert universe["perpetual"]["instrument"] == "PI_XBTUSD"
    assert universe["perpetual"]["quote_currency"] == "USD"
    assert "contractSize=1" in universe["perpetual"]["selection_rule"]
    assert "taker" in contract["buy_sell_classification_owner"]
    assert contract["pre_owner_adapter"]["selector"] == (
        "select_contiguous_cvd_window"
    )


def test_cvd_selector_requires_the_exact_twenty_one_hour_grid() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    current = start + timedelta(hours=21)
    decision = current + timedelta(hours=1, minutes=5)
    observations = []
    for index in range(22):
        stamp = start + timedelta(hours=index)
        if index != 10:
            observations.append(_prospective_cvd("spot", stamp, str(index)))
        observations.append(_prospective_cvd("perp", stamp, str(-index)))

    with pytest.raises(
        ProspectiveCorpusError,
        match="CVD_CONTIGUOUS_GRID_INCOMPLETE",
    ):
        corpus.select_contiguous_cvd_window(
            observations,
            current_observation_time=current,
            decision_time=decision,
        )


def test_cvd_selector_uses_one_latest_revision_before_the_historical_owner() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    current = start + timedelta(hours=20)
    decision = current + timedelta(hours=1, minutes=5)
    observations = []
    for index in range(21):
        stamp = start + timedelta(hours=index)
        observations.append(_prospective_cvd("spot", stamp, str(index)))
        observations.append(_prospective_cvd("perp", stamp, str(-index)))
    observations.append(
        _prospective_cvd(
            "spot",
            current,
            "999",
            available_at=current + timedelta(hours=1, minutes=1),
            revision=2,
        )
    )

    selected = corpus.select_contiguous_cvd_window(
        observations,
        current_observation_time=current,
        decision_time=decision,
    )
    assert len(selected) == 42
    current_spot = [
        row
        for row in selected
        if row.market_type == "spot" and row.observation_time == current
    ]
    assert [row.cvd_usd for row in current_spot] == [Decimal("999")]
    result = flow.spot_perp_cvd_spread(selected, as_of=decision)
    assert result.complete is True
    assert result.source_record_count == 42


def test_cvd_selector_rejects_an_unfrozen_instrument_identity() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    observation = _prospective_cvd("spot", start, "1")
    wrong = corpus.ProspectiveCvdAggregateObservation(
        **{
            **observation.__dict__,
            "instrument": "BTC/USDT",
        }
    )
    with pytest.raises(ProspectiveCorpusError, match="provider/instrument"):
        corpus.select_contiguous_cvd_window(
            (wrong,),
            current_observation_time=start,
            decision_time=start + timedelta(hours=2),
        )


def test_incomplete_cvd_feed_evidence_cannot_reach_the_historical_owner() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    current = start + timedelta(hours=20)
    observations = []
    for index in range(21):
        stamp = start + timedelta(hours=index)
        observations.append(_prospective_cvd("spot", stamp, str(index)))
        observations.append(_prospective_cvd("perp", stamp, str(-index)))
    affected = observations[20]
    observations[20] = corpus.ProspectiveCvdAggregateObservation(
        **{
            **affected.__dict__,
            "cvd_usd": None,
            "interval_complete": False,
        }
    )
    with pytest.raises(
        ProspectiveCorpusError,
        match="CVD_CONTIGUOUS_GRID_INCOMPLETE",
    ):
        corpus.select_contiguous_cvd_window(
            observations,
            current_observation_time=current,
            decision_time=current + timedelta(hours=1, minutes=5),
        )


def test_cvd_initialization_needs_twenty_prior_plus_one_current_observation() -> None:
    contract = corpus.prospective_cvd_acquisition_contract()
    initialization = contract["initialization_requirement"]
    assert initialization["prior_common_observations"] == 20
    assert initialization["current_observations"] == 1
    assert initialization["total_common_observations"] == 21

    start = datetime(2026, 1, 1, tzinfo=UTC)
    as_of = start + timedelta(hours=48)
    short = flow.spot_perp_cvd_spread(_hourly_cvd_series(20, start=start), as_of=as_of)
    assert short.cvd_spread is None
    assert "SPOT_PERP_CVD_SPREAD_INSUFFICIENT_HISTORY" in short.reason_codes
    exact = flow.spot_perp_cvd_spread(_hourly_cvd_series(21, start=start), as_of=as_of)
    assert exact.cvd_spread is not None
    assert exact.complete is True


def test_a_missing_hourly_cvd_slot_stays_missing_and_is_never_compressed() -> None:
    contract = corpus.prospective_cvd_acquisition_contract()
    assert "never zero-filled" in contract["missing_interval_semantics"]
    assert "never silently compressed" in contract["missing_interval_semantics"]

    start = datetime(2026, 1, 1, tzinfo=UTC)
    as_of = start + timedelta(hours=48)
    # 21 hours with one spot hour absent leaves only 20 common observations, so
    # the gap is not silently closed by shifting the neighbours together.
    gapped = flow.spot_perp_cvd_spread(
        _hourly_cvd_series(21, start=start, skip_spot_hours=(9,)),
        as_of=as_of,
    )
    assert gapped.cvd_spread is None
    assert "SPOT_PERP_CVD_SPREAD_INSUFFICIENT_HISTORY" in gapped.reason_codes
    healed = flow.spot_perp_cvd_spread(
        _hourly_cvd_series(22, start=start, skip_spot_hours=(9,)),
        as_of=as_of,
    )
    assert healed.cvd_spread is not None


def test_an_off_grid_cvd_observation_is_refused_by_the_new_contract() -> None:
    contract = corpus.prospective_cvd_acquisition_contract()
    assert contract["timestamp_alignment"] == "EXACT_UTC_HOUR_INTERVAL_START"
    assert contract["off_grid_observation_policy"] == (
        "REFUSE_AT_CAPTURE_NEVER_SNAP_OR_ROUND"
    )
    with pytest.raises(ProspectiveCorpusError, match="exact UTC hour"):
        decision_time_for(
            datetime(2026, 3, 2, 9, 17, tzinfo=UTC), STOP_HOURLY_CADENCE
        )


def test_cvd_revisions_are_append_only_and_late_data_is_invisible() -> None:
    contract = corpus.prospective_cvd_acquisition_contract()
    assert contract["revision_semantics"].startswith("Append-only")
    assert "never" in contract["duplicate_semantics"]
    assert contract["pit_rule"] == "available_at <= decision_time"

    start = datetime(2026, 1, 1, tzinfo=UTC)
    as_of = start + timedelta(hours=48)
    series = list(_hourly_cvd_series(21, start=start))
    late = flow.CvdObservation(
        observation_time=start + timedelta(hours=21),
        market_type="spot",
        cvd_usd=Decimal("999999"),
        provider="synthetic",
        available_at=as_of + timedelta(seconds=1),
    )
    baseline = flow.spot_perp_cvd_spread(tuple(series), as_of=as_of)
    with_late = flow.spot_perp_cvd_spread((*series, late), as_of=as_of)
    assert with_late.cvd_spread == baseline.cvd_spread
    assert with_late.source_record_count == baseline.source_record_count


def test_the_cvd_feature_formula_is_untouched_by_the_acquisition_contract() -> None:
    contract = corpus.prospective_cvd_acquisition_contract()
    assert contract["feature_semantics_unchanged"] is True
    assert contract["historical_feature_owner"]["formula"] == (
        "CVD_SPREAD = z(SpotCVD) - z(PerpCVD)"
    )
    assert flow.spot_perp_cvd_spread.__kwdefaults__ == {
        "zscore_window_periods": 20,
        "min_zscore_periods": None,
    }
    start = datetime(2026, 1, 1, tzinfo=UTC)
    result = flow.spot_perp_cvd_spread(
        _hourly_cvd_series(21, start=start),
        as_of=start + timedelta(hours=48),
    )
    assert result.cvd_spread == result.spot_cvd_zscore - result.perp_cvd_zscore
    assert result.zscore_window_periods == 20


def test_changing_the_cvd_acquisition_cadence_moves_the_protocol_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = protocol_definition()["definition_sha256"]
    monkeypatch.setattr(corpus, "CVD_SELECTED_CADENCE", "4h")
    monkeypatch.setitem(corpus.CVD_CADENCE_CANDIDATES["1h"], "selected", False)
    monkeypatch.setitem(
        corpus.CVD_CADENCE_CANDIDATES["1h"], "rejected_because", "not selected"
    )
    monkeypatch.setitem(corpus.CVD_CADENCE_CANDIDATES["4h"], "selected", True)
    monkeypatch.setitem(
        corpus.CVD_CADENCE_CANDIDATES["4h"], "rejected_because", None
    )
    monkeypatch.setitem(
        corpus.NON_PRICE_INPUT_SOURCES["spot_perp_cvd"]["cadence_governance"],
        "selected_cadence",
        "4h",
    )
    assert protocol_definition()["definition_sha256"] != baseline


# -----------------------------------------------------------------------------
# 12.3 BTC market cap
# -----------------------------------------------------------------------------


def test_the_market_cap_contract_has_one_exact_prospective_source_identity() -> None:
    contract = corpus.prospective_btc_market_cap_acquisition_contract()
    identity = contract["series_identity"]
    assert contract["version"] == "PROSPECTIVE_BTC_MARKET_CAP_ACQUISITION_V1"
    assert contract["asset"] == "BTC"
    assert contract["metric"] == "market_cap_usd"
    assert contract["units"] == "USD"
    assert identity["identity_is_exact"] is True
    assert identity["series_id"] == "BTC_MARKET_CAP_USD"
    assert identity["series_type"] == "market_cap"
    assert identity["unit"] == "usd"
    assert identity["raw_table"] == "raw.generic_series"
    assert identity["unqualified_family_dependency_permitted"] is False
    assert contract["provider_identity"]["provider"] == "coingecko"
    assert contract["provider_identity"]["one_provider_per_epoch"] is True
    assert contract["provider_identity"]["provider_client_exists_in_repository"] is False
    assert contract["observation_cadence"] == "1d"
    assert contract["existing_producer"]["existing_market_cap_producer"] is None
    assert contract["existing_producer"]["generic_series_family_is_sufficient"] is False
    assert contract["derived_construction"]["rejected"] is True
    for field in (
        "observation_time_semantics",
        "available_at_semantics",
        "ingested_at_semantics",
        "revision_policy",
        "source_replacement_policy",
        "pit_rule",
    ):
        assert contract[field], field
    assert contract["pit_rule"] == "available_at <= decision_time"


def test_no_repository_producer_emits_market_cap_today() -> None:
    assert "market_cap" not in generic_series.SUPPORTED_SERIES_TYPES
    declared = {
        *generic_series.MACRO_SERIES_DEFINITIONS,
        *generic_series.ONCHAIN_SERIES_DEFINITIONS,
    }
    assert not any("MARKET_CAP" in series_id for series_id in declared)
    assert corpus.EXISTING_MARKET_CAP_PRODUCER is None


def test_market_cap_schedule_uses_only_locally_observable_response_completion() -> None:
    contract = corpus.prospective_btc_market_cap_acquisition_contract()
    schedule = contract["acquisition_schedule"]
    assert schedule["first_poll_utc"] == "00:45:00"
    assert schedule["attempt_offsets_minutes"] == [0, 5, 10]
    assert schedule["hard_cutoff_utc"] == "00:56:00"
    assert schedule["requested_date_offsets_from_poll_day"] == [1, 2, 3]
    assert schedule["response_field"] == "market_data.market_cap.usd"
    assert "locally observed" in contract["available_at_semantics"]
    assert "not a claim" in contract["available_at_semantics"]
    identity = contract["provider_identity"]
    assert identity["source_documentation"].startswith(
        "https://docs.coingecko.com/"
    )
    assert identity["source_revision_documentation"].startswith(
        "https://support.coingecko.com/"
    )


def test_market_cap_required_date_changes_only_after_the_poll_cutoff() -> None:
    day = datetime(2026, 1, 4, tzinfo=UTC)
    assert corpus.required_market_cap_observation_time(
        day + timedelta(minutes=5)
    ) == datetime(2026, 1, 2, tzinfo=UTC)
    assert corpus.required_market_cap_observation_time(
        day + timedelta(hours=1, minutes=5)
    ) == datetime(2026, 1, 3, tzinfo=UTC)
    assert corpus.market_cap_poll_cycle_for_decision(
        day + timedelta(minutes=55, seconds=59)
    ) == datetime(2026, 1, 3, 0, 45, tzinfo=UTC)
    assert corpus.market_cap_poll_cycle_for_decision(
        day + timedelta(minutes=56)
    ) == datetime(2026, 1, 4, 0, 45, tzinfo=UTC)


def test_market_cap_selector_refuses_an_older_date_as_fallback() -> None:
    day = datetime(2026, 1, 4, tzinfo=UTC)
    decision = day + timedelta(hours=1, minutes=5)
    with pytest.raises(
        ProspectiveCorpusError,
        match="MARKET_CAP_REQUIRED_OBSERVATION_MISSING",
    ):
        corpus.select_market_cap_revisions_for_decision(
            (
                _prospective_market_cap(
                    day - timedelta(days=2),
                    "100",
                    available_at=day - timedelta(days=1, hours=23),
                ),
            ),
            decision_time=decision,
        )


def test_market_cap_selector_uses_latest_revision_without_owner_averaging() -> None:
    day = datetime(2026, 1, 4, tzinfo=UTC)
    observation_time = day - timedelta(days=1)
    decision = day + timedelta(hours=1, minutes=5)
    rows = (
        _prospective_market_cap(
            observation_time,
            "200",
            available_at=day + timedelta(minutes=46),
            revision="1",
        ),
        _prospective_market_cap(
            observation_time,
            "400",
            available_at=day + timedelta(minutes=51),
            revision="2",
        ),
    )
    selected = corpus.select_market_cap_revisions_for_decision(
        rows,
        decision_time=decision,
    )
    assert len(selected) == 1
    assert selected[0].market_cap_usd == Decimal("400")

    result = positioning.open_interest_intensity(
        (_open_interest(observation_time, "100"),),
        selected,
        as_of=decision,
        open_interest_unit="usd",
    )
    assert result.market_cap_usd == Decimal("400")
    assert result.oi_intensity == Decimal("0.25")
    assert result.market_cap_record_count == 1


def test_market_cap_selector_rejects_an_unfrozen_series_identity() -> None:
    day = datetime(2026, 1, 4, tzinfo=UTC)
    row = _prospective_market_cap(
        day - timedelta(days=1),
        "400",
        available_at=day + timedelta(minutes=46),
    )
    wrong = corpus.ProspectiveMarketCapObservation(
        **{
            **row.__dict__,
            "source": "another_provider_path",
        }
    )
    with pytest.raises(ProspectiveCorpusError, match="series/provider/source"):
        corpus.select_market_cap_revisions_for_decision(
            (wrong,),
            decision_time=day + timedelta(hours=1, minutes=5),
        )


def test_oi_intensity_cannot_consume_an_arbitrary_generic_series_row() -> None:
    coverage = corpus.feature_input_coverage_contract()
    assert coverage["unqualified_generic_series_dependency_remains"] is False
    for feature in ("OI_INTENSITY", "OI_INTENSITY_PERCENTILE_180D"):
        row = coverage["rows"][feature]
        assert "generic_series" not in row["raw_input_families"]
        assert "btc_market_cap" in row["raw_input_families"]
        assert row["prospective_acquisition_contract_by_family"][
            "btc_market_cap"
        ] == "PROSPECTIVE_BTC_MARKET_CAP_ACQUISITION_V1"


def test_reopening_the_generic_series_dependency_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        corpus._FEATURE_DEPENDENCIES["OI_INTENSITY"],
        "raw",
        ("derivatives_open_interest", "generic_series"),
    )
    with pytest.raises(
        ProspectiveCorpusError, match="unqualified generic-series family"
    ):
        corpus.feature_input_coverage_contract()


def test_a_missing_market_cap_observation_is_not_evaluable() -> None:
    contract = corpus.prospective_btc_market_cap_acquisition_contract()
    assert contract["missing_value_handling"]["zero_fill_permitted"] is False
    assert contract["missing_value_handling"]["missing_observation"] == (
        "REQUIRED_INPUT_MISSING"
    )
    day = datetime(2026, 1, 1, tzinfo=UTC)
    result = positioning.open_interest_intensity(
        (_open_interest(day, "1000"),),
        (),
        as_of=day + timedelta(hours=1),
        open_interest_unit="usd",
    )
    assert result.complete is False
    assert result.oi_intensity is None
    assert result.market_cap_usd is None
    assert "OI_INTENSITY_MARKET_CAP_INPUT_MISSING" in result.reason_codes


def test_a_late_market_cap_observation_is_not_evaluable_at_that_decision() -> None:
    day = datetime(2026, 1, 1, tzinfo=UTC)
    decision = day + timedelta(hours=1)
    result = positioning.open_interest_intensity(
        (_open_interest(day, "1000"),),
        (
            _market_cap(
                day,
                "2000000",
                available_at=decision + timedelta(seconds=1),
            ),
        ),
        as_of=decision,
        open_interest_unit="usd",
    )
    assert result.complete is False
    assert result.oi_intensity is None
    assert result.market_cap_record_count == 0
    assert "OI_INTENSITY_MARKET_CAP_INPUT_MISSING" in result.reason_codes


def test_the_frozen_market_cap_grid_matches_the_owners_exact_alignment_rule() -> None:
    contract = corpus.prospective_btc_market_cap_acquisition_contract()
    binding = contract["consumer_binding"]
    assert binding["feature_semantics_unchanged"] is True
    assert "exact intersection" in binding["observation_grid_alignment"]
    day = datetime(2026, 1, 1, tzinfo=UTC)
    decision = day + timedelta(hours=1)
    # The owner intersects on an exact observation_time, so a misaligned
    # market-cap grid produces no intensity at all.
    misaligned = positioning.open_interest_intensity(
        (_open_interest(day, "1000"),),
        (_market_cap(day + timedelta(minutes=30), "2000000"),),
        as_of=decision,
        open_interest_unit="usd",
    )
    assert misaligned.oi_intensity is None
    aligned = positioning.open_interest_intensity(
        (_open_interest(day, "1000"),),
        (_market_cap(day, "2000000"),),
        as_of=decision,
        open_interest_unit="usd",
    )
    assert aligned.oi_intensity == Decimal("1000") / Decimal("2000000")


def test_market_cap_revision_semantics_are_deterministic() -> None:
    contract = corpus.prospective_btc_market_cap_acquisition_contract()
    assert contract["revision_policy"].startswith("NEW_REVISION_ROW_PER_RESTATEMENT")
    assert "retained verbatim" in contract["revision_policy"]
    assert "never retroactive" in contract["source_replacement_policy"]
    assert (
        corpus.prospective_btc_market_cap_acquisition_contract()[
            "definition_sha256"
        ]
        == contract["definition_sha256"]
    )


def test_changing_the_market_cap_source_identity_moves_the_protocol_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = protocol_definition()["definition_sha256"]
    monkeypatch.setattr(corpus, "MARKET_CAP_SERIES_ID", "BTC_MARKET_CAP_USD_ALT")
    monkeypatch.setitem(
        corpus.NON_PRICE_INPUT_SOURCES["btc_market_cap"],
        "series_id",
        "BTC_MARKET_CAP_USD_ALT",
    )
    assert protocol_definition()["definition_sha256"] != baseline


def test_each_corrected_source_identity_moves_its_child_and_the_top_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline_top = protocol_definition()["definition_sha256"]
    baseline_market_cap = corpus.prospective_btc_market_cap_acquisition_contract()[
        "definition_sha256"
    ]
    baseline_cvd = corpus.prospective_cvd_acquisition_contract()[
        "definition_sha256"
    ]
    baseline_liquidations = corpus.prospective_liquidation_capture_contract()[
        "definition_sha256"
    ]

    endpoint = "https://api.coingecko.com/api/v3/coins/bitcoin/history-alt"
    monkeypatch.setattr(corpus, "MARKET_CAP_PROVIDER_ENDPOINT", endpoint)
    monkeypatch.setitem(
        corpus.NON_PRICE_INPUT_SOURCES["btc_market_cap"],
        "provider_endpoint",
        endpoint,
    )
    assert corpus.prospective_btc_market_cap_acquisition_contract()[
        "definition_sha256"
    ] != baseline_market_cap

    cvd_instrument = "XBT/USD"
    monkeypatch.setattr(corpus, "CVD_SPOT_INSTRUMENT", cvd_instrument)
    monkeypatch.setitem(
        corpus.CVD_INSTRUMENT_BY_MARKET_TYPE,
        "spot",
        cvd_instrument,
    )
    monkeypatch.setitem(
        corpus.NON_PRICE_INPUT_SOURCES["spot_perp_cvd"][
            "instrument_by_market_type"
        ],
        "spot",
        cvd_instrument,
    )
    assert corpus.prospective_cvd_acquisition_contract()[
        "definition_sha256"
    ] != baseline_cvd

    liquidation_instrument = "PI_XBTUSD_ALT"
    monkeypatch.setattr(
        corpus,
        "LIQUIDATION_INSTRUMENT",
        liquidation_instrument,
    )
    monkeypatch.setitem(
        corpus.NON_PRICE_INPUT_SOURCES["liquidations"],
        "instrument",
        liquidation_instrument,
    )
    assert corpus.prospective_liquidation_capture_contract()[
        "definition_sha256"
    ] != baseline_liquidations
    assert protocol_definition()["definition_sha256"] != baseline_top


def test_a_market_cap_source_without_an_identity_blocks_the_protocol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        corpus.NON_PRICE_INPUT_SOURCES["btc_market_cap"], "provider", ""
    )
    with pytest.raises(
        ProspectiveCorpusError,
        match="PROSPECTIVE_PROTOCOL_BLOCKED_BY_MISSING_MARKET_CAP_SOURCE",
    ):
        protocol_definition()


# -----------------------------------------------------------------------------
# 12.4 liquidations
# -----------------------------------------------------------------------------


def test_the_existing_aggregate_cannot_separate_a_missing_feed_from_an_empty_one() -> None:
    contract = corpus.prospective_liquidation_capture_contract()
    assert contract["existing_aggregate"]["distinguishes_missing_from_empty"] is False
    assert contract["existing_aggregate"]["modified_by_this_protocol"] is False
    signal_time = datetime(2026, 1, 1, 12, tzinfo=UTC)
    aggregate = derivatives.aggregate_btc_derivatives_available_at((), signal_time)
    assert aggregate.long_liquidations_usd == Decimal("0")
    assert aggregate.short_liquidations_usd == Decimal("0")
    assert not hasattr(aggregate, "feed_status")
    assert not hasattr(aggregate, "liquidation_event_count")


def test_an_observed_zero_event_interval_is_not_a_missing_feed() -> None:
    contract = corpus.prospective_liquidation_capture_contract()
    semantics = contract["feed_status_semantics"]
    observed_zero = semantics["OBSERVED_ZERO_EVENTS"]
    unavailable = semantics["SOURCE_UNAVAILABLE"]
    assert observed_zero != unavailable
    assert observed_zero["usable_as_an_observation"] is True
    assert observed_zero["feature_input_state"] == "PRESENT"
    assert observed_zero["notional_before_normalization"].startswith("0 USD")
    assert unavailable["usable_as_an_observation"] is False
    assert unavailable["feature_input_state"] == "REQUIRED_INPUT_MISSING"
    assert contract["missing_feed_can_become_numeric_zero"] is False
    assert contract["feed_state_is_independent_of_the_numeric_value"] is True


def test_liquidation_contract_binds_one_exact_event_census() -> None:
    contract = corpus.prospective_liquidation_capture_contract()
    identity = contract["provider_identity"]
    assert identity["provider"] == "kraken_futures_websocket_v1_trade"
    assert identity["instrument"] == "PI_XBTUSD"
    assert identity["quote_currency"] == "USD"
    assert identity["one_provider_and_instrument_per_epoch"] is True
    census = contract["event_census"]
    assert census["included_event_type"] == "liquidation"
    assert census["contract_size_usd"] == "1"
    assert census["side_mapping"] == {"buy": "short", "sell": "long"}
    assert contract["interval_completion_predicate"]["all_required"] is True


def test_liquidation_zero_is_observed_only_with_complete_feed_evidence() -> None:
    kwargs = _complete_liquidation_interval_kwargs()
    complete = corpus.classify_liquidation_feed_interval(**kwargs)
    assert complete["feed_status"] == "OBSERVED_ZERO_EVENTS"
    assert complete["event_count"] == 0
    assert complete["long_liquidation_notional_usd"] == Decimal("0")
    assert corpus._is_sha256(complete["source_record_ids_digest"])

    partial = corpus.classify_liquidation_feed_interval(
        **{
            **kwargs,
            "coverage_ended_at": kwargs["observation_time"]
            + timedelta(minutes=59),
        }
    )
    assert partial["feed_status"] == "SOURCE_UNAVAILABLE"
    assert partial["event_count"] is None
    assert partial["long_liquidation_notional_usd"] is None
    assert partial["short_liquidation_notional_usd"] is None


def test_liquidation_event_census_and_sequence_fail_closed() -> None:
    kwargs = _complete_liquidation_interval_kwargs()
    observed = corpus.classify_liquidation_feed_interval(
        **{
            **kwargs,
            "event_count": 2,
            "long_liquidation_notional_usd": Decimal("3"),
            "short_liquidation_notional_usd": Decimal("7"),
            "source_record_ids": ("uid-2", "uid-1"),
        }
    )
    assert observed["feed_status"] == "OBSERVED_WITH_EVENTS"
    assert observed["event_count"] == 2
    assert observed["source_record_ids_digest"] == corpus._digest(
        ["uid-1", "uid-2"]
    )

    gap = corpus.classify_liquidation_feed_interval(
        **{
            **kwargs,
            "sequence_gap_detected": True,
        }
    )
    assert gap["feed_status"] == "INVALID"
    assert gap["reason"] == "SEQUENCE_GAP"


def test_liquidation_wrong_identity_and_late_evidence_are_never_observed_zero() -> None:
    kwargs = _complete_liquidation_interval_kwargs()
    wrong = corpus.classify_liquidation_feed_interval(
        **{
            **kwargs,
            "instrument": "BTC/USDT",
        }
    )
    assert wrong["feed_status"] == "INVALID"
    assert wrong["event_count"] is None

    late = corpus.classify_liquidation_feed_interval(
        **{
            **kwargs,
            "available_at": kwargs["decision_time"] + timedelta(seconds=1),
        }
    )
    assert late["feed_status"] == "LATE"
    assert late["event_count"] is None


@pytest.mark.parametrize("status", ["SOURCE_UNAVAILABLE", "LATE", "INVALID"])
def test_an_unusable_liquidation_feed_is_not_evaluable_and_never_zero(
    status: str,
) -> None:
    contract = corpus.prospective_liquidation_capture_contract()
    row = contract["feed_status_semantics"][status]
    assert row["usable_as_an_observation"] is False
    assert row["feature_input_state"] == "REQUIRED_INPUT_MISSING"
    assert row["notional_before_normalization"].startswith("null")
    adapter = corpus.prospective_liquidation_percentile_adapter_contract()
    assert status in adapter["missing_feed_behavior"]["excluded_from_history"]
    assert adapter["missing_feed_behavior"]["missing_feed_percentile"] is None
    assert (
        adapter["missing_feed_behavior"]["missing_feed_percentile_zero_permitted"]
        is False
    )


def test_liquidation_feed_state_and_event_count_are_persisted() -> None:
    contract = corpus.prospective_liquidation_capture_contract()
    for field in (
        "observation_time",
        "available_at",
        "ingested_at",
        "provider",
        "instrument",
        "timeframe",
        "feed_status",
        "event_count",
        "long_liquidation_notional_usd",
        "short_liquidation_notional_usd",
        "source_record_ids_digest",
        "revision",
    ):
        assert field in contract["capture_fields"], field
    table = corpus.data_schema_contract()["tables"][
        "prospective_liquidation_feed_state"
    ]
    assert table["append_only"] is True
    for field in ("feed_status", "event_count", "revision"):
        assert field in table["columns"], field
    assert table["columns"]["event_count"].endswith("null")
    assert table["columns"]["long_liquidation_notional_usd"].endswith("null")


def test_the_missing_versus_empty_distinction_survives_replay() -> None:
    contract = corpus.prospective_liquidation_capture_contract()
    assert "reproduces the missing-versus-empty distinction from storage" in (
        contract["replay_rule"]
    )
    assert "never re-derive feed_status" in contract["replay_rule"]
    restored = corpus.restore_artifacts(ARTIFACT_DIR)
    persisted = json.loads(
        (ARTIFACT_DIR / corpus.LIQUIDATION_CAPTURE_FILENAME).read_text(
            encoding="ascii"
        )
    )
    assert persisted["feed_status_semantics"] == contract["feed_status_semantics"]
    assert restored["child_definition_sha256"][
        "prospective_liquidation_capture"
    ] == contract["definition_sha256"]


def test_no_executable_owner_produces_liquidation_percentile_today() -> None:
    adapter = corpus.prospective_liquidation_percentile_adapter_contract()
    assert adapter["existing_owner"]["executable_owner_found"] is None
    assert adapter["existing_owner"]["new_adapter_required"] is True
    assert adapter["downstream_formula_changed"] is False
    assert not hasattr(volatility, "liquidation_percentile")
    assert not hasattr(volatility, "calculate_liquidation_percentile")


def test_the_liquidation_adapter_is_deterministic_and_inherits_one_convention() -> None:
    adapter = corpus.prospective_liquidation_percentile_adapter_contract()
    convention = adapter["percentile_convention"]
    assert convention["invented_convention"] is False
    assert convention["convention"] == "MIDRANK_PERCENTILE_OF_PRIOR_WINDOW_V1"
    assert convention["current_observation_excluded_from_history"] is True
    assert adapter["window"]["span_days"] == 730
    assert adapter["minimum_history"]["minimum_prior_observations"] == 365
    assert adapter["window"]["boundary"].startswith("half-open")
    assert (
        corpus.prospective_liquidation_percentile_adapter_contract()[
            "definition_sha256"
        ]
        == adapter["definition_sha256"]
    )
    # The two existing repository implementations of the inherited convention
    # agree exactly, so the adapter names one rule and not a family of them.
    history = tuple(Decimal(value) for value in ("1", "2", "2", "5", "8"))
    for value in ("0", "2", "5", "9"):
        assert volatility._percentile_rank(
            Decimal(value), history
        ) == positioning._percentile_rank(Decimal(value), history)


def test_the_liquidation_percentile_convention_is_ambient_context_invariant() -> None:
    history = tuple(Decimal(value) for value in ("1", "2", "2", "5", "8"))
    baseline = volatility._percentile_rank(Decimal("5"), history)
    with localcontext(Context(prec=3)):
        assert volatility._percentile_rank(Decimal("5"), history) == baseline
    adapter_hash = corpus.prospective_liquidation_percentile_adapter_contract()[
        "definition_sha256"
    ]
    with localcontext(Context(prec=3)):
        assert corpus.prospective_liquidation_percentile_adapter_contract()[
            "definition_sha256"
        ] == adapter_hash


def test_orderliness_still_fails_closed_on_a_missing_liquidation_input() -> None:
    present = volatility.calculate_orderliness_score(
        volatility.OrderlinessScoreInput(
            range_percentile=Decimal("10"),
            downside_return=Decimal("1"),
            liquidation_percentile=Decimal("0"),
            volatility_percentile=Decimal("10"),
        )
    )
    assert present.complete is True
    missing = volatility.calculate_orderliness_score(
        volatility.OrderlinessScoreInput(
            range_percentile=Decimal("10"),
            downside_return=Decimal("1"),
            liquidation_percentile=None,
            volatility_percentile=Decimal("10"),
        )
    )
    assert missing.complete is False
    assert "ORDERLINESS_INPUT_MISSING" in missing.reason_codes


def test_an_ambiguous_liquidation_normalization_blocks_the_protocol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(corpus, "LIQUIDATION_PERCENTILE_ADAPTER_REQUIRED", False)
    with pytest.raises(
        ProspectiveCorpusError,
        match="PROSPECTIVE_PROTOCOL_BLOCKED_BY_AMBIGUOUS_LIQUIDATION_NORMALIZATION",
    ):
        protocol_definition()


# -----------------------------------------------------------------------------
# 12.5 warmup
# -----------------------------------------------------------------------------


def test_vol_percentile_2y_first_defines_at_the_derived_contiguous_fixture() -> None:
    derivation = corpus.warmup_history_contract()["vol_percentile_2y_derivation"]
    sessions = derivation["first_evaluable_contiguous_daily_sessions"]
    assert sessions == 386
    assert derivation["first_evaluable_elapsed_calendar_days"] == 385
    start = datetime(2024, 1, 1, tzinfo=UTC)

    complete = volatility.volatility_percentile(
        _rv20_results(sessions, start=start),
        as_of=start + timedelta(days=sessions),
    )
    assert complete.complete is True
    assert complete.history_observation_count == 365
    assert complete.volatility_percentile is not None


def test_one_observation_below_the_threshold_is_incomplete() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    short = volatility.volatility_percentile(
        _rv20_results(385, start=start),
        as_of=start + timedelta(days=385),
    )
    assert short.complete is False
    assert short.history_observation_count == 364
    assert short.volatility_percentile is None
    assert "VOL_PERCENTILE_INSUFFICIENT_HISTORY" in short.reason_codes


def test_the_window_span_alone_does_not_imply_completeness() -> None:
    derivation = corpus.warmup_history_contract()["vol_percentile_2y_derivation"]
    assert derivation["window_span_alone_implies_completeness"] is False
    assert derivation["populated_days_equal_to_the_window_span_required"] is False
    # 750 elapsed days of sparse observations still fail the owner's minimum
    # observation count, so elapsed time is not independently sufficient.
    start = datetime(2024, 1, 1, tzinfo=UTC)
    dense = _rv20_results(100, start=start)
    sparse = tuple(dense[index] for index in range(0, len(dense), 3))
    spread = volatility.volatility_percentile(
        sparse,
        as_of=start + timedelta(days=750),
    )
    assert spread.complete is False
    assert spread.history_observation_count < 365
    assert "VOL_PERCENTILE_INSUFFICIENT_HISTORY" in spread.reason_codes


def test_the_false_750_day_warmup_is_no_longer_a_scientific_minimum() -> None:
    warmup = corpus.warmup_history_contract()
    assert warmup["superseded_claim"]["retained_as_scientific_minimum"] is False
    assert "750" in warmup["superseded_claim"]["claim"]
    assert warmup["elapsed_time_is_an_evaluability_test"] is False
    assert "elapsed_days" in warmup["evaluability_rule"]
    serialized = json.dumps(warmup["rows"])
    assert "750" not in serialized
    longest = warmup["longest_contiguous_history_planning_estimate_by_unit"]
    assert longest["contiguous canonical daily sessions"] == 386
    assert warmup["planning_estimate_label"] == (
        "PLANNING_ESTIMATE_NOT_EVALUABILITY_AUTHORITY"
    )


def test_the_three_warmup_quantities_are_frozen_separately() -> None:
    warmup = corpus.warmup_history_contract()
    assert set(warmup["three_distinct_quantities"]) == {
        "minimum_contiguous_history_to_first_evaluable",
        "minimum_observation_count",
        "rolling_window_span",
    }
    row = warmup["rows"]["VOL_PERCENTILE_2Y"]
    assert "730d eligible trailing window" in row["rolling_window_span"]
    assert row["minimum_observation_count"].startswith("365 prior RV_20")
    assert row["minimum_contiguous_history_to_first_evaluable"]["value"] == 386
    assert "730 populated days are never required" in row["evaluability_predicate"]


def test_a_composite_stays_incomplete_while_any_component_is_incomplete() -> None:
    warmup = corpus.warmup_history_contract()
    assert "every required component is complete" in (
        warmup["composite_inheritance_rule"]
    )
    incomplete = volatility.calculate_orderliness_score(
        volatility.OrderlinessScoreInput(
            range_percentile=None,
            downside_return=Decimal("1"),
            liquidation_percentile=Decimal("5"),
            volatility_percentile=Decimal("10"),
        )
    )
    assert incomplete.complete is False


def test_every_frozen_feature_evaluability_predicate_is_reproducible() -> None:
    first = corpus.warmup_history_contract()
    second = corpus.warmup_history_contract()
    assert first == second
    assert len(first["rows"]) == 33
    assert set(first["rows"]) == set(corpus.INITIAL_FEATURE_NAMES)
    with localcontext(Context(prec=3)):
        assert corpus.warmup_history_contract() == first
    for name, row in first["rows"].items():
        assert row["evaluability_predicate"].strip(), name
        assert "elapsed_days >=" not in row["evaluability_predicate"], name


# -----------------------------------------------------------------------------
# 12.6 preserved authority
# -----------------------------------------------------------------------------


def test_the_new_acquisition_semantics_change_no_historical_gate_value() -> None:
    diff = semantic_diff_from_v5_blockers()
    assert diff["threshold_change_count"] == 0
    assert diff["direction_change_count"] == 0
    assert diff["hard_role_change_count"] == 0
    assert diff["metric_intent_change_count"] == 0
    assert diff["btc019_reopened"] is False
    protocol = protocol_definition()
    assert protocol["no_threshold_authored"] is True
    assert protocol["btc019"]["sealed_sample_opened"] is False
    assert protocol["safety"]["qualifying_observations_collected"] is False
    assert protocol["final_classification"] == (
        "PROSPECTIVE_INTEGRATION_CORPUS_READY_FOR_FOURTH_XHIGH_REVIEW"
    )
    assert protocol["collection_authorized"] is False


def test_the_passed_owners_and_the_risk_size_definition_are_untouched() -> None:
    assert corpus.TRADE_ACTION_COMPARISON_OWNER_VERSION == (
        "TRADE_ACTION_COMPARISON_OWNER_V1"
    )
    assert corpus.TRADE_ELIGIBILITY_COMPOSITE_OWNER_VERSION == (
        "TRADE_ELIGIBILITY_COMPOSITE_OWNER_V1"
    )
    assert corpus.STOP_EVENT_UNIVERSE_ANCHOR == "CONTROL_REFERENCE_TRACK_ACTIVE_STOP"
    assert corpus.PRIOR_OBSERVABLE_OWNER == (
        "PREVIOUS_CONTIGUOUS_REQUIRED_PROVIDER_CONSENSUS_CLOSE_V1"
    )
    assert corpus.RISK_SIZE_QUANTITY == "position_notional"
    assert corpus.RISK_SIZE_PROBABILITY == Decimal("0.95")
    assert corpus.RISK_SIZE_STATISTIC == (
        "nearest_rank_p95_of_the_absolute_relative_differences"
    )
    sufficiency = evidence_sufficiency_contract()
    for metric in TARGET_METRICS:
        assert sufficiency["metrics"][metric]["minimum_denominator_chosen_here"] is None
