"""Final gate-architecture convergence and freeze of BTC_REFERENCE_COMPOSITE_V3.

`BTC_REFERENCE_COMPOSITE_V3_STRUCTURAL_THRESHOLD_CALIBRATION_V1` settled every
semantic the denominator resolution left open and then tried to bind a
threshold to each of the six inherited structural gates. Two calibrated and
four did not, all four of them hard, so the successor could not be frozen. Its
required xHigh review reproduced the whole record, confirmed
`CALIBRATION_INSUFFICIENT`, and classified the project as
`FINAL_CONVERGENCE_WITH_EXISTING_EVIDENCE`: the missing evidence does not
exist outside the sealed window, and for one metric no amount of evidence
would have helped.

This module is that convergence. It decides the successor's final gate
architecture on the evidence already in hand and, if the architecture is
defensible, freezes it. It runs in three strictly ordered stages:

    STAGE 1  reverify the review's findings against the repository's own
             measurements, rather than accepting them as given
        |
        v
    STAGE 2  classify each of the six metrics into exactly one role, define an
             absolute materiality limit, a per-pair certification rule, a
             dependence treatment and a candidate-versus-provider guard
        |
        v
    STAGE 3  emit the complete frozen protocol and hash it

Three things the predecessor did are deliberately not carried forward.

The relative alternative `pi_alt = 3 * pi_bar` is abandoned. On a zero
numerator the Wilson band shrinks with the sample and the alternative shrinks
with it, so the per-pair expected counts converge to 0.64 against 1.92 at every
sample size; `breakout` was unidentifiable at any denominator and on any grid,
which is a property of the objective and not of the evidence. V3's tolerance is
an absolute economic limit instead.

Pair independence is abandoned. Provider-pair rows share underlying structural
events and candidate gate pairs all share the candidate, so no band is pooled
across pairs to set a threshold and no family-wise survival probability is
multiplied anywhere. The approval rule is a deterministic conjunction: every
required pair must certify on its own evidence.

The scalar minimum-comparable-event count is abandoned. It was derived only for
equal denominators and does not carry -- it is not even monotone in the
denominator. Sufficiency is now a confidence bound evaluated on each pair's own
numerator and denominator, so it is valid whatever the denominator vector is.

Nothing here approves a candidate, promotes a canonical reference, moves a
frozen artifact, changes candidate construction, collects new evidence, or
evaluates the candidate against any gate. `MEDIAN_OHLC_V2` is never
constructed. The sealed 2015-07-20..2019-11-30 sample is neither collected,
opened, inspected, queried nor summarised, and the inherited guard refuses any
window that reaches into it.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Context, Decimal, ROUND_HALF_EVEN
from fractions import Fraction
from pathlib import Path
from typing import Any

from btc_predictor.research.cross_provider_structure_comparison import (
    AFFECTED_V2_GATE_METRICS,
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
    UntouchedValidationSampleGuardError,
    guard_untouched_validation_sample,
)
from btc_predictor.research.structural_gate_denominator_resolution import (
    DENOMINATOR_SEMANTICS_VERSION,
    PARENT_DEFINITION_SHA256,
    SUCCESSOR_PROTOCOL_VERSION,
    frozen_parent_definition,
    successor_protocol_definition,
)
from btc_predictor.research.structural_threshold_calibration import (
    CALIBRATION_VERSION,
    CANDIDATE_SERIES_ID,
    MINIMUM_STRUCTURAL_COMPARABILITY_RATE,
    PAIR_ADMISSIBLE,
    REQUIRED_ADMISSIBLE_GATE_PAIR_COUNT,
    calibration_evidence,
    calibration_governance_sha256,
    calibration_pair_universe,
    exact_rate,
    family_failure_probability,
    gate_pair_universe,
    measure_pair,
    classify_calibration_pair,
    wilson_interval,
)


# --- identity -----------------------------------------------------------------

CONVERGENCE_VERSION = "BTC_REFERENCE_COMPOSITE_V3_GATE_ARCHITECTURE_CONVERGENCE_V1"
CONVERGENCE_SCHEMA_VERSION = (
    "BTC_REFERENCE_COMPOSITE_V3_GATE_ARCHITECTURE_CONVERGENCE_RECORD_V1"
)
V3_PROTOCOL_SCHEMA_VERSION = "BTC_REFERENCE_COMPOSITE_V3_PROTOCOL_DEFINITION_V1"

V3_PROTOCOL_VERSION = SUCCESSOR_PROTOCOL_VERSION
V3_FROZEN_STATUS = "FROZEN_RESEARCH_PROTOCOL"

CONVERGENCE_OUTPUT_NAMESPACE = "research_artifacts/btc019_v3_gate_architecture_convergence"
CONVERGENCE_RECORD_FILENAME = "gate_architecture_convergence.json"
V3_PROTOCOL_FILENAME = "reference_composite_v3_protocol.json"
CONVERGENCE_REPORT_FILENAME = "V3_GATE_ARCHITECTURE_CONVERGENCE_REPORT.md"

PREDECESSOR_CALIBRATION_VERSION = CALIBRATION_VERSION
PREDECESSOR_CALIBRATION_REVIEW_COMMIT = "03bb52d2881ca11c55fd09b8a54d922ec7dc0079"
PREDECESSOR_CALIBRATION_IMPLEMENTATION_COMMIT = (
    "fb12b2ffc6144c643d55208b4e94650e4d24cc92"
)
CONVERGENCE_BOUNDARY = "FINAL_CONVERGENCE_WITH_EXISTING_EVIDENCE"


class V3ConvergenceError(ValueError):
    """Raised when convergence or the freeze cannot proceed safely."""


# Statistics and rendering resolve in explicit contexts, never the caller's.
_STAT_CONTEXT = Context(prec=34, rounding=ROUND_HALF_EVEN)
_REPORT_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)


# =============================================================================
# STAGE 1 -- reverify the review's findings from the repository's own evidence
# =============================================================================

REVIEW_FINDING_REDUNDANT_WITHIN_N = "WITHIN_N_NUMERICALLY_IDENTICAL_TO_EXACT_TIMESTAMP"
REVIEW_FINDING_NESTED_STRUCTURAL_STATE = "STRUCTURAL_STATE_IS_A_SUBSET_OF_EXACT_TIMESTAMP"
REVIEW_FINDING_RELATIVE_ALTERNATIVE_DEGENERATE = (
    "RELATIVE_ALTERNATIVE_DEGENERATES_ON_A_ZERO_NUMERATOR"
)
REVIEW_FINDING_MINIMUM_N_INVALID = "SCALAR_MINIMUM_N_DOES_NOT_CARRY_TO_UNEQUAL_DENOMINATORS"
REVIEW_FINDINGS = (
    REVIEW_FINDING_REDUNDANT_WITHIN_N,
    REVIEW_FINDING_NESTED_STRUCTURAL_STATE,
    REVIEW_FINDING_RELATIVE_ALTERNATIVE_DEGENERATE,
    REVIEW_FINDING_MINIMUM_N_INVALID,
)

FINDING_CONFIRMED = "CONFIRMED_BY_INDEPENDENT_RECOMPUTATION"
FINDING_REFUTED = "REFUTED_BY_INDEPENDENT_RECOMPUTATION"

_EXACT_METRIC = "exact_timestamp_swing_disagreement_rate"
_WITHIN_1_METRIC = "within_1_week_swing_disagreement_rate"
_WITHIN_2_METRIC = "within_2_week_swing_disagreement_rate"
_STRUCTURAL_METRIC = "structural_state_disagreement_rate"
_BREAKOUT_METRIC = "breakout_disagreement_rate"
_RECLAIM_METRIC = "reclaim_disagreement_rate"

# The predecessor's published minima, reverified here against the unequal
# denominator vectors a real gate would actually carry.
PUBLISHED_MINIMUM_COMPARABLE_EVENTS = {
    _EXACT_METRIC: 13,
    _STRUCTURAL_METRIC: 17,
}
PUBLISHED_CALIBRATED_THRESHOLDS = {
    _EXACT_METRIC: Decimal("0.25"),
    _STRUCTURAL_METRIC: Decimal("0.20"),
}
UNEQUAL_DENOMINATOR_PROBES = (
    (20, 25, 30),
    (18, 20, 22),
    (30, 30, 30),
    (25, 40, 55),
)


def measured_evidence(repository_root: Path) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Re-measure both already-inspected samples, metric by metric.

    Only the three independent raw-provider pairs exist in this evidence: the
    comparison contract compares observable providers and never builds a
    composite, so no candidate value is constructed anywhere in this module.
    """

    samples = calibration_evidence(repository_root)
    measured: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for metric in AFFECTED_V2_GATE_METRICS:
        by_sample: dict[str, list[dict[str, Any]]] = {}
        for sample_dir in sorted(samples):
            sample = samples[sample_dir]
            policy_version = sample["dataset"]["price_source_policy_version"]
            rows = []
            for comparison in sample["comparisons"]:
                if CANDIDATE_SERIES_ID in comparison["series_ids"]:
                    raise V3ConvergenceError(
                        "development evidence must not contain the candidate series"
                    )
                measurement = measure_pair(comparison, metric)
                admissibility = classify_calibration_pair(
                    measurement,
                    comparison=comparison,
                    dataset_policy_version=policy_version,
                )
                rows.append({**measurement, **admissibility.as_record()})
            by_sample[sample_dir] = sorted(rows, key=lambda item: item["comparison_id"])
        measured[metric] = by_sample
    return measured


def _rows(
    measured: Mapping[str, Mapping[str, Sequence[Mapping[str, Any]]]],
    metric: str,
) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for sample_dir in sorted(measured[metric]):
        for row in measured[metric][sample_dir]:
            flat.append({**row, "sample_dir": sample_dir})
    return flat


def verify_within_n_redundancy(
    measured: Mapping[str, Mapping[str, Sequence[Mapping[str, Any]]]],
) -> dict[str, Any]:
    """Check whether within-1 and within-2 ever differ from exact timestamp."""

    exact = _rows(measured, _EXACT_METRIC)
    comparisons: list[dict[str, Any]] = []
    distinguishing = 0
    merged_total = 0
    for metric in (_WITHIN_1_METRIC, _WITHIN_2_METRIC):
        for base, other in zip(exact, _rows(measured, metric), strict=True):
            if (base["sample_dir"], base["comparison_id"]) != (
                other["sample_dir"],
                other["comparison_id"],
            ):  # pragma: no cover - defensive
                raise V3ConvergenceError("measurement rows are not aligned")
            identical = (
                base["numerator"] == other["numerator"]
                and base["denominator"] == other["denominator"]
            )
            merged = other.get("matched_pair_count", 0)
            merged_total += merged
            if not identical:
                distinguishing += 1
            comparisons.append(
                {
                    "comparison_id": other["comparison_id"],
                    "exact": f"{base['numerator']}/{base['denominator']}",
                    "identical_to_exact_timestamp": identical,
                    "matched_pair_count": merged,
                    "metric": metric,
                    "sample_dir": other["sample_dir"],
                    "within_n": f"{other['numerator']}/{other['denominator']}",
                }
            )
    return {
        "distinguishing_measurement_count": distinguishing,
        "finding": REVIEW_FINDING_REDUNDANT_WITHIN_N,
        "measurement_count": len(comparisons),
        "measurements": comparisons,
        "merged_pair_total": merged_total,
        "statement": (
            "within_1_week and within_2_week differ from exact_timestamp only "
            "where the matching mechanism merges an opposing pair. No "
            "measurement in either already-inspected sample merges one, so on "
            "every observation the repository holds the three metrics are the "
            "same number and their thresholds are not separately identified."
        ),
        "verdict": FINDING_CONFIRMED if distinguishing == 0 else FINDING_REFUTED,
    }


def verify_structural_state_nesting(
    measured: Mapping[str, Mapping[str, Sequence[Mapping[str, Any]]]],
) -> dict[str, Any]:
    """Check that structural state is a subset of exact-timestamp disagreement."""

    rows: list[dict[str, Any]] = []
    violations = 0
    strict = 0
    for base, other in zip(
        _rows(measured, _EXACT_METRIC), _rows(measured, _STRUCTURAL_METRIC), strict=True
    ):
        same_denominator = base["denominator"] == other["denominator"]
        subset = other["numerator"] <= base["numerator"]
        if not (same_denominator and subset):
            violations += 1
        if other["numerator"] < base["numerator"]:
            strict += 1
        rows.append(
            {
                "comparison_id": other["comparison_id"],
                "exact_numerator": base["numerator"],
                "sample_dir": other["sample_dir"],
                "shared_denominator": base["denominator"] if same_denominator else None,
                "structural_state_numerator": other["numerator"],
                "subset": subset and same_denominator,
            }
        )
    return {
        "finding": REVIEW_FINDING_NESTED_STRUCTURAL_STATE,
        "measurements": rows,
        "strictly_smaller_measurement_count": strict,
        "statement": (
            "structural_state shares exact_timestamp's denominator and counts "
            "the subset of its numerator whose difference also changed a "
            "downstream breakout or reclaim state. It is therefore the "
            "economically consequential part of the same event universe, not "
            "an independent signal about a different failure mode."
        ),
        "verdict": FINDING_CONFIRMED if violations == 0 else FINDING_REFUTED,
        "violation_count": violations,
    }


RELATIVE_ALTERNATIVE_PROBE_DENOMINATORS = (5, 10, 20, 50, 100, 200, 1000)


def verify_relative_alternative_degeneracy() -> dict[str, Any]:
    """Show that `3 x pi_bar` cannot identify a metric with a zero numerator.

    The pooled band is estimated over the six admissible pair measurements, so
    a per-pair denominator of ``n`` pools ``6n`` events. On a zero numerator
    the two-sided 95% Wilson upper limit is ``z^2 / (6n + z^2)``, so the
    per-pair expected count under the band converges to ``z^2 / 6`` and under
    the alternative to three times that -- 0.64 against 1.92 -- however large
    the sample grows. A test cannot separate them, at any denominator and on
    any grid, so no further evidence round could have resolved `breakout`.
    """

    probes = []
    for per_pair in RELATIVE_ALTERNATIVE_PROBE_DENOMINATORS:
        pooled = 6 * per_pair
        band = wilson_interval(0, pooled).upper
        expected_band = _STAT_CONTEXT.multiply(Decimal(per_pair), band)
        expected_alt = _STAT_CONTEXT.multiply(Decimal(3 * per_pair), band)
        probes.append(
            {
                "expected_count_under_alternative": str(
                    _REPORT_CONTEXT.plus(expected_alt)
                ),
                "expected_count_under_band": str(_REPORT_CONTEXT.plus(expected_band)),
                "per_pair_denominator": per_pair,
                "pi_bar": str(_REPORT_CONTEXT.plus(band)),
                "pooled_denominator": pooled,
            }
        )
    limit_band = _STAT_CONTEXT.divide(
        _STAT_CONTEXT.power(NORMAL_QUANTILE_0_975, 2), Decimal(6)
    )
    return {
        "expected_count_limit_under_alternative": str(
            _REPORT_CONTEXT.plus(_STAT_CONTEXT.multiply(Decimal(3), limit_band))
        ),
        "expected_count_limit_under_band": str(_REPORT_CONTEXT.plus(limit_band)),
        "finding": REVIEW_FINDING_RELATIVE_ALTERNATIVE_DEGENERATE,
        "probes": probes,
        "statement": (
            "Under a relative alternative the detectable effect shrinks with "
            "the band that defines it, so a metric that observes no "
            "disagreement is unidentifiable at every sample size. The relative "
            "rule is not carried into the frozen protocol."
        ),
        "verdict": FINDING_CONFIRMED,
    }


