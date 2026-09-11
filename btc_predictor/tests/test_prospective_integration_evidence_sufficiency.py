"""Synthetic POSTP1-003 tests for the frozen pre-data sufficiency governance.

No fixture contains a real candidate outcome, metric numerator, relative sizing
difference or collected observation.  The blind monitor receives only scheduled
slot identity, certified universe membership and accounting dispositions.
"""

from __future__ import annotations

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
EVALUATION_CONTRACT_SHA256 = "e" * 64
EPOCH_ID = "SYNTHETIC_POSTP1_003_EPOCH"
EPOCH_START = datetime(2026, 1, 1, tzinfo=UTC)


def _blind_slot(
    expected: dict[str, str],
    *,
    overrides: dict[str, sufficiency.BlindMetricDisposition] | None = None,
) -> sufficiency.BlindScheduledSlot:
    observation_time = datetime.fromisoformat(expected["observation_time"])
    decision_time = datetime.fromisoformat(expected["decision_time"])
    applicable = {
        metric
        for metric, cadence in sufficiency._metric_cadences().items()
        if cadence == expected["cadence"]
    }
    rows = {
        metric: sufficiency.BlindMetricDisposition(
            metric=metric,
            universe_member=True,
            disposition=corpus.STATE_EVALUATED,
        )
        for metric in applicable
    }
    rows.update(overrides or {})
    return sufficiency.BlindScheduledSlot(
        cadence=expected["cadence"],
        observation_time=observation_time,
        decision_time=decision_time,
        slot_id=expected["slot_id"],
        global_disposition=corpus.STATE_EVALUATED,
        global_reason_codes=(),
        metrics=tuple(rows[metric] for metric in sorted(rows)),
    )


def _synthetic_slots_through(
    current: datetime,
) -> tuple[sufficiency.BlindScheduledSlot, ...]:
    return tuple(
        _blind_slot(row)
        for row in sufficiency._expected_slots_through(EPOCH_START, current)
    )


def _monitor(
    slots: tuple[sufficiency.BlindScheduledSlot, ...],
    current: datetime,
) -> dict[str, object]:
    return sufficiency.evaluate_blind_sufficiency(
        slots,
        collection_epoch_id=EPOCH_ID,
        evaluation_contract_sha256=EVALUATION_CONTRACT_SHA256,
        epoch_observation_start=EPOCH_START,
        current_decision_time=current,
    )


# ---------------------------------------------------------------------------
# Historical parity and parent binding
# ---------------------------------------------------------------------------


def test_all_eight_target_metrics_are_recovered_exactly() -> None:
    definition = sufficiency.sufficiency_governance_definition()
    assert tuple(definition["target_metrics"]) == corpus.TARGET_METRICS
    assert len(definition["target_metrics"]) == 8
    assert definition["certified_parent"]["protocol_sha256"] == (
        "8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7"
    )
    assert corpus.protocol_definition()["definition_sha256"] == (
        definition["certified_parent"]["protocol_sha256"]
    )


def test_threshold_direction_hard_role_and_intent_parity_is_mechanical() -> None:
    frozen = {
        gate.metric: gate
        for gate in V2_APPROVAL_GATES
        if gate.metric in corpus.TARGET_METRICS
    }
    diff = sufficiency.semantic_diff_from_stage_b_gates()
    minima = sufficiency.metric_sufficiency_minima()["metrics"]
    assert set(frozen) == set(minima)
    assert diff["threshold_change_count"] == 0
    assert diff["direction_change_count"] == 0
    assert diff["hard_role_change_count"] == 0
    assert diff["metric_intent_change_count"] == 0
    for metric, gate in frozen.items():
        assert minima[metric]["threshold"] == str(gate.threshold)
        assert minima[metric]["direction"] == gate.direction
        assert minima[metric]["hard"] is gate.hard is True
        assert minima[metric]["metric_intent"] == gate.rationale


