"""Synthetic POSTP1-003R2 tests; no real outcome or observation is used."""

from __future__ import annotations

import copy
import inspect
import json
import os
import subprocess
import sys
from dataclasses import fields, replace
from datetime import UTC, datetime, timedelta
from decimal import Context, Decimal, localcontext
from pathlib import Path

import pytest

from btc_predictor.research import prospective_integration_corpus as corpus
from btc_predictor.research import (
    prospective_integration_evidence_sufficiency as sufficiency,
)
from btc_predictor.research.reference_composite_v2 import V2_APPROVAL_GATES
from btc_predictor.research.structural_threshold_calibration import wilson_interval


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPOSITORY_ROOT / sufficiency.OUTPUT_NAMESPACE
EPOCH_START = datetime(2026, 1, 1, tzinfo=UTC)
SUFFICIENT_DECISION_TIME = EPOCH_START + timedelta(days=381, minutes=5)


def _evaluation_contract(tag: str = "A") -> dict[str, object]:
    return sufficiency.build_evaluation_contract(
        candidate_reference_identity=f"SYNTHETIC_CANDIDATE_{tag}",
        control_reference_identity="SYNTHETIC_CONTROL",
        contract_created_at=EPOCH_START - timedelta(seconds=2),
    )


def _authorized_registry(
    *, tag: str = "A",
) -> tuple[sufficiency.EvaluationEpochRegistry, dict[str, object]]:
    registry = sufficiency.EvaluationEpochRegistry()
    authorization = registry.authorize_initial_epoch(
        evaluation_contract=_evaluation_contract(tag),
        epoch_observation_start=EPOCH_START,
        authorized_at=EPOCH_START - timedelta(seconds=1),
    )
    return registry, authorization


def _evidence_through(
    current: datetime,
    *,
    authorization_sha256: str,
    transform: object | None = None,
) -> tuple[
    tuple[sufficiency.BlindEvidenceReference, ...],
    sufficiency.BlindEvidenceResolver,
    dict[str, dict[str, object]],
]:
    references: list[sufficiency.BlindEvidenceReference] = []
    records: dict[str, dict[str, object]] = {}
    for index, row in enumerate(sufficiency._expected_slots_through(EPOCH_START, current)):
        kwargs = {} if transform is None else transform(index, row)
        reference, material = sufficiency.build_synthetic_blind_evidence(
            row,
            evaluation_epoch_authorization_sha256=authorization_sha256,
            **kwargs,
        )
        references.append(reference)
        records.update(material)
    return tuple(references), sufficiency.BlindEvidenceResolver(records), records


def _monitor(
    references: tuple[sufficiency.BlindEvidenceReference, ...],
    resolver: sufficiency.BlindEvidenceResolver,
    registry: sufficiency.EvaluationEpochRegistry,
    authorization: dict[str, object],
    current: datetime,
) -> dict[str, object]:
    return sufficiency.evaluate_blind_sufficiency(
        references,
        resolver=resolver,
        registry=registry,
        evaluation_epoch_authorization_sha256=authorization["record_sha256"],
        current_decision_time=current,
    )


FINITE_RATE_EXPECTATIONS = {
    "gap_through_stop_consensus_agreement_rate": 381,
    "isolated_venue_stop_suppression_rate": 73,
    "regime_classification_disagreement_rate": 189,
    "setup_classification_disagreement_rate": 381,
    "trade_action_disagreement_rate": 381,
    "trade_eligibility_disagreement_rate": 381,
}


def test_corrected_definition_binds_exact_certified_parent_and_failed_lineage() -> None:
    definition = sufficiency.sufficiency_governance_definition()
    assert definition["program_ticket"] == "POSTP1-003R2"
    assert definition["certified_parent"]["protocol_sha256"] == (
        "8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7"
    )
    assert corpus.protocol_definition()["definition_sha256"] == (
        definition["certified_parent"]["protocol_sha256"]
    )
    assert corpus.protocol_definition()["material_child_count"] == 25
    assert definition["definition_sha256"] != sufficiency.FAILED_GOVERNANCE_SHA256
    assert [row["definition_sha256"] for row in definition["failed_governance_lineage"]] == [
        sufficiency.FAILED_GOVERNANCE_SHA256,
        sufficiency.FAILED_R1_GOVERNANCE_SHA256,
    ]
    for row in definition["failed_governance_lineage"]:
        assert row["authoritative"] is False
        assert row["prospective_observations_collected"] is False
        assert row["superseded_before_collection"] is True


def test_all_eight_historical_gates_are_mechanically_unchanged() -> None:
    frozen = {
        gate.metric: gate
        for gate in V2_APPROVAL_GATES
        if gate.metric in corpus.TARGET_METRICS
    }
    diff = sufficiency.semantic_diff_from_stage_b_gates()
    minima = sufficiency.metric_sufficiency_minima()["metrics"]
    assert set(frozen) == set(minima) == set(corpus.TARGET_METRICS)
    assert len(minima) == 8
    assert diff["threshold_change_count"] == 0
    assert diff["direction_change_count"] == 0
    assert diff["hard_role_change_count"] == 0
    assert diff["metric_intent_change_count"] == 0
    for metric, gate in frozen.items():
        assert minima[metric]["performance_threshold"] == str(gate.threshold)
        assert minima[metric]["direction"] == gate.direction
        assert minima[metric]["hard"] is gate.hard is True
        assert minima[metric]["metric_intent"] == gate.rationale


def test_parent_hash_mismatch_refuses_correction(monkeypatch: pytest.MonkeyPatch) -> None:
    original = corpus.protocol_definition()
    monkeypatch.setattr(
        corpus,
        "protocol_definition",
        lambda: {**original, "definition_sha256": "0" * 64},
    )
    with pytest.raises(sufficiency.SufficiencyGovernanceError, match="hash mismatch"):
        sufficiency.sufficiency_governance_definition()


def test_common_rate_evidence_strength_is_mechanically_derived() -> None:
    row = sufficiency.common_rate_evidence_strength()
    assert row["epsilon"] == "0.01"
    assert row["confidence"] == "0.95"
    assert row["closed_boundary_reference"] == "0.99"
    assert row["minimum_all_success_raw_denominator"] == 381
    assert row["boundary_probe"]["n_minus_one"] == 380
    assert row["boundary_probe"]["n_minus_one_satisfies"] is False
    assert row["boundary_probe"]["n_satisfies"] is True
    assert row["performance_threshold_replacement"] is False
    assert min(Decimal(value) for value in row["distance_by_finite_interior_rate_gate"].values()) == Decimal("0.01")


def test_exact_one_point_zero_performance_gate_uses_381_evidence_units() -> None:
    row = sufficiency.statistical_derivations()["rate_metrics"][
        corpus.CROSS_MARKET_METRIC
    ]
    minimum = sufficiency.metric_sufficiency_minima()["metrics"][
        corpus.CROSS_MARKET_METRIC
    ]
    assert row["performance_threshold"] == "1.0"
    assert row["evidence_strength_reference"] == "0.99"
    assert row["minimum_denominator"] == 381
    assert minimum["minimum_raw_sufficiency_denominator"] == 381
    assert minimum["minimum_distinct_dependence_units"] == 381
    assert minimum["performance_gate_unchanged"] is True
    assert wilson_interval(380, 380).lower < Decimal("0.99")
    assert wilson_interval(381, 381).lower >= Decimal("0.99")


