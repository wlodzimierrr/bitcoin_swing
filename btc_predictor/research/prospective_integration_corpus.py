"""``PROSPECTIVE_INTEGRATION_CORPUS_V1`` -- a frozen pre-data evidence protocol.

BTC-019 terminated as ``BTC019_TERMINALLY_BLOCKED_BY_MISSING_INTEGRATION_EVIDENCE``
because eight inherited hard gates name a rate and a threshold but no decision
universe, no complete point-in-time input corpus, no comparison reference and no
denominator.  The evidence that would have answered them does not exist and
cannot be manufactured backwards.

This module is the post-Phase-1 answer: it freezes, *before* a single qualifying
observation is accumulated, every rule that can move any of those eight
measurements.  It authors no threshold, moves no frozen byte, reopens no
BTC-019 artifact and collects nothing.  The eight thresholds, directions, hard
roles and stated intents are imported verbatim from the immutable
``BTC_REFERENCE_COMPOSITE_V2`` approval-gate table and re-verified on every
build; a build that cannot reproduce them refuses.

What the protocol supplies is exactly what the historical record lacks: the
scheduled decision universe, the point-in-time input snapshot, the two
deterministic portfolio tracks, the mechanical stop-event taxonomy that replaces
the old hand-picked development-event list, the numerator and denominator of
each measurement, and the append-only provenance that lets a future evaluator
replay all of it.  Collection is *not* authorised by this module: only an
independently reviewed ``FROZEN`` protocol may enter ``COLLECTING``, and this
module refuses every real aggregation until the protocol, separate sufficiency
governance, and collector implementation have each passed their required
independent review.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, Context, Decimal, localcontext
from pathlib import Path
from typing import Any

from btc_predictor.db import portfolio as _portfolio_db
from btc_predictor.features import entry as _entry
from btc_predictor.features import flow as _flow
from btc_predictor.features import momentum as _momentum
from btc_predictor.features import positioning as _positioning
from btc_predictor.features import trend as _trend
from btc_predictor.features import volatility as _volatility
from btc_predictor.portfolio import state_machine as _state_machine
from btc_predictor.research import reference_composite as _rc
from btc_predictor.research import reference_composite_v2 as _v2
from btc_predictor.research.feature_matrix import INITIAL_FEATURE_NAMES
from btc_predictor.signals import data_quality as _data_quality


# ---------------------------------------------------------------------------
# identity
# ---------------------------------------------------------------------------

PROTOCOL_VERSION = "PROSPECTIVE_INTEGRATION_CORPUS_V1"
PROTOCOL_SCHEMA_VERSION = "PROSPECTIVE_INTEGRATION_CORPUS_V1_PROTOCOL_DEFINITION_V1"
PROTOCOL_STATUS = "CORRECTED_PRE_DATA_PROTOCOL_AWAITING_REPEAT_XHIGH_REVIEW"
PROGRAM_TICKET = "POSTP1-001R"
WORKSTREAM = "EPIC X"
WORKSTREAM_NAME = "PROSPECTIVE INTEGRATION EVIDENCE"
FINAL_CLASSIFICATION = (
    "CORRECTED_PROSPECTIVE_INTEGRATION_CORPUS_V1_READY_FOR_REPEAT_XHIGH_REVIEW"
)
AMBIGUOUS_FROZEN_METRIC_CLASSIFICATION = (
    "PROSPECTIVE_PROTOCOL_BLOCKED_BY_AMBIGUOUS_FROZEN_METRIC"
)
AMBIGUOUS_FROZEN_INPUT_CLASSIFICATION = (
    "PROSPECTIVE_PROTOCOL_BLOCKED_BY_AMBIGUOUS_FROZEN_INPUT"
)
SUCCESSOR_PROTOCOL_VERSION = "PROSPECTIVE_INTEGRATION_CORPUS_V2"

# The artifacts deliberately do not live under ``research_artifacts/``. The
# frozen BTC_REFERENCE_COMPOSITE_V5 terminal assessment hashes an inventory of
# every JSON file under ``data/`` and ``research_artifacts/``, so persisting a
# single new JSON artifact in either tree moves the V5 protocol hash away from
# 95e43ee1...775a89. V5 is immutable authority, so this program persists its
# own prospective evidence outside that historical census.
OUTPUT_NAMESPACE = "prospective_evidence/prospective_integration_corpus_v1"
PROTOCOL_FILENAME = "protocol_definition.json"
METRIC_CONTRACTS_FILENAME = "metric_evidence_contracts.json"
DECISION_UNIVERSE_FILENAME = "decision_universe.json"
STOP_EVENT_TAXONOMY_FILENAME = "stop_event_taxonomy.json"
INPUT_SNAPSHOT_FILENAME = "input_snapshot_schema.json"
PORTFOLIO_TRACK_FILENAME = "portfolio_track_contract.json"
EVIDENCE_SUFFICIENCY_FILENAME = "evidence_sufficiency.json"
SEMANTIC_DIFF_FILENAME = "semantic_diff_from_v5_blockers.json"
FEATURE_INPUT_COVERAGE_FILENAME = "feature_input_coverage.json"
WARMUP_HISTORY_FILENAME = "warmup_history.json"
REPORT_FILENAME = "PROSPECTIVE_INTEGRATION_CORPUS_V1_REPORT.md"


# ---------------------------------------------------------------------------
# BTC-019 lineage.  Recorded as immutable history, never as a dependency this
# program may reopen.
# ---------------------------------------------------------------------------

BTC019_TERMINAL_CLASSIFICATION = "BTC019_TERMINALLY_BLOCKED_BY_MISSING_INTEGRATION_EVIDENCE"
FROZEN_V2_DEFINITION_SHA256 = _v2.FROZEN_V2_DEFINITION_SHA256
FROZEN_V3_DEFINITION_SHA256 = (
    "4232e886e7888b85833f778fcba6b2cb3eb5b7d802748aebf3b8adf19c5bf71a"
)
CERTIFIED_V1_VALIDATOR_DEFINITION_SHA256 = (
    "8e6254e0354c04de077bf482ccb6852bfe4299f138d3c97f1ba33859bfc7ffe7"
)
FROZEN_V4_DEFINITION_SHA256 = (
    "670ff12dd3d63615e9ddb3be05d65505bab16b50e50c1fd9ad077a4923a3f501"
)
FROZEN_V5_DEFINITION_SHA256 = (
    "95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89"
)
FAILED_PROTOCOL_DEFINITION_SHA256 = (
    "aaa05c7288971ecb60e331c750fa728db13a3f2046cd597ffe4957a2f3d37326"
)
FAILED_PROTOCOL_IMPLEMENTATION_COMMIT = (
    "b38f387f822da713aa06489e6643c9d6909de32a"
)
FAILED_PROTOCOL_REVIEW = "FAIL — PROSPECTIVE PROTOCOL INVALID"
FAILED_PROTOCOL_REVIEW_CLASSIFICATION = "PROSPECTIVE_PROTOCOL_REQUIRES_FIX"


# ---------------------------------------------------------------------------
# lifecycle
# ---------------------------------------------------------------------------

LIFECYCLE_DRAFT = "DRAFT"
LIFECYCLE_FROZEN = "FROZEN"
LIFECYCLE_PROTOCOL_CERTIFIED = "PROTOCOL_CERTIFIED"
LIFECYCLE_SUFFICIENCY_GOVERNANCE_FROZEN = "SUFFICIENCY_GOVERNANCE_FROZEN"
LIFECYCLE_SUFFICIENCY_GOVERNANCE_CERTIFIED = "SUFFICIENCY_GOVERNANCE_CERTIFIED"
LIFECYCLE_COLLECTION_IMPLEMENTATION_READY = "COLLECTION_IMPLEMENTATION_READY"
LIFECYCLE_COLLECTION_IMPLEMENTATION_CERTIFIED = "COLLECTION_IMPLEMENTATION_CERTIFIED"
LIFECYCLE_COLLECTING = "COLLECTING"
LIFECYCLE_SUFFICIENT = "SUFFICIENT_FOR_EVALUATION"
LIFECYCLE_EVALUATED = "EVALUATED"
LIFECYCLE_CLOSED = "CLOSED"
LIFECYCLE_STATES = (
    LIFECYCLE_DRAFT,
    LIFECYCLE_FROZEN,
    LIFECYCLE_PROTOCOL_CERTIFIED,
    LIFECYCLE_SUFFICIENCY_GOVERNANCE_FROZEN,
    LIFECYCLE_SUFFICIENCY_GOVERNANCE_CERTIFIED,
    LIFECYCLE_COLLECTION_IMPLEMENTATION_READY,
    LIFECYCLE_COLLECTION_IMPLEMENTATION_CERTIFIED,
    LIFECYCLE_COLLECTING,
    LIFECYCLE_SUFFICIENT,
    LIFECYCLE_EVALUATED,
    LIFECYCLE_CLOSED,
)
LIFECYCLE_TRANSITIONS = {
    LIFECYCLE_DRAFT: (LIFECYCLE_FROZEN,),
    LIFECYCLE_FROZEN: (LIFECYCLE_PROTOCOL_CERTIFIED, LIFECYCLE_CLOSED),
    LIFECYCLE_PROTOCOL_CERTIFIED: (
        LIFECYCLE_SUFFICIENCY_GOVERNANCE_FROZEN,
        LIFECYCLE_CLOSED,
    ),
    LIFECYCLE_SUFFICIENCY_GOVERNANCE_FROZEN: (
        LIFECYCLE_SUFFICIENCY_GOVERNANCE_CERTIFIED,
        LIFECYCLE_CLOSED,
    ),
    LIFECYCLE_SUFFICIENCY_GOVERNANCE_CERTIFIED: (
        LIFECYCLE_COLLECTION_IMPLEMENTATION_READY,
        LIFECYCLE_CLOSED,
    ),
    LIFECYCLE_COLLECTION_IMPLEMENTATION_READY: (
        LIFECYCLE_COLLECTION_IMPLEMENTATION_CERTIFIED,
        LIFECYCLE_CLOSED,
    ),
    LIFECYCLE_COLLECTION_IMPLEMENTATION_CERTIFIED: (
        LIFECYCLE_COLLECTING,
        LIFECYCLE_CLOSED,
    ),
    LIFECYCLE_COLLECTING: (LIFECYCLE_SUFFICIENT, LIFECYCLE_CLOSED),
    LIFECYCLE_SUFFICIENT: (LIFECYCLE_EVALUATED, LIFECYCLE_CLOSED),
    LIFECYCLE_EVALUATED: (LIFECYCLE_CLOSED,),
    LIFECYCLE_CLOSED: (),
}
CURRENT_LIFECYCLE_STATE = LIFECYCLE_FROZEN
COLLECTION_AUTHORIZED = False
COLLECTION_ENTRY_REQUIREMENT = (
    "INDEPENDENT_XHIGH_CERTIFICATION_OF_THIS_EXACT_PROTOCOL_HASH_AND_"
    "INDEPENDENT_XHIGH_CERTIFICATION_OF_THE_EXACT_"
    "PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1_HASH_AND_"
    "INDEPENDENT_IMPLEMENTATION_REVIEW_OF_POSTP1_004_MUST_ALL_PASS"
)


# ---------------------------------------------------------------------------
# the eight formerly ownerless Stage-B measurements
# ---------------------------------------------------------------------------

CROSS_MARKET_METRIC = "cross_market_confirmed_stop_preservation_rate"
GAP_THROUGH_METRIC = "gap_through_stop_consensus_agreement_rate"
ISOLATED_VENUE_METRIC = "isolated_venue_stop_suppression_rate"
REGIME_METRIC = "regime_classification_disagreement_rate"
RISK_SIZE_METRIC = "risk_size_p95_relative_difference"
SETUP_METRIC = "setup_classification_disagreement_rate"
TRADE_ACTION_METRIC = "trade_action_disagreement_rate"
TRADE_ELIGIBILITY_METRIC = "trade_eligibility_disagreement_rate"

TARGET_METRICS = (
    CROSS_MARKET_METRIC,
    GAP_THROUGH_METRIC,
    ISOLATED_VENUE_METRIC,
    REGIME_METRIC,
    RISK_SIZE_METRIC,
    SETUP_METRIC,
    TRADE_ACTION_METRIC,
    TRADE_ELIGIBILITY_METRIC,
)
STOP_EVENT_METRICS = (CROSS_MARKET_METRIC, GAP_THROUGH_METRIC, ISOLATED_VENUE_METRIC)
DECISION_METRICS = (
    REGIME_METRIC,
    RISK_SIZE_METRIC,
    SETUP_METRIC,
    TRADE_ACTION_METRIC,
    TRADE_ELIGIBILITY_METRIC,
)


# ---------------------------------------------------------------------------
# numerical standards.  Every rate, median and percentile in this protocol is
# evaluated inside this explicit context, so no ambient ``Decimal`` context can
# move a persisted number.
# ---------------------------------------------------------------------------

CORPUS_DECIMAL_PRECISION = 60
_CONTEXT = Context(prec=CORPUS_DECIMAL_PRECISION)
_SHA256_HEX_LENGTH = 64


class ProspectiveCorpusError(ValueError):
    """Raised when protocol authority, evidence, or artifact integrity is invalid."""


class CollectionNotAuthorizedError(ProspectiveCorpusError):
    """Raised when a caller tries to collect or aggregate before the freeze passes."""


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


# ===========================================================================
# 1. observation unit and clock
# ===========================================================================
#
# Nothing here is a new timing convention.  Both cadences are the existing
# authoritative owners applied to their own bar:
#
#   * the canonical session boundaries come from ``MarketBarSessionDefinition``
#     (hourly source bars, daily sessions opening 00:00 UTC);
#   * the decision delay is the reference-composite owner's
#     ``DEFAULT_DECISION_DELAY`` of five minutes, which the frozen V2
#     ``point_in_time`` block states for an hourly bar as
#     ``observation_time + 1 hour + 5 minutes``; and
#   * availability is the frozen Phase-1 rule
#     ``AVAILABLE_AT_LTE_DECISION_TIME_V1``.

OBSERVATION_UNIT = "decision_time"
CORPUS_TIMEZONE = "UTC"
DECISION_DELAY = timedelta(minutes=5)
DECISION_DELAY_SECONDS = int(DECISION_DELAY.total_seconds())

STRATEGY_DAILY_CADENCE = "STRATEGY_DAILY"
STOP_HOURLY_CADENCE = "STOP_HOURLY"
DECISION_CADENCES = (STOP_HOURLY_CADENCE, STRATEGY_DAILY_CADENCE)

CADENCE_BAR_TIMEFRAME = {
    STRATEGY_DAILY_CADENCE: "1d",
    STOP_HOURLY_CADENCE: "1h",
}
CADENCE_BAR_INTERVAL = {
    STRATEGY_DAILY_CADENCE: timedelta(days=1),
    STOP_HOURLY_CADENCE: timedelta(hours=1),
}

POINT_IN_TIME_POLICY_VERSION = "AVAILABLE_AT_LTE_DECISION_TIME_V1"
PIT_RULE = "available_at <= decision_time"
CANONICAL_SESSION_OWNER = (
    "btc_predictor.data.ohlcv.CANONICAL_BTC_MARKET_BAR_SESSION"
)
DECISION_DELAY_OWNER = (
    "btc_predictor.research.reference_composite.DEFAULT_DECISION_DELAY"
)
PIT_POLICY_OWNER = (
    "btc_predictor.research.feature_matrix.POINT_IN_TIME_POLICY_VERSION"
)
DECISION_GRID_OWNER = (
    "btc_predictor.research.feature_matrix.decision_timestamp_range"
)

LATE_DATA_POLICY = "NEVER_WAIT_NEVER_BACKFILL_A_CLOSED_DECISION"
DUPLICATE_POLICY = "REFUSE_A_SECOND_OBSERVATION_FOR_ONE_SOURCE_KEY_AT_ONE_SLOT"
REVISION_POLICY = "APPEND_A_NEW_REVISION_ROW_NEVER_OVERWRITE"
MISSING_DATA_POLICY = "EXPLICIT_STATUS_NO_ZERO_FILL_NO_SILENT_OMISSION"


def _require_utc(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ProspectiveCorpusError(f"{field_name} must be timezone-aware UTC")
    if value.utcoffset() != timedelta(0):
        raise ProspectiveCorpusError(f"{field_name} must be UTC")
    return value


def decision_time_for(observation_time: datetime, cadence: str) -> datetime:
    """Return the decision instant a bar starting at ``observation_time`` earns.

    ``bar close + DEFAULT_DECISION_DELAY``.  For ``STOP_HOURLY`` this is exactly
    the frozen V2 ``hourly_decision_time`` of ``observation_time + 1h + 5min``;
    for ``STRATEGY_DAILY`` it is the same owner's rule on the canonical daily
    session.
    """

    observation_time = _require_utc(observation_time, "observation_time")
    if cadence not in DECISION_CADENCES:
        raise ProspectiveCorpusError(f"cadence must be one of {DECISION_CADENCES}")
    if cadence == STRATEGY_DAILY_CADENCE and observation_time != observation_time.replace(
        hour=0, minute=0, second=0, microsecond=0
    ):
        raise ProspectiveCorpusError(
            "a STRATEGY_DAILY observation_time must be a 00:00 UTC canonical session start"
        )
    if cadence == STOP_HOURLY_CADENCE and observation_time != observation_time.replace(
        minute=0, second=0, microsecond=0
    ):
        raise ProspectiveCorpusError(
            "a STOP_HOURLY observation_time must be an exact UTC hour"
        )
    return observation_time + CADENCE_BAR_INTERVAL[cadence] + DECISION_DELAY


def scheduled_decision_slots(
    start: datetime,
    end: datetime,
    *,
    cadence: str,
) -> tuple[dict[str, str], ...]:
    """Enumerate the complete scheduled slot census for one cadence.

    The census is a pure function of the epoch bounds and the cadence.  It never
    consults an observation, an output, or a track's state, so a slot can never
    enter or leave it because of what was measured there.
    """

    start = _require_utc(start, "start")
    end = _require_utc(end, "end")
    if cadence not in DECISION_CADENCES:
        raise ProspectiveCorpusError(f"cadence must be one of {DECISION_CADENCES}")
    if end < start:
        raise ProspectiveCorpusError("end must be >= start")
    step = CADENCE_BAR_INTERVAL[cadence]
    slots = []
    current = start
    while current <= end:
        slots.append(
            {
                "cadence": cadence,
                "decision_time": decision_time_for(current, cadence).isoformat(),
                "observation_time": current.isoformat(),
                "slot_id": _digest(
                    {
                        "cadence": cadence,
                        "observation_time": current.isoformat(),
                        "protocol_version": PROTOCOL_VERSION,
                    }
                ),
            }
        )
        current += step
    return tuple(slots)


# ===========================================================================
# 2. decision universes and evaluability states
# ===========================================================================

UNIVERSE_ALL_SCHEDULED = "ALL_SCHEDULED_DECISION_TIMES"
UNIVERSE_DATA_VALID = "DATA_VALID_DECISION_TIMES"
UNIVERSE_SETUP_EVALUABLE = "SETUP_EVALUABLE_DECISION_TIMES"
UNIVERSE_REGIME_EVALUABLE = "REGIME_EVALUABLE_DECISION_TIMES"
UNIVERSE_ELIGIBILITY_EVALUABLE = "ELIGIBILITY_EVALUABLE_DECISION_TIMES"
UNIVERSE_TRADE_ELIGIBLE = "TRADE_ELIGIBLE_DECISION_TIMES"
UNIVERSE_SIZING_EVALUABLE = "SIZING_EVALUABLE_DECISION_TIMES"
UNIVERSE_POSITION_ACTIVE = "POSITION_ACTIVE_DECISION_TIMES"
UNIVERSE_ACTION_EVALUABLE = "ACTION_EVALUABLE_DECISION_TIMES"
UNIVERSE_STOP_ACTIVE_SLOTS = "STOP_ACTIVE_EVALUATION_SLOTS"
UNIVERSE_CROSS_MARKET_EVENTS = "CROSS_MARKET_CONFIRMED_STOP_EVENTS"
UNIVERSE_ISOLATED_VENUE_EVENTS = "ISOLATED_VENUE_STOP_EVENTS"
UNIVERSE_GAP_THROUGH_EVENTS = "GAP_THROUGH_STOP_EVENTS"

DECISION_UNIVERSES = (
    UNIVERSE_ACTION_EVALUABLE,
    UNIVERSE_ALL_SCHEDULED,
    UNIVERSE_CROSS_MARKET_EVENTS,
    UNIVERSE_DATA_VALID,
    UNIVERSE_ELIGIBILITY_EVALUABLE,
    UNIVERSE_GAP_THROUGH_EVENTS,
    UNIVERSE_ISOLATED_VENUE_EVENTS,
    UNIVERSE_POSITION_ACTIVE,
    UNIVERSE_REGIME_EVALUABLE,
    UNIVERSE_SETUP_EVALUABLE,
    UNIVERSE_SIZING_EVALUABLE,
    UNIVERSE_STOP_ACTIVE_SLOTS,
    UNIVERSE_TRADE_ELIGIBLE,
)

# Predeclared observation dispositions.  A scheduled slot always carries exactly
# one of these; none of them is ever inferred from whether the two tracks agree.
STATE_EVALUATED = "EVALUATED"
STATE_NOT_EVALUABLE = "NOT_EVALUABLE"
STATE_NOT_COMPARABLE = "NOT_COMPARABLE"
STATE_DATA_QUALITY_FAIL = "DATA_QUALITY_FAIL"
STATE_REFERENCE_UNAVAILABLE = "REFERENCE_UNAVAILABLE"
OBSERVATION_STATES = (
    STATE_DATA_QUALITY_FAIL,
    STATE_EVALUATED,
    STATE_NOT_COMPARABLE,
    STATE_NOT_EVALUABLE,
    STATE_REFERENCE_UNAVAILABLE,
)

NOT_EVALUABLE_REASONS = (
    "REQUIRED_INPUT_MISSING",
    "REQUIRED_INPUT_NOT_YET_AVAILABLE_AT_DECISION_TIME",
    "WARMUP_HISTORY_INCOMPLETE",
)
NOT_COMPARABLE_REASONS = (
    "CANDIDATE_TRACK_NOT_EVALUABLE",
    "CONTROL_TRACK_NOT_EVALUABLE",
    "ONE_TRACK_POSITION_ACTIVE_ONE_TRACK_FLAT",
    "ONE_TRACK_PRODUCED_NO_POSITIVE_RISK_SIZE",
    "PROVIDER_QUORUM_ABSENT",
    "NO_PRIOR_OBSERVABLE_REFERENCE_PRICE",
    "PRIOR_REFERENCE_SESSION_MISSING",
    "CONTROL_TRACK_HAS_NO_ACTIVE_STOP",
    "CONTROL_STOP_IDENTITY_UNAVAILABLE",
)
DATA_QUALITY_FAIL_REASONS = ("HARD_DATA_QUALITY_GATE_FAILED",)
REFERENCE_UNAVAILABLE_REASONS = (
    "CANDIDATE_REFERENCE_UNAVAILABLE",
    "CONTROL_REFERENCE_UNAVAILABLE",
)
OBSERVATION_REASON_VOCABULARY = tuple(
    sorted(
        NOT_EVALUABLE_REASONS
        + NOT_COMPARABLE_REASONS
        + DATA_QUALITY_FAIL_REASONS
        + REFERENCE_UNAVAILABLE_REASONS
    )
)

UNDEFINED_INSUFFICIENT_EVIDENCE = "UNDEFINED_INSUFFICIENT_EVIDENCE"

# Every universe is a predicate over inputs and per-track state only.  None of
# them may read a comparison outcome, and this invariant is asserted below.
_UNIVERSE_DEFINITIONS: dict[str, dict[str, Any]] = {
    UNIVERSE_ALL_SCHEDULED: {
        "cadence": list(DECISION_CADENCES),
        "definition": (
            "Every slot the frozen epoch schedules, enumerated from the epoch "
            "bounds and the cadence alone."
        ),
        "parent_universe": None,
    },
    UNIVERSE_DATA_VALID: {
        "cadence": list(DECISION_CADENCES),
        "definition": (
            "Scheduled slots where every required input for the consuming owner "
            "is present with available_at <= decision_time and the hard "
            "data-quality state is resolved for both tracks. A resolved hard "
            "failure is an owner output, not missing evidence."
        ),
        "parent_universe": UNIVERSE_ALL_SCHEDULED,
    },
    UNIVERSE_SETUP_EVALUABLE: {
        "cadence": [STRATEGY_DAILY_CADENCE],
        "definition": (
            "Data-valid daily slots where both tracks hold the complete input "
            "set of all four authoritative setup detectors."
        ),
        "parent_universe": UNIVERSE_DATA_VALID,
    },
    UNIVERSE_REGIME_EVALUABLE: {
        "cadence": [STRATEGY_DAILY_CADENCE],
        "definition": (
            "Data-valid daily slots where both tracks hold the complete required "
            "regime score, smoothing and classification inputs."
        ),
        "parent_universe": UNIVERSE_DATA_VALID,
    },
    UNIVERSE_ELIGIBILITY_EVALUABLE: {
        "cadence": [STRATEGY_DAILY_CADENCE],
        "definition": (
            "Setup-evaluable daily slots where both tracks have every input "
            "required by TRADE_ELIGIBILITY_COMPOSITE_OWNER_V1 and each produces "
            "a complete PERMITTED or NOT_PERMITTED result. Lifecycle state is "
            "an input to permission, not an exclusion: an open, closed or missed "
            "track is deterministically NOT_PERMITTED for a new entry."
        ),
        "parent_universe": UNIVERSE_SETUP_EVALUABLE,
    },
    UNIVERSE_TRADE_ELIGIBLE: {
        "cadence": [STRATEGY_DAILY_CADENCE],
        "definition": (
            "Eligibility-evaluable slots where the track under evaluation "
            "permits a new entry under its own owners."
        ),
        "parent_universe": UNIVERSE_ELIGIBILITY_EVALUABLE,
    },
    UNIVERSE_SIZING_EVALUABLE: {
        "cadence": [STRATEGY_DAILY_CADENCE],
        "definition": (
            "Slots that are trade-eligible in both tracks independently and "
            "where both authoritative INITIAL_POSITION_SIZE results are complete "
            "with a strictly positive position notional."
        ),
        "parent_universe": UNIVERSE_TRADE_ELIGIBLE,
    },
    UNIVERSE_POSITION_ACTIVE: {
        "cadence": list(DECISION_CADENCES),
        "definition": (
            "Slots where the track under evaluation holds an open position under "
            "the authoritative lifecycle owner."
        ),
        "parent_universe": UNIVERSE_ALL_SCHEDULED,
    },
    UNIVERSE_ACTION_EVALUABLE: {
        "cadence": [STRATEGY_DAILY_CADENCE],
        "definition": (
            "Data-valid daily slots where both tracks produce a complete "
            "deterministic ordered action envelope from "
            "TRADE_ACTION_COMPARISON_OWNER_V1, whether flat or in position."
        ),
        "parent_universe": UNIVERSE_DATA_VALID,
    },
    UNIVERSE_STOP_ACTIVE_SLOTS: {
        "cadence": [STOP_HOURLY_CADENCE],
        "definition": (
            "Hourly slots where the control-reference track carries an active "
            "stop on an open position. The immutable control stop identity is "
            "the common event anchor for both candidate and control outcomes."
        ),
        "parent_universe": UNIVERSE_ALL_SCHEDULED,
    },
    UNIVERSE_CROSS_MARKET_EVENTS: {
        "cadence": [STOP_HOURLY_CADENCE],
        "definition": (
            "Stop-active hourly slots the frozen classifier labels "
            "CROSS_MARKET_CONFIRMED_STOP_EVENT."
        ),
        "parent_universe": UNIVERSE_STOP_ACTIVE_SLOTS,
    },
    UNIVERSE_ISOLATED_VENUE_EVENTS: {
        "cadence": [STOP_HOURLY_CADENCE],
        "definition": (
            "Stop-active hourly slots the frozen classifier labels "
            "ISOLATED_VENUE_STOP_EVENT."
        ),
        "parent_universe": UNIVERSE_STOP_ACTIVE_SLOTS,
    },
    UNIVERSE_GAP_THROUGH_EVENTS: {
        "cadence": [STOP_HOURLY_CADENCE],
        "definition": (
            "Stop-active hourly slots the frozen classifier labels "
            "GAP_THROUGH_STOP_EVENT."
        ),
        "parent_universe": UNIVERSE_STOP_ACTIVE_SLOTS,
    },
}


# ===========================================================================
# 3. deterministic champion identity
# ===========================================================================
#
# Every entry is a versioned semantic identity a repository owner declares.
# "latest" appears nowhere: a collector that cannot reproduce this exact set
# must refuse rather than run.

CHAMPION_IDENTITY: dict[str, dict[str, Any]] = {
    "cost_slippage_model": {
        "owner": "btc_predictor.backtest.costs",
        "versions": {"cost_profile_policy": "REALISTIC_COST_MODEL_V1"},
    },
    "data_quality_gate": {
        "owner": "btc_predictor.signals.data_quality",
        "versions": {
            "blocked_actions": "ENTER,ADD",
            "recommendation_actions": "NO_TRADE,WATCH,ENTER,HOLD,ADD,TRIM,EXIT",
        },
    },
    "execution_model": {
        "owner": "btc_predictor.backtest.engine",
        "versions": {
            "backtest_end_policy": "MARK_OPEN_POSITION_NO_FORCED_EXIT_V1",
            "backtest_engine_policy": "EVENT_DRIVEN_BACKTEST_V1",
            "backtest_funding_policy": "BAR_CLOSE_PRE_EXECUTION_CARRY_V1",
            "backtest_nav_policy": "CASH_PLUS_MARKED_UNREALIZED_V1",
        },
    },
    "lifecycle_policy": {
        "owner": "btc_predictor.portfolio.state_machine",
        "versions": {
            "no_average_down": "NO_AVERAGE_DOWN_V1",
            "paper_lifecycle_persistence": "PAPER_LIFECYCLE_PERSISTENCE_V1",
            "position_state_machine": "PAPER_POSITION_STATE_MACHINE_V1",
            "position_transition_record": "PAPER_POSITION_TRANSITION_V1",
        },
    },
    "paper_accounting": {
        "owner": "btc_predictor.portfolio.accounting",
        "versions": {
            "paper_account": "PAPER_ACCOUNT_V1",
            "paper_trade_accounting": "PAPER_TRADE_ACCOUNTING_V1",
        },
    },
    "point_in_time_policy": {
        "owner": PIT_POLICY_OWNER,
        "versions": {"point_in_time": POINT_IN_TIME_POLICY_VERSION},
    },
    "price_source_policy": {
        "owner": "docs/policies/price_source_policy_v1.md",
        "versions": {
            "canonical_production_reference": "UNRESOLVED",
            "price_source_policy": "PRICE_SOURCE_POLICY_V1",
        },
    },
    "risk_policy": {
        "owner": "btc_predictor.risk",
        "versions": {
            "initial_position_size": "INITIAL_POSITION_SIZE_V1",
            "initial_stop": "INITIAL_STOP_V1",
            "reward_risk_filter": "REWARD_RISK_FILTER_V1",
            "risk_at_stop": "RISK_AT_STOP_V1",
            "risk_budget": "RISK_BUDGET_V1",
            "volatility_buffer": "VOLATILITY_BUFFER_V1",
        },
    },
    "rulebook": {
        "owner": "docs/strategy/bitcoin_swing_predictor_rulebook_v1_2.md",
        "versions": {"rulebook": "RULEBOOK_V1_2"},
    },
    "scoring_policy": {
        "owner": "btc_predictor.features.scoring_contracts",
        "versions": {
            "entry_action_classification": "ENTRY_ACTION_CLASSIFICATION_V1",
            "scoring_contracts": "SCORING_CONTRACTS_V1_2",
        },
    },
    "strategy_configuration": {
        "owner": "btc_predictor.config.strategy",
        "versions": {
            "config_version": "strategy_config_v2",
            "parameter_set_id": "default_phase1",
            "strategy_version": "swing_v1.2",
        },
    },
}

CHAMPION_IDENTITY_BINDING_RULE = (
    "A collector binds every declared version identity plus the SHA-256 of the "
    "resolved strategy configuration document. A repository artifact that "
    "carries a hash is bound by hash; one that carries only a versioned "
    "semantic definition is bound by that definition. 'latest' is refused."
)


# ===========================================================================
# 4. point-in-time input snapshot
# ===========================================================================
#
# Every row below is an existing Phase-1 owner that a decision at ``t`` already
# consumes.  Nothing is added because it might be useful later: the non-price
# families are exactly the ones the frozen BTC-048 feature contract
# ``POINT_IN_TIME_FEATURE_MATRIX_V2`` names, and the raw sources are the
# existing PIT tables that already carry ``observation_time``, ``available_at``,
# ``ingested_at``, ``provider``, ``source`` and (where the source revises)
# ``revision``.

PRICE_INPUT_SOURCES: dict[str, dict[str, Any]] = {
    "raw_provider_ohlcv": {
        "candidate_neutral": True,
        "consumers": [
            "btc_predictor.data.ohlcv.build_canonical_market_bars",
            "btc_predictor.research.reference_composite.build_composite_observation",
        ],
        "fields": ["timestamp", "open", "high", "low", "close", "volume"],
        "missing_policy": "EXPLICIT_GAP_NEVER_SPLICED",
        "normalization_owner": "btc_predictor.data.ohlcv.OhlcvBar",
        "pit_rule": "bar close <= decision_time and ingested_at <= decision_time",
        "provenance_fields": ["provider", "exchange", "symbol", "timeframe", "ingested_at"],
        "providers": list(_rc.REQUIRED_COMPOSITE_PROVIDER_IDS),
        "raw_table": "raw.btc_ohlcv",
        "revision_policy": "IMMUTABLE_NO_PROVIDER_REVISIONS",
        "timeframe": "1h",
        "units": "USD per BTC; volume in BTC",
    },
}

NON_PRICE_INPUT_SOURCES: dict[str, dict[str, Any]] = {
    "derivatives_funding": {
        "capture_state": "EXISTING_RAW_PIT_TABLE",
        "consuming_features": ["FUNDING_7D_AVG", "FUNDING_ZSCORE_180D", "FUNDING_HEALTH"],
        "fields": ["funding_rate", "funding_interval_hours"],
        "identity_fields": ["exchange", "symbol", "instrument", "provider"],
        "missing_policy": "EXPLICIT_STATUS_NO_ZERO_FILL",
        "normalization_owner": "btc_predictor.features.positioning",
        "pit_rule": PIT_RULE,
        "provenance_fields": ["observation_time", "available_at", "ingested_at", "source"],
        "raw_table": "raw.funding_rates",
        "revision_policy": "APPEND_ONLY_NO_DECLARED_REVISION_KEY",
        "units": "decimal funding rate per funding interval",
    },
    "derivatives_futures_basis": {
        "consuming_features": [
            "FUTURES_BASIS_AVG",
            "FUTURES_BASIS_ZSCORE_180D",
            "FUTURES_BASIS_HEALTH",
        ],
        "capture_state": "EXISTING_RAW_PIT_TABLE",
        "fields": ["basis_rate", "annualized_basis_rate", "expiry"],
        "identity_fields": ["exchange", "symbol", "instrument", "expiry", "provider"],
        "missing_policy": "EXPLICIT_STATUS_NO_ZERO_FILL",
        "normalization_owner": "btc_predictor.features.positioning",
        "pit_rule": PIT_RULE,
        "provenance_fields": ["observation_time", "available_at", "ingested_at", "source"],
        "raw_table": "raw.futures_basis",
        "revision_policy": "APPEND_ONLY_NO_DECLARED_REVISION_KEY",
        "units": "decimal basis versus spot; annualized decimal basis",
    },
    "derivatives_open_interest": {
        "capture_state": "EXISTING_RAW_PIT_TABLE",
        "consuming_features": [
            "OI_GROWTH_7D",
            "OI_GROWTH_ZSCORE_180D",
            "OI_GROWTH_HEALTH",
            "OI_INTENSITY",
            "OI_INTENSITY_PERCENTILE_180D",
        ],
        "fields": ["open_interest"],
        "identity_fields": ["exchange", "symbol", "instrument", "provider"],
        "missing_policy": "EXPLICIT_STATUS_NO_ZERO_FILL",
        "normalization_owner": "btc_predictor.features.positioning",
        "pit_rule": PIT_RULE,
        "provenance_fields": ["observation_time", "available_at", "ingested_at", "source"],
        "raw_table": "raw.open_interest",
        "revision_policy": "APPEND_ONLY_NO_DECLARED_REVISION_KEY",
        "units": "contracts or BTC as declared by the instrument",
    },
    "liquidations": {
        "available_at_field": "available_at",
        "capture_state": "EXISTING_RAW_PIT_TABLE",
        "consuming_features": [
            "ORDERLINESS_SCORE",
            "VOLATILITY_SCORE",
            "REGIME_SCORE",
            "REGIME_SMOOTHED_SCORE",
        ],
        "consumer_path": (
            "ORDERLINESS_SCORE -> liquidation_cascade -> "
            "liquidation_percentile; the same normalized input is consumed by "
            "STRESS and CAPITULATION market-state flags"
        ),
        "fields": ["timeframe", "side", "quantity", "quantity_unit", "notional_usd"],
        "identity_fields": ["exchange", "symbol", "timeframe", "side", "provider"],
        "ingested_at_field": "ingested_at",
        "missing_policy": (
            "EXPLICIT_STATUS_NO_ZERO_FILL_EMPTY_FEED_IS_DISTINCT_FROM_MISSING_FEED"
        ),
        "normalization_owner": (
            "btc_predictor.data.derivatives.aggregate_btc_derivatives_available_at "
            "+ btc_predictor.features.volatility.calculate_orderliness_score"
        ),
        "observation_time_field": "observation_time",
        "pit_rule": PIT_RULE,
        "provenance_fields": [
            "observation_time",
            "available_at",
            "ingested_at",
            "provider",
            "source",
        ],
        "raw_table": "raw.liquidations",
        "revision_policy": "APPEND_ONLY_NO_DECLARED_REVISION_KEY",
        "units": (
            "quantity in provider-declared quantity_unit; notional_usd in USD "
            "when reported"
        ),
    },
    "etf_flows": {
        "capture_state": "EXISTING_RAW_PIT_TABLE",
        "consuming_features": ["ETF_NORM_5D", "ETF_NORM_20D", "FLOW_ACCEL"],
        "fields": ["flow_usd", "aum_usd"],
        "identity_fields": ["fund", "provider"],
        "missing_policy": "EXPLICIT_STATUS_NO_ZERO_FILL",
        "normalization_owner": "btc_predictor.features.flow",
        "pit_rule": PIT_RULE,
        "provenance_fields": [
            "observation_date",
            "available_at",
            "ingested_at",
            "revision",
            "source",
        ],
        "raw_table": "raw.etf_flows",
        "revision_policy": "NEW_REVISION_ROW_PER_RESTATEMENT",
        "units": "USD",
    },
    "generic_series": {
        "capture_state": "EXISTING_RAW_PIT_TABLE",
        "consuming_features": [
            "OI_INTENSITY",
            "OI_INTENSITY_PERCENTILE_180D",
            "REGIME_SCORE",
            "REGIME_SMOOTHED_SCORE",
        ],
        "fields": ["value", "unit"],
        "identity_fields": ["series_id", "series_type", "provider"],
        "missing_policy": "EXPLICIT_STATUS_NO_ZERO_FILL",
        "normalization_owner": "btc_predictor.data.generic_series",
        "pit_rule": "available_at <= decision_time and observation_time <= decision_time",
        "provenance_fields": [
            "observation_time",
            "available_at",
            "ingested_at",
            "revision",
            "source",
        ],
        "raw_table": "raw.generic_series",
        "revision_policy": "NEW_REVISION_ROW_PER_RESTATEMENT",
        "units": "declared per series in the unit column",
    },
    "spot_perp_cvd": {
        "available_at_field": "available_at",
        "capture_state": "REQUIRES_NEW_COLLECTOR_IN_FIRST_COLLECTION_TICKET",
        "capture_state_reason": (
            "btc_predictor.features.flow.CvdObservation is a feature-layer "
            "boundary with no raw PIT table and no collector in this repository, "
            "so CVD_SPREAD cannot be reproduced from any persisted source today. "
            "The Phase-1 owner and its deterministic regression contract use "
            "aligned exact-hour common timestamps, matching the existing 1h "
            "spot/perp participation source path. The prospective contract freezes "
            "that cadence; it does not collect or fabricate the series."
        ),
        "cadence_derivation": {
            "accepted": "EXACT_UTC_HOURLY_OBSERVATIONS",
            "authority": [
                "btc_predictor.features.flow.CvdObservation.observation_time",
                "btc_predictor.features.flow.spot_perp_cvd_spread common_times",
                "btc_predictor.tests.test_flow_features hourly Phase-1 contract",
                "btc_predictor.features.flow.spot_perp_participation_from_rows 1h spot bars",
            ],
            "conflicting_repository_cadence": None,
            "unique": True,
        },
        "cadence_ambiguity": False,
        "consuming_features": ["CVD_SPREAD"],
        "fields": ["cvd_usd", "market_type"],
        "identity_fields": ["market_type", "provider"],
        "ingested_at_field": "ingested_at",
        "missing_policy": "EXPLICIT_STATUS_NO_ZERO_FILL",
        "normalization_owner": "btc_predictor.features.flow",
        "observation_cadence": "1h",
        "observation_time_alignment": "exact UTC hour",
        "observation_time_field": "observation_time",
        "pit_rule": PIT_RULE,
        "provenance_fields": ["observation_time", "available_at", "ingested_at", "source"],
        "raw_table": "research.prospective_source_input_snapshot (new capture)",
        "revision_policy": "APPEND_ONLY_NEW_REVISION_ROW_PER_RESTATEMENT",
        "units": "USD cumulative volume delta",
        "zscore_window_periods": _flow.spot_perp_cvd_spread.__kwdefaults__[
            "zscore_window_periods"
        ],
    },
    "spot_perp_volume_participation": {
        "capture_state": "EXISTING_RAW_PIT_TABLE",
        "consuming_features": ["SPOT_DOMINANCE"],
        "fields": ["volume", "volume_unit", "notional_usd"],
        "identity_fields": ["exchange", "symbol", "timeframe", "provider"],
        "missing_policy": "EXPLICIT_STATUS_NO_ZERO_FILL",
        "normalization_owner": "btc_predictor.features.flow",
        "pit_rule": PIT_RULE,
        "provenance_fields": ["observation_time", "available_at", "ingested_at", "source"],
        "raw_table": "raw.perp_volume",
        "revision_policy": "APPEND_ONLY_NO_DECLARED_REVISION_KEY",
        "units": "provider-declared volume unit; USD notional when reported",
    },
}

DERIVED_STATE_INPUTS: dict[str, str] = {
    "atr_and_volatility_buffers": "btc_predictor.risk.buffer.VOLATILITY_BUFFER_V1",
    "momentum_persistence": "btc_predictor.features.momentum",
    "regime_state": "btc_predictor.features.regime",
    "risk_budget_state": "btc_predictor.risk.budget.RISK_BUDGET_V1",
    "setup_state": "btc_predictor.features.setup",
    "structural_levels": "btc_predictor.levels",
    "structure_inputs": "btc_predictor.features.structure",
    "trend_inputs": "btc_predictor.features.trend",
    "volatility_inputs": "btc_predictor.features.volatility",
}

PORTFOLIO_STATE_INPUTS: tuple[str, ...] = (
    "cash_balance",
    "nav",
    "open_positions",
    "position_lifecycle_state",
    "previous_adds",
    "previous_stops",
    "previous_trims",
    "realized_pnl",
    "risk_at_stop",
    "tranches",
)

EXCLUDED_INPUT_FAMILIES: dict[str, str] = {
    "new_alpha_datasets": (
        "No dataset outside the frozen Phase-1 feature contract may enter the "
        "corpus; adding one is a PROSPECTIVE_INTEGRATION_CORPUS_V2 change."
    ),
}


# Mechanical closure from the frozen BTC-048 inventory to its raw/PIT inputs.
# Composite rows carry the transitive raw families of their component owners;
# a collector may not satisfy a row by persisting only the already-derived
# feature value.
_FEATURE_DEPENDENCIES: dict[str, dict[str, Any]] = {
    "TREND_SCORE": {"owner": "btc_predictor.features.trend.calculate_trend_score", "raw": ("raw_provider_ohlcv",)},
    "FLOW_SCORE": {"owner": "btc_predictor.features.flow.calculate_flow_score", "raw": ("etf_flows", "raw_provider_ohlcv", "spot_perp_cvd", "spot_perp_volume_participation")},
    "POSITIONING_SCORE": {"owner": "btc_predictor.features.positioning.calculate_positioning_score", "raw": ("derivatives_funding", "derivatives_futures_basis", "derivatives_open_interest")},
    "VOLATILITY_SCORE": {"owner": "btc_predictor.features.volatility.calculate_volatility_score", "raw": ("liquidations", "raw_provider_ohlcv")},
    "STRUCTURE_SCORE": {"owner": "btc_predictor.features.structure.calculate_structure_score", "raw": ("raw_provider_ohlcv",)},
    "REGIME_SCORE": {"owner": "btc_predictor.features.regime.calculate_regime_score", "raw": ("derivatives_funding", "derivatives_futures_basis", "derivatives_open_interest", "etf_flows", "generic_series", "liquidations", "raw_provider_ohlcv", "spot_perp_cvd", "spot_perp_volume_participation")},
    "REGIME_SMOOTHED_SCORE": {"owner": "btc_predictor.features.regime.calculate_regime_smoothing", "raw": ("derivatives_funding", "derivatives_futures_basis", "derivatives_open_interest", "etf_flows", "generic_series", "liquidations", "raw_provider_ohlcv", "spot_perp_cvd", "spot_perp_volume_participation")},
    "ORDERLINESS_SCORE": {"owner": "btc_predictor.features.volatility.calculate_orderliness_score", "raw": ("liquidations", "raw_provider_ohlcv")},
    "MOMENTUM_4W": {"owner": "btc_predictor.features.momentum.four_week_momentum_from_daily_bars", "raw": ("raw_provider_ohlcv",)},
    "MOMENTUM_12W": {"owner": "btc_predictor.features.momentum.twelve_week_momentum_from_daily_bars", "raw": ("raw_provider_ohlcv",)},
    "MA_DISTANCE_20W": {"owner": "btc_predictor.features.trend.twenty_week_ma_distance", "raw": ("raw_provider_ohlcv",)},
    "HIGH_DISTANCE_52W": {"owner": "btc_predictor.features.trend.fifty_two_week_high_distance", "raw": ("raw_provider_ohlcv",)},
    "ETF_NORM_5D": {"owner": "btc_predictor.features.flow.five_day_etf_flow", "raw": ("etf_flows",)},
    "ETF_NORM_20D": {"owner": "btc_predictor.features.flow.twenty_day_etf_flow", "raw": ("etf_flows",)},
    "FLOW_ACCEL": {"owner": "btc_predictor.features.flow.etf_flow_acceleration", "raw": ("etf_flows",)},
    "CVD_SPREAD": {"owner": "btc_predictor.features.flow.spot_perp_cvd_spread", "raw": ("spot_perp_cvd",)},
    "SPOT_DOMINANCE": {"owner": "btc_predictor.features.flow.spot_perp_participation_from_rows", "raw": ("raw_provider_ohlcv", "spot_perp_volume_participation")},
    "FUNDING_7D_AVG": {"owner": "btc_predictor.features.positioning.funding_features", "raw": ("derivatives_funding",)},
    "FUNDING_ZSCORE_180D": {"owner": "btc_predictor.features.positioning.funding_features", "raw": ("derivatives_funding",)},
    "FUNDING_HEALTH": {"owner": "btc_predictor.features.positioning.funding_health", "raw": ("derivatives_funding",)},
    "OI_GROWTH_7D": {"owner": "btc_predictor.features.positioning.open_interest_growth_features", "raw": ("derivatives_open_interest",)},
    "OI_GROWTH_ZSCORE_180D": {"owner": "btc_predictor.features.positioning.open_interest_growth_features", "raw": ("derivatives_open_interest",)},
    "OI_GROWTH_HEALTH": {"owner": "btc_predictor.features.positioning.open_interest_growth_health", "raw": ("derivatives_open_interest",)},
    "OI_INTENSITY": {"owner": "btc_predictor.features.positioning.open_interest_intensity", "raw": ("derivatives_open_interest", "generic_series")},
    "OI_INTENSITY_PERCENTILE_180D": {"owner": "btc_predictor.features.positioning.open_interest_intensity", "raw": ("derivatives_open_interest", "generic_series")},
    "FUTURES_BASIS_AVG": {"owner": "btc_predictor.features.positioning.futures_basis_health", "raw": ("derivatives_futures_basis",)},
    "FUTURES_BASIS_ZSCORE_180D": {"owner": "btc_predictor.features.positioning.futures_basis_health", "raw": ("derivatives_futures_basis",)},
    "FUTURES_BASIS_HEALTH": {"owner": "btc_predictor.features.positioning.futures_basis_health", "raw": ("derivatives_futures_basis",)},
    "RV_7": {"owner": "btc_predictor.features.volatility.realized_volatility_from_daily_bars", "raw": ("raw_provider_ohlcv",)},
    "RV_20": {"owner": "btc_predictor.features.volatility.realized_volatility_from_daily_bars", "raw": ("raw_provider_ohlcv",)},
    "RV_60": {"owner": "btc_predictor.features.volatility.realized_volatility_from_daily_bars", "raw": ("raw_provider_ohlcv",)},
    "VOL_COMPRESSION_RATIO": {"owner": "btc_predictor.features.volatility.volatility_compression_ratio", "raw": ("raw_provider_ohlcv",)},
    "VOL_PERCENTILE_2Y": {"owner": "btc_predictor.features.volatility.volatility_percentile", "raw": ("raw_provider_ohlcv",)},
}


def feature_input_coverage_contract() -> dict[str, Any]:
    """Prove one capture contract exists for every frozen feature dependency."""

    frozen = tuple(INITIAL_FEATURE_NAMES)
    if set(_FEATURE_DEPENDENCIES) != set(frozen) or len(_FEATURE_DEPENDENCIES) != len(frozen):
        missing = sorted(set(frozen) - set(_FEATURE_DEPENDENCIES))
        extra = sorted(set(_FEATURE_DEPENDENCIES) - set(frozen))
        raise ProspectiveCorpusError(
            f"frozen feature dependency closure moved; missing={missing}, extra={extra}"
        )
    capture_contracts = {**PRICE_INPUT_SOURCES, **NON_PRICE_INPUT_SOURCES}
    rows: dict[str, Any] = {}
    used_families: set[str] = set()
    for feature in frozen:
        dependency = _FEATURE_DEPENDENCIES[feature]
        if not isinstance(dependency["owner"], str) or not dependency["owner"]:
            raise ProspectiveCorpusError(
                f"{feature} lacks an explicit deterministic feature owner"
            )
        raw_families = tuple(dependency["raw"])
        absent = tuple(family for family in raw_families if family not in capture_contracts)
        if absent:
            raise ProspectiveCorpusError(
                f"{feature} has required raw families without a capture contract: {absent}"
            )
        if len(raw_families) != len(set(raw_families)):
            raise ProspectiveCorpusError(f"{feature} repeats a raw input family")
        used_families.update(raw_families)
        rows[feature] = {
            "deterministic_feature_owner": dependency["owner"],
            "raw_input_families": list(raw_families),
            "capture_contract_count_by_family": {family: 1 for family in raw_families},
            "future_information_reconstruction_permitted": False,
            "missing_value_default": None,
            "zero_fill_permitted": False,
        }
    unused_contracts = set(capture_contracts) - used_families
    if unused_contracts:
        raise ProspectiveCorpusError(
            f"capture contracts are not traced from INITIAL_FEATURE_NAMES: "
            f"{sorted(unused_contracts)}"
        )
    payload = {
        "all_frozen_features_covered": True,
        "capture_contracts": {
            family: {
                "capture_state": contract.get("capture_state", "EXISTING_RAW_PIT_TABLE"),
                "raw_table": contract["raw_table"],
            }
            for family, contract in sorted(capture_contracts.items())
        },
        "feature_count": len(rows),
        "feature_inventory": list(frozen),
        "feature_inventory_owner": "btc_predictor.research.feature_matrix.INITIAL_FEATURE_NAMES",
        "protocol_version": PROTOCOL_VERSION,
        "required_raw_input_families": sorted(used_families),
        "rows": rows,
        "schema_version": "PROSPECTIVE_FEATURE_INPUT_COVERAGE_V1",
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def _warmup_row(
    owner: str,
    lookback: str,
    semantics: str,
    minimum_observations: str,
    initialization: str,
    effective: str,
) -> dict[str, str]:
    return {
        "owner": owner,
        "lookback_or_window": lookback,
        "calendar_or_session_semantics": semantics,
        "minimum_observations": minimum_observations,
        "additional_initialization_requirement": initialization,
        "effective_warmup": effective,
    }


def warmup_history_contract() -> dict[str, Any]:
    """Derive every frozen feature's pre-evaluation warmup from its owner."""

    cvd_window = _flow.spot_perp_cvd_spread.__kwdefaults__["zscore_window_periods"]
    volume_growth = _flow.spot_perp_participation.__kwdefaults__["growth_window_periods"]
    volume_zscore = _flow.spot_perp_participation.__kwdefaults__["zscore_window_periods"]
    funding_window = _positioning.DEFAULT_FUNDING_ZSCORE_WINDOW_DAYS
    basis_window = _positioning.DEFAULT_FUTURES_BASIS_ZSCORE_WINDOW_DAYS
    oi_window = _positioning.DEFAULT_OI_GROWTH_ZSCORE_WINDOW_DAYS
    oi_growth = _positioning.DEFAULT_OI_GROWTH_WINDOW_DAYS
    percentile_window = _volatility.DEFAULT_VOLATILITY_PERCENTILE_WINDOW_DAYS
    percentile_source_window = 20
    rows = {
        "TREND_SCORE": _warmup_row("btc_predictor.features.trend.calculate_trend_score", f"max({_trend.FIFTY_TWO_WEEK_HIGH_DISTANCE_LOOKBACK_WEEKS} weekly, {_trend.TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS} weekly, {_momentum.TWELVE_WEEK_MOMENTUM_LOOKBACK_DAYS} daily)", "canonical weekly/daily sessions", "52 weekly observations plus component inputs", "weekly structure must also be complete", "52 canonical weekly sessions"),
        "FLOW_SCORE": _warmup_row("btc_predictor.features.flow.calculate_flow_score", "max(20 ETF publication days, 21 hourly CVD observations, 30 hourly participation observations)", "ETF publication days and exact UTC hours", "all selected full-flow components complete", "5-period volume growth needs two windows before 20 prior growth values", "20 ETF publication days and 30 exact-hour spot/perp observations"),
        "POSITIONING_SCORE": _warmup_row("btc_predictor.features.positioning.calculate_positioning_score", f"max({funding_window}d funding, {basis_window}d basis, {oi_window}d OI growth)", "trailing elapsed UTC days", "30 historical observations per z-score/percentile owner", f"OI growth needs an earlier {oi_growth}d comparison", f"{oi_window + oi_growth} calendar days for OI; {funding_window}d funding; {basis_window}d basis"),
        "VOLATILITY_SCORE": _warmup_row("btc_predictor.features.volatility.calculate_volatility_score", f"{percentile_window}d volatility-percentile history", "canonical daily sessions", f"{_volatility.DEFAULT_VOLATILITY_PERCENTILE_MIN_OBSERVATIONS} prior RV_20 results", f"each historical RV_20 needs {percentile_source_window} earlier daily returns", f"{percentile_window + percentile_source_window} calendar days"),
        "STRUCTURE_SCORE": _warmup_row("btc_predictor.features.structure.calculate_structure_score", "current authoritative structure/level/RR inputs", "owner-supplied PIT structures", "one complete input vector", "structural level owners must be complete", "no extra rolling window at this owner"),
        "REGIME_SCORE": _warmup_row("btc_predictor.features.regime.calculate_regime_score", "transitive maximum of trend, flow, positioning, volatility", "mixed canonical sessions", "all selected regime components complete", "full model additionally requires PIT macro/onchain/liquidity inputs", f"{percentile_window + percentile_source_window} calendar days"),
        "REGIME_SMOOTHED_SCORE": _warmup_row("btc_predictor.features.regime.calculate_regime_smoothing", "current regime score and optional prior smoothed score", "strategy-daily decisions", "1 complete current regime score", "the owner deterministically initializes a missing previous smoothed score from the current score and records REGIME_SMOOTHING_PREVIOUS_SCORE_MISSING", f"{percentile_window + percentile_source_window} calendar days"),
        "ORDERLINESS_SCORE": _warmup_row("btc_predictor.features.volatility.calculate_orderliness_score", "current range/downside/liquidation/volatility percentile inputs", "strategy-daily PIT inputs", "one complete input vector", "upstream percentile owners and raw liquidation history must be complete; no window is invented here", "no extra rolling window at this owner"),
        "MOMENTUM_4W": _warmup_row("btc_predictor.features.momentum.four_week_momentum_from_daily_bars", f"{_momentum.FOUR_WEEK_MOMENTUM_LOOKBACK_DAYS} daily periods", "canonical daily sessions", f"{_momentum.FOUR_WEEK_MOMENTUM_LOOKBACK_DAYS + 1} closes", "current plus lookback close", f"{_momentum.FOUR_WEEK_MOMENTUM_LOOKBACK_DAYS} calendar days"),
        "MOMENTUM_12W": _warmup_row("btc_predictor.features.momentum.twelve_week_momentum_from_daily_bars", f"{_momentum.TWELVE_WEEK_MOMENTUM_LOOKBACK_DAYS} daily periods", "canonical daily sessions", f"{_momentum.TWELVE_WEEK_MOMENTUM_LOOKBACK_DAYS + 1} closes", "current plus lookback close", f"{_momentum.TWELVE_WEEK_MOMENTUM_LOOKBACK_DAYS} calendar days"),
        "MA_DISTANCE_20W": _warmup_row("btc_predictor.features.trend.twenty_week_ma_distance", f"{_trend.TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS} weekly periods", "canonical weekly sessions", f"{_trend.TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS} closes", "none", f"{_trend.TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS} canonical weekly sessions"),
        "HIGH_DISTANCE_52W": _warmup_row("btc_predictor.features.trend.fifty_two_week_high_distance", f"{_trend.FIFTY_TWO_WEEK_HIGH_DISTANCE_LOOKBACK_WEEKS} weekly periods", "canonical weekly sessions", f"{_trend.FIFTY_TWO_WEEK_HIGH_DISTANCE_LOOKBACK_WEEKS} highs/closes", "none", f"{_trend.FIFTY_TWO_WEEK_HIGH_DISTANCE_LOOKBACK_WEEKS} canonical weekly sessions"),
        "ETF_NORM_5D": _warmup_row("btc_predictor.features.flow.five_day_etf_flow", f"{_flow.FIVE_DAY_ETF_FLOW_WINDOW_DAYS} publication days", "configured ETF publication calendar", "5 complete fund-universe publication days", "latest PIT AUM required", "5 publication days"),
        "ETF_NORM_20D": _warmup_row("btc_predictor.features.flow.twenty_day_etf_flow", f"{_flow.TWENTY_DAY_ETF_FLOW_WINDOW_DAYS} publication days", "configured ETF publication calendar", "20 complete fund-universe publication days", "latest PIT AUM required", "20 publication days"),
        "FLOW_ACCEL": _warmup_row("btc_predictor.features.flow.etf_flow_acceleration", "5d and 20d ETF normalized windows", "configured ETF publication calendar", "both source windows complete", "none beyond source windows", "20 publication days"),
        "CVD_SPREAD": _warmup_row("btc_predictor.features.flow.spot_perp_cvd_spread", f"{cvd_window} prior periods", "exact UTC hourly common spot/perp timestamps", f"{cvd_window} prior plus 1 current common observation", "z-score excludes current observation from history", f"{cvd_window + 1} consecutive hourly common observations"),
        "SPOT_DOMINANCE": _warmup_row("btc_predictor.features.flow.spot_perp_participation_from_rows", f"{volume_growth}-period current/prior growth windows plus {volume_zscore} prior growth values", "exact UTC hourly common spot/perp timestamps", f"{volume_growth * 2 + volume_zscore} common observations", "growth series initializes after two equal windows", f"{volume_growth * 2 + volume_zscore} consecutive hourly common observations"),
        "FUNDING_7D_AVG": _warmup_row("btc_predictor.features.positioning.funding_health", f"{_positioning.DEFAULT_FUNDING_AVERAGE_WINDOW_DAYS}d", "trailing elapsed UTC days", "at least one available observation; owner records count", "none", f"{_positioning.DEFAULT_FUNDING_AVERAGE_WINDOW_DAYS} calendar days"),
        "FUNDING_ZSCORE_180D": _warmup_row("btc_predictor.features.positioning.funding_health", f"{funding_window}d", "prior observations in trailing elapsed UTC window", f"{_positioning.DEFAULT_FUNDING_MIN_ZSCORE_OBSERVATIONS} prior observations", "current observation excluded from history", f"{funding_window} calendar days"),
        "FUNDING_HEALTH": _warmup_row("btc_predictor.features.positioning.funding_health", "FUNDING_ZSCORE_180D", "inherits funding z-score", "one complete funding z-score", "none", f"{funding_window} calendar days"),
        "OI_GROWTH_7D": _warmup_row("btc_predictor.features.positioning.open_interest_growth_health", f"{oi_growth}d", "elapsed UTC comparison", "current and prior comparable observations", "prior OI observation required", f"{oi_growth} calendar days"),
        "OI_GROWTH_ZSCORE_180D": _warmup_row("btc_predictor.features.positioning.open_interest_growth_health", f"{oi_window}d of growth results", "prior growth observations in trailing elapsed UTC window", f"{_positioning.DEFAULT_OI_GROWTH_MIN_ZSCORE_OBSERVATIONS} prior growth observations", f"earliest growth needs an earlier {oi_growth}d OI observation", f"{oi_window + oi_growth} calendar days"),
        "OI_GROWTH_HEALTH": _warmup_row("btc_predictor.features.positioning.open_interest_growth_health", "OI_GROWTH_ZSCORE_180D", "inherits OI-growth z-score", "one complete OI-growth z-score", "none", f"{oi_window + oi_growth} calendar days"),
        "OI_INTENSITY": _warmup_row("btc_predictor.features.positioning.open_interest_intensity", "current OI and spot market-cap/price input", "same PIT decision", "one complete input pair", "none", "current decision inputs"),
        "OI_INTENSITY_PERCENTILE_180D": _warmup_row("btc_predictor.features.positioning.open_interest_intensity", f"{_positioning.DEFAULT_OI_INTENSITY_PERCENTILE_WINDOW_DAYS}d", "prior observations in trailing elapsed UTC window", f"{_positioning.DEFAULT_OI_INTENSITY_MIN_PERCENTILE_OBSERVATIONS} prior observations", "current intensity required", f"{_positioning.DEFAULT_OI_INTENSITY_PERCENTILE_WINDOW_DAYS} calendar days"),
        "FUTURES_BASIS_AVG": _warmup_row("btc_predictor.features.positioning.futures_basis_health", "current PIT basis observations", "same PIT decision", "at least one available observation", "none", "current decision inputs"),
        "FUTURES_BASIS_ZSCORE_180D": _warmup_row("btc_predictor.features.positioning.futures_basis_health", f"{basis_window}d", "prior observations in trailing elapsed UTC window", f"{_positioning.DEFAULT_FUTURES_BASIS_MIN_ZSCORE_OBSERVATIONS} prior observations", "current observation excluded from history", f"{basis_window} calendar days"),
        "FUTURES_BASIS_HEALTH": _warmup_row("btc_predictor.features.positioning.futures_basis_health", "FUTURES_BASIS_ZSCORE_180D", "inherits basis z-score", "one complete basis z-score", "none", f"{basis_window} calendar days"),
        "RV_7": _warmup_row("btc_predictor.features.volatility.realized_volatility_from_daily_bars", "7 daily returns", "gap-aware canonical daily sessions", "8 closes", "first return needs previous close", "7 calendar-day intervals"),
        "RV_20": _warmup_row("btc_predictor.features.volatility.realized_volatility_from_daily_bars", "20 daily returns", "gap-aware canonical daily sessions", "21 closes", "first return needs previous close", "20 calendar-day intervals"),
        "RV_60": _warmup_row("btc_predictor.features.volatility.realized_volatility_from_daily_bars", "60 daily returns", "gap-aware canonical daily sessions", "61 closes", "first return needs previous close", "60 calendar-day intervals"),
        "VOL_COMPRESSION_RATIO": _warmup_row("btc_predictor.features.volatility.volatility_compression_ratio", "RV_7 and RV_20", "inherits canonical daily sessions", "both realized-volatility inputs complete", "none beyond RV_20", "20 calendar-day intervals"),
        "VOL_PERCENTILE_2Y": _warmup_row("btc_predictor.features.volatility.volatility_percentile", f"{percentile_window}d trailing RV_20 window", "canonical daily sessions", f"current plus at least {_volatility.DEFAULT_VOLATILITY_PERCENTILE_MIN_OBSERVATIONS} prior RV_20 results", f"earliest retained RV_20 needs {percentile_source_window} prior daily returns", f"{percentile_window + percentile_source_window} calendar days"),
    }
    if set(rows) != set(INITIAL_FEATURE_NAMES):
        raise ProspectiveCorpusError("warmup rows must exactly cover INITIAL_FEATURE_NAMES")
    payload = {
        "all_feature_warmups_frozen": True,
        "evaluable_slot_rule": (
            "WARMUP_HISTORY_COMPLETE is true only when every frozen feature's "
            "owner-specific observation count, session/calendar rule and "
            "initialization requirement is satisfied from PIT inputs."
        ),
        "feature_inventory_owner": "btc_predictor.research.feature_matrix.INITIAL_FEATURE_NAMES",
        "longest_required_warmup": f"{percentile_window + percentile_source_window} calendar days",
        "pre_warmup_behavior": (
            "Raw PIT capture may later build history only after both the corpus "
            "protocol and sufficiency-governance hashes plus POSTP1-004 have "
            "passed their required reviews. Until WARMUP_HISTORY_COMPLETE, a "
            "slot is WARMUP_HISTORY_INCOMPLETE and enters no evaluable metric universe."
        ),
        "protocol_version": PROTOCOL_VERSION,
        "rows": rows,
        "schema_version": "PROSPECTIVE_WARMUP_HISTORY_V1",
        "state_name": "WARMUP_HISTORY_COMPLETE",
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


# ===========================================================================
# 5. reference variants
# ===========================================================================
#
# No production reference candidate legitimately exists: PRICE_SOURCE_POLICY_V1
# leaves the canonical production reference UNRESOLVED and the V5 assessment
# records MEDIAN_OHLC_V2 as never constructed or evaluated.  Naming one here
# would invent an authority.  So the corpus freezes the *slot* and its rules and
# stays candidate-neutral: the raw layer persists enough immutable per-provider
# observation to evaluate any authorized reference deterministically, and the
# two identities are supplied later by a separately frozen evaluation contract.

CONTROL_REFERENCE_ROLE = "CONTROL_REFERENCE"
CANDIDATE_REFERENCE_ROLE = "CANDIDATE_REFERENCE"
REFERENCE_ROLES = (CANDIDATE_REFERENCE_ROLE, CONTROL_REFERENCE_ROLE)

REFERENCE_IDENTITY_SOURCE = "PROSPECTIVE_INTEGRATION_EVALUATION_CONTRACT_V1"
REFERENCE_IDENTITY_STATE = "SUPPLIED_BY_SEPARATELY_FROZEN_EVALUATION_CONTRACT"
REFERENCE_IDENTITY_REQUIREMENTS = (
    "Both roles must be deterministic functions of the persisted raw provider "
    "observations available at the same decision_time.",
    "Both identities must be frozen and hashed before the first derived "
    "evaluation record binds them.",
    "Neither identity may be chosen, changed, or re-selected after any Stage-B "
    "aggregate has been observed.",
    "The raw corpus never stores either identity, so a later authorized "
    "candidate is evaluated without rewriting one historical observation.",
)

# ===========================================================================
# 6. the two deterministic portfolio tracks
# ===========================================================================

CONTROL_TRACK = "CONTROL_REFERENCE_TRACK"
CANDIDATE_TRACK = "CANDIDATE_REFERENCE_TRACK"
PORTFOLIO_TRACKS = (CANDIDATE_TRACK, CONTROL_TRACK)

INITIAL_PORTFOLIO_STATE: dict[str, Any] = {
    "cash_balance": "1000000",
    "currency": "USD",
    "nav": "1000000",
    "open_positions": [],
    "pending_orders": [],
    "previous_adds": [],
    "previous_stops": [],
    "previous_trims": [],
    "realized_pnl": "0",
    "state_version": "PROSPECTIVE_INTEGRATION_INITIAL_PORTFOLIO_STATE_V1",
}
INITIAL_PORTFOLIO_STATE_RATIONALE = (
    "A clean prospective experiment: flat, no pending orders, and one fixed "
    "nominal research NAV. No repository authority requires a different opening "
    "state, and a non-flat opening would import an unowned position history into "
    "measurements about reference sensitivity."
)

DIVERGENCE_POLICY = "ALLOW_NATURAL_STATE_DIVERGENCE"
RESYNCHRONIZATION_POLICY = "FORBIDDEN"
SHARED_EXOGENOUS_INPUT_RULE = (
    "Every point-in-time input except the reference-price construction under "
    "test is byte-identical between the two tracks at the same decision_time. A "
    "run that cannot demonstrate identity for a shared input must record that "
    "slot NOT_COMPARABLE with EXOGENOUS_INPUT_DIVERGED rather than compare it."
)
SHARED_EXOGENOUS_INPUT_FAMILIES = tuple(
    sorted(
        tuple(NON_PRICE_INPUT_SOURCES)
        + (
            "clock",
            "cost_slippage_model",
            "execution_model",
            "fees",
            "lifecycle_policy",
            "risk_limits",
            "scoring_policy",
            "strategy_configuration",
            "volatility_configuration",
        )
    )
)
EXOGENOUS_DIVERGENCE_REASON = "EXOGENOUS_INPUT_DIVERGED"

DIVERGENCE_EVIDENCE_FIELDS = (
    "divergence_cause_metric",
    "divergence_cause_reason_codes",
    "first_divergence_decision_time",
    "later_comparison_state",
    "state_digest_candidate",
    "state_digest_control",
)


# ===========================================================================
# 7. mechanical stop-event taxonomy and its deterministic classifier
# ===========================================================================
#
# The historical repository carried five hand-picked development timestamps.
# Nothing here selects a timestamp: an event is whatever the classifier labels
# from the raw provider observations of one canonical hourly slot and the
# control track's active stop.

STOP_EVENT_CLASSIFIER_VERSION = "PROSPECTIVE_STOP_EVENT_CLASSIFIER_V1"
STOP_EVENT_CLASSIFIER_OWNER = (
    "btc_predictor.research.prospective_integration_corpus.classify_stop_event"
)
STOP_EVENT_UNIVERSE_ANCHOR = "CONTROL_REFERENCE_TRACK_ACTIVE_STOP"
PRIOR_OBSERVABLE_OWNER = "PREVIOUS_CONTIGUOUS_REQUIRED_PROVIDER_CONSENSUS_CLOSE_V1"
PRIOR_OBSERVABLE_MAXIMUM_GAP = timedelta(hours=1)

REQUIRED_PROVIDER_IDS = _rc.REQUIRED_COMPOSITE_PROVIDER_IDS
PROVIDER_QUORUM = _v2.V2_MINIMUM_PROVIDER_COUNT
CONFIRMATION_QUORUM = _v2.V2_MINIMUM_PROVIDER_COUNT

LONG_DIRECTION = "long"
SHORT_DIRECTION = "short"
STOP_DIRECTIONS = (LONG_DIRECTION, SHORT_DIRECTION)
STOP_RELEVANT_FIELD = {LONG_DIRECTION: "low", SHORT_DIRECTION: "high"}

EVENT_CROSS_MARKET = "CROSS_MARKET_CONFIRMED_STOP_EVENT"
EVENT_ISOLATED_VENUE = "ISOLATED_VENUE_STOP_EVENT"
EVENT_NONE = "NO_STOP_EVENT"
EVENT_NOT_CLASSIFIABLE = "NOT_CLASSIFIABLE"
STOP_EVENT_CLASSIFICATIONS = (
    EVENT_CROSS_MARKET,
    EVENT_ISOLATED_VENUE,
    EVENT_NONE,
    EVENT_NOT_CLASSIFIABLE,
)

GAP_THROUGH_EVENT = "GAP_THROUGH_STOP_EVENT"
GAP_THROUGH_NOT_PRESENT = "NOT_GAP_THROUGH"
GAP_THROUGH_NOT_EVALUABLE = "NOT_EVALUABLE_PRIOR_CONSENSUS_UNAVAILABLE"
GAP_THROUGH_STATES = (
    GAP_THROUGH_EVENT,
    GAP_THROUGH_NOT_EVALUABLE,
    GAP_THROUGH_NOT_PRESENT,
)

STOP_OUTCOME_TRIGGERED = "TRIGGERED"
STOP_OUTCOME_NOT_TRIGGERED = "NOT_TRIGGERED"
STOP_OUTCOME_UNDEFINED = "UNDEFINED"
STOP_OUTCOMES = (
    STOP_OUTCOME_NOT_TRIGGERED,
    STOP_OUTCOME_TRIGGERED,
    STOP_OUTCOME_UNDEFINED,
)

CLASSIFICATION_PRECEDENCE = (
    "A slot with fewer than PROVIDER_QUORUM available required providers is "
    "NOT_CLASSIFIABLE_INSUFFICIENT_PROVIDER_QUORUM and enters no event "
    "denominator.",
    "Otherwise, CROSS_MARKET_CONFIRMED_STOP_EVENT when at least "
    "CONFIRMATION_QUORUM available required providers reach the stop-relevant "
    "extreme.",
    "Otherwise, any missing required provider makes the slot NOT_CLASSIFIABLE: "
    "the absent venue could change NO_STOP_EVENT into ISOLATED_VENUE_STOP_EVENT "
    "or could prevent isolation from being established.",
    "Otherwise, ISOLATED_VENUE_STOP_EVENT only when exactly one available "
    "required provider reaches it and at least CONFIRMATION_QUORUM available "
    "required providers do not reach it. Isolation is observed, never inferred "
    "through a missing provider.",
    "A one-touch/one-non-touch/one-missing slot is NOT_CLASSIFIABLE because the "
    "missing venue could have confirmed the touch.",
    "Otherwise NO_STOP_EVENT. CROSS_MARKET_CONFIRMED_STOP_EVENT and "
    "ISOLATED_VENUE_STOP_EVENT are mutually exclusive by construction.",
    "GAP_THROUGH_STOP_EVENT is orthogonal and declared separately: it describes "
    "how the stop was crossed, not how many venues reached it, so a slot may "
    "carry both labels and neither universe silently drops the other's event.",
)

GAP_THROUGH_DERIVATION = {
    "accepted_interpretation": PRIOR_OBSERVABLE_OWNER,
    "rows": [
        {
            "candidate_interpretation": "immediately prior required-provider-consensus hourly close",
            "supporting_authority": [
                "PRICE_SOURCE_POLICY_V1: provider outages remain explicit gaps and fallback splicing is prohibited",
                "btc_predictor.portfolio.stop_execution: a gap is decided by the next eligible bar open",
                "btc_predictor.data.ohlcv.CANONICAL_BTC_MARKET_BAR_SESSION: source bars are exact UTC hours",
                "existing stop-event comparison basis: raw required-provider consensus",
            ],
            "conflicting_authority": None,
            "candidate_neutral": True,
            "track_dependent": False,
            "pit_safe": True,
            "unique": True,
            "accepted": True,
        },
        {
            "candidate_interpretation": "previous available provider-consensus close across an outage",
            "supporting_authority": "failed protocol lineage only",
            "conflicting_authority": "PRICE_SOURCE_POLICY_V1 forbids splicing across explicit provider gaps",
            "candidate_neutral": True,
            "track_dependent": False,
            "pit_safe": True,
            "unique": False,
            "accepted": False,
        },
        {
            "candidate_interpretation": "previous candidate reference close",
            "supporting_authority": None,
            "conflicting_authority": "would let the measured candidate define event-universe membership",
            "candidate_neutral": False,
            "track_dependent": True,
            "pit_safe": True,
            "unique": False,
            "accepted": False,
        },
        {
            "candidate_interpretation": "previous control reference close",
            "supporting_authority": "control is the comparison baseline",
            "conflicting_authority": "the historical stop metrics compare a candidate with raw venue consensus; the event taxonomy is candidate-neutral raw evidence",
            "candidate_neutral": True,
            "track_dependent": True,
            "pit_safe": True,
            "unique": False,
            "accepted": False,
        },
        {
            "candidate_interpretation": "previous session open",
            "supporting_authority": None,
            "conflicting_authority": "the execution owner uses the current bar open and supplies no previous-open concept",
            "candidate_neutral": True,
            "track_dependent": False,
            "pit_safe": True,
            "unique": False,
            "accepted": False,
        },
    ],
    "maximum_staleness_seconds": int(PRIOR_OBSERVABLE_MAXIMUM_GAP.total_seconds()),
    "missing_session_semantics": "NOT_EVALUABLE_PRIOR_CONSENSUS_UNAVAILABLE",
    "prior_timestamp_identity": "current canonical hourly observation_time minus exactly one hour",
    "source_identity": "median close over the available required raw providers at the exact prior hour, requiring PROVIDER_QUORUM",
    "unique_interpretation": True,
}

STOP_EVENT_UNIVERSE_DERIVATION = {
    "accepted_interpretation": STOP_EVENT_UNIVERSE_ANCHOR,
    "invariance_principle": (
        "Candidate performance cannot reduce the set of events on which the "
        "candidate is judged merely by altering its own entry, exit or stop state."
    ),
    "rows": [
        {"interpretation": "candidate-track-specific stop", "authority_support": "failed protocol lineage only", "bias_or_provenance_consequence": "candidate state can shrink its own denominator", "accepted": False, "reason": "violates outcome-exogenous universe invariance"},
        {"interpretation": "control-track-specific stop", "authority_support": "historical candidate-versus-control comparison basis and the authoritative control lifecycle", "bias_or_provenance_consequence": "baseline state fixes the event anchor independently of candidate outcomes", "accepted": True, "reason": "the comparison baseline supplies the only pre-existing exogenous stop identity"},
        {"interpretation": "shared pre-divergence stop", "authority_support": "both tracks start from one state", "bias_or_provenance_consequence": "undefined after later entries or stop advances", "accepted": False, "reason": "cannot cover the natural-divergence epoch without inventing a synthetic stop"},
        {"interpretation": "joint/both-track stop universe", "authority_support": None, "bias_or_provenance_consequence": "drops events whenever one track is flat or lacks a stop", "accepted": False, "reason": "candidate behavior can remove events"},
        {"interpretation": "union of track-specific stop events", "authority_support": None, "bias_or_provenance_consequence": "candidate can add endogenous events and incompatible stop levels", "accepted": False, "reason": "no repository owner defines how two stop levels form one event"},
        {"interpretation": "other existing-authority interpretation", "authority_support": None, "bias_or_provenance_consequence": "none found in the full owner trace", "accepted": False, "reason": "no additional authoritative anchor exists"},
    ],
    "unique_interpretation": True,
}

POST_DIVERGENCE_STOP_SEMANTICS = {
    "active_stop_identity": "control lifecycle active stop plus its transition/source identity",
    "candidate_position_state": "persisted on every classified slot but does not control membership",
    "comparison_disposition": (
        "If the control track has an active stop, raw venue events are classified "
        "at that stop and candidate/control reference outcomes remain comparable "
        "even when candidate portfolio state differs. If the control track has no "
        "active stop or its identity is unavailable, the slot is NOT_COMPARABLE "
        "and enters no stop-event denominator."
    ),
    "control_position_state": "must be open with a valid active stop",
    "first_divergence": "first_divergence_decision_time from portfolio_track_contract",
    "hidden_denominator_shrinkage_permitted": False,
}


def assert_required_semantics_unambiguous() -> None:
    """Fail closed if any bounded correction cannot be uniquely derived."""

    cvd_derivation = NON_PRICE_INPUT_SOURCES["spot_perp_cvd"][
        "cadence_derivation"
    ]
    if (
        cvd_derivation["unique"] is not True
        or cvd_derivation["accepted"] != "EXACT_UTC_HOURLY_OBSERVATIONS"
    ):
        raise ProspectiveCorpusError(AMBIGUOUS_FROZEN_INPUT_CLASSIFICATION)
    if GAP_THROUGH_DERIVATION["unique_interpretation"] is not True:
        raise ProspectiveCorpusError(AMBIGUOUS_FROZEN_METRIC_CLASSIFICATION)
    if STOP_EVENT_UNIVERSE_DERIVATION["unique_interpretation"] is not True:
        raise ProspectiveCorpusError(AMBIGUOUS_FROZEN_METRIC_CLASSIFICATION)


@dataclass(frozen=True)
class ProviderObservation:
    """One required provider's canonical hourly bar for one slot."""

    provider_id: str
    observation_time: datetime
    available_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True)