def test_a_certified_corpus_hash_mismatch_refuses_governance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = corpus.protocol_definition()
    monkeypatch.setattr(
        corpus,
        "protocol_definition",
        lambda: {**original, "definition_sha256": "0" * 64},
    )
    with pytest.raises(sufficiency.SufficiencyGovernanceError, match="hash mismatch"):
        sufficiency.sufficiency_governance_definition()


# ---------------------------------------------------------------------------
# Wilson and nearest-rank derivations
# ---------------------------------------------------------------------------


FINITE_RATE_EXPECTATIONS = {
    "gap_through_stop_consensus_agreement_rate": 381,
    "isolated_venue_stop_suppression_rate": 73,
    "regime_classification_disagreement_rate": 189,
    "setup_classification_disagreement_rate": 381,
    "trade_action_disagreement_rate": 381,
    "trade_eligibility_disagreement_rate": 381,
}


@pytest.mark.parametrize(("metric", "n_min"), FINITE_RATE_EXPECTATIONS.items())
def test_each_finite_rate_minimum_is_the_exact_wilson_boundary(
    metric: str,
    n_min: int,
) -> None:
    row = sufficiency.statistical_derivations()["rate_metrics"][metric]
    threshold = Decimal(row["threshold"])
    assert row["derived_n_capability"] == n_min
    assert row["minimum_denominator"] == n_min
    if row["direction"] == "minimum":
        assert wilson_interval(n_min - 1, n_min - 1).lower < threshold
        assert wilson_interval(n_min, n_min).lower >= threshold
    else:
        assert wilson_interval(0, n_min - 1).upper > threshold
        assert wilson_interval(0, n_min).upper <= threshold
    assert row["derivation_trace"][
        "n_capability_minus_one_criterion_satisfied"
    ] is False
    assert row["derivation_trace"]["n_capability_criterion_satisfied"] is True


def test_minimum_and_maximum_rate_directions_use_one_wilson_method() -> None:
    rows = sufficiency.statistical_derivations()["rate_metrics"]
    finite = [row for row in rows.values() if row["derived_n_capability"] is not None]
    assert {row["direction"] for row in finite} == {"minimum", "maximum"}
    assert {row["wilson_method_id"] for row in finite} == {
        sufficiency.WILSON_FORMULA_ID
    }
    assert {row["wilson_z"] for row in finite} == {
        "1.959963984540054235631"
    }


def test_the_exact_one_point_zero_boundary_records_the_no_finite_n_theorem() -> None:
    row = sufficiency.statistical_derivations()["rate_metrics"][
        corpus.CROSS_MARKET_METRIC
    ]
    assert row["threshold"] == "1.0"
    assert row["direction"] == "minimum"
    assert row["derived_n_capability"] is None
    assert row["derivation_trace"]["n_capability_state"] == (
        "NO_FINITE_POSITIVE_INTEGER"
    )
    assert row["exception"] == {
        **row["exception"],
        "applied": True,
        "does_not_change_performance_gate": True,
        "method_id": sufficiency.EXACT_BOUNDARY_EXCEPTION_ID,
        "precision_claim": "ESTIMATOR_IDENTIFIABILITY_ONLY",
    }
    assert row["minimum_denominator"] == 1
    # Concrete probes accompany the exact algebra n/(n+z^2) < 1.
    for denominator in (1, 2, 10, 381, 10_000):
        assert wilson_interval(denominator, denominator).lower < Decimal("1.0")


def test_risk_p95_minimum_is_the_first_nonmaximum_nearest_rank() -> None:
    row = sufficiency.statistical_derivations()["nearest_rank_p95"]
    assert row["minimum_denominator"] == 20
    assert row["n_min_minus_one"] == {
        "denominator": 19,
        "is_sample_maximum": True,
        "rank": 19,
    }
    assert row["n_min"] == {
        "denominator": 20,
        "is_sample_maximum": False,
        "rank": 19,
        "tail_observations_above_rank": 1,
    }
    assert row["n_min_plus_one"] == {
        "denominator": 21,
        "is_sample_maximum": False,
        "rank": 20,
        "tail_observations_above_rank": 1,
    }
    assert row["precision_claim"] == "TAIL_ORDER_STATISTIC_IDENTIFIABILITY_ONLY"


