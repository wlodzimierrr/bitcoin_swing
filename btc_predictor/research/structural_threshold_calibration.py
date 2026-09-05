"""Pre-sealed calibration of the six BTC_REFERENCE_COMPOSITE_V3 structural gates.

`STRUCTURAL_GATE_DENOMINATOR_RESOLUTION_V1` gave each of the six frozen
structural approval gates an explicit numerator, denominator and
`NOT_COMPARABLE` treatment, and carried the six frozen numbers across
verbatim and explicitly `CARRIED_FORWARD_UNCALIBRATED`. Its required xHigh
review then recorded four semantics the proposed successor still leaves open,
each able to move a hard gate verdict on its own. This module closes them and
then, and only then, asks what threshold the already-inspected evidence can
actually support.

The task runs in two strictly ordered phases:

    PHASE A  resolve the remaining statistical and governance semantics,
             persist them as one deterministic artifact, and hash it
        |
        v    hard gate: Phase B verifies that hash before it computes
        |
    PHASE B  estimate the independent cross-provider reference band, and
             select a threshold per metric under a predeclared objective

Phase A is governance: it decides which pairs a gate is computed over, what
makes a pair admissible, how pair measurements become one verdict, what a zero
denominator means, how within-N-week swing matching is performed, what counts
as sufficient comparability evidence, and how sampling uncertainty is
represented. None of those choices consults an observed rate.

Phase B is measurement. It uses the two already-inspected research samples,
2019-12-01..2022-12-31 and 2023-01-01..2025-12-31, and nothing else. The
sealed 2015-07-20..2019-11-30 validation sample is neither collected, opened,
inspected nor summarised here, and the inherited guard refuses any window that
touches it.

Nothing in this module approves a candidate, promotes a canonical reference,
moves a frozen artifact, changes candidate construction, or evaluates the
candidate against any gate. The frozen `BTC_REFERENCE_COMPOSITE_V2` protocol,
its hash, its thresholds and its directions are read and never written.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Context, Decimal, ROUND_HALF_EVEN
from fractions import Fraction
from math import comb
from pathlib import Path
from typing import Any

from btc_predictor.research.btc019_completion_gate import INSPECTED_SAMPLE_DIRS
from btc_predictor.research.cross_provider_structure_comparison import (
    AFFECTED_V2_GATE_METRICS,
    BREAKOUT_FAMILY,
    COMPARABLE,
    COMPARISON_CONTRACT_VERSION,
    RECLAIM_FAMILY,
    STRUCTURAL_DISAGREEMENT,
    SWING_FAMILIES,
    WEEKLY_STRUCTURE_DETECTOR_VERSION,
    compare_sample,
    frozen_v2_gate_metric,
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
    SUCCESSOR_PROTOCOL_VERSION,
    SUCCESSOR_STATUS,
    frozen_structural_gates,
    successor_protocol_definition,
)


# --- identity -----------------------------------------------------------------

CALIBRATION_VERSION = "BTC_REFERENCE_COMPOSITE_V3_STRUCTURAL_THRESHOLD_CALIBRATION_V1"
GOVERNANCE_VERSION = "BTC_REFERENCE_COMPOSITE_V3_STRUCTURAL_CALIBRATION_GOVERNANCE_V1"
GOVERNANCE_SCHEMA_VERSION = (
    "BTC_REFERENCE_COMPOSITE_V3_STRUCTURAL_CALIBRATION_GOVERNANCE_RECORD_V1"
)
CALIBRATION_SCHEMA_VERSION = (
    "BTC_REFERENCE_COMPOSITE_V3_STRUCTURAL_THRESHOLD_CALIBRATION_RECORD_V1"
)

CALIBRATION_OUTPUT_NAMESPACE = "research_artifacts/btc019_structural_threshold_calibration"
GOVERNANCE_FILENAME = "calibration_governance.json"
CALIBRATION_RECORD_FILENAME = "threshold_calibration.json"
CALIBRATION_REPORT_FILENAME = "THRESHOLD_CALIBRATION_REPORT.md"

# The successor this task calibrates for. It stays PROPOSED unless every one of
# its six structural thresholds is calibrated; this module never freezes it.
PROPOSED_SUCCESSOR_VERSION = SUCCESSOR_PROTOCOL_VERSION
PROPOSED_SUCCESSOR_STATUS = SUCCESSOR_STATUS


class ThresholdCalibrationError(ValueError):
    """Malformed input, tampered evidence, or a refused governance binding."""


# Every rate, interval and probability in this module is resolved in an
# explicit local context, so a caller's ambient Decimal settings can never
# decide a persisted threshold.
_STAT_CONTEXT = Context(prec=34, rounding=ROUND_HALF_EVEN)
_REPORT_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)


# =============================================================================
# PHASE A -- governance
# =============================================================================

# --- A1. the pair universe ----------------------------------------------------

SERIES_ROLE_CANDIDATE = "CANDIDATE_REFERENCE_UNDER_EVALUATION"
SERIES_ROLE_RAW_PROVIDER = "INDEPENDENT_RAW_VALIDATION_PROVIDER"
SERIES_ROLE_RESEARCH_COMPOSITE = "RESEARCH_ONLY_HISTORICAL_COMPOSITE"
SERIES_ROLES = (
    SERIES_ROLE_CANDIDATE,
    SERIES_ROLE_RAW_PROVIDER,
    SERIES_ROLE_RESEARCH_COMPOSITE,
)

# The candidate series is the reference the successor protocol builds. Its
# construction is MEDIAN_OHLC_V2, inherited from the frozen parent unchanged;
# this task measures it, it does not build or alter it.
CANDIDATE_SERIES_ID = V2_METHOD_VERSION

# The three independent raw provider series the price-source policy requires.
RAW_VALIDATION_PROVIDER_IDS = REQUIRED_POLICY_PROVIDER_IDS

# Declared comparison series the parent lists that are neither the candidate
# nor an independent observation of the market. MEDIAN_OHLC_V1 is a research
# composite assembled from the same three providers, so a pair containing it
# is not an independent validation of anything.
RESEARCH_ONLY_COMPOSITE_SERIES_IDS = ("MEDIAN_OHLC_V1",)

PAIR_UNIVERSE_ID = "CANDIDATE_VERSUS_INDEPENDENT_RAW_PROVIDER_PAIRS_V1"
PAIR_UNIVERSE_RULE = (
    "The gate pair universe is every unordered pair {candidate series, "
    "independent raw validation provider}, canonicalised by sorted series id "
    "on the pair's common canonical UTC Monday calendar. With the inherited "
    "provider set that is exactly three pairs, and the candidate is on one "
    "side of every one of them."
)
CALIBRATION_PAIR_UNIVERSE_ID = "INDEPENDENT_RAW_PROVIDER_PAIRS_V1"
CALIBRATION_PAIR_UNIVERSE_RULE = (
    "The calibration pair universe is every unordered pair of distinct "
    "independent raw validation providers, canonicalised the same way. With "
    "the inherited provider set that is exactly three pairs per sample, and "
    "the candidate is on neither side of any of them."
)

PAIR_PURPOSE_GATE = "APPROVAL_GATE_PAIR"
PAIR_PURPOSE_CALIBRATION = "SOURCE_DISPERSION_CALIBRATION_PAIR"
PAIR_PURPOSE_EXCLUDED = "EXCLUDED_FROM_BOTH_UNIVERSES"

REJECTED_PAIR_UNIVERSES = (
    {
        "universe": "the three independent raw-provider pairs, used as gates",
        "rejected_because": (
            "The candidate is on neither side, so the gate would approve or "
            "reject the candidate on evidence about two other series. Two "
            "independent venues disagreeing with each other is source "
            "dispersion, not a property of the reference under evaluation. "
            "This is the universe every measurement so far was taken over, "
            "which is exactly why it is retained as calibration evidence and "
            "refused as a gate."
        ),
    },
    {
        "universe": (
            "all ten unordered pairs among the frozen parent's five declared "
            "comparison series"
        ),
        "rejected_because": (
            "Seven of the ten do not contain the candidate, so seven of the "
            "worst-pair inputs could fail the candidate for a disagreement it "
            "is not party to. It also admits MEDIAN_OHLC_V1, a research "
            "composite built from the same three providers, whose agreement "
            "with any of them is a property of the median formula rather than "
            "an independent market observation."
        ),
    },
    {
        "universe": (
            "candidate-versus-provider pairs plus provider-versus-provider "
            "pairs, all treated as gates"
        ),
        "rejected_because": (
            "Same defect as above in a smaller form: three of the six inputs "
            "to a worst-pair verdict would not contain the candidate. Source "
            "dispersion belongs in the calibration of the tolerance, not in "
            "the verdict."
        ),
    },
)

PAIR_UNIVERSE_JUSTIFICATION = (
    "The V3 approval question is whether the candidate canonical reference "
    "agrees sufficiently with independent observable BTC market references. "
    "Only a pair with the candidate on one side is evidence about the "
    "candidate, so only those pairs are gates. Provider-versus-provider pairs "
    "answer a different and necessary question -- how much two legitimate "
    "independent references disagree with each other -- so they set the "
    "tolerance rather than the verdict. This split is also what keeps the "
    "calibration candidate-blind: the series used to choose the thresholds and "
    "the series the thresholds are applied to are disjoint."
)


def gate_pair_universe(
    *,
    candidate_series_id: str = CANDIDATE_SERIES_ID,
    provider_ids: Sequence[str] = RAW_VALIDATION_PROVIDER_IDS,
) -> tuple[tuple[str, str], ...]:
    """Return the exact gate pairs, canonicalised by sorted series id."""

    if candidate_series_id in provider_ids:
        raise ThresholdCalibrationError(
            "the candidate series cannot also be a raw validation provider"
        )
    if len(set(provider_ids)) != len(provider_ids):
        raise ThresholdCalibrationError("raw validation providers must be distinct")
    if not provider_ids:
        raise ThresholdCalibrationError("a gate pair universe needs at least one provider")
    return tuple(
        sorted(
            tuple(sorted((candidate_series_id, provider_id)))
            for provider_id in provider_ids
        )
    )


def calibration_pair_universe(
    provider_ids: Sequence[str] = RAW_VALIDATION_PROVIDER_IDS,
) -> tuple[tuple[str, str], ...]:
    """Return the exact independent-provider calibration pairs."""

    ordered = sorted(set(provider_ids))
    if len(ordered) != len(provider_ids):
        raise ThresholdCalibrationError("raw validation providers must be distinct")
    if len(ordered) < 2:
        raise ThresholdCalibrationError(
            "source dispersion needs at least two independent providers"
        )
    return tuple(
        (ordered[index], right)
        for index in range(len(ordered))
        for right in ordered[index + 1 :]
    )


def series_role(series_id: str) -> str:
    """Return the declared role of one comparison series."""

    if series_id == CANDIDATE_SERIES_ID:
        return SERIES_ROLE_CANDIDATE
    if series_id in RAW_VALIDATION_PROVIDER_IDS:
        return SERIES_ROLE_RAW_PROVIDER
    if series_id in RESEARCH_ONLY_COMPOSITE_SERIES_IDS:
        return SERIES_ROLE_RESEARCH_COMPOSITE
    raise ThresholdCalibrationError(f"undeclared comparison series {series_id!r}")


def pair_purpose(series_pair: Sequence[str]) -> str:
    """Classify one unordered pair into the gate, calibration or neither set."""

    pair = tuple(sorted(series_pair))
    if len(pair) != 2 or pair[0] == pair[1]:
        raise ThresholdCalibrationError("a pair requires two distinct series ids")
    roles = tuple(series_role(series_id) for series_id in pair)
    if SERIES_ROLE_RESEARCH_COMPOSITE in roles:
        return PAIR_PURPOSE_EXCLUDED
    if roles.count(SERIES_ROLE_CANDIDATE) == 1:
        return PAIR_PURPOSE_GATE
    if roles == (SERIES_ROLE_RAW_PROVIDER, SERIES_ROLE_RAW_PROVIDER):
        return PAIR_PURPOSE_CALIBRATION
    return PAIR_PURPOSE_EXCLUDED


# --- A2. pair admissibility ---------------------------------------------------

PAIR_ADMISSIBLE = "PAIR_ADMISSIBLE"
PAIR_INADMISSIBLE = "PAIR_INADMISSIBLE"
PAIR_UNDEFINED_INSUFFICIENT_EVIDENCE = "PAIR_UNDEFINED_INSUFFICIENT_EVIDENCE"
PAIR_STATES = (
    PAIR_ADMISSIBLE,
    PAIR_INADMISSIBLE,
    PAIR_UNDEFINED_INSUFFICIENT_EVIDENCE,
)

PAIR_NOT_IN_UNIVERSE = "PAIR_NOT_IN_DECLARED_UNIVERSE"
PAIR_ROLE_MISMATCH = "PAIR_ROLE_MISMATCH"
PAIR_WRONG_COMPARISON_CONTRACT = "PAIR_WRONG_COMPARISON_CONTRACT"
PAIR_WRONG_DETECTOR_VERSION = "PAIR_WRONG_DETECTOR_VERSION"
PAIR_WRONG_PRICE_SOURCE_POLICY = "PAIR_WRONG_PRICE_SOURCE_POLICY"
PAIR_NO_COMMON_CALENDAR = "PAIR_NO_SHARED_WEEKLY_CALENDAR"
PAIR_NO_CANDIDATE_EVENTS = "PAIR_NO_CANDIDATE_EVENT_UNIVERSE"
PAIR_NO_COMPARABLE_EVENTS = "PAIR_NO_COMPARABLE_EVENT_UNIVERSE"
PAIR_BELOW_COMPARABILITY_FLOOR = "PAIR_BELOW_STRUCTURAL_COMPARABILITY_FLOOR"
PAIR_BELOW_MINIMUM_COMPARABLE_EVENTS = "PAIR_BELOW_MINIMUM_COMPARABLE_EVENTS"
PAIR_UNRECORDED_NOT_COMPARABLE_EVENT = "PAIR_UNRECORDED_NOT_COMPARABLE_EVENT"
PAIR_MALFORMED_MEASUREMENT = "PAIR_MALFORMED_MEASUREMENT"
PAIR_REASON_CODES = (
    PAIR_NOT_IN_UNIVERSE,
    PAIR_ROLE_MISMATCH,
    PAIR_WRONG_COMPARISON_CONTRACT,
    PAIR_WRONG_DETECTOR_VERSION,
    PAIR_WRONG_PRICE_SOURCE_POLICY,
    PAIR_NO_COMMON_CALENDAR,
    PAIR_NO_CANDIDATE_EVENTS,
    PAIR_NO_COMPARABLE_EVENTS,
    PAIR_BELOW_COMPARABILITY_FLOOR,
    PAIR_BELOW_MINIMUM_COMPARABLE_EVENTS,
    PAIR_UNRECORDED_NOT_COMPARABLE_EVENT,
    PAIR_MALFORMED_MEASUREMENT,
)

PAIR_ADMISSIBILITY_RULE = (
    "A pair is PAIR_INADMISSIBLE when its identity is wrong -- it is not in "
    "the declared universe, its two series do not carry the declared roles, or "
    "it was produced by a different comparison contract, structural detector "
    "or price-source policy -- or when its evidence is malformed or an "
    "excluded event was not individually recorded. A pair is "
    "PAIR_UNDEFINED_INSUFFICIENT_EVIDENCE when its identity is sound but its "
    "evidence cannot support a rate: no shared weekly calendar, an empty "
    "candidate-event universe, an empty comparable-event universe, structural "
    "comparability below the declared floor, or fewer comparable events than "
    "the metric's declared minimum. A pair is PAIR_ADMISSIBLE otherwise. No "
    "pair is ever silently dropped: every pair in the universe is measured, "
    "classified and persisted with its reason codes."
)


@dataclass(frozen=True)
class PairAdmissibility:
    """One pair's admissibility verdict with its reason codes."""

    comparison_id: str
    series_pair: tuple[str, str]
    purpose: str
    state: str
    reason_codes: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        if self.state not in PAIR_STATES:
            raise ThresholdCalibrationError(f"unknown pair state {self.state!r}")
        unknown = [code for code in self.reason_codes if code not in PAIR_REASON_CODES]
        if unknown:
            raise ThresholdCalibrationError(f"unknown pair reason codes {unknown}")
        if self.state == PAIR_ADMISSIBLE and self.reason_codes:
            raise ThresholdCalibrationError("an admissible pair carries no reason code")
        if self.state != PAIR_ADMISSIBLE and not self.reason_codes:
            raise ThresholdCalibrationError("a refused pair must name its reason")
        return {
            "comparison_id": self.comparison_id,
            "series_pair": list(self.series_pair),
            "pair_purpose": self.purpose,
            "state": self.state,
            "reason_codes": list(self.reason_codes),
        }


