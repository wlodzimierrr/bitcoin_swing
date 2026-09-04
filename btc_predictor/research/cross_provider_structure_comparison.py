"""Calendar-contiguity-aware cross-provider structural comparison.

`CROSS_PROVIDER_STRUCTURE_COMPARISON_V2` answers one question the BTC-019
structural evidence cannot answer today:

    when two provider series disagree about a weekly swing, breakout or
    reclaim, is that a disagreement about BTC market structure, or only the
    fact that one provider did not publish the observation the detector needs
    to decide it?

`build_canonical_market_bars` emits complete buckets only, so an hourly outage
removes a whole weekly session and the surviving series is legitimately
non-contiguous. `detect_weekly_swing_levels` takes its confirmation window by
row -- ``available_bars[index - 3 : index + 4]`` -- so on such a series the
weeks either side of an absent one are read as neighbours. The V1 comparison
counted the resulting difference as venue disagreement.

This module changes no production semantics. It runs the same production
detectors and adds a versioned research adapter in front of the comparison:

    production weekly swing / breakout-reclaim detectors
        -> per-series weekly session calendar
        -> per-candidate calendar-comparability contract
        -> pairwise cross-provider disagreement metrics

The contract rests on one fact about the production detector. When every
calendar week of a candidate's confirmation window ``T-3 .. T+3`` is present in
a series, those weeks occupy seven consecutive rows, so the row window and the
calendar window are the same window and the detector's verdict at ``T`` is the
calendar-correct verdict. When any of them is absent the row window spans a
different calendar and the verdict is not a verdict about ``T`` at all. Only
the first case is comparable.

Nothing here approves a provider or a composite, opens the sealed
`BTC_REFERENCE_COMPOSITE_V2` validation sample, or moves a frozen threshold,
gate or artifact. The V1 comparison stays exactly as it is and keeps producing
the frozen evidence; this is a second, explicitly versioned measurement that
coexists with it.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Context, Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any

from btc_predictor.data import (
    OhlcvBar,
    build_canonical_market_bars,
    next_bar_timestamp,
    require_utc_datetime,
)
from btc_predictor.levels import (
    BREAKOUT_LEVEL_TYPE,
    DEFAULT_WEEKLY_SWING_LEFT_BARS,
    DEFAULT_WEEKLY_SWING_RIGHT_BARS,
    RECLAIM_LEVEL_TYPE,
    WEEKLY_SWING_HIGH,
    WEEKLY_SWING_LOW,
    detect_breakout_reclaim_levels,
    detect_weekly_swing_levels,
)
from btc_predictor.research.btc019_completion_gate import (
    INSPECTED_SAMPLE_DIRS,
    load_inspected_sample,
    sample_evaluation_time,
    structural_differences,
)
from btc_predictor.research.price_source_policy import (
    BITSTAMP_PROVIDER_ID,
    PRICE_SOURCE_POLICY_VERSION,
)
from btc_predictor.research.reference_composite_v2 import (
    UNTOUCHED_OOS_END,
    UNTOUCHED_OOS_START,
    guard_untouched_validation_sample,
)


COMPARISON_CONTRACT_VERSION = "CROSS_PROVIDER_STRUCTURE_COMPARISON_V2"
LEGACY_COMPARISON_CONTRACT_VERSION = "CROSS_PROVIDER_STRUCTURE_COMPARISON_V1"
COMPARISON_REPORT_SCHEMA_VERSION = "CROSS_PROVIDER_STRUCTURE_COMPARISON_V2_REPORT_V1"

# The production detectors this contract adapts. An evaluation bound to any
# other detector identity has no proven row/calendar equivalence and is
# refused rather than measured.
WEEKLY_STRUCTURE_DETECTOR_VERSION = "BTC_PREDICTOR_WEEKLY_LEVELS_V1"
SUPPORTED_DETECTOR_VERSIONS = (WEEKLY_STRUCTURE_DETECTOR_VERSION,)

WEEKLY_TIMEFRAME = "1w"
WEEKLY_SESSION_STEP = timedelta(weeks=1)

# Pairwise, on the calendar the two compared series have in common. A
# multi-provider consensus quorum is deliberately not computed here: the
# research question is whether a two-series difference is real, and a quorum
# would need its own declared calendar basis before it could mean anything.
PAIRWISE_COMPARISON_BASIS = "PAIRWISE_COMMON_WEEKLY_CALENDAR"

SWING_HIGH_FAMILY = WEEKLY_SWING_HIGH
SWING_LOW_FAMILY = WEEKLY_SWING_LOW
BREAKOUT_FAMILY = BREAKOUT_LEVEL_TYPE
RECLAIM_FAMILY = RECLAIM_LEVEL_TYPE
SWING_FAMILIES = (SWING_HIGH_FAMILY, SWING_LOW_FAMILY)
DERIVED_FAMILIES = (BREAKOUT_FAMILY, RECLAIM_FAMILY)
EVENT_FAMILIES = SWING_FAMILIES + DERIVED_FAMILIES
DERIVED_FAMILY_BY_SWING = {
    SWING_HIGH_FAMILY: BREAKOUT_FAMILY,
    SWING_LOW_FAMILY: RECLAIM_FAMILY,
}

SESSION_PRESENT = "PRESENT"
SESSION_ABSENT = "ABSENT"
SESSION_PENDING = "PENDING"
SESSION_OUT_OF_COVERAGE = "OUT_OF_COVERAGE"
SESSION_STATUSES = (
    SESSION_PRESENT,
    SESSION_ABSENT,
    SESSION_PENDING,
    SESSION_OUT_OF_COVERAGE,
)

COMPARABLE = "COMPARABLE"
NOT_COMPARABLE_AVAILABILITY_GAP = "NOT_COMPARABLE_AVAILABILITY_GAP"
NOT_COMPARABLE_CONFIRMATION_PENDING = "NOT_COMPARABLE_CONFIRMATION_PENDING"
NOT_COMPARABLE_SERIES_COVERAGE = "NOT_COMPARABLE_SERIES_COVERAGE"
NOT_COMPARABLE_SOURCE_LEVEL = "NOT_COMPARABLE_SOURCE_LEVEL"
COMPARABILITY_STATES = (
    COMPARABLE,
    NOT_COMPARABLE_AVAILABILITY_GAP,
    NOT_COMPARABLE_CONFIRMATION_PENDING,
    NOT_COMPARABLE_SERIES_COVERAGE,
    NOT_COMPARABLE_SOURCE_LEVEL,
)

STRUCTURAL_AGREEMENT = "STRUCTURAL_AGREEMENT"
STRUCTURAL_DISAGREEMENT = "STRUCTURAL_DISAGREEMENT"
NOT_COMPARABLE = "NOT_COMPARABLE"
COMPARISON_OUTCOMES = (
    STRUCTURAL_AGREEMENT,
    STRUCTURAL_DISAGREEMENT,
    NOT_COMPARABLE,
)

BOTH_SERIES_DETECT_EVENT = "BOTH_SERIES_DETECT_EVENT"
NEITHER_SERIES_DETECTS_EVENT = "NEITHER_SERIES_DETECTS_EVENT"
SINGLE_SERIES_DETECTS_EVENT = "SINGLE_SERIES_DETECTS_EVENT"
CONFIRMATION_SESSION_AGREES = "CONFIRMATION_SESSION_AGREES"
CONFIRMATION_SESSION_DIFFERS = "CONFIRMATION_SESSION_DIFFERS"
CONFIRMATION_ABSENT_IN_BOTH_SERIES = "CONFIRMATION_ABSENT_IN_BOTH_SERIES"
CONFIRMATION_PRESENT_IN_ONE_SERIES_ONLY = "CONFIRMATION_PRESENT_IN_ONE_SERIES_ONLY"
REQUIRED_SESSION_ABSENT_IN_ONE_SERIES = "REQUIRED_SESSION_ABSENT_IN_ONE_SERIES"
REQUIRED_SESSION_ABSENT_IN_BOTH_SERIES = "REQUIRED_SESSION_ABSENT_IN_BOTH_SERIES"
CONFIRMATION_WINDOW_NOT_YET_AVAILABLE = "CONFIRMATION_WINDOW_NOT_YET_AVAILABLE"
REQUIRED_SESSION_OUTSIDE_SERIES_COVERAGE = "REQUIRED_SESSION_OUTSIDE_SERIES_COVERAGE"
SOURCE_LEVEL_NOT_COMPARABLE = "SOURCE_LEVEL_NOT_COMPARABLE"
SOURCE_LEVEL_NOT_SHARED = "SOURCE_LEVEL_NOT_SHARED"

COMPARISON_REASON_CODES = (
    BOTH_SERIES_DETECT_EVENT,
    NEITHER_SERIES_DETECTS_EVENT,
    SINGLE_SERIES_DETECTS_EVENT,
    CONFIRMATION_SESSION_AGREES,
    CONFIRMATION_SESSION_DIFFERS,
    CONFIRMATION_ABSENT_IN_BOTH_SERIES,
    CONFIRMATION_PRESENT_IN_ONE_SERIES_ONLY,
    REQUIRED_SESSION_ABSENT_IN_ONE_SERIES,
    REQUIRED_SESSION_ABSENT_IN_BOTH_SERIES,
    CONFIRMATION_WINDOW_NOT_YET_AVAILABLE,
    REQUIRED_SESSION_OUTSIDE_SERIES_COVERAGE,
    SOURCE_LEVEL_NOT_COMPARABLE,
    SOURCE_LEVEL_NOT_SHARED,
)

BOTH_SERIES = "both"

# Denominator semantics are named, never implied.
COMPARABLE_EVENT_DENOMINATOR = "comparable_detected_event_union"
ALL_EVENT_DENOMINATOR = "all_detected_event_union"
COMPARABLE_CANDIDATE_DENOMINATOR = "comparable_candidate_sessions"

# The six frozen BTC_REFERENCE_COMPOSITE_V2 approval-gate metrics computed from
# cross-provider weekly structural comparison. Their thresholds are read from
# the frozen protocol definition and are never written by this module.
AFFECTED_V2_GATE_METRICS = (
    "exact_timestamp_swing_disagreement_rate",
    "within_1_week_swing_disagreement_rate",
    "within_2_week_swing_disagreement_rate",
    "structural_state_disagreement_rate",
    "breakout_disagreement_rate",
    "reclaim_disagreement_rate",
)

GATE_DEFINED_AND_UNCONTAMINATED = "DEFINED_AND_UNCONTAMINATED"
GATE_DEFINED_WITH_EXCLUSIONS = "DEFINED_WITH_EXCLUSIONS"
GATE_UNDEFINED_NO_COMPARABLE_EVENTS = "UNDEFINED_NO_COMPARABLE_EVENTS"

READY_TO_BUILD_SEALED_VALIDATOR = "READY_TO_BUILD_SEALED_VALIDATOR"
NOT_READY_STRUCTURAL_GATES_STILL_INVALID = "NOT_READY_STRUCTURAL_GATES_STILL_INVALID"
RESEARCH_INCONCLUSIVE = "RESEARCH_INCONCLUSIVE"
BLOCKED_BY_NEW_CORRECTNESS_DEFECT = "BLOCKED_BY_NEW_CORRECTNESS_DEFECT"
COMPARISON_CLASSIFICATIONS = (
    READY_TO_BUILD_SEALED_VALIDATOR,
    NOT_READY_STRUCTURAL_GATES_STILL_INVALID,
    RESEARCH_INCONCLUSIVE,
    BLOCKED_BY_NEW_CORRECTNESS_DEFECT,
)

# A not-comparable derived candidate can require a calendar hundreds of
# weeks long. Only the first missing sessions of each are listed inline;
# the full calendar is reconstructable from the recorded bounds.
_MAX_REPORTED_SESSIONS = 32

# Rates are resolved in an explicit context so a caller's ambient Decimal
# settings can never decide a persisted research conclusion.
_RATE_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)


class CrossProviderComparisonError(ValueError):
    """Malformed input, tampered evidence, or an unknown detector version."""


@dataclass(frozen=True)
class WeeklySessionCalendar:
    """Which weekly calendar sessions one series can and cannot speak for."""

    series_id: str
    provider: str
    exchange: str
    symbol: str
    timeframe: str
    evaluation_time: datetime
    first_session: datetime
    last_session: datetime
    present_sessions: tuple[datetime, ...]
    absent_sessions: tuple[datetime, ...]

    def session_status(self, session: datetime) -> str:
        """Classify one weekly session for this series at its evaluation time."""

        week = require_weekly_session(session, "session")
        if week in self._present:
            return SESSION_PRESENT
        if self.first_session <= week <= self.last_session:
            return SESSION_ABSENT
        if next_bar_timestamp(week, WEEKLY_TIMEFRAME) > self.evaluation_time:
            return SESSION_PENDING
        return SESSION_OUT_OF_COVERAGE

    @property
    def _present(self) -> frozenset[datetime]:
        return frozenset(self.present_sessions)

    def as_record(self) -> dict[str, Any]:
        return {
            "series_id": self.series_id,
            "provider": self.provider,
            "exchange": self.exchange,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "evaluation_time": self.evaluation_time.isoformat(),
            "first_session": self.first_session.isoformat(),
            "last_session": self.last_session.isoformat(),
            "present_session_count": len(self.present_sessions),
            "absent_session_count": len(self.absent_sessions),
            "absent_sessions": [item.isoformat() for item in self.absent_sessions],
        }


@dataclass(frozen=True)
class WeeklyStructureSnapshot:
    """One series' production structural output plus its session calendar."""

    calendar: WeeklySessionCalendar
    detector_version: str
    left_sessions: int
    right_sessions: int
    swings: Mapping[tuple[str, datetime], Decimal]
    confirmations: Mapping[tuple[str, datetime], datetime]

    @property
    def series_id(self) -> str:
        return self.calendar.series_id

    def detects_swing(self, family: str, session: datetime) -> bool:
        return (family, session) in self.swings

    def confirmation_for(self, family: str, session: datetime) -> datetime | None:
        return self.confirmations.get((DERIVED_FAMILY_BY_SWING[family], session))

    def as_record(self) -> dict[str, Any]:
        return {
            **self.calendar.as_record(),
            "detector_version": self.detector_version,
            "confirmation_window": {
                "left_sessions": self.left_sessions,
                "right_sessions": self.right_sessions,
                "timeframe": WEEKLY_TIMEFRAME,
            },
            "detected_swing_counts": {
                family: sum(1 for key in self.swings if key[0] == family)
                for family in SWING_FAMILIES
            },
            "detected_confirmation_counts": {
                family: sum(1 for key in self.confirmations if key[0] == family)
                for family in DERIVED_FAMILIES
            },
        }