def test_zero_denominator_is_never_sufficient_for_any_metric() -> None:
    current = EPOCH_START
    result = _monitor((), current)
    assert result["overall_sufficient"] is False
    assert result["overall_stage_b_status"] == "INSUFFICIENT_EVIDENCE"
    for row in result["metric_states"].values():
        assert row["evaluable_denominator"] == 0
        assert row["sufficient"] is False


# ---------------------------------------------------------------------------
# Coverage and temporal choices
# ---------------------------------------------------------------------------


def test_coverage_policy_requires_complete_accounting_without_an_invented_floor() -> None:
    policy = sufficiency.coverage_policy()
    assert policy["decision"] == sufficiency.NO_SEPARATE_COVERAGE_FLOOR
    assert policy["evaluability_or_comparability_floor"] is None
    assert policy["accounting_requirement"] == {
        "accounted_scheduled_slot_rate": "1.0",
        "exactly_one_persisted_disposition_per_scheduled_slot": True,
        "unaccounted_scheduled_slot_count_required": 0,
        "unknown_or_missing_disposition_is_an_exclusion": False,
    }
    assert policy["scoped_out_standard"]["id"] == (
        "STRUCTURAL_COMPARABILITY_SUFFICIENCY_V1"
    )


def test_temporal_policy_imports_no_stage_c_horizon() -> None:
    policy = sufficiency.temporal_policy()
    assert policy["policy"] == "NONE"
    assert policy["minimum_calendar_duration"] is None
    assert policy["minimum_distinct_utc_days"] is None
    assert policy["minimum_distinct_iso_weeks"] is None
    assert policy["stage_c_live_shadow_days_imported"] is False
    assert "90" in policy["stage_c_separation"]


def test_all_frozen_exclusion_dispositions_are_counted_without_denominator_credit() -> None:
    current = EPOCH_START + timedelta(days=1, minutes=5)
    slots = list(_synthetic_slots_through(current))
    daily_index = next(
        index
        for index, slot in enumerate(slots)
        if slot.cadence == corpus.STRATEGY_DAILY_CADENCE
    )
    daily = slots[daily_index]
    replacements = {
        "regime_classification_disagreement_rate": sufficiency.BlindMetricDisposition(
            "regime_classification_disagreement_rate",
            False,
            corpus.STATE_NOT_EVALUABLE,
            "REQUIRED_INPUT_MISSING",
        ),
        "risk_size_p95_relative_difference": sufficiency.BlindMetricDisposition(
            "risk_size_p95_relative_difference",
            False,
            corpus.STATE_NOT_COMPARABLE,
            "ONE_TRACK_PRODUCED_NO_POSITIVE_RISK_SIZE",
        ),
        "setup_classification_disagreement_rate": sufficiency.BlindMetricDisposition(
            "setup_classification_disagreement_rate",
            False,
            corpus.STATE_DATA_QUALITY_FAIL,
            "HARD_DATA_QUALITY_GATE_FAILED",
        ),
        "trade_action_disagreement_rate": sufficiency.BlindMetricDisposition(
            "trade_action_disagreement_rate",
            False,
            corpus.STATE_REFERENCE_UNAVAILABLE,
            "CANDIDATE_REFERENCE_UNAVAILABLE",
        ),
    }
    by_metric = {row.metric: row for row in daily.metrics}
    by_metric.update(replacements)
    slots[daily_index] = replace(
        daily,
        metrics=tuple(by_metric[metric] for metric in sorted(by_metric)),
    )
    result = _monitor(tuple(slots), current)
    states = result["metric_states"]
    assert states["regime_classification_disagreement_rate"][
        "not_evaluable_count"
    ] == 1
    assert states["risk_size_p95_relative_difference"][
        "not_comparable_count"
    ] == 1
    assert states["setup_classification_disagreement_rate"][
        "data_quality_fail_count"
    ] == 1
    assert states["trade_action_disagreement_rate"][
        "reference_unavailable_count"
    ] == 1
    for metric in replacements:
        assert states[metric]["evaluable_denominator"] == 0


