"""Hash-bound BTC_REFERENCE_COMPOSITE_V3 validator regressions.

Four things must be impossible here.

The validator must not be able to run against anything but the exact frozen
definition. One changed hex digit in `4232e886...bf71a`, a definition that
names another parent, or a persisted artifact that does not recompute, all
have to refuse before a single verdict is composed -- with no fallback by
version name, no fallback to the parent and no "latest V3".

Missing evidence must not be able to certify. An absent pair, an absent
admissibility state, a null comparability rate, a zero comparable denominator,
a short pair list, an unmeasured Tier-4 gate, an unverifiable derived-level
census and an absent NOT_COMPARABLE count all travel as
`UNDEFINED_INSUFFICIENT_EVIDENCE` or refuse outright -- never as a pass and
never as a rate of 0.0.

A demoted metric and a human opinion must not be able to move a verdict. The
soft gate, the four diagnostics and the free text of a manual review are not
parameters of the composition at all, and the tests prove it by moving them and
watching the verdict stand still.

And the sealed 2015-07-20..2019-11-30 sample must stay shut. `SEALED_EXECUTION`
is refused unconditionally, the inherited guard refuses the window, the
candidate is never constructed, and a full validation run is watched reading
the filesystem to prove it opens no market data at all.
"""

import decimal
import inspect
import json
import os
import re
import subprocess
import sys
from decimal import Context, Decimal, localcontext
from fractions import Fraction
from itertools import product
from pathlib import Path

import pytest