# --- A3. worst-pair aggregation -----------------------------------------------

AGGREGATION_ID = "WORST_ADMISSIBLE_PAIR_V1"
GATE_VERDICT_PASS = "PASS"
GATE_VERDICT_FAIL = "FAIL"
GATE_VERDICT_UNDEFINED = "UNDEFINED_INSUFFICIENT_EVIDENCE"
GATE_VERDICTS = (GATE_VERDICT_PASS, GATE_VERDICT_FAIL, GATE_VERDICT_UNDEFINED)

AGGREGATION_RULE = (
    "One measurement per pair in the gate universe. The gate verdict is the "
    "verdict of the worst admissible defined pair, where 'worst' is read from "
    "the gate's own declared direction: for a maximum gate the worst pair is "
    "the one with the highest defined rate, for a minimum gate the lowest, and "
    "for an equality gate the one furthest from the threshold. Ties are broken "
    "by the lexicographically smallest comparison_id, so the reported pair "
    "identity is deterministic. An undefined or inadmissible required pair is "
    "never converted to a number and never treated as a pass: it makes the "
    "whole gate UNDEFINED_INSUFFICIENT_EVIDENCE, which cannot satisfy "
    "approval. No evidence is not zero disagreement."
)

THRESHOLD_COMPARISON_RULE = (
    "maximum: rate <= threshold PASSES, rate > threshold FAILS; "
    "minimum: rate >= threshold PASSES; "
    "equal: rate == threshold PASSES. Equality is a pass in every direction, "
    "matching the repository's existing structural gate convention. "
    "Comparison is exact Decimal, never binary floating point."
)

DIRECTION_MAXIMUM = "maximum"
DIRECTION_MINIMUM = "minimum"
DIRECTION_EQUAL = "equal"
GATE_DIRECTIONS = (DIRECTION_MAXIMUM, DIRECTION_MINIMUM, DIRECTION_EQUAL)


def threshold_verdict(rate: Decimal | None, *, threshold: Decimal, direction: str) -> str:
    """Return one pair's verdict, or UNDEFINED when the rate has no value."""

    if direction not in GATE_DIRECTIONS:
        raise ThresholdCalibrationError(f"unknown gate direction {direction!r}")
    if rate is None:
        return GATE_VERDICT_UNDEFINED
    if direction == DIRECTION_MAXIMUM:
        return GATE_VERDICT_PASS if rate <= threshold else GATE_VERDICT_FAIL
    if direction == DIRECTION_MINIMUM:
        return GATE_VERDICT_PASS if rate >= threshold else GATE_VERDICT_FAIL
    return GATE_VERDICT_PASS if rate == threshold else GATE_VERDICT_FAIL


def _worst_sort_key(
    rate: Decimal,
    *,
    threshold: Decimal,
    direction: str,
) -> Decimal:
    """Return an ordering value whose maximum is the worst measurement."""

    if direction == DIRECTION_MAXIMUM:
        return rate
    if direction == DIRECTION_MINIMUM:
        return -rate
    return abs(rate - threshold)


def aggregate_worst_pair(
    measurements: Sequence[Mapping[str, Any]],
    *,
    threshold: Decimal,
    direction: str,
    required_pairs: Sequence[tuple[str, str]],
) -> dict[str, Any]:
    """Reduce every gate-pair measurement to one verdict, failing closed.

    ``measurements`` carry ``comparison_id``, ``series_pair``, ``state`` and
    ``rate`` (a string or None). Every required pair must be present, so a
    missing pair is an undefined gate rather than a silently smaller universe.
    """

    if direction not in GATE_DIRECTIONS:
        raise ThresholdCalibrationError(f"unknown gate direction {direction!r}")
    required = {tuple(sorted(pair)) for pair in required_pairs}
    seen = {tuple(sorted(item["series_pair"])) for item in measurements}
    if len(seen) != len(measurements):
        raise ThresholdCalibrationError("a pair was measured more than once")
    unexpected = sorted(seen - required)
    if unexpected:
        raise ThresholdCalibrationError(
            f"measurement outside the declared gate pair universe: {unexpected}"
        )
    missing = sorted(required - seen)
    undefined = sorted(
        item["comparison_id"]
        for item in measurements
        if item["state"] != PAIR_ADMISSIBLE or item.get("rate") is None
    )
    if missing or undefined:
        return {
            "aggregation": AGGREGATION_ID,
            "verdict": GATE_VERDICT_UNDEFINED,
            "worst_pair_comparison_id": None,
            "worst_pair_rate": None,
            "required_pair_count": len(required),
            "admissible_defined_pair_count": len(measurements) - len(undefined),
            "missing_pairs": ["_vs_".join(pair) for pair in missing],
            "undefined_or_inadmissible_pairs": undefined,
        }
    ranked = sorted(
        (
            (
                -_worst_sort_key(
                    Decimal(item["rate"]), threshold=threshold, direction=direction
                ),
                item["comparison_id"],
            )
            for item in measurements
        ),
    )
    worst_id = ranked[0][1]
    worst = next(item for item in measurements if item["comparison_id"] == worst_id)
    worst_rate = Decimal(worst["rate"])
    return {
        "aggregation": AGGREGATION_ID,
        "verdict": threshold_verdict(
            worst_rate, threshold=threshold, direction=direction
        ),
        "worst_pair_comparison_id": worst_id,
        "worst_pair_rate": str(worst_rate),
        "required_pair_count": len(required),
        "admissible_defined_pair_count": len(measurements),
        "missing_pairs": [],
        "undefined_or_inadmissible_pairs": [],
    }


# --- A4. zero-comparable-event semantics --------------------------------------

MEASUREMENT_DEFINED = "DEFINED"
UNDEFINED_NO_CANDIDATE_EVENTS = "UNDEFINED_NO_CANDIDATE_EVENTS"
UNDEFINED_NO_COMPARABLE_EVENTS = "UNDEFINED_NO_COMPARABLE_EVENTS"
MEASUREMENT_STATES = (
    MEASUREMENT_DEFINED,
    UNDEFINED_NO_CANDIDATE_EVENTS,
    UNDEFINED_NO_COMPARABLE_EVENTS,
)

ZERO_DENOMINATOR_RULE = (
    "candidate_event_count == 0 makes the pair measurement "
    "UNDEFINED_NO_CANDIDATE_EVENTS. A zero comparable denominator -- because "
    "no candidate was detected, or because every detected candidate is "
    "NOT_COMPARABLE -- makes it UNDEFINED_NO_COMPARABLE_EVENTS. In both cases "
    "the rate is null, never 0.0, and it can neither pass nor fail a "
    "threshold. One undefined pair in the gate universe makes the whole gate "
    "UNDEFINED_INSUFFICIENT_EVIDENCE; so does every pair being undefined. "
    "NO EVIDENCE != ZERO DISAGREEMENT, in the metric and in the aggregation."
)