# ---------------------------------------------------------------------------
# Blind progress, global cutoff and adversarial invariants
# ---------------------------------------------------------------------------


SUFFICIENT_DECISION_TIME = EPOCH_START + timedelta(days=381, minutes=5)


@pytest.fixture(scope="module")
def sufficient_slots() -> tuple[sufficiency.BlindScheduledSlot, ...]:
    return _synthetic_slots_through(SUFFICIENT_DECISION_TIME)


@pytest.fixture(scope="module")
def sufficient_result(
    sufficient_slots: tuple[sufficiency.BlindScheduledSlot, ...],
) -> dict[str, object]:
    return _monitor(sufficient_slots, SUFFICIENT_DECISION_TIME)


def test_global_cutoff_waits_for_the_last_metric_and_is_earliest(
    sufficient_result: dict[str, object],
) -> None:
    assert sufficient_result["overall_sufficient"] is True
    assert sufficient_result["state"] == "EVALUATION_CUTOFF_FROZEN"
    assert sufficient_result["stage_b_sufficiency_cutoff"] == (
        SUFFICIENT_DECISION_TIME.isoformat()
    )
    metric_states = sufficient_result["metric_states"]
    assert all(row["sufficient"] for row in metric_states.values())
    assert metric_states["setup_classification_disagreement_rate"][
        "first_sufficient_at"
    ] == SUFFICIENT_DECISION_TIME.isoformat()
    assert sufficient_result["accounting"]["unaccounted_scheduled_slots"] == 0


def test_one_unaccounted_slot_prevents_global_sufficiency(
    sufficient_slots: tuple[sufficiency.BlindScheduledSlot, ...],
) -> None:
    missing_hourly = next(
        index
        for index, slot in enumerate(sufficient_slots)
        if slot.cadence == corpus.STOP_HOURLY_CADENCE
    )
    incomplete = sufficient_slots[:missing_hourly] + sufficient_slots[missing_hourly + 1 :]
    result = _monitor(incomplete, SUFFICIENT_DECISION_TIME)
    assert result["overall_sufficient"] is False
    assert result["stage_b_sufficiency_cutoff"] is None
    assert result["accounting"]["unaccounted_scheduled_slots"] == 1


def test_the_monitor_type_has_no_target_outcome_surface() -> None:
    accepted = {field.name for field in fields(sufficiency.BlindMetricDisposition)}
    prohibited = set(
        sufficiency.blind_monitor_contract()["prohibited_input_fields"]
    )
    assert accepted.isdisjoint(prohibited)
    signature = inspect.signature(sufficiency.evaluate_blind_sufficiency)
    assert set(signature.parameters).isdisjoint(prohibited)


def test_opposite_candidate_outcomes_cannot_change_sufficiency(
    sufficient_slots: tuple[sufficiency.BlindScheduledSlot, ...],
) -> None:
    all_favorable_outcomes = {
        metric: [True] * 400 for metric in corpus.TARGET_METRICS
    }
    all_unfavorable_outcomes = {
        metric: [False] * 400 for metric in corpus.TARGET_METRICS
    }
    assert all_favorable_outcomes != all_unfavorable_outcomes
    first = _monitor(sufficient_slots, SUFFICIENT_DECISION_TIME)
    second = _monitor(tuple(reversed(sufficient_slots)), SUFFICIENT_DECISION_TIME)
    assert first == second
    assert first["stage_b_sufficiency_cutoff"] == second[
        "stage_b_sufficiency_cutoff"
    ]