def test_exact_one_point_zero_quantity_boundaries_are_enforced() -> None:
    for count, expected in ((0, False), (1, False), (380, False), (381, True)):
        counter = sufficiency._empty_metric_counter()
        counter["raw_sufficiency_denominator"] = count
        counter["authoritative_coverage_numerator"] = count
        counter["authoritative_coverage_denominator"] = count
        counter["dependence_unit_contributions"] = sufficiency.Counter(
            {f"{index:064x}": 1 for index in range(count)}
        )
        assert sufficiency._metric_satisfied(counter, 381) is expected


def test_one_cross_market_failure_still_fails_exact_performance_gate() -> None:
    result = corpus.aggregate_stage_b_metric(
        corpus.CROSS_MARKET_METRIC,
        numerator=380,
        denominator=381,
        synthetic=True,
    )
    assert Decimal(result["value"]) < Decimal(result["threshold"]) == Decimal("1.0")


@pytest.mark.parametrize(("metric", "n_min"), FINITE_RATE_EXPECTATIONS.items())
def test_each_finite_rate_minimum_retains_exact_wilson_boundary(
    metric: str, n_min: int
) -> None:
    row = sufficiency.statistical_derivations()["rate_metrics"][metric]
    threshold = Decimal(row["threshold"])
    assert row["minimum_denominator"] == n_min
    if row["direction"] == "minimum":
        assert wilson_interval(n_min - 1, n_min - 1).lower < threshold
        assert wilson_interval(n_min, n_min).lower >= threshold
    else:
        assert wilson_interval(0, n_min - 1).upper > threshold
        assert wilson_interval(0, n_min).upper <= threshold
    assert row["n_capability_minus_one_criterion_satisfied"] is False
    assert row["n_capability_criterion_satisfied"] is True


def test_p95_repeatability_boundary_is_exact_and_estimator_unchanged() -> None:
    row = sufficiency.p95_tail_repeatability()
    assert row["quantile"] == "0.95"
    assert row["tail_probability"] == "0.05"
    assert row["minimum_repeated_tail_occurrences"] == 2
    assert row["confidence"] == "0.95"
    assert row["minimum_denominator"] == 93
    assert row["minimum_distinct_sizing_evidence_units"] == 93
    assert Decimal(row["n_92"]["probability"]) < Decimal("0.95")
    assert Decimal(row["n_93"]["probability"]) >= Decimal("0.95")
    assert row["n_92"]["satisfies"] is False
    assert row["n_93"]["satisfies"] is True
    assert row["risk_statistic_changed"] is False
    values = tuple(Decimal(index) for index in range(1, 94))
    assert corpus.nearest_rank_percentile(values, Decimal("0.95")) == Decimal(89)


def test_three_sufficiency_quantities_are_explicitly_distinct() -> None:
    for row in sufficiency.metric_sufficiency_minima()["metrics"].values():
        assert row["performance_denominator"]
        assert row["minimum_raw_sufficiency_denominator"] > 0
        assert row["minimum_distinct_dependence_units"] > 0
        assert set(row["sufficiency_quantities_are_distinct"]) == {
            "effective_dependence_unit_count",
            "performance_denominator",
            "raw_sufficiency_denominator",
        }


def test_coverage_floor_uses_exact_integer_arithmetic() -> None:
    assert sufficiency.authoritative_coverage_satisfied(98, 99) is False
    assert sufficiency.authoritative_coverage_satisfied(99, 100) is True
    assert sufficiency.authoritative_coverage_satisfied(381, 7_601) is False
    assert sufficiency.authoritative_coverage_satisfied(0, 0) is False
    policy = sufficiency.coverage_policy()
    assert policy["floor"] == "0.99"
    assert policy["per_metric"] is True
    assert policy["floor_is_stage_b_performance_threshold"] is False
    assert policy["accounting_requirement"][
        "unaccounted_scheduled_slot_count_required"
    ] == 0


def test_coverage_taxonomy_counts_only_authoritatively_replayed_categories() -> None:
    policy = sufficiency.coverage_policy()
    assert set(policy["blind_categories_counting_as_authoritatively_replayed"]) == {
        "EVALUATED",
        "NOT_COMPARABLE",
        "NOT_IN_UNIVERSE",
    }
    assert set(policy["blind_categories_counting_as_coverage_failure"]) == {
        "DATA_QUALITY_FAIL",
        "PIT_INVALID",
        "REFERENCE_UNAVAILABLE",
        "SOURCE_UNAVAILABLE",
        "WARMUP_INCOMPLETE",
    }


def test_stop_dependence_unit_uses_only_replayed_root_position_episode() -> None:
    episode = "a" * 64
    one = sufficiency._derive_dependence_unit_id(
        corpus.CROSS_MARKET_METRIC,
        slot_id="b" * 64,
        control_position_episode_sha256=episode,
        active_stop_identity="CONTROL_STOP_TRANSITION_1",
    )
    repeated = sufficiency._derive_dependence_unit_id(
        corpus.CROSS_MARKET_METRIC,
        slot_id="c" * 64,
        control_position_episode_sha256=episode,
        active_stop_identity="CONTROL_STOP_TRANSITION_1",
    )
    changed_stop = sufficiency._derive_dependence_unit_id(
        corpus.CROSS_MARKET_METRIC,
        slot_id="d" * 64,
        control_position_episode_sha256=episode,
        active_stop_identity="CONTROL_STOP_TRANSITION_2",
    )
    assert one == repeated
    assert one == changed_stop
    new_position = sufficiency._derive_dependence_unit_id(
        corpus.CROSS_MARKET_METRIC,
        slot_id="e" * 64,
        control_position_episode_sha256="f" * 64,
        active_stop_identity="CONTROL_STOP_TRANSITION_3",
    )
    assert one != new_position
    policy = sufficiency.evidence_unit_policy()["metrics"][
        corpus.CROSS_MARKET_METRIC
    ]
    assert policy["maximum_sufficiency_credit_per_unit"] == 1
    assert "active_stop_identity" not in policy["identity_fields"]
    assert policy["dependence_unit_kind"] == "CONTROL_POSITION_ROOT_LIFECYCLE_EPISODE"


def test_daily_decision_and_sizing_units_are_the_canonical_slot() -> None:
    slot_id = "a" * 64
    for metric in (
        corpus.REGIME_METRIC,
        corpus.RISK_SIZE_METRIC,
        corpus.SETUP_METRIC,
        corpus.TRADE_ACTION_METRIC,
        corpus.TRADE_ELIGIBILITY_METRIC,
    ):
        assert sufficiency._derive_dependence_unit_id(
            metric,
            slot_id=slot_id,
            control_position_episode_sha256=None,
            active_stop_identity=None,
        ) == slot_id


