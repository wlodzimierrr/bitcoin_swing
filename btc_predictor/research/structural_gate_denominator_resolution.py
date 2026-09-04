"""STRUCTURAL_GATE_DENOMINATOR_RESOLUTION: whose denominator is it anyway.

`BTC_REFERENCE_COMPOSITE_V2` froze six approval gates that are rates of
cross-provider weekly structural disagreement, and declared a threshold and a
direction for each. It never declared what any of them is a rate *of*.
`CROSS_PROVIDER_STRUCTURE_COMPARISON_V2` then showed that the answer decides
verdicts: against the identical frozen number the pass/fail outcome moves when
the denominator moves.

This module resolves that question as a governance record. It reads the frozen
protocol, the pre-existing executable formulas, and the frozen calibration
evidence, and asks one thing of each of the six metrics: was a denominator ever
intended, and does the frozen threshold still express the same statistical rule
once the denominator is written down?

It changes no frozen artifact. The `BTC_REFERENCE_COMPOSITE_V2` definition, its
hash, its thresholds and its gate directions are read and re-verified, never
written. It opens, collects and derives nothing from the sealed 2015-2019
validation sample, evaluates no candidate reference, promotes nothing, moves no
threshold and calibrates none.

Where new semantics are required they are published as a *successor* protocol
with its own hash and an explicit parent reference, because the frozen V2
governance says so itself: `material_change_requires` is
`BTC_REFERENCE_COMPOSITE_V3 or later`.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Context, Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any

from btc_predictor.research.cross_provider_structure_comparison import (
    AFFECTED_V2_GATE_METRICS,
    ALL_EVENT_DENOMINATOR,
    BTC019B_DECISION_PATH,
    BTC019B_SWING_DIAGNOSTICS_PATH,
    COMPARABLE_EVENT_DENOMINATOR,
    COMPARISON_CONTRACT_VERSION,
    COMPARISON_REPORT_FILENAME,
    COMPARISON_OUTPUT_NAMESPACE,
    COMPARISON_REPORT_SCHEMA_VERSION,
    COMPLETION_GATE_ASSESSMENT_PATH,
    LEGACY_COMPARISON_CONTRACT_VERSION,
    NOT_COMPARABLE_AVAILABILITY_GAP,
    NOT_COMPARABLE_CONFIRMATION_PENDING,
    NOT_COMPARABLE_SERIES_COVERAGE,
    NOT_COMPARABLE_SOURCE_LEVEL,
    PAIRWISE_COMPARISON_BASIS,
    V2_PROTOCOL_DEFINITION_PATH,
    WEEKLY_STRUCTURE_DETECTOR_VERSION,
)
from btc_predictor.research.reference_composite_v2 import (
    EXPECTED_BTC019B_ARTIFACT_SHA256,
    EXPECTED_V1_ARTIFACT_SHA256,
    EXPECTED_V2_PROTOCOL_ARTIFACT_SHA256,
    FROZEN_V2_DEFINITION_SHA256,
    UNTOUCHED_OOS_END,
    UNTOUCHED_OOS_START,
    V2_PROTOCOL_VERSION,
    guard_untouched_validation_sample,
)


RESOLUTION_VERSION = "STRUCTURAL_GATE_DENOMINATOR_RESOLUTION_V1"
RESOLUTION_SCHEMA_VERSION = "STRUCTURAL_GATE_DENOMINATOR_RESOLUTION_RECORD_V1"

# The denominator vocabulary is itself versioned. A record that names an
# unknown semantics version is refused rather than read under today's meanings.
DENOMINATOR_SEMANTICS_VERSION = "STRUCTURAL_DISAGREEMENT_DENOMINATOR_SEMANTICS_V1"
SUPPORTED_DENOMINATOR_SEMANTICS_VERSIONS = (DENOMINATOR_SEMANTICS_VERSION,)

PARENT_PROTOCOL_VERSION = V2_PROTOCOL_VERSION
PARENT_DEFINITION_SHA256 = FROZEN_V2_DEFINITION_SHA256

# The frozen V2 governance names its own successor tier:
# governance.material_change_requires == "BTC_REFERENCE_COMPOSITE_V3 or later".
# A "V2.1" would be a version tier the frozen protocol does not recognise, and
# the word would imply a minor clarification this resolution finds it is not.
SUCCESSOR_PROTOCOL_VERSION = "BTC_REFERENCE_COMPOSITE_V3"
SUCCESSOR_SCHEMA_VERSION = "BTC_REFERENCE_COMPOSITE_V3_STRUCTURAL_METRIC_DEFINITION_V1"
SUCCESSOR_STATUS = "PROPOSED_PENDING_THRESHOLD_CALIBRATION"

RESOLUTION_OUTPUT_NAMESPACE = "research_artifacts/btc019_gate_denominator_resolution"
RESOLUTION_RECORD_FILENAME = "denominator_resolution.json"
SUCCESSOR_DEFINITION_FILENAME = "successor_protocol_definition.json"

# --- classifications ----------------------------------------------------------

CLARIFICATION_VALID = "CLARIFICATION_VALID"
NEW_PROTOCOL_VERSION_REQUIRED = "NEW_PROTOCOL_VERSION_REQUIRED"
BLOCKED_BY_UNRESOLVED_EVIDENCE = "BLOCKED_BY_UNRESOLVED_EVIDENCE"
RESOLUTION_CLASSIFICATIONS = (
    CLARIFICATION_VALID,
    NEW_PROTOCOL_VERSION_REQUIRED,
    BLOCKED_BY_UNRESOLVED_EVIDENCE,
)

# What the pre-existing evidence turns out to say about each metric's
# denominator, before any decision is taken about what it should be.
DENOMINATOR_INTENT_RECOVERABLE = "DENOMINATOR_INTENT_RECOVERABLE"
DENOMINATOR_INTENT_RECOVERABLE_BUT_DEFECTIVE = (
    "DENOMINATOR_INTENT_RECOVERABLE_BUT_DEFECTIVE"
)
DENOMINATOR_INTENT_NOT_RECOVERABLE = "DENOMINATOR_INTENT_NOT_RECOVERABLE"
DENOMINATOR_INTENT_STATES = (
    DENOMINATOR_INTENT_RECOVERABLE,
    DENOMINATOR_INTENT_RECOVERABLE_BUT_DEFECTIVE,
    DENOMINATOR_INTENT_NOT_RECOVERABLE,
)

THRESHOLD_SEMANTICS_RECOVERABLE = "THRESHOLD_SEMANTICS_RECOVERABLE"
THRESHOLD_SEMANTICS_NOT_RECOVERABLE = "THRESHOLD_SEMANTICS_NOT_RECOVERABLE"
THRESHOLD_SEMANTICS_STATES = (
    THRESHOLD_SEMANTICS_RECOVERABLE,
    THRESHOLD_SEMANTICS_NOT_RECOVERABLE,
)

THRESHOLD_CARRIED_FORWARD_UNCALIBRATED = "CARRIED_FORWARD_UNCALIBRATED"
THRESHOLD_PORTABLE = "PORTABLE"
THRESHOLD_PORTABILITY_STATES = (
    THRESHOLD_PORTABLE,
    THRESHOLD_CARRIED_FORWARD_UNCALIBRATED,
)

# --- denominator vocabulary ---------------------------------------------------

COMPARABLE_DETECTED_EVENT_UNION = COMPARABLE_EVENT_DENOMINATOR
ALL_DETECTED_EVENT_UNION = ALL_EVENT_DENOMINATOR
COMPARABLE_DETECTED_EVENT_UNION_PAIRS_MERGED = (
    "comparable_detected_event_union_matched_pairs_merged"
)
ALL_DETECTED_EVENT_UNION_PAIRS_MERGED = (
    "all_detected_event_union_matched_pairs_merged"
)
COMPARABLE_CANDIDATE_SESSIONS = "comparable_candidate_sessions"

NOT_COMPARABLE_EXCLUDED = "EXCLUDED_FROM_NUMERATOR_AND_DENOMINATOR"
NOT_COMPARABLE_AS_DISAGREEMENT = "COUNTED_AS_DISAGREEMENT_IN_NUMERATOR_AND_DENOMINATOR"
NOT_COMPARABLE_AS_AGREEMENT = "COUNTED_AS_AGREEMENT_IN_DENOMINATOR_ONLY"
NOT_COMPARABLE_TREATMENTS = (
    NOT_COMPARABLE_EXCLUDED,
    NOT_COMPARABLE_AS_DISAGREEMENT,
    NOT_COMPARABLE_AS_AGREEMENT,
)

# --- reason codes -------------------------------------------------------------

FROZEN_V2_DECLARES_NO_DENOMINATOR = "FROZEN_V2_DECLARES_NO_DENOMINATOR"
NOT_COMPARABLE_CATEGORY_ABSENT_AT_FREEZE = "NOT_COMPARABLE_CATEGORY_ABSENT_AT_FREEZE"
ONLY_RECOVERABLE_READING_IS_THE_KNOWN_DEFECT = (
    "ONLY_RECOVERABLE_READING_IS_THE_KNOWN_DEFECT"
)
PRE_EXISTING_FORMULAS_DISAGREE = "PRE_EXISTING_FORMULAS_DISAGREE"
CANDIDATE_UNIVERSE_AMBIGUOUS = "CANDIDATE_UNIVERSE_AMBIGUOUS"
NO_CALIBRATION_ARTIFACT_EXISTS = "NO_CALIBRATION_ARTIFACT_EXISTS"
THRESHOLD_ANCHOR_ENTIRELY_AVAILABILITY_DRIVEN = (
    "THRESHOLD_ANCHOR_ENTIRELY_AVAILABILITY_DRIVEN"
)
THRESHOLD_ANCHOR_EXCEEDS_FROZEN_THRESHOLD = "THRESHOLD_ANCHOR_EXCEEDS_FROZEN_THRESHOLD"
THRESHOLD_ALLOWANCE_NOT_BOUND_TO_A_UNIVERSE = (
    "THRESHOLD_ALLOWANCE_NOT_BOUND_TO_A_UNIVERSE"
)
AGGREGATION_BASIS_UNDECLARED_AT_FREEZE = "AGGREGATION_BASIS_UNDECLARED_AT_FREEZE"
FROZEN_VERDICT_DEPENDS_ON_DENOMINATOR = "FROZEN_VERDICT_DEPENDS_ON_DENOMINATOR"
SUCCESSOR_REQUIRED_BY_PARENT_GOVERNANCE = "SUCCESSOR_REQUIRED_BY_PARENT_GOVERNANCE"

RESOLUTION_REASON_CODES = (
    FROZEN_V2_DECLARES_NO_DENOMINATOR,
    NOT_COMPARABLE_CATEGORY_ABSENT_AT_FREEZE,
    ONLY_RECOVERABLE_READING_IS_THE_KNOWN_DEFECT,
    PRE_EXISTING_FORMULAS_DISAGREE,
    CANDIDATE_UNIVERSE_AMBIGUOUS,
    NO_CALIBRATION_ARTIFACT_EXISTS,
    THRESHOLD_ANCHOR_ENTIRELY_AVAILABILITY_DRIVEN,
    THRESHOLD_ANCHOR_EXCEEDS_FROZEN_THRESHOLD,
    THRESHOLD_ALLOWANCE_NOT_BOUND_TO_A_UNIVERSE,
    AGGREGATION_BASIS_UNDECLARED_AT_FREEZE,
    FROZEN_VERDICT_DEPENDS_ON_DENOMINATOR,
    SUCCESSOR_REQUIRED_BY_PARENT_GOVERNANCE,
)

# Rates are resolved in an explicit context so a caller's ambient Decimal
# settings can never decide a persisted governance conclusion.
_RATE_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)

V1_CANDIDATE_DEFINITION_PATH = (
    "research_artifacts/btc_reference_composite/BTC_REFERENCE_COMPOSITE_V1/"
    "candidate_definition.json"
)
V1_STRUCTURAL_FORMULA_SOURCE = (
    "btc_predictor/research/reference_composite_empirical.py::_structural_comparison"
)
BTC019B_STRUCTURAL_FORMULA_SOURCE = (
    "btc_predictor/research/btc019b_diagnostics.py::_swing_metric_summary"
)


class DenominatorResolutionError(ValueError):
    """Raised when a resolution record or its inputs cannot be trusted."""


# --- per-metric semantics -----------------------------------------------------


@dataclass(frozen=True)
class StructuralMetricResolution:
    """One frozen structural gate, resolved end to end.

    Every field is mandatory. A metric whose denominator, numerator or
    not-comparable treatment is left blank cannot be published, which is the
    defect this record exists to make impossible to repeat.
    """

    metric: str
    candidate_universe: str
    numerator: str
    denominator_id: str
    denominator: str
    agreement_treatment: str
    disagreement_treatment: str
    not_comparable_treatment: str
    absent_source_level_treatment: str
    availability_gap_treatment: str
    pending_confirmation_treatment: str
    aggregation: str
    denominator_intent: str
    threshold_intent_evidence: str
    threshold_semantics: str
    reason_codes: tuple[str, ...]

    def as_record(self, gate: Mapping[str, Any]) -> dict[str, Any]:
        if self.metric not in AFFECTED_V2_GATE_METRICS:
            raise DenominatorResolutionError(
                f"{self.metric!r} is not an affected frozen V2 structural gate"
            )
        for name in (
            "candidate_universe",
            "numerator",
            "denominator",
            "agreement_treatment",
            "disagreement_treatment",
            "absent_source_level_treatment",
            "availability_gap_treatment",
            "pending_confirmation_treatment",
            "aggregation",
            "threshold_intent_evidence",
        ):
            if not getattr(self, name).strip():
                raise DenominatorResolutionError(
                    f"{self.metric!r} leaves {name} undefined; no metric may "
                    "default one silently"
                )
        if self.denominator_id not in _KNOWN_DENOMINATOR_IDS:
            raise DenominatorResolutionError(
                f"{self.metric!r} names unknown denominator {self.denominator_id!r}"
            )
        if self.not_comparable_treatment not in NOT_COMPARABLE_TREATMENTS:
            raise DenominatorResolutionError(
                f"{self.metric!r} names unknown NOT_COMPARABLE treatment "
                f"{self.not_comparable_treatment!r}"
            )
        if self.denominator_intent not in DENOMINATOR_INTENT_STATES:
            raise DenominatorResolutionError(
                f"{self.metric!r} names unknown denominator-intent state"
            )
        if self.threshold_semantics not in THRESHOLD_SEMANTICS_STATES:
            raise DenominatorResolutionError(
                f"{self.metric!r} names unknown threshold-semantics state"
            )
        unknown = [code for code in self.reason_codes if code not in RESOLUTION_REASON_CODES]
        if unknown:
            raise DenominatorResolutionError(
                f"{self.metric!r} names unknown reason codes {unknown}"
            )
        portability = (
            THRESHOLD_PORTABLE
            if self.threshold_semantics == THRESHOLD_SEMANTICS_RECOVERABLE
            else THRESHOLD_CARRIED_FORWARD_UNCALIBRATED
        )
        return {
            "metric": self.metric,
            "candidate_universe": self.candidate_universe,
            "numerator": self.numerator,
            "denominator_id": self.denominator_id,
            "denominator": self.denominator,
            "agreement_treatment": self.agreement_treatment,
            "disagreement_treatment": self.disagreement_treatment,
            "not_comparable_treatment": self.not_comparable_treatment,
            "absent_source_level_treatment": self.absent_source_level_treatment,
            "availability_gap_treatment": self.availability_gap_treatment,
            "pending_confirmation_treatment": self.pending_confirmation_treatment,
            "aggregation": self.aggregation,
            "denominator_intent": self.denominator_intent,
            "threshold_intent_evidence": self.threshold_intent_evidence,
            "threshold_semantics": self.threshold_semantics,
            "threshold_portability": portability,
            # Read from the frozen definition, never authored here.
            "frozen_threshold": gate["threshold"],
            "frozen_direction": gate["direction"],
            "frozen_hard": gate["hard"],
            "frozen_validation_stage": gate["validation_stage"],
            "reason_codes": list(self.reason_codes),
        }


_KNOWN_DENOMINATOR_IDS = (
    COMPARABLE_DETECTED_EVENT_UNION,
    ALL_DETECTED_EVENT_UNION,
    COMPARABLE_DETECTED_EVENT_UNION_PAIRS_MERGED,
    ALL_DETECTED_EVENT_UNION_PAIRS_MERGED,
    COMPARABLE_CANDIDATE_SESSIONS,
)

_SWING_UNIVERSE = (
    "Weekly swing-high and swing-low candidate sessions on the two compared "
    "series' common canonical UTC Monday calendar, both families pooled."
)
_PAIRWISE_AGGREGATION = (
    "One measurement per unordered pair of declared comparison series, "
    f"canonicalised by sorted series id on the {PAIRWISE_COMPARISON_BASIS}. "
    "Every pair's measurement is persisted; the gate verdict is the worst "
    "admissible pair verdict. No multi-provider quorum is formed, because a "
    "quorum series has no calendar of its own to require."
)
_EXCLUDED = (
    "Excluded from both numerator and denominator, and individually recorded "
    "with its reason code, the side that lacked the sessions and the exact "
    "missing sessions."
)

STRUCTURAL_METRIC_RESOLUTIONS = (
    StructuralMetricResolution(
        metric="exact_timestamp_swing_disagreement_rate",
        candidate_universe=_SWING_UNIVERSE,
        numerator=(
            "Comparable detected swing candidates that exactly one series "
            "detects."
        ),
        denominator_id=COMPARABLE_DETECTED_EVENT_UNION,
        denominator=(
            "Swing candidates at least one series detects and both series can "
            "evaluate, i.e. both hold every session of the detector's own "
            "T-3..T+3 confirmation reach."
        ),
        agreement_treatment=(
            "Both series detect, or both series decline to detect, a comparable "
            "candidate. Only the detected ones enter the denominator; a "
            "candidate neither series detects is not an event."
        ),
        disagreement_treatment=(
            "Exactly one series detects a comparable candidate: one event in "
            "the numerator and one in the denominator."
        ),
        not_comparable_treatment=NOT_COMPARABLE_EXCLUDED,
        absent_source_level_treatment=(
            "Not applicable; a swing candidate has no source level."
        ),
        availability_gap_treatment=(
            f"{NOT_COMPARABLE_AVAILABILITY_GAP}: a required session is absent "
            "inside a series' own coverage. Excluded, and separately gated by "
            "the parent protocol's hard availability metrics."
        ),
        pending_confirmation_treatment=(
            f"{NOT_COMPARABLE_CONFIRMATION_PENDING}: a required session had not "
            "closed or not been ingested at the sample's evaluation instant. "
            "Excluded, so appending later history cannot rewrite a past verdict."
        ),
        aggregation=_PAIRWISE_AGGREGATION,
        denominator_intent=DENOMINATOR_INTENT_RECOVERABLE_BUT_DEFECTIVE,
        threshold_intent_evidence=(
            "The frozen source_of_rationale is 'BTC-019B observed 12.1212% "
            "caused by two adjacent-week shifts'. That figure is 4/33 in "
            f"{BTC019B_STRUCTURAL_FORMULA_SOURCE}, whose denominator is the "
            "all-detected-event union of the compared swing sets, so the frozen "
            "0.15 was fixed to sit above it. All four of those numerator events "
            "are NOT_COMPARABLE availability gaps under the comparison "
            "contract, so under the resolved denominator the anchor observation "
            "is not rescaled, it is zero."
        ),
        threshold_semantics=THRESHOLD_SEMANTICS_NOT_RECOVERABLE,
        reason_codes=(
            FROZEN_V2_DECLARES_NO_DENOMINATOR,
            NOT_COMPARABLE_CATEGORY_ABSENT_AT_FREEZE,
            ONLY_RECOVERABLE_READING_IS_THE_KNOWN_DEFECT,
            THRESHOLD_ANCHOR_ENTIRELY_AVAILABILITY_DRIVEN,
            AGGREGATION_BASIS_UNDECLARED_AT_FREEZE,
            FROZEN_VERDICT_DEPENDS_ON_DENOMINATOR,
        ),
    ),
    StructuralMetricResolution(
        metric="within_1_week_swing_disagreement_rate",
        candidate_universe=_SWING_UNIVERSE,
        numerator=(
            "Comparable one-sided swing disagreements that no opposing "
            "comparable one-sided disagreement of the same family sits within "
            "one weekly session of; matching is nearest-admissible-pair first, "
            "so it is independent of provider and dictionary order."
        ),
        denominator_id=COMPARABLE_DETECTED_EVENT_UNION_PAIRS_MERGED,
        denominator=(
            "The comparable detected swing event union with each matched pair "
            "counted once rather than twice, because a structure both series "
            "found one week apart is one structure."
        ),
        agreement_treatment=(
            "As the exact-timestamp metric, plus: a matched pair within the "
            "tolerance is an agreement about one merged structure."
        ),
        disagreement_treatment=(
            "An unmatched comparable one-sided detection, counted once in the "
            "numerator and once in the unmerged part of the denominator."
        ),
        not_comparable_treatment=NOT_COMPARABLE_EXCLUDED,
        absent_source_level_treatment=(
            "Not applicable; a swing candidate has no source level."
        ),
        availability_gap_treatment=(
            f"{NOT_COMPARABLE_AVAILABILITY_GAP}: excluded before matching, so "
            "an availability gap can neither create nor absorb a matched pair."
        ),
        pending_confirmation_treatment=(
            f"{NOT_COMPARABLE_CONFIRMATION_PENDING}: excluded before matching."
        ),
        aggregation=_PAIRWISE_AGGREGATION,
        denominator_intent=DENOMINATOR_INTENT_RECOVERABLE_BUT_DEFECTIVE,
        threshold_intent_evidence=(
            "The frozen source_of_rationale is 'BTC-019B diagnostic rate was "
            "zero; 5% allows sparse unexplained events'. A zero numerator is "
            "denominator-invariant, so the observation carries no denominator "
            "information; the pair-merged denominator itself is recoverable "
            f"from {BTC019B_STRUCTURAL_FORMULA_SOURCE} (33 - matched pairs = "
            "31). What is not recoverable is the allowance: 0.05 was a round "
            "economic tolerance never bound to a stated universe, and the "
            "measured verdict against that identical number moves between the "
            "two denominators."
        ),
        threshold_semantics=THRESHOLD_SEMANTICS_NOT_RECOVERABLE,
        reason_codes=(
            FROZEN_V2_DECLARES_NO_DENOMINATOR,
            NOT_COMPARABLE_CATEGORY_ABSENT_AT_FREEZE,
            ONLY_RECOVERABLE_READING_IS_THE_KNOWN_DEFECT,
            THRESHOLD_ALLOWANCE_NOT_BOUND_TO_A_UNIVERSE,
            AGGREGATION_BASIS_UNDECLARED_AT_FREEZE,
            FROZEN_VERDICT_DEPENDS_ON_DENOMINATOR,
        ),
    ),
    StructuralMetricResolution(
        metric="within_2_week_swing_disagreement_rate",
        candidate_universe=_SWING_UNIVERSE,
        numerator=(
            "As within_1_week with a two weekly-session matching tolerance."
        ),
        denominator_id=COMPARABLE_DETECTED_EVENT_UNION_PAIRS_MERGED,
        denominator=(
            "As within_1_week with a two weekly-session matching tolerance."
        ),
        agreement_treatment=(
            "As within_1_week with a two weekly-session matching tolerance."
        ),
        disagreement_treatment=(
            "An unmatched comparable one-sided detection at two weeks of "
            "tolerance, which the frozen rationale reads as more than label "
            "timing noise."
        ),
        not_comparable_treatment=NOT_COMPARABLE_EXCLUDED,
        absent_source_level_treatment=(
            "Not applicable; a swing candidate has no source level."
        ),
        availability_gap_treatment=(
            f"{NOT_COMPARABLE_AVAILABILITY_GAP}: excluded before matching."
        ),
        pending_confirmation_treatment=(
            f"{NOT_COMPARABLE_CONFIRMATION_PENDING}: excluded before matching."
        ),
        aggregation=_PAIRWISE_AGGREGATION,
        denominator_intent=DENOMINATOR_INTENT_RECOVERABLE_BUT_DEFECTIVE,
        threshold_intent_evidence=(
            "The frozen source_of_rationale is 'BTC-019B diagnostic rate was "
            "zero; stricter 2% tail allowance'. Same structure as within_1_week: "
            "the pair-merged denominator is recoverable, the zero observation "
            "is denominator-invariant, and the 0.02 tail allowance was never "
            "bound to a universe."
        ),
        threshold_semantics=THRESHOLD_SEMANTICS_NOT_RECOVERABLE,
        reason_codes=(
            FROZEN_V2_DECLARES_NO_DENOMINATOR,
            NOT_COMPARABLE_CATEGORY_ABSENT_AT_FREEZE,
            ONLY_RECOVERABLE_READING_IS_THE_KNOWN_DEFECT,
            THRESHOLD_ALLOWANCE_NOT_BOUND_TO_A_UNIVERSE,
            AGGREGATION_BASIS_UNDECLARED_AT_FREEZE,
            FROZEN_VERDICT_DEPENDS_ON_DENOMINATOR,
        ),
    ),
    StructuralMetricResolution(
        metric="structural_state_disagreement_rate",
        candidate_universe=_SWING_UNIVERSE,
        numerator=(
            "Comparable one-sided swing disagreements whose level the detecting "
            "series also confirmed a breakout or reclaim from, so the "
            "difference changed downstream support/resistance state rather "
            "than only a label."
        ),
        denominator_id=COMPARABLE_DETECTED_EVENT_UNION,
        denominator=(
            "The comparable detected swing event union, unmerged: the same "
            "universe as the exact-timestamp metric, because this metric asks "
            "how often a swing difference propagates, not how often one occurs."
        ),
        agreement_treatment=(
            "A comparable swing candidate whose downstream breakout/reclaim "
            "state is the same on both series, including every candidate both "
            "series agree about."
        ),
        disagreement_treatment=(
            "One event in the numerator per comparable one-sided swing whose "
            "structural state changed."
        ),
        not_comparable_treatment=NOT_COMPARABLE_EXCLUDED,
        absent_source_level_treatment=(
            f"{NOT_COMPARABLE_SOURCE_LEVEL} on the derived candidate consulted "
            "for the state change: the swing itself stays in the denominator "
            "only if the swing is comparable, and contributes to the numerator "
            "only on a confirmed derived level."
        ),
        availability_gap_treatment=(
            f"{NOT_COMPARABLE_AVAILABILITY_GAP}: excluded."
        ),
        pending_confirmation_treatment=(
            f"{NOT_COMPARABLE_CONFIRMATION_PENDING}: excluded."
        ),
        aggregation=_PAIRWISE_AGGREGATION,
        denominator_intent=DENOMINATOR_INTENT_RECOVERABLE_BUT_DEFECTIVE,
        threshold_intent_evidence=(
            "The frozen source_of_rationale is 'BTC-019B separated structural "
            "effects from exact timestamp labels' -- an attribution of the "
            "concept, not of the number. BTC-019B measured 2/33 = 6.0606%, "
            "which exceeds the frozen 0.05, so the threshold was never an "
            "accommodation of its own calibration observation; and both "
            "numerator events belong to the two BTC-019B pairs that are "
            "NOT_COMPARABLE availability gaps under the comparison contract."
        ),
        threshold_semantics=THRESHOLD_SEMANTICS_NOT_RECOVERABLE,
        reason_codes=(
            FROZEN_V2_DECLARES_NO_DENOMINATOR,
            NOT_COMPARABLE_CATEGORY_ABSENT_AT_FREEZE,
            ONLY_RECOVERABLE_READING_IS_THE_KNOWN_DEFECT,
            THRESHOLD_ANCHOR_ENTIRELY_AVAILABILITY_DRIVEN,
            THRESHOLD_ANCHOR_EXCEEDS_FROZEN_THRESHOLD,
            AGGREGATION_BASIS_UNDECLARED_AT_FREEZE,
            FROZEN_VERDICT_DEPENDS_ON_DENOMINATOR,
        ),
    ),
    StructuralMetricResolution(
        metric="breakout_disagreement_rate",
        candidate_universe=(
            "Breakout candidates on the pair's common weekly calendar: one per "
            "shared source swing high, keyed by that source level, not by the "
            "confirmation week."
        ),
        numerator=(
            "Comparable breakout candidates the two series resolve differently "
            "-- exactly one confirms, or both confirm in different weeks."
        ),
        denominator_id=COMPARABLE_DETECTED_EVENT_UNION,
        denominator=(
            "Breakout candidates at least one series confirms and both series "
            "can evaluate, i.e. both hold every week from the source swing "
            "through the later confirmation, or through the end of the shared "
            "calendar when either series never confirms."
        ),
        agreement_treatment=(
            "Both series confirm in the same week, or neither ever confirms "
            "across the whole shared remaining calendar. Only confirmed "
            "candidates enter the denominator."
        ),
        disagreement_treatment=(
            "One event in numerator and denominator per comparable candidate "
            "with a differing confirmation."
        ),
        not_comparable_treatment=NOT_COMPARABLE_EXCLUDED,
        absent_source_level_treatment=(
            f"{NOT_COMPARABLE_SOURCE_LEVEL}: a breakout whose source swing is "
            "itself not comparable, or which the two series hold no shared "
            "source swing for, is excluded. The upstream swing disagreement is "
            "already counted once in the swing metrics; counting its shadow "
            "again would double-count one difference."
        ),
        availability_gap_treatment=(
            f"{NOT_COMPARABLE_AVAILABILITY_GAP}: excluded, with the missing "
            "confirmation weeks named."
        ),
        pending_confirmation_treatment=(
            f"{NOT_COMPARABLE_CONFIRMATION_PENDING}: excluded. 'Never confirms' "
            "is a claim about every remaining week, so it may only be made "
            "where every remaining week has arrived."
        ),
        aggregation=_PAIRWISE_AGGREGATION,
        denominator_intent=DENOMINATOR_INTENT_NOT_RECOVERABLE,
        threshold_intent_evidence=(
            "The frozen source_of_rationale is 'Economic reasoning using "
            "existing deterministic breakout logic'. No calibration artifact "
            "exists: BTC-019B computed no breakout rate at all, and the frozen "
            "V2 protocol lists breakout under its 'swings' metric family while "
            f"the only pre-existing implementation, {V1_STRUCTURAL_FORMULA_SOURCE}, "
            "measures it over a per-category breakout event union against a "
            "two-of-three provider consensus. Those are different denominators "
            "and the frozen definition does not choose between them."
        ),
        threshold_semantics=THRESHOLD_SEMANTICS_NOT_RECOVERABLE,
        reason_codes=(
            FROZEN_V2_DECLARES_NO_DENOMINATOR,
            NOT_COMPARABLE_CATEGORY_ABSENT_AT_FREEZE,
            CANDIDATE_UNIVERSE_AMBIGUOUS,
            PRE_EXISTING_FORMULAS_DISAGREE,
            NO_CALIBRATION_ARTIFACT_EXISTS,
            AGGREGATION_BASIS_UNDECLARED_AT_FREEZE,
            FROZEN_VERDICT_DEPENDS_ON_DENOMINATOR,
        ),
    ),
    StructuralMetricResolution(
        metric="reclaim_disagreement_rate",
        candidate_universe=(
            "Reclaim candidates on the pair's common weekly calendar: one per "
            "shared source swing low, keyed by that source level, not by the "
            "confirmation week."
        ),
        numerator=(
            "Comparable reclaim candidates the two series resolve differently "
            "-- exactly one confirms, or both confirm in different weeks."
        ),
        denominator_id=COMPARABLE_DETECTED_EVENT_UNION,
        denominator=(
            "Reclaim candidates at least one series confirms and both series "
            "can evaluate, on the same confirmation calendar rule as breakouts."
        ),
        agreement_treatment=(
            "Both series confirm in the same week, or neither ever confirms "
            "across the whole shared remaining calendar."
        ),
        disagreement_treatment=(
            "One event in numerator and denominator per comparable candidate "
            "with a differing confirmation."
        ),
        not_comparable_treatment=NOT_COMPARABLE_EXCLUDED,
        absent_source_level_treatment=(
            f"{NOT_COMPARABLE_SOURCE_LEVEL}: as breakouts."
        ),
        availability_gap_treatment=(
            f"{NOT_COMPARABLE_AVAILABILITY_GAP}: excluded, with the missing "
            "confirmation weeks named."
        ),
        pending_confirmation_treatment=(
            f"{NOT_COMPARABLE_CONFIRMATION_PENDING}: excluded, as breakouts."
        ),
        aggregation=_PAIRWISE_AGGREGATION,
        denominator_intent=DENOMINATOR_INTENT_NOT_RECOVERABLE,
        threshold_intent_evidence=(
            "The frozen source_of_rationale is 'Economic reasoning using "
            "existing deterministic reclaim logic'. Identical position to "
            "breakout: no calibration artifact, and two incompatible "
            "pre-existing candidate universes."
        ),
        threshold_semantics=THRESHOLD_SEMANTICS_NOT_RECOVERABLE,
        reason_codes=(
            FROZEN_V2_DECLARES_NO_DENOMINATOR,
            NOT_COMPARABLE_CATEGORY_ABSENT_AT_FREEZE,
            CANDIDATE_UNIVERSE_AMBIGUOUS,
            PRE_EXISTING_FORMULAS_DISAGREE,
            NO_CALIBRATION_ARTIFACT_EXISTS,
            AGGREGATION_BASIS_UNDECLARED_AT_FREEZE,
            FROZEN_VERDICT_DEPENDS_ON_DENOMINATOR,
        ),
    ),
)


# --- denominator interpretations considered -----------------------------------

DENOMINATOR_INTERPRETATIONS = (
    {
        "id": COMPARABLE_DETECTED_EVENT_UNION,
        "label": "A. comparable_detected_event_union",
        "not_comparable_treatment": NOT_COMPARABLE_EXCLUDED,
        "verdict": "ADOPTED",
        "basis": (
            "A structurally unevaluable event is neither an agreement nor a "
            "disagreement: it carries no information about whether two series "
            "read structure the same way, so it belongs in neither the "
            "numerator nor the denominator of a rate named 'structural "
            "disagreement'. The parent protocol already gates availability "
            "separately and hard, so removing availability from the structural "
            "rate does not remove it from the approval decision."
        ),
    },
    {
        "id": ALL_DETECTED_EVENT_UNION,
        "label": (
            "B. all_detected_event_union, not-comparable counted as agreement"
        ),
        "not_comparable_treatment": NOT_COMPARABLE_AS_AGREEMENT,
        "verdict": "REJECTED",
        "basis": (
            "Silently converts an unanswered question into a favourable answer. "
            "It is also monotone in the wrong direction: every additional "
            "outage adds a free agreement, so a series that publishes less "
            "scores better. No pre-existing artifact defines it; it is a "
            "reading invented by the question, not recovered from the record."
        ),
    },
    {
        "id": ALL_DETECTED_EVENT_UNION,
        "label": (
            "B0. all_detected_event_union, not-comparable counted as "
            "disagreement -- the frozen protocol's only executable behaviour"
        ),
        "not_comparable_treatment": NOT_COMPARABLE_AS_DISAGREEMENT,
        "verdict": "REJECTED",
        "basis": (
            "This is what the pre-existing formulas actually do, because they "
            "have no third outcome: a one-sided detection caused by an absent "
            "week lands in the symmetric difference and in the union. It is "
            "therefore the only denominator that can be recovered from the "
            "record -- and it is exactly the correctness defect "
            "BTC019_COMPLETION_GATE_ASSESSMENT_V1 recorded and "
            "CROSS_PROVIDER_STRUCTURE_COMPARISON_V2 closed. Recovering it "
            "would reinstate the defect; replacing it is new semantics. That "
            "is the whole reason this resolution is not a clarification."
        ),
    },
    {
        "id": COMPARABLE_CANDIDATE_SESSIONS,
        "label": "C. every comparable candidate session, detected or not",
        "not_comparable_treatment": NOT_COMPARABLE_EXCLUDED,
        "verdict": "REJECTED",
        "basis": (
            "The candidate universe is every weekly session, so the "
            "denominator measures how long the sample is rather than how often "
            "the two series disagree, and any threshold on it would be a "
            "function of sample length. Both pre-existing formulas use "
            "detected-event unions, so this has no support in the record "
            "either."
        ),
    },
    {
        "id": COMPARABLE_DETECTED_EVENT_UNION_PAIRS_MERGED,
        "label": (
            "D. A, with tolerance-matched pairs merged -- for the within-N-week "
            "metrics only"
        ),
        "not_comparable_treatment": NOT_COMPARABLE_EXCLUDED,
        "verdict": "ADOPTED_FOR_WITHIN_N_WEEK_METRICS",
        "basis": (
            "Recovered, not invented: BTC-019B's own pre-existing formula "
            "subtracts the matched pair count from the union, and a "
            "'within N week matched' rate is meaningless if a structure both "
            "series found, one week apart, still counts twice in its "
            "denominator. This is the one place where the six metrics do not "
            "share a denominator, and the pre-existing record is explicit "
            "about it (33 for exact and structural-state, 31 for within-N)."
        ),
    },
)


# --- pre-existing evidence ----------------------------------------------------


@dataclass(frozen=True)
class EvidenceItem:
    """One pre-existing artifact or module, and what it does or does not fix.

    A persisted research artifact is immutable by governance, so its digest is
    pinned into the record. A source module is not: it is recorded by path and
    symbol, because pinning a formatting change would assert an invariant the
    repository never promised and the frozen artifacts already carry the
    numbers the argument rests on.
    """

    tier: int
    identifier: str
    path: str
    establishes: str
    predates_defect_discovery: bool
    symbol: str = ""

    def as_record(self, repository_root: Path) -> dict[str, Any]:
        if not 1 <= self.tier <= 6:
            raise DenominatorResolutionError("evidence tier must be 1..6")
        target = repository_root / self.path
        if not target.is_file():
            raise DenominatorResolutionError(
                f"pre-existing evidence {self.path!r} is missing"
            )
        pinned = self.path.startswith("research_artifacts/")
        return {
            "tier": self.tier,
            "identifier": self.identifier,
            "path": self.path,
            "symbol": self.symbol,
            "digest_pinned": pinned,
            "sha256": (
                hashlib.sha256(target.read_bytes()).hexdigest() if pinned else None
            ),
            "establishes": self.establishes,
            "predates_defect_discovery": self.predates_defect_discovery,
        }


EXAMINED_EVIDENCE = (
    EvidenceItem(
        tier=1,
        identifier="BTC_REFERENCE_COMPOSITE_V2 frozen definition",
        path=V2_PROTOCOL_DEFINITION_PATH,
        establishes=(
            "Declares metric name, threshold, direction, hard flag, rationale "
            "and validation stage for each of the six gates, and a "
            "validation_metric_families listing. It declares no numerator, no "
            "denominator, no candidate universe, no comparison basis and no "
            "treatment of an unevaluable event, for any of the six."
        ),
        predates_defect_discovery=True,
    ),
    EvidenceItem(
        tier=2,
        identifier="BTC_REFERENCE_COMPOSITE_V1 structural comparison formula",
        path="btc_predictor/research/reference_composite_empirical.py",
        symbol="_structural_comparison",
        establishes=(
            "_structural_comparison: per category (swing_high, swing_low, "
            "breakout, reclaim), rate = |events XOR consensus| / "
            "|events OR consensus| against a two-of-three raw-provider "
            "consensus; plus a combined_swing union across the two swing "
            "families. A one-sided detection caused by an absent week is "
            "counted as a disagreement, because no other outcome exists."
        ),
        predates_defect_discovery=True,
    ),
    EvidenceItem(
        tier=3,
        identifier="BTC-019B swing gate diagnostics formula",
        path="btc_predictor/research/btc019b_diagnostics.py",
        symbol="_swing_metric_summary",
        establishes=(
            "_swing_metric_summary: exact_timestamp and structural_state over "
            "len(exact_union); within_1_week and within_2_week over "
            "len(exact_union) - matched_pair_count. The named calibration "
            "source for four of the six frozen thresholds. It also has no "
            "third outcome, and it computes no breakout or reclaim rate."
        ),
        predates_defect_discovery=True,
    ),
    EvidenceItem(
        tier=3,
        identifier="BTC-019B frozen swing diagnostics",
        path=BTC019B_SWING_DIAGNOSTICS_PATH,
        establishes=(
            "The frozen numbers behind the thresholds: exact_timestamp 4/33 = "
            "12.1212%, structural_state 2/33 = 6.0606%, within_1_week and "
            "within_2_week 0/31. Two denominators, 33 and 31, in one artifact."
        ),
        predates_defect_discovery=True,
    ),
    EvidenceItem(
        tier=4,
        identifier="BTC-019B frozen governance assessment",
        path=BTC019B_DECISION_PATH,
        establishes=(
            "exact_swing_gate_assessment: 'Exact timestamps are too brittle as "
            "a standalone weekly-structure gate, but the failure exposed real "
            "omitted-week level and breakout state changes.' Pre-existing "
            "design intent that treats a week the candidate itself omitted as "
            "an economically real structural difference -- the opposite "
            "reading to excluding an unevaluable event, and never reconciled "
            "with it in any frozen artifact."
        ),
        predates_defect_discovery=True,
    ),
    EvidenceItem(
        tier=4,
        identifier="BTC_REFERENCE_COMPOSITE_V1 frozen candidate definition",
        path=V1_CANDIDATE_DEFINITION_PATH,
        establishes=(
            "The V1 frozen gate set contains one structural rate, "
            "external_combined_swing_disagreement_rate_maximum = 0.10, over "
            "the combined swing union. No frozen V1 breakout or reclaim gate "
            "exists for V2's two to inherit a universe from."
        ),
        predates_defect_discovery=True,
    ),
    EvidenceItem(
        tier=6,
        identifier="BTC019_COMPLETION_GATE_ASSESSMENT_V1",
        path=COMPLETION_GATE_ASSESSMENT_PATH,
        establishes=(
            "Records the row-versus-calendar defect that makes the recoverable "
            "denominator inadmissible, and that six V2 approval gates are "
            "computed from the affected comparison."
        ),
        predates_defect_discovery=False,
    ),
    EvidenceItem(
        tier=6,
        identifier=COMPARISON_CONTRACT_VERSION,
        path=f"{COMPARISON_OUTPUT_NAMESPACE}/{COMPARISON_REPORT_FILENAME}",
        establishes=(
            "Supplies the comparability contract this resolution binds, and "
            "the already-inspected measurements used here only to show that "
            "the denominator choice is material."
        ),
        predates_defect_discovery=False,
    ),
)

REJECTED_AS_POST_HOC = (
    {
        "evidence": (
            "The measured pass/fail verdicts of the six gates on the "
            "2019-2022 and 2023-2025 samples"
        ),
        "admitted_for": (
            "Showing that the denominator choice changes verdicts, which is "
            "what makes this a governance question rather than an editorial one."
        ),
        "refused_for": (
            "Choosing a denominator. The adopted denominator is not the "
            "favourable one: under it reclaim still fails five of six measured "
            "pairs and within_2_week four of six."
        ),
    },
    {
        "evidence": (
            "Prose written after the defect was found -- the "
            "CROSS_PROVIDER_STRUCTURE_COMPARISON_V2 report, the BTC-019 "
            "completion-gate report, the ticket Implementation Notes and "
            "CURRENT_STATE"
        ),
        "admitted_for": "Establishing what is known and unresolved today.",
        "refused_for": (
            "Establishing what the frozen protocol intended in 2026-08. None "
            "of it existed when the V2 definition hash was taken."
        ),
    },
    {
        "evidence": (
            "The observation that the comparable denominator would let "
            "breakout_disagreement_rate pass on all six measured pairs"
        ),
        "admitted_for": "Nothing.",
        "refused_for": (
            "Every purpose. It is the single most outcome-favourable fact "
            "available and it is precisely the fact a contaminated process "
            "would lean on."
        ),
    },
)


# --- coverage / comparability contract ----------------------------------------

REQUIRED_COVERAGE_EVIDENCE = (
    "candidate_event_count",
    "all_detected_event_count",
    "comparable_event_count",
    "not_comparable_event_count",
    "structural_comparability_rate",
    "not_comparable_rate",
    "not_comparable_reason_counts",
    "availability_gap_side_counts",
)

COVERAGE_CONTRACT = {
    "purpose": (
        "Excluding an unevaluable event from a structural rate must never let "
        "an outage look like quality. Coverage is therefore published beside "
        "every structural rate, per pair and per event family."
    ),
    "structural_comparability_rate": (
        "comparable_event_count / all_detected_event_count, resolved in an "
        "explicit Decimal context, reported as null when the denominator is "
        "zero rather than as zero."
    ),
    "not_comparable_rate": "1 - structural_comparability_rate.",
    "required_evidence": list(REQUIRED_COVERAGE_EVIDENCE),
    "completeness_invariant": (
        "comparable_event_count + not_comparable_event_count == "
        "all_detected_event_count, and comparable_candidate_count + "
        "not_comparable_candidate_count == candidate_event_count, for every "
        "pair and every family."
    ),
    "new_threshold_created": False,
    "new_numeric_gate_created": False,
    "why_no_numeric_floor": (
        "A minimum comparability rate would be a threshold, and this task may "
        "not calibrate one. The successor therefore requires the evidence and "
        "defers the question of a floor to the separate pre-sealed threshold "
        "calibration task, which must decide it before any sealed evaluation."
    ),
    "existing_parent_defences": [
        "reference_usable_rate (hard, minimum 0.995)",
        "reference_unavailable_rate (hard, maximum 0.005)",
        "daily_bucket_usable_rate (hard, minimum 0.995)",
        "weekly_bucket_usable_rate (hard, minimum 0.990)",
        "silent_incomplete_bucket_omission_count (hard, equal 0)",
        "unrecorded_quality_state_count (hard, equal 0)",
    ],
    "parent_defence_limitation": (
        "Those gates bind the candidate reference series only. The other side "
        "of a comparison is a raw provider whose availability nothing gates, "
        "so comparability evidence is the only place a gap-heavy comparison "
        "series becomes visible."
    ),
    "provenance_requirement": {
        "metric": "unrecorded_not_comparable_event_count",
        "direction": "equal",
        "threshold": 0,
        "hard": True,
        "new_in_successor": True,
        "derivation": (
            "Not a calibrated rate. It is the parent protocol's own "
            "zero-count provenance principle -- unrecorded_quality_state_count "
            "and silent_incomplete_bucket_omission_count are both hard equal-0 "
            "gates -- applied to the category the parent did not have: every "
            "excluded event must be individually reconstructable, with its "
            "reason code, its side and its missing sessions."
        ),
    },
}


# --- frozen-artifact reads ----------------------------------------------------


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("ascii")).hexdigest()


def frozen_parent_definition(repository_root: Path) -> dict[str, Any]:
    """Read the frozen V2 definition and refuse a changed hash.

    The parent hash is an immutable record of what was frozen. This module can
    only read it: there is no code path here that writes the parent artifact.
    """

    path = repository_root / V2_PROTOCOL_DEFINITION_PATH
    definition = json.loads(path.read_text())
    if definition.get("reference_policy_version") != PARENT_PROTOCOL_VERSION:
        raise DenominatorResolutionError(
            "parent artifact is not BTC_REFERENCE_COMPOSITE_V2"
        )
    if definition.get("definition_sha256") != PARENT_DEFINITION_SHA256:
        raise DenominatorResolutionError(
            "frozen BTC_REFERENCE_COMPOSITE_V2 definition hash changed"
        )
    artifact_digest = hashlib.sha256(path.read_bytes()).hexdigest()
    expected = EXPECTED_V2_PROTOCOL_ARTIFACT_SHA256["protocol_definition.json"]
    if artifact_digest != expected:
        raise DenominatorResolutionError(
            "frozen BTC_REFERENCE_COMPOSITE_V2 protocol artifact was modified"
        )
    return definition


def frozen_structural_gates(repository_root: Path) -> dict[str, dict[str, Any]]:
    """Return the six affected gates exactly as the frozen definition holds them."""

    definition = frozen_parent_definition(repository_root)
    gates = {item["metric"]: item for item in definition["approval_gates"]}
    missing = [metric for metric in AFFECTED_V2_GATE_METRICS if metric not in gates]
    if missing:
        raise DenominatorResolutionError(
            f"frozen V2 protocol no longer declares {missing}"
        )
    return {
        metric: {
            "metric": metric,
            "threshold": gates[metric]["threshold"],
            "direction": gates[metric]["direction"],
            "hard": gates[metric]["hard"],
            "validation_stage": gates[metric]["validation_stage"],
            "rationale": gates[metric]["rationale"],
            "source_of_rationale": gates[metric]["source_of_rationale"],
        }
        for metric in AFFECTED_V2_GATE_METRICS
    }


def _verify_frozen_evidence_digests(repository_root: Path) -> None:
    """Refuse to reason from calibration evidence that has changed."""

    groups = (
        (repository_root / "research_artifacts/btc019b", EXPECTED_BTC019B_ARTIFACT_SHA256),
        (
            repository_root
            / "research_artifacts/btc_reference_composite/BTC_REFERENCE_COMPOSITE_V1",
            EXPECTED_V1_ARTIFACT_SHA256,
        ),
    )
    for directory, expected in groups:
        actual = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.iterdir())
            if path.is_file()
        }
        if actual != expected:
            raise DenominatorResolutionError(
                f"frozen calibration evidence changed: {directory.name}"
            )


# --- threshold-intent anchor --------------------------------------------------


def btc019b_threshold_anchor(repository_root: Path) -> dict[str, Any]:
    """Recompute the one numeric anchor the frozen thresholds ever had.

    `exact_timestamp_swing_disagreement_rate` is the only frozen structural
    threshold whose rationale carries a number. This reads BTC-019B's own
    frozen counts, recomputes the rate in an explicit Decimal context, and
    records what the same observation becomes once the events that produced it
    are classified. Nothing new is measured: both sides come from artifacts
    that were already inspected and frozen.
    """

    diagnostics = json.loads(
        (repository_root / BTC019B_SWING_DIAGNOSTICS_PATH).read_text()
    )
    metrics = diagnostics["metrics"]
    comparison_report = json.loads(
        (
            repository_root
            / COMPARISON_OUTPUT_NAMESPACE
            / COMPARISON_REPORT_FILENAME
        ).read_text()
    )
    probe = comparison_report["btc019b_known_case_probe"]
    exact = metrics["exact_timestamp"]
    structural = metrics["structural_state"]
    if probe["frozen_exact_timestamp_denominator"] != exact["denominator"]:
        raise DenominatorResolutionError(
            "BTC-019B denominator disagrees with the comparison contract's probe"
        )
    return {
        "source": (
            "frozen BTC-019B artifacts and the frozen "
            f"{COMPARISON_CONTRACT_VERSION} known-case probe"
        ),
        "exact_timestamp": {
            "frozen_numerator": exact["disagreement_count"],
            "frozen_denominator": exact["denominator"],
            "frozen_denominator_id": ALL_DETECTED_EVENT_UNION,
            "frozen_rate": _rate(exact["disagreement_count"], exact["denominator"]),
            "numerator_events_not_comparable": probe["not_comparable_count"],
            "numerator_under_resolved_denominator": probe[
                "remaining_disagreement_count"
            ],
            "rate_under_resolved_denominator_numerator": _rate(
                probe["remaining_disagreement_count"],
                exact["denominator"] - probe["not_comparable_count"],
            ),
        },
        "structural_state": {
            "frozen_numerator": structural["disagreement_count"],
            "frozen_denominator": structural["denominator"],
            "frozen_denominator_id": ALL_DETECTED_EVENT_UNION,
            "frozen_rate": _rate(
                structural["disagreement_count"], structural["denominator"]
            ),
        },
        "within_week_denominator": metrics["within_1_week"]["denominator"],
        "within_week_denominator_id": ALL_DETECTED_EVENT_UNION_PAIRS_MERGED,
        "finding": (
            "The one numeric anchor the frozen structural thresholds have is "
            "an all-detected-event rate whose numerator is entirely "
            "availability, and the structural_state observation of 6.0606% "
            "exceeds the 0.05 that was frozen for it. Neither number survives "
            "as an anchor once the denominator is written down."
        ),
    }


def _rate(numerator: int, denominator: int) -> str | None:
    if denominator <= 0:
        return None
    return str(_RATE_CONTEXT.divide(Decimal(numerator), Decimal(denominator)))


# --- materiality --------------------------------------------------------------


def denominator_materiality(repository_root: Path) -> dict[str, Any]:
    """Summarise, from the persisted comparison report, that the choice matters.

    Counts only. This is admitted to show the question is material, never to
    choose an answer, so nothing here is a rate or a verdict of this module's
    own making.
    """

    path = (
        repository_root / COMPARISON_OUTPUT_NAMESPACE / COMPARISON_REPORT_FILENAME
    )
    report = json.loads(path.read_text())
    if report.get("schema_version") != COMPARISON_REPORT_SCHEMA_VERSION:
        raise DenominatorResolutionError(
            "persisted comparison report does not carry "
            f"{COMPARISON_REPORT_SCHEMA_VERSION}"
        )
    if report.get("comparison_contract_version") != COMPARISON_CONTRACT_VERSION:
        raise DenominatorResolutionError(
            "persisted comparison report names a different comparison contract"
        )
    gates = {item["metric"]: item for item in report["frozen_v2_gate_measurability"]["gates"]}
    per_metric = []
    for metric in AFFECTED_V2_GATE_METRICS:
        gate = gates[metric]
        rows = gate["measurements"]
        per_metric.append(
            {
                "metric": metric,
                "hard": gate["hard"],
                "measured_pair_count": len(rows),
                "verdict_flips_between_denominators": sum(
                    not row["verdict_stable_across_denominators"] for row in rows
                ),
                "undefined_measurement_count": gate["undefined_measurement_count"],
                "fails_on_resolved_denominator": sum(
                    row["frozen_threshold_verdict_on_revised_denominator"] == "FAIL"
                    for row in rows
                ),
                "fails_on_prior_denominator": sum(
                    row["frozen_threshold_verdict_on_prior_denominator"] == "FAIL"
                    for row in rows
                ),
            }
        )
    return {
        "source": f"{COMPARISON_OUTPUT_NAMESPACE}/{COMPARISON_REPORT_FILENAME}",
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "samples": "already-inspected 2019-2022 and 2023-2025 only",
        "sealed_sample_used": False,
        "admitted_for": "materiality only",
        "per_metric": per_metric,
        "metrics_with_any_verdict_flip": sum(
            item["verdict_flips_between_denominators"] > 0 for item in per_metric
        ),
        "hard_metrics_with_any_verdict_flip": sum(
            item["hard"] and item["verdict_flips_between_denominators"] > 0
            for item in per_metric
        ),
        "resolved_denominator_is_uniformly_favourable": all(
            item["fails_on_resolved_denominator"] == 0 for item in per_metric
        ),
        "totals": report["totals"],
    }


# --- successor protocol -------------------------------------------------------


def successor_protocol_definition(repository_root: Path) -> dict[str, Any]:
    """Build the proposed successor definition and its own hash.

    The successor inherits every parent gate unchanged. It adds only what the
    parent left undefined: the six structural metrics' complete semantics, the
    comparability contract they are read through, and the coverage evidence
    that keeps an excluded event visible. Thresholds are carried across from
    the parent artifact verbatim, so no code path here can author one.
    """

    gates = frozen_structural_gates(repository_root)
    payload = {
        "schema_version": SUCCESSOR_SCHEMA_VERSION,
        "reference_policy_version": SUCCESSOR_PROTOCOL_VERSION,
        "status": SUCCESSOR_STATUS,
        "research_only": True,
        "production_promotion_authorized": False,
        "parent_protocol_version": PARENT_PROTOCOL_VERSION,
        "parent_definition_sha256": PARENT_DEFINITION_SHA256,
        "parent_governance_clause": (
            "BTC_REFERENCE_COMPOSITE_V2 governance.material_change_requires = "
            "'BTC_REFERENCE_COMPOSITE_V3 or later'"
        ),
        "inherits_from_parent_unchanged": (
            "Every parent approval gate, threshold, direction and hard flag; "
            "MEDIAN_OHLC_V2; the quality-state semantics; the higher-timeframe "
            "aggregation contract; the point-in-time contract; the provider "
            "set; the prohibited actions; and the sealed-sample window and its "
            "guard."
        ),
        "changes_relative_to_parent": [
            "Defines the numerator, denominator, candidate universe and "
            "aggregation basis of the six structural gates, which the parent "
            "declared only by name and threshold.",
            "Introduces the NOT_COMPARABLE outcome and its treatment, a "
            "category the parent's vocabulary does not contain.",
            "Requires structural comparability and coverage evidence beside "
            "every structural rate.",
            "Adds one hard zero-count provenance requirement, "
            "unrecorded_not_comparable_event_count, derived from the parent's "
            "own zero-count provenance gates.",
            "Marks the six inherited structural thresholds "
            f"{THRESHOLD_CARRIED_FORWARD_UNCALIBRATED}: their numbers are "
            "carried across unchanged but may not be evaluated until a "
            "separate pre-sealed calibration task binds them to these "
            "denominators.",
        ],
        "does_not_change": [
            "any parent threshold value",
            "any parent gate direction",
            "any parent hard/soft status",
            "candidate construction or MEDIAN_OHLC_V2",
            "production strategy semantics",
            "PRICE_SOURCE_POLICY_V1",
            "BTC_REFERENCE_COMPOSITE_V1 or BTC-019B",
        ],
        "comparison_contract_version": COMPARISON_CONTRACT_VERSION,
        "superseded_comparison_contract_version": LEGACY_COMPARISON_CONTRACT_VERSION,
        "source_detector_version": WEEKLY_STRUCTURE_DETECTOR_VERSION,
        "comparison_basis": PAIRWISE_COMPARISON_BASIS,
        "candidate_construction": (
            "Unchanged from the parent: MEDIAN_OHLC_V2, its quality-state "
            "semantics, its point-in-time contract and its higher-timeframe "
            "aggregation rules. This successor changes how the candidate is "
            "measured, never how it is built."
        ),
        "provider_and_quorum_semantics": (
            "Required providers, minimum_provider_count and the "
            "single-venue-fallback prohibition are inherited unchanged and "
            "govern candidate construction. Structural measurement forms no "
            "quorum: it is pairwise between declared comparison series on their "
            "common weekly calendar, because a two-of-three consensus series "
            "assembled from providers with different calendars has no calendar "
            "of its own for a comparability contract to require. This differs "
            "from the pre-existing V1 and BTC-019B formulas, which both "
            "compared against a consensus, and the parent protocol declared no "
            "basis either way."
        ),
        "denominator_semantics_version": DENOMINATOR_SEMANTICS_VERSION,
        "not_comparable_states": [
            NOT_COMPARABLE_AVAILABILITY_GAP,
            NOT_COMPARABLE_CONFIRMATION_PENDING,
            NOT_COMPARABLE_SERIES_COVERAGE,
            NOT_COMPARABLE_SOURCE_LEVEL,
        ],
        "structural_metrics": [
            item.as_record(gates[item.metric])
            for item in STRUCTURAL_METRIC_RESOLUTIONS
        ],
        "coverage_contract": COVERAGE_CONTRACT,
        "threshold_calibration": {
            "status": "REQUIRED_BEFORE_ANY_SEALED_EVALUATION",
            "scope": list(AFFECTED_V2_GATE_METRICS),
            "performed_here": False,
            "rule": (
                "The successor may not be frozen for evaluation, and no "
                "hash-bound sealed validator may be built on it, until a "
                "separate pre-sealed calibration and governance task binds a "
                "threshold to each of these denominators. That task may use "
                "the already-inspected samples and predeclared economic "
                "reasoning; it may not use the sealed 2015-2019 sample."
            ),
        },
        "sealed_sample": {
            "start": UNTOUCHED_OOS_START.isoformat(),
            "end": UNTOUCHED_OOS_END.isoformat(),
            "opened": False,
            "collected": False,
            "guard": "guard_untouched_validation_sample, inherited unchanged",
        },
    }
    return {**payload, "definition_sha256": _digest(payload)}


def successor_definition_sha256(repository_root: Path) -> str:
    return successor_protocol_definition(repository_root)["definition_sha256"]


# --- the resolution record ----------------------------------------------------

FINAL_CLASSIFICATION = NEW_PROTOCOL_VERSION_REQUIRED

CLASSIFICATION_RULE = (
    f"{CLARIFICATION_VALID} only when the frozen definition, the code that "
    "predates the defect, or a calibration artifact fixes each affected "
    "metric's denominator AND that recovered denominator is admissible, so "
    "writing it down changes no statistical rule; "
    f"{BLOCKED_BY_UNRESOLVED_EVIDENCE} when required pre-existing evidence is "
    "missing or contradictory and neither conclusion can be justified; "
    f"{NEW_PROTOCOL_VERSION_REQUIRED} otherwise -- in particular when the only "
    "recoverable denominator is the known correctness defect, when a metric's "
    "candidate universe was never determinable, or when a frozen threshold's "
    "meaning does not survive the denominator being written down."
)


def build_resolution_record(repository_root: Path) -> dict[str, Any]:
    """Build the deterministic governance record for the six structural gates."""

    _verify_frozen_evidence_digests(repository_root)
    gates = frozen_structural_gates(repository_root)
    successor = successor_protocol_definition(repository_root)
    metrics = [item.as_record(gates[item.metric]) for item in STRUCTURAL_METRIC_RESOLUTIONS]
    if {item["metric"] for item in metrics} != set(AFFECTED_V2_GATE_METRICS):
        raise DenominatorResolutionError(
            "resolution does not cover exactly the six affected V2 gates"
        )
    record = {
        "schema_version": RESOLUTION_SCHEMA_VERSION,
        "resolution_version": RESOLUTION_VERSION,
        "denominator_semantics_version": DENOMINATOR_SEMANTICS_VERSION,
        "task": "STRUCTURAL_GATE_DENOMINATOR_RESOLUTION",
        "research_only": True,
        "btc019_status": "IN PROGRESS",
        "production_canonical_reference": "UNRESOLVED",
        "production_strategy_semantics_changed": False,
        "parent_protocol_version": PARENT_PROTOCOL_VERSION,
        "parent_definition_sha256": PARENT_DEFINITION_SHA256,
        "parent_definition_unchanged": True,
        "comparison_contract_version": COMPARISON_CONTRACT_VERSION,
        "source_detector_version": WEEKLY_STRUCTURE_DETECTOR_VERSION,
        "affected_metrics": list(AFFECTED_V2_GATE_METRICS),
        "frozen_gates_read": [gates[metric] for metric in AFFECTED_V2_GATE_METRICS],
        "frozen_thresholds_changed": False,
        "frozen_gate_directions_changed": False,
        "denominator_interpretations_considered": [
            dict(item) for item in DENOMINATOR_INTERPRETATIONS
        ],
        "examined_evidence": [
            item.as_record(repository_root) for item in EXAMINED_EVIDENCE
        ],
        "rejected_as_post_hoc": [dict(item) for item in REJECTED_AS_POST_HOC],
        "threshold_intent_anchor": btc019b_threshold_anchor(repository_root),
        "denominator_materiality": denominator_materiality(repository_root),
        "metric_resolutions": metrics,
        "coverage_contract": COVERAGE_CONTRACT,
        "classification_rule": CLASSIFICATION_RULE,
        "classification": _classify(metrics),
        "successor_protocol_version": SUCCESSOR_PROTOCOL_VERSION,
        "successor_definition_sha256": successor["definition_sha256"],
        "successor_status": SUCCESSOR_STATUS,
        "outcome_driven_reasoning": {
            "already_inspected_outcomes_influenced_denominator_choice": False,
            "same_decision_if_verdicts_reversed": True,
            "why": (
                "Every load-bearing finding is a fact about the frozen text "
                "and the code that predates the defect: the definition names "
                "no denominator, the only recoverable one is the known defect, "
                "two pre-existing formulas disagree, and breakout and reclaim "
                "have no calibration artifact at all. None of those was read "
                "off a verdict, and the adopted denominator is not the "
                "favourable one."
            ),
        },
        "sealed_sample": {
            "start": UNTOUCHED_OOS_START.isoformat(),
            "end": UNTOUCHED_OOS_END.isoformat(),
            "opened": False,
            "collected": False,
            "statistics_derived": False,
        },
        "next_steps": [
            "Pre-sealed threshold calibration and governance for the six "
            f"{SUCCESSOR_PROTOCOL_VERSION} structural metrics, using the "
            "already-inspected samples only.",
            "Then freeze the successor definition and build the sealed "
            "validator bound to the frozen successor hash.",
            "Then collect 2015-2019, and only then open the sealed sample once.",
        ],
        "may_build_sealed_validator": False,
        "may_collect_sealed_sample": False,
        "may_open_sealed_sample": False,
    }
    return {**record, "artifact_digest": _digest(record)}


def _classify(metrics: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Read the outcome off the per-metric conclusions, not off the verdicts."""

    not_recoverable_denominator = [
        item["metric"]
        for item in metrics
        if item["denominator_intent"] == DENOMINATOR_INTENT_NOT_RECOVERABLE
    ]
    defective_denominator = [
        item["metric"]
        for item in metrics
        if item["denominator_intent"] == DENOMINATOR_INTENT_RECOVERABLE_BUT_DEFECTIVE
    ]
    not_portable = [
        item["metric"]
        for item in metrics
        if item["threshold_semantics"] == THRESHOLD_SEMANTICS_NOT_RECOVERABLE
    ]
    if not_recoverable_denominator or defective_denominator or not_portable:
        outcome = NEW_PROTOCOL_VERSION_REQUIRED
    else:
        outcome = CLARIFICATION_VALID
    reason_codes = sorted(
        {code for item in metrics for code in item["reason_codes"]}
        | {SUCCESSOR_REQUIRED_BY_PARENT_GOVERNANCE}
    )
    return {
        "outcome": outcome,
        "reason_codes": reason_codes,
        "metrics_with_unrecoverable_denominator": not_recoverable_denominator,
        "metrics_with_recoverable_but_defective_denominator": defective_denominator,
        "metrics_with_unportable_threshold": not_portable,
    }