def verify_minimum_n_invalidity() -> dict[str, Any]:
    """Show the predecessor's scalar minima do not carry to unequal denominators."""

    probes = []
    holds_everywhere = True
    monotone = True
    for metric, minimum in sorted(PUBLISHED_MINIMUM_COMPARABLE_EVENTS.items()):
        threshold = PUBLISHED_CALIBRATED_THRESHOLDS[metric]
        alternative = _published_alternative(metric)
        equal = family_failure_probability(
            denominators=[minimum] * REQUIRED_ADMISSIBLE_GATE_PAIR_COUNT,
            threshold=threshold,
            probability=alternative,
        )
        for denominators in UNEQUAL_DENOMINATOR_PROBES:
            power = family_failure_probability(
                denominators=list(denominators),
                threshold=threshold,
                probability=alternative,
            )
            meets = power >= Fraction(4, 5)
            if not meets:
                holds_everywhere = False
            if min(denominators) >= minimum and power < equal:
                monotone = False
            probes.append(
                {
                    "all_denominators_at_or_above_minimum": min(denominators) >= minimum,
                    "denominators": list(denominators),
                    "family_power": str(
                        _REPORT_CONTEXT.plus(
                            _STAT_CONTEXT.divide(
                                Decimal(power.numerator), Decimal(power.denominator)
                            )
                        )
                    ),
                    "meets_declared_power": meets,
                    "metric": metric,
                    "published_minimum": minimum,
                    "power_at_the_published_minimum": str(
                        _REPORT_CONTEXT.plus(
                            _STAT_CONTEXT.divide(
                                Decimal(equal.numerator), Decimal(equal.denominator)
                            )
                        )
                    ),
                }
            )
    return {
        "finding": REVIEW_FINDING_MINIMUM_N_INVALID,
        "power_is_monotone_in_the_denominator": monotone,
        "probes": probes,
        "scalar_minimum_holds_at_every_probe": holds_everywhere,
        "statement": (
            "The published minima were searched only over equal denominators. "
            "They do not carry to the unequal vectors a real gate has, and the "
            "family power is not even monotone in the denominator: raising "
            "every pair above the minimum can lower it, because the smallest "
            "failing count grows with the denominator faster than the "
            "alternative's expected count does. V3 therefore replaces the "
            "scalar minimum with a per-pair confidence bound, which is "
            "evaluated on each pair's own denominator and is valid for any "
            "denominator vector by construction."
        ),
        "verdict": FINDING_CONFIRMED if not holds_everywhere else FINDING_REFUTED,
    }


def _published_alternative(metric: str) -> Fraction:
    """The predecessor's own detectable alternative, recomputed here."""

    pooled = {_EXACT_METRIC: (7, 156), _STRUCTURAL_METRIC: (4, 156)}[metric]
    band = wilson_interval(*pooled).upper
    alternative = min(Fraction(band) * 3, Fraction(1))
    return alternative


def verified_review_findings(
    measured: Mapping[str, Mapping[str, Sequence[Mapping[str, Any]]]],
) -> dict[str, Any]:
    """Stage 1: the four findings this convergence relies on, reverified."""

    findings = {
        REVIEW_FINDING_REDUNDANT_WITHIN_N: verify_within_n_redundancy(measured),
        REVIEW_FINDING_NESTED_STRUCTURAL_STATE: verify_structural_state_nesting(measured),
        REVIEW_FINDING_RELATIVE_ALTERNATIVE_DEGENERATE: (
            verify_relative_alternative_degeneracy()
        ),
        REVIEW_FINDING_MINIMUM_N_INVALID: verify_minimum_n_invalidity(),
    }
    refuted = sorted(
        name for name, item in findings.items() if item["verdict"] != FINDING_CONFIRMED
    )
    if refuted:
        raise V3ConvergenceError(
            "the architecture rests on review findings this evidence refutes: "
            f"{refuted}"
        )
    return {
        "findings": dict(sorted(findings.items())),
        "review_commit": PREDECESSOR_CALIBRATION_REVIEW_COMMIT,
        "taken_on_trust": False,
    }


# =============================================================================
# STAGE 2 -- the final architecture
# =============================================================================

# --- 2A. absolute economic materiality ----------------------------------------

MATERIALITY_POLICY_ID = "ABSOLUTE_STRUCTURAL_MATERIALITY_V1"

# One in five. Declared before any observed rate is consulted, from what a
# structural difference costs the strategy rather than from what the
# development samples happened to show.
STRUCTURAL_MATERIALITY_LIMIT = Decimal("0.20")

MATERIALITY_STATEMENT = (
    "A canonical BTC reference is materially unfit when, against an "
    "independent observable market reference, more than one in five "
    "economically consequential weekly structural events resolves "
    "differently. Economically consequential means the two series disagree "
    "about a weekly swing and the detecting series also confirmed a breakout "
    "or reclaim from it, so the difference changed downstream support and "
    "resistance state rather than only a label."
)

MATERIALITY_DERIVATION = (
    {
        "ground": "structural meaning",
        "reasoning": (
            "The weekly structural map is a set of active levels, not a stream "
            "of independent observations. A disagreement rate is the fraction "
            "of that set which exists in one series and not the other. Above "
            "one in five, more than a fifth of the active map is source "
            "specific and the two series are no longer describing the same "
            "market structure -- whatever their prices look like."
        ),
    },
    {
        "ground": "strategy impact",
        "reasoning": (
            "Weekly levels anchor BTC-141 invalidation and BTC-142 stops, "
            "feed the Structure Score and gate setup classification, and each "
            "level stays active for weeks. A level that only one series ever "
            "printed puts a stop and a setup on a venue artefact for the whole "
            "time it remains in the map."
        ),
    },
    {
        "ground": "stop / MFE / MAE consequences",
        "reasoning": (
            "The trade-level cost of a bad reference is measured directly, and "
            "hard, by the inherited Tier-4 gates: stop_touch_disagreement_rate "
            "at most 0.01, cross_market_confirmed_stop_preservation_rate at "
            "least 1.0, MFE and MAE medians at most 0.0025 and p95 at most "
            "0.01. The structural gate is the upstream cause, not the harm, so "
            "it is set where structural difference stops being isolated and "
            "becomes systematic -- not at the decision-tier tolerances, which "
            "bound the harm itself two orders of magnitude tighter."
        ),
    },
    {
        "ground": "known source sensitivity",
        "reasoning": (
            "BTC-019 rejected Bitstamp as the sole canonical reference on a "
            "handful of structural differences whose Tier-4 consequences were "
            "a missed consensus stop and 2.433 / 4.605 percentage points of "
            "MFE / MAE sensitivity. The project's own precedent is that a few "
            "consequential structural differences are disqualifying when they "
            "propagate, which is what the Tier-4 gates test; the structural "
            "limit's job is to refuse a reference whose whole structural "
            "description differs."
        ),
    },
    {
        "ground": "Phase-1 tolerance philosophy",
        "reasoning": (
            "Phase 1 asks for a reference a competent independent observer "
            "would accept as a description of the same market, not for a "
            "perfect one. Four in five agreement on consequential structural "
            "events is the weakest claim that still supports that reading, and "
            "the limit is a simple interpretable fraction rather than a fitted "
            "decimal."
        ),
    },
)

REJECTED_MATERIALITY_DERIVATIONS = (
    {
        "derivation": "maximum observed disagreement rate plus an epsilon",
        "why_refused": (
            "That defines the unacceptable level as whatever development "
            "evidence happened to produce, so a quiet sample would license a "
            "loose reference and a noisy one a strict reference."
        ),
    },
    {
        "derivation": "a multiple of the observed independent-provider band",
        "why_refused": (
            "This is the predecessor's `3 x pi_bar`. The alternative shrinks "
            "with the band, so a metric observing no disagreement is "
            "unidentifiable at every sample size, and the limit stops meaning "
            "anything economic."
        ),
    },
    {
        "derivation": "the value that reproduces a BTC_REFERENCE_COMPOSITE_V2 verdict",
        "why_refused": (
            "The frozen V2 numbers were carried forward explicitly "
            "uncalibrated; reproducing them would launder an unjustified "
            "number through a new protocol."
        ),
    },
    {
        "derivation": "the value that maximises the number of historical pairs that pass",
        "why_refused": (
            "Pass counting selects the threshold from the outcome. The realism "
            "check below reports how the limit sits against observed "
            "dispersion; it does not choose it."
        ),
    },
    {
        "derivation": "the value that makes the candidate pass",
        "why_refused": (
            "The candidate is never constructed or measured in this task, "
            "precisely so that it cannot inform the limit."
        ),
    },
)

MATERIALITY_INDEPENDENT_OF_OBSERVATION = (
    "The limit answers what disagreement rate would be unacceptable, which is "
    "a question about consequence and not about whether development evidence "
    "happened to observe zero disagreements. It is declared here as a module "
    "constant, ahead of any measurement, and no code path lets an observed "
    "rate move it."
)


# --- 2B. the per-pair certification rule ---------------------------------------

CERTIFICATION_RULE_ID = "PER_PAIR_WILSON_UPPER_BOUND_V1"

NORMAL_QUANTILE_0_950 = Decimal("1.644853626951472714864")
NORMAL_QUANTILE_0_975 = Decimal("1.959963984540054235631")
NORMAL_QUANTILE_0_995 = Decimal("2.575829303548900761546")

CONFIDENCE_LEVELS = {
    "90": NORMAL_QUANTILE_0_950,
    "95": NORMAL_QUANTILE_0_975,
    "99": NORMAL_QUANTILE_0_995,
}
CERTIFICATION_CONFIDENCE_LEVEL = "95"

PAIR_CERTIFIED = "PAIR_CERTIFIED"
PAIR_MATERIAL_FAILURE = "PAIR_MATERIAL_FAILURE"
PAIR_INSUFFICIENT_EVIDENCE = "PAIR_INSUFFICIENT_EVIDENCE"
PAIR_OUTCOMES = (PAIR_CERTIFIED, PAIR_MATERIAL_FAILURE, PAIR_INSUFFICIENT_EVIDENCE)

CERTIFICATION_REASON_NO_COMPARABLE_EVENTS = "NO_COMPARABLE_EVENTS"
CERTIFICATION_REASON_BELOW_COMPARABILITY_FLOOR = "BELOW_STRUCTURAL_COMPARABILITY_FLOOR"
CERTIFICATION_REASON_PAIR_INADMISSIBLE = "PAIR_INADMISSIBLE"
CERTIFICATION_REASON_REQUIRED_PAIR_ABSENT = "REQUIRED_PAIR_ABSENT"
CERTIFICATION_REASON_BOUND_EXCEEDS_LIMIT = "EVIDENCE_DOES_NOT_EXCLUDE_A_MATERIAL_RATE"
CERTIFICATION_REASON_RATE_EXCEEDS_LIMIT = "OBSERVED_RATE_EXCEEDS_THE_MATERIALITY_LIMIT"
CERTIFICATION_REASON_CODES = (
    CERTIFICATION_REASON_BELOW_COMPARABILITY_FLOOR,
    CERTIFICATION_REASON_BOUND_EXCEEDS_LIMIT,
    CERTIFICATION_REASON_NO_COMPARABLE_EVENTS,
    CERTIFICATION_REASON_PAIR_INADMISSIBLE,
    CERTIFICATION_REASON_RATE_EXCEEDS_LIMIT,
    CERTIFICATION_REASON_REQUIRED_PAIR_ABSENT,
)

CERTIFICATION_RULE = (
    "A pair certifies a maximum-direction structural gate when, and only "
    "when, it is admissible, its comparable-event denominator is non-zero, "
    "and the upper limit of the two-sided 95% Wilson score interval on its "
    "own numerator and denominator is at or below the absolute materiality "
    "limit. If the observed point rate itself exceeds the limit the pair is a "
    "material failure. If the point rate is at or below the limit but the "
    "upper limit is not, the pair has not produced enough evidence to exclude "
    "a material rate and is insufficient, never a pass. Equality certifies, in "
    "both comparisons, matching the repository's existing convention that a "
    "gate boundary is inclusive."
)

CERTIFICATION_RULE_PROPERTIES = (
    "One rule replaces the predecessor's separate threshold and scalar "
    "minimum-n, so there is no equal-denominator derivation to carry.",
    "It is evaluated on one pair's own numerator and denominator, so an "
    "unequal denominator vector needs no separate treatment and cannot "
    "invalidate it.",
    "A small denominator widens the interval, so thin evidence fails to "
    "certify rather than passing quietly: insufficient evidence can never "
    "approve.",
    "A zero comparable denominator has no interval at all and is insufficient, "
    "never a rate of 0.0.",
    "It is a deterministic function of two integers, a declared quantile and "
    "an explicit Decimal context, so it reproduces exactly.",
    "It separates a reference that is measurably bad from one that is merely "
    "unmeasured, which the predecessor's single threshold could not.",
)


def wilson_upper_bound(
    numerator: int,
    denominator: int,
    *,
    quantile: Decimal = NORMAL_QUANTILE_0_975,
) -> Decimal | None:
    """Upper limit of the two-sided Wilson score interval, or None on no evidence.

    Written out here rather than delegated so the frozen rule does not depend
    on another task's helper; the 95% case is pinned equal to the predecessor's
    `wilson_interval` by test.
    """

    if numerator < 0 or denominator < 0:
        raise V3ConvergenceError("a count cannot be negative")
    if numerator > denominator:
        raise V3ConvergenceError("a numerator cannot exceed its denominator")
    if denominator == 0:
        return None
    n = Decimal(denominator)
    z2 = _STAT_CONTEXT.power(quantile, 2)
    observed = _STAT_CONTEXT.divide(Decimal(numerator), n)
    denominator_term = _STAT_CONTEXT.add(Decimal(1), _STAT_CONTEXT.divide(z2, n))
    centre = _STAT_CONTEXT.divide(
        _STAT_CONTEXT.add(observed, _STAT_CONTEXT.divide(z2, _STAT_CONTEXT.multiply(Decimal(2), n))),
        denominator_term,
    )
    variance = _STAT_CONTEXT.add(
        _STAT_CONTEXT.divide(
            _STAT_CONTEXT.multiply(observed, _STAT_CONTEXT.subtract(Decimal(1), observed)), n
        ),
        _STAT_CONTEXT.divide(z2, _STAT_CONTEXT.multiply(Decimal(4), _STAT_CONTEXT.power(n, 2))),
    )
    half_width = _STAT_CONTEXT.divide(
        _STAT_CONTEXT.multiply(quantile, _STAT_CONTEXT.sqrt(variance)), denominator_term
    )
    return min(_STAT_CONTEXT.add(centre, half_width), Decimal(1))