@dataclass(frozen=True)
class StructuralComparisonEvent:
    """One candidate structural comparison between two named series."""

    comparison_id: str
    series_ids: tuple[str, str]
    event_family: str
    candidate_session: datetime
    required_sessions: tuple[datetime, ...]
    session_status: Mapping[str, Mapping[datetime, str]]
    missing_required_sessions: Mapping[str, tuple[datetime, ...]]
    availability_gap_side: str | None
    comparability: str
    outcome: str
    detected_in: tuple[str, ...]
    confirmation_sessions: Mapping[str, datetime | None]
    reason_codes: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "comparison_id": self.comparison_id,
            "series_ids": list(self.series_ids),
            "event_family": self.event_family,
            "candidate_session": self.candidate_session.isoformat(),
            # The required calendar is always one contiguous weekly range, so
            # its bounds and length reconstruct it exactly.
            "required_sessions": {
                "first": (
                    None
                    if not self.required_sessions
                    else self.required_sessions[0].isoformat()
                ),
                "last": (
                    None
                    if not self.required_sessions
                    else self.required_sessions[-1].isoformat()
                ),
                "count": len(self.required_sessions),
            },
            # Every required session not listed here is PRESENT in that series.
            "non_present_required_sessions": {
                series_id: [
                    {"session": session.isoformat(), "status": statuses[session]}
                    for session in sorted(statuses)
                    if statuses[session] != SESSION_PRESENT
                ]
                for series_id, statuses in sorted(self.session_status.items())
            },
            "missing_required_session_counts": {
                series_id: len(sessions)
                for series_id, sessions in sorted(self.missing_required_sessions.items())
            },
            "availability_gap_side": self.availability_gap_side,
            "comparability": self.comparability,
            "outcome": self.outcome,
            "source_detector_result": {
                "detected_in": list(self.detected_in),
                "confirmation_sessions": {
                    series_id: None if session is None else session.isoformat()
                    for series_id, session in sorted(self.confirmation_sessions.items())
                },
            },
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class PairwiseStructureComparison:
    """Every candidate comparison between one ordered-independent series pair."""

    comparison_id: str
    series_ids: tuple[str, str]
    series_identities: Mapping[str, Mapping[str, str]]
    detector_version: str
    analysis_start: datetime
    analysis_end: datetime
    candidate_sessions: tuple[datetime, ...]
    events: tuple[StructuralComparisonEvent, ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "comparison_id": self.comparison_id,
            "comparison_contract_version": COMPARISON_CONTRACT_VERSION,
            "series_ids": list(self.series_ids),
            "series_identities": {
                series_id: dict(sorted(identity.items()))
                for series_id, identity in sorted(self.series_identities.items())
            },
            "source_detector_version": self.detector_version,
            "comparison_basis": PAIRWISE_COMPARISON_BASIS,
            "analysis_start": self.analysis_start.isoformat(),
            "analysis_end": self.analysis_end.isoformat(),
            "candidate_session_count": len(self.candidate_sessions),
            "metrics": pairwise_metrics(self),
            "reported_events": [
                event.as_record()
                for event in self.events
                if event.detected_in or event.confirmation_sessions
            ],
        }


def require_weekly_session(value: datetime, field_name: str) -> datetime:
    """Return one unambiguous UTC weekly session start, or refuse the input."""

    session = require_utc_datetime(value, field_name)
    if (session.hour, session.minute, session.second, session.microsecond) != (0, 0, 0, 0):
        raise CrossProviderComparisonError(
            f"{field_name} must be a canonical weekly session start at 00:00 UTC; "
            f"received {session.isoformat()}"
        )
    if session.weekday() != 0:
        raise CrossProviderComparisonError(
            f"{field_name} must be a Monday weekly session start; "
            f"received {session.isoformat()}"
        )
    return session


def weekly_sessions_between(start: datetime, end: datetime) -> tuple[datetime, ...]:
    """Return every weekly session start from ``start`` through ``end``."""

    first = require_weekly_session(start, "start")
    last = require_weekly_session(end, "end")
    if last < first:
        raise CrossProviderComparisonError("end must be >= start")
    sessions = []
    current = first
    while current <= last:
        sessions.append(current)
        current = next_bar_timestamp(current, WEEKLY_TIMEFRAME)
    return tuple(sessions)