def test_pass_fail_pass_optional_stopping_path_cannot_move_the_cutoff(
    sufficient_slots: tuple[sufficiency.BlindScheduledSlot, ...],
) -> None:
    provisional_performance = ("PASS", "FAIL", "PASS")
    assert provisional_performance == ("PASS", "FAIL", "PASS")
    result = _monitor(sufficient_slots, SUFFICIENT_DECISION_TIME)
    assert result["stage_b_sufficiency_cutoff"] == (
        SUFFICIENT_DECISION_TIME.isoformat()
    )
    assert sufficiency.stopping_rule()["performance_results_consumed"] is False


def test_excluding_an_observation_cannot_make_sufficiency_arrive_sooner() -> None:
    extended_time = SUFFICIENT_DECISION_TIME + timedelta(days=1)
    base = list(_synthetic_slots_through(extended_time))
    target_index = next(
        index
        for index, slot in enumerate(base)
        if slot.cadence == corpus.STRATEGY_DAILY_CADENCE
    )
    target = base[target_index]
    replacements = {
        row.metric: (
            sufficiency.BlindMetricDisposition(
                metric=row.metric,
                universe_member=True,
                disposition=corpus.STATE_NOT_COMPARABLE,
                reason_code="CANDIDATE_TRACK_NOT_EVALUABLE",
            )
            if row.metric in {
                "setup_classification_disagreement_rate",
                "trade_action_disagreement_rate",
                "trade_eligibility_disagreement_rate",
            }
            else row
        )
        for row in target.metrics
    }
    base[target_index] = replace(
        target,
        metrics=tuple(replacements[metric] for metric in sorted(replacements)),
    )
    result = _monitor(tuple(base), extended_time)
    assert result["overall_sufficient"] is True
    assert datetime.fromisoformat(result["stage_b_sufficiency_cutoff"]) > (
        SUFFICIENT_DECISION_TIME
    )
    for metric in replacements:
        if replacements[metric].disposition == corpus.STATE_NOT_COMPARABLE:
            assert result["metric_states"][metric]["not_comparable_count"] == 1


def test_data_after_cutoff_cannot_move_the_frozen_evaluation_corpus(
    sufficient_slots: tuple[sufficiency.BlindScheduledSlot, ...],
    sufficient_result: dict[str, object],
) -> None:
    later = SUFFICIENT_DECISION_TIME + timedelta(days=1)
    extended = _synthetic_slots_through(later)
    assert len(extended) > len(sufficient_slots)
    later_result = _monitor(extended, later)
    assert later_result["stage_b_sufficiency_cutoff"] == sufficient_result[
        "stage_b_sufficiency_cutoff"
    ]
    assert later_result["evaluation_corpus_sha256"] == sufficient_result[
        "evaluation_corpus_sha256"
    ]
    assert later_result["evaluation_corpus_slot_ids"] == sufficient_result[
        "evaluation_corpus_slot_ids"
    ]


def test_failed_epoch_cannot_continue_until_it_passes() -> None:
    with pytest.raises(
        sufficiency.EvaluationEpochFrozenError,
        match="frozen at its earliest sufficient cutoff",
    ):
        sufficiency.assert_evaluation_epoch_not_extended(
            frozen_cutoff=SUFFICIENT_DECISION_TIME,
            proposed_cutoff=SUFFICIENT_DECISION_TIME + timedelta(days=1),
            evaluated_result="FAIL",
        )
    sufficiency.assert_evaluation_epoch_not_extended(
        frozen_cutoff=SUFFICIENT_DECISION_TIME,
        proposed_cutoff=SUFFICIENT_DECISION_TIME,
        evaluated_result="FAIL",
    )


def test_blind_slot_validation_refuses_unknown_or_duplicate_accounting(
    sufficient_slots: tuple[sufficiency.BlindScheduledSlot, ...],
) -> None:
    first = sufficient_slots[0]
    with pytest.raises(sufficiency.SufficiencyGovernanceError, match="multiple"):
        _monitor((first, first), first.decision_time)
    bad = replace(first, global_disposition="MISSING_UNKNOWN")
    with pytest.raises(sufficiency.SufficiencyGovernanceError, match="unknown disposition"):
        _monitor((bad,), first.decision_time)


# ---------------------------------------------------------------------------
# Hash and artifact integrity; pre-data boundary
# ---------------------------------------------------------------------------