def measurement_state(*, candidate_event_count: int, denominator: int) -> str:
    """Classify one pair measurement before any rate is formed."""

    if candidate_event_count < 0 or denominator < 0:
        raise ThresholdCalibrationError("event counts cannot be negative")
    if denominator > 0 and candidate_event_count == 0:
        raise ThresholdCalibrationError(
            "a comparable denominator cannot exceed the candidate universe"
        )
    if candidate_event_count == 0:
        return UNDEFINED_NO_CANDIDATE_EVENTS
    if denominator == 0:
        return UNDEFINED_NO_COMPARABLE_EVENTS
    return MEASUREMENT_DEFINED


def exact_rate(numerator: int, denominator: int) -> Decimal | None:
    """Return an exact rate in this module's own context, or None."""

    if numerator < 0 or denominator < 0:
        raise ThresholdCalibrationError("a rate cannot be built from negative counts")
    if numerator > denominator:
        raise ThresholdCalibrationError("a rate numerator cannot exceed its denominator")
    if denominator == 0:
        return None
    return _STAT_CONTEXT.divide(Decimal(numerator), Decimal(denominator))


# --- A5. within-N-week matching -----------------------------------------------

MATCHING_ALGORITHM_ID = "MAX_CARDINALITY_MIN_DISTANCE_LEXICOGRAPHIC_V1"
MATCHING_RULE = (
    "Within a tolerance of N weekly sessions, opposing one-sided comparable "
    "swing disagreements are matched one-to-one, with the swing-high and "
    "swing-low families matched separately and never across each other. The "
    "matching is a maximum-cardinality bipartite matching on the tolerance "
    "graph, so no ordering of the inputs can produce fewer matched pairs than "
    "the graph admits. Among all maximum-cardinality matchings the one "
    "minimising total absolute calendar distance in weeks is taken; among "
    "those, the one whose sorted tuple of (left session, right session) pairs "
    "is lexicographically smallest. The result is therefore independent of "
    "provider order, dictionary order and input order. 'Nearest-admissible-"
    "pair first' is replaced because it is not maximum-cardinality at the "
    "two-week tolerance: left {W0, W4} against right {W2, W6} admits both a "
    "matched count of 2 and a matched count of 1 under orderings that all "
    "satisfy it, and the difference moves a hard gate."
)

WITHIN_WEEK_TOLERANCES = (1, 2)

# Bounded so an adversarial or malformed input cannot turn an exact
# enumeration into an unbounded search. Real inputs are far smaller: the
# pinned detector keeps same-family swings at least four weekly sessions
# apart in one series, so each node has at most two admissible partners.
_MATCHING_MAX_NODES_PER_SIDE = 24
_MATCHING_MAX_EDGES = 64
_MATCHING_STATE_BUDGET = 200_000


def _week_distance(left: datetime, right: datetime) -> int:
    delta = abs((left - right))
    if delta % timedelta(weeks=1):
        raise ThresholdCalibrationError(
            "swing sessions must be whole weekly sessions apart"
        )
    return delta // timedelta(weeks=1)


def match_within_weeks(
    left_sessions: Sequence[datetime],
    right_sessions: Sequence[datetime],
    *,
    weeks: int,
) -> tuple[tuple[datetime, datetime], ...]:
    """Return the normative maximum-cardinality matching within ``weeks``.

    Both sides hold one family's sessions only; the caller separates families.
    """

    if weeks < 0:
        raise ThresholdCalibrationError("a matching tolerance cannot be negative")
    left = sorted(set(left_sessions))
    right = sorted(set(right_sessions))
    if len(left) != len(left_sessions) or len(right) != len(right_sessions):
        raise ThresholdCalibrationError("a side cannot hold one session twice")
    if not left or not right:
        return ()
    if len(left) > _MATCHING_MAX_NODES_PER_SIDE or len(right) > _MATCHING_MAX_NODES_PER_SIDE:
        raise ThresholdCalibrationError(
            "within-N matching refuses an input larger than its declared bound"
        )
    edges: dict[int, tuple[tuple[int, int], ...]] = {}
    edge_count = 0
    for index, left_session in enumerate(left):
        admissible = tuple(
            (other, _week_distance(left_session, right_session))
            for other, right_session in enumerate(right)
            if _week_distance(left_session, right_session) <= weeks
        )
        edges[index] = admissible
        edge_count += len(admissible)
    if edge_count > _MATCHING_MAX_EDGES:
        raise ThresholdCalibrationError(
            "within-N matching refuses a tolerance graph larger than its bound"
        )
    if edge_count == 0:
        return ()
    target = _maximum_cardinality(edges, right_count=len(right))
    best = _best_matching(edges, target=target, left=left, right=right)
    return best


def _maximum_cardinality(
    edges: Mapping[int, Sequence[tuple[int, int]]],
    *,
    right_count: int,
) -> int:
    """Kuhn's augmenting-path maximum bipartite matching size."""

    match_right: dict[int, int] = {}

    def augment(node: int, seen: set[int]) -> bool:
        for other, _distance in edges[node]:
            if other in seen:
                continue
            seen.add(other)
            if other not in match_right or augment(match_right[other], seen):
                match_right[other] = node
                return True
        return False

    size = 0
    for node in sorted(edges):
        if augment(node, set()):
            size += 1
    if size > right_count:  # pragma: no cover - defensive
        raise ThresholdCalibrationError("matching exceeded the right-hand universe")
    return size


def _best_matching(
    edges: Mapping[int, Sequence[tuple[int, int]]],
    *,
    target: int,
    left: Sequence[datetime],
    right: Sequence[datetime],
) -> tuple[tuple[datetime, datetime], ...]:
    """Exhaustively pick the declared best matching among the maximal ones."""

    order = sorted(edges)
    best: tuple[int, tuple[tuple[str, str], ...]] | None = None
    best_pairs: tuple[tuple[datetime, datetime], ...] = ()
    used: set[int] = set()
    chosen: list[tuple[int, int]] = []
    states = 0

    def walk(position: int, matched: int, distance: int) -> None:
        nonlocal best, best_pairs, states
        states += 1
        if states > _MATCHING_STATE_BUDGET:  # pragma: no cover - defensive
            raise ThresholdCalibrationError(
                "within-N matching exceeded its enumeration budget"
            )
        remaining = len(order) - position
        if matched + remaining < target:
            return
        if position == len(order):
            if matched != target:
                return
            pairs = tuple(
                (left[node], right[other]) for node, other in sorted(chosen)
            )
            key = (
                distance,
                tuple(
                    (item[0].isoformat(), item[1].isoformat()) for item in pairs
                ),
            )
            if best is None or key < best:
                best = key
                best_pairs = pairs
            return
        node = order[position]
        for other, edge_distance in edges[node]:
            if other in used:
                continue
            used.add(other)
            chosen.append((node, other))
            walk(position + 1, matched + 1, distance + edge_distance)
            chosen.pop()
            used.discard(other)
        walk(position + 1, matched, distance)

    walk(0, 0, 0)
    if best is None:  # pragma: no cover - defensive
        raise ThresholdCalibrationError("no matching reached the maximum cardinality")
    return best_pairs


def matched_pair_count(
    disagreements_by_side: Mapping[str, Mapping[str, Sequence[datetime]]],
    *,
    weeks: int,
) -> int:
    """Count matched opposing one-sided swing disagreements, family by family.

    ``disagreements_by_side`` maps series id -> event family -> sessions. The
    two series ids are the pair's own, so the mapping has exactly two keys.
    """

    sides = sorted(disagreements_by_side)
    if len(sides) != 2:
        raise ThresholdCalibrationError("matching requires exactly two series")
    left_id, right_id = sides
    total = 0
    families = sorted(
        set(disagreements_by_side[left_id]) | set(disagreements_by_side[right_id])
    )
    for family in families:
        if family not in SWING_FAMILIES:
            raise ThresholdCalibrationError(
                f"within-N matching only merges swing families, not {family!r}"
            )
        total += len(
            match_within_weeks(
                disagreements_by_side[left_id].get(family, ()),
                disagreements_by_side[right_id].get(family, ()),
                weeks=weeks,
            )
        )
    return total


# --- A6. comparability sufficiency --------------------------------------------

COMPARABILITY_POLICY_ID = "STRUCTURAL_COMPARABILITY_SUFFICIENCY_V1"

# The measured set must be at least as large as the excluded set. Below a half,
# the published rate describes a minority of the structure the pair detected,
# so more outages would buy a smaller and quieter denominator. This is a
# coverage floor, not a disagreement tolerance: the two measure different
# things and are never combined into one number.
MINIMUM_STRUCTURAL_COMPARABILITY_RATE = Decimal("0.50")

# Every pair in the gate universe must be admissible and defined. A single
# undefined required candidate-versus-provider pair blocks approval, because
# two thirds of the evidence about a canonical reference is not the evidence.
REQUIRED_ADMISSIBLE_GATE_PAIR_COUNT = 3

COMPARABILITY_POLICY_RULE = (
    "A gate pair is sufficient evidence only when its structural "
    "comparability rate is at least "
    f"{MINIMUM_STRUCTURAL_COMPARABILITY_RATE}, its comparable-event count "
    "reaches the metric's own minimum -- derived in Phase B from the selected "
    "threshold's operating characteristics, not chosen -- and every excluded "
    "event is individually recorded with its reason code, its side and its "
    "missing sessions. All "
    f"{REQUIRED_ADMISSIBLE_GATE_PAIR_COUNT} gate pairs must be sufficient. "
    "Insufficient evidence produces UNDEFINED_INSUFFICIENT_EVIDENCE and "
    "cannot approve; it never produces a pass. The comparability floor and "
    "the disagreement threshold are separate numbers with separate meanings."
)

CALIBRATION_PAIR_ADMISSIBILITY_RULE = (
    "A calibration measurement is admissible on identity, provenance, a "
    "non-zero comparable denominator and the same comparability floor. It is "
    "deliberately not subject to the minimum-comparable-event count: a "
    "calibration measurement contributes to a pooled estimate of the "
    "independent reference band, while a gate measurement has to stand alone "
    "as one pair's verdict. Applying the gate's own minimum to the evidence "
    "that derives it would be circular."
)


# --- A7. sampling uncertainty --------------------------------------------------

UNCERTAINTY_METHOD_ID = "WILSON_SCORE_INTERVAL_95_TWO_SIDED_V1"
# The standard normal 0.975 quantile, predeclared to more digits than any
# persisted value uses, so the interval never depends on a library version.
WILSON_Z_95 = Decimal("1.959963984540054235631")
UNCERTAINTY_METHOD_RULE = (
    "Every observed rate is published with a two-sided 95% Wilson score "
    "interval, computed in an explicit Decimal context from the predeclared "
    "normal quantile. Wilson is used rather than the normal approximation "
    "because the denominators here are small and several numerators are zero, "
    "where the normal interval degenerates to a point and would turn no "
    "evidence into certainty. A zero observed rate therefore never justifies a "
    "strict threshold on its own: the interval's upper limit carries the "
    "denominator into every decision the objective makes."
)


@dataclass(frozen=True)
class WilsonInterval:
    numerator: int
    denominator: int
    rate: Decimal
    lower: Decimal
    upper: Decimal

    def as_record(self) -> dict[str, Any]:
        return {
            "numerator": self.numerator,
            "denominator": self.denominator,
            "observed_rate": str(_REPORT_CONTEXT.plus(self.rate)),
            "wilson_95_lower": str(_REPORT_CONTEXT.plus(self.lower)),
            "wilson_95_upper": str(_REPORT_CONTEXT.plus(self.upper)),
            "wilson_95_half_width": str(
                _REPORT_CONTEXT.divide(
                    _STAT_CONTEXT.subtract(self.upper, self.lower), Decimal(2)
                )
            ),
            "method": UNCERTAINTY_METHOD_ID,
        }