@dataclass(frozen=True)
class PairCertification:
    """One required pair's certification outcome against a materiality limit."""

    comparison_id: str
    numerator: int | None
    denominator: int | None
    rate: Decimal | None
    upper_bound: Decimal | None
    outcome: str
    reason_codes: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        if self.outcome not in PAIR_OUTCOMES:
            raise V3ConvergenceError(f"unknown pair outcome {self.outcome!r}")
        unknown = [
            code for code in self.reason_codes if code not in CERTIFICATION_REASON_CODES
        ]
        if unknown:
            raise V3ConvergenceError(f"unknown certification reason codes {unknown}")
        if self.outcome == PAIR_CERTIFIED and self.reason_codes:
            raise V3ConvergenceError("a certified pair carries no reason code")
        if self.outcome != PAIR_CERTIFIED and not self.reason_codes:
            raise V3ConvergenceError("an uncertified pair must name its reason")
        return {
            "comparison_id": self.comparison_id,
            "denominator": self.denominator,
            "numerator": self.numerator,
            "outcome": self.outcome,
            "rate": None if self.rate is None else str(_REPORT_CONTEXT.plus(self.rate)),
            "reason_codes": list(self.reason_codes),
            "upper_bound": (
                None
                if self.upper_bound is None
                else str(_REPORT_CONTEXT.plus(self.upper_bound))
            ),
        }


def certify_pair(
    measurement: Mapping[str, Any] | None,
    *,
    comparison_id: str,
    limit: Decimal = STRUCTURAL_MATERIALITY_LIMIT,
    quantile: Decimal = NORMAL_QUANTILE_0_975,
    comparability_floor: Decimal = MINIMUM_STRUCTURAL_COMPARABILITY_RATE,
) -> PairCertification:
    """Apply `PER_PAIR_WILSON_UPPER_BOUND_V1` to one pair measurement."""

    if measurement is None:
        return PairCertification(
            comparison_id=comparison_id,
            numerator=None,
            denominator=None,
            rate=None,
            upper_bound=None,
            outcome=PAIR_INSUFFICIENT_EVIDENCE,
            reason_codes=(CERTIFICATION_REASON_REQUIRED_PAIR_ABSENT,),
        )
    reasons: list[str] = []
    # The frozen policy requires a pair to *carry* complete comparability
    # evidence and an established admissible state, not merely to avoid
    # contradicting them: absent evidence is evidence of absence, so a
    # measurement that omits either one cannot certify.
    if measurement.get("state") != PAIR_ADMISSIBLE:
        reasons.append(CERTIFICATION_REASON_PAIR_INADMISSIBLE)
    comparability = measurement.get("structural_comparability_rate")
    if comparability is None:
        reasons.append(CERTIFICATION_REASON_PAIR_INADMISSIBLE)
    elif Decimal(comparability) < comparability_floor:
        reasons.append(CERTIFICATION_REASON_BELOW_COMPARABILITY_FLOOR)
    numerator = measurement["numerator"]
    denominator = measurement["denominator"]
    rate = exact_rate(numerator, denominator)
    upper = wilson_upper_bound(numerator, denominator, quantile=quantile)
    if denominator == 0 or rate is None or upper is None:
        reasons.append(CERTIFICATION_REASON_NO_COMPARABLE_EVENTS)
        return PairCertification(
            comparison_id=comparison_id,
            numerator=numerator,
            denominator=denominator,
            rate=None,
            upper_bound=None,
            outcome=PAIR_INSUFFICIENT_EVIDENCE,
            reason_codes=tuple(sorted(set(reasons))),
        )
    if rate > limit:
        reasons.append(CERTIFICATION_REASON_RATE_EXCEEDS_LIMIT)
        outcome = PAIR_MATERIAL_FAILURE
    elif upper > limit:
        reasons.append(CERTIFICATION_REASON_BOUND_EXCEEDS_LIMIT)
        outcome = PAIR_INSUFFICIENT_EVIDENCE
    elif reasons:
        outcome = PAIR_INSUFFICIENT_EVIDENCE
    else:
        outcome = PAIR_CERTIFIED
    return PairCertification(
        comparison_id=comparison_id,
        numerator=numerator,
        denominator=denominator,
        rate=rate,
        upper_bound=upper,
        outcome=outcome,
        reason_codes=tuple(sorted(set(reasons))),
    )


# --- 2C. aggregation, with no independence assumption anywhere -----------------

AGGREGATION_ID = "ALL_REQUIRED_PAIRS_MUST_CERTIFY_V1"

GATE_PASS = "PASS"
GATE_FAIL = "FAIL"
GATE_INSUFFICIENT = "UNDEFINED_INSUFFICIENT_EVIDENCE"
GATE_VERDICTS = (GATE_PASS, GATE_FAIL, GATE_INSUFFICIENT)

AGGREGATION_RULE = (
    "Every required pair must certify. The gate FAILs when any required pair "
    "is a material failure; otherwise it is UNDEFINED_INSUFFICIENT_EVIDENCE "
    "when any required pair is missing, inadmissible, undefined or "
    "insufficient; and it PASSes only when all of them certify. A definite "
    "material failure outranks missing evidence, so one bad pair cannot be "
    "hidden behind another pair's silence. No probability is combined across "
    "pairs and no survival probability is multiplied: the rule is a "
    "deterministic conjunction over an explicitly enumerated pair set."
)

DEPENDENCE_TREATMENT_ID = "NO_CROSS_PAIR_INDEPENDENCE_ASSUMED_V1"

DEPENDENCE_TREATMENT = (
    {
        "assumption_removed": "pooled provider-pair rows as independent Bernoulli trials",
        "how": (
            "No band is pooled across pairs to set a threshold. The materiality "
            "limit is absolute and economic, so the three provider pairs -- "
            "which share the same underlying weekly structural events, one "
            "market fact appearing in two or three rows -- are never combined "
            "into one estimate that a threshold is read off."
        ),
        "where_it_was": (
            f"{PREDECESSOR_CALIBRATION_VERSION} pooled 156 pair measurements "
            "into one Wilson band and set the threshold from it."
        ),
    },
    {
        "assumption_removed": "multiplied family-wise survival across gate pairs",
        "how": (
            "No family-wise probability is computed. The approval rule is a "
            "conjunction and is reported as one; each pair's 95% statement is "
            "about that pair alone and is labelled as such."
        ),
        "where_it_was": (
            "The predecessor multiplied per-pair pass probabilities across "
            "three gate pairs that all share the candidate series, so the "
            "product was neither an upper nor a lower bound on the true "
            "family-wise rate."
        ),
    },
)

WITHIN_PAIR_DEPENDENCE_DISCLOSURE = (
    "One assumption remains and is declared rather than hidden. The Wilson "
    "interval treats the comparable structural events inside a single pair as "
    "exchangeable trials. They are distinct calendar events, not one fact "
    "repeated across rows, so this is far weaker than the cross-pair "
    "assumption that was removed -- but weekly structure is serially "
    "dependent and one episode can produce two adjacent-week disagreements, so "
    "it is not exact. Its violation is conservative for approval: clustering "
    "inflates a numerator, and on a maximum-direction gate read through an "
    "upper bound that pushes a pair towards insufficient or failure, never "
    "towards a pass. No claim of exact coverage is made or needed, because the "
    "approval rule is the deterministic conjunction and the bound only decides "
    "whether one pair has enough evidence."
)


# --- 2D. the gate architecture -------------------------------------------------

ROLE_HARD = "HARD_APPROVAL_GATE"
ROLE_SOFT = "SOFT_WARNING_GATE"
ROLE_DIAGNOSTIC = "DIAGNOSTIC_ONLY"
ROLE_REMOVED = "REMOVED_FROM_V3"
GATE_ROLES = (ROLE_HARD, ROLE_SOFT, ROLE_DIAGNOSTIC, ROLE_REMOVED)

FINAL_GATE_ROLES = {
    _EXACT_METRIC: ROLE_SOFT,
    _WITHIN_1_METRIC: ROLE_DIAGNOSTIC,
    _WITHIN_2_METRIC: ROLE_DIAGNOSTIC,
    _STRUCTURAL_METRIC: ROLE_HARD,
    _BREAKOUT_METRIC: ROLE_DIAGNOSTIC,
    _RECLAIM_METRIC: ROLE_DIAGNOSTIC,
}

# Every metric answers the same four questions, and the role follows from the
# answers rather than from what the parent protocol happened to contain.
GATE_ARCHITECTURE = (
    {
        "metric": _STRUCTURAL_METRIC,
        "role": ROLE_HARD,
        "protects_against": (
            "A canonical reference whose weekly structural map differs from "
            "independent observable market references in ways that change "
            "downstream support and resistance state -- the failure mode that "
            "puts stops, invalidation levels and setup classification on a "
            "level the market did not make."
        ),
        "covered_by_another_gate": False,
        "coverage_reasoning": (
            "Nothing else in the protocol measures upstream structural "
            "difference. The Tier-4 gates measure the harm once it reaches a "
            "trade; this measures the cause, and a systematically different "
            "structural description can exist in a period whose trades happen "
            "not to expose it."
        ),
        "statistically_supportable": True,
        "support_reasoning": (
            "It has the largest comparable denominator of the six -- 22 to 29 "
            "events per pair per already-inspected sample -- and its rule is a "
            "per-pair confidence bound against an absolute limit, so it needs "
            "no cross-pair pooling and no equal-denominator derivation. The "
            "protocol's own hard `validation_period_days` minimum of 1460 days "
            "makes any admissible validation sample large enough for the bound "
            "to be informative at the development event density."
        ),
        "removing_the_hard_veto_would_weaken_protection": True,
        "weakening_reasoning": (
            "Demoting it would leave no gate at all on upstream structural "
            "difference, and the derived-level and Tier-4 evidence would then "
            "be certifying the consequences of a structurally different series "
            "rather than confirming a structurally equivalent one."
        ),
        "reason_codes": ("ECONOMICALLY_CONSEQUENTIAL_SUBSET", "SUPPORTABLE_DENOMINATOR"),
    },
    {
        "metric": _EXACT_METRIC,
        "role": ROLE_SOFT,
        "protects_against": (
            "A reference that labels weekly swings at different sessions from "
            "independent references even where no downstream state changed -- "
            "an early indication of a structurally different series."
        ),
        "covered_by_another_gate": True,
        "coverage_reasoning": (
            "It shares structural_state's denominator and its numerator is a "
            "superset of structural_state's on every one of the twelve "
            "measurements; structural_state is exactly the part of it that "
            "propagated. Two hard vetoes over one nested event set would be "
            "the same evidence counted twice, which the project's "
            "factor-separation rule refuses. What it adds beyond the hard gate "
            "is timing information that has not yet propagated, which is a "
            "reason to look rather than a reason to reject."
        ),
        "statistically_supportable": True,
        "support_reasoning": (
            "Same denominator as the hard gate, so it is measurable; but a "
            "label-level difference is not by itself economic harm, so its "
            "measurability does not make it an approval veto."
        ),
        "removing_the_hard_veto_would_weaken_protection": False,
        "weakening_reasoning": (
            "Every exact-timestamp disagreement that carries economic "
            "consequence is, by construction, also a structural_state event "
            "and is already vetoed. Those that carry none are labelling "
            "differences; rejecting a sound reference for them costs research "
            "and buys no protection."
        ),
        "reason_codes": ("NESTED_IN_A_SURVIVING_HARD_GATE", "LABEL_LEVEL_SIGNAL_ONLY"),
    },
    {
        "metric": _WITHIN_1_METRIC,
        "role": ROLE_DIAGNOSTIC,
        "protects_against": (
            "Exact-timestamp disagreement that is only a one-week shift of the "
            "same structure, which the metric is meant to forgive."
        ),
        "covered_by_another_gate": True,
        "coverage_reasoning": (
            "It is exact_timestamp with matched opposing pairs merged. No "
            "measurement in either already-inspected sample merges a pair, so "
            "on all twelve observations it is numerically identical to "
            "exact_timestamp and carries no separate information."
        ),
        "statistically_supportable": False,
        "support_reasoning": (
            "Its defining mechanism is never exercised by the evidence, so its "
            "own threshold is not separately identified. A number fixed here "
            "would be a number about exact_timestamp wearing another name."
        ),
        "removing_the_hard_veto_would_weaken_protection": False,
        "weakening_reasoning": (
            "A hard veto on a metric identical to a soft one is not extra "
            "protection; it is the same measurement given a second vote. The "
            "merge count and the calendar displacement of any pair that does "
            "merge stay published, so the mechanism becomes visible the moment "
            "it fires."
        ),
        "reason_codes": ("NOT_SEPARATELY_IDENTIFIED", "MECHANISM_NEVER_EXERCISED"),
    },
    {
        "metric": _WITHIN_2_METRIC,
        "role": ROLE_DIAGNOSTIC,
        "protects_against": (
            "Exact-timestamp disagreement that is a two-week shift of the same "
            "structure."
        ),
        "covered_by_another_gate": True,
        "coverage_reasoning": (
            "Identical position to within_1_week, at a wider tolerance: no "
            "measurement merges a pair, and the only opposing-side swing "
            "disagreement pair anywhere in the record is three weeks apart, "
            "outside both tolerances."
        ),
        "statistically_supportable": False,
        "support_reasoning": (
            "Not separately identified for the same reason, and its inherited "
            "0.02 was a round tail allowance never bound to any event universe."
        ),
        "removing_the_hard_veto_would_weaken_protection": False,
        "weakening_reasoning": (
            "Same as within_1_week. The tolerance ordering is preserved in the "
            "diagnostic, so a future sample that does merge pairs will show "
            "the two tolerances diverging from exact_timestamp before any "
            "threshold is written for them."
        ),
        "reason_codes": ("NOT_SEPARATELY_IDENTIFIED", "MECHANISM_NEVER_EXERCISED"),
    },
    {
        "metric": _BREAKOUT_METRIC,
        "role": ROLE_DIAGNOSTIC,
        "protects_against": (
            "A reference that confirms a breakout of a shared swing high that "
            "independent references do not, or in a different week."
        ),
        "covered_by_another_gate": True,
        "coverage_reasoning": (
            "A breakout difference from a swing the two series disagree about "
            "is already counted once by structural_state -- which is defined "
            "as exactly the swing disagreements that changed breakout or "
            "reclaim state. What remains here is a differing confirmation of a "
            "shared level, whose trade-level consequence is bounded hard and "
            "directly by the inherited Tier-4 stop, MFE/MAE, eligibility, "
            "action and setup-classification gates on hourly synchronized bars."
        ),
        "statistically_supportable": False,
        "support_reasoning": (
            "Zero disagreements over 39 pooled comparable events, on "
            "admissible pair denominators of 5 to 12. At a denominator of 12 "
            "and no disagreements the 95% upper bound is 0.2425, and at 9 it "
            "is 0.2991: the evidence cannot exclude a rate above any "
            "economically defensible limit for a derived level, so no "
            "certification is available at these denominators. Under the "
            "predecessor's relative alternative it was worse -- unidentifiable "
            "at every denominator, as Stage 1 reconfirms."
        ),
        "removing_the_hard_veto_would_weaken_protection": False,
        "weakening_reasoning": (
            "A rate gate that cannot certify on any realistic denominator "
            "delivers UNDEFINED, not protection. The events are economically "
            "meaningful, so V3 keeps them as a complete census with a hard "
            "requirement that every observed derived-level disagreement is "
            "individually reviewed and recorded -- which at these counts is a "
            "stronger control than a rate compared against a number nobody can "
            "defend."
        ),
        "reason_codes": (
            "DENOMINATOR_CANNOT_CERTIFY",
            "PROTECTION_RETAINED_AS_CENSUS_AND_TIER4",
        ),
    },
    {
        "metric": _RECLAIM_METRIC,
        "role": ROLE_DIAGNOSTIC,
        "protects_against": (
            "A reference that confirms a reclaim of a shared swing low that "
            "independent references do not, or in a different week."
        ),
        "covered_by_another_gate": True,
        "coverage_reasoning": (
            "Same position as breakout: propagated swing differences are "
            "already counted by structural_state, and the trade-level "
            "consequence of a differing confirmation is bounded by the "
            "inherited Tier-4 gates."
        ),
        "statistically_supportable": False,
        "support_reasoning": (
            "Three disagreements over 21 pooled comparable events, with "
            "admissible pair denominators of 2 to 6. At 5 comparable events "
            "even a zero numerator has a 95% upper bound of 0.4345, and 1/5 "
            "gives 0.6245. Nothing in that range is an economically "
            "defensible materiality limit for a derived level, and the "
            "non-sealed history that would enlarge the denominator does not "
            "exist."
        ),
        "removing_the_hard_veto_would_weaken_protection": False,
        "weakening_reasoning": (
            "Identical to breakout, and more so: reclaim is the one metric "
            "whose sparsity is genuine rather than an artefact of the "
            "objective, and it is precisely where a frequentist rate would "
            "invent precision. The census plus mandatory individual review "
            "keeps every event visible and accounted for."
        ),
        "reason_codes": (
            "DENOMINATOR_CANNOT_CERTIFY",
            "PROTECTION_RETAINED_AS_CENSUS_AND_TIER4",
        ),
    },
)