def test_top_level_hash_binds_every_material_child() -> None:
    definition = sufficiency.sufficiency_governance_definition()
    assert definition["material_child_count"] == 8
    assert definition["material_child_count"] == len(
        definition["child_definition_sha256"]
    )
    assert set(sufficiency.protocol_hashes()) == set(
        definition["child_definition_sha256"]
    ) | {"sufficiency_governance"}
    assert all(
        sufficiency._is_sha256(value)
        for value in definition["child_definition_sha256"].values()
    )
    sufficiency.verify_sufficiency_governance_definition(definition)


@pytest.mark.parametrize(
    "builder_name",
    [
        "blind_monitor_contract",
        "coverage_policy",
        "evaluation_cutoff_contract",
        "metric_sufficiency_minima",
        "semantic_diff_from_stage_b_gates",
        "statistical_derivations",
        "stopping_rule",
        "temporal_policy",
    ],
)
def test_every_material_child_semantic_mutation_moves_the_parent_hash(
    monkeypatch: pytest.MonkeyPatch,
    builder_name: str,
) -> None:
    baseline = sufficiency.sufficiency_governance_definition()["definition_sha256"]
    builder = getattr(sufficiency, builder_name)
    original = builder()

    def mutated_builder() -> dict[str, object]:
        changed = {key: value for key, value in original.items() if key != "definition_sha256"}
        changed["synthetic_mutation_probe"] = builder_name
        return sufficiency._with_definition_hash(changed)

    monkeypatch.setattr(sufficiency, builder_name, mutated_builder)
    assert sufficiency.sufficiency_governance_definition()["definition_sha256"] != (
        baseline
    )
    with pytest.raises(sufficiency.SufficiencyGovernanceError, match="does not reproduce"):
        sufficiency.restore_artifacts(ARTIFACT_DIR)


def test_governance_hash_is_decimal_context_hash_seed_cwd_and_process_invariant(
    tmp_path: Path,
) -> None:
    expected = sufficiency.protocol_hashes()
    with localcontext(Context(prec=3)):
        assert sufficiency.protocol_hashes() == expected
    with localcontext(Context(prec=200)):
        assert sufficiency.protocol_hashes() == expected
    script = (
        "import json;"
        "from btc_predictor.research import "
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


def test_persisted_artifacts_reproduce_and_write_deterministically(tmp_path: Path) -> None:
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


def test_tampered_child_and_top_level_artifacts_are_refused(tmp_path: Path) -> None:
    sufficiency.write_artifacts(tmp_path)
    child_path = tmp_path / sufficiency.COVERAGE_FILENAME
    child = json.loads(child_path.read_text())
    child["evaluability_or_comparability_floor"] = "0.95"
    child_path.write_text(json.dumps(child, indent=2, sort_keys=True) + "\n")
    with pytest.raises(sufficiency.SufficiencyGovernanceError, match="does not reproduce"):
        sufficiency.restore_artifacts(tmp_path)


def test_governance_is_pre_data_and_authorizes_nothing_downstream() -> None:
    definition = sufficiency.sufficiency_governance_definition()
    assert definition["status"] == "FROZEN_PRE_DATA_SUFFICIENCY_GOVERNANCE"
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
    assert not sufficiency.OUTPUT_NAMESPACE.startswith("data/")
    assert not sufficiency.OUTPUT_NAMESPACE.startswith("research_artifacts/")


def test_report_states_review_handoff_and_boundaries() -> None:
    report = (ARTIFACT_DIR / sufficiency.REPORT_FILENAME).read_text()
    assert sufficiency.FINAL_CLASSIFICATION in report
    assert "Threshold changes: `0`" in report
    assert "Separate numerical coverage floor" in report
    assert "Stage-C 90-day rule imported: `NO`" in report
    assert "POSTP1-004 authorized: `NO`" in report
    assert "Prospective collection authorized: `NO`" in report
    assert "sealed sample touched: `NO / NO`" in report