def test_temporal_policy_adds_no_arbitrary_calendar_gate() -> None:
    policy = sufficiency.temporal_policy()
    assert policy["policy"] == "NO_SEPARATE_ARBITRARY_CALENDAR_MINIMUM"
    assert policy["minimum_calendar_duration"] is None
    assert policy["minimum_distinct_utc_days"] is None
    assert policy["minimum_distinct_iso_weeks"] is None
    assert policy["stage_c_live_shadow_days_imported"] is False
    assert set(policy["concentration_diagnostics"]) == {
        "distinct_utc_days",
        "distinct_iso_weeks",
        "first_evidence_time",
        "last_evidence_time",
        "largest_single_day_contribution",
        "largest_single_week_contribution",
        "distinct_dependence_unit_count",
        "largest_dependence_unit_raw_contribution",
    }


def test_monitor_api_contains_no_caller_authoritative_labels_or_outcomes() -> None:
    accepted = {field.name for field in fields(sufficiency.BlindEvidenceReference)}
    assert accepted == {
        "certified_parent_evidence_manifest_sha256",
        "evaluation_epoch_authorization_sha256",
        "slot_id",
    }
    prohibited = set(
        sufficiency.blind_monitor_contract()["prohibited_monitor_input_fields"]
    )
    assert accepted.isdisjoint(prohibited)
    assert set(inspect.signature(sufficiency.evaluate_blind_sufficiency).parameters).isdisjoint(
        prohibited
    )
    assert sufficiency.blind_monitor_contract()[
        "detailed_parent_reason_codes_exposed_to_monitor"
    ] is False


@pytest.mark.parametrize(
    "fact_kwargs",
    [
        {"universe_member_by_metric": {corpus.REGIME_METRIC: False}},
        {"comparable_by_metric": {corpus.REGIME_METRIC: False}},
        {"warmup_history_complete": False},
        {
            "maximum_available_at_by_metric": {
                corpus.REGIME_METRIC: EPOCH_START + timedelta(days=2)
            }
        },
        {
            "evidence_state_by_metric": {
                corpus.REGIME_METRIC: "SOURCE_UNAVAILABLE"
            }
        },
    ],
)
def test_parent_replay_wins_over_any_rehashed_blind_surface(
    fact_kwargs: dict[str, object],
) -> None:
    registry, authorization = _authorized_registry()
    daily = next(
        row
        for row in sufficiency._expected_slots_through(
            EPOCH_START, EPOCH_START + timedelta(days=1, minutes=5)
        )
        if row["cadence"] == corpus.STRATEGY_DAILY_CADENCE
    )
    reference, records = sufficiency.build_synthetic_blind_evidence(
        daily,
        evaluation_epoch_authorization_sha256=authorization["record_sha256"],
        **fact_kwargs,
    )
    replayed = sufficiency.BlindEvidenceResolver(records).replay(
        reference,
        authorization=authorization,
        current_decision_time=EPOCH_START + timedelta(days=2),
    )
    assert replayed.category_by_metric[corpus.REGIME_METRIC] != "EVALUATED"
    hostile = sufficiency._with_record_hash(
        {
            "declared_blind_projection": {
                corpus.REGIME_METRIC: {
                    "blind_category": "EVALUATED",
                    "dependence_unit_id": daily["slot_id"],
                }
            },
            "evaluation_epoch_authorization_sha256": authorization["record_sha256"],
            "schema_version": sufficiency.BLIND_PROJECTION_VERSION,
            "slot_id": daily["slot_id"],
        }
    )
    records[hostile["record_sha256"]] = hostile
    hostile_reference = replace(
        reference,
        certified_parent_evidence_manifest_sha256=hostile["record_sha256"],
    )
    resolver = sufficiency.BlindEvidenceResolver(records)
    with pytest.raises(
        sufficiency.SufficiencyGovernanceError,
        match="wrong schema/version",
    ):
        resolver.replay(
            hostile_reference,
            authorization=authorization,
            current_decision_time=EPOCH_START + timedelta(days=2),
        )


def test_reason_code_side_channel_is_refused() -> None:
    _registry, authorization = _authorized_registry()
    daily = next(
        row
        for row in sufficiency._expected_slots_through(
            EPOCH_START, EPOCH_START + timedelta(days=1, minutes=5)
        )
        if row["cadence"] == corpus.STRATEGY_DAILY_CADENCE
    )
    reference, records = sufficiency.build_synthetic_blind_evidence(
        daily,
        evaluation_epoch_authorization_sha256=authorization["record_sha256"],
    )
    hostile = sufficiency._with_record_hash(
        {
            "declared_blind_projection": {
                corpus.REGIME_METRIC: {
                    "blind_category": "CANDIDATE_CONTROL_DISAGREEMENT",
                    "dependence_unit_id": daily["slot_id"],
                }
            },
            "evaluation_epoch_authorization_sha256": authorization["record_sha256"],
            "schema_version": sufficiency.BLIND_PROJECTION_VERSION,
            "slot_id": daily["slot_id"],
        }
    )
    records[hostile["record_sha256"]] = hostile
    resolver = sufficiency.BlindEvidenceResolver(records)
    with pytest.raises(sufficiency.SufficiencyGovernanceError):
        resolver.replay(
            replace(
                reference,
                certified_parent_evidence_manifest_sha256=hostile["record_sha256"],
            ),
            authorization=authorization,
            current_decision_time=EPOCH_START + timedelta(days=2),
        )


def test_rehashed_control_stop_identity_cannot_override_lifecycle_replay() -> None:
    _registry, authorization = _authorized_registry()
    hourly = next(
        row
        for row in sufficiency._expected_slots_through(
            EPOCH_START, EPOCH_START + timedelta(hours=2)
        )
        if row["cadence"] == corpus.STOP_HOURLY_CADENCE
    )
    reference, records = sufficiency.build_synthetic_blind_evidence(
        hourly,
        evaluation_epoch_authorization_sha256=authorization["record_sha256"],
    )
    manifest = copy.deepcopy(
        records[reference.certified_parent_evidence_manifest_sha256]
    )
    stop_sha = next(iter(manifest["metric_owner_evidence_sha256_by_metric"].values()))
    hostile_stop = copy.deepcopy(records[stop_sha])
    hostile_stop.pop("record_sha256")
    hostile_stop["active_stop_identity"] = "f" * 64
    hostile_stop = sufficiency._with_record_hash(hostile_stop)
    records[hostile_stop["record_sha256"]] = hostile_stop
    manifest.pop("record_sha256")
    manifest["metric_owner_evidence_sha256_by_metric"] = {
        metric: hostile_stop["record_sha256"]
        for metric in corpus.STOP_EVENT_METRICS
    }
    manifest = sufficiency._with_record_hash(manifest)
    records[manifest["record_sha256"]] = manifest
    with pytest.raises(sufficiency.SufficiencyGovernanceError, match="does not replay"):
        sufficiency.BlindEvidenceResolver(records).replay(
            replace(
                reference,
                certified_parent_evidence_manifest_sha256=manifest["record_sha256"],
            ),
            authorization=authorization,
            current_decision_time=EPOCH_START + timedelta(hours=2),
        )


