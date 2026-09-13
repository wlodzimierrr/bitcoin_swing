"""``PROSPECTIVE_INTEGRATION_CORPUS_V2`` -- the replay-complete certified parent.

POSTP1-001V2, ``EPIC X -- PROSPECTIVE INTEGRATION EVIDENCE``.

``PROSPECTIVE_INTEGRATION_CORPUS_V1`` (``8915d991...fbfac7d7``) passed its sixth
independent exact-hash xHigh review and remains **immutable historical certified
lineage**.  It is not modified in place, its hash does not move, and it is not
called invalid for anything it was reviewed for.  Its one limitation, found by
the POSTP1-003R3 parent-completeness audit, is narrow and named:

    REPLAY PROVENANCE INCOMPLETE FOR THE NEW SUFFICIENCY-AUTHORITY REQUIREMENT

Stage-B sufficiency governance must derive every scientifically material blind
fact by *replaying persisted parent evidence*.  Three V1 structures cannot carry
that weight:

1.  ``prospective_decision_observation.warmup_history_complete`` is a Boolean and
    a singular ``input_snapshot_sha256`` does not enumerate the owner-specific
    history from which each warmup predicate is rerun, so an omitted qualifying
    or adverse observation is undetectable.
2.  ``prospective_portfolio_state`` binds only a ``prior_state_sha256`` digest of
    selected fields -- not the predecessor *record* -- and binds no producing
    transition, while ``prospective_trade_action`` binds a prior state but no
    result.  The exact root opening transition and active-stop membership cannot
    be traversed.
3.  Filling those gaps with governance-authored ``quality_state`` /
    ``upstream_initialization_complete`` conclusions is not a replay of certified
    evidence, which is why POSTP1-003R2 was rejected.

V2 changes **only** the certified-parent evidence/provenance architecture needed
for deterministic transitive replay.  Every provider identity, acquisition
semantic, feature formula, decision rule, risk semantic, stop-event definition
and Stage-B metric/threshold/direction/hard-role/intent is imported from its
existing authoritative owner and re-verified on every build.  The frozen
semantic-parity expectation is zero changes in all eight of those families, and
``semantic_diff_v1_to_v2`` proves it mechanically rather than asserting it.

No prospective observation has ever been collected under V1, so V2 starts fresh:
there is nothing to migrate and nothing is fabricated backwards.  This module
collects nothing, starts no live capture, runs no real Stage-B evaluation and
opens no BTC-019 sealed data.  Every record it can build is synthetic evidence
for the adversarial replay tests that prove the closure works.
"""

from __future__ import annotations

import decimal as _decimal_module
import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Context, Decimal
from pathlib import Path
from typing import Any

from btc_predictor.portfolio import account as _account
from btc_predictor.portfolio import state_machine as _state_machine
from btc_predictor.research import feature_matrix as _feature_matrix
from btc_predictor.research import prospective_integration_corpus as _v1
from btc_predictor.research import prospective_source_integrity as _source_integrity
from btc_predictor.risk import sizing as _sizing

# ---------------------------------------------------------------------------
# 0. identity
# ---------------------------------------------------------------------------

PROTOCOL_VERSION = "PROSPECTIVE_INTEGRATION_CORPUS_V2"
PROTOCOL_SCHEMA_VERSION = "PROSPECTIVE_INTEGRATION_CORPUS_V2_PROTOCOL_DEFINITION_V1"
PROTOCOL_STATUS = (
    "FROZEN_PRE_DATA_REPLAY_COMPLETE_PARENT_V2_AWAITING_XHIGH_REVIEW"
)
FINAL_CLASSIFICATION = "PROSPECTIVE_INTEGRATION_CORPUS_V2_READY_FOR_XHIGH_REVIEW"

BLOCKED_BY_MISSING_OWNER_AUTHORITY = (
    "PROSPECTIVE_CORPUS_V2_BLOCKED_BY_MISSING_EXISTING_OWNER_AUTHORITY"
)
REQUIRES_EPIC_T_AUTHORITY_CHANGE = (
    "PROSPECTIVE_CORPUS_V2_REQUIRES_EPIC_T_AUTHORITY_CHANGE"
)
BLOCKED_BY_CONFLICTING_AUTHORITY = (
    "PROSPECTIVE_CORPUS_V2_BLOCKED_BY_CONFLICTING_AUTHORITY"
)
FAIL_CLOSED_CLASSIFICATIONS = (
    FINAL_CLASSIFICATION,
    BLOCKED_BY_MISSING_OWNER_AUTHORITY,
    REQUIRES_EPIC_T_AUTHORITY_CHANGE,
    BLOCKED_BY_CONFLICTING_AUTHORITY,
)

PROGRAM_TICKET = "POSTP1-001V2"
WORKSTREAM = _v1.WORKSTREAM
WORKSTREAM_NAME = _v1.WORKSTREAM_NAME

OUTPUT_NAMESPACE = "prospective_evidence/prospective_integration_corpus_v2"
PROTOCOL_FILENAME = "protocol_definition.json"
REPORT_FILENAME = "PROSPECTIVE_INTEGRATION_CORPUS_V2_REPORT.md"

CERTIFICATION_STATE = "NOT_CERTIFIED_PENDING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW"
CERTIFICATION_AUTHORITY = (
    "Only an independent exact-hash xHigh review may certify V2. This module may "
    "classify itself no higher than "
    f"{FINAL_CLASSIFICATION}."
)

# ---------------------------------------------------------------------------
# 1. V1 lineage, retained immutable
# ---------------------------------------------------------------------------

PARENT_V1_VERSION = _v1.PROTOCOL_VERSION
PARENT_V1_DEFINITION_SHA256 = (
    "8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7"
)
PARENT_V1_CERTIFICATION = "POSTP1-002R5 PASS"
PARENT_V1_QUALIFYING_OBSERVATIONS_COLLECTED = False
PARENT_V1_LIMITATION = (
    "REPLAY PROVENANCE INCOMPLETE FOR THE NEW SUFFICIENCY-AUTHORITY REQUIREMENT"
)
PARENT_V1_LIMITATION_SCOPE = (
    "V1 remains immutable historical certified lineage and is not invalid for any "
    "semantics its six reviews already accepted. It is insufficient only as the "
    "authoritative parent for the full transitive scientific replay that Stage-B "
    "sufficiency governance now requires."
)
PARENT_V1_POST_CERTIFICATION_CLASSIFICATION = (
    "SUPERSEDED_PRE_COLLECTION_BY_REPLAY_COMPLETE_V2"
)
PARENT_V1_CLASSIFICATION_NOW = (
    "IMMUTABLE_CERTIFIED_LINEAGE_COLLECTION_AUTHORITY_UNCHANGED_UNTIL_V2_REVIEW_PASS"
)

BLOCKING_AUDIT_TICKET = "POSTP1-003R3"
BLOCKING_AUDIT_RESULT = "SUFFICIENCY_GOVERNANCE_REQUIRES_CERTIFIED_CORPUS_CHANGE"
BLOCKING_AUDIT_COMMIT = "49a817f6d39fde6be6cff584ba8d75c0b9e62ba7"
LATEST_FAILED_SUFFICIENCY_GOVERNANCE_SHA256 = (
    "0c0c0f96bc68afee0cbecc285546e0721e6fc621b09354af079adffd5863c64e"
)
FAILED_SUFFICIENCY_GOVERNANCE_SHA256S = (
    "3f51c4d9d8f14689b3f6c863e1731a6ef170b9764162b79bd56cc369af4ae2c7",
    "0ca7a2a8487e9c54b1b0f5ad07201ec39dfd20b328b5e09cb3b51b0de86c8242",
    LATEST_FAILED_SUFFICIENCY_GOVERNANCE_SHA256,
)

FROZEN_V3_DEFINITION_SHA256 = (
    "4232e886e7888b85833f778fcba6b2cb3eb5b7d802748aebf3b8adf19c5bf71a"
)
CERTIFIED_V1_VALIDATOR_DEFINITION_SHA256 = (
    "8e6254e0354c04de077bf482ccb6852bfe4299f138d3c97f1ba33859bfc7ffe7"
)
FROZEN_V4_DEFINITION_SHA256 = (
    "670ff12dd3d63615e9ddb3be05d65505bab16b50e50f1fd9ad077a4923a3f501"
)
FROZEN_V5_DEFINITION_SHA256 = (
    "95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89"
)

# ---------------------------------------------------------------------------
# 2. numerical standards and canonical identity
# ---------------------------------------------------------------------------

CORPUS_DECIMAL_PRECISION = _v1.CORPUS_DECIMAL_PRECISION
_CONTEXT = Context(prec=CORPUS_DECIMAL_PRECISION)
_SHA256_HEX_LENGTH = 64
DIGEST_FIELD = "record_sha256"


class ProspectiveCorpusV2Error(ValueError):
    """Raised when V2 authority, evidence, replay or artifact integrity fails."""


class ReplayRefusedError(ProspectiveCorpusV2Error):
    """Raised when a replay refuses rather than deriving a scientific result."""


class CollectionNotAuthorizedError(ProspectiveCorpusV2Error):
    """Raised when a caller tries to collect before every required review passes."""


def _canonical_json(payload: Any) -> str:
    """Serialize exactly as the certified V1 parent does.

    The encoding is deliberately identical to
    ``prospective_integration_corpus._canonical_json`` so that a V2 record and a
    V1 record of the same payload share one identity. A regression asserts the
    two agree rather than trusting the resemblance.
    """

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


def _require_sha256(value: Any, field_name: str) -> str:
    if not _is_sha256(value):
        raise ProspectiveCorpusV2Error(f"{field_name} must be a SHA-256 digest")
    return value