class StopEvaluationSlot:
    """One hourly stop-evaluation slot anchored to the control-track stop."""

    observation_time: datetime
    track: str
    direction: str
    active_stop: Decimal
    active_stop_identity: str
    control_position_state: str
    candidate_position_state: str
    providers: tuple[ProviderObservation, ...]
    prior_providers: tuple[ProviderObservation, ...] = ()
    first_divergence_decision_time: datetime | None = None


def _decimal(value: Any, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    raise ProspectiveCorpusError(f"{field_name} must be an exact Decimal")


def _median(values: Sequence[Decimal]) -> Decimal:
    """Exact median inside this protocol's own context.

    ``statistics.median`` resolves the even-count midpoint in whatever ambient
    ``Decimal`` context the caller happens to hold, so it is not used here.
    """

    if not values:
        raise ProspectiveCorpusError("a median requires at least one value")
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middle]
    with localcontext(_CONTEXT):
        return (ordered[middle - 1] + ordered[middle]) / Decimal(2)


def nearest_rank_percentile(values: Sequence[Decimal], probability: Decimal) -> Decimal:
    """The authoritative BTC-019 percentile: nearest rank, rounded up.

    The failed sealed-evidence builder interpolated instead and flipped a hard
    gate on the boundary vectors; the repository's owners
    (``reference_composite_empirical._percentile`` and
    ``price_source_policy._nearest_rank_percentile``) both use nearest rank, and
    frozen V4 names it explicitly for the p95 gate family.
    """

    if not values:
        raise ProspectiveCorpusError("a percentile requires at least one value")
    ordered = sorted(values)
    with localcontext(_CONTEXT) as context:
        rank = int(
            (probability * Decimal(len(ordered))).to_integral_value(
                rounding=ROUND_CEILING,
                context=context,
            )
        )
    return ordered[max(rank - 1, 0)]