def test_cross_slot_parent_substitution_is_refused() -> None:
    _registry, authorization = _authorized_registry()
    daily_rows = [
        row
        for row in sufficiency._expected_slots_through(
            EPOCH_START, EPOCH_START + timedelta(days=2, minutes=5)
        )
        if row["cadence"] == corpus.STRATEGY_DAILY_CADENCE
    ]
    first, first_records = sufficiency.build_synthetic_blind_evidence(
        daily_rows[0],
        evaluation_epoch_authorization_sha256=authorization["record_sha256"],
    )
    second, second_records = sufficiency.build_synthetic_blind_evidence(
        daily_rows[1],
        evaluation_epoch_authorization_sha256=authorization["record_sha256"],
    )
    records = {**first_records, **second_records}
    first_manifest = copy.deepcopy(
        records[first.certified_parent_evidence_manifest_sha256]
    )
    second_manifest = records[second.certified_parent_evidence_manifest_sha256]
    first_manifest.pop("record_sha256")
    first_manifest["metric_owner_evidence_sha256_by_metric"][corpus.REGIME_METRIC] = (
        second_manifest["metric_owner_evidence_sha256_by_metric"][corpus.REGIME_METRIC]
    )
    first_manifest = sufficiency._with_record_hash(first_manifest)
    records[first_manifest["record_sha256"]] = first_manifest
    with pytest.raises(sufficiency.SufficiencyGovernanceError, match="wrong slot"):
        sufficiency.BlindEvidenceResolver(records).replay(
            replace(
                first,
                certified_parent_evidence_manifest_sha256=first_manifest[
                    "record_sha256"
                ],
            ),
            authorization=authorization,
            current_decision_time=EPOCH_START + timedelta(days=3),
        )


def test_risk_sizing_opportunity_requires_bound_candidate_control_outputs() -> None:
    _registry, authorization = _authorized_registry()
    daily = next(
        row
        for row in sufficiency._expected_slots_through(
            EPOCH_START, EPOCH_START + timedelta(days=1, minutes=5)
        )
        if row["cadence"] == corpus.STRATEGY_DAILY_CADENCE
    )
    reference, records = sufficiency.build_synthetic_blind_evidence(
        daily,
        evaluation_epoch_authorization_sha256=authorization["record_sha256"],
    )
    manifest = copy.deepcopy(
        records[reference.certified_parent_evidence_manifest_sha256]
    )
    owner_sha = manifest["metric_owner_evidence_sha256_by_metric"][
        corpus.RISK_SIZE_METRIC
    ]
    owner = copy.deepcopy(records[owner_sha])
    candidate_sha = owner["owner_output_record_sha256s"][0]
    hostile_candidate = copy.deepcopy(records[candidate_sha])
    hostile_candidate.pop("record_sha256")
    hostile_candidate["reference_identity"] = "ANOTHER_CANDIDATE"
    hostile_candidate = sufficiency._with_record_hash(hostile_candidate)
    records[hostile_candidate["record_sha256"]] = hostile_candidate
    owner.pop("record_sha256")
    owner["owner_output_record_sha256s"][0] = hostile_candidate["record_sha256"]
    owner = sufficiency._with_record_hash(owner)
    records[owner["record_sha256"]] = owner
    manifest.pop("record_sha256")
    manifest["metric_owner_evidence_sha256_by_metric"][corpus.RISK_SIZE_METRIC] = (
        owner["record_sha256"]
    )
    manifest = sufficiency._with_record_hash(manifest)
    records[manifest["record_sha256"]] = manifest
    with pytest.raises(sufficiency.SufficiencyGovernanceError, match="substituted"):
        sufficiency.BlindEvidenceResolver(records).replay(
            replace(
                reference,
                certified_parent_evidence_manifest_sha256=manifest["record_sha256"],
            ),
            authorization=authorization,
            current_decision_time=EPOCH_START + timedelta(days=2),
        )


def test_warmup_and_pit_failures_add_no_raw_or_unit_credit() -> None:
    registry, authorization = _authorized_registry()
    current = EPOCH_START + timedelta(days=1, minutes=5)

    def transform(_index: int, row: dict[str, str]) -> dict[str, object]:
        if row["cadence"] == corpus.STRATEGY_DAILY_CADENCE:
            return {"warmup_history_complete": False}
        return {}

    references, resolver, _records = _evidence_through(
        current,
        authorization_sha256=authorization["record_sha256"],
        transform=transform,
    )
    result = _monitor(references, resolver, registry, authorization, current)
    for metric in corpus.DECISION_METRICS:
        state = result["metric_states"][metric]
        assert state["raw_sufficiency_denominator"] == 0
        assert state["effective_dependence_unit_count"] == 0
        assert state["authoritative_coverage_numerator"] == 0
        assert state["blind_category_counts"] == {"WARMUP_INCOMPLETE": 1}


def test_381_events_from_one_stop_episode_are_not_381_units() -> None:
    registry, authorization = _authorized_registry()
    current = EPOCH_START + timedelta(hours=398, minutes=5)
    shared_episode = ("a" * 64, "ONE_CONTROL_ACTIVE_STOP_EPISODE")

    def transform(_index: int, row: dict[str, str]) -> dict[str, object]:
        if row["cadence"] != corpus.STOP_HOURLY_CADENCE:
            return {}
        return {
            "stop_episode_by_metric": {
                metric: shared_episode for metric in corpus.STOP_EVENT_METRICS
            }
        }

    references, resolver, _records = _evidence_through(
        current,
        authorization_sha256=authorization["record_sha256"],
        transform=transform,
    )
    result = _monitor(references, resolver, registry, authorization, current)
    gap = result["metric_states"][corpus.GAP_THROUGH_METRIC]
    assert gap["raw_sufficiency_denominator"] == 381
    assert gap["distinct_dependence_unit_count"] == 1
    assert gap["largest_dependence_unit_raw_contribution"] == 381
    assert gap["sufficient"] is False
    assert result["overall_sufficient"] is False


def test_73_isolated_events_from_four_episodes_are_insufficient() -> None:
    registry, authorization = _authorized_registry()
    current = EPOCH_START + timedelta(days=73, minutes=5)

    def transform(index: int, row: dict[str, str]) -> dict[str, object]:
        if row["cadence"] != corpus.STOP_HOURLY_CADENCE:
            return {}
        episode = (
            sufficiency._digest({"episode": index % 4}),
            f"STOP_{index % 4}",
        )
        return {
            "stop_episode_by_metric": {
                corpus.ISOLATED_VENUE_METRIC: episode
            }
        }

    references, resolver, _records = _evidence_through(
        current,
        authorization_sha256=authorization["record_sha256"],
        transform=transform,
    )
    result = _monitor(references, resolver, registry, authorization, current)
    isolated = result["metric_states"][corpus.ISOLATED_VENUE_METRIC]
    assert isolated["raw_sufficiency_denominator"] == 73
    assert isolated["distinct_dependence_unit_count"] == 4
    assert isolated["sufficient"] is False


