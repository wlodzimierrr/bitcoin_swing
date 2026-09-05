"""Hash-bound validator for the frozen BTC_REFERENCE_COMPOSITE_V3 protocol.

`BTC_REFERENCE_COMPOSITE_V3` is frozen at
`4232e886e7888b85833f778fcba6b2cb3eb5b7d802748aebf3b8adf19c5bf71a` and its
required independent xHigh review passed with non-blocking findings. The
review's own conclusion was that the frozen definition determines the
approve/do-not-approve boundary but leaves three things unbound: the composed
approval function and the precedence between `FAIL` and
`UNDEFINED_INSUFFICIENT_EVIDENCE`, the precedence between the operative V3
architecture and the parent's historical `frozen_*` provenance fields, and the
exact Wilson variant behind the named interval.

This module is the executable interpretation contract that closes all three. It
is **not** a new price-reference protocol: it authors no threshold, moves no
frozen byte, and cannot change a verdict the frozen definition already
determines. It resolves only what the frozen definition left to the validator,
and it hashes its own resolution so a future sealed execution record can bind
both the protocol definition and the interpretation that read it.

    bind_frozen_v3()            recompute the V3 hash and refuse anything else
        |
        v
    validator_definition()      the hash-bound interpretation contract
        |
        v
    validate_v3_candidate()     the single authoritative composition point

Nothing here collects, opens, inspects, queries, summarises or profiles the
sealed 2015-07-20..2019-11-30 sample. `SEALED_EXECUTION` is refused
unconditionally at this revision, and in the only mode that does run, a bundle
whose window reaches into the sealed one is refused by the inherited guard.
`MEDIAN_OHLC_V2` is never constructed and no candidate evidence exists in this
module or its tests beyond synthetic fixtures.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN
from fractions import Fraction
from pathlib import Path
from typing import Any

from btc_predictor.data.ohlcv import require_utc_datetime
from btc_predictor.research.cross_provider_structure_comparison import (
    COMPARISON_CONTRACT_VERSION,
    WEEKLY_STRUCTURE_DETECTOR_VERSION,
)
from btc_predictor.research.price_source_policy import (
    PRICE_SOURCE_POLICY_VERSION,
    REQUIRED_POLICY_PROVIDER_IDS,
)
from btc_predictor.research.reference_composite_v2 import (
    UNTOUCHED_OOS_END,
    UNTOUCHED_OOS_START,
    V2_METHOD_VERSION,
    V2_PROTOCOL_VERSION,
    guard_untouched_validation_sample,
)
from btc_predictor.research.structural_gate_denominator_resolution import (
    DENOMINATOR_SEMANTICS_VERSION,
    PARENT_DEFINITION_SHA256,
)
from btc_predictor.research.structural_threshold_calibration import (
    GATE_VERDICT_FAIL,
    GATE_VERDICT_PASS,
    GATE_VERDICT_UNDEFINED,
    PAIR_ADMISSIBLE,
    PAIR_PURPOSE_CALIBRATION,
    PAIR_PURPOSE_GATE,
    pair_purpose,
    threshold_verdict,
)
from btc_predictor.research.reference_composite_v3_convergence import (
    CERTIFICATION_RULE_ID,
    CONVERGENCE_OUTPUT_NAMESPACE,
    GATE_FAIL,
    GATE_INSUFFICIENT,
    GATE_PASS,
    GUARD_FAILED,
    GUARD_SATISFIED,
    GUARD_UNDEFINED,
    INHERITED_TIER4_HARD_GATES,
    PAIR_CERTIFIED,
    PAIR_INSUFFICIENT_EVIDENCE,
    PAIR_MATERIAL_FAILURE,
    ROLE_DIAGNOSTIC,
    ROLE_HARD,
    ROLE_SOFT,
    SOFT_OUTCOME_OK,
    SOFT_OUTCOME_REVIEW_REQUIRED,
    V3_PROTOCOL_VERSION,
    certify_pair,
    evaluate_hard_structural_gate,
    evaluate_soft_gate,
    evaluate_transfer_guard,
    restore_v3_protocol,
    v3_protocol_definition,
    wilson_upper_bound,
)


# =============================================================================
# identity
# =============================================================================

VALIDATOR_VERSION = "BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_V1"
VALIDATOR_SCHEMA_VERSION = "BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_DEFINITION_V1"
VALIDATOR_RECORD_SCHEMA_VERSION = "BTC_REFERENCE_COMPOSITE_V3_VALIDATION_RECORD_V1"
EVIDENCE_BUNDLE_SCHEMA_VERSION = (
    "BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_EVIDENCE_BUNDLE_V1"
)

VALIDATOR_OUTPUT_NAMESPACE = "research_artifacts/btc019_v3_validator"
VALIDATOR_DEFINITION_FILENAME = "validator_definition.json"
VALIDATOR_REPORT_FILENAME = "V3_VALIDATOR_REPORT.md"

# The exact frozen definition this validator is bound to. Binding is to this
# hash, never to the version name and never to the parent.
BOUND_PROTOCOL_VERSION = V3_PROTOCOL_VERSION
BOUND_PROTOCOL_DEFINITION_SHA256 = (
    "4232e886e7888b85833f778fcba6b2cb3eb5b7d802748aebf3b8adf19c5bf71a"
)
PARENT_PROTOCOL_VERSION = V2_PROTOCOL_VERSION
PARENT_PROTOCOL_DEFINITION_SHA256 = (
    "bc312f3e6a6035e00a3cd80103aacdee7b5a02ae69732b7bbca5785a3dd6106a"
)

V3_FREEZE_IMPLEMENTATION_COMMIT = "b60ecc7f36840b429f27a8742b7245d417cf52db"
V3_REVIEW_COMMIT = "e2df3ce036c0e7045361c871f8d303b51533f18d"
V3_REVIEW_RESULT = "PASS_WITH_NON_BLOCKING_FINDINGS"

MATERIAL_CHANGE_REQUIRES = (
    "A change to any verdict-affecting field of this contract requires "
    "BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_V2 or later and a new validator "
    "definition hash. A change to a verdict-affecting semantic of the bound "
    "protocol requires BTC_REFERENCE_COMPOSITE_V4 or later; this validator "
    "may never make one."
)


class ValidatorError(ValueError):
    """Base class for every refusal this validator can raise."""


class ValidatorBindingError(ValidatorError):
    """Raised when the bound frozen definition does not reproduce exactly."""


class ValidatorInputError(ValidatorError):
    """Raised when an evidence bundle is malformed, ambiguous or inconsistent."""


class SealedExecutionNotAuthorizedError(ValidatorError):
    """Raised whenever sealed execution is requested. It is never authorized here."""


# Statistics and rendering resolve in explicit contexts, never the caller's.
_STAT_CONTEXT = Context(prec=34, rounding=ROUND_HALF_EVEN)
_REPORT_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)


def _json_default(value: Any) -> Any:
    """Render the only non-JSON scalars a bundle may carry, deterministically.

    An exact decimal renders as its own literal text and an instant as its
    ISO-8601 form, so a digest never depends on locale, platform float
    formatting or the ambient Decimal context. Anything else refuses rather
    than acquiring an accidental representation.
    """

    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise ValidatorInputError(
        f"a {type(value).__name__} value cannot appear in canonical evidence"
    )


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=_json_default,
    )


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("ascii")).hexdigest()


# =============================================================================
# 1. binding: recompute the frozen V3 hash before anything else runs
# =============================================================================

BINDING_RULE_ID = "REFUSE_TO_RUN_UNLESS_V3_HASH_REPRODUCES_EXACTLY_V1"
BINDING_RULE = (
    "Before any validation logic runs, the frozen BTC_REFERENCE_COMPOSITE_V3 "
    "definition is rebuilt from the repository and restored from its persisted "
    "artifact, and both must digest to "
    f"{BOUND_PROTOCOL_DEFINITION_SHA256} exactly. The restored artifact must "
    f"also name {PARENT_PROTOCOL_DEFINITION_SHA256} as its parent. Anything "
    "else is REFUSE_TO_RUN: there is no fallback by version name, no fallback "
    "to the parent, and no 'latest V3'."
)
BINDING_REFUSAL = "REFUSE_TO_RUN"


def bind_frozen_v3(repository_root: Path) -> dict[str, Any]:
    """Return the frozen V3 definition, or refuse to run.

    Both the module rebuild and the persisted artifact must reproduce the bound
    hash, and they must be byte-equal as canonical JSON, so neither a module
    edit nor an artifact edit can move the definition in silence.
    """

    rebuilt = v3_protocol_definition(repository_root)
    if rebuilt.get("definition_sha256") != BOUND_PROTOCOL_DEFINITION_SHA256:
        raise ValidatorBindingError(
            f"{BINDING_REFUSAL}: the rebuilt BTC_REFERENCE_COMPOSITE_V3 "
            f"definition digests to {rebuilt.get('definition_sha256')!r}, not "
            f"to the bound {BOUND_PROTOCOL_DEFINITION_SHA256}"
        )
    _refuse_a_definition_claiming_sealed_access(rebuilt)
    restored = restore_v3_protocol(repository_root / CONVERGENCE_OUTPUT_NAMESPACE)
    if restored.get("definition_sha256") != BOUND_PROTOCOL_DEFINITION_SHA256:
        raise ValidatorBindingError(
            f"{BINDING_REFUSAL}: the persisted BTC_REFERENCE_COMPOSITE_V3 "
            "artifact does not carry the bound definition hash"
        )
    if _canonical_json(restored) != _canonical_json(rebuilt):
        raise ValidatorBindingError(
            f"{BINDING_REFUSAL}: the persisted BTC_REFERENCE_COMPOSITE_V3 "
            "artifact does not reproduce from the repository"
        )
    if restored.get("reference_policy_version") != BOUND_PROTOCOL_VERSION:
        raise ValidatorBindingError(
            f"{BINDING_REFUSAL}: the bound definition is not "
            f"{BOUND_PROTOCOL_VERSION}"
        )
    if restored.get("parent_definition_sha256") != PARENT_PROTOCOL_DEFINITION_SHA256:
        raise ValidatorBindingError(
            f"{BINDING_REFUSAL}: the bound definition names a different parent hash"
        )
    if restored.get("parent_definition_sha256") == BOUND_PROTOCOL_DEFINITION_SHA256:
        raise ValidatorBindingError(
            f"{BINDING_REFUSAL}: this validator binds the V3 hash, not the parent's"
        )
    _refuse_a_definition_claiming_sealed_access(restored)
    return restored


def _refuse_a_definition_claiming_sealed_access(definition: Mapping[str, Any]) -> None:
    """Refuse a definition that says the sealed sample has been reached.

    Checked on the rebuilt definition as well as the restored one, so the
    refusal stands on its own rather than only through the reproduction
    comparison beside it.
    """

    sealed = definition.get("sample_governance", {}).get("sealed_sample", {})
    if sealed.get("collected") or sealed.get("opened") or sealed.get("inspected"):
        raise ValidatorBindingError(
            f"{BINDING_REFUSAL}: the bound definition claims sealed-sample access"
        )


# =============================================================================
# 2. operative-field precedence (closes review finding P2-3)
# =============================================================================

OPERATIVE_FIELD_PRECEDENCE_ID = (
    "OPERATIVE_V3_FIELDS_OVERRIDE_HISTORICAL_V2_PROVENANCE_V1"
)

# The frozen artifact's operative authority. Everything a verdict depends on is
# read from exactly these blocks.
OPERATIVE_V3_AUTHORITY_FIELDS = (
    "comparability_policy",
    "derived_level_protection",
    "diagnostic_semantics",
    "gate_architecture",
    "gate_pair_universe",
    "inherited_approval_gates",
    "materiality",
    "new_hard_requirements",
    "not_comparable_semantics",
    "soft_gate_semantics",
    "transfer_guard",
)

# Historical parent provenance carried inside `metric_definitions`. These
# describe what BTC_REFERENCE_COMPOSITE_V2 froze; they are never read for a V3
# verdict and can never regain operative authority.
HISTORICAL_PROVENANCE_ONLY_FIELDS = (
    "frozen_direction",
    "frozen_hard",
    "frozen_threshold",
    "frozen_validation_stage",
)

OPERATIVE_FIELD_PRECEDENCE_RULE = (
    "Where the frozen V3 architecture supersedes a parent gate, the operative "
    "authority is the V3 block and never the historical record beside it. "
    "`metric_definitions[*].frozen_threshold`, `frozen_hard`, "
    "`frozen_direction` and `frozen_validation_stage` are "
    "BTC_REFERENCE_COMPOSITE_V2 provenance preserved for audit; no validator "
    "path reads them. `structural_state_disagreement_rate` therefore carries "
    "the operative materiality limit of 0.20 and not the historical 0.05, and "
    "`within_1_week`, `within_2_week`, `breakout` and `reclaim` carry the "
    "operative role DIAGNOSTIC_ONLY and not the historical `frozen_hard: "
    "true`. A diagnostic has no threshold, no pass and no fail, and is not a "
    "parameter of the approval composition at all."
)

OPERATIVE_FIELD_PRECEDENCE_EXAMPLES = (
    {
        "field": "structural_state_disagreement_rate",
        "historical_v2_provenance": "frozen_threshold 0.05, frozen_hard true",
        "operative_v3_authority": "materiality.absolute_limit 0.20, "
        "gate_architecture.roles HARD_APPROVAL_GATE",
        "operative_value_used": "0.20",
    },
    {
        "field": "exact_timestamp_swing_disagreement_rate",
        "historical_v2_provenance": "frozen_threshold 0.15, frozen_hard false",
        "operative_v3_authority": "gate_architecture.roles SOFT_WARNING_GATE, "
        "soft_gate_semantics",
        "operative_value_used": "0.20 as a warning trigger that cannot reject",
    },
    {
        "field": "within_1_week_swing_disagreement_rate",
        "historical_v2_provenance": "frozen_threshold 0.05, frozen_hard true",
        "operative_v3_authority": "gate_architecture.roles DIAGNOSTIC_ONLY",
        "operative_value_used": "none; a diagnostic carries no threshold",
    },
    {
        "field": "within_2_week_swing_disagreement_rate",
        "historical_v2_provenance": "frozen_threshold 0.02, frozen_hard true",
        "operative_v3_authority": "gate_architecture.roles DIAGNOSTIC_ONLY",
        "operative_value_used": "none; a diagnostic carries no threshold",
    },
    {
        "field": "breakout_disagreement_rate",
        "historical_v2_provenance": "frozen_threshold 0.05, frozen_hard true",
        "operative_v3_authority": "gate_architecture.roles DIAGNOSTIC_ONLY",
        "operative_value_used": "none; a diagnostic carries no threshold",
    },
    {
        "field": "reclaim_disagreement_rate",
        "historical_v2_provenance": "frozen_threshold 0.05, frozen_hard true",
        "operative_v3_authority": "gate_architecture.roles DIAGNOSTIC_ONLY",
        "operative_value_used": "none; a diagnostic carries no threshold",
    },
)

STRUCTURAL_METRIC = "structural_state_disagreement_rate"
EXACT_TIMESTAMP_METRIC = "exact_timestamp_swing_disagreement_rate"
DIAGNOSTIC_METRICS = (
    "breakout_disagreement_rate",
    "reclaim_disagreement_rate",
    "within_1_week_swing_disagreement_rate",
    "within_2_week_swing_disagreement_rate",
)


def operative_metric_role(protocol: Mapping[str, Any], metric: str) -> str:
    """Return a metric's operative V3 role, never its historical `frozen_hard`."""

    roles = protocol["gate_architecture"]["roles"]
    if metric not in roles:
        raise ValidatorBindingError(f"{metric!r} carries no operative V3 role")
    return roles[metric]