def _validate_slot(slot: StopEvaluationSlot) -> datetime:
    if not isinstance(slot, StopEvaluationSlot):
        raise ProspectiveCorpusError("a stop classification requires a StopEvaluationSlot")
    if slot.track != CONTROL_TRACK:
        raise ProspectiveCorpusError(
            "the stop-event universe is anchored to the control-reference track"
        )
    if slot.direction not in STOP_DIRECTIONS:
        raise ProspectiveCorpusError(f"direction must be one of {STOP_DIRECTIONS}")
    _decimal(slot.active_stop, "active_stop")
    if not isinstance(slot.active_stop_identity, str) or not slot.active_stop_identity:
        raise ProspectiveCorpusError("active_stop_identity must be non-empty")
    if slot.control_position_state not in _state_machine.OPEN_POSITION_STATES:
        raise ProspectiveCorpusError(
            "the control stop anchor requires an open control position state"
        )
    for field_name, state in (
        ("control_position_state", slot.control_position_state),
        ("candidate_position_state", slot.candidate_position_state),
    ):
        if state not in _state_machine.POSITION_STATES:
            raise ProspectiveCorpusError(
                f"{field_name} must be one of {_state_machine.POSITION_STATES}"
            )
    decision_time = decision_time_for(slot.observation_time, STOP_HOURLY_CADENCE)
    if slot.first_divergence_decision_time is not None:
        _require_utc(
            slot.first_divergence_decision_time,
            "first_divergence_decision_time",
        )
        if slot.first_divergence_decision_time > decision_time:
            raise ProspectiveCorpusError(
                "first_divergence_decision_time cannot be in the future"
            )

    for family_name, observations, expected_time in (
        ("providers", slot.providers, slot.observation_time),
        (
            "prior_providers",
            slot.prior_providers,
            slot.observation_time - PRIOR_OBSERVABLE_MAXIMUM_GAP,
        ),
    ):
        seen: set[str] = set()
        for observation in observations:
            if not isinstance(observation, ProviderObservation):
                raise ProspectiveCorpusError(
                    f"{family_name} must be ProviderObservation rows"
                )
            if observation.provider_id not in REQUIRED_PROVIDER_IDS:
                raise ProspectiveCorpusError(
                    f"provider {observation.provider_id!r} is not a required provider"
                )
            if observation.provider_id in seen:
                raise ProspectiveCorpusError(
                    f"duplicate observation for {observation.provider_id!r} in {family_name}"
                )
            seen.add(observation.provider_id)
            _require_utc(observation.observation_time, "provider observation_time")
            _require_utc(observation.available_at, "provider available_at")
            if observation.observation_time != expected_time:
                raise ProspectiveCorpusError(
                    f"{family_name} must use the exact contiguous hourly session"
                )
            if observation.available_at > decision_time:
                raise ProspectiveCorpusError(
                    f"{observation.provider_id!r} was not available at the decision time"
                )
            for field_name in ("open", "high", "low", "close"):
                _decimal(getattr(observation, field_name), field_name)
    return decision_time