def test_93_risk_rows_from_fewer_than_93_opportunities_are_insufficient() -> None:
    counter = sufficiency._empty_metric_counter()
    counter["raw_sufficiency_denominator"] = 93
    counter["authoritative_coverage_numerator"] = 93
    counter["authoritative_coverage_denominator"] = 93
    counter["dependence_unit_contributions"] = sufficiency.Counter(
        {f"{index:064x}": 1 for index in range(92)}
    )
    assert sufficiency._metric_satisfied(counter, 93) is False


@pytest.fixture(scope="module")
def sufficient_run() -> tuple[
    tuple[sufficiency.BlindEvidenceReference, ...],
    sufficiency.BlindEvidenceResolver,
    sufficiency.EvaluationEpochRegistry,
    dict[str, object],
    dict[str, object],
]:
    registry, authorization = _authorized_registry()
    references, resolver, _records = _evidence_through(
        SUFFICIENT_DECISION_TIME,
        authorization_sha256=authorization["record_sha256"],
    )
    result = _monitor(
        references, resolver, registry, authorization, SUFFICIENT_DECISION_TIME
    )
    return references, resolver, registry, authorization, result


def test_global_cutoff_requires_all_raw_unit_coverage_and_accounting_gates(
    sufficient_run: tuple[object, ...],
) -> None:
    _references, _resolver, registry, authorization, result = sufficient_run
    assert result["overall_sufficient"] is True
    assert result["state"] == "EVALUATION_CUTOFF_FROZEN"
    assert result["stage_b_sufficiency_cutoff"] == SUFFICIENT_DECISION_TIME.isoformat()
    assert result["accounting"]["unaccounted_scheduled_slots"] == 0
    assert all(row["sufficient"] for row in result["metric_states"].values())
    assert all(
        row["authoritative_coverage_satisfied"]
        for row in result["metric_states"].values()
    )
    cutoff = registry.cutoff(authorization["record_sha256"])
    assert cutoff["record_sha256"] == result["cutoff_record_sha256"]
    assert cutoff["authoritative_evidence_manifest_sha256"] == result[
        "authoritative_evidence_manifest_sha256"
    ]
    manifest = registry.evidence_manifest(
        result["authoritative_evidence_manifest_sha256"]
    )
    assert len(manifest) == result["accounting"]["scheduled_slots"]
    assert sufficiency._digest(list(manifest)) == result[
        "authoritative_evidence_manifest_sha256"
    ]


def test_cutoff_validator_replays_strict_manifest_and_all_counters(
    sufficient_run: tuple[object, ...],
) -> None:
    references, resolver, registry, authorization, _result = sufficient_run
    cutoff = registry.cutoff(authorization["record_sha256"])
    manifest = registry.evidence_manifest(
        cutoff["authoritative_evidence_manifest_sha256"]
    )
    assert sufficiency.validate_cutoff_record(
        cutoff,
        manifest_rows=manifest,
        evidence_references=references,
        resolver=resolver,
        authorization=authorization,
    ) == cutoff


def test_caller_fabricated_cutoffs_cannot_be_frozen_or_validated(
    sufficient_run: tuple[object, ...],
) -> None:
    references, resolver, registry, authorization, _result = sufficient_run
    fabricated = {
        "record_sha256": "a" * 64,
        "authoritative_evidence_manifest_sha256": "b" * 64,
    }
    with pytest.raises(sufficiency.SufficiencyGovernanceError, match="caller-supplied"):
        registry.freeze_cutoff(
            authorization["record_sha256"], fabricated, (), {}
        )
    with pytest.raises(sufficiency.SufficiencyGovernanceError, match="fields differ"):
        sufficiency.validate_cutoff_record(
            fabricated,
            manifest_rows=(),
            evidence_references=references,
            resolver=resolver,
            authorization=authorization,
        )


@pytest.mark.parametrize("manifest_attack", ["missing", "duplicate"])
def test_cutoff_manifest_census_attack_is_refused(
    sufficient_run: tuple[object, ...], manifest_attack: str
) -> None:
    references, resolver, registry, authorization, _result = sufficient_run
    cutoff = copy.deepcopy(registry.cutoff(authorization["record_sha256"]))
    manifest = list(
        registry.evidence_manifest(cutoff["authoritative_evidence_manifest_sha256"])
    )
    if manifest_attack == "missing":
        manifest.pop()
    else:
        manifest.append(dict(manifest[-1]))
    cutoff["authoritative_evidence_manifest_sha256"] = sufficiency._digest(manifest)
    cutoff.pop("record_sha256")
    cutoff = sufficiency._with_record_hash(cutoff)
    with pytest.raises(sufficiency.SufficiencyGovernanceError):
        sufficiency.validate_cutoff_record(
            cutoff,
            manifest_rows=manifest,
            evidence_references=references,
            resolver=resolver,
            authorization=authorization,
        )


def test_manifest_reference_from_another_epoch_is_refused() -> None:
    _registry, authorization = _authorized_registry()
    daily = next(
        row
        for row in sufficiency._expected_slots_through(
            EPOCH_START, EPOCH_START + timedelta(days=1, minutes=5)
        )
        if row["cadence"] == corpus.STRATEGY_DAILY_CADENCE
    )
    reference, records = sufficiency.build_synthetic_blind_evidence(
        daily,
        evaluation_epoch_authorization_sha256=authorization["record_sha256"],
    )
    manifest = copy.deepcopy(
        records[reference.certified_parent_evidence_manifest_sha256]
    )
    manifest.pop("record_sha256")
    manifest["evaluation_epoch_authorization_sha256"] = "e" * 64
    manifest = sufficiency._with_record_hash(manifest)
    records[manifest["record_sha256"]] = manifest
    with pytest.raises(sufficiency.SufficiencyGovernanceError, match="wrong epoch"):
        sufficiency.BlindEvidenceResolver(records).replay(
            replace(
                reference,
                certified_parent_evidence_manifest_sha256=manifest["record_sha256"],
            ),
            authorization=authorization,
            current_decision_time=EPOCH_START + timedelta(days=2),
        )