from btc_predictor.research.cross_provider_structure_comparison import (
    COMPARISON_CONTRACT_VERSION,
    WEEKLY_STRUCTURE_DETECTOR_VERSION,
)
from btc_predictor.research.price_source_policy import (
    PRICE_SOURCE_POLICY_VERSION,
)
from btc_predictor.research.reference_composite_v2 import (
    UNTOUCHED_OOS_END,
    UNTOUCHED_OOS_START,
    UntouchedValidationSampleGuardError,
)
from btc_predictor.research.structural_gate_denominator_resolution import (
    DENOMINATOR_SEMANTICS_VERSION,
)
from btc_predictor.research.structural_threshold_calibration import (
    PAIR_ADMISSIBLE,
    PAIR_INADMISSIBLE,
)
from btc_predictor.research.reference_composite_v3_convergence import (
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
    approval_verdict,
    certify_pair,
    evaluate_hard_structural_gate,
    v3_protocol_definition,
)
from btc_predictor.research.reference_composite_v3_validator import (
    BOUND_PROTOCOL_DEFINITION_SHA256,
    CENSUS_REASON_DISAGREES,
    CENSUS_REASON_NOT_VERIFIABLE,
    CENSUS_VERIFICATION_RULE,
    DIAGNOSTIC_METRICS,
    DIAGNOSTIC_REQUIRED_FIELDS,
    EVIDENCE_BUNDLE_SCHEMA_VERSION,
    EXACT_TIMESTAMP_METRIC,
    EXECUTION_MODE_DRY_RUN,
    EXECUTION_MODE_SEALED,
    HARD_REQUIREMENT_IDS,
    HISTORICAL_PROVENANCE_ONLY_FIELDS,
    INHERITED_GATE_COUNT,
    INHERITED_HARD_GATE_COUNT,
    INHERITED_SOFT_GATE_COUNT,
    PARENT_PROTOCOL_DEFINITION_SHA256,
    REASON_ALL_HARD_REQUIREMENTS_SATISFIED,
    REASON_COMPARABILITY_INSUFFICIENT,
    REASON_DERIVED_LEVEL_REVIEW_INCOMPLETE,
    REASON_INHERITED_GATE_EVIDENCE_MISSING,
    REASON_INHERITED_HARD_GATE_FAILED,
    REASON_NOT_COMPARABLE_ACCOUNTING_MISSING,
    REASON_PRECEDENCE,
    REASON_REQUIRED_PAIR_UNIVERSE_INCOMPLETE,
    REASON_STRUCTURAL_GATE_INSUFFICIENT,
    REASON_STRUCTURAL_GATE_MATERIAL_FAILURE,
    REASON_TRANSFER_GUARD_FAILED,
    REASON_TRANSFER_GUARD_UNDEFINED,
    REASON_UNRECORDED_NOT_COMPARABLE_EVENTS,
    REQUIREMENT_COMPARABILITY,
    REQUIREMENT_DERIVED_LEVEL_REVIEW,
    REQUIREMENT_INHERITED_GATES,
    REQUIREMENT_NOT_COMPARABLE,
    REQUIREMENT_PAIR_COMPLETENESS,
    REQUIREMENT_STRUCTURAL_GATE,
    REQUIREMENT_TRANSFER_GUARD,
    REQUIREMENTS_THAT_CAN_FAIL,
    SEALED_EXECUTION_AUTHORIZED,
    STRUCTURAL_METRIC,
    VALIDATOR_DEFINITION_FILENAME,
    VALIDATOR_OUTPUT_NAMESPACE,
    VALIDATOR_RECORD_SCHEMA_VERSION,
    VALIDATOR_REPORT_FILENAME,
    VALIDATOR_SCHEMA_VERSION,
    VALIDATOR_VERSION,
    VERDICT_FAIL,
    VERDICT_INSUFFICIENT,
    VERDICT_PASS,
    VERDICT_VOCABULARY,
    WILSON_BOUNDARY_VECTORS,
    WILSON_CONTINUITY_CORRECTION_APPLIED,
    WILSON_FORMULA_ID,
    SealedExecutionNotAuthorizedError,
    ValidatorBindingError,
    ValidatorError,
    ValidatorInputError,
    bind_frozen_v3,
    canonical_pair_id,
    compose_verdict,
    evidence_bundle_digest,
    inherited_gate_definitions,
    observed_derived_level_counts,
    operative_comparability_floor,
    operative_metric_role,
    operative_normal_quantile,
    operative_structural_limit,
    required_gate_pair_ids,
    required_transfer_guard_pair_ids,
    restore_validator_definition,
    structural_upper_bound,
    validate_v3_candidate,
    validator_definition,
    validator_definition_sha256,
    verify_validator_artifacts,
    write_validator_artifacts,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

# The frozen hash, retyped rather than imported, so an edit to the module's own
# constant cannot make this suite agree with itself about the wrong protocol.
FROZEN_V3_DEFINITION_SHA256 = (
    "4232e886e7888b85833f778fcba6b2cb3eb5b7d802748aebf3b8adf19c5bf71a"
)
FROZEN_V2_PARENT_SHA256 = (
    "bc312f3e6a6035e00a3cd80103aacdee7b5a02ae69732b7bbca5785a3dd6106a"
)

GATE_PAIRS = (
    "MEDIAN_OHLC_V2_vs_bitfinex",
    "MEDIAN_OHLC_V2_vs_bitstamp",
    "MEDIAN_OHLC_V2_vs_coinbase",
)
GUARD_PAIRS = (
    "bitfinex_vs_bitstamp",
    "bitfinex_vs_coinbase",
    "bitstamp_vs_coinbase",
)

# A synthetic window well clear of the sealed one. Nothing in this suite reads
# a collected sample; these instants exist only to satisfy the schema and to
# let the inherited guard prove it is watching.
SYNTHETIC_START = "2023-01-01T00:00:00+00:00"
SYNTHETIC_END = "2025-12-31T23:00:00+00:00"


@pytest.fixture(scope="module")
def protocol() -> dict:
    return v3_protocol_definition(REPOSITORY_ROOT)


@pytest.fixture(scope="module")
def contract() -> dict:
    return validator_definition(REPOSITORY_ROOT)


# =============================================================================
# synthetic fixtures -- no candidate history and no collected sample anywhere
# =============================================================================


def _pair_row(
    comparison_id: str,
    metric: str,
    numerator: int,
    denominator: int,
    *,
    comparability: str | None = "1",
    not_comparable: int = 0,
    state: str = PAIR_ADMISSIBLE,
    **overrides,
) -> dict:
    series_pair = sorted(comparison_id.split("_vs_"))
    detected = denominator + not_comparable
    row: dict = {
        "all_detected_event_count": detected,
        "candidate_event_count": denominator,
        "comparable_event_count": denominator,
        "comparison_id": comparison_id,
        "denominator": denominator,
        "metric": metric,
        "not_comparable_event_count": not_comparable,
        "not_comparable_rate": None if comparability is None else "0",
        "not_comparable_reason_counts": {},
        "numerator": numerator,
        "series_pair": series_pair,
        "state": state,
        "structural_comparability_rate": comparability,
    }
    row.update(overrides)
    return row


def _gate_rows(numerator: int = 0, denominator: int = 40, **overrides) -> list[dict]:
    return [
        _pair_row(name, STRUCTURAL_METRIC, numerator, denominator, **overrides)
        for name in GATE_PAIRS
    ]


def _guard_rows(numerator: int = 0, denominator: int = 40, **overrides) -> list[dict]:
    return [
        _pair_row(name, STRUCTURAL_METRIC, numerator, denominator, **overrides)
        for name in GUARD_PAIRS
    ]


def _soft_rows(numerator: int = 0, denominator: int = 40, **overrides) -> list[dict]:
    return [
        _pair_row(name, EXACT_TIMESTAMP_METRIC, numerator, denominator, **overrides)
        for name in GATE_PAIRS
    ]


def _diagnostic_row(comparison_id: str, count: int = 0, rate: str | None = "0") -> dict:
    row = {
        "calendar_displacement_weeks": [],
        "comparable_event_count": 12,
        "comparison_id": comparison_id,
        "count": count,
        "matched_pair_count": 0,
        "not_comparable_event_count": 0,
        "not_comparable_reason_counts": {},
        "rate": rate,
        "reason_codes": [],
    }
    assert not set(DIAGNOSTIC_REQUIRED_FIELDS) - set(row)
    return row


def _diagnostics(**counts_by_metric) -> dict:
    """Complete diagnostics for every required pair, all four metrics."""

    payload = {}
    for metric in DIAGNOSTIC_METRICS:
        counts = counts_by_metric.get(metric, {})
        payload[metric] = [
            _diagnostic_row(name, counts.get(name, 0)) for name in GATE_PAIRS
        ]
    return payload


def _inherited_measurements(protocol: dict, **overrides) -> dict:
    """A passing measurement for every inherited gate: equality passes."""

    measurements = {}
    for gate in inherited_gate_definitions(protocol):
        threshold = gate["threshold"]
        measurements[gate["metric"]] = (
            threshold if isinstance(threshold, bool) else str(threshold)
        )
    measurements.update(overrides)
    return {key: value for key, value in measurements.items() if value is not None}


def _bundle(protocol: dict, **overrides) -> dict:
    bundle: dict = {
        "derived_level_review": {
            "observed_disagreements": [],
            "reviews": [],
            "unreviewed_derived_level_disagreement_count": 0,
        },
        "diagnostics": _diagnostics(),
        "gate_pair_measurements": _gate_rows(),
        "identities": {
            "candidate_method_version": "MEDIAN_OHLC_V2",
            "candidate_series_id": "MEDIAN_OHLC_V2",
            "comparison_contract_version": COMPARISON_CONTRACT_VERSION,
            "denominator_semantics_version": DENOMINATOR_SEMANTICS_VERSION,
            "price_source_policy_version": PRICE_SOURCE_POLICY_VERSION,
            "provider_ids": ["bitfinex", "bitstamp", "coinbase"],
            "source_detector_version": WEEKLY_STRUCTURE_DETECTOR_VERSION,
        },
        "inherited_gate_measurements": _inherited_measurements(protocol),
        "not_comparable_accounting": {"unrecorded_not_comparable_event_count": 0},
        "provenance": {
            "evidence_builder_version": "SYNTHETIC_EVIDENCE_BUILDER_V1",
            "measurement_record_digest": "a" * 64,
            "sample_manifest_digest": "b" * 64,
        },
        "sample": {
            "end": SYNTHETIC_END,
            "sample_id": "SYNTHETIC_DRY_RUN",
            "start": SYNTHETIC_START,
        },
        "schema_version": EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "soft_gate_pair_measurements": _soft_rows(),
        "transfer_guard_pair_measurements": _guard_rows(),
    }
    bundle.update(overrides)
    return bundle


def _validate(bundle: dict, **kwargs):
    return validate_v3_candidate(bundle, repository_root=REPOSITORY_ROOT, **kwargs)


# =============================================================================
# 1. binding: the exact frozen hash, and nothing else
# =============================================================================


def test_the_validator_binds_the_exact_frozen_v3_hash(contract: dict) -> None:
    binding = contract["binding"]
    assert binding["bound_protocol_definition_sha256"] == FROZEN_V3_DEFINITION_SHA256
    assert BOUND_PROTOCOL_DEFINITION_SHA256 == FROZEN_V3_DEFINITION_SHA256
    assert binding["bound_protocol_version"] == V3_PROTOCOL_VERSION


def test_the_frozen_definition_recomputes_to_the_bound_hash() -> None:
    protocol = bind_frozen_v3(REPOSITORY_ROOT)
    assert protocol["definition_sha256"] == FROZEN_V3_DEFINITION_SHA256


def test_one_changed_hex_digit_in_the_bound_hash_refuses_to_run(monkeypatch) -> None:
    from btc_predictor.research import reference_composite_v3_validator as module

    tampered = FROZEN_V3_DEFINITION_SHA256[:-1] + (
        "b" if FROZEN_V3_DEFINITION_SHA256[-1] == "a" else "a"
    )
    assert tampered != FROZEN_V3_DEFINITION_SHA256
    monkeypatch.setattr(module, "BOUND_PROTOCOL_DEFINITION_SHA256", tampered)
    with pytest.raises(ValidatorBindingError, match="REFUSE_TO_RUN"):
        bind_frozen_v3(REPOSITORY_ROOT)


def test_binding_to_the_parent_hash_refuses_to_run(monkeypatch) -> None:
    from btc_predictor.research import reference_composite_v3_validator as module

    monkeypatch.setattr(
        module, "BOUND_PROTOCOL_DEFINITION_SHA256", FROZEN_V2_PARENT_SHA256
    )
    with pytest.raises(ValidatorBindingError, match="REFUSE_TO_RUN"):
        bind_frozen_v3(REPOSITORY_ROOT)


def test_a_wrong_parent_hash_refuses_to_run(monkeypatch) -> None:
    from btc_predictor.research import reference_composite_v3_validator as module

    monkeypatch.setattr(
        module, "PARENT_PROTOCOL_DEFINITION_SHA256", "c" * 64
    )
    with pytest.raises(ValidatorBindingError, match="different parent hash"):
        bind_frozen_v3(REPOSITORY_ROOT)


def test_the_validator_never_falls_back_to_a_version_name(monkeypatch) -> None:
    """A definition carrying the right name and the wrong hash still refuses."""

    from btc_predictor.research import reference_composite_v3_validator as module

    def _renamed(root: Path) -> dict:
        payload = dict(v3_protocol_definition(root))
        payload["definition_sha256"] = "d" * 64
        return payload

    monkeypatch.setattr(module, "v3_protocol_definition", _renamed)
    with pytest.raises(ValidatorBindingError, match="REFUSE_TO_RUN"):
        bind_frozen_v3(REPOSITORY_ROOT)


def test_the_bound_parent_is_recorded_and_is_not_the_bound_hash(contract: dict) -> None:
    binding = contract["binding"]
    assert binding["parent_protocol_definition_sha256"] == FROZEN_V2_PARENT_SHA256
    assert PARENT_PROTOCOL_DEFINITION_SHA256 == FROZEN_V2_PARENT_SHA256
    assert binding["parent_protocol_definition_sha256"] != FROZEN_V3_DEFINITION_SHA256


def test_the_bound_definition_may_not_claim_sealed_access(monkeypatch) -> None:
    from btc_predictor.research import reference_composite_v3_validator as module

    def _opened(root: Path) -> dict:
        payload = json.loads(json.dumps(v3_protocol_definition(root)))
        payload["sample_governance"]["sealed_sample"]["opened"] = True
        return payload

    monkeypatch.setattr(module, "v3_protocol_definition", _opened)
    with pytest.raises(ValidatorBindingError, match="sealed-sample access"):
        bind_frozen_v3(REPOSITORY_ROOT)


def test_a_persisted_definition_claiming_collection_refuses(monkeypatch) -> None:
    from btc_predictor.research import reference_composite_v3_validator as module

    def _collected(output_dir: Path) -> dict:
        payload = json.loads(json.dumps(v3_protocol_definition(REPOSITORY_ROOT)))
        payload["sample_governance"]["sealed_sample"]["collected"] = True
        return payload

    monkeypatch.setattr(module, "restore_v3_protocol", _collected)
    with pytest.raises(ValidatorBindingError, match="REFUSE_TO_RUN"):
        bind_frozen_v3(REPOSITORY_ROOT)


def test_the_freeze_and_review_commits_are_recorded(contract: dict) -> None:
    binding = contract["binding"]
    assert binding["freeze_implementation_commit"] == (
        "b60ecc7f36840b429f27a8742b7245d417cf52db"
    )
    assert binding["review_commit"] == "e2df3ce036c0e7045361c871f8d303b51533f18d"
    assert binding["review_result"] == "PASS_WITH_NON_BLOCKING_FINDINGS"


# =============================================================================
# 2. operative field precedence (review finding P2-3)
# =============================================================================


def test_the_structural_gate_uses_the_operative_limit_not_the_frozen_threshold(
    protocol: dict,
) -> None:
    historical = {
        item["metric"]: item["frozen_threshold"]
        for item in protocol["metric_definitions"]
    }
    assert historical[STRUCTURAL_METRIC] == "0.05"
    assert operative_structural_limit(protocol) == Decimal("0.20")


def test_the_historical_frozen_hard_flags_do_not_regain_authority(
    protocol: dict,
) -> None:
    historical = {
        item["metric"]: item["frozen_hard"] for item in protocol["metric_definitions"]
    }
    for metric in DIAGNOSTIC_METRICS:
        assert historical[metric] is True
        assert operative_metric_role(protocol, metric) == ROLE_DIAGNOSTIC
    assert historical[EXACT_TIMESTAMP_METRIC] is False
    assert operative_metric_role(protocol, EXACT_TIMESTAMP_METRIC) == ROLE_SOFT
    assert operative_metric_role(protocol, STRUCTURAL_METRIC) == ROLE_HARD


def test_a_synthetic_definition_carrying_both_values_uses_the_operative_one() -> None:
    synthetic = {
        "gate_architecture": {
            "roles": {
                STRUCTURAL_METRIC: ROLE_HARD,
                "within_1_week_swing_disagreement_rate": ROLE_DIAGNOSTIC,
            },
            "certification_rule": {
                "rule_id": "PER_PAIR_WILSON_UPPER_BOUND_V1",
                "normal_quantile": "1.959963984540054235631",
            },
        },
        "materiality": {
            "absolute_limit": "0.20",
            "applies_to": STRUCTURAL_METRIC,
            "direction": "maximum",
        },
        "metric_definitions": [
            {
                "metric": STRUCTURAL_METRIC,
                "frozen_threshold": "0.05",
                "frozen_hard": True,
            },
            {
                "metric": "within_1_week_swing_disagreement_rate",
                "frozen_threshold": "0.05",
                "frozen_hard": True,
            },
        ],
    }
    assert operative_structural_limit(synthetic) == Decimal("0.20")
    assert (
        operative_metric_role(synthetic, "within_1_week_swing_disagreement_rate")
        == ROLE_DIAGNOSTIC
    )


def test_the_contract_names_the_historical_provenance_fields(contract: dict) -> None:
    precedence = contract["operative_field_precedence"]
    assert precedence["precedence_id"] == (
        "OPERATIVE_V3_FIELDS_OVERRIDE_HISTORICAL_V2_PROVENANCE_V1"
    )
    assert set(precedence["historical_provenance_only_fields"]) == {
        "frozen_direction",
        "frozen_hard",
        "frozen_threshold",
        "frozen_validation_stage",
    }
    assert set(HISTORICAL_PROVENANCE_ONLY_FIELDS) == set(
        precedence["historical_provenance_only_fields"]
    )
    for field in HISTORICAL_PROVENANCE_ONLY_FIELDS:
        assert field not in precedence["operative_v3_authority_fields"]


def test_a_metric_with_no_operative_role_refuses(protocol: dict) -> None:
    with pytest.raises(ValidatorBindingError, match="operative V3 role"):
        operative_metric_role(protocol, "invented_metric")


def test_a_diagnostic_carries_no_operative_threshold(contract: dict) -> None:
    for example in contract["operative_field_precedence"]["examples"]:
        if example["operative_v3_authority"].endswith("DIAGNOSTIC_ONLY"):
            assert example["operative_value_used"].startswith("none")


# =============================================================================
# 3. the Wilson bound, written out (review finding P3-5)
# =============================================================================

_QUANTILE = Decimal("1.959963984540054235631")


def _independent_wilson_upper(numerator: int, denominator: int) -> Decimal:
    """The larger root of (p - U)^2 = z^2 * U(1 - U)/n, at 60 digits.

    Algebraically independent of the module's closed form: it solves the score
    equation rather than evaluating the rearranged expression, so agreement is
    evidence about the formula and not about a shared transcription.
    """

    context = Context(prec=60, rounding=decimal.ROUND_HALF_EVEN)
    n = Decimal(denominator)
    p = context.divide(Decimal(numerator), n)
    z2 = context.power(_QUANTILE, 2)
    # (1 + z^2/n) U^2 - (2p + z^2/n) U + p^2 = 0
    a = context.add(Decimal(1), context.divide(z2, n))
    b = context.add(context.multiply(Decimal(2), p), context.divide(z2, n))
    c = context.power(p, 2)
    discriminant = context.subtract(
        context.power(b, 2), context.multiply(Decimal(4), context.multiply(a, c))
    )
    return context.divide(
        context.add(b, context.sqrt(discriminant)), context.multiply(Decimal(2), a)
    )


def _continuity_corrected_upper(numerator: int, denominator: int) -> Decimal:
    """Newcombe's continuity-corrected Wilson upper limit."""

    context = Context(prec=60, rounding=decimal.ROUND_HALF_EVEN)
    n = Decimal(denominator)
    p = context.divide(Decimal(numerator), n)
    z2 = context.power(_QUANTILE, 2)
    inner = context.add(
        context.subtract(z2, context.divide(Decimal(1), n)),
        context.add(
            context.multiply(
                Decimal(4), context.multiply(n, context.multiply(p, context.subtract(Decimal(1), p)))
            ),
            context.add(context.multiply(Decimal(4), p), Decimal(1)),
        ),
    )
    numerator_term = context.add(
        context.add(context.multiply(Decimal(2), context.multiply(n, p)), z2),
        context.add(Decimal(1), context.multiply(_QUANTILE, context.sqrt(inner))),
    )
    return context.divide(
        numerator_term, context.multiply(Decimal(2), context.add(n, z2))
    )


@pytest.mark.parametrize(
    "numerator,denominator",
    [(0, 15), (0, 16), (1, 24), (1, 25), (2, 32), (2, 33), (3, 39), (3, 40), (2, 28)],
)
def test_the_bound_matches_an_independent_evaluation(
    numerator: int, denominator: int
) -> None:
    module_value = structural_upper_bound(numerator, denominator, quantile=_QUANTILE)
    independent = _independent_wilson_upper(numerator, denominator)
    assert abs(module_value - independent) < Decimal("1e-25")


def test_the_formula_is_the_uncorrected_variant(contract: dict) -> None:
    rule = contract["certification_rule"]
    assert rule["formula_id"] == WILSON_FORMULA_ID == (
        "WILSON_SCORE_UPPER_BOUND_UNCORRECTED_V1"
    )
    assert rule["continuity_correction_applied"] is False
    assert WILSON_CONTINUITY_CORRECTION_APPLIED is False
    assert "p_hat + z^2/(2n)" in rule["formula"]
    assert "1 + z^2/n" in rule["formula"]


def test_the_quantile_is_the_hash_bound_one(protocol: dict, contract: dict) -> None:
    quantile = operative_normal_quantile(protocol)
    assert quantile == _QUANTILE
    assert contract["certification_rule"]["normal_quantile"] == str(_QUANTILE)
    assert contract["certification_rule"]["confidence_level_percent"] == "95"


@pytest.mark.parametrize(
    "numerator,denominator,expected",
    [
        (0, 15, PAIR_INSUFFICIENT_EVIDENCE),
        (0, 16, PAIR_CERTIFIED),
        (1, 24, PAIR_INSUFFICIENT_EVIDENCE),
        (1, 25, PAIR_CERTIFIED),
        (2, 32, PAIR_INSUFFICIENT_EVIDENCE),
        (2, 33, PAIR_CERTIFIED),
        (3, 39, PAIR_INSUFFICIENT_EVIDENCE),
        (3, 40, PAIR_CERTIFIED),
    ],
)
def test_the_frozen_boundary_vectors(
    numerator: int, denominator: int, expected: str
) -> None:
    certification = certify_pair(
        _pair_row("bitfinex_vs_bitstamp", STRUCTURAL_METRIC, numerator, denominator),
        comparison_id="bitfinex_vs_bitstamp",
    )
    assert certification.outcome == expected


def test_the_contract_pins_the_boundary_vectors(contract: dict) -> None:
    persisted = {
        (row["numerator"], row["denominator"]): row["outcome"]
        for row in contract["certification_rule"]["boundary_vectors"]
    }
    assert persisted == {
        (0, 15): PAIR_INSUFFICIENT_EVIDENCE,
        (0, 16): PAIR_CERTIFIED,
        (1, 24): PAIR_INSUFFICIENT_EVIDENCE,
        (1, 25): PAIR_CERTIFIED,
        (2, 32): PAIR_INSUFFICIENT_EVIDENCE,
        (2, 33): PAIR_CERTIFIED,
        (3, 39): PAIR_INSUFFICIENT_EVIDENCE,
        (3, 40): PAIR_CERTIFIED,
    }
    assert [dict(row) for row in WILSON_BOUNDARY_VECTORS] == (
        contract["certification_rule"]["boundary_vectors"]
    )


@pytest.mark.parametrize(
    "numerator,denominator", [(0, 16), (1, 25), (2, 33), (3, 40)]
)
def test_the_continuity_corrected_reading_would_refuse_the_frozen_boundaries(
    numerator: int, denominator: int
) -> None:
    """It is a different rule, so it may not silently substitute."""

    limit = Decimal("0.20")
    assert structural_upper_bound(numerator, denominator, quantile=_QUANTILE) <= limit
    assert _continuity_corrected_upper(numerator, denominator) > limit


def test_the_contract_refuses_the_named_alternative_variants(contract: dict) -> None:
    refused = " ".join(contract["certification_rule"]["refused_variants"])
    assert "continuity-corrected" in refused
    assert "scipy" in refused
    assert "floating point" in refused


def test_equality_certifies_at_the_bound(protocol: dict) -> None:
    """A bound exactly at the limit certifies, matching the frozen convention."""

    assert protocol["gate_architecture"]["certification_rule"][
        "equality_behaviour"
    ].startswith("Equality certifies")


# =============================================================================
# 4. point-rate semantics and exact arithmetic
# =============================================================================


def test_a_point_rate_above_the_limit_is_a_material_failure() -> None:
    certification = certify_pair(
        _pair_row("bitfinex_vs_bitstamp", STRUCTURAL_METRIC, 21, 100),
        comparison_id="bitfinex_vs_bitstamp",
    )
    assert certification.outcome == PAIR_MATERIAL_FAILURE
    assert Fraction(21, 100) > Fraction(1, 5)


def test_a_point_rate_exactly_at_the_limit_is_not_a_material_failure() -> None:
    certification = certify_pair(
        _pair_row("bitfinex_vs_bitstamp", STRUCTURAL_METRIC, 20, 100),
        comparison_id="bitfinex_vs_bitstamp",
    )
    assert certification.outcome == PAIR_INSUFFICIENT_EVIDENCE
    assert Fraction(20, 100) == Fraction(1, 5)


def test_the_point_rate_boundary_is_exact_not_binary_float() -> None:
    """1/5 of a denominator that has no binary representation still ties."""

    for denominator in (5, 10, 25, 50, 200, 1000):
        numerator = denominator // 5
        assert Fraction(numerator, denominator) == Fraction(1, 5)
        certification = certify_pair(
            _pair_row("bitfinex_vs_bitstamp", STRUCTURAL_METRIC, numerator, denominator),
            comparison_id="bitfinex_vs_bitstamp",
        )
        assert certification.outcome != PAIR_MATERIAL_FAILURE


def test_the_contract_pins_the_point_rate_semantics(contract: dict) -> None:
    semantics = contract["certification_rule"]["point_rate_semantics"]
    assert "strictly greater" in semantics
    assert "exactly at the limit is not a material failure" in semantics


# =============================================================================
# 5. zero and thin denominators
# =============================================================================


@pytest.mark.parametrize("denominator", [0, 1, 5, 10, 15])
def test_a_thin_or_zero_denominator_cannot_certify(denominator: int) -> None:
    certification = certify_pair(
        _pair_row("bitfinex_vs_bitstamp", STRUCTURAL_METRIC, 0, denominator),
        comparison_id="bitfinex_vs_bitstamp",
    )
    assert certification.outcome == PAIR_INSUFFICIENT_EVIDENCE
    if denominator == 0:
        assert certification.rate is None
        assert certification.upper_bound is None


def test_sixteen_comparable_events_at_zero_disagreements_certifies() -> None:
    certification = certify_pair(
        _pair_row("bitfinex_vs_bitstamp", STRUCTURAL_METRIC, 0, 16),
        comparison_id="bitfinex_vs_bitstamp",
    )
    assert certification.outcome == PAIR_CERTIFIED


def test_zero_over_zero_is_never_a_rate_of_zero() -> None:
    assert structural_upper_bound(0, 0, quantile=_QUANTILE) is None
    certification = certify_pair(
        _pair_row("bitfinex_vs_bitstamp", STRUCTURAL_METRIC, 0, 0),
        comparison_id="bitfinex_vs_bitstamp",
    )
    assert certification.rate is None
    assert "NO_COMPARABLE_EVENTS" in certification.reason_codes


def test_a_zero_denominator_gate_pair_makes_the_run_insufficient(
    protocol: dict,
) -> None:
    bundle = _bundle(protocol, gate_pair_measurements=_gate_rows(0, 0))
    record = _validate(bundle)
    assert record.verdict == VERDICT_INSUFFICIENT
    assert record.primary_reason == REASON_STRUCTURAL_GATE_INSUFFICIENT


# =============================================================================
# 6. the comparability floor
# =============================================================================


@pytest.mark.parametrize(
    "rate,certifies",
    [("0.49", False), ("0.50", True), ("0.51", True)],
)
def test_the_comparability_floor_is_inclusive(rate: str, certifies: bool) -> None:
    certification = certify_pair(
        _pair_row(
            "bitfinex_vs_bitstamp", STRUCTURAL_METRIC, 0, 40, comparability=rate
        ),
        comparison_id="bitfinex_vs_bitstamp",
    )
    assert (certification.outcome == PAIR_CERTIFIED) is certifies


def test_the_operative_floor_is_the_frozen_one(protocol: dict) -> None:
    assert operative_comparability_floor(protocol) == Decimal("0.50")


def test_comparability_alone_does_not_certify(protocol: dict) -> None:
    """A perfect comparability rate on a thin denominator is still insufficient."""

    bundle = _bundle(
        protocol,
        gate_pair_measurements=_gate_rows(0, 15, comparability="1"),
    )
    record = _validate(bundle)
    assert record.verdict == VERDICT_INSUFFICIENT


def test_a_pair_below_the_floor_makes_the_run_insufficient(protocol: dict) -> None:
    rows = _gate_rows()
    rows[0]["structural_comparability_rate"] = "0.49"
    bundle = _bundle(protocol, gate_pair_measurements=rows)
    record = _validate(bundle)
    assert record.verdict == VERDICT_INSUFFICIENT
    assert REASON_COMPARABILITY_INSUFFICIENT in record.reason_codes


def test_a_null_comparability_rate_is_insufficient_not_satisfied(
    protocol: dict,
) -> None:
    rows = _gate_rows(comparability=None)
    bundle = _bundle(protocol, gate_pair_measurements=rows)
    record = _validate(bundle)
    assert record.verdict == VERDICT_INSUFFICIENT
    block = record.payload["hard_requirements"][REQUIREMENT_COMPARABILITY]
    assert block["outcome"] == GATE_INSUFFICIENT
    assert "NO_DETECTED_EVENTS" in block["pairs"][0]["reason_codes"]


def test_a_pair_that_is_not_established_admissible_cannot_certify() -> None:
    certification = certify_pair(
        _pair_row(
            "bitfinex_vs_bitstamp",
            STRUCTURAL_METRIC,
            0,
            40,
            state=PAIR_INADMISSIBLE,
        ),
        comparison_id="bitfinex_vs_bitstamp",
    )
    assert certification.outcome == PAIR_INSUFFICIENT_EVIDENCE
    assert "PAIR_INADMISSIBLE" in certification.reason_codes


# =============================================================================
# 7. the required pair universe
# =============================================================================


def test_the_required_pair_universe_is_exact(protocol: dict, contract: dict) -> None:
    assert required_gate_pair_ids(protocol) == GATE_PAIRS
    assert required_transfer_guard_pair_ids(protocol) == GUARD_PAIRS
    assert tuple(contract["required_gate_pairs"]) == GATE_PAIRS
    assert tuple(contract["required_transfer_guard_pairs"]) == GUARD_PAIRS


@pytest.mark.parametrize("present", [0, 1, 2])
def test_a_short_gate_pair_list_can_never_pass(protocol: dict, present: int) -> None:
    bundle = _bundle(protocol, gate_pair_measurements=_gate_rows()[:present])
    record = _validate(bundle)
    assert record.verdict == VERDICT_INSUFFICIENT
    assert REASON_REQUIRED_PAIR_UNIVERSE_INCOMPLETE in record.reason_codes


def test_a_duplicated_pair_refuses(protocol: dict) -> None:
    rows = _gate_rows()
    bundle = _bundle(protocol, gate_pair_measurements=rows + [rows[0]])
    with pytest.raises(ValidatorInputError, match="DUPLICATE_PAIR_MEASUREMENT"):
        _validate(bundle)


def test_an_unexpected_pair_refuses(protocol: dict) -> None:
    rows = _gate_rows() + [
        _pair_row("MEDIAN_OHLC_V1_vs_bitstamp", STRUCTURAL_METRIC, 0, 40)
    ]
    bundle = _bundle(protocol, gate_pair_measurements=rows)
    with pytest.raises(ValidatorInputError, match="PAIR_ROLE_MISMATCH"):
        _validate(bundle)


def test_a_guard_pair_in_the_gate_universe_refuses(protocol: dict) -> None:
    rows = _gate_rows() + [
        _pair_row("bitfinex_vs_bitstamp", STRUCTURAL_METRIC, 0, 40)
    ]
    bundle = _bundle(protocol, gate_pair_measurements=rows)
    with pytest.raises(
        ValidatorInputError, match="CANDIDATE_ABSENT_FROM_APPROVAL_GATE_PAIR"
    ):
        _validate(bundle)


def test_the_candidate_may_not_appear_in_a_transfer_guard_pair(protocol: dict) -> None:
    rows = _guard_rows() + [
        _pair_row("MEDIAN_OHLC_V2_vs_bitstamp", STRUCTURAL_METRIC, 0, 40)
    ]
    bundle = _bundle(protocol, transfer_guard_pair_measurements=rows)
    with pytest.raises(
        ValidatorInputError, match="CANDIDATE_PRESENT_IN_TRANSFER_GUARD_PAIR"
    ):
        _validate(bundle)


def test_an_undeclared_provider_identity_refuses(protocol: dict) -> None:
    rows = _gate_rows()
    rows[0] = _pair_row("MEDIAN_OHLC_V2_vs_kraken", STRUCTURAL_METRIC, 0, 40)
    bundle = _bundle(protocol, gate_pair_measurements=rows)
    with pytest.raises(ValidatorInputError, match="PROVIDER_IDENTITY_MISMATCH"):
        _validate(bundle)


def test_a_comparison_id_that_is_not_its_own_canonical_id_refuses(
    protocol: dict,
) -> None:
    rows = _gate_rows()
    rows[0]["comparison_id"] = "MEDIAN_OHLC_V2_vs_bitstamp"
    bundle = _bundle(protocol, gate_pair_measurements=rows)
    with pytest.raises(ValidatorInputError, match="PROVIDER_IDENTITY_MISMATCH"):
        _validate(bundle)


def test_a_pair_measuring_another_metric_refuses(protocol: dict) -> None:
    rows = _gate_rows()
    rows[0]["metric"] = EXACT_TIMESTAMP_METRIC
    bundle = _bundle(protocol, gate_pair_measurements=rows)
    with pytest.raises(ValidatorInputError, match="PAIR_MEASURES_ANOTHER_METRIC"):
        _validate(bundle)


def test_a_declared_pair_purpose_that_contradicts_the_identities_refuses(
    protocol: dict,
) -> None:
    rows = _gate_rows()
    rows[0]["pair_purpose"] = "SOURCE_DISPERSION_CALIBRATION_PAIR"
    bundle = _bundle(protocol, gate_pair_measurements=rows)
    with pytest.raises(ValidatorInputError, match="PAIR_ROLE_MISMATCH"):
        _validate(bundle)


def test_a_pair_missing_its_admissibility_state_refuses(protocol: dict) -> None:
    rows = _gate_rows()
    del rows[0]["state"]
    bundle = _bundle(protocol, gate_pair_measurements=rows)
    with pytest.raises(ValidatorInputError, match="omits required fields"):
        _validate(bundle)


def test_a_pair_missing_its_comparability_rate_refuses(protocol: dict) -> None:
    rows = _gate_rows()
    del rows[0]["structural_comparability_rate"]
    bundle = _bundle(protocol, gate_pair_measurements=rows)
    with pytest.raises(ValidatorInputError, match="omits required fields"):
        _validate(bundle)


def test_an_unknown_pair_field_refuses(protocol: dict) -> None:
    rows = _gate_rows()
    rows[0]["invented_field"] = 1
    bundle = _bundle(protocol, gate_pair_measurements=rows)
    with pytest.raises(ValidatorInputError, match="unknown fields"):
        _validate(bundle)


def test_comparability_counts_must_sum_to_the_detected_total(protocol: dict) -> None:
    rows = _gate_rows()
    rows[0]["all_detected_event_count"] = 999
    bundle = _bundle(protocol, gate_pair_measurements=rows)
    with pytest.raises(ValidatorInputError, match="do not sum"):
        _validate(bundle)


def test_a_numerator_above_its_denominator_refuses(protocol: dict) -> None:
    rows = _gate_rows(numerator=41, denominator=40)
    bundle = _bundle(protocol, gate_pair_measurements=rows)
    with pytest.raises(ValidatorInputError, match="exceeds its denominator"):
        _validate(bundle)


# =============================================================================
# 8. pair identity versus ordering
# =============================================================================


def test_the_canonical_pair_id_is_order_independent() -> None:
    assert canonical_pair_id(["coinbase", "bitstamp"]) == "bitstamp_vs_coinbase"
    assert canonical_pair_id(["bitstamp", "coinbase"]) == "bitstamp_vs_coinbase"


def test_a_pair_of_one_series_with_itself_refuses() -> None:
    with pytest.raises(ValidatorInputError, match="two distinct series"):
        canonical_pair_id(["bitstamp", "bitstamp"])


def test_reordering_pairs_cannot_change_the_record(protocol: dict) -> None:
    straight = _validate(_bundle(protocol))
    shuffled = _bundle(
        protocol,
        gate_pair_measurements=list(reversed(_gate_rows())),
        transfer_guard_pair_measurements=list(reversed(_guard_rows())),
        soft_gate_pair_measurements=list(reversed(_soft_rows())),
    )
    assert _validate(shuffled).as_record() == straight.as_record()


def test_reversing_a_series_pair_cannot_change_the_record(protocol: dict) -> None:
    rows = _gate_rows()
    rows[0]["series_pair"] = list(reversed(rows[0]["series_pair"]))
    reversed_record = _validate(_bundle(protocol, gate_pair_measurements=rows))
    assert reversed_record.as_record() == _validate(_bundle(protocol)).as_record()


def test_swapping_data_between_provider_identities_is_different_evidence(
    protocol: dict,
) -> None:
    """Order does not matter; identity does."""

    rows = _gate_rows()
    bitstamp = next(row for row in rows if "bitstamp" in row["comparison_id"])
    coinbase = next(row for row in rows if "coinbase" in row["comparison_id"])
    bitstamp["numerator"], coinbase["numerator"] = 3, 0
    swapped = _gate_rows()
    bitstamp2 = next(row for row in swapped if "bitstamp" in row["comparison_id"])
    coinbase2 = next(row for row in swapped if "coinbase" in row["comparison_id"])
    bitstamp2["numerator"], coinbase2["numerator"] = 0, 3
    first = evidence_bundle_digest(_bundle(protocol, gate_pair_measurements=rows))
    second = evidence_bundle_digest(_bundle(protocol, gate_pair_measurements=swapped))
    assert first != second


def test_reordering_reason_codes_cannot_change_a_digest(protocol: dict) -> None:
    rows = _gate_rows()
    rows[0]["reason_codes"] = ["B_CODE", "A_CODE"]
    other = _gate_rows()
    other[0]["reason_codes"] = ["A_CODE", "B_CODE"]
    assert evidence_bundle_digest(
        _bundle(protocol, gate_pair_measurements=rows)
    ) == evidence_bundle_digest(_bundle(protocol, gate_pair_measurements=other))


# =============================================================================
# 9. the transfer guard
# =============================================================================


def test_all_three_provider_pairs_are_required(protocol: dict, contract: dict) -> None:
    guard = next(
        item
        for item in contract["hard_requirements"]
        if item["requirement"] == REQUIREMENT_TRANSFER_GUARD
    )
    assert guard["evaluated_on"] == list(GUARD_PAIRS)
    assert guard["rule_id"] == "RAW_PROVIDER_STRUCTURAL_DISPERSION_CEILING_V1"


def test_the_guard_is_satisfied_when_every_provider_pair_certifies(
    protocol: dict,
) -> None:
    record = _validate(_bundle(protocol))
    guard = record.payload["hard_requirements"][REQUIREMENT_TRANSFER_GUARD]
    assert guard["outcome"] == GATE_PASS
    assert guard["candidate_data_enters_the_guard"] is False


def test_one_failing_provider_pair_fails_the_guard(protocol: dict) -> None:
    rows = _guard_rows()
    rows[0]["numerator"] = 21
    rows[0]["denominator"] = 100
    rows[0]["comparable_event_count"] = 100
    rows[0]["candidate_event_count"] = 100
    rows[0]["all_detected_event_count"] = 100
    record = _validate(_bundle(protocol, transfer_guard_pair_measurements=rows))
    assert record.verdict == VERDICT_FAIL
    assert record.primary_reason == REASON_TRANSFER_GUARD_FAILED


def test_one_insufficient_provider_pair_leaves_the_guard_undefined(
    protocol: dict,
) -> None:
    rows = _guard_rows()
    rows[0]["numerator"] = 2
    rows[0]["denominator"] = 28
    rows[0]["comparable_event_count"] = 28
    rows[0]["candidate_event_count"] = 28
    rows[0]["all_detected_event_count"] = 28
    record = _validate(_bundle(protocol, transfer_guard_pair_measurements=rows))
    assert record.verdict == VERDICT_INSUFFICIENT
    assert record.primary_reason == REASON_TRANSFER_GUARD_UNDEFINED


def test_a_missing_provider_pair_leaves_the_guard_undefined(protocol: dict) -> None:
    record = _validate(
        _bundle(protocol, transfer_guard_pair_measurements=_guard_rows()[:2])
    )
    assert record.verdict == VERDICT_INSUFFICIENT
    guard = record.payload["hard_requirements"][REQUIREMENT_TRANSFER_GUARD]
    assert guard["outcome"] == GATE_INSUFFICIENT


def test_the_accepted_guard_risk_is_preserved_not_weakened(protocol: dict) -> None:
    """2/28 is the development observation. It stays unresolved by design."""

    assert structural_upper_bound(2, 28, quantile=_QUANTILE) > Decimal("0.20")
    certification = certify_pair(
        _pair_row("bitfinex_vs_bitstamp", STRUCTURAL_METRIC, 2, 28),
        comparison_id="bitfinex_vs_bitstamp",
    )
    assert certification.outcome == PAIR_INSUFFICIENT_EVIDENCE
    assert operative_structural_limit(protocol) == Decimal("0.20")


def test_the_guard_reads_no_candidate_measurement(protocol: dict) -> None:
    """Moving every candidate pair leaves the guard's own outcome untouched."""

    baseline = _validate(_bundle(protocol)).payload["hard_requirements"][
        REQUIREMENT_TRANSFER_GUARD
    ]
    moved = _validate(
        _bundle(protocol, gate_pair_measurements=_gate_rows(21, 100))
    ).payload["hard_requirements"][REQUIREMENT_TRANSFER_GUARD]
    assert moved == baseline


# =============================================================================
# 10. the NOT_COMPARABLE completeness requirement
# =============================================================================


def test_a_zero_unrecorded_count_satisfies_the_requirement(protocol: dict) -> None:
    record = _validate(_bundle(protocol))
    block = record.payload["hard_requirements"][REQUIREMENT_NOT_COMPARABLE]
    assert block["outcome"] == GATE_PASS
    assert block["threshold"] == 0
    assert block["direction"] == "equal"


def test_a_positive_unrecorded_count_is_a_hard_failure(protocol: dict) -> None:
    bundle = _bundle(
        protocol,
        not_comparable_accounting={"unrecorded_not_comparable_event_count": 1},
    )
    record = _validate(bundle)
    assert record.verdict == VERDICT_FAIL
    assert REASON_UNRECORDED_NOT_COMPARABLE_EVENTS in record.reason_codes


def test_a_missing_unrecorded_count_is_insufficient(protocol: dict) -> None:
    bundle = _bundle(
        protocol,
        not_comparable_accounting={"unrecorded_not_comparable_event_count": None},
    )
    record = _validate(bundle)
    assert record.verdict == VERDICT_INSUFFICIENT
    assert REASON_NOT_COMPARABLE_ACCOUNTING_MISSING in record.reason_codes


def test_the_not_comparable_requirement_matches_the_frozen_structured_gate(
    protocol: dict, contract: dict
) -> None:
    frozen = protocol["not_comparable_semantics"][
        "unrecorded_not_comparable_event_count"
    ]
    assert frozen == {"direction": "equal", "hard": True, "threshold": 0}
    handling = contract["not_comparable_handling"]
    assert handling["zero_count"] == VERDICT_PASS
    assert handling["positive_count"] == VERDICT_FAIL
    assert handling["missing_count"] == VERDICT_INSUFFICIENT


def test_the_not_comparable_requirement_is_in_the_composition(contract: dict) -> None:
    """The reference approval_verdict has no parameter for it; this does."""

    assert REQUIREMENT_NOT_COMPARABLE in HARD_REQUIREMENT_IDS
    assert REQUIREMENT_NOT_COMPARABLE in contract["composition"][
        "hard_requirement_ids"
    ]
    assert REQUIREMENT_NOT_COMPARABLE in REQUIREMENTS_THAT_CAN_FAIL


def test_a_negative_unrecorded_count_refuses(protocol: dict) -> None:
    bundle = _bundle(
        protocol,
        not_comparable_accounting={"unrecorded_not_comparable_event_count": -1},
    )
    with pytest.raises(ValidatorInputError, match="cannot be negative"):
        _validate(bundle)


# =============================================================================
# 11. derived-level review completeness, and review as evidence not opinion
# =============================================================================


def _disagreement(comparison_id: str, event_id: str, family: str = "breakout") -> dict:
    return {
        "comparison_id": comparison_id,
        "event_id": event_id,
        "family": family,
        "week": "2024-03-04",
    }


def _review(comparison_id: str, event_id: str, family: str = "breakout", **overrides):
    record = {
        "comparison_id": comparison_id,
        "economic_assessment": "no downstream consequence observed",
        "event_id": event_id,
        "family": family,
        "reviewed_at": "2026-01-01T00:00:00+00:00",
        "reviewer": "analyst",
        "week": "2024-03-04",
    }
    record.update(overrides)
    return record


def _with_one_disagreement(protocol: dict, *, reviewed: bool, **review_overrides):
    pair = GATE_PAIRS[0]
    reviews = [_review(pair, "E1", **review_overrides)] if reviewed else []
    return _bundle(
        protocol,
        derived_level_review={
            "observed_disagreements": [_disagreement(pair, "E1")],
            "reviews": reviews,
            "unreviewed_derived_level_disagreement_count": 0 if reviewed else 1,
        },
        diagnostics=_diagnostics(breakout_disagreement_rate={pair: 1}),
    )


def test_an_unreviewed_derived_level_disagreement_cannot_pass(protocol: dict) -> None:
    record = _validate(_with_one_disagreement(protocol, reviewed=False))
    assert record.verdict == VERDICT_INSUFFICIENT
    assert REASON_DERIVED_LEVEL_REVIEW_INCOMPLETE in record.reason_codes


def test_a_complete_review_record_satisfies_completeness(protocol: dict) -> None:
    record = _validate(_with_one_disagreement(protocol, reviewed=True))
    assert record.verdict == VERDICT_PASS
    block = record.payload["hard_requirements"][REQUIREMENT_DERIVED_LEVEL_REVIEW]
    assert block["reviewed_event_count"] == 1
    assert block["recomputed_unreviewed_count"] == 0


def test_a_missing_derived_level_block_is_insufficient(protocol: dict) -> None:
    record = _validate(_bundle(protocol, derived_level_review={}))
    assert record.verdict == VERDICT_INSUFFICIENT
    assert REASON_DERIVED_LEVEL_REVIEW_INCOMPLETE in record.reason_codes


def test_a_missing_unreviewed_count_is_insufficient(protocol: dict) -> None:
    bundle = _bundle(
        protocol,
        derived_level_review={
            "observed_disagreements": [],
            "reviews": [],
            "unreviewed_derived_level_disagreement_count": None,
        },
    )
    record = _validate(bundle)
    assert record.verdict == VERDICT_INSUFFICIENT


def test_an_incomplete_review_record_does_not_review_anything(protocol: dict) -> None:
    pair = GATE_PAIRS[0]
    review = _review(pair, "E1")
    del review["economic_assessment"]
    bundle = _bundle(
        protocol,
        derived_level_review={
            "observed_disagreements": [_disagreement(pair, "E1")],
            "reviews": [review],
            "unreviewed_derived_level_disagreement_count": 1,
        },
        diagnostics=_diagnostics(breakout_disagreement_rate={pair: 1}),
    )
    record = _validate(bundle)
    assert record.verdict == VERDICT_INSUFFICIENT


def test_a_review_with_no_reviewer_does_not_review_anything(protocol: dict) -> None:
    pair = GATE_PAIRS[0]
    bundle = _bundle(
        protocol,
        derived_level_review={
            "observed_disagreements": [_disagreement(pair, "E1")],
            "reviews": [_review(pair, "E1", reviewer="")],
            "unreviewed_derived_level_disagreement_count": 1,
        },
        diagnostics=_diagnostics(breakout_disagreement_rate={pair: 1}),
    )
    assert _validate(bundle).verdict == VERDICT_INSUFFICIENT


def test_a_review_naming_an_event_the_census_does_not_hold_refuses(
    protocol: dict,
) -> None:
    pair = GATE_PAIRS[0]
    bundle = _bundle(
        protocol,
        derived_level_review={
            "observed_disagreements": [],
            "reviews": [_review(pair, "GHOST")],
            "unreviewed_derived_level_disagreement_count": 0,
        },
    )
    with pytest.raises(ValidatorInputError, match="census does not"):
        _validate(bundle)


def test_a_declared_count_that_contradicts_the_records_refuses(
    protocol: dict,
) -> None:
    pair = GATE_PAIRS[0]
    bundle = _bundle(
        protocol,
        derived_level_review={
            "observed_disagreements": [_disagreement(pair, "E1")],
            "reviews": [],
            "unreviewed_derived_level_disagreement_count": 0,
        },
        diagnostics=_diagnostics(breakout_disagreement_rate={pair: 1}),
    )
    with pytest.raises(ValidatorInputError, match="disagrees with the census"):
        _validate(bundle)


def test_a_census_naming_a_pair_outside_the_universe_refuses(protocol: dict) -> None:
    bundle = _bundle(
        protocol,
        derived_level_review={
            "observed_disagreements": [_disagreement("bitfinex_vs_bitstamp", "E1")],
            "reviews": [],
            "unreviewed_derived_level_disagreement_count": 1,
        },
    )
    with pytest.raises(ValidatorInputError, match="not a required gate pair"):
        _validate(bundle)


def test_a_duplicated_census_entry_refuses(protocol: dict) -> None:
    pair = GATE_PAIRS[0]
    bundle = _bundle(
        protocol,
        derived_level_review={
            "observed_disagreements": [
                _disagreement(pair, "E1"),
                _disagreement(pair, "E1"),
            ],
            "reviews": [],
            "unreviewed_derived_level_disagreement_count": 2,
        },
    )
    with pytest.raises(ValidatorInputError, match="twice"):
        _validate(bundle)


@pytest.mark.parametrize(
    "assessment",
    [
        "the candidate is clearly unfit and must be rejected",
        "excellent, approve immediately",
    ],
)
def test_free_text_review_opinion_cannot_move_the_verdict(
    protocol: dict, assessment: str
) -> None:
    neutral = _validate(_with_one_disagreement(protocol, reviewed=True))
    opinionated = _validate(
        _with_one_disagreement(
            protocol, reviewed=True, economic_assessment=assessment
        )
    )
    assert opinionated.verdict == neutral.verdict == VERDICT_PASS
    assert opinionated.reason_codes == neutral.reason_codes


def test_a_positive_review_cannot_rescue_a_hard_failure(protocol: dict) -> None:
    pair = GATE_PAIRS[0]
    bundle = _bundle(
        protocol,
        gate_pair_measurements=_gate_rows(21, 100),
        derived_level_review={
            "observed_disagreements": [_disagreement(pair, "E1")],
            "reviews": [
                _review(pair, "E1", economic_assessment="entirely harmless, approve")
            ],
            "unreviewed_derived_level_disagreement_count": 0,
        },
        diagnostics=_diagnostics(breakout_disagreement_rate={pair: 1}),
    )
    record = _validate(bundle)
    assert record.verdict == VERDICT_FAIL
    assert record.primary_reason == REASON_STRUCTURAL_GATE_MATERIAL_FAILURE


def test_the_contract_states_that_review_is_completeness_not_scoring(
    contract: dict,
) -> None:
    block = next(
        item
        for item in contract["hard_requirements"]
        if item["requirement"] == REQUIREMENT_DERIVED_LEVEL_REVIEW
    )
    assert "never reads the reviewer's prose" in block["manual_review_semantics"]
    assert block["can_fail"] is False


# =============================================================================
# 12. the derived-level census is verified against the diagnostics
# =============================================================================


def test_the_census_must_match_the_breakout_and_reclaim_diagnostics(
    protocol: dict,
) -> None:
    pair = GATE_PAIRS[0]
    bundle = _bundle(
        protocol,
        diagnostics=_diagnostics(breakout_disagreement_rate={pair: 2}),
    )
    record = _validate(bundle)
    assert record.verdict == VERDICT_INSUFFICIENT
    block = record.payload["hard_requirements"][REQUIREMENT_DERIVED_LEVEL_REVIEW]
    assert block["census_verified"] is False
    assert CENSUS_REASON_DISAGREES in block["reason_codes"]


def test_a_census_mismatch_names_the_pair_and_family(protocol: dict) -> None:
    pair = GATE_PAIRS[2]
    bundle = _bundle(
        protocol,
        diagnostics=_diagnostics(reclaim_disagreement_rate={pair: 4}),
    )
    block = _validate(bundle).payload["hard_requirements"][
        REQUIREMENT_DERIVED_LEVEL_REVIEW
    ]
    assert block["census_disagreements"] == [f"{pair}:reclaim"]


def test_absent_diagnostics_leave_the_census_unverifiable(protocol: dict) -> None:
    record = _validate(_bundle(protocol, diagnostics={}))
    assert record.verdict == VERDICT_INSUFFICIENT
    block = record.payload["hard_requirements"][REQUIREMENT_DERIVED_LEVEL_REVIEW]
    assert CENSUS_REASON_NOT_VERIFIABLE in block["reason_codes"]


def test_a_diagnostic_row_without_a_count_leaves_the_census_unverifiable(
    protocol: dict,
) -> None:
    diagnostics = _diagnostics()
    del diagnostics["breakout_disagreement_rate"][0]["count"]
    record = _validate(_bundle(protocol, diagnostics=diagnostics))
    assert record.verdict == VERDICT_INSUFFICIENT


def test_a_duplicated_diagnostic_row_leaves_the_census_unverifiable(
    protocol: dict,
) -> None:
    diagnostics = _diagnostics()
    diagnostics["reclaim_disagreement_rate"].append(
        dict(diagnostics["reclaim_disagreement_rate"][0])
    )
    counts, reasons = observed_derived_level_counts(
        diagnostics, required_ids=GATE_PAIRS
    )
    assert counts is None
    assert reasons == [CENSUS_REASON_NOT_VERIFIABLE]


def test_a_verified_census_publishes_its_counts(protocol: dict) -> None:
    counts, reasons = observed_derived_level_counts(
        _diagnostics(reclaim_disagreement_rate={GATE_PAIRS[1]: 3}),
        required_ids=GATE_PAIRS,
    )
    assert reasons == []
    assert counts[(GATE_PAIRS[1], "reclaim")] == 3
    assert counts[(GATE_PAIRS[0], "breakout")] == 0


def test_the_census_rule_is_part_of_the_contract(contract: dict) -> None:
    block = next(
        item
        for item in contract["hard_requirements"]
        if item["requirement"] == REQUIREMENT_DERIVED_LEVEL_REVIEW
    )
    assert block["census_verification"] == CENSUS_VERIFICATION_RULE
    assert "never a diagnostic *rate*" in CENSUS_VERIFICATION_RULE


# =============================================================================
# 13. the soft gate warns and never vetoes
# =============================================================================


def test_the_soft_gate_is_ok_when_every_pair_is_below_the_limit(
    protocol: dict,
) -> None:
    record = _validate(_bundle(protocol))
    assert record.payload["soft_gate"]["outcome"] == SOFT_OUTCOME_OK
    assert record.verdict == VERDICT_PASS


def test_a_soft_gate_warning_cannot_reject(protocol: dict) -> None:
    warned = _validate(
        _bundle(protocol, soft_gate_pair_measurements=_soft_rows(60, 100))
    )
    assert warned.payload["soft_gate"]["outcome"] == SOFT_OUTCOME_REVIEW_REQUIRED
    assert warned.verdict == VERDICT_PASS


def test_undefined_soft_evidence_warns_rather_than_reading_ok(protocol: dict) -> None:
    record = _validate(_bundle(protocol, soft_gate_pair_measurements=_soft_rows()[:1]))
    assert record.payload["soft_gate"]["outcome"] == SOFT_OUTCOME_REVIEW_REQUIRED
    assert record.verdict == VERDICT_PASS


def test_the_soft_gate_is_not_a_composition_parameter(
    protocol: dict, contract: dict
) -> None:
    assert contract["soft_requirements"]["enters_the_hard_composition"] is False
    quiet = _validate(_bundle(protocol))
    loud = _validate(
        _bundle(protocol, soft_gate_pair_measurements=_soft_rows(99, 100))
    )
    assert loud.payload["composition"] == quiet.payload["composition"]


# =============================================================================
# 14. diagnostics are published and cannot veto
# =============================================================================


def test_extreme_diagnostic_rates_cannot_change_the_verdict(protocol: dict) -> None:
    extreme = _diagnostics()
    for metric in DIAGNOSTIC_METRICS:
        for row in extreme[metric]:
            row["rate"] = "0.99"
    quiet = _validate(_bundle(protocol))
    noisy = _validate(_bundle(protocol, diagnostics=extreme))
    assert noisy.verdict == quiet.verdict == VERDICT_PASS
    assert noisy.payload["composition"] == quiet.payload["composition"]


def test_the_within_n_diagnostics_never_reach_the_census(protocol: dict) -> None:
    """Only breakout and reclaim are derived levels."""

    diagnostics = _diagnostics(
        within_1_week_swing_disagreement_rate={GATE_PAIRS[0]: 9},
        within_2_week_swing_disagreement_rate={GATE_PAIRS[0]: 9},
    )
    assert _validate(_bundle(protocol, diagnostics=diagnostics)).verdict == VERDICT_PASS


def test_diagnostics_are_published_with_their_required_fields(protocol: dict) -> None:
    record = _validate(_bundle(protocol))
    diagnostics = record.payload["diagnostics"]
    assert diagnostics["complete"] is True
    assert diagnostics["can_veto_approval"] is False
    assert diagnostics["enter_the_hard_composition"] is False
    assert set(diagnostics["metrics"]) == set(DIAGNOSTIC_METRICS)


def test_an_incomplete_diagnostic_record_is_recorded_not_hidden(
    protocol: dict,
) -> None:
    diagnostics = _diagnostics()
    del diagnostics["within_1_week_swing_disagreement_rate"][0]["rate"]
    record = _validate(_bundle(protocol, diagnostics=diagnostics))
    assert record.payload["diagnostics"]["complete"] is False
    assert record.verdict == VERDICT_PASS


def test_an_unknown_diagnostic_metric_is_recorded_as_incomplete(
    protocol: dict,
) -> None:
    diagnostics = _diagnostics()
    diagnostics["invented_diagnostic"] = []
    record = _validate(_bundle(protocol, diagnostics=diagnostics))
    assert "DIAGNOSTIC_UNKNOWN_METRIC" in record.payload["diagnostics"]["reason_codes"]


# =============================================================================
# 15. the inherited Tier-4 gates
# =============================================================================


def test_the_inherited_census_is_thirty_three_gates(protocol: dict) -> None:
    gates = inherited_gate_definitions(protocol)
    assert len(gates) == INHERITED_GATE_COUNT == 33
    assert sum(1 for gate in gates if gate["hard"]) == INHERITED_HARD_GATE_COUNT == 29
    assert sum(1 for gate in gates if not gate["hard"]) == INHERITED_SOFT_GATE_COUNT == 4


def test_the_thirteen_named_tier4_hard_gates_are_exact(protocol: dict) -> None:
    expected = {
        "cross_market_confirmed_stop_preservation_rate",
        "gap_through_stop_consensus_agreement_rate",
        "isolated_venue_stop_suppression_rate",
        "mae_median_absolute_difference",
        "mae_p95_absolute_difference",
        "mfe_median_absolute_difference",
        "mfe_p95_absolute_difference",
        "regime_classification_disagreement_rate",
        "risk_size_p95_relative_difference",
        "setup_classification_disagreement_rate",
        "stop_touch_disagreement_rate",
        "trade_action_disagreement_rate",
        "trade_eligibility_disagreement_rate",
    }
    assert set(INHERITED_TIER4_HARD_GATES) == expected
    assert len(expected) == 13
    hard = {gate["metric"] for gate in inherited_gate_definitions(protocol) if gate["hard"]}
    assert expected <= hard


def test_the_gates_carry_their_frozen_thresholds_and_directions(
    protocol: dict, contract: dict
) -> None:
    frozen = {item["metric"]: item for item in protocol["inherited_approval_gates"]}
    for gate in contract["tier4_inheritance"]["gates"]:
        source = frozen[gate["metric"]]
        assert gate["threshold"] == source["threshold"]
        assert gate["direction"] == source["direction"]
        assert gate["hard"] == source["hard"]


def test_the_gates_are_bound_to_their_source_versions(contract: dict) -> None:
    bound = contract["tier4_inheritance"]["bound_source"]
    assert bound["bound_protocol_definition_sha256"] == FROZEN_V3_DEFINITION_SHA256
    assert bound["comparison_contract_version"] == COMPARISON_CONTRACT_VERSION
    assert bound["source_detector_version"] == WEEKLY_STRUCTURE_DETECTOR_VERSION
    assert bound["measurement_owner_policy_version"] == PRICE_SOURCE_POLICY_VERSION


@pytest.mark.parametrize(
    "metric,value",
    [
        ("stop_touch_disagreement_rate", "0.02"),
        ("cross_market_confirmed_stop_preservation_rate", "0.99"),
        ("mfe_median_absolute_difference", "0.003"),
        ("mae_p95_absolute_difference", "0.02"),
        ("setup_classification_disagreement_rate", "0.02"),
        ("point_in_time_violation_count", "1"),
        ("deterministic_rerun_hash_match", False),
    ],
)
def test_one_violated_inherited_hard_gate_fails_the_run(
    protocol: dict, metric: str, value
) -> None:
    bundle = _bundle(
        protocol,
        inherited_gate_measurements=_inherited_measurements(protocol, **{metric: value}),
    )
    record = _validate(bundle)
    assert record.verdict == VERDICT_FAIL
    assert record.primary_reason == REASON_INHERITED_HARD_GATE_FAILED
    block = record.payload["hard_requirements"][REQUIREMENT_INHERITED_GATES]
    assert metric in block["failing_hard_gates"]


@pytest.mark.parametrize("metric", list(INHERITED_TIER4_HARD_GATES))
def test_every_named_tier4_hard_gate_can_fail_the_run(
    protocol: dict, metric: str
) -> None:
    gates = {gate["metric"]: gate for gate in inherited_gate_definitions(protocol)}
    threshold = Decimal(str(gates[metric]["threshold"]))
    breach = (
        threshold + Decimal("0.5")
        if gates[metric]["direction"] == "maximum"
        else threshold - Decimal("0.5")
    )
    bundle = _bundle(
        protocol,
        inherited_gate_measurements=_inherited_measurements(
            protocol, **{metric: str(breach)}
        ),
    )
    assert _validate(bundle).verdict == VERDICT_FAIL


def test_a_missing_inherited_hard_gate_is_insufficient(protocol: dict) -> None:
    bundle = _bundle(
        protocol,
        inherited_gate_measurements=_inherited_measurements(
            protocol, stop_touch_disagreement_rate=None
        ),
    )
    record = _validate(bundle)
    assert record.verdict == VERDICT_INSUFFICIENT
    assert record.primary_reason == REASON_INHERITED_GATE_EVIDENCE_MISSING


def test_a_missing_inherited_soft_gate_cannot_veto(protocol: dict) -> None:
    bundle = _bundle(
        protocol,
        inherited_gate_measurements=_inherited_measurements(
            protocol, venue_disagreement_rate=None, mfe_max_absolute_difference=None
        ),
    )
    assert _validate(bundle).verdict == VERDICT_PASS


def test_a_violated_inherited_soft_gate_cannot_veto(protocol: dict) -> None:
    bundle = _bundle(
        protocol,
        inherited_gate_measurements=_inherited_measurements(
            protocol, venue_disagreement_rate="0.99", reference_degraded_rate="0.99"
        ),
    )
    record = _validate(bundle)
    assert record.verdict == VERDICT_PASS
    block = record.payload["hard_requirements"][REQUIREMENT_INHERITED_GATES]
    assert block["soft_gates_can_veto"] is False
    assert not block["failing_hard_gates"]


def test_equality_passes_every_inherited_direction(protocol: dict) -> None:
    """The measurement equals the threshold on all 33 gates in the base bundle."""

    record = _validate(_bundle(protocol))
    block = record.payload["hard_requirements"][REQUIREMENT_INHERITED_GATES]
    assert block["outcome"] == GATE_PASS
    assert {row["verdict"] for row in block["gates"]} == {GATE_PASS}


def test_an_inherited_measurement_the_definition_does_not_carry_refuses(
    protocol: dict,
) -> None:
    bundle = _bundle(
        protocol,
        inherited_gate_measurements=_inherited_measurements(
            protocol, invented_tier4_gate="0.01"
        ),
    )
    with pytest.raises(ValidatorInputError, match="does not inherit"):
        _validate(bundle)


def test_a_boolean_gate_refuses_a_numeric_measurement(protocol: dict) -> None:
    bundle = _bundle(
        protocol,
        inherited_gate_measurements=_inherited_measurements(
            protocol, deterministic_rerun_hash_match="1"
        ),
    )
    with pytest.raises(ValidatorInputError, match="boolean gate"):
        _validate(bundle)


def test_a_numeric_gate_refuses_a_boolean_measurement(protocol: dict) -> None:
    bundle = _bundle(
        protocol,
        inherited_gate_measurements=_inherited_measurements(
            protocol, stop_touch_disagreement_rate=True
        ),
    )
    with pytest.raises(ValidatorInputError, match="cannot take a boolean"):
        _validate(bundle)


def test_a_binary_float_measurement_refuses(protocol: dict) -> None:
    bundle = _bundle(
        protocol,
        inherited_gate_measurements=_inherited_measurements(
            protocol, stop_touch_disagreement_rate=0.01
        ),
    )
    with pytest.raises(ValidatorInputError, match="binary float"):
        _validate(bundle)


def test_the_validator_does_not_rederive_a_tier4_formula(contract: dict) -> None:
    parity = contract["tier4_inheritance"]["comparison_convention"]
    assert "never rederives" in parity
    assert "maximum: value <= threshold passes" in parity
    assert PRICE_SOURCE_POLICY_VERSION in parity


def test_the_inherited_gates_are_not_inferred_from_roadmap_prose(
    contract: dict, protocol: dict
) -> None:
    persisted = {gate["metric"] for gate in contract["tier4_inheritance"]["gates"]}
    frozen = {gate["metric"] for gate in protocol["inherited_approval_gates"]}
    assert persisted == frozen


# =============================================================================
# 16. the composed approval function and its precedence
# =============================================================================


def test_the_verdict_vocabulary_is_the_frozen_one(
    protocol: dict, contract: dict
) -> None:
    frozen = protocol["gate_architecture"]["aggregation"]["verdicts"]
    assert set(VERDICT_VOCABULARY) == set(frozen)
    assert contract["verdict_vocabulary"] == list(VERDICT_VOCABULARY)
    assert VERDICT_VOCABULARY == ("PASS", "FAIL", "UNDEFINED_INSUFFICIENT_EVIDENCE")


def test_all_hard_evidence_passing_gives_pass(protocol: dict) -> None:
    record = _validate(_bundle(protocol))
    assert record.verdict == VERDICT_PASS
    assert record.primary_reason == REASON_ALL_HARD_REQUIREMENTS_SATISFIED
    assert set(record.payload["hard_requirement_outcomes"].values()) == {GATE_PASS}


def test_a_structural_material_failure_gives_fail(protocol: dict) -> None:
    record = _validate(_bundle(protocol, gate_pair_measurements=_gate_rows(21, 100)))
    assert record.verdict == VERDICT_FAIL
    assert record.primary_reason == REASON_STRUCTURAL_GATE_MATERIAL_FAILURE


def test_a_thin_structural_denominator_gives_insufficient(protocol: dict) -> None:
    record = _validate(_bundle(protocol, gate_pair_measurements=_gate_rows(0, 15)))
    assert record.verdict == VERDICT_INSUFFICIENT
    assert record.primary_reason == REASON_STRUCTURAL_GATE_INSUFFICIENT


def test_material_failure_outranks_a_guard_that_is_undefined(protocol: dict) -> None:
    guard = _guard_rows()[:2]
    record = _validate(
        _bundle(
            protocol,
            gate_pair_measurements=_gate_rows(21, 100),
            transfer_guard_pair_measurements=guard,
        )
    )
    assert record.verdict == VERDICT_FAIL
    assert record.primary_reason == REASON_STRUCTURAL_GATE_MATERIAL_FAILURE


def test_a_guard_failure_outranks_a_structural_insufficiency(protocol: dict) -> None:
    guard = _guard_rows()
    guard[0].update(
        numerator=21,
        denominator=100,
        comparable_event_count=100,
        candidate_event_count=100,
        all_detected_event_count=100,
    )
    record = _validate(
        _bundle(
            protocol,
            gate_pair_measurements=_gate_rows(0, 15),
            transfer_guard_pair_measurements=guard,
        )
    )
    assert record.verdict == VERDICT_FAIL
    assert record.primary_reason == REASON_TRANSFER_GUARD_FAILED


def test_a_tier4_failure_outranks_a_structural_insufficiency(protocol: dict) -> None:
    record = _validate(
        _bundle(
            protocol,
            gate_pair_measurements=_gate_rows(0, 15),
            inherited_gate_measurements=_inherited_measurements(
                protocol, stop_touch_disagreement_rate="0.5"
            ),
        )
    )
    assert record.verdict == VERDICT_FAIL
    assert record.primary_reason == REASON_INHERITED_HARD_GATE_FAILED


def test_an_unrecorded_not_comparable_violation_outranks_a_missing_pair(
    protocol: dict,
) -> None:
    record = _validate(
        _bundle(
            protocol,
            gate_pair_measurements=_gate_rows()[:2],
            not_comparable_accounting={"unrecorded_not_comparable_event_count": 4},
        )
    )
    assert record.verdict == VERDICT_FAIL
    assert record.primary_reason == REASON_UNRECORDED_NOT_COMPARABLE_EVENTS


def test_an_incomplete_review_with_a_material_failure_still_fails(
    protocol: dict,
) -> None:
    pair = GATE_PAIRS[0]
    record = _validate(
        _bundle(
            protocol,
            gate_pair_measurements=_gate_rows(21, 100),
            derived_level_review={
                "observed_disagreements": [_disagreement(pair, "E1")],
                "reviews": [],
                "unreviewed_derived_level_disagreement_count": 1,
            },
            diagnostics=_diagnostics(breakout_disagreement_rate={pair: 1}),
        )
    )
    assert record.verdict == VERDICT_FAIL
    assert record.primary_reason == REASON_STRUCTURAL_GATE_MATERIAL_FAILURE
    assert REASON_DERIVED_LEVEL_REVIEW_INCOMPLETE in record.reason_codes


def test_the_composition_names_its_single_point(contract: dict) -> None:
    assert contract["composition"]["single_composition_point"] == (
        "validate_v3_candidate"
    )
    assert contract["composition"]["state_space_is_total"] is True


# =============================================================================
# 17. the composed state space is total
# =============================================================================

_LEGAL_OUTCOMES = {
    requirement: (
        (GATE_PASS, GATE_FAIL, GATE_INSUFFICIENT)
        if requirement in REQUIREMENTS_THAT_CAN_FAIL
        else (GATE_PASS, GATE_INSUFFICIENT)
    )
    for requirement in HARD_REQUIREMENT_IDS
}


def _legal_states():
    for combination in product(*(_LEGAL_OUTCOMES[name] for name in HARD_REQUIREMENT_IDS)):
        yield dict(zip(HARD_REQUIREMENT_IDS, combination))


def test_the_legal_state_space_maps_totally_and_deterministically() -> None:
    states = list(_legal_states())
    assert len(states) == 3**4 * 2**3 == 648
    passing = 0
    for outcomes in states:
        result = compose_verdict(outcomes)
        assert result["verdict"] in VERDICT_VOCABULARY
        if any(value == GATE_FAIL for value in outcomes.values()):
            assert result["verdict"] == VERDICT_FAIL
        elif any(value == GATE_INSUFFICIENT for value in outcomes.values()):
            assert result["verdict"] == VERDICT_INSUFFICIENT
        else:
            assert result["verdict"] == VERDICT_PASS
            passing += 1
        assert result["primary_reason"] in result["reason_codes"]
        assert result["reason_codes"] == sorted(set(result["reason_codes"]))
    assert passing == 1


def test_every_state_has_a_primary_reason_from_the_declared_precedence() -> None:
    for outcomes in _legal_states():
        result = compose_verdict(outcomes)
        assert result["primary_reason"] in REASON_PRECEDENCE
        applicable = [
            reason for reason in REASON_PRECEDENCE if reason in result["reason_codes"]
        ]
        assert result["primary_reason"] == applicable[0]


def test_a_material_failure_is_never_explained_by_an_unresolved_requirement() -> None:
    failure_reasons = REASON_PRECEDENCE[:4]
    for outcomes in _legal_states():
        result = compose_verdict(outcomes)
        if result["verdict"] == VERDICT_FAIL:
            assert result["primary_reason"] in failure_reasons


def test_an_evidence_completeness_requirement_may_not_report_a_failure() -> None:
    for requirement in HARD_REQUIREMENT_IDS:
        if requirement in REQUIREMENTS_THAT_CAN_FAIL:
            continue
        outcomes = dict.fromkeys(HARD_REQUIREMENT_IDS, GATE_PASS)
        outcomes[requirement] = GATE_FAIL
        with pytest.raises(ValidatorError, match="cannot report a material failure"):
            compose_verdict(outcomes)


def test_the_composition_refuses_a_missing_or_unknown_requirement() -> None:
    complete = dict.fromkeys(HARD_REQUIREMENT_IDS, GATE_PASS)
    short = dict(complete)
    short.pop(REQUIREMENT_STRUCTURAL_GATE)
    with pytest.raises(ValidatorError, match="missing hard requirements"):
        compose_verdict(short)
    extra = dict(complete, invented_requirement=GATE_PASS)
    with pytest.raises(ValidatorError, match="unknown requirements"):
        compose_verdict(extra)


def test_the_composition_refuses_an_unknown_outcome() -> None:
    outcomes = dict.fromkeys(HARD_REQUIREMENT_IDS, GATE_PASS)
    outcomes[REQUIREMENT_STRUCTURAL_GATE] = "MAYBE"
    with pytest.raises(ValidatorError, match="unknown outcome"):
        compose_verdict(outcomes)


def test_the_reason_vocabulary_is_a_bijection() -> None:
    """One reason per (requirement, non-passing outcome), plus one for a pass."""

    expected = len(REQUIREMENTS_THAT_CAN_FAIL) + len(HARD_REQUIREMENT_IDS) + 1
    assert len(REASON_PRECEDENCE) == expected == 12
    assert len(set(REASON_PRECEDENCE)) == len(REASON_PRECEDENCE)
    seen = set()
    for outcomes in _legal_states():
        seen.update(compose_verdict(outcomes)["reason_codes"])
    assert seen == set(REASON_PRECEDENCE)


def test_the_requirement_order_cannot_change_the_composition() -> None:
    outcomes = {
        REQUIREMENT_STRUCTURAL_GATE: GATE_INSUFFICIENT,
        REQUIREMENT_TRANSFER_GUARD: GATE_FAIL,
        REQUIREMENT_COMPARABILITY: GATE_INSUFFICIENT,
        REQUIREMENT_PAIR_COMPLETENESS: GATE_PASS,
        REQUIREMENT_NOT_COMPARABLE: GATE_FAIL,
        REQUIREMENT_DERIVED_LEVEL_REVIEW: GATE_INSUFFICIENT,
        REQUIREMENT_INHERITED_GATES: GATE_PASS,
    }
    straight = compose_verdict(outcomes)
    shuffled = compose_verdict(dict(reversed(list(outcomes.items()))))
    assert straight == shuffled
    assert straight["primary_reason"] == REASON_TRANSFER_GUARD_FAILED


def test_the_composition_agrees_with_the_reference_approval_verdict() -> None:
    """Parity over the 72 states the frozen reference function can express.

    The validator composes two requirements the reference has no parameter
    for, so parity is asserted with those held at PASS. Where the reference can
    speak, the validator says the same thing -- which is the evidence that it
    resolved the review's open composition rather than authoring a new one.
    """

    states = 0
    for gate_verdict, guard_outcome, comparability, backlog, tier4 in product(
        (GATE_PASS, GATE_FAIL, GATE_INSUFFICIENT),
        (GUARD_SATISFIED, GUARD_FAILED, GUARD_UNDEFINED),
        (True, False),
        (0, 2),
        (True, False),
    ):
        reference = approval_verdict(
            hard_gate={"verdict": gate_verdict},
            transfer_guard={"outcome": guard_outcome},
            comparability_satisfied=comparability,
            unreviewed_derived_level_disagreement_count=backlog,
            tier4_hard_gates_passed=tier4,
        )
        composed = compose_verdict(
            {
                REQUIREMENT_STRUCTURAL_GATE: gate_verdict,
                REQUIREMENT_TRANSFER_GUARD: {
                    GUARD_SATISFIED: GATE_PASS,
                    GUARD_FAILED: GATE_FAIL,
                    GUARD_UNDEFINED: GATE_INSUFFICIENT,
                }[guard_outcome],
                REQUIREMENT_COMPARABILITY: GATE_PASS if comparability else GATE_INSUFFICIENT,
                REQUIREMENT_PAIR_COMPLETENESS: GATE_PASS,
                REQUIREMENT_NOT_COMPARABLE: GATE_PASS,
                REQUIREMENT_DERIVED_LEVEL_REVIEW: (
                    GATE_PASS if backlog == 0 else GATE_INSUFFICIENT
                ),
                REQUIREMENT_INHERITED_GATES: GATE_PASS if tier4 else GATE_FAIL,
            }
        )
        assert composed["verdict"] == reference["verdict"]
        states += 1
    assert states == 72


def test_the_composition_closes_the_reference_functions_missing_requirement() -> None:
    """`approval_verdict` has no parameter for the NOT_COMPARABLE census."""

    parameters = set(inspect.signature(approval_verdict).parameters)
    assert "unrecorded_not_comparable_event_count" not in parameters
    assert REQUIREMENT_NOT_COMPARABLE in HARD_REQUIREMENT_IDS
    assert "required_gate_pair_count" not in set(
        inspect.signature(evaluate_hard_structural_gate).parameters
    )
    assert REQUIREMENT_PAIR_COMPLETENESS in HARD_REQUIREMENT_IDS


def test_the_composition_does_not_depend_on_the_reference_signature(
    contract: dict,
) -> None:
    """Every hard requirement is recovered from the freeze, not from a function."""

    declared = set(contract["composition"]["hard_requirement_ids"])
    assert declared == set(HARD_REQUIREMENT_IDS)
    assert len(declared) == 7


# =============================================================================
# 18. the validator input schema
# =============================================================================


def test_the_bundle_must_declare_its_schema_version(protocol: dict) -> None:
    bundle = _bundle(protocol, schema_version="SOMETHING_ELSE_V1")
    with pytest.raises(ValidatorInputError, match=EVIDENCE_BUNDLE_SCHEMA_VERSION):
        _validate(bundle)


def test_an_unknown_top_level_field_refuses(protocol: dict) -> None:
    bundle = _bundle(protocol)
    bundle["invented_block"] = {}
    with pytest.raises(ValidatorInputError, match="unknown fields"):
        _validate(bundle)


def test_a_missing_top_level_field_refuses(protocol: dict) -> None:
    bundle = _bundle(protocol)
    del bundle["provenance"]
    with pytest.raises(ValidatorInputError, match="omits required fields"):
        _validate(bundle)


@pytest.mark.parametrize(
    "field,value",
    [
        ("comparison_contract_version", "CROSS_PROVIDER_STRUCTURE_COMPARISON_V1"),
        ("source_detector_version", "SOMETHING_ELSE_V1"),
        ("price_source_policy_version", "PRICE_SOURCE_POLICY_V2"),
        ("denominator_semantics_version", "OTHER_V1"),
        ("candidate_series_id", "MEDIAN_OHLC_V1"),
        ("provider_ids", ["bitstamp", "coinbase"]),
    ],
)
def test_a_bundle_measured_under_another_contract_refuses(
    protocol: dict, field: str, value
) -> None:
    identities = dict(_bundle(protocol)["identities"], **{field: value})
    with pytest.raises(ValidatorInputError, match="bound definition does not accept"):
        _validate(_bundle(protocol, identities=identities))


def test_a_malformed_provenance_digest_refuses(protocol: dict) -> None:
    provenance = dict(_bundle(protocol)["provenance"], sample_manifest_digest="short")
    with pytest.raises(ValidatorInputError, match="64-character sha256"):
        _validate(_bundle(protocol, provenance=provenance))


def test_an_uppercase_provenance_digest_refuses(protocol: dict) -> None:
    provenance = dict(
        _bundle(protocol)["provenance"], measurement_record_digest="A" * 64
    )
    with pytest.raises(ValidatorInputError, match="lowercase hexadecimal"):
        _validate(_bundle(protocol, provenance=provenance))


def test_a_naive_sample_instant_refuses(protocol: dict) -> None:
    sample = dict(_bundle(protocol)["sample"], start="2023-01-01T00:00:00")
    with pytest.raises(ValueError):
        _validate(_bundle(protocol, sample=sample))


def test_a_sample_that_ends_before_it_starts_refuses(protocol: dict) -> None:
    sample = dict(_bundle(protocol)["sample"], end="2022-01-01T00:00:00+00:00")
    with pytest.raises(ValidatorInputError, match="ends before it starts"):
        _validate(_bundle(protocol, sample=sample))


def test_the_input_schema_is_published_in_the_contract(contract: dict) -> None:
    schema = contract["input_schema"]
    assert schema["schema_version"] == EVIDENCE_BUNDLE_SCHEMA_VERSION
    assert schema["unknown_fields"] == "REFUSED"
    assert "state" in schema["pair_required_keys"]
    assert "structural_comparability_rate" in schema["pair_required_keys"]


def test_the_contract_states_that_missing_is_never_satisfied(contract: dict) -> None:
    completeness = contract["evidence_completeness"]
    assert completeness["missing_is_never_satisfied"] is True
    assert completeness["required_pair_state"] == PAIR_ADMISSIBLE
    assert set(completeness["nullable_pair_fields"]) == {
        "not_comparable_rate",
        "structural_comparability_rate",
    }


# =============================================================================
# 19. execution mode and the sealed window
# =============================================================================


def test_sealed_execution_is_not_authorized(protocol: dict) -> None:
    assert SEALED_EXECUTION_AUTHORIZED is False
    with pytest.raises(SealedExecutionNotAuthorizedError):
        _validate(_bundle(protocol), execution_mode=EXECUTION_MODE_SEALED)


def test_an_unknown_execution_mode_refuses(protocol: dict) -> None:
    with pytest.raises(ValidatorInputError, match="unknown execution mode"):
        _validate(_bundle(protocol), execution_mode="PRODUCTION")


def test_the_dry_run_mode_is_recorded_on_the_result(protocol: dict) -> None:
    record = _validate(_bundle(protocol))
    assert record.payload["execution_mode"] == EXECUTION_MODE_DRY_RUN


@pytest.mark.parametrize(
    "start,end",
    [
        ("2015-07-20T21:00:00+00:00", "2019-11-30T23:00:00+00:00"),
        ("2014-01-01T00:00:00+00:00", "2016-01-01T00:00:00+00:00"),
        ("2019-01-01T00:00:00+00:00", "2021-01-01T00:00:00+00:00"),
    ],
)
def test_a_bundle_reaching_into_the_sealed_window_is_refused(
    protocol: dict, start: str, end: str
) -> None:
    sample = dict(_bundle(protocol)["sample"], start=start, end=end)
    with pytest.raises(UntouchedValidationSampleGuardError):
        _validate(_bundle(protocol, sample=sample))


def test_the_contract_carries_the_sealed_boundaries(contract: dict) -> None:
    sealed = contract["sealed_sample"]
    assert sealed["start"] == UNTOUCHED_OOS_START.isoformat()
    assert sealed["end"] == UNTOUCHED_OOS_END.isoformat()
    assert sealed["collection_authorized"] is False
    assert sealed["opening_authorized"] is False
    assert sealed["sealed_execution_authorized"] is False


def test_the_sealed_execution_record_requirements_are_declared(
    contract: dict,
) -> None:
    required = set(contract["output_schema"]["sealed_execution_record_requirements"])
    assert {
        "sealed_execution_id",
        "bound_protocol_definition_sha256",
        "validator_definition_sha256",
        "sample_manifest_digest",
        "input_evidence_digest",
        "verdict",
        "reason_codes",
    } <= required


# =============================================================================
# 20. the validation record
# =============================================================================


def test_the_record_binds_both_hashes_and_its_own_input(
    protocol: dict, contract: dict
) -> None:
    bundle = _bundle(protocol)
    record = _validate(bundle)
    payload = record.payload
    assert payload["bound_protocol_definition_sha256"] == FROZEN_V3_DEFINITION_SHA256
    assert payload["parent_protocol_definition_sha256"] == FROZEN_V2_PARENT_SHA256
    assert payload["validator_definition_sha256"] == (
        contract["validator_definition_sha256"]
    )
    assert payload["input_evidence_digest"] == evidence_bundle_digest(bundle)
    assert payload["schema_version"] == VALIDATOR_RECORD_SCHEMA_VERSION


def test_the_record_publishes_every_declared_output_field(
    protocol: dict, contract: dict
) -> None:
    record = _validate(_bundle(protocol))
    assert set(record.payload) == set(contract["output_schema"]["fields"])


def test_the_record_publishes_every_hard_requirement(protocol: dict) -> None:
    record = _validate(_bundle(protocol))
    assert set(record.payload["hard_requirements"]) == set(HARD_REQUIREMENT_IDS)
    assert set(record.payload["hard_requirement_outcomes"]) == set(HARD_REQUIREMENT_IDS)


def test_the_record_publishes_the_pair_certifications(protocol: dict) -> None:
    record = _validate(_bundle(protocol))
    structural = record.payload["hard_requirements"][REQUIREMENT_STRUCTURAL_GATE]
    assert [row["comparison_id"] for row in structural["pairs"]] == list(GATE_PAIRS)
    guard = record.payload["hard_requirements"][REQUIREMENT_TRANSFER_GUARD]
    assert [row["comparison_id"] for row in guard["pairs"]] == list(GUARD_PAIRS)


def test_the_record_digest_covers_the_whole_record(protocol: dict) -> None:
    record = _validate(_bundle(protocol))
    other = _validate(_bundle(protocol, gate_pair_measurements=_gate_rows(0, 41)))
    assert record.payload["validation_record_digest"] != (
        other.payload["validation_record_digest"]
    )


def test_the_record_round_trips_through_json(protocol: dict) -> None:
    record = _validate(_bundle(protocol))
    assert json.loads(json.dumps(record.as_record())) == record.as_record()


# =============================================================================
# 21. the within-pair dependence limitation is carried, and corrected
# =============================================================================


def test_the_record_carries_the_within_pair_limitation(protocol: dict) -> None:
    limitation = _validate(_bundle(protocol)).payload["statistical_limitation"]
    assert limitation["is_a_gate"] is False
    assert "exchangeable" in limitation["within_pair"]
    assert "not attained" in limitation["within_pair"]


def test_the_validator_does_not_repeat_the_frozen_conservatism_claim(
    protocol: dict, contract: dict
) -> None:
    frozen = protocol["dependence_treatment"]["within_pair_disclosure"]
    assert "never towards a pass" in frozen
    limitation = contract["statistical_limitation"]
    assert limitation["repeats_the_frozen_conservatism_claim"] is False
    assert "wrong in direction" in limitation["within_pair"]
    assert "never towards a pass" not in limitation["within_pair"]


def test_no_cross_pair_independence_is_assumed(
    protocol: dict, contract: dict
) -> None:
    assert protocol["dependence_treatment"]["pair_independence_assumed"] is False
    assert protocol["dependence_treatment"]["family_wise_probability_multiplied"] is False
    cross = contract["statistical_limitation"]["cross_pair"]
    assert "no family-wise survival probability is multiplied" in cross


def test_the_point_rate_floor_is_named_as_assumption_free(contract: dict) -> None:
    assert "assumption-free floor" in contract["statistical_limitation"]["within_pair"]


# =============================================================================
# 22. the frozen V3 artifact is untouched
# =============================================================================


def test_the_frozen_v3_artifact_still_digests_to_its_own_hash() -> None:
    persisted = json.loads(
        (
            REPOSITORY_ROOT
            / "research_artifacts/btc019_v3_gate_architecture_convergence"
            / "reference_composite_v3_protocol.json"
        ).read_text()
    )
    assert persisted["definition_sha256"] == FROZEN_V3_DEFINITION_SHA256
    assert persisted["parent_definition_sha256"] == FROZEN_V2_PARENT_SHA256


def test_the_validator_authors_no_threshold_of_its_own(
    protocol: dict, contract: dict
) -> None:
    """Every number the validator compares against comes from the freeze."""

    assert contract["not_a_price_reference_protocol"] is True
    structural = next(
        item
        for item in contract["hard_requirements"]
        if item["requirement"] == REQUIREMENT_STRUCTURAL_GATE
    )
    assert structural["limit"] == protocol["materiality"]["absolute_limit"] == "0.20"
    comparability = next(
        item
        for item in contract["hard_requirements"]
        if item["requirement"] == REQUIREMENT_COMPARABILITY
    )
    assert comparability["floor"] == protocol["comparability_policy"]["floor"] == "0.50"


def test_the_contract_declares_what_a_material_change_requires(contract: dict) -> None:
    assert "BTC_REFERENCE_COMPOSITE_V4" in contract["material_change_requires"]
    assert "VALIDATOR_V2" in contract["material_change_requires"]


# =============================================================================
# 23. persistence, restore and tamper refusal
# =============================================================================


@pytest.fixture
def written(tmp_path: Path) -> Path:
    write_validator_artifacts(REPOSITORY_ROOT, tmp_path)
    return tmp_path


def test_the_written_artifacts_restore_and_verify(written: Path) -> None:
    assert (written / VALIDATOR_DEFINITION_FILENAME).exists()
    assert (written / VALIDATOR_REPORT_FILENAME).exists()
    restored = restore_validator_definition(written)
    assert restored["validator_definition_sha256"] == (
        validator_definition_sha256(REPOSITORY_ROOT)
    )
    assert verify_validator_artifacts(REPOSITORY_ROOT, written) == restored


def _tamper(written: Path, mutate) -> None:
    path = written / VALIDATOR_DEFINITION_FILENAME
    payload = json.loads(path.read_text())
    mutate(payload)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _redigest(payload: dict) -> None:
    """Re-digest a tampered payload so only the semantic checks can catch it."""

    import hashlib

    body = {
        key: value
        for key, value in payload.items()
        if key != "validator_definition_sha256"
    }
    payload["validator_definition_sha256"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "ascii"
        )
    ).hexdigest()