def _at_or_beyond_stop(value: Decimal, stop: Decimal, direction: str) -> bool:
    """The repository's stop convention: ``low <= stop`` / ``high >= stop``.

    Applied to the stop-relevant extreme it answers "did this venue reach the
    stop"; applied to the slot open it answers "was the stop already crossed
    when the slot opened".  One predicate, two questions.
    """

    return value <= stop if direction == LONG_DIRECTION else value >= stop


def _safe_side_of_stop(value: Decimal, stop: Decimal, direction: str) -> bool:
    return not _at_or_beyond_stop(value, stop, direction)


def classify_stop_event(slot: StopEvaluationSlot) -> dict[str, Any]:
    """Classify one hourly stop-evaluation slot deterministically.

    The result is candidate-neutral: it reads only the required providers' raw
    observations and the control track's active stop, never a candidate
    reference, candidate portfolio state, or measured outcome. Provider order,
    dictionary order and the ambient ``Decimal`` context cannot move any field.
    """

    decision_time = _validate_slot(slot)
    field = STOP_RELEVANT_FIELD[slot.direction]
    by_provider = {row.provider_id: row for row in slot.providers}
    available = tuple(
        provider_id for provider_id in REQUIRED_PROVIDER_IDS if provider_id in by_provider
    )
    missing = tuple(
        provider_id
        for provider_id in REQUIRED_PROVIDER_IDS
        if provider_id not in by_provider
    )
    touching = tuple(
        provider_id
        for provider_id in available
        if _at_or_beyond_stop(
            getattr(by_provider[provider_id], field),
            slot.active_stop,
            slot.direction,
        )
    )
    non_touching = tuple(
        provider_id for provider_id in available if provider_id not in touching
    )

    reason_codes: list[str] = []
    if len(available) < PROVIDER_QUORUM:
        classification = EVENT_NOT_CLASSIFIABLE
        reason_codes.append("PROVIDER_QUORUM_ABSENT")
        consensus_extreme: Decimal | None = None
        consensus_open: Decimal | None = None
    else:
        consensus_extreme = _median(
            [getattr(by_provider[provider_id], field) for provider_id in available]
        )
        consensus_open = _median(
            [by_provider[provider_id].open for provider_id in available]
        )
        if len(touching) >= CONFIRMATION_QUORUM:
            classification = EVENT_CROSS_MARKET
        elif missing:
            classification = EVENT_NOT_CLASSIFIABLE
            reason_codes.append(
                "ISOLATION_NOT_ESTABLISHED_MISSING_PROVIDER"
                if len(touching) == 1
                else "EVENT_CLASSIFICATION_UNCERTAIN_MISSING_PROVIDER"
            )
        elif len(touching) == 1 and len(non_touching) >= CONFIRMATION_QUORUM:
            classification = EVENT_ISOLATED_VENUE
        elif len(touching) == 1:
            classification = EVENT_NOT_CLASSIFIABLE
            reason_codes.append("ISOLATION_NON_TOUCHING_QUORUM_ABSENT")
        else:
            classification = EVENT_NONE
    if missing:
        reason_codes.append("REQUIRED_PROVIDER_MISSING")

    prior_by_provider = {
        row.provider_id: row for row in slot.prior_providers
    }
    prior_available = tuple(
        provider_id
        for provider_id in REQUIRED_PROVIDER_IDS
        if provider_id in prior_by_provider
    )
    prior_observable_time = slot.observation_time - PRIOR_OBSERVABLE_MAXIMUM_GAP
    prior_observable_price = (
        _median([prior_by_provider[provider_id].close for provider_id in prior_available])
        if len(prior_available) >= PROVIDER_QUORUM
        else None
    )

    if classification == EVENT_NOT_CLASSIFIABLE:
        gap_state = GAP_THROUGH_NOT_EVALUABLE
        consensus_stop_outcome = STOP_OUTCOME_UNDEFINED
        provider_stop_outcomes: dict[str, str] = {}
    elif prior_observable_price is None:
        gap_state = GAP_THROUGH_NOT_EVALUABLE
        reason_codes.append("NO_PRIOR_OBSERVABLE_REFERENCE_PRICE")
        reason_codes.append("PRIOR_REFERENCE_SESSION_MISSING")
        consensus_stop_outcome = STOP_OUTCOME_UNDEFINED
        provider_stop_outcomes = {}
    elif consensus_open is None:
        raise ProspectiveCorpusError(
            "a classifiable slot must carry a consensus open"
        )
    else:
        gapped = _safe_side_of_stop(
            prior_observable_price, slot.active_stop, slot.direction
        ) and _at_or_beyond_stop(consensus_open, slot.active_stop, slot.direction)
        gap_state = GAP_THROUGH_EVENT if gapped else GAP_THROUGH_NOT_PRESENT
        consensus_stop_outcome = (
            STOP_OUTCOME_TRIGGERED
            if _at_or_beyond_stop(consensus_open, slot.active_stop, slot.direction)
            else STOP_OUTCOME_NOT_TRIGGERED
        )
        provider_stop_outcomes = {
            provider_id: (
                STOP_OUTCOME_TRIGGERED
                if _at_or_beyond_stop(
                    by_provider[provider_id].open, slot.active_stop, slot.direction
                )
                else STOP_OUTCOME_NOT_TRIGGERED
            )
            for provider_id in available
        }

    identity = {
        "active_stop": str(slot.active_stop),
        "active_stop_identity": slot.active_stop_identity,
        "cadence": STOP_HOURLY_CADENCE,
        "classifier_version": STOP_EVENT_CLASSIFIER_VERSION,
        "direction": slot.direction,
        "observation_time": slot.observation_time.isoformat(),
        "protocol_version": PROTOCOL_VERSION,
        "track": slot.track,
    }
    return {
        "available_provider_ids": list(available),
        "active_stop_identity": slot.active_stop_identity,
        "candidate_position_state": slot.candidate_position_state,
        "classification": classification,
        "classifier_version": STOP_EVENT_CLASSIFIER_VERSION,
        "confirmation_quorum": CONFIRMATION_QUORUM,
        "control_position_state": slot.control_position_state,
        "consensus_open": None if consensus_open is None else str(consensus_open),
        "consensus_stop_extreme": (
            None if consensus_extreme is None else str(consensus_extreme)
        ),
        "consensus_stop_outcome": consensus_stop_outcome,
        "decision_time": decision_time.isoformat(),
        "direction": slot.direction,
        "event_id": _digest(identity),
        "gap_through_state": gap_state,
        "first_divergence_decision_time": (
            None
            if slot.first_divergence_decision_time is None
            else slot.first_divergence_decision_time.isoformat()
        ),
        "missing_provider_ids": list(missing),
        "observation_time": slot.observation_time.isoformat(),
        "non_touching_provider_ids": list(non_touching),
        "prior_observable_maximum_gap_seconds": int(
            PRIOR_OBSERVABLE_MAXIMUM_GAP.total_seconds()
        ),
        "prior_observable_owner": PRIOR_OBSERVABLE_OWNER,
        "prior_observable_provider_ids": list(prior_available),
        "prior_observable_observation_time": prior_observable_time.isoformat(),
        "prior_observable_price": (
            None if prior_observable_price is None else str(prior_observable_price)
        ),
        "provider_quorum": PROVIDER_QUORUM,
        "provider_stop_outcomes": dict(sorted(provider_stop_outcomes.items())),
        "reason_codes": sorted(set(reason_codes)),
        "stop_relevant_field": field,
        "touching_provider_ids": list(touching),
        "track": slot.track,
        "universe_anchor": STOP_EVENT_UNIVERSE_ANCHOR,
    }