ARCHITECTURE_REASON_CODES = (
    "DENOMINATOR_CANNOT_CERTIFY",
    "ECONOMICALLY_CONSEQUENTIAL_SUBSET",
    "LABEL_LEVEL_SIGNAL_ONLY",
    "MECHANISM_NEVER_EXERCISED",
    "NESTED_IN_A_SURVIVING_HARD_GATE",
    "NOT_SEPARATELY_IDENTIFIED",
    "PROTECTION_RETAINED_AS_CENSUS_AND_TIER4",
    "SUPPORTABLE_DENOMINATOR",
)


def gate_architecture() -> tuple[dict[str, Any], ...]:
    """The six classifications, validated for completeness and consistency."""

    metrics = tuple(item["metric"] for item in GATE_ARCHITECTURE)
    if sorted(metrics) != sorted(AFFECTED_V2_GATE_METRICS):
        raise V3ConvergenceError(
            "the architecture must classify exactly the six structural metrics"
        )
    if len(set(metrics)) != len(metrics):
        raise V3ConvergenceError("a metric may carry exactly one role")
    for item in GATE_ARCHITECTURE:
        if item["role"] not in GATE_ROLES:
            raise V3ConvergenceError(f"unknown gate role {item['role']!r}")
        if FINAL_GATE_ROLES[item["metric"]] != item["role"]:
            raise V3ConvergenceError(
                f"{item['metric']!r} carries two different roles"
            )
        unknown = [
            code for code in item["reason_codes"] if code not in ARCHITECTURE_REASON_CODES
        ]
        if unknown:
            raise V3ConvergenceError(f"unknown architecture reason codes {unknown}")
        if item["role"] == ROLE_HARD and not item["statistically_supportable"]:
            raise V3ConvergenceError(
                f"{item['metric']!r} cannot be a hard gate it cannot support"
            )
        if item["role"] == ROLE_HARD and item["covered_by_another_gate"]:
            raise V3ConvergenceError(
                f"{item['metric']!r} would be a hard veto on covered ground"
            )
    return tuple(
        {**item, "reason_codes": list(item["reason_codes"])}
        for item in sorted(GATE_ARCHITECTURE, key=lambda entry: entry["metric"])
    )


# --- 2E. soft and diagnostic semantics -----------------------------------------

SOFT_OUTCOME_OK = "OK"
SOFT_OUTCOME_REVIEW_REQUIRED = "WARN_MANUAL_STRUCTURAL_REVIEW_REQUIRED"
SOFT_OUTCOMES = (SOFT_OUTCOME_OK, SOFT_OUTCOME_REVIEW_REQUIRED)

SOFT_GATE_SEMANTICS = {
    "cannot_reject_a_candidate_alone": True,
    "contributes_to_the_approval_verdict": False,
    "evidence_annotation": (
        "A warning is persisted on the approval record with the offending "
        "pairs, their rates and their reason codes, and travels with the "
        "record; an approval issued over a warning shows the warning."
    ),
    "manual_review_trigger": (
        "A warning makes a structured manual structural review mandatory "
        "before approval, in the form BTC-019 already uses for its 82 "
        "persisted review records. The review's outcome is recorded; it does "
        "not become a numeric gate."
    ),
    "measure": (
        "The observed point rate, not the confidence bound: a warning should "
        "fire readily, and a wide interval on thin evidence is itself a reason "
        "to look."
    ),
    "outcome_when_undefined": SOFT_OUTCOME_REVIEW_REQUIRED,
    "outcomes": list(SOFT_OUTCOMES),
    "rule": (
        "OK when every required gate pair is defined, admissible and at or "
        "below the absolute materiality limit on its observed point rate; "
        f"{SOFT_OUTCOME_REVIEW_REQUIRED} otherwise, including when a required "
        "pair is missing or undefined. The limit is the same absolute "
        "structural materiality limit, deliberately applied to the weaker "
        "label-level signal, so the soft gate is a strictly earlier trigger "
        "than the hard gate on the same evidence."
    ),
    "warning_only": True,
}

DIAGNOSTIC_SEMANTICS = {
    "can_veto_approval": False,
    "computed_and_persisted": True,
    "enforcement": (
        "The approval verdict is computed by `approval_verdict`, which reads "
        "hard-gate results only. Diagnostics live in a separate namespace that "
        "no verdict path consults, so a diagnostic value cannot change a "
        "verdict even if it is wrong."
    ),
    "required_fields": [
        "calendar_displacement_weeks",
        "comparable_event_count",
        "count",
        "matched_pair_count",
        "not_comparable_event_count",
        "not_comparable_reason_counts",
        "rate",
        "reason_codes",
    ],
    "rule": (
        "A diagnostic is measured, published per required pair and per sample, "
        "and reviewed. It never enters an approval verdict, never carries a "
        "threshold, and never has a pass or fail."
    ),
}


# --- 2F. comparability, hard ---------------------------------------------------

COMPARABILITY_POLICY_ID = "STRUCTURAL_COMPARABILITY_SUFFICIENCY_V2"
COMPARABILITY_FLOOR = MINIMUM_STRUCTURAL_COMPARABILITY_RATE

COMPARABILITY_POLICY = {
    "accepted_from_predecessor": True,
    "floor": str(COMPARABILITY_FLOOR),
    "hard": True,
    "principle": (
        "The measured set must be at least as large as the set the contract "
        "had to exclude. Below a half, the published rate describes a minority "
        "of the structure the pair actually detected, and that minority was "
        "selected by provider outage rather than by the market -- so a "
        "quieter comparison could be bought with more absent sessions."
    ),
    "why_not_higher": (
        "The other side of every gate pair is a raw provider whose "
        "availability this protocol does not gate; the parent's availability "
        "gates bind the candidate series only. A higher floor would make the "
        "evidence requirement turn on third-party outages rather than on the "
        "candidate, and the per-pair confidence bound already refuses a thin "
        "denominator on its own."
    ),
    "why_not_lower": (
        "A rate computed over a minority of its own detected events is not "
        "evidence of agreement; it is evidence of absence."
    ),
    "required_evidence": [
        "all_detected_event_count",
        "candidate_event_count",
        "comparable_event_count",
        "not_comparable_event_count",
        "not_comparable_rate",
        "not_comparable_reason_counts",
        "structural_comparability_rate",
    ],
    "required_gate_pair_count": REQUIRED_ADMISSIBLE_GATE_PAIR_COUNT,
    "rule": (
        "Every required gate pair must carry complete comparability evidence "
        "and a structural comparability rate at or above the floor. A pair "
        "below the floor is inadmissible and cannot certify any gate. A pair "
        "with no detected events at all has a null rate, never 0.0, and is "
        "insufficient."
    ),
    "zero_comparable_behaviour": (
        "UNDEFINED_INSUFFICIENT_EVIDENCE. A zero comparable denominator is "
        "never read as a zero disagreement rate."
    ),
    "invariant": "insufficient evidence can never approve; it can only refuse",
}


# --- 2G. derived-level protection, kept without a sparse rate gate -------------

DERIVED_LEVEL_PROTECTION_ID = "DERIVED_LEVEL_CENSUS_AND_TIER4_V1"

INHERITED_TIER4_HARD_GATES = (
    "stop_touch_disagreement_rate",
    "cross_market_confirmed_stop_preservation_rate",
    "isolated_venue_stop_suppression_rate",
    "gap_through_stop_consensus_agreement_rate",
    "mfe_median_absolute_difference",
    "mfe_p95_absolute_difference",
    "mae_median_absolute_difference",
    "mae_p95_absolute_difference",
    "trade_eligibility_disagreement_rate",
    "trade_action_disagreement_rate",
    "risk_size_p95_relative_difference",
    "regime_classification_disagreement_rate",
    "setup_classification_disagreement_rate",
)

UNREVIEWED_DERIVED_LEVEL_METRIC = "unreviewed_derived_level_disagreement_count"

DERIVED_LEVEL_PROTECTION = {
    "components": [
        {
            "component": "structural_state hard gate",
            "hard": True,
            "protection": (
                "The hard structural gate is itself defined as the swing "
                "disagreements that changed a breakout or reclaim state, so "
                "derived-level propagation is what it counts. Demoting the "
                "breakout and reclaim rate gates does not remove derived-level "
                "protection; the surviving hard gate is about derived-level "
                "propagation."
            ),
        },
        {
            "component": "hard comparability and coverage requirement",
            "hard": True,
            "protection": (
                "A derived-level comparison built on a gappy calendar is "
                "NOT_COMPARABLE by contract and is excluded from both numerator "
                "and denominator, and a pair whose measured set is a minority "
                "of its detected set cannot certify at all. A low rate bought "
                "with outages is refused before it is read."
            ),
        },
        {
            "component": "derived-level census with mandatory individual review",
            "hard": True,
            "metric": UNREVIEWED_DERIVED_LEVEL_METRIC,
            "protection": (
                "Every comparable breakout and reclaim disagreement observed "
                "on a required gate pair must carry a structured manual review "
                "with a recorded economic assessment, in the form BTC-019 "
                "already uses. The gate is a zero count, in the parent's own "
                "zero-count provenance idiom, not a calibrated rate: at 21 to "
                "39 comparable events a complete census that is individually "
                "reviewed is a stronger control than a rate compared against a "
                "threshold no one can defend."
            ),
        },
        {
            "component": "inherited Tier-4 stop and MFE/MAE sensitivity gates",
            "hard": True,
            "metrics": list(INHERITED_TIER4_HARD_GATES),
            "protection": (
                "These are the direct economic measurement of what a "
                "breakout or reclaim difference actually costs, on hourly "
                "synchronized bars with denominators three orders of magnitude "
                "larger than the weekly structural counts. They are inherited "
                "hard and unchanged, and they are what rejected Bitstamp."
            ),
        },
        {
            "component": "breakout and reclaim diagnostics",
            "hard": False,
            "protection": (
                "The full event census stays published per pair and per "
                "sample, with reasons, so a future sample that does produce a "
                "certifiable denominator can be read against this record "
                "without reopening the contract."
            ),
        },
    ],
    "failure_mode_addressed": (
        "Approval of a reference whose structural differences materially alter "
        "trading outcomes."
    ),
    "protection_id": DERIVED_LEVEL_PROTECTION_ID,
    "sparse_rate_gate_refused_because": (
        "At the observed denominators no threshold is simultaneously "
        "economically defensible and achievable, so a rate gate would publish "
        "either a number fitted to the sample or a permanent UNDEFINED. "
        "Neither is protection."
    ),
}


# --- 2H. the candidate-versus-provider transfer guard --------------------------

TRANSFER_GUARD_ID = "RAW_PROVIDER_STRUCTURAL_DISPERSION_CEILING_V1"

GUARD_SATISFIED = "GUARD_SATISFIED"
GUARD_FAILED = "GUARD_FAILED"
GUARD_UNDEFINED = "GUARD_UNDEFINED_INSUFFICIENT_EVIDENCE"
GUARD_OUTCOMES = (GUARD_SATISFIED, GUARD_FAILED, GUARD_UNDEFINED)

TRANSFER_GUARD = {
    "aggregation": AGGREGATION_ID,
    "computed_on": "INDEPENDENT_RAW_PROVIDER_PAIRS_V1",
    "depends_on_the_candidate": False,
    "failure_mode_blocked": (
        "The candidate is the element-wise median of the same three providers "
        "it is compared against, so median(A,B,C) against A, B or C is "
        "mechanically closer than A against B. A composite could therefore "
        "certify every gate pair merely because it is an arithmetic function "
        "of those pairs' own inputs, while the underlying providers do not "
        "agree about market structure at all. In that state 'the market "
        "structure' is not identified in the period, and no median of the "
        "three can be certified as a canonical description of it, however "
        "close it sits to each input."
    ),
    "guard_id": TRANSFER_GUARD_ID,
    "hard": True,
    "measure": _STRUCTURAL_METRIC,
    "outcomes": list(GUARD_OUTCOMES),
    "rule": (
        "Every unordered pair of distinct independent raw validation "
        "providers must itself certify the structural_state metric, under the "
        "same absolute materiality limit and the same per-pair confidence "
        "bound as the gate pairs, on the same sample and the same comparison "
        "contract. GUARD_FAILED when any provider pair is a material failure; "
        "GUARD_UNDEFINED_INSUFFICIENT_EVIDENCE when any is missing, "
        "inadmissible, undefined or insufficient; GUARD_SATISFIED only when "
        "all of them certify."
    ),
    "why_this_and_not_a_looser_measure": (
        "Every input is a series the candidate is not built from on that "
        "pair's own side, so no arrangement of the median can satisfy the "
        "guard: it is arithmetically impossible for candidate construction to "
        "influence a provider-versus-provider measurement. That is the "
        "property the review's missing guard needed, and a cosmetic guard "
        "computed on candidate pairs would not have it."
    ),
    "why_the_certification_rule_and_not_the_point_rate": (
        "The architecture's invariant is that insufficient evidence cannot "
        "approve. Reading the guard off point estimates would let thin "
        "provider evidence satisfy it silently, which is exactly the leniency "
        "the review identified."
    ),
    "why_not_leave_one_provider_influence": (
        "A leave-one-out dominance diagnostic would require constructing three "
        "alternative composites, which is new candidate-construction semantics "
        "this task may not introduce. It also blocks a narrower mode: with "
        "three providers the median tracking two that agree is the intended "
        "behaviour of a median, not a defect, and the case where that becomes "
        "arbitrary is exactly high raw dispersion, which this guard already "
        "refuses."
    ),
}