# --- persistence --------------------------------------------------------------


def write_resolution_artifacts(
    repository_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Persist the record and the proposed successor as deterministic ASCII JSON."""

    record = build_resolution_record(repository_root)
    successor = successor_protocol_definition(repository_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / RESOLUTION_RECORD_FILENAME).write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="ascii",
    )
    (output_dir / SUCCESSOR_DEFINITION_FILENAME).write_text(
        json.dumps(successor, indent=2, sort_keys=True) + "\n",
        encoding="ascii",
    )
    return record


def restore_resolution_record(output_dir: Path) -> dict[str, Any]:
    """Read a persisted record back, refusing anything it cannot vouch for."""

    record = json.loads((output_dir / RESOLUTION_RECORD_FILENAME).read_text())
    if record.get("schema_version") != RESOLUTION_SCHEMA_VERSION:
        raise DenominatorResolutionError(
            f"persisted record does not carry {RESOLUTION_SCHEMA_VERSION}"
        )
    if (
        record.get("denominator_semantics_version")
        not in SUPPORTED_DENOMINATOR_SEMANTICS_VERSIONS
    ):
        raise DenominatorResolutionError(
            "persisted record names an unknown denominator-semantics version"
        )
    if record.get("parent_definition_sha256") != PARENT_DEFINITION_SHA256:
        raise DenominatorResolutionError(
            "persisted record names a different parent protocol hash"
        )
    if record.get("comparison_contract_version") != COMPARISON_CONTRACT_VERSION:
        raise DenominatorResolutionError(
            "persisted record names a different comparison contract"
        )
    resolutions = record.get("metric_resolutions")
    if not isinstance(resolutions, list) or {
        item.get("metric") for item in resolutions
    } != set(AFFECTED_V2_GATE_METRICS):
        raise DenominatorResolutionError(
            "persisted record does not resolve exactly the six affected gates"
        )
    for item in resolutions:
        for field in ("numerator", "denominator", "denominator_id"):
            if not item.get(field):
                raise DenominatorResolutionError(
                    f"{item.get('metric')!r} has no {field} in the persisted record"
                )
        if item.get("not_comparable_treatment") not in NOT_COMPARABLE_TREATMENTS:
            raise DenominatorResolutionError(
                f"{item.get('metric')!r} has no explicit NOT_COMPARABLE treatment"
            )
    digest = record.get("artifact_digest")
    body = {key: value for key, value in record.items() if key != "artifact_digest"}
    if digest != _digest(body):
        raise DenominatorResolutionError("persisted resolution record was tampered with")
    return record


def restore_successor_definition(output_dir: Path) -> dict[str, Any]:
    """Read the proposed successor back, refusing a wrong parent or a tamper."""

    definition = json.loads((output_dir / SUCCESSOR_DEFINITION_FILENAME).read_text())
    if definition.get("schema_version") != SUCCESSOR_SCHEMA_VERSION:
        raise DenominatorResolutionError(
            f"persisted successor does not carry {SUCCESSOR_SCHEMA_VERSION}"
        )
    if definition.get("parent_definition_sha256") != PARENT_DEFINITION_SHA256:
        raise DenominatorResolutionError(
            "persisted successor names a different parent protocol hash"
        )
    if (
        definition.get("denominator_semantics_version")
        not in SUPPORTED_DENOMINATOR_SEMANTICS_VERSIONS
    ):
        raise DenominatorResolutionError(
            "persisted successor names an unknown denominator-semantics version"
        )
    digest = definition.get("definition_sha256")
    body = {
        key: value for key, value in definition.items() if key != "definition_sha256"
    }
    if digest != _digest(body):
        raise DenominatorResolutionError("persisted successor definition was tampered with")
    return definition


def verify_resolution_artifacts(
    repository_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Recompute both artifacts and refuse a persisted copy that disagrees."""

    persisted = restore_resolution_record(output_dir)
    if persisted != build_resolution_record(repository_root):
        raise DenominatorResolutionError(
            "persisted resolution record does not recompute from the repository"
        )
    successor = restore_successor_definition(output_dir)
    if successor != successor_protocol_definition(repository_root):
        raise DenominatorResolutionError(
            "persisted successor definition does not recompute from the repository"
        )
    if persisted["successor_definition_sha256"] != successor["definition_sha256"]:
        raise DenominatorResolutionError(
            "resolution record and successor definition are not bound together"
        )
    return persisted


def guard_sealed_sample(*, start: Any, end: Any, purpose: str) -> None:
    """Delegate to the inherited sealed-sample guard; this task opens nothing."""

    guard_untouched_validation_sample(start=start, end=end, purpose=purpose)
