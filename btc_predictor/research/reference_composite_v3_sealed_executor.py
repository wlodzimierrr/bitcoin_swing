"""One-shot sealed executor for the frozen BTC_REFERENCE_COMPOSITE_V3 protocol.

`BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_V1` is certified
(`VALIDATOR_CERTIFIED_FOR_SEALED_EXECUTION_PREPARATION`) and hashes to
`8e6254e0...c7ffe7`, but it cannot be the executing validator: its own review
recorded that `sealed_execution_authorized` sits *inside* the hashed contract
and `validate_v3_candidate` refuses `SEALED_EXECUTION` unconditionally, so
enabling the one permitted opening necessarily moves the validator hash.

This module is that minimal successor. `BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_V2`
is built by *deriving* the V1 contract at run time and applying one enumerated
delta to it, so no verdict-affecting semantic can drift in silence:

    v1.validator_definition()        the certified parent contract
        |
        v  ALLOWED_CONTRACT_DELTA, and nothing else
    validator_definition()           the executing contract, newly hashed
        |
        v
    prepare_sealed_execution()       authority, lock, collection plan
    record_frozen_collection_manifest()
    begin_sealed_execution()
    execute_sealed_validation()      the only call that may read sealed bytes

Every verdict-affecting computation is *called* on the parent module rather
than reimplemented here: the pair universe, the seven hard requirements, the
composition, the Wilson certification, the soft gate, the diagnostics and the
33 inherited gates are all `_v1.<name>`. What this module adds is the one-shot
sealed-execution control surface -- an explicit authorization flag, a durable
five-state execution lock, a frozen sample-manifest schema, a provenance
binding and a terminal result schema.

Authorization is not execution. Importing this module, building the contract,
verifying artifacts, hashing the definition and running the whole test suite
collect nothing and open nothing: `execute_sealed_validation` is the sole path
to sealed bytes, it refuses without a durable authorization record in
`EXECUTION_STARTED`, and it is never called on real history here. The sealed
2015-07-20..2019-11-30 sample stays uncollected and unopened.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from btc_predictor.data.ohlcv import require_utc_datetime
from btc_predictor.research.price_source_policy import (
    DEFAULT_PRICE_SOURCE_POLICY,
    PRICE_SOURCE_POLICY_VERSION,
    REQUIRED_POLICY_PROVIDER_IDS,
)
from btc_predictor.research.reference_composite_v2 import (
    UNTOUCHED_OOS_END,
    UNTOUCHED_OOS_START,
    V2_METHOD_VERSION,
    guard_untouched_validation_sample,
)
from btc_predictor.research import reference_composite_v3_validator as _v1
from btc_predictor.research.reference_composite_v3_validator import (
    BOUND_PROTOCOL_DEFINITION_SHA256,
    BOUND_PROTOCOL_VERSION,
    EVIDENCE_BUNDLE_SCHEMA_VERSION,
    EXECUTION_MODE_DRY_RUN,
    EXECUTION_MODE_SEALED,
    EXECUTION_MODES,
    HARD_REQUIREMENT_IDS,
    PARENT_PROTOCOL_DEFINITION_SHA256,
    REQUIREMENT_COMPARABILITY,
    REQUIREMENT_DERIVED_LEVEL_REVIEW,
    REQUIREMENT_INHERITED_GATES,
    REQUIREMENT_NOT_COMPARABLE,
    REQUIREMENT_PAIR_COMPLETENESS,
    REQUIREMENT_STRUCTURAL_GATE,
    REQUIREMENT_TRANSFER_GUARD,
    VERDICT_FAIL,
    VERDICT_INSUFFICIENT,
    VERDICT_PASS,
    VERDICT_VOCABULARY,
    SealedExecutionNotAuthorizedError,
    ValidationRecord,
    ValidatorBindingError,
    ValidatorError,
    ValidatorInputError,
    evidence_bundle_digest,
)


# =============================================================================
# identity and the certified parent
# =============================================================================

VALIDATOR_VERSION = "BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_V2"
VALIDATOR_SCHEMA_VERSION = "BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_DEFINITION_V2"
VALIDATOR_RECORD_SCHEMA_VERSION = "BTC_REFERENCE_COMPOSITE_V3_VALIDATION_RECORD_V2"

PARENT_VALIDATOR_VERSION = _v1.VALIDATOR_VERSION
# Retyped rather than imported, so an edit to the parent module cannot make
# this successor agree with itself about the wrong certified contract.
PARENT_VALIDATOR_DEFINITION_SHA256 = (
    "8e6254e0354c04de077bf482ccb6852bfe4299f138d3c97f1ba33859bfc7ffe7"
)
PARENT_VALIDATOR_IMPLEMENTATION_COMMIT = "cc59362fc182fb9108a154a6a3b019b3e41c0631"
PARENT_VALIDATOR_REVIEW_COMMIT = "ac58d30f2cf37d99fadcf4a0924010264c0c03b8"
PARENT_VALIDATOR_REVIEW_RESULT = "PASS_WITH_NON_BLOCKING_FINDINGS"
PARENT_VALIDATOR_CLASSIFICATION = "VALIDATOR_CERTIFIED_FOR_SEALED_EXECUTION_PREPARATION"

# The frozen protocol, retyped for the same reason.
BOUND_PROTOCOL_DEFINITION_SHA256_EXPECTED = (
    "4232e886e7888b85833f778fcba6b2cb3eb5b7d802748aebf3b8adf19c5bf71a"
)

SEALED_EXECUTOR_OUTPUT_NAMESPACE = "research_artifacts/btc019_v3_sealed_executor"
VALIDATOR_DEFINITION_FILENAME = "validator_definition_v2.json"
SEMANTIC_DELTA_FILENAME = "semantic_delta_v1_to_v2.json"
SEALED_EXECUTOR_REPORT_FILENAME = "SEALED_EXECUTOR_REPORT.md"
AUTHORIZATION_FILENAME = "sealed_execution_authorization.json"

REFUSE_TO_PREPARE = "REFUSE_TO_PREPARE_SEALED_EXECUTION"
REFUSE_TO_FREEZE = "REFUSE_TO_FREEZE_EXECUTING_VALIDATOR"
REFUSE_TO_RUN = "REFUSE_TO_RUN"


class SealedExecutionAuthorizationError(ValidatorError):
    """Raised when sealed execution is requested without valid authority."""


class SealedExecutionStateError(ValidatorError):
    """Raised on an illegal, backward or repeated execution-state transition."""


class SealedSampleManifestError(ValidatorError):
    """Raised when a sealed-sample collection manifest is malformed or tampered."""


class SemanticDriftError(ValidatorError):
    """Raised when V2 differs from certified V1 by anything but the allowed delta."""


def _canonical_json(payload: Mapping[str, Any]) -> str:
    """The parent's canonical serialization, reused rather than restated."""

    return _v1._canonical_json(payload)


def _digest(payload: Mapping[str, Any]) -> str:
    return _v1._digest(payload)


# =============================================================================
# 1. authority: both certified hashes reproduce, or nothing is prepared
# =============================================================================

AUTHORITY_RULE_ID = "REFUSE_UNLESS_V3_AND_V1_VALIDATOR_HASHES_BOTH_REPRODUCE_V1"
AUTHORITY_RULE = (
    "Before any executing contract is built, the frozen "
    "BTC_REFERENCE_COMPOSITE_V3 definition must rebuild and restore to "
    f"{BOUND_PROTOCOL_DEFINITION_SHA256_EXPECTED}, and the certified "
    "BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_V1 contract must rebuild to "
    f"{PARENT_VALIDATOR_DEFINITION_SHA256}. Either failing is "
    f"{REFUSE_TO_PREPARE}: there is no fallback by version name, no rebuild "
    "of the parent under changed semantics, and no 'latest validator'."
)


def verify_parent_authority(repository_root: Path) -> dict[str, Any]:
    """Rebuild both certified authorities, or refuse to prepare anything.

    Returns the certified V1 contract. `_v1.validator_definition` itself binds
    the frozen V3 hash, verifies the persisted V3 artifact reproduces from the
    repository, re-evaluates the eight hash-bound Wilson boundaries through
    `certify_pair` and re-counts the 33 inherited gates, so this call is the
    whole parent authority check and not a name comparison beside it.
    """

    if BOUND_PROTOCOL_DEFINITION_SHA256 != BOUND_PROTOCOL_DEFINITION_SHA256_EXPECTED:
        raise ValidatorBindingError(
            f"{REFUSE_TO_PREPARE}: the parent module binds "
            f"{BOUND_PROTOCOL_DEFINITION_SHA256!r}, not the frozen "
            f"{BOUND_PROTOCOL_DEFINITION_SHA256_EXPECTED}"
        )
    parent = _v1.validator_definition(repository_root)
    actual = parent["validator_definition_sha256"]
    if actual != PARENT_VALIDATOR_DEFINITION_SHA256:
        raise ValidatorBindingError(
            f"{REFUSE_TO_PREPARE}: the certified "
            f"{PARENT_VALIDATOR_VERSION} contract rebuilds to {actual!r}, not "
            f"to the reviewed {PARENT_VALIDATOR_DEFINITION_SHA256}"
        )
    if parent["binding"]["bound_protocol_definition_sha256"] != (
        BOUND_PROTOCOL_DEFINITION_SHA256_EXPECTED
    ):
        raise ValidatorBindingError(
            f"{REFUSE_TO_PREPARE}: the certified parent binds another protocol"
        )
    if parent["sealed_sample"]["sealed_execution_authorized"] is not False:
        raise ValidatorBindingError(
            f"{REFUSE_TO_PREPARE}: the certified parent already authorises "
            "sealed execution, so it is not the reviewed non-executing contract"
        )
    return parent


# =============================================================================
# 2. the sealed sample, exactly as the frozen protocol defines it
# =============================================================================

SEALED_WINDOW_START = UNTOUCHED_OOS_START
SEALED_WINDOW_END = UNTOUCHED_OOS_END
# Retyped from the ticket, so neither a module edit nor an import can widen or
# shorten the window without this constant disagreeing.
SEALED_WINDOW_START_ISO = "2015-07-20T21:00:00+00:00"
SEALED_WINDOW_END_ISO = "2019-11-30T23:00:00+00:00"

SEALED_BAR_INTERVAL = "1h"
SEALED_TIMEZONE = "UTC"
SEALED_PROVIDER_IDS = tuple(sorted(REQUIRED_POLICY_PROVIDER_IDS))
CANDIDATE_SERIES_ID = V2_METHOD_VERSION
CANDIDATE_METHOD_VERSION = V2_METHOD_VERSION

SEALED_WINDOW_RULE = (
    "The sealed sample is exactly "
    f"{SEALED_WINDOW_START_ISO}..{SEALED_WINDOW_END_ISO} on {SEALED_BAR_INTERVAL} "
    f"bars in {SEALED_TIMEZONE}, from exactly the "
    f"{PRICE_SOURCE_POLICY_VERSION} required validation providers "
    f"{list(SEALED_PROVIDER_IDS)}. It may be neither broadened nor shortened, "
    "and no other period may be substituted. A collection manifest, an "
    "authorization record or an evidence bundle naming any other window, "
    f"interval, timezone or provider set is {REFUSE_TO_RUN}."
)