def operative_structural_limit(protocol: Mapping[str, Any]) -> Decimal:
    """Return the operative absolute materiality limit, never a frozen_threshold."""

    materiality = protocol["materiality"]
    if materiality["applies_to"] != STRUCTURAL_METRIC:
        raise ValidatorBindingError("the materiality limit applies to another metric")
    if materiality["direction"] != "maximum":
        raise ValidatorBindingError("the materiality limit is not a maximum")
    return Decimal(materiality["absolute_limit"])


def operative_comparability_floor(protocol: Mapping[str, Any]) -> Decimal:
    """Return the operative hard structural comparability floor."""

    policy = protocol["comparability_policy"]
    if not policy["hard"]:
        raise ValidatorBindingError("the comparability floor is not hard")
    return Decimal(policy["floor"])


def operative_normal_quantile(protocol: Mapping[str, Any]) -> Decimal:
    """Return the hash-bound normal quantile, never a freshly looked-up one."""

    rule = protocol["gate_architecture"]["certification_rule"]
    if rule["rule_id"] != CERTIFICATION_RULE_ID:
        raise ValidatorBindingError("the certification rule id changed")
    return Decimal(rule["normal_quantile"])


def operative_confidence_level_percent(protocol: Mapping[str, Any]) -> str:
    return protocol["gate_architecture"]["certification_rule"]["confidence_level_percent"]


# =============================================================================
# 3. the Wilson bound, written out (closes review finding P3-5)
# =============================================================================

WILSON_FORMULA_ID = "WILSON_SCORE_UPPER_BOUND_UNCORRECTED_V1"
WILSON_CONTINUITY_CORRECTION_APPLIED = False
WILSON_FORMULA_EXPRESSION = (
    "U = ( p_hat + z^2/(2n) + z * sqrt( p_hat*(1 - p_hat)/n + z^2/(4*n^2) ) ) "
    "/ ( 1 + z^2/n ), with p_hat = k/n, k the disagreement count, n the "
    "comparable event count and z the hash-bound normal quantile. This is the "
    "uncorrected two-sided Wilson score interval's upper limit. No continuity "
    "correction is applied, no platform statistics library is consulted, the "
    "quantile is never rounded or re-derived, and the result is clamped at 1."
)
WILSON_FORMULA_REFUSALS = (
    "the continuity-corrected (Newcombe) Wilson upper limit, which refuses the "
    "frozen boundary pairs 0/16, 1/25, 2/33 and 3/40 and is therefore a "
    "different rule, not a stricter reading of the same one",
    "any scipy, statsmodels or other library default whose variant is not "
    "verified formula-for-formula against this expression",
    "a freshly looked-up normal quantile in place of the hash-bound one",
    "binary floating point anywhere in the comparison chain",
)
WILSON_ARITHMETIC = (
    "Decimal in an explicit Context(prec=34, rounding=ROUND_HALF_EVEN), never "
    "the caller's ambient context and never a binary float. The point-rate "
    "comparison is additionally cross-checked in exact rational arithmetic, "
    "and a disagreement between the two refuses rather than resolves."
)
WILSON_ZERO_DENOMINATOR = (
    "n = 0 has no interval and no rate. The rate is null, never 0.0, and the "
    "pair is PAIR_INSUFFICIENT_EVIDENCE with NO_COMPARABLE_EVENTS."
)

# Recomputed from the formula above; pinned here so a later edit to the bound
# cannot move a boundary without this contract's hash saying so.
WILSON_BOUNDARY_VECTORS = (
    {"numerator": 0, "denominator": 15, "outcome": PAIR_INSUFFICIENT_EVIDENCE},
    {"numerator": 0, "denominator": 16, "outcome": PAIR_CERTIFIED},
    {"numerator": 1, "denominator": 24, "outcome": PAIR_INSUFFICIENT_EVIDENCE},
    {"numerator": 1, "denominator": 25, "outcome": PAIR_CERTIFIED},
    {"numerator": 2, "denominator": 32, "outcome": PAIR_INSUFFICIENT_EVIDENCE},
    {"numerator": 2, "denominator": 33, "outcome": PAIR_CERTIFIED},
    {"numerator": 3, "denominator": 39, "outcome": PAIR_INSUFFICIENT_EVIDENCE},
    {"numerator": 3, "denominator": 40, "outcome": PAIR_CERTIFIED},
)


def structural_upper_bound(
    numerator: int,
    denominator: int,
    *,
    quantile: Decimal,
) -> Decimal | None:
    """Return the uncorrected Wilson score upper limit, or None on no evidence.

    Delegated to the frozen protocol's own owner so the validator cannot drift
    from the definition it is bound to. `WILSON_FORMULA_EXPRESSION` states the
    formula the owner implements, and a regression recomputes both against an
    independent 60-digit evaluation.
    """

    return wilson_upper_bound(numerator, denominator, quantile=quantile)


def _exact_rate_exceeds(numerator: int, denominator: int, limit: Decimal) -> bool:
    """Return whether k/n exceeds the limit, in exact rational arithmetic."""

    return Fraction(numerator, denominator) > Fraction(limit)


WILSON_BOUNDARY_ENFORCEMENT = (
    "The pinned boundary vectors are not an assertion about the bound, they are "
    "checked against it. Before any contract is built or any candidate is "
    "composed, each vector is re-evaluated through the certification rule on "
    "the hash-bound quantile and limit, and a disagreement is REFUSE_TO_RUN. "
    "Without this the vectors would record what the bound was expected to do "
    "while the bound itself sat outside both hashes, so an edited "
    "implementation could move a certifying boundary with neither hash "
    "changing. The continuity-corrected reading refuses 0/16, 1/25, 2/33 and "
    "3/40, so substituting it is caught here rather than only by test."
)


def _pair_outcome_at(
    numerator: int, denominator: int, *, limit: Decimal, quantile: Decimal
) -> str:
    """Classify one (k, n) through the very function the gate decides with.

    Deliberately routed through `certify_pair` rather than through the bound
    alone, so the check exercises the whole certification path a required pair
    takes and not a parallel reimplementation of it.
    """

    probe = {
        "comparison_id": "boundary_probe",
        "numerator": numerator,
        "denominator": denominator,
        "state": PAIR_ADMISSIBLE,
        "structural_comparability_rate": str(limit.max(Decimal(1))),
    }
    return certify_pair(
        probe,
        comparison_id="boundary_probe",
        limit=limit,
        quantile=quantile,
        comparability_floor=Decimal(0),
    ).outcome


def verify_wilson_boundary_vectors(*, limit: Decimal, quantile: Decimal) -> None:
    """Refuse if the bound no longer reproduces its own hash-bound boundaries."""

    for row in WILSON_BOUNDARY_VECTORS:
        actual = _pair_outcome_at(
            row["numerator"], row["denominator"], limit=limit, quantile=quantile
        )
        if actual != row["outcome"]:
            raise ValidatorBindingError(
                f"{BINDING_REFUSAL}: the certification rule makes "
                f"{row['numerator']}/{row['denominator']} {actual}, not the "
                f"hash-bound {row['outcome']}"
            )


# =============================================================================
# 4. the required pair universe
# =============================================================================

PAIR_UNIVERSE_ID = "CANDIDATE_VERSUS_INDEPENDENT_RAW_PROVIDER_PAIRS_V1"
ROLE_APPROVAL_GATE_PAIR = "APPROVAL_GATE_PAIR"
ROLE_SOURCE_DISPERSION_GUARD_PAIR = "SOURCE_DISPERSION_GUARD_PAIR"

# `pair_purpose` is the repository's authoritative role classifier; V3 renames
# the provider-versus-provider role because in V3 those pairs are the transfer
# guard's whole input rather than calibration evidence.
_PURPOSE_TO_V3_ROLE = {
    PAIR_PURPOSE_GATE: ROLE_APPROVAL_GATE_PAIR,
    PAIR_PURPOSE_CALIBRATION: ROLE_SOURCE_DISPERSION_GUARD_PAIR,
}

PAIR_VIOLATION_DUPLICATE = "DUPLICATE_PAIR_MEASUREMENT"
PAIR_VIOLATION_UNEXPECTED = "PAIR_NOT_IN_REQUIRED_UNIVERSE"
PAIR_VIOLATION_ROLE = "PAIR_ROLE_MISMATCH"
PAIR_VIOLATION_IDENTITY = "PROVIDER_IDENTITY_MISMATCH"
PAIR_VIOLATION_METRIC = "PAIR_MEASURES_ANOTHER_METRIC"
PAIR_VIOLATION_CANDIDATE_IN_GUARD = "CANDIDATE_PRESENT_IN_TRANSFER_GUARD_PAIR"
PAIR_VIOLATION_CANDIDATE_ABSENT = "CANDIDATE_ABSENT_FROM_APPROVAL_GATE_PAIR"
PAIR_UNIVERSE_VIOLATIONS = (
    PAIR_VIOLATION_CANDIDATE_ABSENT,
    PAIR_VIOLATION_CANDIDATE_IN_GUARD,
    PAIR_VIOLATION_DUPLICATE,
    PAIR_VIOLATION_IDENTITY,
    PAIR_VIOLATION_METRIC,
    PAIR_VIOLATION_ROLE,
    PAIR_VIOLATION_UNEXPECTED,
)
PAIR_UNIVERSE_VIOLATION_DISPOSITION = (
    "REFUSE_TO_RUN. A duplicated, unexpected, wrongly-rolled or "
    "wrongly-identified pair makes the bundle ambiguous about which "
    "measurement governs, and an ambiguous bundle is not evidence about the "
    "candidate at all. A required pair that is simply absent is different: it "
    "is recorded and makes its requirement UNDEFINED_INSUFFICIENT_EVIDENCE."
)


def canonical_pair_id(series_pair: Sequence[str]) -> str:
    """Return the order-independent canonical id of one unordered pair."""

    pair = tuple(sorted(series_pair))
    if len(pair) != 2 or pair[0] == pair[1]:
        raise ValidatorInputError("a pair requires two distinct series ids")
    return "_vs_".join(pair)


def required_gate_pair_ids(protocol: Mapping[str, Any]) -> tuple[str, ...]:
    """Return the exact required candidate-versus-provider pair ids."""

    universe = protocol["gate_pair_universe"]
    if universe["universe_id"] != PAIR_UNIVERSE_ID:
        raise ValidatorBindingError("the gate pair universe id changed")
    pairs = tuple(sorted(universe["gate_pairs"]))
    if len(pairs) != universe["required_gate_pair_count"]:
        raise ValidatorBindingError(
            "the declared gate pairs do not match the required pair count"
        )
    if len(set(pairs)) != len(pairs):
        raise ValidatorBindingError("the declared gate pairs are not distinct")
    return pairs


def required_transfer_guard_pair_ids(protocol: Mapping[str, Any]) -> tuple[str, ...]:
    """Return the exact required provider-versus-provider guard pair ids."""

    pairs = tuple(sorted(protocol["gate_pair_universe"]["calibration_pairs"]))
    if len(set(pairs)) != len(pairs):
        raise ValidatorBindingError("the declared guard pairs are not distinct")
    return pairs


def _classify_pair(series_pair: Sequence[str]) -> str:
    """Return one pair's V3 role from its series identities alone."""

    try:
        purpose = pair_purpose(series_pair)
    except ValueError as error:  # undeclared series, or a malformed pair
        raise ValidatorInputError(f"{PAIR_VIOLATION_IDENTITY}: {error}") from error
    role = _PURPOSE_TO_V3_ROLE.get(purpose)
    if role is None:
        raise ValidatorInputError(
            f"{PAIR_VIOLATION_ROLE}: {canonical_pair_id(series_pair)} belongs to "
            "neither required universe"
        )
    return role


# =============================================================================
# 5. the evidence bundle schema
# =============================================================================

EXECUTION_MODE_DRY_RUN = "DRY_RUN_SYNTHETIC"
EXECUTION_MODE_SEALED = "SEALED_EXECUTION"
EXECUTION_MODES = (EXECUTION_MODE_DRY_RUN, EXECUTION_MODE_SEALED)
SEALED_EXECUTION_AUTHORIZED = False
SEALED_EXECUTION_AUTHORIZATION_RULE = (
    "SEALED_EXECUTION is refused unconditionally at this validator revision. "
    "It becomes reachable only after this validator has passed its own "
    "independent xHigh review and the one-time sealed opening is separately "
    "authorised. DRY_RUN_SYNTHETIC is the only mode that runs, and in it the "
    "inherited guard_untouched_validation_sample refuses any bundle whose "
    "window overlaps 2015-07-20T21:00:00+00:00..2019-11-30T23:00:00+00:00."
)

BUNDLE_REQUIRED_KEYS = (
    "derived_level_review",
    "diagnostics",
    "gate_pair_measurements",
    "identities",
    "inherited_gate_measurements",
    "not_comparable_accounting",
    "provenance",
    "sample",
    "schema_version",
    "soft_gate_pair_measurements",
    "transfer_guard_pair_measurements",
)

SAMPLE_REQUIRED_KEYS = ("end", "sample_id", "start")

IDENTITY_REQUIRED_KEYS = (
    "candidate_method_version",
    "candidate_series_id",
    "comparison_contract_version",
    "denominator_semantics_version",
    "price_source_policy_version",
    "provider_ids",
    "source_detector_version",
)

# The bound identities every measurement must have been produced under. A
# bundle that names a different contract, detector or policy is measuring
# something else and is refused rather than silently accepted.
BOUND_MEASUREMENT_IDENTITIES = {
    "candidate_method_version": V2_METHOD_VERSION,
    "candidate_series_id": V2_METHOD_VERSION,
    "comparison_contract_version": COMPARISON_CONTRACT_VERSION,
    "denominator_semantics_version": DENOMINATOR_SEMANTICS_VERSION,
    "price_source_policy_version": PRICE_SOURCE_POLICY_VERSION,
    "provider_ids": tuple(sorted(REQUIRED_POLICY_PROVIDER_IDS)),
    "source_detector_version": WEEKLY_STRUCTURE_DETECTOR_VERSION,
}