TAMPERS = {
    "bound_v3_hash": lambda payload: payload["binding"].__setitem__(
        "bound_protocol_definition_sha256", "0" * 64
    ),
    "parent_hash": lambda payload: payload["binding"].__setitem__(
        "parent_protocol_definition_sha256", "0" * 64
    ),
    "bound_version": lambda payload: payload["binding"].__setitem__(
        "bound_protocol_version", "BTC_REFERENCE_COMPOSITE_V4"
    ),
    "verdict_vocabulary": lambda payload: payload.__setitem__(
        "verdict_vocabulary", ["PASS", "FAIL"]
    ),
    "verdict_precedence_id": lambda payload: payload["verdict_precedence"].__setitem__(
        "precedence_id", "INSUFFICIENT_OUTRANKS_FAILURE_V1"
    ),
    "verdict_precedence_rule": lambda payload: payload["verdict_precedence"].__setitem__(
        "rule", "if any requirement is insufficient: UNDEFINED_INSUFFICIENT_EVIDENCE"
    ),
    "reason_precedence": lambda payload: payload["verdict_precedence"].__setitem__(
        "reason_precedence", list(reversed(REASON_PRECEDENCE))
    ),
    "operative_precedence": lambda payload: payload[
        "operative_field_precedence"
    ].__setitem__("precedence_id", "HISTORICAL_V2_PROVENANCE_WINS_V1"),
    "historical_fields_restored": lambda payload: payload[
        "operative_field_precedence"
    ].__setitem__("historical_provenance_only_fields", []),
    "wilson_formula_id": lambda payload: payload["certification_rule"].__setitem__(
        "formula_id", "WILSON_SCORE_UPPER_BOUND_CONTINUITY_CORRECTED_V1"
    ),
    "wilson_formula": lambda payload: payload["certification_rule"].__setitem__(
        "formula", "U = p_hat + z * sqrt(p_hat * (1 - p_hat) / n)"
    ),
    "continuity_correction": lambda payload: payload["certification_rule"].__setitem__(
        "continuity_correction_applied", True
    ),
    "certification_rule_id": lambda payload: payload["certification_rule"].__setitem__(
        "rule_id", "PER_PAIR_POINT_RATE_V1"
    ),
    "composition_rule": lambda payload: payload["composition"].__setitem__(
        "composition_rule_id", "V3_ANY_TWO_REQUIREMENTS_V1"
    ),
    "requirement_set": lambda payload: payload["composition"].__setitem__(
        "hard_requirement_ids", [REQUIREMENT_STRUCTURAL_GATE]
    ),
    "tier4_total": lambda payload: payload["tier4_inheritance"].__setitem__(
        "total_gate_count", 32
    ),
    "tier4_hard": lambda payload: payload["tier4_inheritance"].__setitem__(
        "hard_gate_count", 28
    ),
    "tier4_soft": lambda payload: payload["tier4_inheritance"].__setitem__(
        "soft_gate_count", 5
    ),
    "tier4_named": lambda payload: payload["tier4_inheritance"].__setitem__(
        "named_tier4_hard_gates", list(INHERITED_TIER4_HARD_GATES)[:-1]
    ),
    "soft_promoted": lambda payload: payload["tier4_inheritance"].__setitem__(
        "soft_gates_can_regain_a_hard_veto", True
    ),
    "sealed_collection": lambda payload: payload["sealed_sample"].__setitem__(
        "collection_authorized", True
    ),
    "sealed_opening": lambda payload: payload["sealed_sample"].__setitem__(
        "opening_authorized", True
    ),
    "sealed_execution": lambda payload: payload["sealed_sample"].__setitem__(
        "sealed_execution_authorized", True
    ),
    "sealed_start": lambda payload: payload["sealed_sample"].__setitem__(
        "start", "2016-01-01T00:00:00+00:00"
    ),
    "sealed_end": lambda payload: payload["sealed_sample"].__setitem__(
        "end", "2018-01-01T00:00:00+00:00"
    ),
    "not_comparable_positive": lambda payload: payload[
        "not_comparable_handling"
    ].__setitem__("positive_count", VERDICT_PASS),
    "not_comparable_missing": lambda payload: payload[
        "not_comparable_handling"
    ].__setitem__("missing_count", VERDICT_PASS),
    "census_rule": lambda payload: payload["hard_requirements"][5].__setitem__(
        "census_verification", "the census is believed as declared"
    ),
    "price_reference_claim": lambda payload: payload.__setitem__(
        "not_a_price_reference_protocol", False
    ),
    "schema_version": lambda payload: payload.__setitem__(
        "validator_schema_version", "SOMETHING_ELSE_V1"
    ),
    "validator_version": lambda payload: payload.__setitem__(
        "validator_version", "BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_V2"
    ),
}