def wilson_interval(numerator: int, denominator: int) -> WilsonInterval:
    """Return the two-sided 95% Wilson score interval for one measurement."""

    if denominator <= 0:
        raise ThresholdCalibrationError(
            "an interval needs a positive denominator; an undefined rate has none"
        )
    if not 0 <= numerator <= denominator:
        raise ThresholdCalibrationError("numerator must lie within the denominator")
    ctx = _STAT_CONTEXT
    rate = ctx.divide(Decimal(numerator), Decimal(denominator))
    size = Decimal(denominator)
    z_squared = ctx.multiply(WILSON_Z_95, WILSON_Z_95)
    scale = ctx.add(Decimal(1), ctx.divide(z_squared, size))
    centre = ctx.divide(
        ctx.add(rate, ctx.divide(z_squared, ctx.multiply(Decimal(2), size))),
        scale,
    )
    variance = ctx.add(
        ctx.divide(ctx.multiply(rate, ctx.subtract(Decimal(1), rate)), size),
        ctx.divide(z_squared, ctx.multiply(Decimal(4), ctx.multiply(size, size))),
    )
    spread = ctx.divide(ctx.multiply(WILSON_Z_95, variance.sqrt(ctx)), scale)
    # At the extremes the Wilson limits are exactly 0 and exactly 1. Taking
    # them from the arithmetic instead would publish the rounding residue of a
    # 34-digit square root as though it were evidence.
    lower = (
        Decimal(0)
        if numerator == 0
        else max(Decimal(0), ctx.subtract(centre, spread))
    )
    upper = (
        Decimal(1)
        if numerator == denominator
        else min(Decimal(1), ctx.add(centre, spread))
    )
    return WilsonInterval(
        numerator=numerator,
        denominator=denominator,
        rate=rate,
        lower=lower,
        upper=upper,
    )


# --- A8. the calibration objective --------------------------------------------

CALIBRATION_OBJECTIVE_ID = "ACHIEVABLE_AND_DISCRIMINATING_TOLERANCE_V1"

# Interpretable values only. The grid is coarse on purpose: the denominators
# available here do not resolve a threshold more finely than this, and a
# threshold like 0.047 would assert a precision the evidence does not have.
THRESHOLD_GRID = tuple(
    Decimal(value)
    for value in (
        "0.01",
        "0.02",
        "0.03",
        "0.05",
        "0.10",
        "0.15",
        "0.20",
        "0.25",
        "0.30",
        "0.40",
        "0.50",
    )
)

# Family-wise probability that a legitimate reference, behaving exactly like
# the independent band, fails at least one pair of a gate. Set above the
# conventional 0.05 deliberately: a false rejection costs further research,
# while a false approval installs an unreliable canonical price reference in
# every level, stop and setup downstream. The asymmetry is spent on strictness.
FALSE_REJECTION_TOLERANCE = Fraction(1, 10)

# The alternative the gate has to be able to detect: a reference disagreeing
# three times as often as the independent band's own upper limit. Relative, so
# it needs no external materiality constant, and unambiguous: three times the
# disagreement of independent market observers is not a canonical reference.
DISCRIMINATION_MULTIPLE = 3
MINIMUM_DISCRIMINATION_POWER = Fraction(4, 5)

CALIBRATION_OBJECTIVE_RULE = (
    "For each metric: estimate the independent reference band by pooling the "
    "admissible calibration measurements, take its two-sided 95% Wilson upper "
    "limit as the band's conservative level pi_bar, and set the detectable "
    f"alternative at pi_alt = {DISCRIMINATION_MULTIPLE} x pi_bar. A threshold "
    "T on the predeclared grid is ADMISSIBLE when, for every calibration "
    "sample's own pair-denominator regime, the family-wise probability that a "
    "reference at pi_bar fails the worst-pair gate is at most "
    f"{FALSE_REJECTION_TOLERANCE} and the probability that a reference at "
    f"pi_alt fails it is at least {MINIMUM_DISCRIMINATION_POWER}. The "
    "selected threshold is the SMALLEST admissible grid value, so the "
    "objective always pushes toward strictness and is bounded below by "
    "achievability rather than by any observed rate. Binomial probabilities "
    "are exact rational arithmetic over the pair denominators."
)

PROHIBITED_OPTIMIZATION_CRITERIA = (
    "maximising the number of pairs, samples or gates that pass",
    "placing a threshold immediately above the maximum observed rate",
    "choosing a threshold because the candidate reference would survive it",
    "choosing a threshold because it reproduces a frozen V2 verdict",
    "using any measurement in which the candidate reference is one side",
    "using the sealed 2015-2019 sample in any form",
    "fitting a model of any kind, including any machine-learned model",
    "widening a threshold after seeing that a metric would not be calibrated",
)

# --- Phase-B metric statuses --------------------------------------------------

METRIC_CALIBRATED = "CALIBRATED"
METRIC_UNSTABLE = "CALIBRATION_UNSTABLE"
METRIC_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"
METRIC_REQUIRES_NEW_RESEARCH = "REQUIRES_NEW_RESEARCH"
METRIC_STATUSES = (
    METRIC_CALIBRATED,
    METRIC_UNSTABLE,
    METRIC_INSUFFICIENT,
    METRIC_REQUIRES_NEW_RESEARCH,
)

NO_ADMISSIBLE_CALIBRATION_EVIDENCE = "NO_ADMISSIBLE_CALIBRATION_EVIDENCE"
DEGENERATE_ALTERNATIVE_HYPOTHESIS = "DEGENERATE_ALTERNATIVE_HYPOTHESIS"
MECHANISM_NOT_EXERCISED = "METRIC_MECHANISM_NOT_EXERCISED_BY_THE_EVIDENCE"
NO_ADMISSIBLE_THRESHOLD = "NO_ACHIEVABLE_AND_DISCRIMINATING_THRESHOLD_EXISTS"
NEIGHBOURHOOD_VERDICTS_MOVE = "ADJACENT_GRID_VALUES_CHANGE_HISTORICAL_VERDICTS"
METRIC_REASON_CODES = (
    NO_ADMISSIBLE_CALIBRATION_EVIDENCE,
    DEGENERATE_ALTERNATIVE_HYPOTHESIS,
    MECHANISM_NOT_EXERCISED,
    NO_ADMISSIBLE_THRESHOLD,
    NEIGHBOURHOOD_VERDICTS_MOVE,
)

METRIC_STATUS_RULE = (
    f"{METRIC_INSUFFICIENT} when there is no admissible calibration evidence, "
    "when the detectable alternative degenerates to certainty because the "
    "independent band itself is too wide, when the metric's own distinguishing "
    "mechanism is never exercised by the evidence, or when no grid value is "
    "both achievable and discriminating; "
    f"{METRIC_UNSTABLE} when a threshold is selected but an adjacent grid "
    "value changes the historical pair verdicts, so the number sits on a "
    "knife edge; "
    f"{METRIC_CALIBRATED} otherwise. Only a {METRIC_CALIBRATED} metric may "
    "enter a frozen V3 approval protocol."
)

# Metrics whose definition adds a merging step to a simpler metric. If the
# evidence never merges a pair, the metric is numerically indistinguishable
# from that simpler one and its threshold is not separately identified.
MECHANISM_METRICS = {
    "within_1_week_swing_disagreement_rate": "matched_pair_count",
    "within_2_week_swing_disagreement_rate": "matched_pair_count",
}

# --- final classification -----------------------------------------------------

V3_FROZEN_READY_FOR_VALIDATOR = "V3_FROZEN_READY_FOR_VALIDATOR"
GOVERNANCE_UNRESOLVED = "GOVERNANCE_UNRESOLVED"
CALIBRATION_INSUFFICIENT = "CALIBRATION_INSUFFICIENT"
CALIBRATION_UNSTABLE = "CALIBRATION_UNSTABLE"
NEW_RESEARCH_REQUIRED = "NEW_RESEARCH_REQUIRED"
FINAL_CLASSIFICATIONS = (
    V3_FROZEN_READY_FOR_VALIDATOR,
    GOVERNANCE_UNRESOLVED,
    CALIBRATION_INSUFFICIENT,
    CALIBRATION_UNSTABLE,
    NEW_RESEARCH_REQUIRED,
)

FINAL_CLASSIFICATION_RULE = (
    f"{GOVERNANCE_UNRESOLVED} when any Phase-A semantic is unresolved or the "
    "frozen governance hash does not bind Phase B; "
    f"{CALIBRATION_INSUFFICIENT} when any of the six metrics is "
    f"{METRIC_INSUFFICIENT}; {CALIBRATION_UNSTABLE} when none is insufficient "
    f"but at least one is {METRIC_UNSTABLE}; {NEW_RESEARCH_REQUIRED} when a "
    f"metric is {METRIC_REQUIRES_NEW_RESEARCH}; "
    f"{V3_FROZEN_READY_FOR_VALIDATOR} only when all six are "
    f"{METRIC_CALIBRATED} and every freeze condition holds. The successor is "
    "never frozen partially."
)

# --- sample governance --------------------------------------------------------

PERMITTED_CALIBRATION_SAMPLE_DIRS = INSPECTED_SAMPLE_DIRS
SAMPLE_GOVERNANCE_RULE = (
    "Calibration may read only the two already-inspected research samples, "
    "2019-12-01..2022-12-31 and 2023-01-01..2025-12-31, each verified against "
    "its own collection manifest digests before use. They are development and "
    "calibration evidence, not validation evidence: both have already "
    "influenced earlier research decisions in this line, so no result measured "
    "on them is out-of-sample performance. The 2015-07-20..2019-11-30 sample "
    "stays sealed -- not collected, not opened, not inspected, not queried, "
    "not summarised -- and the inherited guard refuses any window that reaches "
    "into it."
)


def guard_sealed_sample(*, start: Any, end: Any, purpose: str) -> None:
    """Delegate to the inherited sealed-sample guard; this task opens nothing."""

    guard_untouched_validation_sample(start=start, end=end, purpose=purpose)


# --- the Phase-A artifact -----------------------------------------------------


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("ascii")).hexdigest()


