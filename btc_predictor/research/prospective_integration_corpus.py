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
module refuses every real aggregation until then.
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

from btc_predictor.research import reference_composite as _rc
from btc_predictor.research import reference_composite_v2 as _v2


# ---------------------------------------------------------------------------
# identity
# ---------------------------------------------------------------------------

PROTOCOL_VERSION = "PROSPECTIVE_INTEGRATION_CORPUS_V1"
PROTOCOL_SCHEMA_VERSION = "PROSPECTIVE_INTEGRATION_CORPUS_V1_PROTOCOL_DEFINITION_V1"
PROTOCOL_STATUS = "FROZEN_PRE_DATA_PROTOCOL"
PROGRAM_TICKET = "POSTP1-001"
WORKSTREAM = "EPIC X"
WORKSTREAM_NAME = "PROSPECTIVE INTEGRATION EVIDENCE"
FINAL_CLASSIFICATION = "PROSPECTIVE_INTEGRATION_CORPUS_V1_READY_FOR_XHIGH_REVIEW"
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


# ---------------------------------------------------------------------------
# lifecycle
# ---------------------------------------------------------------------------

LIFECYCLE_DRAFT = "DRAFT"
LIFECYCLE_FROZEN = "FROZEN"
LIFECYCLE_COLLECTING = "COLLECTING"
LIFECYCLE_SUFFICIENT = "SUFFICIENT_FOR_EVALUATION"
LIFECYCLE_EVALUATED = "EVALUATED"
LIFECYCLE_CLOSED = "CLOSED"
LIFECYCLE_STATES = (
    LIFECYCLE_DRAFT,
    LIFECYCLE_FROZEN,
    LIFECYCLE_COLLECTING,
    LIFECYCLE_SUFFICIENT,
    LIFECYCLE_EVALUATED,
    LIFECYCLE_CLOSED,
)
LIFECYCLE_TRANSITIONS = {
    LIFECYCLE_DRAFT: (LIFECYCLE_FROZEN,),
    LIFECYCLE_FROZEN: (LIFECYCLE_COLLECTING, LIFECYCLE_CLOSED),
    LIFECYCLE_COLLECTING: (LIFECYCLE_SUFFICIENT, LIFECYCLE_CLOSED),
    LIFECYCLE_SUFFICIENT: (LIFECYCLE_EVALUATED, LIFECYCLE_CLOSED),
    LIFECYCLE_EVALUATED: (LIFECYCLE_CLOSED,),
    LIFECYCLE_CLOSED: (),
}
CURRENT_LIFECYCLE_STATE = LIFECYCLE_FROZEN
COLLECTION_AUTHORIZED = False
COLLECTION_ENTRY_REQUIREMENT = (
    "INDEPENDENT_XHIGH_REVIEW_OF_THIS_EXACT_PROTOCOL_HASH_MUST_PASS_FIRST"
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
            "data-quality gate has not failed for either track."
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
            "Setup-evaluable daily slots where both tracks are in a pre-position "
            "lifecycle state, so a new-entry permission is defined for both."
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
            "deterministic action from the authoritative recommendation "
            "vocabulary, whether flat or in position."
        ),
        "parent_universe": UNIVERSE_DATA_VALID,
    },
    UNIVERSE_STOP_ACTIVE_SLOTS: {
        "cadence": [STOP_HOURLY_CADENCE],
        "definition": (
            "Hourly slots where the track under evaluation carries an active "
            "stop on an open position."
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
        "consuming_features": ["REGIME_SCORE", "REGIME_SMOOTHED_SCORE"],
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
        "capture_state": "REQUIRES_NEW_COLLECTOR_IN_FIRST_COLLECTION_TICKET",
        "capture_state_reason": (
            "btc_predictor.features.flow.CvdObservation is a feature-layer "
            "boundary with no raw PIT table and no collector in this repository, "
            "so CVD_SPREAD cannot be reproduced from any persisted source today. "
            "The corpus declares the capture contract; it does not fabricate the "
            "series and it does not drop the feature from the champion."
        ),
        "consuming_features": ["CVD_SPREAD"],
        "fields": ["cvd_usd", "market_type"],
        "identity_fields": ["market_type", "provider"],
        "missing_policy": "EXPLICIT_STATUS_NO_ZERO_FILL",
        "normalization_owner": "btc_predictor.features.flow",
        "pit_rule": PIT_RULE,
        "provenance_fields": ["observation_time", "available_at", "ingested_at", "source"],
        "raw_table": "research.prospective_source_input_snapshot (new capture)",
        "revision_policy": "APPEND_ONLY_NEW_REVISION_ROW_PER_RESTATEMENT",
        "units": "USD cumulative volume delta",
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
    "liquidations": (
        "raw.liquidations exists but the frozen BTC-048 feature contract names no "
        "feature that consumes it, so it is not part of the required decision "
        "reproduction set."
    ),
    "new_alpha_datasets": (
        "No dataset outside the frozen Phase-1 feature contract may enter the "
        "corpus; adding one is a PROSPECTIVE_INTEGRATION_CORPUS_V2 change."
    ),
}


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
# evaluating track's own active stop.

STOP_EVENT_CLASSIFIER_VERSION = "PROSPECTIVE_STOP_EVENT_CLASSIFIER_V1"
STOP_EVENT_CLASSIFIER_OWNER = (
    "btc_predictor.research.prospective_integration_corpus.classify_stop_event"
)

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
EVENT_NOT_CLASSIFIABLE = "NOT_CLASSIFIABLE_INSUFFICIENT_PROVIDER_QUORUM"
STOP_EVENT_CLASSIFICATIONS = (
    EVENT_CROSS_MARKET,
    EVENT_ISOLATED_VENUE,
    EVENT_NONE,
    EVENT_NOT_CLASSIFIABLE,
)

GAP_THROUGH_EVENT = "GAP_THROUGH_STOP_EVENT"
GAP_THROUGH_NOT_PRESENT = "NOT_GAP_THROUGH"
GAP_THROUGH_NOT_EVALUABLE = "NOT_EVALUABLE_NO_PRIOR_OBSERVABLE_PRICE"
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
    "Otherwise, ISOLATED_VENUE_STOP_EVENT when exactly one available required "
    "provider reaches it, so the confirmation quorum is measurably absent.",
    "Otherwise NO_STOP_EVENT. CROSS_MARKET_CONFIRMED_STOP_EVENT and "
    "ISOLATED_VENUE_STOP_EVENT are mutually exclusive by construction.",
    "GAP_THROUGH_STOP_EVENT is orthogonal and declared separately: it describes "
    "how the stop was crossed, not how many venues reached it, so a slot may "
    "carry both labels and neither universe silently drops the other's event.",
)


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
    """One hourly stop-evaluation slot for one portfolio track."""

    observation_time: datetime
    track: str
    direction: str
    active_stop: Decimal
    providers: tuple[ProviderObservation, ...]
    prior_observable_price: Decimal | None = None
    prior_observable_observation_time: datetime | None = None


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
    if slot.track not in PORTFOLIO_TRACKS:
        raise ProspectiveCorpusError(f"track must be one of {PORTFOLIO_TRACKS}")
    if slot.direction not in STOP_DIRECTIONS:
        raise ProspectiveCorpusError(f"direction must be one of {STOP_DIRECTIONS}")
    _decimal(slot.active_stop, "active_stop")
    decision_time = decision_time_for(slot.observation_time, STOP_HOURLY_CADENCE)

    seen: set[str] = set()
    for observation in slot.providers:
        if not isinstance(observation, ProviderObservation):
            raise ProspectiveCorpusError("providers must be ProviderObservation rows")
        if observation.provider_id not in REQUIRED_PROVIDER_IDS:
            raise ProspectiveCorpusError(
                f"provider {observation.provider_id!r} is not a required provider"
            )
        if observation.provider_id in seen:
            raise ProspectiveCorpusError(
                f"duplicate observation for {observation.provider_id!r} at one slot"
            )
        seen.add(observation.provider_id)
        _require_utc(observation.observation_time, "provider observation_time")
        _require_utc(observation.available_at, "provider available_at")
        if observation.observation_time != slot.observation_time:
            raise ProspectiveCorpusError(
                "a provider observation must belong to its own slot"
            )
        if observation.available_at > decision_time:
            raise ProspectiveCorpusError(
                f"{observation.provider_id!r} was not available at the decision time"
            )
        for field_name in ("open", "high", "low", "close"):
            _decimal(getattr(observation, field_name), field_name)

    if slot.prior_observable_price is not None:
        _decimal(slot.prior_observable_price, "prior_observable_price")
        if slot.prior_observable_observation_time is None:
            raise ProspectiveCorpusError(
                "a prior observable price must carry its own observation_time"
            )
        _require_utc(
            slot.prior_observable_observation_time,
            "prior_observable_observation_time",
        )
        if slot.prior_observable_observation_time >= slot.observation_time:
            raise ProspectiveCorpusError(
                "the prior observable price must precede this slot"
            )
    elif slot.prior_observable_observation_time is not None:
        raise ProspectiveCorpusError(
            "prior_observable_observation_time requires a prior_observable_price"
        )
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
    observations and the evaluating track's own active stop, never a candidate
    reference and never an outcome.  Provider order, dictionary order and the
    ambient ``Decimal`` context cannot move any field.
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
        elif len(touching) == 1:
            classification = EVENT_ISOLATED_VENUE
            reason_codes.append("CONFIRMATION_QUORUM_ABSENT")
        else:
            classification = EVENT_NONE
    if missing:
        reason_codes.append("REQUIRED_PROVIDER_MISSING")

    if classification == EVENT_NOT_CLASSIFIABLE:
        gap_state = GAP_THROUGH_NOT_EVALUABLE
        consensus_stop_outcome = STOP_OUTCOME_UNDEFINED
        provider_stop_outcomes: dict[str, str] = {}
    elif slot.prior_observable_price is None:
        gap_state = GAP_THROUGH_NOT_EVALUABLE
        reason_codes.append("NO_PRIOR_OBSERVABLE_REFERENCE_PRICE")
        consensus_stop_outcome = STOP_OUTCOME_UNDEFINED
        provider_stop_outcomes = {}
    elif consensus_open is None:
        raise ProspectiveCorpusError(
            "a classifiable slot must carry a consensus open"
        )
    else:
        gapped = _safe_side_of_stop(
            slot.prior_observable_price, slot.active_stop, slot.direction
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
        "cadence": STOP_HOURLY_CADENCE,
        "classifier_version": STOP_EVENT_CLASSIFIER_VERSION,
        "direction": slot.direction,
        "observation_time": slot.observation_time.isoformat(),
        "protocol_version": PROTOCOL_VERSION,
        "track": slot.track,
    }
    return {
        "available_provider_ids": list(available),
        "classification": classification,
        "classifier_version": STOP_EVENT_CLASSIFIER_VERSION,
        "confirmation_quorum": CONFIRMATION_QUORUM,
        "consensus_open": None if consensus_open is None else str(consensus_open),
        "consensus_stop_extreme": (
            None if consensus_extreme is None else str(consensus_extreme)
        ),
        "consensus_stop_outcome": consensus_stop_outcome,
        "decision_time": decision_time.isoformat(),
        "direction": slot.direction,
        "event_id": _digest(identity),
        "gap_through_state": gap_state,
        "missing_provider_ids": list(missing),
        "observation_time": slot.observation_time.isoformat(),
        "prior_observable_observation_time": (
            None
            if slot.prior_observable_observation_time is None
            else slot.prior_observable_observation_time.isoformat()
        ),
        "prior_observable_price": (
            None if slot.prior_observable_price is None else str(slot.prior_observable_price)
        ),
        "provider_quorum": PROVIDER_QUORUM,
        "provider_stop_outcomes": dict(sorted(provider_stop_outcomes.items())),
        "reason_codes": sorted(set(reason_codes)),
        "stop_relevant_field": field,
        "touching_provider_ids": list(touching),
        "track": slot.track,
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
        "provider_quorum": PROVIDER_QUORUM,
        "required_providers": list(REQUIRED_PROVIDER_IDS),
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

_RECOMMENDATION_ACTIONS = (
    "NO_TRADE",
    "WATCH",
    "ENTER",
    "HOLD",
    "ADD",
    "TRIM",
    "EXIT",
)
_SETUP_DETECTORS = (
    "SETUP_BULL_TREND_CONTINUATION",
    "SETUP_BULLISH_RESET",
    "SETUP_CAPITULATION_REVERSAL",
    "SETUP_BEARISH_DISTRIBUTION",
)
_SETUP_DETECTOR_STATES = ("DETECTED", "NOT_DETECTED")
_REGIME_COMPARISON_BASIS = "categorical_regime_state"

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
            "abs(a - b) / max(a, b) has no repository precedent and would "
            "silently compress every difference."
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
            "Classified CROSS_MARKET_CONFIRMED_STOP_EVENT slots on the candidate "
            "track's own active stop where the candidate reference is usable at "
            "that decision_time."
        ),
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
            "Classified GAP_THROUGH_STOP_EVENT slots on the candidate track's own "
            "active stop where a prior observable reference price exists, the "
            "provider quorum holds and the candidate reference is usable."
        ),
        "evidence_owner": STOP_EVENT_CLASSIFIER_OWNER,
        "gap_through_semantics": (
            "BTC trades continuously, so no overnight-session gap is imported. A "
            "gap-through is a crossing without an observable traded price at the "
            "stop between two consecutive observable reference points: the prior "
            "observable price is strictly on the safe side of the active stop and "
            "the next available slot opens at or beyond it. A REFERENCE_UNAVAILABLE "
            "run simply widens the interval between those two observable points, "
            "so a missing session is handled by the same rule rather than by a "
            "separate calendar convention."
        ),
        "not_comparable_reasons": [
            "CANDIDATE_REFERENCE_UNAVAILABLE",
            "NO_PRIOR_OBSERVABLE_REFERENCE_PRICE",
            "PROVIDER_QUORUM_ABSENT",
        ],
        "numerator": (
            "Events where the candidate reference's TRIGGERED/NOT_TRIGGERED "
            "outcome at the gapping open equals the deterministic venue-consensus "
            "outcome computed from the median of the available required providers."
        ),
        "statistic": "rate",
        "universe": UNIVERSE_GAP_THROUGH_EVENTS,
        "zero_denominator": UNDEFINED_INSUFFICIENT_EVIDENCE,
    },
    ISOLATED_VENUE_METRIC: {
        "cadence": STOP_HOURLY_CADENCE,
        "comparison_basis": "candidate reference versus raw venue consensus",
        "denominator": (
            "Classified ISOLATED_VENUE_STOP_EVENT slots on the candidate track's "
            "own active stop where the candidate reference is usable at that "
            "decision_time."
        ),
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
            "complete deterministic action, whether flat or in position."
        ),
        "evidence_owner": (
            "btc_predictor.reporting.recommendation.render_recommendation"
        ),
        "lifecycle_owner": (
            "btc_predictor.portfolio.state_machine.apply_position_event"
        ),
        "not_comparable_reasons": [
            "CANDIDATE_TRACK_NOT_EVALUABLE",
            "CONTROL_TRACK_NOT_EVALUABLE",
        ],
        "numerator": (
            "Observations where the two tracks' authoritative actions differ."
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
        "vocabulary": list(_RECOMMENDATION_ACTIONS),
        "vocabulary_owner": (
            "btc_predictor.signals.data_quality.RECOMMENDATION_ACTIONS"
        ),
        "zero_denominator": UNDEFINED_INSUFFICIENT_EVIDENCE,
    },
    TRADE_ELIGIBILITY_METRIC: {
        "cadence": STRATEGY_DAILY_CADENCE,
        "comparison_basis": "candidate track versus control track",
        "denominator": (
            "Daily decision observations where both tracks are validly "
            "eligibility-evaluable: setup inputs complete for both and both in a "
            "pre-position lifecycle state."
        ),
        "eligibility_composition": {
            "already_in_position": (
                "Not permitted and not comparable: a track holding an open "
                "position is on the add path, not the entry path. The slot is "
                "recorded NOT_COMPARABLE with "
                "ONE_TRACK_POSITION_ACTIVE_ONE_TRACK_FLAT when the tracks differ "
                "and excluded from the universe when both are in position, so "
                "neither case can deflate the rate by trivial agreement."
            ),
            "data_failure": (
                "A hard data-quality failure blocks ENTER under "
                "apply_data_quality_gate; the slot is DATA_QUALITY_FAIL and "
                "leaves the universe for both tracks together."
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
        "evidence_owner": "btc_predictor.features.entry.classify_entry_action",
        "not_comparable_reasons": [
            "CANDIDATE_TRACK_NOT_EVALUABLE",
            "CONTROL_TRACK_NOT_EVALUABLE",
            "ONE_TRACK_POSITION_ACTIVE_ONE_TRACK_FLAT",
        ],
        "numerator": (
            "Observations where the two tracks disagree on whether a new trade is "
            "permitted."
        ),
        "statistic": "rate",
        "supporting_owners": [
            "btc_predictor.signals.data_quality.apply_data_quality_gate",
            "btc_predictor.signals.hard_veto.evaluate_hard_veto",
            "btc_predictor.risk.reward.evaluate_reward_risk",
            "btc_predictor.risk.sizing.calculate_initial_position_size",
            "btc_predictor.risk.exposure.calculate_risk_at_stop",
        ],
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
# Two different questions, answered separately and both before any data.
#
#   * What does it take to *evaluate* a metric at all?  That is mechanical and
#     derivable, so it is frozen here.
#   * What does it take to *certify* on one?  That is a minimum-denominator
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
        "complete_slot_census_required": True,
        "minimum_comparable_denominator": 1,
        "no_silent_omission_required": True,
        "both_tracks_valid_required": True,
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
        "Stage-B collection terminates on its own predeclared evidence "
        "sufficiency, never on elapsed time and never on an observed rate. "
        "Because the per-metric certification minimums are deferred to "
        f"{SUFFICIENCY_GOVERNANCE_SUCCESSOR}, the epoch has no terminating "
        "condition yet and no Stage-B certification is reachable from this "
        "protocol alone."
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
            "created_at": "timestamptz not null",
            "epoch_end": "timestamptz null",
            "epoch_start": "timestamptz not null",
            "initial_portfolio_state_sha256": "char(64) not null",
            "lifecycle_state": "text not null",
            "protocol_version": "text not null",
            "run_id": "uuid not null",
            "strategy_identity_sha256": "char(64) not null",
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
            "available_provider_ids": "jsonb not null",
            "candidate_stop_outcome": "text null",
            "classification": "text not null",
            "classifier_definition_sha256": "char(64) not null",
            "classifier_version": "text not null",
            "consensus_stop_outcome": "text not null",
            "decision_time": "timestamptz not null",
            "direction": "text not null",
            "event_id": "char(64) not null",
            "gap_through_state": "text not null",
            "missing_provider_ids": "jsonb not null",
            "observation_time": "timestamptz not null",
            "provider_stop_outcomes": "jsonb not null",
            "reason_codes": "jsonb not null",
            "run_id": "uuid not null",
            "touching_provider_ids": "jsonb not null",
            "track": "text not null",
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
    "PROTOCOL FREEZE",
    "INDEPENDENT XHIGH REVIEW",
    "PROSPECTIVE COLLECTION",
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
            f"{EVENT_NOT_CLASSIFIABLE} and enters no denominator."
        ),
        "predecessor_replaced": (
            "btc_predictor.research.reference_composite_empirical."
            "KNOWN_DEVELOPMENT_EVENTS"
        ),
        "protocol_version": PROTOCOL_VERSION,
        "schema_version": "PROSPECTIVE_INTEGRATION_STOP_EVENT_TAXONOMY_V1",
        "stop_outcomes": list(STOP_OUTCOMES),
        "stop_reference_rule": (
            "The stop compared at a slot is the evaluating track's own active "
            "stop under the authoritative lifecycle owner, never a hand-chosen "
            "reviewed level."
        ),
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
    if target not in LIFECYCLE_TRANSITIONS[current]:
        raise ProspectiveCorpusError(
            f"{current} may not transition to {target}"
        )
    if target == LIFECYCLE_COLLECTING:
        raise CollectionNotAuthorizedError(
            f"{LIFECYCLE_COLLECTING} requires {COLLECTION_ENTRY_REQUIREMENT}"
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
    authority = historical_gate_authority()
    children = {
        "data_schema_contract": data_schema_contract(),
        "decision_universe": decision_universe_contract(),
        "evidence_sufficiency": evidence_sufficiency_contract(),
        "input_snapshot_schema": input_snapshot_schema(),
        "metric_evidence_contracts": metric_evidence_contracts(),
        "portfolio_track_contract": portfolio_track_contract(),
        "semantic_diff_from_v5_blockers": semantic_diff_from_v5_blockers(),
        "stage_b_evaluation_contract": stage_b_evaluation_contract(),
        "stop_event_taxonomy": stop_event_taxonomy(),
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
        "Every metric's evaluability minimum is frozen here: a complete "
        "scheduled-slot census, both tracks valid, and a comparable denominator "
        "of at least one. A zero denominator is "
        f"`{UNDEFINED_INSUFFICIENT_EVIDENCE}` and never a PASS.",
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
        _report_markdown(protocol), encoding="ascii"
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
    if (output_dir / REPORT_FILENAME).read_text(encoding="ascii") != _report_markdown(
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