def build_weekly_session_calendar(
    bars: Sequence[OhlcvBar],
    *,
    series_id: str,
    evaluation_time: datetime,
) -> WeeklySessionCalendar:
    """Validate one weekly series and record the calendar it can speak for.

    A series that is not one identified provider's strictly increasing sequence
    of canonical weekly sessions has no calendar reading at all, so it is
    refused rather than measured.

    Only sessions the series can actually speak for at ``evaluation_time`` --
    closed and ingested by then -- become present ones, matching what the
    production detector reads. A bar that has not arrived yet is not evidence
    that a week exists, so appending later history cannot change a comparison
    already made.
    """

    if not series_id:
        raise CrossProviderComparisonError("series_id must be a non-empty identifier")
    as_of = require_utc_datetime(evaluation_time, "evaluation_time")
    ordered = tuple(bars)
    if not ordered:
        raise CrossProviderComparisonError(f"series {series_id!r} holds no weekly bars")

    identities = set()
    previous: datetime | None = None
    present = []
    for bar in ordered:
        if bar.timeframe != WEEKLY_TIMEFRAME:
            raise CrossProviderComparisonError(
                f"series {series_id!r} requires canonical {WEEKLY_TIMEFRAME} bars; "
                f"received {bar.timeframe!r}"
            )
        if not bar.provider or not bar.exchange or not bar.symbol:
            raise CrossProviderComparisonError(
                f"series {series_id!r} has a bar without a complete provider identity"
            )
        session = require_weekly_session(bar.timestamp, "bar timestamp")
        require_utc_datetime(bar.ingested_at, "ingested_at")
        if previous is not None:
            if session == previous:
                raise CrossProviderComparisonError(
                    f"series {series_id!r} repeats weekly session {session.isoformat()}"
                )
            if session < previous:
                raise CrossProviderComparisonError(
                    f"series {series_id!r} is out of order at {session.isoformat()}"
                )
        identities.add((bar.provider, bar.exchange, bar.symbol, bar.timeframe))
        if (
            next_bar_timestamp(session, WEEKLY_TIMEFRAME) <= as_of
            and bar.ingested_at <= as_of
        ):
            present.append(session)
        previous = session
    if len(identities) != 1:
        raise CrossProviderComparisonError(
            f"series {series_id!r} mixes provider/exchange/symbol identities"
        )
    provider, exchange, symbol, timeframe = identities.pop()
    if not present:
        raise CrossProviderComparisonError(
            f"series {series_id!r} holds no weekly session available at "
            f"{as_of.isoformat()}"
        )

    first_session = present[0]
    last_session = present[-1]
    present_set = set(present)
    absent = tuple(
        session
        for session in weekly_sessions_between(first_session, last_session)
        if session not in present_set
    )
    return WeeklySessionCalendar(
        series_id=series_id,
        provider=provider,
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        evaluation_time=as_of,
        first_session=first_session,
        last_session=last_session,
        present_sessions=tuple(present),
        absent_sessions=absent,
    )


def weekly_structure_snapshot(
    bars: Sequence[OhlcvBar],
    *,
    series_id: str,
    evaluation_time: datetime,
    detector_version: str = WEEKLY_STRUCTURE_DETECTOR_VERSION,
    left_sessions: int = DEFAULT_WEEKLY_SWING_LEFT_BARS,
    right_sessions: int = DEFAULT_WEEKLY_SWING_RIGHT_BARS,
) -> WeeklyStructureSnapshot:
    """Run the production detectors on one series and pin its calendar."""

    if detector_version not in SUPPORTED_DETECTOR_VERSIONS:
        raise CrossProviderComparisonError(
            f"unknown structural detector version {detector_version!r}; "
            f"expected one of {SUPPORTED_DETECTOR_VERSIONS}"
        )
    calendar = build_weekly_session_calendar(
        bars,
        series_id=series_id,
        evaluation_time=evaluation_time,
    )
    ordered = tuple(bars)
    levels = detect_weekly_swing_levels(
        ordered,
        as_of=calendar.evaluation_time,
        left_bars=left_sessions,
        right_bars=right_sessions,
    )
    confirmations = detect_breakout_reclaim_levels(
        levels,
        ordered,
        as_of=calendar.evaluation_time,
    )
    return WeeklyStructureSnapshot(
        calendar=calendar,
        detector_version=detector_version,
        left_sessions=left_sessions,
        right_sessions=right_sessions,
        swings={
            (level.level_type, level.level_timestamp): level.price for level in levels
        },
        confirmations={
            (level.level_type, level.source_level_timestamp): level.confirmation_timestamp
            for level in confirmations
        },
    )


def compare_weekly_structure(
    snapshots: Mapping[str, WeeklyStructureSnapshot],
    *,
    series_pair: Sequence[str],
) -> PairwiseStructureComparison:
    """Compare two series on the weekly calendar they have in common."""

    left_id, right_id = _canonical_pair(series_pair)
    left = snapshots[left_id]
    right = snapshots[right_id]
    if left.detector_version != right.detector_version:
        raise CrossProviderComparisonError(
            "a pairwise comparison requires one structural detector version"
        )
    if (left.left_sessions, left.right_sessions) != (
        right.left_sessions,
        right.right_sessions,
    ):
        raise CrossProviderComparisonError(
            "a pairwise comparison requires one confirmation-window contract"
        )
    if left.calendar.evaluation_time != right.calendar.evaluation_time:
        raise CrossProviderComparisonError(
            "a pairwise comparison requires one evaluation time"
        )
    # Instrument symbols are deliberately not required to match. The V1 policy
    # fixes a different venue symbol per provider for the same BTC/USD
    # instrument -- Coinbase publishes `BTC-USD`, Bitstamp and Bitfinex
    # `BTC/USD` -- so both identities are persisted instead of equated.

    analysis_start = max(left.calendar.first_session, right.calendar.first_session)
    analysis_end = min(left.calendar.last_session, right.calendar.last_session)
    if analysis_end < analysis_start:
        raise CrossProviderComparisonError(
            f"series {left_id!r} and {right_id!r} share no weekly calendar"
        )
    candidates = weekly_sessions_between(analysis_start, analysis_end)
    comparison_id = f"{left_id}_vs_{right_id}"

    events: list[StructuralComparisonEvent] = []
    swing_comparability: dict[tuple[str, datetime], str] = {}
    for family in SWING_FAMILIES:
        for session in candidates:
            event = _compare_swing_candidate(
                left,
                right,
                comparison_id=comparison_id,
                family=family,
                session=session,
            )
            swing_comparability[(family, session)] = event.comparability
            events.append(event)
    for family in SWING_FAMILIES:
        for session in candidates:
            if not (left.detects_swing(family, session) or right.detects_swing(family, session)):
                continue
            events.append(
                _compare_derived_candidate(
                    left,
                    right,
                    comparison_id=comparison_id,
                    swing_family=family,
                    session=session,
                    swing_comparability=swing_comparability[(family, session)],
                    analysis_end=analysis_end,
                )
            )
    return PairwiseStructureComparison(
        comparison_id=comparison_id,
        series_ids=(left_id, right_id),
        series_identities={
            snapshot.series_id: {
                "provider": snapshot.calendar.provider,
                "exchange": snapshot.calendar.exchange,
                "symbol": snapshot.calendar.symbol,
                "timeframe": snapshot.calendar.timeframe,
            }
            for snapshot in (left, right)
        },
        detector_version=left.detector_version,
        analysis_start=analysis_start,
        analysis_end=analysis_end,
        candidate_sessions=candidates,
        events=tuple(
            sorted(
                events,
                key=lambda item: (
                    EVENT_FAMILIES.index(item.event_family),
                    item.candidate_session,
                ),
            )
        ),
    )


def _compare_swing_candidate(
    left: WeeklyStructureSnapshot,
    right: WeeklyStructureSnapshot,
    *,
    comparison_id: str,
    family: str,
    session: datetime,
) -> StructuralComparisonEvent:
    required = _confirmation_calendar(
        session,
        left_sessions=left.left_sessions,
        right_sessions=left.right_sessions,
    )
    statuses, missing, comparability, gap_side, reasons = _comparability(
        left,
        right,
        required=required,
    )
    detected = tuple(
        snapshot.series_id
        for snapshot in (left, right)
        if snapshot.detects_swing(family, session)
    )
    if comparability == COMPARABLE:
        if len(detected) == 2:
            outcome = STRUCTURAL_AGREEMENT
            reasons = (*reasons, BOTH_SERIES_DETECT_EVENT)
        elif not detected:
            outcome = STRUCTURAL_AGREEMENT
            reasons = (*reasons, NEITHER_SERIES_DETECTS_EVENT)
        else:
            outcome = STRUCTURAL_DISAGREEMENT
            reasons = (*reasons, SINGLE_SERIES_DETECTS_EVENT)
    else:
        outcome = NOT_COMPARABLE
    return StructuralComparisonEvent(
        comparison_id=comparison_id,
        series_ids=(left.series_id, right.series_id),
        event_family=family,
        candidate_session=session,
        required_sessions=required,
        session_status=statuses,
        missing_required_sessions=missing,
        availability_gap_side=gap_side,
        comparability=comparability,
        outcome=outcome,
        detected_in=detected,
        confirmation_sessions={},
        reason_codes=reasons,
    )