# --- 2I. evaluating the architecture -------------------------------------------


def evaluate_hard_structural_gate(
    measurements: Mapping[str, Mapping[str, Any] | None],
    *,
    required_pairs: Sequence[str],
    limit: Decimal = STRUCTURAL_MATERIALITY_LIMIT,
    quantile: Decimal = NORMAL_QUANTILE_0_975,
    comparability_floor: Decimal = COMPARABILITY_FLOOR,
) -> dict[str, Any]:
    """Aggregate the hard structural gate over its required pairs."""

    if not required_pairs:
        raise V3ConvergenceError("a hard gate needs at least one required pair")
    certifications = [
        certify_pair(
            measurements.get(comparison_id),
            comparison_id=comparison_id,
            limit=limit,
            quantile=quantile,
            comparability_floor=comparability_floor,
        )
        for comparison_id in sorted(required_pairs)
    ]
    outcomes = [item.outcome for item in certifications]
    if PAIR_MATERIAL_FAILURE in outcomes:
        verdict = GATE_FAIL
    elif all(outcome == PAIR_CERTIFIED for outcome in outcomes):
        verdict = GATE_PASS
    else:
        verdict = GATE_INSUFFICIENT
    return {
        "aggregation": AGGREGATION_ID,
        "certified_pair_count": outcomes.count(PAIR_CERTIFIED),
        "limit": str(limit),
        "metric": _STRUCTURAL_METRIC,
        "pairs": [item.as_record() for item in certifications],
        "required_pair_count": len(required_pairs),
        "role": ROLE_HARD,
        "verdict": verdict,
    }


def evaluate_soft_gate(
    measurements: Mapping[str, Mapping[str, Any] | None],
    *,
    required_pairs: Sequence[str],
    limit: Decimal = STRUCTURAL_MATERIALITY_LIMIT,
    comparability_floor: Decimal = COMPARABILITY_FLOOR,
) -> dict[str, Any]:
    """Evaluate the soft exact-timestamp warning gate. It never rejects."""

    rows: list[dict[str, Any]] = []
    warn = False
    for comparison_id in sorted(required_pairs):
        measurement = measurements.get(comparison_id)
        if measurement is None:
            warn = True
            rows.append(
                {
                    "comparison_id": comparison_id,
                    "denominator": None,
                    "numerator": None,
                    "over_limit": None,
                    "rate": None,
                    "reason_codes": [CERTIFICATION_REASON_REQUIRED_PAIR_ABSENT],
                }
            )
            continue
        reasons: list[str] = []
        if measurement.get("state") != PAIR_ADMISSIBLE:
            reasons.append(CERTIFICATION_REASON_PAIR_INADMISSIBLE)
        comparability = measurement.get("structural_comparability_rate")
        if comparability is None:
            reasons.append(CERTIFICATION_REASON_PAIR_INADMISSIBLE)
        elif Decimal(comparability) < comparability_floor:
            reasons.append(CERTIFICATION_REASON_BELOW_COMPARABILITY_FLOOR)
        rate = exact_rate(measurement["numerator"], measurement["denominator"])
        if rate is None:
            reasons.append(CERTIFICATION_REASON_NO_COMPARABLE_EVENTS)
            over = None
        else:
            over = rate > limit
            if over:
                reasons.append(CERTIFICATION_REASON_RATE_EXCEEDS_LIMIT)
        if reasons:
            warn = True
        rows.append(
            {
                "comparison_id": comparison_id,
                "denominator": measurement["denominator"],
                "numerator": measurement["numerator"],
                "over_limit": over,
                "rate": None if rate is None else str(_REPORT_CONTEXT.plus(rate)),
                "reason_codes": sorted(set(reasons)),
            }
        )
    return {
        "cannot_reject_alone": True,
        "contributes_to_the_approval_verdict": False,
        "limit": str(limit),
        "metric": _EXACT_METRIC,
        "outcome": SOFT_OUTCOME_REVIEW_REQUIRED if warn else SOFT_OUTCOME_OK,
        "pairs": rows,
        "role": ROLE_SOFT,
    }


def evaluate_transfer_guard(
    measurements: Mapping[str, Mapping[str, Any] | None],
    *,
    limit: Decimal = STRUCTURAL_MATERIALITY_LIMIT,
    quantile: Decimal = NORMAL_QUANTILE_0_975,
    comparability_floor: Decimal = COMPARABILITY_FLOOR,
) -> dict[str, Any]:
    """Evaluate the raw-provider structural dispersion ceiling."""

    required = sorted(
        "_vs_".join(pair) for pair in calibration_pair_universe()
    )
    certifications = [
        certify_pair(
            measurements.get(comparison_id),
            comparison_id=comparison_id,
            limit=limit,
            quantile=quantile,
            comparability_floor=comparability_floor,
        )
        for comparison_id in required
    ]
    outcomes = [item.outcome for item in certifications]
    if PAIR_MATERIAL_FAILURE in outcomes:
        outcome = GUARD_FAILED
    elif all(item == PAIR_CERTIFIED for item in outcomes):
        outcome = GUARD_SATISFIED
    else:
        outcome = GUARD_UNDEFINED
    return {
        "guard_id": TRANSFER_GUARD_ID,
        "limit": str(limit),
        "measure": _STRUCTURAL_METRIC,
        "outcome": outcome,
        "pairs": [item.as_record() for item in certifications],
        "required_pair_count": len(required),
    }


def approval_verdict(
    *,
    hard_gate: Mapping[str, Any],
    transfer_guard: Mapping[str, Any],
    comparability_satisfied: bool,
    unreviewed_derived_level_disagreement_count: int,
    tier4_hard_gates_passed: bool,
) -> dict[str, Any]:
    """Compose the approval verdict from hard evidence only.

    Nothing soft and nothing diagnostic is a parameter of this function, so a
    diagnostic or a warning cannot change a verdict by any route.
    """

    if unreviewed_derived_level_disagreement_count < 0:
        raise V3ConvergenceError("a review backlog cannot be negative")
    blocking: list[str] = []
    failing: list[str] = []
    if hard_gate["verdict"] == GATE_FAIL:
        failing.append(_STRUCTURAL_METRIC)
    elif hard_gate["verdict"] != GATE_PASS:
        blocking.append(_STRUCTURAL_METRIC)
    if transfer_guard["outcome"] == GUARD_FAILED:
        failing.append(TRANSFER_GUARD_ID)
    elif transfer_guard["outcome"] != GUARD_SATISFIED:
        blocking.append(TRANSFER_GUARD_ID)
    if not comparability_satisfied:
        blocking.append(COMPARABILITY_POLICY_ID)
    if unreviewed_derived_level_disagreement_count:
        blocking.append(UNREVIEWED_DERIVED_LEVEL_METRIC)
    if not tier4_hard_gates_passed:
        failing.append("inherited_tier4_hard_gates")
    if failing:
        verdict = GATE_FAIL
    elif blocking:
        verdict = GATE_INSUFFICIENT
    else:
        verdict = GATE_PASS
    return {
        "blocking": sorted(blocking),
        "failing": sorted(failing),
        "inputs_are_hard_evidence_only": True,
        "verdict": verdict,
    }


# --- 2J. observed dispersion, the realism check, and sensitivity ----------------

SENSITIVITY_ID = "GOVERNANCE_ASSUMPTION_SENSITIVITY_V1"
MATERIALITY_NEIGHBOURHOOD = (
    Decimal("0.10"),
    Decimal("0.15"),
    Decimal("0.20"),
    Decimal("0.25"),
    Decimal("0.30"),
)
COMPARABILITY_NEIGHBOURHOOD = (
    Decimal("0.40"),
    Decimal("0.50"),
    Decimal("0.60"),
    Decimal("0.75"),
)
DENOMINATOR_IMBALANCE_PROBES = (
    (16, 16, 16),
    (16, 30, 60),
    (20, 25, 30),
    (12, 40, 40),
)
_CERTIFYING_DENOMINATOR_CEILING = 5000


REALISM_CHECK_ID = "OBSERVED_DEVELOPMENT_DISPERSION_REALISM_CHECK_V1"

REALISM_CHECK_ROLE = (
    "The materiality limit is declared from economic consequence. This check "
    "runs afterwards and reports only whether that limit is realistic against "
    "legitimate independent-source variation. It cannot move the limit: had it "
    "failed -- had legitimate providers routinely exceeded the limit -- the "
    "conclusion would have been that the metric cannot be a hard gate, not "
    "that the limit should be raised."
)


def observed_development_dispersion(
    measured: Mapping[str, Mapping[str, Sequence[Mapping[str, Any]]]],
    metric: str,
) -> dict[str, Any]:
    """Descriptive per-pair dispersion. No inference is drawn across pairs."""

    rows = []
    worst: Decimal | None = None
    total_numerator = 0
    total_denominator = 0
    for row in _rows(measured, metric):
        rate = exact_rate(row["numerator"], row["denominator"])
        upper = wilson_upper_bound(row["numerator"], row["denominator"])
        total_numerator += row["numerator"]
        total_denominator += row["denominator"]
        if rate is not None and (worst is None or rate > worst):
            worst = rate
        rows.append(
            {
                "admissibility": row["state"],
                "comparison_id": row["comparison_id"],
                "denominator": row["denominator"],
                "numerator": row["numerator"],
                "rate": None if rate is None else str(_REPORT_CONTEXT.plus(rate)),
                "sample_dir": row["sample_dir"],
                "structural_comparability_rate": row["structural_comparability_rate"],
                "wilson_95_upper": (
                    None if upper is None else str(_REPORT_CONTEXT.plus(upper))
                ),
            }
        )
    aggregate = exact_rate(total_numerator, total_denominator)
    return {
        "aggregate_count": f"{total_numerator}/{total_denominator}",
        "aggregate_is_descriptive_only": True,
        "aggregate_rate": (
            None if aggregate is None else str(_REPORT_CONTEXT.plus(aggregate))
        ),
        "measurements": rows,
        "metric": metric,
        "no_interval_is_computed_on_the_aggregate": (
            "The rows share underlying structural events -- one market fact "
            "can appear in two or three of them -- so the aggregate is a count "
            "of observations, not an estimate with a sampling distribution. No "
            "band is read off it and no threshold depends on it."
        ),
        "worst_pair_rate": None if worst is None else str(_REPORT_CONTEXT.plus(worst)),
    }


def gate_viability(
    measured: Mapping[str, Mapping[str, Sequence[Mapping[str, Any]]]],
    metric: str,
    *,
    limit: Decimal,
) -> dict[str, Any]:
    """Could this metric carry a hard gate at ``limit``, on this evidence?

    Viability is asked of the gate, not of one measurement: a hard gate needs
    every required pair to certify, so a metric is viable at a limit only when
    some already-inspected sample has all three of its provider pairs
    certifying there, and no legitimate pair anywhere exceeds the limit. The
    development pairs stand in for gate pairs here only as a feasibility
    question about denominators -- the candidate is never involved.
    """

    exceeding: list[str] = []
    by_sample: dict[str, bool] = {}
    for sample_dir in sorted(measured[metric]):
        certified = 0
        for row in measured[metric][sample_dir]:
            certification = certify_pair(
                row, comparison_id=row["comparison_id"], limit=limit
            )
            if certification.outcome == PAIR_MATERIAL_FAILURE:
                exceeding.append(f"{sample_dir}:{row['comparison_id']}")
            if certification.outcome == PAIR_CERTIFIED:
                certified += 1
        by_sample[sample_dir] = certified >= REQUIRED_ADMISSIBLE_GATE_PAIR_COUNT
    return {
        "all_pairs_certify_by_sample": dict(sorted(by_sample.items())),
        "limit": str(limit),
        "measurements_exceeding_the_limit": sorted(exceeding),
        "metric": metric,
        "viable": not exceeding and any(by_sample.values()),
    }


def viability_boundary(
    measured: Mapping[str, Mapping[str, Sequence[Mapping[str, Any]]]],
    metric: str,
    *,
    grid: Sequence[Decimal] = MATERIALITY_NEIGHBOURHOOD,
) -> str | None:
    """The tightest limit on the grid at which this metric could be hard."""

    for limit in sorted(grid):
        if gate_viability(measured, metric, limit=limit)["viable"]:
            return str(limit)
    return None


def realism_check(
    measured: Mapping[str, Mapping[str, Sequence[Mapping[str, Any]]]],
    *,
    limit: Decimal = STRUCTURAL_MATERIALITY_LIMIT,
) -> dict[str, Any]:
    """Is the declared limit realistic against legitimate source variation?

    Two things have to hold, and they pull in opposite directions. No
    legitimate independent-provider pair may exceed the limit -- otherwise a
    sound reference would be rejected for behaving like the market's own
    sources. And the limit has to be attainable at realistic denominators --
    otherwise the gate returns insufficient evidence forever, which is
    fail-closed but is not a gate. A limit that fails either test cannot carry
    a hard gate; the answer is never to move the limit to fit.
    """

    dispersion = observed_development_dispersion(measured, _STRUCTURAL_METRIC)
    worst = dispersion["worst_pair_rate"]
    exceeding = [
        row
        for row in dispersion["measurements"]
        if row["rate"] is not None and Decimal(row["rate"]) > limit
    ]
    certifying = [
        row
        for row in dispersion["measurements"]
        if row["wilson_95_upper"] is not None
        and Decimal(row["wilson_95_upper"]) <= limit
    ]
    viability = gate_viability(measured, _STRUCTURAL_METRIC, limit=limit)
    if exceeding:
        conclusion = "NOT_REALISTIC_LEGITIMATE_SOURCES_EXCEED_THE_LIMIT"
    elif not viability["viable"]:
        conclusion = "NOT_REALISTIC_LIMIT_UNATTAINABLE_AT_REALISTIC_DENOMINATORS"
    else:
        conclusion = "REALISTIC"
    return {
        "attainable": viability["viable"],
        "certifying_measurement_count": len(certifying),
        "check_id": REALISM_CHECK_ID,
        "conclusion": conclusion,
        "gate_viability": viability,
        "legitimate_measurement_count": len(dispersion["measurements"]),
        "limit": str(limit),
        "measurements_exceeding_the_limit": [
            row["comparison_id"] for row in exceeding
        ],
        "role": REALISM_CHECK_ROLE,
        "statement": (
            "No independent raw-provider pair's observed structural_state rate "
            f"reaches the limit; the worst is {worst}. "
            f"{len(certifying)} of {len(dispersion['measurements'])} "
            "measurements also certify it outright at their own development "
            "denominators, and at least one already-inspected sample has all "
            "three of its pairs certifying, so the limit is attainable and not "
            "only unexceeded."
        )
        if conclusion == "REALISTIC"
        else (
            "The limit is not realistic: either a legitimate independent "
            "provider pair exceeds it, or no sample can certify every required "
            "pair at it. Either way the metric cannot carry a hard gate at "
            "this limit."
        ),
        "worst_pair_rate": worst,
    }




