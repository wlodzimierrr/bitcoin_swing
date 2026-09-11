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

from btc_predictor.data import derivatives as _derivatives
from btc_predictor.data import generic_series as _generic_series
from btc_predictor.db import portfolio as _portfolio_db
from btc_predictor.features import entry as _entry
from btc_predictor.features import flow as _flow
from btc_predictor.features import momentum as _momentum
from btc_predictor.features import positioning as _positioning
from btc_predictor.features import trend as _trend
from btc_predictor.features import volatility as _volatility
from btc_predictor.portfolio import state_machine as _state_machine
from btc_predictor.research import prospective_source_integrity as _source_integrity
from btc_predictor.research import reference_composite as _rc
from btc_predictor.research import reference_composite_v2 as _v2
from btc_predictor.research.feature_matrix import INITIAL_FEATURE_NAMES
from btc_predictor.signals import data_quality as _data_quality


# ---------------------------------------------------------------------------
# identity
# ---------------------------------------------------------------------------

PROTOCOL_VERSION = "PROSPECTIVE_INTEGRATION_CORPUS_V1"
PROTOCOL_SCHEMA_VERSION = "PROSPECTIVE_INTEGRATION_CORPUS_V1_PROTOCOL_DEFINITION_V1"
PROTOCOL_STATUS = "REPLAYABLE_PRE_DATA_PROTOCOL_AWAITING_SIXTH_XHIGH_REVIEW"
PROGRAM_TICKET = "POSTP1-001R5"
WORKSTREAM = "EPIC X"
WORKSTREAM_NAME = "PROSPECTIVE INTEGRATION EVIDENCE"
FINAL_CLASSIFICATION = (
    "PROSPECTIVE_INTEGRATION_CORPUS_READY_FOR_SIXTH_XHIGH_REVIEW"
)
AMBIGUOUS_FROZEN_METRIC_CLASSIFICATION = (
    "PROSPECTIVE_PROTOCOL_BLOCKED_BY_AMBIGUOUS_FROZEN_METRIC"
)
AMBIGUOUS_FROZEN_INPUT_CLASSIFICATION = (
    "PROSPECTIVE_PROTOCOL_BLOCKED_BY_AMBIGUOUS_FROZEN_INPUT"
)
MISSING_MARKET_CAP_SOURCE_CLASSIFICATION = (
    "PROSPECTIVE_PROTOCOL_BLOCKED_BY_MISSING_MARKET_CAP_SOURCE"
)
AMBIGUOUS_LIQUIDATION_NORMALIZATION_CLASSIFICATION = (
    "PROSPECTIVE_PROTOCOL_BLOCKED_BY_AMBIGUOUS_LIQUIDATION_NORMALIZATION"
)
INPUT_GOVERNANCE_INCOMPLETE_CLASSIFICATION = (
    "PROSPECTIVE_INPUT_GOVERNANCE_STILL_INCOMPLETE"
)
SUCCESSOR_PROTOCOL_VERSION = "PROSPECTIVE_INTEGRATION_CORPUS_V2"

# ``PROSPECTIVE_INTEGRATION_CORPUS_V1`` is retained rather than incremented.
# No failed hash was ever certified, no collection epoch opened and no
# qualifying observation exists, so no persisted evidence carries the old
# semantics and nothing would be relabelled backwards.  The repository's own
# versioning authority for this protocol -- ``CHANGE_PROCEDURE`` below --
# requires ``PROSPECTIVE_INTEGRATION_CORPUS_V2`` for a semantic change *after
# collection starts*; it imposes no increment on a pre-data correction, and
# POSTP1-001R and POSTP1-001R2 already corrected this protocol under the same
# reading. Lineage is carried by all retained failed definition hashes.
PROTOCOL_VERSION_RETAINED_RATIONALE = (
    "All five prior definition hashes failed independent review before any "
    "collection epoch opened, so no persisted observation carries the "
    "superseded semantics. CHANGE_PROCEDURE binds "
    f"{SUCCESSOR_PROTOCOL_VERSION} to a semantic change after collection "
    "starts, not to a pre-data correction, so the version is retained and the "
    "five failed definition hashes carry the lineage."
)

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
CVD_ACQUISITION_FILENAME = "prospective_cvd_acquisition_v1.json"
MARKET_CAP_ACQUISITION_FILENAME = "prospective_btc_market_cap_acquisition_v1.json"
LIQUIDATION_CAPTURE_FILENAME = "prospective_liquidation_capture_v1.json"
LIQUIDATION_PERCENTILE_ADAPTER_FILENAME = (
    "prospective_liquidation_percentile_adapter_v1.json"
)
CLOCK_INTEGRITY_FILENAME = "prospective_clock_integrity_v1.json"
STREAM_EPOCH_FILENAME = "source_stream_epoch_v1.json"
STREAM_LIVENESS_FILENAME = "stream_liveness_policy_v1.json"
CVD_INTERVAL_COMPLETENESS_FILENAME = "cvd_interval_completeness_v1.json"
COINGECKO_RESPONSE_VALIDATION_FILENAME = (
    "coingecko_market_cap_response_validation_v1.json"
)
LIQUIDATION_INTERVAL_COMPLETENESS_FILENAME = (
    "liquidation_interval_completeness_v1.json"
)
LIQUIDATION_DAY_CENSUS_FILENAME = "liquidation_utc_day_census_v1.json"
COINGECKO_REQUEST_ATTEMPT_FILENAME = (
    "coingecko_market_cap_request_attempt_v1.json"
)
KRAKEN_FUTURES_METADATA_VALIDATION_FILENAME = (
    "kraken_futures_instrument_metadata_validation_v1.json"
)
SCIENTIFIC_EVIDENCE_RESOLVER_FILENAME = "scientific_evidence_resolver_v1.json"
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
SECOND_FAILED_PROTOCOL_DEFINITION_SHA256 = (
    "0d4f14370c2d17359fa3e5d36ce545f00e00da1a360a66ad3151a37d0cf45a9e"
)
SECOND_FAILED_PROTOCOL_IMPLEMENTATION_COMMIT = (
    "8af223d708ee03b09bca6e43c204620aba44ecab"
)
SECOND_FAILED_PROTOCOL_REVIEW = "FAIL — AMBIGUOUS FROZEN INPUT"
SECOND_FAILED_PROTOCOL_REVIEW_CLASSIFICATION = (
    "PROSPECTIVE_PROTOCOL_BLOCKED_BY_AMBIGUOUS_FROZEN_INPUT"
)
THIRD_FAILED_PROTOCOL_DEFINITION_SHA256 = (
    "40e37067fdddee467ea6c8f0094a2498573e3ff379d35f0fdd5586af423c9862"
)
THIRD_FAILED_PROTOCOL_IMPLEMENTATION_COMMIT = (
    "9b2f23acc793457b0e8683387d8382f06472fdd4"
)
THIRD_FAILED_PROTOCOL_REVIEW = "FAIL — MARKET CAP SOURCE CONTRACT INVALID"
THIRD_FAILED_PROTOCOL_REVIEW_CLASSIFICATION = "PROSPECTIVE_PROTOCOL_REQUIRES_FIX"
FOURTH_FAILED_PROTOCOL_DEFINITION_SHA256 = (
    "e60a951476afb41437347220e7ab043ed6261cc03489da379adfca915c9a7dca"
)
FOURTH_FAILED_PROTOCOL_IMPLEMENTATION_COMMIT = (
    "f54025690975047c9c859567303088a5059f342e"
)
FOURTH_FAILED_PROTOCOL_REVIEW = "FAIL — CORRECTED PROSPECTIVE PROTOCOL INVALID"
FOURTH_FAILED_PROTOCOL_REVIEW_CLASSIFICATION = "PROSPECTIVE_PROTOCOL_REQUIRES_FIX"
FIFTH_FAILED_PROTOCOL_DEFINITION_SHA256 = (
    "fd946a091d9e1944163a78d331c31c518de2f21a35707a32141443d05f9bedff"
)
FIFTH_FAILED_PROTOCOL_IMPLEMENTATION_COMMIT = (
    "b813365c39d0423babe17caeabf85e7b7473de09"
)
FIFTH_FAILED_PROTOCOL_REVIEW_COMMIT = (
    "c61b16cba23a09e1056060a8cb2af4739f2ef5f1"
)
FIFTH_FAILED_PROTOCOL_REVIEW = "FAIL — CORRECTED PROSPECTIVE PROTOCOL INVALID"
FIFTH_FAILED_PROTOCOL_REVIEW_CLASSIFICATION = "PROSPECTIVE_PROTOCOL_REQUIRES_FIX"

# All prior definition hashes are retained as failed, non-authoritative
# pre-data lineage. None was certified, none opened a collection epoch and no
# qualifying observation was collected under any of them.
FAILED_PROSPECTIVE_PROTOCOL_LINEAGE: tuple[dict[str, Any], ...] = (
    {
        "attempt": 1,
        "authoritative": False,
        "definition_sha256": FAILED_PROTOCOL_DEFINITION_SHA256,
        "implementation_commit": FAILED_PROTOCOL_IMPLEMENTATION_COMMIT,
        "qualifying_observations_collected": False,
        "retained": True,
        "review": FAILED_PROTOCOL_REVIEW,
        "review_classification": FAILED_PROTOCOL_REVIEW_CLASSIFICATION,
        "superseded_before_collection": True,
        "ticket": "POSTP1-001",
    },
    {
        "attempt": 2,
        "authoritative": False,
        "definition_sha256": SECOND_FAILED_PROTOCOL_DEFINITION_SHA256,
        "implementation_commit": SECOND_FAILED_PROTOCOL_IMPLEMENTATION_COMMIT,
        "qualifying_observations_collected": False,
        "retained": True,
        "review": SECOND_FAILED_PROTOCOL_REVIEW,
        "review_classification": SECOND_FAILED_PROTOCOL_REVIEW_CLASSIFICATION,
        "superseded_before_collection": True,
        "ticket": "POSTP1-001R",
    },
    {
        "attempt": 3,
        "authoritative": False,
        "definition_sha256": THIRD_FAILED_PROTOCOL_DEFINITION_SHA256,
        "implementation_commit": THIRD_FAILED_PROTOCOL_IMPLEMENTATION_COMMIT,
        "qualifying_observations_collected": False,
        "retained": True,
        "review": THIRD_FAILED_PROTOCOL_REVIEW,
        "review_classification": THIRD_FAILED_PROTOCOL_REVIEW_CLASSIFICATION,
        "superseded_before_collection": True,
        "ticket": "POSTP1-001R2",
    },
    {
        "attempt": 4,
        "authoritative": False,
        "definition_sha256": FOURTH_FAILED_PROTOCOL_DEFINITION_SHA256,
        "implementation_commit": FOURTH_FAILED_PROTOCOL_IMPLEMENTATION_COMMIT,
        "qualifying_observations_collected": False,
        "retained": True,
        "review": FOURTH_FAILED_PROTOCOL_REVIEW,
        "review_classification": FOURTH_FAILED_PROTOCOL_REVIEW_CLASSIFICATION,
        "superseded_before_collection": True,
        "ticket": "POSTP1-001R3",
    },
    {
        "attempt": 5,
        "authoritative": False,
        "definition_sha256": FIFTH_FAILED_PROTOCOL_DEFINITION_SHA256,
        "implementation_commit": FIFTH_FAILED_PROTOCOL_IMPLEMENTATION_COMMIT,
        "qualifying_observations_collected": False,
        "retained": True,
        "review": FIFTH_FAILED_PROTOCOL_REVIEW,
        "review_classification": FIFTH_FAILED_PROTOCOL_REVIEW_CLASSIFICATION,
        "review_commit": FIFTH_FAILED_PROTOCOL_REVIEW_COMMIT,
        "superseded_before_collection": True,
        "ticket": "POSTP1-001R4",
    },
)


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
# 3b. NEW PROSPECTIVE PRE-DATA ACQUISITION GOVERNANCE
# ===========================================================================
#
# Phase-1 owns *feature semantics*: ``spot_perp_cvd_spread``,
# ``open_interest_intensity`` and ``calculate_orderliness_score`` are frozen and
# are not touched by this program.  What Phase-1 never owned, for three of their
# raw inputs, is *acquisition semantics*: which source produces a raw
# observation, on what cadence, with what timestamp, availability and revision
# meaning.  A feature transformation is not a source contract.
#
# The second repeat review proved the point for CVD: the historical owner
# accepts any set of common spot/perp timestamps and is observation-count based,
# so the previous claim that an exact UTC hourly cadence was "uniquely implied"
# by the feature owner was false.  The same review found no real prospective
# source behind ``MarketCapObservation`` and no capture layer able to tell a
# missing liquidation feed from an observed feed with zero liquidation events.
#
# Because this corpus has not begun collection, POSTP1-001R5 is authorised to
# correct those acquisition semantics now.  Everything in this section is
# therefore declared explicitly as NEW pre-data governance authored by this
# ticket.  None of it is presented as historically implicit, none of it was
# selected by inspecting a Stage-B outcome, and each contract carries its own
# deterministic definition hash bound by the parent protocol.

NEW_PRE_DATA_GOVERNANCE_CLASS = "NEW_PROSPECTIVE_PRE_DATA_ACQUISITION_GOVERNANCE"
ACQUISITION_GOVERNANCE_TICKET = "POSTP1-001R5"

PROSPECTIVE_CVD_ACQUISITION_VERSION = "PROSPECTIVE_CVD_ACQUISITION_V1"
PROSPECTIVE_CVD_ACQUISITION_SUCCESSOR = "PROSPECTIVE_CVD_ACQUISITION_V2"
PROSPECTIVE_CVD_AGGREGATE_OBSERVATION_VERSION = (
    "PROSPECTIVE_CVD_AGGREGATE_OBSERVATION_V1"
)
PROSPECTIVE_MARKET_CAP_ACQUISITION_VERSION = (
    "PROSPECTIVE_BTC_MARKET_CAP_ACQUISITION_V1"
)
PROSPECTIVE_MARKET_CAP_ACQUISITION_SUCCESSOR = (
    "PROSPECTIVE_BTC_MARKET_CAP_ACQUISITION_V2"
)
PROSPECTIVE_MARKET_CAP_OBSERVATION_VERSION = (
    "PROSPECTIVE_BTC_MARKET_CAP_OBSERVATION_V1"
)
PROSPECTIVE_LIQUIDATION_CAPTURE_VERSION = "PROSPECTIVE_LIQUIDATION_CAPTURE_V1"
PROSPECTIVE_LIQUIDATION_CAPTURE_SUCCESSOR = "PROSPECTIVE_LIQUIDATION_CAPTURE_V2"
PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_VERSION = (
    "PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_V1"
)
PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_SUCCESSOR = (
    "PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_V2"
)

PROSPECTIVE_CLOCK_INTEGRITY_VERSION = _source_integrity.CLOCK_INTEGRITY_VERSION
SOURCE_STREAM_EPOCH_VERSION = _source_integrity.STREAM_EPOCH_VERSION
STREAM_LIVENESS_POLICY_VERSION = _source_integrity.STREAM_LIVENESS_VERSION
CVD_INTERVAL_COMPLETENESS_VERSION = (
    _source_integrity.CVD_INTERVAL_COMPLETENESS_VERSION
)
COINGECKO_MARKET_CAP_RESPONSE_VALIDATION_VERSION = (
    _source_integrity.COINGECKO_RESPONSE_VALIDATION_VERSION
)
LIQUIDATION_INTERVAL_COMPLETENESS_VERSION = (
    _source_integrity.LIQUIDATION_INTERVAL_COMPLETENESS_VERSION
)
LIQUIDATION_UTC_DAY_CENSUS_VERSION = (
    _source_integrity.LIQUIDATION_DAY_CENSUS_VERSION
)
COINGECKO_MARKET_CAP_REQUEST_ATTEMPT_VERSION = (
    _source_integrity.COINGECKO_REQUEST_ATTEMPT_VERSION
)
KRAKEN_FUTURES_INSTRUMENT_METADATA_VALIDATION_VERSION = (
    _source_integrity.KRAKEN_FUTURES_METADATA_VALIDATION_VERSION
)
SCIENTIFIC_EVIDENCE_RESOLVER_VERSION = (
    _source_integrity.SCIENTIFIC_EVIDENCE_RESOLVER_VERSION
)

MonotonicDomainIdentity = _source_integrity.MonotonicDomainIdentity
ClockIntegrityRecord = _source_integrity.ClockIntegrityRecord
ClockIntervalEvidence = _source_integrity.ClockIntervalEvidence
CoinGeckoMarketCapRequest = _source_integrity.CoinGeckoMarketCapRequest
CoinGeckoMarketCapRequestAttempt = (
    _source_integrity.CoinGeckoMarketCapRequestAttempt
)
ValidatedCoinGeckoMarketCapResponse = (
    _source_integrity.ValidatedCoinGeckoMarketCapResponse
)
CollectorHealthRecord = _source_integrity.CollectorHealthRecord
SourceStreamEpoch = _source_integrity.SourceStreamEpoch
LivenessCheck = _source_integrity.LivenessCheck
StreamLivenessEvidence = _source_integrity.StreamLivenessEvidence
CapturedSourceEvent = _source_integrity.CapturedSourceEvent
KrakenFuturesInstrumentMetadataValidation = (
    _source_integrity.KrakenFuturesInstrumentMetadataValidation
)
PersistedEvidenceResolver = _source_integrity.PersistedEvidenceResolver
StreamIntervalCompleteness = _source_integrity.StreamIntervalCompleteness
CvdHourCompleteness = _source_integrity.CvdHourCompleteness
VerifiedLiquidationHour = _source_integrity.VerifiedLiquidationHour
ProspectiveSourceIntegrityError = (
    _source_integrity.ProspectiveSourceIntegrityError
)

prospective_clock_integrity_contract = (
    _source_integrity.prospective_clock_integrity_contract
)
source_stream_epoch_contract = _source_integrity.source_stream_epoch_contract
stream_liveness_policy_contract = _source_integrity.stream_liveness_policy_contract
cvd_interval_completeness_contract = (
    _source_integrity.cvd_interval_completeness_contract
)
coingecko_market_cap_response_validation_contract = (
    _source_integrity.coingecko_market_cap_response_validation_contract
)
coingecko_market_cap_request_attempt_contract = (
    _source_integrity.coingecko_market_cap_request_attempt_contract
)
kraken_futures_instrument_metadata_validation_contract = (
    _source_integrity.kraken_futures_instrument_metadata_validation_contract
)
scientific_evidence_resolver_contract = (
    _source_integrity.scientific_evidence_resolver_contract
)
liquidation_interval_completeness_contract = (
    _source_integrity.liquidation_interval_completeness_contract
)
liquidation_utc_day_census_contract = (
    _source_integrity.liquidation_utc_day_census_contract
)
validate_coingecko_market_cap_response = (
    _source_integrity.validate_coingecko_market_cap_response
)
replay_coingecko_market_cap_attempt = (
    _source_integrity.replay_coingecko_market_cap_attempt
)
replay_coingecko_market_cap_response = (
    _source_integrity.replay_coingecko_market_cap_response
)
replay_clock_interval = _source_integrity.replay_clock_interval
replay_stream_interval_completeness = (
    _source_integrity.replay_stream_interval_completeness
)
replay_cvd_hour_completeness = _source_integrity.replay_cvd_hour_completeness
replay_verified_liquidation_hour = (
    _source_integrity.replay_verified_liquidation_hour
)
end_stream_epoch = _source_integrity.end_stream_epoch
aggregate_liquidation_utc_day = _source_integrity.aggregate_liquidation_utc_day
expected_liquidation_hour_ids = _source_integrity.expected_liquidation_hour_ids

PROSPECTIVE_ACQUISITION_CONTRACT_VERSIONS = tuple(
    sorted(
        (
            PROSPECTIVE_CVD_ACQUISITION_VERSION,
            PROSPECTIVE_LIQUIDATION_CAPTURE_VERSION,
            PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_VERSION,
            PROSPECTIVE_MARKET_CAP_ACQUISITION_VERSION,
        )
    )
)

# Every acquisition contract must carry this provenance block verbatim. It is
# the honesty guarantee the repeat review asked for: a newly authored rule is
# never allowed to describe itself as inherited Phase-1 authority.
ACQUISITION_GOVERNANCE_PROVENANCE = {
    "authored_by_ticket": ACQUISITION_GOVERNANCE_TICKET,
    "claimed_historically_implicit": False,
    "frozen_before_collection": True,
    "governance_class": NEW_PRE_DATA_GOVERNANCE_CLASS,
    "hash_bound_by_parent_protocol": True,
    "historically_inherited": False,
    "outcome_independent": True,
    "phase_1_feature_semantics_changed": False,
    "qualifying_observations_inspected": False,
    "selected_by_new_pre_data_governance": True,
    "stage_b_outcomes_inspected": False,
}

ACQUISITION_FEED_STATE_REQUIRED = "REQUIRED_INPUT_MISSING"


def _acquisition_provenance() -> dict[str, Any]:
    return dict(ACQUISITION_GOVERNANCE_PROVENANCE)


# ---------------------------------------------------------------------------
# 3b.1 PROSPECTIVE_CVD_ACQUISITION_V1
# ---------------------------------------------------------------------------
#
# What the historical owner actually specifies, read from the owner itself:
# ``spot_perp_cvd_spread`` intersects the spot and perp observation_time sets,
# takes the last common timestamp as the observation, and z-scores each side
# against the prior common observations.  It never inspects the spacing of those
# timestamps.  So the owner specifies a *window in observations* and specifies
# no cadence at all.

CVD_HISTORICAL_OWNER = "btc_predictor.features.flow.spot_perp_cvd_spread"
CVD_HISTORICAL_OWNER_SPECIFIES_CADENCE = False
CVD_HISTORICAL_OWNER_CADENCE_EVIDENCE = (
    "The owner intersects the available spot and perp observation_time sets and "
    "z-scores the resulting common series. It accepts arbitrary common "
    "timestamps, applies no grid, spacing, alignment or interval test, and is "
    "observation-count based. Unit tests exercising hourly fixtures are "
    "evidence about a fixture, never scientific authority for a cadence."
)
CVD_HISTORICAL_OWNER_WINDOW_OBSERVATIONS = _flow.spot_perp_cvd_spread.__kwdefaults__[
    "zscore_window_periods"
]
CVD_HISTORICAL_OWNER_WINDOW = (
    f"{CVD_HISTORICAL_OWNER_WINDOW_OBSERVATIONS} prior common observations"
)
CVD_UNIT_TESTS_ARE_NOT_CADENCE_AUTHORITY = True

CVD_CADENCE_SELECTION_CRITERIA = (
    "phase_1_decision_cadence_compatibility",
    "point_in_time_availability",
    "btc_swing_holding_horizon",
    "existing_spot_perp_volume_infrastructure",
    "capture_without_aggregation_lookahead",
    "operational_reproducibility",
    "source_availability",
    "relationship_to_the_20_observation_normalization_window",
)