def _provider_instrument_symbols() -> dict[str, str]:
    """Instrument identities inherited from the frozen price-source policy."""

    symbols = {
        instrument.provider_id: instrument.symbol
        for instrument in DEFAULT_PRICE_SOURCE_POLICY.instruments
        if instrument.provider_id in SEALED_PROVIDER_IDS
    }
    missing = sorted(set(SEALED_PROVIDER_IDS) - set(symbols))
    if missing:
        raise ValidatorBindingError(
            f"{REFUSE_TO_PREPARE}: {PRICE_SOURCE_POLICY_VERSION} declares no "
            f"instrument for required providers {missing}"
        )
    return symbols


def _provider_exchanges() -> dict[str, str]:
    return {
        instrument.provider_id: instrument.exchange
        for instrument in DEFAULT_PRICE_SOURCE_POLICY.instruments
        if instrument.provider_id in SEALED_PROVIDER_IDS
    }


def sealed_collection_plan() -> list[dict[str, Any]]:
    """The per-provider collection plan, derived from the frozen policy alone."""

    symbols = _provider_instrument_symbols()
    exchanges = _provider_exchanges()
    return [
        {
            "bar_interval": SEALED_BAR_INTERVAL,
            "exchange": exchanges[provider_id],
            "instrument_symbol": symbols[provider_id],
            "price_source_policy_version": PRICE_SOURCE_POLICY_VERSION,
            "provider_id": provider_id,
            "timezone": SEALED_TIMEZONE,
            "window_end": SEALED_WINDOW_END_ISO,
            "window_start": SEALED_WINDOW_START_ISO,
        }
        for provider_id in SEALED_PROVIDER_IDS
    ]


def _verify_sealed_window(start: Any, end: Any, what: str) -> None:
    """Refuse anything but the exact frozen sealed window."""

    if start != SEALED_WINDOW_START_ISO or end != SEALED_WINDOW_END_ISO:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: {what} declares {start!r}..{end!r}, not the "
            f"sealed {SEALED_WINDOW_START_ISO}..{SEALED_WINDOW_END_ISO}"
        )


# =============================================================================
# 3. sealed execution authorization -- explicit, and not sufficient on its own
# =============================================================================

SEALED_EXECUTION_AUTHORIZED = True
ONE_SHOT_EXECUTION = True
REUSE_AFTER_FINALIZED_RUN = "REFUSE"

SEALED_EXECUTION_AUTHORIZATION_RULE = (
    "sealed_execution_authorized is true in this contract and false in the "
    "certified parent: that flag is the whole verdict-affecting delta. "
    "Authorization is necessary and never sufficient. A sealed run additionally "
    "requires an explicit execute_sealed_validation call, the frozen V3 hash, "
    "this contract's own hash, the certified parent hash, the exact sealed "
    "window, a durable authorization record whose derived execution id matches "
    "its own authority, that record in EXECUTION_STARTED, a frozen collection "
    "manifest whose digest the record already carries, and an evidence bundle "
    "whose provenance binds that manifest. Import, contract construction, "
    "definition hashing, artifact verification, preparation and the whole test "
    "suite collect nothing and open nothing."
)

ONE_SHOT_RULE_ID = "BTC019_V3_SEALED_SAMPLE_OPENED_EXACTLY_ONCE_V1"
ONE_SHOT_RULE = (
    "The sealed sample is opened exactly once. A second sealed result for the "
    "same frozen V3 definition hash, the same executing validator hash and the "
    "same sealed sample identity is REFUSE, whether it is requested in the same "
    "process or after a restart. The execution state is durable, never "
    "process-local: it is read from the authorization record before every "
    "transition, no transition may move backwards or repeat, and FINALIZED is "
    "terminal. A finalized run can be re-read but never re-run, and its result "
    "digest is immutable."
)

# --- the execution state machine ---------------------------------------------

STATE_NOT_PREPARED = "NOT_PREPARED"
STATE_PREPARED = "PREPARED"
STATE_COLLECTED_FROZEN = "COLLECTED_FROZEN"
STATE_EXECUTION_STARTED = "EXECUTION_STARTED"
STATE_FINALIZED = "FINALIZED"

EXECUTION_STATES = (
    STATE_NOT_PREPARED,
    STATE_PREPARED,
    STATE_COLLECTED_FROZEN,
    STATE_EXECUTION_STARTED,
    STATE_FINALIZED,
)
_STATE_ORDER = {name: index for index, name in enumerate(EXECUTION_STATES)}
TERMINAL_EXECUTION_STATES = (STATE_FINALIZED,)

TRANSITION_PREPARE = "prepare_sealed_execution"
TRANSITION_FREEZE_COLLECTION = "record_frozen_collection_manifest"
TRANSITION_BEGIN = "begin_sealed_execution"
TRANSITION_FINALIZE = "execute_sealed_validation"

LEGAL_EXECUTION_TRANSITIONS = (
    {"from": STATE_NOT_PREPARED, "to": STATE_PREPARED, "step": TRANSITION_PREPARE},
    {
        "from": STATE_PREPARED,
        "to": STATE_COLLECTED_FROZEN,
        "step": TRANSITION_FREEZE_COLLECTION,
    },
    {
        "from": STATE_COLLECTED_FROZEN,
        "to": STATE_EXECUTION_STARTED,
        "step": TRANSITION_BEGIN,
    },
    {
        "from": STATE_EXECUTION_STARTED,
        "to": STATE_FINALIZED,
        "step": TRANSITION_FINALIZE,
    },
)

EXECUTION_STATE_RULE = (
    "Exactly five states, exactly four legal transitions, strictly forward. A "
    "transition whose source is not the record's current durable state, a "
    "repeat of a state already reached, and any move backwards are all "
    "refused. Only record_frozen_collection_manifest may write a market-derived "
    "field, and only after the raw bytes are already frozen and hashed."
)

EXECUTION_REFUSAL_CONDITIONS = (
    "a finalized execution already exists for this authority",
    "an execution with this authority is already started",
    "the sealed sample manifest has already been consumed by a finalized run",
    "the derived execution id does not match the record's own authority",
    "the executing validator definition hash differs",
    "the frozen V3 definition hash differs",
    "the certified parent validator hash differs",
    "the sealed window differs from the frozen window",
    "no authorization record exists",
    "the authorization record's own digest does not reproduce",
    "sealed_execution_authorized is false",
    "the evidence bundle's provenance does not bind the frozen collection manifest",
)


# =============================================================================
# 4. the durable authorization / lock record
# =============================================================================

AUTHORIZATION_SCHEMA_VERSION = "BTC019_V3_SEALED_EXECUTION_AUTHORIZATION_V1"

AUTHORIZATION_REQUIRED_KEYS = (
    "allowed_provider_ids",
    "authorization_record_sha256",
    "bar_interval",
    "bound_protocol_definition_sha256",
    "candidate_method_version",
    "candidate_series_id",
    "collection_manifest_digest",
    "collection_plan",
    "evidence_bundle_digest",
    "execution_id",
    "execution_result_digest",
    "one_shot_execution",
    "parent_protocol_definition_sha256",
    "parent_validator_definition_sha256",
    "parent_validator_version",
    "price_source_policy_version",
    "reuse_after_finalized_run",
    "schema_version",
    "sealed_window_end",
    "sealed_window_start",
    "state_history",
    "status",
    "timezone",
    "validator_definition_sha256",
    "validator_version",
)

# The market-derived fields. They are null until the step that may legitimately
# write them, and none of them is written by preparation.
MARKET_DERIVED_AUTHORIZATION_FIELDS = (
    "collection_manifest_digest",
    "evidence_bundle_digest",
    "execution_result_digest",
)

EXECUTION_ID_PREFIX = "BTC019_V3_SEALED_EXECUTION_"
EXECUTION_ID_RULE = (
    "The execution id is derived, never chosen: it is the first 32 hexadecimal "
    "characters of the SHA-256 of the canonical authority -- the frozen V3 "
    "hash, this executing validator's hash, the certified parent hash, the "
    "sealed window, the candidate identity and the allowed providers. The same "
    "authority always derives the same id, so a second authorization for the "
    "same authority is detected rather than issued a fresh identity, and any "
    "tamper of an authority field makes the record's own id disagree."
)


def execution_authority(validator_definition_sha256: str) -> dict[str, Any]:
    """The canonical authority every sealed run is bound to."""

    return {
        "allowed_provider_ids": list(SEALED_PROVIDER_IDS),
        "bar_interval": SEALED_BAR_INTERVAL,
        "bound_protocol_definition_sha256": BOUND_PROTOCOL_DEFINITION_SHA256_EXPECTED,
        "candidate_method_version": CANDIDATE_METHOD_VERSION,
        "candidate_series_id": CANDIDATE_SERIES_ID,
        "parent_validator_definition_sha256": PARENT_VALIDATOR_DEFINITION_SHA256,
        "sealed_window_end": SEALED_WINDOW_END_ISO,
        "sealed_window_start": SEALED_WINDOW_START_ISO,
        "timezone": SEALED_TIMEZONE,
        "validator_definition_sha256": validator_definition_sha256,
    }


def derive_execution_id(validator_definition_sha256: str) -> str:
    """Return the deterministic execution id for one authority."""

    return EXECUTION_ID_PREFIX + _digest(
        execution_authority(validator_definition_sha256)
    )[:32]


def _authorization_digest(record: Mapping[str, Any]) -> str:
    body = {
        key: value
        for key, value in record.items()
        if key != "authorization_record_sha256"
    }
    return _digest(body)


def _new_authorization_record(validator_definition_sha256: str) -> dict[str, Any]:
    record: dict[str, Any] = {
        "allowed_provider_ids": list(SEALED_PROVIDER_IDS),
        "bar_interval": SEALED_BAR_INTERVAL,
        "bound_protocol_definition_sha256": BOUND_PROTOCOL_DEFINITION_SHA256_EXPECTED,
        "candidate_method_version": CANDIDATE_METHOD_VERSION,
        "candidate_series_id": CANDIDATE_SERIES_ID,
        "collection_manifest_digest": None,
        "collection_plan": sealed_collection_plan(),
        "evidence_bundle_digest": None,
        "execution_id": derive_execution_id(validator_definition_sha256),
        "execution_result_digest": None,
        "one_shot_execution": ONE_SHOT_EXECUTION,
        "parent_protocol_definition_sha256": PARENT_PROTOCOL_DEFINITION_SHA256,
        "parent_validator_definition_sha256": PARENT_VALIDATOR_DEFINITION_SHA256,
        "parent_validator_version": PARENT_VALIDATOR_VERSION,
        "price_source_policy_version": PRICE_SOURCE_POLICY_VERSION,
        "reuse_after_finalized_run": REUSE_AFTER_FINALIZED_RUN,
        "schema_version": AUTHORIZATION_SCHEMA_VERSION,
        "sealed_window_end": SEALED_WINDOW_END_ISO,
        "sealed_window_start": SEALED_WINDOW_START_ISO,
        "state_history": [
            {
                "from": STATE_NOT_PREPARED,
                "step": TRANSITION_PREPARE,
                "to": STATE_PREPARED,
            }
        ],
        "status": STATE_PREPARED,
        "timezone": SEALED_TIMEZONE,
        "validator_definition_sha256": validator_definition_sha256,
        "validator_version": VALIDATOR_VERSION,
    }
    record["authorization_record_sha256"] = _authorization_digest(record)
    return record