@pytest.mark.parametrize("name", sorted(TAMPERS))
def test_every_meaningful_tamper_is_refused(written: Path, name: str) -> None:
    def mutate(payload: dict) -> None:
        TAMPERS[name](payload)
        _redigest(payload)

    _tamper(written, mutate)
    with pytest.raises(ValidatorError):
        restore_validator_definition(written)


@pytest.mark.parametrize("name", sorted(TAMPERS))
def test_every_meaningful_tamper_moves_the_definition_hash(
    written: Path, name: str
) -> None:
    payload = json.loads((written / VALIDATOR_DEFINITION_FILENAME).read_text())
    before = payload["validator_definition_sha256"]
    TAMPERS[name](payload)
    _redigest(payload)
    assert payload["validator_definition_sha256"] != before


def test_a_tamper_without_a_re_digest_is_refused(written: Path) -> None:
    _tamper(
        written,
        lambda payload: payload["certification_rule"].__setitem__(
            "normal_quantile", "1.64"
        ),
    )
    with pytest.raises(ValidatorError, match="tampered"):
        restore_validator_definition(written)


def test_a_materiality_or_pair_universe_tamper_fails_verification(
    written: Path,
) -> None:
    for mutate in (
        lambda payload: payload["hard_requirements"][0].__setitem__("limit", "0.40"),
        lambda payload: payload.__setitem__("required_gate_pairs", GATE_PAIRS[:1]),
        lambda payload: payload.__setitem__(
            "required_transfer_guard_pairs", list(GUARD_PAIRS[:2])
        ),
        lambda payload: payload["hard_requirements"][2].__setitem__("floor", "0.10"),
    ):
        write_validator_artifacts(REPOSITORY_ROOT, written)
        _tamper(written, lambda payload: (mutate(payload), _redigest(payload)))
        with pytest.raises(ValidatorError, match="does not recompute"):
            verify_validator_artifacts(REPOSITORY_ROOT, written)