CVD_SELECTED_CADENCE = "1h"
CVD_SPOT_PROVIDER_ID = "kraken_spot_websocket_v2_trade"
CVD_SPOT_ENDPOINT = "wss://ws.kraken.com/v2"
CVD_SPOT_INSTRUMENT = "BTC/USD"
CVD_SPOT_SOURCE_DOCUMENTATION = (
    "https://docs.kraken.com/api/docs/websocket-v2/trade/"
)
CVD_PERPETUAL_PROVIDER_ID = "kraken_futures_websocket_v1_trade"
CVD_PERPETUAL_ENDPOINT = "wss://futures.kraken.com/ws/v1"
CVD_PERPETUAL_INSTRUMENT = "PI_XBTUSD"
CVD_PERPETUAL_SOURCE_DOCUMENTATION = (
    "https://docs.kraken.com/api/docs/futures-api/websocket/trade/"
)
CVD_PERPETUAL_INSTRUMENT_METADATA_ENDPOINT = (
    "https://futures.kraken.com/derivatives/api/v3/instruments"
)
CVD_PERPETUAL_INCLUDED_TRADE_TYPES = (
    "block",
    "fill",
    "liquidation",
    "termination",
)
CVD_SPOT_EVENT_TIMESTAMP_FIELD = "timestamp (RFC3339)"
CVD_PERPETUAL_EVENT_TIMESTAMP_FIELD = "time (milliseconds since UTC epoch)"
CVD_PROVIDER_BY_MARKET_TYPE = {
    "perp": CVD_PERPETUAL_PROVIDER_ID,
    "spot": CVD_SPOT_PROVIDER_ID,
}
CVD_INSTRUMENT_BY_MARKET_TYPE = {
    "perp": CVD_PERPETUAL_INSTRUMENT,
    "spot": CVD_SPOT_INSTRUMENT,
}
CVD_SOURCE_METADATA_VERIFIED_AT = "2026-09-09"
CVD_REQUIRED_CONTIGUOUS_HOURS = CVD_HISTORICAL_OWNER_WINDOW_OBSERVATIONS + 1

CVD_CADENCE_CANDIDATES: dict[str, dict[str, Any]] = {
    "1h": {
        "assessment": {
            "btc_swing_holding_horizon": (
                "ACCEPTABLE: a swing position is held for days to weeks while "
                "stops are evaluated hourly, so an hourly flow observation is "
                "never the coarsest evidence in the corpus and never forces a "
                "scheduled slot to be skipped for want of a fresh observation."
            ),
            "capture_without_aggregation_lookahead": (
                "BEST: an exact-hour interval is the finest natively closing "
                "interval the repository already persists, so the observation "
                "is the interval itself and no bucket is ever aggregated from "
                "shorter buckets. Nothing is resampled and no partial interval "
                "can leak into a closed one."
            ),
            "existing_spot_perp_volume_infrastructure": (
                "BEST: raw.btc_ohlcv is 1h and the spot/perp participation "
                "owner already consumes 1h spot and perp rows, so spot and perp "
                "CVD land on the same boundary that infrastructure already "
                "produces."
            ),
            "operational_reproducibility": (
                "BEST: exact UTC hour boundaries carry no session, holiday or "
                "timezone convention to reconstruct at replay."
            ),
            "phase_1_decision_cadence_compatibility": (
                "BEST: STOP_HOURLY is the finer of the two frozen decision "
                "cadences and sits on exact UTC hours, and STRATEGY_DAILY "
                "sessions open on an exact UTC hour, so a 1h observation grid "
                "coincides with every scheduled decision instant of both "
                "cadences without interpolation."
            ),
            "point_in_time_availability": (
                "BEST: the interval closes on the hour and the frozen decision "
                "delay is bar close + 5 minutes, so a closed interval is "
                "available at the very next decision instant of either cadence."
            ),
            "relationship_to_the_20_observation_normalization_window": (
                "BEST: 20 prior plus 1 current common observation spans about "
                "21 hours, so CVD reaches evaluability inside one day and never "
                "becomes the binding warmup constraint of the corpus."
            ),
            "source_availability": (
                "BEST: Kraken's public spot and futures trade WebSockets emit "
                "individual trades in real time with provider-owned taker side, "
                "event timestamp and unique identity. The futures feed also "
                "emits a sequence number. Both exact instruments are USD quoted."
            ),
        },
        "rejected_because": None,
        "selected": True,
    },
    "4h": {
        "assessment": {
            "btc_swing_holding_horizon": "ACCEPTABLE.",
            "capture_without_aggregation_lookahead": (
                "WORSE: a 4h observation must be composed from the hourly "
                "buckets the infrastructure produces, adding an aggregation "
                "step whose partial-bucket handling has to be governed."
            ),
            "existing_spot_perp_volume_infrastructure": (
                "WORSE: no repository source publishes a 4h spot or perp "
                "interval; it would be derived."
            ),
            "operational_reproducibility": (
                "WORSE: a 4h grid needs an arbitrary frozen phase origin."
            ),
            "phase_1_decision_cadence_compatibility": (
                "WORSE: five of every six STOP_HOURLY slots would carry a stale "
                "CVD observation."
            ),
            "point_in_time_availability": "ACCEPTABLE.",
            "relationship_to_the_20_observation_normalization_window": (
                "WORSE: 21 observations span about 3.5 days of warmup for no "
                "contract benefit."
            ),
            "source_availability": "ACCEPTABLE.",
        },
        "rejected_because": (
            "It is a derived interval with an arbitrary phase origin, it must "
            "be aggregated from the hourly buckets the repository already has, "
            "and it is stale at five of every six hourly decision instants."
        ),
        "selected": False,
    },
    "1d": {
        "assessment": {
            "btc_swing_holding_horizon": (
                "ACCEPTABLE for the daily strategy cadence alone."
            ),
            "capture_without_aggregation_lookahead": (
                "WORSE: a daily observation is an aggregation of 24 hourly "
                "buckets and its completeness depends on all of them."
            ),
            "existing_spot_perp_volume_infrastructure": (
                "WORSE: the participation infrastructure is hourly, so a daily "
                "CVD grid would diverge from the sibling flow family."
            ),
            "operational_reproducibility": "ACCEPTABLE on canonical UTC days.",
            "phase_1_decision_cadence_compatibility": (
                "WORST: 23 of every 24 STOP_HOURLY slots would carry a CVD "
                "observation up to 23 hours stale."
            ),
            "point_in_time_availability": "ACCEPTABLE.",
            "relationship_to_the_20_observation_normalization_window": (
                "WORSE: 21 daily observations make CVD a 21-day warmup, adding "
                "a new binding constraint to the corpus for no contract gain."
            ),
            "source_availability": "ACCEPTABLE.",
        },
        "rejected_because": (
            "It cannot serve the hourly decision cadence without up to 23 hours "
            "of staleness, it must be aggregated from hourly buckets, and it "
            "would introduce a 21-day warmup that the hourly contract avoids."
        ),
        "selected": False,
    },
}

CVD_CADENCE_SELECTION_RATIONALE = (
    "1h is selected as the cleanest prospective observation contract, not "
    "because it is inherited and not because it produces any particular "
    "measured value. It is the finest interval aligned with the repository's "
    "existing hourly market infrastructure and the selected exchange-native "
    "real-time trade feeds, it coincides exactly with the "
    "STOP_HOURLY decision grid and with the opening instant of every "
    "STRATEGY_DAILY session, it requires no aggregation and therefore admits no "
    "partial-bucket lookahead, it needs no arbitrary phase origin or session "
    "calendar to replay, and it keeps the frozen 20-prior-observation "
    "normalization window from becoming the corpus's binding warmup. Every "
    "coarser candidate is a derived interval that is stale at most hourly "
    "decision instants. No Stage-B outcome, disagreement rate or target gate "
    "was inspected to reach this choice."
)