def stop_event_classifier_identity() -> dict[str, Any]:
    """The classifier's own version, semantics, and implementation closure."""

    functions = (
        "_at_or_beyond_stop",
        "_median",
        "_safe_side_of_stop",
        "_validate_slot",
        "classify_stop_event",
        "decision_time_for",
    )
    sources = []
    for name in functions:
        owner = globals().get(name)
        if not callable(owner):
            raise ProspectiveCorpusError(f"classifier dependency {name!r} moved")
        sources.append({"function": name, "source": inspect.getsource(owner)})
    semantics = {
        "candidate_neutral": True,
        "classifications": list(STOP_EVENT_CLASSIFICATIONS),
        "confirmation_quorum": CONFIRMATION_QUORUM,
        "event_window": "one canonical 1h session, UTC",
        "gap_through_states": list(GAP_THROUGH_STATES),
        "manual_timestamp_selection_required": False,
        "precedence": list(CLASSIFICATION_PRECEDENCE),
        "prior_observable_derivation": GAP_THROUGH_DERIVATION,
        "provider_quorum": PROVIDER_QUORUM,
        "required_providers": list(REQUIRED_PROVIDER_IDS),
        "stop_event_universe_anchor": STOP_EVENT_UNIVERSE_ANCHOR,
        "stop_event_universe_derivation": STOP_EVENT_UNIVERSE_DERIVATION,
        "stop_relevant_field": dict(STOP_RELEVANT_FIELD),
        "stop_touch_convention": "long: low <= stop; short: high >= stop",
        "venue_consensus": "median over available required providers",
    }
    return {
        "dependency_identities": {
            "canonical_session_owner": CANONICAL_SESSION_OWNER,
            "decision_delay_owner": DECISION_DELAY_OWNER,
            "required_provider_owner": (
                "btc_predictor.research.reference_composite."
                "REQUIRED_COMPOSITE_PROVIDER_IDS"
            ),
            "provider_quorum_owner": (
                "btc_predictor.research.reference_composite_v2."
                "V2_MINIMUM_PROVIDER_COUNT"
            ),
        },
        "implementation_closure_sha256": _digest(sources),
        "implementation_owner": STOP_EVENT_CLASSIFIER_OWNER,
        "semantic_definition": semantics,
        "semantic_definition_sha256": _digest(semantics),
        "version": STOP_EVENT_CLASSIFIER_VERSION,
    }


# ===========================================================================
# 8. historical gate authority
# ===========================================================================
#
# The eight thresholds, directions, hard roles and stated intents are read from
# the immutable BTC_REFERENCE_COMPOSITE_V2 approval-gate table -- the parent
# every later protocol inherits verbatim -- and never restated as literals here.

HISTORICAL_GATE_AUTHORITY = (
    "btc_predictor.research.reference_composite_v2.V2_APPROVAL_GATES"
)


def historical_gate_authority() -> dict[str, dict[str, Any]]:
    """Import the eight frozen gates from immutable authority."""

    rows = {
        gate.metric: {
            "definition": gate.rationale,
            "direction": gate.direction,
            "hard": gate.hard,
            "metric": gate.metric,
            "source_authority": HISTORICAL_GATE_AUTHORITY,
            "source_of_rationale": gate.source_of_rationale,
            "threshold": gate.threshold,
            "validation_stage": gate.validation_stage,
        }
        for gate in _v2.V2_APPROVAL_GATES
        if gate.metric in TARGET_METRICS
    }
    missing = tuple(metric for metric in TARGET_METRICS if metric not in rows)
    if missing:
        raise ProspectiveCorpusError(
            f"the frozen V2 authority no longer carries {missing}"
        )
    if not all(row["hard"] for row in rows.values()):
        raise ProspectiveCorpusError("all eight inherited Stage-B gates are hard")
    return rows


# ===========================================================================
# 9. per-metric prospective evidence contracts
# ===========================================================================
#
# Each contract supplies exactly what the historical gate never had: an owner, a
# universe, a numerator, a denominator, an insufficiency rule and a reason
# vocabulary.  Threshold, direction, hard role and stated intent are copied from
# authority and are asserted unchanged.

_SETUP_DETECTORS = (
    "SETUP_BULL_TREND_CONTINUATION",
    "SETUP_BULLISH_RESET",
    "SETUP_CAPITULATION_REVERSAL",
    "SETUP_BEARISH_DISTRIBUTION",
)
_SETUP_DETECTOR_STATES = ("DETECTED", "NOT_DETECTED")
_REGIME_COMPARISON_BASIS = "categorical_regime_state"

TRADE_ACTION_COMPARISON_OWNER_VERSION = "TRADE_ACTION_COMPARISON_OWNER_V1"
TRADE_ACTION_COMPARISON_OWNER = (
    "btc_predictor.research.prospective_integration_corpus."
    "TRADE_ACTION_COMPARISON_OWNER_V1"
)
TRADE_ACTION_VOCABULARY = (
    "NO_TRADE",
    "WATCH",
    "ENTER",
    "HOLD",
    "ADD",
    "STOP_MOVE",
    "TRIM",
    "EXIT",
    "MISSED",
)
if set(TRADE_ACTION_VOCABULARY) != set(
    _data_quality.RECOMMENDATION_ACTIONS + _portfolio_db.PAPER_ACTIONS
):
    raise ProspectiveCorpusError(
        "trade-action vocabulary must equal the union of decision and persisted actions"
    )
TRADE_ACTION_COMPOSITE_CONTRACT = {
    "version": TRADE_ACTION_COMPARISON_OWNER_VERSION,
    "owner_chain": [
        "btc_predictor.features.setup (four detector state vector)",
        "btc_predictor.features.entry.classify_entry_action (conviction bucket only)",
        "btc_predictor.risk.stop + btc_predictor.risk.reward + btc_predictor.risk.sizing + btc_predictor.risk.exposure",
        "btc_predictor.signals.no_chase.apply_no_chase_filter",
        "btc_predictor.signals.hard_veto.evaluate_hard_veto",
        "btc_predictor.signals.data_quality.apply_data_quality_gate",
        "btc_predictor.signals.exit_rules.evaluate_exit_rules",
        "btc_predictor.signals.trim.evaluate_trim_rules",
        "btc_predictor.risk.trailing.trail_stop_for_position",
        "btc_predictor.signals.add_requirements.add_requirements_from_results",
        "btc_predictor.portfolio.state_machine.apply_position_event",
        "btc_predictor.portfolio entry/add/trim/stop/exit execution owners",
        "btc_predictor.db.portfolio persisted action vocabulary",
    ],
    "precedence": [
        "Process an eligible resting-stop execution before a same-slot strategy decision, matching the adverse-first paper/backtest path.",
        "For an open position, an authoritative EXIT suppresses TRIM; otherwise retain TRIM, STOP_MOVE and ADD outputs in lifecycle order without folding co-occurring materially distinct events into HOLD.",
        "For a new entry, hard veto, no-chase, reference availability, risk and data-quality owners must all resolve before ENTER; WATCH and NO_TRADE remain distinct owner outputs.",
        "Apply the lifecycle owner and persist the accepted or refused transition; a later execution MISS is MISSED, not NO_TRADE.",
    ],
    "input_state": [
        "complete PIT setup/regime/entry/risk/veto outputs",
        "lifecycle state before the slot and its active stop/tranches",
        "pending order and next eligible execution-bar state",
        "data-quality and reference-availability states",
    ],
    "output": (
        "An ordered action envelope over actual repository actions. Two tracks "
        "disagree if their ordered envelopes differ in action, acceptance, or "
        "lifecycle-event identity; presentation text is never compared."
    ),
    "output_action_vocabulary": list(TRADE_ACTION_VOCABULARY),
    "lifecycle_event_vocabulary": list(_state_machine.POSITION_EVENTS),
    "entry_conviction_input_vocabulary": list(_entry.ENTRY_ACTION_LABELS),
    "reason_semantics": (
        "Retain the originating owner, accepted/refused state and complete "
        "reason-code sequence for every envelope element. Equal display labels "
        "do not erase different lifecycle events or acceptance states."
    ),
    "renderer_role": "PRESENTATION_ONLY_NOT_SCIENTIFIC_AUTHORITY",
    "vocabulary_sources": {
        "decision_actions": {
            "owner": "btc_predictor.signals.data_quality.RECOMMENDATION_ACTIONS",
            "values": list(_data_quality.RECOMMENDATION_ACTIONS),
        },
        "entry_buckets": {
            "owner": "btc_predictor.features.entry.ENTRY_ACTION_LABELS",
            "values": list(_entry.ENTRY_ACTION_LABELS),
            "role": "INPUT_CONVICTION_NOT_OUTPUT_ACTION",
        },
        "lifecycle_events": {
            "owner": "btc_predictor.portfolio.state_machine.POSITION_EVENTS",
            "values": list(_state_machine.POSITION_EVENTS),
        },
        "persisted_actions": {
            "owner": "btc_predictor.db.portfolio.PAPER_ACTIONS",
            "values": list(_portfolio_db.PAPER_ACTIONS),
        },
    },
}

TRADE_ELIGIBILITY_COMPOSITE_OWNER_VERSION = "TRADE_ELIGIBILITY_COMPOSITE_OWNER_V1"
TRADE_ELIGIBILITY_COMPOSITE_OWNER = (
    "btc_predictor.research.prospective_integration_corpus."
    "TRADE_ELIGIBILITY_COMPOSITE_OWNER_V1"
)
TRADE_ELIGIBILITY_COMPOSITE_CONTRACT = {
    "version": TRADE_ELIGIBILITY_COMPOSITE_OWNER_VERSION,
    "authoritative_inputs": {
        "setup_eligibility": "complete btc_predictor.features.setup detector vector and supported setup identity",
        "entry_conviction": "btc_predictor.features.entry.classify_entry_action; entry buckets VALID, STRONG or EXCEPTIONAL",
        "regime_context": "resolved regime classification plus stress/severe-crowding states consumed by HARD_VETO_V1",
        "reward_risk": "btc_predictor.risk.reward.evaluate_reward_risk result consumed by HARD_VETO_V1",
        "hard_veto": "btc_predictor.signals.hard_veto.evaluate_hard_veto",
        "data_quality": "btc_predictor.signals.data_quality.apply_data_quality_gate for requested ENTER",
        "no_chase": "btc_predictor.signals.no_chase.apply_no_chase_filter result consumed by HARD_VETO_V1",
        "lifecycle_state": {
            "owner": "btc_predictor.portfolio.state_machine.POSITION_STATES",
            "values": list(_state_machine.POSITION_STATES),
            "pre_position_values": list(_state_machine.PRE_POSITION_STATES),
        },
        "risk_capacity": "complete positive btc_predictor.risk.sizing result plus btc_predictor.risk.exposure within-maximum result",
        "reference_availability": "both authorized reference roles usable under AVAILABLE_AT_LTE_DECISION_TIME_V1",
    },
    "composition": (
        "PERMITTED iff the reference and every required PIT input are available, "
        "the lifecycle is a pre-position state, a supported setup is detected, "
        "the entry bucket is VALID/STRONG/EXCEPTIONAL, HARD_VETO_V1 is complete "
        "and clear (including R/R, regime/context, data quality and no-chase), "
        "and the existing sizing/risk-capacity owners return a complete positive "
        "size within the configured maximum. Otherwise a fully resolved gate is "
        "NOT_PERMITTED; an unresolved input is NOT_COMPARABLE, never false."
    ),
    "output_vocabulary": ["PERMITTED", "NOT_PERMITTED", "NOT_COMPARABLE"],
    "reason_semantics": (
        "Persist every source completion state, source reason code and the exact "
        "blocking owner. No entry-conviction bucket alone is a permission."
    ),
}

RISK_SIZE_QUANTITY = "position_notional"
RISK_SIZE_FORMULA = (
    "abs(candidate_position_notional - control_position_notional) / "
    "control_position_notional"
)
RISK_SIZE_STATISTIC = "nearest_rank_p95_of_the_absolute_relative_differences"
RISK_SIZE_PROBABILITY = Decimal("0.95")

_RISK_SIZE_DERIVATION = {
    "accepted_interpretation": {
        "denominator_universe": UNIVERSE_SIZING_EVALUABLE,
        "formula": RISK_SIZE_FORMULA,
        "quantity": RISK_SIZE_QUANTITY,
        "statistic": RISK_SIZE_STATISTIC,
    },
    "derivation": (
        "The frozen gate states a threshold, a direction and the intent that a "
        "reference change must not materially resize most positions; it states "
        "no formula and no denominator. Three authoritative facts settle all "
        "three open choices. (1) Quantity: the frozen V2 protocol names "
        "'initial position sizing' in its future_strategy_consequence_metrics, "
        "and INITIAL_POSITION_SIZE_V1 -- the sole authoritative sizing owner -- "
        "makes position_notional its only mandatory output; position_quantity "
        "is produced only when an entry price is supplied and risk_budget_amount "
        "is the budget, not the size. (2) Formula: the repository has exactly "
        "one implemented fractional-difference-against-a-comparison-baseline "
        "convention, abs(series - baseline) / baseline, used by "
        "reference_composite_empirical._atr_comparison for the sibling "
        "atr_median/p95_absolute_fractional_difference gates in this same frozen "
        "table, with the comparison baseline in the denominator. The control "
        "reference is this metric's baseline. (3) Statistic: the repository's "
        "p95 owner is nearest rank, in reference_composite_empirical._percentile "
        "and price_source_policy._nearest_rank_percentile, and frozen V4 names "
        "'nearest-rank p95' for the p95 gate family explicitly."
    ),
    "refused_derivations": {
        "interpolated_p95": (
            "The failed V3 sealed-evidence builder interpolated; the repeat "
            "xHigh review recorded that this differs from the authoritative "
            "nearest-rank owner and flips a hard gate on boundary vectors. A "
            "failed lineage is not authority."
        ),
        "max_denominator": (
            "A max-scaled denominator exists in the repository for equality-"
            "tolerance logic, but not as the authoritative measurement-layer "
            "relative-difference statistic for this gate; adopting it here "
            "would silently compress every difference."
        ),
        "nav_normalized_difference": (
            "Dividing by NAV would measure exposure share, not resizing, and "
            "would import each track's own diverged NAV into the denominator."
        ),
        "position_quantity_basis": (
            "position_quantity is optional in the authoritative owner's own "
            "result, so a quantity basis is undefined whenever no entry price "
            "was supplied."
        ),
        "symmetric_mean_denominator": (
            "abs(a - b) / ((a + b) / 2) is a different convention from the only "
            "one this repository implements, and adopting it would author a new "
            "statistic under a threshold calibrated before it existed."
        ),
    },
    "unique_interpretation": True,
}

