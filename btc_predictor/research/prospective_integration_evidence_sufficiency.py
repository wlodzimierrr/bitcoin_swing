"""Corrected pre-data sufficiency governance for prospective Stage-B evidence.

POSTP1-003R2 never collects evidence or consumes a numerator, target outcome,
relative-difference value, or PASS/FAIL result while determining sufficiency.
It binds the certified prospective corpus, separates the three relevant count
types, and owns a stateful reference contract for future POSTP1-004 persistence.
The scientific monitor accepts only content-addressed certified-parent manifests
and derives every blind fact by transitive replay.  Blind projections, cutoff
records and evaluation contracts are cached results, never self-authenticating
scientific authorities.
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
GOVERNANCE_STATUS = "R2_CORRECTED_FROZEN_PRE_DATA_SUFFICIENCY_GOVERNANCE"
PROGRAM_TICKET = "POSTP1-003R2"
WORKSTREAM = "EPIC X"
FINAL_CLASSIFICATION = (
    "PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1_"
    "READY_FOR_FINAL_XHIGH_REVIEW"
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

FAILED_R1_GOVERNANCE_SHA256 = (
    "0ca7a2a8487e9c54b1b0f5ad07201ec39dfd20b328b5e09cb3b51b0de86c8242"
)
FAILED_R1_GOVERNANCE_IMPLEMENTATION_COMMIT = (
    "8540e80e58511818eaa2ce4d976470a405234a53"
)
FAILED_R1_GOVERNANCE_REVIEW_DOCUMENTATION_COMMIT = (
    "1342ff9eca04d254bf17566dcc80b5796310af92"
)
FAILED_R1_GOVERNANCE_REVIEW_RESULT = (
    "FAIL — CORRECTED SUFFICIENCY GOVERNANCE INVALID"
)
FAILED_R1_GOVERNANCE_CLASSIFICATION = "SUFFICIENCY_GOVERNANCE_REQUIRES_FIX"

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
BLIND_PARENT_MANIFEST_FILENAME = "certified_blind_parent_evidence_manifest.json"
BLIND_REPLAY_FILENAME = "blind_replay_derivation_contract.json"
BLIND_CATEGORY_FILENAME = "blind_category_mapping.json"
EVALUATION_CONTRACT_SCHEMA_FILENAME = "evaluation_contract_schema.json"
EPOCH_FILENAME = "evaluation_epoch_contract.json"
CUTOFF_FILENAME = "evaluation_cutoff_contract.json"
CUTOFF_VALIDATION_FILENAME = "cutoff_replay_validation_contract.json"
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


def _verify_record_hash(payload: Mapping[str, Any], name: str) -> str:
    row = dict(payload)
    declared = row.pop("record_sha256", None)
    if not _is_sha256(declared) or _source_integrity.digest(row) != declared:
        raise SufficiencyGovernanceError(f"{name} must carry its real record SHA-256")
    return declared


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
            kind = "CONTROL_POSITION_ROOT_LIFECYCLE_EPISODE"
            owner = (
                "certified control portfolio lifecycle hash chain; the root "
                "opening transition of one economic control position"
            )
            derivation = (
                "sha256(policy version, metric name, certified corpus hash, "
                "replayed control position root opening-transition SHA-256)"
            )
            fields = {
                "control_position_root_opening_transition_sha256": (
                    "derived only by replaying the control portfolio prior-state "
                    "hash chain to the opening transition of the current episode"
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
        "stop_active_identity_membership_only": True,
        "stop_active_identity_part_of_dependence_unit": False,
        "stop_move_creates_new_dependence_unit": False,
        "schema_version": EVIDENCE_UNIT_POLICY_ID,
    }
    return _with_definition_hash(payload)


def _derive_dependence_unit_id(
    metric: str,
    *,
    slot_id: str,
    control_position_episode_sha256: str | None,
    active_stop_identity: str | None = None,
) -> str:
    if metric in _corpus.STOP_EVENT_METRICS:
        if not _is_sha256(control_position_episode_sha256):
            raise SufficiencyGovernanceError(
                "stop evidence lacks a replayed control position episode identity"
            )
        return _digest(
            {
                "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
                "control_position_root_opening_transition_sha256": (
                    control_position_episode_sha256
                ),
                "metric_name": metric,
                "policy_version": EVIDENCE_UNIT_POLICY_ID,
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
BLIND_PARENT_MANIFEST_VERSION = "CERTIFIED_BLIND_PARENT_EVIDENCE_MANIFEST_V1"
BLIND_REPLAY_CONTRACT_VERSION = "CERTIFIED_BLIND_EVIDENCE_REPLAY_V1"
BLIND_CATEGORY_MAPPING_VERSION = "PROSPECTIVE_STAGE_B_BLIND_CATEGORY_MAPPING_V1"
PARENT_INPUT_RECORD_VERSION = "CERTIFIED_PARENT_INPUT_EVIDENCE_V1"
PARENT_WARMUP_RECORD_VERSION = "CERTIFIED_PARENT_WARMUP_REPLAY_EVIDENCE_V1"
PARENT_METRIC_RECORD_VERSION = "CERTIFIED_PARENT_METRIC_OWNER_EVIDENCE_V1"
PARENT_PORTFOLIO_STATE_VERSION = "CERTIFIED_PARENT_PORTFOLIO_STATE_EVIDENCE_V1"
PARENT_TRADE_ACTION_VERSION = "CERTIFIED_PARENT_TRADE_ACTION_EVIDENCE_V1"
PARENT_STOP_INPUT_VERSION = "CERTIFIED_PARENT_STOP_CLASSIFIER_INPUT_V1"
PARENT_RISK_OUTPUT_VERSION = "CERTIFIED_PARENT_RISK_OWNER_OUTPUT_V1"
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
PARENT_INPUT_STATES = (
    "DATA_QUALITY_FAIL",
    "NOT_COMPARABLE",
    "NOT_IN_UNIVERSE",
    "PIT_INVALID",
    "REFERENCE_UNAVAILABLE",
    "SOURCE_UNAVAILABLE",
    "USABLE",
)


@dataclass(frozen=True)
class BlindEvidenceReference:
    """Identity-only input accepted by the scientific monitor."""

    slot_id: str
    certified_parent_evidence_manifest_sha256: str
    evaluation_epoch_authorization_sha256: str


@dataclass(frozen=True)
class ReplayedBlindProjection:
    cadence: str
    observation_time: datetime
    decision_time: datetime
    slot_id: str
    parent_manifest_record_sha256: str
    category_by_metric: Mapping[str, str]
    dependence_unit_by_metric: Mapping[str, str | None]


def blind_monitor_contract() -> dict[str, Any]:
    protocol = _require_certified_corpus()
    parent_manifest = certified_blind_parent_evidence_manifest_contract()
    replay = blind_replay_derivation_contract()
    categories = blind_category_mapping()
    payload = {
        "allowed_monitor_input_fields": [
            "certified_parent_evidence_manifest_sha256",
            "evaluation_epoch_authorization_sha256",
            "slot_id",
        ],
        "blind_category_mapping_sha256": categories["definition_sha256"],
        "blind_category_vocabulary": list(BLIND_CATEGORIES),
        "blind_projection_is_a_derivation_never_an_authority": True,
        "blind_replay_derivation_contract_sha256": replay["definition_sha256"],
        "caller_declared_projection_is_authority": False,
        "certified_parent_manifest_sha256": parent_manifest["definition_sha256"],
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
            "Resolve the identity-only parent manifest, transitively replay each "
            "certified-parent record and named owner, and derive cadence, warmup, "
            "PIT, universe, comparability and the natural dependence unit. A "
            "governance-authored projection is never an evidence root."
        ),
        "resolver_contract_sha256": protocol["child_definition_sha256"][
            "scientific_evidence_resolver"
        ],
        "schema_version": BLIND_PROJECTION_VERSION,
        "warmup_replayed": True,
    }
    return _with_definition_hash(payload)


def certified_blind_parent_evidence_manifest_contract() -> dict[str, Any]:
    """Freeze identity-only parent inputs required at each certified cadence."""

    protocol = _require_certified_corpus()
    parent_hashes = protocol["child_definition_sha256"]
    payload = {
        "conclusion_fields_permitted": False,
        "cross_identity_rules": [
            "every record binds the same certified corpus, slot and decision time",
            "every referenced record is content-addressed and schema/version checked",
            "stop evidence binds the replayed control lifecycle tip and active stop",
            "risk evidence binds paired candidate/control owner outputs",
            "cross-slot, cross-position and cross-metric substitution is refused",
        ],
        "manifest_fields": [
            "cadence",
            "certified_corpus_sha256",
            "decision_time",
            "evaluation_epoch_authorization_sha256",
            "input_evidence_sha256_by_metric",
            "metric_owner_evidence_sha256_by_metric",
            "observation_time",
            "record_sha256",
            "schema_version",
            "slot_id",
            "warmup_evidence_sha256",
        ],
        "parent_bindings": {
            "data_schema_sha256": parent_hashes["data_schema_contract"],
            "decision_universe_sha256": parent_hashes["decision_universe"],
            "metric_evidence_contract_sha256": parent_hashes[
                "metric_evidence_contracts"
            ],
            "portfolio_track_sha256": parent_hashes["portfolio_track_contract"],
            "scientific_evidence_resolver_sha256": parent_hashes[
                "scientific_evidence_resolver"
            ],
            "stage_b_evaluation_contract_sha256": parent_hashes[
                "stage_b_evaluation_contract"
            ],
            "stop_event_taxonomy_sha256": parent_hashes["stop_event_taxonomy"],
            "warmup_history_sha256": parent_hashes["warmup_history"],
        },
        "referenced_record_schemas": {
            PARENT_INPUT_RECORD_VERSION: {
                "fields": [
                    "available_at",
                    "certified_corpus_sha256",
                    "decision_time",
                    "quality_state",
                    "record_sha256",
                    "schema_version",
                    "slot_id",
                    "source_identity",
                ],
                "replay": (
                    "resolve the exact parent source record and its transitive "
                    "source/clock evidence; derive availability and quality under "
                    "the certified source owner"
                ),
            },
            PARENT_WARMUP_RECORD_VERSION: {
                "fields": [
                    "certified_corpus_sha256",
                    "decision_time",
                    "owner_evidence",
                    "record_sha256",
                    "schema_version",
                    "slot_id",
                    "warmup_history_definition_sha256",
                ],
                "replay": (
                    "enumerate every certified warmup owner, resolve all qualifying "
                    "input records, and re-run its exact owner evaluability predicate"
                ),
            },
            PARENT_METRIC_RECORD_VERSION: {
                "fields": [
                    "certified_corpus_sha256",
                    "comparison_input_record_sha256s",
                    "decision_time",
                    "metric",
                    "owner_output_record_sha256s",
                    "record_sha256",
                    "schema_version",
                    "slot_id",
                    "universe_input_record_sha256s",
                ],
                "replay": (
                    "re-run the metric's certified universe and comparability "
                    "predicates from its exact owner inputs and paired outputs"
                ),
            },
            PARENT_PORTFOLIO_STATE_VERSION: {
                "fields": [
                    "active_stop",
                    "as_of",
                    "certified_corpus_sha256",
                    "lifecycle_state",
                    "prior_state_record_sha256",
                    "record_sha256",
                    "schema_version",
                    "state_sha256",
                    "track",
                    "transition_action_record_sha256",
                ],
                "replay": (
                    "traverse and verify the complete control prior-state/action "
                    "chain to the ENTER opening transition of the current episode"
                ),
            },
            PARENT_TRADE_ACTION_VERSION: {
                "fields": [
                    "active_stop",
                    "certified_corpus_sha256",
                    "decision_time",
                    "lifecycle_event",
                    "lifecycle_state_after",
                    "lifecycle_state_before",
                    "prior_portfolio_state_record_sha256",
                    "record_sha256",
                    "schema_version",
                    "track",
                ],
                "replay": "verify transition legality and prior-state cross-binding",
            },
            PARENT_STOP_INPUT_VERSION: {
                "fields": [
                    "active_stop",
                    "active_stop_identity",
                    "candidate_position_state",
                    "candidate_reference_available",
                    "certified_corpus_sha256",
                    "control_portfolio_tip_sha256",
                    "control_position_state",
                    "decision_time",
                    "direction",
                    "first_divergence_decision_time",
                    "observation_time",
                    "prior_provider_observations",
                    "provider_observations",
                    "record_sha256",
                    "schema_version",
                    "slot_id",
                ],
                "replay": (
                    "invoke classify_stop_event on exact provider observations and "
                    "the lifecycle-replayed control active stop"
                ),
            },
            PARENT_RISK_OUTPUT_VERSION: {
                "fields": [
                    "certified_corpus_sha256",
                    "decision_time",
                    "input_record_sha256s",
                    "position_notional",
                    "record_sha256",
                    "reference_identity",
                    "reference_role",
                    "risk_size_complete",
                    "schema_version",
                    "slot_id",
                    "trade_permitted",
                ],
                "replay": (
                    "require the bound candidate/control pair, complete positive "
                    "owner sizing outputs and every transitive input"
                ),
            },
        },
        "required_owner_evidence": {
            _corpus.STOP_HOURLY_CADENCE: {
                metric: [
                    "prospective_source_input_snapshot",
                    "prospective_portfolio_state:CONTROL_REFERENCE_TRACK",
                    "prospective_trade_action lifecycle chain",
                    "prospective_stop_event classifier inputs",
                    "prospective_reference_evaluation:candidate",
                ]
                for metric in _corpus.STOP_EVENT_METRICS
            },
            _corpus.STRATEGY_DAILY_CADENCE: {
                _corpus.REGIME_METRIC: ["paired prospective_strategy_evaluation"],
                _corpus.RISK_SIZE_METRIC: ["paired prospective_risk_evaluation"],
                _corpus.SETUP_METRIC: ["paired prospective_strategy_evaluation"],
                _corpus.TRADE_ACTION_METRIC: ["paired prospective_trade_action"],
                _corpus.TRADE_ELIGIBILITY_METRIC: [
                    "paired prospective_risk_evaluation"
                ],
            },
        },
        "schema_version": BLIND_PARENT_MANIFEST_VERSION,
        "strict_schema": True,
    }
    return _with_definition_hash(payload)


def blind_category_mapping() -> dict[str, Any]:
    payload = {
        "mapping_precedence": [
            "WARMUP_INCOMPLETE",
            "PIT_INVALID",
            "SOURCE_UNAVAILABLE",
            "DATA_QUALITY_FAIL",
            "REFERENCE_UNAVAILABLE",
            "NOT_IN_UNIVERSE",
            "NOT_COMPARABLE",
            "EVALUATED",
        ],
        "outcome_fields_consumed": False,
        "schema_version": BLIND_CATEGORY_MAPPING_VERSION,
        "states": list(BLIND_CATEGORIES),
    }
    return _with_definition_hash(payload)


def blind_replay_derivation_contract() -> dict[str, Any]:
    manifest = certified_blind_parent_evidence_manifest_contract()
    categories = blind_category_mapping()
    payload = {
        "active_stop_membership_replayed": True,
        "blind_category_mapping_sha256": categories["definition_sha256"],
        "cached_projection_authoritative": False,
        "certified_parent_manifest_contract_sha256": manifest["definition_sha256"],
        "comparability_replayed": True,
        "control_root_lifecycle_replayed": True,
        "digest_only_leaf_permitted": False,
        "genuine_sizing_opportunity_replayed": True,
        "pit_replayed_for_every_material_input": True,
        "replay_steps": [
            "resolve exact persisted record",
            "recompute record hash and validate strict schema/version",
            "verify certified-corpus, epoch, slot, cadence and time identities",
            "resolve every transitive parent reference",
            "re-run the certified parent owner predicate",
            "derive the coarse blind category",
            "derive the natural dependence unit without reading an outcome",
        ],
        "schema_version": BLIND_REPLAY_CONTRACT_VERSION,
        "scientific_surface_record_authoritative": False,
        "universe_replayed": True,
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
        "data_schema_sha256": protocol["child_definition_sha256"][
            "data_schema_contract"
        ],
        "portfolio_track_sha256": protocol["child_definition_sha256"][
            "portfolio_track_contract"
        ],
        "stage_b_evaluation_contract_sha256": protocol["child_definition_sha256"][
            "stage_b_evaluation_contract"
        ],
        "stop_event_taxonomy_sha256": protocol["child_definition_sha256"][
            "stop_event_taxonomy"
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


@cache
def _warmup_parent_rows() -> dict[str, dict[str, Any]]:
    return dict(_corpus.warmup_history_contract()["rows"])


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


def _resolve_record(
    resolver: _source_integrity.PersistedEvidenceResolver,
    record_sha256: str,
    schema_version: str,
) -> dict[str, Any]:
    try:
        return resolver.resolve(record_sha256, schema_version=schema_version)
    except _source_integrity.ProspectiveSourceIntegrityError as exc:
        raise SufficiencyGovernanceError(str(exc)) from exc


def _validate_parent_identity(
    row: Mapping[str, Any],
    *,
    slot_id: str,
    decision_time: datetime,
) -> None:
    if row.get("certified_corpus_sha256") != CERTIFIED_CORPUS_SHA256:
        raise SufficiencyGovernanceError("parent evidence has wrong certified corpus")
    if row.get("slot_id") != slot_id:
        raise SufficiencyGovernanceError("parent evidence has wrong slot identity")
    if row.get("decision_time") != decision_time.isoformat():
        raise SufficiencyGovernanceError("parent evidence has wrong decision time")


def _replay_parent_input(
    resolver: _source_integrity.PersistedEvidenceResolver,
    record_sha256: str,
    *,
    slot_id: str,
    decision_time: datetime,
) -> str:
    row = _resolve_record(resolver, record_sha256, PARENT_INPUT_RECORD_VERSION)
    _strict_keys(
        row,
        {
            "available_at",
            "certified_corpus_sha256",
            "decision_time",
            "quality_state",
            "record_sha256",
            "schema_version",
            "slot_id",
            "source_identity",
        },
        "certified parent input evidence",
    )
    _validate_parent_identity(row, slot_id=slot_id, decision_time=decision_time)
    available_at = _require_utc(
        datetime.fromisoformat(row["available_at"]), "parent input available_at"
    )
    if available_at > decision_time:
        return "PIT_INVALID"
    if row["quality_state"] not in PARENT_INPUT_STATES:
        raise SufficiencyGovernanceError("parent input has unknown quality state")
    if not isinstance(row["source_identity"], str) or not row["source_identity"]:
        raise SufficiencyGovernanceError("parent input lacks source identity")
    return str(row["quality_state"])


def _replay_warmup(
    resolver: _source_integrity.PersistedEvidenceResolver,
    record_sha256: str,
    *,
    slot_id: str,
    decision_time: datetime,
) -> bool:
    row = _resolve_record(resolver, record_sha256, PARENT_WARMUP_RECORD_VERSION)
    _strict_keys(
        row,
        {
            "certified_corpus_sha256",
            "decision_time",
            "owner_evidence",
            "record_sha256",
            "schema_version",
            "slot_id",
            "warmup_history_definition_sha256",
        },
        "certified parent warmup evidence",
    )
    _validate_parent_identity(row, slot_id=slot_id, decision_time=decision_time)
    if row["warmup_history_definition_sha256"] != _blind_parent_bindings()[
        "warmup_history_definition_sha256"
    ]:
        raise SufficiencyGovernanceError("warmup evidence has wrong owner contract")
    owner_evidence = row["owner_evidence"]
    if not isinstance(owner_evidence, dict) or not owner_evidence:
        raise SufficiencyGovernanceError("warmup evidence must enumerate owners")
    parent_rows = _warmup_parent_rows()
    if set(owner_evidence) != set(parent_rows):
        raise SufficiencyGovernanceError("warmup owner census differs from parent")
    complete = True
    for feature, evidence in owner_evidence.items():
        _strict_keys(
            evidence,
            {
                "owner",
                "owner_contract_sha256",
                "qualifying_input_record_sha256s",
                "required_observation_count",
                "upstream_initialization_complete",
            },
            f"warmup owner evidence {feature}",
        )
        parent = parent_rows[feature]
        if evidence["owner"] != parent["owner"]:
            raise SufficiencyGovernanceError("warmup owner identity differs")
        if evidence["owner_contract_sha256"] != _digest(parent):
            raise SufficiencyGovernanceError("warmup owner contract differs")
        required = evidence["required_observation_count"]
        references = evidence["qualifying_input_record_sha256s"]
        if not isinstance(required, int) or isinstance(required, bool) or required <= 0:
            raise SufficiencyGovernanceError("warmup required count must be positive")
        if not isinstance(references, list) or len(references) != len(set(references)):
            raise SufficiencyGovernanceError("warmup inputs must be a unique list")
        inputs_complete = all(
            _replay_parent_input(
                resolver, item, slot_id=slot_id, decision_time=decision_time
            )
            == "USABLE"
            for item in references
        )
        upstream = evidence["upstream_initialization_complete"]
        if type(upstream) is not bool:
            raise SufficiencyGovernanceError("warmup upstream state must be Boolean")
        complete &= upstream and inputs_complete and len(references) >= required
    return complete


def _replay_metric_owner_evidence(
    resolver: _source_integrity.PersistedEvidenceResolver,
    record_sha256: str,
    *,
    metric: str,
    slot_id: str,
    decision_time: datetime,
    evaluation_contract: Mapping[str, Any],
) -> tuple[bool, str | None]:
    row = _resolve_record(resolver, record_sha256, PARENT_METRIC_RECORD_VERSION)
    _strict_keys(
        row,
        {
            "certified_corpus_sha256",
            "comparison_input_record_sha256s",
            "decision_time",
            "metric",
            "owner_output_record_sha256s",
            "record_sha256",
            "schema_version",
            "slot_id",
            "universe_input_record_sha256s",
        },
        f"certified parent metric evidence {metric}",
    )
    _validate_parent_identity(row, slot_id=slot_id, decision_time=decision_time)
    if row["metric"] != metric:
        raise SufficiencyGovernanceError("metric evidence substitution refused")
    universe_states = [
        _replay_parent_input(
            resolver, item, slot_id=slot_id, decision_time=decision_time
        )
        for item in row["universe_input_record_sha256s"]
    ]
    comparison_states = [
        _replay_parent_input(
            resolver, item, slot_id=slot_id, decision_time=decision_time
        )
        for item in row["comparison_input_record_sha256s"]
    ]
    state_order = blind_category_mapping()["mapping_precedence"]
    all_states = universe_states + comparison_states
    for category in state_order:
        if category in {"WARMUP_INCOMPLETE", "EVALUATED"}:
            continue
        if category in all_states:
            return False, category
    if not universe_states or not comparison_states:
        raise SufficiencyGovernanceError("metric evidence lacks predicate inputs")

    output_refs = row["owner_output_record_sha256s"]
    if metric == _corpus.RISK_SIZE_METRIC:
        if not isinstance(output_refs, list) or len(output_refs) != 2:
            raise SufficiencyGovernanceError("risk metric needs paired owner outputs")
        outputs = [
            _resolve_record(resolver, item, PARENT_RISK_OUTPUT_VERSION)
            for item in output_refs
        ]
        by_role = {item["reference_role"]: item for item in outputs}
        if set(by_role) != set(_corpus.REFERENCE_ROLES):
            raise SufficiencyGovernanceError("risk outputs lack candidate/control pair")
        identities = {
            _corpus.CANDIDATE_REFERENCE_ROLE: evaluation_contract[
                "candidate_reference_identity"
            ],
            _corpus.CONTROL_REFERENCE_ROLE: evaluation_contract[
                "control_reference_identity"
            ],
        }
        for role, output in by_role.items():
            _strict_keys(
                output,
                {
                    "certified_corpus_sha256",
                    "decision_time",
                    "input_record_sha256s",
                    "position_notional",
                    "record_sha256",
                    "reference_identity",
                    "reference_role",
                    "risk_size_complete",
                    "schema_version",
                    "slot_id",
                    "trade_permitted",
                },
                "certified parent risk output",
            )
            _validate_parent_identity(
                output, slot_id=slot_id, decision_time=decision_time
            )
            if output["reference_identity"] != identities[role]:
                raise SufficiencyGovernanceError("risk output reference substituted")
            transitive = [
                _replay_parent_input(
                    resolver, item, slot_id=slot_id, decision_time=decision_time
                )
                for item in output["input_record_sha256s"]
            ]
            if not transitive or any(item != "USABLE" for item in transitive):
                return False, "NOT_COMPARABLE"
            try:
                positive = Decimal(output["position_notional"]) > 0
            except Exception as exc:
                raise SufficiencyGovernanceError(
                    "risk output position_notional is invalid"
                ) from exc
            if (
                type(output["trade_permitted"]) is not bool
                or type(output["risk_size_complete"]) is not bool
            ):
                raise SufficiencyGovernanceError("risk owner states must be Boolean")
            if not (
                output["trade_permitted"]
                and output["risk_size_complete"]
                and positive
            ):
                return False, "NOT_IN_UNIVERSE"
    else:
        if not isinstance(output_refs, list) or len(output_refs) != 2:
            raise SufficiencyGovernanceError("daily metric needs paired owner outputs")
        outputs = [
            _resolve_record(resolver, item, PARENT_INPUT_RECORD_VERSION)
            for item in output_refs
        ]
        if any(
            _replay_parent_input(
                resolver,
                item["record_sha256"],
                slot_id=slot_id,
                decision_time=decision_time,
            )
            != "USABLE"
            for item in outputs
        ):
            return False, "NOT_COMPARABLE"
    return True, None


def _replay_control_position_root(
    resolver: _source_integrity.PersistedEvidenceResolver,
    tip_sha256: str,
    *,
    slot_id: str,
    decision_time: datetime,
    expected_active_stop_identity: str,
    expected_active_stop: str,
) -> str:
    seen: set[str] = set()
    current_sha = tip_sha256
    opening_transition_sha: str | None = None
    current_episode_open = True
    first = True
    while current_sha is not None:
        if current_sha in seen:
            raise SufficiencyGovernanceError("control portfolio chain cycles")
        seen.add(current_sha)
        row = _resolve_record(resolver, current_sha, PARENT_PORTFOLIO_STATE_VERSION)
        _strict_keys(
            row,
            {
                "active_stop",
                "as_of",
                "certified_corpus_sha256",
                "lifecycle_state",
                "prior_state_record_sha256",
                "record_sha256",
                "schema_version",
                "state_sha256",
                "track",
                "transition_action_record_sha256",
            },
            "certified control portfolio state",
        )
        if row["certified_corpus_sha256"] != CERTIFIED_CORPUS_SHA256:
            raise SufficiencyGovernanceError("portfolio state has wrong certified corpus")
        if _require_utc(
            datetime.fromisoformat(row["as_of"]), "portfolio state as_of"
        ) > decision_time:
            raise SufficiencyGovernanceError("portfolio state is not PIT-valid")
        if row["track"] != _corpus.CONTROL_TRACK:
            raise SufficiencyGovernanceError("stop root must use control track")
        state_payload = {
            key: value
            for key, value in row.items()
            if key not in {"record_sha256", "schema_version", "state_sha256"}
        }
        if row["state_sha256"] != _digest(state_payload):
            raise SufficiencyGovernanceError("portfolio state hash does not reproduce")
        action = _resolve_record(
            resolver, row["transition_action_record_sha256"], PARENT_TRADE_ACTION_VERSION
        )
        _strict_keys(
            action,
            {
                "active_stop",
                "certified_corpus_sha256",
                "decision_time",
                "lifecycle_event",
                "lifecycle_state_after",
                "lifecycle_state_before",
                "prior_portfolio_state_record_sha256",
                "record_sha256",
                "schema_version",
                "track",
            },
            "certified parent trade action",
        )
        if action["certified_corpus_sha256"] != CERTIFIED_CORPUS_SHA256:
            raise SufficiencyGovernanceError("portfolio action has wrong corpus")
        if _require_utc(
            datetime.fromisoformat(action["decision_time"]),
            "portfolio action decision_time",
        ) > decision_time:
            raise SufficiencyGovernanceError("portfolio action is not PIT-valid")
        if action["track"] != _corpus.CONTROL_TRACK:
            raise SufficiencyGovernanceError("portfolio action is not control track")
        if action["prior_portfolio_state_record_sha256"] != row[
            "prior_state_record_sha256"
        ]:
            raise SufficiencyGovernanceError("portfolio action breaks prior-state chain")
        if first:
            if row["active_stop"] != expected_active_stop:
                raise SufficiencyGovernanceError("stop event active stop differs from lifecycle")
            expected_identity = _digest(
                {
                    "active_stop": row["active_stop"],
                    "active_stop_source_state_sha256": row["state_sha256"],
                    "track": _corpus.CONTROL_TRACK,
                }
            )
            if expected_identity != expected_active_stop_identity:
                raise SufficiencyGovernanceError(
                    "stop event active-stop identity does not replay"
                )
            first = False
        event = action["lifecycle_event"]
        if event == "ENTER":
            if not current_episode_open:
                raise SufficiencyGovernanceError("opening transition lies outside episode")
            opening_transition_sha = row["state_sha256"]
            break
        if event == "EXIT":
            current_episode_open = False
        current_sha = row["prior_state_record_sha256"]
    if not _is_sha256(opening_transition_sha):
        raise SufficiencyGovernanceError("control position opening transition not found")
    return opening_transition_sha


def _provider_from_payload(payload: Mapping[str, Any]) -> _corpus.ProviderObservation:
    return _corpus.ProviderObservation(
        provider_id=str(payload["provider_id"]),
        observation_time=_require_utc(
            datetime.fromisoformat(payload["observation_time"]),
            "provider observation_time",
        ),
        available_at=_require_utc(
            datetime.fromisoformat(payload["available_at"]), "provider available_at"
        ),
        open=Decimal(payload["open"]),
        high=Decimal(payload["high"]),
        low=Decimal(payload["low"]),
        close=Decimal(payload["close"]),
    )


def _replay_stop_metric(
    resolver: _source_integrity.PersistedEvidenceResolver,
    record_sha256: str,
    *,
    metric: str,
    slot_id: str,
    decision_time: datetime,
) -> tuple[str, str | None]:
    row = _resolve_record(resolver, record_sha256, PARENT_STOP_INPUT_VERSION)
    _strict_keys(
        row,
        {
            "active_stop",
            "active_stop_identity",
            "candidate_position_state",
            "candidate_reference_available",
            "certified_corpus_sha256",
            "control_portfolio_tip_sha256",
            "control_position_state",
            "decision_time",
            "direction",
            "first_divergence_decision_time",
            "observation_time",
            "prior_provider_observations",
            "provider_observations",
            "record_sha256",
            "schema_version",
            "slot_id",
        },
        "certified parent stop classifier input",
    )
    _validate_parent_identity(row, slot_id=slot_id, decision_time=decision_time)
    root = _replay_control_position_root(
        resolver,
        row["control_portfolio_tip_sha256"],
        slot_id=slot_id,
        decision_time=decision_time,
        expected_active_stop_identity=row["active_stop_identity"],
        expected_active_stop=row["active_stop"],
    )
    observation_time = _require_utc(
        datetime.fromisoformat(row["observation_time"]), "stop observation_time"
    )
    slot = _corpus.StopEvaluationSlot(
        observation_time=observation_time,
        track=_corpus.CONTROL_TRACK,
        direction=row["direction"],
        active_stop=Decimal(row["active_stop"]),
        active_stop_identity=row["active_stop_identity"],
        control_position_state=row["control_position_state"],
        candidate_position_state=row["candidate_position_state"],
        providers=tuple(_provider_from_payload(item) for item in row["provider_observations"]),
        prior_providers=tuple(
            _provider_from_payload(item) for item in row["prior_provider_observations"]
        ),
        first_divergence_decision_time=(
            None
            if row["first_divergence_decision_time"] is None
            else datetime.fromisoformat(row["first_divergence_decision_time"])
        ),
    )
    try:
        classified = _corpus.classify_stop_event(slot)
    except _corpus.ProspectiveCorpusError as exc:
        raise SufficiencyGovernanceError(str(exc)) from exc
    if row["candidate_reference_available"] is not True:
        return "REFERENCE_UNAVAILABLE", None
    universe = {
        _corpus.CROSS_MARKET_METRIC: (
            classified["classification"] == _corpus.EVENT_CROSS_MARKET
        ),
        _corpus.GAP_THROUGH_METRIC: (
            classified["gap_through_state"] == _corpus.GAP_THROUGH_EVENT
        ),
        _corpus.ISOLATED_VENUE_METRIC: (
            classified["classification"] == _corpus.EVENT_ISOLATED_VENUE
        ),
    }
    if not universe[metric]:
        return "NOT_IN_UNIVERSE", None
    return "EVALUATED", root


class BlindEvidenceResolver:
    """Transitively replay certified-parent evidence into a coarse projection."""

    def __init__(self, records: Mapping[str, Mapping[str, Any]]) -> None:
        self.records = records
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
        evaluation_contract = authorization["evaluation_contract"]
        manifest = _resolve_record(
            self._resolver,
            reference.certified_parent_evidence_manifest_sha256,
            BLIND_PARENT_MANIFEST_VERSION,
        )
        _strict_keys(
            manifest,
            {
                "cadence",
                "certified_corpus_sha256",
                "decision_time",
                "evaluation_epoch_authorization_sha256",
                "input_evidence_sha256_by_metric",
                "metric_owner_evidence_sha256_by_metric",
                "observation_time",
                "record_sha256",
                "schema_version",
                "slot_id",
                "warmup_evidence_sha256",
            },
            "certified blind parent manifest",
        )
        auth_hash = authorization["record_sha256"]
        if manifest["certified_corpus_sha256"] != CERTIFIED_CORPUS_SHA256:
            raise SufficiencyGovernanceError("manifest has wrong certified corpus")
        if manifest["evaluation_epoch_authorization_sha256"] != auth_hash:
            raise SufficiencyGovernanceError("manifest has wrong epoch authority")
        if manifest["slot_id"] != reference.slot_id:
            raise SufficiencyGovernanceError("blind evidence slot identity mismatch")

        observation_time = _require_utc(
            datetime.fromisoformat(manifest["observation_time"]), "observation_time"
        )
        decision_time = _require_utc(
            datetime.fromisoformat(manifest["decision_time"]), "decision_time"
        )
        current = _require_utc(current_decision_time, "current_decision_time")
        if decision_time > current:
            raise SufficiencyGovernanceError("parent evidence is not yet available")
        cadence = manifest["cadence"]
        if cadence not in _corpus.DECISION_CADENCES:
            raise SufficiencyGovernanceError("source evidence has unknown cadence")
        expected_decision = _corpus.decision_time_for(observation_time, cadence)
        if decision_time != expected_decision:
            raise SufficiencyGovernanceError("decision_time does not reproduce")
        expected_slot = _corpus.scheduled_decision_slots(
            observation_time, observation_time, cadence=cadence
        )[0]
        if manifest["slot_id"] != expected_slot["slot_id"]:
            raise SufficiencyGovernanceError("slot_id does not reproduce")
        warmup_complete = _replay_warmup(
            self._resolver,
            manifest["warmup_evidence_sha256"],
            slot_id=reference.slot_id,
            decision_time=decision_time,
        )
        required_metrics = {
            metric
            for metric, owner_cadence in _metric_cadences().items()
            if owner_cadence == cadence
        }
        input_by_metric = manifest["input_evidence_sha256_by_metric"]
        owner_by_metric = manifest["metric_owner_evidence_sha256_by_metric"]
        if set(input_by_metric) != required_metrics or set(owner_by_metric) != required_metrics:
            raise SufficiencyGovernanceError(
                "parent manifest must cover every cadence-applicable metric"
            )
        categories: dict[str, str] = {}
        units: dict[str, str | None] = {}
        for metric in sorted(required_metrics):
            input_states = [
                _replay_parent_input(
                    self._resolver,
                    item,
                    slot_id=reference.slot_id,
                    decision_time=decision_time,
                )
                for item in input_by_metric[metric]
            ]
            if not warmup_complete:
                category, root = "WARMUP_INCOMPLETE", None
            elif "PIT_INVALID" in input_states:
                category, root = "PIT_INVALID", None
            elif "SOURCE_UNAVAILABLE" in input_states:
                category, root = "SOURCE_UNAVAILABLE", None
            elif "DATA_QUALITY_FAIL" in input_states:
                category, root = "DATA_QUALITY_FAIL", None
            elif "REFERENCE_UNAVAILABLE" in input_states:
                category, root = "REFERENCE_UNAVAILABLE", None
            elif "NOT_IN_UNIVERSE" in input_states:
                category, root = "NOT_IN_UNIVERSE", None
            elif "NOT_COMPARABLE" in input_states:
                category, root = "NOT_COMPARABLE", None
            elif metric in _corpus.STOP_EVENT_METRICS:
                category, root = _replay_stop_metric(
                    self._resolver,
                    owner_by_metric[metric],
                    metric=metric,
                    slot_id=reference.slot_id,
                    decision_time=decision_time,
                )
            else:
                evaluated, category = _replay_metric_owner_evidence(
                    self._resolver,
                    owner_by_metric[metric],
                    metric=metric,
                    slot_id=reference.slot_id,
                    decision_time=decision_time,
                    evaluation_contract=evaluation_contract,
                )
                root = None
                category = "EVALUATED" if evaluated else category
            if category not in BLIND_CATEGORIES:
                raise SufficiencyGovernanceError("blind category replay unresolved")
            categories[metric] = category
            units[metric] = (
                _derive_dependence_unit_id(
                    metric,
                    slot_id=manifest["slot_id"],
                    control_position_episode_sha256=root,
                )
                if category == "EVALUATED"
                else None
            )
        return ReplayedBlindProjection(
            cadence=cadence,
            observation_time=observation_time,
            decision_time=decision_time,
            slot_id=manifest["slot_id"],
            parent_manifest_record_sha256=manifest["record_sha256"],
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
    """Build a strict synthetic certified-parent graph for adversarial tests.

    The helper creates the same record schemas consumed by ``BlindEvidenceResolver``;
    it does not create or authorize a summary-only production path.
    """

    if not _is_sha256(evaluation_epoch_authorization_sha256):
        raise SufficiencyGovernanceError("synthetic evidence needs authorization hash")
    cadence = str(expected_slot["cadence"])
    slot_id = str(expected_slot["slot_id"])
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
    records: dict[str, dict[str, Any]] = {}

    def persist(payload: Mapping[str, Any]) -> dict[str, Any]:
        record = _with_record_hash(payload)
        existing = records.get(record["record_sha256"])
        if existing is not None and existing != record:
            raise SufficiencyGovernanceError("synthetic evidence hash collision")
        records[record["record_sha256"]] = record
        return record

    def parent_input(
        identity: str,
        *,
        quality_state: str = "USABLE",
        available_at: datetime = decision_time,
    ) -> dict[str, Any]:
        return persist(
            {
                "available_at": _require_utc(available_at, "available_at").isoformat(),
                "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
                "decision_time": decision_time.isoformat(),
                "quality_state": quality_state,
                "schema_version": PARENT_INPUT_RECORD_VERSION,
                "slot_id": slot_id,
                "source_identity": identity,
            }
        )

    warmup_input = parent_input("SYNTHETIC_WARMUP_HISTORY_INPUT")
    warmup_rows = _warmup_parent_rows()
    warmup = persist(
        {
            "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
            "decision_time": decision_time.isoformat(),
            "owner_evidence": {
                feature: {
                    "owner": row["owner"],
                    "owner_contract_sha256": _digest(row),
                    "qualifying_input_record_sha256s": (
                        [warmup_input["record_sha256"]]
                        if warmup_history_complete
                        else []
                    ),
                    "required_observation_count": 1,
                    "upstream_initialization_complete": warmup_history_complete,
                }
                for feature, row in sorted(warmup_rows.items())
            },
            "schema_version": PARENT_WARMUP_RECORD_VERSION,
            "slot_id": slot_id,
            "warmup_history_definition_sha256": _blind_parent_bindings()[
                "warmup_history_definition_sha256"
            ],
        }
    )

    def translated_state(metric: str) -> str:
        value = states.get(metric, "AUTHORITATIVE_REPLAYED")
        return {
            "AUTHORITATIVE_REPLAYED": "USABLE",
            "DATA_QUALITY_FAIL": "DATA_QUALITY_FAIL",
            "INVALID_CLOCK_OR_PIT_EVIDENCE": "PIT_INVALID",
            "REFERENCE_UNAVAILABLE": "REFERENCE_UNAVAILABLE",
            "SOURCE_UNAVAILABLE": "SOURCE_UNAVAILABLE",
            "UNREPLAYABLE_EVIDENCE": "SOURCE_UNAVAILABLE",
        }.get(value, value)

    input_by_metric: dict[str, list[str]] = {}
    owner_by_metric: dict[str, str] = {}
    common_input_by_metric: dict[str, dict[str, Any]] = {}
    for metric in sorted(metrics):
        quality = translated_state(metric)
        if universes.get(metric) is False:
            quality = "NOT_IN_UNIVERSE"
        elif comparability.get(metric) is False:
            quality = "NOT_COMPARABLE"
        available_at = availability.get(metric, decision_time)
        if available_at is None:
            quality = "SOURCE_UNAVAILABLE"
            available_at = decision_time
        common = parent_input(
            f"SYNTHETIC_PARENT_INPUT:{metric}",
            quality_state=quality,
            available_at=available_at,
        )
        common_input_by_metric[metric] = common
        input_by_metric[metric] = [common["record_sha256"]]

    if cadence == _corpus.STRATEGY_DAILY_CADENCE:
        for metric in sorted(metrics):
            output_records: list[str] = []
            if metric == _corpus.RISK_SIZE_METRIC:
                for role, identity in (
                    (_corpus.CANDIDATE_REFERENCE_ROLE, "SYNTHETIC_CANDIDATE_A"),
                    (_corpus.CONTROL_REFERENCE_ROLE, "SYNTHETIC_CONTROL"),
                ):
                    risk = persist(
                        {
                            "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
                            "decision_time": decision_time.isoformat(),
                            "input_record_sha256s": [
                                common_input_by_metric[metric]["record_sha256"]
                            ],
                            "position_notional": "100",
                            "reference_identity": identity,
                            "reference_role": role,
                            "risk_size_complete": True,
                            "schema_version": PARENT_RISK_OUTPUT_VERSION,
                            "slot_id": slot_id,
                            "trade_permitted": True,
                        }
                    )
                    output_records.append(risk["record_sha256"])
            else:
                for role in _corpus.REFERENCE_ROLES:
                    output = parent_input(
                        f"SYNTHETIC_OWNER_OUTPUT:{metric}:{role}"
                    )
                    output_records.append(output["record_sha256"])
            owner = persist(
                {
                    "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
                    "comparison_input_record_sha256s": [
                        common_input_by_metric[metric]["record_sha256"]
                    ],
                    "decision_time": decision_time.isoformat(),
                    "metric": metric,
                    "owner_output_record_sha256s": output_records,
                    "schema_version": PARENT_METRIC_RECORD_VERSION,
                    "slot_id": slot_id,
                    "universe_input_record_sha256s": [
                        common_input_by_metric[metric]["record_sha256"]
                    ],
                }
            )
            owner_by_metric[metric] = owner["record_sha256"]
    else:
        explicit_episodes = set(stop_episodes.values())
        if len(explicit_episodes) > 1:
            raise SufficiencyGovernanceError(
                "one stop slot cannot cite multiple control position episodes"
            )
        episode = next(iter(explicit_episodes), (slot_id, "INITIAL"))
        episode_seed, stop_revision = episode
        if stop_episodes:
            seed_digest = _digest({"synthetic_position_episode": str(episode_seed)})
            enter_time = datetime(2024, 1, 1, tzinfo=UTC) + timedelta(
                seconds=int(seed_digest[:8], 16) % (300 * 86400)
            )
        else:
            enter_time = observation_time - timedelta(hours=2)
        enter_action = persist(
            {
                "active_stop": "100",
                "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
                "decision_time": enter_time.isoformat(),
                "lifecycle_event": "ENTER",
                "lifecycle_state_after": "OPEN_INITIAL",
                "lifecycle_state_before": "WATCH",
                "prior_portfolio_state_record_sha256": None,
                "schema_version": PARENT_TRADE_ACTION_VERSION,
                "track": _corpus.CONTROL_TRACK,
            }
        )
        enter_payload = {
            "active_stop": "100",
            "as_of": enter_time.isoformat(),
            "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
            "lifecycle_state": "OPEN_INITIAL",
            "prior_state_record_sha256": None,
            "track": _corpus.CONTROL_TRACK,
            "transition_action_record_sha256": enter_action["record_sha256"],
        }
        enter_state = persist(
            {
                **enter_payload,
                "schema_version": PARENT_PORTFOLIO_STATE_VERSION,
                "state_sha256": _digest(enter_payload),
            }
        )
        tip = enter_state
        if stop_revision != "INITIAL":
            move_action = persist(
                {
                    "active_stop": "100",
                    "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
                    "decision_time": (enter_time + timedelta(minutes=1)).isoformat(),
                    "lifecycle_event": "STOP_MOVE",
                    "lifecycle_state_after": "OPEN_INITIAL",
                    "lifecycle_state_before": "OPEN_INITIAL",
                    "prior_portfolio_state_record_sha256": enter_state["record_sha256"],
                    "schema_version": PARENT_TRADE_ACTION_VERSION,
                    "track": _corpus.CONTROL_TRACK,
                }
            )
            move_payload = {
                "active_stop": "100",
                "as_of": (enter_time + timedelta(minutes=1)).isoformat(),
                "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
                "lifecycle_state": "OPEN_INITIAL",
                "prior_state_record_sha256": enter_state["record_sha256"],
                "track": _corpus.CONTROL_TRACK,
                "transition_action_record_sha256": move_action["record_sha256"],
            }
            tip = persist(
                {
                    **move_payload,
                    "schema_version": PARENT_PORTFOLIO_STATE_VERSION,
                    "state_sha256": _digest(move_payload),
                }
            )
        active_stop_identity = _digest(
            {
                "active_stop": tip["active_stop"],
                "active_stop_source_state_sha256": tip["state_sha256"],
                "track": _corpus.CONTROL_TRACK,
            }
        )
        hour_index = int(observation_time.timestamp() // 3600)
        isolated = hour_index % 24 == 0
        providers = []
        prior = []
        for index, provider_id in enumerate(_corpus.REQUIRED_PROVIDER_IDS):
            touching = not isolated or index == 0
            providers.append(
                {
                    "available_at": decision_time.isoformat(),
                    "close": "99" if touching else "101",
                    "high": "102",
                    "low": "99" if touching else "101",
                    "observation_time": observation_time.isoformat(),
                    "open": "99" if touching else "101",
                    "provider_id": provider_id,
                }
            )
            prior.append(
                {
                    "available_at": decision_time.isoformat(),
                    "close": "101",
                    "high": "102",
                    "low": "100.5",
                    "observation_time": (
                        observation_time - timedelta(hours=1)
                    ).isoformat(),
                    "open": "101",
                    "provider_id": provider_id,
                }
            )
        stop_input = persist(
            {
                "active_stop": "100",
                "active_stop_identity": active_stop_identity,
                "candidate_position_state": "OPEN_INITIAL",
                "candidate_reference_available": True,
                "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
                "control_portfolio_tip_sha256": tip["record_sha256"],
                "control_position_state": "OPEN_INITIAL",
                "decision_time": decision_time.isoformat(),
                "direction": "long",
                "first_divergence_decision_time": None,
                "observation_time": observation_time.isoformat(),
                "prior_provider_observations": prior,
                "provider_observations": providers,
                "schema_version": PARENT_STOP_INPUT_VERSION,
                "slot_id": slot_id,
            }
        )
        owner_by_metric = {metric: stop_input["record_sha256"] for metric in metrics}

    manifest = persist(
        {
            "cadence": cadence,
            "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
            "decision_time": decision_time.isoformat(),
            "evaluation_epoch_authorization_sha256": (
                evaluation_epoch_authorization_sha256
            ),
            "input_evidence_sha256_by_metric": dict(sorted(input_by_metric.items())),
            "metric_owner_evidence_sha256_by_metric": dict(
                sorted(owner_by_metric.items())
            ),
            "observation_time": observation_time.isoformat(),
            "schema_version": BLIND_PARENT_MANIFEST_VERSION,
            "slot_id": slot_id,
            "warmup_evidence_sha256": warmup["record_sha256"],
        }
    )
    reference = BlindEvidenceReference(
        slot_id=slot_id,
        certified_parent_evidence_manifest_sha256=manifest["record_sha256"],
        evaluation_epoch_authorization_sha256=evaluation_epoch_authorization_sha256,
    )
    return reference, records


EVALUATION_CONTRACT_SCHEMA_VERSION = (
    "PROSPECTIVE_INTEGRATION_EVALUATION_CONTRACT_SCHEMA_V1"
)
EVALUATION_CONTRACT_VERSION = "PROSPECTIVE_INTEGRATION_EVALUATION_CONTRACT_V1"


def evaluation_contract_schema() -> dict[str, Any]:
    protocol = _require_certified_corpus()
    payload = {
        "candidate_control_must_be_distinct": True,
        "exact_fields": [
            "candidate_reference_identity",
            "certified_corpus_sha256",
            "contract_created_at",
            "control_reference_identity",
            "definition_sha256",
            "schema_version",
            "stage_b_evaluation_contract_sha256",
            "sufficiency_governance_sha256",
        ],
        "identity_rules": {
            "candidate_reference_identity": "non-empty canonical identity",
            "control_reference_identity": "non-empty canonical identity",
            "definition_sha256": "canonical exact-contract digest",
        },
        "schema_version": EVALUATION_CONTRACT_SCHEMA_VERSION,
        "stage_b_evaluation_contract_sha256": protocol[
            "child_definition_sha256"
        ]["stage_b_evaluation_contract"],
        "unexpected_fields_permitted": False,
        "version": EVALUATION_CONTRACT_VERSION,
    }
    return _with_definition_hash(payload)


def build_evaluation_contract(
    *,
    candidate_reference_identity: str,
    control_reference_identity: str,
    contract_created_at: datetime,
) -> dict[str, Any]:
    protocol = _require_certified_corpus()
    payload = {
        "candidate_reference_identity": candidate_reference_identity,
        "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
        "contract_created_at": _require_utc(
            contract_created_at, "contract_created_at"
        ).isoformat(),
        "control_reference_identity": control_reference_identity,
        "schema_version": EVALUATION_CONTRACT_VERSION,
        "stage_b_evaluation_contract_sha256": protocol[
            "child_definition_sha256"
        ]["stage_b_evaluation_contract"],
        "sufficiency_governance_sha256": sufficiency_governance_definition()[
            "definition_sha256"
        ],
    }
    contract = _with_definition_hash(payload)
    validate_evaluation_contract(contract)
    return contract


def validate_evaluation_contract(
    evaluation_contract: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(evaluation_contract, Mapping):
        raise SufficiencyGovernanceError("evaluation contract must be an object")
    expected_fields = set(evaluation_contract_schema()["exact_fields"])
    _strict_keys(evaluation_contract, expected_fields, "evaluation contract")
    digest = _verify_hashed_definition(evaluation_contract, "evaluation contract")
    if evaluation_contract["schema_version"] != EVALUATION_CONTRACT_VERSION:
        raise SufficiencyGovernanceError("evaluation contract has wrong schema")
    if evaluation_contract["certified_corpus_sha256"] != CERTIFIED_CORPUS_SHA256:
        raise SufficiencyGovernanceError("evaluation contract has wrong corpus")
    protocol = _require_certified_corpus()
    if evaluation_contract["stage_b_evaluation_contract_sha256"] != protocol[
        "child_definition_sha256"
    ]["stage_b_evaluation_contract"]:
        raise SufficiencyGovernanceError("evaluation contract has wrong Stage-B owner")
    if evaluation_contract["sufficiency_governance_sha256"] != (
        sufficiency_governance_definition()["definition_sha256"]
    ):
        raise SufficiencyGovernanceError("evaluation contract has wrong governance")
    candidate = evaluation_contract["candidate_reference_identity"]
    control = evaluation_contract["control_reference_identity"]
    if not isinstance(candidate, str) or not candidate.strip():
        raise SufficiencyGovernanceError("candidate reference identity is required")
    if not isinstance(control, str) or not control.strip():
        raise SufficiencyGovernanceError("control reference identity is required")
    if candidate == control:
        raise SufficiencyGovernanceError("candidate and control must be distinct")
    try:
        _require_utc(
            datetime.fromisoformat(evaluation_contract["contract_created_at"]),
            "contract_created_at",
        )
    except (TypeError, ValueError) as exc:
        raise SufficiencyGovernanceError(
            "evaluation contract created_at is invalid"
        ) from exc
    return {**dict(evaluation_contract), "definition_sha256": digest}


EPOCH_AUTHORIZATION_VERSION = "PROSPECTIVE_STAGE_B_EVALUATION_EPOCH_AUTHORIZATION_V1"
CUTOFF_RECORD_VERSION = "PROSPECTIVE_STAGE_B_SUFFICIENCY_CUTOFF_RECORD_V1"
EVALUATION_RESULT_IDENTITY_VERSION = "PROSPECTIVE_STAGE_B_EVALUATION_RESULT_IDENTITY_V1"
INITIAL_EPOCH_ID = "INITIAL_STAGE_B_EVALUATION_EPOCH"


def evaluation_epoch_contract() -> dict[str, Any]:
    contract_schema = evaluation_contract_schema()
    payload = {
        "authorization_at_before_epoch_observation_start": True,
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
        "evaluation_contract_schema_sha256": contract_schema["definition_sha256"],
        "initial_epoch_id": INITIAL_EPOCH_ID,
        "initial_epoch_unique": True,
        "postp1_004_persistent_transactional_enforcement_required": True,
        "schema_version": EPOCH_AUTHORIZATION_VERSION,
        "successor_epoch_permitted_automatically": False,
        "terminal_after_any_evaluation_result": True,
    }
    return _with_definition_hash(payload)


def validate_epoch_authorization(authorization: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(authorization)
    _strict_keys(
        row,
        {
            "authorized_at",
            "blind_monitor_sha256",
            "certified_corpus_sha256",
            "coverage_policy_sha256",
            "epoch_observation_start",
            "evaluation_contract",
            "evaluation_contract_sha256",
            "evaluation_epoch_id",
            "evidence_unit_policy_sha256",
            "record_sha256",
            "schema_version",
            "sufficiency_governance_sha256",
            "temporal_policy_sha256",
        },
        "evaluation epoch authorization",
    )
    _verify_record_hash(row, "evaluation epoch authorization")
    if row["schema_version"] != EPOCH_AUTHORIZATION_VERSION:
        raise SufficiencyGovernanceError("authorization has wrong schema")
    if row["evaluation_epoch_id"] != INITIAL_EPOCH_ID:
        raise SufficiencyGovernanceError("authorization has arbitrary epoch identity")
    contract = validate_evaluation_contract(row["evaluation_contract"])
    expected = {
        "blind_monitor_sha256": blind_monitor_contract()["definition_sha256"],
        "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
        "coverage_policy_sha256": coverage_policy()["definition_sha256"],
        "evaluation_contract_sha256": contract["definition_sha256"],
        "evidence_unit_policy_sha256": evidence_unit_policy()["definition_sha256"],
        "sufficiency_governance_sha256": sufficiency_governance_definition()[
            "definition_sha256"
        ],
        "temporal_policy_sha256": temporal_policy()["definition_sha256"],
    }
    for key, value in expected.items():
        if row[key] != value:
            raise SufficiencyGovernanceError(f"authorization has wrong {key}")
    start = _require_utc(
        datetime.fromisoformat(row["epoch_observation_start"]),
        "epoch_observation_start",
    )
    authorized = _require_utc(
        datetime.fromisoformat(row["authorized_at"]), "authorized_at"
    )
    created = _require_utc(
        datetime.fromisoformat(contract["contract_created_at"]),
        "contract_created_at",
    )
    if created > authorized or authorized >= start:
        raise SufficiencyGovernanceError("authorization timing is not prospective")
    return row


def evaluation_cutoff_contract() -> dict[str, Any]:
    replay = blind_replay_derivation_contract()
    payload = {
        "caller_supplied_cutoff_is_scientific_state": False,
        "cutoff_definition": (
            "earliest decision_time where all eight raw minima, all eight "
            "distinct dependence-unit minima, all eight exact coverage floors, "
            "and complete scheduled-slot accounting hold"
        ),
        "cutoff_record_schema_version": CUTOFF_RECORD_VERSION,
        "cutoff_record_strict_fields": sorted(_strict_cutoff_fields()),
        "evidence_after_cutoff_included": False,
        "evidence_manifest_content_addressed": True,
        "first_cutoff_immutable": True,
        "late_revision_moves_cutoff": False,
        "manifest_row_strict_fields": [
            "certified_parent_evidence_manifest_sha256",
            "slot_id",
        ],
        "replay_source": "frozen authoritative evidence manifest",
        "blind_replay_contract_sha256": replay["definition_sha256"],
        "earliest_cutoff_independently_reproduced": True,
        "frozen_manifest_revalidated_before_terminal_result": True,
        "required_bindings": [
            "authoritative_evidence_manifest_sha256",
            "certified_corpus_sha256",
            "coverage_policy_sha256",
            "cutoff_decision_time",
            "decision_universe_sha256",
            "evaluation_contract_sha256",
            "evaluation_epoch_authorization_sha256",
            "evidence_unit_policy_sha256",
            "metric_evidence_contract_sha256",
            "per_metric_counts",
            "sufficiency_governance_sha256",
            "temporal_policy_sha256",
            "window_start",
        ],
        "schema_version": "PROSPECTIVE_STAGE_B_EVALUATION_CUTOFF_CONTRACT_V1",
    }
    return _with_definition_hash(payload)


def cutoff_validation_contract() -> dict[str, Any]:
    cutoff = evaluation_cutoff_contract()
    manifest = certified_blind_parent_evidence_manifest_contract()
    payload = {
        "cutoff_contract_sha256": cutoff["definition_sha256"],
        "earliest_proof": (
            "cutoff T is globally sufficient and the preceding distinct decision "
            "timestamp in the same replayed authoritative prefix is not"
        ),
        "manifest_contract_sha256": manifest["definition_sha256"],
        "manifest_integrity_failure": "REFUSE_WITHOUT_MOVING_CUTOFF",
        "recomputed_fields": [
            "expected scheduled-slot census",
            "all eight raw denominators",
            "all eight distinct dependence-unit counts",
            "all eight coverage numerators and denominators",
            "complete accounting",
            "earliest sufficient decision_time",
            "exact identity-only evidence manifest hash",
        ],
        "schema_version": "PROSPECTIVE_STAGE_B_CUTOFF_REPLAY_VALIDATION_V1",
        "self_rehashed_caller_mapping_authoritative": False,
        "terminal_result_precondition": "FULL_CUTOFF_AND_MANIFEST_REVALIDATION",
    }
    return _with_definition_hash(payload)


def evaluation_result_identity() -> dict[str, Any]:
    payload = {
        "candidate_control_identity_owner": "bound evaluation contract",
        "cutoff_revalidated_before_terminal_result": True,
        "evaluation_contract_revalidated_before_terminal_result": True,
        "frozen_parent_manifest_replayed_before_terminal_result": True,
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


@dataclass(frozen=True)
class SufficiencyDerivation:
    """Pure replay output; possession is never sufficient for persistence."""

    authorization_sha256: str
    cutoff_record: Mapping[str, Any] | None
    evidence_references: tuple[BlindEvidenceReference, ...]
    manifest_rows: tuple[Mapping[str, str], ...]
    progress: Mapping[str, Any]
    replay_decision_time: datetime
    resolver: BlindEvidenceResolver


class EvaluationEpochRegistry:
    """Stateful reference owner; POSTP1-004 must persist it transactionally."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._authorization_by_hash: dict[str, dict[str, Any]] = {}
        self._authorization_by_tuple: dict[tuple[str, str, str], str] = {}
        self._cutoff_by_authorization: dict[str, dict[str, Any]] = {}
        self._manifest_by_hash: dict[str, tuple[dict[str, str], ...]] = {}
        self._progress_by_authorization: dict[str, dict[str, Any]] = {}
        self._derivation_by_authorization: dict[str, SufficiencyDerivation] = {}
        self._terminal_result_by_authorization: dict[str, dict[str, Any]] = {}

    def authorize_initial_epoch(
        self,
        *,
        evaluation_contract: Mapping[str, Any],
        epoch_observation_start: datetime,
        authorized_at: datetime | None = None,
        evaluation_epoch_id: str = INITIAL_EPOCH_ID,
    ) -> dict[str, Any]:
        if evaluation_epoch_id != INITIAL_EPOCH_ID:
            raise SufficiencyGovernanceError("arbitrary evaluation epoch IDs are forbidden")
        contract = validate_evaluation_contract(evaluation_contract)
        evaluation_contract_sha256 = contract["definition_sha256"]
        start = _require_utc(epoch_observation_start, "epoch_observation_start")
        if start != start.replace(hour=0, minute=0, second=0, microsecond=0):
            raise SufficiencyGovernanceError(
                "epoch observation start must be a canonical UTC-day boundary"
            )
        authorized = _require_utc(
            start - timedelta(microseconds=1) if authorized_at is None else authorized_at,
            "authorized_at",
        )
        created = _require_utc(
            datetime.fromisoformat(contract["contract_created_at"]),
            "contract_created_at",
        )
        if created > authorized or authorized >= start:
            raise SufficiencyGovernanceError(
                "evaluation contract and epoch authorization must be prospective"
            )
        definition = sufficiency_governance_definition()
        coverage = coverage_policy()
        temporal = temporal_policy()
        units = evidence_unit_policy()
        blind = blind_monitor_contract()
        record = _with_record_hash(
            {
                "authorized_at": authorized.isoformat(),
                "blind_monitor_sha256": blind["definition_sha256"],
                "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
                "coverage_policy_sha256": coverage["definition_sha256"],
                "epoch_observation_start": start.isoformat(),
                "evaluation_contract": contract,
                "evaluation_contract_sha256": evaluation_contract_sha256,
                "evaluation_epoch_id": evaluation_epoch_id,
                "evidence_unit_policy_sha256": units["definition_sha256"],
                "schema_version": EPOCH_AUTHORIZATION_VERSION,
                "sufficiency_governance_sha256": definition["definition_sha256"],
                "temporal_policy_sha256": temporal["definition_sha256"],
            }
        )
        epoch_key = (
            evaluation_contract_sha256,
            CERTIFIED_CORPUS_SHA256,
            definition["definition_sha256"],
        )
        with self._lock:
            existing_hash = self._authorization_by_tuple.get(epoch_key)
            if existing_hash is not None:
                if existing_hash in self._terminal_result_by_authorization:
                    raise EvaluationEpochFrozenError(
                        "the initial epoch for this contract is terminal"
                    )
                existing = self._authorization_by_hash[existing_hash]
                if existing != record:
                    raise SufficiencyGovernanceError(
                        "this contract/corpus/governance already has its unique initial epoch"
                    )
                return dict(existing)
            self._authorization_by_tuple[epoch_key] = record["record_sha256"]
            self._authorization_by_hash[record["record_sha256"]] = record
        return dict(record)

    def authorization(self, record_sha256: str) -> dict[str, Any]:
        with self._lock:
            try:
                record = dict(self._authorization_by_hash[record_sha256])
            except KeyError as exc:
                raise SufficiencyGovernanceError(
                    "evaluation epoch lacks persisted authorization"
                ) from exc
        return validate_epoch_authorization(record)

    def frozen_progress(self, authorization_sha256: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._progress_by_authorization.get(authorization_sha256)
            return None if row is None else dict(row)

    def freeze_cutoff(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise SufficiencyGovernanceError(
            "caller-supplied cutoff/progress/manifest state is forbidden"
        )

    def freeze_derived_cutoff(self, derivation: SufficiencyDerivation) -> dict[str, Any]:
        if not isinstance(derivation, SufficiencyDerivation):
            raise SufficiencyGovernanceError("authoritative derivation required")
        authorization_sha256 = derivation.authorization_sha256
        authorization = self.authorization(authorization_sha256)
        cutoff = derivation.cutoff_record
        if cutoff is None:
            raise SufficiencyGovernanceError("insufficient derivation has no cutoff")
        validate_cutoff_record(
            cutoff,
            manifest_rows=derivation.manifest_rows,
            evidence_references=derivation.evidence_references,
            resolver=derivation.resolver,
            authorization=authorization,
        )
        frozen_manifest = tuple(dict(row) for row in derivation.manifest_rows)
        manifest_sha256 = cutoff["authoritative_evidence_manifest_sha256"]
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
            self._progress_by_authorization[authorization_sha256] = dict(
                derivation.progress
            )
            self._derivation_by_authorization[authorization_sha256] = derivation
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
            if authorization_sha256 in self._terminal_result_by_authorization:
                raise EvaluationEpochFrozenError("evaluation epoch is already terminal")
            cutoff = self._cutoff_by_authorization.get(authorization_sha256)
            derivation = self._derivation_by_authorization.get(authorization_sha256)
        if cutoff is None or derivation is None:
            raise SufficiencyGovernanceError("result requires a frozen derived cutoff")
        authorization = self.authorization(authorization_sha256)
        validate_cutoff_record(
            cutoff,
            manifest_rows=self.evidence_manifest(
                cutoff["authoritative_evidence_manifest_sha256"]
            ),
            evidence_references=derivation.evidence_references,
            resolver=derivation.resolver,
            authorization=authorization,
        )
        validate_evaluation_contract(authorization["evaluation_contract"])
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
        with self._lock:
            if authorization_sha256 in self._terminal_result_by_authorization:
                raise EvaluationEpochFrozenError("evaluation epoch is already terminal")
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


def derive_stage_b_sufficiency_state(
    evidence_references: Sequence[BlindEvidenceReference],
    *,
    resolver: BlindEvidenceResolver,
    authorization: Mapping[str, Any],
    current_decision_time: datetime,
) -> SufficiencyDerivation:
    """Purely derive the earliest outcome-blind cutoff from parent evidence."""

    if not isinstance(resolver, BlindEvidenceResolver):
        raise SufficiencyGovernanceError("certified BlindEvidenceResolver required")
    authorization = dict(authorization)
    authorization = validate_epoch_authorization(authorization)
    authorization_sha256 = authorization["record_sha256"]
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
                    "certified_parent_evidence_manifest_sha256": (
                        record.parent_manifest_record_sha256
                    ),
                    "slot_id": record.slot_id,
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
            authorization_sha256
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
        return SufficiencyDerivation(
            authorization_sha256=authorization_sha256,
            cutoff_record=None,
            evidence_references=tuple(evidence_references),
            manifest_rows=tuple(sorted(manifest_rows, key=lambda row: row["slot_id"])),
            progress=result,
            replay_decision_time=current,
            resolver=resolver,
        )

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
                authorization_sha256
            ),
            "evidence_unit_policy_sha256": units["definition_sha256"],
            "decision_universe_sha256": minima_definition["decision_universe_sha256"],
            "metric_evidence_contract_sha256": next(iter(minima.values()))[
                "metric_evidence_contract_sha256"
            ],
            "blind_replay_contract_sha256": blind_replay_derivation_contract()[
                "definition_sha256"
            ],
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
                    "authoritative_coverage_floor": "0.99",
                    "minimum_distinct_dependence_units": row[
                        "minimum_distinct_dependence_units"
                    ],
                    "minimum_raw_sufficiency_denominator": row[
                        "minimum_raw_sufficiency_denominator"
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
    frozen_ids = {row["slot_id"] for row in manifest_rows}
    frozen_references = tuple(
        reference for reference in evidence_references if reference.slot_id in frozen_ids
    )
    return SufficiencyDerivation(
        authorization_sha256=authorization_sha256,
        cutoff_record=cutoff_record,
        evidence_references=frozen_references,
        manifest_rows=tuple(manifest_rows),
        progress=result,
        replay_decision_time=current,
        resolver=resolver,
    )


def _strict_cutoff_fields() -> set[str]:
    return {
        "accounting",
        "authoritative_evidence_manifest_sha256",
        "blind_monitor_sha256",
        "blind_replay_contract_sha256",
        "certified_corpus_sha256",
        "coverage_policy_sha256",
        "cutoff_decision_time",
        "decision_universe_sha256",
        "evaluation_contract_sha256",
        "evaluation_epoch_authorization_sha256",
        "evidence_unit_policy_sha256",
        "metric_evidence_contract_sha256",
        "per_metric_counts",
        "record_sha256",
        "schema_version",
        "sufficiency_governance_sha256",
        "temporal_policy_sha256",
        "window_start",
    }


def validate_cutoff_record(
    cutoff: Mapping[str, Any],
    *,
    manifest_rows: Sequence[Mapping[str, str]],
    evidence_references: Sequence[BlindEvidenceReference],
    resolver: BlindEvidenceResolver,
    authorization: Mapping[str, Any],
) -> dict[str, Any]:
    """Reproduce a cutoff, its manifest, all counters and earliest timestamp."""

    if not isinstance(cutoff, Mapping):
        raise SufficiencyGovernanceError("cutoff record must be an object")
    _strict_keys(cutoff, _strict_cutoff_fields(), "cutoff record")
    _verify_record_hash(cutoff, "cutoff record")
    if cutoff["schema_version"] != CUTOFF_RECORD_VERSION:
        raise SufficiencyGovernanceError("cutoff record has wrong schema")
    auth = dict(authorization)
    auth_sha = _verify_record_hash(auth, "evaluation epoch authorization")
    if cutoff["evaluation_epoch_authorization_sha256"] != auth_sha:
        raise SufficiencyGovernanceError("cutoff record has wrong epoch")
    validate_evaluation_contract(auth["evaluation_contract"])
    cutoff_time = _require_utc(
        datetime.fromisoformat(cutoff["cutoff_decision_time"]),
        "cutoff_decision_time",
    )
    strict_manifest = tuple(dict(row) for row in manifest_rows)
    for row in strict_manifest:
        _strict_keys(
            row,
            {"certified_parent_evidence_manifest_sha256", "slot_id"},
            "cutoff evidence manifest row",
        )
    if len({row["slot_id"] for row in strict_manifest}) != len(strict_manifest):
        raise SufficiencyGovernanceError("cutoff manifest duplicates a slot")
    if _digest(list(strict_manifest)) != cutoff[
        "authoritative_evidence_manifest_sha256"
    ]:
        raise SufficiencyGovernanceError("cutoff evidence manifest does not reproduce")
    recomputed = derive_stage_b_sufficiency_state(
        evidence_references,
        resolver=resolver,
        authorization=auth,
        current_decision_time=cutoff_time,
    )
    if recomputed.cutoff_record is None:
        raise SufficiencyGovernanceError("cutoff prefix is not globally sufficient")
    if tuple(recomputed.manifest_rows) != strict_manifest:
        raise SufficiencyGovernanceError("cutoff manifest differs from parent replay")
    if dict(recomputed.cutoff_record) != dict(cutoff):
        raise SufficiencyGovernanceError(
            "cutoff fields or earliest sufficiency differ from parent replay"
        )
    return dict(cutoff)


def evaluate_blind_sufficiency(
    evidence_references: Sequence[BlindEvidenceReference],
    *,
    resolver: BlindEvidenceResolver,
    registry: EvaluationEpochRegistry,
    evaluation_epoch_authorization_sha256: str,
    current_decision_time: datetime,
) -> dict[str, Any]:
    """Derive and statefully freeze the earliest outcome-blind cutoff."""

    if not isinstance(registry, EvaluationEpochRegistry):
        raise SufficiencyGovernanceError("stateful EvaluationEpochRegistry required")
    authorization = registry.authorization(evaluation_epoch_authorization_sha256)
    if registry.is_terminal(evaluation_epoch_authorization_sha256):
        raise EvaluationEpochFrozenError("evaluation epoch is terminal")
    frozen = registry.frozen_progress(evaluation_epoch_authorization_sha256)
    if frozen is not None:
        return frozen
    derivation = derive_stage_b_sufficiency_state(
        evidence_references,
        resolver=resolver,
        authorization=authorization,
        current_decision_time=current_decision_time,
    )
    if derivation.cutoff_record is not None:
        registry.freeze_derived_cutoff(derivation)
    return dict(derivation.progress)


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
    (
        BLIND_CATEGORY_FILENAME,
        "blind_category_mapping",
        "blind_category_mapping",
    ),
    (BLIND_MONITOR_FILENAME, "blind_monitor_contract", "blind_monitor_contract"),
    (
        BLIND_PARENT_MANIFEST_FILENAME,
        "certified_blind_parent_evidence_manifest",
        "certified_blind_parent_evidence_manifest_contract",
    ),
    (
        BLIND_REPLAY_FILENAME,
        "blind_replay_derivation_contract",
        "blind_replay_derivation_contract",
    ),
    (
        COMMON_RATE_FILENAME,
        "common_rate_evidence_strength",
        "common_rate_evidence_strength",
    ),
    (COVERAGE_FILENAME, "coverage_policy", "coverage_policy"),
    (CUTOFF_FILENAME, "evaluation_cutoff_contract", "evaluation_cutoff_contract"),
    (
        CUTOFF_VALIDATION_FILENAME,
        "cutoff_validation_contract",
        "cutoff_validation_contract",
    ),
    (
        EVALUATION_CONTRACT_SCHEMA_FILENAME,
        "evaluation_contract_schema",
        "evaluation_contract_schema",
    ),
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
            },
            {
                "authoritative": False,
                "definition_sha256": FAILED_R1_GOVERNANCE_SHA256,
                "implementation_commit": FAILED_R1_GOVERNANCE_IMPLEMENTATION_COMMIT,
                "prospective_observations_collected": False,
                "review_classification": FAILED_R1_GOVERNANCE_CLASSIFICATION,
                "review_documentation_commit": (
                    FAILED_R1_GOVERNANCE_REVIEW_DOCUMENTATION_COMMIT
                ),
                "review_result": FAILED_R1_GOVERNANCE_REVIEW_RESULT,
                "superseded_before_collection": True,
            },
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
            "data_schema_sha256": protocol["child_definition_sha256"][
                "data_schema_contract"
            ],
            "portfolio_track_sha256": protocol["child_definition_sha256"][
                "portfolio_track_contract"
            ],
            "stop_event_taxonomy_sha256": protocol["child_definition_sha256"][
                "stop_event_taxonomy"
            ],
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
    if definition["definition_sha256"] in {
        FAILED_GOVERNANCE_SHA256,
        FAILED_R1_GOVERNANCE_SHA256,
    }:
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
        f"- Failed R1 predecessor: {FAILED_R1_GOVERNANCE_SHA256} (non-authoritative)",
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
        "The blind monitor consumes only identity-only certified-parent manifests "
        "and a persisted initial-epoch authorization. It transitively replays "
        "warmup, PIT, universe, comparability, stop-root and genuine sizing "
        "evidence; a self-rehashed projection is never authority. The registry "
        "independently revalidates the strict cutoff and frozen manifest before "
        "either PASS or FAIL becomes terminal.",
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