def test_the_repository_artifacts_verify_against_the_repository() -> None:
    output = REPOSITORY_ROOT / VALIDATOR_OUTPUT_NAMESPACE
    persisted = verify_validator_artifacts(REPOSITORY_ROOT, output)
    assert persisted["binding"]["bound_protocol_definition_sha256"] == (
        FROZEN_V3_DEFINITION_SHA256
    )
    assert (output / VALIDATOR_REPORT_FILENAME).exists()


def test_the_validator_definition_hash_is_pinned() -> None:
    """Retyped so no later edit can move a verdict-affecting field in silence."""

    assert validator_definition_sha256(REPOSITORY_ROOT) == (
        "b9a1d878c98fbda7f6ef93186262fb1d7e5825d93249fa1157c3f0856aa15194"
    )


def test_the_report_is_written_and_names_the_binding(written: Path) -> None:
    report = (written / VALIDATOR_REPORT_FILENAME).read_text()
    assert FROZEN_V3_DEFINITION_SHA256 in report
    assert FROZEN_V2_PARENT_SHA256 in report
    assert "REFUSE_TO_RUN" in report
    assert VALIDATOR_VERSION in report


# =============================================================================
# 24. hash determinism
# =============================================================================


def test_the_contract_hash_is_stable_across_repeated_builds() -> None:
    first = validator_definition_sha256(REPOSITORY_ROOT)
    second = validator_definition_sha256(REPOSITORY_ROOT)
    assert first == second