def _compare_derived_candidate(
    left: WeeklyStructureSnapshot,
    right: WeeklyStructureSnapshot,
    *,
    comparison_id: str,
    swing_family: str,
    session: datetime,
    swing_comparability: str,
    analysis_end: datetime,
) -> StructuralComparisonEvent:
    """Compare the breakout/reclaim derived from one weekly swing candidate.

    A confirmation is the first later weekly close that clears the level, so
    every weekly session between the source level and the confirmation decides
    it. The joint requirement is therefore that both series hold the whole
    calendar out to the later of the two confirmations -- and out to the end of
    the shared span when either series never confirms, because "never" is a
    statement about every remaining week.
    """

    family = DERIVED_FAMILY_BY_SWING[swing_family]
    detected = tuple(
        snapshot.series_id
        for snapshot in (left, right)
        if snapshot.detects_swing(swing_family, session)
    )
    confirmations = {
        snapshot.series_id: snapshot.confirmation_for(swing_family, session)
        for snapshot in (left, right)
    }
    if swing_comparability != COMPARABLE or len(detected) != 2:
        reason = (
            SOURCE_LEVEL_NOT_COMPARABLE
            if swing_comparability != COMPARABLE
            else SOURCE_LEVEL_NOT_SHARED
        )
        return StructuralComparisonEvent(
            comparison_id=comparison_id,
            series_ids=(left.series_id, right.series_id),
            event_family=family,
            candidate_session=session,
            required_sessions=(),
            session_status={},
            missing_required_sessions={},
            availability_gap_side=None,
            comparability=NOT_COMPARABLE_SOURCE_LEVEL,
            outcome=NOT_COMPARABLE,
            detected_in=tuple(
                series_id
                for series_id, value in sorted(confirmations.items())
                if value is not None
            ),
            confirmation_sessions=confirmations,
            reason_codes=(reason,),
        )

    observed = [value for value in confirmations.values() if value is not None]
    horizon = max(observed) if len(observed) == 2 else max([analysis_end, *observed])
    first_required = next_bar_timestamp(session, WEEKLY_TIMEFRAME)
    # A source level on the last shared week has no shared confirmation
    # calendar at all. Requiring the first week after it keeps that visible as
    # an explicit availability/coverage reason instead of a silent pass.
    required = weekly_sessions_between(
        first_required,
        max(horizon, first_required),
    )
    statuses, missing, comparability, gap_side, reasons = _comparability(
        left,
        right,
        required=required,
    )
    if comparability == COMPARABLE:
        left_confirmation = confirmations[left.series_id]
        right_confirmation = confirmations[right.series_id]
        if left_confirmation == right_confirmation:
            outcome = STRUCTURAL_AGREEMENT
            reasons = (
                *reasons,
                CONFIRMATION_ABSENT_IN_BOTH_SERIES
                if left_confirmation is None
                else CONFIRMATION_SESSION_AGREES,
            )
        elif left_confirmation is None or right_confirmation is None:
            outcome = STRUCTURAL_DISAGREEMENT
            reasons = (*reasons, CONFIRMATION_PRESENT_IN_ONE_SERIES_ONLY)
        else:
            outcome = STRUCTURAL_DISAGREEMENT
            reasons = (*reasons, CONFIRMATION_SESSION_DIFFERS)
    else:
        outcome = NOT_COMPARABLE
    return StructuralComparisonEvent(
        comparison_id=comparison_id,
        series_ids=(left.series_id, right.series_id),
        event_family=family,
        candidate_session=session,
        required_sessions=required,
        session_status=statuses,
        missing_required_sessions=missing,
        availability_gap_side=gap_side,
        comparability=comparability,
        outcome=outcome,
        detected_in=tuple(
            series_id
            for series_id, value in sorted(confirmations.items())
            if value is not None
        ),
        confirmation_sessions=confirmations,
        reason_codes=reasons,
    )


def _confirmation_calendar(
    session: datetime,
    *,
    left_sessions: int,
    right_sessions: int,
) -> tuple[datetime, ...]:
    week = require_weekly_session(session, "candidate_session")
    return tuple(
        week + offset * WEEKLY_SESSION_STEP
        for offset in range(-left_sessions, right_sessions + 1)
    )


def _comparability(
    left: WeeklyStructureSnapshot,
    right: WeeklyStructureSnapshot,
    *,
    required: Sequence[datetime],
) -> tuple[
    dict[str, dict[datetime, str]],
    dict[str, tuple[datetime, ...]],
    str,
    str | None,
    tuple[str, ...],
]:
    statuses = {
        snapshot.series_id: {
            week: snapshot.calendar.session_status(week) for week in required
        }
        for snapshot in (left, right)
    }
    missing = {
        series_id: tuple(
            sorted(week for week, status in weeks.items() if status != SESSION_PRESENT)
        )
        for series_id, weeks in statuses.items()
    }
    absent_sides = tuple(
        sorted(
            series_id
            for series_id, weeks in statuses.items()
            if any(status == SESSION_ABSENT for status in weeks.values())
        )
    )
    pending = any(
        status == SESSION_PENDING
        for weeks in statuses.values()
        for status in weeks.values()
    )
    coverage = any(
        status == SESSION_OUT_OF_COVERAGE
        for weeks in statuses.values()
        for status in weeks.values()
    )
    reasons: list[str] = []
    if absent_sides:
        reasons.append(
            REQUIRED_SESSION_ABSENT_IN_BOTH_SERIES
            if len(absent_sides) == 2
            else REQUIRED_SESSION_ABSENT_IN_ONE_SERIES
        )
    if pending:
        reasons.append(CONFIRMATION_WINDOW_NOT_YET_AVAILABLE)
    if coverage:
        reasons.append(REQUIRED_SESSION_OUTSIDE_SERIES_COVERAGE)
    if absent_sides:
        comparability = NOT_COMPARABLE_AVAILABILITY_GAP
    elif pending:
        comparability = NOT_COMPARABLE_CONFIRMATION_PENDING
    elif coverage:
        comparability = NOT_COMPARABLE_SERIES_COVERAGE
    else:
        comparability = COMPARABLE
    gap_side = (
        None
        if not absent_sides
        else BOTH_SERIES
        if len(absent_sides) == 2
        else absent_sides[0]
    )
    return statuses, missing, comparability, gap_side, tuple(reasons)


def _canonical_pair(series_pair: Sequence[str]) -> tuple[str, str]:
    pair = tuple(series_pair)
    if len(pair) != 2 or pair[0] == pair[1]:
        raise CrossProviderComparisonError(
            "a pairwise comparison requires two distinct series identifiers"
        )
    ordered = tuple(sorted(pair))
    return ordered[0], ordered[1]


# --- metrics ------------------------------------------------------------------


def _rate(numerator: int, denominator: int) -> str | None:
    """Return an exact rate resolved in this module's own Decimal context."""

    if denominator == 0:
        return None
    return str(_RATE_CONTEXT.divide(Decimal(numerator), Decimal(denominator)))


def _measurement(
    numerator: int,
    denominator: int,
    *,
    denominator_semantics: str,
) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "denominator_semantics": denominator_semantics,
        "rate": _rate(numerator, denominator),
    }


def _family_events(
    comparison: PairwiseStructureComparison,
    family: str,
) -> tuple[StructuralComparisonEvent, ...]:
    return tuple(event for event in comparison.events if event.event_family == family)


def _family_metrics(
    comparison: PairwiseStructureComparison,
    family: str,
) -> dict[str, Any]:
    """Report one family's before/after counts with both denominators named."""

    events = _family_events(comparison, family)
    detected = tuple(event for event in events if event.detected_in)
    comparable = tuple(event for event in events if event.comparability == COMPARABLE)
    comparable_detected = tuple(event for event in comparable if event.detected_in)
    raw_disagreements = tuple(
        event
        for event in detected
        if (
            len(event.detected_in) == 1
            if family in SWING_FAMILIES
            else _confirmation_values(event) is not None
            and len(set(_confirmation_values(event))) == 2
        )
    )
    true_disagreements = tuple(
        event for event in comparable if event.outcome == STRUCTURAL_DISAGREEMENT
    )
    not_comparable = tuple(
        event for event in events if event.comparability != COMPARABLE
    )
    not_comparable_detected = tuple(event for event in not_comparable if event.detected_in)
    reason_counts: dict[str, int] = {}
    for event in not_comparable:
        for code in event.reason_codes:
            reason_counts[code] = reason_counts.get(code, 0) + 1
    return {
        "candidate_session_count": len(events),
        "comparable_candidate_count": len(comparable),
        "not_comparable_candidate_count": len(not_comparable),
        "not_comparable_reason_counts": dict(sorted(reason_counts.items())),
        "raw_detected_event_count": len(detected),
        "raw_disagreement_count": len(raw_disagreements),
        "availability_contaminated_disagreement_count": sum(
            event.comparability != COMPARABLE for event in raw_disagreements
        ),
        "comparable_event_count": len(comparable_detected),
        "not_comparable_event_count": len(not_comparable_detected),
        "agreement_event_count": sum(
            event.outcome == STRUCTURAL_AGREEMENT for event in comparable_detected
        ),
        "true_disagreement_count": len(true_disagreements),
        "prior_disagreement_rate": _measurement(
            len(raw_disagreements),
            len(detected),
            denominator_semantics=ALL_EVENT_DENOMINATOR,
        ),
        "revised_disagreement_rate": _measurement(
            len(true_disagreements),
            len(comparable_detected),
            denominator_semantics=COMPARABLE_EVENT_DENOMINATOR,
        ),
        "revised_disagreement_rate_on_all_events": _measurement(
            len(true_disagreements),
            len(detected),
            denominator_semantics=ALL_EVENT_DENOMINATOR,
        ),
        "disagreement_sessions": [
            {
                "candidate_session": event.candidate_session.isoformat(),
                "detected_in": list(event.detected_in),
                "confirmation_sessions": {
                    series_id: None if value is None else value.isoformat()
                    for series_id, value in sorted(event.confirmation_sessions.items())
                },
            }
            for event in true_disagreements
        ],
        "availability_contaminated_sessions": [
            {
                "candidate_session": event.candidate_session.isoformat(),
                "detected_in": list(event.detected_in),
                "comparability": event.comparability,
                "availability_gap_side": event.availability_gap_side,
                "missing_required_sessions": {
                    series_id: [item.isoformat() for item in sessions]
                    for series_id, sessions in sorted(
                        event.missing_required_sessions.items()
                    )
                    if sessions
                },
                "reason_codes": list(event.reason_codes),
            }
            for event in raw_disagreements
            if event.comparability != COMPARABLE
        ][:_MAX_REPORTED_SESSIONS],
    }


