"""BTC_REFERENCE_COMPOSITE_V3 gate-architecture convergence and freeze regressions.

Three things must be impossible here.

A demoted metric must not be able to reject a candidate through a side door:
diagnostics and the soft gate are not parameters of the approval verdict at
all, and the tests prove that by moving them and watching the verdict stand
still.

Evidence that is not there must not read as agreement. A zero denominator, a
thin denominator, a missing required pair and a pair below the comparability
floor all have to travel as insufficient and fail closed -- never as a pass and
never as a rate of 0.0.

And no correlated pair observation may be multiplied into false precision. The
approval rule is a deterministic conjunction over an enumerated pair set, the
confidence bound is a per-pair statement about one pair's own counts, and the
tests pin both, including under the unequal denominators the predecessor's
scalar minimum could not survive.

The freeze itself is pinned by hash, and the sealed 2015-2019 sample is neither
collected nor opened by any path reachable from this module.
"""

import decimal
import json
import os
import shutil
import subprocess
import sys
from decimal import Context, Decimal
from pathlib import Path

import pytest

from btc_predictor.research.cross_provider_structure_comparison import (
    AFFECTED_V2_GATE_METRICS,
    COMPARISON_CONTRACT_VERSION,
)
from btc_predictor.research.reference_composite_v2 import (
    FROZEN_V2_DEFINITION_SHA256,
    UNTOUCHED_OOS_END,
    UNTOUCHED_OOS_START,
    UntouchedValidationSampleGuardError,
    guard_untouched_validation_sample,
)
from btc_predictor.research.structural_threshold_calibration import (
    PAIR_ADMISSIBLE,
    PAIR_INADMISSIBLE,
    PAIR_UNDEFINED_INSUFFICIENT_EVIDENCE,
    wilson_interval,
)
from btc_predictor.research.reference_composite_v3_convergence import (
    AGGREGATION_ID,
    CERTIFICATION_REASON_BELOW_COMPARABILITY_FLOOR,
    CERTIFICATION_REASON_BOUND_EXCEEDS_LIMIT,
    CERTIFICATION_REASON_NO_COMPARABLE_EVENTS,
    CERTIFICATION_REASON_PAIR_INADMISSIBLE,
    CERTIFICATION_REASON_RATE_EXCEEDS_LIMIT,
    CERTIFICATION_REASON_REQUIRED_PAIR_ABSENT,
    CERTIFICATION_RULE_ID,
    COMPARABILITY_FLOOR,
    CONFIDENCE_LEVELS,
    CONVERGENCE_OUTPUT_NAMESPACE,
    CONVERGENCE_RECORD_FILENAME,
    CONVERGENCE_REPORT_FILENAME,
    CONVERGENCE_SCHEMA_VERSION,
    CONVERGENCE_VERSION,
    DERIVED_LEVEL_PROTECTION_ID,
    FINAL_GATE_ROLES,
    GATE_FAIL,
    GATE_INSUFFICIENT,
    GATE_PASS,
    GUARD_FAILED,
    GUARD_SATISFIED,
    GUARD_UNDEFINED,
    INHERITED_TIER4_HARD_GATES,
    MATERIALITY_POLICY_ID,
    NORMAL_QUANTILE_0_975,
    PAIR_CERTIFIED,
    PAIR_INSUFFICIENT_EVIDENCE,
    PAIR_MATERIAL_FAILURE,
    REVIEW_FINDING_MINIMUM_N_INVALID,
    REVIEW_FINDING_NESTED_STRUCTURAL_STATE,
    REVIEW_FINDING_REDUNDANT_WITHIN_N,
    REVIEW_FINDING_RELATIVE_ALTERNATIVE_DEGENERATE,
    ROLE_DIAGNOSTIC,
    ROLE_HARD,
    ROLE_SOFT,
    SOFT_OUTCOME_OK,
    SOFT_OUTCOME_REVIEW_REQUIRED,
    STRUCTURAL_MATERIALITY_LIMIT,
    TRANSFER_GUARD_ID,
    UNREVIEWED_DERIVED_LEVEL_METRIC,
    V3_FROZEN_READY,
    V3_FROZEN_STATUS,
    V3_PROTOCOL_FILENAME,
    V3_PROTOCOL_SCHEMA_VERSION,
    V3_PROTOCOL_VERSION,
    V3ConvergenceError,
    approval_verdict,
    architecture_comparison,
    build_convergence_record,
    certify_pair,
    convergence_markdown,
    evaluate_hard_structural_gate,
    evaluate_soft_gate,
    evaluate_transfer_guard,
    gate_architecture,
    gate_viability,
    measured_evidence,
    minimum_certifying_denominator,
    restore_convergence_record,
    restore_v3_protocol,
    sealed_window_guard_holds,
    v3_definition_sha256,
    v3_protocol_definition,
    verify_convergence_artifacts,
    wilson_upper_bound,
    write_convergence_artifacts,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

# The architecture this task converged on, retyped so a silent change in the
# module breaks a test rather than quietly moving a governance conclusion.
EXPECTED_ROLES = {
    "exact_timestamp_swing_disagreement_rate": ROLE_SOFT,
    "within_1_week_swing_disagreement_rate": ROLE_DIAGNOSTIC,
    "within_2_week_swing_disagreement_rate": ROLE_DIAGNOSTIC,
    "structural_state_disagreement_rate": ROLE_HARD,
    "breakout_disagreement_rate": ROLE_DIAGNOSTIC,
    "reclaim_disagreement_rate": ROLE_DIAGNOSTIC,
}

_REQUIRED = ("candidate_vs_bitfinex", "candidate_vs_bitstamp", "candidate_vs_coinbase")

# Everything the frozen protocol reads. No collected history appears, so the
# definition cannot depend on a sample.
_PROTOCOL_INPUTS = (
    "research_artifacts",
    "btc_predictor/research/reference_composite_empirical.py",
    "btc_predictor/research/btc019b_diagnostics.py",
)


def _isolated_root(destination: Path) -> Path:
    for relative in _PROTOCOL_INPUTS:
        source = REPOSITORY_ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    return destination


def _pair(numerator: int, denominator: int, **overrides) -> dict:
    row = {
        "numerator": numerator,
        "denominator": denominator,
        "structural_comparability_rate": "1",
        "state": PAIR_ADMISSIBLE,
    }
    row.update(overrides)
    return row


def _clean_pairs(denominator: int = 40) -> dict:
    return {name: _pair(0, denominator) for name in _REQUIRED}


@pytest.fixture(scope="module")
def protocol() -> dict:
    return v3_protocol_definition(REPOSITORY_ROOT)


@pytest.fixture(scope="module")
def record() -> dict:
    return build_convergence_record(REPOSITORY_ROOT)


@pytest.fixture(scope="module")
def measured() -> dict:
    return measured_evidence(REPOSITORY_ROOT)


# =============================================================================
# Stage 1 -- the review findings are reverified, not assumed
# =============================================================================


def test_within_n_is_numerically_identical_to_exact_timestamp(record: dict) -> None:
    finding = record["verified_review_findings"]["findings"][
        REVIEW_FINDING_REDUNDANT_WITHIN_N
    ]
    assert finding["measurement_count"] == 12
    assert finding["distinguishing_measurement_count"] == 0
    assert finding["merged_pair_total"] == 0
    assert all(row["identical_to_exact_timestamp"] for row in finding["measurements"])


def test_structural_state_is_a_strict_subset_of_exact_timestamp(record: dict) -> None:
    finding = record["verified_review_findings"]["findings"][
        REVIEW_FINDING_NESTED_STRUCTURAL_STATE
    ]
    assert finding["violation_count"] == 0
    assert finding["strictly_smaller_measurement_count"] >= 1
    for row in finding["measurements"]:
        assert row["subset"]
        assert row["structural_state_numerator"] <= row["exact_numerator"]


def test_the_relative_alternative_cannot_identify_a_zero_numerator_metric(
    record: dict,
) -> None:
    finding = record["verified_review_findings"]["findings"][
        REVIEW_FINDING_RELATIVE_ALTERNATIVE_DEGENERATE
    ]
    band = Decimal(finding["expected_count_limit_under_band"])
    alternative = Decimal(finding["expected_count_limit_under_alternative"])
    # z^2 / 6 and three times it: the per-pair expected counts converge there
    # whatever the denominator, so no test can separate the two hypotheses.
    assert band.quantize(Decimal("0.0001")) == Decimal("0.6402")
    assert alternative.quantize(Decimal("0.0001")) == Decimal("1.9207")
    counts = [Decimal(row["expected_count_under_band"]) for row in finding["probes"]]
    assert counts == sorted(counts)
    assert all(count < band for count in counts)


def test_the_scalar_minimum_does_not_carry_to_unequal_denominators(
    record: dict,
) -> None:
    finding = record["verified_review_findings"]["findings"][
        REVIEW_FINDING_MINIMUM_N_INVALID
    ]
    assert not finding["scalar_minimum_holds_at_every_probe"]
    assert not finding["power_is_monotone_in_the_denominator"]
    failures = [
        row
        for row in finding["probes"]
        if row["all_denominators_at_or_above_minimum"]
        and not row["meets_declared_power"]
    ]
    assert failures, "the published minima must be shown to fail somewhere"


def test_a_refuted_review_finding_would_stop_the_convergence(monkeypatch) -> None:
    from btc_predictor.research import reference_composite_v3_convergence as module

    for name, finding in (
        ("verify_within_n_redundancy", REVIEW_FINDING_REDUNDANT_WITHIN_N),
        ("verify_structural_state_nesting", REVIEW_FINDING_NESTED_STRUCTURAL_STATE),
    ):
        monkeypatch.setattr(
            module,
            name,
            lambda measured, finding=finding: {
                "finding": finding,
                "verdict": "REFUTED_BY_INDEPENDENT_RECOMPUTATION",
            },
        )
    monkeypatch.setattr(
        module,
        "verify_relative_alternative_degeneracy",
        lambda: {"verdict": module.FINDING_CONFIRMED},
    )
    monkeypatch.setattr(
        module,
        "verify_minimum_n_invalidity",
        lambda: {"verdict": module.FINDING_CONFIRMED},
    )
    with pytest.raises(V3ConvergenceError, match="refutes"):
        module.verified_review_findings({})


# =============================================================================
# Gate roles
# =============================================================================


def test_the_final_roles_are_exactly_pinned(record: dict) -> None:
    assert FINAL_GATE_ROLES == EXPECTED_ROLES
    assert {item["metric"]: item["role"] for item in record["gate_architecture"]} == (
        EXPECTED_ROLES
    )
    assert sorted(EXPECTED_ROLES) == sorted(AFFECTED_V2_GATE_METRICS)


def test_every_metric_carries_exactly_one_role() -> None:
    roles = [item["role"] for item in gate_architecture()]
    assert len(roles) == len(AFFECTED_V2_GATE_METRICS)
    assert set(roles) <= {ROLE_HARD, ROLE_SOFT, ROLE_DIAGNOSTIC}


def test_every_classification_answers_the_four_required_questions() -> None:
    for item in gate_architecture():
        assert item["protects_against"]
        assert isinstance(item["covered_by_another_gate"], bool)
        assert item["coverage_reasoning"]
        assert isinstance(item["statistically_supportable"], bool)
        assert item["support_reasoning"]
        assert isinstance(item["removing_the_hard_veto_would_weaken_protection"], bool)
        assert item["weakening_reasoning"]
        assert item["reason_codes"]


def test_a_hard_gate_does_veto() -> None:
    failing = {**_clean_pairs(), "candidate_vs_bitstamp": _pair(20, 40)}
    gate = evaluate_hard_structural_gate(failing, required_pairs=_REQUIRED)
    assert gate["verdict"] == GATE_FAIL
    verdict = approval_verdict(
        hard_gate=gate,
        transfer_guard={"outcome": GUARD_SATISFIED},
        comparability_satisfied=True,
        unreviewed_derived_level_disagreement_count=0,
        tier4_hard_gates_passed=True,
    )
    assert verdict["verdict"] == GATE_FAIL


def test_a_soft_gate_cannot_independently_veto() -> None:
    warning = evaluate_soft_gate(
        {**_clean_pairs(), "candidate_vs_bitstamp": _pair(20, 40)},
        required_pairs=_REQUIRED,
    )
    assert warning["outcome"] == SOFT_OUTCOME_REVIEW_REQUIRED
    assert warning["cannot_reject_alone"]
    assert not warning["contributes_to_the_approval_verdict"]
    verdict = approval_verdict(
        hard_gate=evaluate_hard_structural_gate(
            _clean_pairs(), required_pairs=_REQUIRED
        ),
        transfer_guard={"outcome": GUARD_SATISFIED},
        comparability_satisfied=True,
        unreviewed_derived_level_disagreement_count=0,
        tier4_hard_gates_passed=True,
    )
    assert verdict["verdict"] == GATE_PASS


def test_a_diagnostic_cannot_veto_by_any_route() -> None:
    # The verdict takes hard evidence only, so no diagnostic value is even
    # expressible as an input to it.
    import inspect

    parameters = set(inspect.signature(approval_verdict).parameters)
    assert parameters == {
        "hard_gate",
        "transfer_guard",
        "comparability_satisfied",
        "unreviewed_derived_level_disagreement_count",
        "tier4_hard_gates_passed",
    }
    for metric, role in FINAL_GATE_ROLES.items():
        if role is ROLE_DIAGNOSTIC:
            assert metric not in parameters


def test_a_diagnostic_metric_carries_no_threshold(protocol: dict) -> None:
    architecture = protocol["gate_architecture"]
    assert set(architecture["diagnostic_metrics"]) == {
        metric for metric, role in EXPECTED_ROLES.items() if role is ROLE_DIAGNOSTIC
    }
    assert not protocol["diagnostic_semantics"]["can_veto_approval"]
    assert protocol["diagnostic_semantics"]["required_fields"]


def test_the_soft_gate_semantics_are_not_vague(protocol: dict) -> None:
    semantics = protocol["soft_gate_semantics"]
    assert semantics["warning_only"]
    assert semantics["cannot_reject_a_candidate_alone"]
    assert not semantics["contributes_to_the_approval_verdict"]
    assert semantics["manual_review_trigger"]
    assert semantics["evidence_annotation"]
    assert semantics["outcome_when_undefined"] == SOFT_OUTCOME_REVIEW_REQUIRED


def test_the_soft_gate_is_ok_only_when_every_pair_is_defined_and_under_the_limit() -> None:
    assert (
        evaluate_soft_gate(_clean_pairs(), required_pairs=_REQUIRED)["outcome"]
        == SOFT_OUTCOME_OK
    )
    missing = {name: _pair(0, 40) for name in _REQUIRED[:2]}
    assert (
        evaluate_soft_gate(missing, required_pairs=_REQUIRED)["outcome"]
        == SOFT_OUTCOME_REVIEW_REQUIRED
    )
    empty = {**_clean_pairs(), "candidate_vs_bitstamp": _pair(0, 0)}
    assert (
        evaluate_soft_gate(empty, required_pairs=_REQUIRED)["outcome"]
        == SOFT_OUTCOME_REVIEW_REQUIRED
    )


# =============================================================================
# Dependence
# =============================================================================


def test_no_pair_survival_probability_is_multiplied(record: dict, protocol: dict) -> None:
    for holder in (record["dependence_treatment"], protocol["dependence_treatment"]):
        assert not holder["family_wise_probability_multiplied"]
        assert not holder["pair_independence_assumed"]
        assert holder["within_pair_disclosure"]
        assert len(holder["assumptions_removed"]) == 2
    source = (
        REPOSITORY_ROOT
        / "btc_predictor/research/reference_composite_v3_convergence.py"
    ).read_text()
    assert "family_failure_probability" in source  # only to reverify the old defect
    assert "policy_conclusion_stable" in source


def test_the_aggregation_is_a_deterministic_conjunction(protocol: dict) -> None:
    aggregation = protocol["gate_architecture"]["aggregation"]
    assert aggregation["aggregation_id"] == AGGREGATION_ID
    assert "every required pair must certify" in aggregation["rule"].lower()
    assert "multiplied" in aggregation["rule"]


def test_all_required_gate_pairs_are_explicit(protocol: dict) -> None:
    universe = protocol["gate_pair_universe"]
    assert universe["required_gate_pair_count"] == 3
    assert len(universe["gate_pairs"]) == 3
    assert all("MEDIAN_OHLC_V2" in pair for pair in universe["gate_pairs"])
    assert len(universe["calibration_pairs"]) == 3
    assert all("MEDIAN_OHLC_V2" not in pair for pair in universe["calibration_pairs"])


def test_one_failing_required_pair_fails_the_gate() -> None:
    pairs = {**_clean_pairs(), "candidate_vs_coinbase": _pair(15, 40)}
    assert (
        evaluate_hard_structural_gate(pairs, required_pairs=_REQUIRED)["verdict"]
        == GATE_FAIL
    )


def test_one_undefined_required_pair_is_insufficient_evidence() -> None:
    pairs = {name: _pair(0, 40) for name in _REQUIRED[:2]}
    gate = evaluate_hard_structural_gate(pairs, required_pairs=_REQUIRED)
    assert gate["verdict"] == GATE_INSUFFICIENT
    absent = [
        row
        for row in gate["pairs"]
        if CERTIFICATION_REASON_REQUIRED_PAIR_ABSENT in row["reason_codes"]
    ]
    assert len(absent) == 1


def test_a_material_failure_outranks_missing_evidence() -> None:
    pairs = {"candidate_vs_bitstamp": _pair(20, 40)}
    assert (
        evaluate_hard_structural_gate(pairs, required_pairs=_REQUIRED)["verdict"]
        == GATE_FAIL
    )


def test_pair_order_cannot_change_a_gate_verdict() -> None:
    pairs = {
        "candidate_vs_bitfinex": _pair(1, 40),
        "candidate_vs_bitstamp": _pair(0, 40),
        "candidate_vs_coinbase": _pair(2, 40),
    }
    forward = evaluate_hard_structural_gate(pairs, required_pairs=_REQUIRED)
    backward = evaluate_hard_structural_gate(
        dict(reversed(list(pairs.items()))), required_pairs=tuple(reversed(_REQUIRED))
    )
    assert forward == backward


# =============================================================================
# Comparability
# =============================================================================


def test_zero_candidates_and_zero_comparable_events_are_insufficient() -> None:
    for row in (_pair(0, 0), _pair(0, 0, structural_comparability_rate=None)):
        certification = certify_pair(row, comparison_id="x")
        assert certification.outcome == PAIR_INSUFFICIENT_EVIDENCE
        assert CERTIFICATION_REASON_NO_COMPARABLE_EVENTS in certification.reason_codes
        assert certification.rate is None
        assert certification.upper_bound is None


def test_below_the_comparability_floor_cannot_certify() -> None:
    certification = certify_pair(
        _pair(0, 40, structural_comparability_rate="0.49"), comparison_id="x"
    )
    assert certification.outcome == PAIR_INSUFFICIENT_EVIDENCE
    assert CERTIFICATION_REASON_BELOW_COMPARABILITY_FLOOR in certification.reason_codes


def test_at_the_comparability_floor_certifies() -> None:
    certification = certify_pair(
        _pair(0, 40, structural_comparability_rate=str(COMPARABILITY_FLOOR)),
        comparison_id="x",
    )
    assert certification.outcome == PAIR_CERTIFIED


def test_above_the_comparability_floor_certifies() -> None:
    certification = certify_pair(
        _pair(0, 40, structural_comparability_rate="0.51"), comparison_id="x"
    )
    assert certification.outcome == PAIR_CERTIFIED


def test_an_inadmissible_pair_cannot_certify() -> None:
    for state in (PAIR_INADMISSIBLE, PAIR_UNDEFINED_INSUFFICIENT_EVIDENCE):
        certification = certify_pair(_pair(0, 40, state=state), comparison_id="x")
        assert certification.outcome == PAIR_INSUFFICIENT_EVIDENCE
        assert CERTIFICATION_REASON_PAIR_INADMISSIBLE in certification.reason_codes


def test_unequal_denominators_are_judged_pair_by_pair() -> None:
    pairs = {
        "candidate_vs_bitfinex": _pair(0, 16),
        "candidate_vs_bitstamp": _pair(0, 60),
        "candidate_vs_coinbase": _pair(0, 200),
    }
    gate = evaluate_hard_structural_gate(pairs, required_pairs=_REQUIRED)
    assert gate["verdict"] == GATE_PASS
    thin = {**pairs, "candidate_vs_bitfinex": _pair(0, 15)}
    assert (
        evaluate_hard_structural_gate(thin, required_pairs=_REQUIRED)["verdict"]
        == GATE_INSUFFICIENT
    )


def test_the_comparability_policy_is_hard_and_fails_closed(protocol: dict) -> None:
    policy = protocol["comparability_policy"]
    assert policy["hard"]
    assert policy["floor"] == str(COMPARABILITY_FLOOR)
    assert policy["required_gate_pair_count"] == 3
    assert "never" in policy["zero_comparable_behaviour"].lower()
    assert policy["invariant"].startswith("insufficient evidence can never approve")
    assert policy["principle"] and policy["why_not_higher"] and policy["why_not_lower"]
    for field in (
        "candidate_event_count",
        "comparable_event_count",
        "not_comparable_event_count",
        "structural_comparability_rate",
    ):
        assert field in policy["required_evidence"]


def test_insufficient_evidence_can_never_approve() -> None:
    gate = evaluate_hard_structural_gate(_clean_pairs(15), required_pairs=_REQUIRED)
    assert gate["verdict"] == GATE_INSUFFICIENT
    verdict = approval_verdict(
        hard_gate=gate,
        transfer_guard={"outcome": GUARD_SATISFIED},
        comparability_satisfied=True,
        unreviewed_derived_level_disagreement_count=0,
        tier4_hard_gates_passed=True,
    )
    assert verdict["verdict"] == GATE_INSUFFICIENT


# =============================================================================
# Threshold
# =============================================================================


def test_below_at_and_above_the_materiality_limit() -> None:
    limit = STRUCTURAL_MATERIALITY_LIMIT
    below = certify_pair(_pair(19, 100), comparison_id="x", limit=limit)
    exactly = certify_pair(_pair(20, 100), comparison_id="x", limit=limit)
    above = certify_pair(_pair(21, 100), comparison_id="x", limit=limit)
    assert below.rate < limit and exactly.rate == limit and above.rate > limit
    # Equality is not a failure; only a strictly greater rate is.
    assert below.outcome != PAIR_MATERIAL_FAILURE
    assert exactly.outcome != PAIR_MATERIAL_FAILURE
    assert above.outcome == PAIR_MATERIAL_FAILURE
    assert CERTIFICATION_REASON_RATE_EXCEEDS_LIMIT in above.reason_codes


def test_the_bound_and_not_only_the_point_rate_decides_a_pass() -> None:
    # 2/28 has a point rate of 0.0714, far under the limit, but its 95% upper
    # bound is 0.2265: the evidence does not exclude a material rate.
    certification = certify_pair(_pair(2, 28), comparison_id="x")
    assert certification.rate < STRUCTURAL_MATERIALITY_LIMIT
    assert certification.upper_bound > STRUCTURAL_MATERIALITY_LIMIT
    assert certification.outcome == PAIR_INSUFFICIENT_EVIDENCE
    assert CERTIFICATION_REASON_BOUND_EXCEEDS_LIMIT in certification.reason_codes


def test_an_upper_bound_exactly_at_the_limit_certifies() -> None:
    bound = wilson_upper_bound(0, 16)
    assert bound <= STRUCTURAL_MATERIALITY_LIMIT
    assert certify_pair(_pair(0, 16), comparison_id="x").outcome == PAIR_CERTIFIED
    assert (
        certify_pair(_pair(0, 15), comparison_id="x").outcome
        == PAIR_INSUFFICIENT_EVIDENCE
    )


def test_the_minimum_certifying_denominator_matches_the_bound() -> None:
    for count in range(4):
        size = minimum_certifying_denominator(
            count, limit=STRUCTURAL_MATERIALITY_LIMIT
        )
        assert wilson_upper_bound(count, size) <= STRUCTURAL_MATERIALITY_LIMIT
        assert wilson_upper_bound(count, size - 1) > STRUCTURAL_MATERIALITY_LIMIT


def test_the_bound_reproduces_the_predecessor_implementation() -> None:
    for numerator, denominator in ((0, 5), (1, 26), (2, 28), (3, 41), (7, 156)):
        assert wilson_upper_bound(numerator, denominator) == wilson_interval(
            numerator, denominator
        ).upper


def test_the_bound_refuses_impossible_counts() -> None:
    with pytest.raises(V3ConvergenceError):
        wilson_upper_bound(-1, 10)
    with pytest.raises(V3ConvergenceError):
        wilson_upper_bound(11, 10)
    assert wilson_upper_bound(0, 0) is None


def test_the_materiality_limit_is_absolute_and_not_relative(protocol: dict) -> None:
    materiality = protocol["materiality"]
    assert materiality["policy_id"] == MATERIALITY_POLICY_ID
    assert materiality["absolute_limit"] == "0.20"
    assert not materiality["relative_alternative_retained"]
    assert len(materiality["derivation"]) == 5
    grounds = {item["ground"] for item in materiality["derivation"]}
    assert "strategy impact" in grounds
    assert "Phase-1 tolerance philosophy" in grounds
    refused = {item["derivation"] for item in materiality["refused_derivations"]}
    assert any("maximum observed" in item for item in refused)
    assert any("multiple of the observed" in item for item in refused)
    assert any("candidate pass" in item for item in refused)


def test_the_limit_is_realistic_but_was_not_chosen_from_the_observations(
    record: dict,
) -> None:
    check = record["realism_check"]
    assert check["conclusion"] == "REALISTIC"
    assert check["measurements_exceeding_the_limit"] == []
    assert check["attainable"]
    # Every legitimate provider pair sits under the limit, and the worst is
    # well under it -- but the limit is declared, not fitted, so it is not the
    # worst observation plus an epsilon.
    assert Decimal(check["worst_pair_rate"]) < STRUCTURAL_MATERIALITY_LIMIT
    assert Decimal(check["worst_pair_rate"]) != STRUCTURAL_MATERIALITY_LIMIT


# =============================================================================
# Diagnostics
# =============================================================================


def test_every_diagnostic_is_recorded_for_every_pair(record: dict) -> None:
    for metric in (
        "within_1_week_swing_disagreement_rate",
        "within_2_week_swing_disagreement_rate",
        "breakout_disagreement_rate",
        "reclaim_disagreement_rate",
    ):
        dispersion = record["development_dispersion"][metric]
        assert len(dispersion["measurements"]) == 6
        for row in dispersion["measurements"]:
            assert row["comparison_id"]
            assert row["denominator"] is not None
            assert row["numerator"] is not None
            assert row["admissibility"]


def test_within_n_diagnostics_record_their_matched_pairs(measured: dict) -> None:
    for metric in (
        "within_1_week_swing_disagreement_rate",
        "within_2_week_swing_disagreement_rate",
    ):
        for sample_dir in measured[metric]:
            for row in measured[metric][sample_dir]:
                assert "matched_pair_count" in row
                assert row["not_comparable_reason_counts"]


def test_a_tampered_diagnostic_cannot_change_an_approval_verdict() -> None:
    baseline = approval_verdict(
        hard_gate=evaluate_hard_structural_gate(
            _clean_pairs(), required_pairs=_REQUIRED
        ),
        transfer_guard={"outcome": GUARD_SATISFIED},
        comparability_satisfied=True,
        unreviewed_derived_level_disagreement_count=0,
        tier4_hard_gates_passed=True,
    )
    assert baseline["verdict"] == GATE_PASS
    assert baseline["inputs_are_hard_evidence_only"]
    with pytest.raises(TypeError):
        approval_verdict(  # type: ignore[call-arg]
            hard_gate=evaluate_hard_structural_gate(
                _clean_pairs(), required_pairs=_REQUIRED
            ),
            transfer_guard={"outcome": GUARD_SATISFIED},
            comparability_satisfied=True,
            unreviewed_derived_level_disagreement_count=0,
            tier4_hard_gates_passed=True,
            breakout_disagreement_rate=Decimal("0.99"),
        )


# =============================================================================
# The transfer guard
# =============================================================================


def _guard_pairs(rows: dict[str, dict] | None = None) -> dict:
    base = {
        "bitfinex_vs_bitstamp": _pair(0, 40),
        "bitfinex_vs_coinbase": _pair(0, 40),
        "bitstamp_vs_coinbase": _pair(0, 40),
    }
    base.update(rows or {})
    return base


def test_the_guard_is_satisfied_when_every_provider_pair_certifies() -> None:
    guard = evaluate_transfer_guard(_guard_pairs())
    assert guard["outcome"] == GUARD_SATISFIED
    assert guard["required_pair_count"] == 3
    assert guard["guard_id"] == TRANSFER_GUARD_ID


def test_the_guard_fails_when_raw_providers_disperse_materially() -> None:
    guard = evaluate_transfer_guard(
        _guard_pairs({"bitfinex_vs_bitstamp": _pair(20, 40)})
    )
    assert guard["outcome"] == GUARD_FAILED


def test_the_guard_is_undefined_on_thin_or_missing_provider_evidence() -> None:
    assert (
        evaluate_transfer_guard(_guard_pairs({"bitfinex_vs_bitstamp": _pair(0, 10)}))[
            "outcome"
        ]
        == GUARD_UNDEFINED
    )
    assert evaluate_transfer_guard({})["outcome"] == GUARD_UNDEFINED


def test_a_failed_or_undefined_guard_blocks_approval() -> None:
    passing = evaluate_hard_structural_gate(_clean_pairs(), required_pairs=_REQUIRED)
    assert (
        approval_verdict(
            hard_gate=passing,
            transfer_guard={"outcome": GUARD_FAILED},
            comparability_satisfied=True,
            unreviewed_derived_level_disagreement_count=0,
            tier4_hard_gates_passed=True,
        )["verdict"]
        == GATE_FAIL
    )
    assert (
        approval_verdict(
            hard_gate=passing,
            transfer_guard={"outcome": GUARD_UNDEFINED},
            comparability_satisfied=True,
            unreviewed_derived_level_disagreement_count=0,
            tier4_hard_gates_passed=True,
        )["verdict"]
        == GATE_INSUFFICIENT
    )


def test_the_guard_never_reads_a_candidate_pair(protocol: dict) -> None:
    guard = protocol["transfer_guard"]
    assert not guard["depends_on_the_candidate"]
    assert guard["hard"]
    assert guard["computed_on"] == "INDEPENDENT_RAW_PROVIDER_PAIRS_V1"
    assert guard["failure_mode_blocked"]
    assert guard["why_not_leave_one_provider_influence"]
    evaluated = evaluate_transfer_guard(
        {**_guard_pairs(), "candidate_vs_bitstamp": _pair(40, 40)}
    )
    # A candidate pair in the input cannot reach the guard's verdict.
    assert evaluated["outcome"] == GUARD_SATISFIED
    assert all("MEDIAN_OHLC_V2" not in row["comparison_id"] for row in evaluated["pairs"])


# =============================================================================
# Derived-level protection
# =============================================================================


def test_derived_level_protection_survives_the_demotion(protocol: dict) -> None:
    protection = protocol["derived_level_protection"]
    assert protection["protection_id"] == DERIVED_LEVEL_PROTECTION_ID
    hard = [item for item in protection["components"] if item["hard"]]
    assert len(hard) == 4
    metrics = {
        metric
        for item in protection["components"]
        for metric in item.get("metrics", [])
    }
    assert set(INHERITED_TIER4_HARD_GATES) <= metrics
    assert "stop_touch_disagreement_rate" in metrics
    assert "mfe_median_absolute_difference" in metrics
    assert "mae_p95_absolute_difference" in metrics


def test_an_unreviewed_derived_level_disagreement_blocks_approval() -> None:
    passing = evaluate_hard_structural_gate(_clean_pairs(), required_pairs=_REQUIRED)
    blocked = approval_verdict(
        hard_gate=passing,
        transfer_guard={"outcome": GUARD_SATISFIED},
        comparability_satisfied=True,
        unreviewed_derived_level_disagreement_count=1,
        tier4_hard_gates_passed=True,
    )
    assert blocked["verdict"] == GATE_INSUFFICIENT
    assert UNREVIEWED_DERIVED_LEVEL_METRIC in blocked["blocking"]
    with pytest.raises(V3ConvergenceError):
        approval_verdict(
            hard_gate=passing,
            transfer_guard={"outcome": GUARD_SATISFIED},
            comparability_satisfied=True,
            unreviewed_derived_level_disagreement_count=-1,
            tier4_hard_gates_passed=True,
        )


def test_a_failing_tier4_gate_fails_approval() -> None:
    verdict = approval_verdict(
        hard_gate=evaluate_hard_structural_gate(
            _clean_pairs(), required_pairs=_REQUIRED
        ),
        transfer_guard={"outcome": GUARD_SATISFIED},
        comparability_satisfied=True,
        unreviewed_derived_level_disagreement_count=0,
        tier4_hard_gates_passed=False,
    )
    assert verdict["verdict"] == GATE_FAIL


def test_the_derived_level_metrics_cannot_certify_at_their_denominators(
    measured: dict,
) -> None:
    for metric in ("breakout_disagreement_rate", "reclaim_disagreement_rate"):
        viability = gate_viability(
            measured, metric, limit=STRUCTURAL_MATERIALITY_LIMIT
        )
        assert not viability["viable"]


# =============================================================================
# Sensitivity
# =============================================================================


def test_the_policy_conclusion_survives_the_neighbourhood(record: dict) -> None:
    sensitivity = record["sensitivity"]
    assert sensitivity["policy_conclusion_stable"]
    assert sensitivity["declared_limit_conclusion_holds"]
    boundaries = sensitivity["viability_boundaries"]
    assert Decimal(boundaries["structural_state_disagreement_rate"]) < Decimal(
        boundaries["breakout_disagreement_rate"]
    )
    assert boundaries["reclaim_disagreement_rate"] is None


def test_the_sensitivity_check_can_actually_fail(record: dict) -> None:
    # The predecessor's stability check could not fail. This one identifies a
    # limit at which the hard gate stops being viable at realistic denominators.
    rows = {
        row["limit"]: row for row in record["sensitivity"]["materiality_neighbourhood"]
    }
    assert not rows["0.10"]["structural_state_viable"]
    assert rows["0.10"]["structural_state_realism"].startswith("NOT_REALISTIC")
    assert rows["0.20"]["structural_state_viable"]


def test_the_evidence_demand_moves_with_the_assumptions(record: dict) -> None:
    rows = {
        row["limit"]: row["minimum_certifying_denominator_by_disagreement_count"]
        for row in record["sensitivity"]["materiality_neighbourhood"]
    }
    assert rows["0.10"]["0"] > rows["0.20"]["0"] > rows["0.30"]["0"]
    levels = {
        row["confidence_level_percent"]: row[
            "minimum_certifying_denominator_by_disagreement_count"
        ]
        for row in record["sensitivity"]["uncertainty_treatment_neighbourhood"]
    }
    assert set(levels) == set(CONFIDENCE_LEVELS)
    assert levels["99"]["0"] > levels["95"]["0"] > levels["90"]["0"]


def test_denominator_imbalance_changes_nothing(record: dict) -> None:
    for row in record["sensitivity"]["denominator_imbalance"]:
        assert row["each_pair_judged_on_its_own_denominator"]
        for name, outcome in row["outcomes"].items():
            index = int(name.rsplit("_", 1)[1])
            size = row["denominators"][index]
            expected = (
                PAIR_CERTIFIED
                if wilson_upper_bound(0, size) <= STRUCTURAL_MATERIALITY_LIMIT
                else PAIR_INSUFFICIENT_EVIDENCE
            )
            assert outcome == expected


# =============================================================================
# The freeze
# =============================================================================


def test_the_protocol_is_frozen_with_its_own_hash(protocol: dict) -> None:
    assert protocol["reference_policy_version"] == V3_PROTOCOL_VERSION
    assert protocol["status"] == V3_FROZEN_STATUS
    assert protocol["schema_version"] == V3_PROTOCOL_SCHEMA_VERSION
    assert len(protocol["definition_sha256"]) == 64
    assert protocol["definition_sha256"] != FROZEN_V2_DEFINITION_SHA256
    assert protocol["definition_sha256"] == v3_definition_sha256(REPOSITORY_ROOT)


def test_the_parent_hash_is_preserved(protocol: dict, record: dict) -> None:
    assert protocol["parent_definition_sha256"] == FROZEN_V2_DEFINITION_SHA256
    assert record["parent_definition_sha256"] == FROZEN_V2_DEFINITION_SHA256
    assert protocol["parent_protocol_version"] == "BTC_REFERENCE_COMPOSITE_V2"


def test_the_protocol_declares_every_field_a_future_verdict_depends_on(
    protocol: dict,
) -> None:
    for field in (
        "candidate",
        "comparability_policy",
        "comparison_contract_version",
        "denominator_semantics_version",
        "dependence_treatment",
        "derived_level_protection",
        "diagnostic_semantics",
        "gate_architecture",
        "gate_pair_universe",
        "inherited_approval_gates",
        "materiality",
        "material_change_requires",
        "metric_definitions",
        "not_comparable_semantics",
        "parent_definition_sha256",
        "sample_governance",
        "soft_gate_semantics",
        "structural_matching_semantics",
        "transfer_guard",
        "validator_requirement",
    ):
        assert protocol[field], field
    architecture = protocol["gate_architecture"]
    assert architecture["hard_metrics"] == ["structural_state_disagreement_rate"]
    assert architecture["soft_metrics"] == ["exact_timestamp_swing_disagreement_rate"]
    assert len(architecture["diagnostic_metrics"]) == 4
    assert architecture["insufficient_evidence_behaviour"].startswith(
        "UNDEFINED_INSUFFICIENT_EVIDENCE"
    )
    certification = architecture["certification_rule"]
    assert certification["rule_id"] == CERTIFICATION_RULE_ID
    assert certification["normal_quantile"] == str(NORMAL_QUANTILE_0_975)
    assert certification["equality_behaviour"]


def test_every_metric_keeps_its_numerator_denominator_and_not_comparable_semantics(
    protocol: dict,
) -> None:
    definitions = {item["metric"]: item for item in protocol["metric_definitions"]}
    assert set(definitions) == set(AFFECTED_V2_GATE_METRICS)
    for definition in definitions.values():
        assert definition["numerator"]
        assert definition["denominator"]
        assert definition["candidate_universe"]
        assert (
            definition["not_comparable_treatment"]
            == "EXCLUDED_FROM_NUMERATOR_AND_DENOMINATOR"
        )


def test_the_inherited_gates_carry_every_parent_gate_but_the_six(
    protocol: dict,
) -> None:
    inherited = {item["metric"] for item in protocol["inherited_approval_gates"]}
    assert not inherited & set(AFFECTED_V2_GATE_METRICS)
    assert len(inherited) == 33
    assert set(INHERITED_TIER4_HARD_GATES) <= inherited
    assert "swing_level_disagreement_rate_above_0_50_atr" in inherited
    assert all(item["inherited_unchanged"] for item in protocol["inherited_approval_gates"])
    hard = [item for item in protocol["inherited_approval_gates"] if item["hard"]]
    assert len(hard) == 29


def test_the_freeze_does_not_authorize_the_validator_or_the_sealed_sample(
    protocol: dict, record: dict
) -> None:
    assert not protocol["production_promotion_authorized"]
    requirement = protocol["validator_requirement"]
    assert not requirement["sealed_sample_may_be_collected"]
    assert not requirement["sealed_sample_may_be_opened"]
    assert requirement["must_bind"].startswith("the BTC_REFERENCE_COMPOSITE_V3")
    assert "parent" in requirement["must_not_bind"]
    assert requirement["sequence"][0].startswith("independent xHigh review")
    assert not record["classification"]["sealed_sample_collection_authorized"]
    assert not record["classification"]["sealed_sample_opening_authorized"]


def test_a_material_change_now_requires_a_successor(protocol: dict) -> None:
    assert protocol["material_change_requires"] == "BTC_REFERENCE_COMPOSITE_V4 or later"


def test_the_classification_is_the_freeze(record: dict) -> None:
    assert record["classification"]["outcome"] == V3_FROZEN_READY
    assert record["classification"]["v3_status_after_this_task"] == V3_FROZEN_STATUS
    assert record["classification"]["validator_construction_authorized"]
    assert record["classification"]["btc019_status_after_this_task"] == "IN_PROGRESS"
    assert record["classification"]["production_canonical_reference"] == "UNRESOLVED"
    assert not record["classification"]["further_evidence_round_authorized"]


def test_the_architecture_comparison_records_every_demotion() -> None:
    comparison = architecture_comparison(REPOSITORY_ROOT)
    assert comparison["v2_and_v3_proposal"]["structural_rate_gates"] == 6
    assert comparison["v2_and_v3_proposal"]["hard_structural_rate_gates"] == 5
    assert comparison["final_v3"]["hard_structural_rate_gates"] == 1
    changes = {row["metric"]: row for row in comparison["metric_changes"]}
    assert changes["structural_state_disagreement_rate"]["change"] == "RETAINED_AS_HARD"
    assert changes["exact_timestamp_swing_disagreement_rate"]["change"] == (
        "RETAINED_AS_SOFT"
    )
    for metric in (
        "within_1_week_swing_disagreement_rate",
        "within_2_week_swing_disagreement_rate",
        "breakout_disagreement_rate",
        "reclaim_disagreement_rate",
    ):
        assert changes[metric]["change"] == "DEMOTED_TO_DIAGNOSTIC"
        assert changes[metric]["parent_hard"]
        assert changes[metric]["why_demoted"]
        assert changes[metric]["protection_that_remains"]
        assert changes[metric]["why_phase_1_safety_is_not_materially_weakened"]


# =============================================================================
# Containment
# =============================================================================


def test_the_sealed_sample_is_neither_collected_nor_opened(
    protocol: dict, record: dict
) -> None:
    sealed = protocol["sample_governance"]["sealed_sample"]
    assert not sealed["collected"]
    assert not sealed["opened"]
    assert not sealed["inspected"]
    assert not sealed["used_in_this_task"]
    assert sealed["guard_refuses_the_sealed_window"]
    assert sealed["start"] == UNTOUCHED_OOS_START.isoformat()
    assert sealed["end"] == UNTOUCHED_OOS_END.isoformat()
    assert not record["sealed_sample_collected"]
    assert not record["sealed_sample_opened"]


def test_the_inherited_guard_still_refuses_the_sealed_window() -> None:
    assert sealed_window_guard_holds()
    with pytest.raises(UntouchedValidationSampleGuardError):
        guard_untouched_validation_sample(
            start=UNTOUCHED_OOS_START,
            end=UNTOUCHED_OOS_END,
            purpose="regression",
        )


def test_no_sealed_history_exists_on_disk() -> None:
    for path in (REPOSITORY_ROOT / "data").rglob("*2015*"):
        pytest.fail(f"sealed-window history is present at {path}")


def test_the_candidate_is_never_constructed_or_measured(
    record: dict, measured: dict
) -> None:
    assert not record["candidate_constructed_in_this_task"]
    assert not record["candidate_measured_in_this_task"]
    assert not record["candidate_final_gate_result_evaluated"]
    for metric in measured:
        for sample_dir in measured[metric]:
            for row in measured[metric][sample_dir]:
                assert "MEDIAN_OHLC_V2" not in row["series_pair"]
                assert "MEDIAN_OHLC_V1" not in row["series_pair"]


def test_no_new_evidence_was_collected(record: dict) -> None:
    assert not record["new_evidence_collected"]
    assert record["evidence_labelling"] == "DEVELOPMENT_CALIBRATION_EVIDENCE"
    assert record["convergence_boundary"] == "FINAL_CONVERGENCE_WITH_EXISTING_EVIDENCE"


def test_the_frozen_prior_artifacts_are_unchanged(record: dict) -> None:
    assert not record["frozen_prior_artifacts_changed"]
    assert record["predecessor_calibration_governance_sha256"] == (
        "503ec79517f34b030d1e8aa690e8a65a4b03050bdb0e2b020b28f9a85267e6e6"
    )
    assert record["proposed_successor_definition_sha256"] == (
        "1ac5438a2eaf742c72bde285ba8289629d17986e1ec00fbee61d724b38417baa"
    )
    assert record["comparison_contract_version"] == COMPARISON_CONTRACT_VERSION


# =============================================================================
# Integrity
# =============================================================================


def _written(tmp_path: Path) -> Path:
    write_convergence_artifacts(REPOSITORY_ROOT, tmp_path)
    return tmp_path


def _retamper(path: Path, mutate) -> None:
    payload = json.loads(path.read_text())
    mutate(payload)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def test_written_artifacts_restore_and_verify(tmp_path: Path) -> None:
    output = _written(tmp_path)
    assert restore_v3_protocol(output)["definition_sha256"] == v3_definition_sha256(
        REPOSITORY_ROOT
    )
    assert restore_convergence_record(output)["classification"]["outcome"] == (
        V3_FROZEN_READY
    )
    assert verify_convergence_artifacts(REPOSITORY_ROOT, output)


def test_the_repository_artifacts_recompute(record: dict) -> None:
    output = REPOSITORY_ROOT / CONVERGENCE_OUTPUT_NAMESPACE
    assert verify_convergence_artifacts(REPOSITORY_ROOT, output) == record
    assert (output / V3_PROTOCOL_FILENAME).exists()
    assert (output / CONVERGENCE_RECORD_FILENAME).exists()
    assert (output / CONVERGENCE_REPORT_FILENAME).exists()


def test_a_wrong_parent_hash_is_refused(tmp_path: Path) -> None:
    output = _written(tmp_path)
    _retamper(
        output / V3_PROTOCOL_FILENAME,
        lambda payload: payload.__setitem__("parent_definition_sha256", "0" * 64),
    )
    with pytest.raises(V3ConvergenceError, match="parent"):
        restore_v3_protocol(output)


def test_a_wrong_governance_predecessor_hash_is_refused(tmp_path: Path) -> None:
    output = _written(tmp_path)
    path = output / CONVERGENCE_RECORD_FILENAME
    payload = json.loads(path.read_text())
    payload["predecessor_calibration_governance_sha256"] = "0" * 64
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(V3ConvergenceError, match="tampered"):
        restore_convergence_record(output)
    payload["artifact_digest"] = "0" * 64
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(V3ConvergenceError, match="tampered"):
        restore_convergence_record(output)


@pytest.mark.parametrize(
    "mutate, match",
    [
        (
            lambda payload: payload["gate_architecture"]["roles"].__setitem__(
                "breakout_disagreement_rate", ROLE_HARD
            ),
            "gate architecture",
        ),
        (
            lambda payload: payload["materiality"].__setitem__("absolute_limit", "0.90"),
            "tampered",
        ),
        (
            lambda payload: payload["diagnostic_semantics"].__setitem__(
                "can_veto_approval", True
            ),
            "tampered",
        ),
        (
            lambda payload: payload["comparability_policy"].__setitem__("floor", "0.01"),
            "tampered",
        ),
        (
            lambda payload: payload["transfer_guard"].__setitem__(
                "depends_on_the_candidate", True
            ),
            "tampered",
        ),
        (
            lambda payload: payload["candidate"].__setitem__(
                "candidate_series_id", "BITSTAMP_ONLY"
            ),
            "tampered",
        ),
        (
            lambda payload: payload.__setitem__("status", "PROPOSED"),
            "not frozen",
        ),
        (
            lambda payload: payload.__setitem__("production_promotion_authorized", True),
            "production promotion",
        ),
        (
            lambda payload: payload["sample_governance"]["sealed_sample"].__setitem__(
                "opened", True
            ),
            "sealed-sample access",
        ),
    ],
)
def test_a_tampered_protocol_field_is_refused(tmp_path: Path, mutate, match) -> None:
    output = _written(tmp_path)
    _retamper(output / V3_PROTOCOL_FILENAME, mutate)
    with pytest.raises(V3ConvergenceError, match=match):
        restore_v3_protocol(output)


def test_a_redigested_tamper_is_still_refused(tmp_path: Path) -> None:
    from btc_predictor.research.reference_composite_v3_convergence import _digest

    output = _written(tmp_path)
    path = output / V3_PROTOCOL_FILENAME
    payload = json.loads(path.read_text())
    payload["materiality"]["absolute_limit"] = "0.90"
    payload.pop("definition_sha256")
    payload["definition_sha256"] = _digest(payload)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    # The digest is now self-consistent, so only recomputation catches it.
    assert restore_v3_protocol(output)
    with pytest.raises(V3ConvergenceError, match="does not recompute"):
        verify_convergence_artifacts(REPOSITORY_ROOT, output)


def test_a_record_promoting_a_diagnostic_to_hard_is_refused(tmp_path: Path) -> None:
    from btc_predictor.research.reference_composite_v3_convergence import _digest

    output = _written(tmp_path)
    path = output / CONVERGENCE_RECORD_FILENAME
    payload = json.loads(path.read_text())
    for item in payload["gate_architecture"]:
        if item["metric"] == "breakout_disagreement_rate":
            item["role"] = ROLE_HARD
    payload.pop("artifact_digest")
    payload["artifact_digest"] = _digest(payload)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(V3ConvergenceError, match="without statistical support"):
        restore_convergence_record(output)


def test_a_record_claiming_sealed_access_or_new_evidence_is_refused(
    tmp_path: Path,
) -> None:
    from btc_predictor.research.reference_composite_v3_convergence import _digest

    for field in (
        "sealed_sample_opened",
        "sealed_sample_collected",
        "candidate_final_gate_result_evaluated",
        "new_evidence_collected",
    ):
        output = _written(tmp_path / field)
        path = output / CONVERGENCE_RECORD_FILENAME
        payload = json.loads(path.read_text())
        payload[field] = True
        payload.pop("artifact_digest")
        payload["artifact_digest"] = _digest(payload)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        with pytest.raises(V3ConvergenceError):
            restore_convergence_record(output)


def test_an_unknown_schema_version_is_refused(tmp_path: Path) -> None:
    output = _written(tmp_path)
    _retamper(
        output / CONVERGENCE_RECORD_FILENAME,
        lambda payload: payload.__setitem__("schema_version", "SOMETHING_ELSE"),
    )
    with pytest.raises(V3ConvergenceError, match=CONVERGENCE_SCHEMA_VERSION):
        restore_convergence_record(output)


# =============================================================================
# Determinism
# =============================================================================


def test_the_definition_rebuilds_where_no_history_exists(tmp_path: Path) -> None:
    isolated = _isolated_root(tmp_path / "root")
    assert v3_protocol_definition(isolated) == v3_protocol_definition(REPOSITORY_ROOT)


def test_the_working_directory_cannot_change_the_definition(
    tmp_path: Path, monkeypatch
) -> None:
    expected = v3_definition_sha256(REPOSITORY_ROOT)
    monkeypatch.chdir(tmp_path)
    assert v3_definition_sha256(REPOSITORY_ROOT) == expected


def test_the_ambient_decimal_context_cannot_change_a_result(record: dict) -> None:
    with decimal.localcontext(Context(prec=6)):
        assert wilson_upper_bound(2, 28) == wilson_upper_bound(2, 28)
        narrow = build_convergence_record(REPOSITORY_ROOT)
    assert narrow == record


def test_provider_and_dictionary_order_cannot_change_a_result(measured: dict) -> None:
    for metric in measured:
        for sample_dir in measured[metric]:
            identifiers = [row["comparison_id"] for row in measured[metric][sample_dir]]
            assert identifiers == sorted(identifiers)
            for row in measured[metric][sample_dir]:
                assert row["series_pair"] == sorted(row["series_pair"])


def test_the_record_is_stable_across_a_process_restart_and_hash_seed() -> None:
    script = (
        "from pathlib import Path;"
        "from btc_predictor.research.reference_composite_v3_convergence import "
        "build_convergence_record, v3_definition_sha256;"
        "record = build_convergence_record(Path('.'));"
        "print(record['artifact_digest']);"
        "print(v3_definition_sha256(Path('.')))"
    )
    digests = []
    for seed in ("0", "12345"):
        environment = {**os.environ, "PYTHONHASHSEED": seed}
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            check=True,
            cwd=REPOSITORY_ROOT,
            env=environment,
            text=True,
        )
        digests.append(result.stdout.strip())
    assert digests[0] == digests[1]
    assert v3_definition_sha256(REPOSITORY_ROOT) in digests[0]


def test_the_written_artifacts_are_deterministic_ascii(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_convergence_artifacts(REPOSITORY_ROOT, first)
    write_convergence_artifacts(REPOSITORY_ROOT, second)
    for name in (
        V3_PROTOCOL_FILENAME,
        CONVERGENCE_RECORD_FILENAME,
        CONVERGENCE_REPORT_FILENAME,
    ):
        left = (first / name).read_bytes()
        assert left == (second / name).read_bytes()
        left.decode("ascii")


def test_the_report_renders_every_decimal_in_plain_notation(
    protocol: dict, record: dict
) -> None:
    report = convergence_markdown(protocol, record)
    assert "E-" not in report and "E+" not in report
    assert CONVERGENCE_VERSION in report
    assert V3_FROZEN_READY in report
    assert protocol["definition_sha256"] in report
    assert FROZEN_V2_DEFINITION_SHA256 in report
    for metric, role in EXPECTED_ROLES.items():
        assert f"| {metric} | {role} |" in report