def minimum_certifying_denominator(
    disagreements: int,
    *,
    limit: Decimal,
    quantile: Decimal = NORMAL_QUANTILE_0_975,
) -> int | None:
    """Smallest denominator at which `disagreements` still certifies."""

    if disagreements < 0:
        raise V3ConvergenceError("a count cannot be negative")
    size = max(disagreements, 1)
    while size <= _CERTIFYING_DENOMINATOR_CEILING:
        bound = wilson_upper_bound(disagreements, size, quantile=quantile)
        if bound is not None and bound <= limit:
            return size
        size += 1
    return None


def sensitivity_surface(
    measured: Mapping[str, Mapping[str, Sequence[Mapping[str, Any]]]],
) -> dict[str, Any]:
    """Vary the governance assumptions that actually matter, not the verdicts.

    The predecessor's stability check compared historical PASS/FAIL labels
    across thresholds that were all far above every observed rate, so all three
    verdict sets were identical by construction and the check could not fail.
    What has to be robust here is the *policy conclusion*, and the conclusion
    is an ordering: structural_state can carry a hard gate at a limit where the
    derived-level metrics cannot. So the neighbourhood is swept for each
    metric's viability boundary -- the tightest limit at which it could carry a
    hard gate on evidence of this shape -- and the conclusion is stable when
    that ordering survives, not when a historical label does.
    """

    boundaries = {
        metric: viability_boundary(measured, metric)
        for metric in (_STRUCTURAL_METRIC, _BREAKOUT_METRIC, _RECLAIM_METRIC)
    }
    materiality_rows = []
    for limit in MATERIALITY_NEIGHBOURHOOD:
        minima = {
            str(count): minimum_certifying_denominator(count, limit=limit)
            for count in range(4)
        }
        structural = realism_check(measured, limit=limit)
        derived = {
            metric: gate_viability(measured, metric, limit=limit)["viable"]
            for metric in (_BREAKOUT_METRIC, _RECLAIM_METRIC)
        }
        materiality_rows.append(
            {
                "derived_level_metrics_viable": dict(sorted(derived.items())),
                "limit": str(limit),
                "minimum_certifying_denominator_by_disagreement_count": minima,
                "structural_state_certifying_measurement_count": structural[
                    "certifying_measurement_count"
                ],
                "structural_state_realism": structural["conclusion"],
                "structural_state_viable": structural["gate_viability"]["viable"],
            }
        )
    uncertainty_rows = []
    for level in sorted(CONFIDENCE_LEVELS):
        quantile = CONFIDENCE_LEVELS[level]
        uncertainty_rows.append(
            {
                "confidence_level_percent": level,
                "minimum_certifying_denominator_by_disagreement_count": {
                    str(count): minimum_certifying_denominator(
                        count, limit=STRUCTURAL_MATERIALITY_LIMIT, quantile=quantile
                    )
                    for count in range(4)
                },
                "quantile": str(quantile),
            }
        )
    comparability_rows = []
    dispersion = observed_development_dispersion(measured, _STRUCTURAL_METRIC)
    for floor in COMPARABILITY_NEIGHBOURHOOD:
        admissible = [
            row
            for row in dispersion["measurements"]
            if row["structural_comparability_rate"] is not None
            and Decimal(row["structural_comparability_rate"]) >= floor
        ]
        comparability_rows.append(
            {
                "admissible_measurement_count": len(admissible),
                "floor": str(floor),
                "measurement_count": len(dispersion["measurements"]),
                "structural_state_viable": gate_viability(
                    measured, _STRUCTURAL_METRIC, limit=STRUCTURAL_MATERIALITY_LIMIT
                )["viable"],
            }
        )
    imbalance_rows = []
    for denominators in DENOMINATOR_IMBALANCE_PROBES:
        rows = {
            f"pair_{index}": certify_pair(
                {
                    "numerator": 0,
                    "denominator": size,
                    "structural_comparability_rate": "1",
                    "state": PAIR_ADMISSIBLE,
                },
                comparison_id=f"pair_{index}",
            ).outcome
            for index, size in enumerate(denominators)
        }
        imbalance_rows.append(
            {
                "denominators": list(denominators),
                "each_pair_judged_on_its_own_denominator": True,
                "outcomes": dict(sorted(rows.items())),
            }
        )
    structural_boundary = boundaries[_STRUCTURAL_METRIC]
    derived_boundaries = [
        boundaries[_BREAKOUT_METRIC],
        boundaries[_RECLAIM_METRIC],
    ]
    ordering_holds = structural_boundary is not None and all(
        boundary is None or Decimal(structural_boundary) < Decimal(boundary)
        for boundary in derived_boundaries
    )
    declared_row = next(
        row
        for row in materiality_rows
        if Decimal(row["limit"]) == STRUCTURAL_MATERIALITY_LIMIT
    )
    declared_holds = declared_row["structural_state_viable"] and not any(
        declared_row["derived_level_metrics_viable"].values()
    )
    return {
        "comparability_floor_neighbourhood": comparability_rows,
        "declared_limit_conclusion_holds": declared_holds,
        "denominator_imbalance": imbalance_rows,
        "materiality_neighbourhood": materiality_rows,
        "policy_conclusion_stable": bool(ordering_holds and declared_holds),
        "sensitivity_id": SENSITIVITY_ID,
        "statement": (
            "The architecture, not a historical verdict label, is what is "
            "tested. structural_state can carry a hard gate from "
            f"{structural_boundary} onwards; breakout only from "
            f"{boundaries[_BREAKOUT_METRIC]} and reclaim nowhere on the "
            "neighbourhood at all. That ordering is what the demotions rest "
            "on, and it is not a property of the declared limit: no limit in "
            "the neighbourhood reverses it. The limit does change what "
            "evidence the hard gate demands -- at 0.10 a clean pair needs 35 "
            "comparable events and no development sample can certify all "
            "three pairs, which is the boundary at which structural_state "
            "would itself stop being a viable hard gate. Denominator "
            "imbalance changes nothing, because the rule is evaluated per "
            "pair on that pair's own counts."
        ),
        "uncertainty_treatment_neighbourhood": uncertainty_rows,
        "viability_boundaries": dict(sorted(boundaries.items())),
    }


# =============================================================================
# STAGE 3 -- the frozen protocol
# =============================================================================

REPLACED_PARENT_GATES = tuple(sorted(AFFECTED_V2_GATE_METRICS))

NEW_HARD_REQUIREMENTS = (
    "structural_comparability_rate",
    "required_gate_pair_count",
    "unrecorded_not_comparable_event_count",
    UNREVIEWED_DERIVED_LEVEL_METRIC,
    "raw_provider_structural_dispersion_guard",
)

MATERIAL_CHANGE_REQUIRES = "BTC_REFERENCE_COMPOSITE_V4 or later"

FUTURE_VALIDATOR_REQUIREMENT = {
    "authorized_after": (
        "this frozen definition receives its own independent xHigh review"
    ),
    "must_bind": "the BTC_REFERENCE_COMPOSITE_V3 definition_sha256 in this artifact",
    "must_not_bind": "the parent BTC_REFERENCE_COMPOSITE_V2 hash",
    "sealed_sample_may_be_collected": False,
    "sealed_sample_may_be_opened": False,
    "sequence": [
        "independent xHigh review of this frozen definition",
        "build the validator bound to this definition hash",
        "collect 2015-07-20..2019-11-30",
        "open the sealed sample exactly once",
        "evaluate the candidate against this definition",
        "only then may PRICE_SOURCE_POLICY_V2 and a BTC-019 closure be written",
    ],
}


def sealed_window_guard_holds() -> bool:
    """Confirm the inherited guard still refuses the sealed window itself.

    This is a containment check, not an access: the guard is asked about the
    declared boundaries and must raise. Anything else means the seal has been
    weakened somewhere upstream, and this task must not freeze a protocol on
    top of that.
    """

    try:
        guard_untouched_validation_sample(
            start=UNTOUCHED_OOS_START,
            end=UNTOUCHED_OOS_END,
            purpose=f"{CONVERGENCE_VERSION} sealed-window containment check",
        )
    except UntouchedValidationSampleGuardError:
        return True
    return False


def _sealed_sample_block() -> dict[str, Any]:
    if not sealed_window_guard_holds():
        raise V3ConvergenceError(
            "the inherited sealed-sample guard no longer refuses its own window"
        )
    return {
        "collected": False,
        "end": UNTOUCHED_OOS_END.isoformat(),
        "guard": "guard_untouched_validation_sample, inherited unchanged",
        "guard_refuses_the_sealed_window": True,
        "inspected": False,
        "opened": False,
        "start": UNTOUCHED_OOS_START.isoformat(),
        "status": "SEALED_UNOPENED",
        "used_in_this_task": False,
    }


def v3_protocol_definition(repository_root: Path) -> dict[str, Any]:
    """Build the complete frozen BTC_REFERENCE_COMPOSITE_V3 definition and hash it.

    Deterministic from module constants plus the frozen parent artifact, so it
    reproduces in a tree that holds no collected history at all. No measured
    rate enters it: the protocol is governance, and the evidence lives in the
    convergence record beside it.
    """

    parent = frozen_parent_definition(repository_root)
    proposal = successor_protocol_definition(repository_root)
    parent_gates = {item["metric"]: item for item in parent["approval_gates"]}
    inherited = [
        {
            "direction": gate["direction"],
            "hard": gate["hard"],
            "inherited_unchanged": True,
            "metric": metric,
            "threshold": gate["threshold"],
        }
        for metric, gate in sorted(parent_gates.items())
        if metric not in AFFECTED_V2_GATE_METRICS
    ]
    structural = [item for item in gate_architecture()]
    payload: dict[str, Any] = {
        "candidate": {
            "candidate_construction": (
                "Unchanged from the parent: the element-wise median of every "
                "provider value available at the fixed composite decision "
                "time, its quality-state semantics, its point-in-time contract "
                "and its higher-timeframe aggregation rules. V3 changes how "
                "the candidate is measured, never how it is built."
            ),
            "candidate_construction_changed": False,
            "candidate_series_id": V2_METHOD_VERSION,
            "method_version": V2_METHOD_VERSION,
            "minimum_provider_count": parent["providers"]["minimum_provider_count"],
            "provider_set": list(REQUIRED_POLICY_PROVIDER_IDS),
            "single_venue_fallback_allowed": parent["providers"][
                "single_venue_fallback_allowed"
            ],
        },
        "comparability_policy": {
            **COMPARABILITY_POLICY,
            "policy_id": COMPARABILITY_POLICY_ID,
        },
        "comparison_contract_version": COMPARISON_CONTRACT_VERSION,
        "convergence_version": CONVERGENCE_VERSION,
        "denominator_semantics_version": DENOMINATOR_SEMANTICS_VERSION,
        "dependence_treatment": {
            "assumptions_removed": list(DEPENDENCE_TREATMENT),
            "family_wise_probability_multiplied": False,
            "pair_independence_assumed": False,
            "treatment_id": DEPENDENCE_TREATMENT_ID,
            "within_pair_disclosure": WITHIN_PAIR_DEPENDENCE_DISCLOSURE,
        },
        "derived_level_protection": DERIVED_LEVEL_PROTECTION,
        "diagnostic_semantics": DIAGNOSTIC_SEMANTICS,
        "gate_architecture": {
            "aggregation": {
                "aggregation_id": AGGREGATION_ID,
                "rule": AGGREGATION_RULE,
                "verdicts": list(GATE_VERDICTS),
            },
            "certification_rule": {
                "confidence_level_percent": CERTIFICATION_CONFIDENCE_LEVEL,
                "equality_behaviour": (
                    "Equality certifies. A rate exactly at the limit passes and "
                    "an upper bound exactly at the limit certifies, matching "
                    "the repository's inclusive gate-boundary convention."
                ),
                "normal_quantile": str(NORMAL_QUANTILE_0_975),
                "outcomes": list(PAIR_OUTCOMES),
                "properties": list(CERTIFICATION_RULE_PROPERTIES),
                "reason_codes": list(CERTIFICATION_REASON_CODES),
                "rule": CERTIFICATION_RULE,
                "rule_id": CERTIFICATION_RULE_ID,
            },
            "diagnostic_metrics": sorted(
                metric
                for metric, role in FINAL_GATE_ROLES.items()
                if role == ROLE_DIAGNOSTIC
            ),
            "hard_metrics": sorted(
                metric for metric, role in FINAL_GATE_ROLES.items() if role == ROLE_HARD
            ),
            "insufficient_evidence_behaviour": (
                "UNDEFINED_INSUFFICIENT_EVIDENCE, which cannot approve. "
                "Insufficient evidence never becomes a pass and never becomes "
                "a rate of 0.0."
            ),
            "metrics": structural,
            "removed_metrics": [],
            "roles": dict(sorted(FINAL_GATE_ROLES.items())),
            "soft_metrics": sorted(
                metric for metric, role in FINAL_GATE_ROLES.items() if role == ROLE_SOFT
            ),
        },
        "gate_pair_universe": {
            "admissibility": (
                "A pair is admissible when both series carry their declared "
                "roles, the measurement was produced by this comparison "
                "contract and this detector version under "
                f"{PRICE_SOURCE_POLICY_VERSION}, and its structural "
                "comparability rate is at or above the floor. An inadmissible "
                "pair is never dropped: it is recorded and makes its gate "
                "insufficient."
            ),
            "aggregation": AGGREGATION_ID,
            "calibration_pairs": sorted(
                "_vs_".join(pair) for pair in calibration_pair_universe()
            ),
            "gate_pairs": sorted("_vs_".join(pair) for pair in gate_pair_universe()),
            "pair_roles": {
                "APPROVAL_GATE_PAIR": (
                    "one candidate series against one independent raw "
                    "validation provider; the only evidence that decides the "
                    "candidate"
                ),
                "SOURCE_DISPERSION_GUARD_PAIR": (
                    "two distinct independent raw validation providers; "
                    "evidence about whether market structure is identified at "
                    "all, and the transfer guard's whole input"
                ),
            },
            "required_gate_pair_count": REQUIRED_ADMISSIBLE_GATE_PAIR_COUNT,
            "universe_id": "CANDIDATE_VERSUS_INDEPENDENT_RAW_PROVIDER_PAIRS_V1",
        },
        "hypothesis": parent["hypothesis"],
        "inherited_approval_gates": inherited,
        "inherited_unchanged_from_parent": [
            "MEDIAN_OHLC_V2 candidate construction",
            "the quality-state semantics",
            "the higher-timeframe aggregation contract",
            "the point-in-time contract",
            "the provider set, instruments and minimum provider count",
            "the ATR materiality grid and its 0.50 primary threshold",
            "the live-shadow requirement",
            "every parent approval gate except the six structural rate gates",
            "the sealed-sample guard and its window",
        ],
        "materiality": {
            "absolute_limit": str(STRUCTURAL_MATERIALITY_LIMIT),
            "applies_to": _STRUCTURAL_METRIC,
            "derivation": list(MATERIALITY_DERIVATION),
            "direction": "maximum",
            "independent_of_observation": MATERIALITY_INDEPENDENT_OF_OBSERVATION,
            "policy_id": MATERIALITY_POLICY_ID,
            "refused_derivations": list(REJECTED_MATERIALITY_DERIVATIONS),
            "relative_alternative_retained": False,
            "statement": MATERIALITY_STATEMENT,
        },
        "material_change_requires": MATERIAL_CHANGE_REQUIRES,
        "metric_definitions": proposal["structural_metrics"],
        "new_hard_requirements": list(NEW_HARD_REQUIREMENTS),
        "not_comparable_semantics": {
            "excluded_from_numerator_and_denominator": True,
            "reason": (
                "An unevaluable event is neither an agreement nor a "
                "disagreement. Counting it as agreement would make every extra "
                "outage buy a free agreement."
            ),
            "states": proposal["not_comparable_states"],
            "unrecorded_not_comparable_event_count": {
                "direction": "equal",
                "hard": True,
                "threshold": 0,
            },
        },
        "parent_definition_sha256": PARENT_DEFINITION_SHA256,
        "parent_protocol_version": V2_PROTOCOL_VERSION,
        "predecessor_governance": {
            "calibration_review_commit": PREDECESSOR_CALIBRATION_REVIEW_COMMIT,
            "calibration_version": PREDECESSOR_CALIBRATION_VERSION,
            "convergence_boundary": CONVERGENCE_BOUNDARY,
            "denominator_semantics_version": DENOMINATOR_SEMANTICS_VERSION,
            "proposed_definition_sha256": proposal["definition_sha256"],
        },
        "price_source_policy_version": PRICE_SOURCE_POLICY_VERSION,
        "production_promotion_authorized": False,
        "reference_policy_version": V3_PROTOCOL_VERSION,
        "research_only": True,
        "sample_governance": {
            "development_evidence_is_not_out_of_sample": True,
            "already_inspected_samples": [
                "data/btc019/2023-01-01_2025-12-31",
                "data/btc_reference_composite_v1/external_2019-12-01_2022-12-31",
            ],
            "sealed_sample": _sealed_sample_block(),
            "validation_sample": (
                "the sealed 2015-07-20..2019-11-30 window, opened exactly once "
                "by a validator bound to this definition hash"
            ),
        },
        "schema_version": V3_PROTOCOL_SCHEMA_VERSION,
        "soft_gate_semantics": SOFT_GATE_SEMANTICS,
        "source_detector_version": WEEKLY_STRUCTURE_DETECTOR_VERSION,
        "status": V3_FROZEN_STATUS,
        "structural_matching_semantics": {
            "algorithm_id": "MAX_CARDINALITY_MIN_DISTANCE_LEXICOGRAPHIC_V1",
            "comparison_basis": proposal["comparison_basis"],
            "families_matched_separately": ["swing_high", "swing_low"],
            "inherited_from": PREDECESSOR_CALIBRATION_VERSION,
            "role_in_v3": (
                "Diagnostic only. The within-N metrics it serves are "
                "diagnostics, so the matching no longer affects any verdict; "
                "it remains fully specified so the diagnostic is reproducible."
            ),
            "tolerances_weeks": [1, 2],
        },
        "superseded_gate_metrics": list(REPLACED_PARENT_GATES),
        "transfer_guard": TRANSFER_GUARD,
        "validator_requirement": FUTURE_VALIDATOR_REQUIREMENT,
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def v3_definition_sha256(repository_root: Path) -> str:
    return v3_protocol_definition(repository_root)["definition_sha256"]


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("ascii")).hexdigest()