def test_the_working_directory_cannot_change_the_contract_hash(
    tmp_path: Path, monkeypatch
) -> None:
    expected = validator_definition_sha256(REPOSITORY_ROOT)
    monkeypatch.chdir(tmp_path)
    assert validator_definition_sha256(REPOSITORY_ROOT) == expected


def test_the_ambient_decimal_context_cannot_change_a_result(protocol: dict) -> None:
    baseline = _validate(_bundle(protocol)).as_record()
    with localcontext(Context(prec=6)):
        narrowed = _validate(_bundle(protocol)).as_record()
        narrow_hash = validator_definition_sha256(REPOSITORY_ROOT)
    assert narrowed == baseline
    assert narrow_hash == validator_definition_sha256(REPOSITORY_ROOT)


def test_the_contract_carries_no_wall_clock_or_filesystem_path(
    contract: dict,
) -> None:
    rendered = json.dumps(contract)
    assert str(REPOSITORY_ROOT) not in rendered
    assert "/home/" not in rendered
    # The only instants it carries are the two frozen sealed boundaries.
    instants = set(re.findall(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", rendered))
    assert instants == {
        UNTOUCHED_OOS_START.isoformat()[:19],
        UNTOUCHED_OOS_END.isoformat()[:19],
    }


def test_the_contract_is_stable_across_a_process_restart_and_hash_seed() -> None:
    script = (
        "from pathlib import Path;"
        "from btc_predictor.research.reference_composite_v3_validator import "
        "validator_definition_sha256;"
        "print(validator_definition_sha256(Path('.')))"
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
    assert digests[0] == validator_definition_sha256(REPOSITORY_ROOT)


def test_the_written_definition_is_deterministic_ascii(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    write_validator_artifacts(REPOSITORY_ROOT, first)
    write_validator_artifacts(REPOSITORY_ROOT, second)
    for name in (VALIDATOR_DEFINITION_FILENAME, VALIDATOR_REPORT_FILENAME):
        left = (first / name).read_bytes()
        assert left == (second / name).read_bytes()
        assert left.decode("ascii")


def test_a_decimal_or_datetime_in_a_bundle_digests_deterministically(
    protocol: dict,
) -> None:
    rows = _gate_rows()
    rows[0]["structural_comparability_rate"] = Decimal("0.90")
    other = _gate_rows()
    other[0]["structural_comparability_rate"] = "0.90"
    assert evidence_bundle_digest(
        _bundle(protocol, gate_pair_measurements=rows)
    ) == evidence_bundle_digest(_bundle(protocol, gate_pair_measurements=other))


def test_an_undigestable_value_refuses_rather_than_acquiring_a_representation(
    protocol: dict,
) -> None:
    rows = _gate_rows()
    rows[0]["not_comparable_reason_counts"] = {"x": object()}
    with pytest.raises(ValidatorInputError, match="canonical evidence"):
        evidence_bundle_digest(_bundle(protocol, gate_pair_measurements=rows))


# =============================================================================
# 25. the sealed sample is never touched, and the candidate never constructed
# =============================================================================


def test_no_sealed_history_exists_on_disk() -> None:
    for path in (REPOSITORY_ROOT / "data").rglob("*"):
        if not path.is_file():
            continue
        for year in ("2015", "2016", "2017", "2018", "2019"):
            if year in path.name:
                pytest.fail(f"sealed-window history is present at {path}")


def test_a_full_validation_reads_no_market_data(protocol: dict, monkeypatch) -> None:
    """Watch every filesystem read a whole run performs."""

    import builtins

    opened: list[str] = []
    real_open = builtins.open
    real_read_text = Path.read_text
    real_read_bytes = Path.read_bytes

    def watched_open(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    def watched_read_text(self, *args, **kwargs):
        opened.append(str(self))
        return real_read_text(self, *args, **kwargs)

    def watched_read_bytes(self, *args, **kwargs):
        opened.append(str(self))
        return real_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", watched_open)
    monkeypatch.setattr(Path, "read_text", watched_read_text)
    monkeypatch.setattr(Path, "read_bytes", watched_read_bytes)
    record = _validate(_bundle(protocol))
    monkeypatch.undo()

    assert record.verdict == VERDICT_PASS
    data_root = str(REPOSITORY_ROOT / "data")
    for path in opened:
        assert not path.startswith(data_root), f"a run read collected data at {path}"
        for year in ("2015", "2016", "2017", "2018", "2019"):
            assert year not in path, f"a run touched {year} history at {path}"
    assert opened, "the watchers observed nothing at all"


def test_the_collector_is_never_called_from_a_validation(
    protocol: dict, monkeypatch
) -> None:
    from btc_predictor.data import ohlcv

    def _refuse(*args, **kwargs):  # pragma: no cover - must never run
        pytest.fail("the validator called the OHLCV collector")

    monkeypatch.setattr(ohlcv, "collect_btc_ohlcv", _refuse)
    assert _validate(_bundle(protocol)).verdict == VERDICT_PASS


def test_the_candidate_is_never_constructed_here(protocol: dict) -> None:
    """The candidate appears only as an identity label, never as a series."""

    record = _validate(_bundle(protocol))
    assert record.payload["provenance"]["candidate_series_id"] == "MEDIAN_OHLC_V2"
    for row in record.payload["hard_requirements"][REQUIREMENT_TRANSFER_GUARD]["pairs"]:
        assert "MEDIAN_OHLC" not in row["comparison_id"]


def test_the_bound_definition_says_the_sample_is_unopened(protocol: dict) -> None:
    sealed = protocol["sample_governance"]["sealed_sample"]
    assert sealed["status"] == "SEALED_UNOPENED"
    assert sealed["collected"] is False
    assert sealed["opened"] is False
    assert sealed["inspected"] is False
    assert sealed["guard_refuses_the_sealed_window"] is True