def prospective_cvd_acquisition_contract() -> dict[str, Any]:
    """Freeze what one prospective ``CvdObservation`` means, before any data."""

    if CVD_SELECTED_CADENCE not in CVD_CADENCE_CANDIDATES:
        raise ProspectiveCorpusError("the selected CVD cadence is not a candidate")
    selected = tuple(
        cadence
        for cadence, row in CVD_CADENCE_CANDIDATES.items()
        if row["selected"]
    )
    if selected != (CVD_SELECTED_CADENCE,):
        raise ProspectiveCorpusError(
            "exactly one CVD cadence candidate may be selected"
        )
    for cadence, row in CVD_CADENCE_CANDIDATES.items():
        missing = tuple(
            criterion
            for criterion in CVD_CADENCE_SELECTION_CRITERIA
            if criterion not in row["assessment"]
        )
        if missing:
            raise ProspectiveCorpusError(
                f"CVD cadence candidate {cadence} is unassessed against {missing}"
            )
        if row["selected"] is (row["rejected_because"] is not None):
            raise ProspectiveCorpusError(
                f"CVD cadence candidate {cadence} has an inconsistent verdict"
            )
    window = CVD_HISTORICAL_OWNER_WINDOW_OBSERVATIONS
    payload = {
        "acquisition_governance": _acquisition_provenance(),
        "aggregation_method": (
            "For Kraken spot BTC/USD, signed USD notional is price * qty with a "
            "positive sign for provider side=buy and negative for side=sell. "
            "For Kraken Futures PI_XBTUSD, contractSize=1 USD and signed USD "
            "notional is qty * 1 USD with the same taker-side signs. Every "
            f"provider trade type in {list(CVD_PERPETUAL_INCLUDED_TRADE_TYPES)} "
            "is included when it carries a valid taker side. The signed sums "
            "are accumulated directly inside [t,t+1h); no interval is built "
            "from other intervals or resampled."
        ),
        "available_at_semantics": (
            "The collector's clock-integrity-validated UTC wall-clock instant at which the "
            "closed interval and its completion evidence were validated. It is "
            "never back-dated to the interval boundary and makes no claim about "
            "a provider first-publication instant. Duration and liveness "
            "deadlines use the monotonic clock. An observation whose "
            "available_at is later than decision_time is invisible."
        ),
        "buy_sell_classification_owner": (
            "Kraken's exchange-native side field, documented on both selected "
            "trade feeds as the side of the taker order. The capture layer never "
            "infers a side from price, never reclassifies a trade and marks the "
            "whole interval INVALID if any captured trade lacks buy/sell side."
        ),
        "calculation_interval": (
            f"one closed [t, t + {CVD_SELECTED_CADENCE}) interval per "
            "market_type per provider"
        ),
        "cadence_selection": {
            "candidates": CVD_CADENCE_CANDIDATES,
            "criteria": list(CVD_CADENCE_SELECTION_CRITERIA),
            "empirically_optimized_against_target_gates": False,
            "historically_inherited": False,
            "rationale": CVD_CADENCE_SELECTION_RATIONALE,
            "selected_by_new_pre_data_governance": True,
            "selected_cadence": CVD_SELECTED_CADENCE,
            "stage_b_disagreement_outcomes_inspected": False,
        },
        "consuming_features": ["CVD_SPREAD"],
        "cvd_usd_definition": (
            "cvd_usd is the signed USD notional taker delta of the interval: "
            "the sum of buyer-initiated trade notional minus the sum of "
            "seller-initiated trade notional, in USD, over the closed interval "
            "and the one exact frozen instrument for that market_type. Spot "
            "notional is price * BTC quantity; PI_XBTUSD is a 1 USD inverse "
            "contract and its notional is contract quantity * 1 USD. It is an "
            "interval delta, not a running cumulative total, so no observation "
            "depends on an unbounded history and a missing interval can never "
            "be reconstructed from its neighbours."
        ),
        "duplicate_semantics": (
            "Raw spot trades are unique by (provider, instrument, trade_id) and "
            "raw perpetual trades by (provider, instrument, uid). A conflicting "
            "duplicate source id invalidates the hour. Aggregate revisions are "
            "append-only; the prospective selector passes exactly the latest "
            "revision available at the decision to the historical owner, never "
            "multiple revisions that the owner would sum."
        ),
        "epoch_rule": (
            "Any change to the cadence, provider set, spot or perpetual market "
            f"universe, buy/sell classification or aggregation requires "
            f"{PROSPECTIVE_CVD_ACQUISITION_SUCCESSOR} and a new prospective "
            "collection epoch for every affected metric. Observations already "
            "captured under this contract are never resampled, re-bucketed or "
            "relabelled backwards."
        ),
        "event_inclusion": {
            "interval_boundary": "half-open [t, t + 1h)",
            "local_receipt_boundary": (
                "received_at <= finalized_at; exact equality is admitted. An "
                "event received one microsecond later cannot enter that revision."
            ),
            "perpetual_included_trade_types": list(
                CVD_PERPETUAL_INCLUDED_TRADE_TYPES
            ),
            "perpetual_timestamp_field": CVD_PERPETUAL_EVENT_TIMESTAMP_FIELD,
            "spot_included_events": "every trade array item",
            "spot_timestamp_field": CVD_SPOT_EVENT_TIMESTAMP_FIELD,
            "timestamp_conversion": (
                "Parse the provider timestamp as UTC without rounding; assign "
                "the event to the unique exact-hour half-open interval that "
                "contains it."
            ),
        },
        "feature_semantics_owner": CVD_HISTORICAL_OWNER,
        "feature_semantics_unchanged": True,
        "historical_feature_owner": {
            "cadence_evidence": CVD_HISTORICAL_OWNER_CADENCE_EVIDENCE,
            "formula": "CVD_SPREAD = z(SpotCVD) - z(PerpCVD)",
            "owner": CVD_HISTORICAL_OWNER,
            "specifies_cadence": CVD_HISTORICAL_OWNER_SPECIFIES_CADENCE,
            "specifies_window": CVD_HISTORICAL_OWNER_WINDOW,
            "unit_tests_are_cadence_authority": (
                not CVD_UNIT_TESTS_ARE_NOT_CADENCE_AUTHORITY
            ),
            "window_observations": window,
        },
        "ingested_at_semantics": (
            "The wall-clock instant the capture layer persisted the row. It "
            "orders storage only and never admits or excludes an observation "
            "from a decision."
        ),
        "initialization_requirement": {
            "current_observations": 1,
            "cvd_observation_meaning": (
                f"one closed {CVD_SELECTED_CADENCE} interval of signed USD "
                "taker delta for one market_type"
            ),
            "prior_common_observations": window,
            "statement": (
                f"{window} immediately prior contiguous {CVD_SELECTED_CADENCE} "
                "common spot/perp observations plus the exact current hour; "
                "a missing interior hour is not replaced by an older observation"
            ),
            "total_common_observations": window + 1,
        },
        "market_universe": {
            "frozen_before_collection": True,
            "perpetual": {
                "endpoint": CVD_PERPETUAL_ENDPOINT,
                "instrument_type": "perpetual_swap",
                "instrument": CVD_PERPETUAL_INSTRUMENT,
                "instrument_metadata_endpoint": (
                    CVD_PERPETUAL_INSTRUMENT_METADATA_ENDPOINT
                ),
                "provider": CVD_PERPETUAL_PROVIDER_ID,
                "quote_currency": "USD",
                "selection_rule": (
                    "Exactly Kraken Futures PI_XBTUSD, verified before this "
                    "freeze as a tradeable, non-expired BTC:USD inverse contract "
                    "with contractSize=1. No second instrument or venue may be "
                    "added, removed or substituted inside the epoch."
                ),
                "source_documentation": CVD_PERPETUAL_SOURCE_DOCUMENTATION,
                "underlying": "BTC",
                "venue": "kraken_futures",
            },
            "spot": {
                "endpoint": CVD_SPOT_ENDPOINT,
                "instrument_type": "spot",
                "instrument": CVD_SPOT_INSTRUMENT,
                "provider": CVD_SPOT_PROVIDER_ID,
                "quote_currency": "USD",
                "selection_rule": (
                    "Exactly Kraken spot BTC/USD. Selecting the same exchange's "
                    "USD spot and perpetual markets avoids a cross-provider "
                    "microstructure confound and supplies a provider-owned taker "
                    "side on both legs. No second spot instrument or venue may "
                    "be added, removed or substituted inside the epoch."
                ),
                "source_documentation": CVD_SPOT_SOURCE_DOCUMENTATION,
                "underlying": "BTC",
                "venue": "kraken_spot",
            },
            "source_metadata_verified_at": CVD_SOURCE_METADATA_VERIFIED_AT,
            "universe_change_requires": PROSPECTIVE_CVD_ACQUISITION_SUCCESSOR,
        },
        "missing_interval_semantics": (
            "The prospective selector requires the exact current UTC hour and "
            "its 20 immediately preceding UTC hours for both market types. A "
            "missing, late, invalid or incomplete interval makes CVD_SPREAD not "
            "evaluable until that gap ages out of the 21-hour contiguous window. "
            "It is never zero-filled, carried forward, interpolated or replaced "
            "by an older observation; calendar time is never silently compressed "
            "by row adjacency before the historical observation-count owner "
            "runs."
        ),
        "observation_cadence": CVD_SELECTED_CADENCE,
        "observation_time_semantics": (
            "The exact UTC start instant of the closed interval, aligned to the "
            "exact hour. An off-grid observation_time is refused at capture."
        ),
        "off_grid_observation_policy": "REFUSE_AT_CAPTURE_NEVER_SNAP_OR_ROUND",
        "pit_rule": PIT_RULE,
        "protocol_version": PROTOCOL_VERSION,
        "provider_identity": {
            "identity_fields": ["provider", "market_type"],
            "one_provider_per_market_type_per_epoch": True,
            "provider_by_market_type": dict(CVD_PROVIDER_BY_MARKET_TYPE),
            "instrument_by_market_type": dict(CVD_INSTRUMENT_BY_MARKET_TYPE),
            "provider_replacement_requires": (
                PROSPECTIVE_CVD_ACQUISITION_SUCCESSOR
            ),
            "recorded_per_observation": True,
            "statement": (
                "The exact provider and instrument above are frozen for each "
                "market_type and persisted on every row. Any other identity, or "
                "mixing providers inside one series, is refused."
            ),
        },
        "pre_owner_adapter": {
            "input_type": "ProspectiveCvdAggregateObservation",
            "output_type": "btc_predictor.features.flow.CvdObservation",
            "selector": "select_contiguous_cvd_window",
            "statement": (
                "The prospective row retains provider, instrument and revision; "
                "the selector verifies the exact identity and contiguous grid, "
                "chooses one latest available revision, then strips only the "
                "acquisition-only fields for the historical feature owner."
            ),
        },
        "raw_feed_completion": {
            "complete_is_caller_supplied": False,
            "completion_contract": CVD_INTERVAL_COMPLETENESS_VERSION,
            "completion_contract_sha256": cvd_interval_completeness_contract()[
                "definition_sha256"
            ],
            "decision_cutoff": "interval close + 5 minutes",
            "perpetual": (
                "one SOURCE_STREAM_EPOCH_V1 acknowledged before interval start "
                "and continuous through interval close; collector-owned "
                "ping/pong liveness and health pass; no local loss, invalid "
                "event or conflicting uid. Futures seq is validated only "
                "inside its documented subscription scope and never across a "
                "reconnect."
            ),
            "spot": (
                "one SOURCE_STREAM_EPOCH_V1 acknowledged before interval start "
                "and continuous through interval close; collector-owned "
                "ping/pong liveness and health pass; no local loss, invalid "
                "event or conflicting trade_id. trade_id is an identity and "
                "deduplication key, not an undocumented continuity proof."
            ),
            "source_stream_epoch_contract_sha256": source_stream_epoch_contract()[
                "definition_sha256"
            ],
            "stream_liveness_policy_sha256": stream_liveness_policy_contract()[
                "definition_sha256"
            ],
            "runtime_futures_metadata_validation_sha256": (
                kraken_futures_instrument_metadata_validation_contract()[
                    "definition_sha256"
                ]
            ),
            "scientific_evidence_resolver_sha256": (
                scientific_evidence_resolver_contract()["definition_sha256"]
            ),
            "unmet_predicate": "REQUIRED_INPUT_MISSING",
        },
        "revision_semantics": (
            "Append-only. A provider restatement of a closed interval is a new "
            "revision row for the same (provider, market_type, "
            "observation_time); the earlier revision is retained verbatim and a "
            "decision replays against exactly the latest revision available at "
            "its own decision_time. The pre-owner selector passes one revision "
            "per market_type/hour so the historical aggregation owner cannot "
            "sum revisions together."
        ),
        "schema_version": "PROSPECTIVE_CVD_ACQUISITION_V1",
        "aggregate_observation_schema_version": (
            PROSPECTIVE_CVD_AGGREGATE_OBSERVATION_VERSION
        ),
        "timestamp_alignment": "EXACT_UTC_HOUR_INTERVAL_START",
        "units": "USD",
        "version": PROSPECTIVE_CVD_ACQUISITION_VERSION,
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def _require_utc_instant(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ProspectiveCorpusError(f"{field_name} must be timezone-aware UTC")
    return value.astimezone(UTC)


@dataclass(frozen=True)
class ProspectiveCvdAggregateObservation:
    """One CVD leg derived only from a mechanically verified common hour."""

    completeness: CvdHourCompleteness
    market_type: str
    revision: int

    @property
    def observation_time(self) -> datetime:
        return self.completeness.as_record()["interval_start"]

    @property
    def available_at(self) -> datetime:
        return self.completeness.as_record()["finalized_at"]

    @property
    def cvd_usd(self) -> Decimal | None:
        return self.completeness.as_record()[f"{self.market_type}_cvd_usd"]

    @property
    def provider(self) -> str:
        return CVD_PROVIDER_BY_MARKET_TYPE[self.market_type]

    @property
    def instrument(self) -> str:
        return CVD_INSTRUMENT_BY_MARKET_TYPE[self.market_type]

    @property
    def interval_complete(self) -> bool:
        return bool(self.completeness.as_record()["complete"])

    def as_record(self) -> dict[str, Any]:
        if self.market_type not in {"spot", "perp"}:
            raise ProspectiveCorpusError("market_type must be spot or perp")
        if not isinstance(self.revision, int) or isinstance(self.revision, bool):
            raise ProspectiveCorpusError("CVD revision must be an integer")
        if self.revision < 1:
            raise ProspectiveCorpusError("CVD revision must be >= 1")
        completion = self.completeness.as_record()
        value = completion[f"{self.market_type}_cvd_usd"]
        provider = CVD_PROVIDER_BY_MARKET_TYPE[self.market_type]
        instrument = CVD_INSTRUMENT_BY_MARKET_TYPE[self.market_type]
        payload = {
            "available_at": completion["finalized_at"],
            "completion_evidence": completion,
            "completion_evidence_sha256": completion["record_sha256"],
            "cvd_usd": value,
            "instrument": instrument,
            "interval_complete": completion["complete"],
            "market_type": self.market_type,
            "observation_time": completion["interval_start"],
            "provider": provider,
            "revision": self.revision,
            "schema_version": PROSPECTIVE_CVD_AGGREGATE_OBSERVATION_VERSION,
        }
        payload["record_sha256"] = _source_integrity.digest(payload)
        return payload

    def evidence_records(self) -> dict[str, dict[str, Any]]:
        records = self.completeness.evidence_records()
        row = self.as_record()
        records[row["record_sha256"]] = row
        return records

    def as_owner_observation(self) -> _flow.CvdObservation:
        record = self.as_record()
        if not record["interval_complete"] or record["cvd_usd"] is None:
            raise ProspectiveCorpusError(
                "incomplete CVD intervals cannot reach the historical owner"
            )
        return _flow.CvdObservation(
            observation_time=record["observation_time"],
            market_type=record["market_type"],
            cvd_usd=record["cvd_usd"],
            provider=record["provider"],
            available_at=record["available_at"],
        )


def replay_prospective_cvd_aggregate_observation(
    record_sha256: str,
    resolver: PersistedEvidenceResolver,
) -> dict[str, Any]:
    persisted = resolver.resolve(
        record_sha256,
        schema_version=PROSPECTIVE_CVD_AGGREGATE_OBSERVATION_VERSION,
    )
    completion_object = replay_cvd_hour_completeness(
        persisted["completion_evidence_sha256"], resolver
    )
    completion = completion_object.as_record()
    if persisted["completion_evidence"] != completion:
        raise ProspectiveCorpusError(
            "CVD surface completion snapshot differs from resolved evidence"
        )
    replayed = ProspectiveCvdAggregateObservation(
        completeness=completion_object,
        market_type=persisted["market_type"],
        revision=persisted["revision"],
    ).as_record()
    if persisted != replayed:
        raise ProspectiveCorpusError(
            "CVD surface differs from replayed completeness evidence"
        )
    return replayed


def select_contiguous_cvd_window(
    observations: Sequence[ProspectiveCvdAggregateObservation],
    *,
    current_observation_time: datetime,
    decision_time: datetime,
) -> tuple[_flow.CvdObservation, ...]:
    """Select exactly one PIT revision on the frozen contiguous CVD grid.

    The Phase-1 feature owner intentionally remains observation-count based.
    This prospective pre-owner boundary prevents row adjacency from replacing
    an absent UTC hour and prevents append-only revisions from being summed.
    """

    current = _require_utc_instant(
        current_observation_time,
        "current_observation_time",
    )
    decision = _require_utc_instant(decision_time, "decision_time")
    if current.minute or current.second or current.microsecond:
        raise ProspectiveCorpusError("current CVD observation must be an exact UTC hour")
    expected_times = tuple(
        current - timedelta(hours=offset)
        for offset in range(CVD_REQUIRED_CONTIGUOUS_HOURS - 1, -1, -1)
    )
    expected_time_set = set(expected_times)
    grouped: dict[
        tuple[str, datetime],
        list[ProspectiveCvdAggregateObservation],
    ] = {}
    for observation in observations:
        record = observation.as_record()
        observation_time = record["observation_time"]
        if observation_time not in expected_time_set:
            continue
        market_type = record["market_type"]
        expected_provider = CVD_PROVIDER_BY_MARKET_TYPE[market_type]
        expected_instrument = CVD_INSTRUMENT_BY_MARKET_TYPE[market_type]
        if (
            record["provider"] != expected_provider
            or record["instrument"] != expected_instrument
        ):
            raise ProspectiveCorpusError(
                f"unexpected {market_type} CVD provider/instrument identity"
            )
        if (
            observation_time.minute
            or observation_time.second
            or observation_time.microsecond
        ):
            raise ProspectiveCorpusError("CVD observation must be an exact UTC hour")
        if record["interval_complete"] and record["available_at"] < (
            observation_time + timedelta(hours=1)
        ):
            raise ProspectiveCorpusError(
                "complete CVD interval cannot be available before interval close"
            )
        if not record["interval_complete"]:
            continue
        if record["available_at"] <= decision:
            grouped.setdefault((market_type, observation_time), []).append(observation)

    selected: list[_flow.CvdObservation] = []
    missing: list[str] = []
    common_completion_by_time: dict[datetime, str] = {}
    for observation_time in expected_times:
        for market_type in ("spot", "perp"):
            revisions = grouped.get((market_type, observation_time), [])
            if not revisions:
                missing.append(f"{market_type}:{observation_time.isoformat()}")
                continue
            revision_ids = [row.revision for row in revisions]
            if len(revision_ids) != len(set(revision_ids)):
                raise ProspectiveCorpusError(
                    "duplicate CVD revision identity for one interval"
                )
            revisions.sort(key=lambda row: row.available_at)
            if (
                len(revisions) > 1
                and revisions[-1].available_at == revisions[-2].available_at
            ):
                raise ProspectiveCorpusError(
                    "conflicting CVD revisions share one available_at instant"
                )
            chosen = revisions[-1]
            completion_sha256 = chosen.as_record()["completion_evidence_sha256"]
            prior_completion = common_completion_by_time.setdefault(
                observation_time,
                completion_sha256,
            )
            if prior_completion != completion_sha256:
                raise ProspectiveCorpusError(
                    "spot and perp CVD rows do not bind one common completeness record"
                )
            selected.append(chosen.as_owner_observation())
    if missing:
        raise ProspectiveCorpusError(
            "CVD_CONTIGUOUS_GRID_INCOMPLETE: " + ", ".join(missing)
        )
    return tuple(selected)


# ---------------------------------------------------------------------------
# 3b.2 PROSPECTIVE_BTC_MARKET_CAP_ACQUISITION_V1
# ---------------------------------------------------------------------------
#
# ``open_interest_intensity`` requires a ``MarketCapObservation`` for OI_INTENSITY
# and OI_INTENSITY_PERCENTILE_180D.  Nothing in this repository produces one:
# ``MarketCapObservation`` is constructed only inside a feature test, and
# ``raw.generic_series`` supports the series types
# ("macro", "liquidity", "onchain", "market_proxy") with no market-cap series
# definition and no market-cap producer.  The previous freeze pointed
# OI_INTENSITY at the unqualified generic-series family, which is not a source
# contract: a consumer would have had to search for an arbitrary row.

EXISTING_MARKET_CAP_PRODUCER = None
EXISTING_MARKET_CAP_PRODUCER_EVIDENCE = (
    "btc_predictor.features.positioning.MarketCapObservation is constructed "
    "nowhere outside btc_predictor/tests/test_positioning_features.py. "
    "btc_predictor.data.generic_series.SUPPORTED_SERIES_TYPES is "
    f"{list(_generic_series.SUPPORTED_SERIES_TYPES)} and neither "
    "MACRO_SERIES_DEFINITIONS nor ONCHAIN_SERIES_DEFINITIONS declares a "
    "market-capitalisation series. No collector, adapter or migration in this "
    "repository emits market_cap_usd."
)

MARKET_CAP_SERIES_ID = "BTC_MARKET_CAP_USD"
MARKET_CAP_SERIES_TYPE = "market_cap"
MARKET_CAP_SERIES_UNIT = "usd"
MARKET_CAP_RAW_TABLE = "raw.generic_series"
MARKET_CAP_PROVIDER_ID = "coingecko"
MARKET_CAP_PROVIDER_SOURCE = "coingecko_v3_coins_bitcoin_history_market_cap_usd"
MARKET_CAP_PROVIDER_ASSET_IDENTIFIER = "bitcoin"
MARKET_CAP_PROVIDER_FIELD = "market_data.market_cap.usd"
MARKET_CAP_OBSERVATION_CADENCE = "1d"
MARKET_CAP_OBSERVATION_GRID = "EXACT_UTC_DAY_START_00_00_00Z"
MARKET_CAP_PROVIDER_ENDPOINT = (
    "https://api.coingecko.com/api/v3/coins/bitcoin/history"
)
MARKET_CAP_PROVIDER_DOCUMENTATION = (
    "https://docs.coingecko.com/reference/coins-id-history"
)
MARKET_CAP_REVISION_DOCUMENTATION = (
    "https://support.coingecko.com/hc/en-us/articles/"
    "61976309053337-Why-do-historical-market-cap-values-change-shortly-after-a-date-then-settle"
)
MARKET_CAP_PROVIDER_DAILY_AVAILABLE_UTC = "00:35:00"
MARKET_CAP_POLL_HOUR = 0
MARKET_CAP_POLL_MINUTE = 45
MARKET_CAP_POLL_ATTEMPT_OFFSETS_MINUTES = (0, 5, 10)
MARKET_CAP_POLL_RESPONSE_TIMEOUT_SECONDS = 45
MARKET_CAP_POLL_HARD_CUTOFF_MINUTE = 56
MARKET_CAP_REQUERY_DATE_OFFSETS = (1, 2, 3)
MARKET_CAP_SOURCE_METADATA_VERIFIED_AT = "2026-09-09"

MARKET_CAP_SELECTION_CRITERIA = (
    "machine_accessible_without_a_negotiated_credential",
    "stable_asset_and_field_identity",
    "clear_observation_timestamp_semantics",
    "cadence_sufficient_for_the_frozen_strategy_decision_cadence",
    "revision_semantics_available_or_capturable",
    "reproducible_at_replay",
    "operationally_maintainable_from_existing_repository_boundaries",
    "candidate_neutral_with_respect_to_the_reference_under_test",
)

MARKET_CAP_DERIVED_CONSTRUCTION_CONSIDERED = {
    "construction": "market_cap = BTC price x circulating supply",
    "rejected": True,
    "rejected_because": (
        "It is not owned by any repository authority and this task declines to "
        "establish it. It would require a second frozen acquisition contract "
        "for an independently reproducible circulating-supply series, and it "
        "would make an exogenous feature input depend on a BTC price series at "
        "a time when PRICE_SOURCE_POLICY_V1 leaves the canonical production "
        "reference UNRESOLVED and this corpus is comparing two reference "
        "identities. SHARED_EXOGENOUS_INPUT_RULE requires every exogenous input "
        "to be identical across the candidate and control tracks, so an input "
        "derived from the reference under test is inadmissible here. Consuming "
        "an authoritative market-cap feed is materially less methodology, and "
        "the ticket's own instruction is to prefer the direct feed."
    ),
}

MARKET_CAP_SOURCE_VERIFICATION_OBLIGATION = (
    "Official CoinGecko documentation and one non-persisted schema probe on "
    "2026-09-09 verified that /coins/bitcoin/history returns USD market cap for "
    "a requested date, labels the snapshot at 00:00 UTC, and exposes the last "
    "completed day at 00:35 on the next UTC day. CoinGecko also documents "
    "scheduled market-cap restatements through day + 2 and exposes no finality "
    "field. This contract therefore freezes observable scheduled retrieval, not "
    "an unknowable provider-first-publication instant. POSTP1-004 must implement "
    "this exact source against the generic-series boundary. If it cannot, the "
    "collector must fail closed and the contract must be reissued as "
    f"{PROSPECTIVE_MARKET_CAP_ACQUISITION_SUCCESSOR} with a new collection "
    "epoch; it may never be silently adapted to whatever the provider happens "
    "to publish."
)


def prospective_btc_market_cap_acquisition_contract() -> dict[str, Any]:
    """Freeze one exact prospective BTC market-cap source, before any data."""

    if EXISTING_MARKET_CAP_PRODUCER is not None:
        raise ProspectiveCorpusError(
            "an existing market-cap producer must be consumed rather than frozen"
        )
    if MARKET_CAP_SERIES_TYPE in _generic_series.SUPPORTED_SERIES_TYPES:
        raise ProspectiveCorpusError(
            "the market-cap series type is no longer a new acquisition "
            "vocabulary member; rebind the contract to the existing owner"
        )
    payload = {
        "acquisition_governance": _acquisition_provenance(),
        "acquisition_schedule": {
            "attempt_offsets_minutes": list(
                MARKET_CAP_POLL_ATTEMPT_OFFSETS_MINUTES
            ),
            "first_poll_utc": (
                f"{MARKET_CAP_POLL_HOUR:02d}:{MARKET_CAP_POLL_MINUTE:02d}:00"
            ),
            "hard_cutoff_utc": (
                f"{MARKET_CAP_POLL_HOUR:02d}:"
                f"{MARKET_CAP_POLL_HARD_CUTOFF_MINUTE:02d}:00"
            ),
            "http_method": "GET",
            "provider_documented_completed_day_available_utc": (
                MARKET_CAP_PROVIDER_DAILY_AVAILABLE_UTC
            ),
            "provider_endpoint": MARKET_CAP_PROVIDER_ENDPOINT,
            "query_parameters": {
                "date": "YYYY-MM-DD for each requested UTC observation date",
                "localization": "false",
            },
            "request_parameter_canonicalization": (
                "UTF-8 RFC3986 query values, keys sorted lexicographically as "
                "date=YYYY-MM-DD&localization=false"
            ),
            "requested_date_offsets_from_poll_day": list(
                MARKET_CAP_REQUERY_DATE_OFFSETS
            ),
            "response_field": MARKET_CAP_PROVIDER_FIELD,
            "response_timeout_seconds": (
                MARKET_CAP_POLL_RESPONSE_TIMEOUT_SECONDS
            ),
            "timeout_boundary": (
                "Scientifically successful response requires mechanically "
                "derived same-domain monotonic elapsed time <= 45.000 seconds; "
                "45.001 seconds is TIMEOUT. The 00:56 cycle cutoff is separate."
            ),
            "retry_rule": (
                "At the fixed offsets 0, 5 and 10 minutes from 00:45 UTC, "
                "request each still-unresolved date. Stop requesting that date "
                "after its first valid response in the cycle. No response "
                "completed after the 00:56 UTC hard cutoff belongs to that "
                "cycle. Persist one audit result for every attempt, including "
                "timeouts and invalid payloads."
            ),
            "revision_capture": (
                "Each cycle requests poll-day minus 1, 2 and 3 UTC dates so "
                "CoinGecko's documented through-day+2 recalculations can be "
                "observed prospectively. Persist exact raw response bytes in "
                "BYTEA plus their digest and "
                "append a revision row only when the valid payload or parsed "
                "USD value differs from the latest captured row."
            ),
        },
        "asset": "BTC",
        "clock_integrity": {
            "contract": PROSPECTIVE_CLOCK_INTEGRITY_VERSION,
            "definition_sha256": prospective_clock_integrity_contract()[
                "definition_sha256"
            ],
            "response_without_valid_clock_is_scientific_evidence": False,
        },
        "available_at_semantics": (
            "The collector's locally observed wall-clock instant at which the "
            "complete, successful HTTP response for that requested date was "
            "received and validated. It is not a claim about when CoinGecko "
            "first published or finalized the value and is never back-dated "
            "to observation_time. A revision whose available_at is later than "
            "decision_time is invisible to that decision."
        ),
        "consumer_binding": {
            "consuming_features": [
                "OI_INTENSITY",
                "OI_INTENSITY_PERCENTILE_180D",
            ],
            "feature_owner": (
                "btc_predictor.features.positioning.open_interest_intensity"
            ),
            "feature_semantics_unchanged": True,
            "pre_owner_selector": (
                "select_market_cap_revisions_for_decision; supplies at most "
                "one, exactly latest-available revision per observation_time "
                "because the historical owner averages duplicate timestamps"
            ),
            "pre_owner_selector_input": "ProspectiveMarketCapObservation",
            "observation_grid_alignment": (
                "The frozen owner forms intensity only on the exact "
                "intersection of the open-interest aggregate observation_time "
                "set and the market-cap observation_time set "
                "(_open_interest_intensity_by_time). The prospective "
                "open-interest capture consumed by OI_INTENSITY must therefore "
                "present its aggregate on this same exact "
                f"{MARKET_CAP_OBSERVATION_GRID} grid. This is an acquisition "
                "alignment requirement on the prospective capture layer only; "
                "no positioning formula is altered."
            ),
            "open_interest_unit_rule": (
                "The open_interest_unit selector the owner requires is pinned "
                "once per collection epoch and persisted with it. This contract "
                "does not choose it and no unit choice may be revisited after "
                "collection starts."
            ),
            "typed_boundary": (
                "btc_predictor.features.positioning.MarketCapObservation"
            ),
        },
        "decision_binding": {
            "cycle_selection": (
                "Use the current UTC poll day only once its 00:56 hard cutoff "
                "has passed; before then use the prior UTC poll day."
            ),
            "daily_00_05_example": (
                "A decision on UTC day D at 00:05 uses the completed prior "
                "poll cycle on D-1, whose required observation is D-2 00:00."
            ),
            "hourly_01_05_example": (
                "A decision on UTC day D at 01:05 uses the completed poll "
                "cycle on D, whose required observation is D-1 00:00."
            ),
            "required_observation": (
                "Exactly poll-day minus 1 at 00:00 UTC. The latest revision of "
                "that date available by decision_time is required."
            ),
            "selector": "required_market_cap_observation_time",
        },
        "derived_construction": MARKET_CAP_DERIVED_CONSTRUCTION_CONSIDERED,
        "epoch_rule": (
            "Any change to the series identity, provider identity, cadence, "
            "unit or timestamp semantics requires "
            f"{PROSPECTIVE_MARKET_CAP_ACQUISITION_SUCCESSOR} and a new "
            "prospective collection epoch for OI_INTENSITY and "
            "OI_INTENSITY_PERCENTILE_180D. No observation is resampled or "
            "relabelled backwards."
        ),
        "existing_producer": {
            "evidence": EXISTING_MARKET_CAP_PRODUCER_EVIDENCE,
            "existing_market_cap_producer": EXISTING_MARKET_CAP_PRODUCER,
            "generic_series_family_is_sufficient": False,
            "unqualified_generic_series_dependency_permitted": False,
        },
        "ingested_at_semantics": (
            "The wall-clock instant the capture layer persisted the row. It "
            "orders storage only and never admits or excludes an observation "
            "from a decision."
        ),
        "metric": "market_cap_usd",
        "missing_value_handling": {
            "late_observation": ACQUISITION_FEED_STATE_REQUIRED,
            "missing_observation": ACQUISITION_FEED_STATE_REQUIRED,
            "statement": (
                "If the exact observation date required by decision_binding "
                "has no valid revision available by decision_time, every "
                "OI-intensity feature is NOT_EVALUABLE. An older observation "
                "is never substituted. The value is never zero-filled, "
                "defaulted, carried forward or reconstructed from price."
            ),
            "zero_fill_permitted": False,
        },
        "observation_cadence": MARKET_CAP_OBSERVATION_CADENCE,
        "observation_time_semantics": (
            "The exact UTC start instant of the observed day, "
            f"{MARKET_CAP_OBSERVATION_GRID}. An off-grid observation_time is "
            "refused at capture and never snapped."
        ),
        "pit_rule": PIT_RULE,
        "protocol_version": PROTOCOL_VERSION,
        "provider_identity": {
            "one_provider_per_epoch": True,
            "provider": MARKET_CAP_PROVIDER_ID,
            "provider_asset_identifier": MARKET_CAP_PROVIDER_ASSET_IDENTIFIER,
            "provider_boundary": (
                "btc_predictor.data.generic_series.MacroDataProvider"
            ),
            "provider_field": MARKET_CAP_PROVIDER_FIELD,
            "provider_client_exists_in_repository": False,
            "recorded_per_observation": True,
            "source": MARKET_CAP_PROVIDER_SOURCE,
            "source_documentation": MARKET_CAP_PROVIDER_DOCUMENTATION,
            "source_metadata_verified_at": (
                MARKET_CAP_SOURCE_METADATA_VERIFIED_AT
            ),
            "source_revision_documentation": (
                MARKET_CAP_REVISION_DOCUMENTATION
            ),
            "verification_obligation": (
                MARKET_CAP_SOURCE_VERIFICATION_OBLIGATION
            ),
        },
        "request_response_identity": {
            "observation_constructor": "ProspectiveMarketCapObservation",
            "request_attempt_record": "CoinGeckoMarketCapRequestAttempt",
            "request_attempt_contract": (
                COINGECKO_MARKET_CAP_REQUEST_ATTEMPT_VERSION
            ),
            "request_attempt_definition_sha256": (
                coingecko_market_cap_request_attempt_contract()[
                    "definition_sha256"
                ]
            ),
            "raw_response_bytes_persistence": "PostgreSQL BYTEA",
            "response_validation_contract": (
                COINGECKO_MARKET_CAP_RESPONSE_VALIDATION_VERSION
            ),
            "response_validation_definition_sha256": (
                coingecko_market_cap_response_validation_contract()[
                    "definition_sha256"
                ]
            ),
            "unbound_observation_time_value_provider_tuple_permitted": False,
        },
        "revision_policy": (
            "NEW_REVISION_ROW_PER_RESTATEMENT, the existing raw.generic_series "
            "convention. A restated day is a new revision row keyed by "
            "(series_id, observation_time, revision); the earlier revision is "
            "retained verbatim. For every observation_time, the pre-owner "
            "selector chooses exactly the single revision having the greatest "
            "available_at not later than decision_time. Revisions are never "
            "averaged, and equal-available_at conflicts fail closed."
        ),
        "schema_version": "PROSPECTIVE_BTC_MARKET_CAP_ACQUISITION_V1",
        "observation_schema_version": PROSPECTIVE_MARKET_CAP_OBSERVATION_VERSION,
        "selection": {
            "criteria": list(MARKET_CAP_SELECTION_CRITERIA),
            "oi_intensity_values_inspected": False,
            "rationale": (
                "CoinGecko's requested-date history endpoint exposes one BTC "
                "USD market-cap field with documented daily timing and "
                "restatement behavior. raw.generic_series is the repository's "
                "point-in-time scalar-series boundary and already carries "
                "observation_time, available_at, ingested_at, provider, source, "
                "unit and revision. Fixed polling makes the provider's changing "
                "value locally observable without pretending it exposes a "
                "finality timestamp. A direct feed is preferred over the "
                "price-derived construction under derived_construction. No "
                "OI-intensity or Stage-B value was inspected."
            ),
            "stage_b_outcomes_inspected": False,
        },
        "series_identity": {
            "identity_fields": ["series_id", "series_type", "provider"],
            "identity_is_exact": True,
            "raw_table": MARKET_CAP_RAW_TABLE,
            "series_id": MARKET_CAP_SERIES_ID,
            "series_type": MARKET_CAP_SERIES_TYPE,
            "series_type_is_new_acquisition_vocabulary": True,
            "series_type_vocabulary_extension_owner": (
                "btc_predictor.data.generic_series.SUPPORTED_SERIES_TYPES"
            ),
            "series_type_vocabulary_extension_required_of": "POSTP1-004",
            "unit": MARKET_CAP_SERIES_UNIT,
            "unqualified_family_dependency_permitted": False,
        },
        "source_replacement_policy": (
            "A source replacement is never retroactive. The retired provider's "
            "observations are retained verbatim, the replacement is frozen as "
            f"{PROSPECTIVE_MARKET_CAP_ACQUISITION_SUCCESSOR}, and a new "
            "collection epoch begins for the affected features. Two providers "
            "are never blended into one series and a gap is never patched from "
            "a second provider."
        ),
        "units": "USD",
        "version": PROSPECTIVE_MARKET_CAP_ACQUISITION_VERSION,
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def market_cap_poll_cycle_for_decision(decision_time: datetime) -> datetime:
    """Return the nominal 00:45 UTC poll cycle completed for a decision."""

    decision = _require_utc_instant(decision_time, "decision_time")
    poll_day = decision.date()
    cutoff = datetime(
        poll_day.year,
        poll_day.month,
        poll_day.day,
        MARKET_CAP_POLL_HOUR,
        MARKET_CAP_POLL_HARD_CUTOFF_MINUTE,
        tzinfo=UTC,
    )
    if decision < cutoff:
        poll_day -= timedelta(days=1)
    return datetime(
        poll_day.year,
        poll_day.month,
        poll_day.day,
        MARKET_CAP_POLL_HOUR,
        MARKET_CAP_POLL_MINUTE,
        tzinfo=UTC,
    )


@dataclass(frozen=True)
class ProspectiveMarketCapObservation:
    """Append-only revision built only from one validated request/response."""

    validated_response: ValidatedCoinGeckoMarketCapResponse
    revision: str
    ingested_at: datetime

    @property
    def observation_time(self) -> datetime:
        return self.validated_response.as_record()["observation_time"]

    @property
    def market_cap_usd(self) -> Decimal:
        return self.validated_response.market_cap_usd

    @property
    def series_id(self) -> str:
        return MARKET_CAP_SERIES_ID

    @property
    def series_type(self) -> str:
        return MARKET_CAP_SERIES_TYPE

    @property
    def unit(self) -> str:
        return MARKET_CAP_SERIES_UNIT

    @property
    def provider(self) -> str:
        return MARKET_CAP_PROVIDER_ID

    @property
    def source(self) -> str:
        return MARKET_CAP_PROVIDER_SOURCE

    @property
    def available_at(self) -> datetime:
        return self.validated_response.as_record()["available_at"]

    def as_record(self) -> dict[str, Any]:
        independently_validated = validate_coingecko_market_cap_response(
            self.validated_response.request
        )
        if independently_validated.market_cap_usd != self.validated_response.market_cap_usd:
            raise ProspectiveCorpusError(
                "market-cap value does not reproduce from the bound response"
            )
        validated = self.validated_response.as_record()
        request = self.validated_response.request.as_record()
        expected_acquisition_hash = prospective_btc_market_cap_acquisition_contract()[
            "definition_sha256"
        ]
        if request["acquisition_contract_sha256"] != expected_acquisition_hash:
            raise ProspectiveCorpusError(
                "market-cap request is not bound to the frozen acquisition contract"
            )
        observation_time = validated["observation_time"]
        available_at = validated["available_at"]
        ingested_at = _require_utc_instant(self.ingested_at, "ingested_at")
        if ingested_at < available_at:
            raise ProspectiveCorpusError(
                "market-cap ingested_at cannot precede available_at"
            )
        if not isinstance(self.revision, str) or not self.revision.strip():
            raise ProspectiveCorpusError("market-cap revision must be non-empty")
        payload = {
            "available_at": available_at,
            "ingested_at": ingested_at,
            "market_cap_usd": validated["market_cap_usd"],
            "observation_time": observation_time,
            "provider": validated["provider"],
            "request_sha256": validated["request_sha256"],
            "request_record": request,
            "request_record_sha256": validated["request_record_sha256"],
            "requested_date": validated["requested_date"],
            "response_sha256": validated["response_sha256"],
            "revision": self.revision,
            "schema_version": PROSPECTIVE_MARKET_CAP_OBSERVATION_VERSION,
            "series_id": MARKET_CAP_SERIES_ID,
            "series_type": MARKET_CAP_SERIES_TYPE,
            "source": validated["source"],
            "unit": MARKET_CAP_SERIES_UNIT,
            "validated_response_sha256": validated["record_sha256"],
        }
        payload["record_sha256"] = _source_integrity.digest(payload)
        return payload

    def evidence_records(self) -> dict[str, dict[str, Any]]:
        records = self.validated_response.evidence_records()
        row = self.as_record()
        records[row["record_sha256"]] = row
        return records

    def as_owner_observation(self) -> _positioning.MarketCapObservation:
        record = self.as_record()
        return _positioning.MarketCapObservation(
            observation_time=record["observation_time"],
            market_cap_usd=record["market_cap_usd"],
            provider=record["provider"],
            available_at=record["available_at"],
        )


def replay_prospective_market_cap_observation(
    record_sha256: str,
    resolver: PersistedEvidenceResolver,
) -> dict[str, Any]:
    persisted = resolver.resolve(
        record_sha256,
        schema_version=PROSPECTIVE_MARKET_CAP_OBSERVATION_VERSION,
    )
    validated_persisted = resolver.resolve(persisted["validated_response_sha256"])
    validated_response = replay_coingecko_market_cap_response(
        persisted["request_record_sha256"], resolver
    )
    validated = validated_response.as_record()
    if validated != validated_persisted:
        raise ProspectiveCorpusError(
            "validated market-cap response does not replay from its attempt"
        )
    request = resolver.resolve(persisted["request_record_sha256"])
    if request != persisted["request_record"]:
        raise ProspectiveCorpusError(
            "market-cap surface request snapshot differs from resolved attempt"
        )
    replayed = ProspectiveMarketCapObservation(
        validated_response=validated_response,
        revision=persisted["revision"],
        ingested_at=persisted["ingested_at"],
    ).as_record()
    if persisted != replayed:
        raise ProspectiveCorpusError(
            "market-cap surface differs from replayed request/response evidence"
        )
    return replayed


def required_market_cap_observation_time(decision_time: datetime) -> datetime:
    """Return the one daily observation required by the completed poll cycle."""

    poll_cycle = market_cap_poll_cycle_for_decision(decision_time)
    return poll_cycle.replace(hour=0, minute=0) - timedelta(days=1)


def select_market_cap_revisions_for_decision(
    market_caps: Sequence[ProspectiveMarketCapObservation],
    *,
    decision_time: datetime,
) -> tuple[_positioning.MarketCapObservation, ...]:
    """Select one latest PIT revision per day and require the scheduled date."""

    decision = _require_utc_instant(decision_time, "decision_time")
    required_time = required_market_cap_observation_time(decision)
    grouped: dict[
        datetime,
        list[ProspectiveMarketCapObservation],
    ] = {}
    for observation in market_caps:
        record = observation.as_record()
        observation_time = record["observation_time"]
        if (
            observation_time.hour
            or observation_time.minute
            or observation_time.second
            or observation_time.microsecond
        ):
            raise ProspectiveCorpusError(
                "market-cap observation must be an exact UTC day start"
            )
        if (
            record["series_id"] != MARKET_CAP_SERIES_ID
            or record["series_type"] != MARKET_CAP_SERIES_TYPE
            or record["unit"] != MARKET_CAP_SERIES_UNIT
            or record["provider"] != MARKET_CAP_PROVIDER_ID
            or record["source"] != MARKET_CAP_PROVIDER_SOURCE
        ):
            raise ProspectiveCorpusError(
                "unexpected market-cap series/provider/source identity"
            )
        if (
            observation_time <= required_time
            and record["available_at"] <= decision
        ):
            grouped.setdefault(observation_time, []).append(observation)

    selected: list[_positioning.MarketCapObservation] = []
    for observation_time in sorted(grouped):
        revisions = grouped[observation_time]
        revision_ids = [row.revision for row in revisions]
        if len(revision_ids) != len(set(revision_ids)):
            raise ProspectiveCorpusError(
                "duplicate market-cap revision identity for one observation"
            )
        revisions.sort(key=lambda row: row.available_at)
        if (
            len(revisions) > 1
            and revisions[-1].available_at == revisions[-2].available_at
        ):
            raise ProspectiveCorpusError(
                "conflicting market-cap revisions share one available_at instant"
            )
        selected.append(revisions[-1].as_owner_observation())
    if required_time not in grouped:
        raise ProspectiveCorpusError(
            "MARKET_CAP_REQUIRED_OBSERVATION_MISSING: "
            f"{required_time.isoformat()}"
        )
    return tuple(selected)


# ---------------------------------------------------------------------------
# 3b.3 PROSPECTIVE_LIQUIDATION_CAPTURE_V1
# ---------------------------------------------------------------------------
#
# ``aggregate_btc_derivatives_available_at`` starts long_liquidations_usd and
# short_liquidations_usd at Decimal("0") and adds whatever Liquidation rows are
# available.  An hour with no rows because the feed was down and an hour with no
# rows because nothing liquidated therefore produce byte-identical zeros.  The
# aggregate carries no feed-state field of any kind, so the distinction is not
# recoverable downstream.  This is stated as a fact about the existing owner,
# not repaired in it: the fix belongs to the prospective capture layer.

LIQUIDATION_AGGREGATE_OWNER = (
    "btc_predictor.data.derivatives.aggregate_btc_derivatives_available_at"
)
LIQUIDATION_PROVIDER_ID = CVD_PERPETUAL_PROVIDER_ID
LIQUIDATION_ENDPOINT = CVD_PERPETUAL_ENDPOINT
LIQUIDATION_INSTRUMENT = CVD_PERPETUAL_INSTRUMENT
LIQUIDATION_SOURCE_DOCUMENTATION = CVD_PERPETUAL_SOURCE_DOCUMENTATION
LIQUIDATION_INSTRUMENT_METADATA_ENDPOINT = (
    CVD_PERPETUAL_INSTRUMENT_METADATA_ENDPOINT
)
LIQUIDATION_EVENT_TYPE = "liquidation"
LIQUIDATION_CONTRACT_SIZE_USD = Decimal("1")
LIQUIDATION_TIMEFRAME = "1h"
LIQUIDATION_SOURCE_METADATA_VERIFIED_AT = CVD_SOURCE_METADATA_VERIFIED_AT
LIQUIDATION_SIDE_TO_POSITION = {
    "buy": "short",
    "sell": "long",
}
EXISTING_AGGREGATE_DISTINGUISHES_MISSING_FROM_EMPTY = False
EXISTING_AGGREGATE_EVIDENCE = (
    "The owner initialises long_liquidations_usd and short_liquidations_usd to "
    "Decimal('0') and accumulates only the Liquidation rows it was given. It "
    "records no feed status, no event count and no per-interval coverage, so an "
    "unavailable feed and an observed interval with zero liquidation events "
    "both yield exactly 0. BtcDerivativesAggregate exposes no field that could "
    "separate them afterwards."
)

FEED_STATUS_OBSERVED_WITH_EVENTS = "OBSERVED_WITH_EVENTS"
FEED_STATUS_OBSERVED_ZERO_EVENTS = "OBSERVED_ZERO_EVENTS"
FEED_STATUS_SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
FEED_STATUS_LATE = "LATE"
FEED_STATUS_INVALID = "INVALID"
LIQUIDATION_FEED_STATUSES = (
    FEED_STATUS_INVALID,
    FEED_STATUS_LATE,
    FEED_STATUS_OBSERVED_WITH_EVENTS,
    FEED_STATUS_OBSERVED_ZERO_EVENTS,
    FEED_STATUS_SOURCE_UNAVAILABLE,
)
LIQUIDATION_OBSERVED_FEED_STATUSES = (
    FEED_STATUS_OBSERVED_WITH_EVENTS,
    FEED_STATUS_OBSERVED_ZERO_EVENTS,
)
LIQUIDATION_UNUSABLE_FEED_STATUSES = (
    FEED_STATUS_INVALID,
    FEED_STATUS_LATE,
    FEED_STATUS_SOURCE_UNAVAILABLE,
)

LIQUIDATION_FEED_STATUS_SEMANTICS: dict[str, dict[str, Any]] = {
    FEED_STATUS_OBSERVED_WITH_EVENTS: {
        "definition": (
            "The frozen Kraken PI_XBTUSD trade subscription satisfied every "
            "interval-completion predicate and reported at least one event "
            "whose provider trade type is liquidation."
        ),
        "event_count_rule": "event_count > 0",
        "feature_input_state": "PRESENT",
        "notional_before_normalization": "the observed signed-side USD notional",
        "usable_as_an_observation": True,
    },
    FEED_STATUS_OBSERVED_ZERO_EVENTS: {
        "definition": (
            "The frozen Kraken PI_XBTUSD trade subscription satisfied every "
            "interval-completion predicate and reported no event whose "
            "provider trade type is liquidation. The interval was observed; "
            "the market simply produced nothing."
        ),
        "event_count_rule": "event_count == 0",
        "feature_input_state": "PRESENT",
        "notional_before_normalization": (
            "0 USD, which is a legitimate observed value and not a fill-in"
        ),
        "usable_as_an_observation": True,
    },
    FEED_STATUS_SOURCE_UNAVAILABLE: {
        "definition": (
            "The frozen subscription was not acknowledged before interval "
            "start, or its uninterrupted epoch, collector-owned transport "
            "liveness, collector health, or clock coverage did not remain "
            "valid through interval close."
        ),
        "event_count_rule": "event_count is null",
        "feature_input_state": ACQUISITION_FEED_STATE_REQUIRED,
        "notional_before_normalization": (
            "null; a numeric zero is refused for this status"
        ),
        "usable_as_an_observation": False,
    },
    FEED_STATUS_LATE: {
        "definition": (
            "The interval's liquidation evidence first became retrievable after "
            "the decision instant that needed it. The decision is closed and is "
            "never reopened or backfilled."
        ),
        "event_count_rule": "event_count is null at that decision",
        "feature_input_state": ACQUISITION_FEED_STATE_REQUIRED,
        "notional_before_normalization": (
            "null at that decision; a numeric zero is refused for this status"
        ),
        "usable_as_an_observation": False,
    },
    FEED_STATUS_INVALID: {
        "definition": (
            "The provider answered but the payload failed a capture-layer "
            "validity rule: wrong provider/instrument, applicable in-epoch "
            "sequence validation, unknown "
            "side or event type, non-positive quantity, inconsistent count or "
            "notional, conflicting uid, or source-id digest mismatch."
        ),
        "event_count_rule": "event_count is null",
        "feature_input_state": ACQUISITION_FEED_STATE_REQUIRED,
        "notional_before_normalization": (
            "null; a numeric zero is refused for this status"
        ),
        "usable_as_an_observation": False,
    },
}

LIQUIDATION_CAPTURE_FIELDS = (
    "observation_time",
    "available_at",
    "ingested_at",
    "provider",
    "instrument",
    "timeframe",
    "event_type",
    "contract_size_usd",
    "source_stream_epoch_sha256",
    "stream_liveness_sha256",
    "collector_health_sha256",
    "clock_integrity_sha256",
    "completion_evidence_sha256",
    "feed_status",
    "event_count",
    "long_liquidation_notional_usd",
    "short_liquidation_notional_usd",
    "source_record_ids_digest",
    "revision",
)


def classify_liquidation_feed_interval(
    completeness: StreamIntervalCompleteness,
    *,
    decision_time: datetime,
) -> dict[str, Any]:
    """Classify one hour from verified lifecycle/event records only."""

    return _source_integrity.classify_liquidation_interval(
        completeness,
        decision_time=decision_time,
    )


def prospective_liquidation_capture_contract() -> dict[str, Any]:
    """Freeze liquidation feed state separately from the aggregate value."""

    if EXISTING_AGGREGATE_DISTINGUISHES_MISSING_FROM_EMPTY:
        raise ProspectiveCorpusError(
            "the existing aggregate does not distinguish a missing feed from an "
            "observed empty feed; the contract may not claim that it does"
        )
    covered = set(LIQUIDATION_FEED_STATUS_SEMANTICS)
    if covered != set(LIQUIDATION_FEED_STATUSES):
        raise ProspectiveCorpusError("every feed status needs frozen semantics")
    for status in LIQUIDATION_UNUSABLE_FEED_STATUSES:
        row = LIQUIDATION_FEED_STATUS_SEMANTICS[status]
        if row["usable_as_an_observation"] or row["feature_input_state"] != (
            ACQUISITION_FEED_STATE_REQUIRED
        ):
            raise ProspectiveCorpusError(
                f"{status} must make the required liquidation input missing"
            )
    payload = {
        "acquisition_governance": _acquisition_provenance(),
        "available_at_semantics": (
            "The clock-integrity-validated UTC wall-clock instant at which the closed interval and all "
            "of its completion evidence were validated. It is never back-dated "
            "to interval close and makes no claim about a provider finality "
            "timestamp. Durations and deadlines use the monotonic clock."
        ),
        "capture_fields": list(LIQUIDATION_CAPTURE_FIELDS),
        "captured_interval": {
            "cadence": "1h",
            "cadence_rationale": (
                "Liquidation evidence is captured on the same exact-UTC-hour "
                "grid the stop-evaluation cadence and raw.btc_ohlcv already "
                "use, so an interval's coverage is decidable at the decision "
                "instant that consumes it and no interval is aggregated from "
                "shorter ones. Selected as new pre-data governance, not "
                "inherited."
            ),
            "observation_time_semantics": (
                "the exact UTC start instant of the closed interval"
            ),
        },
        "consuming_features": [
            "ORDERLINESS_SCORE",
            "REGIME_SCORE",
            "REGIME_SMOOTHED_SCORE",
            "VOLATILITY_SCORE",
        ],
        "event_census": {
            "contract_size_usd": str(LIQUIDATION_CONTRACT_SIZE_USD),
            "included_event_type": LIQUIDATION_EVENT_TYPE,
            "notional_rule": (
                "For PI_XBTUSD, liquidation USD notional equals provider qty "
                "times the instrument metadata contractSize of 1 USD."
            ),
            "other_trade_types_included": False,
            "side_mapping": dict(LIQUIDATION_SIDE_TO_POSITION),
            "side_rule": (
                "Kraken side is taker side: sell liquidates a long position and "
                "buy liquidates a short position. Unknown sides invalidate the "
                "whole interval."
            ),
            "source_identity": (
                "Every included provider uid is unique within the frozen "
                "provider/instrument feed and the sorted set is hash-bound to "
                "the interval."
            ),
        },
        "duplicate_semantics": (
            "One row per (provider, instrument, timeframe, observation_time, "
            "revision). A conflicting duplicate is refused and recorded as a "
            "data-quality event."
        ),
        "epoch_rule": (
            "Any change to the captured interval, provider, instrument "
            "universe or feed-status vocabulary requires "
            f"{PROSPECTIVE_LIQUIDATION_CAPTURE_SUCCESSOR} and a new prospective "
            "collection epoch."
        ),
        "existing_aggregate": {
            "distinguishes_missing_from_empty": (
                EXISTING_AGGREGATE_DISTINGUISHES_MISSING_FROM_EMPTY
            ),
            "evidence": EXISTING_AGGREGATE_EVIDENCE,
            "modified_by_this_protocol": False,
            "owner": LIQUIDATION_AGGREGATE_OWNER,
        },
        "feed_state_is_independent_of_the_numeric_value": True,
        "feed_status_semantics": LIQUIDATION_FEED_STATUS_SEMANTICS,
        "feed_status_vocabulary": list(LIQUIDATION_FEED_STATUSES),
        "interval_completion_predicate": {
            "all_required": True,
            "classifier": "classify_liquidation_feed_interval",
            "complete_is_caller_supplied": False,
            "definition_sha256": liquidation_interval_completeness_contract()[
                "definition_sha256"
            ],
            "conditions": [
                "one SOURCE_STREAM_EPOCH_V1 acknowledged strictly before interval start",
                "the same epoch remains valid continuously through interval close",
                "collector-owned STREAM_LIVENESS_POLICY_V1 passes",
                "collector health has no parser, serialization, durable-append, queue, drop, unexpected-message, duplicate-conflict, exception or sequence-validation failure",
                "event census is reconstructed from exact epoch-bound events",
                "every event received_at is clock-validated and no later than finalization",
                "PI_XBTUSD runtime metadata passes before interval start and again at finalization",
                "finalization and available_at bind usable clock-integrity evidence",
            ],
            "failure_semantics": (
                "Incomplete coverage is SOURCE_UNAVAILABLE; evidence arriving "
                "after decision is LATE; malformed or internally inconsistent "
                "evidence is INVALID. None may carry numeric notionals."
            ),
            "observed_zero_rule": (
                "OBSERVED_ZERO_EVENTS is permitted only when every condition "
                "passes, event_count is zero, the source-id set is empty and "
                "both side notionals equal zero."
            ),
        },
        "missing_feed_can_become_numeric_zero": False,
        "daily_census": {
            "contract": LIQUIDATION_UTC_DAY_CENSUS_VERSION,
            "definition_sha256": liquidation_utc_day_census_contract()[
                "definition_sha256"
            ],
            "expected_exact_utc_hours": 24,
            "requires_independent_hour_replay": True,
            "surface_status_is_authority": False,
        },
        "observed_feed_statuses": list(LIQUIDATION_OBSERVED_FEED_STATUSES),
        "pit_rule": PIT_RULE,
        "protocol_version": PROTOCOL_VERSION,
        "provider_identity": {
            "endpoint": LIQUIDATION_ENDPOINT,
            "event_feed": "Kraken Futures WebSocket v1 trade",
            "instrument": LIQUIDATION_INSTRUMENT,
            "instrument_metadata_endpoint": (
                LIQUIDATION_INSTRUMENT_METADATA_ENDPOINT
            ),
            "instrument_type": "perpetual_swap",
            "one_provider_and_instrument_per_epoch": True,
            "provider": LIQUIDATION_PROVIDER_ID,
            "quote_currency": "USD",
            "source_documentation": LIQUIDATION_SOURCE_DOCUMENTATION,
            "source_metadata_verified_at": (
                LIQUIDATION_SOURCE_METADATA_VERIFIED_AT
            ),
            "statement": (
                "Only liquidation-typed trade events from Kraken Futures "
                "PI_XBTUSD form the interval census. A partial venue, alternate "
                "instrument, stablecoin quote or secondary source may not be "
                "called complete or patched into this epoch."
            ),
        },
        "provenance": {
            "raw_table": "raw.liquidations",
            "source_record_identity": (
                "Every contributing raw liquidation record id is retained and a "
                "digest over the sorted id set is persisted with the interval, "
                "so an interval's numeric value is always traceable to the "
                "exact record set that produced it."
            ),
            "typed_raw_row": "btc_predictor.data.derivatives.Liquidation",
        },
        "replay_rule": (
            "Resolve the complete SOURCE_STREAM_EPOCH_V1, liveness, collector-"
            "health, clock, runtime metadata and source-event census records; "
            "recompute every digest and predicate; then rederive feed_status, "
            "event_count and notionals. This reproduces the missing-versus-empty "
            "distinction from storage. A self-consistent rehashed surface row "
            "cannot override its cited completeness evidence. The daily reducer "
            "repeats this transitive replay for all 24 exact hours."
        ),
        "scientific_evidence_resolver_sha256": (
            scientific_evidence_resolver_contract()["definition_sha256"]
        ),
        "revision_semantics": (
            "Append-only. A provider restatement of a closed interval is a new "
            "revision row; the earlier revision is retained verbatim and a "
            "decision replays against the revision available at its own "
            "decision_time. A revision may change feed_status only forwards "
            "into a new row, never by rewriting an existing one. The adapter "
            "selects exactly the latest revision available per interval before "
            "calling any historical aggregate owner."
        ),
        "schema_version": "PROSPECTIVE_LIQUIDATION_CAPTURE_V1",
        "units": (
            "USD notional per side from 1 USD PI_XBTUSD contracts; event_count "
            "is a count"
        ),
        "unusable_feed_statuses": list(LIQUIDATION_UNUSABLE_FEED_STATUSES),
        "version": PROSPECTIVE_LIQUIDATION_CAPTURE_VERSION,
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


# ---------------------------------------------------------------------------
# 3b.4 PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_V1
# ---------------------------------------------------------------------------
#
# ``calculate_orderliness_score`` consumes ``liquidation_percentile`` as an
# already-normalized input and no executable owner in this repository produces
# it: a repository-wide search finds the name only as a score input, a config
# threshold and a reporting field.  Option A of the ticket therefore fails --
# there is no overlooked owner -- and option B applies.
#
# The choice is not opportunistic.  The repository owns exactly one percentile
# convention, implemented identically in the two existing percentile owners, and
# exactly one of those two owners is co-consumed by the same orderliness score.
# The adapter inherits both rather than inventing a third.

LIQUIDATION_PERCENTILE_ADAPTER_REQUIRED = True
LIQUIDATION_PERCENTILE_EXISTING_OWNER = None
LIQUIDATION_PERCENTILE_OWNER_SEARCH_EVIDENCE = (
    "liquidation_percentile appears in this repository only as an input field "
    "on OrderlinessScoreInput, StressFlagInput and CapitulationFlagInput, as "
    "the configured thresholds liquidation_percentile_min / "
    "liquidation_percentile_max, and as a reporting passthrough in "
    "btc_predictor.reporting.alerts. No function computes it from raw "
    "liquidation notional."
)

LIQUIDATION_PERCENTILE_CONVENTION = "MIDRANK_PERCENTILE_OF_PRIOR_WINDOW_V1"
LIQUIDATION_PERCENTILE_CONVENTION_OWNERS = (
    "btc_predictor.features.volatility._percentile_rank",
    "btc_predictor.features.positioning._percentile_rank",
)
LIQUIDATION_PERCENTILE_CONVENTION_FORMULA = (
    "((count(history < value) + 0.5 * count(history == value)) / "
    "len(history)) * 100"
)

LIQUIDATION_PERCENTILE_WINDOW_DAYS = (
    _volatility.DEFAULT_VOLATILITY_PERCENTILE_WINDOW_DAYS
)
LIQUIDATION_PERCENTILE_MIN_OBSERVATIONS = (
    _volatility.DEFAULT_VOLATILITY_PERCENTILE_MIN_OBSERVATIONS
)

LIQUIDATION_PERCENTILE_WINDOW_RATIONALE = (
    "calculate_orderliness_score weighs liquidation_percentile and "
    "volatility_percentile against thresholds inside one penalty vector, so the "
    "two must be commensurable. volatility_percentile is the only percentile "
    "whose window is already an input to that score, and its owner "
    "btc_predictor.features.volatility.volatility_percentile declares a "
    f"{LIQUIDATION_PERCENTILE_WINDOW_DAYS}-day half-open trailing window with "
    f"{LIQUIDATION_PERCENTILE_MIN_OBSERVATIONS} minimum prior observations. The "
    "adapter inherits exactly that window and minimum rather than importing the "
    "180-day positioning window or authoring a third. The choice is also inert "
    "for the corpus schedule: the resulting first-evaluable requirement is "
    "strictly smaller than VOL_PERCENTILE_2Y's, which already binds the corpus "
    "warmup, so it adds no new constraint. No liquidation value, orderliness "
    "score or Stage-B outcome was inspected."
)


def prospective_liquidation_percentile_adapter_contract() -> dict[str, Any]:
    """Freeze how raw liquidation notional becomes liquidation_percentile."""

    if LIQUIDATION_PERCENTILE_EXISTING_OWNER is not None:
        raise ProspectiveCorpusError(
            "an existing normalization owner must be consumed rather than "
            "replaced by a new adapter"
        )
    if not LIQUIDATION_PERCENTILE_ADAPTER_REQUIRED:
        raise ProspectiveCorpusError(
            AMBIGUOUS_LIQUIDATION_NORMALIZATION_CLASSIFICATION
        )
    payload = {
        "acquisition_governance": _acquisition_provenance(),
        "consumer": (
            "btc_predictor.features.volatility.calculate_orderliness_score "
            "liquidation_cascade component; the same normalized value is the "
            "STRESS and CAPITULATION market-state flag input"
        ),
        "downstream_formula_changed": False,
        "epoch_rule": (
            "Any change to the input quantity, window, minimum observation "
            "count, observation universe or percentile convention requires "
            f"{PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_SUCCESSOR} and a new "
            "prospective collection epoch."
        ),
        "existing_owner": {
            "evidence": LIQUIDATION_PERCENTILE_OWNER_SEARCH_EVIDENCE,
            "executable_owner_found": LIQUIDATION_PERCENTILE_EXISTING_OWNER,
            "new_adapter_required": LIQUIDATION_PERCENTILE_ADAPTER_REQUIRED,
        },
        "input": {
            "daily_census_contract": LIQUIDATION_UTC_DAY_CENSUS_VERSION,
            "daily_census_definition_sha256": liquidation_utc_day_census_contract()[
                "definition_sha256"
            ],
            "feed_status_gate": list(LIQUIDATION_OBSERVED_FEED_STATUSES),
            "quantity": (
                "total observed liquidation notional in USD for one valid "
                "LIQUIDATION_UTC_DAY_CENSUS_V1: long plus short notionals "
                "summed over exactly the 24 expected complete UTC hours"
            ),
            "side_treatment": (
                "Both sides are summed. liquidation_cascade is an aggregate "
                "market-stress component and no repository consumer of "
                "liquidation_percentile expresses a directional preference, so "
                "no side is weighted, dropped or taken as a maximum."
            ),
            "source_contract": PROSPECTIVE_LIQUIDATION_CAPTURE_VERSION,
            "units": "USD",
        },
        "minimum_history": {
            "first_evaluable_contiguous_daily_observations": (
                LIQUIDATION_PERCENTILE_MIN_OBSERVATIONS + 1
            ),
            "minimum_prior_observations": LIQUIDATION_PERCENTILE_MIN_OBSERVATIONS,
            "rule": (
                "Below the minimum the adapter returns no value and records "
                "LIQUIDATION_PERCENTILE_INSUFFICIENT_HISTORY. It never returns "
                "a provisional percentile from a short window."
            ),
        },
        "missing_feed_behavior": {
            "excluded_from_history": list(LIQUIDATION_UNUSABLE_FEED_STATUSES),
            "missing_feed_percentile": None,
            "missing_feed_percentile_zero_permitted": False,
            "observed_zero_events_enters_history": True,
            "observed_zero_events_notional": "0 USD",
            "statement": (
                "A day containing any interval whose feed_status is "
                f"{list(LIQUIDATION_UNUSABLE_FEED_STATUSES)} yields no "
                "liquidation observation: the adapter returns None with reason "
                "LIQUIDATION_FEED_UNAVAILABLE, the day enters neither the "
                "current value nor the history, and the consuming decision is "
                f"{STATE_NOT_EVALUABLE} with reason "
                f"{ACQUISITION_FEED_STATE_REQUIRED}. A day whose intervals are "
                f"all {FEED_STATUS_OBSERVED_ZERO_EVENTS} yields a legitimate 0 "
                "USD notional that is normalized like any other observation. A "
                "missing feed can never become a zero percentile."
            ),
        },
        "observation_universe": (
            "One observation per canonical UTC daily session in which every "
            "one of the exact 24 expected hourly liquidation intervals is "
            "present and observed, with no duplicate interval identity, restricted to "
            "the frozen provider and instrument universe of "
            f"{PROSPECTIVE_LIQUIDATION_CAPTURE_VERSION}. The universe is a "
            "predicate over feed state alone and never reads a comparison "
            "outcome."
        ),
        "output": {
            "field": "liquidation_percentile",
            "range": "0 to 100 inclusive",
            "units": "percentile points",
        },
        "percentile_convention": {
            "co_consumed_reference_owner": (
                "btc_predictor.features.volatility.volatility_percentile"
            ),
            "convention": LIQUIDATION_PERCENTILE_CONVENTION,
            "current_observation_excluded_from_history": True,
            "existing_convention_owners": list(
                LIQUIDATION_PERCENTILE_CONVENTION_OWNERS
            ),
            "formula": LIQUIDATION_PERCENTILE_CONVENTION_FORMULA,
            "invented_convention": False,
        },
        "pit_rule": (
            "available_at <= decision_time for the current observation and for "
            "every observation in the trailing window. A restatement that "
            "arrives after a decision never enters that decision's history."
        ),
        "protocol_version": PROTOCOL_VERSION,
        "schema_version": "PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_V1",
        "version": PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_VERSION,
        "window": {
            "boundary": "half-open [observation_time - window, observation_time)",
            "inherited_from": (
                "btc_predictor.features.volatility."
                "DEFAULT_VOLATILITY_PERCENTILE_WINDOW_DAYS"
            ),
            "rationale": LIQUIDATION_PERCENTILE_WINDOW_RATIONALE,
            "span_days": LIQUIDATION_PERCENTILE_WINDOW_DAYS,
        },
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def prospective_acquisition_governance() -> dict[str, Any]:
    """Summarise the acquisition semantics this ticket newly froze."""

    contracts = {
        PROSPECTIVE_CVD_ACQUISITION_VERSION: prospective_cvd_acquisition_contract(),
        PROSPECTIVE_LIQUIDATION_CAPTURE_VERSION: (
            prospective_liquidation_capture_contract()
        ),
        PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_VERSION: (
            prospective_liquidation_percentile_adapter_contract()
        ),
        PROSPECTIVE_MARKET_CAP_ACQUISITION_VERSION: (
            prospective_btc_market_cap_acquisition_contract()
        ),
    }
    if tuple(sorted(contracts)) != PROSPECTIVE_ACQUISITION_CONTRACT_VERSIONS:
        raise ProspectiveCorpusError(INPUT_GOVERNANCE_INCOMPLETE_CLASSIFICATION)
    for version, contract in contracts.items():
        provenance = contract["acquisition_governance"]
        if (
            provenance["governance_class"] != NEW_PRE_DATA_GOVERNANCE_CLASS
            or provenance["historically_inherited"] is not False
            or provenance["claimed_historically_implicit"] is not False
            or provenance["frozen_before_collection"] is not True
            or provenance["stage_b_outcomes_inspected"] is not False
            or provenance["authored_by_ticket"] != ACQUISITION_GOVERNANCE_TICKET
        ):
            raise ProspectiveCorpusError(
                f"{version} does not declare itself new pre-data governance"
            )
        if contract["version"] != version:
            raise ProspectiveCorpusError(f"{version} misdeclares its own version")
    return {
        "contract_versions": list(PROSPECTIVE_ACQUISITION_CONTRACT_VERSIONS),
        "contracts": contracts,
        "distinguishes_feature_semantics_from_acquisition_semantics": True,
        "governance_class": NEW_PRE_DATA_GOVERNANCE_CLASS,
        "phase_1_authority_claimed_for_new_rules": False,
        "phase_1_feature_semantics_owner": (
            "the frozen Phase-1 feature owners, which this program does not "
            "modify: spot_perp_cvd_spread, open_interest_intensity and "
            "calculate_orderliness_score keep their formulas, windows and "
            "reason codes exactly"
        ),
        "ticket": ACQUISITION_GOVERNANCE_TICKET,
    }

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
        "capture_state": "REQUIRES_PROSPECTIVE_COMPLETENESS_ADAPTER",
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
        "existing_aggregate_distinguishes_missing_from_empty": (
            EXISTING_AGGREGATE_DISTINGUISHES_MISSING_FROM_EMPTY
        ),
        "existing_aggregate_owner": LIQUIDATION_AGGREGATE_OWNER,
        "feed_state_owner": PROSPECTIVE_LIQUIDATION_CAPTURE_VERSION,
        "fields": list(LIQUIDATION_CAPTURE_FIELDS),
        "identity_fields": ["provider", "instrument", "timeframe"],
        "ingested_at_field": "ingested_at",
        "instrument": LIQUIDATION_INSTRUMENT,
        "interval_classifier": "classify_liquidation_feed_interval",
        "missing_policy": (
            "EXPLICIT_FEED_STATE_NO_ZERO_FILL_EMPTY_FEED_IS_DISTINCT_FROM_MISSING_FEED"
        ),
        "normalization_owner": (
            f"{PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_VERSION} -> "
            "btc_predictor.features.volatility.calculate_orderliness_score"
        ),
        "observation_time_field": "observation_time",
        "pit_rule": PIT_RULE,
        "prospective_acquisition_contract": (
            PROSPECTIVE_LIQUIDATION_CAPTURE_VERSION
        ),
        "provenance_fields": [
            "observation_time",
            "available_at",
            "ingested_at",
            "provider",
            "source",
            "feed_status",
            "event_count",
            "source_record_ids_digest",
        ],
        "provider": LIQUIDATION_PROVIDER_ID,
        "raw_table": "raw.liquidations",
        "revision_policy": "APPEND_ONLY_NEW_REVISION_ROW_PER_RESTATEMENT",
        "units": "1 USD inverse contracts; per-side notional in USD",
    },
    "btc_market_cap": {
        "available_at_field": "available_at",
        "capture_state": "REQUIRES_NEW_COLLECTOR_IN_FIRST_COLLECTION_TICKET",
        "capture_state_reason": (
            "No repository producer emits market_cap_usd today: "
            "MarketCapObservation is constructed only in a feature test and "
            "raw.generic_series declares no market-capitalisation series. "
            f"{PROSPECTIVE_MARKET_CAP_ACQUISITION_VERSION} freezes one exact "
            "series and provider identity before collection; POSTP1-004 "
            "implements the collector."
        ),
        "consuming_features": ["OI_INTENSITY", "OI_INTENSITY_PERCENTILE_180D"],
        "fields": ["value", "unit"],
        "identity_fields": ["series_id", "series_type", "provider"],
        "ingested_at_field": "ingested_at",
        "missing_policy": "EXPLICIT_STATUS_NO_ZERO_FILL_NO_CARRY_FORWARD",
        "normalization_owner": (
            "btc_predictor.features.positioning.open_interest_intensity"
        ),
        "observation_cadence": MARKET_CAP_OBSERVATION_CADENCE,
        "observation_time_alignment": MARKET_CAP_OBSERVATION_GRID,
        "observation_time_field": "observation_time",
        "poll_cycle_selector": "market_cap_poll_cycle_for_decision",
        "pit_rule": PIT_RULE,
        "prospective_acquisition_contract": (
            PROSPECTIVE_MARKET_CAP_ACQUISITION_VERSION
        ),
        "provenance_fields": [
            "observation_time",
            "available_at",
            "ingested_at",
            "revision",
            "source",
        ],
        "provider": MARKET_CAP_PROVIDER_ID,
        "provider_endpoint": MARKET_CAP_PROVIDER_ENDPOINT,
        "required_date_selector": "required_market_cap_observation_time",
        "raw_table": MARKET_CAP_RAW_TABLE,
        "revision_policy": "NEW_REVISION_ROW_PER_RESTATEMENT",
        "revision_selector": "select_market_cap_revisions_for_decision",
        "series_id": MARKET_CAP_SERIES_ID,
        "series_type": MARKET_CAP_SERIES_TYPE,
        "units": "USD",
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
            "REGIME_SCORE",
            "REGIME_SMOOTHED_SCORE",
        ],
        "declared_series_ids": sorted(
            (*_generic_series.MACRO_SERIES_IDS, *_generic_series.ONCHAIN_SERIES_IDS)
        ),
        "declared_series_types": list(_generic_series.SUPPORTED_SERIES_TYPES),
        "fields": ["value", "unit"],
        "identity_fields": ["series_id", "series_type", "provider"],
        "market_cap_supplied_here": False,
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
            "The Phase-1 owner defines the transformation but never defined a "
            "persisted source, cadence or feed-state contract, so acquisition "
            f"semantics are frozen prospectively by "
            f"{PROSPECTIVE_CVD_ACQUISITION_VERSION}. Nothing is collected or "
            "fabricated here."
        ),
        "cadence_governance": {
            "historical_feature_owner": CVD_HISTORICAL_OWNER,
            "historical_feature_owner_specifies_cadence": (
                CVD_HISTORICAL_OWNER_SPECIFIES_CADENCE
            ),
            "historical_feature_owner_specifies_window": (
                CVD_HISTORICAL_OWNER_WINDOW
            ),
            "historically_inherited": False,
            "selected_by_new_pre_data_governance": True,
            "selected_cadence": CVD_SELECTED_CADENCE,
            "unit_tests_used_as_cadence_authority": False,
        },
        "consuming_features": ["CVD_SPREAD"],
        "fields": ["cvd_usd", "market_type", "instrument", "revision"],
        "identity_fields": ["market_type", "provider", "instrument"],
        "ingested_at_field": "ingested_at",
        "missing_policy": "EXPLICIT_STATUS_NO_ZERO_FILL_MISSING_INTERVAL_STAYS_MISSING",
        "normalization_owner": "btc_predictor.features.flow",
        "observation_cadence": CVD_SELECTED_CADENCE,
        "observation_time_alignment": "exact UTC hour",
        "observation_time_field": "observation_time",
        "pit_rule": PIT_RULE,
        "pre_owner_selector": "select_contiguous_cvd_window",
        "prospective_acquisition_contract": PROSPECTIVE_CVD_ACQUISITION_VERSION,
        "provider_by_market_type": dict(CVD_PROVIDER_BY_MARKET_TYPE),
        "instrument_by_market_type": dict(CVD_INSTRUMENT_BY_MARKET_TYPE),
        "provenance_fields": ["observation_time", "available_at", "ingested_at", "source"],
        "raw_table": "research.prospective_source_input_snapshot (new capture)",
        "revision_policy": "APPEND_ONLY_NEW_REVISION_ROW_PER_RESTATEMENT",
        "units": "USD signed taker delta per closed interval",
        "zscore_window_periods": CVD_HISTORICAL_OWNER_WINDOW_OBSERVATIONS,
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
    "OI_INTENSITY": {"owner": "btc_predictor.features.positioning.open_interest_intensity", "raw": ("btc_market_cap", "derivatives_open_interest")},
    "OI_INTENSITY_PERCENTILE_180D": {"owner": "btc_predictor.features.positioning.open_interest_intensity", "raw": ("btc_market_cap", "derivatives_open_interest")},
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
            "prospective_acquisition_contract_by_family": {
                family: capture_contracts[family].get(
                    "prospective_acquisition_contract"
                )
                for family in raw_families
            },
            "unqualified_family_dependency": False,
            "zero_fill_permitted": False,
        }
    # The repeat review's P1-B finding: OI intensity may not resolve its
    # market-cap input by searching an unqualified generic-series family.
    for feature in ("OI_INTENSITY", "OI_INTENSITY_PERCENTILE_180D"):
        families = rows[feature]["raw_input_families"]
        if "generic_series" in families:
            raise ProspectiveCorpusError(
                f"{feature} may not depend on the unqualified generic-series "
                "family; it must name the frozen market-cap source contract"
            )
        if "btc_market_cap" not in families:
            raise ProspectiveCorpusError(
                f"{feature} must bind the frozen prospective market-cap source"
            )
        if rows[feature]["prospective_acquisition_contract_by_family"][
            "btc_market_cap"
        ] != PROSPECTIVE_MARKET_CAP_ACQUISITION_VERSION:
            raise ProspectiveCorpusError(
                f"{feature} does not bind "
                f"{PROSPECTIVE_MARKET_CAP_ACQUISITION_VERSION}"
            )
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
                "prospective_acquisition_contract": contract.get(
                    "prospective_acquisition_contract"
                ),
                "raw_table": contract["raw_table"],
            }
            for family, contract in sorted(capture_contracts.items())
        },
        "feature_count": len(rows),
        "feature_inventory": list(frozen),
        "feature_inventory_owner": "btc_predictor.research.feature_matrix.INITIAL_FEATURE_NAMES",
        "newly_frozen_acquisition_contracts": list(
            PROSPECTIVE_ACQUISITION_CONTRACT_VERSIONS
        ),
        "protocol_version": PROTOCOL_VERSION,
        "required_raw_input_families": sorted(used_families),
        "rows": rows,
        "schema_version": "PROSPECTIVE_FEATURE_INPUT_COVERAGE_V2",
        "unqualified_generic_series_dependency_remains": False,
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