# =============================================================================
# the convergence record
# =============================================================================

V3_FROZEN_READY = "V3_FROZEN_READY_FOR_VALIDATOR"
V3_NOT_FREEZABLE = "V3_NOT_FREEZABLE_SOURCE_POLICY_REDESIGN_REQUIRED"
FINAL_CLASSIFICATIONS = (V3_FROZEN_READY, V3_NOT_FREEZABLE)

FINAL_CLASSIFICATION_RULE = (
    f"{V3_FROZEN_READY} when every surviving hard gate carries an absolute "
    "materiality limit derived from consequence rather than from observation, "
    "a certification rule valid on the denominators a real gate will have, an "
    "explicit dependence treatment that assumes no cross-pair independence, a "
    "non-candidate-dependent transfer guard, a hard comparability policy whose "
    "insufficient-evidence branch cannot approve, and preserved derived-level "
    "protection -- and the realism check confirms the limit is achievable by a "
    f"legitimate reference. {V3_NOT_FREEZABLE} otherwise. There is no third "
    "outcome: this is the final convergence on the existing evidence, and a "
    "further research round is not available."
)

ARCHITECTURE_COMPARISON_ID = "V2_V3_PROPOSAL_VERSUS_FINAL_V3_ARCHITECTURE_V1"


def architecture_comparison(repository_root: Path) -> dict[str, Any]:
    """Persist exactly what was demoted, why, and what protection remains."""

    parent = frozen_parent_definition(repository_root)
    parent_gates = {item["metric"]: item for item in parent["approval_gates"]}
    demotions = []
    for item in gate_architecture():
        metric = item["metric"]
        was_hard = parent_gates[metric]["hard"]
        role = item["role"]
        if role == ROLE_HARD:
            change = "RETAINED_AS_HARD"
        elif role == ROLE_SOFT:
            change = "RETAINED_AS_SOFT" if not was_hard else "DEMOTED_TO_SOFT"
        else:
            change = "DEMOTED_TO_DIAGNOSTIC"
        demotions.append(
            {
                "change": change,
                "final_role": role,
                "metric": metric,
                "parent_hard": was_hard,
                "parent_threshold": parent_gates[metric]["threshold"],
                "protection_that_remains": item["coverage_reasoning"],
                "why_demoted": item["support_reasoning"]
                if role != ROLE_HARD
                else "not demoted",
                "why_phase_1_safety_is_not_materially_weakened": item[
                    "weakening_reasoning"
                ],
            }
        )
    parent_structural_hard = sum(
        1 for metric in AFFECTED_V2_GATE_METRICS if parent_gates[metric]["hard"]
    )
    final_hard = sum(1 for role in FINAL_GATE_ROLES.values() if role == ROLE_HARD)
    return {
        "comparison_id": ARCHITECTURE_COMPARISON_ID,
        "final_v3": {
            "diagnostic_structural_metrics": sorted(
                metric
                for metric, role in FINAL_GATE_ROLES.items()
                if role == ROLE_DIAGNOSTIC
            ),
            "hard_structural_rate_gates": final_hard,
            "new_hard_requirements": list(NEW_HARD_REQUIREMENTS),
            "soft_structural_metrics": sorted(
                metric for metric, role in FINAL_GATE_ROLES.items() if role == ROLE_SOFT
            ),
            "structural_rate_gates": final_hard
            + sum(1 for role in FINAL_GATE_ROLES.values() if role == ROLE_SOFT),
        },
        "metric_changes": demotions,
        "net_effect": (
            "Five hard structural rate gates become one. Two of the five were "
            "numerically identical to a metric that is now soft, two could not "
            "certify at any defensible limit on their own denominators, and "
            "the survivor is the economically consequential subset of the "
            "fifth. In exchange the protocol gains four hard requirements that "
            "are actually computable -- a comparability floor, a required-pair "
            "count, a zero-count derived-level review census and a "
            "non-candidate-dependent raw-provider dispersion guard -- and "
            "keeps every inherited Tier-4 hard gate, which is where a "
            "structural difference's economic cost is measured directly."
        ),
        "v2_and_v3_proposal": {
            "hard_structural_rate_gates": parent_structural_hard,
            "structural_rate_gates": len(AFFECTED_V2_GATE_METRICS),
            "thresholds_were": "CARRIED_FORWARD_UNCALIBRATED",
        },
    }


def build_convergence_record(repository_root: Path) -> dict[str, Any]:
    """Stage 1 to Stage 3 as one deterministic artifact."""

    measured = measured_evidence(repository_root)
    findings = verified_review_findings(measured)
    architecture = gate_architecture()
    check = realism_check(measured)
    sensitivity = sensitivity_surface(measured)
    protocol = v3_protocol_definition(repository_root)
    freezable = (
        check["conclusion"] == "REALISTIC"
        and sensitivity["policy_conclusion_stable"]
        and any(item["role"] == ROLE_HARD for item in architecture)
    )
    classification = V3_FROZEN_READY if freezable else V3_NOT_FREEZABLE
    record: dict[str, Any] = {
        "architecture_comparison": architecture_comparison(repository_root),
        "btc019_status": "IN_PROGRESS",
        "candidate_constructed_in_this_task": False,
        "candidate_final_gate_result_evaluated": False,
        "candidate_measured_in_this_task": False,
        "classification": {
            "btc019_status_after_this_task": "IN_PROGRESS",
            "further_evidence_round_authorized": False,
            "outcome": classification,
            "production_canonical_reference": "UNRESOLVED",
            "sealed_sample_collection_authorized": False,
            "sealed_sample_opening_authorized": False,
            "v3_definition_sha256": protocol["definition_sha256"],
            "v3_status_after_this_task": (
                V3_FROZEN_STATUS if freezable else "PROPOSED"
            ),
            "validator_construction_authorized": freezable,
        },
        "classification_rule": FINAL_CLASSIFICATION_RULE,
        "comparability_policy": {
            **COMPARABILITY_POLICY,
            "policy_id": COMPARABILITY_POLICY_ID,
        },
        "comparison_contract_version": COMPARISON_CONTRACT_VERSION,
        "convergence_boundary": CONVERGENCE_BOUNDARY,
        "convergence_version": CONVERGENCE_VERSION,
        "denominator_semantics_version": DENOMINATOR_SEMANTICS_VERSION,
        "dependence_treatment": {
            "assumptions_removed": list(DEPENDENCE_TREATMENT),
            "family_wise_probability_multiplied": False,
            "pair_independence_assumed": False,
            "treatment_id": DEPENDENCE_TREATMENT_ID,
            "within_pair_disclosure": WITHIN_PAIR_DEPENDENCE_DISCLOSURE,
        },
        "derived_level_protection": DERIVED_LEVEL_PROTECTION,
        "development_dispersion": {
            metric: observed_development_dispersion(measured, metric)
            for metric in sorted(AFFECTED_V2_GATE_METRICS)
        },
        "diagnostic_semantics": DIAGNOSTIC_SEMANTICS,
        "evidence_labelling": "DEVELOPMENT_CALIBRATION_EVIDENCE",
        "frozen_prior_artifacts_changed": False,
        "gate_architecture": list(architecture),
        "materiality": protocol["materiality"],
        "new_evidence_collected": False,
        "parent_definition_sha256": PARENT_DEFINITION_SHA256,
        "parent_protocol_version": V2_PROTOCOL_VERSION,
        "predecessor_calibration_governance_sha256": calibration_governance_sha256(
            repository_root
        ),
        "predecessor_calibration_review_commit": PREDECESSOR_CALIBRATION_REVIEW_COMMIT,
        "predecessor_calibration_version": PREDECESSOR_CALIBRATION_VERSION,
        "price_source_policy_version": PRICE_SOURCE_POLICY_VERSION,
        "production_promotion_authorized": False,
        "proposed_successor_definition_sha256": successor_protocol_definition(
            repository_root
        )["definition_sha256"],
        "realism_check": check,
        "research_only": True,
        "schema_version": CONVERGENCE_SCHEMA_VERSION,
        "sealed_sample": _sealed_sample_block(),
        "sealed_sample_collected": False,
        "sealed_sample_opened": False,
        "sensitivity": sensitivity,
        "soft_gate_semantics": SOFT_GATE_SEMANTICS,
        "source_detector_version": WEEKLY_STRUCTURE_DETECTOR_VERSION,
        "transfer_guard": TRANSFER_GUARD,
        "v3_definition_sha256": protocol["definition_sha256"],
        "v3_protocol_version": V3_PROTOCOL_VERSION,
        "verified_review_findings": findings,
    }
    record["artifact_digest"] = _digest(record)
    return record


# --- persistence ---------------------------------------------------------------