_METRIC_EVIDENCE: dict[str, dict[str, Any]] = {
    CROSS_MARKET_METRIC: {
        "cadence": STOP_HOURLY_CADENCE,
        "comparison_basis": "candidate reference versus raw venue consensus",
        "denominator": (
            "Classified CROSS_MARKET_CONFIRMED_STOP_EVENT slots at the control "
            "track's active stop where both reference outcomes are usable at "
            "that decision_time."
        ),
        "derived_universe_anchor": STOP_EVENT_UNIVERSE_DERIVATION,
        "evidence_owner": STOP_EVENT_CLASSIFIER_OWNER,
        "not_comparable_reasons": [
            "CANDIDATE_REFERENCE_UNAVAILABLE",
            "PROVIDER_QUORUM_ABSENT",
        ],
        "numerator": (
            "Events where the candidate reference series also reaches the "
            "stop-relevant extreme, so the genuine shared tail move is preserved."
        ),
        "statistic": "rate",
        "universe": UNIVERSE_CROSS_MARKET_EVENTS,
        "zero_denominator": UNDEFINED_INSUFFICIENT_EVIDENCE,
    },
    GAP_THROUGH_METRIC: {
        "cadence": STOP_HOURLY_CADENCE,
        "comparison_basis": "candidate reference versus raw venue consensus",
        "denominator": (
            "Classified GAP_THROUGH_STOP_EVENT slots at the control track's "
            "active stop where the exact immediately preceding hourly raw-"
            "provider consensus close and both current reference opens are usable."
        ),
        "derived_universe_anchor": STOP_EVENT_UNIVERSE_DERIVATION,
        "gap_through_derivation": GAP_THROUGH_DERIVATION,
        "evidence_owner": STOP_EVENT_CLASSIFIER_OWNER,
        "gap_through_semantics": (
            "BTC trades continuously, so no overnight-session gap is imported. A "
            "gap-through is a crossing without an observable traded price at the "
            "control stop between two contiguous canonical hourly observations: "
            "the immediately preceding required-provider-consensus close is "
            "strictly safe and the current consensus open is at or beyond the "
            "stop. A missing prior hour is NOT_EVALUABLE; an older observation "
            "may not be substituted."
        ),
        "not_comparable_reasons": [
            "CANDIDATE_REFERENCE_UNAVAILABLE",
            "NO_PRIOR_OBSERVABLE_REFERENCE_PRICE",
            "PRIOR_REFERENCE_SESSION_MISSING",
            "PROVIDER_QUORUM_ABSENT",
        ],
        "numerator": (
            "Count of denominator events where the candidate reference is "
            "TRIGGERED at the control stop on the current hourly open. Venue "
            "consensus is TRIGGERED by construction for every denominator event; "
            "this statistic therefore measures candidate preservation of those "
            "consensus gap-throughs, not equality of two unconstrained outcomes."
        ),
        "statistic": "rate",
        "universe": UNIVERSE_GAP_THROUGH_EVENTS,
        "zero_denominator": UNDEFINED_INSUFFICIENT_EVIDENCE,
    },
    ISOLATED_VENUE_METRIC: {
        "cadence": STOP_HOURLY_CADENCE,
        "comparison_basis": "candidate reference versus raw venue consensus",
        "denominator": (
            "Classified ISOLATED_VENUE_STOP_EVENT slots at the control track's "
            "active stop where exactly one provider touches, at least the "
            "confirmation quorum is observed not touching, and both reference "
            "outcomes are usable."
        ),
        "derived_universe_anchor": STOP_EVENT_UNIVERSE_DERIVATION,
        "evidence_owner": STOP_EVENT_CLASSIFIER_OWNER,
        "not_comparable_reasons": [
            "CANDIDATE_REFERENCE_UNAVAILABLE",
            "PROVIDER_QUORUM_ABSENT",
        ],
        "numerator": (
            "Events where the candidate reference series does not reach the "
            "stop-relevant extreme, so the single-venue wick is suppressed."
        ),
        "statistic": "rate",
        "universe": UNIVERSE_ISOLATED_VENUE_EVENTS,
        "zero_denominator": UNDEFINED_INSUFFICIENT_EVIDENCE,
    },
    REGIME_METRIC: {
        "cadence": STRATEGY_DAILY_CADENCE,
        "comparison_basis": "candidate track versus control track",
        "comparison_field": _REGIME_COMPARISON_BASIS,
        "denominator": (
            "Daily decision observations where both tracks hold the complete "
            "required regime inputs and both produce a REGIME_CLASSIFICATION."
        ),
        "evidence_owner": (
            "btc_predictor.features.regime.calculate_regime_classification"
        ),
        "not_comparable_reasons": [
            "CANDIDATE_TRACK_NOT_EVALUABLE",
            "CONTROL_TRACK_NOT_EVALUABLE",
        ],
        "numerator": (
            "Observations where the two tracks' authoritative categorical regime "
            "labels differ. The raw and smoothed scores are persisted beside the "
            "comparison as evidence but are never the compared field: the gate's "
            "own words are 'regime labels'."
        ),
        "statistic": "rate",
        "universe": UNIVERSE_REGIME_EVALUABLE,
        "vocabulary_owner": (
            "btc_predictor.features.regime.REGIME_CLASSIFICATION_LABELS"
        ),
        "zero_denominator": UNDEFINED_INSUFFICIENT_EVIDENCE,
    },
    RISK_SIZE_METRIC: {
        "cadence": STRATEGY_DAILY_CADENCE,
        "comparison_basis": "candidate track versus control track",
        "denominator": (
            "Daily decision observations where both tracks independently permit "
            "an entry and both authoritative INITIAL_POSITION_SIZE results are "
            "complete with a strictly positive position_notional."
        ),
        "derived_interpretation": _RISK_SIZE_DERIVATION,
        "evidence_owner": (
            "btc_predictor.risk.sizing.calculate_initial_position_size"
        ),
        "formula": RISK_SIZE_FORMULA,
        "not_comparable_reasons": [
            "CANDIDATE_TRACK_NOT_EVALUABLE",
            "CONTROL_TRACK_NOT_EVALUABLE",
            "ONE_TRACK_POSITION_ACTIVE_ONE_TRACK_FLAT",
            "ONE_TRACK_PRODUCED_NO_POSITIVE_RISK_SIZE",
        ],
        "numerator": (
            "Not a count. The reported value is the nearest-rank p95 of the "
            "absolute relative differences over the denominator universe."
        ),
        "quantity": RISK_SIZE_QUANTITY,
        "statistic": RISK_SIZE_STATISTIC,
        "statistic_owner": (
            "btc_predictor.research.prospective_integration_corpus."
            "nearest_rank_percentile"
        ),
        "universe": UNIVERSE_SIZING_EVALUABLE,
        "zero_denominator": UNDEFINED_INSUFFICIENT_EVIDENCE,
    },
    SETUP_METRIC: {
        "cadence": STRATEGY_DAILY_CADENCE,
        "comparison_basis": "candidate track versus control track",
        "comparison_field": "authoritative_setup_detector_state_vector",
        "denominator": (
            "Daily decision observations where both tracks hold the complete "
            "input set of all four authoritative setup detectors."
        ),
        "evidence_owner": "btc_predictor.features.setup",
        "not_comparable_reasons": [
            "CANDIDATE_TRACK_NOT_EVALUABLE",
            "CONTROL_TRACK_NOT_EVALUABLE",
        ],
        "numerator": (
            "Observations where the two tracks' ordered four-detector state "
            "vectors differ in any component. No repository authority defines a "
            "precedence among simultaneously detected setups, so a single-label "
            "collapse would invent strategy semantics; comparing the complete "
            "vector also refuses to call two different setup states 'the same' "
            "because both happen to end in NO_TRADE."
        ),
        "statistic": "rate",
        "universe": UNIVERSE_SETUP_EVALUABLE,
        "vocabulary": {
            "detectors": list(_SETUP_DETECTORS),
            "states": list(_SETUP_DETECTOR_STATES),
        },
        "zero_denominator": UNDEFINED_INSUFFICIENT_EVIDENCE,
    },
    TRADE_ACTION_METRIC: {
        "cadence": STRATEGY_DAILY_CADENCE,
        "comparison_basis": "candidate track versus control track",
        "denominator": (
            "Every daily decision observation where both tracks produce a "
            "complete deterministic ordered action envelope, whether flat or in "
            "position. Flat-vs-position slots remain comparable because both "
            "owners still produce actual action envelopes."
        ),
        "evidence_owner": TRADE_ACTION_COMPARISON_OWNER,
        "owner_contract": TRADE_ACTION_COMPOSITE_CONTRACT,
        "not_comparable_reasons": [
            "CANDIDATE_TRACK_NOT_EVALUABLE",
            "CONTROL_TRACK_NOT_EVALUABLE",
        ],
        "numerator": (
            "Observations where the two tracks' authoritative ordered action "
            "envelopes differ in action, acceptance or lifecycle-event identity."
        ),
        "reproduction_evidence": [
            "lifecycle_state_before",
            "lifecycle_event",
            "lifecycle_state_after",
            "tranches",
            "active_stop",
            "nav",
        ],
        "statistic": "rate",
        "universe": UNIVERSE_ACTION_EVALUABLE,
        "vocabulary": list(TRADE_ACTION_VOCABULARY),
        "vocabulary_owner": TRADE_ACTION_COMPOSITE_CONTRACT["vocabulary_sources"],
        "zero_denominator": UNDEFINED_INSUFFICIENT_EVIDENCE,
    },
    TRADE_ELIGIBILITY_METRIC: {
        "cadence": STRATEGY_DAILY_CADENCE,
        "comparison_basis": "candidate track versus control track",
        "denominator": (
            "Daily decision observations where both tracks have complete inputs "
            "for TRADE_ELIGIBILITY_COMPOSITE_OWNER_V1 and each produces "
            "PERMITTED or NOT_PERMITTED. Flat-vs-position and both-position "
            "states stay in this universe; lifecycle state is a permission input."
        ),
        "eligibility_composition": {
            "already_in_position": (
                "NOT_PERMITTED for a new entry. The existing position remains on "
                "its management/add path, but that does not make new-entry "
                "permission undefined. This keeps lifecycle divergence visible."
            ),
            "data_failure": (
                "A resolved hard data-quality failure blocks ENTER under "
                "apply_data_quality_gate and is a NOT_PERMITTED result. Missing "
                "quality evidence is NOT_COMPARABLE."
            ),
            "permitted_definition": (
                "trade_permitted is TRUE only when, under that track's own "
                "owners: the data-quality gate does not block ENTER, no hard veto "
                "fires, at least one authoritative setup detector is DETECTED, "
                "the reward/risk filter passes, the entry action classifies as an "
                "entry, and the risk owners produce a complete strictly positive "
                "initial position size within the configured risk-at-stop limit."
            ),
            "reference_unavailable": (
                "REFERENCE_UNAVAILABLE for either track makes the slot "
                "NOT_COMPARABLE with the affected side named; it is never read "
                "as 'not permitted'."
            ),
            "regime_or_setup_veto": (
                "A regime or setup veto is a NOT_PERMITTED outcome, not an "
                "exclusion: the slot stays in the denominator."
            ),
            "risk_capacity_veto": (
                "A RISK_AT_STOP_V1 capacity refusal is a NOT_PERMITTED outcome, "
                "not an exclusion."
            ),
            "reward_risk_veto": (
                "A REWARD_RISK_FILTER_V1 refusal is a NOT_PERMITTED outcome, not "
                "an exclusion."
            ),
        },
        "evidence_owner": TRADE_ELIGIBILITY_COMPOSITE_OWNER,
        "owner_contract": TRADE_ELIGIBILITY_COMPOSITE_CONTRACT,
        "not_comparable_reasons": [
            "CANDIDATE_TRACK_NOT_EVALUABLE",
            "CONTROL_TRACK_NOT_EVALUABLE",
            "REQUIRED_INPUT_MISSING",
            "REQUIRED_INPUT_NOT_YET_AVAILABLE_AT_DECISION_TIME",
        ],
        "numerator": (
            "Observations where the two tracks disagree on whether a new trade is "
            "permitted."
        ),
        "statistic": "rate",
        "supporting_owners": list(
            TRADE_ELIGIBILITY_COMPOSITE_CONTRACT["authoritative_inputs"].values()
        ),
        "universe": UNIVERSE_ELIGIBILITY_EVALUABLE,
        "zero_denominator": UNDEFINED_INSUFFICIENT_EVIDENCE,
    },
}