# ---------------------------------------------------------------------------
# owner-derived warmup, rebuilt
# ---------------------------------------------------------------------------
#
# The repeat review's P2 finding: a single "750-day" number was reported as the
# exact owner-derived warmup and used as an evaluability test.  It is neither.
# VOL_PERCENTILE_2Y's owner declares a 730-day *eligible trailing window* and
# separately requires 365 *prior qualifying observations* inside it, and its
# upstream RV_20 needs 21 contiguous daily closes before the first of those
# exists.  With contiguous daily observations the feature therefore first
# defines at 386 contiguous daily sessions -- 385 elapsed calendar days -- and
# 730 populated days are never required.  730 and 365 are different quantities
# and are frozen as different fields here.
#
# Evaluability is a rule, not an elapsed-time constant: enough qualifying
# observations inside the applicable trailing window, and every upstream
# initialization satisfied.  A contiguous-history number is retained only as a
# planning estimate and is labelled as one.

WARMUP_UNIT_DAILY_SESSION = "contiguous canonical daily sessions"
WARMUP_UNIT_WEEKLY_SESSION = "contiguous canonical weekly sessions"
WARMUP_UNIT_ETF_PUBLICATION_DAY = "contiguous ETF publication days"
WARMUP_UNIT_HOURLY_COMMON = "contiguous exact-hour common spot/perp observations"
WARMUP_UNIT_DAILY_SOURCE = "contiguous daily source observations"
WARMUP_UNIT_MIXED = "mixed component units"
WARMUP_PLANNING_ESTIMATE_LABEL = "PLANNING_ESTIMATE_NOT_EVALUABILITY_AUTHORITY"