def _require_utc(value: Any, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ProspectiveCorpusV2Error(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ProspectiveCorpusV2Error(f"{field_name} must be UTC")
    return value


def _isoformat(value: datetime) -> str:
    return _require_utc(value, "timestamp").isoformat()


def _parse_utc(value: Any, field_name: str) -> datetime:
    if isinstance(value, datetime):
        return _require_utc(value, field_name)
    if not isinstance(value, str):
        raise ProspectiveCorpusV2Error(f"{field_name} must be an ISO-8601 UTC string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:  # pragma: no cover - defensive
        raise ProspectiveCorpusV2Error(f"{field_name} is not ISO-8601") from error
    return _require_utc(parsed, field_name)


def _decimal(value: Any, field_name: str) -> Decimal:
    """Parse an exact Decimal from a persisted string.

    Persisted evidence carries numbers as strings precisely so that no ambient
    ``Decimal`` context, float repr or locale can move a scientific value between
    the write and the replay.
    """

    if isinstance(value, bool) or not isinstance(value, str):
        raise ProspectiveCorpusV2Error(f"{field_name} must be an exact decimal string")
    try:
        return Decimal(value)
    except Exception as error:  # pragma: no cover - defensive
        raise ProspectiveCorpusV2Error(f"{field_name} is not a decimal") from error


# ===========================================================================
# 3. the content-addressed scientific evidence store
# ===========================================================================
#
# V1 already froze ``SCIENTIFIC_EVIDENCE_RESOLVER_V1`` and the governing rule
# ``SCIENTIFIC SURFACE RECORDS ARE NOT AUTHORITIES``.  V2 does not redesign that
# layer; it reuses it and adds the decision, owner-history and portfolio closure
# that references it.  The store here is the executable expression of the same
# contract: identity is the digest of the canonical payload without the digest
# field, a missing reference refuses, and a substituted reference refuses.

EVIDENCE_RESOLVER_VERSION = _source_integrity.SCIENTIFIC_EVIDENCE_RESOLVER_VERSION
EVIDENCE_RESOLVER_V2_VERSION = "SCIENTIFIC_EVIDENCE_RESOLVER_V2"

RECORD_KIND_FIELD = "record_kind"
SCHEMA_VERSION_FIELD = "schema_version"
CORPUS_BINDING_FIELD = "certified_corpus_sha256"

SOURCE_OBSERVATION_KIND = "PROSPECTIVE_SOURCE_OBSERVATION_V2"
DERIVED_FEATURE_KIND = "PROSPECTIVE_DERIVED_FEATURE_V2"
OWNER_HISTORY_MANIFEST_KIND = "PROSPECTIVE_OWNER_HISTORY_MANIFEST_V2"
SLOT_EVIDENCE_MANIFEST_KIND = "PROSPECTIVE_SLOT_EVIDENCE_MANIFEST_V2"
DECISION_OBSERVATION_KIND = "PROSPECTIVE_DECISION_OBSERVATION_V2"
DECISION_OWNER_OUTPUT_KIND = "PROSPECTIVE_DECISION_OWNER_OUTPUT_V2"
REFERENCE_EVALUATION_KIND = "PROSPECTIVE_REFERENCE_EVALUATION_V2"
RISK_EVALUATION_KIND = "PROSPECTIVE_RISK_EVALUATION_V2"
PORTFOLIO_STATE_KIND = "PROSPECTIVE_PORTFOLIO_STATE_V2"
PORTFOLIO_TRANSITION_KIND = "PROSPECTIVE_PORTFOLIO_TRANSITION_V2"
STOP_EVENT_KIND = "PROSPECTIVE_STOP_EVENT_V2"
SOURCE_ACQUISITION_EVIDENCE_KIND = "PROSPECTIVE_SOURCE_ACQUISITION_EVIDENCE_V2"

RECORD_KINDS = (
    DECISION_OBSERVATION_KIND,
    DECISION_OWNER_OUTPUT_KIND,
    DERIVED_FEATURE_KIND,
    OWNER_HISTORY_MANIFEST_KIND,
    PORTFOLIO_STATE_KIND,
    PORTFOLIO_TRANSITION_KIND,
    REFERENCE_EVALUATION_KIND,
    RISK_EVALUATION_KIND,
    SLOT_EVIDENCE_MANIFEST_KIND,
    SOURCE_ACQUISITION_EVIDENCE_KIND,
    SOURCE_OBSERVATION_KIND,
    STOP_EVENT_KIND,
)

RECORD_SCHEMA_VERSIONS = {kind: f"{kind}_SCHEMA_V1" for kind in RECORD_KINDS}

MISSING_REFERENCE_BEHAVIOR = "REFUSE"
SUBSTITUTED_REFERENCE_BEHAVIOR = "REFUSE"
DIGEST_ROLE = "identity and integrity check, never semantic authority"


class EvidenceStore:
    """An append-only content-addressed store of exact scientific records.

    This is the executable counterpart of
    ``research.prospective_scientific_evidence_record``.  ``put`` computes the
    identity; a caller cannot assert one.  ``get`` recomputes the digest before
    returning, so a mutated payload can never be resolved under its old name.
    """

    __slots__ = ("_records",)

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    def put(self, record: Mapping[str, Any]) -> str:
        payload = dict(record)
        if DIGEST_FIELD in payload:
            raise ProspectiveCorpusV2Error(
                f"a caller may not assert {DIGEST_FIELD}; identity is computed"
            )
        kind = payload.get(RECORD_KIND_FIELD)
        if kind not in RECORD_KINDS:
            raise ProspectiveCorpusV2Error(f"unknown record kind {kind!r}")
        if payload.get(SCHEMA_VERSION_FIELD) != RECORD_SCHEMA_VERSIONS[kind]:
            raise ProspectiveCorpusV2Error(f"{kind} carries the wrong schema version")
        digest = _digest(payload)
        payload[DIGEST_FIELD] = digest
        existing = self._records.get(digest)
        if existing is not None and existing != payload:  # pragma: no cover
            raise ProspectiveCorpusV2Error("content-addressed identity collision")
        self._records[digest] = payload
        return digest

    def get(self, sha256: Any, *, expected_kind: str | None = None) -> dict[str, Any]:
        _require_sha256(sha256, "record reference")
        record = self._records.get(sha256)
        if record is None:
            raise ReplayRefusedError(f"missing evidence reference {sha256}")
        recomputed = dict(record)
        declared = recomputed.pop(DIGEST_FIELD)
        if declared != sha256 or _digest(recomputed) != sha256:  # pragma: no cover
            raise ReplayRefusedError(f"evidence record {sha256} does not re-digest")
        if expected_kind is not None and record[RECORD_KIND_FIELD] != expected_kind:
            raise ReplayRefusedError(
                f"{sha256} is a {record[RECORD_KIND_FIELD]}, not a {expected_kind}"
            )
        return dict(record)

    def contains(self, sha256: str) -> bool:
        return sha256 in self._records

    def of_kind(self, kind: str) -> tuple[dict[str, Any], ...]:
        if kind not in RECORD_KINDS:
            raise ProspectiveCorpusV2Error(f"unknown record kind {kind!r}")
        return tuple(
            dict(record)
            for _, record in sorted(self._records.items())
            if record[RECORD_KIND_FIELD] == kind
        )

    def __len__(self) -> int:  # pragma: no cover - convenience
        return len(self._records)

    def tamper(self, sha256: str, field: str, value: Any) -> str:
        """Re-publish a mutated copy under its own new identity.

        Adversarial tests need a record that is internally self-consistent and
        wrong. Mutating in place would break content addressing itself and prove
        nothing; publishing the mutation honestly is the harder test, because the
        replay must then catch it by cross-binding rather than by digest.
        """

        record = self.get(sha256)
        record.pop(DIGEST_FIELD)
        if field not in record:
            raise ProspectiveCorpusV2Error(f"{field} is not a field of this record")
        record[field] = value
        return self.put(record)


# ===========================================================================
# 4. the owner/evaluability census
# ===========================================================================
#
# The POSTP1-003R3 audit's first blocker: a single generic
# ``input_snapshot_sha256`` does not establish warmup/history closure, and a
# single generic count rule would flatten heterogeneous scientific predicates
# into one invented one.  Neither is acceptable, so this census does the
# opposite of inventing: every row is *derived* from the owner that already owns
# the feature, and the class only selects which frozen predicate *shape* reads
# those owner-supplied parameters.
#
# The parameters themselves come from the certified V1 parent's own
# ``warmup_history`` child, which derived them from the live owner modules and
# was reviewed six times.  V2 re-derives them on every build and refuses if the
# owner inventory or any parameter has moved.

OBSERVATION_TIME_FIELD = "observation_time"
AVAILABLE_AT_FIELD = "available_at"
PIT_POLICY_VERSION = _v1.POINT_IN_TIME_POLICY_VERSION
PIT_RULE = _v1.PIT_RULE
REVISION_POLICY = _v1.REVISION_POLICY
MISSING_DATA_POLICY = _v1.MISSING_DATA_POLICY
DUPLICATE_POLICY = _v1.DUPLICATE_POLICY

OBSERVED_WITH_EVENTS = _source_integrity.FEED_STATUS_OBSERVED_WITH_EVENTS
OBSERVED_ZERO_EVENTS = _source_integrity.FEED_STATUS_OBSERVED_ZERO_EVENTS
SOURCE_UNAVAILABLE = _source_integrity.FEED_STATUS_SOURCE_UNAVAILABLE
OBSERVATION_LATE = _source_integrity.FEED_STATUS_LATE
OBSERVATION_INVALID = _source_integrity.FEED_STATUS_INVALID

QUALIFYING_OBSERVATION_STATUSES = _v1.LIQUIDATION_OBSERVED_FEED_STATUSES
ADVERSE_OBSERVATION_STATUSES = _v1.LIQUIDATION_UNUSABLE_FEED_STATUSES
OBSERVATION_STATUSES = _v1.LIQUIDATION_FEED_STATUSES

OBSERVATION_STATUS_OWNER = (
    "btc_predictor.research.prospective_integration_corpus."
    "LIQUIDATION_FEED_STATUSES"
)
OBSERVATION_STATUS_RULE = (
    "An observed interval carrying zero events is a scientific observation, not "
    "a missing feed, and an unavailable, late or invalid interval is adverse "
    "evidence that the history is incomplete -- never a zero and never an "
    "omission. V2 reuses the certified V1 feed-status vocabulary verbatim rather "
    "than authoring a second one."
)

# Owner classes.  Each names one frozen predicate shape, not one number.
CLASS_PRIOR_WINDOW_MIN_COUNT_ELAPSED = "PRIOR_WINDOW_MIN_COUNT_ELAPSED_V2"
CLASS_PRIOR_WINDOW_MIN_COUNT_OBSERVATIONS = (
    "PRIOR_WINDOW_MIN_COUNT_OBSERVATIONS_V2"
)
CLASS_TRAILING_WINDOW_AT_LEAST_ONE = "TRAILING_WINDOW_AT_LEAST_ONE_V2"
CLASS_CONTIGUOUS_SESSION_CLOSES = "CONTIGUOUS_SESSION_CLOSES_V2"
CLASS_EXACT_LOOKBACK_PAIR = "EXACT_LOOKBACK_PAIR_V2"
CLASS_AT_OR_BEFORE_LOOKBACK_PAIR = "AT_OR_BEFORE_LOOKBACK_PAIR_V2"
CLASS_WEEKLY_SESSION_COUNT = "WEEKLY_SESSION_COUNT_V2"
CLASS_PUBLICATION_DAY_COUNT = "PUBLICATION_DAY_COUNT_V2"
CLASS_DUAL_WINDOW_GROWTH_ZSCORE = "DUAL_WINDOW_GROWTH_ZSCORE_V2"
CLASS_COMPONENT_CONJUNCTION = "COMPONENT_CONJUNCTION_V2"
CLASS_CURRENT_VECTOR_ONLY = "CURRENT_VECTOR_ONLY_V2"
CLASS_DETERMINISTIC_INIT_SMOOTHING = "DETERMINISTIC_INIT_SMOOTHING_V2"

OWNER_CLASSES = (
    CLASS_AT_OR_BEFORE_LOOKBACK_PAIR,
    CLASS_COMPONENT_CONJUNCTION,
    CLASS_CONTIGUOUS_SESSION_CLOSES,
    CLASS_CURRENT_VECTOR_ONLY,
    CLASS_DETERMINISTIC_INIT_SMOOTHING,
    CLASS_DUAL_WINDOW_GROWTH_ZSCORE,
    CLASS_EXACT_LOOKBACK_PAIR,
    CLASS_PRIOR_WINDOW_MIN_COUNT_ELAPSED,
    CLASS_PRIOR_WINDOW_MIN_COUNT_OBSERVATIONS,
    CLASS_PUBLICATION_DAY_COUNT,
    CLASS_TRAILING_WINDOW_AT_LEAST_ONE,
    CLASS_WEEKLY_SESSION_COUNT,
)

OWNER_CLASS_PREDICATES: dict[str, str] = {
    CLASS_PRIOR_WINDOW_MIN_COUNT_ELAPSED: (
        "At least minimum_prior_count qualifying observations of the required "
        "series fall inside the half-open elapsed window "
        "[observation_time - window_span, observation_time), and the current "
        "observation_time itself carries a qualifying observation. The window "
        "span alone never implies completeness."
    ),
    CLASS_PRIOR_WINDOW_MIN_COUNT_OBSERVATIONS: (
        "At least minimum_prior_count qualifying observations of the required "
        "series precede observation_time on the owner's acquisition grid, and "
        "the current observation_time carries one. The owner counts "
        "observations, not elapsed days, and supplies no cadence of its own."
    ),
    CLASS_TRAILING_WINDOW_AT_LEAST_ONE: (
        "At least one qualifying observation falls inside the half-open "
        "trailing window (observation_time - window_span, observation_time]."
    ),
    CLASS_CONTIGUOUS_SESSION_CLOSES: (
        "minimum_contiguous_count consecutive canonical sessions ending at "
        "observation_time each carry a qualifying observation with no gap, and "
        "every one of them is strictly positive."
    ),
    CLASS_EXACT_LOOKBACK_PAIR: (
        "A qualifying observation exists at observation_time and at exactly "
        "observation_time - lookback_periods sessions."
    ),
    CLASS_AT_OR_BEFORE_LOOKBACK_PAIR: (
        "A qualifying observation exists at observation_time and at least one "
        "exists at or before observation_time - lookback_span."
    ),
    CLASS_WEEKLY_SESSION_COUNT: (
        "minimum_count qualifying weekly-session observations fall inside the "
        "trailing weekly window ending at observation_time."
    ),
    CLASS_PUBLICATION_DAY_COUNT: (
        "minimum_count complete fund-universe publication days fall inside the "
        "trailing publication-calendar window, and the current point-in-time "
        "AUM observation is present."
    ),
    CLASS_DUAL_WINDOW_GROWTH_ZSCORE: (
        "minimum_count common observations exist, enough for two equal growth "
        "windows plus the prior growth history the z-score needs, and both "
        "growth z-scores are defined."
    ),
    CLASS_COMPONENT_CONJUNCTION: (
        "Every named component owner is independently evaluable under its own "
        "predicate. The composite inherits their predicates and invents no "
        "window of its own."
    ),
    CLASS_CURRENT_VECTOR_ONLY: (
        "Every named current input is present at this decision with "
        "available_at <= decision_time. No history window applies at this owner."
    ),
    CLASS_DETERMINISTIC_INIT_SMOOTHING: (
        "The upstream component is evaluable. A missing previous smoothed score "
        "is deterministically initialized by the owner itself and is recorded, "
        "never treated as missing evidence."
    ),
}

# Frozen evaluability outcome vocabulary.
EVALUABLE = "EVALUABLE"
NOT_EVALUABLE = "NOT_EVALUABLE"
EVALUABILITY_STATES = (EVALUABLE, NOT_EVALUABLE)

REASON_HISTORY_INCOMPLETE = "OWNER_HISTORY_INCOMPLETE"
REASON_CURRENT_OBSERVATION_MISSING = "CURRENT_OBSERVATION_MISSING"
REASON_LOOKBACK_OBSERVATION_MISSING = "LOOKBACK_OBSERVATION_MISSING"
REASON_CONTIGUITY_BROKEN = "CONTIGUOUS_HISTORY_BROKEN"
REASON_NON_POSITIVE_OBSERVATION = "NON_POSITIVE_OBSERVATION_IN_REQUIRED_HISTORY"
REASON_UPSTREAM_NOT_EVALUABLE = "UPSTREAM_COMPONENT_NOT_EVALUABLE"
REASON_REQUIRED_INPUT_MISSING = _v1.ACQUISITION_FEED_STATE_REQUIRED
REASON_ADVERSE_OBSERVATION = "ADVERSE_OBSERVATION_IN_REQUIRED_HISTORY"

EVALUABILITY_REASON_CODES = tuple(
    sorted(
        {
            REASON_ADVERSE_OBSERVATION,
            REASON_CONTIGUITY_BROKEN,
            REASON_CURRENT_OBSERVATION_MISSING,
            REASON_HISTORY_INCOMPLETE,
            REASON_LOOKBACK_OBSERVATION_MISSING,
            REASON_NON_POSITIVE_OBSERVATION,
            REASON_REQUIRED_INPUT_MISSING,
            REASON_UPSTREAM_NOT_EVALUABLE,
        }
    )
)


# ---------------------------------------------------------------------------
# 4a. evidence selectors
# ---------------------------------------------------------------------------
#
# A selector names *what the owner reads*, exactly enough that a replay can
# recompute the expected evidence set from the store without consulting the
# manifest it is checking.  Two series kinds exist because the owners genuinely
# differ: some read a captured source series, and some -- the percentile and
# z-score families -- read the prior results of another *derived* feature.  A
# percentile owner that needed 365 prior RV_20 results is not satisfied by 365
# daily closes, and flattening the two would be exactly the generic count rule
# this census exists to avoid.

SERIES_KIND_SOURCE = "SOURCE_OBSERVATION_SERIES"
SERIES_KIND_DERIVED = "DERIVED_FEATURE_SERIES"
SERIES_KIND_COMPONENTS = "COMPONENT_OWNER_SET"
SERIES_KINDS = (SERIES_KIND_COMPONENTS, SERIES_KIND_DERIVED, SERIES_KIND_SOURCE)

CADENCE_HOURLY = "1h"
CADENCE_DAILY = "1d"
CADENCE_WEEKLY = "1w"
CADENCE_PUBLICATION_DAY = "ETF_PUBLICATION_DAY"
REQUIRED_CADENCES = (
    CADENCE_DAILY,
    CADENCE_HOURLY,
    CADENCE_PUBLICATION_DAY,
    CADENCE_WEEKLY,
)

CADENCE_INTERVAL = {
    CADENCE_HOURLY: timedelta(hours=1),
    CADENCE_DAILY: timedelta(days=1),
    CADENCE_WEEKLY: timedelta(days=7),
    CADENCE_PUBLICATION_DAY: timedelta(days=1),
}

# Series identities.  ``family`` is the certified V1 capture family; nothing here
# introduces a provider, endpoint or normalization the parent did not already
# freeze.
SERIES_CANONICAL_DAILY_CLOSE = "CANONICAL_DAILY_CLOSE"
SERIES_CANONICAL_WEEKLY_SESSION = "CANONICAL_WEEKLY_SESSION"
SERIES_CANONICAL_HOURLY_BAR = "CANONICAL_HOURLY_BAR"
SERIES_ETF_PUBLICATION_DAY = "ETF_FUND_UNIVERSE_PUBLICATION_DAY"
SERIES_FUNDING_RATE = "DERIVATIVES_FUNDING_RATE"
SERIES_FUTURES_BASIS = "DERIVATIVES_FUTURES_BASIS"
SERIES_OPEN_INTEREST = "DERIVATIVES_OPEN_INTEREST"
SERIES_BTC_MARKET_CAP = _v1.MARKET_CAP_SERIES_ID
SERIES_SPOT_PERP_CVD = "SPOT_PERP_COMMON_CVD_OBSERVATION"
SERIES_SPOT_PERP_PARTICIPATION = "SPOT_PERP_COMMON_VOLUME_PARTICIPATION"
SERIES_LIQUIDATION_DAILY = "LIQUIDATION_UTC_DAY_AGGREGATE"
SERIES_STRUCTURE_INPUT = "STRUCTURE_POINT_IN_TIME_INPUT_VECTOR"

_SERIES_FAMILY: dict[str, str] = {
    SERIES_CANONICAL_DAILY_CLOSE: "raw_provider_ohlcv",
    SERIES_CANONICAL_WEEKLY_SESSION: "raw_provider_ohlcv",
    SERIES_CANONICAL_HOURLY_BAR: "raw_provider_ohlcv",
    SERIES_ETF_PUBLICATION_DAY: "etf_flows",
    SERIES_FUNDING_RATE: "derivatives_funding",
    SERIES_FUTURES_BASIS: "derivatives_futures_basis",
    SERIES_OPEN_INTEREST: "derivatives_open_interest",
    SERIES_BTC_MARKET_CAP: "btc_market_cap",
    SERIES_SPOT_PERP_CVD: "spot_perp_cvd",
    SERIES_SPOT_PERP_PARTICIPATION: "spot_perp_volume_participation",
    SERIES_LIQUIDATION_DAILY: "liquidations",
    SERIES_STRUCTURE_INPUT: "raw_provider_ohlcv",
}

_SERIES_CADENCE: dict[str, str] = {
    SERIES_CANONICAL_DAILY_CLOSE: CADENCE_DAILY,
    SERIES_CANONICAL_WEEKLY_SESSION: CADENCE_WEEKLY,
    SERIES_CANONICAL_HOURLY_BAR: CADENCE_HOURLY,
    SERIES_ETF_PUBLICATION_DAY: CADENCE_PUBLICATION_DAY,
    SERIES_FUNDING_RATE: CADENCE_DAILY,
    SERIES_FUTURES_BASIS: CADENCE_DAILY,
    SERIES_OPEN_INTEREST: CADENCE_DAILY,
    SERIES_BTC_MARKET_CAP: _v1.MARKET_CAP_OBSERVATION_CADENCE,
    SERIES_SPOT_PERP_CVD: _v1.CVD_SELECTED_CADENCE,
    SERIES_SPOT_PERP_PARTICIPATION: CADENCE_HOURLY,
    SERIES_LIQUIDATION_DAILY: CADENCE_DAILY,
    SERIES_STRUCTURE_INPUT: CADENCE_DAILY,
}


@dataclass(frozen=True)
class EvidenceSelector:
    """The deterministic rule for what one owner reads at one slot."""

    series_kind: str
    series_id: str
    cadence: str
    window_kind: str
    window_span: str | None
    minimum_count: int | None
    window_span_days: int | None = None
    window_span_observations: int | None = None
    components: tuple[str, ...] = ()
    current_observation_required: bool = True
    additional_series: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        if self.series_kind not in SERIES_KINDS:
            raise ProspectiveCorpusV2Error(f"unknown series kind {self.series_kind!r}")
        if self.cadence not in REQUIRED_CADENCES and self.series_kind != (
            SERIES_KIND_COMPONENTS
        ):
            raise ProspectiveCorpusV2Error(f"unknown cadence {self.cadence!r}")
        return {
            "additional_series": list(self.additional_series),
            "cadence": self.cadence,
            "components": list(self.components),
            "current_observation_required": self.current_observation_required,
            "minimum_count": self.minimum_count,
            "series_family": _SERIES_FAMILY.get(self.series_id),
            "series_id": self.series_id,
            "series_kind": self.series_kind,
            "window_kind": self.window_kind,
            "window_span": self.window_span,
            "window_span_days": self.window_span_days,
            "window_span_observations": self.window_span_observations,
        }


WINDOW_HALF_OPEN_PRIOR = "HALF_OPEN_PRIOR_ELAPSED_[t-W,t)"
WINDOW_HALF_OPEN_TRAILING = "HALF_OPEN_TRAILING_ELAPSED_(t-W,t]"
WINDOW_PRIOR_OBSERVATIONS = "PRIOR_OBSERVATION_COUNT_ON_THE_OWNER_GRID"
WINDOW_CONTIGUOUS_SESSIONS = "CONTIGUOUS_SESSIONS_ENDING_AT_t"
WINDOW_EXACT_LOOKBACK = "EXACT_LOOKBACK_SESSION_OFFSET"
WINDOW_AT_OR_BEFORE_LOOKBACK = "AT_OR_BEFORE_ELAPSED_LOOKBACK"
WINDOW_TRAILING_SESSION_COUNT = "TRAILING_SESSION_COUNT_ENDING_AT_t"
WINDOW_NONE = "NO_WINDOW_AT_THIS_OWNER"
WINDOW_UNBOUNDED_TRAILING = "UNBOUNDED_TRAILING_AT_OR_BEFORE_t"
WINDOW_KINDS = (
    WINDOW_AT_OR_BEFORE_LOOKBACK,
    WINDOW_CONTIGUOUS_SESSIONS,
    WINDOW_EXACT_LOOKBACK,
    WINDOW_HALF_OPEN_PRIOR,
    WINDOW_HALF_OPEN_TRAILING,
    WINDOW_NONE,
    WINDOW_PRIOR_OBSERVATIONS,
    WINDOW_TRAILING_SESSION_COUNT,
    WINDOW_UNBOUNDED_TRAILING,
)


# ---------------------------------------------------------------------------
# 4b. owner parameters, re-derived from the live owners
# ---------------------------------------------------------------------------


def _owner_parameters() -> dict[str, Any]:
    """Re-derive every warmup parameter from the owner that owns it.

    V2 does not trust the certified parent's persisted JSON for these numbers and
    it does not restate them as literals. It reads the owner modules, exactly as
    the certified ``warmup_history`` child did, and the census then cross-checks
    the two. If an owner renames a constant or moves a default, the build refuses
    rather than freezing a stale parameter into a new parent hash.
    """

    from btc_predictor.features import flow as _flow
    from btc_predictor.features import momentum as _momentum
    from btc_predictor.features import positioning as _positioning
    from btc_predictor.features import trend as _trend
    from btc_predictor.features import volatility as _volatility

    cvd_kwargs = _flow.spot_perp_cvd_spread.__kwdefaults__
    participation_kwargs = _flow.spot_perp_participation.__kwdefaults__
    percentile_kwargs = _volatility.volatility_percentile.__kwdefaults__
    rv_windows = {
        _volatility.RV_7_FEATURE_ID: 7,
        _volatility.RV_20_FEATURE_ID: 20,
        _volatility.RV_60_FEATURE_ID: 60,
    }
    for feature_id, window in rv_windows.items():
        if feature_id != f"RV_{window}":
            raise ProspectiveCorpusV2Error(
                f"the realized-volatility owner renamed {feature_id}"
            )
    source_feature_id = percentile_kwargs["source_feature_id"]
    if source_feature_id not in rv_windows:
        raise ProspectiveCorpusV2Error(
            "the volatility-percentile source feature is not a known RV owner"
        )
    parameters = {
        "basis_min": _positioning.DEFAULT_FUTURES_BASIS_MIN_ZSCORE_OBSERVATIONS,
        "basis_window_days": _positioning.DEFAULT_FUTURES_BASIS_ZSCORE_WINDOW_DAYS,
        "cvd_prior_observations": cvd_kwargs["zscore_window_periods"],
        "cvd_selected_cadence": _v1.CVD_SELECTED_CADENCE,
        "etf_5_days": _flow.FIVE_DAY_ETF_FLOW_WINDOW_DAYS,
        "etf_20_days": _flow.TWENTY_DAY_ETF_FLOW_WINDOW_DAYS,
        "funding_average_window_days": (
            _positioning.DEFAULT_FUNDING_AVERAGE_WINDOW_DAYS
        ),
        "funding_min": _positioning.DEFAULT_FUNDING_MIN_ZSCORE_OBSERVATIONS,
        "funding_window_days": _positioning.DEFAULT_FUNDING_ZSCORE_WINDOW_DAYS,
        "high_distance_weeks": _trend.FIFTY_TWO_WEEK_HIGH_DISTANCE_LOOKBACK_WEEKS,
        "liquidation_percentile_min": _v1.LIQUIDATION_PERCENTILE_MIN_OBSERVATIONS,
        "liquidation_percentile_window_days": _v1.LIQUIDATION_PERCENTILE_WINDOW_DAYS,
        "ma_distance_weeks": _trend.TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS,
        "momentum_4w_periods": _momentum.FOUR_WEEK_MOMENTUM_LOOKBACK_DAYS,
        "momentum_12w_periods": _momentum.TWELVE_WEEK_MOMENTUM_LOOKBACK_DAYS,
        "oi_growth_min": _positioning.DEFAULT_OI_GROWTH_MIN_ZSCORE_OBSERVATIONS,
        "oi_growth_window_days": _positioning.DEFAULT_OI_GROWTH_WINDOW_DAYS,
        "oi_growth_zscore_window_days": (
            _positioning.DEFAULT_OI_GROWTH_ZSCORE_WINDOW_DAYS
        ),
        "oi_intensity_min": (
            _positioning.DEFAULT_OI_INTENSITY_MIN_PERCENTILE_OBSERVATIONS
        ),
        "oi_intensity_window_days": (
            _positioning.DEFAULT_OI_INTENSITY_PERCENTILE_WINDOW_DAYS
        ),
        "participation_growth_periods": participation_kwargs[
            "growth_window_periods"
        ],
        "participation_zscore_periods": participation_kwargs[
            "zscore_window_periods"
        ],
        "rv_7_returns": rv_windows[_volatility.RV_7_FEATURE_ID],
        "rv_20_returns": rv_windows[_volatility.RV_20_FEATURE_ID],
        "rv_60_returns": rv_windows[_volatility.RV_60_FEATURE_ID],
        "vol_percentile_min_prior": percentile_kwargs["min_percentile_observations"],
        "vol_percentile_source_feature_id": source_feature_id,
        "vol_percentile_window_days": percentile_kwargs["percentile_window_days"],
    }
    for name, value in parameters.items():
        if isinstance(value, bool) or (
            not isinstance(value, (int, str)) or (isinstance(value, int) and value <= 0)
        ):
            raise ProspectiveCorpusV2Error(
                f"owner parameter {name} is not a positive integer or identity"
            )
    if parameters["vol_percentile_min_prior"] > parameters[
        "vol_percentile_window_days"
    ]:
        raise ProspectiveCorpusV2Error(
            "the trailing window cannot hold the required prior observations"
        )
    return parameters


# ---------------------------------------------------------------------------
# 4c. the mechanical owner census
# ---------------------------------------------------------------------------

# The evaluability owner and the deterministic feature owner are not always the
# same function: three positioning families compute the value in a ``*_features``
# owner and decide completeness in the ``*_health`` owner that wraps it. The
# certified parent's ``warmup_history`` child binds the evaluability owner and
# its ``feature_input_coverage`` child binds the feature owner, so V2 states both
# explicitly and cross-checks each against its own parent authority rather than
# collapsing them into one name.
_EVALUABILITY_OWNER: dict[str, str] = {
    "TREND_SCORE": "btc_predictor.features.trend.calculate_trend_score",
    "FLOW_SCORE": "btc_predictor.features.flow.calculate_flow_score",
    "POSITIONING_SCORE": (
        "btc_predictor.features.positioning.calculate_positioning_score"
    ),
    "VOLATILITY_SCORE": "btc_predictor.features.volatility.calculate_volatility_score",
    "STRUCTURE_SCORE": "btc_predictor.features.structure.calculate_structure_score",
    "REGIME_SCORE": "btc_predictor.features.regime.calculate_regime_score",
    "REGIME_SMOOTHED_SCORE": (
        "btc_predictor.features.regime.calculate_regime_smoothing"
    ),
    "ORDERLINESS_SCORE": (
        "btc_predictor.features.volatility.calculate_orderliness_score"
    ),
    "MOMENTUM_4W": (
        "btc_predictor.features.momentum.four_week_momentum_from_daily_bars"
    ),
    "MOMENTUM_12W": (
        "btc_predictor.features.momentum.twelve_week_momentum_from_daily_bars"
    ),
    "MA_DISTANCE_20W": "btc_predictor.features.trend.twenty_week_ma_distance",
    "HIGH_DISTANCE_52W": "btc_predictor.features.trend.fifty_two_week_high_distance",
    "ETF_NORM_5D": "btc_predictor.features.flow.five_day_etf_flow",
    "ETF_NORM_20D": "btc_predictor.features.flow.twenty_day_etf_flow",
    "FLOW_ACCEL": "btc_predictor.features.flow.etf_flow_acceleration",
    "CVD_SPREAD": "btc_predictor.features.flow.spot_perp_cvd_spread",
    "SPOT_DOMINANCE": (
        "btc_predictor.features.flow.spot_perp_participation_from_rows"
    ),
    "FUNDING_7D_AVG": "btc_predictor.features.positioning.funding_health",
    "FUNDING_ZSCORE_180D": "btc_predictor.features.positioning.funding_health",
    "FUNDING_HEALTH": "btc_predictor.features.positioning.funding_health",
    "OI_GROWTH_7D": (
        "btc_predictor.features.positioning.open_interest_growth_health"
    ),
    "OI_GROWTH_ZSCORE_180D": (
        "btc_predictor.features.positioning.open_interest_growth_health"
    ),
    "OI_GROWTH_HEALTH": (
        "btc_predictor.features.positioning.open_interest_growth_health"
    ),
    "OI_INTENSITY": "btc_predictor.features.positioning.open_interest_intensity",
    "OI_INTENSITY_PERCENTILE_180D": (
        "btc_predictor.features.positioning.open_interest_intensity"
    ),
    "FUTURES_BASIS_AVG": "btc_predictor.features.positioning.futures_basis_health",
    "FUTURES_BASIS_ZSCORE_180D": (
        "btc_predictor.features.positioning.futures_basis_health"
    ),
    "FUTURES_BASIS_HEALTH": (
        "btc_predictor.features.positioning.futures_basis_health"
    ),
    "RV_7": "btc_predictor.features.volatility.realized_volatility_from_daily_bars",
    "RV_20": "btc_predictor.features.volatility.realized_volatility_from_daily_bars",
    "RV_60": "btc_predictor.features.volatility.realized_volatility_from_daily_bars",
    "VOL_COMPRESSION_RATIO": (
        "btc_predictor.features.volatility.volatility_compression_ratio"
    ),
    "VOL_PERCENTILE_2Y": "btc_predictor.features.volatility.volatility_percentile",
}


MISSING_BEHAVIOR_NOT_EVALUABLE = (
    "NOT_EVALUABLE_WITH_AN_EXPLICIT_REASON_CODE_NEVER_ZERO_FILLED"
)
MISSING_BEHAVIOR_DETERMINISTIC_INIT = (
    "THE_OWNER_DETERMINISTICALLY_INITIALIZES_AND_RECORDS_ITS_OWN_REASON_CODE"
)


OWNER_SYMBOL_RESOLUTION_RULE = (
    "Every owner string V2 freezes is imported and resolved on every build. The "
    "certified parent's feature_input_coverage child validated only that its "
    "owner string was a non-empty str, and two of its declared feature owners "
    "-- btc_predictor.features.positioning.funding_features and "
    "btc_predictor.features.positioning.open_interest_growth_features -- do not "
    "exist. Their real owners are the *_health functions the parent's own "
    "warmup_history child already names, so no science is affected: the parent "
    "measured the right predicate under a wrong label. V2 therefore records "
    "both the parent-declared string, for exact lineage, and the resolved "
    "symbol it verifies, and refuses to build if a resolved symbol disappears. "
    "The correction lives in this new V2 child; the certified V1 child is not "
    "edited, because editing it would move the immutable parent hash."
)


def _resolve_owner_symbol(path: str) -> bool:
    """Return whether a dotted owner path resolves to a real repository symbol."""

    from importlib import import_module

    if not isinstance(path, str) or not path.startswith("btc_predictor."):
        raise ProspectiveCorpusV2Error(f"{path!r} is not a repository owner path")
    module_path, _, symbol = path.rpartition(".")
    try:
        module = import_module(module_path)
    except ImportError:  # pragma: no cover - defensive
        return False
    return hasattr(module, symbol)


def _owner_row(
    *,
    owner_class: str,
    owner_contract: str,
    deterministic_feature_owner: str,
    resolved_feature_owner: str,
    selector: EvidenceSelector,
    upstream_initialization: str,
    missing_data_behavior: str = MISSING_BEHAVIOR_NOT_EVALUABLE,
    strictly_positive_required: bool = False,
    lookback_periods: int | None = None,
    lookback_span_days: int | None = None,
) -> dict[str, Any]:
    if owner_class not in OWNER_CLASSES:
        raise ProspectiveCorpusV2Error(f"unknown owner class {owner_class!r}")
    if selector.window_kind not in WINDOW_KINDS:
        raise ProspectiveCorpusV2Error(f"unknown window kind {selector.window_kind!r}")
    return {
        "evidence_selector": selector.as_record(),
        "parent_declared_feature_owner": deterministic_feature_owner,
        "parent_declared_feature_owner_resolves": _resolve_owner_symbol(
            deterministic_feature_owner
        ),
        "resolved_feature_owner": resolved_feature_owner,
        "lookback_periods": lookback_periods,
        "lookback_span_days": lookback_span_days,
        "minimum_history_predicate": OWNER_CLASS_PREDICATES[owner_class],
        "missing_data_behavior": missing_data_behavior,
        "owner_class": owner_class,
        "owner_contract": owner_contract,
        "pit_predicate": (
            f"{PIT_POLICY_VERSION}: {PIT_RULE}, resolved per observation_time to "
            "the latest revision whose available_at does not exceed decision_time; "
            "a later revision and a future-available observation are both excluded."
        ),
        "strictly_positive_required": strictly_positive_required,
        "upstream_initialization_predicate": upstream_initialization,
    }



# ---------------------------------------------------------------------------
# 4d. boundaries this census declares rather than hides
# ---------------------------------------------------------------------------
#
# Three facts about the existing owners are load-bearing for replay and are not
# stated anywhere in the certified parent.  V2 records them as boundaries rather
# than papering over them, because an unrecorded default is exactly the kind of
# hidden authority this corpus exists to remove.

UNOWNED_INPUT_BOUNDARIES: dict[str, dict[str, Any]] = {
    "market_holidays": {
        "consumers": [
            "btc_predictor.features.flow.five_day_etf_flow",
            "btc_predictor.features.flow.twenty_day_etf_flow",
            "btc_predictor.features.flow.etf_flow_window",
        ],
        "default": "an empty holiday set",
        "existing_owner": None,
        "replay_requirement": (
            "The ETF publication window is walked backwards over weekdays that "
            "are not in the supplied holiday set, so window membership is a "
            "function of that set. With the default empty set a market holiday "
            "is indistinguishable from a missing publication. A V2 owner-history "
            "manifest for ETF_NORM_5D, ETF_NORM_20D and FLOW_ACCEL therefore "
            "carries the exact ordered publication observations it selected, so "
            "membership is evidence rather than a recomputation."
        ),
        "search_evidence": (
            "No holiday calendar source family exists in the certified parent's "
            "PRICE_INPUT_SOURCES or NON_PRICE_INPUT_SOURCES, and no warmup row "
            "names one."
        ),
    },
    "canonical_bar_derivation_cutoff": {
        "consumers": ["btc_predictor.data.ohlcv.build_canonical_market_bars"],
        "default": "the caller's data_available_at cutoff",
        "existing_owner": _v1.CANONICAL_SESSION_OWNER,
        "replay_requirement": (
            "Daily and weekly canonical bars are derived from 1h source bars and "
            "a bar is emitted only when every constituent hour is present, so a "
            "bar's very existence is point-in-time evidence. Every V2 source "
            "observation on a derived session therefore carries the constituent "
            "source-record references that produced it, and the manifest resolves "
            "them; a bar without its constituents is not replayable evidence."
        ),
        "search_evidence": (
            "The canonical session owner defines the weekly boundary as Monday "
            "00:00 UTC and the daily boundary as 00:00 UTC."
        ),
    },
    "same_timestamp_revision_resolution": {
        "consumers": [
            "btc_predictor.features.positioning.funding_health",
            "btc_predictor.features.positioning.futures_basis_health",
            "btc_predictor.features.positioning.open_interest_growth_health",
            "btc_predictor.features.positioning.open_interest_intensity",
        ],
        "default": (
            "the owners aggregate every row sharing an observation_time rather "
            "than resolving a revision"
        ),
        "existing_owner": None,
        "replay_requirement": (
            "The certified parent freezes "
            f"{REVISION_POLICY} and {DUPLICATE_POLICY}, but only the ETF owner "
            "resolves revisions; the positioning owners sum or average rows that "
            "share a timestamp. V2 does not change any owner. It records the "
            "exact revision selected per observation_time in the owner-history "
            "manifest and refuses two distinct records claiming one revision, so "
            "a restatement is visible evidence instead of a silent blend."
        ),
        "search_evidence": (
            "Revision resolution appears in exactly one feature owner module."
        ),
    },
}

FROZEN_INPUT_POLICIES = {
    "duplicate_policy": DUPLICATE_POLICY,
    "late_data_policy": _v1.LATE_DATA_POLICY,
    "missing_data_policy": MISSING_DATA_POLICY,
    "revision_policy": REVISION_POLICY,
}

DELEGATED_GRID_OWNERS = {
    "canonical_session_owner": _v1.CANONICAL_SESSION_OWNER,
    "decision_delay_owner": _v1.DECISION_DELAY_OWNER,
    "decision_grid_owner": _v1.DECISION_GRID_OWNER,
    "pit_policy_owner": _v1.PIT_POLICY_OWNER,
}


# The parent declares a deterministic feature owner per feature and an
# evaluability owner per feature; four of the former do not resolve to a real
# symbol (see OWNER_SYMBOL_RESOLUTION_RULE). ``_RESOLVED_FEATURE_OWNER`` is the
# symbol V2 verifies: the parent's declared owner wherever it resolves, and the
# parent's own evaluability owner for the four it does not. Nothing is invented;
# the substitute is always a string the certified parent already froze.
_RESOLVED_FEATURE_OWNER: dict[str, str] = {
    feature: (
        owner
        if _resolve_owner_symbol(owner)
        else _EVALUABILITY_OWNER[feature]
    )
    for feature, owner in (
        (name, spec["owner"]) for name, spec in _v1._FEATURE_DEPENDENCIES.items()
    )
}


def owner_evaluability_census() -> dict[str, Any]:
    """Bind every frozen feature owner to a replayable evidence selector.

    Each of the 33 names in ``INITIAL_FEATURE_NAMES`` lands in exactly one owner
    class, and every class parameter is the owner's own. The certified parent's
    ``warmup_history`` child is then cross-checked row for row: same owners, same
    inventory, same 33 names. Any divergence refuses the build.
    """

    parameters = _owner_parameters()
    features = tuple(_feature_matrix.INITIAL_FEATURE_NAMES)
    dependencies = _v1._FEATURE_DEPENDENCIES
    rv_20 = parameters["vol_percentile_source_feature_id"]
    rv_20_closes = parameters["rv_20_returns"] + 1

    rows: dict[str, dict[str, Any]] = {}

    def daily(series: str = SERIES_CANONICAL_DAILY_CLOSE, **kwargs: Any) -> EvidenceSelector:
        return EvidenceSelector(
            series_kind=SERIES_KIND_SOURCE,
            series_id=series,
            cadence=_SERIES_CADENCE[series],
            **kwargs,
        )

    def derived(series: str, **kwargs: Any) -> EvidenceSelector:
        # A percentile or z-score owner reads the *prior results* of another
        # frozen feature, so the upstream owner is declared as a component and
        # its own predicate is replayed rather than assumed satisfied.
        return EvidenceSelector(
            series_kind=SERIES_KIND_DERIVED,
            series_id=series,
            cadence=CADENCE_DAILY,
            components=(series,),
            **kwargs,
        )

    def components(*names: str) -> EvidenceSelector:
        return EvidenceSelector(
            series_kind=SERIES_KIND_COMPONENTS,
            series_id="COMPONENT_OWNERS",
            cadence=CADENCE_DAILY,
            window_kind=WINDOW_NONE,
            window_span=None,
            minimum_count=None,
            components=tuple(names),
        )

    # -- composites and health inheritors: COMPONENT_CONJUNCTION ------------
    rows["TREND_SCORE"] = _owner_row(
        owner_class=CLASS_COMPONENT_CONJUNCTION,
        owner_contract=_EVALUABILITY_OWNER["TREND_SCORE"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["TREND_SCORE"],
        deterministic_feature_owner=dependencies["TREND_SCORE"]["owner"],
        selector=components("MA_DISTANCE_20W", "HIGH_DISTANCE_52W", "MOMENTUM_12W"),
        upstream_initialization=(
            "the weekly structure and every selected component owner must be "
            "independently complete"
        ),
    )
    rows["FLOW_SCORE"] = _owner_row(
        owner_class=CLASS_COMPONENT_CONJUNCTION,
        owner_contract=_EVALUABILITY_OWNER["FLOW_SCORE"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["FLOW_SCORE"],
        deterministic_feature_owner=dependencies["FLOW_SCORE"]["owner"],
        selector=components(
            "ETF_NORM_5D", "ETF_NORM_20D", "FLOW_ACCEL", "CVD_SPREAD", "SPOT_DOMINANCE"
        ),
        upstream_initialization=(
            "the participation growth series needs two equal windows before its "
            "own z-score history exists"
        ),
    )
    rows["POSITIONING_SCORE"] = _owner_row(
        owner_class=CLASS_COMPONENT_CONJUNCTION,
        owner_contract=_EVALUABILITY_OWNER["POSITIONING_SCORE"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["POSITIONING_SCORE"],
        deterministic_feature_owner=dependencies["POSITIONING_SCORE"]["owner"],
        selector=components(
            "FUNDING_HEALTH", "OI_GROWTH_HEALTH", "FUTURES_BASIS_HEALTH"
        ),
        upstream_initialization=(
            f"the earliest OI-growth observation needs an OI observation "
            f"{parameters['oi_growth_window_days']}d earlier"
        ),
    )
    rows["VOLATILITY_SCORE"] = _owner_row(
        owner_class=CLASS_COMPONENT_CONJUNCTION,
        owner_contract=_EVALUABILITY_OWNER["VOLATILITY_SCORE"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["VOLATILITY_SCORE"],
        deterministic_feature_owner=dependencies["VOLATILITY_SCORE"]["owner"],
        selector=components(
            "RV_7", "RV_20", "RV_60", "VOL_COMPRESSION_RATIO", "VOL_PERCENTILE_2Y"
        ),
        upstream_initialization=(
            f"each {rv_20} result needs {rv_20_closes} contiguous daily closes"
        ),
    )
    rows["REGIME_SCORE"] = _owner_row(
        owner_class=CLASS_COMPONENT_CONJUNCTION,
        owner_contract=_EVALUABILITY_OWNER["REGIME_SCORE"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["REGIME_SCORE"],
        deterministic_feature_owner=dependencies["REGIME_SCORE"]["owner"],
        selector=components(
            "TREND_SCORE",
            "FLOW_SCORE",
            "POSITIONING_SCORE",
            "VOLATILITY_SCORE",
            "STRUCTURE_SCORE",
            "ORDERLINESS_SCORE",
        ),
        upstream_initialization=(
            "the full model additionally requires the point-in-time macro, "
            "on-chain and liquidity inputs"
        ),
    )
    rows["FLOW_ACCEL"] = _owner_row(
        owner_class=CLASS_COMPONENT_CONJUNCTION,
        owner_contract=_EVALUABILITY_OWNER["FLOW_ACCEL"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["FLOW_ACCEL"],
        deterministic_feature_owner=dependencies["FLOW_ACCEL"]["owner"],
        selector=components("ETF_NORM_5D", "ETF_NORM_20D"),
        upstream_initialization="none beyond the two source windows",
    )
    rows["VOL_COMPRESSION_RATIO"] = _owner_row(
        owner_class=CLASS_COMPONENT_CONJUNCTION,
        owner_contract=_EVALUABILITY_OWNER["VOL_COMPRESSION_RATIO"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["VOL_COMPRESSION_RATIO"],
        deterministic_feature_owner=dependencies["VOL_COMPRESSION_RATIO"]["owner"],
        selector=components("RV_7", "RV_20"),
        upstream_initialization=f"none beyond {rv_20}; {rv_20} must be non-zero",
    )
    rows["FUNDING_HEALTH"] = _owner_row(
        owner_class=CLASS_COMPONENT_CONJUNCTION,
        owner_contract=_EVALUABILITY_OWNER["FUNDING_HEALTH"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["FUNDING_HEALTH"],
        deterministic_feature_owner=dependencies["FUNDING_HEALTH"]["owner"],
        selector=components("FUNDING_ZSCORE_180D"),
        upstream_initialization="none beyond the funding z-score",
    )
    rows["OI_GROWTH_HEALTH"] = _owner_row(
        owner_class=CLASS_COMPONENT_CONJUNCTION,
        owner_contract=_EVALUABILITY_OWNER["OI_GROWTH_HEALTH"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["OI_GROWTH_HEALTH"],
        deterministic_feature_owner=dependencies["OI_GROWTH_HEALTH"]["owner"],
        selector=components("OI_GROWTH_ZSCORE_180D"),
        upstream_initialization="none beyond the OI-growth z-score",
    )
    rows["FUTURES_BASIS_HEALTH"] = _owner_row(
        owner_class=CLASS_COMPONENT_CONJUNCTION,
        owner_contract=_EVALUABILITY_OWNER["FUTURES_BASIS_HEALTH"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["FUTURES_BASIS_HEALTH"],
        deterministic_feature_owner=dependencies["FUTURES_BASIS_HEALTH"]["owner"],
        selector=components("FUTURES_BASIS_ZSCORE_180D"),
        upstream_initialization="none beyond the basis z-score",
    )

    # -- prior-window percentile / z-score owners ---------------------------
    rows["VOL_PERCENTILE_2Y"] = _owner_row(
        owner_class=CLASS_PRIOR_WINDOW_MIN_COUNT_ELAPSED,
        owner_contract=_EVALUABILITY_OWNER["VOL_PERCENTILE_2Y"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["VOL_PERCENTILE_2Y"],
        deterministic_feature_owner=dependencies["VOL_PERCENTILE_2Y"]["owner"],
        selector=derived(
            rv_20,
            window_kind=WINDOW_HALF_OPEN_PRIOR,
            window_span=f"{parameters['vol_percentile_window_days']}d",
            window_span_days=parameters["vol_percentile_window_days"],
            minimum_count=parameters["vol_percentile_min_prior"],
        ),
        upstream_initialization=(
            f"each {rv_20} result needs {rv_20_closes} contiguous daily closes "
            f"({parameters['rv_20_returns']} daily returns)"
        ),
    )
    rows["FUNDING_ZSCORE_180D"] = _owner_row(
        owner_class=CLASS_PRIOR_WINDOW_MIN_COUNT_ELAPSED,
        owner_contract=_EVALUABILITY_OWNER["FUNDING_ZSCORE_180D"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["FUNDING_ZSCORE_180D"],
        deterministic_feature_owner=dependencies["FUNDING_ZSCORE_180D"]["owner"],
        selector=daily(
            SERIES_FUNDING_RATE,
            window_kind=WINDOW_HALF_OPEN_PRIOR,
            window_span=f"{parameters['funding_window_days']}d",
            window_span_days=parameters["funding_window_days"],
            minimum_count=parameters["funding_min"],
        ),
        upstream_initialization=(
            "the current observation is excluded from its own history and the "
            "prior history's variance must be non-zero"
        ),
    )
    rows["FUTURES_BASIS_ZSCORE_180D"] = _owner_row(
        owner_class=CLASS_PRIOR_WINDOW_MIN_COUNT_ELAPSED,
        owner_contract=_EVALUABILITY_OWNER["FUTURES_BASIS_ZSCORE_180D"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["FUTURES_BASIS_ZSCORE_180D"],
        deterministic_feature_owner=dependencies["FUTURES_BASIS_ZSCORE_180D"]["owner"],
        selector=daily(
            SERIES_FUTURES_BASIS,
            window_kind=WINDOW_HALF_OPEN_PRIOR,
            window_span=f"{parameters['basis_window_days']}d",
            window_span_days=parameters["basis_window_days"],
            minimum_count=parameters["basis_min"],
        ),
        upstream_initialization=(
            "the current observation is excluded from its own history and the "
            "prior history's variance must be non-zero"
        ),
    )
    rows["OI_GROWTH_ZSCORE_180D"] = _owner_row(
        owner_class=CLASS_PRIOR_WINDOW_MIN_COUNT_ELAPSED,
        owner_contract=_EVALUABILITY_OWNER["OI_GROWTH_ZSCORE_180D"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["OI_GROWTH_ZSCORE_180D"],
        deterministic_feature_owner=dependencies["OI_GROWTH_ZSCORE_180D"]["owner"],
        selector=derived(
            "OI_GROWTH_7D",
            window_kind=WINDOW_HALF_OPEN_PRIOR,
            window_span=f"{parameters['oi_growth_zscore_window_days']}d",
            window_span_days=parameters["oi_growth_zscore_window_days"],
            minimum_count=parameters["oi_growth_min"],
        ),
        upstream_initialization=(
            "the earliest retained growth observation itself needs an "
            f"open-interest observation {parameters['oi_growth_window_days']}d "
            "earlier"
        ),
    )
    rows["OI_INTENSITY_PERCENTILE_180D"] = _owner_row(
        owner_class=CLASS_PRIOR_WINDOW_MIN_COUNT_ELAPSED,
        owner_contract=_EVALUABILITY_OWNER["OI_INTENSITY_PERCENTILE_180D"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["OI_INTENSITY_PERCENTILE_180D"],
        deterministic_feature_owner=dependencies["OI_INTENSITY_PERCENTILE_180D"]["owner"],
        selector=derived(
            "OI_INTENSITY",
            window_kind=WINDOW_HALF_OPEN_PRIOR,
            window_span=f"{parameters['oi_intensity_window_days']}d",
            window_span_days=parameters["oi_intensity_window_days"],
            minimum_count=parameters["oi_intensity_min"],
        ),
        upstream_initialization=(
            "every historical intensity observation needs its own aligned "
            "open-interest and market-cap pair"
        ),
    )
    rows["CVD_SPREAD"] = _owner_row(
        owner_class=CLASS_PRIOR_WINDOW_MIN_COUNT_OBSERVATIONS,
        owner_contract=_EVALUABILITY_OWNER["CVD_SPREAD"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["CVD_SPREAD"],
        deterministic_feature_owner=dependencies["CVD_SPREAD"]["owner"],
        selector=EvidenceSelector(
            series_kind=SERIES_KIND_SOURCE,
            series_id=SERIES_SPOT_PERP_CVD,
            cadence=parameters["cvd_selected_cadence"],
            window_kind=WINDOW_PRIOR_OBSERVATIONS,
            window_span=(
                f"{parameters['cvd_prior_observations']} prior common observations"
            ),
            window_span_observations=parameters["cvd_prior_observations"],
            minimum_count=parameters["cvd_prior_observations"],
        ),
        upstream_initialization=(
            "the z-score excludes the current observation from its own history, "
            "and both the spot and perp sides must carry the same common "
            "timestamps; neither side's history may be degenerate"
        ),
    )

    # -- at-least-one trailing owners ---------------------------------------
    rows["FUNDING_7D_AVG"] = _owner_row(
        owner_class=CLASS_TRAILING_WINDOW_AT_LEAST_ONE,
        owner_contract=_EVALUABILITY_OWNER["FUNDING_7D_AVG"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["FUNDING_7D_AVG"],
        deterministic_feature_owner=dependencies["FUNDING_7D_AVG"]["owner"],
        selector=daily(
            SERIES_FUNDING_RATE,
            window_kind=WINDOW_HALF_OPEN_TRAILING,
            window_span=f"{parameters['funding_average_window_days']}d",
            window_span_days=parameters["funding_average_window_days"],
            minimum_count=1,
            current_observation_required=False,
        ),
        upstream_initialization="none",
    )
    rows["FUTURES_BASIS_AVG"] = _owner_row(
        owner_class=CLASS_TRAILING_WINDOW_AT_LEAST_ONE,
        owner_contract=_EVALUABILITY_OWNER["FUTURES_BASIS_AVG"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["FUTURES_BASIS_AVG"],
        deterministic_feature_owner=dependencies["FUTURES_BASIS_AVG"]["owner"],
        selector=daily(
            SERIES_FUTURES_BASIS,
            window_kind=WINDOW_UNBOUNDED_TRAILING,
            window_span=None,
            minimum_count=1,
            current_observation_required=False,
        ),
        upstream_initialization="none",
    )

    # -- contiguous-session owners ------------------------------------------
    for feature, returns in (
        ("RV_7", parameters["rv_7_returns"]),
        ("RV_20", parameters["rv_20_returns"]),
        ("RV_60", parameters["rv_60_returns"]),
    ):
        rows[feature] = _owner_row(
            owner_class=CLASS_CONTIGUOUS_SESSION_CLOSES,
            owner_contract=_EVALUABILITY_OWNER[feature],
            deterministic_feature_owner=dependencies[feature]["owner"],
            resolved_feature_owner=_RESOLVED_FEATURE_OWNER[feature],
            selector=daily(
                window_kind=WINDOW_CONTIGUOUS_SESSIONS,
                window_span=f"{returns} daily returns",
                window_span_observations=returns + 1,
                minimum_count=returns + 1,
            ),
            upstream_initialization="the first return needs the previous close",
            strictly_positive_required=True,
        )

    # -- lookback-pair owners -----------------------------------------------
    for feature, periods in (
        ("MOMENTUM_4W", parameters["momentum_4w_periods"]),
        ("MOMENTUM_12W", parameters["momentum_12w_periods"]),
    ):
        rows[feature] = _owner_row(
            owner_class=CLASS_EXACT_LOOKBACK_PAIR,
            owner_contract=_EVALUABILITY_OWNER[feature],
            deterministic_feature_owner=dependencies[feature]["owner"],
            resolved_feature_owner=_RESOLVED_FEATURE_OWNER[feature],
            selector=daily(
                window_kind=WINDOW_EXACT_LOOKBACK,
                window_span=f"{periods} daily periods",
                window_span_observations=periods,
                minimum_count=2,
            ),
            upstream_initialization="the current close plus the lookback close",
            lookback_periods=periods,
        )
    rows["OI_GROWTH_7D"] = _owner_row(
        owner_class=CLASS_AT_OR_BEFORE_LOOKBACK_PAIR,
        owner_contract=_EVALUABILITY_OWNER["OI_GROWTH_7D"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["OI_GROWTH_7D"],
        deterministic_feature_owner=dependencies["OI_GROWTH_7D"]["owner"],
        selector=daily(
            SERIES_OPEN_INTEREST,
            window_kind=WINDOW_AT_OR_BEFORE_LOOKBACK,
            window_span=f"{parameters['oi_growth_window_days']}d",
            window_span_days=parameters["oi_growth_window_days"],
            minimum_count=2,
        ),
        upstream_initialization=(
            "a prior open-interest observation at or before "
            f"t - {parameters['oi_growth_window_days']}d is required"
        ),
        lookback_span_days=parameters["oi_growth_window_days"],
    )

    # -- weekly-session owners ----------------------------------------------
    for feature, weeks in (
        ("MA_DISTANCE_20W", parameters["ma_distance_weeks"]),
        ("HIGH_DISTANCE_52W", parameters["high_distance_weeks"]),
    ):
        rows[feature] = _owner_row(
            owner_class=CLASS_WEEKLY_SESSION_COUNT,
            owner_contract=_EVALUABILITY_OWNER[feature],
            deterministic_feature_owner=dependencies[feature]["owner"],
            resolved_feature_owner=_RESOLVED_FEATURE_OWNER[feature],
            selector=EvidenceSelector(
                series_kind=SERIES_KIND_SOURCE,
                series_id=SERIES_CANONICAL_WEEKLY_SESSION,
                cadence=CADENCE_WEEKLY,
                window_kind=WINDOW_TRAILING_SESSION_COUNT,
                window_span=f"{weeks} weekly periods",
                window_span_observations=weeks,
                minimum_count=weeks,
            ),
            upstream_initialization="none",
        )

    # -- ETF publication-calendar owners ------------------------------------
    for feature, days in (
        ("ETF_NORM_5D", parameters["etf_5_days"]),
        ("ETF_NORM_20D", parameters["etf_20_days"]),
    ):
        rows[feature] = _owner_row(
            owner_class=CLASS_PUBLICATION_DAY_COUNT,
            owner_contract=_EVALUABILITY_OWNER[feature],
            deterministic_feature_owner=dependencies[feature]["owner"],
            resolved_feature_owner=_RESOLVED_FEATURE_OWNER[feature],
            selector=EvidenceSelector(
                series_kind=SERIES_KIND_SOURCE,
                series_id=SERIES_ETF_PUBLICATION_DAY,
                cadence=CADENCE_PUBLICATION_DAY,
                window_kind=WINDOW_TRAILING_SESSION_COUNT,
                window_span=f"{days} publication days",
                window_span_observations=days,
                minimum_count=days,
            ),
            upstream_initialization="the latest point-in-time AUM is required",
        )

    # -- dual-window growth z-score -----------------------------------------
    participation_minimum = (
        parameters["participation_growth_periods"] * 2
        + parameters["participation_zscore_periods"]
    )
    rows["SPOT_DOMINANCE"] = _owner_row(
        owner_class=CLASS_DUAL_WINDOW_GROWTH_ZSCORE,
        owner_contract=_EVALUABILITY_OWNER["SPOT_DOMINANCE"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["SPOT_DOMINANCE"],
        deterministic_feature_owner=dependencies["SPOT_DOMINANCE"]["owner"],
        selector=EvidenceSelector(
            series_kind=SERIES_KIND_SOURCE,
            series_id=SERIES_SPOT_PERP_PARTICIPATION,
            cadence=CADENCE_HOURLY,
            window_kind=WINDOW_CONTIGUOUS_SESSIONS,
            window_span=(
                f"{parameters['participation_growth_periods']}-period current and "
                "prior growth windows plus "
                f"{parameters['participation_zscore_periods']} prior growth values"
            ),
            window_span_observations=participation_minimum,
            minimum_count=participation_minimum,
        ),
        upstream_initialization=(
            "the growth series initializes only after two equal windows"
        ),
    )

    # -- current-vector owners ----------------------------------------------
    rows["STRUCTURE_SCORE"] = _owner_row(
        owner_class=CLASS_CURRENT_VECTOR_ONLY,
        owner_contract=_EVALUABILITY_OWNER["STRUCTURE_SCORE"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["STRUCTURE_SCORE"],
        deterministic_feature_owner=dependencies["STRUCTURE_SCORE"]["owner"],
        selector=EvidenceSelector(
            series_kind=SERIES_KIND_SOURCE,
            series_id=SERIES_STRUCTURE_INPUT,
            cadence=CADENCE_DAILY,
            window_kind=WINDOW_NONE,
            window_span=None,
            minimum_count=1,
        ),
        upstream_initialization=(
            "the structural level and risk/reward owners must be complete"
        ),
    )
    rows["ORDERLINESS_SCORE"] = _owner_row(
        owner_class=CLASS_CURRENT_VECTOR_ONLY,
        owner_contract=_EVALUABILITY_OWNER["ORDERLINESS_SCORE"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["ORDERLINESS_SCORE"],
        deterministic_feature_owner=dependencies["ORDERLINESS_SCORE"]["owner"],
        selector=EvidenceSelector(
            series_kind=SERIES_KIND_SOURCE,
            series_id=SERIES_LIQUIDATION_DAILY,
            cadence=CADENCE_DAILY,
            window_kind=WINDOW_NONE,
            window_span=None,
            minimum_count=1,
            additional_series=(SERIES_CANONICAL_DAILY_CLOSE,),
        ),
        upstream_initialization=(
            "the volatility-percentile owner and "
            f"{_v1.PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_VERSION} must each "
            "be complete; an unavailable, late or invalid liquidation feed leaves "
            "the liquidation input missing and never zero"
        ),
    )
    rows["OI_INTENSITY"] = _owner_row(
        owner_class=CLASS_CURRENT_VECTOR_ONLY,
        owner_contract=_EVALUABILITY_OWNER["OI_INTENSITY"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["OI_INTENSITY"],
        deterministic_feature_owner=dependencies["OI_INTENSITY"]["owner"],
        selector=EvidenceSelector(
            series_kind=SERIES_KIND_SOURCE,
            series_id=SERIES_OPEN_INTEREST,
            cadence=CADENCE_DAILY,
            window_kind=WINDOW_NONE,
            window_span=None,
            minimum_count=1,
            additional_series=(SERIES_BTC_MARKET_CAP,),
        ),
        upstream_initialization=(
            "the market-cap input is supplied by "
            f"{_v1.PROSPECTIVE_MARKET_CAP_ACQUISITION_VERSION} on the "
            f"{_v1.MARKET_CAP_OBSERVATION_GRID} grid; the open-interest aggregate "
            "and the market-cap observation must share an exact observation_time"
        ),
    )

    # -- deterministic-init smoothing ---------------------------------------
    rows["REGIME_SMOOTHED_SCORE"] = _owner_row(
        owner_class=CLASS_DETERMINISTIC_INIT_SMOOTHING,
        owner_contract=_EVALUABILITY_OWNER["REGIME_SMOOTHED_SCORE"],
        resolved_feature_owner=_RESOLVED_FEATURE_OWNER["REGIME_SMOOTHED_SCORE"],
        deterministic_feature_owner=dependencies["REGIME_SMOOTHED_SCORE"]["owner"],
        selector=components("REGIME_SCORE"),
        upstream_initialization=(
            "the owner deterministically initializes a missing previous smoothed "
            "score from the current score and records "
            "REGIME_SMOOTHING_PREVIOUS_SCORE_MISSING"
        ),
        missing_data_behavior=MISSING_BEHAVIOR_DETERMINISTIC_INIT,
    )

    _verify_owner_census(rows, features, parameters)
    by_class: dict[str, list[str]] = {name: [] for name in OWNER_CLASSES}
    for feature in features:
        by_class[rows[feature]["owner_class"]].append(feature)
    payload = {
        "class_predicates": dict(OWNER_CLASS_PREDICATES),
        "delegated_grid_owners": dict(DELEGATED_GRID_OWNERS),
        "every_feature_in_exactly_one_class": True,
        "frozen_input_policies": dict(FROZEN_INPUT_POLICIES),
        "feature_count": len(rows),
        "feature_inventory": list(features),
        "feature_inventory_owner": (
            "btc_predictor.research.feature_matrix.INITIAL_FEATURE_NAMES"
        ),
        "generic_count_rule_substituted_for_owner_predicates": False,
        "missing_data_policy": MISSING_DATA_POLICY,
        "observation_status_owner": OBSERVATION_STATUS_OWNER,
        "observation_status_rule": OBSERVATION_STATUS_RULE,
        "owner_classes": list(OWNER_CLASSES),
        "owner_parameters": parameters,
        "owner_symbol_resolution_rule": OWNER_SYMBOL_RESOLUTION_RULE,
        "parent_declared_feature_owners_that_do_not_resolve": sorted(
            feature
            for feature, row in rows.items()
            if not row["parent_declared_feature_owner_resolves"]
        ),
        "owners_by_class": {name: sorted(members) for name, members in by_class.items()},
        "parent_v1_warmup_history_sha256": _v1.warmup_history_contract()[
            "definition_sha256"
        ],
        "pit_policy_version": PIT_POLICY_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "qualifying_observation_statuses": list(QUALIFYING_OBSERVATION_STATUSES),
        "adverse_observation_statuses": list(ADVERSE_OBSERVATION_STATUSES),
        "rows": rows,
        "schema_version": "PROSPECTIVE_OWNER_EVALUABILITY_CENSUS_V2",
        "unowned_input_boundaries": UNOWNED_INPUT_BOUNDARIES,
        "series_identities": {
            series: {
                "cadence": _SERIES_CADENCE[series],
                "family": _SERIES_FAMILY[series],
            }
            for series in sorted(_SERIES_FAMILY)
        },
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def _verify_owner_census(
    rows: Mapping[str, Any],
    features: Sequence[str],
    parameters: Mapping[str, Any],
) -> None:
    """Refuse a census that drifts from the frozen inventory or the parent."""

    missing = sorted(set(features) - set(rows))
    extra = sorted(set(rows) - set(features))
    if missing or extra:
        raise ProspectiveCorpusV2Error(
            f"owner census does not cover the frozen inventory; "
            f"missing={missing}, extra={extra}"
        )
    warmup = _v1.warmup_history_contract()
    parent_rows = warmup["rows"]
    if set(parent_rows) != set(features):
        raise ProspectiveCorpusV2Error(
            "the certified parent's warmup inventory no longer matches "
            "INITIAL_FEATURE_NAMES"
        )
    for feature in features:
        row = rows[feature]
        parent_owner = parent_rows[feature]["owner"]
        if row["owner_contract"] != parent_owner:
            raise ProspectiveCorpusV2Error(
                f"{feature} names evaluability owner {row['owner_contract']}, but "
                f"the certified parent binds {parent_owner}"
            )
        parent_feature_owner = _v1._FEATURE_DEPENDENCIES[feature]["owner"]
        if row["parent_declared_feature_owner"] != parent_feature_owner:
            raise ProspectiveCorpusV2Error(
                f"{feature} names feature owner "
                f"{row['parent_declared_feature_owner']}, but the certified "
                f"parent binds {parent_feature_owner}"
            )
        if not _resolve_owner_symbol(row["resolved_feature_owner"]):
            raise ProspectiveCorpusV2Error(
                f"{feature} resolves to {row['resolved_feature_owner']}, which "
                "is not a real repository symbol"
            )
        if not _resolve_owner_symbol(row["owner_contract"]):
            raise ProspectiveCorpusV2Error(
                f"{feature} names evaluability owner {row['owner_contract']}, "
                "which is not a real repository symbol"
            )
        selector = row["evidence_selector"]
        if selector["series_kind"] == SERIES_KIND_COMPONENTS:
            unknown = sorted(set(selector["components"]) - set(features))
            if unknown:
                raise ProspectiveCorpusV2Error(
                    f"{feature} names components outside the frozen inventory: "
                    f"{unknown}"
                )
            if not selector["components"]:
                raise ProspectiveCorpusV2Error(
                    f"{feature} is a composite with no component owners"
                )
        elif selector["series_kind"] == SERIES_KIND_DERIVED:
            if selector["series_id"] not in features:
                raise ProspectiveCorpusV2Error(
                    f"{feature} reads a derived series that is not a frozen feature"
                )
        elif selector["series_id"] not in _SERIES_FAMILY:
            raise ProspectiveCorpusV2Error(
                f"{feature} reads an undeclared source series"
            )
        else:
            family = _SERIES_FAMILY[selector["series_id"]]
            declared = tuple(_v1._FEATURE_DEPENDENCIES[feature]["raw"])
            if family not in declared:
                raise ProspectiveCorpusV2Error(
                    f"{feature} reads {family}, which the certified parent does "
                    f"not list among its raw families {declared}"
                )
            for additional in selector["additional_series"]:
                if _SERIES_FAMILY[additional] not in declared:
                    raise ProspectiveCorpusV2Error(
                        f"{feature} reads an additional family the certified "
                        "parent does not declare"
                    )
    if parameters["vol_percentile_source_feature_id"] not in features:
        raise ProspectiveCorpusV2Error(
            "the volatility-percentile source feature left the frozen inventory"
        )


# ===========================================================================
# 5. deterministic owner-specific evidence selection and evaluability
# ===========================================================================
#
# The audit's precise complaint about V1 was that a manifest which simply *lists*
# its own references cannot expose an omission: the list is self-consistent
# whatever it leaves out.  The answer is a second, independent derivation.  The
# selector below recomputes the *expected* evidence set for one owner at one slot
# from the evidence store alone, never reading the manifest it is about to check.
# Equality of the two sets is then the completeness proof, and the owner's own
# predicate -- not a count, and not a Boolean anyone wrote down -- decides
# evaluability from the resolved records.


@dataclass(frozen=True)
class DecisionSlot:
    """The identity of one scientific decision slot."""

    slot_id: str
    cadence: str
    observation_time: datetime
    decision_time: datetime

    def as_record(self) -> dict[str, Any]:
        if self.cadence not in _v1.DECISION_CADENCES:
            raise ProspectiveCorpusV2Error(f"unknown cadence {self.cadence!r}")
        observation_time = _require_utc(self.observation_time, "observation_time")
        decision_time = _require_utc(self.decision_time, "decision_time")
        expected = _v1.decision_time_for(observation_time, self.cadence)
        if decision_time != expected:
            raise ProspectiveCorpusV2Error(
                "decision_time must be the certified parent's own derivation "
                f"{expected.isoformat()}, not {decision_time.isoformat()}"
            )
        if self.slot_id != slot_identity(self.cadence, observation_time):
            raise ProspectiveCorpusV2Error("slot_id is not the derived slot identity")
        return {
            "cadence": self.cadence,
            "decision_time": _isoformat(decision_time),
            "observation_time": _isoformat(observation_time),
            "slot_id": self.slot_id,
        }


SLOT_IDENTITY_DERIVATION = (
    "sha256 over canonical {cadence, observation_time, protocol_version}, the "
    "certified parent's own derivation shape from scheduled_decision_slots, "
    "with protocol_version bound to this corpus. Because the corpus version is "
    "part of the preimage, V2 slot identities are a new identity space. That is "
    "correct and harmless here: V1 collected zero qualifying observations, so no "
    "slot identity is being reassigned, and the sufficiency layer's counts and "
    "minima are counts of units rather than of particular identity values."
)


def slot_identity(cadence: str, observation_time: datetime) -> str:
    """Derive a slot identity; a caller may never assert one.

    The identity is a pure function of the frozen cadence, the canonical
    observation instant and the corpus version, so two records claiming the same
    slot cannot disagree about which slot it is, and a wrong-slot substitution
    moves the identity.
    """

    if cadence not in _v1.DECISION_CADENCES:
        raise ProspectiveCorpusV2Error(f"unknown cadence {cadence!r}")
    return _digest(
        {
            "cadence": cadence,
            "observation_time": _isoformat(_require_utc(observation_time, "t")),
            "protocol_version": PROTOCOL_VERSION,
        }
    )


def decision_slot(cadence: str, observation_time: datetime) -> DecisionSlot:
    """Build one slot from the certified parent's own cadence derivation."""

    observation_time = _require_utc(observation_time, "observation_time")
    return DecisionSlot(
        slot_id=slot_identity(cadence, observation_time),
        cadence=cadence,
        observation_time=observation_time,
        decision_time=_v1.decision_time_for(observation_time, cadence),
    )


# ---------------------------------------------------------------------------
# 5a. point-in-time resolution
# ---------------------------------------------------------------------------

PIT_REVISION_RULE = (
    "For each observation_time, the qualifying record is the highest revision "
    "whose available_at does not exceed decision_time. A later revision that "
    "became available after the decision is excluded, never spliced in, and "
    "never silently replaces the revision the decision actually saw."
)


def _series_records(
    store: EvidenceStore,
    *,
    series_kind: str,
    series_id: str,
    cadence: str,
) -> tuple[dict[str, Any], ...]:
    kind = (
        DERIVED_FEATURE_KIND
        if series_kind == SERIES_KIND_DERIVED
        else SOURCE_OBSERVATION_KIND
    )
    key = "feature" if kind == DERIVED_FEATURE_KIND else "series_id"
    return tuple(
        record
        for record in store.of_kind(kind)
        if record[key] == series_id and record["cadence"] == cadence
    )


def _resolve_point_in_time(
    records: Iterable[Mapping[str, Any]],
    *,
    decision_time: datetime,
) -> tuple[tuple[datetime, dict[str, Any]], ...]:
    """Return one PIT-valid record per observation_time, ordered in time."""

    best: dict[datetime, dict[str, Any]] = {}
    for record in records:
        available_at = _parse_utc(record[AVAILABLE_AT_FIELD], AVAILABLE_AT_FIELD)
        if available_at > decision_time:
            continue
        observation_time = _parse_utc(
            record[OBSERVATION_TIME_FIELD], OBSERVATION_TIME_FIELD
        )
        current = best.get(observation_time)
        if current is None or int(record["revision"]) > int(current["revision"]):
            best[observation_time] = dict(record)
        elif int(record["revision"]) == int(current["revision"]) and (
            record[DIGEST_FIELD] != current[DIGEST_FIELD]
        ):
            raise ReplayRefusedError(
                f"{DUPLICATE_POLICY}: two distinct records claim revision "
                f"{record['revision']} at {observation_time.isoformat()}"
            )
    return tuple(sorted(best.items(), key=lambda item: item[0]))


# ---------------------------------------------------------------------------
# 5b. the expected-set selector
# ---------------------------------------------------------------------------


def _grid_times(
    *, end: datetime, cadence: str, count: int
) -> tuple[datetime, ...]:
    interval = CADENCE_INTERVAL[cadence]
    return tuple(end - interval * offset for offset in reversed(range(count)))


def expected_owner_evidence(
    store: EvidenceStore,
    *,
    feature: str,
    slot: DecisionSlot,
    census: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Recompute one owner's expected evidence set from the store alone.

    This function never reads an owner-history manifest. That is the whole point:
    the manifest is checked against an independent derivation, so a manifest that
    quietly omits a qualifying observation, omits an adverse one the predicate
    needs, substitutes a wrong-slot or wrong-source record, or carries a
    future-available revision cannot agree with it.
    """

    census = census if census is not None else owner_evaluability_census()
    rows = census["rows"]
    if feature not in rows:
        raise ProspectiveCorpusV2Error(f"{feature} is not a censused owner")
    selector = rows[feature]["evidence_selector"]
    kind = selector["series_kind"]
    if kind == SERIES_KIND_COMPONENTS:
        return {
            "adverse_record_sha256s": [],
            "additional_record_sha256s": {},
            "component_owners": list(selector["components"]),
            "observation_record_sha256s": [],
            "series_kind": kind,
        }

    resolved = _resolve_point_in_time(
        _series_records(
            store,
            series_kind=kind,
            series_id=selector["series_id"],
            cadence=selector["cadence"],
        ),
        decision_time=slot.decision_time,
    )
    window_kind = selector["window_kind"]
    cadence = selector["cadence"]
    end = slot.observation_time

    if window_kind == WINDOW_HALF_OPEN_PRIOR:
        span = timedelta(days=int(selector["window_span_days"]))
        lower, upper = end - span, end
        chosen = [
            (moment, record)
            for moment, record in resolved
            if lower <= moment < upper
        ]
        if selector["current_observation_required"]:
            chosen += [
                (moment, record) for moment, record in resolved if moment == end
            ]
    elif window_kind == WINDOW_HALF_OPEN_TRAILING:
        span = timedelta(days=int(selector["window_span_days"]))
        chosen = [
            (moment, record)
            for moment, record in resolved
            if end - span < moment <= end
        ]
    elif window_kind == WINDOW_UNBOUNDED_TRAILING:
        chosen = [(moment, record) for moment, record in resolved if moment <= end]
    elif window_kind == WINDOW_PRIOR_OBSERVATIONS:
        required = int(selector["window_span_observations"])
        prior = [(moment, record) for moment, record in resolved if moment < end]
        chosen = prior[-required:] if required else []
        if selector["current_observation_required"]:
            chosen += [
                (moment, record) for moment, record in resolved if moment == end
            ]
    elif window_kind == WINDOW_CONTIGUOUS_SESSIONS:
        required = int(
            selector["window_span_observations"]
            if selector["window_span_observations"] is not None
            else selector["minimum_count"]
        )
        wanted = set(_grid_times(end=end, cadence=cadence, count=required))
        chosen = [
            (moment, record) for moment, record in resolved if moment in wanted
        ]
    elif window_kind == WINDOW_TRAILING_SESSION_COUNT:
        # A weekly session and an ETF publication day are calendar sessions, not
        # fixed offsets: the series itself declares its grid. The window is the
        # last ``count`` resolved observations at or before the slot, so removing
        # a record from the evidence store slides the window onto an older one
        # and the persisted manifest stops matching -- which is exactly the
        # detection the omission tests require.
        required = int(
            selector["window_span_observations"]
            if selector["window_span_observations"] is not None
            else selector["minimum_count"]
        )
        at_or_before = [
            (moment, record) for moment, record in resolved if moment <= end
        ]
        chosen = at_or_before[-required:] if required else []
    elif window_kind == WINDOW_EXACT_LOOKBACK:
        offset = CADENCE_INTERVAL[cadence] * int(selector["window_span_observations"])
        wanted = {end, end - offset}
        chosen = [
            (moment, record) for moment, record in resolved if moment in wanted
        ]
    elif window_kind == WINDOW_AT_OR_BEFORE_LOOKBACK:
        limit = end - timedelta(days=int(selector["window_span_days"]))
        before = [(moment, record) for moment, record in resolved if moment <= limit]
        chosen = before[-1:] + [
            (moment, record) for moment, record in resolved if moment == end
        ]
    elif window_kind == WINDOW_NONE:
        chosen = [(moment, record) for moment, record in resolved if moment == end]
    else:  # pragma: no cover - WINDOW_KINDS is exhaustive above
        raise ProspectiveCorpusV2Error(f"unhandled window kind {window_kind!r}")

    ordered = sorted(
        {record[DIGEST_FIELD]: (moment, record) for moment, record in chosen}.values(),
        key=lambda item: (item[0], item[1][DIGEST_FIELD]),
    )
    qualifying = [
        record[DIGEST_FIELD]
        for _, record in ordered
        if record["observation_status"] in QUALIFYING_OBSERVATION_STATUSES
    ]
    adverse = [
        record[DIGEST_FIELD]
        for _, record in ordered
        if record["observation_status"] in ADVERSE_OBSERVATION_STATUSES
    ]
    additional: dict[str, list[str]] = {}
    for series in selector["additional_series"]:
        aligned = _resolve_point_in_time(
            _series_records(
                store,
                series_kind=SERIES_KIND_SOURCE,
                series_id=series,
                cadence=_SERIES_CADENCE[series],
            ),
            decision_time=slot.decision_time,
        )
        additional[series] = [
            record[DIGEST_FIELD] for moment, record in aligned if moment == end
        ]
    return {
        "adverse_record_sha256s": adverse,
        "additional_record_sha256s": additional,
        "component_owners": [],
        "observation_record_sha256s": qualifying,
        "series_kind": kind,
    }


# ---------------------------------------------------------------------------
# 5c. the owner-specific evaluability predicates
# ---------------------------------------------------------------------------


def _observation_times(
    store: EvidenceStore, references: Iterable[str]
) -> tuple[datetime, ...]:
    return tuple(
        sorted(
            _parse_utc(store.get(ref)[OBSERVATION_TIME_FIELD], OBSERVATION_TIME_FIELD)
            for ref in references
        )
    )


def _all_strictly_positive(store: EvidenceStore, references: Iterable[str]) -> bool:
    for ref in references:
        record = store.get(ref)
        value = record.get("value")
        if value is None or _decimal(value, "value") <= 0:
            return False
    return True


def evaluate_owner_predicate(
    store: EvidenceStore,
    *,
    feature: str,
    slot: DecisionSlot,
    evidence: Mapping[str, Any],
    component_states: Mapping[str, str],
    census: Mapping[str, Any],
) -> dict[str, Any]:
    """Run one owner's own frozen evaluability predicate over resolved evidence.

    No Boolean substitutes for this. The result is derived from the records the
    selector resolved and, for a composite, from the components' own derived
    results -- never from a persisted ``warmup_history_complete`` or an
    ``upstream_initialization_complete`` field.
    """

    row = census["rows"][feature]
    selector = row["evidence_selector"]
    owner_class = row["owner_class"]
    qualifying = list(evidence["observation_record_sha256s"])
    adverse = list(evidence["adverse_record_sha256s"])
    reasons: set[str] = set()
    if adverse:
        reasons.add(REASON_ADVERSE_OBSERVATION)

    end = slot.observation_time
    cadence = selector["cadence"]
    minimum = selector["minimum_count"]
    observed = len(qualifying)
    required = minimum
    evaluable = True

    if owner_class in (CLASS_COMPONENT_CONJUNCTION, CLASS_DETERMINISTIC_INIT_SMOOTHING):
        components = tuple(selector["components"])
        required = len(components)
        observed = sum(
            1 for name in components if component_states.get(name) == EVALUABLE
        )
        missing = [
            name for name in components if component_states.get(name) != EVALUABLE
        ]
        if missing:
            evaluable = False
            reasons.add(REASON_UPSTREAM_NOT_EVALUABLE)
    elif owner_class == CLASS_PRIOR_WINDOW_MIN_COUNT_ELAPSED:
        span = timedelta(days=int(selector["window_span_days"]))
        times = _observation_times(store, qualifying)
        prior = [moment for moment in times if end - span <= moment < end]
        observed = len(prior)
        if observed < minimum:
            evaluable = False
            reasons.add(REASON_HISTORY_INCOMPLETE)
        if selector["current_observation_required"] and end not in times:
            evaluable = False
            reasons.add(REASON_CURRENT_OBSERVATION_MISSING)
    elif owner_class == CLASS_PRIOR_WINDOW_MIN_COUNT_OBSERVATIONS:
        times = _observation_times(store, qualifying)
        prior = [moment for moment in times if moment < end]
        observed = len(prior)
        if observed < minimum:
            evaluable = False
            reasons.add(REASON_HISTORY_INCOMPLETE)
        if selector["current_observation_required"] and end not in times:
            evaluable = False
            reasons.add(REASON_CURRENT_OBSERVATION_MISSING)
    elif owner_class == CLASS_TRAILING_WINDOW_AT_LEAST_ONE:
        if observed < minimum:
            evaluable = False
            reasons.add(REASON_REQUIRED_INPUT_MISSING)
    elif owner_class in (
        CLASS_CONTIGUOUS_SESSION_CLOSES,
        CLASS_DUAL_WINDOW_GROWTH_ZSCORE,
    ):
        count = int(
            selector["window_span_observations"]
            if selector["window_span_observations"] is not None
            else minimum
        )
        required = count
        wanted = _grid_times(end=end, cadence=cadence, count=count)
        times = set(_observation_times(store, qualifying))
        present = [moment for moment in wanted if moment in times]
        observed = len(present)
        if observed < count:
            evaluable = False
            reasons.add(REASON_CONTIGUITY_BROKEN)
        if row["strictly_positive_required"] and not _all_strictly_positive(
            store, qualifying
        ):
            evaluable = False
            reasons.add(REASON_NON_POSITIVE_OBSERVATION)
    elif owner_class in (CLASS_WEEKLY_SESSION_COUNT, CLASS_PUBLICATION_DAY_COUNT):
        count = int(
            selector["window_span_observations"]
            if selector["window_span_observations"] is not None
            else minimum
        )
        required = count
        times = _observation_times(store, qualifying)
        observed = len([moment for moment in times if moment <= end])
        if observed < count:
            evaluable = False
            reasons.add(REASON_HISTORY_INCOMPLETE)
        if selector["current_observation_required"] and end not in set(times):
            evaluable = False
            reasons.add(REASON_CURRENT_OBSERVATION_MISSING)
    elif owner_class == CLASS_EXACT_LOOKBACK_PAIR:
        offset = CADENCE_INTERVAL[cadence] * int(selector["window_span_observations"])
        times = set(_observation_times(store, qualifying))
        required = 2
        observed = len({end, end - offset} & times)
        if end not in times:
            evaluable = False
            reasons.add(REASON_CURRENT_OBSERVATION_MISSING)
        if end - offset not in times:
            evaluable = False
            reasons.add(REASON_LOOKBACK_OBSERVATION_MISSING)
    elif owner_class == CLASS_AT_OR_BEFORE_LOOKBACK_PAIR:
        limit = end - timedelta(days=int(selector["window_span_days"]))
        times = _observation_times(store, qualifying)
        required = 2
        has_current = end in set(times)
        has_prior = any(moment <= limit for moment in times)
        observed = int(has_current) + int(has_prior)
        if not has_current:
            evaluable = False
            reasons.add(REASON_CURRENT_OBSERVATION_MISSING)
        if not has_prior:
            evaluable = False
            reasons.add(REASON_LOOKBACK_OBSERVATION_MISSING)
    elif owner_class == CLASS_CURRENT_VECTOR_ONLY:
        times = set(_observation_times(store, qualifying))
        required = 1 + len(selector["additional_series"])
        observed = int(end in times)
        if end not in times:
            evaluable = False
            reasons.add(REASON_CURRENT_OBSERVATION_MISSING)
        for series in selector["additional_series"]:
            aligned = evidence["additional_record_sha256s"].get(series) or []
            usable = [
                ref
                for ref in aligned
                if store.get(ref)["observation_status"]
                in QUALIFYING_OBSERVATION_STATUSES
            ]
            observed += int(bool(usable))
            if not usable:
                evaluable = False
                reasons.add(REASON_REQUIRED_INPUT_MISSING)
    else:  # pragma: no cover - OWNER_CLASSES is exhaustive above
        raise ProspectiveCorpusV2Error(f"unhandled owner class {owner_class!r}")

    if owner_class not in (
        CLASS_COMPONENT_CONJUNCTION,
        CLASS_DETERMINISTIC_INIT_SMOOTHING,
    ):
        for name in selector["components"]:
            if component_states.get(name) != EVALUABLE:
                evaluable = False
                reasons.add(REASON_UPSTREAM_NOT_EVALUABLE)

    return {
        "evaluability_state": EVALUABLE if evaluable else NOT_EVALUABLE,
        "observed_count": observed,
        "owner_class": owner_class,
        "reason_codes": sorted(reasons),
        "required_count": required,
    }


def _owner_dependency_order(census: Mapping[str, Any]) -> tuple[str, ...]:
    """Topologically order the censused owners so components resolve first."""

    rows = census["rows"]
    ordered: list[str] = []
    seen: set[str] = set()
    visiting: set[str] = set()

    def visit(feature: str) -> None:
        if feature in seen:
            return
        if feature in visiting:
            raise ProspectiveCorpusV2Error(
                f"the owner census contains a dependency cycle at {feature}"
            )
        visiting.add(feature)
        selector = rows[feature]["evidence_selector"]
        for component in selector["components"]:
            visit(component)
        if selector["series_kind"] == SERIES_KIND_DERIVED:
            visit(selector["series_id"])
        visiting.discard(feature)
        seen.add(feature)
        ordered.append(feature)

    for feature in sorted(rows):
        visit(feature)
    return tuple(ordered)


# ===========================================================================
# 6. PROSPECTIVE_OWNER_HISTORY_MANIFEST_V2
# ===========================================================================

OWNER_HISTORY_MANIFEST_VERSION = OWNER_HISTORY_MANIFEST_KIND
OWNER_HISTORY_MANIFEST_FIELDS = (
    "additional_record_sha256s",
    "adverse_record_sha256s",
    "cadence",
    CORPUS_BINDING_FIELD,
    "component_manifest_sha256s",
    "decision_time",
    "evidence_selector",
    "observation_record_sha256s",
    "observation_time",
    "owner_class",
    "owner_contract",
    "owner_contract_sha256",
    "owner_id",
    "pit_selection_semantics",
    RECORD_KIND_FIELD,
    "required_cadence",
    SCHEMA_VERSION_FIELD,
    "series_identity",
    "slot_id",
)

OWNER_HISTORY_MANIFEST_CONCLUSION_FIELDS_REFUSED = (
    "comparability",
    "evaluability_state",
    "quality_state",
    "universe_member",
    "upstream_initialization_complete",
    "warmup_history_complete",
)


def owner_contract_sha256(feature: str, census: Mapping[str, Any]) -> str:
    """Hash one owner's frozen contract row.

    Binding the row rather than the owner's name means a changed window, a
    changed minimum, a changed selector or a changed missing-data behavior all
    move the manifest identity.
    """

    if feature not in census["rows"]:
        raise ProspectiveCorpusV2Error(f"{feature} is not a censused owner")
    return _digest({"owner_id": feature, "row": census["rows"][feature]})


def build_owner_history_manifest(
    store: EvidenceStore,
    *,
    feature: str,
    slot: DecisionSlot,
    corpus_sha256: str,
    component_manifest_sha256s: Mapping[str, str] | None = None,
    census: Mapping[str, Any] | None = None,
    evidence: Mapping[str, Any] | None = None,
) -> str:
    """Persist one owner's complete history manifest for one slot."""

    census = census if census is not None else owner_evaluability_census()
    row = census["rows"][feature]
    selector = row["evidence_selector"]
    evidence = (
        evidence
        if evidence is not None
        else expected_owner_evidence(store, feature=feature, slot=slot, census=census)
    )
    components = dict(component_manifest_sha256s or {})
    declared = tuple(selector["components"])
    if sorted(components) != sorted(declared):
        raise ProspectiveCorpusV2Error(
            f"{feature} requires component manifests for {sorted(declared)}"
        )
    payload = {
        "additional_record_sha256s": {
            series: list(refs)
            for series, refs in sorted(evidence["additional_record_sha256s"].items())
        },
        "adverse_record_sha256s": list(evidence["adverse_record_sha256s"]),
        "cadence": slot.cadence,
        CORPUS_BINDING_FIELD: _require_sha256(corpus_sha256, CORPUS_BINDING_FIELD),
        "component_manifest_sha256s": {
            name: _require_sha256(components[name], name) for name in sorted(components)
        },
        "decision_time": _isoformat(slot.decision_time),
        "evidence_selector": selector,
        "observation_record_sha256s": list(evidence["observation_record_sha256s"]),
        "observation_time": _isoformat(slot.observation_time),
        "owner_class": row["owner_class"],
        "owner_contract": row["owner_contract"],
        "owner_contract_sha256": owner_contract_sha256(feature, census),
        "owner_id": feature,
        "pit_selection_semantics": {
            "pit_policy_version": PIT_POLICY_VERSION,
            "pit_rule": PIT_RULE,
            "revision_rule": PIT_REVISION_RULE,
        },
        RECORD_KIND_FIELD: OWNER_HISTORY_MANIFEST_KIND,
        "required_cadence": selector["cadence"],
        SCHEMA_VERSION_FIELD: RECORD_SCHEMA_VERSIONS[OWNER_HISTORY_MANIFEST_KIND],
        "series_identity": {
            "series_family": selector["series_family"],
            "series_id": selector["series_id"],
            "series_kind": selector["series_kind"],
        },
        "slot_id": slot.slot_id,
    }
    if sorted(payload) != sorted(OWNER_HISTORY_MANIFEST_FIELDS):
        raise ProspectiveCorpusV2Error(
            "the owner-history manifest schema is strict and did not match"
        )
    return store.put(payload)


def replay_owner_history_manifest(
    store: EvidenceStore,
    *,
    manifest_sha256: str,
    slot: DecisionSlot,
    corpus_sha256: str,
    component_states: Mapping[str, str] | None = None,
    census: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify one owner-history manifest and derive its evaluability result.

    Refuses -- it does not return a degraded answer -- when any required
    reference is missing, any referenced record fails to validate, any identity,
    cadence or window disagrees, a mandatory record is omitted, an extraneous
    wrong-slot record is substituted, or a PIT constraint is violated.
    """

    census = census if census is not None else owner_evaluability_census()
    manifest = store.get(manifest_sha256, expected_kind=OWNER_HISTORY_MANIFEST_KIND)
    feature = manifest["owner_id"]
    if feature not in census["rows"]:
        raise ReplayRefusedError(f"{feature} is not a censused owner")
    row = census["rows"][feature]

    for field in OWNER_HISTORY_MANIFEST_CONCLUSION_FIELDS_REFUSED:
        if field in manifest:
            raise ReplayRefusedError(
                f"an owner-history manifest may not carry the conclusion {field}"
            )
    if manifest[CORPUS_BINDING_FIELD] != corpus_sha256:
        raise ReplayRefusedError("the manifest binds a different certified corpus")
    if manifest["slot_id"] != slot.slot_id:
        raise ReplayRefusedError("the manifest belongs to another slot")
    if manifest["cadence"] != slot.cadence:
        raise ReplayRefusedError("the manifest declares another cadence")
    if _parse_utc(manifest["decision_time"], "decision_time") != slot.decision_time:
        raise ReplayRefusedError("the manifest declares another decision time")
    if (
        _parse_utc(manifest["observation_time"], "observation_time")
        != slot.observation_time
    ):
        raise ReplayRefusedError("the manifest declares another observation time")
    if manifest["owner_contract"] != row["owner_contract"]:
        raise ReplayRefusedError("the manifest binds another owner contract")
    if manifest["owner_contract_sha256"] != owner_contract_sha256(feature, census):
        raise ReplayRefusedError("the owner contract hash does not reproduce")
    if manifest["owner_class"] != row["owner_class"]:
        raise ReplayRefusedError("the manifest declares another owner class")
    if manifest["evidence_selector"] != row["evidence_selector"]:
        raise ReplayRefusedError("the manifest declares another evidence selector")
    if manifest["required_cadence"] != row["evidence_selector"]["cadence"]:
        raise ReplayRefusedError("the manifest declares another required cadence")

    expected = expected_owner_evidence(
        store, feature=feature, slot=slot, census=census
    )
    if list(manifest["observation_record_sha256s"]) != list(
        expected["observation_record_sha256s"]
    ):
        raise ReplayRefusedError(
            f"{feature}: the persisted qualifying history does not equal the "
            "expected owner evidence set recomputed from the evidence store"
        )
    if list(manifest["adverse_record_sha256s"]) != list(
        expected["adverse_record_sha256s"]
    ):
        raise ReplayRefusedError(
            f"{feature}: the persisted adverse history does not equal the "
            "expected owner evidence set recomputed from the evidence store"
        )
    persisted_additional = {
        series: list(refs)
        for series, refs in manifest["additional_record_sha256s"].items()
    }
    expected_additional = {
        series: list(refs)
        for series, refs in expected["additional_record_sha256s"].items()
    }
    if persisted_additional != expected_additional:
        raise ReplayRefusedError(
            f"{feature}: the persisted aligned-input references do not equal the "
            "expected set"
        )

    resolved_states = dict(component_states or {})
    declared_components = tuple(row["evidence_selector"]["components"])
    if sorted(manifest["component_manifest_sha256s"]) != sorted(declared_components):
        raise ReplayRefusedError(
            f"{feature}: the component manifest set does not match the census"
        )
    for name, child_sha in sorted(manifest["component_manifest_sha256s"].items()):
        child = replay_owner_history_manifest(
            store,
            manifest_sha256=child_sha,
            slot=slot,
            corpus_sha256=corpus_sha256,
            component_states=resolved_states,
            census=census,
        )
        if child["owner_id"] != name:
            raise ReplayRefusedError(
                f"{feature}: component manifest {name} resolves to "
                f"{child['owner_id']}"
            )
        resolved_states[name] = child["evaluability_state"]

    for reference in (
        list(manifest["observation_record_sha256s"])
        + list(manifest["adverse_record_sha256s"])
        + [ref for refs in persisted_additional.values() for ref in refs]
    ):
        record = store.get(reference)
        if record[RECORD_KIND_FIELD] not in (
            SOURCE_OBSERVATION_KIND,
            DERIVED_FEATURE_KIND,
        ):
            raise ReplayRefusedError(
                "an owner-history manifest may reference only source or derived "
                "observation records"
            )
        if _parse_utc(record[AVAILABLE_AT_FIELD], AVAILABLE_AT_FIELD) > (
            slot.decision_time
        ):
            raise ReplayRefusedError(
                "a future-available observation cannot enter a point-in-time "
                "history"
            )

    result = evaluate_owner_predicate(
        store,
        feature=feature,
        slot=slot,
        evidence=expected,
        component_states=resolved_states,
        census=census,
    )
    return {
        **result,
        "manifest_sha256": manifest_sha256,
        "owner_id": feature,
        "slot_id": slot.slot_id,
    }


# ===========================================================================
# 7. warmup is derived, never asserted
# ===========================================================================
#
# V1's ``warmup_history_complete`` Boolean stops being scientific authority in
# V2.  It may be retained only as a cached projection, and a cached value that
# disagrees with the replay refuses rather than winning.

WARMUP_STATE_COMPLETE = _v1.warmup_history_contract()["state_name"]
WARMUP_STATE_INCOMPLETE = "WARMUP_HISTORY_INCOMPLETE"
WARMUP_STATES = (WARMUP_STATE_COMPLETE, WARMUP_STATE_INCOMPLETE)

WARMUP_AUTHORITY_RULE = (
    "Authoritative warmup state is obtained by resolving each required owner's "
    "history manifest, resolving every referenced source and derived record, "
    "running that owner's own frozen evaluability predicate, and combining the "
    "results under the frozen decision-evaluability contract. No "
    "warmup_history_complete Boolean, no upstream_initialization_complete flag "
    "and no governance-authored conclusion may substitute for that replay."
)
CACHED_WARMUP_ROLE = "NON_AUTHORITATIVE_CACHED_DERIVED_PROJECTION"
CACHED_WARMUP_MISMATCH_BEHAVIOR = "REFUSE"

DECISION_EVALUABILITY_VERSION = "PROSPECTIVE_DECISION_EVALUABILITY_CONTRACT_V2"
COMBINATION_RULE = (
    "A slot's warmup/evaluability state is COMPLETE only when every owner the "
    "consuming decision owner requires at that cadence is independently "
    "EVALUABLE under its own predicate. The combination is a conjunction over "
    "heterogeneous owner results; it is never a count, never an elapsed-time "
    "comparison, and never a shortcut through one composite."
)

STOP_CADENCE_FEATURE_OWNERS_RATIONALE = (
    "The frozen stop-event classifier "
    f"{_v1.STOP_EVENT_CLASSIFIER_OWNER} consumes only the required providers' "
    "raw hourly observations and the control track's replayed active stop; its "
    "input contract names no member of INITIAL_FEATURE_NAMES. The hourly "
    "cadence therefore requires no frozen feature owner, and its evidence "
    "closure is the stop-event and portfolio-transition closure instead. This "
    "is stated rather than left implicit, and it is verified against the "
    "classifier's own input fields on every build."
)


def _stop_slot_input_fields() -> tuple[str, ...]:
    return tuple(sorted(_v1.StopEvaluationSlot.__dataclass_fields__))


def required_owners_for_cadence(
    cadence: str, census: Mapping[str, Any] | None = None
) -> tuple[str, ...]:
    """Return the frozen feature owners a cadence's decision owner requires."""

    census = census if census is not None else owner_evaluability_census()
    if cadence not in _v1.DECISION_CADENCES:
        raise ProspectiveCorpusV2Error(f"unknown cadence {cadence!r}")
    if cadence == _v1.STRATEGY_DAILY_CADENCE:
        return tuple(sorted(census["rows"]))
    features = set(census["rows"])
    overlap = sorted(features & set(_stop_slot_input_fields()))
    if overlap:  # pragma: no cover - the classifier contract forbids this
        raise ProspectiveCorpusV2Error(
            "the stop-event classifier now names frozen feature owners: "
            f"{overlap}; the cadence owner set must be re-derived"
        )
    return ()


def decision_evaluability_contract() -> dict[str, Any]:
    """Freeze how owner-specific results combine into one slot's warmup state."""

    census = owner_evaluability_census()
    payload = {
        "cached_warmup_mismatch_behavior": CACHED_WARMUP_MISMATCH_BEHAVIOR,
        "cached_warmup_role": CACHED_WARMUP_ROLE,
        "combination_rule": COMBINATION_RULE,
        "elapsed_time_is_an_evaluability_test": False,
        "evaluability_reason_codes": list(EVALUABILITY_REASON_CODES),
        "evaluability_states": list(EVALUABILITY_STATES),
        "owner_census_sha256": census["definition_sha256"],
        "parent_v1_evaluability_rule": _v1.WARMUP_EVALUABILITY_RULE,
        "protocol_version": PROTOCOL_VERSION,
        "replay_order": [
            "resolve the slot's owner-history manifest for every required owner",
            "recompute the expected owner evidence set from the evidence store",
            "refuse on any omission, substitution, identity or PIT violation",
            "resolve every referenced source and derived record",
            "run that owner's own frozen evaluability predicate",
            "combine the owner results under the frozen conjunction",
            "compare any cached projection and refuse on disagreement",
        ],
        "required_owners_by_cadence": {
            cadence: list(required_owners_for_cadence(cadence, census))
            for cadence in _v1.DECISION_CADENCES
        },
        "schema_version": DECISION_EVALUABILITY_VERSION,
        "stop_cadence_feature_owner_rationale": (
            STOP_CADENCE_FEATURE_OWNERS_RATIONALE
        ),
        "stop_event_classifier_input_fields": list(_stop_slot_input_fields()),
        "stop_event_classifier_owner": _v1.STOP_EVENT_CLASSIFIER_OWNER,
        "warmup_authority_rule": WARMUP_AUTHORITY_RULE,
        "warmup_boolean_is_authoritative": False,
        "warmup_states": list(WARMUP_STATES),
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def build_slot_owner_history_graph(
    store: EvidenceStore,
    *,
    slot: DecisionSlot,
    corpus_sha256: str,
    census: Mapping[str, Any] | None = None,
    features: Sequence[str] | None = None,
) -> dict[str, str]:
    """Persist the complete owner-history manifest graph for one slot."""

    census = census if census is not None else owner_evaluability_census()
    wanted = (
        tuple(features)
        if features is not None
        else required_owners_for_cadence(slot.cadence, census)
    )
    needed: set[str] = set()

    def expand(feature: str) -> None:
        if feature in needed:
            return
        needed.add(feature)
        selector = census["rows"][feature]["evidence_selector"]
        for component in selector["components"]:
            expand(component)

    for feature in wanted:
        expand(feature)

    manifests: dict[str, str] = {}
    for feature in _owner_dependency_order(census):
        if feature not in needed:
            continue
        selector = census["rows"][feature]["evidence_selector"]
        manifests[feature] = build_owner_history_manifest(
            store,
            feature=feature,
            slot=slot,
            corpus_sha256=corpus_sha256,
            component_manifest_sha256s={
                name: manifests[name] for name in selector["components"]
            },
            census=census,
        )
    return manifests


def replay_decision_evaluability(
    store: EvidenceStore,
    *,
    slot: DecisionSlot,
    corpus_sha256: str,
    owner_manifest_sha256s: Mapping[str, str],
    census: Mapping[str, Any] | None = None,
    cached_warmup_state: str | None = None,
) -> dict[str, Any]:
    """Derive one slot's authoritative warmup/evaluability state by replay."""

    census = census if census is not None else owner_evaluability_census()
    required = required_owners_for_cadence(slot.cadence, census)
    missing = sorted(set(required) - set(owner_manifest_sha256s))
    if missing:
        raise ReplayRefusedError(
            f"the slot omits owner-history manifests for {missing}"
        )
    states: dict[str, str] = {}
    results: dict[str, dict[str, Any]] = {}
    for feature in _owner_dependency_order(census):
        reference = owner_manifest_sha256s.get(feature)
        if reference is None:
            continue
        result = replay_owner_history_manifest(
            store,
            manifest_sha256=reference,
            slot=slot,
            corpus_sha256=corpus_sha256,
            component_states=states,
            census=census,
        )
        states[feature] = result["evaluability_state"]
        results[feature] = result
    unresolved = sorted(set(owner_manifest_sha256s) - set(results))
    if unresolved:  # pragma: no cover - defensive
        raise ReplayRefusedError(
            f"the slot binds manifests for uncensused owners {unresolved}"
        )
    incomplete = sorted(
        feature for feature in required if states.get(feature) != EVALUABLE
    )
    derived_state = WARMUP_STATE_INCOMPLETE if incomplete else WARMUP_STATE_COMPLETE
    if cached_warmup_state is not None:
        if cached_warmup_state not in WARMUP_STATES:
            raise ReplayRefusedError("the cached warmup projection is not a warmup state")
        if cached_warmup_state != derived_state:
            raise ReplayRefusedError(
                "the cached warmup projection disagrees with the replayed "
                f"owner-specific result: cached={cached_warmup_state}, "
                f"replayed={derived_state}"
            )
    return {
        "cached_warmup_state": cached_warmup_state,
        "derived_warmup_state": derived_state,
        "not_evaluable_owners": incomplete,
        "owner_results": results,
        "owner_states": states,
        "required_owners": list(required),
        "slot_id": slot.slot_id,
    }


# ===========================================================================
# 8. synthetic evidence construction
# ===========================================================================
#
# Nothing below collects anything.  These builders exist so the replay closure
# can be *demonstrated* on a graph this module constructs itself, which is the
# only honest way to show a pre-data parent works: build a complete valid graph,
# then damage it one reference at a time and require the replay to refuse.

SYNTHETIC_EVIDENCE_ONLY = True
SYNTHETIC_EVIDENCE_RULE = (
    "Every record these builders produce is synthetic. No qualifying prospective "
    "observation is collected, no live capture starts, no real Stage-B numerator "
    "is inspected and no BTC-019 sealed data is opened."
)


def source_observation_record(
    *,
    corpus_sha256: str,
    series_id: str,
    observation_time: datetime,
    available_at: datetime,
    value: str | None,
    observation_status: str = OBSERVED_WITH_EVENTS,
    revision: int = 1,
    cadence: str | None = None,
    provider: str | None = None,
    source_evidence_sha256s: Sequence[str] = (),
) -> dict[str, Any]:
    """One immutable point-in-time source observation.

    ``value`` is an exact decimal *string*: a persisted scientific number must be
    invariant to the ambient ``Decimal`` context on both the write and the read,
    and a float repr is not. An unusable status carries no value at all rather
    than a zero, which is the certified parent's own missing-data rule.
    """

    if series_id not in _SERIES_FAMILY:
        raise ProspectiveCorpusV2Error(f"unknown series {series_id!r}")
    if observation_status not in OBSERVATION_STATUSES:
        raise ProspectiveCorpusV2Error(f"unknown status {observation_status!r}")
    if observation_status in ADVERSE_OBSERVATION_STATUSES and value is not None:
        raise ProspectiveCorpusV2Error(
            f"{MISSING_DATA_POLICY}: an unusable observation carries no value"
        )
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise ProspectiveCorpusV2Error("revision must be a positive integer")
    if value is not None:
        _decimal(value, "value")
    return {
        AVAILABLE_AT_FIELD: _isoformat(_require_utc(available_at, AVAILABLE_AT_FIELD)),
        "cadence": cadence if cadence is not None else _SERIES_CADENCE[series_id],
        CORPUS_BINDING_FIELD: _require_sha256(corpus_sha256, CORPUS_BINDING_FIELD),
        OBSERVATION_TIME_FIELD: _isoformat(
            _require_utc(observation_time, OBSERVATION_TIME_FIELD)
        ),
        "observation_status": observation_status,
        "provider": provider,
        RECORD_KIND_FIELD: SOURCE_OBSERVATION_KIND,
        "revision": revision,
        SCHEMA_VERSION_FIELD: RECORD_SCHEMA_VERSIONS[SOURCE_OBSERVATION_KIND],
        "series_family": _SERIES_FAMILY[series_id],
        "series_id": series_id,
        "source_evidence_sha256s": list(source_evidence_sha256s),
        "value": value,
    }


def derived_feature_record(
    *,
    corpus_sha256: str,
    feature: str,
    observation_time: datetime,
    available_at: datetime,
    value: str | None,
    observation_status: str = OBSERVED_WITH_EVENTS,
    revision: int = 1,
    cadence: str = CADENCE_DAILY,
    owner_history_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    """One derived feature result, itself point-in-time and content-addressed."""

    if feature not in _feature_matrix.INITIAL_FEATURE_NAMES:
        raise ProspectiveCorpusV2Error(f"{feature} is not a frozen feature")
    if observation_status not in OBSERVATION_STATUSES:
        raise ProspectiveCorpusV2Error(f"unknown status {observation_status!r}")
    if observation_status in ADVERSE_OBSERVATION_STATUSES and value is not None:
        raise ProspectiveCorpusV2Error(
            f"{MISSING_DATA_POLICY}: an unusable result carries no value"
        )
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise ProspectiveCorpusV2Error("revision must be a positive integer")
    if value is not None:
        _decimal(value, "value")
    return {
        AVAILABLE_AT_FIELD: _isoformat(_require_utc(available_at, AVAILABLE_AT_FIELD)),
        "cadence": cadence,
        CORPUS_BINDING_FIELD: _require_sha256(corpus_sha256, CORPUS_BINDING_FIELD),
        "feature": feature,
        OBSERVATION_TIME_FIELD: _isoformat(
            _require_utc(observation_time, OBSERVATION_TIME_FIELD)
        ),
        "observation_status": observation_status,
        "owner_contract": _EVALUABILITY_OWNER[feature],
        "owner_history_manifest_sha256": owner_history_manifest_sha256,
        RECORD_KIND_FIELD: DERIVED_FEATURE_KIND,
        "revision": revision,
        SCHEMA_VERSION_FIELD: RECORD_SCHEMA_VERSIONS[DERIVED_FEATURE_KIND],
        "value": value,
    }


def _required_history_depth(census: Mapping[str, Any]) -> dict[str, int]:
    """How deep each series must be seeded for a complete synthetic slot."""

    depth: dict[str, int] = {}
    for feature, row in census["rows"].items():
        selector = row["evidence_selector"]
        if selector["series_kind"] == SERIES_KIND_COMPONENTS:
            continue
        cadence = selector["cadence"]
        interval = CADENCE_INTERVAL[cadence]
        window_kind = selector["window_kind"]
        if window_kind == WINDOW_HALF_OPEN_PRIOR:
            span = timedelta(days=int(selector["window_span_days"]))
            needed = max(
                int(selector["minimum_count"]) + 1,
                0,
            )
            needed = min(needed, int(span / interval) + 1)
        elif window_kind == WINDOW_HALF_OPEN_TRAILING:
            needed = 1
        elif window_kind == WINDOW_UNBOUNDED_TRAILING:
            needed = 1
        elif window_kind == WINDOW_PRIOR_OBSERVATIONS:
            needed = int(selector["window_span_observations"]) + 1
        elif window_kind in (
            WINDOW_CONTIGUOUS_SESSIONS,
            WINDOW_TRAILING_SESSION_COUNT,
        ):
            needed = int(selector["window_span_observations"])
        elif window_kind == WINDOW_EXACT_LOOKBACK:
            needed = int(selector["window_span_observations"]) + 1
        elif window_kind == WINDOW_AT_OR_BEFORE_LOOKBACK:
            needed = int(selector["window_span_days"]) + 1
        else:
            needed = 1
        key = (
            selector["series_id"]
            if selector["series_kind"] == SERIES_KIND_SOURCE
            else f"DERIVED::{selector['series_id']}"
        )
        depth[key] = max(depth.get(key, 0), needed)
        for series in selector["additional_series"]:
            depth[series] = max(depth.get(series, 0), 1)
    return depth


def seed_complete_slot_evidence(
    store: EvidenceStore,
    *,
    slot: DecisionSlot,
    corpus_sha256: str,
    census: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Seed one slot's complete, valid, synthetic owner-history graph.

    Every observation is available strictly before the decision instant, so the
    point-in-time rule is satisfied by construction and a later test can violate
    it deliberately.
    """

    census = census if census is not None else owner_evaluability_census()
    depth = _required_history_depth(census)
    seeded: dict[str, dict[str, str]] = {}
    for key, count in sorted(depth.items()):
        derived = key.startswith("DERIVED::")
        series = key.split("::", 1)[1] if derived else key
        cadence = CADENCE_DAILY if derived else _SERIES_CADENCE[series]
        interval = CADENCE_INTERVAL[cadence]
        moments = tuple(
            slot.observation_time - interval * offset
            for offset in reversed(range(count))
        )
        refs: dict[str, str] = {}
        for index, moment in enumerate(moments, start=1):
            available_at = moment + interval
            if available_at > slot.decision_time:
                available_at = slot.decision_time
            payload = (
                derived_feature_record(
                    corpus_sha256=corpus_sha256,
                    feature=series,
                    observation_time=moment,
                    available_at=available_at,
                    value=str(index),
                    cadence=cadence,
                )
                if derived
                else source_observation_record(
                    corpus_sha256=corpus_sha256,
                    series_id=series,
                    observation_time=moment,
                    available_at=available_at,
                    value=str(index),
                )
            )
            refs[_isoformat(moment)] = store.put(payload)
        seeded[key] = refs
    return {"depth": depth, "records": seeded}


# ===========================================================================
# 9. the content-addressed acyclic portfolio transition graph
# ===========================================================================
#
# The audit's second blocker: ``prospective_portfolio_state`` bound only a
# ``prior_state_sha256`` digest of selected fields, and ``prospective_trade_action``
# bound a prior state but no result, so no resulting state could prove which
# predecessor and which action produced it, and neither the root opening
# transition nor active-stop membership could be traversed.
#
# V2 closes that with two record kinds and one direction of reference:
#
#     prior state  <---- transition ----  (prior_state_record_sha256)
#          ^                  ^
#          |                  |
#          +---- resulting state binds both ----+
#
# The transition never references the resulting state, so no hash cycle exists:
# a state's identity depends on the transition, which depends on the prior
# state, which depends on its own transition, down to a genesis whose
# predecessor and producing transition are both explicitly null.  The resulting
# state referencing its producing transition is what closes the replay chain.

STATE_KIND_GENESIS = "GENESIS"
STATE_KIND_DERIVED = "DERIVED"
STATE_KINDS = (STATE_KIND_DERIVED, STATE_KIND_GENESIS)

TRANSITION_CLASS_ENTER = "ENTER"
TRANSITION_CLASS_ADD = "ADD"
TRANSITION_CLASS_TRIM = "TRIM"
TRANSITION_CLASS_STOP_MOVE = "STOP_MOVE"
TRANSITION_CLASS_EXIT = "EXIT"
TRANSITION_CLASS_STATE_PRESERVING = "NO_ACTION_STATE_PRESERVING"
TRANSITION_CLASSES = (
    TRANSITION_CLASS_ADD,
    TRANSITION_CLASS_ENTER,
    TRANSITION_CLASS_EXIT,
    TRANSITION_CLASS_STATE_PRESERVING,
    TRANSITION_CLASS_STOP_MOVE,
    TRANSITION_CLASS_TRIM,
)

TRANSITION_CLASS_BY_EVENT: dict[str, str] = {
    _state_machine.ENTER: TRANSITION_CLASS_ENTER,
    _state_machine.ADD: TRANSITION_CLASS_ADD,
    _state_machine.TRIM: TRANSITION_CLASS_TRIM,
    _state_machine.STOP_MOVE: TRANSITION_CLASS_STOP_MOVE,
    _state_machine.EXIT: TRANSITION_CLASS_EXIT,
    _state_machine.OBSERVE: TRANSITION_CLASS_STATE_PRESERVING,
    _state_machine.HOLD: TRANSITION_CLASS_STATE_PRESERVING,
    _state_machine.ARM_ENTRY: TRANSITION_CLASS_STATE_PRESERVING,
    _state_machine.DISARM_ENTRY: TRANSITION_CLASS_STATE_PRESERVING,
    _state_machine.DEFEND: TRANSITION_CLASS_STATE_PRESERVING,
    _state_machine.RECOVER: TRANSITION_CLASS_STATE_PRESERVING,
    _state_machine.MISS: TRANSITION_CLASS_STATE_PRESERVING,
}

PORTFOLIO_TRANSITION_OWNER = "btc_predictor.portfolio.state_machine"
PORTFOLIO_TRANSITION_OWNER_VERSION = (
    _state_machine.POSITION_STATE_MACHINE_POLICY_VERSION
)
PORTFOLIO_TRANSITION_RECORD_OWNER_VERSION = (
    _state_machine.POSITION_TRANSITION_RECORD_VERSION
)
PORTFOLIO_SINGLE_STEP_REPLAY_OWNER = (
    "btc_predictor.portfolio.state_machine.apply_position_event"
)
PORTFOLIO_SNAPSHOT_REPLAY_OWNER = (
    "btc_predictor.portfolio.state_machine.restore_position_lifecycle"
)
ACCOUNT_OWNER = "btc_predictor.portfolio.account"
ACCOUNT_OWNER_VERSION = _account.PAPER_ACCOUNT_POLICY_VERSION
ACCOUNT_FEATURE_ID = _account.PAPER_ACCOUNT_FEATURE_ID

ACYCLICITY_RULE = (
    "A transition references its prior state and never its resulting state; a "
    "state references its prior state and its producing transition. Identity "
    "therefore flows strictly backwards in time to a genesis with both "
    "references null, and no content hash can contain itself."
)

# The authoritative state machine computes ``average_entry_price`` and every
# pro-rata trim quantity under the *ambient* Decimal context, and renders them
# with ``str``, so the persisted digit count of a post-TRIM tranche is a function
# of ``getcontext().prec``. A scientific record whose bytes move with an ambient
# setting is not deterministic evidence, so V2 pins the context -- and pins it to
# the interpreter default the state machine already runs under everywhere in this
# repository, so no byte any existing caller produces moves. The precision is
# read from the interpreter rather than restated, and the build refuses if that
# default ever changes underneath the contract.
OWNER_REPLAY_DECIMAL_PRECISION = _decimal_module.DefaultContext.prec
OWNER_REPLAY_DECIMAL_ROUNDING = _decimal_module.DefaultContext.rounding
_OWNER_CONTEXT = Context(
    prec=OWNER_REPLAY_DECIMAL_PRECISION,
    rounding=OWNER_REPLAY_DECIMAL_ROUNDING,
)
OWNER_REPLAY_CONTEXT_OWNERS = (
    ACCOUNT_OWNER,
    PORTFOLIO_TRANSITION_OWNER,
    "btc_predictor.risk.sizing",
)
PORTFOLIO_NUMERICAL_CONTEXT_RULE = (
    "None of the authoritative owners V2 invokes -- the position state machine, "
    "the paper account and the initial position sizer -- pins a Decimal "
    "context, so the persisted digit count of an average entry, a pro-rata trim "
    "quantity, an available-cash balance or a position notional follows "
    "getcontext().prec. Evidence whose bytes move with an ambient setting is not "
    "deterministic, so V2 constructs and replays every record that invokes one "
    "of those owners inside one pinned context, and pins it to the interpreter "
    "default those owners already run under throughout this repository "
    f"(precision {OWNER_REPLAY_DECIMAL_PRECISION}, rounding "
    f"{OWNER_REPLAY_DECIMAL_ROUNDING}). No owner, formula or economic meaning "
    "changes, no byte an existing caller produces moves, and persisted V2 "
    "evidence becomes invariant to whatever ambient context a future collector "
    "happens to set. The corpus statistic context of precision "
    f"{CORPUS_DECIMAL_PRECISION} governs the corpus's own arithmetic and is "
    "deliberately not imposed on owner code, because doing so would change the "
    "persisted strings those certified owners produce."
)

UNREALIZED_PNL_OWNER = "btc_predictor.portfolio.accounting"
UNREALIZED_PNL_BINDING_RULE = (
    "Unrealized profit and loss is bound by content-addressed reference to the "
    "accounting owner's own output and is never re-derived here. NAV is then "
    "obtained by invoking the existing PaperAccount.nav owner on the replayed "
    "account and the referenced unrealized value, and the replay refuses if the "
    "persisted NAV does not equal that invocation. V2 binds and re-invokes; it "
    "authors no portfolio economics."
)

ACCOUNT_OPERATIONS = (
    "apply_funding_cost",
    "archive",
    "charge_fee",
    "charge_funding",
    "settle_realized_pnl",
)


def _restore_paper_account(record: Mapping[str, Any]) -> _account.PaperAccount:
    """Rebuild a PaperAccount from its own record and prove the round trip.

    The account is a frozen dataclass whose ``as_record`` is the authority on its
    own shape, so restoration is reconstruct-then-compare -- the same
    self-proving pattern the lifecycle owner uses. Nothing about fees, funding or
    settlement is restated here.
    """

    source = dict(record)
    costs = source["costs"]
    account = _account.PaperAccount(
        feature_id=source["feature_id"],
        policy_version=source["policy_version"],
        account_name=source["account_name"],
        base_currency=source["base_currency"],
        starting_nav=_decimal(source["starting_nav"], "starting_nav"),
        cash=_decimal(source["cash"], "cash"),
        reserved_cash=_decimal(source["reserved_cash"], "reserved_cash"),
        realized_pnl=_decimal(source["realized_pnl"], "realized_pnl"),
        fees_paid=_decimal(source["fees_paid"], "fees_paid"),
        funding_paid=_decimal(source["funding_paid"], "funding_paid"),
        costs=_account.ExecutionCosts(
            policy_version=costs["policy_version"],
            fee_bps=_decimal(costs["fee_bps"], "fee_bps"),
            slippage_bps=_decimal(costs["slippage_bps"], "slippage_bps"),
            funding_cost_bps_per_day=_decimal(
                costs["funding_cost_bps_per_day"], "funding_cost_bps_per_day"
            ),
        ),
        status=source["status"],
        created_at=_parse_utc(source["created_at"], "created_at"),
        config_metadata=dict(source["config_metadata"]),
        reason_codes=tuple(source["reason_codes"]),
    )
    if account.as_record() != source:
        raise ReplayRefusedError("the persisted account does not reproduce")
    return account


def _apply_account_operations(
    account: _account.PaperAccount, operations: Sequence[Mapping[str, Any]]
) -> _account.PaperAccount:
    """Apply the transition's bound account operations through the owner itself."""

    for operation in operations:
        name = operation.get("operation")
        if name not in ACCOUNT_OPERATIONS:
            raise ReplayRefusedError(f"unknown account operation {name!r}")
        arguments = dict(operation.get("arguments") or {})
        if name == "charge_fee":
            account = account.charge_fee(_decimal(arguments["notional"], "notional"))
        elif name == "charge_funding":
            account = account.charge_funding(
                _decimal(arguments["notional"], "notional"),
                days=_decimal(arguments["days"], "days"),
                direction=arguments["direction"],
            )
        elif name == "apply_funding_cost":
            account = account.apply_funding_cost(
                _decimal(arguments["amount"], "amount")
            )
        elif name == "settle_realized_pnl":
            account = account.settle_realized_pnl(
                _decimal(arguments["amount"], "amount")
            )
        else:
            account = account.archive()
    return account


def _position_event_arguments(event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "event": event["event"],
        "event_time": _parse_utc(event["event_time"], "event_time"),
        "quantity": (
            _decimal(event["quantity"], "quantity")
            if event.get("quantity") is not None
            else None
        ),
        "price": (
            _decimal(event["price"], "price") if event.get("price") is not None else None
        ),
        "stop_price": (
            _decimal(event["stop_price"], "stop_price")
            if event.get("stop_price") is not None
            else None
        ),
        "reason_codes": tuple(event.get("reason_codes") or ()),
        "source_feature_id": event.get("source_feature_id"),
        "source_record_id": event.get("source_record_id"),
    }


def position_event(
    *,
    event: str,
    event_time: datetime,
    quantity: str | None = None,
    price: str | None = None,
    stop_price: str | None = None,
    reason_codes: Sequence[str] = (),
    source_feature_id: str | None = None,
    source_record_id: str | None = None,
) -> dict[str, Any]:
    """One position event, normalized so an omitted optional key cannot move a hash.

    ``PositionTransition.as_record`` omits ``source_feature_id`` and
    ``source_record_id`` entirely when the first is None, so two economically
    identical transitions would otherwise hash differently depending on how they
    were produced. V2's own transition evidence always carries both keys, with an
    explicit null.
    """

    if event not in _state_machine.POSITION_EVENTS:
        raise ProspectiveCorpusV2Error(f"unknown position event {event!r}")
    for value, name in ((quantity, "quantity"), (price, "price"), (stop_price, "stop_price")):
        if value is not None:
            _decimal(value, name)
    return {
        "event": event,
        "event_time": _isoformat(_require_utc(event_time, "event_time")),
        "price": price,
        "quantity": quantity,
        "reason_codes": list(reason_codes),
        "source_feature_id": source_feature_id,
        "source_record_id": source_record_id,
        "stop_price": stop_price,
    }


PORTFOLIO_STATE_FIELDS = (
    "account_record",
    "as_of",
    CORPUS_BINDING_FIELD,
    "decision_time",
    "nav",
    "nav_unrealized_pnl",
    "nav_unrealized_pnl_evidence_sha256",
    "nav_unrealized_pnl_owner",
    "position_lifecycle_record",
    "prior_state_record_sha256",
    "producing_transition_record_sha256",
    RECORD_KIND_FIELD,
    SCHEMA_VERSION_FIELD,
    "slot_id",
    "state_kind",
    "track",
)

PORTFOLIO_TRANSITION_FIELDS = (
    "account_operations",
    "action_evidence_record_sha256",
    CORPUS_BINDING_FIELD,
    "decision_time",
    "nav_unrealized_pnl",
    "nav_unrealized_pnl_evidence_sha256",
    "new_lifecycle_parameters",
    "opens_new_position_lifecycle",
    "position_events",
    "prior_state_record_sha256",
    RECORD_KIND_FIELD,
    "risk_evidence_record_sha256",
    SCHEMA_VERSION_FIELD,
    "slot_id",
    "stop_evidence_record_sha256",
    "track",
    "transition_class",
    "transition_owner",
    "transition_owner_version",
    "transition_type",
)

GENESIS_CONTRACT = {
    "distinguishable_from_missing_predecessor": True,
    "prior_state_record_sha256": None,
    "producing_transition_record_sha256": None,
    "rule": (
        "Exactly one state per track may declare state_kind GENESIS, and only a "
        "GENESIS state may carry a null predecessor or a null producing "
        "transition. Every later state must bind both. A null predecessor on a "
        "DERIVED state is refused, so 'no predecessor recorded' and 'this is the "
        "beginning' can never be confused."
    ),
    "state_kind": STATE_KIND_GENESIS,
}


def build_portfolio_genesis_state(
    store: EvidenceStore,
    *,
    track: str,
    corpus_sha256: str,
    slot: DecisionSlot,
    symbol: str,
    direction: str = _state_machine.LONG_DIRECTION,
    initial_state: str = _state_machine.WATCH,
    account_record: Mapping[str, Any],
    config_metadata: Mapping[str, str] | None = None,
) -> str:
    """Persist one track's explicit flat genesis state."""

    if track not in _v1.PORTFOLIO_TRACKS:
        raise ProspectiveCorpusV2Error(f"unknown track {track!r}")
    with _decimal_module.localcontext(_OWNER_CONTEXT):
        lifecycle = _state_machine.start_position_lifecycle(
            symbol=symbol,
            direction=direction,
            state=initial_state,
            config_metadata=config_metadata,
        )
        account = _restore_paper_account(account_record)
        nav = account.nav(unrealized_pnl=Decimal("0"))
        payload = {
            "account_record": account.as_record(),
            "as_of": _isoformat(slot.decision_time),
            CORPUS_BINDING_FIELD: _require_sha256(
                corpus_sha256, CORPUS_BINDING_FIELD
            ),
            "decision_time": _isoformat(slot.decision_time),
            "nav": str(nav),
            "nav_unrealized_pnl": "0",
            "nav_unrealized_pnl_evidence_sha256": None,
            "nav_unrealized_pnl_owner": UNREALIZED_PNL_OWNER,
            "position_lifecycle_record": lifecycle.as_record(),
            "prior_state_record_sha256": None,
            "producing_transition_record_sha256": None,
            RECORD_KIND_FIELD: PORTFOLIO_STATE_KIND,
            SCHEMA_VERSION_FIELD: RECORD_SCHEMA_VERSIONS[PORTFOLIO_STATE_KIND],
            "slot_id": slot.slot_id,
            "state_kind": STATE_KIND_GENESIS,
            "track": track,
        }
    if sorted(payload) != sorted(PORTFOLIO_STATE_FIELDS):
        raise ProspectiveCorpusV2Error("the portfolio state schema is strict")
    return store.put(payload)


def build_portfolio_transition(
    store: EvidenceStore,
    *,
    track: str,
    corpus_sha256: str,
    slot: DecisionSlot,
    prior_state_record_sha256: str,
    position_events: Sequence[Mapping[str, Any]],
    action_evidence_record_sha256: str,
    opens_new_position_lifecycle: bool = False,
    new_lifecycle_parameters: Mapping[str, Any] | None = None,
    account_operations: Sequence[Mapping[str, Any]] = (),
    stop_evidence_record_sha256: str | None = None,
    risk_evidence_record_sha256: str | None = None,
    nav_unrealized_pnl: str = "0",
    nav_unrealized_pnl_evidence_sha256: str | None = None,
) -> str:
    """Persist one transition, binding its exact predecessor and action evidence."""

    if track not in _v1.PORTFOLIO_TRACKS:
        raise ProspectiveCorpusV2Error(f"unknown track {track!r}")
    events = [dict(event) for event in position_events]
    if not events:
        raise ProspectiveCorpusV2Error("a transition applies at least one event")
    transition_type = events[-1]["event"]
    if transition_type not in _state_machine.POSITION_EVENTS:
        raise ProspectiveCorpusV2Error(f"unknown event {transition_type!r}")
    transition_class = TRANSITION_CLASS_BY_EVENT[transition_type]
    if transition_class in (
        TRANSITION_CLASS_ENTER,
        TRANSITION_CLASS_STOP_MOVE,
    ) and stop_evidence_record_sha256 is None:
        raise ProspectiveCorpusV2Error(
            f"a {transition_class} transition must bind its stop evidence"
        )
    if transition_class in (
        TRANSITION_CLASS_ENTER,
        TRANSITION_CLASS_ADD,
    ) and risk_evidence_record_sha256 is None:
        raise ProspectiveCorpusV2Error(
            f"a {transition_class} transition must bind its risk evidence"
        )
    if opens_new_position_lifecycle and not new_lifecycle_parameters:
        raise ProspectiveCorpusV2Error(
            "opening a new position lifecycle requires its frozen parameters"
        )
    if new_lifecycle_parameters and not opens_new_position_lifecycle:
        raise ProspectiveCorpusV2Error(
            "new lifecycle parameters require opens_new_position_lifecycle"
        )
    _decimal(nav_unrealized_pnl, "nav_unrealized_pnl")
    payload = {
        "account_operations": [dict(item) for item in account_operations],
        "action_evidence_record_sha256": _require_sha256(
            action_evidence_record_sha256, "action_evidence_record_sha256"
        ),
        CORPUS_BINDING_FIELD: _require_sha256(corpus_sha256, CORPUS_BINDING_FIELD),
        "decision_time": _isoformat(slot.decision_time),
        "nav_unrealized_pnl": nav_unrealized_pnl,
        "nav_unrealized_pnl_evidence_sha256": nav_unrealized_pnl_evidence_sha256,
        "new_lifecycle_parameters": (
            dict(new_lifecycle_parameters) if new_lifecycle_parameters else None
        ),
        "opens_new_position_lifecycle": bool(opens_new_position_lifecycle),
        "position_events": events,
        "prior_state_record_sha256": _require_sha256(
            prior_state_record_sha256, "prior_state_record_sha256"
        ),
        RECORD_KIND_FIELD: PORTFOLIO_TRANSITION_KIND,
        "risk_evidence_record_sha256": risk_evidence_record_sha256,
        SCHEMA_VERSION_FIELD: RECORD_SCHEMA_VERSIONS[PORTFOLIO_TRANSITION_KIND],
        "slot_id": slot.slot_id,
        "stop_evidence_record_sha256": stop_evidence_record_sha256,
        "track": track,
        "transition_class": transition_class,
        "transition_owner": PORTFOLIO_TRANSITION_OWNER,
        "transition_owner_version": PORTFOLIO_TRANSITION_OWNER_VERSION,
        "transition_type": transition_type,
    }
    if sorted(payload) != sorted(PORTFOLIO_TRANSITION_FIELDS):
        raise ProspectiveCorpusV2Error("the portfolio transition schema is strict")
    return store.put(payload)


def _apply_transition(
    store: EvidenceStore, prior: Mapping[str, Any], transition: Mapping[str, Any]
) -> dict[str, Any]:
    """Run the existing owners over prior state plus transition."""

    with _decimal_module.localcontext(_OWNER_CONTEXT):
        if transition["opens_new_position_lifecycle"]:
            prior_lifecycle = _state_machine.restore_position_lifecycle(
                prior["position_lifecycle_record"]
            )
            if not prior_lifecycle.is_terminal:
                raise ReplayRefusedError(
                    "a new position lifecycle may open only after the previous "
                    "one reached a terminal state; a forged continuation of a "
                    "live position is refused"
                )
            parameters = dict(transition["new_lifecycle_parameters"])
            lifecycle = _state_machine.start_position_lifecycle(
                symbol=parameters["symbol"],
                direction=parameters.get(
                    "direction", _state_machine.LONG_DIRECTION
                ),
                state=parameters.get("initial_state", _state_machine.WATCH),
                config_metadata=parameters.get("config_metadata"),
            )
        else:
            lifecycle = _state_machine.restore_position_lifecycle(
                prior["position_lifecycle_record"]
            )
        for event in transition["position_events"]:
            lifecycle = _state_machine.apply_position_event(
                lifecycle, **_position_event_arguments(event)
            )
        account = _apply_account_operations(
            _restore_paper_account(prior["account_record"]),
            transition["account_operations"],
        )
        unrealized = _decimal(
            transition["nav_unrealized_pnl"], "nav_unrealized_pnl"
        )
        nav = account.nav(unrealized_pnl=unrealized)
        return {
            "account_record": account.as_record(),
            "nav": str(nav),
            "nav_unrealized_pnl": transition["nav_unrealized_pnl"],
            "position_lifecycle_record": lifecycle.as_record(),
        }


def build_portfolio_state(
    store: EvidenceStore,
    *,
    corpus_sha256: str,
    slot: DecisionSlot,
    prior_state_record_sha256: str,
    producing_transition_record_sha256: str,
) -> str:
    """Persist the resulting state the existing owners produce from prior + transition."""

    prior = store.get(prior_state_record_sha256, expected_kind=PORTFOLIO_STATE_KIND)
    transition = store.get(
        producing_transition_record_sha256, expected_kind=PORTFOLIO_TRANSITION_KIND
    )
    if transition["prior_state_record_sha256"] != prior_state_record_sha256:
        raise ProspectiveCorpusV2Error(
            "the transition does not belong to this predecessor"
        )
    produced = _apply_transition(store, prior, transition)
    payload = {
        **produced,
        "as_of": _isoformat(slot.decision_time),
        CORPUS_BINDING_FIELD: _require_sha256(corpus_sha256, CORPUS_BINDING_FIELD),
        "decision_time": _isoformat(slot.decision_time),
        "nav_unrealized_pnl_evidence_sha256": transition[
            "nav_unrealized_pnl_evidence_sha256"
        ],
        "nav_unrealized_pnl_owner": UNREALIZED_PNL_OWNER,
        "prior_state_record_sha256": prior_state_record_sha256,
        "producing_transition_record_sha256": producing_transition_record_sha256,
        RECORD_KIND_FIELD: PORTFOLIO_STATE_KIND,
        SCHEMA_VERSION_FIELD: RECORD_SCHEMA_VERSIONS[PORTFOLIO_STATE_KIND],
        "slot_id": slot.slot_id,
        "state_kind": STATE_KIND_DERIVED,
        "track": transition["track"],
    }
    if sorted(payload) != sorted(PORTFOLIO_STATE_FIELDS):
        raise ProspectiveCorpusV2Error("the portfolio state schema is strict")
    return store.put(payload)


def replay_portfolio_state(
    store: EvidenceStore,
    *,
    state_record_sha256: str,
    corpus_sha256: str,
) -> dict[str, Any]:
    """Replay one state from its exact predecessor and producing transition.

    Loads the prior state, loads the producing transition, runs the existing
    portfolio transition semantics over them, reconstructs the expected resulting
    state and requires exact equality with the persisted one. Any missing
    predecessor, missing transition, cross-position predecessor, transition/prior
    mismatch or altered field on either side refuses.
    """

    state = store.get(state_record_sha256, expected_kind=PORTFOLIO_STATE_KIND)
    if state[CORPUS_BINDING_FIELD] != corpus_sha256:
        raise ReplayRefusedError("the state binds a different certified corpus")
    if state["state_kind"] not in STATE_KINDS:
        raise ReplayRefusedError(f"unknown state kind {state['state_kind']!r}")
    if state["track"] not in _v1.PORTFOLIO_TRACKS:
        raise ReplayRefusedError(f"unknown track {state['track']!r}")

    if state["state_kind"] == STATE_KIND_GENESIS:
        if state["prior_state_record_sha256"] is not None:
            raise ReplayRefusedError("a genesis state cannot bind a predecessor")
        if state["producing_transition_record_sha256"] is not None:
            raise ReplayRefusedError(
                "a genesis state cannot bind a producing transition"
            )
        with _decimal_module.localcontext(_OWNER_CONTEXT):
            lifecycle = _state_machine.restore_position_lifecycle(
                state["position_lifecycle_record"]
            )
            if lifecycle.transitions:
                raise ReplayRefusedError(
                    "a genesis lifecycle must carry no transition history"
                )
            account = _restore_paper_account(state["account_record"])
            if str(account.nav(unrealized_pnl=Decimal("0"))) != state["nav"]:
                raise ReplayRefusedError("the genesis NAV does not reproduce")
        return {
            "account_record": state["account_record"],
            "is_genesis": True,
            "lifecycle_state": lifecycle.state,
            "position_lifecycle_record": state["position_lifecycle_record"],
            "state_record_sha256": state_record_sha256,
            "stop_price": lifecycle.stop_price,
            "track": state["track"],
        }

    if state["prior_state_record_sha256"] is None:
        raise ReplayRefusedError(
            "a derived state must bind its predecessor record; a null "
            "predecessor is reserved for genesis"
        )
    if state["producing_transition_record_sha256"] is None:
        raise ReplayRefusedError("a derived state must bind its producing transition")

    prior = store.get(
        state["prior_state_record_sha256"], expected_kind=PORTFOLIO_STATE_KIND
    )
    transition = store.get(
        state["producing_transition_record_sha256"],
        expected_kind=PORTFOLIO_TRANSITION_KIND,
    )
    if transition["prior_state_record_sha256"] != state["prior_state_record_sha256"]:
        raise ReplayRefusedError(
            "the producing transition belongs to another predecessor"
        )
    if transition[CORPUS_BINDING_FIELD] != corpus_sha256:
        raise ReplayRefusedError("the transition binds a different certified corpus")
    if transition["track"] != state["track"] or prior["track"] != state["track"]:
        raise ReplayRefusedError("the transition chain crosses portfolio tracks")
    if transition["decision_time"] != state["as_of"]:
        raise ReplayRefusedError("the transition time does not match the state")
    if _parse_utc(prior["as_of"], "as_of") > _parse_utc(state["as_of"], "as_of"):
        raise ReplayRefusedError("the predecessor is later than its successor")
    store.get(
        transition["action_evidence_record_sha256"],
        expected_kind=DECISION_OWNER_OUTPUT_KIND,
    )
    if transition["stop_evidence_record_sha256"] is not None:
        store.get(transition["stop_evidence_record_sha256"])
    if transition["risk_evidence_record_sha256"] is not None:
        store.get(
            transition["risk_evidence_record_sha256"],
            expected_kind=RISK_EVALUATION_KIND,
        )

    produced = _apply_transition(store, prior, transition)
    for field, value in produced.items():
        if state[field] != value:
            raise ReplayRefusedError(
                f"the persisted resulting state's {field} does not equal the "
                "state replayed from its predecessor and transition"
            )
    with _decimal_module.localcontext(_OWNER_CONTEXT):
        lifecycle = _state_machine.restore_position_lifecycle(
            state["position_lifecycle_record"]
        )
    return {
        "account_record": state["account_record"],
        "is_genesis": False,
        "lifecycle_state": lifecycle.state,
        "position_lifecycle_record": state["position_lifecycle_record"],
        "prior_state_record_sha256": state["prior_state_record_sha256"],
        "producing_transition_record_sha256": state[
            "producing_transition_record_sha256"
        ],
        "state_record_sha256": state_record_sha256,
        "stop_price": lifecycle.stop_price,
        "track": state["track"],
        "transition_class": transition["transition_class"],
        "transition_type": transition["transition_type"],
    }


def replay_portfolio_chain(
    store: EvidenceStore, *, state_record_sha256: str, corpus_sha256: str
) -> tuple[dict[str, Any], ...]:
    """Walk and verify the whole predecessor chain back to genesis.

    The walk is what proves acyclicity operationally as well as structurally: a
    repeated state on one path refuses instead of looping.
    """

    chain: list[dict[str, Any]] = []
    seen: set[str] = set()
    current = state_record_sha256
    while current is not None:
        if current in seen:
            raise ReplayRefusedError(
                "the portfolio graph contains a cycle; it must be acyclic"
            )
        seen.add(current)
        result = replay_portfolio_state(
            store, state_record_sha256=current, corpus_sha256=corpus_sha256
        )
        chain.append(result)
        current = result.get("prior_state_record_sha256")
    return tuple(reversed(chain))


# ---------------------------------------------------------------------------
# 9a. root position episode, active-stop lineage and exit/re-entry
# ---------------------------------------------------------------------------

ROOT_LIFECYCLE_DERIVATION_VERSION = "PROSPECTIVE_ROOT_LIFECYCLE_DERIVATION_V2"
ROOT_LIFECYCLE_RULE = (
    "Walk the verified predecessor/transition chain backwards from the state "
    "under evaluation until the ENTER transition that opened the currently open "
    "position after flat. That transition record's own content address is the "
    "root lifecycle identity. There is no governance-authored root-position "
    "SHA: the identity is a traversal result, and a forged root opening "
    "transition moves the chain and is refused by the state replay before the "
    "traversal reaches it."
)

ACTIVE_STOP_LINEAGE_RULE = (
    "ENTER establishes the initial stop; STOP_MOVE replaces it; ADD may modify "
    "the position and, where the existing owner permits, its stop; TRIM "
    "preserves or modifies state under the existing owner; EXIT terminates the "
    "position and its stop. Every stop therefore has a producing transition, and "
    "a stop that appears without one is refused."
)

ACTIVE_STOP_MEMBERSHIP_RULE = (
    "A stop-event record proves membership by naming the control state record "
    "whose replayed lifecycle carries that exact active stop at the event time, "
    "inside the same root lifecycle episode. An asserted active_stop_identity "
    "establishes nothing on its own: the identity is re-derived from the graph "
    "and compared, and a stop belonging to another position moves the root and "
    "is refused."
)

EXIT_REENTRY_RULE = (
    "A STOP_MOVE inside one position keeps the same root opening transition, "
    "because the chain reaches the same ENTER. An EXIT terminates the lifecycle, "
    "and the next ENTER can only occur on a new lifecycle, whose chain reaches a "
    "different ENTER. The two are therefore distinguishable by traversal alone, "
    "so a later sufficiency layer can count one root lifecycle unit per episode "
    "without a surrogate authority."
)


def derive_root_opening_transition(
    store: EvidenceStore, *, state_record_sha256: str, corpus_sha256: str
) -> dict[str, Any]:
    """Derive the exact ENTER transition that opened the current position."""

    chain = replay_portfolio_chain(
        store, state_record_sha256=state_record_sha256, corpus_sha256=corpus_sha256
    )
    tip = chain[-1]
    with _decimal_module.localcontext(_OWNER_CONTEXT):
        lifecycle = _state_machine.restore_position_lifecycle(
            tip["position_lifecycle_record"]
        )
    if lifecycle.state not in _state_machine.OPEN_POSITION_STATES:
        return {
            "position_open": False,
            "root_opening_transition_sha256": None,
            "root_state_record_sha256": None,
            "track": tip["track"],
        }
    for node in reversed(chain):
        if node.get("transition_class") != TRANSITION_CLASS_ENTER:
            continue
        return {
            "position_open": True,
            "root_opening_transition_sha256": node[
                "producing_transition_record_sha256"
            ],
            "root_state_record_sha256": node["state_record_sha256"],
            "track": node["track"],
        }
    raise ReplayRefusedError(
        "an open position has no ENTER transition in its verified chain"
    )


def derive_active_stop(
    store: EvidenceStore, *, state_record_sha256: str, corpus_sha256: str
) -> dict[str, Any]:
    """Derive the active stop and the exact transition that installed it."""

    chain = replay_portfolio_chain(
        store, state_record_sha256=state_record_sha256, corpus_sha256=corpus_sha256
    )
    tip = chain[-1]
    stop = tip["stop_price"]
    if stop is None:
        return {
            "active_stop": None,
            "installing_transition_sha256": None,
            "root_opening_transition_sha256": None,
            "stop_advance_count": 0,
            "track": tip["track"],
        }
    root = derive_root_opening_transition(
        store, state_record_sha256=state_record_sha256, corpus_sha256=corpus_sha256
    )
    installing: str | None = None
    advances = 0
    started = False
    for node in chain:
        if node.get("state_record_sha256") == root["root_state_record_sha256"]:
            started = True
        if not started:
            continue
        transition_class = node.get("transition_class")
        if transition_class == TRANSITION_CLASS_ENTER:
            installing = node["producing_transition_record_sha256"]
        elif transition_class == TRANSITION_CLASS_STOP_MOVE:
            installing = node["producing_transition_record_sha256"]
            advances += 1
    if installing is None:
        raise ReplayRefusedError(
            "an active stop exists with no producing transition in its episode"
        )
    return {
        "active_stop": str(stop),
        "installing_transition_sha256": installing,
        "root_opening_transition_sha256": root["root_opening_transition_sha256"],
        "stop_advance_count": advances,
        "track": tip["track"],
    }


def prove_active_stop_membership(
    store: EvidenceStore,
    *,
    stop_event_record_sha256: str,
    corpus_sha256: str,
) -> dict[str, Any]:
    """Prove the referenced stop was the control portfolio's active stop.

    The proof reads the content-addressed state, walks the transition chain and
    compares. The stop-event record's own ``active_stop_identity`` is treated as
    a claim to be checked, never as the thing that establishes membership.
    """

    event = store.get(stop_event_record_sha256, expected_kind=STOP_EVENT_KIND)
    if event[CORPUS_BINDING_FIELD] != corpus_sha256:
        raise ReplayRefusedError("the stop event binds a different certified corpus")
    if event["track"] != _v1.CONTROL_TRACK:
        raise ReplayRefusedError(
            "the stop-event universe is anchored to the control track's active stop"
        )
    derived = derive_active_stop(
        store,
        state_record_sha256=event["control_state_record_sha256"],
        corpus_sha256=corpus_sha256,
    )
    if derived["active_stop"] is None:
        raise ReplayRefusedError(
            "the control track carries no active stop at this event"
        )
    if _decimal(derived["active_stop"], "active_stop") != _decimal(
        event["active_stop"], "active_stop"
    ):
        raise ReplayRefusedError(
            "the stop-event's active stop is not the control track's replayed "
            "active stop"
        )
    expected_identity = active_stop_identity(
        root_opening_transition_sha256=derived["root_opening_transition_sha256"],
        installing_transition_sha256=derived["installing_transition_sha256"],
    )
    if event["active_stop_identity"] != expected_identity:
        raise ReplayRefusedError(
            "the asserted active stop identity is not the identity derived from "
            "the portfolio transition graph"
        )
    control = store.get(
        event["control_state_record_sha256"], expected_kind=PORTFOLIO_STATE_KIND
    )
    # The stop in force while an hourly bar forms is the one the control track
    # already carried when that bar opened. A state stamped after the bar is a
    # later stop being read back onto an earlier event, so it is refused.
    if _parse_utc(control["as_of"], "as_of") > _parse_utc(
        event["observation_time"], "observation_time"
    ):
        raise ReplayRefusedError(
            "the referenced control state was not in force when the observed "
            "bar formed"
        )
    return {
        **derived,
        "control_state_record_sha256": event["control_state_record_sha256"],
        "membership_proved": True,
        "stop_event_record_sha256": stop_event_record_sha256,
    }


ACTIVE_STOP_IDENTITY_VERSION = "PROSPECTIVE_ACTIVE_STOP_IDENTITY_V2"


def active_stop_identity(
    *, root_opening_transition_sha256: str, installing_transition_sha256: str
) -> str:
    """Derive a stop identity from the graph; a caller may never assert one."""

    return _digest(
        {
            "installing_transition_sha256": _require_sha256(
                installing_transition_sha256, "installing_transition_sha256"
            ),
            "root_opening_transition_sha256": _require_sha256(
                root_opening_transition_sha256, "root_opening_transition_sha256"
            ),
            "version": ACTIVE_STOP_IDENTITY_VERSION,
        }
    )


# ===========================================================================
# 10. decision-owner, reference, risk and stop-event evidence
# ===========================================================================

DECISION_OWNER_REGIME = "REGIME_CLASSIFICATION"
DECISION_OWNER_SETUP = "SETUP_DETECTOR_STATES"
DECISION_OWNER_TRADE_ACTION = "TRADE_ACTION"
DECISION_OWNER_TRADE_ELIGIBILITY = "TRADE_ELIGIBILITY"
DECISION_OWNERS = (
    DECISION_OWNER_REGIME,
    DECISION_OWNER_SETUP,
    DECISION_OWNER_TRADE_ACTION,
    DECISION_OWNER_TRADE_ELIGIBILITY,
)

DECISION_OWNER_VERSIONS = {
    DECISION_OWNER_REGIME: _v1._REGIME_COMPARISON_BASIS,
    DECISION_OWNER_SETUP: "SETUP_DETECTOR_STATES_V1",
    DECISION_OWNER_TRADE_ACTION: _v1.TRADE_ACTION_COMPARISON_OWNER_VERSION,
    DECISION_OWNER_TRADE_ELIGIBILITY: (
        _v1.TRADE_ELIGIBILITY_COMPOSITE_OWNER_VERSION
    ),
}

RISK_SIZING_OWNER = (
    "btc_predictor.risk.sizing.calculate_initial_position_size"
)
RISK_SIZING_FEATURE_ID = _sizing.INITIAL_POSITION_SIZE_FEATURE_ID
RISK_SIZING_OWNER_VERSION = _sizing.INITIAL_POSITION_SIZE_POLICY_VERSION

RISK_EVALUATION_FIELDS = (
    "cadence",
    CORPUS_BINDING_FIELD,
    "decision_time",
    "input_record_sha256s",
    "observation_time",
    "owner_feature_id",
    "owner_record",
    "owner_version",
    "position_notional",
    RECORD_KIND_FIELD,
    "reference_identity",
    "reference_role",
    "risk_size_complete",
    SCHEMA_VERSION_FIELD,
    "sizing_inputs",
    "slot_id",
    "track",
    "trade_permitted",
)

RISK_SIZING_INPUT_FIELDS = (
    "entry_price",
    "maximum_notional_fraction_nav",
    "nav",
    "risk_fraction_nav",
    "stop_distance_fraction",
)

TRADE_PERMITTED_NULL_RULE = (
    "trade_permitted is a strict Boolean in V2. The certified parent's typed "
    "projection allowed NULL and the blind parent evidence schema forbids a "
    "non-Boolean, which left an unresolved gate with no defined mapping. V2 "
    "closes that by construction: an unresolved eligibility gate is not a null "
    "permission, it is a slot that never becomes sizing-evaluable, and the "
    "universe predicate excludes it with an explicit reason code."
)


def decision_owner_output_record(
    *,
    corpus_sha256: str,
    slot: DecisionSlot,
    track: str,
    owner: str,
    owner_version: str,
    output: Mapping[str, Any],
    input_record_sha256s: Sequence[str],
    owner_history_manifest_sha256s: Mapping[str, str] | None = None,
    reason_codes: Sequence[str] = (),
) -> dict[str, Any]:
    """One decision owner's output for one track at one slot."""

    if owner not in DECISION_OWNERS:
        raise ProspectiveCorpusV2Error(f"unknown decision owner {owner!r}")
    if track not in _v1.PORTFOLIO_TRACKS:
        raise ProspectiveCorpusV2Error(f"unknown track {track!r}")
    return {
        "cadence": slot.cadence,
        CORPUS_BINDING_FIELD: _require_sha256(corpus_sha256, CORPUS_BINDING_FIELD),
        "decision_time": _isoformat(slot.decision_time),
        "input_record_sha256s": [
            _require_sha256(ref, "input_record_sha256s") for ref in input_record_sha256s
        ],
        "observation_time": _isoformat(slot.observation_time),
        "owner": owner,
        "owner_history_manifest_sha256s": {
            name: _require_sha256(ref, name)
            for name, ref in sorted((owner_history_manifest_sha256s or {}).items())
        },
        "owner_version": owner_version,
        "output": dict(output),
        "reason_codes": list(reason_codes),
        RECORD_KIND_FIELD: DECISION_OWNER_OUTPUT_KIND,
        SCHEMA_VERSION_FIELD: RECORD_SCHEMA_VERSIONS[DECISION_OWNER_OUTPUT_KIND],
        "slot_id": slot.slot_id,
        "track": track,
    }


def reference_evaluation_record(
    *,
    corpus_sha256: str,
    slot: DecisionSlot,
    reference_role: str,
    reference_identity: str,
    reference_ohlc: Mapping[str, str],
    input_record_sha256s: Sequence[str],
    available_at: datetime,
) -> dict[str, Any]:
    """One authorized reference variant's output for one slot."""

    if reference_role not in _v1.REFERENCE_ROLES:
        raise ProspectiveCorpusV2Error(f"unknown reference role {reference_role!r}")
    return {
        AVAILABLE_AT_FIELD: _isoformat(_require_utc(available_at, AVAILABLE_AT_FIELD)),
        "cadence": slot.cadence,
        CORPUS_BINDING_FIELD: _require_sha256(corpus_sha256, CORPUS_BINDING_FIELD),
        "decision_time": _isoformat(slot.decision_time),
        "input_record_sha256s": [
            _require_sha256(ref, "input_record_sha256s") for ref in input_record_sha256s
        ],
        "observation_time": _isoformat(slot.observation_time),
        RECORD_KIND_FIELD: REFERENCE_EVALUATION_KIND,
        "reference_identity": reference_identity,
        "reference_ohlc": {key: str(value) for key, value in sorted(reference_ohlc.items())},
        "reference_role": reference_role,
        SCHEMA_VERSION_FIELD: RECORD_SCHEMA_VERSIONS[REFERENCE_EVALUATION_KIND],
        "slot_id": slot.slot_id,
    }


def build_risk_evaluation(
    store: EvidenceStore,
    *,
    corpus_sha256: str,
    slot: DecisionSlot,
    track: str,
    reference_role: str,
    reference_identity: str,
    sizing_inputs: Mapping[str, str | None],
    trade_permitted: bool,
    input_record_sha256s: Sequence[str],
) -> str:
    """Run the authoritative sizing owner and persist its exact inputs and output.

    The record carries every input ``INITIAL_POSITION_SIZE_V1`` consumes, so a
    replay re-runs the owner rather than reading back an answer. The certified
    parent's typed projection carried the notional but neither NAV nor the risk
    fraction, which is precisely why the sizing opportunity could not be proved.
    """

    if reference_role not in _v1.REFERENCE_ROLES:
        raise ProspectiveCorpusV2Error(f"unknown reference role {reference_role!r}")
    if track not in _v1.PORTFOLIO_TRACKS:
        raise ProspectiveCorpusV2Error(f"unknown track {track!r}")
    if not isinstance(trade_permitted, bool):
        raise ProspectiveCorpusV2Error(TRADE_PERMITTED_NULL_RULE)
    inputs = {field: sizing_inputs.get(field) for field in RISK_SIZING_INPUT_FIELDS}
    if sorted(sizing_inputs) != sorted(RISK_SIZING_INPUT_FIELDS):
        raise ProspectiveCorpusV2Error(
            f"the sizing inputs are strict: {sorted(RISK_SIZING_INPUT_FIELDS)}"
        )
    with _decimal_module.localcontext(_OWNER_CONTEXT):
        owner_record = _sizing.calculate_initial_position_size(
            nav=inputs["nav"],
            risk_fraction_nav=inputs["risk_fraction_nav"],
            stop_distance_fraction=inputs["stop_distance_fraction"],
            entry_price=inputs["entry_price"],
            maximum_notional_fraction_nav=inputs["maximum_notional_fraction_nav"],
        ).as_record()
    payload = {
        "cadence": slot.cadence,
        CORPUS_BINDING_FIELD: _require_sha256(corpus_sha256, CORPUS_BINDING_FIELD),
        "decision_time": _isoformat(slot.decision_time),
        "input_record_sha256s": [
            _require_sha256(ref, "input_record_sha256s") for ref in input_record_sha256s
        ],
        "observation_time": _isoformat(slot.observation_time),
        "owner_feature_id": RISK_SIZING_FEATURE_ID,
        "owner_record": owner_record,
        "owner_version": RISK_SIZING_OWNER_VERSION,
        "position_notional": owner_record["position_notional"],
        RECORD_KIND_FIELD: RISK_EVALUATION_KIND,
        "reference_identity": reference_identity,
        "reference_role": reference_role,
        "risk_size_complete": bool(owner_record["complete"]),
        SCHEMA_VERSION_FIELD: RECORD_SCHEMA_VERSIONS[RISK_EVALUATION_KIND],
        "sizing_inputs": dict(inputs),
        "slot_id": slot.slot_id,
        "track": track,
        "trade_permitted": trade_permitted,
    }
    if sorted(payload) != sorted(RISK_EVALUATION_FIELDS):
        raise ProspectiveCorpusV2Error("the risk evaluation schema is strict")
    return store.put(payload)


def replay_risk_evaluation(
    store: EvidenceStore, *, risk_record_sha256: str, corpus_sha256: str
) -> dict[str, Any]:
    """Re-run the sizing owner from the bound inputs and compare exactly."""

    record = store.get(risk_record_sha256, expected_kind=RISK_EVALUATION_KIND)
    if record[CORPUS_BINDING_FIELD] != corpus_sha256:
        raise ReplayRefusedError("the risk record binds a different certified corpus")
    if record["owner_version"] != RISK_SIZING_OWNER_VERSION:
        raise ReplayRefusedError("the risk record binds another sizing owner version")
    if not isinstance(record["trade_permitted"], bool):
        raise ReplayRefusedError(TRADE_PERMITTED_NULL_RULE)
    for reference in record["input_record_sha256s"]:
        store.get(reference)
    inputs = record["sizing_inputs"]
    with _decimal_module.localcontext(_OWNER_CONTEXT):
        replayed = _sizing.calculate_initial_position_size(
            nav=inputs["nav"],
            risk_fraction_nav=inputs["risk_fraction_nav"],
            stop_distance_fraction=inputs["stop_distance_fraction"],
            entry_price=inputs["entry_price"],
            maximum_notional_fraction_nav=inputs["maximum_notional_fraction_nav"],
        ).as_record()
    if replayed != record["owner_record"]:
        raise ReplayRefusedError(
            "the persisted sizing output does not equal the owner's replayed "
            "result from the bound inputs"
        )
    if replayed["position_notional"] != record["position_notional"]:
        raise ReplayRefusedError("the projected notional does not equal the owner's")
    if bool(replayed["complete"]) != record["risk_size_complete"]:
        raise ReplayRefusedError("the projected completeness does not equal the owner's")
    return {
        "owner_record": replayed,
        "position_notional": replayed["position_notional"],
        "reference_identity": record["reference_identity"],
        "reference_role": record["reference_role"],
        "risk_record_sha256": risk_record_sha256,
        "risk_size_complete": bool(replayed["complete"]),
        "slot_id": record["slot_id"],
        "track": record["track"],
        "trade_permitted": record["trade_permitted"],
    }


# ---------------------------------------------------------------------------
# 10a. genuine paired sizing opportunity
# ---------------------------------------------------------------------------

SIZING_OPPORTUNITY_RULE = (
    "A sizing comparison is admissible only when one slot carries exactly two "
    "risk-evaluation records, one per reference role, with distinct reference "
    "identities, both permitting a trade, both complete under "
    f"{RISK_SIZING_OWNER_VERSION}, both replaying to their persisted output from "
    "their own bound inputs, both notionals strictly positive, and both bound to "
    "the same slot identity, the same certified corpus and their own track's "
    "portfolio state. No daily-slot Boolean establishes the opportunity."
)
SIZING_OPPORTUNITY_REFUSALS = (
    "CANDIDATE_REFERENCE_UNAVAILABLE",
    "CONTROL_REFERENCE_UNAVAILABLE",
    "ONE_TRACK_PRODUCED_NO_POSITIVE_RISK_SIZE",
    "REFERENCE_IDENTITY_NOT_DISTINCT",
    "SIZING_PAIR_INCOMPLETE",
)


def prove_paired_sizing_opportunity(
    store: EvidenceStore,
    *,
    slot: DecisionSlot,
    corpus_sha256: str,
    risk_record_sha256_by_role: Mapping[str, str],
) -> dict[str, Any]:
    """Prove a genuine paired sizing opportunity from evidence, not a Boolean."""

    roles = sorted(_v1.REFERENCE_ROLES)
    if sorted(risk_record_sha256_by_role) != roles:
        raise ReplayRefusedError(
            "SIZING_PAIR_INCOMPLETE: a sizing opportunity requires exactly one "
            f"risk evaluation per reference role {roles}"
        )
    replayed: dict[str, dict[str, Any]] = {}
    for role in roles:
        result = replay_risk_evaluation(
            store,
            risk_record_sha256=risk_record_sha256_by_role[role],
            corpus_sha256=corpus_sha256,
        )
        if result["reference_role"] != role:
            raise ReplayRefusedError(
                "a risk evaluation was substituted across reference roles"
            )
        if result["slot_id"] != slot.slot_id:
            raise ReplayRefusedError(
                "a risk evaluation from another slot was substituted"
            )
        replayed[role] = result
    identities = {result["reference_identity"] for result in replayed.values()}
    if len(identities) != len(roles):
        raise ReplayRefusedError(
            "REFERENCE_IDENTITY_NOT_DISTINCT: the candidate and control "
            "references must be distinct identities"
        )
    tracks = {result["track"] for result in replayed.values()}
    if len(tracks) != len(roles):
        raise ReplayRefusedError("the two risk evaluations share one track")
    for role, result in replayed.items():
        if not result["trade_permitted"] or not result["risk_size_complete"]:
            raise ReplayRefusedError(
                "ONE_TRACK_PRODUCED_NO_POSITIVE_RISK_SIZE: "
                f"{role} did not produce a complete permitted size"
            )
        notional = result["position_notional"]
        if notional is None or _decimal(notional, "position_notional") <= 0:
            raise ReplayRefusedError(
                "ONE_TRACK_PRODUCED_NO_POSITIVE_RISK_SIZE: "
                f"{role} produced no strictly positive notional"
            )
    candidate = replayed[_v1.CANDIDATE_REFERENCE_ROLE]["position_notional"]
    control = replayed[_v1.CONTROL_REFERENCE_ROLE]["position_notional"]
    with _decimal_module.localcontext(_CONTEXT):
        difference = abs(
            _decimal(candidate, "candidate") - _decimal(control, "control")
        ) / _decimal(control, "control")
    return {
        "candidate_position_notional": candidate,
        "control_position_notional": control,
        "opportunity_proved": True,
        "reference_identities": sorted(identities),
        "relative_difference": str(difference),
        "slot_id": slot.slot_id,
    }


# ---------------------------------------------------------------------------
# 10b. stop-event evidence
# ---------------------------------------------------------------------------

STOP_EVENT_FIELDS = (
    "active_stop",
    "active_stop_identity",
    "candidate_reference_record_sha256",
    "classification",
    "classifier_owner",
    "classifier_version",
    CORPUS_BINDING_FIELD,
    "control_state_record_sha256",
    "decision_time",
    "direction",
    "gap_through_state",
    "observation_time",
    "prior_provider_observation_sha256s",
    "provider_observation_sha256s",
    RECORD_KIND_FIELD,
    SCHEMA_VERSION_FIELD,
    "slot_id",
    "track",
    "universe_anchor",
)


def build_stop_event(
    store: EvidenceStore,
    *,
    corpus_sha256: str,
    slot: DecisionSlot,
    control_state_record_sha256: str,
    provider_observation_sha256s: Sequence[str],
    prior_provider_observation_sha256s: Sequence[str] = (),
    candidate_reference_record_sha256: str | None = None,
    direction: str = _state_machine.LONG_DIRECTION,
    classification: str = _v1.EVENT_NONE,
    gap_through_state: str = _v1.GAP_THROUGH_NOT_PRESENT,
) -> str:
    """Persist one stop-evaluation slot bound to the replayed control stop."""

    derived = derive_active_stop(
        store,
        state_record_sha256=control_state_record_sha256,
        corpus_sha256=corpus_sha256,
    )
    if derived["active_stop"] is None:
        raise ProspectiveCorpusV2Error(
            "a stop event requires the control track to carry an active stop"
        )
    if classification not in _v1.STOP_EVENT_CLASSIFICATIONS:
        raise ProspectiveCorpusV2Error(f"unknown classification {classification!r}")
    if gap_through_state not in _v1.GAP_THROUGH_STATES:
        raise ProspectiveCorpusV2Error(f"unknown gap-through state {gap_through_state!r}")
    payload = {
        "active_stop": derived["active_stop"],
        "active_stop_identity": active_stop_identity(
            root_opening_transition_sha256=derived["root_opening_transition_sha256"],
            installing_transition_sha256=derived["installing_transition_sha256"],
        ),
        "candidate_reference_record_sha256": candidate_reference_record_sha256,
        "classification": classification,
        "classifier_owner": _v1.STOP_EVENT_CLASSIFIER_OWNER,
        "classifier_version": _v1.STOP_EVENT_CLASSIFIER_VERSION,
        CORPUS_BINDING_FIELD: _require_sha256(corpus_sha256, CORPUS_BINDING_FIELD),
        "control_state_record_sha256": _require_sha256(
            control_state_record_sha256, "control_state_record_sha256"
        ),
        "decision_time": _isoformat(slot.decision_time),
        "direction": direction,
        "gap_through_state": gap_through_state,
        "observation_time": _isoformat(slot.observation_time),
        "prior_provider_observation_sha256s": [
            _require_sha256(ref, "prior_provider_observation_sha256s")
            for ref in prior_provider_observation_sha256s
        ],
        "provider_observation_sha256s": [
            _require_sha256(ref, "provider_observation_sha256s")
            for ref in provider_observation_sha256s
        ],
        RECORD_KIND_FIELD: STOP_EVENT_KIND,
        SCHEMA_VERSION_FIELD: RECORD_SCHEMA_VERSIONS[STOP_EVENT_KIND],
        "slot_id": slot.slot_id,
        "track": _v1.CONTROL_TRACK,
        "universe_anchor": _v1.STOP_EVENT_UNIVERSE_ANCHOR,
    }
    if sorted(payload) != sorted(STOP_EVENT_FIELDS):
        raise ProspectiveCorpusV2Error("the stop event schema is strict")
    return store.put(payload)


# ===========================================================================
# 11. PROSPECTIVE_SLOT_EVIDENCE_MANIFEST_V2
# ===========================================================================
#
# One immutable content-addressed commitment per scientific decision slot,
# naming the exact evidence needed to reproduce that slot.  It contains
# references, never conclusions -- and because a self-consistent manifest proves
# nothing on its own, §7's independent verification is what gives it force.

SLOT_EVIDENCE_MANIFEST_VERSION = SLOT_EVIDENCE_MANIFEST_KIND

SLOT_EVIDENCE_MANIFEST_FIELDS = (
    "cadence",
    CORPUS_BINDING_FIELD,
    "decision_owner_record_sha256s",
    "decision_time",
    "derived_feature_record_sha256s",
    "input_snapshot_record_sha256",
    "observation_time",
    "owner_history_manifest_sha256s",
    "portfolio_state_record_sha256s",
    "portfolio_transition_record_sha256s",
    RECORD_KIND_FIELD,
    "reference_evaluation_record_sha256s",
    "risk_evaluation_record_sha256s",
    "schema_identities",
    SCHEMA_VERSION_FIELD,
    "slot_id",
    "source_acquisition_record_sha256s",
    "stop_event_record_sha256",
)

SLOT_EVIDENCE_MANIFEST_CONCLUSION_FIELDS_REFUSED = (
    "active_stop_identity",
    "comparability",
    "control_root_position_sha256",
    "quality_state",
    "sizing_opportunity",
    "universe_member",
    "warmup_history_complete",
)

MANIFEST_IS_NOT_SUFFICIENT_AUTHORITY = (
    "The manifest is a commitment to an evidence set, not a finding about it. "
    "Replay independently verifies that every required reference exists, that "
    "every referenced record validates, that every identity, cadence and window "
    "matches, that no mandatory evidence is omitted, that no extraneous "
    "wrong-slot evidence is substituted, and that every point-in-time constraint "
    "holds. A self-consistent manifest with an omitted required history refuses."
)

INPUT_SNAPSHOT_ROLE = (
    "QUERY_CONVENIENCE_INDEX_NOT_THE_TOTAL_SCIENTIFIC_EVIDENCE_ROOT"
)


def build_slot_evidence_manifest(
    store: EvidenceStore,
    *,
    slot: DecisionSlot,
    corpus_sha256: str,
    owner_history_manifest_sha256s: Mapping[str, str],
    source_acquisition_record_sha256s: Sequence[str] = (),
    derived_feature_record_sha256s: Mapping[str, str] | None = None,
    decision_owner_record_sha256s: Mapping[str, Mapping[str, str]] | None = None,
    portfolio_state_record_sha256s: Mapping[str, str] | None = None,
    portfolio_transition_record_sha256s: Mapping[str, str] | None = None,
    reference_evaluation_record_sha256s: Mapping[str, str] | None = None,
    risk_evaluation_record_sha256s: Mapping[str, str] | None = None,
    stop_event_record_sha256: str | None = None,
    input_snapshot_record_sha256: str | None = None,
) -> str:
    """Persist one slot's complete evidence manifest."""

    payload = {
        "cadence": slot.cadence,
        CORPUS_BINDING_FIELD: _require_sha256(corpus_sha256, CORPUS_BINDING_FIELD),
        "decision_owner_record_sha256s": {
            owner: {
                track: _require_sha256(ref, track)
                for track, ref in sorted(entries.items())
            }
            for owner, entries in sorted((decision_owner_record_sha256s or {}).items())
        },
        "decision_time": _isoformat(slot.decision_time),
        "derived_feature_record_sha256s": {
            feature: _require_sha256(ref, feature)
            for feature, ref in sorted((derived_feature_record_sha256s or {}).items())
        },
        "input_snapshot_record_sha256": input_snapshot_record_sha256,
        "observation_time": _isoformat(slot.observation_time),
        "owner_history_manifest_sha256s": {
            owner: _require_sha256(ref, owner)
            for owner, ref in sorted(owner_history_manifest_sha256s.items())
        },
        "portfolio_state_record_sha256s": {
            track: _require_sha256(ref, track)
            for track, ref in sorted((portfolio_state_record_sha256s or {}).items())
        },
        "portfolio_transition_record_sha256s": {
            track: _require_sha256(ref, track)
            for track, ref in sorted(
                (portfolio_transition_record_sha256s or {}).items()
            )
        },
        RECORD_KIND_FIELD: SLOT_EVIDENCE_MANIFEST_KIND,
        "reference_evaluation_record_sha256s": {
            role: _require_sha256(ref, role)
            for role, ref in sorted(
                (reference_evaluation_record_sha256s or {}).items()
            )
        },
        "risk_evaluation_record_sha256s": {
            role: _require_sha256(ref, role)
            for role, ref in sorted((risk_evaluation_record_sha256s or {}).items())
        },
        "schema_identities": dict(sorted(RECORD_SCHEMA_VERSIONS.items())),
        SCHEMA_VERSION_FIELD: RECORD_SCHEMA_VERSIONS[SLOT_EVIDENCE_MANIFEST_KIND],
        "slot_id": slot.slot_id,
        "source_acquisition_record_sha256s": [
            _require_sha256(ref, "source_acquisition_record_sha256s")
            for ref in source_acquisition_record_sha256s
        ],
        "stop_event_record_sha256": stop_event_record_sha256,
    }
    if sorted(payload) != sorted(SLOT_EVIDENCE_MANIFEST_FIELDS):
        raise ProspectiveCorpusV2Error("the slot evidence manifest schema is strict")
    return store.put(payload)


def replay_slot_evidence_manifest(
    store: EvidenceStore,
    *,
    manifest_sha256: str,
    slot: DecisionSlot,
    corpus_sha256: str,
    census: Mapping[str, Any] | None = None,
    cached_warmup_state: str | None = None,
) -> dict[str, Any]:
    """Verify one slot's total evidence closure and derive its blind facts."""

    census = census if census is not None else owner_evaluability_census()
    manifest = store.get(manifest_sha256, expected_kind=SLOT_EVIDENCE_MANIFEST_KIND)
    for field in SLOT_EVIDENCE_MANIFEST_CONCLUSION_FIELDS_REFUSED:
        if field in manifest:
            raise ReplayRefusedError(
                f"a slot evidence manifest may not carry the conclusion {field}"
            )
    if manifest[CORPUS_BINDING_FIELD] != corpus_sha256:
        raise ReplayRefusedError("the manifest binds a different certified corpus")
    if manifest["slot_id"] != slot.slot_id:
        raise ReplayRefusedError("the manifest belongs to another slot")
    if manifest["cadence"] != slot.cadence:
        raise ReplayRefusedError("the manifest declares another cadence")
    if _parse_utc(manifest["decision_time"], "decision_time") != slot.decision_time:
        raise ReplayRefusedError("the manifest declares another decision time")
    if (
        _parse_utc(manifest["observation_time"], "observation_time")
        != slot.observation_time
    ):
        raise ReplayRefusedError("the manifest declares another observation time")
    if manifest["schema_identities"] != dict(sorted(RECORD_SCHEMA_VERSIONS.items())):
        raise ReplayRefusedError("the manifest binds another record schema set")

    evaluability = replay_decision_evaluability(
        store,
        slot=slot,
        corpus_sha256=corpus_sha256,
        owner_manifest_sha256s=manifest["owner_history_manifest_sha256s"],
        census=census,
        cached_warmup_state=cached_warmup_state,
    )

    for reference in manifest["source_acquisition_record_sha256s"]:
        store.get(reference)
    for feature, reference in manifest["derived_feature_record_sha256s"].items():
        record = store.get(reference, expected_kind=DERIVED_FEATURE_KIND)
        if record["feature"] != feature:
            raise ReplayRefusedError(
                f"the derived-feature reference for {feature} resolves to "
                f"{record['feature']}"
            )
        if _parse_utc(record[OBSERVATION_TIME_FIELD], OBSERVATION_TIME_FIELD) != (
            slot.observation_time
        ):
            raise ReplayRefusedError(
                f"the derived-feature record for {feature} belongs to another slot"
            )
    for owner, entries in manifest["decision_owner_record_sha256s"].items():
        for track, reference in entries.items():
            record = store.get(reference, expected_kind=DECISION_OWNER_OUTPUT_KIND)
            if record["owner"] != owner or record["track"] != track:
                raise ReplayRefusedError(
                    "a decision-owner record was substituted across owner or track"
                )
            if record["slot_id"] != slot.slot_id:
                raise ReplayRefusedError(
                    "a decision-owner record from another slot was substituted"
                )

    portfolio: dict[str, Any] = {}
    for track, reference in manifest["portfolio_state_record_sha256s"].items():
        result = replay_portfolio_state(
            store, state_record_sha256=reference, corpus_sha256=corpus_sha256
        )
        if result["track"] != track:
            raise ReplayRefusedError(
                "a portfolio state was substituted across tracks"
            )
        portfolio[track] = result
    for track, reference in manifest["portfolio_transition_record_sha256s"].items():
        transition = store.get(reference, expected_kind=PORTFOLIO_TRANSITION_KIND)
        if transition["track"] != track:
            raise ReplayRefusedError(
                "a portfolio transition was substituted across tracks"
            )
        if transition["slot_id"] != slot.slot_id:
            raise ReplayRefusedError(
                "a portfolio transition from another slot was substituted"
            )
        state_reference = manifest["portfolio_state_record_sha256s"].get(track)
        if state_reference is None:
            raise ReplayRefusedError(
                "a transition is bound without the state it produced"
            )
        state = store.get(state_reference, expected_kind=PORTFOLIO_STATE_KIND)
        if state["producing_transition_record_sha256"] != reference:
            raise ReplayRefusedError(
                "the bound transition is not the one that produced the bound state"
            )

    for role, reference in manifest["reference_evaluation_record_sha256s"].items():
        record = store.get(reference, expected_kind=REFERENCE_EVALUATION_KIND)
        if record["reference_role"] != role or record["slot_id"] != slot.slot_id:
            raise ReplayRefusedError(
                "a reference evaluation was substituted across role or slot"
            )
        if _parse_utc(record[AVAILABLE_AT_FIELD], AVAILABLE_AT_FIELD) > (
            slot.decision_time
        ):
            raise ReplayRefusedError(
                "a reference evaluation that was not available at the decision "
                "cannot enter the slot"
            )

    sizing = None
    if manifest["risk_evaluation_record_sha256s"]:
        sizing = prove_paired_sizing_opportunity(
            store,
            slot=slot,
            corpus_sha256=corpus_sha256,
            risk_record_sha256_by_role=manifest["risk_evaluation_record_sha256s"],
        )

    stop_membership = None
    if manifest["stop_event_record_sha256"] is not None:
        stop_membership = prove_active_stop_membership(
            store,
            stop_event_record_sha256=manifest["stop_event_record_sha256"],
            corpus_sha256=corpus_sha256,
        )

    if manifest["input_snapshot_record_sha256"] is not None:
        store.get(manifest["input_snapshot_record_sha256"])

    return {
        "derived_warmup_state": evaluability["derived_warmup_state"],
        "evaluability": evaluability,
        "input_snapshot_role": INPUT_SNAPSHOT_ROLE,
        "manifest_sha256": manifest_sha256,
        "portfolio": portfolio,
        "sizing_opportunity": sizing,
        "slot_id": slot.slot_id,
        "stop_membership": stop_membership,
    }


# ===========================================================================
# 12. the V2 scientific decision record
# ===========================================================================

DECISION_OBSERVATION_FIELDS = (
    "cadence",
    "cached_projections",
    CORPUS_BINDING_FIELD,
    "decision_time",
    "observation_state",
    "observation_time",
    "output_record_sha256s",
    "portfolio_context_record_sha256s",
    "reason_codes",
    RECORD_KIND_FIELD,
    SCHEMA_VERSION_FIELD,
    "slot_evidence_manifest_sha256",
    "slot_id",
    "strategy_identity_sha256",
)

CACHED_PROJECTION_FIELDS = (
    "comparability",
    "quality_state",
    "universe_membership",
    "warmup_history_state",
)
CACHED_PROJECTION_ROLE = (
    "Every field in cached_projections is a non-authoritative derived cache kept "
    "for query convenience. Each must equal the value the replay derives; a "
    "disagreement refuses. None of them may be read as evidence."
)


def build_decision_observation(
    store: EvidenceStore,
    *,
    corpus_sha256: str,
    slot: DecisionSlot,
    slot_evidence_manifest_sha256: str,
    strategy_identity_sha256: str,
    observation_state: str,
    output_record_sha256s: Mapping[str, str] | None = None,
    portfolio_context_record_sha256s: Mapping[str, str] | None = None,
    cached_projections: Mapping[str, Any] | None = None,
    reason_codes: Sequence[str] = (),
) -> str:
    """Persist one V2 scientific decision observation."""

    if observation_state not in _v1.OBSERVATION_STATES:
        raise ProspectiveCorpusV2Error(
            f"unknown observation state {observation_state!r}"
        )
    projections = dict(cached_projections or {})
    unknown = sorted(set(projections) - set(CACHED_PROJECTION_FIELDS))
    if unknown:
        raise ProspectiveCorpusV2Error(
            f"cached_projections is a strict set; unknown fields {unknown}"
        )
    payload = {
        "cadence": slot.cadence,
        "cached_projections": {
            field: projections.get(field) for field in CACHED_PROJECTION_FIELDS
        },
        CORPUS_BINDING_FIELD: _require_sha256(corpus_sha256, CORPUS_BINDING_FIELD),
        "decision_time": _isoformat(slot.decision_time),
        "observation_state": observation_state,
        "observation_time": _isoformat(slot.observation_time),
        "output_record_sha256s": {
            name: _require_sha256(ref, name)
            for name, ref in sorted((output_record_sha256s or {}).items())
        },
        "portfolio_context_record_sha256s": {
            track: _require_sha256(ref, track)
            for track, ref in sorted(
                (portfolio_context_record_sha256s or {}).items()
            )
        },
        "reason_codes": list(reason_codes),
        RECORD_KIND_FIELD: DECISION_OBSERVATION_KIND,
        SCHEMA_VERSION_FIELD: RECORD_SCHEMA_VERSIONS[DECISION_OBSERVATION_KIND],
        "slot_evidence_manifest_sha256": _require_sha256(
            slot_evidence_manifest_sha256, "slot_evidence_manifest_sha256"
        ),
        "slot_id": slot.slot_id,
        "strategy_identity_sha256": _require_sha256(
            strategy_identity_sha256, "strategy_identity_sha256"
        ),
    }
    if sorted(payload) != sorted(DECISION_OBSERVATION_FIELDS):
        raise ProspectiveCorpusV2Error("the decision observation schema is strict")
    return store.put(payload)


def replay_decision_observation(
    store: EvidenceStore,
    *,
    observation_sha256: str,
    slot: DecisionSlot,
    corpus_sha256: str,
    census: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Replay one decision observation through its bound evidence manifest."""

    record = store.get(observation_sha256, expected_kind=DECISION_OBSERVATION_KIND)
    if record[CORPUS_BINDING_FIELD] != corpus_sha256:
        raise ReplayRefusedError("the observation binds a different certified corpus")
    if record["slot_id"] != slot.slot_id:
        raise ReplayRefusedError("the observation belongs to another slot")
    if "warmup_history_complete" in record:
        raise ReplayRefusedError(
            "a V2 decision observation may not carry an authoritative warmup "
            "Boolean; warmup is a replayed derivation"
        )
    result = replay_slot_evidence_manifest(
        store,
        manifest_sha256=record["slot_evidence_manifest_sha256"],
        slot=slot,
        corpus_sha256=corpus_sha256,
        census=census,
        cached_warmup_state=record["cached_projections"].get("warmup_history_state"),
    )
    for name, reference in record["output_record_sha256s"].items():
        store.get(reference)
    for track, reference in record["portfolio_context_record_sha256s"].items():
        replayed = replay_portfolio_state(
            store, state_record_sha256=reference, corpus_sha256=corpus_sha256
        )
        if replayed["track"] != track:
            raise ReplayRefusedError(
                "a portfolio context record was substituted across tracks"
            )
    return {**result, "observation_sha256": observation_sha256}


# ===========================================================================
# 13. the frozen V2 child contracts
# ===========================================================================


def slot_evidence_manifest_contract() -> dict[str, Any]:
    """Freeze the slot evidence manifest and why it is not itself sufficient."""

    payload = {
        "binds_at_minimum": [
            "slot identity",
            "cadence",
            "decision_time",
            "input snapshot identity",
            "per-owner and per-feature history manifests",
            "source and acquisition evidence references",
            "derived-feature evidence references",
            "decision-owner evidence references",
            "control and candidate portfolio evidence where applicable",
            "stop-event evidence where applicable",
            "risk-evaluation evidence where applicable",
            "schema and version identities",
            "certified corpus V2 identity",
        ],
        "conclusion_fields_permitted": False,
        "conclusion_fields_refused": list(
            SLOT_EVIDENCE_MANIFEST_CONCLUSION_FIELDS_REFUSED
        ),
        "content_addressed": True,
        "independent_verification": [
            "all required references exist",
            "all referenced records validate and re-digest",
            "all identities, cadences and windows match",
            "no mandatory evidence is omitted",
            "no extraneous wrong-slot evidence is substituted",
            "all point-in-time constraints hold",
        ],
        "input_snapshot_role": INPUT_SNAPSHOT_ROLE,
        "manifest_fields": list(SLOT_EVIDENCE_MANIFEST_FIELDS),
        "manifest_is_not_sufficient_authority": (
            MANIFEST_IS_NOT_SUFFICIENT_AUTHORITY
        ),
        "one_manifest_per_scientific_decision_slot": True,
        "protocol_version": PROTOCOL_VERSION,
        "record_kind": SLOT_EVIDENCE_MANIFEST_KIND,
        "schema_version": "PROSPECTIVE_SLOT_EVIDENCE_MANIFEST_CONTRACT_V2",
        "self_consistent_manifest_with_omitted_history": "REFUSE",
        "slot_identity_derivation": SLOT_IDENTITY_DERIVATION,
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def owner_history_manifest_contract() -> dict[str, Any]:
    """Freeze the per-owner history manifest the audit found missing."""

    payload = {
        "adverse_observation_statuses": list(ADVERSE_OBSERVATION_STATUSES),
        "conclusion_fields_refused": list(
            OWNER_HISTORY_MANIFEST_CONCLUSION_FIELDS_REFUSED
        ),
        "content_addressed": True,
        "manifest_fields": list(OWNER_HISTORY_MANIFEST_FIELDS),
        "observation_status_rule": OBSERVATION_STATUS_RULE,
        "one_manifest_per_owner_per_slot": True,
        "persists_for_every_required_owner": [
            "feature / owner identity",
            "owner contract hash",
            "decision slot",
            "decision time",
            "source / series identities",
            "required cadence",
            "required historical interval and window semantics",
            "exact ordered qualifying observation record SHAs",
            "exact ordered adverse observation record SHAs",
            "exact historical availability and point-in-time selection semantics",
            "manifest digest",
        ],
        "pit_revision_rule": PIT_REVISION_RULE,
        "protocol_version": PROTOCOL_VERSION,
        "qualifying_observation_statuses": list(QUALIFYING_OBSERVATION_STATUSES),
        "record_kind": OWNER_HISTORY_MANIFEST_KIND,
        "schema_version": "PROSPECTIVE_OWNER_HISTORY_MANIFEST_CONTRACT_V2",
        "singular_input_snapshot_is_insufficient": (
            "A generic input_snapshot_sha256 commits to a payload, not to the "
            "owner-specific history each warmup predicate reruns, so it cannot "
            "make an omitted qualifying or adverse observation detectable. That "
            "is the certified parent's named limitation and the reason this "
            "contract exists."
        ),
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def owner_history_completeness_contract() -> dict[str, Any]:
    """Freeze the deterministic expected-set recomputation."""

    payload = {
        "comparison": (
            "expected owner evidence refs == persisted owner-history manifest refs"
        ),
        "detects": [
            "omitted qualifying observation",
            "omitted adverse or missing observation required by the predicate",
            "extra substituted observation",
            "wrong date",
            "wrong cadence",
            "wrong source",
            "future-available observation",
        ],
        "expected_set_owner": (
            "btc_predictor.research.prospective_integration_corpus_v2."
            "expected_owner_evidence"
        ),
        "expected_set_reads_the_manifest": False,
        "failure_semantics": "REFUSE",
        "protocol_version": PROTOCOL_VERSION,
        "rationale": (
            "A manifest checked only against itself is self-consistent whatever "
            "it omits. The expected set is therefore recomputed from the "
            "evidence store alone, under the owner's own frozen selector, and "
            "never reads the manifest it is checking."
        ),
        "replay_owner": (
            "btc_predictor.research.prospective_integration_corpus_v2."
            "replay_owner_history_manifest"
        ),
        "schema_version": "PROSPECTIVE_OWNER_HISTORY_COMPLETENESS_V2",
        "selector_semantics_frozen_by": (
            "PROSPECTIVE_OWNER_EVALUABILITY_CENSUS_V2"
        ),
        "window_kinds": list(WINDOW_KINDS),
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def decision_observation_contract() -> dict[str, Any]:
    """Freeze the V2 decision record and the demotion of cached fields."""

    payload = {
        "binds_at_minimum": [
            "slot identity",
            "observation time",
            "decision time",
            "slot evidence manifest SHA",
            "strategy / rulebook version",
            "certified corpus V2 hash and version",
            "decision and output record hashes",
            "portfolio context hashes where applicable",
        ],
        "cached_projection_fields": list(CACHED_PROJECTION_FIELDS),
        "cached_projection_role": CACHED_PROJECTION_ROLE,
        "cached_warmup_mismatch_behavior": CACHED_WARMUP_MISMATCH_BEHAVIOR,
        "observation_states": list(_v1.OBSERVATION_STATES),
        "parent_v1_warmup_boolean": {
            "field": "warmup_history_complete",
            "v1_role": "INDEPENDENT_SCIENTIFIC_AUTHORITY",
            "v2_role": CACHED_WARMUP_ROLE,
            "v2_disposition": (
                "REMOVED_FROM_THE_V2_DECISION_RECORD_AND_RETAINED_ONLY_AS_A_"
                "CACHED_PROJECTION_UNDER_cached_projections.warmup_history_state"
            ),
        },
        "protocol_version": PROTOCOL_VERSION,
        "record_fields": list(DECISION_OBSERVATION_FIELDS),
        "record_kind": DECISION_OBSERVATION_KIND,
        "schema_version": "PROSPECTIVE_DECISION_OBSERVATION_CONTRACT_V2",
        "slot_manifest_is_the_evidence_root": True,
        "warmup_authority_rule": WARMUP_AUTHORITY_RULE,
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def portfolio_transition_contract() -> dict[str, Any]:
    """Freeze the transition record and its bindings."""

    payload = {
        "acyclicity_rule": ACYCLICITY_RULE,
        "binds": [
            "the exact prior state record",
            "the exact decision / action evidence record",
            "the transition type and class",
            "the ordered position events the authoritative owner applies",
            "required stop evidence for ENTER and STOP_MOVE",
            "required risk evidence for ENTER and ADD",
            "the account operations the account owner applies",
        ],
        "binds_resulting_state": False,
        "binds_resulting_state_rationale": (
            "A transition that also named its resulting state would put the "
            "state's own hash inside the state's preimage. The resulting state "
            "referencing its producing transition closes the replay chain "
            "without that cycle."
        ),
        "event_vocabulary_owner": (
            "btc_predictor.portfolio.state_machine.POSITION_EVENTS"
        ),
        "events": list(_state_machine.POSITION_EVENTS),
        "optional_key_normalization": (
            "The authoritative transition record omits source_feature_id and "
            "source_record_id entirely when the first is None, so two "
            "economically identical transitions would hash differently "
            "depending on how they were produced. V2's own transition evidence "
            "always carries both keys with an explicit null."
        ),
        "protocol_version": PROTOCOL_VERSION,
        "record_fields": list(PORTFOLIO_TRANSITION_FIELDS),
        "record_kind": PORTFOLIO_TRANSITION_KIND,
        "schema_version": "PROSPECTIVE_PORTFOLIO_TRANSITION_CONTRACT_V2",
        "transition_class_by_event": dict(sorted(TRANSITION_CLASS_BY_EVENT.items())),
        "transition_classes": list(TRANSITION_CLASSES),
        "transition_owner": PORTFOLIO_TRANSITION_OWNER,
        "transition_owner_version": PORTFOLIO_TRANSITION_OWNER_VERSION,
        "transition_record_owner_version": PORTFOLIO_TRANSITION_RECORD_OWNER_VERSION,
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def portfolio_state_contract() -> dict[str, Any]:
    """Freeze the state record, its predecessor binding and its genesis."""

    payload = {
        "account_owner": ACCOUNT_OWNER,
        "account_owner_version": ACCOUNT_OWNER_VERSION,
        "binds_predecessor_record": True,
        "binds_producing_transition": True,
        "digest_of_selected_fields_is_insufficient": (
            "A prior_state_sha256 over selected state fields commits to a "
            "summary, not to the predecessor scientific record, so a replay "
            "cannot load and validate what actually preceded this state. V2 "
            "binds prior_state_record_sha256, the content address of the "
            "predecessor record itself, and the replay loads it."
        ),
        "genesis_contract": GENESIS_CONTRACT,
        "initial_state_owner": "PROSPECTIVE_INTEGRATION_CORPUS_V1.INITIAL_PORTFOLIO_STATE",
        "initial_state_sha256": _v1.portfolio_track_contract()["initial_state_sha256"],
        "lifecycle_owner": PORTFOLIO_TRANSITION_OWNER,
        "lifecycle_owner_version": PORTFOLIO_TRANSITION_OWNER_VERSION,
        "nav_owner": "btc_predictor.portfolio.account.PaperAccount.nav",
        "numerical_context_rule": PORTFOLIO_NUMERICAL_CONTEXT_RULE,
        "owner_replay_decimal_precision": OWNER_REPLAY_DECIMAL_PRECISION,
        "owner_replay_decimal_rounding": str(OWNER_REPLAY_DECIMAL_ROUNDING),
        "protocol_version": PROTOCOL_VERSION,
        "record_fields": list(PORTFOLIO_STATE_FIELDS),
        "record_kind": PORTFOLIO_STATE_KIND,
        "schema_version": "PROSPECTIVE_PORTFOLIO_STATE_CONTRACT_V2",
        "state_kinds": list(STATE_KINDS),
        "tracks": list(_v1.PORTFOLIO_TRACKS),
        "unrealized_pnl_binding_rule": UNREALIZED_PNL_BINDING_RULE,
        "unrealized_pnl_owner": UNREALIZED_PNL_OWNER,
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def portfolio_transition_replay_contract() -> dict[str, Any]:
    """Freeze the deterministic state-transition replay owner."""

    payload = {
        "account_operations": list(ACCOUNT_OPERATIONS),
        "economic_meaning_changed": False,
        "failure_semantics": "REFUSE",
        "protocol_version": PROTOCOL_VERSION,
        "replay_order": [
            "load the prior state record",
            "load the producing transition record",
            "require the transition's prior_state_record_sha256 to equal the "
            "state's own predecessor reference",
            "load the transition's action, stop and risk evidence",
            "restore the prior position lifecycle through its own owner",
            "apply each bound position event through the authoritative owner",
            "apply each bound account operation through the account owner",
            "recompute NAV by invoking the account owner's nav",
            "require exact equality with the persisted resulting state",
        ],
        "replay_owner": (
            "btc_predictor.research.prospective_integration_corpus_v2."
            "replay_portfolio_state"
        ),
        "schema_version": "PROSPECTIVE_PORTFOLIO_TRANSITION_REPLAY_V2",
        "single_step_public_api_absent": (
            "The authoritative module's single-step transition replay helper is "
            "private and unexported, and every public replay entry point begins "
            "at a pre-position root. V2 therefore restores the prior lifecycle "
            "through the public restore_position_lifecycle -- which itself "
            "re-replays the whole chain and compares field for field -- and then "
            "applies the transition's events through the public "
            "apply_position_event. No private helper is called and no invariant "
            "is re-encoded."
        ),
        "supported_transitions": {
            transition_class: sorted(
                event
                for event, mapped in TRANSITION_CLASS_BY_EVENT.items()
                if mapped == transition_class
            )
            for transition_class in TRANSITION_CLASSES
        },
        "transition_owner": PORTFOLIO_TRANSITION_OWNER,
        "transition_owner_version": PORTFOLIO_TRANSITION_OWNER_VERSION,
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def root_lifecycle_derivation_contract() -> dict[str, Any]:
    """Freeze how the root opening transition is traversed, not asserted."""

    payload = {
        "derivation_owner": (
            "btc_predictor.research.prospective_integration_corpus_v2."
            "derive_root_opening_transition"
        ),
        "exit_reentry_rule": EXIT_REENTRY_RULE,
        "governance_authored_root_position_sha": False,
        "protocol_version": PROTOCOL_VERSION,
        "root_lifecycle_rule": ROOT_LIFECYCLE_RULE,
        "schema_version": ROOT_LIFECYCLE_DERIVATION_VERSION,
        "traversal": [
            "verify the state and its whole predecessor chain",
            "walk backwards until the ENTER transition that opened the "
            "currently open position after flat",
            "return that transition's own content address as the root identity",
        ],
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def active_stop_membership_contract() -> dict[str, Any]:
    """Freeze active-stop lineage and membership as traversal results."""

    payload = {
        "active_stop_identity_derivation": (
            "sha256 over canonical {root_opening_transition_sha256, "
            "installing_transition_sha256, version}"
        ),
        "active_stop_identity_version": ACTIVE_STOP_IDENTITY_VERSION,
        "asserted_identity_establishes_membership": False,
        "lineage_rule": ACTIVE_STOP_LINEAGE_RULE,
        "membership_owner": (
            "btc_predictor.research.prospective_integration_corpus_v2."
            "prove_active_stop_membership"
        ),
        "membership_rule": ACTIVE_STOP_MEMBERSHIP_RULE,
        "no_stop_without_a_producing_transition": True,
        "protocol_version": PROTOCOL_VERSION,
        "schema_version": "PROSPECTIVE_ACTIVE_STOP_MEMBERSHIP_V2",
        "stop_event_universe_anchor": _v1.STOP_EVENT_UNIVERSE_ANCHOR,
        "stop_event_classifier_owner": _v1.STOP_EVENT_CLASSIFIER_OWNER,
        "stop_event_classifier_version": _v1.STOP_EVENT_CLASSIFIER_VERSION,
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def risk_opportunity_evidence_contract() -> dict[str, Any]:
    """Freeze what proves a genuine paired sizing opportunity."""

    payload = {
        "binds": [
            "candidate risk-evaluation output",
            "control risk-evaluation output",
            "reference identities",
            "decision slot",
            "entry and risk context",
            "portfolio and input evidence",
            "point-in-time availability",
        ],
        "generic_daily_slot_boolean_permitted": False,
        "metric": _v1.RISK_SIZE_METRIC,
        "opportunity_owner": (
            "btc_predictor.research.prospective_integration_corpus_v2."
            "prove_paired_sizing_opportunity"
        ),
        "opportunity_rule": SIZING_OPPORTUNITY_RULE,
        "protocol_version": PROTOCOL_VERSION,
        "refusal_reasons": list(SIZING_OPPORTUNITY_REFUSALS),
        "risk_evaluation_fields": list(RISK_EVALUATION_FIELDS),
        "schema_version": "PROSPECTIVE_RISK_OPPORTUNITY_EVIDENCE_V2",
        "sizing_input_fields": list(RISK_SIZING_INPUT_FIELDS),
        "sizing_owner": RISK_SIZING_OWNER,
        "sizing_owner_feature_id": RISK_SIZING_FEATURE_ID,
        "sizing_owner_version": RISK_SIZING_OWNER_VERSION,
        "statistic": _v1.RISK_SIZE_STATISTIC,
        "trade_permitted_null_rule": TRADE_PERMITTED_NULL_RULE,
        "v1_gap": (
            "The certified parent's typed risk projection carried the notional, "
            "the completeness flag and one shared decision_time, but neither NAV "
            "nor the risk fraction, so the sizing owner could not be re-run, and "
            "neither the slot identity nor the two reference identities, so "
            "'same slot, paired and distinct' was not checkable. V2 binds all of "
            "them and changes no sizing parameter."
        ),
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


# ---------------------------------------------------------------------------
# 13a. the mechanical replay-closure matrices
# ---------------------------------------------------------------------------

_STOP_METRIC_EVIDENCE = (
    f"{SLOT_EVIDENCE_MANIFEST_KIND}.stop_event_record_sha256",
    f"{STOP_EVENT_KIND}.provider_observation_sha256s",
    f"{STOP_EVENT_KIND}.prior_provider_observation_sha256s",
    f"{STOP_EVENT_KIND}.control_state_record_sha256",
    f"{PORTFOLIO_STATE_KIND}.prior_state_record_sha256",
    f"{PORTFOLIO_STATE_KIND}.producing_transition_record_sha256",
    f"{PORTFOLIO_TRANSITION_KIND}.action_evidence_record_sha256",
    f"{STOP_EVENT_KIND}.candidate_reference_record_sha256",
)

_DECISION_METRIC_EVIDENCE = (
    f"{SLOT_EVIDENCE_MANIFEST_KIND}.owner_history_manifest_sha256s",
    f"{OWNER_HISTORY_MANIFEST_KIND}.observation_record_sha256s",
    f"{OWNER_HISTORY_MANIFEST_KIND}.adverse_record_sha256s",
    f"{OWNER_HISTORY_MANIFEST_KIND}.component_manifest_sha256s",
    f"{SLOT_EVIDENCE_MANIFEST_KIND}.derived_feature_record_sha256s",
    f"{SLOT_EVIDENCE_MANIFEST_KIND}.decision_owner_record_sha256s",
    f"{SLOT_EVIDENCE_MANIFEST_KIND}.reference_evaluation_record_sha256s",
)

_ACTION_METRIC_EVIDENCE = _DECISION_METRIC_EVIDENCE + (
    f"{SLOT_EVIDENCE_MANIFEST_KIND}.portfolio_state_record_sha256s",
    f"{SLOT_EVIDENCE_MANIFEST_KIND}.portfolio_transition_record_sha256s",
)

_RISK_METRIC_EVIDENCE = _ACTION_METRIC_EVIDENCE + (
    f"{SLOT_EVIDENCE_MANIFEST_KIND}.risk_evaluation_record_sha256s",
    f"{RISK_EVALUATION_KIND}.sizing_inputs",
    f"{RISK_EVALUATION_KIND}.owner_record",
    f"{RISK_EVALUATION_KIND}.input_record_sha256s",
)

_METRIC_EVIDENCE_BY_METRIC: dict[str, tuple[str, ...]] = {
    _v1.CROSS_MARKET_METRIC: _STOP_METRIC_EVIDENCE,
    _v1.GAP_THROUGH_METRIC: _STOP_METRIC_EVIDENCE,
    _v1.ISOLATED_VENUE_METRIC: _STOP_METRIC_EVIDENCE,
    _v1.REGIME_METRIC: _DECISION_METRIC_EVIDENCE,
    _v1.SETUP_METRIC: _DECISION_METRIC_EVIDENCE,
    _v1.TRADE_ACTION_METRIC: _ACTION_METRIC_EVIDENCE,
    _v1.TRADE_ELIGIBILITY_METRIC: _ACTION_METRIC_EVIDENCE,
    _v1.RISK_SIZE_METRIC: _RISK_METRIC_EVIDENCE,
}

_METRIC_REPLAY_OWNER: dict[str, tuple[str, ...]] = {
    _v1.CROSS_MARKET_METRIC: (
        "prove_active_stop_membership",
        "replay_portfolio_chain",
    ),
    _v1.GAP_THROUGH_METRIC: (
        "prove_active_stop_membership",
        "replay_portfolio_chain",
    ),
    _v1.ISOLATED_VENUE_METRIC: (
        "prove_active_stop_membership",
        "replay_portfolio_chain",
    ),
    _v1.REGIME_METRIC: ("replay_decision_evaluability",),
    _v1.SETUP_METRIC: ("replay_decision_evaluability",),
    _v1.TRADE_ACTION_METRIC: (
        "replay_decision_evaluability",
        "replay_portfolio_state",
    ),
    _v1.TRADE_ELIGIBILITY_METRIC: (
        "replay_decision_evaluability",
        "replay_portfolio_state",
    ),
    _v1.RISK_SIZE_METRIC: (
        "replay_decision_evaluability",
        "replay_risk_evaluation",
        "prove_paired_sizing_opportunity",
    ),
}


def metric_replay_closure_matrix() -> dict[str, Any]:
    """Prove all eight Stage-B metrics are replayable from V2 parent evidence."""

    contracts = _v1.metric_evidence_contracts()["contracts"]
    authority = _v1.historical_gate_authority()
    rows: dict[str, Any] = {}
    for metric in _v1.TARGET_METRICS:
        contract = contracts[metric]
        gate = authority[metric]
        if gate["threshold"] != contract["threshold"]:
            raise ProspectiveCorpusV2Error(f"{metric} threshold disagreement")
        evidence = _METRIC_EVIDENCE_BY_METRIC[metric]
        owners = _METRIC_REPLAY_OWNER[metric]
        rows[metric] = {
            "authoritative_owner": contract["evidence_owner"],
            "cadence": contract["cadence"],
            "comparability_predicate_replayable": True,
            "denominator_membership_predicate_replayable": True,
            "direction": gate["direction"],
            "hard": gate["hard"],
            "metric": metric,
            "required_v2_evidence_references": list(evidence),
            "replay_owners": [
                f"btc_predictor.research.prospective_integration_corpus_v2.{name}"
                for name in owners
            ],
            "replayable": "YES",
            "threshold": gate["threshold"],
            "universe": contract["universe"],
            "universe_predicate_replayable": True,
        }
    replayable = sum(1 for row in rows.values() if row["replayable"] == "YES")
    if replayable != len(_v1.TARGET_METRICS):
        raise ProspectiveCorpusV2Error(
            f"only {replayable}/{len(_v1.TARGET_METRICS)} metrics are replayable"
        )
    payload = {
        "governance_authored_conclusions_required": False,
        "metric_count": len(rows),
        "parent_v1_metric_evidence_sha256": _v1.metric_evidence_contracts()[
            "definition_sha256"
        ],
        "protocol_version": PROTOCOL_VERSION,
        "replayable_count": replayable,
        "replayable_ratio": f"{replayable}/{len(_v1.TARGET_METRICS)}",
        "rows": rows,
        "schema_version": "PROSPECTIVE_METRIC_REPLAY_CLOSURE_MATRIX_V2",
        "universe_definitions_owner": (
            "PROSPECTIVE_INTEGRATION_CORPUS_V1.decision_universe_contract"
        ),
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def feature_replay_closure_matrix() -> dict[str, Any]:
    """Prove all 33 frozen features are replayable from V2 parent evidence."""

    census = owner_evaluability_census()
    rows: dict[str, Any] = {}
    for feature in _feature_matrix.INITIAL_FEATURE_NAMES:
        row = census["rows"][feature]
        selector = row["evidence_selector"]
        rows[feature] = {
            "evaluability_predicate": row["minimum_history_predicate"],
            "evaluability_predicate_owner": row["owner_contract"],
            "exact_input_history_reference": (
                f"{OWNER_HISTORY_MANIFEST_KIND}.observation_record_sha256s"
                if selector["series_kind"] != SERIES_KIND_COMPONENTS
                else f"{OWNER_HISTORY_MANIFEST_KIND}.component_manifest_sha256s"
            ),
            "feature": feature,
            "missing_data_behavior": row["missing_data_behavior"],
            "owner_class": row["owner_class"],
            "pit_valid_revision_reference": PIT_REVISION_RULE,
            "replayable": "YES",
            "resulting_value_reference": (
                f"{SLOT_EVIDENCE_MANIFEST_KIND}.derived_feature_record_sha256s"
            ),
            "series_family": selector["series_family"],
            "series_id": selector["series_id"],
            "series_kind": selector["series_kind"],
            "source_identity_reference": (
                f"{SOURCE_OBSERVATION_KIND}.series_id and .provider"
            ),
        }
    replayable = sum(1 for row in rows.values() if row["replayable"] == "YES")
    total = len(_feature_matrix.INITIAL_FEATURE_NAMES)
    if replayable != total:
        raise ProspectiveCorpusV2Error(f"only {replayable}/{total} features replayable")
    payload = {
        "feature_count": total,
        "feature_inventory_owner": (
            "btc_predictor.research.feature_matrix.INITIAL_FEATURE_NAMES"
        ),
        "owner_census_sha256": census["definition_sha256"],
        "owner_class_count": len(OWNER_CLASSES),
        "protocol_version": PROTOCOL_VERSION,
        "replayable_count": replayable,
        "replayable_ratio": f"{replayable}/{total}",
        "rows": rows,
        "schema_version": "PROSPECTIVE_FEATURE_REPLAY_CLOSURE_MATRIX_V2",
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


# ---------------------------------------------------------------------------
# 13b. the executable replay contracts, hash-bound
# ---------------------------------------------------------------------------
#
# Scientifically material selection rules must not live only in code.  Each
# replay owner below is frozen with its identity, its contract hash, its
# selection semantics, the evidence schemas it requires and its failure
# semantics.  A later executable-semantic manifest may additionally bind
# concrete runtime code; that is POSTP1-003R3's job, not this parent's.

_REPLAY_CONTRACTS: tuple[dict[str, Any], ...] = (
    {
        "failure_semantics": "REFUSE",
        "owner_identity": "expected_owner_evidence",
        "required_evidence_schemas": [
            SOURCE_OBSERVATION_KIND,
            DERIVED_FEATURE_KIND,
        ],
        "selection_semantics": (
            "Resolve every record of the owner's declared series and cadence, "
            "keep only revisions available at or before the decision instant, "
            "take the highest such revision per observation_time, then apply the "
            "owner's own frozen window kind. The manifest under test is never "
            "read."
        ),
    },
    {
        "failure_semantics": "REFUSE",
        "owner_identity": "evaluate_owner_predicate",
        "required_evidence_schemas": [
            SOURCE_OBSERVATION_KIND,
            DERIVED_FEATURE_KIND,
            OWNER_HISTORY_MANIFEST_KIND,
        ],
        "selection_semantics": (
            "Run the owner's own class predicate over the resolved qualifying "
            "and adverse records and over the components' replayed results. "
            "Heterogeneous owner predicates are preserved; no generic count "
            "rule substitutes for one."
        ),
    },
    {
        "failure_semantics": "REFUSE",
        "owner_identity": "replay_owner_history_manifest",
        "required_evidence_schemas": [OWNER_HISTORY_MANIFEST_KIND],
        "selection_semantics": (
            "Verify identity, cadence, window, owner contract hash and "
            "point-in-time validity, require the persisted reference sets to "
            "equal the independently recomputed expected sets, recursively "
            "replay every component manifest, then run the owner predicate."
        ),
    },
    {
        "failure_semantics": "REFUSE",
        "owner_identity": "replay_decision_evaluability",
        "required_evidence_schemas": [OWNER_HISTORY_MANIFEST_KIND],
        "selection_semantics": (
            "Replay every required owner in dependency order and combine the "
            "results under the frozen conjunction. A cached warmup projection "
            "that disagrees with the derived state refuses."
        ),
    },
    {
        "failure_semantics": "REFUSE",
        "owner_identity": "replay_portfolio_state",
        "required_evidence_schemas": [
            PORTFOLIO_STATE_KIND,
            PORTFOLIO_TRANSITION_KIND,
            DECISION_OWNER_OUTPUT_KIND,
        ],
        "selection_semantics": (
            "Load the exact predecessor record and the exact producing "
            "transition, require the transition to name that same predecessor, "
            "re-run the authoritative lifecycle and account owners, and require "
            "exact equality with the persisted resulting state."
        ),
    },
    {
        "failure_semantics": "REFUSE",
        "owner_identity": "derive_root_opening_transition",
        "required_evidence_schemas": [
            PORTFOLIO_STATE_KIND,
            PORTFOLIO_TRANSITION_KIND,
        ],
        "selection_semantics": (
            "Verify the whole chain, then walk backwards to the ENTER "
            "transition that opened the currently open position after flat."
        ),
    },
    {
        "failure_semantics": "REFUSE",
        "owner_identity": "prove_active_stop_membership",
        "required_evidence_schemas": [
            STOP_EVENT_KIND,
            PORTFOLIO_STATE_KIND,
            PORTFOLIO_TRANSITION_KIND,
        ],
        "selection_semantics": (
            "Derive the control track's active stop and its installing "
            "transition from the graph, re-derive the stop identity, and "
            "require the stop event's asserted stop and identity to equal them."
        ),
    },
    {
        "failure_semantics": "REFUSE",
        "owner_identity": "replay_risk_evaluation",
        "required_evidence_schemas": [RISK_EVALUATION_KIND],
        "selection_semantics": (
            "Re-run the authoritative sizing owner over the record's own bound "
            "inputs and require exact equality with the persisted owner result."
        ),
    },
    {
        "failure_semantics": "REFUSE",
        "owner_identity": "prove_paired_sizing_opportunity",
        "required_evidence_schemas": [RISK_EVALUATION_KIND],
        "selection_semantics": (
            "Require exactly one replayed risk evaluation per reference role at "
            "one slot, distinct reference identities, distinct tracks, both "
            "permitted, both complete and both notionals strictly positive."
        ),
    },
    {
        "failure_semantics": "REFUSE",
        "owner_identity": "replay_slot_evidence_manifest",
        "required_evidence_schemas": [SLOT_EVIDENCE_MANIFEST_KIND],
        "selection_semantics": (
            "Verify slot identity and schema identities, replay owner-history "
            "evaluability, resolve and cross-check every bound record, replay "
            "the portfolio states and their producing transitions, prove the "
            "sizing pair and the stop membership where present."
        ),
    },
    {
        "failure_semantics": "REFUSE",
        "owner_identity": "replay_decision_observation",
        "required_evidence_schemas": [DECISION_OBSERVATION_KIND],
        "selection_semantics": (
            "Replay the bound slot evidence manifest and compare every cached "
            "projection with the derived result."
        ),
    },
)

_REPLAY_MODULE = "btc_predictor.research.prospective_integration_corpus_v2"


def parent_replay_contract_registry() -> dict[str, Any]:
    """Hash-bind the parent's own replay architecture."""

    contracts: dict[str, Any] = {}
    for entry in _REPLAY_CONTRACTS:
        identity = entry["owner_identity"]
        if identity not in globals() or not callable(globals()[identity]):
            raise ProspectiveCorpusV2Error(
                f"the replay registry names {identity}, which is not a real owner"
            )
        for schema in entry["required_evidence_schemas"]:
            if schema not in RECORD_KINDS:
                raise ProspectiveCorpusV2Error(
                    f"{identity} requires an undeclared evidence schema {schema}"
                )
        row = {
            "failure_semantics": entry["failure_semantics"],
            "owner": f"{_REPLAY_MODULE}.{identity}",
            "owner_identity": identity,
            "required_evidence_schemas": list(entry["required_evidence_schemas"]),
            "selection_semantics": entry["selection_semantics"],
        }
        row["owner_contract_sha256"] = _digest(row)
        contracts[identity] = row
    payload = {
        "contract_count": len(contracts),
        "contracts": contracts,
        "executable_semantic_manifest_owner": (
            "POSTP1-003R3 may additionally bind concrete runtime code; this "
            "parent binds the selection semantics, the required evidence "
            "schemas and the failure semantics so that they do not live only in "
            "code."
        ),
        "protocol_version": PROTOCOL_VERSION,
        "record_kinds": list(RECORD_KINDS),
        "record_schema_versions": dict(sorted(RECORD_SCHEMA_VERSIONS.items())),
        "schema_version": "PROSPECTIVE_PARENT_REPLAY_CONTRACT_REGISTRY_V2",
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def source_evidence_reuse_contract() -> dict[str, Any]:
    """Bind, unchanged and by hash, the already-certified source layer."""

    parent = _v1.protocol_definition()
    children = parent["child_definition_sha256"]
    reused = (
        "coingecko_market_cap_request_attempt",
        "coingecko_market_cap_response_validation",
        "cvd_interval_completeness",
        "kraken_futures_instrument_metadata_validation",
        "liquidation_interval_completeness",
        "liquidation_utc_day_census",
        "prospective_btc_market_cap_acquisition",
        "prospective_clock_integrity",
        "prospective_cvd_acquisition",
        "prospective_liquidation_capture",
        "prospective_liquidation_percentile_adapter",
        "scientific_evidence_resolver",
        "source_stream_epoch",
        "stream_liveness_policy",
    )
    missing = sorted(set(reused) - set(children))
    if missing:
        raise ProspectiveCorpusV2Error(
            f"the certified parent no longer binds source children {missing}"
        )
    payload = {
        "certified_parent_sha256": parent["definition_sha256"],
        "redesigned": False,
        "reused_child_sha256": {name: children[name] for name in reused},
        "reused_child_count": len(reused),
        "protocol_version": PROTOCOL_VERSION,
        "resolver_version": EVIDENCE_RESOLVER_VERSION,
        "rule": (
            "V2 does not redesign the already-certified source-completeness "
            "layer. CoinGecko request and response evidence, clock integrity, "
            "stream epochs, liveness, collector health, CVD completeness, "
            "liquidation completeness and the UTC day census, and runtime "
            "metadata validation are reused exactly as the certified parent "
            "froze them, bound here by hash. V2 adds the decision, "
            "owner-history and portfolio closure that references them."
        ),
        "schema_version": "PROSPECTIVE_SOURCE_EVIDENCE_REUSE_V2",
        "v2_resolver_extension": {
            "adds": [
                "owner-history expected-set recomputation",
                "portfolio predecessor and producing-transition resolution",
                "slot manifest total-closure verification",
            ],
            "changes_source_semantics": False,
            "version": EVIDENCE_RESOLVER_V2_VERSION,
        },
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def collection_epoch_contract() -> dict[str, Any]:
    """Freeze when V2 qualifying collection may begin, and that it may not yet."""

    payload = {
        "collection_authorized": False,
        "postp1_004_authorized": False,
        "preconditions_in_order": [
            "V2 implementation",
            "exact-hash independent xHigh review PASS",
            "sufficiency governance reissued against V2",
            "sufficiency governance exact-hash review PASS",
            "POSTP1-004 implementation",
            "POSTP1-004 independent review PASS",
        ],
        "protocol_version": PROTOCOL_VERSION,
        "qualifying_v1_evidence_exists": False,
        "schema_version": "PROSPECTIVE_V2_COLLECTION_EPOCH_V2",
        "v1_evidence_counts_toward_v2_sufficiency": False,
        "v1_migration_required": False,
        "v1_observation_fabrication_permitted": False,
        "v1_qualifying_observations_collected": (
            PARENT_V1_QUALIFYING_OBSERVATIONS_COLLECTED
        ),
        "v2_starts_fresh_rationale": (
            "Zero qualifying prospective observations were ever collected under "
            "V1, so there is nothing to migrate and nothing may be fabricated "
            "backwards. V2's collection epoch begins empty."
        ),
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


# ---------------------------------------------------------------------------
# 13c. the additive V2 persisted schema
# ---------------------------------------------------------------------------

_V2_TABLE_CONTRACT: dict[str, dict[str, Any]] = {
    "prospective_owner_history_manifest_v2": {
        "append_only": True,
        "columns": {
            "additional_record_sha256s": "jsonb not null",
            "adverse_record_sha256s": "jsonb not null",
            "cadence": "text not null",
            "certified_corpus_sha256": "char(64) not null",
            "component_manifest_sha256s": "jsonb not null",
            "decision_time": "timestamptz not null",
            "evidence_selector": "jsonb not null",
            "manifest_sha256": "char(64) not null",
            "observation_record_sha256s": "jsonb not null",
            "observation_time": "timestamptz not null",
            "owner_class": "text not null",
            "owner_contract": "text not null",
            "owner_contract_sha256": "char(64) not null",
            "owner_id": "text not null",
            "pit_selection_semantics": "jsonb not null",
            "required_cadence": "text not null",
            "run_id": "uuid not null",
            "schema_version": "text not null",
            "series_identity": "jsonb not null",
            "slot_id": "char(64) not null",
        },
        "layer": "RAW",
        "primary_key": ["run_id", "manifest_sha256"],
        "purpose": (
            "The complete owner-specific history for one owner at one slot. The "
            "reference lists are ordered and exhaustive, and a replay recomputes "
            "the expected set independently rather than trusting them."
        ),
    },
    "prospective_slot_evidence_manifest_v2": {
        "append_only": True,
        "columns": {
            "cadence": "text not null",
            "certified_corpus_sha256": "char(64) not null",
            "decision_owner_record_sha256s": "jsonb not null",
            "decision_time": "timestamptz not null",
            "derived_feature_record_sha256s": "jsonb not null",
            "input_snapshot_record_sha256": "char(64) null",
            "manifest_sha256": "char(64) not null",
            "observation_time": "timestamptz not null",
            "owner_history_manifest_sha256s": "jsonb not null",
            "portfolio_state_record_sha256s": "jsonb not null",
            "portfolio_transition_record_sha256s": "jsonb not null",
            "reference_evaluation_record_sha256s": "jsonb not null",
            "risk_evaluation_record_sha256s": "jsonb not null",
            "run_id": "uuid not null",
            "schema_identities": "jsonb not null",
            "schema_version": "text not null",
            "slot_id": "char(64) not null",
            "source_acquisition_record_sha256s": "jsonb not null",
            "stop_event_record_sha256": "char(64) null",
        },
        "layer": "RAW",
        "primary_key": ["run_id", "manifest_sha256"],
        "purpose": (
            "One immutable content-addressed commitment to the exact evidence "
            "set needed to reproduce one scientific decision slot. It carries "
            "references only; a conclusion column is refused."
        ),
    },
    "prospective_decision_observation_v2": {
        "append_only": True,
        "columns": {
            "cached_projections": "jsonb not null",
            "cadence": "text not null",
            "certified_corpus_sha256": "char(64) not null",
            "decision_time": "timestamptz not null",
            "observation_state": "text not null",
            "observation_time": "timestamptz not null",
            "output_record_sha256s": "jsonb not null",
            "portfolio_context_record_sha256s": "jsonb not null",
            "reason_codes": "jsonb not null",
            "record_sha256": "char(64) not null",
            "run_id": "uuid not null",
            "schema_version": "text not null",
            "slot_evidence_manifest_sha256": "char(64) not null",
            "slot_id": "char(64) not null",
            "strategy_identity_sha256": "char(64) not null",
        },
        "layer": "RAW",
        "primary_key": ["run_id", "cadence", "observation_time"],
        "purpose": (
            "The V2 scheduled slot census. warmup_history_complete is gone from "
            "this row: warmup lives in cached_projections as a non-authoritative "
            "derived cache that must equal the replayed owner-specific result."
        ),
    },
    "prospective_portfolio_transition_v2": {
        "append_only": True,
        "columns": {
            "account_operations": "jsonb not null",
            "action_evidence_record_sha256": "char(64) not null",
            "certified_corpus_sha256": "char(64) not null",
            "decision_time": "timestamptz not null",
            "nav_unrealized_pnl": "numeric not null",
            "nav_unrealized_pnl_evidence_sha256": "char(64) null",
            "new_lifecycle_parameters": "jsonb null",
            "opens_new_position_lifecycle": "boolean not null",
            "position_events": "jsonb not null",
            "prior_state_record_sha256": "char(64) not null",
            "record_sha256": "char(64) not null",
            "risk_evidence_record_sha256": "char(64) null",
            "run_id": "uuid not null",
            "schema_version": "text not null",
            "slot_id": "char(64) not null",
            "stop_evidence_record_sha256": "char(64) null",
            "track": "text not null",
            "transition_class": "text not null",
            "transition_owner": "text not null",
            "transition_owner_version": "text not null",
            "transition_type": "text not null",
        },
        "layer": "DERIVED",
        "primary_key": ["run_id", "record_sha256"],
        "purpose": (
            "One portfolio transition, binding its exact predecessor record and "
            "its exact action evidence. It deliberately does not bind the "
            "resulting state, so no hash cycle can form."
        ),
    },
    "prospective_portfolio_state_v2": {
        "append_only": True,
        "columns": {
            "account_record": "jsonb not null",
            "as_of": "timestamptz not null",
            "certified_corpus_sha256": "char(64) not null",
            "decision_time": "timestamptz not null",
            "nav": "numeric not null",
            "nav_unrealized_pnl": "numeric not null",
            "nav_unrealized_pnl_evidence_sha256": "char(64) null",
            "nav_unrealized_pnl_owner": "text not null",
            "position_lifecycle_record": "jsonb not null",
            "prior_state_record_sha256": "char(64) null",
            "producing_transition_record_sha256": "char(64) null",
            "record_sha256": "char(64) not null",
            "run_id": "uuid not null",
            "schema_version": "text not null",
            "slot_id": "char(64) not null",
            "state_kind": "text not null",
            "track": "text not null",
        },
        "layer": "DERIVED",
        "primary_key": ["run_id", "record_sha256"],
        "purpose": (
            "One resulting portfolio state, binding the content address of its "
            "predecessor record and of the transition that produced it. Both are "
            "null only for the single GENESIS state of a track."
        ),
    },
    "prospective_risk_evaluation_v2": {
        "append_only": True,
        "columns": {
            "cadence": "text not null",
            "certified_corpus_sha256": "char(64) not null",
            "decision_time": "timestamptz not null",
            "input_record_sha256s": "jsonb not null",
            "observation_time": "timestamptz not null",
            "owner_feature_id": "text not null",
            "owner_record": "jsonb not null",
            "owner_version": "text not null",
            "position_notional": "numeric null",
            "record_sha256": "char(64) not null",
            "reference_identity": "text not null",
            "reference_role": "text not null",
            "risk_size_complete": "boolean not null",
            "run_id": "uuid not null",
            "schema_version": "text not null",
            "sizing_inputs": "jsonb not null",
            "slot_id": "char(64) not null",
            "track": "text not null",
            "trade_permitted": "boolean not null",
        },
        "layer": "DERIVED",
        "primary_key": ["run_id", "reference_role", "slot_id"],
        "purpose": (
            "One reference role's risk evaluation at one slot, carrying every "
            "input the authoritative sizing owner consumes so the owner can be "
            "re-run rather than read back. trade_permitted is strictly Boolean."
        ),
    },
    "prospective_stop_event_v2": {
        "append_only": True,
        "columns": {
            "active_stop": "numeric not null",
            "active_stop_identity": "char(64) not null",
            "candidate_reference_record_sha256": "char(64) null",
            "certified_corpus_sha256": "char(64) not null",
            "classification": "text not null",
            "classifier_owner": "text not null",
            "classifier_version": "text not null",
            "control_state_record_sha256": "char(64) not null",
            "decision_time": "timestamptz not null",
            "direction": "text not null",
            "gap_through_state": "text not null",
            "observation_time": "timestamptz not null",
            "prior_provider_observation_sha256s": "jsonb not null",
            "provider_observation_sha256s": "jsonb not null",
            "record_sha256": "char(64) not null",
            "run_id": "uuid not null",
            "schema_version": "text not null",
            "slot_id": "char(64) not null",
            "track": "text not null",
            "universe_anchor": "text not null",
        },
        "layer": "DERIVED",
        "primary_key": ["run_id", "track", "observation_time"],
        "purpose": (
            "One stop-evaluation slot whose active stop and stop identity are "
            "re-derived from the control track's verified transition graph. The "
            "asserted identity is a claim the replay checks, never the authority."
        ),
    },
}


def data_schema_contract_v2() -> dict[str, Any]:
    """Freeze the additive V2 schema beside the certified parent's own."""

    parent_schema = _v1.data_schema_contract()
    payload = {
        "additive_extension_of": parent_schema["schema_version"],
        "content_addressed_immutability_rule": (
            "Every scientifically material V2 record's identity is the digest of "
            "its canonical payload without the digest field. Changing a history "
            "reference, a predecessor state, a transition, a source record, an "
            "owner contract or a slot identity therefore moves that record's "
            "hash, and moves the slot manifest and parent evidence identity that "
            "reference it."
        ),
        "database": parent_schema["database"],
        "evidence_graph_rule": parent_schema["evidence_graph_rule"],
        "implementation_state": _v1.SCHEMA_IMPLEMENTATION_STATE,
        "parent_schema_sha256": parent_schema["definition_sha256"],
        "parent_tables_unchanged": True,
        "protocol_version": PROTOCOL_VERSION,
        "referential_integrity": {
            "decision_observation_to_slot_manifest": (
                "slot_evidence_manifest_sha256 resolves and belongs to this slot"
            ),
            "owner_history_to_observations": (
                "every observation and adverse reference resolves and is "
                "point-in-time valid"
            ),
            "slot_manifest_to_owner_history": (
                "every required owner's manifest resolves and replays"
            ),
            "state_to_predecessor": "prior_state_record_sha256 resolves",
            "state_to_transition": (
                "producing_transition_record_sha256 resolves and names this "
                "state's own predecessor"
            ),
            "stop_event_to_control_state": (
                "control_state_record_sha256 resolves and replays to this active "
                "stop"
            ),
            "transition_to_action": "action_evidence_record_sha256 resolves",
        },
        "schema": _v1.CORPUS_SCHEMA,
        "schema_version": "PROSPECTIVE_INTEGRATION_CORPUS_SCHEMA_V2",
        "table_prefix": _v1.CORPUS_TABLE_PREFIX,
        "tables": _V2_TABLE_CONTRACT,
        "typed_table_role": parent_schema["exact_record_persistence"]["typed_table_role"],
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


# ---------------------------------------------------------------------------
# 13d. inherited V1 children, bound by hash and unchanged
# ---------------------------------------------------------------------------

_V1_CHILDREN_SUPERSEDED_BY_V2: dict[str, str] = {
    "data_schema_contract": "data_schema_contract_v2",
    "warmup_history": "owner_evaluability_census",
}
_V1_CHILDREN_EXTENDED_BY_V2: dict[str, tuple[str, ...]] = {
    "decision_universe": ("decision_evaluability_contract",),
    "evidence_sufficiency": ("collection_epoch_contract",),
    "feature_input_coverage": ("feature_replay_closure_matrix",),
    "input_snapshot_schema": ("slot_evidence_manifest_contract",),
    "metric_evidence_contracts": ("metric_replay_closure_matrix",),
    "portfolio_track_contract": (
        "portfolio_state_contract",
        "portfolio_transition_contract",
    ),
    "stage_b_evaluation_contract": ("parent_replay_contract_registry",),
    "stop_event_taxonomy": ("active_stop_membership_contract",),
    "semantic_diff_from_v5_blockers": ("semantic_diff_v1_to_v2",),
}


# ---------------------------------------------------------------------------
# 13e0. V2's own frozen commitment to the historical Stage-B gates
# ---------------------------------------------------------------------------
#
# A parity check that reads the same authority on both sides proves nothing: if
# the upstream gate moved, both sides move together and the diff still reports
# zero.  V2 therefore transcribes the eight frozen gates here, as literals, and
# the semantic diff compares the *live* certified authority against this
# commitment.  Nothing here authors a threshold: every value is the frozen V2
# approval gate the certified parent already imports verbatim, and a
# disagreement refuses the build rather than publishing the moved number.

_FROZEN_STAGE_B_GATES: dict[str, dict[str, Any]] = {
    "cross_market_confirmed_stop_preservation_rate": {
        "cadence": "STOP_HOURLY",
        "direction": "minimum",
        "evidence_owner": (
            "btc_predictor.research.prospective_integration_corpus."
            "classify_stop_event"
        ),
        "hard": True,
        "statistic": "rate",
        "threshold": "1.0",
        "universe": "CROSS_MARKET_CONFIRMED_STOP_EVENTS",
    },
    "gap_through_stop_consensus_agreement_rate": {
        "cadence": "STOP_HOURLY",
        "direction": "minimum",
        "evidence_owner": (
            "btc_predictor.research.prospective_integration_corpus."
            "classify_stop_event"
        ),
        "hard": True,
        "statistic": "rate",
        "threshold": "0.99",
        "universe": "GAP_THROUGH_STOP_EVENTS",
    },
    "isolated_venue_stop_suppression_rate": {
        "cadence": "STOP_HOURLY",
        "direction": "minimum",
        "evidence_owner": (
            "btc_predictor.research.prospective_integration_corpus."
            "classify_stop_event"
        ),
        "hard": True,
        "statistic": "rate",
        "threshold": "0.95",
        "universe": "ISOLATED_VENUE_STOP_EVENTS",
    },
    "regime_classification_disagreement_rate": {
        "cadence": "STRATEGY_DAILY",
        "direction": "maximum",
        "evidence_owner": (
            "btc_predictor.features.regime.calculate_regime_classification"
        ),
        "hard": True,
        "statistic": "rate",
        "threshold": "0.02",
        "universe": "REGIME_EVALUABLE_DECISION_TIMES",
    },
    "risk_size_p95_relative_difference": {
        "cadence": "STRATEGY_DAILY",
        "direction": "maximum",
        "evidence_owner": (
            "btc_predictor.risk.sizing.calculate_initial_position_size"
        ),
        "hard": True,
        "statistic": "nearest_rank_p95_of_the_absolute_relative_differences",
        "threshold": "0.10",
        "universe": "SIZING_EVALUABLE_DECISION_TIMES",
    },
    "setup_classification_disagreement_rate": {
        "cadence": "STRATEGY_DAILY",
        "direction": "maximum",
        "evidence_owner": "btc_predictor.features.setup",
        "hard": True,
        "statistic": "rate",
        "threshold": "0.01",
        "universe": "SETUP_EVALUABLE_DECISION_TIMES",
    },
    "trade_action_disagreement_rate": {
        "cadence": "STRATEGY_DAILY",
        "direction": "maximum",
        "evidence_owner": (
            "btc_predictor.research.prospective_integration_corpus."
            "TRADE_ACTION_COMPARISON_OWNER_V1"
        ),
        "hard": True,
        "statistic": "rate",
        "threshold": "0.01",
        "universe": "ACTION_EVALUABLE_DECISION_TIMES",
    },
    "trade_eligibility_disagreement_rate": {
        "cadence": "STRATEGY_DAILY",
        "direction": "maximum",
        "evidence_owner": (
            "btc_predictor.research.prospective_integration_corpus."
            "TRADE_ELIGIBILITY_COMPOSITE_OWNER_V1"
        ),
        "hard": True,
        "statistic": "rate",
        "threshold": "0.01",
        "universe": "ELIGIBILITY_EVALUABLE_DECISION_TIMES",
    },
}

# The same reasoning applies to the inherited children: pinning the 25 certified
# V1 child hashes here is what makes "V1 is unmutated" a verified result rather
# than an asserted one.
_FROZEN_V1_CHILD_SHA256: dict[str, str] = {
    "coingecko_market_cap_request_attempt": (
        "4ea71f2461ac9d4a279c757ee349be4df76679e070e0a896e3e53ca9f0175fc6"
    ),
    "coingecko_market_cap_response_validation": (
        "1cda159214ab5b2045790a5fa3c1ca7e3ba0d51d41456be4c5bc5d5e75f67eee"
    ),
    "cvd_interval_completeness": (
        "b26bd859c30648b182d06e669177b1c440e7329de18c135be429f41c3c6cc906"
    ),
    "data_schema_contract": (
        "0c29908f121c9060d47c5153aa938feed48f73a69268d323e9e72b9affcbf66d"
    ),
    "decision_universe": (
        "b78abe4e34dfdcd097523dc80548bc452c4a5eb787fda4ea82ba47784a36c3ce"
    ),
    "evidence_sufficiency": (
        "af424423723f377d22fdddd01e396de9a2323db0c9aa59defd57b78076cc5df9"
    ),
    "feature_input_coverage": (
        "73d5909cb47d4cd63efc9e743a706448c8e609e65593f4474d183e759513f580"
    ),
    "input_snapshot_schema": (
        "c90999c6a73574fed161297eefc17ff55f2bdf068b79e5d55d6785f8fd25c69c"
    ),
    "kraken_futures_instrument_metadata_validation": (
        "efeb5be0164582370aea0cefc4c5be8802de80ee551bb77e763c6c713e84ee6e"
    ),
    "liquidation_interval_completeness": (
        "346214ec2b6c6dd7cf5b31b76134d85756d2a1a7aaa7e7006199c8a2c0ff2522"
    ),
    "liquidation_utc_day_census": (
        "7180ad6cb78f2abe03308618ab369e94509bb20c3f4bb8b7ac9535abb190a4a2"
    ),
    "metric_evidence_contracts": (
        "98746db2d5d8d9a7d2d5846a83333ff356c6747f39949c2c0bdae38f799e3c98"
    ),
    "portfolio_track_contract": (
        "92887cc240c77ebcea24eb5e9b521fda84f036f33e1d033eea663587cd5360f4"
    ),
    "prospective_btc_market_cap_acquisition": (
        "76738c92292058c557a9828d3b1d8c2e88fee591b2ef37096f01c163a590a798"
    ),
    "prospective_clock_integrity": (
        "be449ebd62b7bcc8cf90ea8c9b38d3fb06f382ff16cc19a5cb04ff9697823ef2"
    ),
    "prospective_cvd_acquisition": (
        "65ff928b3eaed7eba7db9f5ebd7f0a0c06e79648218dc851ca993960b896390f"
    ),
    "prospective_liquidation_capture": (
        "d4268aa2833b8f386777729ae69c9625895b477733c1a62866ea896d141798c8"
    ),
    "prospective_liquidation_percentile_adapter": (
        "606e3930d32f13550b86c6db918782274bd1758a5548dea147771eb766b215b7"
    ),
    "scientific_evidence_resolver": (
        "ea8ce4f3c79638b322a3c9c354ed38f8b2f2689b5dc79c1538aa2b9b9e41ac1e"
    ),
    "semantic_diff_from_v5_blockers": (
        "49b129afd07a08ddfbe6b4195e648b7ab28f712a3d2747739ec139ef7965673d"
    ),
    "source_stream_epoch": (
        "b8e35f3bc14252334d1a651c3a6e28cb1685cfcfb4e415ab5b9e8f73bb6434e5"
    ),
    "stage_b_evaluation_contract": (
        "a98c161de21ecb31467fbd73c80f606e2999bd1843429976147ec46d299212f0"
    ),
    "stop_event_taxonomy": (
        "ebd2d322db1994332844a6a597fcad7673b61632fb34f1361e758546af6e971e"
    ),
    "stream_liveness_policy": (
        "efe9402aa3721234cfe7d05791d3735b817d96130dc359acc50d102d2c0f80a5"
    ),
    "warmup_history": (
        "71af8a1a0fe31e60d0be3bd37292a73f174b8112b731eb619d41ad26d1de50ac"
    ),
}


def inherited_v1_child_bindings() -> dict[str, Any]:
    """Bind every certified V1 child by hash and say what V2 does with it."""

    parent = _v1.protocol_definition()
    children = dict(parent["child_definition_sha256"])
    if parent["definition_sha256"] != PARENT_V1_DEFINITION_SHA256:
        raise ProspectiveCorpusV2Error(
            "the certified parent no longer reproduces to its frozen hash; V2 "
            "refuses to build on a moved parent"
        )
    if parent["material_child_count"] != len(children):
        raise ProspectiveCorpusV2Error("the certified parent's child count moved")
    if sorted(children) != sorted(_FROZEN_V1_CHILD_SHA256):
        raise ProspectiveCorpusV2Error(
            "the certified parent's child inventory no longer matches V2's "
            "frozen commitment to it"
        )
    moved = sorted(
        name
        for name, sha256 in children.items()
        if sha256 != _FROZEN_V1_CHILD_SHA256[name]
    )
    if moved:
        raise ProspectiveCorpusV2Error(
            f"certified V1 children moved since V2 pinned them: {moved}; V2 "
            "refuses to build on a mutated parent"
        )
    rows: dict[str, Any] = {}
    for name, sha256 in sorted(children.items()):
        if name in _V1_CHILDREN_SUPERSEDED_BY_V2:
            disposition = "SUPERSEDED_FOR_REPLAY_CLOSURE_V1_RETAINED_IMMUTABLE"
            successors: tuple[str, ...] = (_V1_CHILDREN_SUPERSEDED_BY_V2[name],)
        elif name in _V1_CHILDREN_EXTENDED_BY_V2:
            disposition = "EXTENDED_BY_A_NEW_V2_CHILD_V1_SEMANTICS_UNCHANGED"
            successors = _V1_CHILDREN_EXTENDED_BY_V2[name]
        else:
            disposition = "REUSED_UNCHANGED_BY_HASH"
            successors = ()
        rows[name] = {
            "disposition": disposition,
            "v1_definition_sha256": sha256,
            "v2_successors": list(successors),
        }
    payload = {
        "certified_parent_child_count": len(children),
        "certified_parent_sha256": parent["definition_sha256"],
        "certified_parent_version": parent["protocol_version"],
        "extended_count": sum(
            1 for row in rows.values() if row["disposition"].startswith("EXTENDED")
        ),
        "protocol_version": PROTOCOL_VERSION,
        "reused_unchanged_count": sum(
            1 for row in rows.values() if row["disposition"] == "REUSED_UNCHANGED_BY_HASH"
        ),
        "rows": rows,
        "schema_version": "PROSPECTIVE_INHERITED_V1_CHILD_BINDINGS_V2",
        "superseded_count": sum(
            1 for row in rows.values() if row["disposition"].startswith("SUPERSEDED")
        ),
        "v1_artifact_directory": _v1.OUTPUT_NAMESPACE,
        "v1_child_hashes_verified_against_v2_commitment": True,
        "v1_mutated": bool(moved) or parent["definition_sha256"] != (
            PARENT_V1_DEFINITION_SHA256
        ),
        "v1_mutation_check": (
            "the certified parent hash and all 25 of its child hashes are "
            "compared against V2's own frozen transcription of them on every "
            "build; a single moved byte refuses"
        ),
        "v2_artifact_directory": OUTPUT_NAMESPACE,
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


# ---------------------------------------------------------------------------
# 13e. the V1 -> V2 semantic diff
# ---------------------------------------------------------------------------

SEMANTIC_DIFF_VERSION = "PROSPECTIVE_INTEGRATION_CORPUS_V1_TO_V2_SEMANTIC_DIFF"

PERMITTED_V2_CHANGES = (
    "new evidence manifests",
    "new transitive references",
    "new parent replay contracts",
    "new portfolio state/transition cross-binding",
    "derived/cache fields demoted from authority",
    "schema/version changes required to support replay",
)


def _metric_parity() -> dict[str, Any]:
    """Compare the live certified gate authority against V2's frozen commitment.

    The comparison is deliberately *not* between two readings of the same
    authority: that would move together under an upstream change and report zero
    forever. The left side is the live
    ``historical_gate_authority`` / ``metric_evidence_contracts`` pair, and the
    right side is ``_FROZEN_STAGE_B_GATES``, transcribed into this module. A
    disagreement is a real change and it refuses the build.
    """

    authority = _v1.historical_gate_authority()
    contracts = _v1.metric_evidence_contracts()["contracts"]
    matrix = metric_replay_closure_matrix()["rows"]
    if sorted(_FROZEN_STAGE_B_GATES) != sorted(_v1.TARGET_METRICS):
        raise ProspectiveCorpusV2Error(
            "V2's frozen Stage-B commitment no longer covers the frozen metric "
            "set exactly"
        )
    rows: dict[str, Any] = {}
    changes = {
        "direction_changes": 0,
        "hard_role_changes": 0,
        "metric_intent_changes": 0,
        "threshold_changes": 0,
    }
    for metric in _v1.TARGET_METRICS:
        gate = authority[metric]
        contract = contracts[metric]
        row = matrix[metric]
        frozen = _FROZEN_STAGE_B_GATES[metric]
        # Every comparison crosses the boundary: live authority on one side,
        # V2's own frozen literal on the other. The published matrix is checked
        # against the same commitment, so a moved number cannot reach an
        # artifact by agreeing with itself.
        threshold_changed = int(
            gate["threshold"] != frozen["threshold"]
            or row["threshold"] != frozen["threshold"]
        )
        direction_changed = int(
            gate["direction"] != frozen["direction"]
            or row["direction"] != frozen["direction"]
        )
        hard_changed = int(
            gate["hard"] != frozen["hard"] or row["hard"] != frozen["hard"]
        )
        intent_changed = int(
            contract["universe"] != frozen["universe"]
            or contract["cadence"] != frozen["cadence"]
            or contract["evidence_owner"] != frozen["evidence_owner"]
            or contract["statistic"] != frozen["statistic"]
            or row["universe"] != frozen["universe"]
            or row["cadence"] != frozen["cadence"]
            or row["authoritative_owner"] != frozen["evidence_owner"]
        )
        changes["threshold_changes"] += threshold_changed
        changes["direction_changes"] += direction_changed
        changes["hard_role_changes"] += hard_changed
        changes["metric_intent_changes"] += intent_changed
        rows[metric] = {
            "direction": frozen["direction"],
            "direction_changed": bool(direction_changed),
            "hard": frozen["hard"],
            "hard_role_changed": bool(hard_changed),
            "historical_definition": gate["definition"],
            "metric_intent_changed": bool(intent_changed),
            "statistic": frozen["statistic"],
            "threshold": frozen["threshold"],
            "threshold_changed": bool(threshold_changed),
            "universe": frozen["universe"],
        }
    return {
        "changes": changes,
        "comparison_basis": (
            "live certified gate authority and metric evidence contracts versus "
            "V2's own frozen transcription; never one authority against itself"
        ),
        "rows": rows,
    }


def _feature_parity() -> dict[str, Any]:
    """Recompute per-feature semantic parity against the certified parent."""

    census = owner_evaluability_census()
    warmup = _v1.warmup_history_contract()["rows"]
    coverage = _v1.feature_input_coverage_contract()["rows"]
    changed: list[str] = []
    relabelled: list[str] = []
    for feature, row in census["rows"].items():
        if row["owner_contract"] != warmup[feature]["owner"]:
            changed.append(feature)
        if row["resolved_feature_owner"] != coverage[feature][
            "deterministic_feature_owner"
        ]:
            relabelled.append(feature)
    return {
        "feature_semantic_changes": len(changed),
        "features_with_a_changed_owner": sorted(changed),
        "owner_labels_corrected_to_a_resolving_symbol": sorted(relabelled),
        "owner_label_correction_is_a_science_change": False,
    }


def semantic_diff_v1_to_v2() -> dict[str, Any]:
    """Demonstrate mechanically that V2 changes no trading or metric science."""

    metrics = _metric_parity()
    features = _feature_parity()
    parent = _v1.protocol_definition()
    source_reuse = source_evidence_reuse_contract()
    changes = {
        "acquisition_source_changes": 0,
        "decision_rule_changes": 0,
        "feature_formula_changes": features["feature_semantic_changes"],
        "metric_intent_changes": metrics["changes"]["metric_intent_changes"],
        "risk_changes": 0,
        "stage_b_direction_changes": metrics["changes"]["direction_changes"],
        "stage_b_threshold_changes": metrics["changes"]["threshold_changes"],
        "stage_b_hard_role_changes": metrics["changes"]["hard_role_changes"],
        "stop_event_definition_changes": 0,
    }
    if source_reuse["redesigned"]:  # pragma: no cover - defensive
        changes["acquisition_source_changes"] = 1
    if _v1.RISK_SIZE_FORMULA != (
        "abs(candidate_position_notional - control_position_notional) / "
        "control_position_notional"
    ) or RISK_SIZING_OWNER_VERSION != _sizing.INITIAL_POSITION_SIZE_POLICY_VERSION:
        changes["risk_changes"] = 1
    if (
        _v1.STOP_EVENT_CLASSIFIER_VERSION
        != active_stop_membership_contract()["stop_event_classifier_version"]
        or _v1.STOP_EVENT_UNIVERSE_ANCHOR
        != active_stop_membership_contract()["stop_event_universe_anchor"]
    ):  # pragma: no cover - defensive
        changes["stop_event_definition_changes"] = 1
    if set(TRANSITION_CLASS_BY_EVENT) != set(_state_machine.POSITION_EVENTS):
        changes["decision_rule_changes"] = 1
    nonzero = sorted(name for name, count in changes.items() if count)
    if nonzero:
        raise ProspectiveCorpusV2Error(
            f"V2 must change no trading, source, metric, threshold, risk or "
            f"stop-event science, but found changes in {nonzero}"
        )
    payload = {
        "changes": changes,
        "expected_semantic_parity_with_v1": {
            "direction_changes": 0,
            "feature_semantic_changes": 0,
            "hard_role_changes": 0,
            "metric_intent_changes": 0,
            "risk_semantic_changes": 0,
            "source_semantic_changes": 0,
            "stop_event_semantic_changes": 0,
            "threshold_changes": 0,
        },
        "feature_parity": features,
        "metric_parity": metrics["rows"],
        "parent_v1_sha256": parent["definition_sha256"],
        "permitted_v2_changes": list(PERMITTED_V2_CHANGES),
        "preserved_unchanged": [
            "provider and source identities",
            "CoinGecko acquisition semantics",
            "Kraken acquisition semantics",
            "clock-integrity semantics",
            "stream-completeness semantics",
            "CVD definition",
            "liquidation definition",
            "the 33 feature scientific definitions",
            "decision cadences",
            "the point-in-time rule",
            "warmup scientific predicates",
            "regime and setup definitions",
            "the stop-event taxonomy",
            "portfolio economic semantics",
            "trade-action semantics",
            "trade-eligibility semantics",
            "risk-sizing semantics",
            "Stage-B metric definitions, thresholds, directions, hard roles and intent",
        ],
        "protocol_version": PROTOCOL_VERSION,
        "schema_version": SEMANTIC_DIFF_VERSION,
        "v2_changes_are_evidence_architecture_only": True,
        "what_v2_adds": {
            "cached_fields_demoted": [
                "warmup_history_complete becomes a non-authoritative cached "
                "projection that must equal the replayed owner-specific result",
            ],
            "new_cross_bindings": [
                "a state binds its predecessor record and its producing transition",
                "a transition binds its exact prior state and action evidence",
                "a stop event binds the control state whose replay carries its stop",
                "a risk evaluation binds every input its owner consumes",
            ],
            "new_manifests": [
                OWNER_HISTORY_MANIFEST_KIND,
                SLOT_EVIDENCE_MANIFEST_KIND,
            ],
            "new_replay_contracts": sorted(
                parent_replay_contract_registry()["contracts"]
            ),
            "numerical_context_pinning": PORTFOLIO_NUMERICAL_CONTEXT_RULE,
            "owner_label_correction": (
                "Four certified-parent feature-owner labels do not resolve to a "
                "real symbol. V2 records both the parent's label and the "
                "resolving symbol -- which is the parent's own evaluability "
                "owner in every case -- and verifies the latter imports. The "
                "predicate measured is unchanged; only the label is corrected, "
                "in a new V2 child, leaving the certified V1 child untouched."
            ),
            "slot_identity_space": SLOT_IDENTITY_DERIVATION,
        },
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


# ---------------------------------------------------------------------------
# 13f. the parent-completeness acceptance demonstration
# ---------------------------------------------------------------------------

SYNTHETIC_ACCEPTANCE_CORPUS_SHA256 = _digest(
    {"purpose": "PROSPECTIVE_INTEGRATION_CORPUS_V2_SYNTHETIC_ACCEPTANCE"}
)
SYNTHETIC_ACCEPTANCE_ANCHOR = datetime(2026, 9, 10, tzinfo=UTC)
SYNTHETIC_ACCEPTANCE_SYMBOL = "BTCUSD"

REQUIRED_BLIND_FACTS = (
    "active-stop membership",
    "comparability",
    "control-position root lifecycle",
    "genuine paired sizing opportunity",
    "metric universe membership",
    "point-in-time visibility",
    "regime/setup/action/eligibility owner state",
    "source quality",
    "warmup/evaluability",
)

SURROGATES_NOT_REQUIRED = (
    "active_stop_membership",
    "comparability Boolean",
    "control root SHA",
    "quality_state",
    "sizing-opportunity Boolean",
    "universe Boolean",
    "warmup Boolean",
)


def _synthetic_account_record() -> dict[str, Any]:
    with _decimal_module.localcontext(_OWNER_CONTEXT):
        return _account.PaperAccount(
            feature_id=_account.PAPER_ACCOUNT_FEATURE_ID,
            policy_version=_account.PAPER_ACCOUNT_POLICY_VERSION,
            account_name="prospective-synthetic",
            base_currency="USD",
            starting_nav=Decimal(_v1.INITIAL_PORTFOLIO_STATE["cash_balance"]),
            cash=Decimal(_v1.INITIAL_PORTFOLIO_STATE["cash_balance"]),
            reserved_cash=Decimal("0"),
            realized_pnl=Decimal(_v1.INITIAL_PORTFOLIO_STATE["realized_pnl"]),
            fees_paid=Decimal("0"),
            funding_paid=Decimal("0"),
            costs=_account.ExecutionCosts(
                policy_version=_account.EXECUTION_COST_POLICY_VERSION,
                fee_bps=Decimal("5"),
                slippage_bps=Decimal("2"),
                funding_cost_bps_per_day=Decimal("1"),
            ),
            status=_account.ACCOUNT_ACTIVE,
            created_at=SYNTHETIC_ACCEPTANCE_ANCHOR,
            config_metadata={
                "config_version": "strategy_config_v2",
                "parameter_set_id": "default_phase1",
                "strategy_version": "swing_v1.2",
            },
            reason_codes=("PAPER_ACCOUNT_OPENED",),
        ).as_record()


def demonstrate_parent_completeness(
    census: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one complete synthetic slot graph and derive every blind fact.

    This is the acceptance test of the whole ticket, run as a construction
    rather than an assertion: if a future sufficiency layer could not derive a
    required fact from V2 parent evidence alone, this function could not return
    it. Everything here is synthetic; nothing is collected.
    """

    census = census if census is not None else owner_evaluability_census()
    corpus = SYNTHETIC_ACCEPTANCE_CORPUS_SHA256
    store = EvidenceStore()
    daily = decision_slot(_v1.STRATEGY_DAILY_CADENCE, SYNTHETIC_ACCEPTANCE_ANCHOR)
    seed_complete_slot_evidence(
        store, slot=daily, corpus_sha256=corpus, census=census
    )
    owner_manifests = build_slot_owner_history_graph(
        store, slot=daily, corpus_sha256=corpus, census=census
    )
    evaluability = replay_decision_evaluability(
        store,
        slot=daily,
        corpus_sha256=corpus,
        owner_manifest_sha256s=owner_manifests,
        census=census,
    )

    references = {
        role: store.put(
            reference_evaluation_record(
                corpus_sha256=corpus,
                slot=daily,
                reference_role=role,
                reference_identity=f"SYNTHETIC_{role}",
                reference_ohlc={
                    "close": "100000",
                    "high": "101000",
                    "low": "99000",
                    "open": "99500",
                },
                input_record_sha256s=[],
                available_at=daily.decision_time,
            )
        )
        for role in sorted(_v1.REFERENCE_ROLES)
    }
    decision_outputs = {
        owner: {
            track: store.put(
                decision_owner_output_record(
                    corpus_sha256=corpus,
                    slot=daily,
                    track=track,
                    owner=owner,
                    owner_version=DECISION_OWNER_VERSIONS[owner],
                    output={"state": f"SYNTHETIC_{owner}"},
                    input_record_sha256s=[],
                    owner_history_manifest_sha256s=owner_manifests,
                )
            )
            for track in sorted(_v1.PORTFOLIO_TRACKS)
        }
        for owner in DECISION_OWNERS
    }
    account_record = _synthetic_account_record()
    # The genesis state precedes every transition in wall-clock order: a
    # predecessor later than its successor is refused, and rightly so.
    genesis_slot = decision_slot(
        _v1.STOP_HOURLY_CADENCE, SYNTHETIC_ACCEPTANCE_ANCHOR - timedelta(hours=1)
    )
    genesis = {
        track: build_portfolio_genesis_state(
            store,
            track=track,
            corpus_sha256=corpus,
            slot=genesis_slot,
            symbol=SYNTHETIC_ACCEPTANCE_SYMBOL,
            account_record=account_record,
        )
        for track in sorted(_v1.PORTFOLIO_TRACKS)
    }
    role_by_track = {
        _v1.CANDIDATE_TRACK: _v1.CANDIDATE_REFERENCE_ROLE,
        _v1.CONTROL_TRACK: _v1.CONTROL_REFERENCE_ROLE,
    }
    risk_records = {
        role_by_track[track]: build_risk_evaluation(
            store,
            corpus_sha256=corpus,
            slot=daily,
            track=track,
            reference_role=role_by_track[track],
            reference_identity=f"SYNTHETIC_{role_by_track[track]}",
            sizing_inputs={
                "entry_price": "100000",
                "maximum_notional_fraction_nav": None,
                "nav": _v1.INITIAL_PORTFOLIO_STATE["nav"],
                "risk_fraction_nav": "0.005",
                "stop_distance_fraction": (
                    "0.05" if track == _v1.CONTROL_TRACK else "0.052"
                ),
            },
            trade_permitted=True,
            input_record_sha256s=[genesis[track]],
        )
        for track in sorted(_v1.PORTFOLIO_TRACKS)
    }
    sizing = prove_paired_sizing_opportunity(
        store,
        slot=daily,
        corpus_sha256=corpus,
        risk_record_sha256_by_role=risk_records,
    )

    hourly = decision_slot(
        _v1.STOP_HOURLY_CADENCE, SYNTHETIC_ACCEPTANCE_ANCHOR + timedelta(hours=1)
    )
    enter = build_portfolio_transition(
        store,
        track=_v1.CONTROL_TRACK,
        corpus_sha256=corpus,
        slot=hourly,
        prior_state_record_sha256=genesis[_v1.CONTROL_TRACK],
        position_events=[
            position_event(
                event=_state_machine.ARM_ENTRY, event_time=hourly.decision_time
            ),
            position_event(
                event=_state_machine.ENTER,
                event_time=hourly.decision_time,
                quantity="3",
                price="100000",
                stop_price="95000",
                source_feature_id="INITIAL_STOP",
                source_record_id="SYNTHETIC_STOP_1",
            ),
        ],
        action_evidence_record_sha256=decision_outputs[DECISION_OWNER_TRADE_ACTION][
            _v1.CONTROL_TRACK
        ],
        stop_evidence_record_sha256=decision_outputs[DECISION_OWNER_TRADE_ACTION][
            _v1.CONTROL_TRACK
        ],
        risk_evidence_record_sha256=risk_records[_v1.CONTROL_REFERENCE_ROLE],
    )
    opened = build_portfolio_state(
        store,
        corpus_sha256=corpus,
        slot=hourly,
        prior_state_record_sha256=genesis[_v1.CONTROL_TRACK],
        producing_transition_record_sha256=enter,
    )
    moved_slot = decision_slot(
        _v1.STOP_HOURLY_CADENCE, SYNTHETIC_ACCEPTANCE_ANCHOR + timedelta(hours=2)
    )
    stop_move = build_portfolio_transition(
        store,
        track=_v1.CONTROL_TRACK,
        corpus_sha256=corpus,
        slot=moved_slot,
        prior_state_record_sha256=opened,
        position_events=[
            position_event(
                event=_state_machine.STOP_MOVE,
                event_time=moved_slot.decision_time,
                stop_price="96000",
                source_feature_id="TRAILING_STOP",
                source_record_id="SYNTHETIC_STRUCTURE_1",
            )
        ],
        action_evidence_record_sha256=decision_outputs[DECISION_OWNER_TRADE_ACTION][
            _v1.CONTROL_TRACK
        ],
        stop_evidence_record_sha256=decision_outputs[DECISION_OWNER_TRADE_ACTION][
            _v1.CONTROL_TRACK
        ],
    )
    moved = build_portfolio_state(
        store,
        corpus_sha256=corpus,
        slot=moved_slot,
        prior_state_record_sha256=opened,
        producing_transition_record_sha256=stop_move,
    )
    # The stop event is evaluated on a later bar than the one whose decision
    # moved the stop, because the stop in force while a bar forms is the one the
    # track already carried when that bar opened.
    event_slot = decision_slot(
        _v1.STOP_HOURLY_CADENCE, SYNTHETIC_ACCEPTANCE_ANCHOR + timedelta(hours=4)
    )
    providers = [
        store.put(
            source_observation_record(
                corpus_sha256=corpus,
                series_id=SERIES_CANONICAL_HOURLY_BAR,
                observation_time=event_slot.observation_time,
                available_at=event_slot.decision_time,
                value="94000",
                provider=provider,
            )
        )
        for provider in sorted(_v1.REQUIRED_PROVIDER_IDS)
    ]
    stop_event = build_stop_event(
        store,
        corpus_sha256=corpus,
        slot=event_slot,
        control_state_record_sha256=moved,
        provider_observation_sha256s=providers,
        candidate_reference_record_sha256=references[_v1.CANDIDATE_REFERENCE_ROLE],
        classification=_v1.EVENT_CROSS_MARKET,
    )
    membership = prove_active_stop_membership(
        store, stop_event_record_sha256=stop_event, corpus_sha256=corpus
    )
    root = derive_root_opening_transition(
        store, state_record_sha256=moved, corpus_sha256=corpus
    )

    daily_manifest = build_slot_evidence_manifest(
        store,
        slot=daily,
        corpus_sha256=corpus,
        owner_history_manifest_sha256s=owner_manifests,
        decision_owner_record_sha256s=decision_outputs,
        portfolio_state_record_sha256s=genesis,
        reference_evaluation_record_sha256s=references,
        risk_evaluation_record_sha256s=risk_records,
    )
    observation = build_decision_observation(
        store,
        corpus_sha256=corpus,
        slot=daily,
        slot_evidence_manifest_sha256=daily_manifest,
        strategy_identity_sha256=_digest({"strategy": "SYNTHETIC"}),
        observation_state=_v1.STATE_EVALUATED,
        cached_projections={
            "warmup_history_state": evaluability["derived_warmup_state"]
        },
        portfolio_context_record_sha256s=genesis,
    )
    replayed = replay_decision_observation(
        store, observation_sha256=observation, slot=daily, corpus_sha256=corpus
    )

    hourly_manifest = build_slot_evidence_manifest(
        store,
        slot=event_slot,
        corpus_sha256=corpus,
        owner_history_manifest_sha256s={},
        stop_event_record_sha256=stop_event,
        source_acquisition_record_sha256s=providers,
    )
    hourly_replay = replay_slot_evidence_manifest(
        store,
        manifest_sha256=hourly_manifest,
        slot=event_slot,
        corpus_sha256=corpus,
        census=census,
    )
    return {
        "daily_slot_evidence_manifest_sha256": daily_manifest,
        "daily_slot_id": daily.slot_id,
        "decision_observation_sha256": observation,
        "derived_warmup_state": replayed["derived_warmup_state"],
        "evidence_record_count": len(store),
        "hourly_slot_evidence_manifest_sha256": hourly_manifest,
        "hourly_slot_id": event_slot.slot_id,
        "stop_move_slot_id": moved_slot.slot_id,
        "owner_history_manifest_count": len(owner_manifests),
        "root_opening_transition_sha256": root["root_opening_transition_sha256"],
        "sizing_relative_difference": sizing["relative_difference"],
        "stop_membership_active_stop": membership["active_stop"],
        "stop_membership_proved": membership["membership_proved"],
        "stop_membership_root_sha256": membership[
            "root_opening_transition_sha256"
        ],
        "stop_replay_membership_proved": (
            hourly_replay["stop_membership"]["membership_proved"]
        ),
    }


def parent_completeness_acceptance() -> dict[str, Any]:
    """Freeze the fact-by-fact acceptance the demonstration establishes."""

    demonstration = demonstrate_parent_completeness()
    if demonstration["derived_warmup_state"] != WARMUP_STATE_COMPLETE:
        raise ProspectiveCorpusV2Error(
            "the acceptance demonstration did not derive a complete warmup state"
        )
    if not demonstration["stop_membership_proved"]:
        raise ProspectiveCorpusV2Error(
            "the acceptance demonstration did not prove active-stop membership"
        )
    facts = {
        "active-stop membership": (
            "prove_active_stop_membership re-derives the control track's active "
            "stop and its identity from the verified transition graph"
        ),
        "comparability": (
            "the slot manifest binds both reference evaluations and both tracks' "
            "portfolio states, and the replay refuses a substituted role, track "
            "or slot"
        ),
        "control-position root lifecycle": (
            "derive_root_opening_transition walks the verified chain to the ENTER "
            "that opened the current position"
        ),
        "genuine paired sizing opportunity": (
            "prove_paired_sizing_opportunity re-runs the sizing owner for both "
            "roles from their own bound inputs and requires distinct identities, "
            "distinct tracks, completeness and strict positivity"
        ),
        "metric universe membership": (
            "the metric replay-closure matrix names the V2 references each "
            "universe predicate needs and all eight are replayable"
        ),
        "point-in-time visibility": (
            "every owner-history reference is resolved under the frozen "
            "revision rule and a future-available record is excluded and refused"
        ),
        "regime/setup/action/eligibility owner state": (
            "each decision owner's output is a content-addressed record bound to "
            "its slot, track and owner-history manifests"
        ),
        "source quality": (
            "each observation carries a frozen feed status, adverse statuses "
            "enter the manifest as adverse evidence, and the certified source "
            "layer is bound unchanged by hash"
        ),
        "warmup/evaluability": (
            "replay_decision_evaluability reruns every required owner's own "
            "predicate over its resolved history and refuses a disagreeing cache"
        ),
    }
    if sorted(facts) != sorted(REQUIRED_BLIND_FACTS):
        raise ProspectiveCorpusV2Error(
            "the acceptance map does not cover every required blind fact"
        )
    payload = {
        "demonstration": demonstration,
        "demonstration_owner": (
            f"{_REPLAY_MODULE}.demonstrate_parent_completeness"
        ),
        "demonstration_sha256": _digest(demonstration),
        "invented_outside_the_parent_graph": [],
        "protocol_version": PROTOCOL_VERSION,
        "required_blind_facts": dict(sorted(facts.items())),
        "schema_version": "PROSPECTIVE_PARENT_COMPLETENESS_ACCEPTANCE_V2",
        "surrogate_authorities_not_required": list(SURROGATES_NOT_REQUIRED),
        "synthetic_evidence_only": SYNTHETIC_EVIDENCE_ONLY,
        "synthetic_evidence_rule": SYNTHETIC_EVIDENCE_RULE,
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


# ===========================================================================
# 14. safety gates
# ===========================================================================

COLLECTION_AUTHORIZED = False
POSTP1_004_AUTHORIZED = False
SUFFICIENCY_GOVERNANCE_ISSUED_HERE = False
BTC019_REOPENED = False
BTC019_SEALED_DATA_ACCESSED = False
EPIC_T_MODIFIED = False

COLLECTION_ENTRY_REQUIREMENT = (
    "V2 qualifying prospective collection may begin only after this corpus "
    "passes an exact-hash independent xHigh review, sufficiency governance is "
    "reissued against the V2 hash and passes its own exact-hash review, and "
    "POSTP1-004 is implemented and passes its independent review."
)

BLOCKED_SUFFICIENCY_GOVERNANCE = {
    "failed_hashes_retained_non_authoritative": list(
        FAILED_SUFFICIENCY_GOVERNANCE_SHA256S
    ),
    "new_governance_hash_issued_here": SUFFICIENCY_GOVERNANCE_ISSUED_HERE,
    "postp1_003r3_blocked_pending_v2_review": True,
    "postp1_003r3_must_then": [
        "bind the V2 parent",
        "perform true owner-level replay",
        "bind executable semantics",
        "enforce canonical candidate/control identity",
    ],
    "postp1_003r3_rules_unchanged": "381 / 93 / 0.99",
    "successor_ticket": BLOCKING_AUDIT_TICKET,
}


def assert_collection_not_authorized() -> None:
    """Refuse any caller that tries to collect before every review passes."""

    if COLLECTION_AUTHORIZED or POSTP1_004_AUTHORIZED:  # pragma: no cover
        raise CollectionNotAuthorizedError(COLLECTION_ENTRY_REQUIREMENT)


# ===========================================================================
# 15. the frozen parent
# ===========================================================================

_CHILD_ARTIFACTS: tuple[tuple[str, str], ...] = (
    ("active_stop_membership_contract.json", "active_stop_membership_contract"),
    ("collection_epoch_contract.json", "collection_epoch_contract"),
    ("data_schema_contract_v2.json", "data_schema_contract_v2"),
    ("decision_evaluability_contract.json", "decision_evaluability_contract"),
    ("decision_observation_contract.json", "decision_observation_contract"),
    ("feature_replay_closure_matrix.json", "feature_replay_closure_matrix"),
    ("inherited_v1_child_bindings.json", "inherited_v1_child_bindings"),
    ("metric_replay_closure_matrix.json", "metric_replay_closure_matrix"),
    ("owner_evaluability_census.json", "owner_evaluability_census"),
    (
        "owner_history_completeness_contract.json",
        "owner_history_completeness_contract",
    ),
    ("owner_history_manifest_contract.json", "owner_history_manifest_contract"),
    ("parent_completeness_acceptance.json", "parent_completeness_acceptance"),
    ("parent_replay_contract_registry.json", "parent_replay_contract_registry"),
    ("portfolio_state_contract.json", "portfolio_state_contract"),
    ("portfolio_transition_contract.json", "portfolio_transition_contract"),
    (
        "portfolio_transition_replay_contract.json",
        "portfolio_transition_replay_contract",
    ),
    ("risk_opportunity_evidence_contract.json", "risk_opportunity_evidence_contract"),
    ("root_lifecycle_derivation_contract.json", "root_lifecycle_derivation_contract"),
    ("semantic_diff_v1_to_v2.json", "semantic_diff_v1_to_v2"),
    ("slot_evidence_manifest_contract.json", "slot_evidence_manifest_contract"),
    ("source_evidence_reuse_contract.json", "source_evidence_reuse_contract"),
)

_CHILD_KEY_BY_FILENAME = {
    filename: filename[: -len(".json")] for filename, _ in _CHILD_ARTIFACTS
}


def _child_payloads() -> dict[str, dict[str, Any]]:
    return {filename: globals()[builder]() for filename, builder in _CHILD_ARTIFACTS}


def protocol_definition() -> dict[str, Any]:
    """Build the frozen V2 parent, binding every material child by hash."""

    assert_collection_not_authorized()
    children = {
        _CHILD_KEY_BY_FILENAME[filename]: globals()[builder]()
        for filename, builder in _CHILD_ARTIFACTS
    }
    if len({filename for filename, _ in _CHILD_ARTIFACTS}) != len(_CHILD_ARTIFACTS):
        raise ProspectiveCorpusV2Error("the child artifact registry repeats a file")
    inherited = children["inherited_v1_child_bindings"]
    payload: dict[str, Any] = {
        "btc019": {
            "reopened": BTC019_REOPENED,
            "sealed_data_accessed": BTC019_SEALED_DATA_ACCESSED,
            "sealed_sample_collected": False,
            "sealed_sample_opened": False,
            "terminal_classification": _v1.BTC019_TERMINAL_CLASSIFICATION,
        },
        "certification": {
            "certified": False,
            "certification_authority": CERTIFICATION_AUTHORITY,
            "certification_state": CERTIFICATION_STATE,
            "permitted_classifications": list(FAIL_CLOSED_CLASSIFICATIONS),
        },
        "child_definition_sha256": {
            name: child["definition_sha256"] for name, child in children.items()
        },
        "collection_authorized": COLLECTION_AUTHORIZED,
        "collection_entry_requirement": COLLECTION_ENTRY_REQUIREMENT,
        "content_addressed_immutability": {
            "identity_moves_when_any_of_these_change": [
                "a history reference",
                "a predecessor state",
                "a transition",
                "a source record",
                "an owner contract",
                "a slot identity",
            ],
            "rule": children["data_schema_contract_v2"][
                "content_addressed_immutability_rule"
            ],
        },
        "final_classification": FINAL_CLASSIFICATION,
        "lineage": {
            "blocking_audit": {
                "commit": BLOCKING_AUDIT_COMMIT,
                "result": BLOCKING_AUDIT_RESULT,
                "ticket": BLOCKING_AUDIT_TICKET,
            },
            "certified_v1_validator_definition_sha256": (
                CERTIFIED_V1_VALIDATOR_DEFINITION_SHA256
            ),
            "frozen_v3_definition_sha256": FROZEN_V3_DEFINITION_SHA256,
            "frozen_v4_definition_sha256": FROZEN_V4_DEFINITION_SHA256,
            "frozen_v5_definition_sha256": FROZEN_V5_DEFINITION_SHA256,
            "parent_v1": {
                "artifact_directory": _v1.OUTPUT_NAMESPACE,
                "certification": PARENT_V1_CERTIFICATION,
                "classification_now": PARENT_V1_CLASSIFICATION_NOW,
                "classification_after_v2_review_pass": (
                    PARENT_V1_POST_CERTIFICATION_CLASSIFICATION
                ),
                "definition_sha256": PARENT_V1_DEFINITION_SHA256,
                "limitation": PARENT_V1_LIMITATION,
                "limitation_scope": PARENT_V1_LIMITATION_SCOPE,
                "material_child_count": inherited["certified_parent_child_count"],
                "mutated_by_v2": inherited["v1_mutated"],
                "qualifying_observations_collected": (
                    PARENT_V1_QUALIFYING_OBSERVATIONS_COLLECTED
                ),
                "version": PARENT_V1_VERSION,
            },
        },
        "material_child_count": len(children),
        "material_child_enumeration": (
            "mechanically enumerated from the single artifact/builder registry"
        ),
        "no_threshold_authored": True,
        "numerical_standards": {
            "corpus_decimal_precision": CORPUS_DECIMAL_PRECISION,
            "invariant_to": [
                "ambient Decimal precision and rounding",
                "PYTHONHASHSEED",
                "the working directory",
                "process restart",
                "input ordering permutations",
            ],
            "owner_replay_decimal_precision": OWNER_REPLAY_DECIMAL_PRECISION,
            "owner_replay_decimal_rounding": str(OWNER_REPLAY_DECIMAL_ROUNDING),
            "owner_replay_context_owners": list(OWNER_REPLAY_CONTEXT_OWNERS),
            "rule": PORTFOLIO_NUMERICAL_CONTEXT_RULE,
        },
        "primary_requirement": (
            "Every scientifically material blind fact required by Stage-B "
            "sufficiency can be regenerated from immutable persisted parent "
            "evidence without trusting a Boolean, a summary state, a digest-only "
            "leaf, or a governance-authored conclusion."
        ),
        "program_ticket": PROGRAM_TICKET,
        "protocol_version": PROTOCOL_VERSION,
        "record_kinds": list(RECORD_KINDS),
        "relationship_to_epic_t": {
            "epic_t_authority_change_required": False,
            "epic_t_modified": EPIC_T_MODIFIED,
            "epic_t_re_review_required": False,
            "epic_t_state": "CLOSED / PASS WITH NON-BLOCKING FINDINGS",
        },
        "required_replayable_facts": list(REQUIRED_BLIND_FACTS),
        "safety": {
            "btc019_sealed_data_accessed": BTC019_SEALED_DATA_ACCESSED,
            "new_market_evidence_collected": False,
            "persistent_live_collection_started": False,
            "qualifying_observations_collected": False,
            "real_stage_b_evaluated": False,
            "synthetic_evidence_only": SYNTHETIC_EVIDENCE_ONLY,
        },
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "status": PROTOCOL_STATUS,
        "sufficiency_governance": BLOCKED_SUFFICIENCY_GOVERNANCE,
        "surrogate_authorities_not_required": list(SURROGATES_NOT_REQUIRED),
        "target_metrics": list(_v1.TARGET_METRICS),
        "workstream": {"epic": WORKSTREAM, "name": WORKSTREAM_NAME},
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def protocol_hashes() -> dict[str, str]:
    """Every deterministic hash this parent reports."""

    protocol = protocol_definition()
    hashes = dict(protocol["child_definition_sha256"])
    hashes["corpus_protocol_v2"] = protocol["definition_sha256"]
    return dict(sorted(hashes.items()))


def verify_protocol_definition(persisted: Mapping[str, Any]) -> None:
    """Refuse a persisted parent that does not reproduce from the module."""

    expected = protocol_definition()
    if dict(persisted) != expected:
        raise ProspectiveCorpusV2Error("the persisted protocol does not reproduce")
    declared = dict(persisted)["definition_sha256"]
    if not _is_sha256(declared):
        raise ProspectiveCorpusV2Error("definition_sha256 is not a SHA-256 digest")
    recomputed = dict(persisted)
    recomputed.pop("definition_sha256")
    if _digest(recomputed) != declared:
        raise ProspectiveCorpusV2Error("definition_sha256 does not recompute")


# ===========================================================================
# 16. artifacts
# ===========================================================================


def _report_markdown(protocol: Mapping[str, Any]) -> str:
    hashes = protocol["child_definition_sha256"]
    diff = semantic_diff_v1_to_v2()
    metrics = metric_replay_closure_matrix()
    features = feature_replay_closure_matrix()
    acceptance = parent_completeness_acceptance()
    inherited = inherited_v1_child_bindings()
    lines = [
        f"# {PROTOCOL_VERSION}",
        "",
        f"- Program / ticket: `{PROGRAM_TICKET}` -- `{WORKSTREAM} -- {WORKSTREAM_NAME}`",
        f"- Definition hash: `{protocol['definition_sha256']}`",
        f"- Status: `{protocol['status']}`",
        f"- Classification: `{protocol['final_classification']}`",
        f"- Certification: `{protocol['certification']['certification_state']}`",
        f"- Material children: {protocol['material_child_count']}",
        "",
        "## Why V2 exists",
        "",
        "`PROSPECTIVE_INTEGRATION_CORPUS_V1` "
        f"(`{PARENT_V1_DEFINITION_SHA256}`) passed its sixth independent",
        "exact-hash xHigh review and remains immutable historical certified",
        "lineage. It is not modified in place and it is not invalid for any",
        "semantics those reviews accepted. Its one limitation is narrow:",
        "",
        f"> {PARENT_V1_LIMITATION}",
        "",
        f"{PARENT_V1_LIMITATION_SCOPE}",
        "",
        "The POSTP1-003R3 parent-completeness audit found three concrete gaps:",
        "a warmup Boolean with no owner-specific history behind it, a portfolio",
        "state chain that bound neither its predecessor record nor its producing",
        "transition, and governance-authored conclusions filling both holes.",
        "V2 closes them and changes nothing else.",
        "",
        "## Semantic parity with V1",
        "",
        "| change family | count |",
        "| --- | --- |",
    ]
    for name, count in sorted(diff["changes"].items()):
        lines.append(f"| `{name}` | {count} |")
    lines += [
        "",
        "Every count is recomputed on each build from the certified parent's own",
        "gate authority, metric contracts, warmup rows and feature coverage; a",
        "non-zero count refuses the build rather than freezing a drifted parent.",
        "",
        "## Replay closure",
        "",
        f"- Stage-B metrics replayable: **{metrics['replayable_ratio']}**",
        f"- Frozen features replayable: **{features['replayable_ratio']}**",
        f"- Distinct owner classes: {features['owner_class_count']}",
        "- Warmup Boolean authoritative: **NO** -- warmup is a replayed",
        "  derivation and a disagreeing cache refuses",
        "- Slot evidence manifest: "
        f"`{SLOT_EVIDENCE_MANIFEST_KIND}`",
        "- Owner history manifest: "
        f"`{OWNER_HISTORY_MANIFEST_KIND}`",
        "",
        "## Portfolio graph",
        "",
        f"{ACYCLICITY_RULE}",
        "",
        f"- Root lifecycle: {ROOT_LIFECYCLE_RULE}",
        f"- Active stop: {ACTIVE_STOP_MEMBERSHIP_RULE}",
        f"- Exit / re-entry: {EXIT_REENTRY_RULE}",
        "",
        "## Parent-completeness acceptance",
        "",
        "A synthetic graph of "
        f"{acceptance['demonstration']['evidence_record_count']} records and "
        f"{acceptance['demonstration']['owner_history_manifest_count']} owner-history",
        "manifests derives every required blind fact from parent evidence alone.",
        "None of the following is invented outside the parent graph:",
        "",
    ]
    for surrogate in protocol["surrogate_authorities_not_required"]:
        lines.append(f"- `{surrogate}`")
    lines += [
        "",
        "## Inherited V1 children",
        "",
        f"- reused unchanged by hash: {inherited['reused_unchanged_count']}",
        f"- extended by a new V2 child: {inherited['extended_count']}",
        f"- superseded for replay closure: {inherited['superseded_count']}",
        f"- V1 mutated: {inherited['v1_mutated']}",
        "",
        "## Material child hashes",
        "",
        "| child | definition hash |",
        "| --- | --- |",
    ]
    for name in sorted(hashes):
        lines.append(f"| `{name}` | `{hashes[name]}` |")
    lines += [
        "",
        "## Safety",
        "",
        f"- Collection authorized: {protocol['collection_authorized']}",
        f"- POSTP1-004 authorized: {POSTP1_004_AUTHORIZED}",
        "- New sufficiency governance issued here: "
        f"{SUFFICIENCY_GOVERNANCE_ISSUED_HERE}",
        f"- Qualifying observations collected: "
        f"{protocol['safety']['qualifying_observations_collected']}",
        f"- Real Stage-B evaluated: {protocol['safety']['real_stage_b_evaluated']}",
        "- BTC-019 sealed data accessed: "
        f"{protocol['safety']['btc019_sealed_data_accessed']}",
        f"- Epic T modified: {protocol['relationship_to_epic_t']['epic_t_modified']}",
        "",
        f"{COLLECTION_ENTRY_REQUIREMENT}",
        "",
    ]
    return "\n".join(lines) + "\n"


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
            raise ProspectiveCorpusV2Error(f"persisted {filename} does not reproduce")
        if protocol["child_definition_sha256"].get(
            _CHILD_KEY_BY_FILENAME[filename]
        ) != expected["definition_sha256"]:
            raise ProspectiveCorpusV2Error(
                f"the protocol does not bind the persisted {filename} hash"
            )
    if (output_dir / REPORT_FILENAME).read_text(encoding="utf-8") != _report_markdown(
        protocol
    ):
        raise ProspectiveCorpusV2Error("the persisted report does not reproduce")
    return protocol


def main() -> None:  # pragma: no cover - operational artifact writer
    root = Path(__file__).resolve().parents[2]
    protocol = write_artifacts(root / OUTPUT_NAMESPACE)
    print(protocol["definition_sha256"])


if __name__ == "__main__":  # pragma: no cover
    main()