def metric_evidence_contracts() -> dict[str, Any]:
    """Bind each frozen gate to its prospective, executable evidence definition."""

    authority = historical_gate_authority()
    contracts = {}
    for metric in TARGET_METRICS:
        evidence = dict(_METRIC_EVIDENCE[metric])
        gate = authority[metric]
        if evidence["universe"] not in DECISION_UNIVERSES:
            raise ProspectiveCorpusError(f"{metric} names an undeclared universe")
        contracts[metric] = {
            **evidence,
            "direction": gate["direction"],
            "hard": gate["hard"],
            "historical_definition": gate["definition"],
            "historical_source_authority": gate["source_authority"],
            "historical_source_of_rationale": gate["source_of_rationale"],
            "insufficient_rule": (
                "A zero or absent denominator is "
                f"{UNDEFINED_INSUFFICIENT_EVIDENCE}; it is never a PASS and never "
                "the numeric value 0."
            ),
            "metric": metric,
            "reason_vocabulary": list(OBSERVATION_REASON_VOCABULARY),
            "threshold": gate["threshold"],
        }
    payload = {
        "comparability_evidence_fields": list(COMPARABILITY_EVIDENCE_FIELDS),
        "contracts": contracts,
        "metric_count": len(contracts),
        "observation_states": list(OBSERVATION_STATES),
        "protocol_version": PROTOCOL_VERSION,
        "schema_version": "PROSPECTIVE_INTEGRATION_METRIC_EVIDENCE_CONTRACTS_V1",
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


COMPARABILITY_EVIDENCE_FIELDS = (
    "candidate_reference_identity",
    "configuration_identity",
    "control_reference_identity",
    "corpus_protocol_sha256",
    "denominator",
    "event_count",
    "exclusion_counts_by_reason",
    "not_comparable_count",
    "numerator",
    "scheduled_slot_count",
    "strategy_identity",
    "trade_count",
    "universe",
    "window_end",
    "window_start",
)


# ===========================================================================
# 10. evidence sufficiency
# ===========================================================================
#
# Arithmetic definedness and certification sufficiency are different questions.
# This contract freezes only that a zero denominator is undefined. What it
# takes to certify is a minimum-denominator
#     decision.  The repository has already established, through
#     BTC_REFERENCE_COMPOSITE_V3_STRUCTURAL_THRESHOLD_CALIBRATION_V1 and the
#     convergence review that followed it, that choosing a rate gate's minimum
#     n is its own pre-data governance task with its own predeclared objective.
#     PER_PAIR_WILSON_UPPER_BOUND_V1 is frozen for the V3 structural gate family
#     and controls only that scope. Authoring a number for these eight gates
#     here would be exactly the unapproved methodology this protocol exists to
#     prevent, so each metric is marked rather than guessed.

REPORTABLE_NOT_CERTIFIABLE = (
    "REPORTABLE_BUT_NOT_CERTIFIABLE_WITHOUT_SEPARATE_PRE_DATA_GOVERNANCE"
)
SUFFICIENCY_GOVERNANCE_SUCCESSOR = (
    "PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1"
)

EVALUABILITY_MINIMUMS: dict[str, dict[str, Any]] = {
    metric: {
        "arithmetic_nonempty_denominator_required": True,
        "complete_slot_census_required": True,
        "no_silent_omission_required": True,
        "both_tracks_valid_required": True,
        "certification_minimum_selected_here": None,
    }
    for metric in TARGET_METRICS
}

COLLECTION_HORIZON = {
    "calendar_minimum_days": None,
    "calendar_minimum_rationale": (
        "None is imposed. Stage-C's live_shadow_days >= 90 is a "
        "post-certification promotion gate about publication latency in live "
        "operation; it is not a Stage-B evidence-sufficiency rule and frozen V4 "
        "moved it out of historical validation precisely to stop the two being "
        "read as one. Importing 90 days here would restate a different gate's "
        "number as this stage's minimum."
    ),
    "termination_rule": (
        "A future collection epoch terminates on independently certified, "
        "predeclared evidence sufficiency, never on elapsed time or an observed "
        "rate. This protocol chooses no minimum or terminating condition."
    ),
    "termination_state": "STAGE_B_TERMINATION_UNDEFINED_UNTIL_SUFFICIENCY_GOVERNANCE",
}


def evidence_sufficiency_contract() -> dict[str, Any]:
    authority = historical_gate_authority()
    metrics = {}
    for metric in TARGET_METRICS:
        metrics[metric] = {
            "certification_sufficiency_state": REPORTABLE_NOT_CERTIFIABLE,
            "certification_sufficiency_owner": SUFFICIENCY_GOVERNANCE_SUCCESSOR,
            "direction": authority[metric]["direction"],
            "evaluability_minimum": dict(EVALUABILITY_MINIMUMS[metric]),
            "metric": metric,
            "minimum_denominator_chosen_here": None,
            "threshold": authority[metric]["threshold"],
            "zero_denominator_outcome": UNDEFINED_INSUFFICIENT_EVIDENCE,
            "zero_denominator_passes": False,
        }
    payload = {
        "collection_horizon": dict(COLLECTION_HORIZON),
        "insufficient_evidence_state": UNDEFINED_INSUFFICIENT_EVIDENCE,
        "metrics": metrics,
        "minimums_selected_from_observed_outcomes": False,
        "pre_collection_sequence": {
            "collection_entry_requirement": COLLECTION_ENTRY_REQUIREMENT,
            "postp1_003_owner": SUFFICIENCY_GOVERNANCE_SUCCESSOR,
            "postp1_003_independent_review_required": True,
            "postp1_004_blocked_until_postp1_003_review_passes": True,
            "protocol_repeat_review_required": True,
            "sufficiency_minima_selected_here": False,
        },
        "protocol_version": PROTOCOL_VERSION,
        "schema_version": "PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_V1",
        "scoped_out_authority": {
            "per_pair_wilson_upper_bound_v1": (
                "Frozen for the BTC_REFERENCE_COMPOSITE_V3 structural gate family "
                "only. A newer narrow versioned policy controls only its own "
                "declared scope, so it is not carried across to these eight "
                "gates by this protocol."
            )
        },
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


# ===========================================================================
# 11. post-hoc contamination prohibitions
# ===========================================================================

PROHIBITED_AFTER_COLLECTION_STARTS = (
    "add or remove a non-price input family",
    "change a comparison reference identity",
    "change a denominator or its universe predicate",
    "change an evidence-sufficiency minimum",
    "change the cost or slippage model",
    "change the event classifier or any of its quorums, windows or fields",
    "change the strategy, risk, lifecycle or execution identity",
    "change a threshold, direction or hard role",
    "exclude an observed event or slot that the frozen rules admit",
    "resynchronize the two portfolio tracks",
    "retroactively relabel any persisted observation",
)
CHANGE_PROCEDURE = (
    f"Any change to a semantic field requires {SUCCESSOR_PROTOCOL_VERSION}, which "
    "starts a new prospective collection epoch for every affected metric. "
    "Observations already collected under this protocol keep their original "
    "labels; nothing is relabelled backwards and no epoch is merged."
)

HUMAN_REVIEW_POLICY = {
    "blinding": (
        "Where a review is unavoidable, the reviewer is blinded to the candidate "
        "outcome wherever practical and the blinding state is persisted."
    ),
    "manual_event_selection_required": False,
    "predeclared_questions_required": True,
    "prose_may_override_gate_arithmetic": False,
    "required_for_any_target_metric": False,
    "reviewer_record_fields": [
        "blinded",
        "decision",
        "predeclared_question_id",
        "reason",
        "reviewed_at",
        "reviewer_identity",
    ],
    "statement": (
        "Every one of the eight measurements is produced by a deterministic "
        "owner from persisted point-in-time evidence. No manual timestamp "
        "selection and no reviewer judgement enters any numerator or denominator."
    ),
}


# ===========================================================================
# 12. persisted schema contract
# ===========================================================================
#
# PostgreSQL-compatible types in the existing ``research`` schema.  This task is
# protocol-only by repository convention -- an implemented migration would make
# a collection target exist before the freeze has been reviewed -- so the
# complete contract is frozen here and the migration belongs to the first
# collection ticket.

CORPUS_SCHEMA = "research"
CORPUS_TABLE_PREFIX = "prospective_"
SCHEMA_IMPLEMENTATION_STATE = "CONTRACT_ONLY_MIGRATION_DEFERRED_TO_FIRST_COLLECTOR_TICKET"

_APPEND_ONLY_RAW_TABLES = (
    "prospective_run",
    "prospective_decision_observation",
    "prospective_source_input_snapshot",
    "prospective_data_quality_event",
)

_TABLE_CONTRACT: dict[str, dict[str, Any]] = {
    "prospective_run": {
        "append_only": True,
        "columns": {
            "collection_epoch": "text not null",
            "corpus_protocol_sha256": "char(64) not null",
            "corpus_protocol_review_sha256": "char(64) not null",
            "created_at": "timestamptz not null",
            "epoch_end": "timestamptz null",
            "epoch_start": "timestamptz not null",
            "initial_portfolio_state_sha256": "char(64) not null",
            "lifecycle_state": "text not null",
            "protocol_version": "text not null",
            "run_id": "uuid not null",
            "strategy_identity_sha256": "char(64) not null",
            "sufficiency_governance_sha256": "char(64) not null",
            "sufficiency_governance_review_sha256": "char(64) not null",
            "postp1_004_implementation_review_sha256": "char(64) not null",
        },
        "layer": "RAW",
        "primary_key": ["run_id"],
        "purpose": "One frozen prospective collection epoch.",
    },
    "prospective_decision_observation": {
        "append_only": True,
        "columns": {
            "cadence": "text not null",
            "decision_time": "timestamptz not null",
            "input_snapshot_sha256": "char(64) null",
            "observation_state": "text not null",
            "observation_time": "timestamptz not null",
            "reason_codes": "jsonb not null",
            "run_id": "uuid not null",
            "slot_id": "char(64) not null",
            "universes": "jsonb not null",
            "warmup_history_complete": "boolean not null",
            "warmup_history_definition_sha256": "char(64) not null",
        },
        "layer": "RAW",
        "primary_key": ["run_id", "cadence", "observation_time"],
        "purpose": (
            "The complete scheduled slot census. Every slot the epoch schedules "
            "has exactly one row, so a silent omission is detectable by count."
        ),
    },
    "prospective_source_input_snapshot": {
        "append_only": True,
        "columns": {
            "available_at": "timestamptz not null",
            "decision_time": "timestamptz not null",
            "ingested_at": "timestamptz not null",
            "observation_time": "timestamptz not null",
            "payload": "jsonb not null",
            "payload_sha256": "char(64) not null",
            "provider": "text not null",
            "revision": "text not null",
            "run_id": "uuid not null",
            "source_family": "text not null",
            "source_key": "text not null",
            "units": "text not null",
        },
        "layer": "RAW",
        "primary_key": [
            "run_id",
            "source_family",
            "source_key",
            "observation_time",
            "revision",
        ],
        "purpose": (
            "Immutable point-in-time source observations, candidate-neutral. A "
            "restatement is a new revision row; an overwrite is refused."
        ),
    },
    "prospective_data_quality_event": {
        "append_only": True,
        "columns": {
            "decision_time": "timestamptz not null",
            "detail": "jsonb not null",
            "detected_at": "timestamptz not null",
            "event_type": "text not null",
            "run_id": "uuid not null",
            "sequence": "bigint not null",
            "source_family": "text null",
        },
        "layer": "RAW",
        "primary_key": ["run_id", "sequence"],
        "purpose": (
            "Mutation, deletion, duplicate, revision, late-arrival and "
            "source-replacement detections, recorded rather than repaired."
        ),
    },
    "prospective_reference_evaluation": {
        "append_only": True,
        "columns": {
            "decision_time": "timestamptz not null",
            "input_snapshot_sha256": "char(64) not null",
            "observation_time": "timestamptz not null",
            "output_sha256": "char(64) not null",
            "quality_state": "text not null",
            "reference_identity": "text not null",
            "reference_ohlc": "jsonb not null",
            "reference_role": "text not null",
            "run_id": "uuid not null",
        },
        "layer": "DERIVED",
        "primary_key": [
            "run_id",
            "reference_role",
            "reference_identity",
            "observation_time",
        ],
        "purpose": "One authorized reference variant's output for one slot.",
    },
    "prospective_strategy_evaluation": {
        "append_only": True,
        "columns": {
            "decision_time": "timestamptz not null",
            "input_snapshot_sha256": "char(64) not null",
            "output_sha256": "char(64) not null",
            "reason_codes": "jsonb not null",
            "regime_classification": "text null",
            "regime_score": "numeric(38,18) null",
            "regime_smoothed_score": "numeric(38,18) null",
            "run_id": "uuid not null",
            "setup_detector_states": "jsonb not null",
            "strategy_identity_sha256": "char(64) not null",
            "track": "text not null",
        },
        "layer": "DERIVED",
        "primary_key": ["run_id", "track", "decision_time"],
        "purpose": "Regime and setup outputs for one track at one decision.",
    },
    "prospective_risk_evaluation": {
        "append_only": True,
        "columns": {
            "decision_time": "timestamptz not null",
            "entry_price": "numeric(38,18) null",
            "input_snapshot_sha256": "char(64) not null",
            "output_sha256": "char(64) not null",
            "position_notional": "numeric(38,18) null",
            "reason_codes": "jsonb not null",
            "risk_at_stop": "numeric(38,18) null",
            "risk_budget_amount": "numeric(38,18) null",
            "risk_size_complete": "boolean not null",
            "run_id": "uuid not null",
            "stop_distance_fraction": "numeric(38,18) null",
            "stop_price": "numeric(38,18) null",
            "track": "text not null",
            "trade_permitted": "boolean null",
            "trade_eligibility_composite_version": "text not null",
            "trade_eligibility_input_states": "jsonb not null",
        },
        "layer": "DERIVED",
        "primary_key": ["run_id", "track", "decision_time"],
        "purpose": "Eligibility and sizing outputs for one track at one decision.",
    },
    "prospective_portfolio_state": {
        "append_only": True,
        "columns": {
            "active_stop": "numeric(38,18) null",
            "as_of": "timestamptz not null",
            "cash_balance": "numeric(38,18) not null",
            "lifecycle_state": "text not null",
            "nav": "numeric(38,18) not null",
            "prior_state_sha256": "char(64) null",
            "realized_pnl": "numeric(38,18) not null",
            "run_id": "uuid not null",
            "state_sha256": "char(64) not null",
            "track": "text not null",
            "tranches": "jsonb not null",
        },
        "layer": "DERIVED",
        "primary_key": ["run_id", "track", "as_of"],
        "purpose": "The hash-chained state history of one deterministic track.",
    },
    "prospective_trade_action": {
        "append_only": True,
        "columns": {
            "action": "text not null",
            "action_envelope": "jsonb not null",
            "action_comparison_owner_version": "text not null",
            "decision_time": "timestamptz not null",
            "lifecycle_event": "text null",
            "lifecycle_state_after": "text not null",
            "lifecycle_state_before": "text not null",
            "output_sha256": "char(64) not null",
            "prior_portfolio_state_sha256": "char(64) not null",
            "reason_codes": "jsonb not null",
            "run_id": "uuid not null",
            "track": "text not null",
        },
        "layer": "DERIVED",
        "primary_key": ["run_id", "track", "decision_time"],
        "purpose": "The authoritative action, with everything needed to replay it.",
    },
    "prospective_stop_event": {
        "append_only": True,
        "columns": {
            "active_stop": "numeric(38,18) not null",
            "active_stop_identity": "text not null",
            "available_provider_ids": "jsonb not null",
            "candidate_position_state": "text not null",
            "candidate_stop_outcome": "text null",
            "classification": "text not null",
            "classifier_definition_sha256": "char(64) not null",
            "classifier_version": "text not null",
            "consensus_stop_outcome": "text not null",
            "control_position_state": "text not null",
            "decision_time": "timestamptz not null",
            "direction": "text not null",
            "event_id": "char(64) not null",
            "gap_through_state": "text not null",
            "first_divergence_decision_time": "timestamptz null",
            "missing_provider_ids": "jsonb not null",
            "non_touching_provider_ids": "jsonb not null",
            "observation_time": "timestamptz not null",
            "provider_stop_outcomes": "jsonb not null",
            "prior_observable_maximum_gap_seconds": "integer not null",
            "prior_observable_observation_time": "timestamptz not null",
            "prior_observable_owner": "text not null",
            "prior_observable_price": "numeric(38,18) null",
            "prior_observable_provider_ids": "jsonb not null",
            "reason_codes": "jsonb not null",
            "run_id": "uuid not null",
            "touching_provider_ids": "jsonb not null",
            "track": "text not null",
            "universe_anchor": "text not null",
        },
        "layer": "DERIVED",
        "primary_key": ["run_id", "track", "observation_time"],
        "purpose": "One mechanically classified stop-evaluation slot.",
    },
    "prospective_metric_comparison": {
        "append_only": True,
        "columns": {
            "candidate_reference_identity": "text not null",
            "comparability": "jsonb not null",
            "control_reference_identity": "text not null",
            "corpus_protocol_sha256": "char(64) not null",
            "denominator": "bigint null",
            "metric": "text not null",
            "not_comparable_count": "bigint not null",
            "numerator": "bigint null",
            "run_id": "uuid not null",
            "undefined_reason": "text null",
            "universe": "text not null",
            "value": "numeric(38,18) null",
            "window_end": "timestamptz not null",
            "window_start": "timestamptz not null",
        },
        "layer": "DERIVED",
        "primary_key": ["run_id", "metric", "window_start", "window_end"],
        "purpose": (
            "One Stage-B measurement with the complete comparability evidence "
            "beside it. A null value carries an undefined_reason and never 0."
        ),
    },
}


def data_schema_contract() -> dict[str, Any]:
    payload = {
        "append_only_raw_tables": list(_APPEND_ONLY_RAW_TABLES),
        "collection_entry_bindings": {
            "corpus_protocol_review_sha256": "independent PASS review of exact corpus_protocol_sha256",
            "postp1_004_implementation_review_sha256": "independent PASS review of exact collector implementation",
            "sufficiency_governance_review_sha256": "independent PASS review of exact sufficiency_governance_sha256",
            "required_relation": "ALL_THREE_BINDINGS_REQUIRED",
        },
        "database": "postgresql",
        "implementation_state": SCHEMA_IMPLEMENTATION_STATE,
        "redis_required": False,
        "schema": CORPUS_SCHEMA,
        "schema_version": "PROSPECTIVE_INTEGRATION_CORPUS_SCHEMA_V1",
        "table_prefix": CORPUS_TABLE_PREFIX,
        "tables": _TABLE_CONTRACT,
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


# ===========================================================================
# 13. collector boundary, provenance and deterministic replay
# ===========================================================================

CAPTURE_STAGE = "CAPTURE"
DERIVE_STAGE = "DERIVE"
EVALUATE_STAGE = "EVALUATE"
COLLECTOR_STAGES = (CAPTURE_STAGE, DERIVE_STAGE, EVALUATE_STAGE)

COLLECTOR_INTERFACE = {
    CAPTURE_STAGE: {
        "entry_point": "collect_decision_snapshot(decision_time)",
        "may_read": ["external sources", "prospective_run"],
        "may_write": list(_APPEND_ONLY_RAW_TABLES),
        "postcondition": (
            "Every qualifying raw observation for that decision_time is durably "
            "persisted with observation_time and available_at before any derived "
            "record exists, so no future outcome can alter what was captured."
        ),
        "reads_reference_identity": False,
    },
    DERIVE_STAGE: {
        "entry_point": "derive_decision_evidence(run_id, decision_time)",
        "may_read": list(_APPEND_ONLY_RAW_TABLES),
        "may_write": [
            name
            for name, row in _TABLE_CONTRACT.items()
            if row["layer"] == "DERIVED" and name != "prospective_metric_comparison"
        ],
        "postcondition": (
            "Derived records reference raw record identities and digests; they "
            "never rewrite a raw row."
        ),
        "reads_reference_identity": True,
    },
    EVALUATE_STAGE: {
        "entry_point": "evaluate_stage_b(run_id, window)",
        "may_read": list(_TABLE_CONTRACT),
        "may_write": ["prospective_metric_comparison"],
        "postcondition": (
            "Measurement semantics are read from the frozen protocol hash; the "
            "evaluator authors none."
        ),
        "reads_reference_identity": True,
    },
}

EVIDENCE_IDENTITY_FIELDS = (
    "configuration_identity",
    "corpus_protocol_sha256",
    "decision_time",
    "execution_version",
    "input_snapshot_sha256",
    "lifecycle_version",
    "output_sha256",
    "prior_portfolio_state_sha256",
    "raw_source_identities",
    "reference_identity",
    "risk_version",
    "strategy_version",
)

PROVENANCE_DETECTION_REQUIREMENTS = (
    "deletion",
    "duplicate observation",
    "late arrival",
    "mutation",
    "revision",
    "source replacement",
)

REPLAY_CONTRACT = {
    "guarantee": (
        "Every derived record regenerates byte-identically from the immutable "
        "raw rows, the frozen protocol hash and the declared version identities."
    ),
    "mutable_application_state_permitted": False,
    "numerical_invariance": [
        "ambient Decimal context",
        "PYTHONHASHSEED",
        "dictionary iteration order",
        "provider order",
        "process restart",
        "working directory",
    ],
    "replay_inputs": [
        "prospective_run",
        "prospective_decision_observation",
        "prospective_source_input_snapshot",
        "prospective_data_quality_event",
    ],
}

STAGE_B_EVALUATION_CONTRACT_VERSION = "PROSPECTIVE_STAGE_B_EVALUATION_CONTRACT_V1"

FUTURE_WORKFLOW = (
    "POSTP1-001R CORRECTED PROTOCOL",
    "REPEAT INDEPENDENT XHIGH REVIEW OF EXACT CORRECTED PROTOCOL HASH",
    "POSTP1-003 PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1",
    "INDEPENDENT XHIGH REVIEW OF EXACT SUFFICIENCY-GOVERNANCE HASH",
    "POSTP1-004 SCHEMA + COLLECTORS + DECISION SNAPSHOT IMPLEMENTATION",
    "INDEPENDENT IMPLEMENTATION REVIEW",
    "COLLECTION AUTHORIZATION",
    "PROSPECTIVE COLLECTION AND WARMUP CAPTURE",
    "EVIDENCE SUFFICIENCY CHECK",
    "STAGE-B EVALUATION",
    "IF PASS: candidate/reference research may proceed under a separately "
    "authorized protocol",
    "FORMAL POST-CERTIFICATION LIVE-SHADOW GATE WHEN APPLICABLE",
)


def stage_b_evaluation_contract() -> dict[str, Any]:
    """Predeclare the evaluator so it can never author a measurement semantic."""

    contracts = metric_evidence_contracts()["contracts"]
    metrics = {}
    for metric in TARGET_METRICS:
        contract = contracts[metric]
        metrics[metric] = {
            "denominator": contract["denominator"],
            "direction": contract["direction"],
            "input_artifact": (
                "prospective_stop_event"
                if metric in STOP_EVENT_METRICS
                else "prospective_strategy_evaluation, prospective_risk_evaluation, "
                "prospective_trade_action"
            ),
            "insufficient_rule": contract["insufficient_rule"],
            "metric_owner": contract["evidence_owner"],
            "numerator": contract["numerator"],
            "reason_vocabulary": contract["reason_vocabulary"],
            "statistic": contract["statistic"],
            "threshold": contract["threshold"],
            "universe_filter": contract["universe"],
        }
    payload = {
        "evaluator_may_change_measurement_semantics": False,
        "executed_on_real_prospective_data_by_this_task": False,
        "metrics": metrics,
        "output_table": "prospective_metric_comparison",
        "protocol_version": PROTOCOL_VERSION,
        "schema_version": STAGE_B_EVALUATION_CONTRACT_VERSION,
        "warmup_entry_requirement": (
            "WARMUP_HISTORY_COMPLETE must be true before a slot may enter any "
            "metric's evaluable universe"
        ),
        "warmup_history_definition_sha256": warmup_history_contract()[
            "definition_sha256"
        ],
        "workflow": list(FUTURE_WORKFLOW),
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


# ===========================================================================
# 14. child contract artifacts
# ===========================================================================


def decision_universe_contract() -> dict[str, Any]:
    cadences = {}
    for cadence in DECISION_CADENCES:
        cadences[cadence] = {
            "bar_close_rule": (
                f"a {CADENCE_BAR_TIMEFRAME[cadence]} canonical session closes one "
                "interval after its start"
            ),
            "bar_timeframe": CADENCE_BAR_TIMEFRAME[cadence],
            "decision_delay_seconds": DECISION_DELAY_SECONDS,
            "decision_time_rule": (
                "observation_time + bar interval + decision delay"
            ),
            "session_owner": CANONICAL_SESSION_OWNER,
        }
    payload = {
        "clock_alignment": (
            "Canonical UTC sessions: hourly bars on the exact hour, daily "
            "sessions opening 00:00 UTC, weekly sessions Monday 00:00 UTC."
        ),
        "decision_cadences": cadences,
        "decision_delay_owner": DECISION_DELAY_OWNER,
        "decision_grid_owner": DECISION_GRID_OWNER,
        "denominator_independence_rule": (
            "No universe predicate reads a comparison outcome. A timestamp can "
            "never enter or leave a denominator because the candidate and "
            "control outputs happen to agree or disagree."
        ),
        "duplicate_policy": DUPLICATE_POLICY,
        "late_data_policy": LATE_DATA_POLICY,
        "missing_data_policy": MISSING_DATA_POLICY,
        "not_comparable_reasons": list(NOT_COMPARABLE_REASONS),
        "not_evaluable_reasons": list(NOT_EVALUABLE_REASONS),
        "observation_states": list(OBSERVATION_STATES),
        "observation_unit": OBSERVATION_UNIT,
        "pit_policy_owner": PIT_POLICY_OWNER,
        "pit_policy_version": POINT_IN_TIME_POLICY_VERSION,
        "pit_rule": PIT_RULE,
        "protocol_version": PROTOCOL_VERSION,
        "reason_vocabulary": list(OBSERVATION_REASON_VOCABULARY),
        "revision_policy": REVISION_POLICY,
        "schema_version": "PROSPECTIVE_INTEGRATION_DECISION_UNIVERSE_V1",
        "scheduled_slot_census_required": True,
        "timezone": CORPUS_TIMEZONE,
        "universes": _UNIVERSE_DEFINITIONS,
        "warmup_history": warmup_history_contract(),
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def stop_event_taxonomy() -> dict[str, Any]:
    payload = {
        "classifier": stop_event_classifier_identity(),
        "event_universes": {
            UNIVERSE_CROSS_MARKET_EVENTS: EVENT_CROSS_MARKET,
            UNIVERSE_GAP_THROUGH_EVENTS: GAP_THROUGH_EVENT,
            UNIVERSE_ISOLATED_VENUE_EVENTS: EVENT_ISOLATED_VENUE,
        },
        "hand_picked_development_events_used": False,
        "missing_provider_handling": (
            "A missing required provider is named in missing_provider_ids and "
            "never imputed. Below the provider quorum the slot is "
            f"{EVENT_NOT_CLASSIFIABLE} and enters no denominator. A one-touch/"
            "one-non-touch/one-missing slot is also NOT_CLASSIFIABLE because "
            "the observed non-touching set does not satisfy the confirmation "
            "quorum needed to establish isolation."
        ),
        "predecessor_replaced": (
            "btc_predictor.research.reference_composite_empirical."
            "KNOWN_DEVELOPMENT_EVENTS"
        ),
        "protocol_version": PROTOCOL_VERSION,
        "schema_version": "PROSPECTIVE_INTEGRATION_STOP_EVENT_TAXONOMY_V1",
        "stop_outcomes": list(STOP_OUTCOMES),
        "gap_through_derivation": GAP_THROUGH_DERIVATION,
        "post_divergence_semantics": POST_DIVERGENCE_STOP_SEMANTICS,
        "stop_reference_rule": (
            "The stop compared at a slot is the control-reference track's active "
            "stop under the authoritative lifecycle owner, never a hand-chosen "
            "reviewed level and never a candidate-owned denominator anchor."
        ),
        "stop_universe_derivation": STOP_EVENT_UNIVERSE_DERIVATION,
        "tie_rule": (
            "Reaching the stop is a non-strict comparison on the stop-relevant "
            "extreme, so a venue that touches exactly the stop counts as "
            "reaching it, matching the repository's own stop-touch convention."
        ),
        "venue_disagreement_handling": (
            "Disagreement among available providers is the measurement, not an "
            "error: the touching set, the median consensus and every provider's "
            "own outcome are persisted."
        ),
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def input_snapshot_schema() -> dict[str, Any]:
    payload = {
        "champion_identity": CHAMPION_IDENTITY,
        "champion_identity_binding_rule": CHAMPION_IDENTITY_BINDING_RULE,
        "derived_state_inputs": DERIVED_STATE_INPUTS,
        "excluded_input_families": EXCLUDED_INPUT_FAMILIES,
        "feature_contract_owner": (
            "btc_predictor.research.feature_matrix.INITIAL_FEATURE_NAMES"
        ),
        "feature_input_coverage": feature_input_coverage_contract(),
        "non_price_input_sources": NON_PRICE_INPUT_SOURCES,
        "pit_availability_fields": ["observation_time", "available_at", "ingested_at"],
        "pit_rule": PIT_RULE,
        "portfolio_state_inputs": list(PORTFOLIO_STATE_INPUTS),
        "price_input_sources": PRICE_INPUT_SOURCES,
        "protocol_version": PROTOCOL_VERSION,
        "provenance_detection_requirements": list(PROVENANCE_DETECTION_REQUIREMENTS),
        "schema_version": "PROSPECTIVE_INTEGRATION_INPUT_SNAPSHOT_V1",
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def portfolio_track_contract() -> dict[str, Any]:
    payload = {
        "divergence_evidence_fields": list(DIVERGENCE_EVIDENCE_FIELDS),
        "divergence_policy": DIVERGENCE_POLICY,
        "exogenous_divergence_reason": EXOGENOUS_DIVERGENCE_REASON,
        "initial_state": INITIAL_PORTFOLIO_STATE,
        "initial_state_rationale": INITIAL_PORTFOLIO_STATE_RATIONALE,
        "initial_state_sha256": _digest(INITIAL_PORTFOLIO_STATE),
        "protocol_version": PROTOCOL_VERSION,
        "reference_identity_requirements": list(REFERENCE_IDENTITY_REQUIREMENTS),
        "reference_identity_source": REFERENCE_IDENTITY_SOURCE,
        "reference_identity_state": REFERENCE_IDENTITY_STATE,
        "reference_roles": list(REFERENCE_ROLES),
        "resynchronization_policy": RESYNCHRONIZATION_POLICY,
        "schema_version": "PROSPECTIVE_INTEGRATION_PORTFOLIO_TRACK_V1",
        "shared_exogenous_input_families": list(SHARED_EXOGENOUS_INPUT_FAMILIES),
        "shared_exogenous_input_rule": SHARED_EXOGENOUS_INPUT_RULE,
        "tracks": {
            CANDIDATE_TRACK: {
                "reference_role": CANDIDATE_REFERENCE_ROLE,
                "starts_from_initial_state": True,
            },
            CONTROL_TRACK: {
                "reference_role": CONTROL_REFERENCE_ROLE,
                "starts_from_initial_state": True,
            },
        },
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


# ===========================================================================
# 15. semantic diff against the V5 Stage-B blockers
# ===========================================================================


def semantic_diff_from_v5_blockers() -> dict[str, Any]:
    """Map each unresolved V5 Stage-B gate to its prospective evidence definition."""

    authority = historical_gate_authority()
    contracts = metric_evidence_contracts()["contracts"]
    rows = {}
    for metric in TARGET_METRICS:
        gate = authority[metric]
        contract = contracts[metric]
        rows[metric] = {
            "historical_unresolved_gate": {
                "definition": gate["definition"],
                "direction": gate["direction"],
                "hard": gate["hard"],
                "source_authority": gate["source_authority"],
                "threshold": gate["threshold"],
                "v5_state": "UNRESOLVED_NO_EXECUTABLE_MEASUREMENT_OWNER",
            },
            "prospective_executable_definition": {
                "decision_universe": contract["universe"],
                "denominator": contract["denominator"],
                "evidence_owner": contract["evidence_owner"],
                "input_corpus": (
                    "prospective_source_input_snapshot + "
                    "prospective_portfolio_state"
                ),
                "numerator": contract["numerator"],
                "pit_schema": PIT_RULE,
                "statistic": contract["statistic"],
            },
            "supplied": [
                "decision_universe",
                "denominator",
                "event_universe" if metric in STOP_EVENT_METRICS else "input_corpus",
                "numerator",
                "pit_schema",
            ],
            "unchanged": {
                "definition": gate["definition"] == contract["historical_definition"],
                "direction": gate["direction"] == contract["direction"],
                "hard": gate["hard"] == contract["hard"],
                "threshold": gate["threshold"] == contract["threshold"],
            },
        }
    changed = {
        "direction_change_count": sum(
            0 if row["unchanged"]["direction"] else 1 for row in rows.values()
        ),
        "hard_role_change_count": sum(
            0 if row["unchanged"]["hard"] else 1 for row in rows.values()
        ),
        "metric_intent_change_count": sum(
            0 if row["unchanged"]["definition"] else 1 for row in rows.values()
        ),
        "threshold_change_count": sum(
            0 if row["unchanged"]["threshold"] else 1 for row in rows.values()
        ),
    }
    if any(changed.values()):
        raise ProspectiveCorpusError(
            f"the prospective protocol moved a historical gate value: {changed}"
        )
    payload = {
        **changed,
        "btc019_reopened": False,
        "btc019_terminal_classification": BTC019_TERMINAL_CLASSIFICATION,
        "gate_count": len(rows),
        "protocol_version": PROTOCOL_VERSION,
        "rows": rows,
        "schema_version": "PROSPECTIVE_INTEGRATION_SEMANTIC_DIFF_V1",
        "source_protocol": "BTC_REFERENCE_COMPOSITE_V5",
        "source_protocol_definition_sha256": FROZEN_V5_DEFINITION_SHA256,
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


# ===========================================================================
# 16. collection and aggregation guards
# ===========================================================================


def assert_collection_not_authorized() -> None:
    """Refuse collection while the freeze has not passed independent review."""

    if COLLECTION_AUTHORIZED or CURRENT_LIFECYCLE_STATE != LIFECYCLE_FROZEN:
        raise ProspectiveCorpusError(
            "this revision must remain a pre-data protocol; a collecting "
            "revision requires its own reviewed hash"
        )


def assert_lifecycle_transition(current: str, target: str) -> None:
    if current not in LIFECYCLE_STATES or target not in LIFECYCLE_STATES:
        raise ProspectiveCorpusError(f"lifecycle states are {LIFECYCLE_STATES}")
    if target == LIFECYCLE_COLLECTING:
        raise CollectionNotAuthorizedError(
            f"{LIFECYCLE_COLLECTING} requires {COLLECTION_ENTRY_REQUIREMENT}"
        )
    if target not in LIFECYCLE_TRANSITIONS[current]:
        raise ProspectiveCorpusError(
            f"{current} may not transition to {target}"
        )


def aggregate_stage_b_metric(
    metric: str,
    *,
    numerator: int | None,
    denominator: int | None,
    synthetic: bool,
    lifecycle_state: str = CURRENT_LIFECYCLE_STATE,
) -> dict[str, Any]:
    """Compose one Stage-B measurement from an already-counted numerator pair.

    Real qualifying evidence cannot be aggregated at this lifecycle state: the
    protocol has not been independently reviewed, so producing a real Stage-B
    aggregate now would be an outcome the freeze was supposed to precede.  Only
    explicitly synthetic counts run, and a zero denominator is never a PASS and
    never the value ``0``.
    """

    if metric not in TARGET_METRICS:
        raise ProspectiveCorpusError(f"{metric!r} is not a target Stage-B metric")
    if not isinstance(synthetic, bool):
        raise ProspectiveCorpusError("synthetic must be an explicit boolean")
    if not synthetic and lifecycle_state not in (
        LIFECYCLE_SUFFICIENT,
        LIFECYCLE_EVALUATED,
    ):
        raise CollectionNotAuthorizedError(
            "no real Stage-B aggregate may be produced before the protocol is "
            f"{LIFECYCLE_SUFFICIENT}; this revision is {lifecycle_state}"
        )
    if isinstance(numerator, bool) or isinstance(denominator, bool):
        raise ProspectiveCorpusError("counts must be integers, not booleans")
    gate = historical_gate_authority()[metric]
    if denominator in (None, 0):
        return {
            "denominator": denominator,
            "direction": gate["direction"],
            "metric": metric,
            "numerator": numerator,
            "synthetic": synthetic,
            "threshold": gate["threshold"],
            "undefined_reason": UNDEFINED_INSUFFICIENT_EVIDENCE,
            "value": None,
        }
    if numerator is None:
        raise ProspectiveCorpusError("a defined denominator requires a numerator")
    if numerator < 0 or denominator < 0 or numerator > denominator:
        raise ProspectiveCorpusError("a rate requires 0 <= numerator <= denominator")
    with localcontext(_CONTEXT):
        value = Decimal(numerator) / Decimal(denominator)
    return {
        "denominator": denominator,
        "direction": gate["direction"],
        "metric": metric,
        "numerator": numerator,
        "synthetic": synthetic,
        "threshold": gate["threshold"],
        "undefined_reason": None,
        "value": str(value),
    }


def risk_size_p95(
    candidate_notionals: Sequence[Decimal],
    control_notionals: Sequence[Decimal],
) -> dict[str, Any]:
    """The frozen risk-size statistic over an already-filtered sizing universe.

    Both sequences are the sizing-evaluable universe in the same order, so every
    control notional is strictly positive by construction; a non-positive one is
    a protocol violation rather than a value to divide by.
    """

    if len(candidate_notionals) != len(control_notionals):
        raise ProspectiveCorpusError("the two sizing series must be aligned")
    if not candidate_notionals:
        return {
            "denominator": 0,
            "metric": RISK_SIZE_METRIC,
            "statistic": RISK_SIZE_STATISTIC,
            "undefined_reason": UNDEFINED_INSUFFICIENT_EVIDENCE,
            "value": None,
        }
    differences = []
    with localcontext(_CONTEXT):
        for candidate, control in zip(candidate_notionals, control_notionals, strict=True):
            _decimal(candidate, "candidate_position_notional")
            _decimal(control, "control_position_notional")
            if control <= 0:
                raise ProspectiveCorpusError(
                    "the sizing universe admits only strictly positive control "
                    "notionals"
                )
            differences.append(abs(candidate - control) / control)
    return {
        "denominator": len(differences),
        "metric": RISK_SIZE_METRIC,
        "statistic": RISK_SIZE_STATISTIC,
        "undefined_reason": None,
        "value": str(nearest_rank_percentile(differences, RISK_SIZE_PROBABILITY)),
    }


# ===========================================================================
# 17. the frozen protocol definition
# ===========================================================================


def protocol_definition() -> dict[str, Any]:
    """Build the top-level protocol, binding every material child hash."""

    assert_collection_not_authorized()
    assert_required_semantics_unambiguous()
    authority = historical_gate_authority()
    children = {
        "data_schema_contract": data_schema_contract(),
        "decision_universe": decision_universe_contract(),
        "evidence_sufficiency": evidence_sufficiency_contract(),
        "feature_input_coverage": feature_input_coverage_contract(),
        "input_snapshot_schema": input_snapshot_schema(),
        "metric_evidence_contracts": metric_evidence_contracts(),
        "portfolio_track_contract": portfolio_track_contract(),
        "semantic_diff_from_v5_blockers": semantic_diff_from_v5_blockers(),
        "stage_b_evaluation_contract": stage_b_evaluation_contract(),
        "stop_event_taxonomy": stop_event_taxonomy(),
        "warmup_history": warmup_history_contract(),
    }
    payload: dict[str, Any] = {
        "btc019": {
            "reopened": False,
            "sealed_sample_collected": False,
            "sealed_sample_opened": False,
            "successor_of_btc019": False,
            "terminal_classification": BTC019_TERMINAL_CLASSIFICATION,
        },
        "child_definition_sha256": {
            name: child["definition_sha256"] for name, child in children.items()
        },
        "collection_authorized": COLLECTION_AUTHORIZED,
        "collection_authorization_semantics": {
            "all_requirements_must_pass": True,
            "corpus_protocol_independently_certified": False,
            "postp1_004_implementation_independently_certified": False,
            "sufficiency_governance_definition_sha256": None,
            "sufficiency_governance_independently_certified": False,
            "warmup_or_nonqualifying_capture_exception": False,
        },
        "collection_entry_requirement": COLLECTION_ENTRY_REQUIREMENT,
        "collector_boundary": {
            "interface": COLLECTOR_INTERFACE,
            "stages": list(COLLECTOR_STAGES),
        },
        "evidence_identity_fields": list(EVIDENCE_IDENTITY_FIELDS),
        "final_classification": FINAL_CLASSIFICATION,
        "human_review_policy": HUMAN_REVIEW_POLICY,
        "lifecycle": {
            "current_state": CURRENT_LIFECYCLE_STATE,
            "states": list(LIFECYCLE_STATES),
            "transitions": {
                state: list(targets) for state, targets in LIFECYCLE_TRANSITIONS.items()
            },
        },
        "lineage": {
            "certified_v1_validator_definition_sha256": (
                CERTIFIED_V1_VALIDATOR_DEFINITION_SHA256
            ),
            "frozen_v2_definition_sha256": FROZEN_V2_DEFINITION_SHA256,
            "frozen_v3_definition_sha256": FROZEN_V3_DEFINITION_SHA256,
            "frozen_v4_definition_sha256": FROZEN_V4_DEFINITION_SHA256,
            "frozen_v5_definition_sha256": FROZEN_V5_DEFINITION_SHA256,
            "failed_prospective_protocol": {
                "definition_sha256": FAILED_PROTOCOL_DEFINITION_SHA256,
                "implementation_commit": FAILED_PROTOCOL_IMPLEMENTATION_COMMIT,
                "review": FAILED_PROTOCOL_REVIEW,
                "review_classification": FAILED_PROTOCOL_REVIEW_CLASSIFICATION,
                "retained": True,
                "superseded_before_collection": True,
            },
        },
        "historical_gate_authority": authority,
        "no_threshold_authored": True,
        "numerical_standards": {
            "decimal_precision": CORPUS_DECIMAL_PRECISION,
            "invariant_to": list(REPLAY_CONTRACT["numerical_invariance"]),
        },
        "observation_unit": OBSERVATION_UNIT,
        "post_hoc_contamination": {
            "change_procedure": CHANGE_PROCEDURE,
            "prohibited_after_collection_starts": list(
                PROHIBITED_AFTER_COLLECTION_STARTS
            ),
            "successor_protocol": SUCCESSOR_PROTOCOL_VERSION,
        },
        "program_ticket": PROGRAM_TICKET,
        "protocol_version": PROTOCOL_VERSION,
        "provenance_detection_requirements": list(PROVENANCE_DETECTION_REQUIREMENTS),
        "relationship_to_epic_t": {
            "epic_t_authority_change_required": False,
            "epic_t_modified": False,
            "epic_t_state": "CLOSED / PASS WITH NON-BLOCKING FINDINGS",
        },
        "relationship_to_phase_1": {
            "btc019_historical_reference_research": "TERMINALLY_BLOCKED",
            "phase_1_deterministic_implementation": "COMPLETE",
            "production_canonical_reference": "UNRESOLVED",
            "prospective_integration_evidence_program": "NEW_POST_PHASE_1_WORKSTREAM",
        },
        "replay_contract": REPLAY_CONTRACT,
        "research_only": True,
        "safety": {
            "btc019_sealed_data_accessed": False,
            "new_market_evidence_collected": False,
            "qualifying_observations_collected": False,
            "real_stage_b_outcomes_evaluated": False,
        },
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "sealed_sample_dependency": {
            "opens_btc019_on_stage_b_pass": False,
            "statement": (
                "The historical BTC-019 sealed sample remains NOT COLLECTED, NOT "
                "OPENED and NOT EVALUATED. This program does not authorize "
                "opening it and creates no automatic future dependency that "
                "would; any use of it requires a separate explicit governance "
                "decision."
            ),
        },
        "status": PROTOCOL_STATUS,
        "target_metrics": list(TARGET_METRICS),
        "workflow": list(FUTURE_WORKFLOW),
        "workstream": {"epic": WORKSTREAM, "name": WORKSTREAM_NAME},
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def protocol_hashes() -> dict[str, str]:
    """Every deterministic hash this protocol reports."""

    protocol = protocol_definition()
    hashes = dict(protocol["child_definition_sha256"])
    hashes["corpus_protocol"] = protocol["definition_sha256"]
    return dict(sorted(hashes.items()))


def verify_protocol_definition(persisted: Mapping[str, Any]) -> None:
    """Refuse a persisted protocol that does not reproduce from the module."""

    expected = protocol_definition()
    if dict(persisted) != expected:
        raise ProspectiveCorpusError("the persisted protocol does not reproduce")
    declared = dict(persisted)["definition_sha256"]
    if not _is_sha256(declared):
        raise ProspectiveCorpusError("definition_sha256 is not a SHA-256 digest")
    recomputed = dict(persisted)
    recomputed.pop("definition_sha256")
    if _digest(recomputed) != declared:
        raise ProspectiveCorpusError("definition_sha256 does not recompute")


# ===========================================================================
# 18. artifacts
# ===========================================================================

DATA_SCHEMA_FILENAME = "data_schema_contract.json"
STAGE_B_EVALUATION_FILENAME = "stage_b_evaluation_contract.json"

_CHILD_ARTIFACTS = (
    (METRIC_CONTRACTS_FILENAME, "metric_evidence_contracts"),
    (DATA_SCHEMA_FILENAME, "data_schema_contract"),
    (STAGE_B_EVALUATION_FILENAME, "stage_b_evaluation_contract"),
    (DECISION_UNIVERSE_FILENAME, "decision_universe_contract"),
    (STOP_EVENT_TAXONOMY_FILENAME, "stop_event_taxonomy"),
    (INPUT_SNAPSHOT_FILENAME, "input_snapshot_schema"),
    (PORTFOLIO_TRACK_FILENAME, "portfolio_track_contract"),
    (EVIDENCE_SUFFICIENCY_FILENAME, "evidence_sufficiency_contract"),
    (SEMANTIC_DIFF_FILENAME, "semantic_diff_from_v5_blockers"),
    (FEATURE_INPUT_COVERAGE_FILENAME, "feature_input_coverage_contract"),
    (WARMUP_HISTORY_FILENAME, "warmup_history_contract"),
)


_CHILD_KEY_BY_FILENAME = {
    METRIC_CONTRACTS_FILENAME: "metric_evidence_contracts",
    DATA_SCHEMA_FILENAME: "data_schema_contract",
    STAGE_B_EVALUATION_FILENAME: "stage_b_evaluation_contract",
    DECISION_UNIVERSE_FILENAME: "decision_universe",
    STOP_EVENT_TAXONOMY_FILENAME: "stop_event_taxonomy",
    INPUT_SNAPSHOT_FILENAME: "input_snapshot_schema",
    PORTFOLIO_TRACK_FILENAME: "portfolio_track_contract",
    EVIDENCE_SUFFICIENCY_FILENAME: "evidence_sufficiency",
    SEMANTIC_DIFF_FILENAME: "semantic_diff_from_v5_blockers",
    FEATURE_INPUT_COVERAGE_FILENAME: "feature_input_coverage",
    WARMUP_HISTORY_FILENAME: "warmup_history",
}


def _child_payloads() -> dict[str, dict[str, Any]]:
    return {
        filename: globals()[builder]() for filename, builder in _CHILD_ARTIFACTS
    }


def _report_markdown(protocol: Mapping[str, Any]) -> str:
    hashes = protocol["child_definition_sha256"]
    diff = semantic_diff_from_v5_blockers()
    lines = [
        f"# {PROTOCOL_VERSION}",
        "",
        f"- Program / ticket: `{PROGRAM_TICKET}` -- `{WORKSTREAM} -- {WORKSTREAM_NAME}`",
        f"- Status: `{PROTOCOL_STATUS}`",
        f"- Protocol hash: `{protocol['definition_sha256']}`",
        f"- Final classification: `{FINAL_CLASSIFICATION}`",
        f"- Threshold changes: `{diff['threshold_change_count']}`",
        f"- Direction changes: `{diff['direction_change_count']}`",
        f"- Hard-role changes: `{diff['hard_role_change_count']}`",
        f"- Metric-intent changes: `{diff['metric_intent_change_count']}`",
        "- Qualifying observations collected: no",
        "- Real Stage-B outcomes evaluated: no",
        "- BTC-019 reopened: no",
        "- BTC-019 sealed sample collected / opened: no / no",
        "",
        "## What this program is",
        "",
        "BTC-019 is historically terminal at "
        f"`{BTC019_TERMINAL_CLASSIFICATION}` and is not repaired here. This is a "
        "new post-Phase-1 prospective evidence program that creates, forward in "
        "time, the deterministic integration evidence that did not exist when "
        "BTC-019 terminated. It is not `BTC_REFERENCE_COMPOSITE_V6`: no frozen "
        "V3, V4, V5 or certified V1 byte moves, and no approval threshold, "
        "direction or hard role changes.",
        "",
        "## Failed lineage retained",
        "",
        f"- Failed protocol hash: `{FAILED_PROTOCOL_DEFINITION_SHA256}`",
        f"- Failed implementation commit: `{FAILED_PROTOCOL_IMPLEMENTATION_COMMIT}`",
        f"- Review: `{FAILED_PROTOCOL_REVIEW}` / `{FAILED_PROTOCOL_REVIEW_CLASSIFICATION}`",
        "- Superseded before collection: `YES`",
        "",
        "## Corrected ownership and input closure",
        "",
        "- `raw.liquidations` is a required append-only PIT capture family.",
        "- Every `INITIAL_FEATURE_NAMES` member is bound to its transitive raw "
        "input families and one prospective capture contract.",
        "- CVD cadence is exact-hour UTC with the authoritative 20-period z-score window.",
        f"- Trade-action comparison owner: `{TRADE_ACTION_COMPARISON_OWNER_VERSION}`.",
        f"- Trade-eligibility permission owner: `{TRADE_ELIGIBILITY_COMPOSITE_OWNER_VERSION}`.",
        f"- Stop-event anchor: `{STOP_EVENT_UNIVERSE_ANCHOR}`.",
        f"- Gap-through prior owner: `{PRIOR_OBSERVABLE_OWNER}`; maximum gap: `3600s`.",
        "",
        "## Frozen child contracts",
        "",
    ]
    for name in sorted(hashes):
        lines.append(f"- `{name}`: `{hashes[name]}`")
    lines += [
        "",
        "## The eight measurements",
        "",
        "| metric | universe | statistic | threshold | direction |",
        "| --- | --- | --- | --- | --- |",
    ]
    contracts = metric_evidence_contracts()["contracts"]
    for metric in TARGET_METRICS:
        row = contracts[metric]
        lines.append(
            f"| `{metric}` | `{row['universe']}` | {row['statistic']} | "
            f"`{row['threshold']}` | `{row['direction']}` |"
        )
    lines += [
        "",
        "## Evidence sufficiency",
        "",
        "Arithmetic evaluability is frozen here: a complete scheduled-slot "
        "census, complete PIT inputs, frozen warmup completion and both tracks' "
        "owner outputs. A zero denominator is "
        f"`{UNDEFINED_INSUFFICIENT_EVIDENCE}` and never a PASS; this protocol "
        "chooses no certification minimum.",
        "",
        "Per-metric certification minimums are deliberately not chosen here. "
        "Selecting a rate gate's minimum n is its own pre-data governance task "
        "in this repository, so all eight are marked "
        f"`{REPORTABLE_NOT_CERTIFIABLE}` and deferred to "
        f"`{SUFFICIENCY_GOVERNANCE_SUCCESSOR}`. No calendar minimum is imported "
        "from Stage-C's `live_shadow_days >= 90`.",
        "",
        "## Collection is not authorized",
        "",
        f"Lifecycle state is `{CURRENT_LIFECYCLE_STATE}`. Entering "
        f"`{LIFECYCLE_COLLECTING}` requires `{COLLECTION_ENTRY_REQUIREMENT}`. "
        "The sealed BTC-019 sample stays NOT COLLECTED, NOT OPENED and NOT "
        "EVALUATED, and a Stage-B PASS here does not open it.",
        "",
        f"Final classification: `{FINAL_CLASSIFICATION}`",
        "",
    ]
    return "\n".join(lines)


def write_artifacts(output_dir: Path) -> dict[str, Any]:
    protocol = protocol_definition()
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {PROTOCOL_FILENAME: protocol, **_child_payloads()}
    for filename, payload in payloads.items():
        (output_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
        )
    (output_dir / REPORT_FILENAME).write_text(
        _report_markdown(protocol), encoding="utf-8"
    )
    return protocol


def restore_artifacts(output_dir: Path) -> dict[str, Any]:
    protocol = json.loads(
        (output_dir / PROTOCOL_FILENAME).read_text(encoding="ascii")
    )
    verify_protocol_definition(protocol)
    for filename, expected in _child_payloads().items():
        persisted = json.loads((output_dir / filename).read_text(encoding="ascii"))
        if persisted != expected:
            raise ProspectiveCorpusError(f"persisted {filename} does not reproduce")
        if protocol["child_definition_sha256"].get(
            _CHILD_KEY_BY_FILENAME[filename]
        ) != expected["definition_sha256"]:
            raise ProspectiveCorpusError(
                f"the protocol does not bind the persisted {filename} hash"
            )
    if (output_dir / REPORT_FILENAME).read_text(encoding="utf-8") != _report_markdown(
        protocol
    ):
        raise ProspectiveCorpusError("the persisted report does not reproduce")
    return protocol


def main() -> None:  # pragma: no cover - operational artifact writer
    root = Path(__file__).resolve().parents[2]
    protocol = write_artifacts(root / OUTPUT_NAMESPACE)
    print(protocol["definition_sha256"])


if __name__ == "__main__":  # pragma: no cover
    main()