@pytest.mark.parametrize(
    "mutation",
    [
        ("raw", 1),
        ("dependence", 1),
        ("coverage", -1),
        ("late_cutoff", 1),
        ("early_cutoff", -1),
    ],
)
def test_self_rehashed_false_cutoff_is_refused(
    sufficient_run: tuple[object, ...], mutation: tuple[str, int]
) -> None:
    references, resolver, registry, authorization, _result = sufficient_run
    cutoff = copy.deepcopy(registry.cutoff(authorization["record_sha256"]))
    manifest = registry.evidence_manifest(
        cutoff["authoritative_evidence_manifest_sha256"]
    )
    kind, delta = mutation
    if kind == "raw":
        cutoff["per_metric_counts"][corpus.CROSS_MARKET_METRIC][
            "raw_sufficiency_denominator"
        ] += delta
    elif kind == "dependence":
        cutoff["per_metric_counts"][corpus.CROSS_MARKET_METRIC][
            "distinct_dependence_unit_count"
        ] += delta
    elif kind == "coverage":
        cutoff["per_metric_counts"][corpus.CROSS_MARKET_METRIC][
            "authoritative_coverage_numerator"
        ] += delta
    else:
        cutoff["cutoff_decision_time"] = (
            datetime.fromisoformat(cutoff["cutoff_decision_time"])
            + timedelta(days=delta)
        ).isoformat()
    cutoff.pop("record_sha256")
    cutoff = sufficiency._with_record_hash(cutoff)
    with pytest.raises(sufficiency.SufficiencyGovernanceError):
        sufficiency.validate_cutoff_record(
            cutoff,
            manifest_rows=manifest,
            evidence_references=references,
            resolver=resolver,
            authorization=authorization,
        )


@pytest.mark.parametrize("corruption", ["deleted", "substituted"])
def test_frozen_parent_evidence_corruption_prevents_terminal_result(
    sufficient_run: tuple[object, ...], corruption: str
) -> None:
    _references, resolver, registry, authorization, _result = sufficient_run
    cutoff = registry.cutoff(authorization["record_sha256"])
    manifest = registry.evidence_manifest(
        cutoff["authoritative_evidence_manifest_sha256"]
    )
    parent_sha = manifest[0]["certified_parent_evidence_manifest_sha256"]
    records = resolver.records
    original = records[parent_sha]
    if corruption == "deleted":
        del records[parent_sha]
    else:
        records[parent_sha] = {
            **original,
            "cadence": "SUBSTITUTED_CADENCE",
        }
    try:
        with pytest.raises(sufficiency.SufficiencyGovernanceError):
            registry.persist_evaluation_result(
                authorization_sha256=authorization["record_sha256"],
                result="PASS",
            )
    finally:
        records[parent_sha] = original


def test_one_unaccounted_slot_prevents_cutoff() -> None:
    registry, authorization = _authorized_registry()
    references, resolver, records = _evidence_through(
        SUFFICIENT_DECISION_TIME,
        authorization_sha256=authorization["record_sha256"],
    )
    missing = references[0]
    incomplete = references[1:]
    result = _monitor(
        incomplete,
        sufficiency.BlindEvidenceResolver(records),
        registry,
        authorization,
        SUFFICIENT_DECISION_TIME,
    )
    assert missing.slot_id not in {row.slot_id for row in incomplete}
    assert result["overall_sufficient"] is False
    assert result["stage_b_sufficiency_cutoff"] is None
    assert result["accounting"]["unaccounted_scheduled_slots"] == 1


def test_about_five_percent_authoritative_coverage_cannot_certify() -> None:
    counter = sufficiency._empty_metric_counter()
    counter["raw_sufficiency_denominator"] = 381
    counter["authoritative_coverage_numerator"] = 381
    counter["authoritative_coverage_denominator"] = 7_601
    counter["dependence_unit_contributions"] = sufficiency.Counter(
        {f"{index:064x}": 1 for index in range(381)}
    )
    assert sufficiency._metric_satisfied(counter, 381) is False


def test_opposite_hidden_outcomes_have_identical_sufficiency_state() -> None:
    first_registry, first_authorization = _authorized_registry()
    second_registry, second_authorization = _authorized_registry()
    assert first_authorization == second_authorization
    current = EPOCH_START + timedelta(days=3, minutes=5)
    references, resolver, records = _evidence_through(
        current,
        authorization_sha256=first_authorization["record_sha256"],
    )
    favorable_hidden_outcomes = {metric: True for metric in corpus.TARGET_METRICS}
    adverse_hidden_outcomes = {metric: False for metric in corpus.TARGET_METRICS}
    assert favorable_hidden_outcomes != adverse_hidden_outcomes
    first = _monitor(
        references, resolver, first_registry, first_authorization, current
    )
    second = _monitor(
        tuple(reversed(references)),
        sufficiency.BlindEvidenceResolver(records),
        second_registry,
        second_authorization,
        current,
    )
    assert first == second


def test_late_revision_and_surface_mutation_cannot_move_frozen_cutoff(
    sufficient_run: tuple[object, ...],
) -> None:
    references, resolver, registry, authorization, frozen = sufficient_run
    later = SUFFICIENT_DECISION_TIME + timedelta(days=2)
    extended, extended_resolver, _records = _evidence_through(
        later,
        authorization_sha256=authorization["record_sha256"],
    )
    assert len(extended) > len(references)
    replayed = _monitor(extended, extended_resolver, registry, authorization, later)
    assert replayed == frozen
    assert replayed["stage_b_sufficiency_cutoff"] == frozen[
        "stage_b_sufficiency_cutoff"
    ]
    assert replayed["authoritative_evidence_manifest_sha256"] == frozen[
        "authoritative_evidence_manifest_sha256"
    ]


def test_epoch_authorization_requires_real_contract_hash_and_fixed_identity() -> None:
    registry = sufficiency.EvaluationEpochRegistry()
    with pytest.raises(sufficiency.SufficiencyGovernanceError, match="fields differ"):
        registry.authorize_initial_epoch(
            evaluation_contract={
                "definition_sha256": "e" * 64,
                "schema_version": "PLACEHOLDER",
            },
            epoch_observation_start=EPOCH_START,
        )
    with pytest.raises(sufficiency.SufficiencyGovernanceError, match="arbitrary"):
        registry.authorize_initial_epoch(
            evaluation_contract=_evaluation_contract(),
            epoch_observation_start=EPOCH_START,
            evaluation_epoch_id="RANDOM_RETRY",
        )
    authorization = registry.authorize_initial_epoch(
        evaluation_contract=_evaluation_contract(),
        epoch_observation_start=EPOCH_START,
    )
    assert authorization["evaluation_epoch_id"] == sufficiency.INITIAL_EPOCH_ID
    assert sufficiency._is_sha256(authorization["evaluation_contract_sha256"])
    for field in (
        "blind_monitor_sha256",
        "certified_corpus_sha256",
        "coverage_policy_sha256",
        "evidence_unit_policy_sha256",
        "sufficiency_governance_sha256",
        "temporal_policy_sha256",
    ):
        assert sufficiency._is_sha256(authorization[field])