WARMUP_EVALUABILITY_RULE = (
    "A feature is evaluable at a decision when enough qualifying observations "
    "exist inside its owner's applicable trailing window AND every upstream "
    "initialization requirement is satisfied from point-in-time inputs. "
    "Elapsed time is never the test: elapsed_days >= a hardcoded longest warmup "
    "is neither necessary nor sufficient, and no such comparison may gate a "
    "slot."
)
WARMUP_ELAPSED_TIME_IS_AN_EVALUABILITY_TEST = False

# ``RV_n`` is annotated by its own owner's feature id, so the daily-return
# window is read from the owner rather than restated here.
_RV_WINDOW_DAYS = {
    _volatility.RV_7_FEATURE_ID: 7,
    _volatility.RV_20_FEATURE_ID: 20,
    _volatility.RV_60_FEATURE_ID: 60,
}
_VOL_PERCENTILE_KWDEFAULTS = _volatility.volatility_percentile.__kwdefaults__


def _warmup_row(
    owner: str,
    *,
    rolling_window_span: str,
    minimum_observation_count: str,
    upstream_initialization: str,
    calendar_or_session_rule: str,
    evaluability_predicate: str,
    contiguous_history: tuple[int, str] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "calendar_or_session_rule": calendar_or_session_rule,
        "evaluability_predicate": evaluability_predicate,
        "minimum_contiguous_history_to_first_evaluable": None,
        "minimum_observation_count": minimum_observation_count,
        "owner": owner,
        "rolling_window_span": rolling_window_span,
        "upstream_initialization": upstream_initialization,
    }
    if contiguous_history is not None:
        value, unit = contiguous_history
        row["minimum_contiguous_history_to_first_evaluable"] = {
            "label": WARMUP_PLANNING_ESTIMATE_LABEL,
            "planning_estimate_only": True,
            "unit": unit,
            "value": value,
        }
    return row