def write_execution_authorization(
    authorization_dir: Path, record: Mapping[str, Any]
) -> Path:
    """Persist the lock record deterministically, so a restart reads it back."""

    authorization_dir.mkdir(parents=True, exist_ok=True)
    path = authorization_dir / AUTHORIZATION_FILENAME
    path.write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="ascii",
    )
    return path


def read_execution_authorization(
    authorization_dir: Path, *, validator_definition_sha256: str
) -> dict[str, Any]:
    """Read the durable lock record, refusing every authority tamper.

    The record is never trusted: its own digest is recomputed, its execution id
    is re-derived from its authority, and every hash, the window, the provider
    set and the candidate identity are compared against this module's bound
    constants. A record that fails any of them cannot authorise anything.
    """

    path = authorization_dir / AUTHORIZATION_FILENAME
    if not path.exists():
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: no {AUTHORIZATION_SCHEMA_VERSION} record exists "
            f"at {AUTHORIZATION_FILENAME}"
        )
    try:
        record = json.loads(path.read_text(encoding="ascii"))
    except (ValueError, UnicodeDecodeError) as error:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: the authorization record is not readable ascii JSON"
        ) from error
    if not isinstance(record, dict):
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: the authorization record is not a mapping"
        )
    missing = sorted(set(AUTHORIZATION_REQUIRED_KEYS) - set(record))
    unknown = sorted(set(record) - set(AUTHORIZATION_REQUIRED_KEYS))
    if missing:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: the authorization record omits {missing}"
        )
    if unknown:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: the authorization record carries unknown fields {unknown}"
        )
    if record["schema_version"] != AUTHORIZATION_SCHEMA_VERSION:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: the record does not carry {AUTHORIZATION_SCHEMA_VERSION}"
        )
    if record["authorization_record_sha256"] != _authorization_digest(record):
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: the authorization record was tampered with"
        )
    expectations = {
        "bound_protocol_definition_sha256": BOUND_PROTOCOL_DEFINITION_SHA256_EXPECTED,
        "candidate_method_version": CANDIDATE_METHOD_VERSION,
        "candidate_series_id": CANDIDATE_SERIES_ID,
        "parent_protocol_definition_sha256": PARENT_PROTOCOL_DEFINITION_SHA256,
        "parent_validator_definition_sha256": PARENT_VALIDATOR_DEFINITION_SHA256,
        "parent_validator_version": PARENT_VALIDATOR_VERSION,
        "validator_definition_sha256": validator_definition_sha256,
        "validator_version": VALIDATOR_VERSION,
    }
    for field, expected in expectations.items():
        if record[field] != expected:
            raise SealedExecutionAuthorizationError(
                f"{REFUSE_TO_RUN}: the authorization record declares "
                f"{field}={record[field]!r}, not {expected!r}"
            )
    _verify_sealed_window(
        record["sealed_window_start"],
        record["sealed_window_end"],
        "the authorization record",
    )
    if list(record["allowed_provider_ids"]) != list(SEALED_PROVIDER_IDS):
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: the authorization record allows providers "
            f"{record['allowed_provider_ids']!r}, not {list(SEALED_PROVIDER_IDS)!r}"
        )
    if record["bar_interval"] != SEALED_BAR_INTERVAL:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: the authorization record names another bar interval"
        )
    if record["timezone"] != SEALED_TIMEZONE:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: the authorization record names another timezone"
        )
    if record["one_shot_execution"] is not True:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: the authorization record disables the one-shot rule"
        )
    if record["reuse_after_finalized_run"] != REUSE_AFTER_FINALIZED_RUN:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: the authorization record permits reuse after a "
            "finalized run"
        )
    expected_id = derive_execution_id(validator_definition_sha256)
    if record["execution_id"] != expected_id:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: the authorization record's execution id "
            f"{record['execution_id']!r} does not derive from its own authority"
        )
    if record["status"] not in EXECUTION_STATES:
        raise SealedExecutionStateError(
            f"{REFUSE_TO_RUN}: unknown execution state {record['status']!r}"
        )
    if record["collection_plan"] != sealed_collection_plan():
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: the authorization record carries another "
            "collection plan than the frozen price-source policy declares"
        )
    return record


def sealed_execution_status(
    authorization_dir: Path, *, validator_definition_sha256: str
) -> str:
    """Return the durable execution state, NOT_PREPARED when none exists."""

    if not (authorization_dir / AUTHORIZATION_FILENAME).exists():
        return STATE_NOT_PREPARED
    record = read_execution_authorization(
        authorization_dir, validator_definition_sha256=validator_definition_sha256
    )
    return record["status"]


def _transition(
    record: dict[str, Any], *, to_state: str, step: str
) -> dict[str, Any]:
    """Move one durable record strictly forward along a declared transition."""

    current = record["status"]
    legal = {
        (row["from"], row["to"]): row["step"] for row in LEGAL_EXECUTION_TRANSITIONS
    }
    if current in TERMINAL_EXECUTION_STATES:
        raise SealedExecutionStateError(
            f"{REFUSE_TO_RUN}: execution {record['execution_id']} is "
            f"{current} and terminal; {ONE_SHOT_RULE_ID} refuses a second run"
        )
    if _STATE_ORDER[to_state] <= _STATE_ORDER[current]:
        raise SealedExecutionStateError(
            f"{REFUSE_TO_RUN}: {current} -> {to_state} is not a forward transition"
        )
    if legal.get((current, to_state)) != step:
        raise SealedExecutionStateError(
            f"{REFUSE_TO_RUN}: {step} requires state "
            f"{[row['from'] for row in LEGAL_EXECUTION_TRANSITIONS if row['step'] == step]}"
            f", not {current}"
        )
    moved = dict(record)
    moved["status"] = to_state
    moved["state_history"] = [dict(row) for row in record["state_history"]] + [
        {"from": current, "step": step, "to": to_state}
    ]
    moved["authorization_record_sha256"] = _authorization_digest(
        {
            key: value
            for key, value in moved.items()
            if key != "authorization_record_sha256"
        }
    )
    return moved


# =============================================================================
# 5. the sealed-sample collection contract and manifest
# =============================================================================

MANIFEST_SCHEMA_VERSION = "BTC019_V3_SEALED_SAMPLE_MANIFEST_V1"

COLLECTION_SEQUENCE = (
    "collect raw provider data",
    "write immutable raw files",
    "compute per-file SHA-256",
    "create the collection manifest",
    "freeze the manifest and record its digest on the authorization record",
    "only then construct the candidate and any derived evidence",
)
COLLECTION_SEQUENCE_RULE = (
    "The raw bytes are frozen before anything is analysed. No candidate is "
    "constructed, no derived evidence is built and no strategy quantity is "
    "computed until every raw file exists, every per-file digest is computed "
    "and the manifest is frozen onto the authorization record. The manifest "
    "may carry no strategy outcome at all: it records what was collected, "
    "never what the collection implies."
)

PRE_FREEZE_ALLOWED_OPERATIONS = (
    "file_readable",
    "schema_valid",
    "timestamps_parse",
    "provider_identity_correct",
    "window_correct",
    "hash_computed",
)
PRE_FREEZE_FORBIDDEN_OPERATIONS = (
    "candidate_performance",
    "gate_results",
    "structural_disagreements",
    "returns",
    "stop_touches",
    "mfe_mae",
    "provider_comparison_results",
)
PRE_FREEZE_RULE = (
    "Before the manifest is frozen the only permitted operations are the "
    f"technical integrity checks {list(PRE_FREEZE_ALLOWED_OPERATIONS)}. "
    f"{list(PRE_FREEZE_FORBIDDEN_OPERATIONS)} are refused, and so is any "
    "research summary of the sealed bytes. Inspecting the sample before its "
    "own manifest is frozen would make the frozen manifest a description of "
    "something already read."
)

# Substrings that would make a manifest field a strategy outcome rather than a
# collection fact. Checked over every key at every depth, so a nested block
# cannot smuggle one in.
FORBIDDEN_MANIFEST_KEY_FRAGMENTS = (
    "breakout",
    "candidate",
    "certif",
    "disagree",
    "gate",
    "mae",
    "mfe",
    "outcome",
    "performance",
    "reclaim",
    "return",
    "stop_touch",
    "swing",
    "verdict",
)

MANIFEST_REQUIRED_KEYS = (
    "bar_interval",
    "bound_protocol_definition_sha256",
    "collection_method",
    "collection_method_version",
    "execution_id",
    "files",
    "manifest_sha256",
    "manifest_version",
    "parent_validator_definition_sha256",
    "provider_ids",
    "timezone",
    "validator_definition_sha256",
    "window_end",
    "window_start",
)
MANIFEST_FILE_REQUIRED_KEYS = (
    "byte_count",
    "collection_source_identifier",
    "duplicate_interval_count",
    "duplicate_intervals",
    "first_observation",
    "last_observation",
    "path",
    "provider_id",
    "raw_mutation_count",
    "row_count",
    "sha256",
    "source_provenance",
)
MANIFEST_PROVENANCE_REQUIRED_KEYS = (
    "endpoint",
    "exchange",
    "instrument_symbol",
    "request_count",
)
MANIFEST_MISSING_KEYS = ("missing_interval_count", "missing_intervals")


def _require_exact_keys(
    payload: Mapping[str, Any], required: Sequence[str], what: str
) -> None:
    missing = sorted(set(required) - set(payload))
    if missing:
        raise SealedSampleManifestError(f"{what} omits required fields {missing}")
    unknown = sorted(set(payload) - set(required))
    if unknown:
        raise SealedSampleManifestError(f"{what} carries unknown fields {unknown}")