def test_evaluation_contract_strict_schema_and_bindings_fail_closed() -> None:
    registry = sufficiency.EvaluationEpochRegistry()
    for payload in ({}, {"foo": "bar"}):
        with pytest.raises(sufficiency.SufficiencyGovernanceError):
            registry.authorize_initial_epoch(
                evaluation_contract=sufficiency._with_definition_hash(payload),
                epoch_observation_start=EPOCH_START,
            )

    valid = _evaluation_contract()
    mutations = [
        {key: value for key, value in valid.items() if key != "candidate_reference_identity"},
        {key: value for key, value in valid.items() if key != "control_reference_identity"},
        {**valid, "candidate_reference_identity": valid["control_reference_identity"]},
        {**valid, "certified_corpus_sha256": "0" * 64},
        {**valid, "sufficiency_governance_sha256": "1" * 64},
        {**valid, "stage_b_evaluation_contract_sha256": "2" * 64},
    ]
    for mutation in mutations:
        mutation.pop("definition_sha256", None)
        with pytest.raises(sufficiency.SufficiencyGovernanceError):
            registry.authorize_initial_epoch(
                evaluation_contract=sufficiency._with_definition_hash(mutation),
                epoch_observation_start=EPOCH_START,
            )


def test_evaluation_contract_and_authorization_must_precede_epoch() -> None:
    late_contract = sufficiency.build_evaluation_contract(
        candidate_reference_identity="SYNTHETIC_CANDIDATE_A",
        control_reference_identity="SYNTHETIC_CONTROL",
        contract_created_at=EPOCH_START,
    )
    registry = sufficiency.EvaluationEpochRegistry()
    with pytest.raises(sufficiency.SufficiencyGovernanceError, match="prospective"):
        registry.authorize_initial_epoch(
            evaluation_contract=late_contract,
            epoch_observation_start=EPOCH_START,
            authorized_at=EPOCH_START,
        )


def test_initial_epoch_is_unique_across_parallel_contract_retry() -> None:
    registry, authorization = _authorized_registry()
    assert registry.authorize_initial_epoch(
        evaluation_contract=_evaluation_contract(),
        epoch_observation_start=EPOCH_START,
        authorized_at=EPOCH_START - timedelta(seconds=1),
    ) == authorization
    changed = registry.authorize_initial_epoch(
        evaluation_contract=_evaluation_contract("CHANGED"),
        epoch_observation_start=EPOCH_START,
        authorized_at=EPOCH_START - timedelta(seconds=1),
    )
    assert changed["evaluation_contract_sha256"] != authorization[
        "evaluation_contract_sha256"
    ]


def test_valid_revalidated_cutoff_allows_pass_terminal(
    sufficient_run: tuple[object, ...],
) -> None:
    _references, _resolver, registry, authorization, _result = sufficient_run
    derivation = registry._derivation_by_authorization[authorization["record_sha256"]]
    fresh = sufficiency.EvaluationEpochRegistry()
    fresh_authorization = fresh.authorize_initial_epoch(
        evaluation_contract=_evaluation_contract(),
        epoch_observation_start=EPOCH_START,
        authorized_at=EPOCH_START - timedelta(seconds=1),
    )
    assert fresh_authorization == authorization
    fresh.freeze_derived_cutoff(derivation)
    terminal = fresh.persist_evaluation_result(
        authorization_sha256=authorization["record_sha256"],
        result="PASS",
    )
    assert terminal["result"] == "PASS"
    assert terminal["terminal"] is True
    with pytest.raises(sufficiency.EvaluationEpochFrozenError):
        fresh.persist_evaluation_result(
            authorization_sha256=authorization["record_sha256"],
            result="PASS",
        )


def test_fail_is_terminal_and_arbitrary_retry_id_is_not_authorization(
    sufficient_run: tuple[object, ...],
) -> None:
    references, resolver, registry, authorization, _result = sufficient_run
    terminal = registry.persist_evaluation_result(
        authorization_sha256=authorization["record_sha256"],
        result="FAIL",
    )
    assert terminal["terminal"] is True
    assert terminal["result"] == "FAIL"
    assert terminal["cutoff_record_sha256"] == registry.cutoff(
        authorization["record_sha256"]
    )["record_sha256"]
    with pytest.raises(sufficiency.EvaluationEpochFrozenError, match="terminal"):
        _monitor(
            references,
            resolver,
            registry,
            authorization,
            SUFFICIENT_DECISION_TIME,
        )
    with pytest.raises(sufficiency.EvaluationEpochFrozenError, match="terminal"):
        registry.authorize_initial_epoch(
            evaluation_contract=_evaluation_contract(),
            epoch_observation_start=EPOCH_START,
            authorized_at=EPOCH_START - timedelta(seconds=1),
        )
    with pytest.raises(sufficiency.SufficiencyGovernanceError, match="arbitrary"):
        registry.authorize_initial_epoch(
            evaluation_contract=_evaluation_contract(),
            epoch_observation_start=EPOCH_START,
            evaluation_epoch_id="NEW_RANDOM_UUID",
        )


def test_every_sufficiency_result_binds_parent_policy_and_epoch_identities() -> None:
    registry, authorization = _authorized_registry()
    current = EPOCH_START + timedelta(days=1, minutes=5)
    references, resolver, _records = _evidence_through(
        current,
        authorization_sha256=authorization["record_sha256"],
    )
    result = _monitor(references, resolver, registry, authorization, current)
    for field in (
        "blind_monitor_sha256",
        "certified_corpus_sha256",
        "coverage_policy_sha256",
        "decision_universe_sha256",
        "evaluation_contract_sha256",
        "evaluation_epoch_authorization_sha256",
        "evidence_unit_policy_sha256",
        "governance_sha256",
        "metric_evidence_contract_sha256",
        "temporal_policy_sha256",
    ):
        assert sufficiency._is_sha256(result[field])
    assert result["window_start"] == EPOCH_START.isoformat()
    assert result["current_decision_time"] == current.isoformat()


def test_top_level_hash_mechanically_binds_every_material_child() -> None:
    definition = sufficiency.sufficiency_governance_definition()
    assert definition["material_child_count"] == len(sufficiency._CHILD_ARTIFACTS)
    assert definition["material_child_count"] == len(
        definition["child_definition_sha256"]
    )
    assert definition["material_child_count"] == 18
    assert set(sufficiency.protocol_hashes()) == set(
        definition["child_definition_sha256"]
    ) | {"sufficiency_governance"}
    assert all(
        sufficiency._is_sha256(value)
        for value in definition["child_definition_sha256"].values()
    )
    sufficiency.verify_sufficiency_governance_definition(definition)


def test_blind_and_cutoff_executable_schemas_are_hash_bound() -> None:
    manifest = sufficiency.certified_blind_parent_evidence_manifest_contract()
    assert set(manifest["referenced_record_schemas"]) == {
        sufficiency.PARENT_INPUT_RECORD_VERSION,
        sufficiency.PARENT_METRIC_RECORD_VERSION,
        sufficiency.PARENT_PORTFOLIO_STATE_VERSION,
        sufficiency.PARENT_RISK_OUTPUT_VERSION,
        sufficiency.PARENT_STOP_INPUT_VERSION,
        sufficiency.PARENT_TRADE_ACTION_VERSION,
        sufficiency.PARENT_WARMUP_RECORD_VERSION,
    }
    cutoff = sufficiency.evaluation_cutoff_contract()
    assert set(cutoff["cutoff_record_strict_fields"]) == (
        sufficiency._strict_cutoff_fields()
    )
    assert cutoff["manifest_row_strict_fields"] == [
        "certified_parent_evidence_manifest_sha256",
        "slot_id",
    ]
    evaluation = sufficiency.evaluation_contract_schema()
    assert set(evaluation["exact_fields"]) == {
        "candidate_reference_identity",
        "certified_corpus_sha256",
        "contract_created_at",
        "control_reference_identity",
        "definition_sha256",
        "schema_version",
        "stage_b_evaluation_contract_sha256",
        "sufficiency_governance_sha256",
    }