def _confirmation_values(
    event: StructuralComparisonEvent,
) -> tuple[datetime | None, ...] | None:
    if len(event.confirmation_sessions) != 2:
        return None
    return tuple(value for _, value in sorted(event.confirmation_sessions.items()))


def _swing_disagreement_events(
    comparison: PairwiseStructureComparison,
) -> tuple[StructuralComparisonEvent, ...]:
    return tuple(
        event
        for event in comparison.events
        if event.event_family in SWING_FAMILIES
        and event.comparability == COMPARABLE
        and event.outcome == STRUCTURAL_DISAGREEMENT
    )


def _raw_swing_disagreement_events(
    comparison: PairwiseStructureComparison,
) -> tuple[StructuralComparisonEvent, ...]:
    """Swing candidates the production detectors resolve differently.

    This is the V1 unit: comparability is not consulted, so an availability
    gap and a venue disagreement are still indistinguishable here. It exists
    only to report the prior measurement beside the revised one.
    """

    return tuple(
        event
        for event in comparison.events
        if event.event_family in SWING_FAMILIES and len(event.detected_in) == 1
    )


def _comparable_swing_event_count(comparison: PairwiseStructureComparison) -> int:
    return sum(
        1
        for event in comparison.events
        if event.event_family in SWING_FAMILIES
        and event.comparability == COMPARABLE
        and event.detected_in
    )


def _matched_within(
    comparison: PairwiseStructureComparison,
    *,
    weeks: int,
    comparable_only: bool = True,
) -> int:
    """Pair opposing comparable swing disagreements within ``weeks`` sessions.

    The nearest admissible pair is taken first, then the next, so the matching
    is independent of both provider order and dictionary order.
    """

    left_id, right_id = comparison.series_ids
    disagreements = (
        _swing_disagreement_events(comparison)
        if comparable_only
        else _raw_swing_disagreement_events(comparison)
    )
    left_only = [
        event for event in disagreements if event.detected_in == (left_id,)
    ]
    right_only = [
        event for event in disagreements if event.detected_in == (right_id,)
    ]
    candidates = sorted(
        (
            abs((left.candidate_session - right.candidate_session).days) // 7,
            left.candidate_session,
            right.candidate_session,
            left.event_family,
        )
        for left in left_only
        for right in right_only
        if left.event_family == right.event_family
        and abs((left.candidate_session - right.candidate_session).days) <= weeks * 7
    )
    used_left: set[tuple[str, datetime]] = set()
    used_right: set[tuple[str, datetime]] = set()
    matched = 0
    for _, left_session, right_session, family in candidates:
        if (family, left_session) in used_left or (family, right_session) in used_right:
            continue
        used_left.add((family, left_session))
        used_right.add((family, right_session))
        matched += 1
    return matched


def _structural_state_disagreement_count(
    comparison: PairwiseStructureComparison,
    *,
    comparable_only: bool = True,
) -> int:
    """Count comparable swing disagreements that changed breakout/reclaim state.

    A swing only one series holds changes structural state when that series
    also confirmed a breakout or reclaim from it; otherwise the difference is a
    label the downstream structure never used.
    """

    confirmed = {
        (event.event_family, event.candidate_session): event
        for event in comparison.events
        if event.event_family in DERIVED_FAMILIES
    }
    disagreements = (
        _swing_disagreement_events(comparison)
        if comparable_only
        else _raw_swing_disagreement_events(comparison)
    )
    count = 0
    for event in disagreements:
        derived = confirmed.get(
            (DERIVED_FAMILY_BY_SWING[event.event_family], event.candidate_session)
        )
        if derived is not None and derived.detected_in:
            count += 1
    return count


def pairwise_metrics(comparison: PairwiseStructureComparison) -> dict[str, Any]:
    """Return every family metric plus the six frozen V2 structural metrics."""

    families = {family: _family_metrics(comparison, family) for family in EVENT_FAMILIES}
    exact_numerator = sum(
        families[family]["true_disagreement_count"] for family in SWING_FAMILIES
    )
    exact_denominator = _comparable_swing_event_count(comparison)
    all_swing_events = sum(
        families[family]["raw_detected_event_count"] for family in SWING_FAMILIES
    )
    all_swing_disagreements = sum(
        families[family]["raw_disagreement_count"] for family in SWING_FAMILIES
    )
    combined: dict[str, Any] = {
        "raw_detected_event_count": all_swing_events,
        "raw_disagreement_count": all_swing_disagreements,
        "availability_contaminated_disagreement_count": sum(
            families[family]["availability_contaminated_disagreement_count"]
            for family in SWING_FAMILIES
        ),
        "comparable_event_count": exact_denominator,
        "not_comparable_event_count": sum(
            families[family]["not_comparable_event_count"] for family in SWING_FAMILIES
        ),
        "true_disagreement_count": exact_numerator,
        "exact_timestamp_swing_disagreement_rate": _measurement(
            exact_numerator,
            exact_denominator,
            denominator_semantics=COMPARABLE_EVENT_DENOMINATOR,
        ),
        "prior_exact_timestamp_swing_disagreement_rate": _measurement(
            all_swing_disagreements,
            all_swing_events,
            denominator_semantics=ALL_EVENT_DENOMINATOR,
        ),
    }
    for weeks in (1, 2):
        matched = _matched_within(comparison, weeks=weeks)
        prior_matched = _matched_within(comparison, weeks=weeks, comparable_only=False)
        combined[f"within_{weeks}_week_swing_disagreement_rate"] = _measurement(
            exact_numerator - 2 * matched,
            exact_denominator - matched,
            denominator_semantics=COMPARABLE_EVENT_DENOMINATOR,
        )
        combined[f"prior_within_{weeks}_week_swing_disagreement_rate"] = _measurement(
            all_swing_disagreements - 2 * prior_matched,
            all_swing_events - prior_matched,
            denominator_semantics=ALL_EVENT_DENOMINATOR,
        )
        combined[f"within_{weeks}_week_matched_pair_count"] = matched
        combined[f"prior_within_{weeks}_week_matched_pair_count"] = prior_matched
    combined["structural_state_disagreement_rate"] = _measurement(
        _structural_state_disagreement_count(comparison),
        exact_denominator,
        denominator_semantics=COMPARABLE_EVENT_DENOMINATOR,
    )
    combined["prior_structural_state_disagreement_rate"] = _measurement(
        _structural_state_disagreement_count(comparison, comparable_only=False),
        all_swing_events,
        denominator_semantics=ALL_EVENT_DENOMINATOR,
    )
    return {
        **families,
        "combined_swing": combined,
        "breakout_disagreement_rate": families[BREAKOUT_FAMILY][
            "revised_disagreement_rate"
        ],
        "reclaim_disagreement_rate": families[RECLAIM_FAMILY][
            "revised_disagreement_rate"
        ],
        "prior_breakout_disagreement_rate": families[BREAKOUT_FAMILY][
            "prior_disagreement_rate"
        ],
        "prior_reclaim_disagreement_rate": families[RECLAIM_FAMILY][
            "prior_disagreement_rate"
        ],
    }


def frozen_v2_gate_metric(metrics: Mapping[str, Any], metric: str) -> dict[str, Any]:
    """Return one affected frozen-V2 metric measured under this contract."""

    if metric in (
        "exact_timestamp_swing_disagreement_rate",
        "within_1_week_swing_disagreement_rate",
        "within_2_week_swing_disagreement_rate",
        "structural_state_disagreement_rate",
    ):
        return metrics["combined_swing"][metric]
    if metric in ("breakout_disagreement_rate", "reclaim_disagreement_rate"):
        return metrics[metric]
    raise CrossProviderComparisonError(f"unknown affected V2 gate metric {metric!r}")


def prior_v2_gate_metric(metrics: Mapping[str, Any], metric: str) -> dict[str, Any]:
    """Return the same metric on the V1 all-detected-event denominator."""

    if metric in (
        "exact_timestamp_swing_disagreement_rate",
        "within_1_week_swing_disagreement_rate",
        "within_2_week_swing_disagreement_rate",
        "structural_state_disagreement_rate",
    ):
        return metrics["combined_swing"][f"prior_{metric}"]
    if metric in ("breakout_disagreement_rate", "reclaim_disagreement_rate"):
        return metrics[f"prior_{metric}"]
    raise CrossProviderComparisonError(f"unknown affected V2 gate metric {metric!r}")