PROVENANCE_REQUIRED_KEYS = (
    "evidence_builder_version",
    "measurement_record_digest",
    "sample_manifest_digest",
)

# Exactly the fields `measure_pair` plus `PairAdmissibility.as_record` emit,
# split into what a certification may not proceed without and what travels with
# it. Anything else in a pair record is refused.
PAIR_REQUIRED_KEYS = (
    "all_detected_event_count",
    "candidate_event_count",
    "comparable_event_count",
    "comparison_id",
    "denominator",
    "metric",
    "not_comparable_event_count",
    "not_comparable_rate",
    "not_comparable_reason_counts",
    "numerator",
    "series_pair",
    "state",
    "structural_comparability_rate",
)
PAIR_OPTIONAL_KEYS = (
    "matched_pair_count",
    "measurement_state",
    "pair_purpose",
    "rate",
    "reason_codes",
    "uncertainty",
)
# The only pair fields the frozen rule defines as nullable. A null in either
# means "no detected events at all", which is insufficient evidence -- never a
# satisfied requirement.
PAIR_NULLABLE_KEYS = ("not_comparable_rate", "structural_comparability_rate")

DIAGNOSTIC_REQUIRED_FIELDS = (
    "calendar_displacement_weeks",
    "comparable_event_count",
    "count",
    "matched_pair_count",
    "not_comparable_event_count",
    "not_comparable_reason_counts",
    "rate",
    "reason_codes",
)

DERIVED_LEVEL_REVIEW_REQUIRED_KEYS = (
    "observed_disagreements",
    "reviews",
    "unreviewed_derived_level_disagreement_count",
)
DERIVED_LEVEL_EVENT_REQUIRED_KEYS = ("comparison_id", "event_id", "family", "week")
DERIVED_LEVEL_REVIEW_RECORD_REQUIRED_KEYS = (
    "comparison_id",
    "economic_assessment",
    "event_id",
    "family",
    "reviewed_at",
    "reviewer",
    "week",
)
DERIVED_LEVEL_FAMILIES = ("breakout", "reclaim")

NOT_COMPARABLE_ACCOUNTING_REQUIRED_KEYS = ("unrecorded_not_comparable_event_count",)