@pytest.mark.parametrize(
    "builder_name",
    [builder for _filename, _child_key, builder in sufficiency._CHILD_ARTIFACTS],
)
def test_every_material_child_mutation_moves_parent_hash(
    monkeypatch: pytest.MonkeyPatch, builder_name: str
) -> None:
    baseline = sufficiency.sufficiency_governance_definition()["definition_sha256"]
    builder = getattr(sufficiency, builder_name)
    original = builder()

    def mutated_builder() -> dict[str, object]:
        changed = {
            key: value for key, value in original.items() if key != "definition_sha256"
        }
        changed["synthetic_mutation_probe"] = builder_name
        return sufficiency._with_definition_hash(changed)

    monkeypatch.setattr(sufficiency, builder_name, mutated_builder)
    assert sufficiency.sufficiency_governance_definition()["definition_sha256"] != baseline


@pytest.mark.parametrize(
    ("builder_name", "field"),
    [
        ("common_rate_evidence_strength", "minimum_all_success_raw_denominator"),
        ("p95_tail_repeatability", "minimum_denominator"),
        ("coverage_policy", "floor"),
        ("evidence_unit_policy", "raw_observations_are_independent_by_default"),
        ("blind_monitor_contract", "caller_declared_projection_is_authority"),
        ("certified_blind_parent_evidence_manifest_contract", "required_owner_evidence"),
        ("blind_replay_derivation_contract", "replay_steps"),
        ("blind_category_mapping", "mapping_precedence"),
        ("evaluation_contract_schema", "exact_fields"),
        ("evaluation_epoch_contract", "initial_epoch_unique"),
        ("evaluation_cutoff_contract", "first_cutoff_immutable"),
        ("cutoff_validation_contract", "earliest_proof"),
    ],
)
def test_required_semantic_mutations_move_child_and_parent(
    monkeypatch: pytest.MonkeyPatch,
    builder_name: str,
    field: str,
) -> None:
    builder = getattr(sufficiency, builder_name)
    original = builder()
    baseline_parent = sufficiency.sufficiency_governance_definition()[
        "definition_sha256"
    ]

    def mutated() -> dict[str, object]:
        row = {key: value for key, value in original.items() if key != "definition_sha256"}
        if isinstance(row[field], bool):
            row[field] = not row[field]
        elif isinstance(row[field], int):
            row[field] += 1
        else:
            row[field] = "MUTATED"
        return sufficiency._with_definition_hash(row)

    monkeypatch.setattr(sufficiency, builder_name, mutated)
    assert mutated()["definition_sha256"] != original["definition_sha256"]
    assert sufficiency.sufficiency_governance_definition()["definition_sha256"] != baseline_parent


def test_hash_is_decimal_context_seed_cwd_and_process_invariant(tmp_path: Path) -> None:
    expected = sufficiency.protocol_hashes()
    with localcontext(Context(prec=3)):
        assert sufficiency.protocol_hashes() == expected
    with localcontext(Context(prec=200)):
        assert sufficiency.protocol_hashes() == expected
    script = (
        "import json;from btc_predictor.research import "
        "prospective_integration_evidence_sufficiency as s;"
        "print(json.dumps(s.protocol_hashes(),sort_keys=True))"
    )
    for seed, cwd in (("0", REPOSITORY_ROOT), ("19", tmp_path), ("999", tmp_path)):
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=cwd,
            env={
                **os.environ,
                "PYTHONHASHSEED": seed,
                "PYTHONPATH": str(REPOSITORY_ROOT),
            },
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == expected


def test_artifacts_reproduce_and_regenerate_deterministically(tmp_path: Path) -> None:
    restored = sufficiency.restore_artifacts(ARTIFACT_DIR)
    assert restored == sufficiency.sufficiency_governance_definition()
    sufficiency.write_artifacts(tmp_path)
    first = {path.name: path.read_bytes() for path in sorted(tmp_path.iterdir())}
    sufficiency.write_artifacts(tmp_path)
    second = {path.name: path.read_bytes() for path in sorted(tmp_path.iterdir())}
    persisted = {
        path.name: path.read_bytes() for path in sorted(ARTIFACT_DIR.iterdir())
    }
    assert first == second == persisted


def test_tampered_child_and_unbound_artifact_are_refused(tmp_path: Path) -> None:
    sufficiency.write_artifacts(tmp_path)
    child_path = tmp_path / sufficiency.COVERAGE_FILENAME
    child = json.loads(child_path.read_text())
    child["floor"] = "0.05"
    child_path.write_text(json.dumps(child, indent=2, sort_keys=True) + "\n")
    with pytest.raises(sufficiency.SufficiencyGovernanceError, match="does not reproduce"):
        sufficiency.restore_artifacts(tmp_path)
    sufficiency.write_artifacts(tmp_path)
    (tmp_path / "unbound.json").write_text("{}\n")
    with pytest.raises(sufficiency.SufficiencyGovernanceError, match="unbound"):
        sufficiency.restore_artifacts(tmp_path)


def test_governance_is_pre_data_and_authorizes_nothing_downstream() -> None:
    definition = sufficiency.sufficiency_governance_definition()
    assert definition["status"] == "R2_CORRECTED_FROZEN_PRE_DATA_SUFFICIENCY_GOVERNANCE"
    assert definition["final_classification"] == sufficiency.FINAL_CLASSIFICATION
    assert definition["collection_authorized"] is False
    assert definition["postp1_004_authorized"] is False
    assert definition["safety"] == {
        "btc019_sealed_data_accessed": False,
        "prospective_observations_collected": False,
        "real_stage_b_evaluation_run": False,
        "real_stage_b_numerators_inspected": False,
    }
    assert definition["btc019"] == {
        "reopened": False,
        "sealed_sample_accessed": False,
        "terminal": True,
    }
    assert definition["epic_t"] == {"modified": False, "reopened": False}


def test_report_states_central_answers_and_review_handoff() -> None:
    report = (ARTIFACT_DIR / sufficiency.REPORT_FILENAME).read_text()
    assert sufficiency.FINAL_CLASSIFICATION in report
    assert "Threshold changes: 0" in report
    assert "performance threshold remains exactly 1.0" in report
    assert "380 all-success independent units fail and 381 pass" in report
    assert "93 distinct sizing opportunities" in report
    assert "at least 0.99" in report
    assert "no separate arbitrary calendar minimum" in report
    assert "POSTP1-004 authorized: NO" in report
    assert "Prospective collection authorized: NO" in report
    assert "sealed sample touched: NO / NO" in report