# --- legacy reconciliation ----------------------------------------------------


def reconcile_legacy_differences(
    comparisons: Mapping[str, PairwiseStructureComparison],
    legacy_differences: Sequence[Any],
) -> tuple[dict[str, Any], ...]:
    """Classify each V1 structural difference under the V2 contract.

    The V1 comparison counts a symmetric-difference element: one swing that
    only one series holds, or one breakout/reclaim identified by its source
    level and its confirmation week. Every such element is anchored to exactly
    one candidate session here, so the prior count can be carried across
    without re-deriving it.
    """

    index = {
        frozenset(comparison.series_ids): comparison for comparison in comparisons.values()
    }
    events = {
        (frozenset(comparison.series_ids), event.event_family, event.candidate_session): event
        for comparison in comparisons.values()
        for event in comparison.events
    }
    reconciled = []
    for difference in legacy_differences:
        baseline, candidate = difference.comparison.split("_vs_")
        key = frozenset((baseline, candidate))
        if key not in index:
            raise CrossProviderComparisonError(
                f"legacy comparison {difference.comparison!r} has no V2 counterpart"
            )
        event = events.get((key, difference.level_type, difference.level_timestamp))
        if event is None:
            raise CrossProviderComparisonError(
                f"legacy {difference.level_type} at "
                f"{difference.level_timestamp.isoformat()} has no V2 candidate"
            )
        reconciled.append(
            {
                "legacy_comparison": difference.comparison,
                "legacy_classification": difference.classification,
                "comparison_id": event.comparison_id,
                "event_family": event.event_family,
                "candidate_session": event.candidate_session.isoformat(),
                "confirmation_timestamp": (
                    None
                    if difference.confirmation_timestamp is None
                    else difference.confirmation_timestamp.isoformat()
                ),
                "present_in": difference.present_in,
                "comparability": event.comparability,
                "outcome": event.outcome,
                "availability_gap_side": event.availability_gap_side,
                "missing_required_sessions": {
                    series_id: [item.isoformat() for item in sessions]
                    for series_id, sessions in sorted(event.missing_required_sessions.items())
                    if sessions
                },
                "reason_codes": list(event.reason_codes),
            }
        )
    return tuple(
        sorted(
            reconciled,
            key=lambda item: (
                item["comparison_id"],
                EVENT_FAMILIES.index(item["event_family"]),
                item["candidate_session"],
                item["confirmation_timestamp"] or "",
                item["present_in"],
            ),
        )
    )


# --- sample runner ------------------------------------------------------------


def sample_manifest(sample_dir: Path, *, sample_id: str) -> dict[str, Any]:
    """Return the collected sample's own provenance, verified before use."""

    manifest = json.loads((sample_dir / "collection_manifest.json").read_text())
    if manifest["price_source_policy_version"] != PRICE_SOURCE_POLICY_VERSION:
        raise CrossProviderComparisonError(
            "collected sample was not gathered under the active price-source policy"
        )
    providers = []
    for provider in sorted(manifest["providers"], key=lambda item: item["provider"]):
        path = sample_dir / f"{provider['provider']}_btc_usd_1h.jsonl.gz"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != provider["raw_artifact_sha256"]:
            raise CrossProviderComparisonError(
                f"collected artifact digest mismatch: {path}"
            )
        providers.append(
            {
                "provider": provider["provider"],
                "exchange": provider["exchange"],
                "instrument": provider["instrument"],
                "first_timestamp": provider["first_timestamp"],
                "last_timestamp": provider["last_timestamp"],
                "raw_artifact": path.name,
                "raw_artifact_sha256": digest,
            }
        )
    return {
        "collection_manifest": f"{sample_id}/collection_manifest.json",
        "price_source_policy_version": manifest["price_source_policy_version"],
        "historical_period_start": manifest["historical_period_start"],
        "historical_period_end": manifest["historical_period_end"],
        "providers": providers,
    }


def weekly_series_by_provider(
    histories: Mapping[str, Sequence[OhlcvBar]],
    *,
    evaluation_time: datetime,
) -> dict[str, tuple[OhlcvBar, ...]]:
    """Build each provider's canonical weekly series at one evaluation instant."""

    return {
        provider_id: tuple(
            bar
            for bar in build_canonical_market_bars(
                bars,
                data_available_at=evaluation_time,
                timeframes=(WEEKLY_TIMEFRAME,),
            )
            if bar.timeframe == WEEKLY_TIMEFRAME
        )
        for provider_id, bars in sorted(histories.items())
    }


def compare_sample(
    sample_dir: Path,
    *,
    sample_id: str | None = None,
    baseline_provider_id: str = BITSTAMP_PROVIDER_ID,
) -> dict[str, Any]:
    """Re-measure one already-collected sample under the V2 comparison.

    ``sample_id`` is the repository-relative identity recorded in the result,
    so the persisted record does not carry the absolute path of whichever
    machine produced it.
    """

    identity = sample_dir.as_posix() if sample_id is None else sample_id
    manifest = sample_manifest(sample_dir, sample_id=identity)
    histories = load_inspected_sample(sample_dir)
    evaluation_time = sample_evaluation_time(histories)
    earliest = min(bar.timestamp for bars in histories.values() for bar in bars)
    latest = max(bar.timestamp for bars in histories.values() for bar in bars)
    guard_untouched_validation_sample(
        start=earliest,
        end=latest,
        purpose=f"{COMPARISON_CONTRACT_VERSION} re-measurement",
    )

    weekly = weekly_series_by_provider(histories, evaluation_time=evaluation_time)
    snapshots = {
        provider_id: weekly_structure_snapshot(
            bars,
            series_id=provider_id,
            evaluation_time=evaluation_time,
        )
        for provider_id, bars in weekly.items()
    }
    provider_ids = sorted(snapshots)
    comparisons = {}
    for index, left_id in enumerate(provider_ids):
        for right_id in provider_ids[index + 1 :]:
            comparison = compare_weekly_structure(snapshots, series_pair=(left_id, right_id))
            comparisons[comparison.comparison_id] = comparison

    legacy = structural_differences(
        histories,
        baseline_provider_id=baseline_provider_id,
        as_of=evaluation_time,
    )
    reconciled = reconcile_legacy_differences(comparisons, legacy)
    return {
        "sample_dir": identity,
        "dataset": manifest,
        "evaluation_time": evaluation_time.isoformat(),
        "observation_window": {
            "first_hourly_observation": earliest.isoformat(),
            "last_hourly_observation": latest.isoformat(),
        },
        "series": [snapshots[provider_id].as_record() for provider_id in provider_ids],
        "comparisons": [
            comparisons[comparison_id].as_record()
            for comparison_id in sorted(comparisons)
        ],
        "legacy_reconciliation": {
            "legacy_comparison_contract_version": LEGACY_COMPARISON_CONTRACT_VERSION,
            "baseline_provider_id": baseline_provider_id,
            "legacy_difference_count": len(legacy),
            "now_not_comparable_count": sum(
                item["outcome"] == NOT_COMPARABLE for item in reconciled
            ),
            "still_disagreement_count": sum(
                item["outcome"] == STRUCTURAL_DISAGREEMENT for item in reconciled
            ),
            "now_agreement_count": sum(
                item["outcome"] == STRUCTURAL_AGREEMENT for item in reconciled
            ),
            "differences": list(reconciled),
        },
    }


# --- frozen V2 gate measurability --------------------------------------------

# Predeclared before the samples were measured, so the outcome is read off the
# evidence rather than chosen after seeing it.
CLASSIFICATION_RULE = (
    "BLOCKED_BY_NEW_CORRECTNESS_DEFECT when a collected artifact digest fails, "
    "the contract refuses its own inputs, or the V1 structural counts no longer "
    "reproduce; NOT_READY_STRUCTURAL_GATES_STILL_INVALID when any affected hard "
    "gate metric has no comparable denominator on a measured pair, or when "
    "not-comparable events outnumber comparable events in a pair's structural "
    "event universe; RESEARCH_INCONCLUSIVE when every affected hard gate is "
    "defined but a frozen threshold's verdict changes between the comparable "
    "and all-event denominators, so the frozen number cannot be applied to the "
    "revised denominator without changing its meaning; "
    "READY_TO_BUILD_SEALED_VALIDATOR otherwise."
)

V2_PROTOCOL_DEFINITION_PATH = (
    "research_artifacts/btc_reference_composite/BTC_REFERENCE_COMPOSITE_V2/"
    "protocol_definition.json"
)
BTC019B_DECISION_PATH = "research_artifacts/btc019b/final_diagnostic_decision.json"
BTC019B_SWING_DIAGNOSTICS_PATH = (
    "research_artifacts/btc019b/swing_disagreement_diagnostics.json"
)
FROZEN_V1_COMPARISON_REPORT_PATH = (
    "research_artifacts/btc019_correction_audit/PRICE_SOURCE_POLICY_V1/"
    "comparison_report.json"
)
COMPLETION_GATE_ASSESSMENT_PATH = (
    "research_artifacts/btc019_completion_gate/completion_gate_assessment.json"
)