def _require_hex_digest(value: Any, what: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise SealedSampleManifestError(f"{what} must be a 64-character sha256 digest")
    if any(character not in "0123456789abcdef" for character in value):
        raise SealedSampleManifestError(f"{what} must be lowercase hexadecimal")
    return value


def _require_count(value: Any, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SealedSampleManifestError(f"{what} must be an integer count")
    if value < 0:
        raise SealedSampleManifestError(f"{what} cannot be negative")
    return value


def _refuse_strategy_outcome_fields(node: Any, path: str = "manifest") -> None:
    """Refuse any manifest key that would record what the collection implies."""

    if isinstance(node, Mapping):
        for key, value in node.items():
            lowered = str(key).lower()
            for fragment in FORBIDDEN_MANIFEST_KEY_FRAGMENTS:
                if fragment in lowered:
                    raise SealedSampleManifestError(
                        f"{path}.{key} is a strategy outcome; a "
                        f"{MANIFEST_SCHEMA_VERSION} manifest records collection "
                        "facts only"
                    )
            _refuse_strategy_outcome_fields(value, f"{path}.{key}")
    elif isinstance(node, (list, tuple)):
        for index, value in enumerate(node):
            _refuse_strategy_outcome_fields(value, f"{path}[{index}]")


def manifest_digest(manifest: Mapping[str, Any]) -> str:
    """Digest one manifest's content, excluding its own declared digest."""

    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    return _digest(body)


def _parse_instant(value: Any, what: str) -> datetime:
    if not isinstance(value, str):
        raise SealedSampleManifestError(f"{what} must be an ISO-8601 UTC instant")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise SealedSampleManifestError(f"{what} is not an ISO-8601 instant") from error
    try:
        return require_utc_datetime(parsed, what)
    except ValueError as error:
        raise SealedSampleManifestError(str(error)) from error


def validate_sealed_sample_manifest(
    manifest: Any,
    *,
    execution_id: str,
    validator_definition_sha256: str,
) -> dict[str, Any]:
    """Return the manifest, or refuse it. Reads no bytes of any collected file."""

    if not isinstance(manifest, Mapping):
        raise SealedSampleManifestError("the collection manifest must be a mapping")
    _refuse_strategy_outcome_fields(manifest)
    _require_exact_keys(manifest, MANIFEST_REQUIRED_KEYS, "the collection manifest")
    if manifest["manifest_version"] != MANIFEST_SCHEMA_VERSION:
        raise SealedSampleManifestError(
            f"the collection manifest does not carry {MANIFEST_SCHEMA_VERSION}"
        )
    if manifest["execution_id"] != execution_id:
        raise SealedSampleManifestError(
            f"the collection manifest names execution {manifest['execution_id']!r}, "
            f"not {execution_id!r}"
        )
    if manifest["bound_protocol_definition_sha256"] != (
        BOUND_PROTOCOL_DEFINITION_SHA256_EXPECTED
    ):
        raise SealedSampleManifestError(
            "the collection manifest binds another frozen V3 definition hash"
        )
    if manifest["validator_definition_sha256"] != validator_definition_sha256:
        raise SealedSampleManifestError(
            "the collection manifest binds another executing validator hash"
        )
    if manifest["parent_validator_definition_sha256"] != (
        PARENT_VALIDATOR_DEFINITION_SHA256
    ):
        raise SealedSampleManifestError(
            "the collection manifest names another certified parent hash"
        )
    _verify_sealed_window(
        manifest["window_start"], manifest["window_end"], "the collection manifest"
    )
    if manifest["bar_interval"] != SEALED_BAR_INTERVAL:
        raise SealedSampleManifestError(
            f"the collection manifest declares bar interval "
            f"{manifest['bar_interval']!r}, not {SEALED_BAR_INTERVAL!r}"
        )
    if manifest["timezone"] != SEALED_TIMEZONE:
        raise SealedSampleManifestError(
            f"the collection manifest declares timezone {manifest['timezone']!r}, "
            f"not {SEALED_TIMEZONE!r}"
        )
    if not isinstance(manifest["collection_method"], str) or not manifest[
        "collection_method"
    ]:
        raise SealedSampleManifestError("the collection manifest omits its method")
    if not isinstance(manifest["collection_method_version"], str) or not manifest[
        "collection_method_version"
    ]:
        raise SealedSampleManifestError(
            "the collection manifest omits its method version"
        )
    providers = manifest["provider_ids"]
    if not isinstance(providers, (list, tuple)):
        raise SealedSampleManifestError("provider_ids must be a list")
    if len(set(providers)) != len(providers):
        raise SealedSampleManifestError(
            "the collection manifest names a provider twice"
        )
    if tuple(sorted(providers)) != SEALED_PROVIDER_IDS:
        raise SealedSampleManifestError(
            f"the collection manifest names providers {sorted(providers)}, not the "
            f"required {list(SEALED_PROVIDER_IDS)}"
        )

    files = manifest["files"]
    if not isinstance(files, (list, tuple)):
        raise SealedSampleManifestError("files must be a list")
    symbols = _provider_instrument_symbols()
    exchanges = _provider_exchanges()
    window_start = _parse_instant(SEALED_WINDOW_START_ISO, "the sealed window start")
    window_end = _parse_instant(SEALED_WINDOW_END_ISO, "the sealed window end")
    seen: set[str] = set()
    for row in files:
        if not isinstance(row, Mapping):
            raise SealedSampleManifestError("every manifest file entry must be a mapping")
        _require_exact_keys(
            row,
            MANIFEST_FILE_REQUIRED_KEYS + MANIFEST_MISSING_KEYS,
            "a manifest file entry",
        )
        provider_id = row["provider_id"]
        if provider_id not in SEALED_PROVIDER_IDS:
            raise SealedSampleManifestError(
                f"the collection manifest carries a file for unexpected provider "
                f"{provider_id!r}"
            )
        if provider_id in seen:
            raise SealedSampleManifestError(
                f"the collection manifest carries {provider_id!r} twice"
            )
        seen.add(provider_id)
        _require_hex_digest(row["sha256"], f"{provider_id} sha256")
        if not isinstance(row["path"], str) or not row["path"]:
            raise SealedSampleManifestError(f"{provider_id} omits its raw file path")
        for field in (
            "byte_count",
            "duplicate_interval_count",
            "missing_interval_count",
            "raw_mutation_count",
            "row_count",
        ):
            _require_count(row[field], f"{provider_id} {field}")
        if row["row_count"] == 0:
            raise SealedSampleManifestError(f"{provider_id} collected no rows at all")
        if row["raw_mutation_count"] != 0:
            raise SealedSampleManifestError(
                f"{provider_id} declares {row['raw_mutation_count']} raw mutations; "
                "frozen raw bytes are never edited"
            )
        for field, count_field in (
            ("missing_intervals", "missing_interval_count"),
            ("duplicate_intervals", "duplicate_interval_count"),
        ):
            intervals = row[field]
            if not isinstance(intervals, (list, tuple)):
                raise SealedSampleManifestError(f"{provider_id} {field} must be a list")
            if len(intervals) != row[count_field]:
                raise SealedSampleManifestError(
                    f"{provider_id} declares {row[count_field]} {field} but lists "
                    f"{len(intervals)}"
                )
            for instant in intervals:
                _parse_instant(instant, f"{provider_id} {field} entry")
        first = _parse_instant(row["first_observation"], f"{provider_id} first_observation")
        last = _parse_instant(row["last_observation"], f"{provider_id} last_observation")
        if first > last:
            raise SealedSampleManifestError(
                f"{provider_id} first observation is after its last"
            )
        if first < window_start or last > window_end:
            raise SealedSampleManifestError(
                f"{provider_id} observations reach outside the sealed window"
            )
        provenance = row["source_provenance"]
        if not isinstance(provenance, Mapping):
            raise SealedSampleManifestError(
                f"{provider_id} omits its source provenance"
            )
        _require_exact_keys(
            provenance,
            MANIFEST_PROVENANCE_REQUIRED_KEYS,
            f"{provider_id} source_provenance",
        )
        if provenance["instrument_symbol"] != symbols[provider_id]:
            raise SealedSampleManifestError(
                f"{provider_id} collected instrument "
                f"{provenance['instrument_symbol']!r}, not the "
                f"{PRICE_SOURCE_POLICY_VERSION} {symbols[provider_id]!r}"
            )
        if provenance["exchange"] != exchanges[provider_id]:
            raise SealedSampleManifestError(
                f"{provider_id} names another exchange than the frozen policy"
            )
        if not isinstance(provenance["endpoint"], str) or not provenance["endpoint"]:
            raise SealedSampleManifestError(f"{provider_id} omits its endpoint")
        _require_count(provenance["request_count"], f"{provider_id} request_count")
        if not isinstance(row["collection_source_identifier"], str) or not row[
            "collection_source_identifier"
        ]:
            raise SealedSampleManifestError(
                f"{provider_id} omits its collection source identifier"
            )
    if tuple(sorted(seen)) != SEALED_PROVIDER_IDS:
        raise SealedSampleManifestError(
            f"the collection manifest carries files for {sorted(seen)}, not the "
            f"required {list(SEALED_PROVIDER_IDS)}"
        )
    declared = manifest["manifest_sha256"]
    _require_hex_digest(declared, "manifest_sha256")
    actual = manifest_digest(manifest)
    if declared != actual:
        raise SealedSampleManifestError(
            f"the collection manifest declares {declared}, but its own content "
            f"digests to {actual}"
        )
    return dict(manifest)


def verify_collected_file_digests(
    manifest: Mapping[str, Any], repository_root: Path
) -> None:
    """Recompute each frozen raw file's digest. Only the NEXT task may call it.

    Hashing a collected file is one of the six technical integrity checks
    `PRE_FREEZE_ALLOWED_OPERATIONS` permits, and it is the check that catches a
    file changed after its digest was recorded. It reads sealed bytes, so it is
    reachable only from the collection step of the sealed run; nothing in this
    ticket calls it on real history.
    """

    import hashlib

    for row in manifest["files"]:
        path = repository_root / row["path"]
        if not path.exists():
            raise SealedSampleManifestError(
                f"{row['provider_id']} raw file {row['path']} does not exist"
            )
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != row["sha256"]:
            raise SealedSampleManifestError(
                f"{row['provider_id']} raw file changed after it was hashed: "
                f"{row['path']} digests to {digest}, not {row['sha256']}"
            )


def assert_pre_freeze_operation_allowed(operation: str) -> None:
    """Refuse any research operation requested before the manifest is frozen."""

    if operation in PRE_FREEZE_ALLOWED_OPERATIONS:
        return
    raise SealedSampleManifestError(
        f"{REFUSE_TO_RUN}: {operation!r} is not one of the technical integrity "
        f"checks {list(PRE_FREEZE_ALLOWED_OPERATIONS)} permitted before the "
        "collection manifest is frozen"
    )


# =============================================================================
# 6. input provenance the sealed run must bind
# =============================================================================

INPUT_PROVENANCE_BINDINGS = (
    "sealed_sample_manifest_sha256",
    "bound_protocol_definition_sha256",
    "validator_definition_sha256",
    "parent_validator_definition_sha256",
    "candidate_method_version",
    "comparison_contract_version",
    "source_detector_version",
    "price_source_policy_version",
    "denominator_semantics_version",
    "tier4_measurement_versions",
)
INPUT_PROVENANCE_RULE = (
    "The evidence bundle a sealed run consumes must bind the frozen sample "
    "manifest digest the authorization record already carries, the frozen V3 "
    "hash, this executing validator's hash, the candidate construction version, "
    "the comparison contract, the detector version, the price-source policy and "
    f"the inherited Tier-4 measurement versions. Any mismatch is {REFUSE_TO_RUN}: "
    "a bundle measured under another contract is evidence about something else."
)


# =============================================================================
# 7. the executing contract: the certified parent plus one enumerated delta
# =============================================================================

DELTA_ID = "SEALED_EXECUTION_AUTHORIZATION_ONLY_V1"

# Every field of the certified V1 contract this successor is permitted to
# change, and every field it is permitted to add. The actual diff is computed
# and compared against this list before the contract is hashed, so a field this
# list does not name cannot differ at all.
ALLOWED_CONTRACT_CHANGED_FIELDS = (
    "output_schema.fields",
    "output_schema.record_schema_version",
    "sealed_sample.collection_authorized",
    "sealed_sample.opening_authorized",
    "sealed_sample.sealed_execution_authorized",
    "sealed_sample.sealed_execution_rule",
    "validator_schema_version",
    "validator_version",
)
ALLOWED_CONTRACT_ADDED_FIELDS = (
    "parent_validator",
    "sealed_execution_control",
    "sealed_sample.execution_states",
    "sealed_sample.one_shot_execution",
    "sealed_sample.reuse_after_finalized_run",
    "sealed_sample_contract",
    "semantic_delta",
)
ALLOWED_CONTRACT_REMOVED_FIELDS: tuple[str, ...] = ()

# The verdict-affecting fields of the certified parent that may never move.
PRESERVED_CONTRACT_FIELDS = (
    "binding",
    "certification_rule",
    "composition",
    "diagnostic_requirements",
    "evidence_completeness",
    "hard_requirements",
    "input_schema",
    "material_change_requires",
    "not_a_price_reference_protocol",
    "not_comparable_handling",
    "operative_field_precedence",
    "reason_vocabulary",
    "required_gate_pairs",
    "required_transfer_guard_pairs",
    "soft_requirements",
    "statistical_limitation",
    "tier4_inheritance",
    "verdict_precedence",
    "verdict_vocabulary",
)

SEMANTIC_DELTA_STATEMENT = (
    "BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_V2 = the certified "
    "BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_V1 semantics, unchanged, plus "
    "sealed_execution_authorized false -> true, plus the execution-control "
    "artifacts that make that authorization one-shot. This contract is not "
    "written independently: it is derived from the parent contract at build "
    "time and the computed diff is compared against the declared delta before "
    f"anything is hashed, so any other difference is {REFUSE_TO_FREEZE}."
)

TERMINAL_OUTCOMES = {
    VERDICT_PASS: (
        "The candidate is approved under the frozen BTC_REFERENCE_COMPOSITE_V3 "
        "protocol. PRICE_SOURCE_POLICY_V2 may then be written and BTC-019 may "
        "close successfully."
    ),
    VERDICT_FAIL: (
        "The candidate is rejected under the frozen protocol. V3 may not be "
        "retuned using the sealed sample."
    ),
    VERDICT_INSUFFICIENT: (
        "The candidate is not approved and the canonical production reference "
        "remains unresolved. V3 may not be retuned using the sealed sample."
    ),
}
TERMINAL_OUTCOME_RULE = (
    "All three verdicts are valid terminal research outcomes of the one-shot "
    "run. Nothing in this contract promises that BTC-019 passes. After the "
    "sealed sample is opened there is no post-sealed tuning: no threshold, "
    "gate, denominator, window or pair universe may be changed in response to "
    "what the sealed sample showed, and no second sample may be collected to "
    "improve an outcome."
)

NO_RESULT_DEPENDENT_BEHAVIOUR = (
    "Nothing in preparation, collection or execution branches on a sealed "
    "value. There is no rule that widens the window when coverage is low, adds "
    "data when the guard is undefined, or extends the sample when the candidate "
    "nearly passes. The window, the provider set, the pair universes, every "
    "threshold and the composition are all fixed before the first byte is "
    "collected, and the execution lock makes a second attempt impossible."
)

POST_REVIEW_IMMUTABILITY = (
    "Once this contract passes its own independent xHigh review it is frozen: "
    "no edit, no rebuild under changed semantics and no new hash before the "
    "sealed execution. The one permitted run must bind exactly the reviewed "
    "validator_definition_sha256."
)


def _record_output_schema_fields() -> list[str]:
    """The parent's published record fields plus this successor's own three."""

    return sorted(
        set(_v1.OUTPUT_SCHEMA_FIELDS)
        | {
            "parent_validator_definition_sha256",
            "parent_validator_version",
            "sealed_execution",
        }
    )


SEALED_EXECUTION_RESULT_SCHEMA_VERSION = "BTC019_V3_SEALED_VALIDATION_RESULT_V1"
SEALED_EXECUTION_RESULT_FIELDS = (
    "all_reasons",
    "bound_protocol_definition_sha256",
    "candidate_evidence_digest",
    "candidate_method_version",
    "candidate_series_id",
    "candidate_pair_certifications",
    "diagnostics",
    "execution_id",
    "final_verdict",
    "hard_requirement_outcomes",
    "inherited_gate_outcomes",
    "not_comparable_accounting",
    "parent_validator_definition_sha256",
    "primary_reason",
    "provenance",
    "result_sha256",
    "review_completeness",
    "schema_version",
    "sealed_sample_manifest_sha256",
    "seven_hard_requirements",
    "soft_gate",
    "transfer_guard_pair_certifications",
    "validation_record",
    "validator_definition_sha256",
)


def _sealed_sample_contract_block() -> dict[str, Any]:
    return {
        "bar_interval": SEALED_BAR_INTERVAL,
        "collection_manifest_file_required_keys": list(
            MANIFEST_FILE_REQUIRED_KEYS + MANIFEST_MISSING_KEYS
        ),
        "collection_manifest_required_keys": list(MANIFEST_REQUIRED_KEYS),
        "collection_manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "collection_sequence": list(COLLECTION_SEQUENCE),
        "collection_sequence_rule": COLLECTION_SEQUENCE_RULE,
        "forbidden_manifest_key_fragments": list(FORBIDDEN_MANIFEST_KEY_FRAGMENTS),
        "input_provenance_bindings": list(INPUT_PROVENANCE_BINDINGS),
        "input_provenance_rule": INPUT_PROVENANCE_RULE,
        "manifest_carries_no_strategy_outcome": True,
        "manifest_source_provenance_required_keys": list(
            MANIFEST_PROVENANCE_REQUIRED_KEYS
        ),
        "pre_freeze_allowed_operations": list(PRE_FREEZE_ALLOWED_OPERATIONS),
        "pre_freeze_forbidden_operations": list(PRE_FREEZE_FORBIDDEN_OPERATIONS),
        "pre_freeze_rule": PRE_FREEZE_RULE,
        "price_source_policy_version": PRICE_SOURCE_POLICY_VERSION,
        "provider_ids": list(SEALED_PROVIDER_IDS),
        "collection_plan": sealed_collection_plan(),
        "timezone": SEALED_TIMEZONE,
        "window_end": SEALED_WINDOW_END_ISO,
        "window_rule": SEALED_WINDOW_RULE,
        "window_start": SEALED_WINDOW_START_ISO,
    }


def _sealed_execution_control_block() -> dict[str, Any]:
    return {
        "authorization_record_required_keys": list(AUTHORIZATION_REQUIRED_KEYS),
        "authorization_record_schema_version": AUTHORIZATION_SCHEMA_VERSION,
        "authorization_rule": SEALED_EXECUTION_AUTHORIZATION_RULE,
        "authority_rule": AUTHORITY_RULE,
        "authority_rule_id": AUTHORITY_RULE_ID,
        "durable_lock": True,
        "execution_id_rule": EXECUTION_ID_RULE,
        "execution_id_prefix": EXECUTION_ID_PREFIX,
        "execution_states": list(EXECUTION_STATES),
        "execution_state_rule": EXECUTION_STATE_RULE,
        "legal_transitions": [dict(row) for row in LEGAL_EXECUTION_TRANSITIONS],
        "market_derived_fields_null_until_earned": list(
            MARKET_DERIVED_AUTHORIZATION_FIELDS
        ),
        "no_result_dependent_behaviour": NO_RESULT_DEPENDENT_BEHAVIOUR,
        "one_shot_rule": ONE_SHOT_RULE,
        "one_shot_rule_id": ONE_SHOT_RULE_ID,
        "post_review_immutability": POST_REVIEW_IMMUTABILITY,
        "preparation_reads_no_sealed_bytes": True,
        "refusal_conditions": list(EXECUTION_REFUSAL_CONDITIONS),
        "result_schema_fields": list(SEALED_EXECUTION_RESULT_FIELDS),
        "result_schema_version": SEALED_EXECUTION_RESULT_SCHEMA_VERSION,
        "terminal_execution_states": list(TERMINAL_EXECUTION_STATES),
        "terminal_outcome_rule": TERMINAL_OUTCOME_RULE,
        "terminal_outcomes": dict(TERMINAL_OUTCOMES),
        "the_only_call_that_may_read_sealed_bytes": "execute_sealed_validation",
    }


def _semantic_delta_block() -> dict[str, Any]:
    return {
        "added_fields": list(ALLOWED_CONTRACT_ADDED_FIELDS),
        "changed_fields": list(ALLOWED_CONTRACT_CHANGED_FIELDS),
        "delta_id": DELTA_ID,
        "derived_from_parent_at_build_time": True,
        "on_unauthorized_difference": REFUSE_TO_FREEZE,
        "preserved_parent_fields": list(PRESERVED_CONTRACT_FIELDS),
        "removed_fields": list(ALLOWED_CONTRACT_REMOVED_FIELDS),
        "statement": SEMANTIC_DELTA_STATEMENT,
        "verdict_affecting_delta": {
            "field": "sealed_sample.sealed_execution_authorized",
            "parent_value": False,
            "value": True,
        },
    }


def validator_definition(repository_root: Path) -> dict[str, Any]:
    """Build the executing contract by deriving the certified parent's.

    The parent contract is rebuilt and its reviewed hash reverified first, then
    exactly the declared delta is applied, then the computed diff is checked
    against that declared delta. Nothing is authored here that the parent did
    not already say, so a verdict-affecting drift cannot reach the hash.
    """

    parent = verify_parent_authority(repository_root)
    payload = {
        key: value
        for key, value in parent.items()
        if key != "validator_definition_sha256"
    }
    payload["validator_version"] = VALIDATOR_VERSION
    payload["validator_schema_version"] = VALIDATOR_SCHEMA_VERSION
    payload["output_schema"] = dict(parent["output_schema"])
    payload["output_schema"]["record_schema_version"] = VALIDATOR_RECORD_SCHEMA_VERSION
    payload["output_schema"]["fields"] = _record_output_schema_fields()
    payload["sealed_sample"] = dict(parent["sealed_sample"])
    payload["sealed_sample"].update(
        {
            "collection_authorized": True,
            "execution_states": list(EXECUTION_STATES),
            "one_shot_execution": ONE_SHOT_EXECUTION,
            "opening_authorized": True,
            "reuse_after_finalized_run": REUSE_AFTER_FINALIZED_RUN,
            "sealed_execution_authorized": SEALED_EXECUTION_AUTHORIZED,
            "sealed_execution_rule": SEALED_EXECUTION_AUTHORIZATION_RULE,
        }
    )
    payload["parent_validator"] = {
        "certification": PARENT_VALIDATOR_CLASSIFICATION,
        "implementation_commit": PARENT_VALIDATOR_IMPLEMENTATION_COMMIT,
        "review_commit": PARENT_VALIDATOR_REVIEW_COMMIT,
        "review_result": PARENT_VALIDATOR_REVIEW_RESULT,
        "sealed_execution_authorized": False,
        "validator_definition_sha256": PARENT_VALIDATOR_DEFINITION_SHA256,
        "validator_version": PARENT_VALIDATOR_VERSION,
    }
    payload["sealed_execution_control"] = _sealed_execution_control_block()
    payload["sealed_sample_contract"] = _sealed_sample_contract_block()
    payload["semantic_delta"] = _semantic_delta_block()

    delta = _compute_semantic_delta(parent, payload)
    _assert_delta_is_authorized(delta)
    payload["validator_definition_sha256"] = _digest(payload)
    return payload


def validator_definition_sha256(repository_root: Path) -> str:
    return validator_definition(repository_root)["validator_definition_sha256"]


# =============================================================================
# 8. the deterministic V1 -> V2 semantic diff
# =============================================================================


def _compare(left: Any, right: Any) -> bool:
    """Compare two contract values by their canonical serialization."""

    return _canonical_json({"v": left}) == _canonical_json({"v": right})


def _compute_semantic_delta(
    parent: Mapping[str, Any], successor: Mapping[str, Any]
) -> dict[str, Any]:
    """Return the exact field-level difference between the two contracts.

    A top-level block that is byte-identical stays one `identical` path, so the
    diff never buries the delta in noise. A block that differs is decomposed one
    level, so the reader is told exactly which sub-field moved rather than that
    "sealed_sample changed". A block the parent does not have at all is one
    `added` path: it authored nothing the parent already said.
    """

    left = {
        key: value
        for key, value in parent.items()
        if key != "validator_definition_sha256"
    }
    right = {
        key: value
        for key, value in successor.items()
        if key != "validator_definition_sha256"
    }
    added: list[str] = []
    removed: list[str] = []
    changed: list[str] = []
    identical: list[str] = []
    for key in sorted(set(left) | set(right)):
        if key not in right:
            removed.append(key)
            continue
        if key not in left:
            added.append(key)
            continue
        if _compare(left[key], right[key]):
            identical.append(key)
            continue
        if isinstance(left[key], Mapping) and isinstance(right[key], Mapping):
            inner_left, inner_right = left[key], right[key]
            for inner in sorted(set(inner_left) | set(inner_right)):
                path = f"{key}.{inner}"
                if inner not in inner_right:
                    removed.append(path)
                elif inner not in inner_left:
                    added.append(path)
                elif _compare(inner_left[inner], inner_right[inner]):
                    identical.append(path)
                else:
                    changed.append(path)
            continue
        changed.append(key)
    return {
        "added_fields": sorted(added),
        "changed_fields": sorted(changed),
        "delta_id": DELTA_ID,
        "identical_fields": sorted(identical),
        "removed_fields": sorted(removed),
    }


def _assert_delta_is_authorized(delta: Mapping[str, Any]) -> None:
    """Refuse to freeze an executing contract that changed anything else."""

    for label, actual, allowed in (
        ("changed", delta["changed_fields"], ALLOWED_CONTRACT_CHANGED_FIELDS),
        ("added", delta["added_fields"], ALLOWED_CONTRACT_ADDED_FIELDS),
        ("removed", delta["removed_fields"], ALLOWED_CONTRACT_REMOVED_FIELDS),
    ):
        surprises = sorted(set(actual) - set(allowed))
        if surprises:
            raise SemanticDriftError(
                f"{REFUSE_TO_FREEZE}: {label} fields {surprises} are not part of "
                f"the authorized {DELTA_ID} delta"
            )
        absent = sorted(set(allowed) - set(actual))
        if absent:
            raise SemanticDriftError(
                f"{REFUSE_TO_FREEZE}: the declared delta claims {label} fields "
                f"{absent} that the contracts do not actually differ in"
            )
    for field in PRESERVED_CONTRACT_FIELDS:
        if any(path == field or path.startswith(f"{field}.") for path in
               list(delta["changed_fields"]) + list(delta["removed_fields"])):
            raise SemanticDriftError(
                f"{REFUSE_TO_FREEZE}: the preserved parent field {field!r} moved"
            )


def semantic_delta(repository_root: Path) -> dict[str, Any]:
    """Return the persisted, deterministic V1 -> V2 semantic diff."""

    parent = verify_parent_authority(repository_root)
    successor = validator_definition(repository_root)
    delta = _compute_semantic_delta(parent, successor)
    _assert_delta_is_authorized(delta)
    payload = {
        **delta,
        "parent_validator_definition_sha256": parent["validator_definition_sha256"],
        "parent_validator_version": PARENT_VALIDATOR_VERSION,
        "preserved_parent_fields": list(PRESERVED_CONTRACT_FIELDS),
        "statement": SEMANTIC_DELTA_STATEMENT,
        "validator_definition_sha256": successor["validator_definition_sha256"],
        "validator_version": VALIDATOR_VERSION,
        "verdict_affecting_delta": {
            "field": "sealed_sample.sealed_execution_authorized",
            "parent_value": False,
            "value": True,
        },
    }
    payload["semantic_delta_sha256"] = _digest(payload)
    return payload


# =============================================================================
# 9. the composition -- every verdict-affecting step is the parent's own
# =============================================================================

DRY_RUN_SEALED_EXECUTION_BLOCK = {
    "authorized": SEALED_EXECUTION_AUTHORIZED,
    "execution_id": None,
    "execution_state": None,
    "one_shot_execution": ONE_SHOT_EXECUTION,
    "reuse_after_finalized_run": REUSE_AFTER_FINALIZED_RUN,
    "sealed_sample_manifest_sha256": None,
    "this_record_opened_the_sealed_sample": False,
}


def _authorize_sample_window(
    *,
    start: datetime,
    end: datetime,
    execution_mode: str,
    authorization: Mapping[str, Any] | None,
) -> None:
    """Apply the inherited guard, or the sealed window's one authorization.

    In `DRY_RUN_SYNTHETIC` this is exactly the parent's call: the inherited
    `guard_untouched_validation_sample` refuses any bundle reaching into
    2015-07-20..2019-11-30. In `SEALED_EXECUTION` the window must instead be
    that sealed window *exactly* -- neither broadened nor shortened, and never
    substituted -- and a durable authorization record must already stand in
    `EXECUTION_STARTED`.
    """

    if execution_mode != EXECUTION_MODE_SEALED:
        guard_untouched_validation_sample(
            start=start, end=end, purpose=f"{VALIDATOR_VERSION} {execution_mode}"
        )
        return
    if authorization is None:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: {EXECUTION_MODE_SEALED} requires a durable "
            f"{AUTHORIZATION_SCHEMA_VERSION} record"
        )
    _verify_sealed_window(start.isoformat(), end.isoformat(), "the evidence bundle")
    if authorization["status"] != STATE_EXECUTION_STARTED:
        raise SealedExecutionStateError(
            f"{REFUSE_TO_RUN}: execution {authorization['execution_id']} is "
            f"{authorization['status']}, not {STATE_EXECUTION_STARTED}"
        )


def validate_v3_candidate(
    evidence_bundle: Mapping[str, Any],
    *,
    repository_root: Path,
    execution_mode: str = EXECUTION_MODE_DRY_RUN,
    sealed_execution_authorization: Mapping[str, Any] | None = None,
) -> ValidationRecord:
    """Produce exactly one BTC-019 result under the frozen V3 protocol.

    The sequence, the schema and every verdict-affecting computation are the
    certified parent's: `_v1._validate_pair_universe`, the seven `_v1`
    requirement functions, `_v1.compose_verdict`, `_v1.evaluate_soft_gate` and
    `_v1._validate_diagnostics` are called, never reimplemented. What differs is
    only the window authorization above, this successor's own identity, and the
    sealed-execution block published beside the verdict.
    """

    if execution_mode not in EXECUTION_MODES:
        raise ValidatorInputError(f"unknown execution mode {execution_mode!r}")
    if execution_mode == EXECUTION_MODE_SEALED and not SEALED_EXECUTION_AUTHORIZED:
        raise SealedExecutionNotAuthorizedError(
            f"{REFUSE_TO_RUN}: sealed execution is not authorized by this contract"
        )
    if execution_mode != EXECUTION_MODE_SEALED and sealed_execution_authorization:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: an authorization record may accompany only "
            f"{EXECUTION_MODE_SEALED}"
        )

    protocol = _v1.bind_frozen_v3(repository_root)
    contract = validator_definition(repository_root)

    bundle = _v1._require_mapping(evidence_bundle, "the evidence bundle")
    _v1._require_exact_keys(bundle, _v1.BUNDLE_REQUIRED_KEYS, (), "the evidence bundle")
    if bundle["schema_version"] != EVIDENCE_BUNDLE_SCHEMA_VERSION:
        raise ValidatorInputError(
            f"the evidence bundle does not carry {EVIDENCE_BUNDLE_SCHEMA_VERSION}"
        )

    sample = _v1._require_mapping(bundle["sample"], "the sample block")
    _v1._require_exact_keys(sample, _v1.SAMPLE_REQUIRED_KEYS, (), "the sample block")
    start = _v1._parse_instant(sample["start"], "sample start")
    end = _v1._parse_instant(sample["end"], "sample end")
    if end < start:
        raise ValidatorInputError("the sample ends before it starts")
    _authorize_sample_window(
        start=start,
        end=end,
        execution_mode=execution_mode,
        authorization=sealed_execution_authorization,
    )

    identities = _v1._require_mapping(bundle["identities"], "the identities block")
    _v1._require_exact_keys(
        identities, _v1.IDENTITY_REQUIRED_KEYS, (), "the identities block"
    )
    for field, expected in _v1.BOUND_MEASUREMENT_IDENTITIES.items():
        declared = identities[field]
        actual = tuple(sorted(declared)) if isinstance(declared, list) else declared
        if actual != expected:
            raise ValidatorInputError(
                f"the bundle declares {field}={declared!r}, which the bound "
                f"definition does not accept (expected {expected!r})"
            )

    provenance = _v1._require_mapping(bundle["provenance"], "the provenance block")
    _v1._require_exact_keys(
        provenance, _v1.PROVENANCE_REQUIRED_KEYS, (), "the provenance block"
    )
    for field in ("measurement_record_digest", "sample_manifest_digest"):
        _v1._require_hex_digest(provenance[field], field)

    gate_ids = _v1.required_gate_pair_ids(protocol)
    guard_ids = _v1.required_transfer_guard_pair_ids(protocol)
    limit = _v1.operative_structural_limit(protocol)
    floor = _v1.operative_comparability_floor(protocol)
    quantile = _v1.operative_normal_quantile(protocol)
    gates = _v1.inherited_gate_definitions(protocol)
    _v1._verify_inherited_gate_census(gates)

    gate_measurements = _v1._validate_pair_universe(
        bundle["gate_pair_measurements"],
        required_ids=gate_ids,
        expected_role=_v1.ROLE_APPROVAL_GATE_PAIR,
        metric=_v1.STRUCTURAL_METRIC,
        floor=floor,
        what="gate_pair_measurements",
    )
    guard_measurements = _v1._validate_pair_universe(
        bundle["transfer_guard_pair_measurements"],
        required_ids=guard_ids,
        expected_role=_v1.ROLE_SOURCE_DISPERSION_GUARD_PAIR,
        metric=_v1.STRUCTURAL_METRIC,
        floor=floor,
        what="transfer_guard_pair_measurements",
    )
    soft_measurements = _v1._validate_pair_universe(
        bundle["soft_gate_pair_measurements"],
        required_ids=gate_ids,
        expected_role=_v1.ROLE_APPROVAL_GATE_PAIR,
        metric=_v1.EXACT_TIMESTAMP_METRIC,
        floor=floor,
        what="soft_gate_pair_measurements",
    )

    hard_requirements = {
        REQUIREMENT_STRUCTURAL_GATE: _v1._structural_gate_requirement(
            gate_measurements,
            required_ids=gate_ids,
            limit=limit,
            quantile=quantile,
            floor=floor,
        ),
        REQUIREMENT_TRANSFER_GUARD: _v1._transfer_guard_requirement(
            guard_measurements,
            required_ids=guard_ids,
            limit=limit,
            quantile=quantile,
            floor=floor,
        ),
        REQUIREMENT_COMPARABILITY: _v1._comparability_requirement(
            gate_measurements, required_ids=gate_ids, floor=floor
        ),
        REQUIREMENT_PAIR_COMPLETENESS: _v1._pair_completeness_requirement(
            gate_measurements,
            required_ids=gate_ids,
            guard_measurements=guard_measurements,
            guard_required_ids=guard_ids,
        ),
        REQUIREMENT_NOT_COMPARABLE: _v1._not_comparable_requirement(
            bundle["not_comparable_accounting"]
        ),
        REQUIREMENT_DERIVED_LEVEL_REVIEW: _v1._derived_level_review_requirement(
            bundle["derived_level_review"],
            required_ids=gate_ids,
            diagnostics=bundle["diagnostics"],
        ),
        REQUIREMENT_INHERITED_GATES: _v1._inherited_gate_requirement(
            bundle["inherited_gate_measurements"], gates=gates
        ),
    }
    composition = _v1.compose_verdict(
        {name: block["outcome"] for name, block in hard_requirements.items()}
    )

    soft = _v1.evaluate_soft_gate(
        {name: soft_measurements.get(name) for name in gate_ids},
        required_pairs=gate_ids,
        limit=limit,
        comparability_floor=floor,
    )
    diagnostics = _v1._validate_diagnostics(bundle["diagnostics"])

    if sealed_execution_authorization is None:
        sealed_block = dict(DRY_RUN_SEALED_EXECUTION_BLOCK)
    else:
        sealed_block = {
            "authorized": SEALED_EXECUTION_AUTHORIZED,
            "execution_id": sealed_execution_authorization["execution_id"],
            "execution_state": STATE_FINALIZED,
            "one_shot_execution": ONE_SHOT_EXECUTION,
            "reuse_after_finalized_run": REUSE_AFTER_FINALIZED_RUN,
            "sealed_sample_manifest_sha256": sealed_execution_authorization[
                "collection_manifest_digest"
            ],
            "this_record_opened_the_sealed_sample": True,
        }

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
            name: hard_requirements[name]["outcome"]
            for name in sorted(hard_requirements)
        },
        "input_evidence_digest": evidence_bundle_digest(bundle),
        "parent_protocol_definition_sha256": protocol["parent_definition_sha256"],
        "parent_validator_definition_sha256": PARENT_VALIDATOR_DEFINITION_SHA256,
        "parent_validator_version": PARENT_VALIDATOR_VERSION,
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
        "sealed_execution": sealed_block,
        "soft_gate": {
            **soft,
            "can_veto_approval": False,
            "enters_the_hard_composition": False,
        },
        "statistical_limitation": {
            "cross_pair": _v1.DEPENDENCE_LIMITATION_CROSS_PAIR,
            "is_a_gate": _v1.DEPENDENCE_LIMITATION_IS_A_GATE,
            "limitation_id": _v1.DEPENDENCE_LIMITATION_ID,
            "within_pair": _v1.DEPENDENCE_LIMITATION,
        },
        "validator_definition_sha256": contract["validator_definition_sha256"],
        "validator_version": VALIDATOR_VERSION,
        "verdict": composition["verdict"],
    }
    payload["validation_record_digest"] = _digest(payload)
    return ValidationRecord(payload=payload)