def calibration_governance_definition(repository_root: Path) -> dict[str, Any]:
    """Build the deterministic Phase-A governance definition and hash it.

    Every semantic Phase B depends on is fixed here, before any rate is
    computed. The proposed successor is read for its identity and its parent
    binding only; neither it nor the frozen parent is written.
    """

    proposal = successor_protocol_definition(repository_root)
    gates = frozen_structural_gates(repository_root)
    if proposal["parent_definition_sha256"] != PARENT_DEFINITION_SHA256:
        raise ThresholdCalibrationError(
            "proposed successor does not bind the frozen parent definition hash"
        )
    if proposal["status"] != PROPOSED_SUCCESSOR_STATUS:
        raise ThresholdCalibrationError(
            "proposed successor is no longer pending threshold calibration"
        )
    payload: dict[str, Any] = {
        "schema_version": GOVERNANCE_SCHEMA_VERSION,
        "governance_version": GOVERNANCE_VERSION,
        "calibration_version": CALIBRATION_VERSION,
        "parent_protocol_version": V2_PROTOCOL_VERSION,
        "parent_definition_sha256": PARENT_DEFINITION_SHA256,
        "proposed_successor_version": PROPOSED_SUCCESSOR_VERSION,
        "proposed_successor_status": PROPOSED_SUCCESSOR_STATUS,
        "proposed_successor_definition_sha256": proposal["definition_sha256"],
        "comparison_contract_version": COMPARISON_CONTRACT_VERSION,
        "denominator_semantics_version": DENOMINATOR_SEMANTICS_VERSION,
        "source_detector_version": WEEKLY_STRUCTURE_DETECTOR_VERSION,
        "price_source_policy_version": PRICE_SOURCE_POLICY_VERSION,
        "settles_review_findings": [
            "pair universe behind 'each unordered pair of declared comparison "
            "series'",
            "pair admissibility and the place of an undefined pair in the "
            "worst-pair verdict",
            "the normative reading of a zero-comparable-event rate",
            "the exact within-N-week matching rule at the two-week tolerance",
        ],
        "pair_universe": {
            "gate_universe_id": PAIR_UNIVERSE_ID,
            "gate_universe_rule": PAIR_UNIVERSE_RULE,
            "gate_pairs": [
                "_vs_".join(pair) for pair in gate_pair_universe()
            ],
            "calibration_universe_id": CALIBRATION_PAIR_UNIVERSE_ID,
            "calibration_universe_rule": CALIBRATION_PAIR_UNIVERSE_RULE,
            "calibration_pairs": [
                "_vs_".join(pair) for pair in calibration_pair_universe()
            ],
            "justification": PAIR_UNIVERSE_JUSTIFICATION,
            "rejected_universes": [dict(item) for item in REJECTED_PAIR_UNIVERSES],
            "roles": {
                "candidate_series_id": CANDIDATE_SERIES_ID,
                "candidate_construction": proposal["candidate_construction"],
                "independent_raw_validation_providers": list(
                    RAW_VALIDATION_PROVIDER_IDS
                ),
                "research_only_historical_composites": list(
                    RESEARCH_ONLY_COMPOSITE_SERIES_IDS
                ),
                "series_roles": list(SERIES_ROLES),
                "pair_purposes": [
                    PAIR_PURPOSE_GATE,
                    PAIR_PURPOSE_CALIBRATION,
                    PAIR_PURPOSE_EXCLUDED,
                ],
            },
        },
        "pair_admissibility": {
            "states": list(PAIR_STATES),
            "reason_codes": list(PAIR_REASON_CODES),
            "rule": PAIR_ADMISSIBILITY_RULE,
            "calibration_rule": CALIBRATION_PAIR_ADMISSIBILITY_RULE,
        },
        "pair_aggregation": {
            "aggregation_id": AGGREGATION_ID,
            "rule": AGGREGATION_RULE,
            "threshold_comparison_rule": THRESHOLD_COMPARISON_RULE,
            "verdicts": list(GATE_VERDICTS),
            "directions": list(GATE_DIRECTIONS),
        },
        "zero_denominator_semantics": {
            "states": list(MEASUREMENT_STATES),
            "rule": ZERO_DENOMINATOR_RULE,
        },
        "within_week_matching": {
            "algorithm_id": MATCHING_ALGORITHM_ID,
            "rule": MATCHING_RULE,
            "tolerances_weeks": list(WITHIN_WEEK_TOLERANCES),
            "objectives_in_order": [
                "maximise the number of matched pairs",
                "minimise total absolute calendar distance in weeks",
                "lexicographically minimise the sorted matched-pair sessions",
            ],
            "families_matched_separately": list(SWING_FAMILIES),
        },
        "comparability_sufficiency": {
            "policy_id": COMPARABILITY_POLICY_ID,
            "rule": COMPARABILITY_POLICY_RULE,
            "minimum_structural_comparability_rate": str(
                MINIMUM_STRUCTURAL_COMPARABILITY_RATE
            ),
            "required_admissible_gate_pair_count": REQUIRED_ADMISSIBLE_GATE_PAIR_COUNT,
            "minimum_comparable_events_per_gate_pair": "DERIVED_IN_PHASE_B_PER_METRIC",
            "insufficient_evidence_consequence": GATE_VERDICT_UNDEFINED,
        },
        "uncertainty": {
            "method_id": UNCERTAINTY_METHOD_ID,
            "rule": UNCERTAINTY_METHOD_RULE,
            "normal_quantile_0_975": str(WILSON_Z_95),
        },
        "calibration_objective": {
            "objective_id": CALIBRATION_OBJECTIVE_ID,
            "rule": CALIBRATION_OBJECTIVE_RULE,
            "threshold_grid": [str(value) for value in THRESHOLD_GRID],
            "false_rejection_tolerance": str(FALSE_REJECTION_TOLERANCE),
            "discrimination_multiple": DISCRIMINATION_MULTIPLE,
            "minimum_discrimination_power": str(MINIMUM_DISCRIMINATION_POWER),
            "selection": "smallest admissible grid value",
            "candidate_generation": (
                "the predeclared interpretable grid only; no continuous search "
                "and no value outside the grid may be selected"
            ),
        },
        "metric_status": {
            "statuses": list(METRIC_STATUSES),
            "reason_codes": list(METRIC_REASON_CODES),
            "rule": METRIC_STATUS_RULE,
            "mechanism_metrics": dict(sorted(MECHANISM_METRICS.items())),
        },
        "final_classification": {
            "classifications": list(FINAL_CLASSIFICATIONS),
            "rule": FINAL_CLASSIFICATION_RULE,
        },
        "prohibited_optimization_criteria": list(PROHIBITED_OPTIMIZATION_CRITERIA),
        "sample_governance": {
            "rule": SAMPLE_GOVERNANCE_RULE,
            "permitted_calibration_samples": list(PERMITTED_CALIBRATION_SAMPLE_DIRS),
            "sealed_sample": {
                "start": UNTOUCHED_OOS_START.isoformat(),
                "end": UNTOUCHED_OOS_END.isoformat(),
                "collected": False,
                "opened": False,
                "permitted_for_calibration": False,
                "guard": "guard_untouched_validation_sample, inherited unchanged",
            },
            "evidence_labelling": "DEVELOPMENT_CALIBRATION_EVIDENCE",
        },
        "calibration_population": {
            "band_estimated_on": CALIBRATION_PAIR_UNIVERSE_ID,
            "thresholds_applied_to": PAIR_UNIVERSE_ID,
            "disclosed_limitation": (
                "The tolerance is estimated on independent provider pairs and "
                "applied to candidate-versus-provider pairs. The two "
                "populations are not the same one. The candidate is the "
                "element-wise median of the same three providers, so its "
                "structural agreement with any one of them is expected to be "
                "at least as good as two providers' agreement with each other. "
                "A tolerance calibrated on the provider band is therefore "
                "conservative against falsely rejecting a sound reference and "
                "lenient against falsely approving a poor one. That asymmetry "
                "is the price of calibrating without consulting the candidate, "
                "and it is disclosed rather than corrected, because correcting "
                "it would require measuring the candidate and would make the "
                "threshold candidate-dependent."
            ),
            "candidate_measurements_used": 0,
        },
        "hard_soft_status_policy": (
            "Hard and soft statuses are inherited from the frozen parent "
            "unchanged. Changing one is new policy, not calibration, so this "
            "task records the inherited status beside every calibrated "
            "threshold and changes none."
        ),
        "inherited_gate_directions": {
            metric: {
                "direction": gates[metric]["direction"],
                "hard": gates[metric]["hard"],
                "frozen_threshold": gates[metric]["threshold"],
            }
            for metric in AFFECTED_V2_GATE_METRICS
        },
        "calibrated_metrics": list(AFFECTED_V2_GATE_METRICS),
        "changes_no_production_semantics": True,
        "candidate_construction_changed": False,
        "production_promotion_authorized": False,
        "research_only": True,
    }
    payload["governance_sha256"] = _digest(payload)
    return payload


def calibration_governance_sha256(repository_root: Path) -> str:
    return calibration_governance_definition(repository_root)["governance_sha256"]