def frozen_affected_v2_gates(repository_root: Path) -> tuple[dict[str, Any], ...]:
    """Read the six affected approval gates from the frozen V2 definition.

    The thresholds are read, never written. This module has no path that can
    change a frozen gate, a threshold or a direction.
    """

    definition = json.loads((repository_root / V2_PROTOCOL_DEFINITION_PATH).read_text())
    gates = {gate["metric"]: gate for gate in definition["approval_gates"]}
    missing = [metric for metric in AFFECTED_V2_GATE_METRICS if metric not in gates]
    if missing:
        raise CrossProviderComparisonError(
            f"frozen V2 protocol no longer declares {missing}"
        )
    return tuple(
        {
            "metric": metric,
            "hard": gates[metric]["hard"],
            "direction": gates[metric]["direction"],
            "threshold": gates[metric]["threshold"],
            "validation_stage": gates[metric]["validation_stage"],
        }
        for metric in AFFECTED_V2_GATE_METRICS
    )


def _threshold_verdict(
    measurement: Mapping[str, Any],
    gate: Mapping[str, Any],
) -> str | None:
    if measurement["rate"] is None:
        return None
    value = Decimal(measurement["rate"])
    threshold = Decimal(str(gate["threshold"]))
    if gate["direction"] == "maximum":
        return "PASS" if value <= threshold else "FAIL"
    if gate["direction"] == "minimum":
        return "PASS" if value >= threshold else "FAIL"
    return "PASS" if value == threshold else "FAIL"