def _vol_percentile_2y_derivation() -> dict[str, Any]:
    """Derive VOL_PERCENTILE_2Y's three distinct warmup quantities exactly."""

    source_feature_id = _VOL_PERCENTILE_KWDEFAULTS["source_feature_id"]
    if source_feature_id not in _RV_WINDOW_DAYS:
        raise ProspectiveCorpusError(
            "the volatility-percentile source feature is not a known RV owner"
        )
    for feature_id, window in _RV_WINDOW_DAYS.items():
        if feature_id != f"RV_{window}":
            raise ProspectiveCorpusError(
                f"the realized-volatility owner renamed {feature_id}"
            )
    rv_return_window = _RV_WINDOW_DAYS[source_feature_id]
    rv_closes = rv_return_window + 1
    window_span_days = _VOL_PERCENTILE_KWDEFAULTS["percentile_window_days"]
    minimum_prior = _VOL_PERCENTILE_KWDEFAULTS["min_percentile_observations"]
    first_evaluable_sessions = rv_closes + minimum_prior
    if minimum_prior > window_span_days:
        raise ProspectiveCorpusError(
            "the trailing window cannot hold the required prior observations"
        )
    return {
        "current_observation_required": 1,
        "first_evaluable_contiguous_daily_sessions": first_evaluable_sessions,
        "first_evaluable_elapsed_calendar_days": first_evaluable_sessions - 1,
        "populated_days_equal_to_the_window_span_required": False,
        "rolling_window_boundary": (
            "half-open [observation_time - window, observation_time)"
        ),
        "rolling_window_span_days": window_span_days,
        "source_feature_id": source_feature_id,
        "statement": (
            f"The owner keeps a {window_span_days}-day eligible trailing window "
            f"and requires {minimum_prior} prior {source_feature_id} "
            "observations inside it, never "
            f"{window_span_days} populated days. Each of those "
            f"{source_feature_id} results needs {rv_closes} contiguous daily "
            f"closes, so with contiguous daily observations the first evaluable "
            f"decision is at session {first_evaluable_sessions} "
            f"({first_evaluable_sessions - 1} elapsed calendar days)."
        ),
        "upstream_initialization": (
            f"each {source_feature_id} result needs {rv_closes} contiguous "
            f"daily closes ({rv_return_window} daily returns)"
        ),
        "upstream_source_closes": rv_closes,
        "upstream_source_return_window_days": rv_return_window,
        "window_span_alone_implies_completeness": False,
    }