def require_frozen_governance(
    repository_root: Path,
    *,
    governance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Phase B's hard gate: refuse to compute against unfrozen semantics."""

    recomputed = calibration_governance_definition(repository_root)
    if governance is None:
        return recomputed
    if governance.get("governance_sha256") != recomputed["governance_sha256"]:
        raise ThresholdCalibrationError(
            "Phase-A governance hash does not match the repository definition; "
            "Phase B refuses to calibrate against unfrozen semantics"
        )
    if dict(governance) != recomputed:
        raise ThresholdCalibrationError(
            "Phase-A governance payload was modified without changing its hash"
        )
    return recomputed


# =============================================================================
# PHASE B -- calibration
# =============================================================================

_SWING_METRICS = (
    "exact_timestamp_swing_disagreement_rate",
    "within_1_week_swing_disagreement_rate",
    "within_2_week_swing_disagreement_rate",
    "structural_state_disagreement_rate",
)
_FAMILY_BY_METRIC = {
    "breakout_disagreement_rate": BREAKOUT_FAMILY,
    "reclaim_disagreement_rate": RECLAIM_FAMILY,
}


def _comparability_counts(
    metrics: Mapping[str, Any],
    metric: str,
) -> tuple[int, int, int, dict[str, int]]:
    """Return candidate, comparable and not-comparable counts for one metric."""

    if metric in _SWING_METRICS:
        combined = metrics["combined_swing"]
        candidate = sum(
            metrics[family]["candidate_session_count"] for family in SWING_FAMILIES
        )
        reasons: dict[str, int] = {}
        for family in SWING_FAMILIES:
            for code, count in metrics[family]["not_comparable_reason_counts"].items():
                reasons[code] = reasons.get(code, 0) + count
        return (
            candidate,
            combined["comparable_event_count"],
            combined["not_comparable_event_count"],
            dict(sorted(reasons.items())),
        )
    family = _FAMILY_BY_METRIC[metric]
    record = metrics[family]
    return (
        record["candidate_session_count"],
        record["comparable_event_count"],
        record["not_comparable_event_count"],
        dict(sorted(record["not_comparable_reason_counts"].items())),
    )


def _one_sided_swing_disagreements(
    comparison: Mapping[str, Any],
) -> dict[str, dict[str, list[datetime]]]:
    """Group comparable one-sided swing disagreements by side and family."""

    sides = {series_id: {} for series_id in comparison["series_ids"]}
    for event in comparison["reported_events"]:
        if event["event_family"] not in SWING_FAMILIES:
            continue
        if event["comparability"] != COMPARABLE:
            continue
        if event["outcome"] != STRUCTURAL_DISAGREEMENT:
            continue
        detected = event["source_detector_result"]["detected_in"]
        if len(detected) != 1:
            raise ThresholdCalibrationError(
                "a comparable swing disagreement must be detected in one series"
            )
        side = sides[detected[0]]
        side.setdefault(event["event_family"], []).append(
            datetime.fromisoformat(event["candidate_session"])
        )
    return {
        series_id: {
            family: sorted(sessions) for family, sessions in sorted(families.items())
        }
        for series_id, families in sorted(sides.items())
    }


def measure_pair(
    comparison: Mapping[str, Any],
    metric: str,
) -> dict[str, Any]:
    """Measure one metric on one pairwise comparison under V3 semantics."""

    if metric not in AFFECTED_V2_GATE_METRICS:
        raise ThresholdCalibrationError(f"unknown structural metric {metric!r}")
    metrics = comparison["metrics"]
    candidate, comparable, not_comparable, reasons = _comparability_counts(
        metrics, metric
    )
    matched = None
    if metric.startswith("within_"):
        weeks = WITHIN_WEEK_TOLERANCES[
            0 if metric.startswith("within_1_") else 1
        ]
        exact = frozen_v2_gate_metric(metrics, "exact_timestamp_swing_disagreement_rate")
        matched = matched_pair_count(
            _one_sided_swing_disagreements(comparison), weeks=weeks
        )
        numerator = exact["numerator"] - 2 * matched
        denominator = exact["denominator"] - matched
        if numerator < 0 or denominator < 0 or numerator > denominator:
            raise ThresholdCalibrationError(
                "within-N merging produced an impossible measurement"
            )
    else:
        measurement = frozen_v2_gate_metric(metrics, metric)
        numerator = measurement["numerator"]
        denominator = measurement["denominator"]
    detected_total = comparable + not_comparable
    state = measurement_state(
        candidate_event_count=candidate, denominator=denominator
    )
    rate = exact_rate(numerator, denominator)
    comparability_rate = (
        None
        if detected_total == 0
        else _STAT_CONTEXT.divide(Decimal(comparable), Decimal(detected_total))
    )
    record: dict[str, Any] = {
        "comparison_id": comparison["comparison_id"],
        "series_pair": sorted(comparison["series_ids"]),
        "metric": metric,
        "measurement_state": state,
        "numerator": numerator,
        "denominator": denominator,
        "rate": None if rate is None else str(_REPORT_CONTEXT.plus(rate)),
        "candidate_event_count": candidate,
        "all_detected_event_count": detected_total,
        "comparable_event_count": comparable,
        "not_comparable_event_count": not_comparable,
        "structural_comparability_rate": (
            None
            if comparability_rate is None
            else str(_REPORT_CONTEXT.plus(comparability_rate))
        ),
        "not_comparable_rate": (
            None
            if comparability_rate is None
            else str(
                _REPORT_CONTEXT.subtract(Decimal(1), comparability_rate)
            )
        ),
        "not_comparable_reason_counts": reasons,
        "uncertainty": (
            None if denominator == 0 else wilson_interval(numerator, denominator).as_record()
        ),
    }
    if matched is not None:
        record["matched_pair_count"] = matched
    if comparable + not_comparable != detected_total:  # pragma: no cover - defensive
        raise ThresholdCalibrationError("comparability completeness invariant failed")
    return record


def classify_calibration_pair(
    measurement: Mapping[str, Any],
    *,
    comparison: Mapping[str, Any],
    dataset_policy_version: str,
) -> PairAdmissibility:
    """Classify one calibration measurement without ever dropping it."""

    pair = tuple(sorted(measurement["series_pair"]))
    reasons: list[str] = []
    try:
        purpose = pair_purpose(pair)
    except ThresholdCalibrationError:
        purpose = PAIR_PURPOSE_EXCLUDED
        reasons.append(PAIR_ROLE_MISMATCH)
    if purpose != PAIR_PURPOSE_CALIBRATION and PAIR_ROLE_MISMATCH not in reasons:
        reasons.append(PAIR_ROLE_MISMATCH)
    if pair not in calibration_pair_universe():
        reasons.append(PAIR_NOT_IN_UNIVERSE)
    if comparison.get("comparison_contract_version") != COMPARISON_CONTRACT_VERSION:
        reasons.append(PAIR_WRONG_COMPARISON_CONTRACT)
    if comparison.get("source_detector_version") != WEEKLY_STRUCTURE_DETECTOR_VERSION:
        reasons.append(PAIR_WRONG_DETECTOR_VERSION)
    if dataset_policy_version != PRICE_SOURCE_POLICY_VERSION:
        reasons.append(PAIR_WRONG_PRICE_SOURCE_POLICY)
    if reasons:
        return PairAdmissibility(
            comparison_id=measurement["comparison_id"],
            series_pair=pair,
            purpose=purpose,
            state=PAIR_INADMISSIBLE,
            reason_codes=tuple(reasons),
        )
    undefined: list[str] = []
    if measurement["measurement_state"] == UNDEFINED_NO_CANDIDATE_EVENTS:
        undefined.append(PAIR_NO_CANDIDATE_EVENTS)
    elif measurement["measurement_state"] == UNDEFINED_NO_COMPARABLE_EVENTS:
        undefined.append(PAIR_NO_COMPARABLE_EVENTS)
    comparability = measurement["structural_comparability_rate"]
    if comparability is None:
        if PAIR_NO_CANDIDATE_EVENTS not in undefined:
            undefined.append(PAIR_NO_CANDIDATE_EVENTS)
    elif Decimal(comparability) < MINIMUM_STRUCTURAL_COMPARABILITY_RATE:
        undefined.append(PAIR_BELOW_COMPARABILITY_FLOOR)
    if undefined:
        return PairAdmissibility(
            comparison_id=measurement["comparison_id"],
            series_pair=pair,
            purpose=purpose,
            state=PAIR_UNDEFINED_INSUFFICIENT_EVIDENCE,
            reason_codes=tuple(undefined),
        )
    return PairAdmissibility(
        comparison_id=measurement["comparison_id"],
        series_pair=pair,
        purpose=purpose,
        state=PAIR_ADMISSIBLE,
        reason_codes=(),
    )


# --- exact binomial operating characteristics ---------------------------------


def binomial_tail_at_least(*, size: int, count: int, probability: Fraction) -> Fraction:
    """Exact P(X >= count) for X ~ Binomial(size, probability)."""

    if size < 0 or count < 0:
        raise ThresholdCalibrationError("binomial arguments cannot be negative")
    if not 0 <= probability <= 1:
        raise ThresholdCalibrationError("a probability must lie in [0, 1]")
    if count == 0:
        return Fraction(1)
    if count > size:
        return Fraction(0)
    complement = Fraction(1) - probability
    return sum(
        (
            Fraction(comb(size, index))
            * probability**index
            * complement ** (size - index)
            for index in range(count, size + 1)
        ),
        Fraction(0),
    )


def smallest_failing_count(*, size: int, threshold: Decimal) -> int:
    """Return the smallest disagreement count that fails a maximum gate."""

    if size <= 0:
        raise ThresholdCalibrationError("a denominator must be positive")
    limit = Fraction(threshold)
    for count in range(size + 1):
        if Fraction(count, size) > limit:
            return count
    return size + 1


def family_failure_probability(
    denominators: Sequence[int],
    *,
    threshold: Decimal,
    probability: Fraction,
) -> Fraction:
    """Exact probability that at least one pair of a worst-pair gate fails."""

    survival = Fraction(1)
    for size in denominators:
        failing = smallest_failing_count(size=size, threshold=threshold)
        survival *= Fraction(1) - binomial_tail_at_least(
            size=size, count=failing, probability=probability
        )
    return Fraction(1) - survival


def _fraction_text(value: Fraction) -> str:
    return str(_REPORT_CONTEXT.divide(Decimal(value.numerator), Decimal(value.denominator)))


def minimum_comparable_events(
    *,
    threshold: Decimal,
    band: Fraction,
    alternative: Fraction,
    pair_count: int,
    limit: int = 400,
) -> int | None:
    """Smallest equal pair denominator at which the gate meets the objective."""

    for size in range(1, limit + 1):
        denominators = [size] * pair_count
        if family_failure_probability(
            denominators, threshold=threshold, probability=band
        ) > FALSE_REJECTION_TOLERANCE:
            continue
        if family_failure_probability(
            denominators, threshold=threshold, probability=alternative
        ) < MINIMUM_DISCRIMINATION_POWER:
            continue
        return size
    return None


# --- calibration evidence ------------------------------------------------------


def calibration_evidence(repository_root: Path) -> dict[str, Any]:
    """Re-measure both already-inspected samples for calibration use only.

    Each sample is loaded through the comparison contract's own manifest
    verification, so a changed artifact byte refuses the whole calibration.
    """

    samples: dict[str, Any] = {}
    for sample_dir in PERMITTED_CALIBRATION_SAMPLE_DIRS:
        result = compare_sample(repository_root / sample_dir, sample_id=sample_dir)
        guard_sealed_sample(
            start=datetime.fromisoformat(
                result["observation_window"]["first_hourly_observation"]
            ),
            end=datetime.fromisoformat(
                result["observation_window"]["last_hourly_observation"]
            ),
            purpose=f"{CALIBRATION_VERSION} reference-band estimation",
        )
        samples[sample_dir] = result
    return samples


def _sample_measurements(
    samples: Mapping[str, Mapping[str, Any]],
    metric: str,
) -> dict[str, list[dict[str, Any]]]:
    measured: dict[str, list[dict[str, Any]]] = {}
    for sample_dir in sorted(samples):
        sample = samples[sample_dir]
        policy_version = sample["dataset"]["price_source_policy_version"]
        rows = []
        for comparison in sample["comparisons"]:
            measurement = measure_pair(comparison, metric)
            admissibility = classify_calibration_pair(
                measurement,
                comparison=comparison,
                dataset_policy_version=policy_version,
            )
            rows.append({**measurement, **admissibility.as_record()})
        measured[sample_dir] = sorted(rows, key=lambda item: item["comparison_id"])
    return measured


def calibrate_metric(
    metric: str,
    measurements_by_sample: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    frozen_gate: Mapping[str, Any],
) -> dict[str, Any]:
    """Select this metric's threshold under the predeclared objective."""

    admissible = {
        sample_dir: [row for row in rows if row["state"] == PAIR_ADMISSIBLE]
        for sample_dir, rows in sorted(measurements_by_sample.items())
    }
    pooled_numerator = sum(
        row["numerator"] for rows in admissible.values() for row in rows
    )
    pooled_denominator = sum(
        row["denominator"] for rows in admissible.values() for row in rows
    )
    reasons: list[str] = []
    result: dict[str, Any] = {
        "metric": metric,
        "frozen_v2_threshold": frozen_gate["threshold"],
        "frozen_v2_threshold_portability": "CARRIED_FORWARD_UNCALIBRATED",
        "direction": frozen_gate["direction"],
        "hard": frozen_gate["hard"],
        "hard_soft_status_source": "INHERITED_FROM_FROZEN_PARENT_UNCHANGED",
        "validation_stage": frozen_gate["validation_stage"],
        "gate_pair_universe": ["_vs_".join(pair) for pair in gate_pair_universe()],
        "calibration_pair_universe": [
            "_vs_".join(pair) for pair in calibration_pair_universe()
        ],
        "aggregation": AGGREGATION_ID,
        "matching_algorithm": (
            MATCHING_ALGORITHM_ID if metric.startswith("within_") else None
        ),
        "not_comparable_treatment": "EXCLUDED_FROM_NUMERATOR_AND_DENOMINATOR",
        "samples": {
            sample_dir: {
                "measurements": [dict(row) for row in rows],
                "admissible_pair_count": len(
                    [row for row in rows if row["state"] == PAIR_ADMISSIBLE]
                ),
                "pair_denominators": [
                    row["denominator"]
                    for row in rows
                    if row["state"] == PAIR_ADMISSIBLE
                ],
                "sample_numerator": sum(
                    row["numerator"]
                    for row in rows
                    if row["state"] == PAIR_ADMISSIBLE
                ),
                "sample_denominator": sum(
                    row["denominator"]
                    for row in rows
                    if row["state"] == PAIR_ADMISSIBLE
                ),
            }
            for sample_dir, rows in sorted(measurements_by_sample.items())
        },
        "pooled_numerator": pooled_numerator,
        "pooled_denominator": pooled_denominator,
    }
    for sample_dir, rows in sorted(measurements_by_sample.items()):
        block = result["samples"][sample_dir]
        block["sample_rate"] = (
            None
            if block["sample_denominator"] == 0
            else str(
                _REPORT_CONTEXT.divide(
                    Decimal(block["sample_numerator"]),
                    Decimal(block["sample_denominator"]),
                )
            )
        )
        block["sample_uncertainty"] = (
            None
            if block["sample_denominator"] == 0
            else wilson_interval(
                block["sample_numerator"], block["sample_denominator"]
            ).as_record()
        )
        block["worst_admissible_pair_rate"] = max(
            (
                row["rate"]
                for row in rows
                if row["state"] == PAIR_ADMISSIBLE and row["rate"] is not None
            ),
            key=lambda value: Decimal(value),
            default=None,
        )

    if pooled_denominator == 0:
        reasons.append(NO_ADMISSIBLE_CALIBRATION_EVIDENCE)
        result.update(
            {
                "reference_band": None,
                "selected_threshold": None,
                "status": METRIC_INSUFFICIENT,
                "reason_codes": reasons,
            }
        )
        return result

    band_interval = wilson_interval(pooled_numerator, pooled_denominator)
    band = Fraction(band_interval.upper)
    alternative = min(Fraction(1), band * DISCRIMINATION_MULTIPLE)
    result["reference_band"] = {
        "pooled": band_interval.as_record(),
        "band_level_pi_bar": _fraction_text(band),
        "detectable_alternative_pi_alt": _fraction_text(alternative),
        "discrimination_multiple": DISCRIMINATION_MULTIPLE,
        "population": (
            "independent raw provider pairs only; the candidate reference is "
            "on neither side of any calibration measurement"
        ),
    }

    surface = []
    for threshold in THRESHOLD_GRID:
        rows = []
        admissible_here = True
        for sample_dir in sorted(admissible):
            denominators = [row["denominator"] for row in admissible[sample_dir]]
            if not denominators:
                admissible_here = False
                rows.append(
                    {
                        "sample_dir": sample_dir,
                        "pair_denominators": [],
                        "false_rejection_probability": None,
                        "discrimination_power": None,
                        "meets_objective": False,
                    }
                )
                continue
            false_rejection = family_failure_probability(
                denominators, threshold=threshold, probability=band
            )
            power = family_failure_probability(
                denominators, threshold=threshold, probability=alternative
            )
            meets = (
                false_rejection <= FALSE_REJECTION_TOLERANCE
                and power >= MINIMUM_DISCRIMINATION_POWER
            )
            admissible_here = admissible_here and meets
            rows.append(
                {
                    "sample_dir": sample_dir,
                    "pair_denominators": denominators,
                    "false_rejection_probability": _fraction_text(false_rejection),
                    "discrimination_power": _fraction_text(power),
                    "meets_objective": meets,
                }
            )
        surface.append(
            {
                "threshold": str(threshold),
                "per_sample": rows,
                "admissible": admissible_here,
                "historical_pair_verdicts": _historical_verdicts(
                    admissible, threshold=threshold, direction=frozen_gate["direction"]
                ),
            }
        )
    result["objective_surface"] = surface

    if alternative >= 1:
        reasons.append(DEGENERATE_ALTERNATIVE_HYPOTHESIS)
    mechanism_field = MECHANISM_METRICS.get(metric)
    if mechanism_field is not None:
        exercised = any(
            row.get(mechanism_field, 0) > 0
            for rows in admissible.values()
            for row in rows
        )
        result["mechanism_exercised"] = exercised
        result["mechanism_field"] = mechanism_field
        if not exercised:
            reasons.append(MECHANISM_NOT_EXERCISED)
    selected = next(
        (Decimal(item["threshold"]) for item in surface if item["admissible"]),
        None,
    )
    if selected is None:
        reasons.append(NO_ADMISSIBLE_THRESHOLD)
    result["selected_threshold"] = None if selected is None else str(selected)

    if selected is not None:
        index = THRESHOLD_GRID.index(selected)
        neighbourhood = [
            THRESHOLD_GRID[position]
            for position in (index - 1, index, index + 1)
            if 0 <= position < len(THRESHOLD_GRID)
        ]
        base = _historical_verdicts(
            admissible, threshold=selected, direction=frozen_gate["direction"]
        )
        moved = [
            str(value)
            for value in neighbourhood
            if _historical_verdicts(
                admissible, threshold=value, direction=frozen_gate["direction"]
            )
            != base
        ]
        result["sensitivity"] = {
            "neighbourhood": [str(value) for value in neighbourhood],
            "historical_pair_verdicts_at_selected": base,
            "neighbours_that_move_historical_verdicts": moved,
            "admissible_grid_values": [
                item["threshold"] for item in surface if item["admissible"]
            ],
        }
        if moved:
            reasons.append(NEIGHBOURHOOD_VERDICTS_MOVE)
        result["minimum_comparable_events_per_gate_pair"] = minimum_comparable_events(
            threshold=selected,
            band=band,
            alternative=alternative,
            pair_count=REQUIRED_ADMISSIBLE_GATE_PAIR_COUNT,
        )
    else:
        result["sensitivity"] = {
            "neighbourhood": [],
            "historical_pair_verdicts_at_selected": {},
            "neighbours_that_move_historical_verdicts": [],
            "admissible_grid_values": [],
        }
        result["minimum_comparable_events_per_gate_pair"] = None

    if any(
        code in reasons
        for code in (
            NO_ADMISSIBLE_CALIBRATION_EVIDENCE,
            DEGENERATE_ALTERNATIVE_HYPOTHESIS,
            MECHANISM_NOT_EXERCISED,
            NO_ADMISSIBLE_THRESHOLD,
        )
    ):
        status = METRIC_INSUFFICIENT
    elif NEIGHBOURHOOD_VERDICTS_MOVE in reasons:
        status = METRIC_UNSTABLE
    else:
        status = METRIC_CALIBRATED
    result["status"] = status
    result["reason_codes"] = reasons
    if status != METRIC_CALIBRATED:
        result["selected_threshold_usable"] = False
    else:
        result["selected_threshold_usable"] = True
    return result


def _historical_verdicts(
    admissible: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    threshold: Decimal,
    direction: str,
) -> dict[str, str]:
    """Verdicts a threshold would give the admissible calibration pairs."""

    verdicts: dict[str, str] = {}
    for sample_dir in sorted(admissible):
        for row in admissible[sample_dir]:
            key = f"{sample_dir}::{row['comparison_id']}"
            rate = None if row["rate"] is None else Decimal(row["rate"])
            verdicts[key] = threshold_verdict(
                rate, threshold=threshold, direction=direction
            )
    return verdicts


# --- the calibration record ---------------------------------------------------


def build_calibration_record(repository_root: Path) -> dict[str, Any]:
    """Run Phase A, bind its hash, then run Phase B and classify the result."""

    governance = calibration_governance_definition(repository_root)
    require_frozen_governance(repository_root, governance=governance)
    gates = frozen_structural_gates(repository_root)
    samples = calibration_evidence(repository_root)
    metrics = []
    for metric in AFFECTED_V2_GATE_METRICS:
        measurements = _sample_measurements(samples, metric)
        metrics.append(
            calibrate_metric(metric, measurements, frozen_gate=gates[metric])
        )
    classification = _classify(metrics)
    record = {
        "schema_version": CALIBRATION_SCHEMA_VERSION,
        "calibration_version": CALIBRATION_VERSION,
        "governance_version": GOVERNANCE_VERSION,
        "governance_sha256": governance["governance_sha256"],
        "phase_a_frozen_before_calibration": True,
        "parent_protocol_version": V2_PROTOCOL_VERSION,
        "parent_definition_sha256": PARENT_DEFINITION_SHA256,
        "proposed_successor_version": PROPOSED_SUCCESSOR_VERSION,
        "proposed_successor_definition_sha256": governance[
            "proposed_successor_definition_sha256"
        ],
        "comparison_contract_version": COMPARISON_CONTRACT_VERSION,
        "denominator_semantics_version": DENOMINATOR_SEMANTICS_VERSION,
        "source_detector_version": WEEKLY_STRUCTURE_DETECTOR_VERSION,
        "price_source_policy_version": PRICE_SOURCE_POLICY_VERSION,
        "calibration_objective": CALIBRATION_OBJECTIVE_ID,
        "calibration_objective_rule": CALIBRATION_OBJECTIVE_RULE,
        "prohibited_optimization_criteria": list(PROHIBITED_OPTIMIZATION_CRITERIA),
        "evidence_labelling": "DEVELOPMENT_CALIBRATION_EVIDENCE",
        "evidence_is_not_out_of_sample": True,
        "datasets": {
            sample_dir: samples[sample_dir]["dataset"] for sample_dir in sorted(samples)
        },
        "evaluation_times": {
            sample_dir: samples[sample_dir]["evaluation_time"]
            for sample_dir in sorted(samples)
        },
        "metric_calibrations": metrics,
        "candidate_measured_in_this_task": False,
        "candidate_construction_changed": False,
        "production_swing_semantics_changed": False,
        "frozen_v2_artifacts_changed": False,
        "sealed_sample_collected": False,
        "sealed_sample_opened": False,
        "sealed_sample_used_for_calibration": False,
        "production_promotion_authorized": False,
        "btc019_status": "IN_PROGRESS",
        "production_canonical_reference": "UNRESOLVED",
        "successor_status": PROPOSED_SUCCESSOR_STATUS,
        "classification": classification,
        "classification_rule": FINAL_CLASSIFICATION_RULE,
        "research_only": True,
    }
    record["artifact_digest"] = _digest(record)
    return record


def _classify(metrics: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    statuses = {item["metric"]: item["status"] for item in metrics}
    unresolved_hard = sorted(
        item["metric"]
        for item in metrics
        if item["hard"] and item["status"] != METRIC_CALIBRATED
    )
    calibrated = sorted(
        item["metric"] for item in metrics if item["status"] == METRIC_CALIBRATED
    )
    insufficient = sorted(
        item["metric"] for item in metrics if item["status"] == METRIC_INSUFFICIENT
    )
    unstable = sorted(
        item["metric"] for item in metrics if item["status"] == METRIC_UNSTABLE
    )
    new_research = sorted(
        item["metric"]
        for item in metrics
        if item["status"] == METRIC_REQUIRES_NEW_RESEARCH
    )
    if new_research:
        outcome = NEW_RESEARCH_REQUIRED
    elif insufficient:
        outcome = CALIBRATION_INSUFFICIENT
    elif unstable:
        outcome = CALIBRATION_UNSTABLE
    elif len(calibrated) == len(AFFECTED_V2_GATE_METRICS):
        outcome = V3_FROZEN_READY_FOR_VALIDATOR
    else:  # pragma: no cover - defensive
        outcome = GOVERNANCE_UNRESOLVED
    freeze_conditions = {
        "all_six_thresholds_calibrated": len(calibrated)
        == len(AFFECTED_V2_GATE_METRICS),
        "no_unresolved_hard_gate": not unresolved_hard,
        "governance_semantics_explicit": True,
        "no_sealed_data_used": True,
    }
    return {
        "outcome": outcome,
        "metric_statuses": dict(sorted(statuses.items())),
        "calibrated_metrics": calibrated,
        "insufficient_metrics": insufficient,
        "unstable_metrics": unstable,
        "unresolved_hard_gates": unresolved_hard,
        "v3_freeze_conditions": freeze_conditions,
        "v3_frozen": outcome == V3_FROZEN_READY_FOR_VALIDATOR,
        "successor_status_after_this_task": (
            PROPOSED_SUCCESSOR_STATUS
            if outcome != V3_FROZEN_READY_FOR_VALIDATOR
            else "FROZEN_RESEARCH_PROTOCOL"
        ),
        "validator_construction_authorized": outcome
        == V3_FROZEN_READY_FOR_VALIDATOR,
        "sealed_sample_collection_authorized": False,
        "sealed_sample_opening_authorized": False,
    }


# --- persistence ---------------------------------------------------------------


def write_calibration_artifacts(
    repository_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Persist the governance definition and the calibration record."""

    governance = calibration_governance_definition(repository_root)
    record = build_calibration_record(repository_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / GOVERNANCE_FILENAME).write_text(
        json.dumps(governance, indent=2, sort_keys=True) + "\n",
        encoding="ascii",
    )
    (output_dir / CALIBRATION_RECORD_FILENAME).write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="ascii",
    )
    (output_dir / CALIBRATION_REPORT_FILENAME).write_text(
        calibration_markdown(governance, record),
        encoding="ascii",
    )
    return record


def restore_governance_definition(output_dir: Path) -> dict[str, Any]:
    """Read the persisted governance definition, refusing a tamper."""

    payload = json.loads((output_dir / GOVERNANCE_FILENAME).read_text())
    if payload.get("schema_version") != GOVERNANCE_SCHEMA_VERSION:
        raise ThresholdCalibrationError(
            f"persisted governance does not carry {GOVERNANCE_SCHEMA_VERSION}"
        )
    if payload.get("parent_definition_sha256") != PARENT_DEFINITION_SHA256:
        raise ThresholdCalibrationError(
            "persisted governance names a different parent protocol hash"
        )
    if payload.get("comparison_contract_version") != COMPARISON_CONTRACT_VERSION:
        raise ThresholdCalibrationError(
            "persisted governance names a different comparison contract"
        )
    digest = payload.get("governance_sha256")
    body = {key: value for key, value in payload.items() if key != "governance_sha256"}
    if digest != _digest(body):
        raise ThresholdCalibrationError("persisted governance definition was tampered with")
    return payload


def restore_calibration_record(output_dir: Path) -> dict[str, Any]:
    """Read the persisted calibration record, refusing anything unvouched."""

    record = json.loads((output_dir / CALIBRATION_RECORD_FILENAME).read_text())
    if record.get("schema_version") != CALIBRATION_SCHEMA_VERSION:
        raise ThresholdCalibrationError(
            f"persisted record does not carry {CALIBRATION_SCHEMA_VERSION}"
        )
    if record.get("parent_definition_sha256") != PARENT_DEFINITION_SHA256:
        raise ThresholdCalibrationError(
            "persisted record names a different parent protocol hash"
        )
    if record.get("comparison_contract_version") != COMPARISON_CONTRACT_VERSION:
        raise ThresholdCalibrationError(
            "persisted record names a different comparison contract"
        )
    calibrations = record.get("metric_calibrations")
    if not isinstance(calibrations, list) or {
        item.get("metric") for item in calibrations
    } != set(AFFECTED_V2_GATE_METRICS):
        raise ThresholdCalibrationError(
            "persisted record does not calibrate exactly the six structural gates"
        )
    for item in calibrations:
        if item.get("status") not in METRIC_STATUSES:
            raise ThresholdCalibrationError(
                f"{item.get('metric')!r} carries no known calibration status"
            )
        if item.get("status") == METRIC_CALIBRATED and not item.get(
            "selected_threshold"
        ):
            raise ThresholdCalibrationError(
                f"{item.get('metric')!r} is CALIBRATED with no threshold"
            )
        if item.get("status") != METRIC_CALIBRATED and item.get(
            "selected_threshold_usable"
        ):
            raise ThresholdCalibrationError(
                f"{item.get('metric')!r} offers a usable threshold it did not earn"
            )
    if record.get("sealed_sample_opened") or record.get("sealed_sample_collected"):
        raise ThresholdCalibrationError("persisted record claims sealed-sample access")
    digest = record.get("artifact_digest")
    body = {key: value for key, value in record.items() if key != "artifact_digest"}
    if digest != _digest(body):
        raise ThresholdCalibrationError("persisted calibration record was tampered with")
    return record


def verify_calibration_artifacts(
    repository_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Recompute both artifacts and refuse a persisted copy that disagrees."""

    governance = restore_governance_definition(output_dir)
    require_frozen_governance(repository_root, governance=governance)
    persisted = restore_calibration_record(output_dir)
    if persisted != build_calibration_record(repository_root):
        raise ThresholdCalibrationError(
            "persisted calibration record does not recompute from the repository"
        )
    if persisted["governance_sha256"] != governance["governance_sha256"]:
        raise ThresholdCalibrationError(
            "calibration record and governance definition are not bound together"
        )
    return persisted


# --- report --------------------------------------------------------------------


def _measurement_line(row: Mapping[str, Any]) -> str:
    rate = "undefined" if row["rate"] is None else row["rate"][:8]
    comparability = (
        "n/a"
        if row["structural_comparability_rate"] is None
        else row["structural_comparability_rate"][:6]
    )
    interval = (
        "n/a"
        if row["uncertainty"] is None
        else (
            f"[{row['uncertainty']['wilson_95_lower'][:6]}, "
            f"{row['uncertainty']['wilson_95_upper'][:6]}]"
        )
    )
    return (
        f"| {row['comparison_id']} | {row['numerator']}/{row['denominator']} | "
        f"{rate} | {interval} | {row['comparable_event_count']}/"
        f"{row['all_detected_event_count']} | {comparability} | {row['state']} |"
    )


def calibration_markdown(
    governance: Mapping[str, Any],
    record: Mapping[str, Any],
) -> str:
    """Render the human-readable calibration report deterministically."""

    lines: list[str] = []
    add = lines.append
    add(f"# {CALIBRATION_VERSION}")
    add("")
    add(
        "Pre-sealed threshold calibration for the six "
        f"{PROPOSED_SUCCESSOR_VERSION} structural approval gates. No candidate "
        "is evaluated, no canonical reference is promoted, no frozen artifact "
        "is changed, and the sealed 2015-2019 validation sample is neither "
        "collected nor opened."
    )
    add("")
    add(f"- Parent protocol: `{record['parent_protocol_version']}`")
    add(f"- Parent definition hash: `{record['parent_definition_sha256']}`")
    add(
        f"- Proposed successor: `{record['proposed_successor_version']}` "
        f"(`{record['proposed_successor_definition_sha256']}`)"
    )
    add(f"- Phase-A governance: `{GOVERNANCE_VERSION}`")
    add(f"- Phase-A governance hash: `{record['governance_sha256']}`")
    add(f"- Comparison contract: `{record['comparison_contract_version']}`")
    add(f"- Structural detector: `{record['source_detector_version']}`")
    add(f"- Final classification: **{record['classification']['outcome']}**")
    add("")
    add("## Phase A -- governance settled before any rate was computed")
    add("")
    add(f"**Gate pair universe** (`{governance['pair_universe']['gate_universe_id']}`)")
    add("")
    for pair in governance["pair_universe"]["gate_pairs"]:
        add(f"- `{pair}`")
    add("")
    add(governance["pair_universe"]["gate_universe_rule"])
    add("")
    add(governance["pair_universe"]["justification"])
    add("")
    add("Rejected pair universes:")
    add("")
    for item in governance["pair_universe"]["rejected_universes"]:
        add(f"- **{item['universe']}** -- {item['rejected_because']}")
    add("")
    add(
        "**Calibration pair universe** "
        f"(`{governance['pair_universe']['calibration_universe_id']}`): "
        + ", ".join(
            f"`{pair}`" for pair in governance["pair_universe"]["calibration_pairs"]
        )
        + ". "
        + governance["pair_universe"]["calibration_universe_rule"]
    )
    add("")
    for heading, body in (
        ("Pair admissibility", governance["pair_admissibility"]["rule"]),
        (
            "Calibration-pair admissibility",
            governance["pair_admissibility"]["calibration_rule"],
        ),
        ("Worst-pair aggregation", governance["pair_aggregation"]["rule"]),
        (
            "Threshold comparison",
            governance["pair_aggregation"]["threshold_comparison_rule"],
        ),
        (
            "Zero-comparable-event semantics",
            governance["zero_denominator_semantics"]["rule"],
        ),
        ("Within-N-week matching", governance["within_week_matching"]["rule"]),
        (
            "Comparability sufficiency",
            governance["comparability_sufficiency"]["rule"],
        ),
        ("Sampling uncertainty", governance["uncertainty"]["rule"]),
        ("Calibration objective", governance["calibration_objective"]["rule"]),
        ("Metric status", governance["metric_status"]["rule"]),
        ("Sample governance", governance["sample_governance"]["rule"]),
    ):
        add(f"**{heading}.** {body}")
        add("")
    add("Prohibited optimisation criteria:")
    add("")
    for item in governance["prohibited_optimization_criteria"]:
        add(f"- {item}")
    add("")
    add("## Phase B -- calibration evidence and thresholds")
    add("")
    add(
        "Both samples are development and calibration evidence, not validation "
        "evidence. Neither is out-of-sample: both have already informed earlier "
        "decisions in this research line."
    )
    add("")
    for sample_dir in sorted(record["datasets"]):
        dataset = record["datasets"][sample_dir]
        add(
            f"- `{sample_dir}`: {dataset['historical_period_start']} .. "
            f"{dataset['historical_period_end']}, evaluated at "
            f"`{record['evaluation_times'][sample_dir]}`"
        )
        for provider in dataset["providers"]:
            add(
                f"  - `{provider['provider']}` "
                f"`{provider['raw_artifact_sha256']}`"
            )
    add("")
    for calibration in record["metric_calibrations"]:
        add(f"### {calibration['metric']}")
        add("")
        add(
            f"- Frozen V2 threshold: `{calibration['frozen_v2_threshold']}` "
            f"({calibration['frozen_v2_threshold_portability']})"
        )
        add(
            f"- Direction `{calibration['direction']}`, "
            f"{'hard' if calibration['hard'] else 'soft'} "
            f"({calibration['hard_soft_status_source']})"
        )
        if calibration["matching_algorithm"]:
            add(f"- Matching: `{calibration['matching_algorithm']}`")
        add(f"- NOT_COMPARABLE: {calibration['not_comparable_treatment']}")
        add("")
        for sample_dir in sorted(calibration["samples"]):
            block = calibration["samples"][sample_dir]
            add(f"**{sample_dir}**")
            add("")
            add(
                "| pair | numerator/denominator | rate | Wilson 95% | "
                "comparable/detected | comparability | pair state |"
            )
            add("| --- | --- | --- | --- | --- | --- | --- |")
            for row in block["measurements"]:
                add(_measurement_line(row))
            add("")
        band = calibration["reference_band"]
        if band is None:
            add("No admissible calibration evidence.")
            add("")
        else:
            add(
                f"- Pooled independent band: "
                f"{band['pooled']['numerator']}/{band['pooled']['denominator']} = "
                f"{band['pooled']['observed_rate'][:8]}, Wilson 95% "
                f"[{band['pooled']['wilson_95_lower'][:8]}, "
                f"{band['pooled']['wilson_95_upper'][:8]}]"
            )
            add(
                f"- Band level pi_bar = {band['band_level_pi_bar'][:8]}, "
                f"detectable alternative pi_alt = "
                f"{band['detectable_alternative_pi_alt'][:8]}"
            )
            add("")
            add("| threshold | admissible | per-sample false rejection / power |")
            add("| --- | --- | --- |")
            for item in calibration["objective_surface"]:
                detail = "; ".join(
                    (
                        f"{row['sample_dir'].split('/')[-1]}: "
                        + (
                            "no admissible pair"
                            if row["false_rejection_probability"] is None
                            else (
                                f"{row['false_rejection_probability'][:6]} / "
                                f"{row['discrimination_power'][:6]}"
                            )
                        )
                    )
                    for row in item["per_sample"]
                )
                add(
                    f"| {item['threshold']} | "
                    f"{'yes' if item['admissible'] else 'no'} | {detail} |"
                )
            add("")
        add(
            f"- Proposed V3 threshold: "
            f"`{calibration['selected_threshold']}`"
            if calibration["selected_threshold"]
            else "- Proposed V3 threshold: none"
        )
        add(
            "- Minimum comparable events per gate pair: "
            f"`{calibration['minimum_comparable_events_per_gate_pair']}`"
        )
        add(
            "- Sensitivity neighbourhood: "
            + (
                ", ".join(calibration["sensitivity"]["neighbourhood"]) or "none"
            )
            + "; neighbours moving historical verdicts: "
            + (
                ", ".join(
                    calibration["sensitivity"][
                        "neighbours_that_move_historical_verdicts"
                    ]
                )
                or "none"
            )
        )
        add(f"- Status: **{calibration['status']}**")
        if calibration["reason_codes"]:
            add("- Reasons: " + ", ".join(calibration["reason_codes"]))
        add("")
    classification = record["classification"]
    add("## Outcome")
    add("")
    add(f"- Classification: **{classification['outcome']}**")
    add(f"- Calibrated: {', '.join(classification['calibrated_metrics']) or 'none'}")
    add(
        f"- Insufficient: {', '.join(classification['insufficient_metrics']) or 'none'}"
    )
    add(f"- Unstable: {', '.join(classification['unstable_metrics']) or 'none'}")
    add(
        "- Unresolved hard gates: "
        f"{', '.join(classification['unresolved_hard_gates']) or 'none'}"
    )
    add(
        f"- {PROPOSED_SUCCESSOR_VERSION} status after this task: "
        f"**{classification['successor_status_after_this_task']}**"
    )
    add(
        "- Validator construction authorised: "
        f"{'yes' if classification['validator_construction_authorized'] else 'no'}"
    )
    add("- Sealed sample collected: no")
    add("- Sealed sample opened: no")
    add("")
    add(FINAL_CLASSIFICATION_RULE)
    add("")
    return "\n".join(lines)


def main() -> None:  # pragma: no cover - operational entry point
    repository_root = Path(__file__).resolve().parents[2]
    output_dir = repository_root / CALIBRATION_OUTPUT_NAMESPACE
    record = write_calibration_artifacts(repository_root, output_dir)
    print(record["classification"]["outcome"])


if __name__ == "__main__":  # pragma: no cover - operational entry point
    main()