# =============================================================================
# 10. preparation, collection freeze, start and the one terminal execution
# =============================================================================


def prepare_sealed_execution(
    repository_root: Path, *, authorization_dir: Path
) -> dict[str, Any]:
    """Establish the durable one-shot authority. Reads no sealed byte.

    Verifies both certified hashes, this contract's own authorization flag and
    the enumerated semantic delta, refuses if any execution authority already
    exists, and writes the lock record with every market-derived field null.
    """

    contract = validator_definition(repository_root)
    if contract["sealed_sample"]["sealed_execution_authorized"] is not True:
        raise SealedExecutionNotAuthorizedError(
            f"{REFUSE_TO_PREPARE}: this contract does not authorise sealed execution"
        )
    semantic_delta(repository_root)
    digest = contract["validator_definition_sha256"]
    existing = authorization_dir / AUTHORIZATION_FILENAME
    if existing.exists():
        record = read_execution_authorization(
            authorization_dir, validator_definition_sha256=digest
        )
        raise SealedExecutionStateError(
            f"{REFUSE_TO_PREPARE}: execution {record['execution_id']} already "
            f"exists in state {record['status']}; {ONE_SHOT_RULE_ID} issues one "
            "authority per authority, never a second"
        )
    record = _new_authorization_record(digest)
    for field in MARKET_DERIVED_AUTHORIZATION_FIELDS:
        if record[field] is not None:
            raise SealedExecutionStateError(
                f"{REFUSE_TO_PREPARE}: preparation populated the market-derived "
                f"field {field!r}"
            )
    write_execution_authorization(authorization_dir, record)
    return record