def write_convergence_artifacts(
    repository_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Persist the frozen protocol, the convergence record and the report."""

    protocol = v3_protocol_definition(repository_root)
    record = build_convergence_record(repository_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / V3_PROTOCOL_FILENAME).write_text(
        json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    (output_dir / CONVERGENCE_RECORD_FILENAME).write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    (output_dir / CONVERGENCE_REPORT_FILENAME).write_text(
        convergence_markdown(protocol, record), encoding="ascii"
    )
    return record


def restore_v3_protocol(output_dir: Path) -> dict[str, Any]:
    """Read the persisted frozen protocol, refusing a tamper."""

    payload = json.loads((output_dir / V3_PROTOCOL_FILENAME).read_text())
    if payload.get("schema_version") != V3_PROTOCOL_SCHEMA_VERSION:
        raise V3ConvergenceError(
            f"persisted protocol does not carry {V3_PROTOCOL_SCHEMA_VERSION}"
        )
    if payload.get("reference_policy_version") != V3_PROTOCOL_VERSION:
        raise V3ConvergenceError("persisted protocol is not BTC_REFERENCE_COMPOSITE_V3")
    if payload.get("parent_definition_sha256") != PARENT_DEFINITION_SHA256:
        raise V3ConvergenceError("persisted protocol names a different parent hash")
    if payload.get("status") != V3_FROZEN_STATUS:
        raise V3ConvergenceError("persisted protocol is not frozen")
    if payload.get("production_promotion_authorized"):
        raise V3ConvergenceError("persisted protocol authorises production promotion")
    sealed = payload.get("sample_governance", {}).get("sealed_sample", {})
    if sealed.get("collected") or sealed.get("opened"):
        raise V3ConvergenceError("persisted protocol claims sealed-sample access")
    roles = payload.get("gate_architecture", {}).get("roles")
    if roles != dict(sorted(FINAL_GATE_ROLES.items())):
        raise V3ConvergenceError("persisted protocol carries a different gate architecture")
    digest = payload.get("definition_sha256")
    body = {key: value for key, value in payload.items() if key != "definition_sha256"}
    if digest != _digest(body):
        raise V3ConvergenceError("persisted V3 protocol definition was tampered with")
    return payload


def restore_convergence_record(output_dir: Path) -> dict[str, Any]:
    """Read the persisted convergence record, refusing anything unvouched."""

    record = json.loads((output_dir / CONVERGENCE_RECORD_FILENAME).read_text())
    if record.get("schema_version") != CONVERGENCE_SCHEMA_VERSION:
        raise V3ConvergenceError(
            f"persisted record does not carry {CONVERGENCE_SCHEMA_VERSION}"
        )
    if record.get("parent_definition_sha256") != PARENT_DEFINITION_SHA256:
        raise V3ConvergenceError("persisted record names a different parent hash")
    if record.get("comparison_contract_version") != COMPARISON_CONTRACT_VERSION:
        raise V3ConvergenceError("persisted record names a different comparison contract")
    outcome = record.get("classification", {}).get("outcome")
    if outcome not in FINAL_CLASSIFICATIONS:
        raise V3ConvergenceError("persisted record carries no known classification")
    architecture = record.get("gate_architecture")
    if not isinstance(architecture, list) or {
        item.get("metric") for item in architecture
    } != set(AFFECTED_V2_GATE_METRICS):
        raise V3ConvergenceError(
            "persisted record does not classify exactly the six structural gates"
        )
    for item in architecture:
        if item.get("role") not in GATE_ROLES:
            raise V3ConvergenceError(f"{item.get('metric')!r} carries no known role")
        if item.get("role") == ROLE_HARD and not item.get("statistically_supportable"):
            raise V3ConvergenceError(
                f"{item.get('metric')!r} is hard without statistical support"
            )
    if record.get("sealed_sample_opened") or record.get("sealed_sample_collected"):
        raise V3ConvergenceError("persisted record claims sealed-sample access")
    if record.get("candidate_final_gate_result_evaluated"):
        raise V3ConvergenceError("persisted record claims a candidate gate result")
    if record.get("new_evidence_collected"):
        raise V3ConvergenceError("persisted record claims a new evidence round")
    digest = record.get("artifact_digest")
    body = {key: value for key, value in record.items() if key != "artifact_digest"}
    if digest != _digest(body):
        raise V3ConvergenceError("persisted convergence record was tampered with")
    return record


def verify_convergence_artifacts(
    repository_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Recompute both artifacts and refuse a persisted copy that disagrees."""

    protocol = restore_v3_protocol(output_dir)
    if protocol != v3_protocol_definition(repository_root):
        raise V3ConvergenceError(
            "persisted V3 protocol does not recompute from the repository"
        )
    record = restore_convergence_record(output_dir)
    if record != build_convergence_record(repository_root):
        raise V3ConvergenceError(
            "persisted convergence record does not recompute from the repository"
        )
    if record["v3_definition_sha256"] != protocol["definition_sha256"]:
        raise V3ConvergenceError(
            "convergence record and V3 protocol are not bound together"
        )
    return record


# --- report --------------------------------------------------------------------


def _rendered(value: str | None, digits: int) -> str:
    """Truncate a persisted decimal string without dropping its exponent."""

    if value is None:
        return "n/a"
    return f"{Decimal(value):f}"[:digits]


def convergence_markdown(
    protocol: Mapping[str, Any],
    record: Mapping[str, Any],
) -> str:
    """Render the human-readable convergence report deterministically."""

    lines: list[str] = []
    add = lines.append
    add(f"# {CONVERGENCE_VERSION}")
    add("")
    add(
        "Final gate-architecture convergence for "
        f"{V3_PROTOCOL_VERSION}, on the evidence already in hand. No new "
        "evidence is collected, no candidate is constructed or measured, no "
        "frozen artifact is changed, and the sealed 2015-2019 validation "
        "sample is neither collected nor opened."
    )
    add("")
    add(f"- Parent: `{V2_PROTOCOL_VERSION}` `{PARENT_DEFINITION_SHA256}`")
    add(
        f"- Predecessor calibration: `{PREDECESSOR_CALIBRATION_VERSION}`, review "
        f"`{PREDECESSOR_CALIBRATION_REVIEW_COMMIT}`"
    )
    add(f"- Convergence boundary: `{CONVERGENCE_BOUNDARY}`")
    add(f"- Outcome: **`{record['classification']['outcome']}`**")
    add(f"- `{V3_PROTOCOL_VERSION}` definition hash: `{protocol['definition_sha256']}`")
    add("")

    add("## Stage 1 -- the review's findings, reverified here")
    add("")
    add(
        "Each finding is recomputed from the repository's own measurements "
        "rather than taken on trust."
    )
    add("")
    add("| Finding | Verdict | Evidence |")
    add("| --- | --- | --- |")
    findings = record["verified_review_findings"]["findings"]
    redundancy = findings[REVIEW_FINDING_REDUNDANT_WITHIN_N]
    add(
        f"| within-N identical to exact timestamp | {redundancy['verdict']} | "
        f"{redundancy['distinguishing_measurement_count']} of "
        f"{redundancy['measurement_count']} measurements distinguish them; "
        f"{redundancy['merged_pair_total']} pairs merged in total |"
    )
    nesting = findings[REVIEW_FINDING_NESTED_STRUCTURAL_STATE]
    add(
        f"| structural state nested in exact timestamp | {nesting['verdict']} | "
        f"{nesting['violation_count']} violations; strictly smaller on "
        f"{nesting['strictly_smaller_measurement_count']} of "
        f"{len(nesting['measurements'])} |"
    )
    degeneracy = findings[REVIEW_FINDING_RELATIVE_ALTERNATIVE_DEGENERATE]
    add(
        f"| relative alternative degenerates | {degeneracy['verdict']} | "
        "per-pair expected counts converge to "
        f"{_rendered(degeneracy['expected_count_limit_under_band'], 6)} against "
        f"{_rendered(degeneracy['expected_count_limit_under_alternative'], 6)} "
        "at every denominator |"
    )
    minimum = findings[REVIEW_FINDING_MINIMUM_N_INVALID]
    add(
        f"| scalar minimum-n does not carry | {minimum['verdict']} | holds at "
        f"every probe: {minimum['scalar_minimum_holds_at_every_probe']}; power "
        f"monotone in n: {minimum['power_is_monotone_in_the_denominator']} |"
    )
    add("")
    add("### The relative alternative, at every denominator")
    add("")
    add("| per-pair n | pooled 6n | pi_bar | n*pi_bar | n*pi_alt |")
    add("| --- | --- | --- | --- | --- |")
    for probe in degeneracy["probes"]:
        add(
            f"| {probe['per_pair_denominator']} | {probe['pooled_denominator']} | "
            f"{_rendered(probe['pi_bar'], 10)} | "
            f"{_rendered(probe['expected_count_under_band'], 6)} | "
            f"{_rendered(probe['expected_count_under_alternative'], 6)} |"
        )
    add("")
    add("### The scalar minimum, under unequal denominators")
    add("")
    add("| metric | published minimum | denominators | family power | meets 0.80 |")
    add("| --- | --- | --- | --- | --- |")
    for probe in minimum["probes"]:
        add(
            f"| {probe['metric']} | {probe['published_minimum']} | "
            f"{probe['denominators']} | {_rendered(probe['family_power'], 6)} | "
            f"{probe['meets_declared_power']} |"
        )
    add("")

    add("## Stage 2 -- the final architecture")
    add("")
    add("| metric | role | supportable | covered elsewhere | reasons |")
    add("| --- | --- | --- | --- | --- |")
    for item in record["gate_architecture"]:
        add(
            f"| {item['metric']} | {item['role']} | "
            f"{item['statistically_supportable']} | "
            f"{item['covered_by_another_gate']} | "
            f"{', '.join(item['reason_codes'])} |"
        )
    add("")
    add("### Absolute materiality")
    add("")
    add(record["materiality"]["statement"])
    add("")
    add(
        f"- Limit: `{record['materiality']['absolute_limit']}`, direction "
        f"`{record['materiality']['direction']}`, applied to "
        f"`{record['materiality']['applies_to']}`"
    )
    add(
        "- Relative `3 x pi_bar` retained: "
        f"{record['materiality']['relative_alternative_retained']}"
    )
    for ground in record["materiality"]["derivation"]:
        add(f"- **{ground['ground']}.** {ground['reasoning']}")
    add("")
    add("### Certification rule")
    add("")
    add(protocol["gate_architecture"]["certification_rule"]["rule"])
    add("")
    for prop in protocol["gate_architecture"]["certification_rule"]["properties"]:
        add(f"- {prop}")
    add("")
    add("### Dependence")
    add("")
    for removed in record["dependence_treatment"]["assumptions_removed"]:
        add(f"- **Removed:** {removed['assumption_removed']}. {removed['how']}")
    add(f"- **Disclosed:** {record['dependence_treatment']['within_pair_disclosure']}")
    add("")
    add("### Transfer guard")
    add("")
    add(record["transfer_guard"]["rule"])
    add("")
    add(f"- Blocks: {record['transfer_guard']['failure_mode_blocked']}")
    add(
        "- Depends on the candidate: "
        f"{record['transfer_guard']['depends_on_the_candidate']}. "
        f"{record['transfer_guard']['why_this_and_not_a_looser_measure']}"
    )
    add("")

    add("## Observed development dispersion, and the realism check")
    add("")
    add(REALISM_CHECK_ROLE)
    add("")
    add("| sample | pair | count | rate | 95% upper | comparability | admissibility |")
    add("| --- | --- | --- | --- | --- | --- | --- |")
    for row in record["development_dispersion"][_STRUCTURAL_METRIC]["measurements"]:
        add(
            f"| {row['sample_dir']} | {row['comparison_id']} | "
            f"{row['numerator']}/{row['denominator']} | "
            f"{_rendered(row['rate'], 8)} | "
            f"{_rendered(row['wilson_95_upper'], 8)} | "
            f"{_rendered(row['structural_comparability_rate'], 6)} | "
            f"{row['admissibility']} |"
        )
    add("")
    check = record["realism_check"]
    add(f"- Conclusion: **{check['conclusion']}**")
    add(f"- Worst legitimate pair rate: {_rendered(check['worst_pair_rate'], 8)}")
    add(
        f"- Measurements certifying at the limit: "
        f"{check['certifying_measurement_count']} of "
        f"{check['legitimate_measurement_count']}"
    )
    add(f"- {check['statement']}")
    add("")

    add("## Sensitivity to the governance assumptions")
    add("")
    add(record["sensitivity"]["statement"])
    add("")
    add(
        "| limit | min n at 0/1/2/3 disagreements | realism | structural state "
        "viable | breakout viable | reclaim viable |"
    )
    add("| --- | --- | --- | --- | --- | --- |")
    for row in record["sensitivity"]["materiality_neighbourhood"]:
        minima = row["minimum_certifying_denominator_by_disagreement_count"]
        add(
            f"| {row['limit']} | "
            f"{minima['0']}/{minima['1']}/{minima['2']}/{minima['3']} | "
            f"{row['structural_state_realism']} | "
            f"{row['structural_state_viable']} | "
            f"{row['derived_level_metrics_viable'][_BREAKOUT_METRIC]} | "
            f"{row['derived_level_metrics_viable'][_RECLAIM_METRIC]} |"
        )
    add("")
    add("| metric | tightest limit at which it could be a hard gate |")
    add("| --- | --- |")
    for metric, boundary in record["sensitivity"]["viability_boundaries"].items():
        add(f"| {metric} | {boundary if boundary is not None else 'nowhere'} |")
    add("")
    add("| confidence | min n at 0/1/2/3 disagreements |")
    add("| --- | --- |")
    for row in record["sensitivity"]["uncertainty_treatment_neighbourhood"]:
        minima = row["minimum_certifying_denominator_by_disagreement_count"]
        add(
            f"| {row['confidence_level_percent']}% | "
            f"{minima['0']}/{minima['1']}/{minima['2']}/{minima['3']} |"
        )
    add("")
    add("| comparability floor | admissible measurements |")
    add("| --- | --- |")
    for row in record["sensitivity"]["comparability_floor_neighbourhood"]:
        add(
            f"| {row['floor']} | {row['admissible_measurement_count']} of "
            f"{row['measurement_count']} |"
        )
    add("")
    add(
        "- Policy conclusion stable across the neighbourhood: "
        f"**{record['sensitivity']['policy_conclusion_stable']}**; the "
        "conclusion holds at the declared limit: "
        f"**{record['sensitivity']['declared_limit_conclusion_holds']}**"
    )
    add("")

    add("## Old architecture against final architecture")
    add("")
    comparison = record["architecture_comparison"]
    add(
        f"- `{V2_PROTOCOL_VERSION}` / V3 proposal: "
        f"{comparison['v2_and_v3_proposal']['structural_rate_gates']} structural "
        f"rate gates, {comparison['v2_and_v3_proposal']['hard_structural_rate_gates']} "
        "hard, thresholds "
        f"`{comparison['v2_and_v3_proposal']['thresholds_were']}`"
    )
    add(
        f"- Final `{V3_PROTOCOL_VERSION}`: "
        f"{comparison['final_v3']['hard_structural_rate_gates']} hard structural "
        f"rate gate, {len(comparison['final_v3']['soft_structural_metrics'])} soft, "
        f"{len(comparison['final_v3']['diagnostic_structural_metrics'])} diagnostics, "
        f"plus {len(comparison['final_v3']['new_hard_requirements'])} new hard "
        "requirements"
    )
    add("")
    add("| metric | change | parent hard | why | what remains |")
    add("| --- | --- | --- | --- | --- |")
    for row in comparison["metric_changes"]:
        add(
            f"| {row['metric']} | {row['change']} | {row['parent_hard']} | "
            f"{row['why_demoted']} | {row['protection_that_remains']} |"
        )
    add("")
    add(comparison["net_effect"])
    add("")

    add("## Derived-level protection after the simplification")
    add("")
    for component in record["derived_level_protection"]["components"]:
        add(
            f"- **{component['component']}** (hard: {component['hard']}). "
            f"{component['protection']}"
        )
    add("")

    add("## Governance")
    add("")
    add(f"- `BTC-019`: {record['btc019_status']}")
    add(
        "- Production canonical reference: "
        f"{record['classification']['production_canonical_reference']}"
    )
    add(f"- `{V3_PROTOCOL_VERSION}` status: {record['classification']['v3_status_after_this_task']}")
    add(
        "- Validator construction authorised: "
        f"{record['classification']['validator_construction_authorized']}, after "
        "an independent review of this frozen definition"
    )
    add(
        "- Sealed sample collected: "
        f"{record['sealed_sample_collected']}; opened: "
        f"{record['sealed_sample_opened']}"
    )
    add(f"- New evidence collected: {record['new_evidence_collected']}")
    add(
        "- Candidate constructed / measured / evaluated: "
        f"{record['candidate_constructed_in_this_task']} / "
        f"{record['candidate_measured_in_this_task']} / "
        f"{record['candidate_final_gate_result_evaluated']}"
    )
    add(f"- Frozen prior artifacts changed: {record['frozen_prior_artifacts_changed']}")
    add(f"- Further evidence round authorised: "
        f"{record['classification']['further_evidence_round_authorized']}")
    add("")
    add(f"Classification rule: {record['classification_rule']}")
    add("")
    return "\n".join(lines)


def main() -> None:  # pragma: no cover - operational entry point
    repository_root = Path.cwd()
    record = write_convergence_artifacts(
        repository_root, repository_root / CONVERGENCE_OUTPUT_NAMESPACE
    )
    print(record["classification"]["outcome"])
    print(record["v3_definition_sha256"])


if __name__ == "__main__":  # pragma: no cover - operational entry point
    main()
