"""Frozen pre-data sufficiency governance for the eight prospective Stage-B gates.

``PROSPECTIVE_INTEGRATION_CORPUS_V1`` deliberately left certification sample
sizes to a separate, pre-collection decision.  This module makes that decision
without collecting an observation and without reading a target numerator or
candidate/control outcome.  It binds the certified corpus hash, imports all
historical gate semantics mechanically, derives the finite Wilson capability
floors, records the exact-boundary exception forced by the inherited ``1.0``
minimum gate, and defines the blind earliest-cutoff monitor that POSTP1-004 must
implement.

The monitor's input types contain no target outcome field.  They account for
scheduled slots, universe membership and dispositions only; consequently a
numerator, relative-difference value or provisional PASS/FAIL result cannot
move a sufficiency cutoff through this API.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_CEILING, Context, Decimal, localcontext
from pathlib import Path
from typing import Any

from btc_predictor.research import prospective_integration_corpus as _corpus
from btc_predictor.research.structural_threshold_calibration import (
    UNCERTAINTY_METHOD_ID,
    WILSON_Z_95,
    wilson_interval,
)


# ---------------------------------------------------------------------------
# Frozen identity and dependency
# ---------------------------------------------------------------------------

GOVERNANCE_VERSION = (
    "PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1"
)
GOVERNANCE_SCHEMA_VERSION = (
    "PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_DEFINITION_V1"
)
GOVERNANCE_STATUS = "FROZEN_PRE_DATA_SUFFICIENCY_GOVERNANCE"
PROGRAM_TICKET = "POSTP1-003"
WORKSTREAM = "EPIC X"
FINAL_CLASSIFICATION = (
    "PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1_"
    "READY_FOR_XHIGH_REVIEW"
)
SUCCESSOR_GOVERNANCE_VERSION = (
    "PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V2"
)

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
CERTIFIED_CORPUS_REVIEW_DOCUMENTATION_COMMIT = (
    "946e393b9750aa775054ac49316c4e5465152966"
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
MINIMA_FILENAME = "metric_sufficiency_minima.json"
DERIVATIONS_FILENAME = "statistical_derivations.json"
COVERAGE_FILENAME = "coverage_policy.json"
TEMPORAL_FILENAME = "temporal_policy.json"
BLIND_MONITOR_FILENAME = "blind_monitor_contract.json"
STOPPING_RULE_FILENAME = "stopping_rule.json"
CUTOFF_FILENAME = "evaluation_cutoff_contract.json"
SEMANTIC_DIFF_FILENAME = "semantic_diff_from_stage_b_gates.json"
REPORT_FILENAME = (
    "PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1_REPORT.md"
)

_DECIMAL_CONTEXT = Context(prec=60)
_SHA256_HEX_LENGTH = 64


class SufficiencyGovernanceError(ValueError):
    """Raised when frozen governance or blind evidence fails closed."""


class EvaluationEpochFrozenError(SufficiencyGovernanceError):
    """Raised when one evaluated epoch is extended past its frozen cutoff."""


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


def _with_definition_hash(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["definition_sha256"] = _digest(result)
    return result


def _require_certified_corpus() -> dict[str, Any]:
    protocol = _corpus.protocol_definition()
    actual = protocol.get("definition_sha256")
    if actual != CERTIFIED_CORPUS_SHA256:
        raise SufficiencyGovernanceError(
            "certified corpus hash mismatch: sufficiency governance refuses"
        )
    if protocol.get("protocol_version") != CERTIFIED_CORPUS_VERSION:
        raise SufficiencyGovernanceError(
            "certified corpus version mismatch: sufficiency governance refuses"
        )
    if tuple(protocol.get("target_metrics", ())) != _corpus.TARGET_METRICS:
        raise SufficiencyGovernanceError(
            "certified corpus target-metric census moved"
        )
    return protocol


# ---------------------------------------------------------------------------
# Mechanical historical parity
# ---------------------------------------------------------------------------


def _historical_gate_rows() -> dict[str, dict[str, Any]]:
    """Recover the eight immutable performance gates through their owner."""

    authority = _corpus.historical_gate_authority()
    contracts = _corpus.metric_evidence_contracts()["contracts"]
    if set(authority) != set(_corpus.TARGET_METRICS):
        raise SufficiencyGovernanceError("historical authority does not carry eight gates")
    if set(contracts) != set(_corpus.TARGET_METRICS):
        raise SufficiencyGovernanceError("certified corpus does not carry eight metrics")
    rows: dict[str, dict[str, Any]] = {}
    for metric in _corpus.TARGET_METRICS:
        gate = authority[metric]
        contract = contracts[metric]
        parity = {
            "threshold": contract["threshold"] == gate["threshold"],
            "direction": contract["direction"] == gate["direction"],
            "hard": contract["hard"] == gate["hard"],
            "metric_intent": (
                contract["historical_definition"] == gate["definition"]
            ),
        }
        if not all(parity.values()):
            raise SufficiencyGovernanceError(
                f"{metric} differs from immutable Stage-B authority"
            )
        rows[metric] = {
            "direction": gate["direction"],
            "hard": gate["hard"],
            "metric": metric,
            "metric_intent": gate["definition"],
            "metric_intent_source": gate["source_of_rationale"],
            "parity": parity,
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


# ---------------------------------------------------------------------------
# Statistical derivations
# ---------------------------------------------------------------------------

RATE_METRICS = tuple(
    metric
    for metric in _corpus.TARGET_METRICS
    if metric != _corpus.RISK_SIZE_METRIC
)
RISK_P95_METRIC = _corpus.RISK_SIZE_METRIC

WILSON_FORMULA_ID = "WILSON_SCORE_INTERVAL_95_TWO_SIDED_UNCORRECTED_V1"
WILSON_CAPABILITY_RULE_ID = "PERFECT_SAMPLE_WILSON_CAPABILITY_FLOOR_V1"
EXACT_BOUNDARY_EXCEPTION_ID = (
    "EXACT_POINT_RATE_BOUNDARY_IDENTIFIABILITY_EXCEPTION_V1"
)
NEAREST_RANK_RULE_ID = "NEAREST_RANK_P95_NOT_SAMPLE_MAXIMUM_V1"


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
    """Derive the exact extreme-sample capability floor in a fixed context."""

    if direction not in ("minimum", "maximum"):
        raise SufficiencyGovernanceError("rate direction must be minimum or maximum")
    if threshold < 0 or threshold > 1:
        raise SufficiencyGovernanceError("a rate threshold must lie in [0, 1]")
    # At these closed boundaries every finite Wilson confidence limit is
    # strictly inside the unit interval.  Returning None records the theorem;
    # it must never be replaced by a search cap.
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
        raise SufficiencyGovernanceError("closed-form Wilson minimum failed owner parity")
    return candidate


def _rate_derivation(metric: str, gate: Mapping[str, Any]) -> dict[str, Any]:
    direction = str(gate["direction"])
    threshold = Decimal(str(gate["threshold"]))
    capability = _finite_wilson_minimum(threshold, direction)
    if capability is None:
        # The inherited 1.0 performance boundary is exact.  For every finite n,
        # WilsonLower(n,n) = n/(n+z^2) < 1, so no honest finite confidence floor
        # exists.  The exception selects only the smallest positive n at which
        # the inherited empirical point-rate gate is defined and can distinguish
        # one success from one failure.  It does not claim population precision
        # and does not alter the 1.0 performance threshold.
        if not (direction == "minimum" and threshold == 1):
            raise SufficiencyGovernanceError(
                "an unsupported closed-boundary rate has no finite Wilson minimum"
            )
        minimum = 1
        z_squared = _DECIMAL_CONTEXT.multiply(WILSON_Z_95, WILSON_Z_95)
        trace = {
            "boundary_proof": (
                "For every finite positive n, WilsonLower(n,n) = "
                "n / (n + z^2) < 1 because z^2 > 0."
            ),
            "n_capability": None,
            "n_capability_state": "NO_FINITE_POSITIVE_INTEGER",
            "n_minus_one_exception_criterion_satisfied": False,
            "n_selected": minimum,
            "n_selected_exception_criterion": (
                "denominator is positive, the empirical rate is defined, and "
                "the only non-perfect one-observation sample is distinguishable"
            ),
            "n_selected_exception_criterion_satisfied": True,
            "wilson_lower_at_selected_n": str(
                _wilson_extreme_bound(direction, minimum)
            ),
            "z_squared": str(z_squared),
        }
        return {
            "capability_formula": (
                "WilsonLower(successes=n,n,z) >= threshold"
            ),
            "derived_n_capability": None,
            "derivation_trace": trace,
            "direction": direction,
            "exception": {
                "applied": True,
                "alternatives_considered": {
                    "change_inherited_threshold": (
                        "REFUSED_CERTIFIED_CORPUS_CHANGE"
                    ),
                    "import_another_metrics_tolerance": (
                        "REFUSED_NEW_UNCALIBRATED_PERFORMANCE_THRESHOLD"
                    ),
                    "round_wilson_lower_to_one": (
                        "REFUSED_HIDDEN_NUMERICAL_APPROXIMATION"
                    ),
                    "unreachable_infinite_minimum": (
                        "REFUSED_NO_OPERATIONAL_STOPPING_POINT"
                    ),
                },
                "does_not_change_performance_gate": True,
                "method_id": EXACT_BOUNDARY_EXCEPTION_ID,
                "precision_claim": "ESTIMATOR_IDENTIFIABILITY_ONLY",
                "reason": (
                    "The inherited exact 1.0 point-rate boundary admits no "
                    "finite Wilson lower-bound capability n. Replacing 1.0 by "
                    "an interior tolerance would change the certified corpus. "
                    "The smallest positive denominator is therefore frozen as "
                    "an explicit estimator-identifiability exception, not as a "
                    "confidence or population-precision claim."
                ),
            },
            "metric": metric,
            "minimum_denominator": minimum,
            "successes_at_capability_probe": "n",
            "threshold": str(gate["threshold"]),
            "wilson_method_id": WILSON_FORMULA_ID,
            "wilson_z": str(WILSON_Z_95),
        }

    previous = capability - 1
    current_bound = _wilson_extreme_bound(direction, capability)
    previous_bound = (
        None if previous == 0 else _wilson_extreme_bound(direction, previous)
    )
    if direction == "maximum":
        formula = "WilsonUpper(successes=0,n,z) <= threshold"
        probe = 0
        current_satisfied = current_bound <= threshold
        previous_satisfied = (
            False if previous_bound is None else previous_bound <= threshold
        )
    else:
        formula = "WilsonLower(successes=n,n,z) >= threshold"
        probe = "n"
        current_satisfied = current_bound >= threshold
        previous_satisfied = (
            False if previous_bound is None else previous_bound >= threshold
        )
    return {
        "capability_formula": formula,
        "derived_n_capability": capability,
        "derivation_trace": {
            "bound_at_n_capability": str(current_bound),
            "bound_at_n_capability_minus_one": (
                None if previous_bound is None else str(previous_bound)
            ),
            "n_capability_criterion_satisfied": current_satisfied,
            "n_capability_minus_one_criterion_satisfied": previous_satisfied,
        },
        "direction": direction,
        "exception": {"applied": False},
        "metric": metric,
        "minimum_denominator": capability,
        "successes_at_capability_probe": probe,
        "threshold": str(gate["threshold"]),
        "wilson_method_id": WILSON_FORMULA_ID,
        "wilson_z": str(WILSON_Z_95),
    }


def nearest_rank(probability: Decimal, denominator: int) -> int:
    if denominator <= 0:
        raise SufficiencyGovernanceError("nearest rank needs a positive denominator")
    if probability <= 0 or probability > 1:
        raise SufficiencyGovernanceError("nearest-rank probability must lie in (0, 1]")
    with localcontext(_DECIMAL_CONTEXT) as context:
        return int(
            context.multiply(probability, Decimal(denominator)).to_integral_value(
                rounding=ROUND_CEILING,
                context=context,
            )
        )


def _nearest_rank_p95_derivation() -> dict[str, Any]:
    probability = _corpus.RISK_SIZE_PROBABILITY
    minimum = next(
        denominator
        for denominator in range(1, 10_000)
        if nearest_rank(probability, denominator) < denominator
    )
    rank_before = nearest_rank(probability, minimum - 1)
    rank_at = nearest_rank(probability, minimum)
    rank_after = nearest_rank(probability, minimum + 1)
    return {
        "derivation": (
            "smallest positive n for which ceil(0.95*n) < n, so the selected "
            "nearest-rank p95 is not the sample maximum"
        ),
        "estimator": _corpus.RISK_SIZE_STATISTIC,
        "formula": "rank = ceil(0.95 * n)",
        "metric": RISK_P95_METRIC,
        "minimum_denominator": minimum,
        "n_min_minus_one": {
            "denominator": minimum - 1,
            "is_sample_maximum": rank_before == minimum - 1,
            "rank": rank_before,
        },
        "n_min": {
            "denominator": minimum,
            "is_sample_maximum": rank_at == minimum,
            "rank": rank_at,
            "tail_observations_above_rank": minimum - rank_at,
        },
        "n_min_plus_one": {
            "denominator": minimum + 1,
            "is_sample_maximum": rank_after == minimum + 1,
            "rank": rank_after,
            "tail_observations_above_rank": minimum + 1 - rank_after,
        },
        "precision_claim": "TAIL_ORDER_STATISTIC_IDENTIFIABILITY_ONLY",
        "probability": str(probability),
        "rule_id": NEAREST_RANK_RULE_ID,
        "sufficiency_reason": (
            "At n=20 the nearest-rank p95 first selects the nineteenth order "
            "statistic and leaves one observed value above it. This is enough "
            "to make the frozen integration diagnostic a tail statistic rather "
            "than the maximum; it is not a claim about population-quantile "
            "precision or distributional coverage."
        ),
    }


def statistical_derivations() -> dict[str, Any]:
    gates = _historical_gate_rows()
    rates = {
        metric: _rate_derivation(metric, gates[metric]) for metric in RATE_METRICS
    }
    payload = {
        "ambient_decimal_context_consumed": False,
        "nearest_rank_p95": _nearest_rank_p95_derivation(),
        "rate_metrics": rates,
        "schema_version": "PROSPECTIVE_SUFFICIENCY_STATISTICAL_DERIVATIONS_V1",
        "wilson": {
            "confidence_level": "0.95",
            "continuity_correction_applied": False,
            "formula_id": WILSON_FORMULA_ID,
            "method_owner": (
                "btc_predictor.research.structural_threshold_calibration."
                "wilson_interval"
            ),
            "owner_method_id": UNCERTAINTY_METHOD_ID,
            "purpose": "PRE_DATA_MINIMUM_DENOMINATOR_SELECTION_ONLY",
            "replaces_inherited_point_metric_pass_fail": False,
            "rule_id": WILSON_CAPABILITY_RULE_ID,
            "z": str(WILSON_Z_95),
        },
    }
    return _with_definition_hash(payload)


def metric_sufficiency_minima() -> dict[str, Any]:
    protocol = _require_certified_corpus()
    gates = _historical_gate_rows()
    contracts = _corpus.metric_evidence_contracts()["contracts"]
    derivations = statistical_derivations()
    rows: dict[str, dict[str, Any]] = {}
    for metric in _corpus.TARGET_METRICS:
        gate = gates[metric]
        contract = contracts[metric]
        if metric == RISK_P95_METRIC:
            derivation = derivations["nearest_rank_p95"]
            method = NEAREST_RANK_RULE_ID
        else:
            derivation = derivations["rate_metrics"][metric]
            method = (
                derivation["exception"]["method_id"]
                if derivation["exception"]["applied"]
                else WILSON_CAPABILITY_RULE_ID
            )
        rows[metric] = {
            "additional_conditions": [
                "100_PERCENT_SCHEDULED_SLOT_ACCOUNTING_AT_PREFIX",
                "UNACCOUNTED_SCHEDULED_SLOT_COUNT_EQUALS_ZERO",
                "CERTIFIED_CANDIDATE_NEUTRAL_UNIVERSE_AND_EXCLUSIONS",
                "ZERO_DENOMINATOR_IS_UNDEFINED_INSUFFICIENT_EVIDENCE",
            ],
            "cadence": contract["cadence"],
            "counter_fields": {
                "accounted_opportunity_count": "accounted_opportunity_count",
                "data_quality_fail_count": "data_quality_fail_count",
                "denominator": "evaluable_denominator",
                "exclusions": "exclusion_counts_by_reason",
                "not_comparable": "not_comparable_count",
                "not_evaluable": "not_evaluable_count",
                "reference_unavailable": "reference_unavailable_count",
            },
            "direction": gate["direction"],
            "hard": gate["hard"],
            "metric": metric,
            "metric_evidence_contract_sha256": protocol[
                "child_definition_sha256"
            ]["metric_evidence_contracts"],
            "metric_intent": gate["metric_intent"],
            "minimum_denominator": derivation["minimum_denominator"],
            "no_pooling": True,
            "performance_gate_unchanged": True,
            "statistical_method": method,
            "threshold": str(gate["threshold"]),
            "universe": contract["universe"],
            "zero_denominator_outcome": _corpus.UNDEFINED_INSUFFICIENT_EVIDENCE,
            "zero_denominator_sufficient": False,
        }
    payload = {
        "certified_corpus_sha256": CERTIFIED_CORPUS_SHA256,
        "decision_universe_sha256": protocol["child_definition_sha256"][
            "decision_universe"
        ],
        "metric_count": len(rows),
        "metrics": rows,
        "no_candidate_identity_used_to_choose_minima": True,
        "no_observed_outcome_used_to_choose_minima": True,
        "schema_version": "PROSPECTIVE_METRIC_SUFFICIENCY_MINIMA_V1",
        "statistical_derivations_sha256": derivations["definition_sha256"],
    }
    return _with_definition_hash(payload)


# ---------------------------------------------------------------------------
# Coverage, temporal and stopping policies
# ---------------------------------------------------------------------------

NO_SEPARATE_COVERAGE_FLOOR = "NO_SEPARATE_NUMERICAL_COVERAGE_FLOOR"
NO_TEMPORAL_MINIMUM = "NONE"


def coverage_policy() -> dict[str, Any]:
    payload = {
        "accounting_requirement": {
            "accounted_scheduled_slot_rate": "1.0",
            "exactly_one_persisted_disposition_per_scheduled_slot": True,
            "unaccounted_scheduled_slot_count_required": 0,
            "unknown_or_missing_disposition_is_an_exclusion": False,
        },
        "applicable_existing_numerical_standard_found": False,
        "candidate_neutral_exclusions_required": True,
        "decision": NO_SEPARATE_COVERAGE_FLOOR,
        "diagnostics_not_gates": [
            "distinct_utc_days",
            "distinct_iso_weeks",
            "largest_single_day_denominator_contribution",
            "largest_single_week_denominator_contribution",
        ],
        "evaluability_or_comparability_floor": None,
        "reasoning": (
            "No frozen repository percentage applies to these eight prospective "
            "universes. The historical 0.50 structural-pair comparability rule "
            "is explicitly scoped to a different V3 gate family, while the "
            "certified corpus already fixes candidate-neutral universes and "
            "exclusions. Requiring every scheduled slot to be accounted and "
            "each metric to reach its own denominator minimum prevents a "
            "candidate from buying sufficiency through silent omissions; a "
            "second percentage would add an uncalibrated conventional number."
        ),
        "alternatives_considered": {
            "reuse_structural_pair_floor_0_50": "REFUSED_WRONG_FROZEN_SCOPE",
            "select_conventional_0_90_0_95_or_0_99": (
                "REFUSED_NO_OUTCOME_INDEPENDENT_OPERATIONAL_DERIVATION"
            ),
        },
        "scoped_out_standard": {
            "id": "STRUCTURAL_COMPARABILITY_SUFFICIENCY_V1",
            "reason": "applies only to V3 structural gate pairs, not these universes",
        },
        "schema_version": "PROSPECTIVE_SUFFICIENCY_COVERAGE_POLICY_V1",
    }
    return _with_definition_hash(payload)


def temporal_policy() -> dict[str, Any]:
    payload = {
        "concentration_diagnostics_persisted": True,
        "minimum_calendar_duration": None,
        "minimum_distinct_iso_weeks": None,
        "minimum_distinct_utc_days": None,
        "policy": NO_TEMPORAL_MINIMUM,
        "reasoning": (
            "The metric-specific event and decision denominators define the "
            "amount of Stage-B integration evidence. No existing authority "
            "requires temporal spreading for these gates, and no outcome-free "
            "derivation identifies a calendar value. Concentration is therefore "
            "persisted diagnostically rather than turned into an arbitrary gate."
        ),
        "alternatives_considered": {
            "30_60_90_or_180_calendar_days": (
                "REFUSED_NO_OUTCOME_INDEPENDENT_DERIVATION"
            ),
            "reuse_stage_c_90_days": "REFUSED_DIFFERENT_GOVERNANCE_STAGE",
        },
        "schema_version": "PROSPECTIVE_SUFFICIENCY_TEMPORAL_POLICY_V1",
        "stage_c_live_shadow_days_imported": False,
        "stage_c_separation": (
            "live_shadow_days >= 90 remains the distinct post-certification "
            "Stage-C promotion gate and is not Stage-B sufficiency"
        ),
    }
    return _with_definition_hash(payload)


SUFFICIENCY_STATES = (
    "NOT_STARTED",
    "ACCUMULATING",
    "METRIC_PARTIALLY_SUFFICIENT",
    "ALL_METRICS_SUFFICIENT",
    "EVALUATION_CUTOFF_FROZEN",
)


def blind_monitor_contract() -> dict[str, Any]:
    protocol = _require_certified_corpus()
    payload = {
        "allowed_input_fields": [
            "cadence",
            "decision_time",
            "global_disposition",
            "global_reason_codes",
            "metric",
            "metric_disposition",
            "metric_reason_code",
            "observation_time",
            "slot_id",
            "universe_member",
        ],
        "contract_version": "PROSPECTIVE_STAGE_B_SUFFICIENCY_MONITOR_V1",
        "cutoff_clock": "decision_time",
        "decision_universe_sha256": protocol["child_definition_sha256"][
            "decision_universe"
        ],
        "denominator_contribution": (
            "1 iff certified universe_member is true and metric_disposition is "
            "EVALUATED; otherwise 0"
        ),
        "metric_evidence_contract_sha256": protocol["child_definition_sha256"][
            "metric_evidence_contracts"
        ],
        "outcome_blind": True,
        "production_visibility_before_cutoff": {
            "decision_maker_visible": [
                "accounting_progress",
                "coverage_diagnostics",
                "denominator_progress",
                "sufficiency_state",
            ],
            "target_outcomes_visible": False,
        },
        "prohibited_input_fields": [
            "aggregate_metric_result",
            "candidate_control_agreement",
            "metric_numerator",
            "pass_fail_result",
            "risk_size_relative_difference",
            "success_or_failure_bit",
        ],
        "scheduled_slot_owner": (
            "btc_predictor.research.prospective_integration_corpus."
            "scheduled_decision_slots"
        ),
        "schema_version": "PROSPECTIVE_STAGE_B_SUFFICIENCY_MONITOR_CONTRACT_V1",
        "states": list(SUFFICIENCY_STATES),
        "state_transitions": {
            "NOT_STARTED": ["ACCUMULATING"],
            "ACCUMULATING": [
                "METRIC_PARTIALLY_SUFFICIENT",
                "ALL_METRICS_SUFFICIENT",
                "EVALUATION_CUTOFF_FROZEN",
            ],
            "METRIC_PARTIALLY_SUFFICIENT": [
                "ALL_METRICS_SUFFICIENT",
                "EVALUATION_CUTOFF_FROZEN",
            ],
            "ALL_METRICS_SUFFICIENT": ["EVALUATION_CUTOFF_FROZEN"],
            "EVALUATION_CUTOFF_FROZEN": [],
        },
        "universe_membership_authority": {
            "candidate_controlled_override_permitted": False,
            "rule": (
                "Replay and derive membership from the certified decision-"
                "universe predicate and evidence graph; never trust a caller-"
                "selected exclusion label"
            ),
        },
        "window_start_semantics": (
            "epoch_observation_start is the first canonical post-warmup "
            "observation boundary; warmup capture is never denominator evidence"
        ),
    }
    return _with_definition_hash(payload)


def stopping_rule() -> dict[str, Any]:
    payload = {
        "collection_stop_condition": (
            "ALL eight metric-specific sufficiency contracts satisfied AND "
            "all global accounting and coverage requirements satisfied"
        ),
        "global_metric_rule": "ALL_8_NO_WEIGHTING_NO_SUBSTITUTION",
        "metric_numerators_consumed": False,
        "optional_stopping_permitted": False,
        "outcome_blind": True,
        "pass_chasing_permitted": False,
        "performance_results_consumed": False,
        "same_epoch_extension_after_evaluation_permitted": False,
        "schema_version": "PROSPECTIVE_STAGE_B_STOPPING_RULE_V1",
        "successor_epoch_rule": (
            "A future re-evaluation requires separate prospective governance "
            "authorized before that future epoch's outcomes are seen"
        ),
    }
    return _with_definition_hash(payload)


def evaluation_cutoff_contract() -> dict[str, Any]:
    payload = {
        "corpus_freeze_rule": (
            "Freeze the Stage-B evaluation corpus to evidence PIT-available at "
            "or before stage_b_sufficiency_cutoff"
        ),
        "cutoff_definition": (
            "earliest decision_time at which all eight metric minima and all "
            "global accounting/coverage requirements are simultaneously satisfied"
        ),
        "cutoff_field": "stage_b_sufficiency_cutoff",
        "deterministic": True,
        "evidence_after_cutoff_included": False,
        "future_evaluation_contract_binding_required": True,
        "pre_cutoff_stage_b_status": "INSUFFICIENT_EVIDENCE",
        "schema_version": "PROSPECTIVE_STAGE_B_EVALUATION_CUTOFF_CONTRACT_V1",
    }
    return _with_definition_hash(payload)


# ---------------------------------------------------------------------------
# Top-level hash-bound definition and artifacts
# ---------------------------------------------------------------------------

_CHILD_ARTIFACTS = (
    (BLIND_MONITOR_FILENAME, "blind_monitor_contract", "blind_monitor_contract"),
    (COVERAGE_FILENAME, "coverage_policy", "coverage_policy"),
    (CUTOFF_FILENAME, "evaluation_cutoff_contract", "evaluation_cutoff_contract"),
    (MINIMA_FILENAME, "metric_sufficiency_minima", "metric_sufficiency_minima"),
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
            "protocol_sha256": CERTIFIED_CORPUS_SHA256,
            "protocol_version": CERTIFIED_CORPUS_VERSION,
            "review_documentation_commit": (
                CERTIFIED_CORPUS_REVIEW_DOCUMENTATION_COMMIT
            ),
            "review_fix_commit": CERTIFIED_CORPUS_REVIEW_FIX_COMMIT,
            "review_result": CERTIFIED_CORPUS_REVIEW_RESULT,
            "review_ticket": CERTIFIED_CORPUS_REVIEW_TICKET,
        },
        "change_procedure": (
            "Any material change to a minimum denominator, coverage policy, "
            "temporal rule, Wilson confidence level, quantile sufficiency rule, "
            "blind stopping logic or cutoff semantics requires "
            f"{SUCCESSOR_GOVERNANCE_VERSION} and a new prospective epoch where applicable."
        ),
        "child_definition_sha256": dict(sorted(child_hashes.items())),
        "collection_authorized": False,
        "decimal_precision": _DECIMAL_CONTEXT.prec,
        "epic_t": {"modified": False, "reopened": False},
        "evaluation_contract_identity": (
            "SUPPLIED_LATER_BY_PROSPECTIVE_INTEGRATION_EVALUATION_CONTRACT_V1"
        ),
        "final_classification": FINAL_CLASSIFICATION,
        "governance_version": GOVERNANCE_VERSION,
        "material_child_count": len(child_hashes),
        "postp1_004_authorized": False,
        "program_ticket": PROGRAM_TICKET,
        "schema_version": GOVERNANCE_SCHEMA_VERSION,
        "stage_b_performance_gate_owner": _corpus.HISTORICAL_GATE_AUTHORITY,
        "stage_b_performance_gates_changed": False,
        "status": GOVERNANCE_STATUS,
        "target_metrics": list(_corpus.TARGET_METRICS),
        "workstream": WORKSTREAM,
        "parent_child_bindings": {
            "decision_universe_sha256": protocol["child_definition_sha256"][
                "decision_universe"
            ],
            "metric_evidence_contract_sha256": protocol[
                "child_definition_sha256"
            ]["metric_evidence_contracts"],
            "stage_b_evaluation_contract_sha256": protocol[
                "child_definition_sha256"
            ]["stage_b_evaluation_contract"],
        },
        "safety": {
            "btc019_sealed_data_accessed": False,
            "prospective_observations_collected": False,
            "real_stage_b_evaluation_run": False,
            "real_stage_b_numerators_inspected": False,
        },
    }
    return _with_definition_hash(payload)


def protocol_hashes() -> dict[str, str]:
    definition = sufficiency_governance_definition()
    hashes = dict(definition["child_definition_sha256"])
    hashes["sufficiency_governance"] = definition["definition_sha256"]
    return dict(sorted(hashes.items()))


def verify_sufficiency_governance_definition(persisted: Mapping[str, Any]) -> None:
    expected = sufficiency_governance_definition()
    if dict(persisted) != expected:
        raise SufficiencyGovernanceError("persisted sufficiency governance does not reproduce")
    recomputed = dict(persisted)
    declared = recomputed.pop("definition_sha256", None)
    if not _is_sha256(declared) or _digest(recomputed) != declared:
        raise SufficiencyGovernanceError("sufficiency-governance hash does not recompute")


# ---------------------------------------------------------------------------
# Executable blind monitor over synthetic or future persisted projections
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BlindMetricDisposition:
    """Outcome-free quantity/accounting projection for one metric and slot."""

    metric: str
    universe_member: bool
    disposition: str
    reason_code: str | None = None


@dataclass(frozen=True)
class BlindScheduledSlot:
    """One expected corpus slot and all cadence-applicable metric dispositions."""

    cadence: str
    observation_time: datetime
    decision_time: datetime
    slot_id: str
    global_disposition: str
    global_reason_codes: tuple[str, ...]
    metrics: tuple[BlindMetricDisposition, ...]


def _require_utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise SufficiencyGovernanceError(f"{name} must be timezone-aware UTC")
    if value.utcoffset() != timedelta(0):
        raise SufficiencyGovernanceError(f"{name} must be UTC")
    return value


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
                    observation_time,
                    observation_time,
                    cadence=cadence,
                )
            )
            observation_time += step
    return tuple(
        sorted(rows, key=lambda row: (row["decision_time"], row["cadence"], row["slot_id"]))
    )


_METRIC_CADENCES = {
    metric: str(contract["cadence"])
    for metric, contract in _corpus.metric_evidence_contracts()["contracts"].items()
}


def _metric_cadences() -> dict[str, str]:
    return dict(_METRIC_CADENCES)


def _validate_blind_slot(slot: BlindScheduledSlot) -> tuple[str, dict[str, BlindMetricDisposition]]:
    if not isinstance(slot, BlindScheduledSlot):
        raise SufficiencyGovernanceError("blind monitor accepts BlindScheduledSlot only")
    observation_time = _require_utc(slot.observation_time, "observation_time")
    decision_time = _require_utc(slot.decision_time, "decision_time")
    if slot.cadence not in _corpus.DECISION_CADENCES:
        raise SufficiencyGovernanceError("blind slot names an unknown cadence")
    expected_decision = _corpus.decision_time_for(observation_time, slot.cadence)
    if decision_time != expected_decision:
        raise SufficiencyGovernanceError("blind slot decision_time does not reproduce")
    expected = _corpus.scheduled_decision_slots(
        observation_time,
        observation_time,
        cadence=slot.cadence,
    )[0]
    if slot.slot_id != expected["slot_id"]:
        raise SufficiencyGovernanceError("blind slot id does not reproduce")
    if slot.global_disposition not in _corpus.OBSERVATION_STATES:
        raise SufficiencyGovernanceError("blind slot names an unknown disposition")
    if len(set(slot.global_reason_codes)) != len(slot.global_reason_codes):
        raise SufficiencyGovernanceError("global reason codes must be unique")
    if any(
        reason not in _corpus.OBSERVATION_REASON_VOCABULARY
        for reason in slot.global_reason_codes
    ):
        raise SufficiencyGovernanceError("blind slot names an unknown reason code")
    if slot.global_disposition != _corpus.STATE_EVALUATED and not slot.global_reason_codes:
        raise SufficiencyGovernanceError(
            "a non-evaluated scheduled slot needs a frozen reason code"
        )

    by_metric: dict[str, BlindMetricDisposition] = {}
    for row in slot.metrics:
        if not isinstance(row, BlindMetricDisposition):
            raise SufficiencyGovernanceError("metric rows must be blind dispositions")
        if row.metric in by_metric:
            raise SufficiencyGovernanceError("a slot repeats a metric disposition")
        if type(row.universe_member) is not bool:
            raise SufficiencyGovernanceError("universe_member must be Boolean")
        if row.disposition not in _corpus.OBSERVATION_STATES:
            raise SufficiencyGovernanceError("metric row names an unknown disposition")
        if row.disposition == _corpus.STATE_EVALUATED:
            if row.reason_code is not None:
                raise SufficiencyGovernanceError("an evaluated metric row has no exclusion reason")
        elif row.reason_code not in _corpus.OBSERVATION_REASON_VOCABULARY:
            raise SufficiencyGovernanceError("excluded metric row needs a frozen reason code")
        expected_reasons = {
            _corpus.STATE_NOT_EVALUABLE: set(_corpus.NOT_EVALUABLE_REASONS),
            _corpus.STATE_NOT_COMPARABLE: set(_corpus.NOT_COMPARABLE_REASONS),
            _corpus.STATE_DATA_QUALITY_FAIL: set(_corpus.DATA_QUALITY_FAIL_REASONS),
            _corpus.STATE_REFERENCE_UNAVAILABLE: set(
                _corpus.REFERENCE_UNAVAILABLE_REASONS
            ),
        }
        if (
            row.disposition != _corpus.STATE_EVALUATED
            and row.reason_code not in expected_reasons[row.disposition]
        ):
            raise SufficiencyGovernanceError(
                "metric disposition and frozen reason category disagree"
            )
        by_metric[row.metric] = row
    cadences = _metric_cadences()
    required = {metric for metric, cadence in cadences.items() if cadence == slot.cadence}
    if set(by_metric) != required:
        raise SufficiencyGovernanceError(
            "a blind slot must account for every cadence-applicable target metric"
        )
    if slot.global_disposition != _corpus.STATE_EVALUATED and any(
        row.disposition == _corpus.STATE_EVALUATED for row in by_metric.values()
    ):
        raise SufficiencyGovernanceError(
            "a globally unusable slot cannot contribute an evaluated metric"
        )
    return slot.slot_id, by_metric


def _iso_week(value: datetime) -> str:
    year, week, _weekday = value.isocalendar()
    return f"{year:04d}-W{week:02d}"


def _blind_slot_payload(slot: BlindScheduledSlot) -> dict[str, Any]:
    return {
        "cadence": slot.cadence,
        "decision_time": slot.decision_time.isoformat(),
        "global_disposition": slot.global_disposition,
        "global_reason_codes": list(slot.global_reason_codes),
        "metrics": [
            {
                "disposition": row.disposition,
                "metric": row.metric,
                "reason_code": row.reason_code,
                "universe_member": row.universe_member,
            }
            for row in sorted(slot.metrics, key=lambda item: item.metric)
        ],
        "observation_time": slot.observation_time.isoformat(),
        "slot_id": slot.slot_id,
    }


def _empty_metric_counter() -> dict[str, Any]:
    return {
        "accounted_opportunity_count": 0,
        "data_quality_fail_count": 0,
        "evaluable_denominator": 0,
        "eligible_opportunities": 0,
        "exclusion_counts_by_reason": Counter(),
        "not_comparable_count": 0,
        "not_evaluable_count": 0,
        "reference_unavailable_count": 0,
        "day_contributions": Counter(),
        "week_contributions": Counter(),
    }


def _add_metric_row(
    counter: dict[str, Any],
    row: BlindMetricDisposition,
    decision_time: datetime,
) -> None:
    counter["accounted_opportunity_count"] += 1
    if row.universe_member:
        counter["eligible_opportunities"] += 1
    if row.universe_member and row.disposition == _corpus.STATE_EVALUATED:
        counter["evaluable_denominator"] += 1
        counter["day_contributions"][decision_time.date().isoformat()] += 1
        counter["week_contributions"][_iso_week(decision_time)] += 1
    elif row.disposition != _corpus.STATE_EVALUATED:
        counter["exclusion_counts_by_reason"][row.reason_code] += 1
        if row.disposition == _corpus.STATE_NOT_EVALUABLE:
            counter["not_evaluable_count"] += 1
        elif row.disposition == _corpus.STATE_NOT_COMPARABLE:
            counter["not_comparable_count"] += 1
        elif row.disposition == _corpus.STATE_DATA_QUALITY_FAIL:
            counter["data_quality_fail_count"] += 1
        elif row.disposition == _corpus.STATE_REFERENCE_UNAVAILABLE:
            counter["reference_unavailable_count"] += 1


def _materialize_metric_state(
    metric: str,
    counter: Mapping[str, Any],
    *,
    required: int,
    first_sufficient_at: str | None,
    universe: str,
) -> dict[str, Any]:
    day_counts: Counter[str] = counter["day_contributions"]
    week_counts: Counter[str] = counter["week_contributions"]
    denominator = int(counter["evaluable_denominator"])
    return {
        "accounted_opportunity_count": int(counter["accounted_opportunity_count"]),
        "data_quality_fail_count": int(counter["data_quality_fail_count"]),
        "distinct_iso_weeks": len(week_counts),
        "distinct_utc_days": len(day_counts),
        "eligible_opportunities": int(counter["eligible_opportunities"]),
        "event_count": (
            int(counter["eligible_opportunities"])
            if metric in _corpus.STOP_EVENT_METRICS
            else None
        ),
        "evaluable_denominator": denominator,
        "exclusion_counts_by_reason": dict(sorted(counter["exclusion_counts_by_reason"].items())),
        "first_sufficient_at": first_sufficient_at,
        "largest_single_day_denominator_contribution": max(day_counts.values(), default=0),
        "largest_single_week_denominator_contribution": max(week_counts.values(), default=0),
        "metric": metric,
        "not_comparable_count": int(counter["not_comparable_count"]),
        "not_evaluable_count": int(counter["not_evaluable_count"]),
        "reference_unavailable_count": int(counter["reference_unavailable_count"]),
        "required_denominator": required,
        "sufficient": denominator >= required and denominator > 0,
        "trade_count": denominator if metric == _corpus.RISK_SIZE_METRIC else None,
        "universe": universe,
    }


def evaluate_blind_sufficiency(
    slots: Sequence[BlindScheduledSlot],
    *,
    collection_epoch_id: str,
    evaluation_contract_sha256: str,
    epoch_observation_start: datetime,
    current_decision_time: datetime,
) -> dict[str, Any]:
    """Evaluate quantity-only sufficiency and freeze the earliest valid cutoff.

    There is intentionally no numerator or metric-value parameter.  Slot
    coordinates are checked against the certified corpus scheduler and every
    cadence-applicable metric must have one disposition projection.
    """

    _require_certified_corpus()
    if not isinstance(collection_epoch_id, str) or not collection_epoch_id:
        raise SufficiencyGovernanceError("collection_epoch_id must be non-empty")
    if not _is_sha256(evaluation_contract_sha256):
        raise SufficiencyGovernanceError("evaluation contract identity must be SHA-256")
    start = _require_utc(epoch_observation_start, "epoch_observation_start")
    current = _require_utc(current_decision_time, "current_decision_time")
    if current < start:
        raise SufficiencyGovernanceError(
            "current_decision_time cannot precede the collection epoch"
        )
    expected = _expected_slots_through(start, current)
    expected_by_id = {row["slot_id"]: row for row in expected}

    records: dict[str, tuple[BlindScheduledSlot, dict[str, BlindMetricDisposition]]] = {}
    for slot in slots:
        slot_id, metrics = _validate_blind_slot(slot)
        if slot.decision_time > current:
            raise SufficiencyGovernanceError("blind evidence lies after current_decision_time")
        if slot_id not in expected_by_id:
            raise SufficiencyGovernanceError("blind evidence is outside the frozen epoch census")
        if slot_id in records:
            raise SufficiencyGovernanceError("a scheduled slot has multiple dispositions")
        records[slot_id] = (slot, metrics)

    minima = metric_sufficiency_minima()["metrics"]
    counters = {metric: _empty_metric_counter() for metric in _corpus.TARGET_METRICS}
    first_sufficient: dict[str, str | None] = {
        metric: None for metric in _corpus.TARGET_METRICS
    }
    cutoff: datetime | None = None
    expected_prefix = 0
    accounted_prefix = 0

    expected_by_time: dict[datetime, list[dict[str, str]]] = defaultdict(list)
    for row in expected:
        expected_by_time[datetime.fromisoformat(row["decision_time"])].append(row)
    for decision_time in sorted(expected_by_time):
        group = expected_by_time[decision_time]
        expected_prefix += len(group)
        for expected_row in group:
            record = records.get(expected_row["slot_id"])
            if record is None:
                continue
            accounted_prefix += 1
            _slot, metric_rows = record
            for metric, row in metric_rows.items():
                _add_metric_row(counters[metric], row, decision_time)
                required = int(minima[metric]["minimum_denominator"])
                if (
                    first_sufficient[metric] is None
                    and counters[metric]["evaluable_denominator"] >= required
                ):
                    first_sufficient[metric] = decision_time.isoformat()
        all_metrics = all(
            counters[metric]["evaluable_denominator"]
            >= int(minima[metric]["minimum_denominator"])
            and counters[metric]["evaluable_denominator"] > 0
            for metric in _corpus.TARGET_METRICS
        )
        if all_metrics and accounted_prefix == expected_prefix:
            cutoff = decision_time
            break

    # If a cutoff was found, counters already stop exactly there. Otherwise
    # they contain every accounted record through the requested current time.
    metric_states = {
        metric: _materialize_metric_state(
            metric,
            counters[metric],
            required=int(minima[metric]["minimum_denominator"]),
            first_sufficient_at=first_sufficient[metric],
            universe=str(minima[metric]["universe"]),
        )
        for metric in _corpus.TARGET_METRICS
    }
    all_metric_specific = all(row["sufficient"] for row in metric_states.values())
    if cutoff is not None:
        state = "EVALUATION_CUTOFF_FROZEN"
        cutoff_expected = sum(
            1
            for row in expected
            if datetime.fromisoformat(row["decision_time"]) <= cutoff
        )
        cutoff_accounted = cutoff_expected
    else:
        cutoff_expected = len(expected)
        cutoff_accounted = len(records)
        if not records:
            state = "NOT_STARTED"
        elif all_metric_specific:
            state = "ALL_METRICS_SUFFICIENT"
        elif any(row["sufficient"] for row in metric_states.values()):
            state = "METRIC_PARTIALLY_SUFFICIENT"
        else:
            state = "ACCUMULATING"
    unaccounted = cutoff_expected - cutoff_accounted
    overall_sufficient = cutoff is not None

    definition = sufficiency_governance_definition()
    minima_definition = metric_sufficiency_minima()
    coverage = coverage_policy()
    result = {
        "accounting": {
            "accounted_scheduled_slots": cutoff_accounted,
            "scheduled_slots": cutoff_expected,
            "unaccounted_scheduled_slots": unaccounted,
        },
        "collection_epoch_id": collection_epoch_id,
        "coverage_policy_sha256": coverage["definition_sha256"],
        "current_decision_time": current.isoformat(),
        "decision_universe_sha256": minima_definition["decision_universe_sha256"],
        "evaluation_contract_sha256": evaluation_contract_sha256,
        "evaluation_contract_identity_owns": [
            "candidate_reference_identity",
            "configuration_identity",
            "control_reference_identity",
            "strategy_identity",
        ],
        "evaluation_corpus_frozen": overall_sufficient,
        "evaluation_corpus_slot_ids": sorted(
            slot_id
            for slot_id, (slot, _metrics) in records.items()
            if cutoff is not None and slot.decision_time <= cutoff
        ),
        "global_condition": "ALL_8_AND_GLOBAL_ACCOUNTING_COVERAGE",
        "governance_sha256": definition["definition_sha256"],
        "metric_evidence_contract_sha256": next(
            iter(minima_definition["metrics"].values())
        )["metric_evidence_contract_sha256"],
        "metric_states": metric_states,
        "overall_stage_b_status": (
            "READY_FOR_STAGE_B_EVALUATION"
            if overall_sufficient
            else "INSUFFICIENT_EVIDENCE"
        ),
        "overall_sufficient": overall_sufficient,
        "schema_version": "PROSPECTIVE_STAGE_B_SUFFICIENCY_RESULT_V1",
        "stage_b_sufficiency_cutoff": (
            None if cutoff is None else cutoff.isoformat()
        ),
        "state": state,
        "window_start": start.isoformat(),
    }
    cutoff_blind_payloads = sorted(
        (
            _blind_slot_payload(slot)
            for slot, _metrics in records.values()
            if cutoff is not None and slot.decision_time <= cutoff
        ),
        key=lambda row: (row["decision_time"], row["cadence"], row["slot_id"]),
    )
    result["evaluation_corpus_blind_evidence_sha256"] = (
        None if cutoff is None else _digest(cutoff_blind_payloads)
    )
    result["evaluation_corpus_sha256"] = (
        None
        if cutoff is None
        else _digest(
            {
                "collection_epoch_id": collection_epoch_id,
                "cutoff": cutoff.isoformat(),
                "evaluation_contract_sha256": evaluation_contract_sha256,
                "governance_sha256": definition["definition_sha256"],
                "blind_evidence_sha256": result[
                    "evaluation_corpus_blind_evidence_sha256"
                ],
                "slot_ids": result["evaluation_corpus_slot_ids"],
            }
        )
    )
    result["result_sha256"] = _digest(result)
    return result


def assert_evaluation_epoch_not_extended(
    *,
    frozen_cutoff: datetime,
    proposed_cutoff: datetime,
    evaluated_result: str,
) -> None:
    """Refuse pass-chasing or any other extension of an evaluated epoch."""

    frozen = _require_utc(frozen_cutoff, "frozen_cutoff")
    proposed = _require_utc(proposed_cutoff, "proposed_cutoff")
    if evaluated_result not in ("PASS", "FAIL"):
        raise SufficiencyGovernanceError("evaluated_result must be PASS or FAIL")
    if proposed != frozen:
        raise EvaluationEpochFrozenError(
            "an evaluated Stage-B epoch is frozen at its earliest sufficient cutoff"
        )


# ---------------------------------------------------------------------------
# Deterministic report and persistence
# ---------------------------------------------------------------------------


def _report_markdown(definition: Mapping[str, Any]) -> str:
    minima = metric_sufficiency_minima()["metrics"]
    derivations = statistical_derivations()
    diff = semantic_diff_from_stage_b_gates()
    coverage = coverage_policy()
    temporal = temporal_policy()
    lines = [
        f"# {GOVERNANCE_VERSION}",
        "",
        f"- Ticket: `{PROGRAM_TICKET}`",
        f"- Status: `{GOVERNANCE_STATUS}`",
        f"- Definition hash: `{definition['definition_sha256']}`",
        f"- Final classification: `{FINAL_CLASSIFICATION}`",
        f"- Certified corpus: `{CERTIFIED_CORPUS_SHA256}`",
        f"- Material child count: `{definition['material_child_count']}`",
        "- Prospective observations collected: `NO`",
        "- Real Stage-B evaluation run: `NO`",
        "- POSTP1-004 authorized: `NO`",
        "- Prospective collection authorized: `NO`",
        "- BTC-019 reopened / sealed sample touched: `NO / NO`",
        "",
        "## Material children",
        "",
    ]
    for name, digest in definition["child_definition_sha256"].items():
        lines.append(f"- `{name}`: `{digest}`")
    lines += [
        "",
        "## Historical Stage-B parity",
        "",
        f"- Metrics recovered: `{diff['metric_count']}`",
        f"- Threshold changes: `{diff['threshold_change_count']}`",
        f"- Direction changes: `{diff['direction_change_count']}`",
        f"- Hard-role changes: `{diff['hard_role_change_count']}`",
        f"- Metric-intent changes: `{diff['metric_intent_change_count']}`",
        "- Sufficiency changes the inherited point-metric PASS/FAIL rule: `NO`",
        "",
        "## Metric minima",
        "",
        "| metric | threshold | direction | minimum n | method |",
        "| --- | ---: | --- | ---: | --- |",
    ]
    for metric in _corpus.TARGET_METRICS:
        row = minima[metric]
        lines.append(
            f"| `{metric}` | `{row['threshold']}` | `{row['direction']}` | "
            f"`{row['minimum_denominator']}` | `{row['statistical_method']}` |"
        )
    boundary = derivations["rate_metrics"][_corpus.CROSS_MARKET_METRIC]
    p95 = derivations["nearest_rank_p95"]
    lines += [
        "",
        "The inherited `cross_market_confirmed_stop_preservation_rate >= 1.0` "
        "has no finite Wilson capability denominator: for every finite positive "
        "`n`, `WilsonLower(n,n) = n/(n+z^2) < 1`. Its explicit boundary "
        f"exception freezes `n={boundary['minimum_denominator']}` only as point-"
        "estimator identifiability; it makes no confidence or population-precision claim.",
        "",
        f"The nearest-rank p95 minimum is `n={p95['minimum_denominator']}`: "
        f"rank `{p95['n_min']['rank']}` leaves "
        f"`{p95['n_min']['tail_observations_above_rank']}` observed tail value above it.",
        "",
        "## Coverage and time",
        "",
        "- Scheduled-slot accounting: `100%`",
        "- Unaccounted slot permitted: `NO`",
        f"- Separate numerical coverage floor: `{coverage['decision']}`",
        f"- Calendar/days/weeks minimum: `{temporal['policy']}`",
        "- Stage-C 90-day rule imported: `NO`",
        "- Day/week concentration diagnostics persisted: `YES`",
        "",
        "## Blind stopping and cutoff",
        "",
        "`PROSPECTIVE_STAGE_B_SUFFICIENCY_MONITOR_V1` can consume only slot "
        "identity, time, universe membership and disposition fields. It cannot "
        "consume target numerators, agreement bits, relative-difference values, "
        "aggregate metrics or PASS/FAIL results.",
        "",
        "The cutoff is the earliest decision time at which all eight minima and "
        "all accounting/coverage rules hold. The evaluation corpus is frozen at "
        "that cutoff. A failed epoch cannot continue until it passes.",
        "",
        f"Final classification: `{FINAL_CLASSIFICATION}`",
        "",
    ]
    return "\n".join(lines)


def write_artifacts(output_dir: Path) -> dict[str, Any]:
    definition = sufficiency_governance_definition()
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {DEFINITION_FILENAME: definition, **_child_payloads()}
    for filename, payload in payloads.items():
        (output_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="ascii",
        )
    (output_dir / REPORT_FILENAME).write_text(
        _report_markdown(definition),
        encoding="utf-8",
    )
    return definition


def restore_artifacts(output_dir: Path) -> dict[str, Any]:
    definition = json.loads(
        (output_dir / DEFINITION_FILENAME).read_text(encoding="ascii")
    )
    verify_sufficiency_governance_definition(definition)
    for filename, child_key, builder in _CHILD_ARTIFACTS:
        persisted = json.loads((output_dir / filename).read_text(encoding="ascii"))
        expected = globals()[builder]()
        if persisted != expected:
            raise SufficiencyGovernanceError(f"persisted {filename} does not reproduce")
        if definition["child_definition_sha256"].get(child_key) != expected[
            "definition_sha256"
        ]:
            raise SufficiencyGovernanceError(
                f"top-level definition does not bind {filename}"
            )
    if (output_dir / REPORT_FILENAME).read_text(encoding="utf-8") != _report_markdown(
        definition
    ):
        raise SufficiencyGovernanceError("persisted sufficiency report does not reproduce")
    return definition


def main() -> None:  # pragma: no cover - operational artifact writer
    root = Path(__file__).resolve().parents[2]
    definition = write_artifacts(root / OUTPUT_NAMESPACE)
    print(definition["definition_sha256"])


if __name__ == "__main__":  # pragma: no cover
    main()