def record_frozen_collection_manifest(
    repository_root: Path,
    *,
    authorization_dir: Path,
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze one validated collection manifest onto the durable record."""

    digest = validator_definition_sha256(repository_root)
    record = read_execution_authorization(
        authorization_dir, validator_definition_sha256=digest
    )
    validated = validate_sealed_sample_manifest(
        manifest,
        execution_id=record["execution_id"],
        validator_definition_sha256=digest,
    )
    moved = _transition(
        record, to_state=STATE_COLLECTED_FROZEN, step=TRANSITION_FREEZE_COLLECTION
    )
    moved["collection_manifest_digest"] = validated["manifest_sha256"]
    moved["authorization_record_sha256"] = _authorization_digest(moved)
    write_execution_authorization(authorization_dir, moved)
    return moved


def begin_sealed_execution(
    repository_root: Path, *, authorization_dir: Path
) -> dict[str, Any]:
    """Claim the one execution. Durable before any sealed byte is read."""

    digest = validator_definition_sha256(repository_root)
    record = read_execution_authorization(
        authorization_dir, validator_definition_sha256=digest
    )
    if record["collection_manifest_digest"] is None:
        raise SealedExecutionStateError(
            f"{REFUSE_TO_RUN}: no frozen collection manifest is recorded"
        )
    moved = _transition(
        record, to_state=STATE_EXECUTION_STARTED, step=TRANSITION_BEGIN
    )
    write_execution_authorization(authorization_dir, moved)
    return moved


def _bind_input_provenance(
    bundle: Mapping[str, Any], record: Mapping[str, Any]
) -> None:
    """Refuse a bundle whose provenance does not bind the frozen manifest."""

    provenance = bundle.get("provenance")
    if not isinstance(provenance, Mapping):
        raise ValidatorInputError("the provenance block must be a mapping")
    declared = provenance.get("sample_manifest_digest")
    if declared != record["collection_manifest_digest"]:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: the evidence bundle binds sample manifest "
            f"{declared!r}, not the frozen {record['collection_manifest_digest']!r}"
        )
    identities = bundle.get("identities")
    if not isinstance(identities, Mapping):
        raise ValidatorInputError("the identities block must be a mapping")
    if identities.get("candidate_method_version") != record["candidate_method_version"]:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: the evidence bundle names another candidate "
            "construction version than the authorization record"
        )
    if identities.get("candidate_series_id") != record["candidate_series_id"]:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: the evidence bundle names another candidate series"
        )
    declared_providers = identities.get("provider_ids")
    if not isinstance(declared_providers, (list, tuple)) or tuple(
        sorted(declared_providers)
    ) != tuple(record["allowed_provider_ids"]):
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: the evidence bundle names providers "
            f"{declared_providers!r}, not the authorised "
            f"{record['allowed_provider_ids']!r}"
        )


def execute_sealed_validation(
    evidence_bundle: Mapping[str, Any],
    *,
    repository_root: Path,
    authorization_dir: Path,
) -> dict[str, Any]:
    """Run the single permitted sealed validation and finalize it, forever.

    This is the only call in the repository that may consume sealed evidence.
    It refuses without a durable record in `EXECUTION_STARTED`, refuses a bundle
    whose provenance does not bind the frozen collection manifest, and moves the
    record to `FINALIZED` so no second sealed result can ever be produced for
    this authority.
    """

    contract = validator_definition(repository_root)
    digest = contract["validator_definition_sha256"]
    record = read_execution_authorization(
        authorization_dir, validator_definition_sha256=digest
    )
    if record["status"] == STATE_FINALIZED:
        raise SealedExecutionStateError(
            f"{REFUSE_TO_RUN}: execution {record['execution_id']} is already "
            f"FINALIZED; {ONE_SHOT_RULE_ID} refuses a second sealed result"
        )
    if record["status"] != STATE_EXECUTION_STARTED:
        raise SealedExecutionStateError(
            f"{REFUSE_TO_RUN}: execution {record['execution_id']} is "
            f"{record['status']}, not {STATE_EXECUTION_STARTED}"
        )
    _bind_input_provenance(evidence_bundle, record)
    validation = validate_v3_candidate(
        evidence_bundle,
        repository_root=repository_root,
        execution_mode=EXECUTION_MODE_SEALED,
        sealed_execution_authorization=record,
    )
    result = _sealed_execution_result(validation, record=record)
    moved = _transition(record, to_state=STATE_FINALIZED, step=TRANSITION_FINALIZE)
    moved["evidence_bundle_digest"] = validation.payload["input_evidence_digest"]
    moved["execution_result_digest"] = result["result_sha256"]
    moved["authorization_record_sha256"] = _authorization_digest(moved)
    write_execution_authorization(authorization_dir, moved)
    return result


def _sealed_execution_result(
    validation: ValidationRecord, *, record: Mapping[str, Any]
) -> dict[str, Any]:
    """Render the terminal BTC019_V3_SEALED_VALIDATION_RESULT_V1 record.

    Every field a reader needs to know whether BTC-019 passed is published
    explicitly; nothing requires post-hoc interpretation.
    """

    payload = validation.payload
    hard = payload["hard_requirements"]
    result: dict[str, Any] = {
        "all_reasons": list(payload["reason_codes"]),
        "bound_protocol_definition_sha256": payload[
            "bound_protocol_definition_sha256"
        ],
        "candidate_evidence_digest": payload["input_evidence_digest"],
        "candidate_method_version": record["candidate_method_version"],
        "candidate_pair_certifications": [
            dict(row) for row in hard[REQUIREMENT_STRUCTURAL_GATE].get("pairs", [])
        ],
        "candidate_series_id": record["candidate_series_id"],
        "diagnostics": payload["diagnostics"],
        "execution_id": record["execution_id"],
        "final_verdict": payload["verdict"],
        "hard_requirement_outcomes": payload["hard_requirement_outcomes"],
        "inherited_gate_outcomes": hard[REQUIREMENT_INHERITED_GATES],
        "not_comparable_accounting": hard[REQUIREMENT_NOT_COMPARABLE],
        "parent_validator_definition_sha256": PARENT_VALIDATOR_DEFINITION_SHA256,
        "primary_reason": payload["primary_reason"],
        "provenance": payload["provenance"],
        "review_completeness": hard[REQUIREMENT_DERIVED_LEVEL_REVIEW],
        "schema_version": SEALED_EXECUTION_RESULT_SCHEMA_VERSION,
        "sealed_sample_manifest_sha256": record["collection_manifest_digest"],
        "seven_hard_requirements": {name: hard[name] for name in sorted(hard)},
        "soft_gate": payload["soft_gate"],
        "transfer_guard_pair_certifications": [
            dict(row) for row in hard[REQUIREMENT_TRANSFER_GUARD].get("pairs", [])
        ],
        "validation_record": validation.as_record(),
        "validator_definition_sha256": payload["validator_definition_sha256"],
    }
    if result["final_verdict"] not in VERDICT_VOCABULARY:
        raise ValidatorError(
            f"a sealed result may only be one of {list(VERDICT_VOCABULARY)}"
        )
    missing = sorted(set(SEALED_EXECUTION_RESULT_FIELDS) - set(result) - {"result_sha256"})
    unknown = sorted(set(result) - set(SEALED_EXECUTION_RESULT_FIELDS))
    if missing or unknown:
        raise ValidatorError(
            f"the sealed result schema is out of step: missing {missing}, "
            f"unknown {unknown}"
        )
    result["result_sha256"] = _digest(result)
    return result


# =============================================================================
# 11. persistence, restore and tamper refusal
# =============================================================================


def write_sealed_executor_artifacts(
    repository_root: Path, output_dir: Path
) -> dict[str, Any]:
    """Persist the executing contract, its semantic delta and its report."""

    output_dir.mkdir(parents=True, exist_ok=True)
    definition = validator_definition(repository_root)
    delta = semantic_delta(repository_root)
    (output_dir / VALIDATOR_DEFINITION_FILENAME).write_text(
        json.dumps(definition, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="ascii",
    )
    (output_dir / SEMANTIC_DELTA_FILENAME).write_text(
        json.dumps(delta, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="ascii",
    )
    (output_dir / SEALED_EXECUTOR_REPORT_FILENAME).write_text(
        sealed_executor_markdown(definition, delta), encoding="ascii"
    )
    return definition


def restore_sealed_executor_definition(output_dir: Path) -> dict[str, Any]:
    """Read the persisted executing contract, refusing the tampers it can see.

    This is a cheap first line only. `verify_sealed_executor_artifacts` is the
    complete check, and the runtime never trusts the persisted file: every
    entry point rebuilds the contract from the repository.
    """

    payload = json.loads(
        (output_dir / VALIDATOR_DEFINITION_FILENAME).read_text(encoding="ascii")
    )
    if payload.get("validator_schema_version") != VALIDATOR_SCHEMA_VERSION:
        raise ValidatorError(
            f"persisted contract does not carry {VALIDATOR_SCHEMA_VERSION}"
        )
    if payload.get("validator_version") != VALIDATOR_VERSION:
        raise ValidatorError("persisted contract is not this validator version")
    parent = payload.get("parent_validator", {})
    if parent.get("validator_definition_sha256") != PARENT_VALIDATOR_DEFINITION_SHA256:
        raise ValidatorError("persisted contract names another certified parent")
    binding = payload.get("binding", {})
    if binding.get("bound_protocol_definition_sha256") != (
        BOUND_PROTOCOL_DEFINITION_SHA256_EXPECTED
    ):
        raise ValidatorError("persisted contract binds another V3 definition hash")
    sealed = payload.get("sealed_sample", {})
    if sealed.get("sealed_execution_authorized") is not True:
        raise ValidatorError("persisted contract does not authorise sealed execution")
    if sealed.get("one_shot_execution") is not True:
        raise ValidatorError("persisted contract drops the one-shot rule")
    if sealed.get("reuse_after_finalized_run") != REUSE_AFTER_FINALIZED_RUN:
        raise ValidatorError("persisted contract permits reuse after a finalized run")
    if sealed.get("start") != SEALED_WINDOW_START_ISO or sealed.get("end") != (
        SEALED_WINDOW_END_ISO
    ):
        raise ValidatorError("persisted contract carries a different sealed window")
    control = payload.get("sealed_execution_control", {})
    if control.get("execution_states") != list(EXECUTION_STATES):
        raise ValidatorError("persisted contract carries a different state machine")
    if control.get("one_shot_rule_id") != ONE_SHOT_RULE_ID:
        raise ValidatorError("persisted contract carries a different one-shot rule")
    if control.get("result_schema_version") != SEALED_EXECUTION_RESULT_SCHEMA_VERSION:
        raise ValidatorError("persisted contract carries a different result schema")
    contract = payload.get("sealed_sample_contract", {})
    if contract.get("collection_manifest_schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ValidatorError("persisted contract carries a different manifest schema")
    if payload.get("verdict_vocabulary") != list(VERDICT_VOCABULARY):
        raise ValidatorError("persisted contract carries a different verdict vocabulary")
    digest = payload.get("validator_definition_sha256")
    body = {
        key: value
        for key, value in payload.items()
        if key != "validator_definition_sha256"
    }
    if digest != _digest(body):
        raise ValidatorError("persisted validator definition was tampered with")
    return payload


def verify_sealed_executor_artifacts(
    repository_root: Path, output_dir: Path
) -> dict[str, Any]:
    """Recompute the contract and refuse a persisted copy that disagrees."""

    persisted = restore_sealed_executor_definition(output_dir)
    rebuilt = validator_definition(repository_root)
    if _canonical_json(persisted) != _canonical_json(rebuilt):
        raise ValidatorError(
            "persisted validator definition does not recompute from the repository"
        )
    return persisted


# =============================================================================
# report
# =============================================================================


def sealed_executor_markdown(
    definition: Mapping[str, Any], delta: Mapping[str, Any]
) -> str:
    """Render the executing contract and its semantic delta deterministically."""

    control = definition["sealed_execution_control"]
    sample = definition["sealed_sample_contract"]
    lines: list[str] = [
        f"# {VALIDATOR_VERSION}",
        "",
        "The executing successor to the certified",
        f"`{PARENT_VALIDATOR_VERSION}`. It is derived from the parent contract at",
        "build time and differs from it by exactly one verdict-affecting field --",
        "`sealed_execution_authorized`, false -> true -- plus the execution-control",
        "artifacts that make that authorization one-shot.",
        "",
        "## Binding",
        "",
        f"- Bound protocol hash: `{definition['binding']['bound_protocol_definition_sha256']}`",
        f"- Parent validator: `{PARENT_VALIDATOR_VERSION}`",
        f"- Parent validator hash: `{PARENT_VALIDATOR_DEFINITION_SHA256}`",
        f"- Executing validator hash: `{definition['validator_definition_sha256']}`",
        f"- Parent certification: `{PARENT_VALIDATOR_CLASSIFICATION}`",
        "",
        "## Semantic delta",
        "",
        f"`{delta['delta_id']}`",
        "",
        "Changed:",
        "",
    ]
    lines += [f"- `{name}`" for name in delta["changed_fields"]]
    lines += ["", "Added:", ""]
    lines += [f"- `{name}`" for name in delta["added_fields"]]
    lines += [
        "",
        f"Removed: {len(delta['removed_fields'])}",
        "",
        "Every other field of the certified parent is byte-identical.",
        "",
        "## One-shot execution",
        "",
        "```text",
        " -> ".join(EXECUTION_STATES),
        "```",
        "",
    ]
    for row in control["legal_transitions"]:
        lines.append(f"- `{row['from']}` -> `{row['to']}` via `{row['step']}`")
    lines += [
        "",
        control["one_shot_rule"],
        "",
        "## Sealed sample",
        "",
        f"- Window: `{sample['window_start']}` .. `{sample['window_end']}`",
        f"- Bar interval: `{sample['bar_interval']}`, timezone `{sample['timezone']}`",
        f"- Providers: {', '.join(f'`{name}`' for name in sample['provider_ids'])}",
        f"- Manifest schema: `{sample['collection_manifest_schema_version']}`",
        f"- Result schema: `{control['result_schema_version']}`",
        "- Collected: no",
        "- Opened: no",
        "",
        "## Collection sequence",
        "",
    ]
    lines += [f"{index}. {step}" for index, step in enumerate(sample["collection_sequence"], 1)]
    lines += ["", "## Terminal outcomes", ""]
    for verdict in VERDICT_VOCABULARY:
        lines += [f"### `{verdict}`", "", control["terminal_outcomes"][verdict], ""]
    lines += [control["terminal_outcome_rule"], ""]
    return "\n".join(lines)


def main() -> None:  # pragma: no cover - operational entry point
    repository_root = Path(__file__).resolve().parents[2]
    output_dir = repository_root / SEALED_EXECUTOR_OUTPUT_NAMESPACE
    definition = write_sealed_executor_artifacts(repository_root, output_dir)
    print(definition["validator_definition_sha256"])


if __name__ == "__main__":  # pragma: no cover - operational entry point
    main()