def _require_mapping(value: Any, what: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValidatorInputError(f"{what} must be a mapping")
    return value


def _require_exact_keys(
    payload: Mapping[str, Any],
    required: Sequence[str],
    optional: Sequence[str],
    what: str,
) -> None:
    keys = set(payload)
    missing = sorted(set(required) - keys)
    if missing:
        raise ValidatorInputError(f"{what} omits required fields {missing}")
    unknown = sorted(keys - set(required) - set(optional))
    if unknown:
        raise ValidatorInputError(f"{what} carries unknown fields {unknown}")


def _require_count(value: Any, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidatorInputError(f"{what} must be an integer count")
    if value < 0:
        raise ValidatorInputError(f"{what} cannot be negative")
    return value


def _decimal(value: Any, what: str) -> Decimal:
    """Parse an exact decimal, refusing binary floats outright."""

    if isinstance(value, bool) or isinstance(value, float):
        raise ValidatorInputError(f"{what} must not be a binary float")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        try:
            return Decimal(value)
        except InvalidOperation as error:
            raise ValidatorInputError(f"{what} is not an exact decimal") from error
    raise ValidatorInputError(f"{what} is not an exact decimal")


DECLARED_VALUE_VERIFICATION_ID = "DECLARED_PAIR_VALUES_VERIFIED_AGAINST_OWN_COUNTS_V1"
DECLARED_VALUE_VERIFICATION = (
    "A pair's denominator and its comparability rates are not believed, they "
    "are verified against the counts the same record carries. The bound "
    f"{DENOMINATOR_SEMANTICS_VERSION} defines structural_comparability_rate as "
    "comparable_event_count / all_detected_event_count, not_comparable_rate as "
    "its complement, and both as null exactly when nothing was detected; the "
    "frozen metric definition makes the structural denominator the comparable "
    "detected event union. A record whose declared values contradict its own "
    "counts is ambiguous about which reading governs, so it is refused rather "
    "than resolved -- the same treatment a duplicated or wrongly-identified "
    "pair receives. The rate is checked the way the point rate already is: the "
    "declared reading and the exact-rational reading must agree at the hard "
    "comparability floor, so no rounding can move a pair across it and no "
    "declared rate can certify a pair its own counts place below it."
)


def _verify_declared_pair_values(
    record: Mapping[str, Any], canonical: str, floor: Decimal
) -> None:
    """Refuse a pair whose declared values contradict its own counts."""

    comparable = record["comparable_event_count"]
    detected = record["all_detected_event_count"]
    if record["denominator"] != comparable:
        raise ValidatorInputError(
            f"{canonical} declares a denominator of {record['denominator']} but "
            f"carries {comparable} comparable events"
        )
    for field in PAIR_NULLABLE_KEYS:
        declared = record[field]
        if detected == 0 and declared is not None:
            raise ValidatorInputError(
                f"{canonical} detected no events, so {field} must be null"
            )
        if detected != 0 and declared is None:
            raise ValidatorInputError(
                f"{canonical} detected {detected} events, so {field} cannot be null"
            )
    if detected == 0:
        return
    declared_rate = _decimal(
        record["structural_comparability_rate"],
        f"{canonical} structural_comparability_rate",
    )
    if (declared_rate >= floor) != (Fraction(comparable, detected) >= Fraction(floor)):
        raise ValidatorInputError(
            f"{canonical} declares a structural comparability rate of "
            f"{declared_rate} that disagrees with its own "
            f"{comparable}/{detected} comparable events at the floor"
        )


def _validate_pair_record(row: Any, metric: str, floor: Decimal) -> dict[str, Any]:
    record = dict(_require_mapping(row, "a pair measurement"))
    _require_exact_keys(
        record, PAIR_REQUIRED_KEYS, PAIR_OPTIONAL_KEYS, "a pair measurement"
    )
    series_pair = record["series_pair"]
    if not isinstance(series_pair, (list, tuple)) or len(series_pair) != 2:
        raise ValidatorInputError("series_pair must name exactly two series")
    if any(not isinstance(item, str) for item in series_pair):
        raise ValidatorInputError("series_pair must name two series ids")
    canonical = canonical_pair_id(series_pair)
    if record["comparison_id"] != canonical:
        raise ValidatorInputError(
            f"{PAIR_VIOLATION_IDENTITY}: comparison_id "
            f"{record['comparison_id']!r} is not the canonical id {canonical!r} "
            "of its own series pair"
        )
    if record["metric"] != metric:
        raise ValidatorInputError(
            f"{PAIR_VIOLATION_METRIC}: {canonical} measures {record['metric']!r}, "
            f"not {metric!r}"
        )
    _require_count(record["numerator"], f"{canonical} numerator")
    _require_count(record["denominator"], f"{canonical} denominator")
    if record["numerator"] > record["denominator"]:
        raise ValidatorInputError(f"{canonical} numerator exceeds its denominator")
    for field in (
        "all_detected_event_count",
        "candidate_event_count",
        "comparable_event_count",
        "not_comparable_event_count",
    ):
        _require_count(record[field], f"{canonical} {field}")
    if (
        record["comparable_event_count"] + record["not_comparable_event_count"]
        != record["all_detected_event_count"]
    ):
        raise ValidatorInputError(
            f"{canonical} comparability counts do not sum to its detected total"
        )
    if not isinstance(record["not_comparable_reason_counts"], Mapping):
        raise ValidatorInputError(
            f"{canonical} not_comparable_reason_counts must be a mapping"
        )
    for field in PAIR_NULLABLE_KEYS:
        if record[field] is not None:
            _decimal(record[field], f"{canonical} {field}")
    _verify_declared_pair_values(record, canonical, floor)
    declared_purpose = record.get("pair_purpose")
    if declared_purpose is not None:
        try:
            actual = pair_purpose(series_pair)
        except ValueError as error:
            raise ValidatorInputError(f"{PAIR_VIOLATION_IDENTITY}: {error}") from error
        if declared_purpose != actual:
            raise ValidatorInputError(
                f"{PAIR_VIOLATION_ROLE}: {canonical} declares {declared_purpose!r} "
                f"but its identities make it {actual!r}"
            )
    return record


def _validate_pair_universe(
    rows: Any,
    *,
    required_ids: Sequence[str],
    expected_role: str,
    metric: str,
    floor: Decimal,
    what: str,
) -> dict[str, dict[str, Any]]:
    """Return required-id -> measurement, refusing every structural violation.

    Ordering never matters and identity always does: every record is keyed by
    the canonical id built from its own sorted series pair, so a reordered list
    is the same evidence and a pair whose provider labels were swapped onto
    other counts is not.
    """

    if not isinstance(rows, (list, tuple)):
        raise ValidatorInputError(f"{what} must be a list of pair measurements")
    seen: dict[str, dict[str, Any]] = {}
    for row in rows:
        record = _validate_pair_record(row, metric, floor)
        comparison_id = record["comparison_id"]
        role = _classify_pair(record["series_pair"])
        if role != expected_role:
            if expected_role == ROLE_SOURCE_DISPERSION_GUARD_PAIR:
                raise ValidatorInputError(
                    f"{PAIR_VIOLATION_CANDIDATE_IN_GUARD}: {comparison_id} is not a "
                    "provider-versus-provider pair"
                )
            raise ValidatorInputError(
                f"{PAIR_VIOLATION_CANDIDATE_ABSENT}: {comparison_id} is not a "
                "candidate-versus-provider pair"
            )
        if comparison_id in seen:
            raise ValidatorInputError(
                f"{PAIR_VIOLATION_DUPLICATE}: {what} carries {comparison_id} twice"
            )
        if comparison_id not in required_ids:
            raise ValidatorInputError(
                f"{PAIR_VIOLATION_UNEXPECTED}: {comparison_id} is not one of the "
                f"required {sorted(required_ids)}"
            )
        seen[comparison_id] = record
    return seen


def _validate_diagnostics(payload: Any) -> dict[str, Any]:
    """Record diagnostic completeness without ever letting it reach a verdict."""

    families: dict[str, Any] = {}
    complete = True
    if not isinstance(payload, Mapping):
        return {
            "complete": False,
            "metrics": {},
            "reason_codes": ["DIAGNOSTIC_BLOCK_MALFORMED"],
        }
    reasons: list[str] = []
    for metric in DIAGNOSTIC_METRICS:
        rows = payload.get(metric)
        recorded: list[dict[str, Any]] = []
        if not isinstance(rows, (list, tuple)):
            complete = False
            reasons.append(f"DIAGNOSTIC_ABSENT:{metric}")
            families[metric] = recorded
            continue
        for row in rows:
            if not isinstance(row, Mapping):
                complete = False
                reasons.append(f"DIAGNOSTIC_RECORD_MALFORMED:{metric}")
                continue
            missing = sorted(set(DIAGNOSTIC_REQUIRED_FIELDS) - set(row))
            if missing:
                complete = False
                reasons.append(f"DIAGNOSTIC_RECORD_INCOMPLETE:{metric}")
            recorded.append(
                {key: row[key] for key in sorted(row) if key != "reason_codes"}
                | {"reason_codes": sorted(row.get("reason_codes", []))}
            )
        families[metric] = sorted(
            recorded, key=lambda item: str(item.get("comparison_id", ""))
        )
    unknown = sorted(set(payload) - set(DIAGNOSTIC_METRICS))
    if unknown:
        complete = False
        reasons.append("DIAGNOSTIC_UNKNOWN_METRIC")
    return {
        "complete": complete,
        "metrics": families,
        "reason_codes": sorted(set(reasons)),
    }


def _canonical_pair_row(row: Any) -> Any:
    """Canonicalise one pair row so a re-ordering cannot move a digest.

    A pair is unordered, so its `series_pair` is sorted; its reason codes are a
    set written as a list, so they are sorted too. Both carry the same meaning
    in any order, and `_validate_pair_record` already pins the identity of the
    pair to the canonical id built from those same two series ids, so nothing
    here can make swapped provider labels look order-equivalent.
    """

    if not isinstance(row, Mapping):
        return row
    record = dict(row)
    series_pair = record.get("series_pair")
    if isinstance(series_pair, (list, tuple)) and all(
        isinstance(item, str) for item in series_pair
    ):
        record["series_pair"] = sorted(series_pair)
    reason_codes = record.get("reason_codes")
    if isinstance(reason_codes, (list, tuple)) and all(
        isinstance(item, str) for item in reason_codes
    ):
        record["reason_codes"] = sorted(reason_codes)
    return record


def canonical_evidence_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Return the bundle in canonical order, so pair order cannot move a digest."""

    canonical = dict(bundle)
    for key in (
        "gate_pair_measurements",
        "soft_gate_pair_measurements",
        "transfer_guard_pair_measurements",
    ):
        rows = canonical.get(key)
        if isinstance(rows, (list, tuple)):
            canonical[key] = sorted(
                (_canonical_pair_row(row) for row in rows),
                key=lambda item: str(item.get("comparison_id", ""))
                if isinstance(item, Mapping)
                else str(item),
            )
    diagnostics = canonical.get("diagnostics")
    if isinstance(diagnostics, Mapping):
        canonical["diagnostics"] = {
            metric: (
                sorted(
                    (dict(row) if isinstance(row, Mapping) else row for row in rows),
                    key=lambda item: str(item.get("comparison_id", ""))
                    if isinstance(item, Mapping)
                    else str(item),
                )
                if isinstance(rows, (list, tuple))
                else rows
            )
            for metric, rows in sorted(diagnostics.items())
        }
    review = canonical.get("derived_level_review")
    if isinstance(review, Mapping):
        ordered = dict(review)
        for key in ("observed_disagreements", "reviews"):
            rows = ordered.get(key)
            if isinstance(rows, (list, tuple)):
                ordered[key] = sorted(
                    (dict(row) if isinstance(row, Mapping) else row for row in rows),
                    key=lambda item: (
                        str(item.get("comparison_id", "")),
                        str(item.get("event_id", "")),
                    )
                    if isinstance(item, Mapping)
                    else (str(item), ""),
                )
        canonical["derived_level_review"] = ordered
    identities = canonical.get("identities")
    if isinstance(identities, Mapping):
        ordered_identities = dict(identities)
        providers = ordered_identities.get("provider_ids")
        if isinstance(providers, (list, tuple)):
            ordered_identities["provider_ids"] = sorted(providers)
        canonical["identities"] = ordered_identities
    return canonical


def evidence_bundle_digest(bundle: Mapping[str, Any]) -> str:
    """Digest one bundle's semantic content, invariant to declaration order."""

    return _digest(canonical_evidence_bundle(bundle))


# =============================================================================
# 6. the composed hard requirements (closes review finding P2-2)
# =============================================================================

REQUIREMENT_STRUCTURAL_GATE = "structural_state_hard_gate"
REQUIREMENT_TRANSFER_GUARD = "raw_provider_structural_dispersion_guard"
REQUIREMENT_COMPARABILITY = "structural_comparability_sufficiency"
REQUIREMENT_PAIR_COMPLETENESS = "required_gate_pair_completeness"
REQUIREMENT_NOT_COMPARABLE = "unrecorded_not_comparable_event_count"
REQUIREMENT_DERIVED_LEVEL_REVIEW = "unreviewed_derived_level_disagreement_count"
REQUIREMENT_INHERITED_GATES = "inherited_approval_hard_gates"

# Every hard requirement capable of affecting the final V3 result, recovered
# from the frozen definition rather than from the reference function's
# signature. `unrecorded_not_comparable_event_count` is here precisely because
# `approval_verdict` has no parameter for it.
HARD_REQUIREMENT_IDS = (
    REQUIREMENT_STRUCTURAL_GATE,
    REQUIREMENT_TRANSFER_GUARD,
    REQUIREMENT_COMPARABILITY,
    REQUIREMENT_PAIR_COMPLETENESS,
    REQUIREMENT_NOT_COMPARABLE,
    REQUIREMENT_DERIVED_LEVEL_REVIEW,
    REQUIREMENT_INHERITED_GATES,
)

REQUIREMENT_OUTCOMES = (GATE_PASS, GATE_FAIL, GATE_INSUFFICIENT)

# Which requirements can produce a material failure at all. The other three are
# evidence-completeness requirements: they can refuse, never condemn.
REQUIREMENTS_THAT_CAN_FAIL = (
    REQUIREMENT_INHERITED_GATES,
    REQUIREMENT_NOT_COMPARABLE,
    REQUIREMENT_STRUCTURAL_GATE,
    REQUIREMENT_TRANSFER_GUARD,
)

VERDICT_PASS = GATE_PASS
VERDICT_FAIL = GATE_FAIL
VERDICT_INSUFFICIENT = GATE_INSUFFICIENT
VERDICT_VOCABULARY = (VERDICT_PASS, VERDICT_FAIL, VERDICT_INSUFFICIENT)

COMPOSITION_RULE_ID = "V3_COMPOSED_HARD_APPROVAL_CONJUNCTION_V1"
COMPOSITION_RULE = (
    "The final verdict is a deterministic function of the seven hard "
    "requirement outcomes and of nothing else. No soft outcome, no diagnostic "
    "value and no free-text review opinion is a parameter of it. Every "
    "requirement is hard, so the candidate is approved only when all seven "
    "pass; the composition's job is to name which of the two "
    "do-not-approve labels applies."
)

VERDICT_PRECEDENCE_ID = "MATERIAL_FAILURE_OUTRANKS_INSUFFICIENT_EVIDENCE_V1"
VERDICT_PRECEDENCE_RULE = (
    "if any hard requirement is a material failure: FAIL; "
    "else if any hard requirement is missing, undefined, inadmissible, "
    "insufficient or incomplete: UNDEFINED_INSUFFICIENT_EVIDENCE; "
    "else: PASS."
)
VERDICT_PRECEDENCE_EVIDENCE = (
    "The frozen gate_architecture.aggregation states the same precedence "
    "within one gate -- 'a definite material failure outranks missing "
    "evidence, so one bad pair cannot be hidden behind another pair's "
    "silence' -- and transfer_guard.rule repeats it for the guard. The "
    "reference approval_verdict composes across requirements the same way: it "
    "collects failing and blocking requirements separately and returns FAIL "
    "whenever anything is failing, regardless of what is blocking. Lifting "
    "the within-gate rule to the cross-gate composition is the only reading "
    "consistent with both, and it is the reading the reference implementation "
    "already exhibits. The alternative -- letting an unresolved requirement "
    "mask a definite failure -- is refused by the frozen invariant that "
    "insufficient evidence can only refuse, never decide."
)

REASON_STRUCTURAL_GATE_MATERIAL_FAILURE = "STRUCTURAL_STATE_GATE_MATERIAL_FAILURE"
REASON_TRANSFER_GUARD_FAILED = "RAW_PROVIDER_DISPERSION_GUARD_FAILED"
REASON_INHERITED_HARD_GATE_FAILED = "INHERITED_HARD_APPROVAL_GATE_FAILED"
REASON_UNRECORDED_NOT_COMPARABLE_EVENTS = "UNRECORDED_NOT_COMPARABLE_EVENTS_PRESENT"
REASON_STRUCTURAL_GATE_INSUFFICIENT = "STRUCTURAL_STATE_GATE_INSUFFICIENT_EVIDENCE"
REASON_TRANSFER_GUARD_UNDEFINED = "RAW_PROVIDER_DISPERSION_GUARD_UNDEFINED"
REASON_COMPARABILITY_INSUFFICIENT = "STRUCTURAL_COMPARABILITY_INSUFFICIENT"
REASON_REQUIRED_PAIR_UNIVERSE_INCOMPLETE = "REQUIRED_GATE_PAIR_UNIVERSE_INCOMPLETE"
REASON_NOT_COMPARABLE_ACCOUNTING_MISSING = "NOT_COMPARABLE_ACCOUNTING_MISSING"
REASON_DERIVED_LEVEL_REVIEW_INCOMPLETE = "DERIVED_LEVEL_REVIEW_INCOMPLETE"
REASON_INHERITED_GATE_EVIDENCE_MISSING = "INHERITED_HARD_GATE_EVIDENCE_MISSING"
REASON_ALL_HARD_REQUIREMENTS_SATISFIED = "ALL_HARD_REQUIREMENTS_SATISFIED"

# The primary classification is the first applicable reason in this order.
# Failures come first, so a FAIL is never explained by an unresolved
# requirement. The order is part of the validator hash, so no dictionary
# ordering can select it.
REASON_PRECEDENCE = (
    REASON_STRUCTURAL_GATE_MATERIAL_FAILURE,
    REASON_TRANSFER_GUARD_FAILED,
    REASON_INHERITED_HARD_GATE_FAILED,
    REASON_UNRECORDED_NOT_COMPARABLE_EVENTS,
    REASON_STRUCTURAL_GATE_INSUFFICIENT,
    REASON_TRANSFER_GUARD_UNDEFINED,
    REASON_COMPARABILITY_INSUFFICIENT,
    REASON_REQUIRED_PAIR_UNIVERSE_INCOMPLETE,
    REASON_NOT_COMPARABLE_ACCOUNTING_MISSING,
    REASON_DERIVED_LEVEL_REVIEW_INCOMPLETE,
    REASON_INHERITED_GATE_EVIDENCE_MISSING,
    REASON_ALL_HARD_REQUIREMENTS_SATISFIED,
)

# Exactly one reason per (requirement, non-passing outcome), plus one for the
# approving state. `_FAILURE_REASONS` is total over `REQUIREMENTS_THAT_CAN_FAIL`
# and defined nowhere else, so an evidence-completeness requirement has no
# failure label to reach for even by accident.
_FAILURE_REASONS = {
    REQUIREMENT_INHERITED_GATES: REASON_INHERITED_HARD_GATE_FAILED,
    REQUIREMENT_NOT_COMPARABLE: REASON_UNRECORDED_NOT_COMPARABLE_EVENTS,
    REQUIREMENT_STRUCTURAL_GATE: REASON_STRUCTURAL_GATE_MATERIAL_FAILURE,
    REQUIREMENT_TRANSFER_GUARD: REASON_TRANSFER_GUARD_FAILED,
}
_INSUFFICIENT_REASONS = {
    REQUIREMENT_STRUCTURAL_GATE: REASON_STRUCTURAL_GATE_INSUFFICIENT,
    REQUIREMENT_TRANSFER_GUARD: REASON_TRANSFER_GUARD_UNDEFINED,
    REQUIREMENT_INHERITED_GATES: REASON_INHERITED_GATE_EVIDENCE_MISSING,
    REQUIREMENT_NOT_COMPARABLE: REASON_NOT_COMPARABLE_ACCOUNTING_MISSING,
    REQUIREMENT_COMPARABILITY: REASON_COMPARABILITY_INSUFFICIENT,
    REQUIREMENT_PAIR_COMPLETENESS: REASON_REQUIRED_PAIR_UNIVERSE_INCOMPLETE,
    REQUIREMENT_DERIVED_LEVEL_REVIEW: REASON_DERIVED_LEVEL_REVIEW_INCOMPLETE,
}


def compose_verdict(outcomes: Mapping[str, str]) -> dict[str, Any]:
    """Reduce the seven hard requirement outcomes to exactly one verdict.

    Total over the whole state space: every requirement carries one of three
    outcomes, every combination maps to exactly one verdict, and there is no
    ambiguous state to fall through.
    """

    missing = sorted(set(HARD_REQUIREMENT_IDS) - set(outcomes))
    if missing:
        raise ValidatorError(f"the composition is missing hard requirements {missing}")
    unknown = sorted(set(outcomes) - set(HARD_REQUIREMENT_IDS))
    if unknown:
        raise ValidatorError(f"the composition carries unknown requirements {unknown}")
    failing: list[str] = []
    blocking: list[str] = []
    reasons: set[str] = set()
    for requirement in HARD_REQUIREMENT_IDS:
        outcome = outcomes[requirement]
        if outcome not in REQUIREMENT_OUTCOMES:
            raise ValidatorError(
                f"{requirement} carries unknown outcome {outcome!r}"
            )
        if outcome == GATE_FAIL:
            if requirement not in REQUIREMENTS_THAT_CAN_FAIL:
                raise ValidatorError(
                    f"{requirement} is an evidence-completeness requirement and "
                    "cannot report a material failure"
                )
            failing.append(requirement)
            reasons.add(_FAILURE_REASONS[requirement])
        elif outcome == GATE_INSUFFICIENT:
            blocking.append(requirement)
            reasons.add(_INSUFFICIENT_REASONS[requirement])
    if failing:
        verdict = VERDICT_FAIL
    elif blocking:
        verdict = VERDICT_INSUFFICIENT
    else:
        verdict = VERDICT_PASS
        reasons.add(REASON_ALL_HARD_REQUIREMENTS_SATISFIED)
    primary = next(reason for reason in REASON_PRECEDENCE if reason in reasons)
    return {
        "blocking_requirements": sorted(blocking),
        "composition_rule_id": COMPOSITION_RULE_ID,
        "failing_requirements": sorted(failing),
        "primary_reason": primary,
        "reason_codes": sorted(reasons),
        "verdict": verdict,
        "verdict_precedence_id": VERDICT_PRECEDENCE_ID,
    }


# --- 6A. the hard structural gate ---------------------------------------------


def _structural_gate_requirement(
    measurements: Mapping[str, Mapping[str, Any]],
    *,
    required_ids: Sequence[str],
    limit: Decimal,
    quantile: Decimal,
    floor: Decimal,
) -> dict[str, Any]:
    gate = evaluate_hard_structural_gate(
        {name: measurements.get(name) for name in required_ids},
        required_pairs=required_ids,
        limit=limit,
        quantile=quantile,
        comparability_floor=floor,
    )
    _cross_check_point_rates(measurements, required_ids=required_ids, limit=limit)
    return {**gate, "outcome": gate["verdict"], "requirement": REQUIREMENT_STRUCTURAL_GATE}


def _cross_check_point_rates(
    measurements: Mapping[str, Mapping[str, Any]],
    *,
    required_ids: Sequence[str],
    limit: Decimal,
) -> None:
    """Refuse if the Decimal and exact-rational point-rate readings disagree.

    The frozen rule resolves the rate in a 34-digit Decimal context. This
    recomputes the same comparison as a ratio of integers and refuses rather
    than resolving a disagreement, so no rounding can turn a material failure
    into an insufficiency or the reverse.
    """

    for comparison_id in sorted(required_ids):
        measurement = measurements.get(comparison_id)
        if measurement is None:
            continue
        denominator = measurement["denominator"]
        if denominator == 0:
            continue
        numerator = measurement["numerator"]
        decimal_rate = _STAT_CONTEXT.divide(Decimal(numerator), Decimal(denominator))
        if (decimal_rate > limit) != _exact_rate_exceeds(numerator, denominator, limit):
            raise ValidatorError(
                f"{comparison_id}: the Decimal and exact-rational point-rate "
                "readings disagree at the materiality limit"
            )


# --- 6B. the transfer guard ----------------------------------------------------


def _transfer_guard_requirement(
    measurements: Mapping[str, Mapping[str, Any]],
    *,
    required_ids: Sequence[str],
    limit: Decimal,
    quantile: Decimal,
    floor: Decimal,
) -> dict[str, Any]:
    guard = evaluate_transfer_guard(
        {name: measurements.get(name) for name in required_ids},
        limit=limit,
        quantile=quantile,
        comparability_floor=floor,
    )
    _cross_check_point_rates(measurements, required_ids=required_ids, limit=limit)
    outcome = {
        GUARD_SATISFIED: GATE_PASS,
        GUARD_FAILED: GATE_FAIL,
        GUARD_UNDEFINED: GATE_INSUFFICIENT,
    }[guard["outcome"]]
    return {
        **guard,
        "candidate_data_enters_the_guard": False,
        "outcome": outcome,
        "requirement": REQUIREMENT_TRANSFER_GUARD,
    }


# --- 6C. comparability sufficiency and pair completeness -----------------------

COMPARABILITY_REQUIRED_EVIDENCE = (
    "all_detected_event_count",
    "candidate_event_count",
    "comparable_event_count",
    "not_comparable_event_count",
    "not_comparable_rate",
    "not_comparable_reason_counts",
    "structural_comparability_rate",
)


def _comparability_requirement(
    measurements: Mapping[str, Mapping[str, Any]],
    *,
    required_ids: Sequence[str],
    floor: Decimal,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    satisfied = True
    for comparison_id in sorted(required_ids):
        measurement = measurements.get(comparison_id)
        reasons: list[str] = []
        rate: Decimal | None = None
        if measurement is None:
            reasons.append("REQUIRED_PAIR_ABSENT")
        else:
            if measurement.get("state") != PAIR_ADMISSIBLE:
                reasons.append("PAIR_NOT_ESTABLISHED_ADMISSIBLE")
            missing = [
                field
                for field in COMPARABILITY_REQUIRED_EVIDENCE
                if field not in measurement
            ]
            if missing:
                reasons.append("COMPARABILITY_EVIDENCE_INCOMPLETE")
            declared = measurement.get("structural_comparability_rate")
            if declared is None:
                # Null by the frozen rule when nothing was detected at all;
                # insufficient, never a satisfied floor.
                reasons.append("NO_DETECTED_EVENTS")
            else:
                rate = _decimal(declared, f"{comparison_id} structural_comparability_rate")
                if rate < floor:
                    reasons.append("BELOW_STRUCTURAL_COMPARABILITY_FLOOR")
        if reasons:
            satisfied = False
        rows.append(
            {
                "comparison_id": comparison_id,
                "reason_codes": sorted(set(reasons)),
                "satisfied": not reasons,
                "structural_comparability_rate": (
                    None if rate is None else str(_REPORT_CONTEXT.plus(rate))
                ),
            }
        )
    return {
        "floor": str(floor),
        "outcome": GATE_PASS if satisfied else GATE_INSUFFICIENT,
        "pairs": rows,
        "policy_id": "STRUCTURAL_COMPARABILITY_SUFFICIENCY_V2",
        "requirement": REQUIREMENT_COMPARABILITY,
    }


def _pair_completeness_requirement(
    measurements: Mapping[str, Mapping[str, Any]],
    *,
    required_ids: Sequence[str],
    guard_measurements: Mapping[str, Mapping[str, Any]],
    guard_required_ids: Sequence[str],
) -> dict[str, Any]:
    missing_gate = sorted(set(required_ids) - set(measurements))
    missing_guard = sorted(set(guard_required_ids) - set(guard_measurements))
    complete = not missing_gate and not missing_guard
    return {
        "missing_gate_pairs": missing_gate,
        "missing_transfer_guard_pairs": missing_guard,
        "outcome": GATE_PASS if complete else GATE_INSUFFICIENT,
        "present_gate_pair_count": len(measurements),
        "present_transfer_guard_pair_count": len(guard_measurements),
        "requirement": REQUIREMENT_PAIR_COMPLETENESS,
        "required_gate_pair_count": len(required_ids),
        "required_gate_pairs": sorted(required_ids),
        "required_transfer_guard_pair_count": len(guard_required_ids),
        "required_transfer_guard_pairs": sorted(guard_required_ids),
        "universe_id": PAIR_UNIVERSE_ID,
    }


# --- 6D. the NOT_COMPARABLE completeness gate ----------------------------------

NOT_COMPARABLE_REQUIREMENT_INTERPRETATION = (
    "not_comparable_semantics.unrecorded_not_comparable_event_count is frozen "
    "as a structured gate -- direction 'equal', threshold 0, hard true -- in "
    "the same zero-count idiom as the parent's point_in_time_violation_count "
    "and historical_fallback_splice_count. Under the repository's own "
    "threshold convention a present measurement that violates its threshold is "
    "a gate FAIL, and only an absent or null measurement is UNDEFINED. A "
    "positive count is therefore a material hard failure, not an "
    "insufficiency: an event the contract could not evaluate and that nothing "
    "recorded is a defect in the measurement itself, and the frozen semantics "
    "make excluding it from both numerator and denominator conditional on its "
    "being recorded. A missing count is insufficient evidence."
)


def _not_comparable_requirement(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {
            "declared_count": None,
            "direction": "equal",
            "outcome": GATE_INSUFFICIENT,
            "reason_codes": ["NOT_COMPARABLE_ACCOUNTING_ABSENT"],
            "requirement": REQUIREMENT_NOT_COMPARABLE,
            "threshold": 0,
        }
    unknown = sorted(set(payload) - set(NOT_COMPARABLE_ACCOUNTING_REQUIRED_KEYS))
    if unknown:
        raise ValidatorInputError(
            f"the not-comparable accounting block carries unknown fields {unknown}"
        )
    value = payload.get("unrecorded_not_comparable_event_count")
    if value is None:
        return {
            "declared_count": None,
            "direction": "equal",
            "outcome": GATE_INSUFFICIENT,
            "reason_codes": ["NOT_COMPARABLE_COUNT_ABSENT"],
            "requirement": REQUIREMENT_NOT_COMPARABLE,
            "threshold": 0,
        }
    count = _require_count(value, "unrecorded_not_comparable_event_count")
    verdict = threshold_verdict(Decimal(count), threshold=Decimal(0), direction="equal")
    return {
        "declared_count": count,
        "direction": "equal",
        "outcome": GATE_PASS if verdict == GATE_VERDICT_PASS else GATE_FAIL,
        "reason_codes": [] if verdict == GATE_VERDICT_PASS else ["UNRECORDED_EVENTS_PRESENT"],
        "requirement": REQUIREMENT_NOT_COMPARABLE,
        "threshold": 0,
    }


# --- 6E. derived-level review completeness -------------------------------------

MANUAL_REVIEW_SEMANTICS = (
    "Review completeness is hard; review opinion is not a gate. The validator "
    "verifies that a structured review record exists for every observed "
    "comparable breakout and reclaim disagreement on a required gate pair, "
    "that it carries every required field, that its event identity matches the "
    "census entry, and that its provenance is present. It never reads the "
    "reviewer's prose as a pass or a fail. Human prose is not an unhashable "
    "decision input, so a negative assessment cannot reject a candidate the "
    "hard evidence approves and a positive assessment cannot rescue one the "
    "hard evidence fails."
)
DERIVED_LEVEL_REVIEW_INTERPRETATION = (
    "unreviewed_derived_level_disagreement_count == 0 must hold before PASS. "
    "The frozen artifact declares it hard in prose without the structured "
    "direction/threshold pair its NOT_COMPARABLE sibling carries, and the "
    "reference approval_verdict treats a positive count as blocking rather "
    "than failing. A backlog of unreviewed events is missing evidence about "
    "events that have not been assessed, not a measured defect, so a positive "
    "count is UNDEFINED_INSUFFICIENT_EVIDENCE and so is a missing count."
)


DERIVED_LEVEL_DIAGNOSTIC_METRIC_BY_FAMILY = {
    "breakout": "breakout_disagreement_rate",
    "reclaim": "reclaim_disagreement_rate",
}

CENSUS_VERIFICATION_RULE = (
    "The census of observed derived-level disagreements is verified against "
    "the frozen breakout and reclaim diagnostics rather than believed. The "
    "frozen requirement is that *every observed* comparable breakout and "
    "reclaim disagreement on a required gate pair carries a structured "
    "review, so a census that under-reports what was observed would satisfy "
    "the requirement by omission -- the exact fail-open the review fix closed "
    "for comparability evidence. The diagnostics are the only in-protocol "
    "record of what was observed, and diagnostic_semantics.required_fields "
    "makes `count` mandatory on each of them, so for every required gate pair "
    "the census must hold exactly the diagnostics' breakout and reclaim "
    "counts. A missing, duplicated or malformed diagnostic row leaves the "
    "census unverifiable and refuses. This consults a diagnostic *count* "
    "through a frozen evidence-completeness rule and never a diagnostic "
    "*rate*: no diagnostic value enters the hard composition, and this path "
    "can only refuse, never approve."
)

CENSUS_REASON_NOT_VERIFIABLE = "DERIVED_LEVEL_CENSUS_NOT_VERIFIABLE"
CENSUS_REASON_DISAGREES = "DERIVED_LEVEL_CENSUS_DISAGREES_WITH_DIAGNOSTICS"


def observed_derived_level_counts(
    diagnostics: Any,
    *,
    required_ids: Sequence[str],
) -> tuple[dict[tuple[str, str], int] | None, list[str]]:
    """Return observed breakout/reclaim counts per required pair, or None.

    None means the diagnostics do not establish what was observed, which makes
    the census unverifiable and therefore insufficient.
    """

    if not isinstance(diagnostics, Mapping):
        return None, [CENSUS_REASON_NOT_VERIFIABLE]
    counts: dict[tuple[str, str], int] = {}
    for family, metric in sorted(DERIVED_LEVEL_DIAGNOSTIC_METRIC_BY_FAMILY.items()):
        rows = diagnostics.get(metric)
        if not isinstance(rows, (list, tuple)):
            return None, [CENSUS_REASON_NOT_VERIFIABLE]
        seen: dict[str, int] = {}
        for row in rows:
            if not isinstance(row, Mapping):
                return None, [CENSUS_REASON_NOT_VERIFIABLE]
            comparison_id = row.get("comparison_id")
            count = row.get("count")
            if not isinstance(comparison_id, str):
                return None, [CENSUS_REASON_NOT_VERIFIABLE]
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                return None, [CENSUS_REASON_NOT_VERIFIABLE]
            if comparison_id in seen:
                return None, [CENSUS_REASON_NOT_VERIFIABLE]
            seen[comparison_id] = count
        for comparison_id in required_ids:
            if comparison_id not in seen:
                return None, [CENSUS_REASON_NOT_VERIFIABLE]
            counts[(comparison_id, family)] = seen[comparison_id]
    return counts, []


def _derived_level_review_requirement(
    payload: Any,
    *,
    required_ids: Sequence[str],
    diagnostics: Any,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {
            "census_disagreements": [],
            "census_verified": False,
            "declared_count": None,
            "observed_disagreement_count": None,
            "outcome": GATE_INSUFFICIENT,
            "reason_codes": ["DERIVED_LEVEL_REVIEW_BLOCK_ABSENT"],
            "recomputed_unreviewed_count": None,
            "requirement": REQUIREMENT_DERIVED_LEVEL_REVIEW,
            "reviewed_event_count": None,
            "unreviewed_event_ids": [],
        }
    unknown = sorted(set(payload) - set(DERIVED_LEVEL_REVIEW_REQUIRED_KEYS))
    if unknown:
        raise ValidatorInputError(
            f"the derived-level review block carries unknown fields {unknown}"
        )
    missing = sorted(set(DERIVED_LEVEL_REVIEW_REQUIRED_KEYS) - set(payload))
    if missing:
        return {
            "census_disagreements": [],
            "census_verified": False,
            "declared_count": None,
            "observed_disagreement_count": None,
            "outcome": GATE_INSUFFICIENT,
            "reason_codes": ["DERIVED_LEVEL_REVIEW_EVIDENCE_INCOMPLETE"],
            "recomputed_unreviewed_count": None,
            "requirement": REQUIREMENT_DERIVED_LEVEL_REVIEW,
            "reviewed_event_count": None,
            "unreviewed_event_ids": [],
        }
    observed = payload["observed_disagreements"]
    reviews = payload["reviews"]
    if not isinstance(observed, (list, tuple)) or not isinstance(
        reviews, (list, tuple)
    ):
        raise ValidatorInputError(
            "derived-level observed_disagreements and reviews must be lists"
        )
    observed_keys: list[tuple[str, str]] = []
    census_counts: dict[tuple[str, str], int] = {}
    for row in observed:
        record = _require_mapping(row, "a derived-level disagreement")
        missing_fields = sorted(set(DERIVED_LEVEL_EVENT_REQUIRED_KEYS) - set(record))
        if missing_fields:
            raise ValidatorInputError(
                f"a derived-level disagreement omits {missing_fields}"
            )
        if record["family"] not in DERIVED_LEVEL_FAMILIES:
            raise ValidatorInputError(
                f"unknown derived-level family {record['family']!r}"
            )
        if record["comparison_id"] not in required_ids:
            raise ValidatorInputError(
                f"a derived-level disagreement names {record['comparison_id']!r}, "
                "which is not a required gate pair"
            )
        key = (str(record["comparison_id"]), str(record["event_id"]))
        if key in observed_keys:
            raise ValidatorInputError(
                f"derived-level census carries {key} twice"
            )
        observed_keys.append(key)
        family_key = (str(record["comparison_id"]), str(record["family"]))
        census_counts[family_key] = census_counts.get(family_key, 0) + 1
    reviewed_keys: set[tuple[str, str]] = set()
    for row in reviews:
        record = _require_mapping(row, "a derived-level review record")
        missing_fields = sorted(
            set(DERIVED_LEVEL_REVIEW_RECORD_REQUIRED_KEYS) - set(record)
        )
        if missing_fields:
            # An incomplete review record does not review anything; it is not
            # counted, and the backlog it leaves is what refuses.
            continue
        if any(record[field] in (None, "") for field in ("reviewer", "reviewed_at")):
            continue
        key = (str(record["comparison_id"]), str(record["event_id"]))
        if key not in observed_keys:
            raise ValidatorInputError(
                f"a derived-level review names {key}, which the census does not "
                "record as a disagreement"
            )
        reviewed_keys.add(key)
    unreviewed = sorted(key for key in observed_keys if key not in reviewed_keys)
    recomputed = len(unreviewed)
    observed_counts, census_reasons = observed_derived_level_counts(
        diagnostics, required_ids=required_ids
    )
    disagreeing: list[str] = []
    if observed_counts is not None:
        disagreeing = sorted(
            f"{comparison_id}:{family}"
            for (comparison_id, family), expected in observed_counts.items()
            if census_counts.get((comparison_id, family), 0) != expected
        )
        if disagreeing:
            census_reasons = [CENSUS_REASON_DISAGREES]
    census_verified = not census_reasons
    declared = payload["unreviewed_derived_level_disagreement_count"]
    if declared is None:
        return {
            "census_disagreements": disagreeing,
            "census_verified": census_verified,
            "declared_count": None,
            "observed_disagreement_count": len(observed_keys),
            "outcome": GATE_INSUFFICIENT,
            "reason_codes": sorted(
                {"DERIVED_LEVEL_UNREVIEWED_COUNT_ABSENT", *census_reasons}
            ),
            "recomputed_unreviewed_count": recomputed,
            "requirement": REQUIREMENT_DERIVED_LEVEL_REVIEW,
            "reviewed_event_count": len(reviewed_keys),
            "unreviewed_event_ids": [list(key) for key in unreviewed],
        }
    declared_count = _require_count(
        declared, "unreviewed_derived_level_disagreement_count"
    )
    if declared_count != recomputed:
        raise ValidatorInputError(
            "the declared unreviewed derived-level count "
            f"({declared_count}) disagrees with the census and review records "
            f"({recomputed})"
        )
    reasons = set(census_reasons)
    if recomputed:
        reasons.add("UNREVIEWED_DERIVED_LEVEL_EVENTS")
    return {
        "census_disagreements": disagreeing,
        "census_verified": census_verified,
        "declared_count": declared_count,
        "observed_disagreement_count": len(observed_keys),
        "outcome": GATE_PASS if not reasons else GATE_INSUFFICIENT,
        "reason_codes": sorted(reasons),
        "recomputed_unreviewed_count": recomputed,
        "requirement": REQUIREMENT_DERIVED_LEVEL_REVIEW,
        "reviewed_event_count": len(reviewed_keys),
        "unreviewed_event_ids": [list(key) for key in unreviewed],
    }


# --- 6F. the inherited approval gates ------------------------------------------

TIER4_PARITY_RULE = (
    "The validator never rederives a Tier-4 quantity. Stop-touch sensitivity, "
    "stop preservation, MFE, MAE, eligibility, action, risk size, regime and "
    "setup classification are measured by the existing owners under "
    f"{PRICE_SOURCE_POLICY_VERSION}, and the validator compares those "
    "measurements against the frozen thresholds using the repository's own "
    "direction convention -- maximum: value <= threshold passes; minimum: "
    "value >= threshold passes; equal: value == threshold passes -- in exact "
    "Decimal, with equality passing in every direction. A bundle that names a "
    "different comparison contract, detector version or price-source policy "
    "than the bound definition is refused rather than compared."
)


def inherited_gate_definitions(
    protocol: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Return the 33 inherited approval gates exactly as the freeze carries them."""

    gates = protocol["inherited_approval_gates"]
    if not isinstance(gates, list) or not gates:
        raise ValidatorBindingError("the bound definition carries no inherited gates")
    metrics = [gate["metric"] for gate in gates]
    if len(set(metrics)) != len(metrics):
        raise ValidatorBindingError("the inherited gates are not distinct")
    if not all(gate.get("inherited_unchanged") for gate in gates):
        raise ValidatorBindingError("an inherited gate is not marked unchanged")
    return tuple(
        {
            "direction": gate["direction"],
            "hard": bool(gate["hard"]),
            "metric": gate["metric"],
            "threshold": gate["threshold"],
        }
        for gate in sorted(gates, key=lambda item: item["metric"])
    )


INHERITED_GATE_COUNT = 33
INHERITED_HARD_GATE_COUNT = 29
INHERITED_SOFT_GATE_COUNT = 4


def _verify_inherited_gate_census(gates: Sequence[Mapping[str, Any]]) -> None:
    hard = [gate for gate in gates if gate["hard"]]
    soft = [gate for gate in gates if not gate["hard"]]
    if len(gates) != INHERITED_GATE_COUNT:
        raise ValidatorBindingError(
            f"expected {INHERITED_GATE_COUNT} inherited gates, found {len(gates)}"
        )
    if len(hard) != INHERITED_HARD_GATE_COUNT or len(soft) != INHERITED_SOFT_GATE_COUNT:
        raise ValidatorBindingError(
            f"expected {INHERITED_HARD_GATE_COUNT} hard and "
            f"{INHERITED_SOFT_GATE_COUNT} soft inherited gates, found "
            f"{len(hard)} and {len(soft)}"
        )
    hard_metrics = {gate["metric"] for gate in hard}
    missing = sorted(set(INHERITED_TIER4_HARD_GATES) - hard_metrics)
    if missing:
        raise ValidatorBindingError(
            f"the named Tier-4 hard gates are not all inherited hard: {missing}"
        )


def _compare_inherited_gate(gate: Mapping[str, Any], value: Any) -> str:
    threshold = gate["threshold"]
    if isinstance(threshold, bool):
        if not isinstance(value, bool):
            raise ValidatorInputError(
                f"{gate['metric']} is a boolean gate and needs a boolean measurement"
            )
        if gate["direction"] != "equal":
            raise ValidatorBindingError(
                f"{gate['metric']} is boolean but not an equality gate"
            )
        return GATE_VERDICT_PASS if value is threshold else GATE_VERDICT_FAIL
    if isinstance(value, bool):
        raise ValidatorInputError(
            f"{gate['metric']} is a numeric gate and cannot take a boolean"
        )
    return threshold_verdict(
        _decimal(value, f"{gate['metric']} measurement"),
        threshold=_decimal(threshold, f"{gate['metric']} threshold"),
        direction=gate["direction"],
    )


def _inherited_gate_requirement(
    measurements: Any,
    *,
    gates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    payload = _require_mapping(measurements, "inherited_gate_measurements")
    known = {gate["metric"] for gate in gates}
    unknown = sorted(set(payload) - known)
    if unknown:
        raise ValidatorInputError(
            f"inherited_gate_measurements names gates the bound definition does "
            f"not inherit: {unknown}"
        )
    rows: list[dict[str, Any]] = []
    failing: list[str] = []
    blocking: list[str] = []
    for gate in gates:
        metric = gate["metric"]
        value = payload.get(metric)
        if value is None:
            verdict = GATE_VERDICT_UNDEFINED
        else:
            verdict = _compare_inherited_gate(gate, value)
        if gate["hard"]:
            if verdict == GATE_VERDICT_FAIL:
                failing.append(metric)
            elif verdict != GATE_VERDICT_PASS:
                blocking.append(metric)
        rows.append(
            {
                "direction": gate["direction"],
                "hard": gate["hard"],
                "measured": None if value is None else str(value),
                "metric": metric,
                "threshold": str(gate["threshold"]),
                "verdict": verdict,
            }
        )
    if failing:
        outcome = GATE_FAIL
    elif blocking:
        outcome = GATE_INSUFFICIENT
    else:
        outcome = GATE_PASS
    return {
        "blocking_hard_gates": sorted(blocking),
        "failing_hard_gates": sorted(failing),
        "gates": rows,
        "hard_gate_count": sum(1 for gate in gates if gate["hard"]),
        "outcome": outcome,
        "requirement": REQUIREMENT_INHERITED_GATES,
        "soft_gates_can_veto": False,
        "soft_gate_count": sum(1 for gate in gates if not gate["hard"]),
        "tier4_hard_gates": list(INHERITED_TIER4_HARD_GATES),
    }


# =============================================================================
# 7. the within-pair dependence limitation (metadata, not a gate)
# =============================================================================

DEPENDENCE_LIMITATION_ID = "WITHIN_PAIR_CLUSTERING_LIMITATION_V1"
DEPENDENCE_LIMITATION_IS_A_GATE = False
DEPENDENCE_LIMITATION = (
    "The uncorrected Wilson bound treats the comparable structural events "
    "inside a single pair as exchangeable Bernoulli-type observations. Weekly "
    "structure is serially dependent and one episode can produce two "
    "adjacent-week disagreements, so they are not. Positive within-pair "
    "dependence widens the count's distribution in both tails, so nominal 95% "
    "coverage is not attained and the residual risk includes a false "
    "certification, not only a false refusal: against a beta-binomial with the "
    "same mean, a pair whose true structural disagreement rate is 0.30 "
    "certifies with probability 0.115 at n=30 under an intra-cluster "
    "correlation of 0.2, against 0.0003 under exchangeability. The frozen "
    "artifact's claim that this violation can only push a pair towards "
    "insufficiency or failure is wrong in direction, and this validator does "
    "not repeat it. The deterministic point-rate limit remains an "
    "assumption-free floor that the bound only tightens, so the gate is never "
    "weaker than having no bound at all. This is recorded provenance about a "
    "frozen rule the validator implements unchanged; it is not a new gate and "
    "it moves no verdict."
)
DEPENDENCE_LIMITATION_CROSS_PAIR = (
    "No cross-pair independence is assumed anywhere: no band is pooled across "
    "pairs and no family-wise survival probability is multiplied. Aggregation "
    "is a deterministic conjunction over an enumerated pair set."
)


# =============================================================================
# 8. the single authoritative composition point
# =============================================================================


@dataclass(frozen=True)
class ValidationRecord:
    """One complete, reproducible BTC-019 validation result."""

    payload: dict[str, Any]

    @property
    def verdict(self) -> str:
        return self.payload["verdict"]

    @property
    def primary_reason(self) -> str:
        return self.payload["primary_reason"]

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return tuple(self.payload["reason_codes"])

    def as_record(self) -> dict[str, Any]:
        return json.loads(_canonical_json(self.payload))


def validate_v3_candidate(
    evidence_bundle: Mapping[str, Any],
    *,
    repository_root: Path,
    execution_mode: str = EXECUTION_MODE_DRY_RUN,
) -> ValidationRecord:
    """Produce exactly one final BTC-019 result under the frozen V3 protocol.

    This is the only composition point. Every hard requirement, the soft gate,
    the diagnostics, the pair certifications, the transfer guard and the
    inherited gates are evaluated here and nowhere else, and the record binds
    the protocol hash, the validator hash and a digest of its own input.
    """

    if execution_mode not in EXECUTION_MODES:
        raise ValidatorInputError(f"unknown execution mode {execution_mode!r}")
    if execution_mode == EXECUTION_MODE_SEALED:
        raise SealedExecutionNotAuthorizedError(
            "SEALED_EXECUTION is not authorized at this validator revision: the "
            "sealed 2015-07-20..2019-11-30 sample may be collected and opened "
            "only after this validator has passed its own independent xHigh "
            "review"
        )
    if not SEALED_EXECUTION_AUTHORIZED and execution_mode != EXECUTION_MODE_DRY_RUN:
        raise SealedExecutionNotAuthorizedError("only DRY_RUN_SYNTHETIC may run here")

    protocol = bind_frozen_v3(repository_root)
    contract = validator_definition(repository_root)

    bundle = _require_mapping(evidence_bundle, "the evidence bundle")
    _require_exact_keys(bundle, BUNDLE_REQUIRED_KEYS, (), "the evidence bundle")
    if bundle["schema_version"] != EVIDENCE_BUNDLE_SCHEMA_VERSION:
        raise ValidatorInputError(
            f"the evidence bundle does not carry {EVIDENCE_BUNDLE_SCHEMA_VERSION}"
        )

    sample = _require_mapping(bundle["sample"], "the sample block")
    _require_exact_keys(sample, SAMPLE_REQUIRED_KEYS, (), "the sample block")
    start = _parse_instant(sample["start"], "sample start")
    end = _parse_instant(sample["end"], "sample end")
    if end < start:
        raise ValidatorInputError("the sample ends before it starts")
    # The sealed window is known to the validator and refused in this mode.
    guard_untouched_validation_sample(
        start=start,
        end=end,
        purpose=f"{VALIDATOR_VERSION} {execution_mode}",
    )

    identities = _require_mapping(bundle["identities"], "the identities block")
    _require_exact_keys(identities, IDENTITY_REQUIRED_KEYS, (), "the identities block")
    for field, expected in BOUND_MEASUREMENT_IDENTITIES.items():
        declared = identities[field]
        actual = tuple(sorted(declared)) if isinstance(declared, list) else declared
        if actual != expected:
            raise ValidatorInputError(
                f"the bundle declares {field}={declared!r}, which the bound "
                f"definition does not accept (expected {expected!r})"
            )

    provenance = _require_mapping(bundle["provenance"], "the provenance block")
    _require_exact_keys(
        provenance, PROVENANCE_REQUIRED_KEYS, (), "the provenance block"
    )
    for field in ("measurement_record_digest", "sample_manifest_digest"):
        _require_hex_digest(provenance[field], field)

    gate_ids = required_gate_pair_ids(protocol)
    guard_ids = required_transfer_guard_pair_ids(protocol)
    limit = operative_structural_limit(protocol)
    floor = operative_comparability_floor(protocol)
    quantile = operative_normal_quantile(protocol)
    gates = inherited_gate_definitions(protocol)
    _verify_inherited_gate_census(gates)

    gate_measurements = _validate_pair_universe(
        bundle["gate_pair_measurements"],
        required_ids=gate_ids,
        expected_role=ROLE_APPROVAL_GATE_PAIR,
        metric=STRUCTURAL_METRIC,
        floor=floor,
        what="gate_pair_measurements",
    )
    guard_measurements = _validate_pair_universe(
        bundle["transfer_guard_pair_measurements"],
        required_ids=guard_ids,
        expected_role=ROLE_SOURCE_DISPERSION_GUARD_PAIR,
        metric=STRUCTURAL_METRIC,
        floor=floor,
        what="transfer_guard_pair_measurements",
    )
    soft_measurements = _validate_pair_universe(
        bundle["soft_gate_pair_measurements"],
        required_ids=gate_ids,
        expected_role=ROLE_APPROVAL_GATE_PAIR,
        metric=EXACT_TIMESTAMP_METRIC,
        floor=floor,
        what="soft_gate_pair_measurements",
    )

    structural = _structural_gate_requirement(
        gate_measurements,
        required_ids=gate_ids,
        limit=limit,
        quantile=quantile,
        floor=floor,
    )
    guard = _transfer_guard_requirement(
        guard_measurements,
        required_ids=guard_ids,
        limit=limit,
        quantile=quantile,
        floor=floor,
    )
    comparability = _comparability_requirement(
        gate_measurements, required_ids=gate_ids, floor=floor
    )
    completeness = _pair_completeness_requirement(
        gate_measurements,
        required_ids=gate_ids,
        guard_measurements=guard_measurements,
        guard_required_ids=guard_ids,
    )
    not_comparable = _not_comparable_requirement(bundle["not_comparable_accounting"])
    derived_level = _derived_level_review_requirement(
        bundle["derived_level_review"],
        required_ids=gate_ids,
        diagnostics=bundle["diagnostics"],
    )
    inherited = _inherited_gate_requirement(
        bundle["inherited_gate_measurements"], gates=gates
    )

    hard_requirements = {
        REQUIREMENT_STRUCTURAL_GATE: structural,
        REQUIREMENT_TRANSFER_GUARD: guard,
        REQUIREMENT_COMPARABILITY: comparability,
        REQUIREMENT_PAIR_COMPLETENESS: completeness,
        REQUIREMENT_NOT_COMPARABLE: not_comparable,
        REQUIREMENT_DERIVED_LEVEL_REVIEW: derived_level,
        REQUIREMENT_INHERITED_GATES: inherited,
    }
    composition = compose_verdict(
        {name: block["outcome"] for name, block in hard_requirements.items()}
    )

    soft = evaluate_soft_gate(
        {name: soft_measurements.get(name) for name in gate_ids},
        required_pairs=gate_ids,
        limit=limit,
        comparability_floor=floor,
    )
    diagnostics = _validate_diagnostics(bundle["diagnostics"])

    payload: dict[str, Any] = {
        "bound_protocol_definition_sha256": protocol["definition_sha256"],
        "bound_protocol_version": BOUND_PROTOCOL_VERSION,
        "composition": composition,
        "diagnostics": {
            **diagnostics,
            "can_veto_approval": False,
            "enter_the_hard_composition": False,
        },
        "execution_mode": execution_mode,
        "hard_requirements": {
            name: hard_requirements[name] for name in sorted(hard_requirements)
        },
        "hard_requirement_outcomes": {
            name: hard_requirements[name]["outcome"] for name in sorted(hard_requirements)
        },
        "input_evidence_digest": evidence_bundle_digest(bundle),
        "parent_protocol_definition_sha256": protocol["parent_definition_sha256"],
        "primary_reason": composition["primary_reason"],
        "provenance": {
            "candidate_series_id": identities["candidate_series_id"],
            "comparison_contract_version": identities["comparison_contract_version"],
            "denominator_semantics_version": identities[
                "denominator_semantics_version"
            ],
            "evidence_builder_version": provenance["evidence_builder_version"],
            "measurement_record_digest": provenance["measurement_record_digest"],
            "price_source_policy_version": identities["price_source_policy_version"],
            "provider_ids": sorted(identities["provider_ids"]),
            "sample_end": end.isoformat(),
            "sample_id": sample["sample_id"],
            "sample_manifest_digest": provenance["sample_manifest_digest"],
            "sample_start": start.isoformat(),
            "source_detector_version": identities["source_detector_version"],
        },
        "reason_codes": composition["reason_codes"],
        "schema_version": VALIDATOR_RECORD_SCHEMA_VERSION,
        "soft_gate": {
            **soft,
            "can_veto_approval": False,
            "enters_the_hard_composition": False,
        },
        "statistical_limitation": {
            "cross_pair": DEPENDENCE_LIMITATION_CROSS_PAIR,
            "is_a_gate": DEPENDENCE_LIMITATION_IS_A_GATE,
            "limitation_id": DEPENDENCE_LIMITATION_ID,
            "within_pair": DEPENDENCE_LIMITATION,
        },
        "validator_definition_sha256": contract["validator_definition_sha256"],
        "validator_version": VALIDATOR_VERSION,
        "verdict": composition["verdict"],
    }
    payload["validation_record_digest"] = _digest(payload)
    return ValidationRecord(payload=payload)


def _parse_instant(value: Any, what: str) -> datetime:
    if isinstance(value, datetime):
        return require_utc_datetime(value, what)
    if not isinstance(value, str):
        raise ValidatorInputError(f"{what} must be an ISO-8601 UTC instant")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValidatorInputError(f"{what} is not an ISO-8601 instant") from error
    return require_utc_datetime(parsed, what)


def _require_hex_digest(value: Any, what: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValidatorInputError(f"{what} must be a 64-character sha256 digest")
    if any(character not in "0123456789abcdef" for character in value):
        raise ValidatorInputError(f"{what} must be lowercase hexadecimal")
    return value


# =============================================================================
# 9. the hash-bound validator contract
# =============================================================================

SEALED_EXECUTION_RECORD_REQUIREMENTS = (
    "sealed_execution_id",
    "bound_protocol_definition_sha256",
    "validator_definition_sha256",
    "sample_manifest_digest",
    "input_evidence_digest",
    "verdict",
    "primary_reason",
    "reason_codes",
    "hard_requirement_outcomes",
    "execution_timestamp_non_semantic",
)

OUTPUT_SCHEMA_FIELDS = (
    "bound_protocol_definition_sha256",
    "bound_protocol_version",
    "composition",
    "diagnostics",
    "execution_mode",
    "hard_requirement_outcomes",
    "hard_requirements",
    "input_evidence_digest",
    "parent_protocol_definition_sha256",
    "primary_reason",
    "provenance",
    "reason_codes",
    "schema_version",
    "soft_gate",
    "statistical_limitation",
    "validation_record_digest",
    "validator_definition_sha256",
    "validator_version",
    "verdict",
)


def _hard_requirement_contract(protocol: Mapping[str, Any]) -> list[dict[str, Any]]:
    limit = operative_structural_limit(protocol)
    floor = operative_comparability_floor(protocol)
    return [
        {
            "can_fail": True,
            "evaluated_on": list(required_gate_pair_ids(protocol)),
            "insufficient_when": "any required pair is missing, inadmissible, "
            "carries no comparability evidence, has a zero comparable "
            "denominator, or has a point rate at or below the limit whose "
            "Wilson upper bound is not",
            "fails_when": "any required pair's observed point rate exceeds the limit",
            "limit": str(limit),
            "metric": STRUCTURAL_METRIC,
            "requirement": REQUIREMENT_STRUCTURAL_GATE,
            "role": ROLE_HARD,
            "rule_id": "ALL_REQUIRED_PAIRS_MUST_CERTIFY_V1",
        },
        {
            "can_fail": True,
            "evaluated_on": list(required_transfer_guard_pair_ids(protocol)),
            "insufficient_when": "any required provider pair is missing, "
            "inadmissible, undefined or insufficient",
            "fails_when": "any required provider pair is a material failure",
            "limit": str(limit),
            "metric": STRUCTURAL_METRIC,
            "requirement": REQUIREMENT_TRANSFER_GUARD,
            "role": ROLE_HARD,
            "rule_id": "RAW_PROVIDER_STRUCTURAL_DISPERSION_CEILING_V1",
        },
        {
            "can_fail": False,
            "evaluated_on": list(required_gate_pair_ids(protocol)),
            "insufficient_when": "any required gate pair is absent, is not "
            "established PAIR_ADMISSIBLE, omits any required comparability "
            "field, carries a null comparability rate, or sits below the floor",
            "fails_when": "never; comparability is an evidence requirement",
            "floor": str(floor),
            "requirement": REQUIREMENT_COMPARABILITY,
            "required_evidence": list(COMPARABILITY_REQUIRED_EVIDENCE),
            "role": ROLE_HARD,
            "rule_id": "STRUCTURAL_COMPARABILITY_SUFFICIENCY_V2",
        },
        {
            "can_fail": False,
            "evaluated_on": list(required_gate_pair_ids(protocol))
            + list(required_transfer_guard_pair_ids(protocol)),
            "insufficient_when": "any required gate pair or guard pair is absent",
            "fails_when": "never; an absent pair is silence, not a measured defect",
            "requirement": REQUIREMENT_PAIR_COMPLETENESS,
            "required_gate_pair_count": len(required_gate_pair_ids(protocol)),
            "required_transfer_guard_pair_count": len(
                required_transfer_guard_pair_ids(protocol)
            ),
            "role": ROLE_HARD,
            "rule_id": PAIR_UNIVERSE_ID,
            "structural_violation_disposition": PAIR_UNIVERSE_VIOLATION_DISPOSITION,
            "structural_violations": list(PAIR_UNIVERSE_VIOLATIONS),
        },
        {
            "can_fail": True,
            "direction": protocol["not_comparable_semantics"][
                "unrecorded_not_comparable_event_count"
            ]["direction"],
            "insufficient_when": "the count is absent or null",
            "interpretation": NOT_COMPARABLE_REQUIREMENT_INTERPRETATION,
            "fails_when": "the count is present and greater than zero",
            "requirement": REQUIREMENT_NOT_COMPARABLE,
            "role": ROLE_HARD,
            "threshold": protocol["not_comparable_semantics"][
                "unrecorded_not_comparable_event_count"
            ]["threshold"],
        },
        {
            "can_fail": False,
            "census_verification": CENSUS_VERIFICATION_RULE,
            "insufficient_when": "the count is absent, the census or review "
            "records are absent, the recomputed backlog is greater than zero, "
            "or the census does not match the frozen breakout and reclaim "
            "diagnostics on every required gate pair",
            "interpretation": DERIVED_LEVEL_REVIEW_INTERPRETATION,
            "fails_when": "never; an unreviewed event is unassessed evidence",
            "manual_review_semantics": MANUAL_REVIEW_SEMANTICS,
            "requirement": REQUIREMENT_DERIVED_LEVEL_REVIEW,
            "required_review_fields": list(DERIVED_LEVEL_REVIEW_RECORD_REQUIRED_KEYS),
            "role": ROLE_HARD,
            "threshold": 0,
        },
        {
            "can_fail": True,
            "hard_gate_count": INHERITED_HARD_GATE_COUNT,
            "insufficient_when": "any inherited hard gate has no measurement",
            "fails_when": "any inherited hard gate's measurement violates its threshold",
            "formula_parity": TIER4_PARITY_RULE,
            "requirement": REQUIREMENT_INHERITED_GATES,
            "role": ROLE_HARD,
            "soft_gate_count": INHERITED_SOFT_GATE_COUNT,
            "soft_gates_can_veto": False,
            "tier4_hard_gates": list(INHERITED_TIER4_HARD_GATES),
            "total_gate_count": INHERITED_GATE_COUNT,
        },
    ]


def validator_definition(repository_root: Path) -> dict[str, Any]:
    """Build the complete hash-bound validator contract.

    Deterministic from module constants plus the frozen definition it binds, so
    it reproduces anywhere the frozen artifact does. It contains no measured
    value, no wall-clock value and no filesystem path.
    """

    protocol = bind_frozen_v3(repository_root)
    gates = inherited_gate_definitions(protocol)
    _verify_inherited_gate_census(gates)
    verify_wilson_boundary_vectors(
        limit=operative_structural_limit(protocol),
        quantile=operative_normal_quantile(protocol),
    )
    payload: dict[str, Any] = {
        "binding": {
            "binding_rule": BINDING_RULE,
            "binding_rule_id": BINDING_RULE_ID,
            "bound_protocol_definition_sha256": BOUND_PROTOCOL_DEFINITION_SHA256,
            "bound_protocol_version": BOUND_PROTOCOL_VERSION,
            "freeze_implementation_commit": V3_FREEZE_IMPLEMENTATION_COMMIT,
            "on_mismatch": BINDING_REFUSAL,
            "parent_protocol_definition_sha256": PARENT_PROTOCOL_DEFINITION_SHA256,
            "parent_protocol_version": PARENT_PROTOCOL_VERSION,
            "review_commit": V3_REVIEW_COMMIT,
            "review_result": V3_REVIEW_RESULT,
        },
        "certification_rule": {
            "arithmetic": WILSON_ARITHMETIC,
            "boundary_vectors": [dict(row) for row in WILSON_BOUNDARY_VECTORS],
            "boundary_vectors_enforced_at_runtime": True,
            "boundary_vector_enforcement": WILSON_BOUNDARY_ENFORCEMENT,
            "confidence_level_percent": operative_confidence_level_percent(protocol),
            "continuity_correction_applied": WILSON_CONTINUITY_CORRECTION_APPLIED,
            "equality_behaviour": protocol["gate_architecture"]["certification_rule"][
                "equality_behaviour"
            ],
            "formula": WILSON_FORMULA_EXPRESSION,
            "formula_id": WILSON_FORMULA_ID,
            "normal_quantile": str(operative_normal_quantile(protocol)),
            "outcomes": [
                PAIR_CERTIFIED,
                PAIR_MATERIAL_FAILURE,
                PAIR_INSUFFICIENT_EVIDENCE,
            ],
            "point_rate_semantics": (
                "A rate strictly greater than the limit is "
                "PAIR_MATERIAL_FAILURE. A rate exactly at the limit is not a "
                "material failure by point rate; the confidence rule may still "
                "make it insufficient."
            ),
            "refused_variants": list(WILSON_FORMULA_REFUSALS),
            "rule_id": CERTIFICATION_RULE_ID,
            "zero_denominator": WILSON_ZERO_DENOMINATOR,
        },
        "composition": {
            "composition_rule": COMPOSITION_RULE,
            "composition_rule_id": COMPOSITION_RULE_ID,
            "hard_requirement_ids": list(HARD_REQUIREMENT_IDS),
            "requirement_outcomes": list(REQUIREMENT_OUTCOMES),
            "requirements_that_can_fail": list(REQUIREMENTS_THAT_CAN_FAIL),
            "single_composition_point": "validate_v3_candidate",
            "state_space_is_total": True,
        },
        "diagnostic_requirements": {
            "can_veto_approval": False,
            "enter_the_hard_composition": False,
            "metrics": list(DIAGNOSTIC_METRICS),
            "required_fields": list(DIAGNOSTIC_REQUIRED_FIELDS),
            "role": ROLE_DIAGNOSTIC,
            "rule": (
                "Diagnostics are validated for completeness and published per "
                "required pair. They carry no threshold, no pass and no fail, "
                "and are not parameters of the composition. They may reach a "
                "verdict only through a separately frozen evidence-completeness "
                "rule, which in V3 is the derived-level review census: the "
                "breakout and reclaim `count` fields bound how large that "
                "census must be, and no diagnostic rate is read anywhere."
            ),
            "census_verification": CENSUS_VERIFICATION_RULE,
        },
        "evidence_completeness": {
            "declared_value_verification": DECLARED_VALUE_VERIFICATION,
            "declared_value_verification_id": DECLARED_VALUE_VERIFICATION_ID,
            "missing_is_never_satisfied": True,
            "nullable_pair_fields": list(PAIR_NULLABLE_KEYS),
            "nullable_semantics": (
                "structural_comparability_rate and not_comparable_rate are null "
                "exactly when the pair detected no events at all. Null is "
                "insufficient evidence, never a satisfied floor and never a "
                "rate of 0.0. No other field may be absent or null."
            ),
            "required_pair_evidence": list(PAIR_REQUIRED_KEYS),
            "required_pair_state": PAIR_ADMISSIBLE,
            "rule": (
                "A required pair must explicitly carry an established "
                "PAIR_ADMISSIBLE state, a present structural comparability "
                "rate, a numerator, a denominator, its canonical comparison "
                "identity, both provider identities and its complete "
                "not-comparable reason and event counters. An omitted field is "
                "evidence of absence and can only refuse; it never defaults to "
                "a pass."
            ),
        },
        "hard_requirements": _hard_requirement_contract(protocol),
        "input_schema": {
            "bound_measurement_identities": {
                key: (list(value) if isinstance(value, tuple) else value)
                for key, value in sorted(BOUND_MEASUREMENT_IDENTITIES.items())
            },
            "derived_level_review_required_keys": list(
                DERIVED_LEVEL_REVIEW_REQUIRED_KEYS
            ),
            "identity_required_keys": list(IDENTITY_REQUIRED_KEYS),
            "pair_optional_keys": list(PAIR_OPTIONAL_KEYS),
            "pair_required_keys": list(PAIR_REQUIRED_KEYS),
            "provenance_required_keys": list(PROVENANCE_REQUIRED_KEYS),
            "required_keys": list(BUNDLE_REQUIRED_KEYS),
            "sample_required_keys": list(SAMPLE_REQUIRED_KEYS),
            "schema_version": EVIDENCE_BUNDLE_SCHEMA_VERSION,
            "unknown_fields": "REFUSED",
        },
        "material_change_requires": MATERIAL_CHANGE_REQUIRES,
        "not_a_price_reference_protocol": True,
        "not_comparable_handling": {
            "excluded_from_numerator_and_denominator": protocol[
                "not_comparable_semantics"
            ]["excluded_from_numerator_and_denominator"],
            "interpretation": NOT_COMPARABLE_REQUIREMENT_INTERPRETATION,
            "missing_count": VERDICT_INSUFFICIENT,
            "positive_count": VERDICT_FAIL,
            "states": list(protocol["not_comparable_semantics"]["states"]),
            "zero_count": VERDICT_PASS,
        },
        "operative_field_precedence": {
            "examples": [dict(row) for row in OPERATIVE_FIELD_PRECEDENCE_EXAMPLES],
            "historical_provenance_only_fields": list(
                HISTORICAL_PROVENANCE_ONLY_FIELDS
            ),
            "operative_v3_authority_fields": list(OPERATIVE_V3_AUTHORITY_FIELDS),
            "precedence_id": OPERATIVE_FIELD_PRECEDENCE_ID,
            "rule": OPERATIVE_FIELD_PRECEDENCE_RULE,
        },
        "output_schema": {
            "fields": list(OUTPUT_SCHEMA_FIELDS),
            "record_schema_version": VALIDATOR_RECORD_SCHEMA_VERSION,
            "sealed_execution_record_requirements": list(
                SEALED_EXECUTION_RECORD_REQUIREMENTS
            ),
        },
        "reason_vocabulary": {
            "primary_reason_rule": (
                "The primary classification is the first applicable reason in "
                "the declared precedence order, which is part of this "
                "definition's hash. Every applicable reason is also published "
                "as a complete sorted set. No dictionary ordering can select "
                "the primary reason and ties cannot arise."
            ),
            "reasons": list(REASON_PRECEDENCE),
        },
        "required_gate_pairs": list(required_gate_pair_ids(protocol)),
        "required_transfer_guard_pairs": list(
            required_transfer_guard_pair_ids(protocol)
        ),
        "sealed_sample": {
            "collection_authorized": False,
            "end": protocol["sample_governance"]["sealed_sample"]["end"],
            "execution_modes": list(EXECUTION_MODES),
            "opening_authorized": False,
            "sealed_execution_authorized": SEALED_EXECUTION_AUTHORIZED,
            "sealed_execution_rule": SEALED_EXECUTION_AUTHORIZATION_RULE,
            "start": protocol["sample_governance"]["sealed_sample"]["start"],
        },
        "soft_requirements": {
            "cannot_reject_alone": True,
            "enters_the_hard_composition": False,
            "limit": str(operative_structural_limit(protocol)),
            "metric": EXACT_TIMESTAMP_METRIC,
            "outcomes": [SOFT_OUTCOME_OK, SOFT_OUTCOME_REVIEW_REQUIRED],
            "role": ROLE_SOFT,
            "undefined_behaviour": (
                "A missing, inadmissible or undefined required pair warns. "
                "Absent evidence never reads as OK."
            ),
        },
        "statistical_limitation": {
            "cross_pair": DEPENDENCE_LIMITATION_CROSS_PAIR,
            "is_a_gate": DEPENDENCE_LIMITATION_IS_A_GATE,
            "limitation_id": DEPENDENCE_LIMITATION_ID,
            "repeats_the_frozen_conservatism_claim": False,
            "within_pair": DEPENDENCE_LIMITATION,
        },
        "tier4_inheritance": {
            "bound_source": {
                "bound_protocol_definition_sha256": BOUND_PROTOCOL_DEFINITION_SHA256,
                "comparison_contract_version": COMPARISON_CONTRACT_VERSION,
                "denominator_semantics_version": DENOMINATOR_SEMANTICS_VERSION,
                "measurement_owner_policy_version": PRICE_SOURCE_POLICY_VERSION,
                "parent_protocol_definition_sha256": PARENT_PROTOCOL_DEFINITION_SHA256,
                "source_detector_version": WEEKLY_STRUCTURE_DETECTOR_VERSION,
            },
            "comparison_convention": TIER4_PARITY_RULE,
            "gates": [dict(gate) for gate in gates],
            "hard_gate_count": INHERITED_HARD_GATE_COUNT,
            "named_tier4_hard_gates": list(INHERITED_TIER4_HARD_GATES),
            "soft_gate_count": INHERITED_SOFT_GATE_COUNT,
            "soft_gates_can_regain_a_hard_veto": False,
            "total_gate_count": INHERITED_GATE_COUNT,
        },
        "validator_schema_version": VALIDATOR_SCHEMA_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "verdict_precedence": {
            "insufficient_condition": "no material hard failure, and at least "
            "one hard requirement missing, undefined, inadmissible, "
            "insufficient or incomplete",
            "fail_condition": "at least one hard requirement is a material failure",
            "pass_condition": "every hard requirement passes",
            "precedence_id": VERDICT_PRECEDENCE_ID,
            "reason_precedence": list(REASON_PRECEDENCE),
            "repository_evidence": VERDICT_PRECEDENCE_EVIDENCE,
            "rule": VERDICT_PRECEDENCE_RULE,
        },
        "verdict_vocabulary": list(VERDICT_VOCABULARY),
    }
    payload["validator_definition_sha256"] = _digest(payload)
    return payload


def validator_definition_sha256(repository_root: Path) -> str:
    return validator_definition(repository_root)["validator_definition_sha256"]


# =============================================================================
# 10. persistence, restore and tamper refusal
# =============================================================================


def write_validator_artifacts(
    repository_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Persist the validator contract and its report."""

    output_dir.mkdir(parents=True, exist_ok=True)
    definition = validator_definition(repository_root)
    (output_dir / VALIDATOR_DEFINITION_FILENAME).write_text(
        json.dumps(definition, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="ascii",
    )
    (output_dir / VALIDATOR_REPORT_FILENAME).write_text(
        validator_markdown(definition), encoding="ascii"
    )
    return definition


def restore_validator_definition(output_dir: Path) -> dict[str, Any]:
    """Read the persisted validator contract, refusing every meaningful tamper."""

    payload = json.loads(
        (output_dir / VALIDATOR_DEFINITION_FILENAME).read_text(encoding="ascii")
    )
    if payload.get("validator_schema_version") != VALIDATOR_SCHEMA_VERSION:
        raise ValidatorError(
            f"persisted contract does not carry {VALIDATOR_SCHEMA_VERSION}"
        )
    if payload.get("validator_version") != VALIDATOR_VERSION:
        raise ValidatorError("persisted contract is not this validator version")
    binding = payload.get("binding", {})
    if binding.get("bound_protocol_definition_sha256") != BOUND_PROTOCOL_DEFINITION_SHA256:
        raise ValidatorError("persisted contract binds a different V3 definition hash")
    if binding.get("parent_protocol_definition_sha256") != PARENT_PROTOCOL_DEFINITION_SHA256:
        raise ValidatorError("persisted contract names a different parent hash")
    if binding.get("bound_protocol_version") != BOUND_PROTOCOL_VERSION:
        raise ValidatorError("persisted contract binds a different protocol version")
    if payload.get("verdict_vocabulary") != list(VERDICT_VOCABULARY):
        raise ValidatorError("persisted contract carries a different verdict vocabulary")
    precedence = payload.get("verdict_precedence", {})
    if precedence.get("precedence_id") != VERDICT_PRECEDENCE_ID:
        raise ValidatorError("persisted contract carries a different verdict precedence")
    if precedence.get("rule") != VERDICT_PRECEDENCE_RULE:
        raise ValidatorError("persisted contract carries a different precedence rule")
    if precedence.get("reason_precedence") != list(REASON_PRECEDENCE):
        raise ValidatorError("persisted contract carries a different reason precedence")
    operative = payload.get("operative_field_precedence", {})
    if operative.get("precedence_id") != OPERATIVE_FIELD_PRECEDENCE_ID:
        raise ValidatorError(
            "persisted contract carries a different operative-field precedence"
        )
    if operative.get("historical_provenance_only_fields") != list(
        HISTORICAL_PROVENANCE_ONLY_FIELDS
    ):
        raise ValidatorError(
            "persisted contract restores historical provenance fields to authority"
        )
    certification = payload.get("certification_rule", {})
    if certification.get("formula_id") != WILSON_FORMULA_ID:
        raise ValidatorError("persisted contract names a different Wilson formula")
    if certification.get("formula") != WILSON_FORMULA_EXPRESSION:
        raise ValidatorError("persisted contract carries a different Wilson formula")
    if certification.get("continuity_correction_applied"):
        raise ValidatorError("persisted contract applies a continuity correction")
    if certification.get("boundary_vectors") != [
        dict(row) for row in WILSON_BOUNDARY_VECTORS
    ]:
        raise ValidatorError("persisted contract pins different boundary vectors")
    if not certification.get("boundary_vectors_enforced_at_runtime"):
        raise ValidatorError("persisted contract stops enforcing its own boundaries")
    if certification.get("rule_id") != CERTIFICATION_RULE_ID:
        raise ValidatorError("persisted contract names a different certification rule")
    composition = payload.get("composition", {})
    if composition.get("composition_rule_id") != COMPOSITION_RULE_ID:
        raise ValidatorError("persisted contract carries a different composition rule")
    if composition.get("hard_requirement_ids") != list(HARD_REQUIREMENT_IDS):
        raise ValidatorError("persisted contract composes a different requirement set")
    tier4 = payload.get("tier4_inheritance", {})
    if tier4.get("total_gate_count") != INHERITED_GATE_COUNT:
        raise ValidatorError("persisted contract inherits a different gate count")
    if tier4.get("hard_gate_count") != INHERITED_HARD_GATE_COUNT:
        raise ValidatorError("persisted contract inherits a different hard gate count")
    if tier4.get("soft_gate_count") != INHERITED_SOFT_GATE_COUNT:
        raise ValidatorError("persisted contract inherits a different soft gate count")
    if tier4.get("named_tier4_hard_gates") != list(INHERITED_TIER4_HARD_GATES):
        raise ValidatorError("persisted contract names different Tier-4 hard gates")
    if tier4.get("soft_gates_can_regain_a_hard_veto"):
        raise ValidatorError("persisted contract promotes a soft inherited gate")
    sealed = payload.get("sealed_sample", {})
    if sealed.get("collection_authorized") or sealed.get("opening_authorized"):
        raise ValidatorError("persisted contract authorises sealed-sample access")
    if sealed.get("sealed_execution_authorized"):
        raise ValidatorError("persisted contract authorises sealed execution")
    if sealed.get("start") != UNTOUCHED_OOS_START.isoformat() or sealed.get(
        "end"
    ) != UNTOUCHED_OOS_END.isoformat():
        raise ValidatorError("persisted contract carries different sealed boundaries")
    derived_level = next(
        (
            item
            for item in payload.get("hard_requirements", [])
            if isinstance(item, Mapping)
            and item.get("requirement") == REQUIREMENT_DERIVED_LEVEL_REVIEW
        ),
        {},
    )
    if derived_level.get("census_verification") != CENSUS_VERIFICATION_RULE:
        raise ValidatorError(
            "persisted contract carries a different derived-level census rule"
        )
    completeness = payload.get("evidence_completeness", {})
    if completeness.get("declared_value_verification_id") != (
        DECLARED_VALUE_VERIFICATION_ID
    ):
        raise ValidatorError(
            "persisted contract stops verifying declared pair values against "
            "their own counts"
        )
    if not completeness.get("missing_is_never_satisfied"):
        raise ValidatorError("persisted contract lets missing evidence satisfy")
    not_comparable = payload.get("not_comparable_handling", {})
    if (
        not_comparable.get("zero_count") != VERDICT_PASS
        or not_comparable.get("positive_count") != VERDICT_FAIL
        or not_comparable.get("missing_count") != VERDICT_INSUFFICIENT
    ):
        raise ValidatorError(
            "persisted contract carries a different NOT_COMPARABLE requirement"
        )
    if payload.get("not_a_price_reference_protocol") is not True:
        raise ValidatorError("persisted contract claims to be a price-reference protocol")
    digest = payload.get("validator_definition_sha256")
    body = {
        key: value
        for key, value in payload.items()
        if key != "validator_definition_sha256"
    }
    if digest != _digest(body):
        raise ValidatorError("persisted validator definition was tampered with")
    return payload


def verify_validator_artifacts(
    repository_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Recompute the contract and refuse a persisted copy that disagrees."""

    persisted = restore_validator_definition(output_dir)
    rebuilt = validator_definition(repository_root)
    if _canonical_json(persisted) != _canonical_json(rebuilt):
        raise ValidatorError(
            "persisted validator definition does not recompute from the repository"
        )
    return persisted


# =============================================================================
# report
# =============================================================================


def validator_markdown(definition: Mapping[str, Any]) -> str:
    """Render the validator contract as a deterministic report."""

    binding = definition["binding"]
    certification = definition["certification_rule"]
    lines: list[str] = [
        f"# {VALIDATOR_VERSION}",
        "",
        "An executable interpretation contract bound to the frozen",
        "`BTC_REFERENCE_COMPOSITE_V3` definition hash. It is not a new",
        "price-reference protocol: it authors no threshold, moves no frozen byte,",
        "and resolves only what the frozen definition left to a validator.",
        "",
        "## Binding",
        "",
        f"- Bound protocol: `{binding['bound_protocol_version']}`",
        f"- Bound definition hash: `{binding['bound_protocol_definition_sha256']}`",
        f"- Parent hash (not bound to): `{binding['parent_protocol_definition_sha256']}`",
        f"- Freeze commit: `{binding['freeze_implementation_commit']}`",
        f"- Review commit: `{binding['review_commit']}` "
        f"({binding['review_result']})",
        f"- On mismatch: `{binding['on_mismatch']}`",
        f"- Validator definition hash: "
        f"`{definition['validator_definition_sha256']}`",
        "",
        "## Verdict precedence",
        "",
        f"```text\n{definition['verdict_precedence']['rule']}\n```",
        "",
        "## Composed hard requirements",
        "",
    ]
    for requirement in definition["hard_requirements"]:
        lines.append(
            f"- `{requirement['requirement']}` -- "
            f"can fail: {str(requirement['can_fail']).lower()}"
        )
    lines += [
        "",
        "## Certification rule",
        "",
        f"- Formula id: `{certification['formula_id']}`",
        f"- Continuity correction: "
        f"{str(certification['continuity_correction_applied']).lower()}",
        f"- Quantile: `{certification['normal_quantile']}`",
        f"- Confidence level: {certification['confidence_level_percent']}%",
        "",
        "| k | n | outcome |",
        "| --- | --- | --- |",
    ]
    for row in certification["boundary_vectors"]:
        lines.append(f"| {row['numerator']} | {row['denominator']} | {row['outcome']} |")
    lines += [
        "",
        "## Required pairs",
        "",
        "Approval gate pairs:",
        "",
    ]
    lines += [f"- `{name}`" for name in definition["required_gate_pairs"]]
    lines += ["", "Transfer-guard pairs:", ""]
    lines += [f"- `{name}`" for name in definition["required_transfer_guard_pairs"]]
    lines += [
        "",
        "## Sealed sample",
        "",
        f"- Window: `{definition['sealed_sample']['start']}` .. "
        f"`{definition['sealed_sample']['end']}`",
        "- Collection authorized: no",
        "- Opening authorized: no",
        "- `SEALED_EXECUTION` authorized: no",
        "",
        "## Statistical limitation",
        "",
        definition["statistical_limitation"]["within_pair"],
        "",
    ]
    return "\n".join(lines)


def main() -> None:  # pragma: no cover - operational entry point
    repository_root = Path(__file__).resolve().parents[2]
    output_dir = repository_root / VALIDATOR_OUTPUT_NAMESPACE
    definition = write_validator_artifacts(repository_root, output_dir)
    print(definition["validator_definition_sha256"])


if __name__ == "__main__":  # pragma: no cover - operational entry point
    main()