def warmup_history_contract() -> dict[str, Any]:
    """Derive every frozen feature's evaluability predicate from its owner."""

    cvd_window = CVD_HISTORICAL_OWNER_WINDOW_OBSERVATIONS
    volume_growth = _flow.spot_perp_participation.__kwdefaults__["growth_window_periods"]
    volume_zscore = _flow.spot_perp_participation.__kwdefaults__["zscore_window_periods"]
    funding_avg = _positioning.DEFAULT_FUNDING_AVERAGE_WINDOW_DAYS
    funding_window = _positioning.DEFAULT_FUNDING_ZSCORE_WINDOW_DAYS
    funding_min = _positioning.DEFAULT_FUNDING_MIN_ZSCORE_OBSERVATIONS
    basis_window = _positioning.DEFAULT_FUTURES_BASIS_ZSCORE_WINDOW_DAYS
    basis_min = _positioning.DEFAULT_FUTURES_BASIS_MIN_ZSCORE_OBSERVATIONS
    oi_growth = _positioning.DEFAULT_OI_GROWTH_WINDOW_DAYS
    oi_window = _positioning.DEFAULT_OI_GROWTH_ZSCORE_WINDOW_DAYS
    oi_min = _positioning.DEFAULT_OI_GROWTH_MIN_ZSCORE_OBSERVATIONS
    oi_intensity_window = _positioning.DEFAULT_OI_INTENSITY_PERCENTILE_WINDOW_DAYS
    oi_intensity_min = _positioning.DEFAULT_OI_INTENSITY_MIN_PERCENTILE_OBSERVATIONS
    etf_5 = _flow.FIVE_DAY_ETF_FLOW_WINDOW_DAYS
    etf_20 = _flow.TWENTY_DAY_ETF_FLOW_WINDOW_DAYS
    momentum_4 = _momentum.FOUR_WEEK_MOMENTUM_LOOKBACK_DAYS
    momentum_12 = _momentum.TWELVE_WEEK_MOMENTUM_LOOKBACK_DAYS
    ma_weeks = _trend.TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS
    high_weeks = _trend.FIFTY_TWO_WEEK_HIGH_DISTANCE_LOOKBACK_WEEKS
    rv_7 = _RV_WINDOW_DAYS[_volatility.RV_7_FEATURE_ID]
    rv_20 = _RV_WINDOW_DAYS[_volatility.RV_20_FEATURE_ID]
    rv_60 = _RV_WINDOW_DAYS[_volatility.RV_60_FEATURE_ID]

    vol_percentile = _vol_percentile_2y_derivation()
    vol_percentile_sessions = vol_percentile["first_evaluable_contiguous_daily_sessions"]
    liquidation_sessions = LIQUIDATION_PERCENTILE_MIN_OBSERVATIONS + 1
    orderliness_sessions = max(vol_percentile_sessions, liquidation_sessions)
    funding_sessions = funding_min + 1
    basis_sessions = basis_min + 1
    oi_growth_sessions = oi_growth + oi_min + 1
    oi_intensity_sessions = oi_intensity_min + 1
    positioning_sessions = max(funding_sessions, basis_sessions, oi_growth_sessions)

    rows: dict[str, Any] = {
        "TREND_SCORE": _warmup_row(
            "btc_predictor.features.trend.calculate_trend_score",
            rolling_window_span=(
                f"max({high_weeks} weekly, {ma_weeks} weekly, {momentum_12} daily)"
            ),
            minimum_observation_count=(
                "every selected trend component complete at this decision"
            ),
            upstream_initialization=(
                "the weekly structure and every component owner must be complete"
            ),
            calendar_or_session_rule="canonical weekly and daily sessions",
            evaluability_predicate=(
                f"MA_DISTANCE_20W, HIGH_DISTANCE_52W and the selected momentum "
                "components are each independently complete under their own "
                "owners"
            ),
            contiguous_history=(high_weeks, WARMUP_UNIT_WEEKLY_SESSION),
        ),
        "FLOW_SCORE": _warmup_row(
            "btc_predictor.features.flow.calculate_flow_score",
            rolling_window_span=(
                f"max({etf_20} ETF publication days, {cvd_window + 1} "
                f"{CVD_SELECTED_CADENCE} CVD observations, "
                f"{volume_growth * 2 + volume_zscore} hourly participation "
                "observations)"
            ),
            minimum_observation_count=(
                "every selected full-flow component complete at this decision"
            ),
            upstream_initialization=(
                "the participation growth series needs two equal windows before "
                "its own z-score history exists"
            ),
            calendar_or_session_rule=(
                "ETF publication days and exact UTC hours; the units are not "
                "commensurable and are not collapsed into one number"
            ),
            evaluability_predicate=(
                "ETF_NORM_5D, ETF_NORM_20D, FLOW_ACCEL, CVD_SPREAD and "
                "SPOT_DOMINANCE are each independently complete under their own "
                "owners"
            ),
            contiguous_history=None,
        ),
        "POSITIONING_SCORE": _warmup_row(
            "btc_predictor.features.positioning.calculate_positioning_score",
            rolling_window_span=(
                f"max({funding_window}d funding, {basis_window}d basis, "
                f"{oi_window}d OI growth)"
            ),
            minimum_observation_count=(
                f"{funding_min} prior funding, {basis_min} prior basis and "
                f"{oi_min} prior OI-growth observations in their own windows"
            ),
            upstream_initialization=(
                f"the earliest OI-growth observation needs an OI observation "
                f"{oi_growth}d earlier"
            ),
            calendar_or_session_rule="trailing elapsed UTC day windows",
            evaluability_predicate=(
                "FUNDING_HEALTH, OI_GROWTH_HEALTH and FUTURES_BASIS_HEALTH are "
                "each complete, and the configured leverage-health input is "
                "present"
            ),
            contiguous_history=(positioning_sessions, WARMUP_UNIT_DAILY_SOURCE),
        ),
        "VOLATILITY_SCORE": _warmup_row(
            "btc_predictor.features.volatility.calculate_volatility_score",
            rolling_window_span=(
                f"{vol_percentile['rolling_window_span_days']}d eligible "
                "trailing RV window inherited from VOL_PERCENTILE_2Y"
            ),
            minimum_observation_count=(
                f"{vol_percentile['rolling_window_span_days']}d window holding "
                f"{_VOL_PERCENTILE_KWDEFAULTS['min_percentile_observations']} "
                "prior RV_20 observations"
            ),
            upstream_initialization=vol_percentile["upstream_initialization"],
            calendar_or_session_rule="canonical daily sessions",
            evaluability_predicate=(
                "every selected volatility component, VOL_PERCENTILE_2Y "
                "included, is complete under its own owner"
            ),
            contiguous_history=(vol_percentile_sessions, WARMUP_UNIT_DAILY_SESSION),
        ),
        "STRUCTURE_SCORE": _warmup_row(
            "btc_predictor.features.structure.calculate_structure_score",
            rolling_window_span="none at this owner",
            minimum_observation_count="one complete current input vector",
            upstream_initialization=(
                "the structural level and risk/reward owners must be complete"
            ),
            calendar_or_session_rule="owner-supplied point-in-time structures",
            evaluability_predicate=(
                "the current structure, level and risk/reward inputs are all "
                "present at this decision"
            ),
            contiguous_history=None,
        ),
        "REGIME_SCORE": _warmup_row(
            "btc_predictor.features.regime.calculate_regime_score",
            rolling_window_span=(
                "transitive maximum of the trend, flow, positioning and "
                "volatility component windows"
            ),
            minimum_observation_count=(
                "every required regime component complete at this decision"
            ),
            upstream_initialization=(
                "the full model additionally requires the point-in-time macro, "
                "on-chain and liquidity inputs"
            ),
            calendar_or_session_rule="mixed canonical sessions",
            evaluability_predicate=(
                "every required component score is independently complete; the "
                "composite inherits their predicates and invents no window"
            ),
            contiguous_history=(vol_percentile_sessions, WARMUP_UNIT_DAILY_SESSION),
        ),
        "REGIME_SMOOTHED_SCORE": _warmup_row(
            "btc_predictor.features.regime.calculate_regime_smoothing",
            rolling_window_span="current regime score and optional prior smoothed score",
            minimum_observation_count="1 complete current regime score",
            upstream_initialization=(
                "the owner deterministically initializes a missing previous "
                "smoothed score from the current score and records "
                "REGIME_SMOOTHING_PREVIOUS_SCORE_MISSING"
            ),
            calendar_or_session_rule="strategy-daily decisions",
            evaluability_predicate=(
                "REGIME_SCORE is complete at this decision"
            ),
            contiguous_history=(vol_percentile_sessions, WARMUP_UNIT_DAILY_SESSION),
        ),
        "ORDERLINESS_SCORE": _warmup_row(
            "btc_predictor.features.volatility.calculate_orderliness_score",
            rolling_window_span=(
                "none at this owner; the range, liquidation and volatility "
                "percentile inputs carry their own windows"
            ),
            minimum_observation_count="one complete current input vector",
            upstream_initialization=(
                "the volatility-percentile owner and "
                f"{PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_VERSION} must "
                "each be complete; an unavailable, late or invalid liquidation "
                "feed leaves the liquidation input missing and never zero"
            ),
            calendar_or_session_rule="strategy-daily point-in-time inputs",
            evaluability_predicate=(
                "range_percentile, downside_return, liquidation_percentile and "
                "volatility_percentile are all present at this decision"
            ),
            contiguous_history=(orderliness_sessions, WARMUP_UNIT_DAILY_SESSION),
        ),
        "MOMENTUM_4W": _warmup_row(
            "btc_predictor.features.momentum.four_week_momentum_from_daily_bars",
            rolling_window_span=f"{momentum_4} daily periods",
            minimum_observation_count=f"{momentum_4 + 1} closes",
            upstream_initialization="the current close plus the lookback close",
            calendar_or_session_rule="canonical daily sessions",
            evaluability_predicate=(
                f"a close exists at this session and at the session "
                f"{momentum_4} periods earlier"
            ),
            contiguous_history=(momentum_4 + 1, WARMUP_UNIT_DAILY_SESSION),
        ),
        "MOMENTUM_12W": _warmup_row(
            "btc_predictor.features.momentum.twelve_week_momentum_from_daily_bars",
            rolling_window_span=f"{momentum_12} daily periods",
            minimum_observation_count=f"{momentum_12 + 1} closes",
            upstream_initialization="the current close plus the lookback close",
            calendar_or_session_rule="canonical daily sessions",
            evaluability_predicate=(
                f"a close exists at this session and at the session "
                f"{momentum_12} periods earlier"
            ),
            contiguous_history=(momentum_12 + 1, WARMUP_UNIT_DAILY_SESSION),
        ),
        "MA_DISTANCE_20W": _warmup_row(
            "btc_predictor.features.trend.twenty_week_ma_distance",
            rolling_window_span=f"{ma_weeks} weekly periods",
            minimum_observation_count=f"{ma_weeks} weekly closes",
            upstream_initialization="none",
            calendar_or_session_rule="canonical weekly sessions",
            evaluability_predicate=(
                f"{ma_weeks} weekly closes exist in the trailing weekly window"
            ),
            contiguous_history=(ma_weeks, WARMUP_UNIT_WEEKLY_SESSION),
        ),
        "HIGH_DISTANCE_52W": _warmup_row(
            "btc_predictor.features.trend.fifty_two_week_high_distance",
            rolling_window_span=f"{high_weeks} weekly periods",
            minimum_observation_count=f"{high_weeks} weekly highs and closes",
            upstream_initialization="none",
            calendar_or_session_rule="canonical weekly sessions",
            evaluability_predicate=(
                f"{high_weeks} weekly observations exist in the trailing weekly "
                "window"
            ),
            contiguous_history=(high_weeks, WARMUP_UNIT_WEEKLY_SESSION),
        ),
        "ETF_NORM_5D": _warmup_row(
            "btc_predictor.features.flow.five_day_etf_flow",
            rolling_window_span=f"{etf_5} publication days",
            minimum_observation_count=(
                f"{etf_5} complete fund-universe publication days"
            ),
            upstream_initialization="the latest point-in-time AUM is required",
            calendar_or_session_rule="configured ETF publication calendar",
            evaluability_predicate=(
                f"{etf_5} complete publication days and a current AUM exist"
            ),
            contiguous_history=(etf_5, WARMUP_UNIT_ETF_PUBLICATION_DAY),
        ),
        "ETF_NORM_20D": _warmup_row(
            "btc_predictor.features.flow.twenty_day_etf_flow",
            rolling_window_span=f"{etf_20} publication days",
            minimum_observation_count=(
                f"{etf_20} complete fund-universe publication days"
            ),
            upstream_initialization="the latest point-in-time AUM is required",
            calendar_or_session_rule="configured ETF publication calendar",
            evaluability_predicate=(
                f"{etf_20} complete publication days and a current AUM exist"
            ),
            contiguous_history=(etf_20, WARMUP_UNIT_ETF_PUBLICATION_DAY),
        ),
        "FLOW_ACCEL": _warmup_row(
            "btc_predictor.features.flow.etf_flow_acceleration",
            rolling_window_span=f"the {etf_5}d and {etf_20}d normalized windows",
            minimum_observation_count="both source windows complete",
            upstream_initialization="none beyond the two source windows",
            calendar_or_session_rule="configured ETF publication calendar",
            evaluability_predicate="ETF_NORM_5D and ETF_NORM_20D are both complete",
            contiguous_history=(etf_20, WARMUP_UNIT_ETF_PUBLICATION_DAY),
        ),
        "CVD_SPREAD": _warmup_row(
            CVD_HISTORICAL_OWNER,
            rolling_window_span=(
                f"{cvd_window} prior common observations; the owner specifies a "
                "window in observations and specifies no cadence"
            ),
            minimum_observation_count=(
                f"{cvd_window} prior plus 1 current common spot/perp observation"
            ),
            upstream_initialization=(
                "the z-score excludes the current observation from its own "
                "history, and both the spot and perp series must carry the same "
                "common timestamps"
            ),
            calendar_or_session_rule=(
                f"{PROSPECTIVE_CVD_ACQUISITION_VERSION} supplies the "
                f"{CVD_SELECTED_CADENCE} acquisition grid; the feature owner "
                "supplies the observation count"
            ),
            evaluability_predicate=(
                f"{cvd_window} prior common observations plus the current one "
                "exist with available_at <= decision_time, and neither side's "
                "history is degenerate"
            ),
            contiguous_history=(cvd_window + 1, WARMUP_UNIT_HOURLY_COMMON),
        ),
        "SPOT_DOMINANCE": _warmup_row(
            "btc_predictor.features.flow.spot_perp_participation_from_rows",
            rolling_window_span=(
                f"{volume_growth}-period current and prior growth windows plus "
                f"{volume_zscore} prior growth values"
            ),
            minimum_observation_count=(
                f"{volume_growth * 2 + volume_zscore} common observations"
            ),
            upstream_initialization=(
                "the growth series initializes only after two equal windows"
            ),
            calendar_or_session_rule="exact UTC hourly common spot/perp timestamps",
            evaluability_predicate=(
                f"{volume_growth * 2 + volume_zscore} common observations exist "
                "and both growth z-scores are defined"
            ),
            contiguous_history=(
                volume_growth * 2 + volume_zscore,
                WARMUP_UNIT_HOURLY_COMMON,
            ),
        ),
        "FUNDING_7D_AVG": _warmup_row(
            "btc_predictor.features.positioning.funding_health",
            rolling_window_span=f"{funding_avg}d, half-open (t - {funding_avg}d, t]",
            minimum_observation_count="at least 1 available observation",
            upstream_initialization="none",
            calendar_or_session_rule="trailing elapsed UTC days",
            evaluability_predicate=(
                f"at least one funding observation falls in (t - {funding_avg}d, t]"
            ),
            contiguous_history=None,
        ),
        "FUNDING_ZSCORE_180D": _warmup_row(
            "btc_predictor.features.positioning.funding_health",
            rolling_window_span=(
                f"{funding_window}d, half-open [t - {funding_window}d, t)"
            ),
            minimum_observation_count=f"{funding_min} prior observations",
            upstream_initialization=(
                "the current observation is excluded from its own history"
            ),
            calendar_or_session_rule="trailing elapsed UTC days",
            evaluability_predicate=(
                f"{funding_min} prior funding observations fall in "
                f"[t - {funding_window}d, t) and their variance is non-zero"
            ),
            contiguous_history=(funding_sessions, WARMUP_UNIT_DAILY_SOURCE),
        ),
        "FUNDING_HEALTH": _warmup_row(
            "btc_predictor.features.positioning.funding_health",
            rolling_window_span="inherits FUNDING_ZSCORE_180D",
            minimum_observation_count="one complete funding z-score",
            upstream_initialization="none",
            calendar_or_session_rule="inherits the funding z-score",
            evaluability_predicate="FUNDING_ZSCORE_180D is complete",
            contiguous_history=(funding_sessions, WARMUP_UNIT_DAILY_SOURCE),
        ),
        "OI_GROWTH_7D": _warmup_row(
            "btc_predictor.features.positioning.open_interest_growth_health",
            rolling_window_span=f"{oi_growth}d comparison",
            minimum_observation_count="a current and a prior comparable observation",
            upstream_initialization=(
                f"a prior OI observation at or before t - {oi_growth}d is required"
            ),
            calendar_or_session_rule="elapsed UTC day comparison",
            evaluability_predicate=(
                f"a current OI aggregate exists and an aggregate exists at or "
                f"before t - {oi_growth}d"
            ),
            contiguous_history=(oi_growth + 1, WARMUP_UNIT_DAILY_SOURCE),
        ),
        "OI_GROWTH_ZSCORE_180D": _warmup_row(
            "btc_predictor.features.positioning.open_interest_growth_health",
            rolling_window_span=f"{oi_window}d of growth results",
            minimum_observation_count=f"{oi_min} prior growth observations",
            upstream_initialization=(
                f"the earliest retained growth observation itself needs an OI "
                f"observation {oi_growth}d earlier"
            ),
            calendar_or_session_rule="trailing elapsed UTC days",
            evaluability_predicate=(
                f"{oi_min} prior growth observations fall in "
                f"[t - {oi_window}d, t) and their variance is non-zero"
            ),
            contiguous_history=(oi_growth_sessions, WARMUP_UNIT_DAILY_SOURCE),
        ),
        "OI_GROWTH_HEALTH": _warmup_row(
            "btc_predictor.features.positioning.open_interest_growth_health",
            rolling_window_span="inherits OI_GROWTH_ZSCORE_180D",
            minimum_observation_count="one complete OI-growth z-score",
            upstream_initialization="none",
            calendar_or_session_rule="inherits the OI-growth z-score",
            evaluability_predicate="OI_GROWTH_ZSCORE_180D is complete",
            contiguous_history=(oi_growth_sessions, WARMUP_UNIT_DAILY_SOURCE),
        ),
        "OI_INTENSITY": _warmup_row(
            "btc_predictor.features.positioning.open_interest_intensity",
            rolling_window_span="none at this owner",
            minimum_observation_count=(
                "one open-interest aggregate and one market-cap observation at "
                "the same exact observation_time"
            ),
            upstream_initialization=(
                f"the market-cap input is supplied by "
                f"{PROSPECTIVE_MARKET_CAP_ACQUISITION_VERSION} on the "
                f"{MARKET_CAP_OBSERVATION_GRID} grid; a missing or late "
                "market-cap observation leaves the feature not evaluable"
            ),
            calendar_or_session_rule="the same point-in-time decision",
            evaluability_predicate=(
                "the open-interest aggregate and the market-cap observation "
                "share an exact observation_time and both are available at the "
                "decision"
            ),
            contiguous_history=None,
        ),
        "OI_INTENSITY_PERCENTILE_180D": _warmup_row(
            "btc_predictor.features.positioning.open_interest_intensity",
            rolling_window_span=(
                f"{oi_intensity_window}d, half-open "
                f"[t - {oi_intensity_window}d, t)"
            ),
            minimum_observation_count=(
                f"{oi_intensity_min} prior intensity observations"
            ),
            upstream_initialization=(
                "every historical intensity observation needs its own aligned "
                "open-interest and market-cap pair"
            ),
            calendar_or_session_rule="trailing elapsed UTC days",
            evaluability_predicate=(
                f"a current intensity exists and {oi_intensity_min} prior "
                f"intensity observations fall in [t - {oi_intensity_window}d, t)"
            ),
            contiguous_history=(oi_intensity_sessions, WARMUP_UNIT_DAILY_SOURCE),
        ),
        "FUTURES_BASIS_AVG": _warmup_row(
            "btc_predictor.features.positioning.futures_basis_health",
            rolling_window_span="none at this owner",
            minimum_observation_count="at least 1 available basis observation",
            upstream_initialization="none",
            calendar_or_session_rule="the same point-in-time decision",
            evaluability_predicate=(
                "at least one basis observation is available at the decision"
            ),
            contiguous_history=None,
        ),
        "FUTURES_BASIS_ZSCORE_180D": _warmup_row(
            "btc_predictor.features.positioning.futures_basis_health",
            rolling_window_span=f"{basis_window}d, half-open [t - {basis_window}d, t)",
            minimum_observation_count=f"{basis_min} prior observations",
            upstream_initialization=(
                "the current observation is excluded from its own history"
            ),
            calendar_or_session_rule="trailing elapsed UTC days",
            evaluability_predicate=(
                f"{basis_min} prior basis observations fall in "
                f"[t - {basis_window}d, t) and their variance is non-zero"
            ),
            contiguous_history=(basis_sessions, WARMUP_UNIT_DAILY_SOURCE),
        ),
        "FUTURES_BASIS_HEALTH": _warmup_row(
            "btc_predictor.features.positioning.futures_basis_health",
            rolling_window_span="inherits FUTURES_BASIS_ZSCORE_180D",
            minimum_observation_count="one complete basis z-score",
            upstream_initialization="none",
            calendar_or_session_rule="inherits the basis z-score",
            evaluability_predicate="FUTURES_BASIS_ZSCORE_180D is complete",
            contiguous_history=(basis_sessions, WARMUP_UNIT_DAILY_SOURCE),
        ),
        "RV_7": _warmup_row(
            "btc_predictor.features.volatility.realized_volatility_from_daily_bars",
            rolling_window_span=f"{rv_7} daily returns",
            minimum_observation_count=f"{rv_7 + 1} contiguous daily closes",
            upstream_initialization="the first return needs the previous close",
            calendar_or_session_rule="gap-aware canonical daily sessions",
            evaluability_predicate=(
                f"{rv_7 + 1} contiguous daily closes are available and all are "
                "strictly positive"
            ),
            contiguous_history=(rv_7 + 1, WARMUP_UNIT_DAILY_SESSION),
        ),
        "RV_20": _warmup_row(
            "btc_predictor.features.volatility.realized_volatility_from_daily_bars",
            rolling_window_span=f"{rv_20} daily returns",
            minimum_observation_count=f"{rv_20 + 1} contiguous daily closes",
            upstream_initialization="the first return needs the previous close",
            calendar_or_session_rule="gap-aware canonical daily sessions",
            evaluability_predicate=(
                f"{rv_20 + 1} contiguous daily closes are available and all are "
                "strictly positive"
            ),
            contiguous_history=(rv_20 + 1, WARMUP_UNIT_DAILY_SESSION),
        ),
        "RV_60": _warmup_row(
            "btc_predictor.features.volatility.realized_volatility_from_daily_bars",
            rolling_window_span=f"{rv_60} daily returns",
            minimum_observation_count=f"{rv_60 + 1} contiguous daily closes",
            upstream_initialization="the first return needs the previous close",
            calendar_or_session_rule="gap-aware canonical daily sessions",
            evaluability_predicate=(
                f"{rv_60 + 1} contiguous daily closes are available and all are "
                "strictly positive"
            ),
            contiguous_history=(rv_60 + 1, WARMUP_UNIT_DAILY_SESSION),
        ),
        "VOL_COMPRESSION_RATIO": _warmup_row(
            "btc_predictor.features.volatility.volatility_compression_ratio",
            rolling_window_span=f"the RV_{rv_7} and RV_{rv_20} windows",
            minimum_observation_count="both realized-volatility inputs complete",
            upstream_initialization=f"none beyond RV_{rv_20}",
            calendar_or_session_rule="inherits the canonical daily sessions",
            evaluability_predicate=(
                f"RV_{rv_7} and RV_{rv_20} are both complete and RV_{rv_20} is "
                "non-zero"
            ),
            contiguous_history=(rv_20 + 1, WARMUP_UNIT_DAILY_SESSION),
        ),
        "VOL_PERCENTILE_2Y": _warmup_row(
            "btc_predictor.features.volatility.volatility_percentile",
            rolling_window_span=(
                f"{vol_percentile['rolling_window_span_days']}d eligible "
                f"trailing window, {vol_percentile['rolling_window_boundary']}"
            ),
            minimum_observation_count=(
                f"{_VOL_PERCENTILE_KWDEFAULTS['min_percentile_observations']} "
                f"prior {vol_percentile['source_feature_id']} observations "
                "inside that window, plus 1 current observation"
            ),
            upstream_initialization=vol_percentile["upstream_initialization"],
            calendar_or_session_rule="canonical daily sessions",
            evaluability_predicate=(
                f"a current {vol_percentile['source_feature_id']} result exists "
                "and at least "
                f"{_VOL_PERCENTILE_KWDEFAULTS['min_percentile_observations']} "
                "prior results fall inside "
                f"{vol_percentile['rolling_window_boundary']}. The window span "
                "alone never implies completeness and "
                f"{vol_percentile['rolling_window_span_days']} populated days "
                "are never required."
            ),
            contiguous_history=(vol_percentile_sessions, WARMUP_UNIT_DAILY_SESSION),
        ),
    }
    if set(rows) != set(INITIAL_FEATURE_NAMES):
        raise ProspectiveCorpusError("warmup rows must exactly cover INITIAL_FEATURE_NAMES")

    longest_by_unit: dict[str, int] = {}
    for row in rows.values():
        estimate = row["minimum_contiguous_history_to_first_evaluable"]
        if estimate is None:
            continue
        unit = estimate["unit"]
        longest_by_unit[unit] = max(longest_by_unit.get(unit, 0), estimate["value"])

    payload = {
        "all_feature_warmups_frozen": True,
        "composite_inheritance_rule": (
            "A composite score is complete only when every required component "
            "is complete under its own owner's predicate. A composite invents "
            "no window of its own and never substitutes an elapsed-time proxy "
            "for a component's predicate."
        ),
        "elapsed_time_is_an_evaluability_test": (
            WARMUP_ELAPSED_TIME_IS_AN_EVALUABILITY_TEST
        ),
        "evaluability_rule": WARMUP_EVALUABILITY_RULE,
        "feature_inventory_owner": (
            "btc_predictor.research.feature_matrix.INITIAL_FEATURE_NAMES"
        ),
        "longest_contiguous_history_planning_estimate_by_unit": dict(
            sorted(longest_by_unit.items())
        ),
        "planning_estimate_label": WARMUP_PLANNING_ESTIMATE_LABEL,
        "planning_estimate_units_are_not_commensurable": True,
        "pre_warmup_behavior": (
            "Raw point-in-time capture may build history only after both the "
            "corpus protocol and sufficiency-governance hashes plus POSTP1-004 "
            "have passed their required reviews. Until WARMUP_HISTORY_COMPLETE "
            "a slot is WARMUP_HISTORY_INCOMPLETE and enters no evaluable metric "
            "universe."
        ),
        "protocol_version": PROTOCOL_VERSION,
        "rows": rows,
        "schema_version": "PROSPECTIVE_WARMUP_HISTORY_V2",
        "state_name": "WARMUP_HISTORY_COMPLETE",
        "superseded_claim": {
            "claim": "750 calendar days is the exact owner-derived warmup",
            "correction": vol_percentile["statement"],
            "retained_as_scientific_minimum": False,
            "why_it_was_wrong": (
                "It added the 730-day eligible trailing window to a 20-day "
                "upstream window as if both were required populated histories, "
                "and then used the sum as an elapsed-time evaluability test. "
                "The owner requires "
                f"{_VOL_PERCENTILE_KWDEFAULTS['min_percentile_observations']} "
                "prior observations inside the window, not "
                f"{vol_percentile['rolling_window_span_days']} populated days."
            ),
        },
        "three_distinct_quantities": {
            "minimum_contiguous_history_to_first_evaluable": (
                "A planning estimate under contiguous observations only. It is "
                "not the evaluability authority and no slot is admitted or "
                "refused by comparing elapsed time against it."
            ),
            "minimum_observation_count": (
                "The qualifying observations an owner requires inside its "
                "applicable trailing window. This, with the upstream "
                "initialization, is the evaluability authority."
            ),
            "rolling_window_span": (
                "The eligible trailing window an owner searches. It states "
                "which observations may count, never how many must exist."
            ),
        },
        "vol_percentile_2y_derivation": vol_percentile,
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

    # CVD cadence is no longer claimed to be uniquely implied by the Phase-1
    # feature owner -- it demonstrably is not.  What must hold instead is that
    # the acquisition semantics are frozen here, honestly labelled as new
    # pre-data governance, and never attributed to inherited authority.
    cvd = NON_PRICE_INPUT_SOURCES["spot_perp_cvd"]["cadence_governance"]
    if (
        cvd["historical_feature_owner_specifies_cadence"] is not False
        or cvd["historically_inherited"] is not False
        or cvd["selected_by_new_pre_data_governance"] is not True
        or cvd["unit_tests_used_as_cadence_authority"] is not False
        or cvd["selected_cadence"] != CVD_SELECTED_CADENCE
    ):
        raise ProspectiveCorpusError(INPUT_GOVERNANCE_INCOMPLETE_CLASSIFICATION)
    cvd_source = NON_PRICE_INPUT_SOURCES["spot_perp_cvd"]
    if (
        cvd_source["provider_by_market_type"] != CVD_PROVIDER_BY_MARKET_TYPE
        or cvd_source["instrument_by_market_type"]
        != CVD_INSTRUMENT_BY_MARKET_TYPE
        or cvd_source["pre_owner_selector"]
        != "select_contiguous_cvd_window"
    ):
        raise ProspectiveCorpusError(INPUT_GOVERNANCE_INCOMPLETE_CLASSIFICATION)
    market_cap = NON_PRICE_INPUT_SOURCES["btc_market_cap"]
    if (
        market_cap["series_id"] != MARKET_CAP_SERIES_ID
        or market_cap["series_type"] != MARKET_CAP_SERIES_TYPE
        or market_cap["provider"] != MARKET_CAP_PROVIDER_ID
        or market_cap["provider_endpoint"] != MARKET_CAP_PROVIDER_ENDPOINT
        or market_cap["revision_selector"]
        != "select_market_cap_revisions_for_decision"
        or market_cap["required_date_selector"]
        != "required_market_cap_observation_time"
    ):
        raise ProspectiveCorpusError(MISSING_MARKET_CAP_SOURCE_CLASSIFICATION)
    liquidations = NON_PRICE_INPUT_SOURCES["liquidations"]
    if (
        liquidations["existing_aggregate_distinguishes_missing_from_empty"]
        is not False
        or liquidations["provider"] != LIQUIDATION_PROVIDER_ID
        or liquidations["instrument"] != LIQUIDATION_INSTRUMENT
        or liquidations["interval_classifier"]
        != "classify_liquidation_feed_interval"
    ):
        raise ProspectiveCorpusError(INPUT_GOVERNANCE_INCOMPLETE_CLASSIFICATION)
    if not LIQUIDATION_PERCENTILE_ADAPTER_REQUIRED:
        raise ProspectiveCorpusError(
            AMBIGUOUS_LIQUIDATION_NORMALIZATION_CLASSIFICATION
        )
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
    "change a frozen acquisition cadence, provider, market universe, series "
    "identity, feed-status vocabulary or normalization adapter",
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
    "prospective_scientific_evidence_record",
    "prospective_coingecko_request_attempt",
    "prospective_validated_market_cap_response",
    "prospective_clock_integrity",
    "prospective_clock_interval_evidence",
    "prospective_stream_epoch",
    "prospective_stream_liveness",
    "prospective_stream_collector_health",
    "prospective_source_event",
    "prospective_kraken_futures_metadata_validation",
    "prospective_stream_interval_completeness",
    "prospective_cvd_interval_completeness",
    "prospective_liquidation_interval_completeness",
    "prospective_liquidation_day_census",
    "prospective_decision_observation",
    "prospective_source_input_snapshot",
    "prospective_liquidation_feed_state",
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
    "prospective_scientific_evidence_record": {
        "append_only": True,
        "columns": {
            "canonical_payload_bytes": "bytea not null",
            "record_kind": "text not null",
            "record_sha256": "char(64) not null",
            "run_id": "uuid not null",
            "schema_version": "text not null",
        },
        "layer": "RAW",
        "primary_key": ["run_id", "record_sha256"],
        "purpose": (
            "Content-addressed canonical payload for every material scientific "
            "record. SHA-256 is recomputed over canonical_payload_bytes; the "
            "schema-versioned decoder reconstructs the typed record, including "
            "tagged exact bytes and Decimal/timestamp values. Typed tables are "
            "query projections and cannot replace this resolver authority."
        ),
    },
    "prospective_coingecko_request_attempt": {
        "append_only": True,
        "columns": {
            "acquisition_contract_sha256": "char(64) not null",
            "asset_id": "text not null",
            "endpoint_identity": "text not null",
            "endpoint_version": "text not null",
            "http_method": "text not null",
            "attempt_id": "text not null",
            "http_status": "integer null",
            "collector_version": "text not null",
            "clock_interval_evidence_sha256": "char(64) not null",
            "parameter_canonicalization": "text not null",
            "provider": "text not null",
            "query_parameters": "jsonb not null",
            "maximum_success_elapsed_seconds": "numeric not null check (= 45)",
            "monotonic_elapsed_seconds": "numeric not null",
            "outcome": "text not null",
            "raw_response_bytes": "bytea null",
            "reason_code": "text null",
            "request_sha256": "char(64) not null",
            "request_record_sha256": "char(64) not null",
            "actual_request_started_at": "timestamptz not null",
            "request_start_clock_sha256": "char(64) not null",
            "requested_date": "date not null",
            "requested_currency": "text not null",
            "requested_field": "text not null",
            "response_sha256": "char(64) null",
            "run_id": "uuid not null",
            "scheduled_poll_time": "timestamptz not null",
            "schema_version": "text not null",
            "scientific_clock_usable": "boolean not null",
            "serialized_query": "text not null",
            "source_contract_version": "text not null",
            "terminated_at": "timestamptz not null",
            "termination_clock_sha256": "char(64) not null",
        },
        "layer": "RAW",
        "primary_key": ["run_id", "attempt_id"],
        "purpose": (
            "One immutable CoinGecko scheduled attempt for every outcome. "
            "Timeout/transport rows need no fake status, response or value; "
            "successful response bytes are exact BYTEA and digest-bound."
        ),
    },
    "prospective_validated_market_cap_response": {
        "append_only": True,
        "columns": {
            "available_at": "timestamptz not null",
            "market_cap_usd": "numeric not null",
            "observation_time": "timestamptz not null",
            "provider": "text not null",
            "request_sha256": "char(64) not null",
            "request_record_sha256": "char(64) not null",
            "requested_date": "date not null",
            "response_sha256": "char(64) not null",
            "run_id": "uuid not null",
            "schema_version": "text not null",
            "source": "text not null",
            "validation_contract": "text not null",
            "validation_contract_sha256": "char(64) not null",
            "validated_response_sha256": "char(64) not null",
        },
        "layer": "RAW",
        "primary_key": ["run_id", "validated_response_sha256"],
        "purpose": (
            "A validated bitcoin/USD response bound to exactly one request. "
            "observation_time is derived from requested_date and is not caller supplied."
        ),
    },
    "prospective_clock_integrity": {
        "append_only": True,
        "columns": {
            "clock_health_sha256": "char(64) not null",
            "collector_host_id": "text not null",
            "collector_process_id": "text not null",
            "boot_id": "text not null",
            "estimated_utc_offset_seconds": "numeric not null",
            "health_query_succeeded": "boolean not null",
            "maximum_permitted_absolute_error_seconds": "numeric not null",
            "monotonic_domain_id": "char(64) not null",
            "monotonic_observed_seconds": "numeric not null",
            "observed_at": "timestamptz not null",
            "offset_uncertainty_seconds": "numeric null",
            "process_start_identity": "text not null",
            "reason_codes": "jsonb not null",
            "run_id": "uuid not null",
            "schema_version": "text not null",
            "synchronization_mechanism": "text not null",
            "synchronization_source": "text not null",
            "synchronized": "boolean not null",
            "usable": "boolean not null",
        },
        "layer": "RAW",
        "primary_key": ["run_id", "clock_health_sha256"],
        "purpose": "OS/NTP/chrony evidence governing every scientific local timestamp.",
    },
    "prospective_clock_interval_evidence": {
        "append_only": True,
        "columns": {
            "clock_health_record_sha256s": "jsonb not null",
            "clock_interval_evidence_sha256": "char(64) not null",
            "end_clock_sha256": "char(64) not null",
            "maximum_clock_health_gap_seconds": "numeric not null",
            "maximum_permitted_wall_step_seconds": "numeric not null",
            "monotonic_domain_id": "char(64) not null",
            "monotonic_elapsed_seconds": "numeric not null",
            "reason_codes": "jsonb not null",
            "run_id": "uuid not null",
            "schema_version": "text not null",
            "start_clock_sha256": "char(64) not null",
            "usable": "boolean not null",
            "wall_clock_elapsed_seconds": "numeric not null",
            "wall_monotonic_divergence_seconds": "numeric not null",
        },
        "layer": "RAW",
        "primary_key": ["run_id", "clock_interval_evidence_sha256"],
        "purpose": (
            "Full same-domain wall/monotonic interval plus every renewed clock "
            "health reference needed to replay freshness and divergence."
        ),
    },
    "prospective_stream_epoch": {
        "append_only": True,
        "columns": {
            "channel": "text not null",
            "collector_sha256": "char(64) not null",
            "collector_version": "text not null",
            "connection_established_at": "timestamptz not null",
            "connection_clock_sha256": "char(64) not null",
            "connection_session_id": "text null",
            "end_reason": "text null",
            "epoch_ended_at": "timestamptz null",
            "epoch_started_at": "timestamptz not null",
            "end_clock_sha256": "char(64) null",
            "establishment_clock_sha256": "char(64) not null",
            "establishment_health_sha256": "char(64) not null",
            "instrument": "text not null",
            "local_epoch_id": "text not null",
            "monotonic_domain_id": "char(64) not null",
            "provider": "text not null",
            "record_sha256": "char(64) not null",
            "run_id": "uuid not null",
            "schema_version": "text not null",
            "source_contract_sha256": "char(64) not null",
            "subscription_ack_clock_sha256": "char(64) not null",
            "subscription_acknowledged_at": "timestamptz not null",
        },
        "layer": "RAW",
        "primary_key": ["run_id", "local_epoch_id"],
        "purpose": "One uninterrupted acknowledged subscription epoch; reconnect always creates another.",
    },
    "prospective_stream_liveness": {
        "append_only": True,
        "columns": {
            "checks": "jsonb not null",
            "collector_owned": "boolean not null",
            "epoch_id": "text not null",
            "interval_end": "timestamptz not null",
            "interval_start": "timestamptz not null",
            "interval_end_monotonic_seconds": "numeric not null",
            "interval_start_monotonic_seconds": "numeric not null",
            "interval_clock_evidence_sha256": "char(64) not null",
            "liveness_record_sha256": "char(64) not null",
            "maximum_permitted_liveness_gap_seconds": "numeric not null",
            "monotonic_domain_id": "char(64) not null",
            "monotonic_elapsed_seconds": "numeric not null",
            "ping_cadence_seconds": "numeric not null",
            "pong_timeout_seconds": "numeric not null",
            "reason_codes": "jsonb not null",
            "run_id": "uuid not null",
            "schema_version": "text not null",
            "usable": "boolean not null",
            "wall_elapsed_seconds": "numeric not null",
            "wall_monotonic_divergence_seconds": "numeric not null",
        },
        "layer": "RAW",
        "primary_key": ["run_id", "epoch_id", "interval_start"],
        "purpose": "Collector-owned monotonic ping/pong deadline census for an exact interval.",
    },
    "prospective_stream_collector_health": {
        "append_only": True,
        "columns": {
            "clock_integrity_sha256": "char(64) not null",
            "counters": "jsonb not null",
            "epoch_id": "text not null",
            "health_record_sha256": "char(64) not null",
            "observed_at": "timestamptz not null",
            "period_end": "timestamptz not null",
            "period_start": "timestamptz not null",
            "reason_codes": "jsonb not null",
            "run_id": "uuid not null",
            "schema_version": "text not null",
            "usable": "boolean not null",
        },
        "layer": "RAW",
        "primary_key": ["run_id", "health_record_sha256"],
        "purpose": "Mechanical evidence that no local parser, queue, serialization or append loss occurred.",
    },
    "prospective_source_event": {
        "append_only": True,
        "columns": {
            "epoch_id": "text not null",
            "event_time": "timestamptz not null",
            "event_type": "text not null",
            "channel": "text not null",
            "instrument": "text not null",
            "price": "numeric not null",
            "provider": "text not null",
            "quantity": "numeric not null",
            "raw_payload_sha256": "char(64) not null",
            "received_at": "timestamptz not null",
            "received_at_clock_sha256": "char(64) not null",
            "received_at_monotonic_seconds": "numeric not null",
            "record_sha256": "char(64) not null",
            "run_id": "uuid not null",
            "schema_version": "text not null",
            "scientific_payload_sha256": "char(64) not null",
            "sequence_number": "bigint null",
            "side": "text not null",
            "signed_notional_usd": "numeric not null",
            "source_event_id": "text not null",
        },
        "layer": "RAW",
        "primary_key": ["run_id", "epoch_id", "source_event_id", "raw_payload_sha256"],
        "purpose": "Exact epoch-bound trade event; identical retransmissions deduplicate and conflicts invalidate.",
    },
    "prospective_kraken_futures_metadata_validation": {
        "append_only": True,
        "columns": {
            "contract_size_usd": "numeric not null",
            "endpoint": "text not null",
            "instrument_type": "text not null",
            "maximum_age_seconds": "numeric not null",
            "metadata_record_sha256": "char(64) not null",
            "product_id": "text not null",
            "query_succeeded": "boolean not null",
            "raw_payload_sha256": "char(64) not null",
            "reason_codes": "jsonb not null",
            "retrieval_clock_sha256": "char(64) not null",
            "retrieved_at": "timestamptz not null",
            "run_id": "uuid not null",
            "schema_version": "text not null",
            "tradeable": "boolean not null",
            "underlying": "text not null",
            "usable": "boolean not null",
            "validation_id": "text not null",
        },
        "layer": "RAW",
        "primary_key": ["run_id", "metadata_record_sha256"],
        "purpose": (
            "Start/finalization runtime validation of PI_XBTUSD material "
            "metadata; missing, stale or drifted values invalidate the hour."
        ),
    },
    "prospective_stream_interval_completeness": {
        "append_only": True,
        "columns": {
            "clock_integrity_reference": "char(64) not null",
            "collector_health_pass": "boolean not null",
            "collector_health_sha256": "char(64) not null",
            "complete": "boolean not null",
            "duplicate_retransmission_count": "integer not null",
            "epoch_to_finalization_clock_sha256": "char(64) not null",
            "epoch_continuous_through_end": "boolean not null",
            "epoch_id": "text not null",
            "event_census_sha256": "char(64) not null",
            "event_count": "integer not null",
            "event_record_sha256s": "jsonb not null",
            "events": "jsonb not null",
            "finalization_clock_sha256": "char(64) not null",
            "finalized_at": "timestamptz not null",
            "instrument": "text not null",
            "interval_end": "timestamptz not null",
            "interval_start": "timestamptz not null",
            "interval_clock_evidence_sha256": "char(64) not null",
            "liveness_pass": "boolean not null",
            "liveness_sha256": "char(64) not null",
            "metadata_validation_sha256s": "jsonb not null",
            "monotonic_domain_id": "char(64) not null",
            "provider": "text not null",
            "provider_sequence_integrity_pass": "boolean not null",
            "reason_codes": "jsonb not null",
            "run_id": "uuid not null",
            "schema_version": "text not null",
            "source_epoch_sha256": "char(64) not null",
            "stream_interval_record_sha256": "char(64) not null",
            "subscription_ack_before_start": "boolean not null",
        },
        "layer": "RAW",
        "primary_key": ["run_id", "stream_interval_record_sha256"],
        "purpose": (
            "Replayable per-leg completeness referencing the exact epoch, "
            "liveness, health, clock, metadata and event evidence graph."
        ),
    },
    "prospective_cvd_interval_completeness": {
        "append_only": True,
        "columns": {
            "complete": "boolean not null",
            "completion_evidence_sha256": "char(64) not null",
            "finalized_at": "timestamptz not null",
            "interval_end": "timestamptz not null",
            "interval_start": "timestamptz not null",
            "perp_cvd_usd": "numeric null",
            "perp_epoch_id": "text not null",
            "perp_collector_health_pass": "boolean not null",
            "perp_clock_integrity_sha256": "char(64) not null",
            "perp_event_census_sha256": "char(64) not null",
            "perp_event_count": "integer not null",
            "perp_interval_completeness": "jsonb not null",
            "perp_interval_completeness_sha256": "char(64) not null",
            "perp_liveness_pass": "boolean not null",
            "perp_sequence_integrity_pass": "boolean not null",
            "perp_subscription_ack_before_start": "boolean not null",
            "reason_codes": "jsonb not null",
            "run_id": "uuid not null",
            "schema_version": "text not null",
            "spot_cvd_usd": "numeric null",
            "spot_epoch_id": "text not null",
            "spot_collector_health_pass": "boolean not null",
            "spot_clock_integrity_sha256": "char(64) not null",
            "spot_event_census_sha256": "char(64) not null",
            "spot_event_count": "integer not null",
            "spot_interval_completeness": "jsonb not null",
            "spot_interval_completeness_sha256": "char(64) not null",
            "spot_liveness_pass": "boolean not null",
            "spot_subscription_ack_before_start": "boolean not null",
        },
        "layer": "RAW",
        "primary_key": ["run_id", "interval_start", "completion_evidence_sha256"],
        "purpose": "Mechanically derived common spot/perpetual CVD hour; complete is never caller supplied.",
    },
    "prospective_liquidation_interval_completeness": {
        "append_only": True,
        "columns": {
            "available_at": "timestamptz not null",
            "completion_evidence_sha256": "char(64) not null",
            "clock_integrity_sha256": "char(64) not null",
            "collector_health_sha256": "char(64) not null",
            "contract_size_usd": "numeric not null",
            "event_count": "integer null",
            "event_type": "text not null",
            "decision_time": "timestamptz not null",
            "feed_status": "text not null",
            "finalized_at": "timestamptz not null",
            "instrument": "text not null",
            "interval_start": "timestamptz not null",
            "long_liquidation_notional_usd": "numeric null",
            "provider": "text not null",
            "reason": "text null",
            "run_id": "uuid not null",
            "schema_version": "text not null",
            "short_liquidation_notional_usd": "numeric null",
            "source_record_ids_digest": "char(64) null",
            "source_epoch_sha256": "char(64) not null",
            "stream_liveness_sha256": "char(64) not null",
            "timeframe": "text not null",
            "verified_hour_record_sha256": "char(64) not null",
        },
        "layer": "RAW",
        "primary_key": ["run_id", "interval_start", "completion_evidence_sha256"],
        "purpose": "Hourly liquidation state derived from the same verified Futures stream evidence as CVD.",
    },
    "prospective_liquidation_day_census": {
        "append_only": True,
        "columns": {
            "census_sha256": "char(64) not null",
            "census_status": "text not null",
            "available_at": "timestamptz null",
            "event_count": "integer null",
            "duplicate_interval_ids": "jsonb not null",
            "expected_hour_count": "integer not null",
            "expected_interval_ids": "jsonb not null",
            "hourly_record_digests": "jsonb not null",
            "hourly_completeness_evidence_digests": "jsonb not null",
            "long_liquidation_notional_usd": "numeric null",
            "missing_interval_ids": "jsonb not null",
            "observation_date": "date not null",
            "observation_time": "timestamptz not null",
            "observed_hour_count": "integer not null",
            "reason_codes": "jsonb not null",
            "run_id": "uuid not null",
            "schema_version": "text not null",
            "short_liquidation_notional_usd": "numeric null",
            "total_liquidation_notional_usd": "numeric null",
            "unexpected_interval_ids": "jsonb not null",
        },
        "layer": "RAW",
        "primary_key": ["run_id", "observation_date", "census_sha256"],
        "purpose": "Exact 24-hour UTC census required before any daily liquidation value exists.",
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
    "prospective_liquidation_feed_state": {
        "append_only": True,
        "columns": {
            "available_at": "timestamptz not null",
            "clock_integrity_sha256": "char(64) not null",
            "collector_health_sha256": "char(64) not null",
            "completion_evidence_sha256": "char(64) not null",
            "contract_size_usd": "numeric not null",
            "event_count": "integer null",
            "event_type": "text not null",
            "feed_status": "text not null",
            "ingested_at": "timestamptz not null",
            "instrument": "text not null",
            "long_liquidation_notional_usd": "numeric null",
            "observation_time": "timestamptz not null",
            "provider": "text not null",
            "revision": "text not null",
            "run_id": "uuid not null",
            "short_liquidation_notional_usd": "numeric null",
            "source_record_ids_digest": "char(64) null",
            "source_stream_epoch_sha256": "char(64) not null",
            "stream_liveness_sha256": "char(64) not null",
            "timeframe": "text not null",
        },
        "layer": "RAW",
        "primary_key": [
            "run_id",
            "provider",
            "instrument",
            "timeframe",
            "observation_time",
            "revision",
        ],
        "purpose": (
            "Liquidation feed state persisted independently of the aggregate "
            "numeric value, so an observed interval with zero liquidation "
            "events is never stored as, nor recovered as, a missing feed. "
            f"feed_status is drawn from {list(LIQUIDATION_FEED_STATUSES)} and "
            f"is owned by {PROSPECTIVE_LIQUIDATION_CAPTURE_VERSION}; the "
            "notional columns are null for every unusable status and are never "
            "defaulted to zero."
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
        "exact_record_persistence": {
            "authority_table": "prospective_scientific_evidence_record",
            "canonical_payload": (
                "Exact canonical ASCII bytes of the normalized record payload "
                "excluding record_sha256; bytes use the frozen lossless tagged "
                "representation and Decimal/timestamp values are decoded under "
                "the record's schema_version."
            ),
            "digest_rule": (
                "sha256(canonical_payload_bytes) == record_sha256"
            ),
            "typed_table_role": (
                "Query/index projection only; never evidence authority and never "
                "a replacement for the exact content-addressed record."
            ),
        },
        "implementation_state": SCHEMA_IMPLEMENTATION_STATE,
        "evidence_graph_rule": (
            "SCIENTIFIC SURFACE RECORDS ARE NOT AUTHORITIES. Every surface must "
            "resolve its exact referenced records, recompute all digests, validate "
            "schema/version and transitive semantics, verify cross-record identity, "
            "and only then derive a value or status. Digest-only evidence is refused."
        ),
        "referential_integrity": {
            "clock_interval_to_health": "all clock_health_record_sha256s resolve",
            "coingecko_response_to_attempt": "request_record_sha256 resolves",
            "cvd_to_stream_intervals": "both interval completeness hashes resolve",
            "liquidation_day_to_hours": "all 24 verified-hour hashes resolve",
            "liquidation_hour_to_completeness": "completeness_evidence_sha256 resolves",
            "stream_event_to_receive_clock": "received_at_clock_sha256 resolves",
            "stream_interval_to_graph": (
                "epoch, liveness, collector health, clock interval, final clock, "
                "runtime metadata and every event digest resolve"
            ),
        },
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
    "evidence_resolution_order": [
        "resolve every referenced record",
        "recompute its digest and validate schema/version",
        "resolve all transitive material evidence",
        "re-run the owner predicate and verify cross-record identity",
        "compare the replay-derived scientific fields with the surface",
    ],
    "digest_only_material_evidence_permitted": False,
    "mutable_application_state_permitted": False,
    "scientific_surface_records_are_authorities": False,
    "numerical_invariance": [
        "ambient Decimal context",
        "PYTHONHASHSEED",
        "dictionary iteration order",
        "provider order",
        "process restart",
        "working directory",
    ],
    "replay_inputs": [
        *_APPEND_ONLY_RAW_TABLES,
    ],
}

STAGE_B_EVALUATION_CONTRACT_VERSION = "PROSPECTIVE_STAGE_B_EVALUATION_CONTRACT_V1"

FUTURE_WORKFLOW = (
    "POSTP1-001R5 REPLAYABLE CORRECTED PROTOCOL",
    "SIXTH INDEPENDENT XHIGH REVIEW OF EXACT CORRECTED PROTOCOL HASH",
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
        "acquisition_semantics_are_new_pre_data_governance": True,
        "acquisition_semantics_distinct_from_feature_semantics": True,
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
        "prospective_acquisition_contract_versions": list(
            PROSPECTIVE_ACQUISITION_CONTRACT_VERSIONS
        ),
        "protocol_version": PROTOCOL_VERSION,
        "provenance_detection_requirements": list(PROVENANCE_DETECTION_REQUIREMENTS),
        "schema_version": "PROSPECTIVE_INTEGRATION_INPUT_SNAPSHOT_V2",
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
    acquisition = prospective_acquisition_governance()
    children = {
        _CHILD_KEY_BY_FILENAME[filename]: globals()[builder]()
        for filename, builder in _CHILD_ARTIFACTS
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
        "material_child_count": len(children),
        "material_child_enumeration": (
            "mechanically enumerated from the single artifact/builder registry"
        ),
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
            "failed_prospective_protocols": [
                dict(row) for row in FAILED_PROSPECTIVE_PROTOCOL_LINEAGE
            ],
            "failed_prospective_protocol_count": len(
                FAILED_PROSPECTIVE_PROTOCOL_LINEAGE
            ),
            "protocol_version_retained_rationale": (
                PROTOCOL_VERSION_RETAINED_RATIONALE
            ),
        },
        "prospective_acquisition_governance": {
            key: value
            for key, value in acquisition.items()
            if key != "contracts"
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
    (
        COINGECKO_REQUEST_ATTEMPT_FILENAME,
        "coingecko_market_cap_request_attempt_contract",
    ),
    (
        COINGECKO_RESPONSE_VALIDATION_FILENAME,
        "coingecko_market_cap_response_validation_contract",
    ),
    (CVD_INTERVAL_COMPLETENESS_FILENAME, "cvd_interval_completeness_contract"),
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
    (CVD_ACQUISITION_FILENAME, "prospective_cvd_acquisition_contract"),
    (
        MARKET_CAP_ACQUISITION_FILENAME,
        "prospective_btc_market_cap_acquisition_contract",
    ),
    (LIQUIDATION_CAPTURE_FILENAME, "prospective_liquidation_capture_contract"),
    (
        LIQUIDATION_PERCENTILE_ADAPTER_FILENAME,
        "prospective_liquidation_percentile_adapter_contract",
    ),
    (CLOCK_INTEGRITY_FILENAME, "prospective_clock_integrity_contract"),
    (STREAM_EPOCH_FILENAME, "source_stream_epoch_contract"),
    (STREAM_LIVENESS_FILENAME, "stream_liveness_policy_contract"),
    (
        KRAKEN_FUTURES_METADATA_VALIDATION_FILENAME,
        "kraken_futures_instrument_metadata_validation_contract",
    ),
    (
        SCIENTIFIC_EVIDENCE_RESOLVER_FILENAME,
        "scientific_evidence_resolver_contract",
    ),
    (
        LIQUIDATION_INTERVAL_COMPLETENESS_FILENAME,
        "liquidation_interval_completeness_contract",
    ),
    (LIQUIDATION_DAY_CENSUS_FILENAME, "liquidation_utc_day_census_contract"),
)


_CHILD_KEY_BY_FILENAME = {
    COINGECKO_REQUEST_ATTEMPT_FILENAME: "coingecko_market_cap_request_attempt",
    COINGECKO_RESPONSE_VALIDATION_FILENAME: (
        "coingecko_market_cap_response_validation"
    ),
    CVD_INTERVAL_COMPLETENESS_FILENAME: "cvd_interval_completeness",
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
    CVD_ACQUISITION_FILENAME: "prospective_cvd_acquisition",
    MARKET_CAP_ACQUISITION_FILENAME: "prospective_btc_market_cap_acquisition",
    LIQUIDATION_CAPTURE_FILENAME: "prospective_liquidation_capture",
    LIQUIDATION_PERCENTILE_ADAPTER_FILENAME: (
        "prospective_liquidation_percentile_adapter"
    ),
    CLOCK_INTEGRITY_FILENAME: "prospective_clock_integrity",
    STREAM_EPOCH_FILENAME: "source_stream_epoch",
    STREAM_LIVENESS_FILENAME: "stream_liveness_policy",
    KRAKEN_FUTURES_METADATA_VALIDATION_FILENAME: (
        "kraken_futures_instrument_metadata_validation"
    ),
    SCIENTIFIC_EVIDENCE_RESOLVER_FILENAME: "scientific_evidence_resolver",
    LIQUIDATION_INTERVAL_COMPLETENESS_FILENAME: (
        "liquidation_interval_completeness"
    ),
    LIQUIDATION_DAY_CENSUS_FILENAME: "liquidation_utc_day_census",
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
    ]
    for row in FAILED_PROSPECTIVE_PROTOCOL_LINEAGE:
        lines += [
            f"- Attempt {row['attempt']} (`{row['ticket']}`) hash: "
            f"`{row['definition_sha256']}`",
            f"  - Implementation commit: `{row['implementation_commit']}`",
            f"  - Review: `{row['review']}` / `{row['review_classification']}`",
            "  - Retained as failed, non-authoritative, superseded before "
            "collection: `YES`",
        ]
    warmup = warmup_history_contract()
    derivation = warmup["vol_percentile_2y_derivation"]
    lines += [
        "",
        f"Version retained rather than incremented: {PROTOCOL_VERSION_RETAINED_RATIONALE}",
        "",
        "## New prospective pre-data acquisition governance",
        "",
        "Phase-1 owns the feature transformations. It never owned a persisted "
        "source, cadence or feed-state contract for three of their raw inputs, "
        f"so `{ACQUISITION_GOVERNANCE_TICKET}` freezes those acquisition "
        "semantics now, before collection, and declares them explicitly as new "
        "governance rather than inherited authority.",
        "",
        f"- `{PROSPECTIVE_CVD_ACQUISITION_VERSION}`: the historical owner "
        f"`{CVD_HISTORICAL_OWNER}` specifies **no cadence** -- it accepts "
        "arbitrary common timestamps and is observation-count based, requiring "
        f"`{CVD_HISTORICAL_OWNER_WINDOW}`. The "
        f"`{CVD_SELECTED_CADENCE}` acquisition cadence is selected here by new "
        "pre-data governance over exact Kraken `BTC/USD` spot and `PI_XBTUSD` "
        "perpetual trade feeds. Every complete hour is reconstructed from one "
        "uninterrupted acknowledged subscription epoch, collector-owned "
        "ping/pong liveness, renewed same-domain clock health, collector-health "
        "counters, runtime PI_XBTUSD metadata and exact event/received-at "
        "censuses; nothing is stitched across reconnects and no event received "
        "after finalization can enter the closed revision. The selector requires the "
        "current and 20 prior contiguous UTC hours before the observation-count "
        "owner; no Stage-B outcome was inspected.",
        f"- `{PROSPECTIVE_MARKET_CAP_ACQUISITION_VERSION}`: no repository "
        "producer emits `market_cap_usd` today, and the unqualified "
        "`raw.generic_series` family is not a source contract. One exact series "
        f"identity is frozen: `{MARKET_CAP_SERIES_ID}` / "
        f"`{MARKET_CAP_SERIES_TYPE}` / `{MARKET_CAP_SERIES_UNIT}` from provider "
        f"`{MARKET_CAP_PROVIDER_ID}` `{MARKET_CAP_PROVIDER_ENDPOINT}` on "
        f"`{MARKET_CAP_RAW_TABLE}` at `{MARKET_CAP_OBSERVATION_CADENCE}`. Fixed "
        "00:45/00:50/00:55 UTC polling serializes `date=YYYY-MM-DD`, binds each "
        "exact response BYTEA and byte digest to its exact request attempt, "
        "mechanically enforces the inclusive 45-second monotonic timeout, "
        "represents timeout/transport failures without fake response fields, "
        "validates exact `bitcoin` / "
        "`btc` identity and a finite positive `market_data.market_cap.usd`, "
        "records clock-valid response completion locally, requeries day-1 "
        "through day-3, requires the exact scheduled date and selects one "
        "latest PIT revision per timestamp.",
        f"- `{PROSPECTIVE_LIQUIDATION_CAPTURE_VERSION}`: the existing aggregate "
        f"`{LIQUIDATION_AGGREGATE_OWNER}` collapses a missing feed and an "
        "observed zero-event feed to the same numeric zero. The prospective "
        "capture layer uses only Kraken Futures `PI_XBTUSD` liquidation-typed "
        "trade events and reuses the same epoch/liveness/health evidence as CVD. "
        "An observed zero requires one fully replayed exact hour. The daily "
        "reducer resolves each cited completeness record and its transitive graph, "
        "so a rehashed surface cannot override incomplete evidence; a daily "
        "value requires the exact 24-hour UTC census with no missing or duplicate "
        f"identity, over `{list(LIQUIDATION_FEED_STATUSES)}`.",
        f"- `{PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_VERSION}`: no "
        "executable owner produces `liquidation_percentile`, so one is frozen "
        f"here over a `{LIQUIDATION_PERCENTILE_WINDOW_DAYS}`-day half-open "
        f"trailing window with `{LIQUIDATION_PERCENTILE_MIN_OBSERVATIONS}` "
        f"minimum prior observations and the repository's own "
        f"`{LIQUIDATION_PERCENTILE_CONVENTION}` convention.",
        f"- `{PROSPECTIVE_CLOCK_INTEGRITY_VERSION}`: scientific local wall "
        "timestamps require an auditable synchronized OS/NTP/chrony health "
        "record with absolute offset and uncertainty each no greater than one "
        "second. Health is polled every 30 seconds, may be no older than 40 "
        "seconds and may have no renewal gap above 40 seconds. Durations and "
        "liveness deadlines use one explicit host/process/start/boot monotonic "
        "domain; a larger than one-second wall/monotonic divergence invalidates "
        "the affected evidence.",
        "",
        "## Warmup is a rule, not a constant",
        "",
        f"- `VOL_PERCENTILE_2Y` trailing window span: "
        f"`{derivation['rolling_window_span_days']}` days, "
        f"`{derivation['rolling_window_boundary']}`.",
        "- Minimum prior observations: "
        f"`{_VOL_PERCENTILE_KWDEFAULTS['min_percentile_observations']}`.",
        f"- Upstream initialization: {derivation['upstream_initialization']}.",
        "- First evaluable with contiguous daily observations: "
        f"`{derivation['first_evaluable_contiguous_daily_sessions']}` sessions "
        f"(`{derivation['first_evaluable_elapsed_calendar_days']}` elapsed "
        "calendar days).",
        "- `750 calendar days` is **not** retained as a scientific minimum; "
        "contiguous-history numbers are retained only as "
        f"`{WARMUP_PLANNING_ESTIMATE_LABEL}`.",
        "",
        "## Corrected ownership and input closure",
        "",
        "- `raw.liquidations` is a required append-only PIT capture family.",
        "- Every `INITIAL_FEATURE_NAMES` member is bound to its transitive raw "
        "input families and one prospective capture contract.",
        "- `OI_INTENSITY` and `OI_INTENSITY_PERCENTILE_180D` name the frozen "
        "market-cap source contract, never an unqualified generic-series "
        "family.",
        f"- Trade-action comparison owner: `{TRADE_ACTION_COMPARISON_OWNER_VERSION}`.",
        f"- Trade-eligibility permission owner: `{TRADE_ELIGIBILITY_COMPOSITE_OWNER_VERSION}`.",
        f"- Stop-event anchor: `{STOP_EVENT_UNIVERSE_ANCHOR}`.",
        f"- Gap-through prior owner: `{PRIOR_OBSERVABLE_OWNER}`; maximum gap: `3600s`.",
        "",
        "## Frozen child contracts",
        "",
        f"Material child count (mechanically enumerated): `{len(hashes)}`",
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