def gate_measurability(
    repository_root: Path,
    samples: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Report whether each affected frozen V2 structural gate is measurable.

    This is a measurability probe on raw provider pairs, not an approval
    evaluation of any candidate reference. It changes no threshold and
    promotes nothing.
    """

    gates = frozen_affected_v2_gates(repository_root)
    measurements = []
    for gate in gates:
        rows = []
        for sample_dir in sorted(samples):
            for comparison in samples[sample_dir]["comparisons"]:
                metrics = comparison["metrics"]
                revised = frozen_v2_gate_metric(metrics, gate["metric"])
                prior = prior_v2_gate_metric(metrics, gate["metric"])
                excluded = metrics["combined_swing"]["not_comparable_event_count"]
                if gate["metric"] == "breakout_disagreement_rate":
                    excluded = metrics[BREAKOUT_FAMILY]["not_comparable_event_count"]
                elif gate["metric"] == "reclaim_disagreement_rate":
                    excluded = metrics[RECLAIM_FAMILY]["not_comparable_event_count"]
                if revised["denominator"] == 0:
                    status = GATE_UNDEFINED_NO_COMPARABLE_EVENTS
                elif excluded:
                    status = GATE_DEFINED_WITH_EXCLUSIONS
                else:
                    status = GATE_DEFINED_AND_UNCONTAMINATED
                revised_verdict = _threshold_verdict(revised, gate)
                prior_verdict = _threshold_verdict(prior, gate)
                rows.append(
                    {
                        "sample_dir": sample_dir,
                        "comparison_id": comparison["comparison_id"],
                        "status": status,
                        "excluded_event_count": excluded,
                        "revised": revised,
                        "prior": prior,
                        "frozen_threshold_verdict_on_revised_denominator": revised_verdict,
                        "frozen_threshold_verdict_on_prior_denominator": prior_verdict,
                        "verdict_stable_across_denominators": revised_verdict
                        == prior_verdict,
                    }
                )
        measurements.append(
            {
                **gate,
                "threshold_changed": False,
                "measurements": rows,
                "undefined_measurement_count": sum(
                    row["status"] == GATE_UNDEFINED_NO_COMPARABLE_EVENTS for row in rows
                ),
                "verdict_unstable_measurement_count": sum(
                    not row["verdict_stable_across_denominators"] for row in rows
                ),
            }
        )
    return {
        "note": (
            "Measurability probe on raw provider pairs under "
            f"{COMPARISON_CONTRACT_VERSION}. It evaluates no candidate reference, "
            "approves nothing, and leaves every frozen threshold and gate exactly "
            "as the frozen V2 protocol declares it."
        ),
        "gates": measurements,
    }


# --- BTC-019B known-case probe ------------------------------------------------


def btc019b_known_case_probe(repository_root: Path) -> dict[str, Any]:
    """Apply the comparability contract to BTC-019B's own frozen disagreements.

    BTC-019B compared the frozen `MEDIAN_OHLC_V1` composite against provider
    consensus and recorded four exact-timestamp swing disagreements. Its
    quality-state record also names the weekly buckets the composite omitted
    because the venues disagreed for whole hours. Both facts are read from the
    frozen artifacts; the classification is derived here.
    """

    decision = json.loads((repository_root / BTC019B_DECISION_PATH).read_text())
    diagnostics = json.loads(
        (repository_root / BTC019B_SWING_DIAGNOSTICS_PATH).read_text()
    )
    omitted = tuple(
        sorted(
            {
                require_weekly_session(
                    datetime.fromisoformat(record["weekly_bucket"]),
                    "weekly_bucket",
                )
                for record in decision["quality_state_analysis"][
                    "unresolved_venue_disagreement"
                ]["records"]
                if record["complete_week_omitted_from_frozen_composite"]
            }
        )
    )
    records = []
    for record in diagnostics["records"]:
        session = require_weekly_session(
            datetime.fromisoformat(record["event_timestamp"]),
            "event_timestamp",
        )
        required = _confirmation_calendar(
            session,
            left_sessions=DEFAULT_WEEKLY_SWING_LEFT_BARS,
            right_sessions=DEFAULT_WEEKLY_SWING_RIGHT_BARS,
        )
        blocking = tuple(week for week in omitted if week in required)
        records.append(
            {
                "pair_id": record["pair_id"],
                "event_type": record["event_type"],
                "disagreement_side": record["disagreement_side"],
                "event_timestamp": session.isoformat(),
                "required_sessions": [item.isoformat() for item in required],
                "composite_omitted_sessions_in_window": [
                    item.isoformat() for item in blocking
                ],
                "comparability": (
                    NOT_COMPARABLE_AVAILABILITY_GAP if blocking else COMPARABLE
                ),
                "outcome": NOT_COMPARABLE if blocking else STRUCTURAL_DISAGREEMENT,
            }
        )
    records.sort(key=lambda item: (item["event_timestamp"], item["disagreement_side"]))
    return {
        "source": "frozen BTC-019B artifacts; classification derived here",
        "frozen_exact_timestamp_disagreement_count": diagnostics["metrics"][
            "exact_timestamp"
        ]["disagreement_count"],
        "frozen_exact_timestamp_denominator": diagnostics["metrics"]["exact_timestamp"][
            "denominator"
        ],
        "composite_omitted_weekly_sessions": [item.isoformat() for item in omitted],
        "not_comparable_count": sum(
            item["outcome"] == NOT_COMPARABLE for item in records
        ),
        "remaining_disagreement_count": sum(
            item["outcome"] == STRUCTURAL_DISAGREEMENT for item in records
        ),
        "records": records,
    }


# --- legacy reproduction ------------------------------------------------------


def legacy_reproduction(
    repository_root: Path,
    samples: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Prove the V1 comparison still reproduces its own frozen numbers.

    The old contract is not retired, corrected or re-run under new semantics.
    It is executed exactly as it stands and checked against the evidence it
    produced, so both comparison versions coexist.
    """

    frozen = json.loads((repository_root / FROZEN_V1_COMPARISON_REPORT_PATH).read_text())
    assessment = json.loads(
        (repository_root / COMPLETION_GATE_ASSESSMENT_PATH).read_text()
    )
    per_sample = []
    for sample_dir in sorted(samples):
        differences = samples[sample_dir]["legacy_reconciliation"]["differences"]
        counts = {
            family: sum(item["event_family"] == family for item in differences)
            for family in EVENT_FAMILIES
        }
        recorded = len(assessment["samples"][sample_dir]["structural_differences"])
        per_sample.append(
            {
                "sample_dir": sample_dir,
                "difference_count": len(differences),
                "difference_counts_by_family": counts,
                "completion_gate_recorded_difference_count": recorded,
                "reproduces_completion_gate_record": len(differences) == recorded,
            }
        )
    frozen_counts = {
        SWING_HIGH_FAMILY: frozen["swing_high_difference_count"],
        SWING_LOW_FAMILY: frozen["swing_low_difference_count"],
        BREAKOUT_FAMILY: frozen["breakout_difference_count"],
        RECLAIM_FAMILY: frozen["reclaim_difference_count"],
    }
    development = next(
        item for item in per_sample if item["sample_dir"] == INSPECTED_SAMPLE_DIRS[0]
    )
    return {
        "legacy_comparison_contract_version": LEGACY_COMPARISON_CONTRACT_VERSION,
        "frozen_v1_comparison_report": FROZEN_V1_COMPARISON_REPORT_PATH,
        "frozen_v1_difference_counts_by_family": frozen_counts,
        "recomputed_v1_difference_counts_by_family": development[
            "difference_counts_by_family"
        ],
        "frozen_v1_counts_reproduce": development["difference_counts_by_family"]
        == frozen_counts,
        "completion_gate_assessment": COMPLETION_GATE_ASSESSMENT_PATH,
        "samples": per_sample,
        "all_samples_reproduce": all(
            item["reproduces_completion_gate_record"] for item in per_sample
        ),
    }


# --- report -------------------------------------------------------------------


def build_comparison_report(
    repository_root: Path,
    *,
    sample_dirs: Sequence[str] = INSPECTED_SAMPLE_DIRS,
    baseline_provider_id: str = BITSTAMP_PROVIDER_ID,
) -> dict[str, Any]:
    """Return the deterministic `CROSS_PROVIDER_STRUCTURE_COMPARISON_V2` record."""

    samples = {
        relative: compare_sample(
            repository_root / relative,
            sample_id=relative,
            baseline_provider_id=baseline_provider_id,
        )
        for relative in sample_dirs
    }
    reproduction = legacy_reproduction(repository_root, samples)
    measurability = gate_measurability(repository_root, samples)
    totals = _report_totals(samples)
    classification = _classify(
        reproduction=reproduction,
        measurability=measurability,
        samples=samples,
    )
    return {
        "schema_version": COMPARISON_REPORT_SCHEMA_VERSION,
        "comparison_contract_version": COMPARISON_CONTRACT_VERSION,
        "legacy_comparison_contract_version": LEGACY_COMPARISON_CONTRACT_VERSION,
        "source_detector_version": WEEKLY_STRUCTURE_DETECTOR_VERSION,
        "price_source_policy_version": PRICE_SOURCE_POLICY_VERSION,
        "btc019_status": "IN PROGRESS",
        "production_canonical_reference": "UNRESOLVED",
        "production_swing_semantics_changed": False,
        "research_only": True,
        "sealed_sample_opened": False,
        "sealed_validation_window": {
            "start": UNTOUCHED_OOS_START.isoformat(),
            "end": UNTOUCHED_OOS_END.isoformat(),
        },
        "comparison_basis": PAIRWISE_COMPARISON_BASIS,
        "calendar_contract": {
            "timeframe": WEEKLY_TIMEFRAME,
            "session_identity": "UTC Monday 00:00 canonical weekly bucket start",
            "session_statuses": list(SESSION_STATUSES),
            "comparability_states": list(COMPARABILITY_STATES),
            "outcomes": list(COMPARISON_OUTCOMES),
            "reason_codes": list(COMPARISON_REASON_CODES),
            "swing_required_sessions": (
                "candidate week T-3 .. T+3, the detector's own confirmation reach"
            ),
            "derived_required_sessions": (
                "every weekly session after the source swing through the later of "
                "the two confirmations, or through the end of the shared calendar "
                "when either series never confirms"
            ),
            "denominator_semantics": {
                "comparable_event": COMPARABLE_EVENT_DENOMINATOR,
                "all_event": ALL_EVENT_DENOMINATOR,
                "comparable_candidate": COMPARABLE_CANDIDATE_DENOMINATOR,
            },
        },
        "confirmation_window": {
            "left_sessions": DEFAULT_WEEKLY_SWING_LEFT_BARS,
            "right_sessions": DEFAULT_WEEKLY_SWING_RIGHT_BARS,
            "timeframe": WEEKLY_TIMEFRAME,
        },
        "baseline_provider_id": baseline_provider_id,
        "legacy_reproduction": reproduction,
        "btc019b_known_case_probe": btc019b_known_case_probe(repository_root),
        "samples": samples,
        "totals": totals,
        "frozen_v2_gate_measurability": measurability,
        "classification_rule": CLASSIFICATION_RULE,
        "classification": classification,
    }


def _report_totals(samples: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    comparisons = [
        comparison
        for sample in samples.values()
        for comparison in sample["comparisons"]
    ]
    reconciliation = [sample["legacy_reconciliation"] for sample in samples.values()]
    return {
        "sample_count": len(samples),
        "pairwise_comparison_count": len(comparisons),
        "candidate_session_count": sum(
            comparison["candidate_session_count"] for comparison in comparisons
        ),
        "legacy_difference_count": sum(
            item["legacy_difference_count"] for item in reconciliation
        ),
        "legacy_difference_now_not_comparable_count": sum(
            item["now_not_comparable_count"] for item in reconciliation
        ),
        "legacy_difference_still_disagreement_count": sum(
            item["still_disagreement_count"] for item in reconciliation
        ),
        "legacy_difference_now_agreement_count": sum(
            item["now_agreement_count"] for item in reconciliation
        ),
        **{
            f"{family}_true_disagreement_count": sum(
                comparison["metrics"][family]["true_disagreement_count"]
                for comparison in comparisons
            )
            for family in EVENT_FAMILIES
        },
        **{
            f"{family}_not_comparable_event_count": sum(
                comparison["metrics"][family]["not_comparable_event_count"]
                for comparison in comparisons
            )
            for family in EVENT_FAMILIES
        },
        "comparable_event_count": sum(
            comparison["metrics"][family]["comparable_event_count"]
            for comparison in comparisons
            for family in EVENT_FAMILIES
        ),
        "not_comparable_event_count": sum(
            comparison["metrics"][family]["not_comparable_event_count"]
            for comparison in comparisons
            for family in EVENT_FAMILIES
        ),
        "availability_gap_side_counts": _availability_gap_side_counts(samples),
    }


def _availability_gap_side_counts(
    samples: Mapping[str, Mapping[str, Any]],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for sample in samples.values():
        for comparison in sample["comparisons"]:
            for event in comparison["reported_events"]:
                side = event["availability_gap_side"]
                if side is None:
                    continue
                counts[side] = counts.get(side, 0) + 1
    return dict(sorted(counts.items()))


def _classify(
    *,
    reproduction: Mapping[str, Any],
    measurability: Mapping[str, Any],
    samples: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    reasons: list[str] = []
    if not (
        reproduction["frozen_v1_counts_reproduce"]
        and reproduction["all_samples_reproduce"]
    ):
        reasons.append("V1_STRUCTURAL_COUNTS_NO_LONGER_REPRODUCE")
        return {
            "outcome": BLOCKED_BY_NEW_CORRECTNESS_DEFECT,
            "reason_codes": reasons,
        }
    hard_gates = [gate for gate in measurability["gates"] if gate["hard"]]
    if any(gate["undefined_measurement_count"] for gate in hard_gates):
        reasons.append("HARD_STRUCTURAL_GATE_HAS_NO_COMPARABLE_DENOMINATOR")
    availability_dominated = [
        comparison["comparison_id"]
        for sample in samples.values()
        for comparison in sample["comparisons"]
        if sum(
            comparison["metrics"][family]["not_comparable_event_count"]
            for family in EVENT_FAMILIES
        )
        > sum(
            comparison["metrics"][family]["comparable_event_count"]
            for family in EVENT_FAMILIES
        )
    ]
    if availability_dominated:
        reasons.append("STRUCTURAL_EVENT_UNIVERSE_DOMINATED_BY_AVAILABILITY")
    if reasons:
        return {
            "outcome": NOT_READY_STRUCTURAL_GATES_STILL_INVALID,
            "reason_codes": reasons,
            "availability_dominated_comparisons": availability_dominated,
        }
    unstable = [
        gate["metric"]
        for gate in hard_gates
        if gate["verdict_unstable_measurement_count"]
    ]
    if unstable:
        return {
            "outcome": RESEARCH_INCONCLUSIVE,
            "reason_codes": ["FROZEN_THRESHOLD_VERDICT_DEPENDS_ON_DENOMINATOR"],
            "denominator_sensitive_hard_gates": unstable,
        }
    return {
        "outcome": READY_TO_BUILD_SEALED_VALIDATOR,
        "reason_codes": [
            "V1_EVIDENCE_REPRODUCES",
            "AVAILABILITY_GAPS_SEPARATED_FROM_DISAGREEMENT",
            "AFFECTED_HARD_GATES_DEFINED_ON_AN_EXPLICIT_DENOMINATOR",
        ],
        "scope": (
            "The comparison path is valid enough to proceed to validator "
            "construction. BTC_REFERENCE_COMPOSITE_V2 is not approved, BTC-019 "
            "is not DONE, and the sealed sample stays shut."
        ),
    }


# --- persistence --------------------------------------------------------------


COMPARISON_OUTPUT_NAMESPACE = "research_artifacts/btc019_structure_comparison_v2"
COMPARISON_REPORT_FILENAME = "comparison_report.json"


def write_comparison_report(
    repository_root: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Persist the report as deterministic ASCII JSON."""

    report = build_comparison_report(repository_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="ascii",
    )
    return report


def restore_comparison_report(output_path: Path) -> dict[str, Any]:
    """Read a persisted report back, refusing an unknown schema."""

    report = json.loads(output_path.read_text())
    if report.get("schema_version") != COMPARISON_REPORT_SCHEMA_VERSION:
        raise CrossProviderComparisonError(
            "persisted report does not carry "
            f"{COMPARISON_REPORT_SCHEMA_VERSION}"
        )
    if report.get("comparison_contract_version") != COMPARISON_CONTRACT_VERSION:
        raise CrossProviderComparisonError(
            "persisted report was produced by a different comparison contract"
        )
    if report.get("source_detector_version") not in SUPPORTED_DETECTOR_VERSIONS:
        raise CrossProviderComparisonError(
            "persisted report names an unknown structural detector version"
        )
    for field in (
        "legacy_reproduction",
        "samples",
        "totals",
        "frozen_v2_gate_measurability",
        "classification",
        "classification_rule",
        "calendar_contract",
        "confirmation_window",
    ):
        if field not in report:
            raise CrossProviderComparisonError(
                f"persisted report is missing required provenance field {field!r}"
            )
    return report


def verify_comparison_report(repository_root: Path, output_path: Path) -> dict[str, Any]:
    """Recompute the report and refuse a persisted copy that disagrees."""

    persisted = restore_comparison_report(output_path)
    recomputed = build_comparison_report(repository_root)
    if persisted != recomputed:
        raise CrossProviderComparisonError(
            "persisted comparison report does not recompute from the collected "
            "histories"
        )
    return persisted
