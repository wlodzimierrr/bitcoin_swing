"""Corrected pre-data sufficiency governance for prospective Stage-B evidence.

POSTP1-003R1 never collects evidence or consumes a numerator, target outcome,
relative-difference value, or PASS/FAIL result while determining sufficiency.
It binds the certified prospective corpus, separates the three relevant count
types, and owns a stateful reference contract for future POSTP1-004 persistence.
The scientific monitor accepts only content-addressed evidence references.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, Context, Decimal, localcontext
from fractions import Fraction
from functools import cache
from pathlib import Path
from threading import RLock
from typing import Any

from btc_predictor.research import prospective_integration_corpus as _corpus
from btc_predictor.research import prospective_source_integrity as _source_integrity
from btc_predictor.research.structural_threshold_calibration import (
    UNCERTAINTY_METHOD_ID,
    WILSON_Z_95,
    wilson_interval,
)


GOVERNANCE_VERSION = "PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1"
GOVERNANCE_SCHEMA_VERSION = (
    "PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_DEFINITION_V1"
)
GOVERNANCE_STATUS = "CORRECTED_FROZEN_PRE_DATA_SUFFICIENCY_GOVERNANCE"
PROGRAM_TICKET = "POSTP1-003R1"
WORKSTREAM = "EPIC X"
FINAL_CLASSIFICATION = (
    "PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1_"
    "READY_FOR_REPEAT_XHIGH_REVIEW"
)

FAILED_GOVERNANCE_SHA256 = (
    "3f51c4d9d8f14689b3f6c863e1731a6ef170b9764162b79bd56cc369af4ae2c7"
)
FAILED_GOVERNANCE_IMPLEMENTATION_COMMIT = (
    "90a0252744f333e2168ad3904efbc1ec14c5693e"
)
FAILED_GOVERNANCE_REVIEW_DOCUMENTATION_COMMIT = (
    "86def44f0a734efdf175b3be8541644029f5f31d"
)
FAILED_GOVERNANCE_REVIEW_RESULT = "FAIL — SUFFICIENCY GOVERNANCE INVALID"
FAILED_GOVERNANCE_CLASSIFICATION = "SUFFICIENCY_GOVERNANCE_REQUIRES_FIX"

CERTIFIED_CORPUS_VERSION = _corpus.PROTOCOL_VERSION
CERTIFIED_CORPUS_SHA256 = (
    "8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7"
)
CERTIFIED_CORPUS_IMPLEMENTATION_COMMIT = (
    "428356665dff0985cf8b1c379f6f18bf6cc5bac1"
)
CERTIFIED_CORPUS_REVIEW_FIX_COMMIT = (
    "ab3b353e344465966da321af02b08f6fe28213f5"
)
CERTIFIED_CORPUS_REVIEW_TICKET = "POSTP1-002R5"
CERTIFIED_CORPUS_REVIEW_RESULT = (
    "PROSPECTIVE_PROTOCOL_CERTIFIED_FOR_SUFFICIENCY_GOVERNANCE"
)

OUTPUT_NAMESPACE = (
    "prospective_evidence/"
    "prospective_integration_evidence_sufficiency_governance_v1"
)
DEFINITION_FILENAME = "sufficiency_governance_definition.json"
COMMON_RATE_FILENAME = "common_rate_evidence_strength.json"
P95_FILENAME = "p95_tail_repeatability.json"
MINIMA_FILENAME = "metric_sufficiency_minima.json"
DERIVATIONS_FILENAME = "statistical_derivations.json"
COVERAGE_FILENAME = "coverage_policy.json"
EVIDENCE_UNIT_FILENAME = "evidence_unit_policy.json"
TEMPORAL_FILENAME = "temporal_policy.json"
BLIND_MONITOR_FILENAME = "blind_monitor_contract.json"
EPOCH_FILENAME = "evaluation_epoch_contract.json"
CUTOFF_FILENAME = "evaluation_cutoff_contract.json"
RESULT_IDENTITY_FILENAME = "evaluation_result_identity.json"
STOPPING_RULE_FILENAME = "stopping_rule.json"
SEMANTIC_DIFF_FILENAME = "semantic_diff_from_stage_b_gates.json"
REPORT_FILENAME = (
    "PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1_REPORT.md"
)

_DECIMAL_CONTEXT = Context(prec=80)
_SHA256_HEX_LENGTH = 64


class SufficiencyGovernanceError(ValueError):
    """Frozen governance, evidence, or identity failed closed."""


class EvaluationEpochFrozenError(SufficiencyGovernanceError):
    """An immutable cutoff or terminal evaluation epoch was extended."""


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("ascii")).hexdigest()


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != _SHA256_HEX_LENGTH:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _with_definition_hash(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["definition_sha256"] = _digest(result)
    return result


def _with_record_hash(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["record_sha256"] = _source_integrity.digest(result)
    return result


def _verify_hashed_definition(payload: Mapping[str, Any], name: str) -> str:
    row = dict(payload)
    declared = row.pop("definition_sha256", None)
    if not _is_sha256(declared) or _digest(row) != declared:
        raise SufficiencyGovernanceError(f"{name} must carry its real SHA-256")
    return declared


def _require_certified_corpus() -> dict[str, Any]:
    protocol = _corpus.protocol_definition()
    if protocol.get("definition_sha256") != CERTIFIED_CORPUS_SHA256:
        raise SufficiencyGovernanceError("certified corpus hash mismatch")
    if protocol.get("protocol_version") != CERTIFIED_CORPUS_VERSION:
        raise SufficiencyGovernanceError("certified corpus version mismatch")
    if tuple(protocol.get("target_metrics", ())) != _corpus.TARGET_METRICS:
        raise SufficiencyGovernanceError("certified corpus target census moved")
    if protocol.get("material_child_count") != 25:
        raise SufficiencyGovernanceError("certified corpus child census moved")
    return protocol


def _historical_gate_rows() -> dict[str, dict[str, Any]]:
    authority = _corpus.historical_gate_authority()
    contracts = _corpus.metric_evidence_contracts()["contracts"]
    if set(authority) != set(_corpus.TARGET_METRICS):
        raise SufficiencyGovernanceError("historical authority must carry eight gates")
    if set(contracts) != set(_corpus.TARGET_METRICS):
        raise SufficiencyGovernanceError("certified corpus must carry eight metrics")
    rows: dict[str, dict[str, Any]] = {}
    for metric in _corpus.TARGET_METRICS:
        gate = authority[metric]
        contract = contracts[metric]
        parity = {
            "threshold": contract["threshold"] == gate["threshold"],
            "direction": contract["direction"] == gate["direction"],
            "hard": contract["hard"] == gate["hard"],
            "metric_intent": contract["historical_definition"] == gate["definition"],
        }
        if not all(parity.values()):
            raise SufficiencyGovernanceError(
                f"{metric} differs from immutable Stage-B authority"
            )
        rows[metric] = {
            "cadence": contract["cadence"],
            "direction": gate["direction"],
            "hard": gate["hard"],
            "metric": metric,
            "metric_intent": gate["definition"],
            "metric_intent_source": gate["source_of_rationale"],
            "parity": parity,
            "performance_denominator": contract["denominator"],
            "source_authority": gate["source_authority"],
            "threshold": gate["threshold"],
            "universe": contract["universe"],
        }
    return rows


def semantic_diff_from_stage_b_gates() -> dict[str, Any]:
    rows = _historical_gate_rows()
    payload = {
        "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
        "direction_change_count": sum(
            not row["parity"]["direction"] for row in rows.values()
        ),
        "hard_role_change_count": sum(
            not row["parity"]["hard"] for row in rows.values()
        ),
        "metric_count": len(rows),
        "metric_intent_change_count": sum(
            not row["parity"]["metric_intent"] for row in rows.values()
        ),
        "rows": rows,
        "schema_version": "STAGE_B_GATE_SEMANTIC_DIFF_V1",
        "threshold_change_count": sum(
            not row["parity"]["threshold"] for row in rows.values()
        ),
    }
    if any(
        payload[key] != 0
        for key in (
            "threshold_change_count",
            "direction_change_count",
            "hard_role_change_count",
            "metric_intent_change_count",
        )
    ):
        raise SufficiencyGovernanceError("immutable Stage-B gate parity failed")
    return _with_definition_hash(payload)


RATE_METRICS = tuple(
    metric for metric in _corpus.TARGET_METRICS if metric != _corpus.RISK_SIZE_METRIC
)
RISK_P95_METRIC = _corpus.RISK_SIZE_METRIC
WILSON_FORMULA_ID = "WILSON_SCORE_INTERVAL_95_TWO_SIDED_UNCORRECTED_V1"
WILSON_CAPABILITY_RULE_ID = "PERFECT_SAMPLE_WILSON_CAPABILITY_FLOOR_V1"
COMMON_RATE_EVIDENCE_STRENGTH_ID = "COMMON_RATE_EVIDENCE_STRENGTH_V1"
P95_TAIL_REPEATABILITY_ID = "P95_TAIL_REPEATABILITY_SUFFICIENCY_V1"
RATE_EVIDENCE_EPSILON = Decimal("0.01")
RATE_EVIDENCE_REFERENCE = Decimal("0.99")
P95_QUANTILE = Decimal("0.95")
P95_TAIL_PROBABILITY = Decimal("0.05")
P95_REPEATABILITY_HITS = 2
EVIDENCE_CONFIDENCE = Decimal("0.95")


def _decimal_ceiling(value: Decimal) -> int:
    with localcontext(_DECIMAL_CONTEXT) as context:
        return int(value.to_integral_value(rounding=ROUND_CEILING, context=context))


def _wilson_extreme_bound(direction: str, denominator: int) -> Decimal:
    if denominator <= 0:
        raise SufficiencyGovernanceError("a Wilson bound needs positive evidence")
    interval = wilson_interval(
        denominator if direction == "minimum" else 0,
        denominator,
    )
    return interval.lower if direction == "minimum" else interval.upper


def _finite_wilson_minimum(threshold: Decimal, direction: str) -> int | None:
    if direction not in ("minimum", "maximum"):
        raise SufficiencyGovernanceError("rate direction must be minimum or maximum")
    if threshold < 0 or threshold > 1:
        raise SufficiencyGovernanceError("a rate threshold must lie in [0,1]")
    if (direction == "minimum" and threshold == 1) or (
        direction == "maximum" and threshold == 0
    ):
        return None
    with localcontext(_DECIMAL_CONTEXT) as context:
        z_squared = context.multiply(WILSON_Z_95, WILSON_Z_95)
        if direction == "minimum":
            unrounded = context.divide(
                context.multiply(z_squared, threshold),
                context.subtract(Decimal(1), threshold),
            )
        else:
            unrounded = context.divide(
                context.multiply(z_squared, context.subtract(Decimal(1), threshold)),
                threshold,
            )
    candidate = max(1, _decimal_ceiling(unrounded))
    bound = _wilson_extreme_bound(direction, candidate)
    satisfied = bound >= threshold if direction == "minimum" else bound <= threshold
    previous_satisfied = False
    if candidate > 1:
        previous = _wilson_extreme_bound(direction, candidate - 1)
        previous_satisfied = (
            previous >= threshold if direction == "minimum" else previous <= threshold
        )
    if not satisfied or previous_satisfied:
        raise SufficiencyGovernanceError("Wilson minimum failed owner parity")
    return candidate


def common_rate_evidence_strength() -> dict[str, Any]:
    gates = _historical_gate_rows()
    distances: dict[str, str] = {}
    for metric in RATE_METRICS:
        threshold = Decimal(str(gates[metric]["threshold"]))
        distance = min(threshold, Decimal(1) - threshold)
        if distance > 0:
            distances[metric] = str(distance)
    epsilon = min(Decimal(value) for value in distances.values())
    if epsilon != RATE_EVIDENCE_EPSILON:
        raise SufficiencyGovernanceError("mechanical rate epsilon moved")
    reference = Decimal(1) - epsilon
    minimum = _finite_wilson_minimum(reference, "minimum")
    if minimum != 381:
        raise SufficiencyGovernanceError("common evidence-strength minimum moved")
    payload = {
        "boundary_probe": {
            "n_minus_one": 380,
            "n_minus_one_lower": str(_wilson_extreme_bound("minimum", 380)),
            "n_minus_one_satisfies": False,
            "n": 381,
            "n_lower": str(_wilson_extreme_bound("minimum", 381)),
            "n_satisfies": True,
        },
        "closed_boundary_reference": str(reference),
        "confidence": str(EVIDENCE_CONFIDENCE),
        "distance_by_finite_interior_rate_gate": dict(sorted(distances.items())),
        "epsilon": str(epsilon),
        "epsilon_derivation": (
            "minimum positive distance from the closed boundary {0,1} among "
            "the inherited Stage-B rate thresholds"
        ),
        "minimum_all_success_raw_denominator": minimum,
        "performance_threshold_replacement": False,
        "purpose": "PRE_DATA_COMMON_RATE_EVIDENCE_STRENGTH_ONLY",
        "schema_version": COMMON_RATE_EVIDENCE_STRENGTH_ID,
        "wilson_method_id": WILSON_FORMULA_ID,
        "wilson_owner_method_id": UNCERTAINTY_METHOD_ID,
        "wilson_z": str(WILSON_Z_95),
    }
    return _with_definition_hash(payload)


def _rate_derivation(metric: str, gate: Mapping[str, Any]) -> dict[str, Any]:
    direction = str(gate["direction"])
    threshold = Decimal(str(gate["threshold"]))
    if metric == _corpus.CROSS_MARKET_METRIC:
        common = common_rate_evidence_strength()
        return {
            "derived_n_capability": None,
            "direction": direction,
            "evidence_strength_confidence": common["confidence"],
            "evidence_strength_epsilon": common["epsilon"],
            "evidence_strength_reference": common["closed_boundary_reference"],
            "evidence_strength_rule_id": COMMON_RATE_EVIDENCE_STRENGTH_ID,
            "metric": metric,
            "minimum_denominator": common["minimum_all_success_raw_denominator"],
            "performance_threshold": str(gate["threshold"]),
            "performance_threshold_changed": False,
            "threshold": str(gate["threshold"]),
            "wilson_method_id": WILSON_FORMULA_ID,
            "wilson_z": str(WILSON_Z_95),
        }
    capability = _finite_wilson_minimum(threshold, direction)
    if capability is None:
        raise SufficiencyGovernanceError("unexpected closed rate boundary")
    current = _wilson_extreme_bound(direction, capability)
    previous = _wilson_extreme_bound(direction, capability - 1)
    return {
        "derived_n_capability": capability,
        "direction": direction,
        "metric": metric,
        "minimum_denominator": capability,
        "n_capability_bound": str(current),
        "n_capability_criterion_satisfied": (
            current >= threshold if direction == "minimum" else current <= threshold
        ),
        "n_capability_minus_one_bound": str(previous),
        "n_capability_minus_one_criterion_satisfied": (
            previous >= threshold if direction == "minimum" else previous <= threshold
        ),
        "performance_threshold": str(gate["threshold"]),
        "performance_threshold_changed": False,
        "threshold": str(gate["threshold"]),
        "wilson_method_id": WILSON_FORMULA_ID,
        "wilson_z": str(WILSON_Z_95),
    }


def _tail_repeatability_probability_fraction(denominator: int) -> Fraction:
    if not isinstance(denominator, int) or isinstance(denominator, bool) or denominator < 0:
        raise SufficiencyGovernanceError("tail denominator must be non-negative integer")
    if denominator == 0:
        return Fraction(0, 1)
    tail = Fraction(1, 20)
    non_tail = Fraction(19, 20)
    return 1 - non_tail**denominator - denominator * tail * non_tail ** (
        denominator - 1
    )


def _fraction_decimal(value: Fraction) -> str:
    with localcontext(_DECIMAL_CONTEXT):
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def p95_tail_repeatability() -> dict[str, Any]:
    target = Fraction(19, 20)
    minimum = next(
        n for n in range(1, 10_000) if _tail_repeatability_probability_fraction(n) >= target
    )
    if minimum != 93:
        raise SufficiencyGovernanceError("p95 repeatability minimum moved")
    p92 = _tail_repeatability_probability_fraction(92)
    p93 = _tail_repeatability_probability_fraction(93)
    payload = {
        "confidence": str(EVIDENCE_CONFIDENCE),
        "formula": "1 - 0.95^n - n * 0.05 * 0.95^(n-1)",
        "iid_scope": "PRE_DATA_SUFFICIENCY_CALCULATION_ONLY",
        "minimum_denominator": minimum,
        "minimum_distinct_sizing_evidence_units": minimum,
        "minimum_repeated_tail_occurrences": P95_REPEATABILITY_HITS,
        "n_92": {"probability": _fraction_decimal(p92), "satisfies": p92 >= target},
        "n_93": {"probability": _fraction_decimal(p93), "satisfies": p93 >= target},
        "population_quantile_confidence_interval_claim": False,
        "quantile": str(P95_QUANTILE),
        "risk_statistic_changed": False,
        "risk_statistic_owner": (
            "btc_predictor.research.prospective_integration_corpus."
            "nearest_rank_percentile"
        ),
        "schema_version": P95_TAIL_REPEATABILITY_ID,
        "tail_probability": str(P95_TAIL_PROBABILITY),
    }
    return _with_definition_hash(payload)


def statistical_derivations() -> dict[str, Any]:
    gates = _historical_gate_rows()
    common = common_rate_evidence_strength()
    p95 = p95_tail_repeatability()
    payload = {
        "ambient_decimal_context_consumed": False,
        "common_rate_evidence_strength_sha256": common["definition_sha256"],
        "nearest_rank_p95": p95,
        "p95_tail_repeatability_sha256": p95["definition_sha256"],
        "rate_metrics": {
            metric: _rate_derivation(metric, gates[metric]) for metric in RATE_METRICS
        },
        "schema_version": "PROSPECTIVE_SUFFICIENCY_STATISTICAL_DERIVATIONS_V1",
        "wilson": {
            "confidence_level": str(EVIDENCE_CONFIDENCE),
            "continuity_correction_applied": False,
            "formula_id": WILSON_FORMULA_ID,
            "method_owner": (
                "btc_predictor.research.structural_threshold_calibration.wilson_interval"
            ),
            "owner_method_id": UNCERTAINTY_METHOD_ID,
            "replaces_inherited_point_metric_pass_fail": False,
            "z": str(WILSON_Z_95),
        },
    }
    return _with_definition_hash(payload)


EVIDENCE_UNIT_POLICY_ID = "PROSPECTIVE_STAGE_B_EVIDENCE_UNIT_POLICY_V1"
COVERAGE_POLICY_ID = "PROSPECTIVE_STAGE_B_AUTHORITATIVE_COVERAGE_V1"
TEMPORAL_POLICY_ID = "PROSPECTIVE_STAGE_B_TEMPORAL_POLICY_V1"
COVERAGE_FLOOR_NUMERATOR = 99
COVERAGE_FLOOR_DENOMINATOR = 100
NO_SEPARATE_ARBITRARY_CALENDAR_MINIMUM = "NONE"


def evidence_unit_policy() -> dict[str, Any]:
    protocol = _require_certified_corpus()
    metrics: dict[str, Any] = {}
    for metric in _corpus.TARGET_METRICS:
        if metric in _corpus.STOP_EVENT_METRICS:
            kind = "CONTROL_POSITION_ACTIVE_STOP_LIFECYCLE_EPISODE"
            owner = (
                "certified control portfolio lifecycle hash chain plus "
                "prospective_stop_event.active_stop_identity"
            )
            derivation = (
                "sha256(control position opening-transition identity, active stop "
                "identity, certified corpus hash, policy version)"
            )
            fields = {
                "active_stop_identity": (
                    "prospective_stop_event.active_stop_identity; control lifecycle "
                    "active stop plus transition/source identity"
                ),
                "control_position_episode_sha256": (
                    "replayed root opening transition from the control portfolio "
                    "prior_state_sha256 hash chain"
                ),
            }
        elif metric == _corpus.RISK_SIZE_METRIC:
            kind = "AUTHORITATIVE_DAILY_SIZING_OPPORTUNITY"
            owner = (
                "PROSPECTIVE_INTEGRATION_DECISION_UNIVERSE_V1 canonical daily slot "
                "plus paired prospective_risk_evaluation records"
            )
            derivation = "canonical STRATEGY_DAILY slot_id"
            fields = {"slot_id": "certified UTC strategy decision identity"}
        else:
            kind = "AUTHORITATIVE_DAILY_DECISION"
            owner = "PROSPECTIVE_INTEGRATION_DECISION_UNIVERSE_V1"
            derivation = "canonical STRATEGY_DAILY slot_id"
            fields = {"slot_id": "certified UTC strategy decision identity"}
        metrics[metric] = {
            "dependence_unit_derivation": derivation,
            "dependence_unit_kind": kind,
            "dependence_unit_owner": owner,
            "identity_fields": fields,
            "maximum_sufficiency_credit_per_unit": 1,
            "revisions_or_replays_create_new_unit": False,
        }
    payload = {
        "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
        "decision_universe_sha256": protocol["child_definition_sha256"][
            "decision_universe"
        ],
        "metric_evidence_contract_sha256": protocol["child_definition_sha256"][
            "metric_evidence_contracts"
        ],
        "metrics": metrics,
        "raw_observations_are_independent_by_default": False,
        "schema_version": EVIDENCE_UNIT_POLICY_ID,
    }
    return _with_definition_hash(payload)


def _derive_dependence_unit_id(
    metric: str,
    *,
    slot_id: str,
    control_position_episode_sha256: str | None,
    active_stop_identity: str | None,
) -> str:
    if metric in _corpus.STOP_EVENT_METRICS:
        if not _is_sha256(control_position_episode_sha256):
            raise SufficiencyGovernanceError(
                "stop evidence lacks a replayed control position episode identity"
            )
        if not isinstance(active_stop_identity, str) or not active_stop_identity:
            raise SufficiencyGovernanceError(
                "stop evidence lacks a replayed active stop identity"
            )
        return _digest(
            {
                "active_stop_identity": active_stop_identity,
                "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
                "control_position_episode_sha256": control_position_episode_sha256,
                "policy": EVIDENCE_UNIT_POLICY_ID,
            }
        )
    if not _is_sha256(slot_id):
        raise SufficiencyGovernanceError("daily evidence lacks canonical slot identity")
    return slot_id


def metric_sufficiency_minima() -> dict[str, Any]:
    protocol = _require_certified_corpus()
    gates = _historical_gate_rows()
    contracts = _corpus.metric_evidence_contracts()["contracts"]
    derivations = statistical_derivations()
    unit_policy = evidence_unit_policy()
    rows: dict[str, dict[str, Any]] = {}
    for metric in _corpus.TARGET_METRICS:
        if metric == RISK_P95_METRIC:
            minimum = int(derivations["nearest_rank_p95"]["minimum_denominator"])
            method = P95_TAIL_REPEATABILITY_ID
        else:
            minimum = int(derivations["rate_metrics"][metric]["minimum_denominator"])
            method = (
                COMMON_RATE_EVIDENCE_STRENGTH_ID
                if metric == _corpus.CROSS_MARKET_METRIC
                else WILSON_CAPABILITY_RULE_ID
            )
        rows[metric] = {
            "authoritative_coverage_floor": "0.99",
            "cadence": contracts[metric]["cadence"],
            "direction": gates[metric]["direction"],
            "hard": gates[metric]["hard"],
            "metric": metric,
            "metric_evidence_contract_sha256": protocol[
                "child_definition_sha256"
            ]["metric_evidence_contracts"],
            "metric_intent": gates[metric]["metric_intent"],
            "minimum_distinct_dependence_units": minimum,
            "minimum_raw_sufficiency_denominator": minimum,
            "performance_denominator": contracts[metric]["denominator"],
            "performance_gate_unchanged": True,
            "performance_threshold": str(gates[metric]["threshold"]),
            "statistical_method": method,
            "sufficiency_quantities_are_distinct": {
                "effective_dependence_unit_count": True,
                "performance_denominator": True,
                "raw_sufficiency_denominator": True,
            },
            "universe": contracts[metric]["universe"],
            "unit_policy": unit_policy["metrics"][metric],
            "zero_denominator_outcome": _corpus.UNDEFINED_INSUFFICIENT_EVIDENCE,
            "zero_denominator_sufficient": False,
        }
    payload = {
        "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
        "decision_universe_sha256": protocol["child_definition_sha256"][
            "decision_universe"
        ],
        "evidence_unit_policy_sha256": unit_policy["definition_sha256"],
        "metric_count": len(rows),
        "metrics": rows,
        "no_candidate_identity_used_to_choose_minima": True,
        "no_observed_outcome_used_to_choose_minima": True,
        "schema_version": "PROSPECTIVE_METRIC_SUFFICIENCY_MINIMA_V1",
        "statistical_derivations_sha256": derivations["definition_sha256"],
    }
    return _with_definition_hash(payload)


def coverage_policy() -> dict[str, Any]:
    common = common_rate_evidence_strength()
    payload = {
        "accounting_requirement": {
            "accounted_scheduled_slot_rate": "1.0",
            "exactly_one_persisted_evidence_reference_per_scheduled_slot": True,
            "unaccounted_scheduled_slot_count_required": 0,
        },
        "authoritative_coverage_denominator": (
            "all expected post-warmup scheduled slots at the metric's certified "
            "cadence through the prefix"
        ),
        "authoritative_coverage_numerator": (
            "scheduled post-warmup slots where certified replay establishes "
            "warmup, PIT, universe membership, and a final EVALUATED, "
            "NOT_IN_UNIVERSE, or NOT_COMPARABLE disposition"
        ),
        "blind_categories_counting_as_authoritatively_replayed": [
            "EVALUATED",
            "NOT_COMPARABLE",
            "NOT_IN_UNIVERSE",
        ],
        "blind_categories_counting_as_coverage_failure": [
            "DATA_QUALITY_FAIL",
            "PIT_INVALID",
            "REFERENCE_UNAVAILABLE",
            "SOURCE_UNAVAILABLE",
            "WARMUP_INCOMPLETE",
        ],
        "common_rate_evidence_strength_sha256": common["definition_sha256"],
        "comparison": "coverage_numerator * 100 >= coverage_denominator * 99",
        "exact_integer_comparison": True,
        "floor": "0.99",
        "floor_is_stage_b_performance_threshold": False,
        "floor_source_epsilon": common["epsilon"],
        "per_metric": True,
        "schema_version": COVERAGE_POLICY_ID,
    }
    return _with_definition_hash(payload)


def authoritative_coverage_satisfied(numerator: int, denominator: int) -> bool:
    for name, value in (("numerator", numerator), ("denominator", denominator)):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise SufficiencyGovernanceError(f"coverage {name} must be non-negative int")
    if numerator > denominator:
        raise SufficiencyGovernanceError("coverage numerator exceeds denominator")
    return denominator > 0 and numerator * COVERAGE_FLOOR_DENOMINATOR >= (
        denominator * COVERAGE_FLOOR_NUMERATOR
    )


def temporal_policy() -> dict[str, Any]:
    payload = {
        "concentration_diagnostics": [
            "distinct_utc_days",
            "distinct_iso_weeks",
            "first_evidence_time",
            "last_evidence_time",
            "largest_single_day_contribution",
            "largest_single_week_contribution",
            "distinct_dependence_unit_count",
            "largest_dependence_unit_raw_contribution",
        ],
        "diagnostics_are_additional_hard_gates": False,
        "evidence_unit_policy": EVIDENCE_UNIT_POLICY_ID,
        "minimum_calendar_duration": None,
        "minimum_distinct_iso_weeks": None,
        "minimum_distinct_utc_days": None,
        "policy": "NO_SEPARATE_ARBITRARY_CALENDAR_MINIMUM",
        "reasoning": (
            "Dependence is governed by hard natural evidence-unit rules rather "
            "than raw clustered observations or an arbitrary elapsed duration."
        ),
        "schema_version": TEMPORAL_POLICY_ID,
        "stage_c_live_shadow_days_imported": False,
    }
    return _with_definition_hash(payload)


BLIND_MONITOR_VERSION = "PROSPECTIVE_STAGE_B_SUFFICIENCY_MONITOR_V1"
BLIND_PROJECTION_VERSION = "PROSPECTIVE_STAGE_B_BLIND_EVIDENCE_PROJECTION_V1"
BLIND_SOURCE_RECORD_VERSION = "PROSPECTIVE_STAGE_B_BLIND_SOURCE_EVIDENCE_V1"
BLIND_CATEGORIES = (
    "DATA_QUALITY_FAIL",
    "EVALUATED",
    "NOT_COMPARABLE",
    "NOT_IN_UNIVERSE",
    "PIT_INVALID",
    "REFERENCE_UNAVAILABLE",
    "SOURCE_UNAVAILABLE",
    "WARMUP_INCOMPLETE",
)
AUTHORITATIVE_REPLAY_STATES = (
    "AUTHORITATIVE_REPLAYED",
    "DATA_QUALITY_FAIL",
    "INVALID_CLOCK_OR_PIT_EVIDENCE",
    "REFERENCE_UNAVAILABLE",
    "SOURCE_UNAVAILABLE",
    "UNREPLAYABLE_EVIDENCE",
)
_COVERED_CATEGORIES = frozenset({"EVALUATED", "NOT_COMPARABLE", "NOT_IN_UNIVERSE"})


@dataclass(frozen=True)
class BlindEvidenceReference:
    """Identity-only input accepted by the scientific monitor."""

    slot_id: str
    authoritative_evidence_record_sha256: str
    evaluation_epoch_authorization_sha256: str


@dataclass(frozen=True)
class ReplayedBlindProjection:
    cadence: str
    observation_time: datetime
    decision_time: datetime
    slot_id: str
    source_record_sha256: str
    projection_record_sha256: str
    category_by_metric: Mapping[str, str]
    dependence_unit_by_metric: Mapping[str, str | None]


def blind_monitor_contract() -> dict[str, Any]:
    protocol = _require_certified_corpus()
    payload = {
        "allowed_monitor_input_fields": [
            "authoritative_evidence_record_sha256",
            "evaluation_epoch_authorization_sha256",
            "slot_id",
        ],
        "blind_category_vocabulary": list(BLIND_CATEGORIES),
        "caller_declared_projection_is_authority": False,
        "contract_version": BLIND_MONITOR_VERSION,
        "decision_universe_sha256": protocol["child_definition_sha256"][
            "decision_universe"
        ],
        "dependence_unit_replayed": True,
        "detailed_parent_reason_codes_exposed_to_monitor": False,
        "metric_evidence_contract_sha256": protocol["child_definition_sha256"][
            "metric_evidence_contracts"
        ],
        "outcome_blind": True,
        "pit_replayed": True,
        "prohibited_monitor_input_fields": [
            "aggregate_metric_result",
            "candidate_control_agreement",
            "global_disposition",
            "metric_disposition",
            "metric_numerator",
            "pass_fail_result",
            "post_warmup",
            "reason_code",
            "risk_size_relative_difference",
            "universe_member",
        ],
        "projection_rule": (
            "Resolve content-addressed source evidence, verify certified parent "
            "identities, replay cadence/warmup/PIT/universe/comparability and the "
            "natural dependence unit, derive only the coarse blind category, then "
            "require any convenience projection to match exactly."
        ),
        "resolver_contract_sha256": protocol["child_definition_sha256"][
            "scientific_evidence_resolver"
        ],
        "schema_version": BLIND_PROJECTION_VERSION,
        "warmup_replayed": True,
    }
    return _with_definition_hash(payload)


@cache
def _blind_parent_bindings() -> dict[str, str]:
    protocol = _require_certified_corpus()
    return {
        "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
        "decision_universe_sha256": protocol["child_definition_sha256"][
            "decision_universe"
        ],
        "metric_evidence_contract_sha256": protocol["child_definition_sha256"][
            "metric_evidence_contracts"
        ],
        "warmup_history_definition_sha256": protocol["child_definition_sha256"][
            "warmup_history"
        ],
    }


def _require_utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise SufficiencyGovernanceError(f"{name} must be timezone-aware UTC")
    if value.utcoffset() != timedelta(0):
        raise SufficiencyGovernanceError(f"{name} must be UTC")
    return value.astimezone(UTC)


def _strict_keys(row: Mapping[str, Any], expected: set[str], name: str) -> None:
    actual = set(row)
    if actual != expected:
        raise SufficiencyGovernanceError(
            f"{name} fields differ: missing={sorted(expected - actual)}, "
            f"unexpected={sorted(actual - expected)}"
        )


@cache
def _metric_cadences() -> dict[str, str]:
    return {
        metric: str(contract["cadence"])
        for metric, contract in _corpus.metric_evidence_contracts()["contracts"].items()
    }


def _expected_slots_through(
    epoch_observation_start: datetime,
    current_decision_time: datetime,
) -> tuple[dict[str, str], ...]:
    start = _require_utc(epoch_observation_start, "epoch_observation_start")
    current = _require_utc(current_decision_time, "current_decision_time")
    if start != start.replace(hour=0, minute=0, second=0, microsecond=0):
        raise SufficiencyGovernanceError(
            "epoch_observation_start must be a canonical 00:00 UTC boundary"
        )
    rows: list[dict[str, str]] = []
    for cadence in _corpus.DECISION_CADENCES:
        observation_time = start
        step = _corpus.CADENCE_BAR_INTERVAL[cadence]
        while _corpus.decision_time_for(observation_time, cadence) <= current:
            rows.extend(
                _corpus.scheduled_decision_slots(
                    observation_time, observation_time, cadence=cadence
                )
            )
            observation_time += step
    return tuple(
        sorted(
            rows,
            key=lambda row: (row["decision_time"], row["cadence"], row["slot_id"]),
        )
    )


def _derive_blind_category(
    fact: Mapping[str, Any],
    *,
    warmup_complete: bool,
    decision_time: datetime,
) -> str:
    if not warmup_complete:
        return "WARMUP_INCOMPLETE"
    state = fact["evidence_state"]
    maximum_available_at = fact["maximum_available_at"]
    if state == "INVALID_CLOCK_OR_PIT_EVIDENCE":
        return "PIT_INVALID"
    if maximum_available_at is not None:
        available = datetime.fromisoformat(maximum_available_at)
        _require_utc(available, "maximum_available_at")
        if available > decision_time:
            return "PIT_INVALID"
    if state in {"SOURCE_UNAVAILABLE", "UNREPLAYABLE_EVIDENCE"}:
        return "SOURCE_UNAVAILABLE"
    if state == "DATA_QUALITY_FAIL":
        return "DATA_QUALITY_FAIL"
    if state == "REFERENCE_UNAVAILABLE":
        return "REFERENCE_UNAVAILABLE"
    if state != "AUTHORITATIVE_REPLAYED":
        raise SufficiencyGovernanceError("unknown authoritative replay state")
    if fact["universe_member"] is False:
        return "NOT_IN_UNIVERSE"
    if fact["universe_member"] is not True:
        raise SufficiencyGovernanceError("replayed universe membership is unresolved")
    if fact["comparable"] is False:
        return "NOT_COMPARABLE"
    if fact["comparable"] is not True:
        raise SufficiencyGovernanceError("replayed comparability is unresolved")
    return "EVALUATED"


class BlindEvidenceResolver:
    """Replay content-addressed blind source evidence into a coarse projection."""

    def __init__(self, records: Mapping[str, Mapping[str, Any]]) -> None:
        self._resolver = _source_integrity.PersistedEvidenceResolver(records=records)
        self._expected_bindings = _blind_parent_bindings()

    def replay(
        self,
        reference: BlindEvidenceReference,
        *,
        authorization: Mapping[str, Any],
        current_decision_time: datetime,
    ) -> ReplayedBlindProjection:
        if not isinstance(reference, BlindEvidenceReference):
            raise SufficiencyGovernanceError(
                "scientific monitor accepts BlindEvidenceReference only"
            )
        if not _is_sha256(reference.slot_id):
            raise SufficiencyGovernanceError("reference slot_id must be SHA-256")
        if reference.evaluation_epoch_authorization_sha256 != authorization.get(
            "record_sha256"
        ):
            raise SufficiencyGovernanceError("evidence references another epoch")
        try:
            envelope = self._resolver.resolve(
                reference.authoritative_evidence_record_sha256,
                schema_version=BLIND_PROJECTION_VERSION,
            )
            source = self._resolver.resolve(
                envelope["source_evidence_record_sha256"],
                schema_version=BLIND_SOURCE_RECORD_VERSION,
            )
        except _source_integrity.ProspectiveSourceIntegrityError as exc:
            raise SufficiencyGovernanceError(str(exc)) from exc
        _strict_keys(
            envelope,
            {
                "declared_blind_projection",
                "evaluation_epoch_authorization_sha256",
                "record_sha256",
                "schema_version",
                "slot_id",
                "source_evidence_record_sha256",
            },
            "blind projection envelope",
        )
        _strict_keys(
            source,
            {
                "cadence",
                "certified_corpus_sha256",
                "decision_time",
                "decision_universe_sha256",
                "evaluation_epoch_authorization_sha256",
                "metric_evidence_contract_sha256",
                "metric_facts",
                "observation_time",
                "record_available_at",
                "record_sha256",
                "schema_version",
                "slot_id",
                "warmup_history_complete",
                "warmup_history_definition_sha256",
            },
            "blind source evidence",
        )
        for key, expected in self._expected_bindings.items():
            if source.get(key) != expected:
                raise SufficiencyGovernanceError(f"source evidence has wrong {key}")
        auth_hash = authorization["record_sha256"]
        if source["evaluation_epoch_authorization_sha256"] != auth_hash:
            raise SufficiencyGovernanceError("source evidence has wrong epoch authority")
        if envelope["evaluation_epoch_authorization_sha256"] != auth_hash:
            raise SufficiencyGovernanceError("projection has wrong epoch authority")
        if envelope["slot_id"] != reference.slot_id or source["slot_id"] != reference.slot_id:
            raise SufficiencyGovernanceError("blind evidence slot identity mismatch")

        observation_time = _require_utc(
            datetime.fromisoformat(source["observation_time"]), "observation_time"
        )
        decision_time = _require_utc(
            datetime.fromisoformat(source["decision_time"]), "decision_time"
        )
        record_available_at = _require_utc(
            datetime.fromisoformat(source["record_available_at"]), "record_available_at"
        )
        current = _require_utc(current_decision_time, "current_decision_time")
        if record_available_at > current:
            raise SufficiencyGovernanceError("evidence record is unavailable at current time")
        cadence = source["cadence"]
        if cadence not in _corpus.DECISION_CADENCES:
            raise SufficiencyGovernanceError("source evidence has unknown cadence")
        expected_decision = _corpus.decision_time_for(observation_time, cadence)
        if decision_time != expected_decision:
            raise SufficiencyGovernanceError("decision_time does not reproduce")
        expected_slot = _corpus.scheduled_decision_slots(
            observation_time, observation_time, cadence=cadence
        )[0]
        if source["slot_id"] != expected_slot["slot_id"]:
            raise SufficiencyGovernanceError("slot_id does not reproduce")
        if type(source["warmup_history_complete"]) is not bool:
            raise SufficiencyGovernanceError("warmup state must be replayed Boolean")

        facts = source["metric_facts"]
        if not isinstance(facts, dict):
            raise SufficiencyGovernanceError("metric facts must be an object")
        required_metrics = {
            metric
            for metric, owner_cadence in _metric_cadences().items()
            if owner_cadence == cadence
        }
        if set(facts) != required_metrics:
            raise SufficiencyGovernanceError(
                "source evidence must cover every cadence-applicable metric"
            )
        categories: dict[str, str] = {}
        units: dict[str, str | None] = {}
        for metric in sorted(facts):
            fact = facts[metric]
            if not isinstance(fact, dict):
                raise SufficiencyGovernanceError("metric fact must be an object")
            _strict_keys(
                fact,
                {
                    "active_stop_identity",
                    "comparable",
                    "control_position_episode_sha256",
                    "evidence_state",
                    "maximum_available_at",
                    "metric",
                    "universe_member",
                },
                f"metric fact {metric}",
            )
            if fact["metric"] != metric:
                raise SufficiencyGovernanceError("metric fact identity mismatch")
            if fact["evidence_state"] not in AUTHORITATIVE_REPLAY_STATES:
                raise SufficiencyGovernanceError("metric fact has unknown replay state")
            for field in ("universe_member", "comparable"):
                if fact[field] is not None and type(fact[field]) is not bool:
                    raise SufficiencyGovernanceError(f"{field} must be Boolean or null")
            category = _derive_blind_category(
                fact,
                warmup_complete=source["warmup_history_complete"],
                decision_time=decision_time,
            )
            categories[metric] = category
            units[metric] = (
                _derive_dependence_unit_id(
                    metric,
                    slot_id=source["slot_id"],
                    control_position_episode_sha256=fact[
                        "control_position_episode_sha256"
                    ],
                    active_stop_identity=fact["active_stop_identity"],
                )
                if category == "EVALUATED"
                else None
            )
        declared = envelope["declared_blind_projection"]
        expected_projection = {
            metric: {
                "blind_category": categories[metric],
                "dependence_unit_id": units[metric],
            }
            for metric in sorted(categories)
        }
        if declared != expected_projection:
            raise SufficiencyGovernanceError(
                "declared projection differs from authoritative replay"
            )
        for row in declared.values():
            category = row["blind_category"]
            if category not in BLIND_CATEGORIES:
                raise SufficiencyGovernanceError(
                    "blind projection exposes outcome side channel"
                )
        return ReplayedBlindProjection(
            cadence=cadence,
            observation_time=observation_time,
            decision_time=decision_time,
            slot_id=source["slot_id"],
            source_record_sha256=source["record_sha256"],
            projection_record_sha256=envelope["record_sha256"],
            category_by_metric=categories,
            dependence_unit_by_metric=units,
        )


def build_synthetic_blind_evidence(
    expected_slot: Mapping[str, str],
    *,
    evaluation_epoch_authorization_sha256: str,
    evidence_state_by_metric: Mapping[str, str] | None = None,
    universe_member_by_metric: Mapping[str, bool | None] | None = None,
    comparable_by_metric: Mapping[str, bool | None] | None = None,
    maximum_available_at_by_metric: Mapping[str, datetime | None] | None = None,
    warmup_history_complete: bool = True,
    stop_episode_by_metric: Mapping[str, tuple[str, str]] | None = None,
) -> tuple[BlindEvidenceReference, dict[str, dict[str, Any]]]:
    """Build deterministic content records for explicitly synthetic tests only."""

    if not _is_sha256(evaluation_epoch_authorization_sha256):
        raise SufficiencyGovernanceError("synthetic evidence needs authorization hash")
    parent_bindings = _blind_parent_bindings()
    cadence = str(expected_slot["cadence"])
    observation_time = _require_utc(
        datetime.fromisoformat(expected_slot["observation_time"]), "observation_time"
    )
    decision_time = _require_utc(
        datetime.fromisoformat(expected_slot["decision_time"]), "decision_time"
    )
    metrics = {
        metric
        for metric, owner_cadence in _metric_cadences().items()
        if owner_cadence == cadence
    }
    states = dict(evidence_state_by_metric or {})
    universes = dict(universe_member_by_metric or {})
    comparability = dict(comparable_by_metric or {})
    availability = dict(maximum_available_at_by_metric or {})
    stop_episodes = dict(stop_episode_by_metric or {})
    facts: dict[str, dict[str, Any]] = {}
    for metric in sorted(metrics):
        state = states.get(metric, "AUTHORITATIVE_REPLAYED")
        universe = universes.get(metric, True)
        comparable = comparability.get(metric, True)
        available_at = availability.get(metric, decision_time)
        episode = stop_episodes.get(metric)
        if metric in _corpus.STOP_EVENT_METRICS and episode is None:
            episode = (
                _digest({"synthetic_control_position_episode": expected_slot["slot_id"]}),
                f"SYNTHETIC_ACTIVE_STOP_{expected_slot['slot_id']}",
            )
        facts[metric] = {
            "active_stop_identity": None if episode is None else episode[1],
            "comparable": comparable,
            "control_position_episode_sha256": None if episode is None else episode[0],
            "evidence_state": state,
            "maximum_available_at": (
                None
                if available_at is None
                else _require_utc(available_at, "available_at").isoformat()
            ),
            "metric": metric,
            "universe_member": universe,
        }
    source = _with_record_hash(
        {
            "cadence": cadence,
            "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
            "decision_time": decision_time.isoformat(),
            "decision_universe_sha256": parent_bindings["decision_universe_sha256"],
            "evaluation_epoch_authorization_sha256": (
                evaluation_epoch_authorization_sha256
            ),
            "metric_evidence_contract_sha256": parent_bindings[
                "metric_evidence_contract_sha256"
            ],
            "metric_facts": facts,
            "observation_time": observation_time.isoformat(),
            "record_available_at": decision_time.isoformat(),
            "schema_version": BLIND_SOURCE_RECORD_VERSION,
            "slot_id": expected_slot["slot_id"],
            "warmup_history_complete": warmup_history_complete,
            "warmup_history_definition_sha256": parent_bindings[
                "warmup_history_definition_sha256"
            ],
        }
    )
    derived: dict[str, dict[str, Any]] = {}
    for metric, fact in facts.items():
        category = _derive_blind_category(
            fact,
            warmup_complete=warmup_history_complete,
            decision_time=decision_time,
        )
        derived[metric] = {
            "blind_category": category,
            "dependence_unit_id": (
                _derive_dependence_unit_id(
                    metric,
                    slot_id=expected_slot["slot_id"],
                    control_position_episode_sha256=fact[
                        "control_position_episode_sha256"
                    ],
                    active_stop_identity=fact["active_stop_identity"],
                )
                if category == "EVALUATED"
                else None
            ),
        }
    envelope = _with_record_hash(
        {
            "declared_blind_projection": dict(sorted(derived.items())),
            "evaluation_epoch_authorization_sha256": (
                evaluation_epoch_authorization_sha256
            ),
            "schema_version": BLIND_PROJECTION_VERSION,
            "slot_id": expected_slot["slot_id"],
            "source_evidence_record_sha256": source["record_sha256"],
        }
    )
    reference = BlindEvidenceReference(
        slot_id=expected_slot["slot_id"],
        authoritative_evidence_record_sha256=envelope["record_sha256"],
        evaluation_epoch_authorization_sha256=(
            evaluation_epoch_authorization_sha256
        ),
    )
    return reference, {
        source["record_sha256"]: source,
        envelope["record_sha256"]: envelope,
    }


EPOCH_AUTHORIZATION_VERSION = "PROSPECTIVE_STAGE_B_EVALUATION_EPOCH_AUTHORIZATION_V1"
CUTOFF_RECORD_VERSION = "PROSPECTIVE_STAGE_B_SUFFICIENCY_CUTOFF_RECORD_V1"
EVALUATION_RESULT_IDENTITY_VERSION = "PROSPECTIVE_STAGE_B_EVALUATION_RESULT_IDENTITY_V1"
INITIAL_EPOCH_ID = "INITIAL_STAGE_B_EVALUATION_EPOCH"


def evaluation_epoch_contract() -> dict[str, Any]:
    payload = {
        "authorization_before_first_qualifying_observation": True,
        "authorization_bindings": [
            "blind_monitor_sha256",
            "certified_corpus_sha256",
            "coverage_policy_sha256",
            "epoch_observation_start",
            "evaluation_contract_sha256",
            "evaluation_epoch_id",
            "evidence_unit_policy_sha256",
            "sufficiency_governance_sha256",
            "temporal_policy_sha256",
        ],
        "evaluation_contract_definition_must_recompute": True,
        "initial_epoch_id": INITIAL_EPOCH_ID,
        "initial_epoch_unique": True,
        "postp1_004_persistent_transactional_enforcement_required": True,
        "schema_version": EPOCH_AUTHORIZATION_VERSION,
        "successor_epoch_permitted_automatically": False,
        "terminal_after_any_evaluation_result": True,
    }
    return _with_definition_hash(payload)


def evaluation_cutoff_contract() -> dict[str, Any]:
    payload = {
        "cutoff_definition": (
            "earliest decision_time where all eight raw minima, all eight "
            "distinct dependence-unit minima, all eight exact coverage floors, "
            "and complete scheduled-slot accounting hold"
        ),
        "cutoff_record_schema_version": CUTOFF_RECORD_VERSION,
        "evidence_after_cutoff_included": False,
        "evidence_manifest_content_addressed": True,
        "first_cutoff_immutable": True,
        "late_revision_moves_cutoff": False,
        "replay_source": "frozen authoritative evidence manifest",
        "required_bindings": [
            "authoritative_evidence_manifest_sha256",
            "certified_corpus_sha256",
            "coverage_policy_sha256",
            "cutoff_decision_time",
            "evaluation_contract_sha256",
            "evaluation_epoch_authorization_sha256",
            "evidence_unit_policy_sha256",
            "per_metric_counts",
            "sufficiency_governance_sha256",
            "temporal_policy_sha256",
            "window_start",
        ],
        "schema_version": "PROSPECTIVE_STAGE_B_EVALUATION_CUTOFF_CONTRACT_V1",
    }
    return _with_definition_hash(payload)


def evaluation_result_identity() -> dict[str, Any]:
    payload = {
        "candidate_control_identity_owner": "bound evaluation contract",
        "floating_pass_fail_result_permitted": False,
        "required_bindings": [
            "certified_corpus_sha256",
            "cutoff_record_sha256",
            "evaluation_contract_sha256",
            "evaluation_epoch_authorization_sha256",
            "sufficiency_governance_sha256",
        ],
        "schema_version": EVALUATION_RESULT_IDENTITY_VERSION,
        "terminal_results": ["FAIL", "PASS"],
    }
    return _with_definition_hash(payload)


def stopping_rule() -> dict[str, Any]:
    payload = {
        "collection_stop_condition": (
            "ALL eight raw minima AND all eight distinct dependence-unit minima "
            "AND all eight 0.99 coverage floors AND 100 percent scheduled-slot "
            "accounting with zero unaccounted slots"
        ),
        "global_metric_rule": "ALL_8_NO_WEIGHTING_NO_SUBSTITUTION",
        "metric_numerators_consumed": False,
        "optional_stopping_permitted": False,
        "outcome_blind": True,
        "pass_chasing_permitted": False,
        "performance_results_consumed": False,
        "same_epoch_extension_after_evaluation_permitted": False,
        "schema_version": "PROSPECTIVE_STAGE_B_STOPPING_RULE_V1",
        "successor_epoch_permitted_automatically": False,
    }
    return _with_definition_hash(payload)


class EvaluationEpochRegistry:
    """Stateful reference owner; POSTP1-004 must persist it transactionally."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._authorization_by_hash: dict[str, dict[str, Any]] = {}
        self._authorization_by_governance: dict[tuple[str, str], str] = {}
        self._cutoff_by_authorization: dict[str, dict[str, Any]] = {}
        self._manifest_by_hash: dict[str, tuple[dict[str, str], ...]] = {}
        self._progress_by_authorization: dict[str, dict[str, Any]] = {}
        self._terminal_result_by_authorization: dict[str, dict[str, Any]] = {}

    def authorize_initial_epoch(
        self,
        *,
        evaluation_contract: Mapping[str, Any],
        epoch_observation_start: datetime,
        evaluation_epoch_id: str = INITIAL_EPOCH_ID,
    ) -> dict[str, Any]:
        if evaluation_epoch_id != INITIAL_EPOCH_ID:
            raise SufficiencyGovernanceError("arbitrary evaluation epoch IDs are forbidden")
        evaluation_contract_sha256 = _verify_hashed_definition(
            evaluation_contract, "evaluation contract"
        )
        start = _require_utc(epoch_observation_start, "epoch_observation_start")
        if start != start.replace(hour=0, minute=0, second=0, microsecond=0):
            raise SufficiencyGovernanceError(
                "epoch observation start must be a canonical UTC-day boundary"
            )
        definition = sufficiency_governance_definition()
        coverage = coverage_policy()
        temporal = temporal_policy()
        units = evidence_unit_policy()
        blind = blind_monitor_contract()
        record = _with_record_hash(
            {
                "blind_monitor_sha256": blind["definition_sha256"],
                "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
                "coverage_policy_sha256": coverage["definition_sha256"],
                "epoch_observation_start": start.isoformat(),
                "evaluation_contract_sha256": evaluation_contract_sha256,
                "evaluation_epoch_id": evaluation_epoch_id,
                "evidence_unit_policy_sha256": units["definition_sha256"],
                "schema_version": EPOCH_AUTHORIZATION_VERSION,
                "sufficiency_governance_sha256": definition["definition_sha256"],
                "temporal_policy_sha256": temporal["definition_sha256"],
            }
        )
        governance_key = (CERTIFIED_CORPUS_SHA256, definition["definition_sha256"])
        with self._lock:
            existing_hash = self._authorization_by_governance.get(governance_key)
            if existing_hash is not None:
                existing = self._authorization_by_hash[existing_hash]
                if existing != record:
                    raise SufficiencyGovernanceError(
                        "this corpus/governance already has its unique initial epoch"
                    )
                return dict(existing)
            self._authorization_by_governance[governance_key] = record["record_sha256"]
            self._authorization_by_hash[record["record_sha256"]] = record
        return dict(record)

    def authorization(self, record_sha256: str) -> dict[str, Any]:
        with self._lock:
            try:
                return dict(self._authorization_by_hash[record_sha256])
            except KeyError as exc:
                raise SufficiencyGovernanceError(
                    "evaluation epoch lacks persisted authorization"
                ) from exc

    def frozen_progress(self, authorization_sha256: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._progress_by_authorization.get(authorization_sha256)
            return None if row is None else dict(row)

    def freeze_cutoff(
        self,
        authorization_sha256: str,
        cutoff: Mapping[str, Any],
        manifest_rows: Sequence[Mapping[str, str]],
        progress: Mapping[str, Any],
    ) -> dict[str, Any]:
        frozen_manifest = tuple(dict(row) for row in manifest_rows)
        manifest_sha256 = cutoff.get("authoritative_evidence_manifest_sha256")
        if _digest(list(frozen_manifest)) != manifest_sha256:
            raise SufficiencyGovernanceError("cutoff evidence manifest does not reproduce")
        with self._lock:
            if authorization_sha256 in self._terminal_result_by_authorization:
                raise EvaluationEpochFrozenError("evaluation epoch is terminal")
            existing = self._cutoff_by_authorization.get(authorization_sha256)
            if existing is not None:
                if existing != dict(cutoff):
                    raise EvaluationEpochFrozenError("first cutoff record is immutable")
                return dict(existing)
            self._cutoff_by_authorization[authorization_sha256] = dict(cutoff)
            self._manifest_by_hash[str(manifest_sha256)] = frozen_manifest
            self._progress_by_authorization[authorization_sha256] = dict(progress)
            return dict(cutoff)

    def cutoff(self, authorization_sha256: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._cutoff_by_authorization.get(authorization_sha256)
            return None if row is None else dict(row)

    def evidence_manifest(self, manifest_sha256: str) -> tuple[dict[str, str], ...]:
        with self._lock:
            try:
                return tuple(
                    dict(row) for row in self._manifest_by_hash[manifest_sha256]
                )
            except KeyError as exc:
                raise SufficiencyGovernanceError(
                    "frozen evidence manifest is not persisted"
                ) from exc

    def persist_evaluation_result(
        self,
        *,
        authorization_sha256: str,
        result: str,
    ) -> dict[str, Any]:
        if result not in ("PASS", "FAIL"):
            raise SufficiencyGovernanceError("evaluation result must be PASS or FAIL")
        with self._lock:
            authorization = self.authorization(authorization_sha256)
            cutoff = self._cutoff_by_authorization.get(authorization_sha256)
            if cutoff is None:
                raise SufficiencyGovernanceError("result requires a frozen cutoff")
            if authorization_sha256 in self._terminal_result_by_authorization:
                raise EvaluationEpochFrozenError("evaluation epoch is already terminal")
            definition = sufficiency_governance_definition()
            record = _with_record_hash(
                {
                    "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
                    "cutoff_record_sha256": cutoff["record_sha256"],
                    "evaluation_contract_sha256": authorization[
                        "evaluation_contract_sha256"
                    ],
                    "evaluation_epoch_authorization_sha256": authorization_sha256,
                    "result": result,
                    "schema_version": EVALUATION_RESULT_IDENTITY_VERSION,
                    "sufficiency_governance_sha256": definition["definition_sha256"],
                    "terminal": True,
                }
            )
            self._terminal_result_by_authorization[authorization_sha256] = record
            return dict(record)

    def is_terminal(self, authorization_sha256: str) -> bool:
        with self._lock:
            return authorization_sha256 in self._terminal_result_by_authorization


def _iso_week(value: datetime) -> str:
    year, week, _weekday = value.isocalendar()
    return f"{year:04d}-W{week:02d}"


def _empty_metric_counter() -> dict[str, Any]:
    return {
        "authoritative_coverage_denominator": 0,
        "authoritative_coverage_numerator": 0,
        "blind_category_counts": Counter(),
        "day_contributions": Counter(),
        "dependence_unit_contributions": Counter(),
        "first_evidence_time": None,
        "last_evidence_time": None,
        "raw_sufficiency_denominator": 0,
        "week_contributions": Counter(),
    }


def _add_projection(
    counter: dict[str, Any],
    *,
    category: str,
    dependence_unit_id: str | None,
    decision_time: datetime,
) -> None:
    counter["blind_category_counts"][category] += 1
    if category in _COVERED_CATEGORIES:
        counter["authoritative_coverage_numerator"] += 1
    if category != "EVALUATED":
        return
    if not _is_sha256(dependence_unit_id):
        raise SufficiencyGovernanceError("evaluated evidence lacks dependence identity")
    counter["raw_sufficiency_denominator"] += 1
    counter["dependence_unit_contributions"][dependence_unit_id] += 1
    counter["day_contributions"][decision_time.date().isoformat()] += 1
    counter["week_contributions"][_iso_week(decision_time)] += 1
    timestamp = decision_time.isoformat()
    if counter["first_evidence_time"] is None:
        counter["first_evidence_time"] = timestamp
    counter["last_evidence_time"] = timestamp


def _metric_satisfied(counter: Mapping[str, Any], required: int) -> bool:
    return (
        int(counter["raw_sufficiency_denominator"]) >= required
        and len(counter["dependence_unit_contributions"]) >= required
        and authoritative_coverage_satisfied(
            int(counter["authoritative_coverage_numerator"]),
            int(counter["authoritative_coverage_denominator"]),
        )
    )


def _materialize_metric_state(
    metric: str,
    counter: Mapping[str, Any],
    *,
    required: int,
) -> dict[str, Any]:
    days: Counter[str] = counter["day_contributions"]
    weeks: Counter[str] = counter["week_contributions"]
    units: Counter[str] = counter["dependence_unit_contributions"]
    coverage_numerator = int(counter["authoritative_coverage_numerator"])
    coverage_denominator = int(counter["authoritative_coverage_denominator"])
    coverage_ok = authoritative_coverage_satisfied(
        coverage_numerator, coverage_denominator
    )
    raw = int(counter["raw_sufficiency_denominator"])
    effective = len(units)
    return {
        "authoritative_coverage_denominator": coverage_denominator,
        "authoritative_coverage_floor": "0.99",
        "authoritative_coverage_numerator": coverage_numerator,
        "authoritative_coverage_satisfied": coverage_ok,
        "blind_category_counts": dict(sorted(counter["blind_category_counts"].items())),
        "distinct_dependence_unit_count": effective,
        "distinct_iso_weeks": len(weeks),
        "distinct_utc_days": len(days),
        "effective_dependence_unit_count": effective,
        "first_evidence_time": counter["first_evidence_time"],
        "largest_dependence_unit_raw_contribution": max(units.values(), default=0),
        "largest_single_day_contribution": max(days.values(), default=0),
        "largest_single_week_contribution": max(weeks.values(), default=0),
        "last_evidence_time": counter["last_evidence_time"],
        "metric": metric,
        "minimum_distinct_dependence_units": required,
        "minimum_raw_sufficiency_denominator": required,
        "raw_sufficiency_denominator": raw,
        "sufficient": _metric_satisfied(counter, required),
    }


def evaluate_blind_sufficiency(
    evidence_references: Sequence[BlindEvidenceReference],
    *,
    resolver: BlindEvidenceResolver,
    registry: EvaluationEpochRegistry,
    evaluation_epoch_authorization_sha256: str,
    current_decision_time: datetime,
) -> dict[str, Any]:
    """Derive and statefully freeze the earliest outcome-blind cutoff."""

    if not isinstance(resolver, BlindEvidenceResolver):
        raise SufficiencyGovernanceError("certified BlindEvidenceResolver required")
    if not isinstance(registry, EvaluationEpochRegistry):
        raise SufficiencyGovernanceError("stateful EvaluationEpochRegistry required")
    authorization = registry.authorization(evaluation_epoch_authorization_sha256)
    if registry.is_terminal(evaluation_epoch_authorization_sha256):
        raise EvaluationEpochFrozenError("evaluation epoch is terminal")
    frozen = registry.frozen_progress(evaluation_epoch_authorization_sha256)
    if frozen is not None:
        return frozen
    current = _require_utc(current_decision_time, "current_decision_time")
    start = _require_utc(
        datetime.fromisoformat(authorization["epoch_observation_start"]),
        "epoch_observation_start",
    )
    if current < start:
        raise SufficiencyGovernanceError("current time precedes epoch start")
    expected = _expected_slots_through(start, current)
    expected_by_id = {row["slot_id"]: row for row in expected}

    records: dict[str, ReplayedBlindProjection] = {}
    for reference in evidence_references:
        projection = resolver.replay(
            reference,
            authorization=authorization,
            current_decision_time=current,
        )
        if projection.slot_id not in expected_by_id:
            raise SufficiencyGovernanceError("evidence lies outside epoch census")
        if projection.slot_id in records:
            raise SufficiencyGovernanceError("scheduled slot has multiple evidence records")
        records[projection.slot_id] = projection

    minima_definition = metric_sufficiency_minima()
    minima = minima_definition["metrics"]
    counters = {metric: _empty_metric_counter() for metric in _corpus.TARGET_METRICS}
    expected_by_time: dict[datetime, list[dict[str, str]]] = defaultdict(list)
    for row in expected:
        expected_by_time[datetime.fromisoformat(row["decision_time"])].append(row)

    cutoff: datetime | None = None
    expected_prefix = 0
    accounted_prefix = 0
    manifest_rows: list[dict[str, str]] = []
    cadences = _metric_cadences()
    for decision_time in sorted(expected_by_time):
        group = expected_by_time[decision_time]
        expected_prefix += len(group)
        for expected_row in group:
            applicable = [
                metric
                for metric, cadence in cadences.items()
                if cadence == expected_row["cadence"]
            ]
            for metric in applicable:
                counters[metric]["authoritative_coverage_denominator"] += 1
            record = records.get(expected_row["slot_id"])
            if record is None:
                continue
            accounted_prefix += 1
            manifest_rows.append(
                {
                    "projection_record_sha256": record.projection_record_sha256,
                    "slot_id": record.slot_id,
                    "source_record_sha256": record.source_record_sha256,
                }
            )
            for metric in applicable:
                _add_projection(
                    counters[metric],
                    category=record.category_by_metric[metric],
                    dependence_unit_id=record.dependence_unit_by_metric[metric],
                    decision_time=decision_time,
                )
        all_metrics = all(
            _metric_satisfied(
                counters[metric],
                int(minima[metric]["minimum_raw_sufficiency_denominator"]),
            )
            for metric in _corpus.TARGET_METRICS
        )
        if all_metrics and accounted_prefix == expected_prefix:
            cutoff = decision_time
            break

    if cutoff is None:
        accounting_expected = len(expected)
        accounting_accounted = len(records)
    else:
        accounting_expected = expected_prefix
        accounting_accounted = accounted_prefix
    metric_states = {
        metric: _materialize_metric_state(
            metric,
            counters[metric],
            required=int(minima[metric]["minimum_raw_sufficiency_denominator"]),
        )
        for metric in _corpus.TARGET_METRICS
    }
    all_metric_specific = all(row["sufficient"] for row in metric_states.values())
    unaccounted = accounting_expected - accounting_accounted
    overall_sufficient = cutoff is not None and unaccounted == 0

    definition = sufficiency_governance_definition()
    coverage = coverage_policy()
    temporal = temporal_policy()
    units = evidence_unit_policy()
    blind = blind_monitor_contract()
    result: dict[str, Any] = {
        "accounting": {
            "accounted_scheduled_slots": accounting_accounted,
            "scheduled_slots": accounting_expected,
            "unaccounted_scheduled_slots": unaccounted,
        },
        "blind_monitor_sha256": blind["definition_sha256"],
        "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
        "coverage_policy_sha256": coverage["definition_sha256"],
        "current_decision_time": current.isoformat(),
        "decision_universe_sha256": minima_definition["decision_universe_sha256"],
        "evaluation_contract_sha256": authorization["evaluation_contract_sha256"],
        "evaluation_epoch_authorization_sha256": (
            evaluation_epoch_authorization_sha256
        ),
        "evidence_unit_policy_sha256": units["definition_sha256"],
        "global_condition": "ALL_8_RAW_AND_UNITS_AND_COVERAGE_AND_ACCOUNTING",
        "governance_sha256": definition["definition_sha256"],
        "metric_evidence_contract_sha256": next(iter(minima.values()))[
            "metric_evidence_contract_sha256"
        ],
        "metric_states": metric_states,
        "overall_stage_b_status": (
            "READY_FOR_STAGE_B_EVALUATION"
            if overall_sufficient
            else "INSUFFICIENT_EVIDENCE"
        ),
        "overall_sufficient": overall_sufficient,
        "schema_version": "PROSPECTIVE_STAGE_B_SUFFICIENCY_RESULT_V1",
        "stage_b_sufficiency_cutoff": None if cutoff is None else cutoff.isoformat(),
        "state": (
            "EVALUATION_CUTOFF_FROZEN"
            if overall_sufficient
            else (
                "ALL_METRICS_SUFFICIENT"
                if all_metric_specific
                else (
                    "METRIC_PARTIALLY_SUFFICIENT"
                    if any(row["sufficient"] for row in metric_states.values())
                    else ("ACCUMULATING" if records else "NOT_STARTED")
                )
            )
        ),
        "temporal_policy_sha256": temporal["definition_sha256"],
        "window_start": start.isoformat(),
    }
    if cutoff is None:
        result["authoritative_evidence_manifest_sha256"] = None
        result["cutoff_record_sha256"] = None
        result["result_sha256"] = _digest(result)
        return result

    manifest_rows = sorted(manifest_rows, key=lambda row: row["slot_id"])
    manifest_sha256 = _digest(manifest_rows)
    cutoff_record = _with_record_hash(
        {
            "accounting": result["accounting"],
            "authoritative_evidence_manifest_sha256": manifest_sha256,
            "blind_monitor_sha256": blind["definition_sha256"],
            "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
            "coverage_policy_sha256": coverage["definition_sha256"],
            "cutoff_decision_time": cutoff.isoformat(),
            "evaluation_contract_sha256": authorization["evaluation_contract_sha256"],
            "evaluation_epoch_authorization_sha256": (
                evaluation_epoch_authorization_sha256
            ),
            "evidence_unit_policy_sha256": units["definition_sha256"],
            "per_metric_counts": {
                metric: {
                    "authoritative_coverage_denominator": row[
                        "authoritative_coverage_denominator"
                    ],
                    "authoritative_coverage_numerator": row[
                        "authoritative_coverage_numerator"
                    ],
                    "distinct_dependence_unit_count": row[
                        "distinct_dependence_unit_count"
                    ],
                    "raw_sufficiency_denominator": row[
                        "raw_sufficiency_denominator"
                    ],
                }
                for metric, row in metric_states.items()
            },
            "schema_version": CUTOFF_RECORD_VERSION,
            "sufficiency_governance_sha256": definition["definition_sha256"],
            "temporal_policy_sha256": temporal["definition_sha256"],
            "window_start": start.isoformat(),
        }
    )
    result["authoritative_evidence_manifest_sha256"] = manifest_sha256
    result["cutoff_record_sha256"] = cutoff_record["record_sha256"]
    result["result_sha256"] = _digest(result)
    registry.freeze_cutoff(
        evaluation_epoch_authorization_sha256,
        cutoff_record,
        manifest_rows,
        result,
    )
    return result


def assert_evaluation_epoch_not_extended(
    *,
    frozen_cutoff: datetime,
    proposed_cutoff: datetime,
    evaluated_result: str,
) -> None:
    """Compatibility guard; the registry is the authoritative stateful owner."""

    frozen = _require_utc(frozen_cutoff, "frozen_cutoff")
    proposed = _require_utc(proposed_cutoff, "proposed_cutoff")
    if evaluated_result not in ("PASS", "FAIL"):
        raise SufficiencyGovernanceError("evaluated_result must be PASS or FAIL")
    if proposed != frozen:
        raise EvaluationEpochFrozenError("evaluated Stage-B epoch is terminal")


_CHILD_ARTIFACTS = (
    (BLIND_MONITOR_FILENAME, "blind_monitor_contract", "blind_monitor_contract"),
    (
        COMMON_RATE_FILENAME,
        "common_rate_evidence_strength",
        "common_rate_evidence_strength",
    ),
    (COVERAGE_FILENAME, "coverage_policy", "coverage_policy"),
    (CUTOFF_FILENAME, "evaluation_cutoff_contract", "evaluation_cutoff_contract"),
    (EPOCH_FILENAME, "evaluation_epoch_contract", "evaluation_epoch_contract"),
    (
        RESULT_IDENTITY_FILENAME,
        "evaluation_result_identity",
        "evaluation_result_identity",
    ),
    (EVIDENCE_UNIT_FILENAME, "evidence_unit_policy", "evidence_unit_policy"),
    (MINIMA_FILENAME, "metric_sufficiency_minima", "metric_sufficiency_minima"),
    (P95_FILENAME, "p95_tail_repeatability", "p95_tail_repeatability"),
    (
        SEMANTIC_DIFF_FILENAME,
        "semantic_diff_from_stage_b_gates",
        "semantic_diff_from_stage_b_gates",
    ),
    (DERIVATIONS_FILENAME, "statistical_derivations", "statistical_derivations"),
    (STOPPING_RULE_FILENAME, "stopping_rule", "stopping_rule"),
    (TEMPORAL_FILENAME, "temporal_policy", "temporal_policy"),
)


def _child_payloads() -> dict[str, dict[str, Any]]:
    return {
        filename: globals()[builder]()
        for filename, _child_key, builder in _CHILD_ARTIFACTS
    }


def sufficiency_governance_definition() -> dict[str, Any]:
    protocol = _require_certified_corpus()
    children = _child_payloads()
    child_hashes = {
        child_key: children[filename]["definition_sha256"]
        for filename, child_key, _builder in _CHILD_ARTIFACTS
    }
    payload = {
        "btc019": {
            "reopened": False,
            "sealed_sample_accessed": False,
            "terminal": True,
        },
        "certified_parent": {
            "implementation_commit": CERTIFIED_CORPUS_IMPLEMENTATION_COMMIT,
            "material_child_count": protocol["material_child_count"],
            "protocol_sha256": CERTIFIED_CORPUS_SHA256,
            "protocol_version": CERTIFIED_CORPUS_VERSION,
            "review_fix_commit": CERTIFIED_CORPUS_REVIEW_FIX_COMMIT,
            "review_result": CERTIFIED_CORPUS_REVIEW_RESULT,
            "review_ticket": CERTIFIED_CORPUS_REVIEW_TICKET,
        },
        "child_definition_sha256": dict(sorted(child_hashes.items())),
        "collection_authorized": False,
        "decimal_precision": _DECIMAL_CONTEXT.prec,
        "epic_t": {"modified": False, "reopened": False},
        "failed_governance_lineage": [
            {
                "authoritative": False,
                "definition_sha256": FAILED_GOVERNANCE_SHA256,
                "implementation_commit": FAILED_GOVERNANCE_IMPLEMENTATION_COMMIT,
                "prospective_observations_collected": False,
                "review_classification": FAILED_GOVERNANCE_CLASSIFICATION,
                "review_documentation_commit": (
                    FAILED_GOVERNANCE_REVIEW_DOCUMENTATION_COMMIT
                ),
                "review_result": FAILED_GOVERNANCE_REVIEW_RESULT,
                "superseded_before_collection": True,
            }
        ],
        "final_classification": FINAL_CLASSIFICATION,
        "governance_version": GOVERNANCE_VERSION,
        "material_child_count": len(child_hashes),
        "material_child_enumeration": "single mechanical artifact registry",
        "parent_child_bindings": {
            "decision_universe_sha256": protocol["child_definition_sha256"][
                "decision_universe"
            ],
            "metric_evidence_contract_sha256": protocol[
                "child_definition_sha256"
            ]["metric_evidence_contracts"],
            "scientific_evidence_resolver_sha256": protocol[
                "child_definition_sha256"
            ]["scientific_evidence_resolver"],
            "stage_b_evaluation_contract_sha256": protocol[
                "child_definition_sha256"
            ]["stage_b_evaluation_contract"],
            "warmup_history_definition_sha256": protocol[
                "child_definition_sha256"
            ]["warmup_history"],
        },
        "postp1_004_authorized": False,
        "program_ticket": PROGRAM_TICKET,
        "safety": {
            "btc019_sealed_data_accessed": False,
            "prospective_observations_collected": False,
            "real_stage_b_evaluation_run": False,
            "real_stage_b_numerators_inspected": False,
        },
        "schema_version": GOVERNANCE_SCHEMA_VERSION,
        "stage_b_performance_gate_owner": _corpus.HISTORICAL_GATE_AUTHORITY,
        "stage_b_performance_gates_changed": False,
        "status": GOVERNANCE_STATUS,
        "target_metrics": list(_corpus.TARGET_METRICS),
        "version_retained_rationale": (
            "The failed definition was never certified, no collection began, and "
            "the failed exact hash remains explicit non-authoritative lineage."
        ),
        "workstream": WORKSTREAM,
    }
    definition = _with_definition_hash(payload)
    if definition["definition_sha256"] == FAILED_GOVERNANCE_SHA256:
        raise SufficiencyGovernanceError("corrected governance hash did not move")
    return definition


def protocol_hashes() -> dict[str, str]:
    definition = sufficiency_governance_definition()
    hashes = dict(definition["child_definition_sha256"])
    hashes["sufficiency_governance"] = definition["definition_sha256"]
    return dict(sorted(hashes.items()))


def verify_sufficiency_governance_definition(persisted: Mapping[str, Any]) -> None:
    expected = sufficiency_governance_definition()
    if dict(persisted) != expected:
        raise SufficiencyGovernanceError("persisted governance does not reproduce")
    _verify_hashed_definition(persisted, "sufficiency governance")


def _report_markdown(definition: Mapping[str, Any]) -> str:
    minima = metric_sufficiency_minima()["metrics"]
    diff = semantic_diff_from_stage_b_gates()
    p95 = p95_tail_repeatability()
    lines = [
        f"# {GOVERNANCE_VERSION}",
        "",
        f"- Ticket: {PROGRAM_TICKET}",
        f"- Status: {GOVERNANCE_STATUS}",
        f"- Definition hash: {definition['definition_sha256']}",
        f"- Final classification: {FINAL_CLASSIFICATION}",
        f"- Certified corpus: {CERTIFIED_CORPUS_SHA256}",
        f"- Failed predecessor: {FAILED_GOVERNANCE_SHA256} (non-authoritative)",
        f"- Material child count: {definition['material_child_count']}",
        "- Prospective observations collected: NO",
        "- Real Stage-B evaluation run: NO",
        "- POSTP1-004 authorized: NO",
        "- Prospective collection authorized: NO",
        "- BTC-019 reopened / sealed sample touched: NO / NO",
        "",
        "## Material children",
        "",
    ]
    for name, digest in definition["child_definition_sha256"].items():
        lines.append(f"- {name}: {digest}")
    lines += [
        "",
        "## Historical parity",
        "",
        f"- Threshold changes: {diff['threshold_change_count']}",
        f"- Direction changes: {diff['direction_change_count']}",
        f"- Hard-role changes: {diff['hard_role_change_count']}",
        f"- Metric-intent changes: {diff['metric_intent_change_count']}",
        "",
        "## Corrected sufficiency minima",
        "",
        "| metric | performance threshold | raw minimum | distinct-unit minimum |",
        "| --- | ---: | ---: | ---: |",
    ]
    for metric in _corpus.TARGET_METRICS:
        row = minima[metric]
        lines.append(
            f"| {metric} | {row['performance_threshold']} | "
            f"{row['minimum_raw_sufficiency_denominator']} | "
            f"{row['minimum_distinct_dependence_units']} |"
        )
    lines += [
        "",
        "The exact 1.0 performance threshold remains exactly 1.0. Its common "
        "evidence-strength reference is 0.99, not a replacement performance gate; "
        "380 all-success independent units fail and 381 pass evidence quantity.",
        "",
        "Nearest-rank p95 remains unchanged. Repeatable tail evidence requires "
        f"93 distinct sizing opportunities: P92={p95['n_92']['probability']} and "
        f"P93={p95['n_93']['probability']}.",
        "",
        "Every metric independently requires exact authoritative replay coverage "
        "of at least 0.99. Natural evidence units govern dependence; no separate "
        "arbitrary calendar minimum or Stage-C 90-day rule is imported.",
        "",
        "The blind monitor consumes only content-addressed evidence references and "
        "a persisted initial-epoch authorization. It replays warmup, PIT, universe, "
        "disposition and dependence identity, freezes an evidence manifest at the "
        "first sufficient cutoff, and makes PASS and FAIL terminal.",
        "",
        f"Final classification: {FINAL_CLASSIFICATION}",
        "",
    ]
    return "\n".join(lines)


def write_artifacts(output_dir: Path) -> dict[str, Any]:
    definition = sufficiency_governance_definition()
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {DEFINITION_FILENAME: definition, **_child_payloads()}
    expected_files = set(payloads) | {REPORT_FILENAME}
    for existing in output_dir.iterdir():
        if existing.is_file() and existing.name not in expected_files:
            existing.unlink()
    for filename, payload in payloads.items():
        (output_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="ascii",
        )
    (output_dir / REPORT_FILENAME).write_text(
        _report_markdown(definition), encoding="utf-8"
    )
    return definition


def restore_artifacts(output_dir: Path) -> dict[str, Any]:
    definition = json.loads(
        (output_dir / DEFINITION_FILENAME).read_text(encoding="ascii")
    )
    verify_sufficiency_governance_definition(definition)
    expected_files = {DEFINITION_FILENAME, REPORT_FILENAME}
    for filename, child_key, builder in _CHILD_ARTIFACTS:
        expected_files.add(filename)
        persisted = json.loads((output_dir / filename).read_text(encoding="ascii"))
        expected = globals()[builder]()
        if persisted != expected:
            raise SufficiencyGovernanceError(f"persisted {filename} does not reproduce")
        if definition["child_definition_sha256"].get(child_key) != expected[
            "definition_sha256"
        ]:
            raise SufficiencyGovernanceError(f"top-level does not bind {filename}")
    actual_files = {path.name for path in output_dir.iterdir() if path.is_file()}
    if actual_files != expected_files:
        raise SufficiencyGovernanceError("artifact directory has unbound files")
    if (output_dir / REPORT_FILENAME).read_text(encoding="utf-8") != _report_markdown(
        definition
    ):
        raise SufficiencyGovernanceError("persisted report does not reproduce")
    return definition


def main() -> None:  # pragma: no cover
    root = Path(__file__).resolve().parents[2]
    definition = write_artifacts(root / OUTPUT_NAMESPACE)
    print(definition["definition_sha256"])


if __name__ == "__main__":  # pragma: no cover
    main()
