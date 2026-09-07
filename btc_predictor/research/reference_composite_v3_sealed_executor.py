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
    execute_sealed_validation(root)  atomically consume, then read sealed bytes
    recover_sealed_execution(root)  verify durable artifacts, never raw bytes

Every verdict-affecting computation is *called* on the parent module rather
than reimplemented here: the pair universe, the seven hard requirements, the
composition, the Wilson certification, the soft gate, the diagnostics and the
33 inherited gates are all `_v1.<name>`. What this module adds is the one-shot
sealed-execution control surface -- an explicit authorization flag, a path-bound
five-state authority, a cross-process POSIX lock, atomic/fsynced persistence, a
canonical frozen sample manifest, raw-byte revalidation, immutable evidence and
result artifacts, and deterministic no-rerun recovery.

Authorization is not execution. Importing this module, building the contract,
verifying artifacts, hashing the definition and running the whole test suite
collect nothing and open nothing: `execute_sealed_validation` is the sole path
to sealed bytes, it accepts only a durable `COLLECTED_FROZEN` authority and
persists `EXECUTION_STARTED` before its first read. It is never called on real
history here. The sealed
2015-07-20..2019-11-30 sample stays uncollected and unopened.
"""

from __future__ import annotations

import fcntl
import gzip
import hashlib
import json
import os
import stat
import tempfile
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterator

from btc_predictor.data.ohlcv import OhlcvBar, require_utc_datetime
from btc_predictor.research.btc019_empirical import RAW_ARTIFACT_SCHEMA_VERSION
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
from btc_predictor.research import reference_composite_v3_sealed_evidence as _evidence_owner
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
EXECUTOR_LOCK_FILENAME = "sealed_executor.lock"
MANIFEST_FILENAME = "sealed_sample_manifest.json"
EVIDENCE_FILENAME = "sealed_evidence_bundle.json"
RESULT_FILENAME = "sealed_validation_result.json"
RAW_COLLECTION_DIRNAME = "raw_collection"

FAILED_EXECUTOR_DEFINITION_SHA256 = (
    "e21e6ad8e8a40e4ee0763d7f3176efc168dacc0701f8e1199ae8a25ee5f9d784"
)
FAILED_EXECUTOR_IMPLEMENTATION_COMMIT = (
    "568ebb8ca8ead0025fb30d5b15e576797d17dffb"
)
FAILED_EXECUTOR_REVIEW_COMMIT = "daa664753ed3a6e282fa53577be9f680bfa7c8fd"
FAILED_EXECUTOR_REVIEW_RESULT = "FAIL_SEALED_EXECUTOR_INVALID"

PREVIOUS_EXECUTOR_DEFINITION_SHA256 = (
    "49abd68975217bb78affc0b6bd6f5e2ba066e84ec745dc5b9bdf82d3bea99729"
)
PREVIOUS_EXECUTOR_IMPLEMENTATION_COMMIT = (
    "9ca2b5bfdb129441d0b6857b496b526f7d5685df"
)
PREVIOUS_EXECUTOR_REVIEW_COMMIT = (
    "45c5e04044d054757b583cbb2aaed5915d196852"
)
PREVIOUS_EXECUTOR_REVIEW_RESULT = "FAIL_SEALED_EXECUTOR_INVALID"

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


class SealedExecutionIntegrityError(ValidatorError):
    """Raised when durable state and its immutable artifacts disagree."""


class SealedExecutionInterruptedError(ValidatorError):
    """Raised for an operationally interrupted run, never a scientific verdict."""


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
COLLECTION_METHOD = "btc_predictor.research.btc019_empirical.collect_btc019_evidence"
COLLECTION_METHOD_VERSION = "BTC019_COLLECTOR_V1"
SEALED_EVIDENCE_BUILDER_VERSION = _evidence_owner.BUILDER_VERSION
SEALED_EVIDENCE_BUILDER_MODULE = _evidence_owner.BUILDER_MODULE
SEALED_EVIDENCE_BUILDER_FUNCTION = _evidence_owner.BUILDER_FUNCTION
SEALED_EVIDENCE_BUILDER_DEFINITION_SHA256 = (
    "d8ff41f734dbeefbc2df06bac97637c3e3a06d23ae3cea5049541d3ddeeabb85"
)
_FIXED_SEALED_EVIDENCE_BUILDER = _evidence_owner.build_sealed_evidence


def fixed_evidence_builder_definition() -> dict[str, Any]:
    """Verify and return the one repository-owned live builder definition."""

    if _evidence_owner.build_sealed_evidence is not _FIXED_SEALED_EVIDENCE_BUILDER:
        raise ValidatorBindingError(
            f"{REFUSE_TO_RUN}: canonical evidence-builder function object moved"
        )
    definition = _evidence_owner.builder_definition()
    expected = {
        "builder_function": SEALED_EVIDENCE_BUILDER_FUNCTION,
        "builder_input_type": "VerifiedRawCollection",
        "builder_module": SEALED_EVIDENCE_BUILDER_MODULE,
        "builder_version": SEALED_EVIDENCE_BUILDER_VERSION,
        "builder_definition_sha256": SEALED_EVIDENCE_BUILDER_DEFINITION_SHA256,
    }
    for field, value in expected.items():
        if definition.get(field) != value:
            raise ValidatorBindingError(
                f"{REFUSE_TO_RUN}: fixed evidence-builder {field} moved; "
                "a new V2 contract hash is required"
            )
    return definition


def _raw_relative_path(provider_id: str) -> str:
    return f"{RAW_COLLECTION_DIRNAME}/{provider_id}_btc_usd_1h.jsonl.gz"

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


def _provider_endpoints() -> dict[str, str]:
    return {
        instrument.provider_id: instrument.api_endpoint
        for instrument in DEFAULT_PRICE_SOURCE_POLICY.instruments
        if instrument.provider_id in SEALED_PROVIDER_IDS
    }


def _provider_roles() -> dict[str, tuple[str, ...]]:
    return {
        instrument.provider_id: instrument.roles
        for instrument in DEFAULT_PRICE_SOURCE_POLICY.instruments
        if instrument.provider_id in SEALED_PROVIDER_IDS
    }


def _collection_source_identifier(provider_id: str) -> str:
    plan = {row["provider_id"]: row for row in sealed_collection_plan()}[provider_id]
    return (
        f"{provider_id}:{plan['exchange']}:{plan['instrument_symbol']}:"
        f"{SEALED_BAR_INTERVAL}:{SEALED_WINDOW_START_ISO}:{SEALED_WINDOW_END_ISO}"
    )


def sealed_collection_plan() -> list[dict[str, Any]]:
    """The per-provider collection plan, derived from the frozen policy alone."""

    symbols = _provider_instrument_symbols()
    exchanges = _provider_exchanges()
    endpoints = _provider_endpoints()
    roles = _provider_roles()
    return [
        {
            "bar_interval": SEALED_BAR_INTERVAL,
            "endpoint": endpoints[provider_id],
            "exchange": exchanges[provider_id],
            "instrument_symbol": symbols[provider_id],
            "price_source_policy_version": PRICE_SOURCE_POLICY_VERSION,
            "price_source_roles": list(roles[provider_id]),
            "provider_id": provider_id,
            "raw_relative_path": _raw_relative_path(provider_id),
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
    "Authorization is necessary and never sufficient. The live call loads only "
    "the canonical persisted authority below its path-bound execution root, "
    "verifies its exact history, earned fields and immutable artifacts while "
    "holding an exclusive POSIX file lock, atomically persists "
    "COLLECTED_FROZEN -> EXECUTION_STARTED, then and only then rereads the "
    "manifest-bound raw bytes and invokes the frozen evidence-builder boundary. "
    "No caller-supplied mapping or prebuilt evidence can authorize sealed mode."
)

ONE_SHOT_RULE_ID = "BTC019_V3_SEALED_SAMPLE_OPENED_EXACTLY_ONCE_V1"
ONE_SHOT_RULE = (
    "The sealed sample is opened exactly once. A second sealed result for the "
    "same frozen V3 definition hash, the same executing validator hash and the "
    "same sealed sample identity is REFUSE, whether it is requested in the same "
    "process or after a restart. EXECUTION_STARTED consumes the authority "
    "permanently, including when execution crashes before the first raw read or "
    "before FINALIZED. Normal execution never accepts EXECUTION_STARTED. "
    "Recovery may verify already-published evidence and result artifacts and "
    "finalize them, but it never opens raw files or recomputes evidence."
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
TRANSITION_FINALIZE = "finalize_sealed_execution"

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
    "Exactly five states and the exact history prefix for the current state are "
    "required. Missing, extra, duplicate, reordered, backward and skipped "
    "transitions are refused even when the record is self-rehashed. "
    "COLLECTED_FROZEN -> EXECUTION_STARTED permanently consumes the authority; "
    "normal execution can neither start nor resume from EXECUTION_STARTED."
)

STATE_HISTORY_CONTRACT = {
    state: [dict(row) for row in LEGAL_EXECUTION_TRANSITIONS[:index]]
    for index, state in enumerate(EXECUTION_STATES)
}

STATE_EARNED_FIELD_CONTRACT = {
    STATE_PREPARED: {
        "collection_manifest_digest": "ABSENT",
        "evidence_bundle_digest": "ABSENT",
        "execution_result_digest": "ABSENT",
    },
    STATE_COLLECTED_FROZEN: {
        "collection_manifest_digest": "REQUIRED",
        "evidence_bundle_digest": "ABSENT",
        "execution_result_digest": "ABSENT",
    },
    STATE_EXECUTION_STARTED: {
        "collection_manifest_digest": "REQUIRED",
        "evidence_bundle_digest": "OPTIONAL_AFTER_DURABLE_PUBLICATION",
        "execution_result_digest": "OPTIONAL_AFTER_DURABLE_PUBLICATION",
    },
    STATE_FINALIZED: {
        "collection_manifest_digest": "REQUIRED",
        "evidence_bundle_digest": "REQUIRED",
        "execution_result_digest": "REQUIRED",
    },
}

STATE_ARTIFACT_CONTRACT = {
    STATE_PREPARED: {"manifest": "ABSENT", "evidence": "ABSENT", "result": "ABSENT"},
    STATE_COLLECTED_FROZEN: {
        "manifest": "REQUIRED",
        "evidence": "ABSENT",
        "result": "ABSENT",
    },
    STATE_EXECUTION_STARTED: {
        "manifest": "REQUIRED",
        "evidence": "OPTIONAL_AFTER_PUBLICATION",
        "result": "OPTIONAL_AFTER_PUBLICATION_REQUIRES_EVIDENCE",
    },
    STATE_FINALIZED: {
        "manifest": "REQUIRED",
        "evidence": "REQUIRED",
        "result": "REQUIRED",
    },
}

EXECUTION_STARTED_ALLOWED_CHECKPOINTS = (
    {
        "checkpoint": "AUTHORITY_CONSUMED",
        "evidence_artifact": False,
        "evidence_digest": False,
        "result_artifact": False,
        "result_digest": False,
    },
    {
        "checkpoint": "EVIDENCE_PUBLISHED",
        "evidence_artifact": True,
        "evidence_digest": False,
        "result_artifact": False,
        "result_digest": False,
    },
    {
        "checkpoint": "EVIDENCE_CHECKPOINTED",
        "evidence_artifact": True,
        "evidence_digest": True,
        "result_artifact": False,
        "result_digest": False,
    },
    {
        "checkpoint": "RESULT_PUBLISHED",
        "evidence_artifact": True,
        "evidence_digest": True,
        "result_artifact": True,
        "result_digest": False,
    },
    {
        "checkpoint": "RESULT_CHECKPOINTED",
        "evidence_artifact": True,
        "evidence_digest": True,
        "result_artifact": True,
        "result_digest": True,
    },
)

CRASH_INJECTION_POINTS = (
    "after_prepared_write",
    "after_manifest_persisted_before_collected_frozen",
    "after_collected_frozen",
    "after_execution_started_before_raw_read",
    "after_first_raw_file_read",
    "after_evidence_persisted",
    "after_result_temp_write",
    "after_result_atomic_publish",
    "after_result_digest_persisted_before_finalized",
    "after_finalized",
)


def _crash_injection_point(point: str) -> None:
    """No-op production hook monkeypatched by synthetic crash tests."""

    if point not in CRASH_INJECTION_POINTS:  # pragma: no cover - internal guard
        raise ValueError(f"unknown crash injection point {point!r}")

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
    "the execution root differs from the root bound at preparation",
    "the state history is not the exact legal prefix for the durable state",
    "a state carries an impossible future field or omits an earned field",
    "a required canonical manifest, evidence or result artifact is absent",
    "sealed_execution_authorized is false",
    "the persisted evidence bundle's provenance does not bind the frozen manifest",
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
    "execution_root_sha256",
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

# The artifact-derived fields. They are null until their immutable artifact has
# been published, and none of them is written by preparation.
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
    "sealed window, the candidate identity, the allowed providers and the "
    "SHA-256 of the canonical resolved execution-root path. The same authority "
    "at the same root always derives the same id; copying a record to another "
    "root or tampering an authority field makes the id disagree."
)


def _canonical_execution_root(execution_root: Path, *, create: bool) -> Path:
    root = Path(execution_root)
    if root.is_symlink():
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: the execution root may not be a symlink"
        )
    if create:
        root.mkdir(parents=True, exist_ok=True)
    try:
        resolved = root.resolve(strict=True)
    except FileNotFoundError as error:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: the execution root does not exist"
        ) from error
    if not resolved.is_dir():
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: the execution root is not a directory"
        )
    return resolved


def _execution_root_sha256(execution_root: Path) -> str:
    return hashlib.sha256(os.fsencode(str(execution_root))).hexdigest()


def execution_authority(
    validator_definition_sha256: str, *, execution_root: Path
) -> dict[str, Any]:
    """The canonical authority every sealed run is bound to."""

    canonical_root = _canonical_execution_root(execution_root, create=False)
    return {
        "allowed_provider_ids": list(SEALED_PROVIDER_IDS),
        "bar_interval": SEALED_BAR_INTERVAL,
        "bound_protocol_definition_sha256": BOUND_PROTOCOL_DEFINITION_SHA256_EXPECTED,
        "candidate_method_version": CANDIDATE_METHOD_VERSION,
        "candidate_series_id": CANDIDATE_SERIES_ID,
        "execution_root_sha256": _execution_root_sha256(canonical_root),
        "parent_validator_definition_sha256": PARENT_VALIDATOR_DEFINITION_SHA256,
        "sealed_window_end": SEALED_WINDOW_END_ISO,
        "sealed_window_start": SEALED_WINDOW_START_ISO,
        "timezone": SEALED_TIMEZONE,
        "validator_definition_sha256": validator_definition_sha256,
    }


def derive_execution_id(
    validator_definition_sha256: str, *, execution_root: Path
) -> str:
    """Return the deterministic execution id for one authority."""

    return EXECUTION_ID_PREFIX + _digest(
        execution_authority(
            validator_definition_sha256, execution_root=execution_root
        )
    )[:32]


def _authorization_digest(record: Mapping[str, Any]) -> str:
    body = {
        key: value
        for key, value in record.items()
        if key != "authorization_record_sha256"
    }
    return _digest(body)


def _new_authorization_record(
    validator_definition_sha256: str, *, execution_root: Path
) -> dict[str, Any]:
    root_digest = _execution_root_sha256(execution_root)
    record: dict[str, Any] = {
        "allowed_provider_ids": list(SEALED_PROVIDER_IDS),
        "bar_interval": SEALED_BAR_INTERVAL,
        "bound_protocol_definition_sha256": BOUND_PROTOCOL_DEFINITION_SHA256_EXPECTED,
        "candidate_method_version": CANDIDATE_METHOD_VERSION,
        "candidate_series_id": CANDIDATE_SERIES_ID,
        "collection_manifest_digest": None,
        "collection_plan": sealed_collection_plan(),
        "evidence_bundle_digest": None,
        "execution_id": derive_execution_id(
            validator_definition_sha256, execution_root=execution_root
        ),
        "execution_root_sha256": root_digest,
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


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    ).encode("ascii")


def _fsync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_write_bytes(
    path: Path,
    payload: bytes,
    *,
    replace: bool,
    temp_crash_point: str | None = None,
) -> Path:
    """Publish bytes durably with a same-directory fsync/replace sequence."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if not replace and path.exists():
        raise SealedExecutionIntegrityError(
            f"{REFUSE_TO_RUN}: immutable artifact {path.name} already exists"
        )
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.tmp."
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as artifact:
            artifact.write(payload)
            artifact.flush()
            os.fsync(artifact.fileno())
        if temp_crash_point is not None:
            _crash_injection_point(temp_crash_point)
        if not replace and path.exists():
            raise SealedExecutionIntegrityError(
                f"{REFUSE_TO_RUN}: immutable artifact {path.name} already exists"
            )
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()
    return path


def _atomic_write_json(
    path: Path,
    payload: Mapping[str, Any],
    *,
    replace: bool,
    temp_crash_point: str | None = None,
) -> Path:
    return _atomic_write_bytes(
        path,
        _json_bytes(payload),
        replace=replace,
        temp_crash_point=temp_crash_point,
    )


def _read_ascii_json(path: Path, what: str) -> dict[str, Any]:
    try:
        if path.is_symlink():
            raise SealedExecutionIntegrityError(
                f"{REFUSE_TO_RUN}: {what} may not be a symlink"
            )
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(descriptor, "rb", closefd=True) as artifact:
            raw = artifact.read()
        payload = json.loads(raw.decode("ascii"))
    except (FileNotFoundError, ValueError, UnicodeDecodeError) as error:
        raise SealedExecutionIntegrityError(
            f"{REFUSE_TO_RUN}: {what} is not durable readable ascii JSON"
        ) from error
    if not isinstance(payload, dict):
        raise SealedExecutionIntegrityError(
            f"{REFUSE_TO_RUN}: {what} is not a mapping"
        )
    return payload


@contextmanager
def _exclusive_executor_lock(
    execution_root: Path, *, create_root: bool = False
) -> Iterator[Path]:
    """Hold the POSIX cross-process lock for one control-plane transaction."""

    root = _canonical_execution_root(execution_root, create=create_root)
    path = root / EXECUTOR_LOCK_FILENAME
    descriptor = os.open(
        path,
        os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise SealedExecutionIntegrityError(
                f"{REFUSE_TO_RUN}: the executor lock is not a regular file"
            )
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield root
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _write_execution_authorization(
    execution_root: Path, record: Mapping[str, Any]
) -> Path:
    """Atomically replace and fsync the canonical durable authority record."""

    return _atomic_write_json(
        execution_root / AUTHORIZATION_FILENAME, record, replace=True
    )


def _validate_state_history(record: Mapping[str, Any]) -> None:
    history = record["state_history"]
    expected = STATE_HISTORY_CONTRACT[record["status"]]
    if history != expected:
        raise SealedExecutionStateError(
            f"{REFUSE_TO_RUN}: state history is not the exact legal prefix for "
            f"{record['status']}"
        )


def _validate_state_earned_fields(record: Mapping[str, Any]) -> None:
    contract = STATE_EARNED_FIELD_CONTRACT[record["status"]]
    for field, rule in contract.items():
        present = record[field] is not None
        if rule == "ABSENT" and present:
            raise SealedExecutionStateError(
                f"{REFUSE_TO_RUN}: {record['status']} carries future field {field}"
            )
        if rule == "REQUIRED" and not present:
            raise SealedExecutionStateError(
                f"{REFUSE_TO_RUN}: {record['status']} has not earned field {field}"
            )
        if present:
            _require_hex_digest(record[field], field)
    if (
        record["execution_result_digest"] is not None
        and record["evidence_bundle_digest"] is None
    ):
        raise SealedExecutionStateError(
            f"{REFUSE_TO_RUN}: a result digest cannot exist without its evidence digest"
        )


def _validate_artifact_matrix(
    execution_root: Path,
    record: Mapping[str, Any],
    *,
    allow_prepared_manifest_recovery: bool = False,
) -> None:
    paths = {
        "manifest": execution_root / MANIFEST_FILENAME,
        "evidence": execution_root / EVIDENCE_FILENAME,
        "result": execution_root / RESULT_FILENAME,
    }
    exists = {name: path.exists() for name, path in paths.items()}
    status = record["status"]
    if status == STATE_PREPARED:
        permitted_manifest = allow_prepared_manifest_recovery and exists["manifest"]
        if (exists["manifest"] and not permitted_manifest) or exists["evidence"] or exists["result"]:
            raise SealedExecutionIntegrityError(
                f"{REFUSE_TO_RUN}: PREPARED has an impossible published artifact set"
            )
        return
    if not exists["manifest"]:
        raise SealedExecutionIntegrityError(
            f"{REFUSE_TO_RUN}: {status} requires canonical {MANIFEST_FILENAME}"
        )
    manifest = _read_ascii_json(paths["manifest"], "the canonical manifest")
    validated = validate_sealed_sample_manifest(
        manifest,
        execution_id=record["execution_id"],
        validator_definition_sha256=record["validator_definition_sha256"],
    )
    if validated["manifest_sha256"] != record["collection_manifest_digest"]:
        raise SealedExecutionIntegrityError(
            f"{REFUSE_TO_RUN}: authority and canonical manifest digests disagree"
        )
    if status == STATE_COLLECTED_FROZEN and (exists["evidence"] or exists["result"]):
        raise SealedExecutionIntegrityError(
            f"{REFUSE_TO_RUN}: COLLECTED_FROZEN carries execution artifacts"
        )
    if status == STATE_EXECUTION_STARTED:
        checkpoint = {
            "evidence_artifact": exists["evidence"],
            "evidence_digest": record["evidence_bundle_digest"] is not None,
            "result_artifact": exists["result"],
            "result_digest": record["execution_result_digest"] is not None,
        }
        allowed = [
            {key: value for key, value in row.items() if key != "checkpoint"}
            for row in EXECUTION_STARTED_ALLOWED_CHECKPOINTS
        ]
        if checkpoint not in allowed:
            raise SealedExecutionIntegrityError(
                f"{REFUSE_TO_RUN}: EXECUTION_STARTED has an unreachable "
                f"artifact/digest checkpoint {checkpoint}"
            )
    if status == STATE_FINALIZED and not (exists["evidence"] and exists["result"]):
        raise SealedExecutionIntegrityError(
            f"{REFUSE_TO_RUN}: FINALIZED requires evidence and result artifacts"
        )
    if exists["evidence"]:
        evidence = _read_evidence_artifact(execution_root, record=record)
        if record["evidence_bundle_digest"] is not None and (
            evidence["evidence_bundle_digest"] != record["evidence_bundle_digest"]
        ):
            raise SealedExecutionIntegrityError(
                f"{REFUSE_TO_RUN}: authority and evidence digests disagree"
            )
    if exists["result"]:
        result = _read_result_artifact_shallow(execution_root, record=record)
        if record["execution_result_digest"] is not None and (
            result["result_sha256"] != record["execution_result_digest"]
        ):
            raise SealedExecutionIntegrityError(
                f"{REFUSE_TO_RUN}: authority and result digests disagree"
            )


def read_execution_authorization(
    execution_root: Path,
    *,
    validator_definition_sha256: str,
    _allow_prepared_manifest_recovery: bool = False,
) -> dict[str, Any]:
    """Read the durable lock record, refusing every authority tamper.

    The record is never trusted: its own digest is recomputed, its execution id
    is re-derived from its authority, and every hash, the window, the provider
    set and the candidate identity are compared against this module's bound
    constants. A record that fails any of them cannot authorise anything.
    """

    root = _canonical_execution_root(execution_root, create=False)
    path = root / AUTHORIZATION_FILENAME
    if not path.exists():
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: no {AUTHORIZATION_SCHEMA_VERSION} record exists "
            f"at {AUTHORIZATION_FILENAME}"
        )
    try:
        record = _read_ascii_json(path, "the authorization record")
    except SealedExecutionIntegrityError as error:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: the authorization record is not readable ascii JSON"
        ) from error
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
        "execution_root_sha256": _execution_root_sha256(root),
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
    expected_id = derive_execution_id(
        validator_definition_sha256, execution_root=root
    )
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
    _validate_state_history(record)
    _validate_state_earned_fields(record)
    _validate_artifact_matrix(
        root,
        record,
        allow_prepared_manifest_recovery=_allow_prepared_manifest_recovery,
    )
    return record


def sealed_execution_status(
    execution_root: Path, *, validator_definition_sha256: str
) -> str:
    """Return the durable execution state, NOT_PREPARED when none exists."""

    if not (execution_root / AUTHORIZATION_FILENAME).exists():
        return STATE_NOT_PREPARED
    record = read_execution_authorization(
        execution_root, validator_definition_sha256=validator_definition_sha256
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
    if manifest["collection_method"] != COLLECTION_METHOD:
        raise SealedSampleManifestError(
            "the collection manifest names another collection owner"
        )
    if manifest["collection_method_version"] != COLLECTION_METHOD_VERSION:
        raise SealedSampleManifestError(
            "the collection manifest names another collection method version"
        )
    providers = manifest["provider_ids"]
    if not isinstance(providers, (list, tuple)):
        raise SealedSampleManifestError("provider_ids must be a list")
    if len(set(providers)) != len(providers):
        raise SealedSampleManifestError(
            "the collection manifest names a provider twice"
        )
    if tuple(providers) != SEALED_PROVIDER_IDS:
        raise SealedSampleManifestError(
            f"the collection manifest names providers {providers}, not the canonical "
            f"ordered set {list(SEALED_PROVIDER_IDS)}"
        )

    files = manifest["files"]
    if not isinstance(files, (list, tuple)):
        raise SealedSampleManifestError("files must be a list")
    symbols = _provider_instrument_symbols()
    exchanges = _provider_exchanges()
    endpoints = _provider_endpoints()
    window_start = _parse_instant(SEALED_WINDOW_START_ISO, "the sealed window start")
    window_end = _parse_instant(SEALED_WINDOW_END_ISO, "the sealed window end")
    seen: set[str] = set()
    if len(files) != len(SEALED_PROVIDER_IDS):
        raise SealedSampleManifestError(
            "the collection manifest must carry exactly one file per required provider"
        )
    for expected_provider_id, row in zip(SEALED_PROVIDER_IDS, files, strict=True):
        if not isinstance(row, Mapping):
            raise SealedSampleManifestError("every manifest file entry must be a mapping")
        _require_exact_keys(
            row,
            MANIFEST_FILE_REQUIRED_KEYS + MANIFEST_MISSING_KEYS,
            "a manifest file entry",
        )
        provider_id = row["provider_id"]
        if provider_id != expected_provider_id:
            raise SealedSampleManifestError(
                "manifest file entries must use canonical provider order"
            )
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
        expected_path = _raw_relative_path(provider_id)
        if row["path"] != expected_path:
            raise SealedSampleManifestError(
                f"{provider_id} raw path must be the frozen {expected_path!r}"
            )
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
        if row["byte_count"] == 0:
            raise SealedSampleManifestError(f"{provider_id} raw file is empty")
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
        if provenance["endpoint"] != endpoints[provider_id]:
            raise SealedSampleManifestError(
                f"{provider_id} names another endpoint than the frozen policy"
            )
        request_count = _require_count(
            provenance["request_count"], f"{provider_id} request_count"
        )
        if request_count == 0:
            raise SealedSampleManifestError(
                f"{provider_id} request_count must be positive"
            )
        if row["collection_source_identifier"] != _collection_source_identifier(
            provider_id
        ):
            raise SealedSampleManifestError(
                f"{provider_id} collection source identity is not canonical"
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


RAW_RECORD_REQUIRED_KEYS = (
    "close",
    "exchange",
    "fallback_used",
    "high",
    "ingested_at",
    "low",
    "open",
    "price_source_policy_version",
    "price_source_roles",
    "provider",
    "schema_version",
    "symbol",
    "timeframe",
    "timestamp",
    "volume",
)


@dataclass(frozen=True)
class VerifiedRawFile:
    provider_id: str
    relative_path: str
    sha256: str
    raw_bytes: bytes
    bars: tuple[OhlcvBar, ...]
    device: int
    inode: int


@dataclass(frozen=True)
class VerifiedRawCollection:
    manifest: Mapping[str, Any]
    files: tuple[VerifiedRawFile, ...]

    @property
    def histories(self) -> Mapping[str, tuple[OhlcvBar, ...]]:
        return MappingProxyType({row.provider_id: row.bars for row in self.files})


def _read_regular_file_under_root(
    root: Path, relative_path: str
) -> tuple[bytes, os.stat_result]:
    """Read one regular file with no symlink or traversal component."""

    relative = Path(relative_path)
    if relative.is_absolute() or not relative.parts or any(
        part in ("", ".", "..") for part in relative.parts
    ):
        raise SealedSampleManifestError(
            f"raw path {relative_path!r} is not a safe relative path"
        )
    directory_descriptor = os.open(
        root, os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    )
    opened_directories = [directory_descriptor]
    file_descriptor: int | None = None
    try:
        current = directory_descriptor
        for part in relative.parts[:-1]:
            current = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=current,
            )
            opened_directories.append(current)
        file_descriptor = os.open(
            relative.parts[-1],
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=current,
        )
        metadata = os.fstat(file_descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise SealedSampleManifestError(
                f"raw path {relative_path!r} is not a regular file"
            )
        chunks = []
        while True:
            chunk = os.read(file_descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks), metadata
    except (FileNotFoundError, NotADirectoryError, OSError) as error:
        if isinstance(error, SealedSampleManifestError):
            raise
        raise SealedSampleManifestError(
            f"raw file {relative_path!r} does not exist as a safe regular file"
        ) from error
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)
        for descriptor in reversed(opened_directories):
            os.close(descriptor)


def _raw_record_to_bar(record: Any, *, provider_id: str, line_number: int) -> OhlcvBar:
    what = f"{provider_id} raw row {line_number}"
    if not isinstance(record, Mapping):
        raise SealedSampleManifestError(f"{what} is not a mapping")
    _require_exact_keys(record, RAW_RECORD_REQUIRED_KEYS, what)
    expected = {
        "exchange": _provider_exchanges()[provider_id],
        "fallback_used": False,
        "price_source_policy_version": PRICE_SOURCE_POLICY_VERSION,
        "price_source_roles": list(_provider_roles()[provider_id]),
        "provider": provider_id,
        "schema_version": RAW_ARTIFACT_SCHEMA_VERSION,
        "symbol": _provider_instrument_symbols()[provider_id],
        "timeframe": SEALED_BAR_INTERVAL,
    }
    for field, value in expected.items():
        if record[field] != value:
            raise SealedSampleManifestError(
                f"{what} declares {field}={record[field]!r}, not {value!r}"
            )
    timestamp = _parse_instant(record["timestamp"], f"{what} timestamp")
    ingested_at = _parse_instant(record["ingested_at"], f"{what} ingested_at")
    if timestamp.minute or timestamp.second or timestamp.microsecond:
        raise SealedSampleManifestError(f"{what} is not aligned to an hourly boundary")
    if not SEALED_WINDOW_START <= timestamp <= SEALED_WINDOW_END:
        raise SealedSampleManifestError(f"{what} lies outside the sealed window")
    if ingested_at < timestamp + timedelta(hours=1):
        raise SealedSampleManifestError(
            f"{what} claims availability before the hourly bar closed"
        )
    numbers: dict[str, Decimal] = {}
    for field in ("open", "high", "low", "close", "volume"):
        try:
            value = Decimal(record[field])
        except Exception as error:
            raise SealedSampleManifestError(f"{what} {field} is not decimal") from error
        if not value.is_finite():
            raise SealedSampleManifestError(f"{what} {field} is not finite")
        numbers[field] = value
    if min(numbers[name] for name in ("open", "high", "low", "close")) <= 0:
        raise SealedSampleManifestError(f"{what} carries a non-positive price")
    if numbers["volume"] < 0:
        raise SealedSampleManifestError(f"{what} carries negative volume")
    if numbers["low"] > min(numbers["open"], numbers["close"]) or numbers[
        "high"
    ] < max(numbers["open"], numbers["close"]):
        raise SealedSampleManifestError(f"{what} violates OHLC candle invariants")
    return OhlcvBar(
        timestamp=timestamp,
        exchange=record["exchange"],
        symbol=record["symbol"],
        timeframe=record["timeframe"],
        open=numbers["open"],
        high=numbers["high"],
        low=numbers["low"],
        close=numbers["close"],
        volume=numbers["volume"],
        provider=provider_id,
        ingested_at=ingested_at,
    )


def _decode_raw_history(raw_bytes: bytes, *, provider_id: str) -> tuple[OhlcvBar, ...]:
    try:
        decoded = gzip.decompress(raw_bytes).decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise SealedSampleManifestError(
            f"{provider_id} raw file is not valid UTF-8 gzip JSONL"
        ) from error
    bars = []
    for line_number, line in enumerate(decoded.splitlines(), 1):
        if not line:
            raise SealedSampleManifestError(
                f"{provider_id} raw row {line_number} is empty"
            )
        try:
            record = json.loads(line)
        except ValueError as error:
            raise SealedSampleManifestError(
                f"{provider_id} raw row {line_number} is not JSON"
            ) from error
        bars.append(
            _raw_record_to_bar(
                record, provider_id=provider_id, line_number=line_number
            )
        )
    if not bars:
        raise SealedSampleManifestError(f"{provider_id} raw file has no rows")
    if [bar.timestamp for bar in bars] != sorted(bar.timestamp for bar in bars):
        raise SealedSampleManifestError(
            f"{provider_id} raw rows are not in timestamp order"
        )
    return tuple(bars)


def _verify_raw_metadata(
    row: Mapping[str, Any], raw_bytes: bytes, bars: Sequence[OhlcvBar]
) -> None:
    provider_id = row["provider_id"]
    timestamps = [bar.timestamp for bar in bars]
    counts: dict[datetime, int] = {}
    for timestamp in timestamps:
        counts[timestamp] = counts.get(timestamp, 0) + 1
    expected = []
    cursor = SEALED_WINDOW_START
    while cursor <= SEALED_WINDOW_END:
        expected.append(cursor)
        cursor += timedelta(hours=1)
    missing = [item.isoformat() for item in expected if item not in counts]
    duplicates = sorted(
        item.isoformat() for item, count in counts.items() if count > 1
    )
    actual = {
        "byte_count": len(raw_bytes),
        "duplicate_interval_count": len(duplicates),
        "duplicate_intervals": duplicates,
        "first_observation": min(timestamps).isoformat(),
        "last_observation": max(timestamps).isoformat(),
        "missing_interval_count": len(missing),
        "missing_intervals": missing,
        "row_count": len(bars),
    }
    for field, value in actual.items():
        if row[field] != value:
            raise SealedSampleManifestError(
                f"{provider_id} manifest {field} does not match its raw bytes"
            )


def verify_collected_file_digests(
    manifest: Mapping[str, Any], execution_root: Path, *, execution_read: bool = False
) -> VerifiedRawCollection:
    """Securely reopen, hash and technically verify every canonical raw file."""

    root = _canonical_execution_root(execution_root, create=False)
    raw_root = root / RAW_COLLECTION_DIRNAME
    if raw_root.is_symlink() or not raw_root.is_dir():
        raise SealedSampleManifestError(
            f"the canonical {RAW_COLLECTION_DIRNAME} directory is missing or unsafe"
        )
    expected_names = {
        Path(_raw_relative_path(provider_id)).name
        for provider_id in SEALED_PROVIDER_IDS
    }
    actual_names = {path.name for path in raw_root.iterdir()}
    if actual_names != expected_names:
        raise SealedSampleManifestError(
            f"raw collection files are {sorted(actual_names)}, not "
            f"{sorted(expected_names)}"
        )
    verified = []
    seen_files: set[tuple[int, int]] = set()
    for index, row in enumerate(manifest["files"]):
        raw_bytes, metadata = _read_regular_file_under_root(root, row["path"])
        if execution_read and index == 0:
            _crash_injection_point("after_first_raw_file_read")
        identity = (metadata.st_dev, metadata.st_ino)
        if identity in seen_files:
            raise SealedSampleManifestError(
                "two providers resolve to the same raw file inode"
            )
        seen_files.add(identity)
        digest = hashlib.sha256(raw_bytes).hexdigest()
        if digest != row["sha256"]:
            raise SealedSampleManifestError(
                f"{row['provider_id']} raw file changed after it was hashed: "
                f"{row['path']} digests to {digest}, not {row['sha256']}"
            )
        bars = _decode_raw_history(raw_bytes, provider_id=row["provider_id"])
        _verify_raw_metadata(row, raw_bytes, bars)
        verified.append(
            VerifiedRawFile(
                provider_id=row["provider_id"],
                relative_path=row["path"],
                sha256=digest,
                raw_bytes=raw_bytes,
                bars=bars,
                device=metadata.st_dev,
                inode=metadata.st_ino,
            )
        )
    return VerifiedRawCollection(
        manifest=MappingProxyType(dict(manifest)), files=tuple(verified)
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

SEALED_EVIDENCE_ARTIFACT_SCHEMA_VERSION = "BTC019_V3_SEALED_EVIDENCE_ARTIFACT_V2"
SEALED_EVIDENCE_ARTIFACT_FIELDS = (
    "bound_protocol_definition_sha256",
    "candidate_method_version",
    "candidate_series_id",
    "evidence_artifact_sha256",
    "evidence_builder_definition_sha256",
    "evidence_builder_function",
    "evidence_builder_module",
    "evidence_builder_version",
    "evidence_bundle",
    "evidence_bundle_digest",
    "execution_id",
    "parent_validator_definition_sha256",
    "schema_version",
    "sealed_sample_manifest_sha256",
    "validator_definition_sha256",
)

EXCLUSIVE_LOCKING_RULE = (
    f"Every prepare, freeze, begin, execute, recover and finalized-result read "
    f"takes fcntl.flock(LOCK_EX) on the fixed {EXECUTOR_LOCK_FILENAME} regular "
    "file. The lock covers the canonical authority read, validation and state "
    "write; execute retains it through evidence/result publication and FINALIZED."
)
ATOMIC_PERSISTENCE_RULE = (
    "Authority, manifest, evidence and result JSON are written to a temporary "
    "regular file in the destination directory, fsynced, atomically published "
    "with os.replace and followed by a directory fsync. Evidence and result "
    "targets are immutable and refuse replacement. Durability assumes POSIX "
    "local-filesystem fsync and atomic same-directory rename semantics."
)
EXECUTION_ROOT_POLICY = (
    "The caller selects one directory, not an authorization file. Preparation "
    "canonicalizes its real path and binds that path's SHA-256 into the authority "
    "and execution id. Every artifact then has one fixed filename below that root; "
    "moving or copying the authority to another root refuses. Raw provider files "
    "have fixed relative paths below raw_collection and every symlink, traversal, "
    "non-regular file, duplicate inode and unexpected directory entry is refused."
)
RAW_REVALIDATION_RULE = (
    "Freezing and execution both securely reopen every fixed provider file, "
    "recompute SHA-256 and byte count, parse the gzip JSONL owner schema, and "
    "recompute row count, first/last timestamp, missing intervals and duplicate "
    "intervals. After EXECUTION_STARTED is durable, execute first reloads and "
    "fully validates the canonical persisted manifest and compares its canonical "
    "digest to the authority; raw verification consumes that exact in-memory "
    "snapshot before the fixed evidence builder is invoked."
)
POST_START_MANIFEST_VALIDATION_RULE_ID = (
    "AUTHORITY_BOUND_MANIFEST_REVALIDATED_AFTER_EXECUTION_STARTED_V1"
)
POST_START_MANIFEST_VALIDATION_RULE = (
    "Immediately after EXECUTION_STARTED is durably persisted and before any raw "
    "file is opened, reload the canonical persisted manifest, validate its exact "
    "schema, self-digest, V3/V2/V1 authority bindings, execution id, sealed window, "
    "provider/file associations and raw digest declarations, and carry that exact "
    "validated snapshot into raw verification. Any failure refuses before evidence "
    "construction."
)
MANIFEST_DIGEST_EQUALITY_RULE_ID = "PERSISTED_MANIFEST_DIGEST_EQUALS_AUTHORITY_V1"
MANIFEST_DIGEST_EQUALITY_RULE = (
    "The canonical digest recomputed from the post-start persisted manifest must "
    "equal authority.collection_manifest_digest exactly. A re-digested changed "
    "manifest is still refused because its new digest is not the frozen authority; "
    "a changed manifest retaining the old digest is refused by self-digest validation."
)
EVIDENCE_CONSTRUCTION_RULE = (
    "The public in-memory validator is DRY_RUN_SYNTHETIC only. The live API accepts "
    "neither a caller-supplied builder nor a prebuilt evidence mapping. After the "
    "one-shot transition and authority-bound manifest/raw verification, the executor "
    "verifies and invokes exactly one repository-owned module/function with the "
    "immutable VerifiedRawCollection. The contract and evidence artifact bind the "
    "builder version, module, function and transitive implementation-definition hash; "
    "any code or identity drift refuses until a new V2 contract hash is issued. The "
    "evidence artifact and its authority digest are durable before certified V1 "
    "validation begins."
)
RECOVERY_RULE = (
    "Normal execute accepts COLLECTED_FROZEN only. EXECUTION_STARTED is permanently "
    "consumed: recovery never reopens raw files and never invokes the builder. If "
    "no result exists it reports EXECUTION_INTERRUPTED_NO_RESULT; if immutable "
    "evidence and result exist it verifies their full cross-bindings and may "
    "complete FINALIZED without recomputing evidence."
)
RESULT_RESTORE_RULE = (
    "A finalized restore verifies exact schemas and self-digests, execution id, "
    "V3/V2/V1 hashes, manifest and evidence digests, candidate identity, verdict "
    "vocabulary, all hard structures and the authorization result digest. It "
    "replays certified validation over persisted evidence only to cross-check the "
    "result; it never opens raw data."
)


def _sealed_sample_contract_block() -> dict[str, Any]:
    return {
        "bar_interval": SEALED_BAR_INTERVAL,
        "collection_manifest_file_required_keys": list(
            MANIFEST_FILE_REQUIRED_KEYS + MANIFEST_MISSING_KEYS
        ),
        "collection_manifest_required_keys": list(MANIFEST_REQUIRED_KEYS),
        "collection_manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "canonical_manifest_filename": MANIFEST_FILENAME,
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
        "raw_artifact_schema_version": RAW_ARTIFACT_SCHEMA_VERSION,
        "raw_collection_directory": RAW_COLLECTION_DIRNAME,
        "raw_file_paths": {
            provider_id: _raw_relative_path(provider_id)
            for provider_id in SEALED_PROVIDER_IDS
        },
        "raw_record_required_keys": list(RAW_RECORD_REQUIRED_KEYS),
        "raw_revalidation_rule": RAW_REVALIDATION_RULE,
        "post_start_manifest_validation_rule_id": (
            POST_START_MANIFEST_VALIDATION_RULE_ID
        ),
        "post_start_manifest_validation_rule": POST_START_MANIFEST_VALIDATION_RULE,
        "manifest_digest_equality_rule_id": MANIFEST_DIGEST_EQUALITY_RULE_ID,
        "manifest_digest_equality_rule": MANIFEST_DIGEST_EQUALITY_RULE,
        "collection_plan": sealed_collection_plan(),
        "timezone": SEALED_TIMEZONE,
        "window_end": SEALED_WINDOW_END_ISO,
        "window_rule": SEALED_WINDOW_RULE,
        "window_start": SEALED_WINDOW_START_ISO,
    }


def _sealed_execution_control_block() -> dict[str, Any]:
    builder = fixed_evidence_builder_definition()
    return {
        "atomic_persistence_rule": ATOMIC_PERSISTENCE_RULE,
        "authorization_record_required_keys": list(AUTHORIZATION_REQUIRED_KEYS),
        "authorization_record_schema_version": AUTHORIZATION_SCHEMA_VERSION,
        "authorization_filename": AUTHORIZATION_FILENAME,
        "authorization_rule": SEALED_EXECUTION_AUTHORIZATION_RULE,
        "authority_rule": AUTHORITY_RULE,
        "authority_rule_id": AUTHORITY_RULE_ID,
        "crash_injection_points": list(CRASH_INJECTION_POINTS),
        "durable_lock": True,
        "evidence_artifact_fields": list(SEALED_EVIDENCE_ARTIFACT_FIELDS),
        "evidence_artifact_filename": EVIDENCE_FILENAME,
        "evidence_artifact_schema_version": SEALED_EVIDENCE_ARTIFACT_SCHEMA_VERSION,
        "evidence_builder": builder,
        "evidence_builder_version": SEALED_EVIDENCE_BUILDER_VERSION,
        "evidence_builder_module": SEALED_EVIDENCE_BUILDER_MODULE,
        "evidence_builder_function": SEALED_EVIDENCE_BUILDER_FUNCTION,
        "evidence_builder_definition_sha256": (
            SEALED_EVIDENCE_BUILDER_DEFINITION_SHA256
        ),
        "evidence_construction_rule": EVIDENCE_CONSTRUCTION_RULE,
        "exclusive_locking_rule": EXCLUSIVE_LOCKING_RULE,
        "execution_root_policy": EXECUTION_ROOT_POLICY,
        "execution_id_rule": EXECUTION_ID_RULE,
        "execution_id_prefix": EXECUTION_ID_PREFIX,
        "execution_states": list(EXECUTION_STATES),
        "execution_state_rule": EXECUTION_STATE_RULE,
        "exact_state_artifact_matrix": {
            state: dict(value) for state, value in STATE_ARTIFACT_CONTRACT.items()
        },
        "exact_state_earned_fields": {
            state: dict(value) for state, value in STATE_EARNED_FIELD_CONTRACT.items()
        },
        "exact_state_histories": {
            state: [dict(row) for row in history]
            for state, history in STATE_HISTORY_CONTRACT.items()
        },
        "execution_started_allowed_checkpoints": [
            dict(row) for row in EXECUTION_STARTED_ALLOWED_CHECKPOINTS
        ],
        "legal_transitions": [dict(row) for row in LEGAL_EXECUTION_TRANSITIONS],
        "market_derived_fields_null_until_earned": list(
            MARKET_DERIVED_AUTHORIZATION_FIELDS
        ),
        "no_result_dependent_behaviour": NO_RESULT_DEPENDENT_BEHAVIOUR,
        "one_shot_rule": ONE_SHOT_RULE,
        "one_shot_rule_id": ONE_SHOT_RULE_ID,
        "post_review_immutability": POST_REVIEW_IMMUTABILITY,
        "preparation_reads_no_sealed_bytes": True,
        "recovery_rule": RECOVERY_RULE,
        "refusal_conditions": list(EXECUTION_REFUSAL_CONDITIONS),
        "result_filename": RESULT_FILENAME,
        "result_restore_rule": RESULT_RESTORE_RULE,
        "result_schema_fields": list(SEALED_EXECUTION_RESULT_FIELDS),
        "result_schema_version": SEALED_EXECUTION_RESULT_SCHEMA_VERSION,
        "terminal_execution_states": list(TERMINAL_EXECUTION_STATES),
        "terminal_outcome_rule": TERMINAL_OUTCOME_RULE,
        "terminal_outcomes": dict(TERMINAL_OUTCOMES),
        "the_only_call_that_may_read_sealed_bytes": "execute_sealed_validation",
        "lock_filename": EXECUTOR_LOCK_FILENAME,
        "normal_execute_allowed_from": STATE_COLLECTED_FROZEN,
        "normal_execute_forbidden_from": [STATE_EXECUTION_STARTED, STATE_FINALIZED],
        "started_consumes_authority_permanently": True,
        "supersedes_failed_executor_hash": PREVIOUS_EXECUTOR_DEFINITION_SHA256,
        "failed_executor_implementation_commit": (
            PREVIOUS_EXECUTOR_IMPLEMENTATION_COMMIT
        ),
        "failure_review_commit": PREVIOUS_EXECUTOR_REVIEW_COMMIT,
        "failure_review_result": PREVIOUS_EXECUTOR_REVIEW_RESULT,
        "executor_lineage": [
            {
                "definition_sha256": FAILED_EXECUTOR_DEFINITION_SHA256,
                "implementation_commit": FAILED_EXECUTOR_IMPLEMENTATION_COMMIT,
                "review_commit": FAILED_EXECUTOR_REVIEW_COMMIT,
                "review_result": FAILED_EXECUTOR_REVIEW_RESULT,
            },
            {
                "definition_sha256": PREVIOUS_EXECUTOR_DEFINITION_SHA256,
                "implementation_commit": PREVIOUS_EXECUTOR_IMPLEMENTATION_COMMIT,
                "review_commit": PREVIOUS_EXECUTOR_REVIEW_COMMIT,
                "review_result": PREVIOUS_EXECUTOR_REVIEW_RESULT,
            },
        ],
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
        "supersedes_failed_executor_hash": PREVIOUS_EXECUTOR_DEFINITION_SHA256,
        "failed_executor_implementation_commit": (
            PREVIOUS_EXECUTOR_IMPLEMENTATION_COMMIT
        ),
        "failure_review_commit": PREVIOUS_EXECUTOR_REVIEW_COMMIT,
        "failure_review_result": PREVIOUS_EXECUTOR_REVIEW_RESULT,
        "executor_lineage": [
            dict(row)
            for row in successor["sealed_execution_control"]["executor_lineage"]
        ],
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

_CAPABILITY_SECRET = object()


class _ConsumedExecutionCapability:
    """Process-local proof created only after the durable begin transition."""

    __slots__ = ("record", "_secret")

    def __init__(self, record: Mapping[str, Any], *, _secret: object) -> None:
        if _secret is not _CAPABILITY_SECRET:
            raise SealedExecutionAuthorizationError(
                f"{REFUSE_TO_RUN}: live capability is executor-owned"
            )
        self.record = MappingProxyType(dict(record))
        self._secret = _secret


def _consumed_capability(record: Mapping[str, Any]) -> _ConsumedExecutionCapability:
    if record["status"] != STATE_EXECUTION_STARTED:
        raise SealedExecutionStateError(
            f"{REFUSE_TO_RUN}: capability requires durable {STATE_EXECUTION_STARTED}"
        )
    return _ConsumedExecutionCapability(record, _secret=_CAPABILITY_SECRET)


def _authorize_sample_window(
    *,
    start: datetime,
    end: datetime,
    execution_mode: str,
    capability: _ConsumedExecutionCapability | None,
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
    if capability is None or capability._secret is not _CAPABILITY_SECRET:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: {EXECUTION_MODE_SEALED} requires the executor-owned "
            "consumed capability"
        )
    authorization = capability.record
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
    """Validate synthetic evidence only; the live sealed path is executor-owned."""

    if execution_mode == EXECUTION_MODE_SEALED or sealed_execution_authorization is not None:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: in-memory evidence and authorization cannot enter "
            f"{EXECUTION_MODE_SEALED}; use execute_sealed_validation(execution_root, "
            "repository_root=...)"
        )
    return _validate_v3_candidate_core(
        evidence_bundle,
        repository_root=repository_root,
        execution_mode=execution_mode,
        capability=None,
    )


def _validate_v3_candidate_core(
    evidence_bundle: Mapping[str, Any],
    *,
    repository_root: Path,
    execution_mode: str,
    capability: _ConsumedExecutionCapability | None,
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
    if execution_mode == EXECUTION_MODE_SEALED and capability is None:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: sealed validation requires a consumed capability"
        )
    if execution_mode != EXECUTION_MODE_SEALED and capability is not None:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: a live capability may accompany only "
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
        capability=capability,
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

    if capability is None:
        sealed_block = dict(DRY_RUN_SEALED_EXECUTION_BLOCK)
    else:
        sealed_execution_authorization = capability.record
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


def _bind_input_provenance(
    bundle: Mapping[str, Any], record: Mapping[str, Any]
) -> None:
    """Refuse evidence that does not bind the consumed durable authority."""

    provenance = bundle.get("provenance")
    if not isinstance(provenance, Mapping):
        raise ValidatorInputError("the provenance block must be a mapping")
    if provenance.get("evidence_builder_version") != SEALED_EVIDENCE_BUILDER_VERSION:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: live evidence was not built by the hash-bound builder"
        )
    declared = provenance.get("sample_manifest_digest")
    if declared != record["collection_manifest_digest"]:
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: evidence binds manifest {declared!r}, not the "
            f"frozen {record['collection_manifest_digest']!r}"
        )
    identities = bundle.get("identities")
    if not isinstance(identities, Mapping):
        raise ValidatorInputError("the identities block must be a mapping")
    for field in ("candidate_method_version", "candidate_series_id"):
        if identities.get(field) != record[field]:
            raise SealedExecutionAuthorizationError(
                f"{REFUSE_TO_RUN}: evidence {field} does not bind the authority"
            )
    declared_providers = identities.get("provider_ids")
    if not isinstance(declared_providers, (list, tuple)) or tuple(
        sorted(declared_providers)
    ) != tuple(record["allowed_provider_ids"]):
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: evidence names providers {declared_providers!r}, "
            f"not {record['allowed_provider_ids']!r}"
        )


def _evidence_builder_invocation_point(
    builder: Any, collection: VerifiedRawCollection
) -> None:
    """No-op audit hook monkeypatched only by synthetic ownership tests."""


def _invoke_fixed_evidence_builder(
    collection: VerifiedRawCollection,
) -> Mapping[str, Any]:
    """Verify and invoke the canonical owner; no caller dependency enters here."""

    fixed_evidence_builder_definition()
    builder = _evidence_owner.build_sealed_evidence
    if builder is not _FIXED_SEALED_EVIDENCE_BUILDER:
        raise ValidatorBindingError(
            f"{REFUSE_TO_RUN}: live evidence builder is not the fixed owner"
        )
    _evidence_builder_invocation_point(builder, collection)
    return builder(collection)


def _evidence_artifact(
    bundle: Mapping[str, Any], *, record: Mapping[str, Any]
) -> dict[str, Any]:
    digest = evidence_bundle_digest(bundle)
    artifact: dict[str, Any] = {
        "bound_protocol_definition_sha256": BOUND_PROTOCOL_DEFINITION_SHA256_EXPECTED,
        "candidate_method_version": record["candidate_method_version"],
        "candidate_series_id": record["candidate_series_id"],
        "evidence_builder_definition_sha256": (
            SEALED_EVIDENCE_BUILDER_DEFINITION_SHA256
        ),
        "evidence_builder_function": SEALED_EVIDENCE_BUILDER_FUNCTION,
        "evidence_builder_module": SEALED_EVIDENCE_BUILDER_MODULE,
        "evidence_builder_version": SEALED_EVIDENCE_BUILDER_VERSION,
        "evidence_bundle": _v1.canonical_evidence_bundle(bundle),
        "evidence_bundle_digest": digest,
        "execution_id": record["execution_id"],
        "parent_validator_definition_sha256": PARENT_VALIDATOR_DEFINITION_SHA256,
        "schema_version": SEALED_EVIDENCE_ARTIFACT_SCHEMA_VERSION,
        "sealed_sample_manifest_sha256": record["collection_manifest_digest"],
        "validator_definition_sha256": record["validator_definition_sha256"],
    }
    artifact["evidence_artifact_sha256"] = _digest(artifact)
    return artifact


def _read_evidence_artifact(
    execution_root: Path, *, record: Mapping[str, Any]
) -> dict[str, Any]:
    artifact = _read_ascii_json(
        execution_root / EVIDENCE_FILENAME, "the immutable evidence artifact"
    )
    missing = sorted(set(SEALED_EVIDENCE_ARTIFACT_FIELDS) - set(artifact))
    unknown = sorted(set(artifact) - set(SEALED_EVIDENCE_ARTIFACT_FIELDS))
    if missing or unknown:
        raise SealedExecutionIntegrityError(
            f"{REFUSE_TO_RUN}: evidence schema missing {missing}, unknown {unknown}"
        )
    expected = {
        "bound_protocol_definition_sha256": BOUND_PROTOCOL_DEFINITION_SHA256_EXPECTED,
        "candidate_method_version": record["candidate_method_version"],
        "candidate_series_id": record["candidate_series_id"],
        "evidence_builder_definition_sha256": (
            SEALED_EVIDENCE_BUILDER_DEFINITION_SHA256
        ),
        "evidence_builder_function": SEALED_EVIDENCE_BUILDER_FUNCTION,
        "evidence_builder_module": SEALED_EVIDENCE_BUILDER_MODULE,
        "evidence_builder_version": SEALED_EVIDENCE_BUILDER_VERSION,
        "execution_id": record["execution_id"],
        "parent_validator_definition_sha256": PARENT_VALIDATOR_DEFINITION_SHA256,
        "schema_version": SEALED_EVIDENCE_ARTIFACT_SCHEMA_VERSION,
        "sealed_sample_manifest_sha256": record["collection_manifest_digest"],
        "validator_definition_sha256": record["validator_definition_sha256"],
    }
    for field, value in expected.items():
        if artifact[field] != value:
            raise SealedExecutionIntegrityError(
                f"{REFUSE_TO_RUN}: evidence artifact {field} does not bind authority"
            )
    declared_artifact_digest = artifact["evidence_artifact_sha256"]
    body = {key: value for key, value in artifact.items() if key != "evidence_artifact_sha256"}
    if declared_artifact_digest != _digest(body):
        raise SealedExecutionIntegrityError(
            f"{REFUSE_TO_RUN}: evidence artifact digest does not reproduce"
        )
    bundle = artifact["evidence_bundle"]
    if not isinstance(bundle, Mapping):
        raise SealedExecutionIntegrityError(
            f"{REFUSE_TO_RUN}: persisted evidence bundle is not a mapping"
        )
    if artifact["evidence_bundle_digest"] != evidence_bundle_digest(bundle):
        raise SealedExecutionIntegrityError(
            f"{REFUSE_TO_RUN}: persisted evidence bundle digest does not reproduce"
        )
    _bind_input_provenance(bundle, record)
    return artifact


def _read_result_artifact_shallow(
    execution_root: Path, *, record: Mapping[str, Any]
) -> dict[str, Any]:
    result = _read_ascii_json(
        execution_root / RESULT_FILENAME, "the immutable result artifact"
    )
    missing = sorted(set(SEALED_EXECUTION_RESULT_FIELDS) - set(result))
    unknown = sorted(set(result) - set(SEALED_EXECUTION_RESULT_FIELDS))
    if missing or unknown:
        raise SealedExecutionIntegrityError(
            f"{REFUSE_TO_RUN}: result schema missing {missing}, unknown {unknown}"
        )
    declared = result["result_sha256"]
    body = {key: value for key, value in result.items() if key != "result_sha256"}
    if declared != _digest(body):
        raise SealedExecutionIntegrityError(
            f"{REFUSE_TO_RUN}: result digest does not reproduce"
        )
    expected = {
        "bound_protocol_definition_sha256": BOUND_PROTOCOL_DEFINITION_SHA256_EXPECTED,
        "candidate_evidence_digest": record.get("evidence_bundle_digest")
        or result["candidate_evidence_digest"],
        "candidate_method_version": record["candidate_method_version"],
        "candidate_series_id": record["candidate_series_id"],
        "execution_id": record["execution_id"],
        "parent_validator_definition_sha256": PARENT_VALIDATOR_DEFINITION_SHA256,
        "schema_version": SEALED_EXECUTION_RESULT_SCHEMA_VERSION,
        "sealed_sample_manifest_sha256": record["collection_manifest_digest"],
        "validator_definition_sha256": record["validator_definition_sha256"],
    }
    for field, value in expected.items():
        if result[field] != value:
            raise SealedExecutionIntegrityError(
                f"{REFUSE_TO_RUN}: result {field} does not bind authority"
            )
    if result["final_verdict"] not in VERDICT_VOCABULARY:
        raise SealedExecutionIntegrityError(
            f"{REFUSE_TO_RUN}: result carries an operational or unknown verdict"
        )
    if set(result["seven_hard_requirements"]) != set(HARD_REQUIREMENT_IDS):
        raise SealedExecutionIntegrityError(
            f"{REFUSE_TO_RUN}: result does not carry the seven hard requirements"
        )
    return result


def prepare_sealed_execution(
    repository_root: Path, *, authorization_dir: Path
) -> dict[str, Any]:
    """Exclusively create the one path-bound PREPARED authority."""

    contract = validator_definition(repository_root)
    if contract["sealed_sample"]["sealed_execution_authorized"] is not True:
        raise SealedExecutionNotAuthorizedError(
            f"{REFUSE_TO_PREPARE}: this contract does not authorise sealed execution"
        )
    semantic_delta(repository_root)
    digest = contract["validator_definition_sha256"]
    with _exclusive_executor_lock(authorization_dir, create_root=True) as root:
        existing = root / AUTHORIZATION_FILENAME
        if existing.exists():
            record = read_execution_authorization(
                root, validator_definition_sha256=digest
            )
            raise SealedExecutionStateError(
                f"{REFUSE_TO_PREPARE}: execution {record['execution_id']} already "
                f"exists in state {record['status']}"
            )
        for filename in (MANIFEST_FILENAME, EVIDENCE_FILENAME, RESULT_FILENAME):
            if (root / filename).exists():
                raise SealedExecutionIntegrityError(
                    f"{REFUSE_TO_PREPARE}: orphan control artifact {filename} exists"
                )
        record = _new_authorization_record(digest, execution_root=root)
        _validate_state_history(record)
        _validate_state_earned_fields(record)
        _write_execution_authorization(root, record)
        _crash_injection_point("after_prepared_write")
        return record


def record_frozen_collection_manifest(
    repository_root: Path,
    *,
    authorization_dir: Path,
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify raw bytes, durably publish the manifest, then freeze authority."""

    digest = validator_definition_sha256(repository_root)
    with _exclusive_executor_lock(authorization_dir) as root:
        record = read_execution_authorization(
            root,
            validator_definition_sha256=digest,
            _allow_prepared_manifest_recovery=True,
        )
        if record["status"] != STATE_PREPARED:
            raise SealedExecutionStateError(
                f"{REFUSE_TO_RUN}: collection freeze requires PREPARED, not "
                f"{record['status']}"
            )
        validated = validate_sealed_sample_manifest(
            manifest,
            execution_id=record["execution_id"],
            validator_definition_sha256=digest,
        )
        verify_collected_file_digests(validated, root)
        manifest_path = root / MANIFEST_FILENAME
        if manifest_path.exists():
            persisted = _read_ascii_json(manifest_path, "the canonical manifest")
            if _canonical_json(persisted) != _canonical_json(validated):
                raise SealedExecutionIntegrityError(
                    f"{REFUSE_TO_RUN}: an orphan manifest differs from this freeze"
                )
        else:
            _atomic_write_json(manifest_path, validated, replace=False)
        _crash_injection_point("after_manifest_persisted_before_collected_frozen")
        moved = _transition(
            record,
            to_state=STATE_COLLECTED_FROZEN,
            step=TRANSITION_FREEZE_COLLECTION,
        )
        moved["collection_manifest_digest"] = validated["manifest_sha256"]
        moved["authorization_record_sha256"] = _authorization_digest(moved)
        _write_execution_authorization(root, moved)
        _crash_injection_point("after_collected_frozen")
        return moved


def begin_sealed_execution(
    repository_root: Path, *, authorization_dir: Path
) -> dict[str, Any]:
    """Exclusively consume authority without opening a raw file."""

    digest = validator_definition_sha256(repository_root)
    with _exclusive_executor_lock(authorization_dir) as root:
        record = read_execution_authorization(
            root, validator_definition_sha256=digest
        )
        moved = _transition(
            record, to_state=STATE_EXECUTION_STARTED, step=TRANSITION_BEGIN
        )
        _write_execution_authorization(root, moved)
        _crash_injection_point("after_execution_started_before_raw_read")
        return moved


def _authority_bound_manifest_snapshot_after_start(
    root: Path,
    *,
    record: Mapping[str, Any],
    validator_definition_sha256: str,
) -> Mapping[str, Any]:
    """Reload and validate the exact manifest authority before any raw read."""

    persisted = _read_ascii_json(root / MANIFEST_FILENAME, "the canonical manifest")
    validated = validate_sealed_sample_manifest(
        persisted,
        execution_id=record["execution_id"],
        validator_definition_sha256=validator_definition_sha256,
    )
    actual = validated["manifest_sha256"]
    expected = record["collection_manifest_digest"]
    if actual != expected:
        raise SealedExecutionIntegrityError(
            f"{REFUSE_TO_RUN}: post-start canonical manifest digests to {actual}, "
            f"not the authority-bound {expected}"
        )
    # Detach the exact validated snapshot from the decoded persisted mapping.
    # Raw verification reads this snapshot, never another filesystem reload.
    return MappingProxyType(json.loads(_canonical_json(validated)))


def execute_sealed_validation(
    execution_root: Path,
    *,
    repository_root: Path,
) -> dict[str, Any]:
    """Consume COLLECTED_FROZEN and own the complete one-shot sealed path."""

    if isinstance(execution_root, Mapping):
        raise SealedExecutionAuthorizationError(
            f"{REFUSE_TO_RUN}: prebuilt evidence is forbidden on the live API"
        )
    contract = validator_definition(repository_root)
    digest = contract["validator_definition_sha256"]
    with _exclusive_executor_lock(execution_root) as root:
        record = read_execution_authorization(
            root, validator_definition_sha256=digest
        )
        if record["status"] != STATE_COLLECTED_FROZEN:
            raise SealedExecutionStateError(
                f"{REFUSE_TO_RUN}: normal execute requires COLLECTED_FROZEN, not "
                f"{record['status']}; consumed execution cannot retry"
            )
        started = _transition(
            record, to_state=STATE_EXECUTION_STARTED, step=TRANSITION_BEGIN
        )
        _write_execution_authorization(root, started)
        capability = _consumed_capability(started)
        _crash_injection_point("after_execution_started_before_raw_read")

        manifest = _authority_bound_manifest_snapshot_after_start(
            root,
            record=started,
            validator_definition_sha256=digest,
        )
        collection = verify_collected_file_digests(
            manifest, root, execution_read=True
        )
        bundle = _invoke_fixed_evidence_builder(collection)
        if not isinstance(bundle, Mapping):
            raise ValidatorInputError("the sealed evidence builder returned no mapping")
        _bind_input_provenance(bundle, started)

        evidence = _evidence_artifact(bundle, record=started)
        _atomic_write_json(root / EVIDENCE_FILENAME, evidence, replace=False)
        _crash_injection_point("after_evidence_persisted")
        checkpoint = dict(started)
        checkpoint["evidence_bundle_digest"] = evidence["evidence_bundle_digest"]
        checkpoint["authorization_record_sha256"] = _authorization_digest(checkpoint)
        _write_execution_authorization(root, checkpoint)

        validation = _validate_v3_candidate_core(
            bundle,
            repository_root=repository_root,
            execution_mode=EXECUTION_MODE_SEALED,
            capability=capability,
        )
        result = _sealed_execution_result(validation, record=checkpoint)
        _atomic_write_json(
            root / RESULT_FILENAME,
            result,
            replace=False,
            temp_crash_point="after_result_temp_write",
        )
        _crash_injection_point("after_result_atomic_publish")
        result_checkpoint = dict(checkpoint)
        result_checkpoint["execution_result_digest"] = result["result_sha256"]
        result_checkpoint["authorization_record_sha256"] = _authorization_digest(
            result_checkpoint
        )
        _write_execution_authorization(root, result_checkpoint)
        _crash_injection_point("after_result_digest_persisted_before_finalized")

        finalized = _transition(
            result_checkpoint,
            to_state=STATE_FINALIZED,
            step=TRANSITION_FINALIZE,
        )
        _write_execution_authorization(root, finalized)
        _crash_injection_point("after_finalized")
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


RECOVERY_INTERRUPTED_NO_RESULT = "EXECUTION_INTERRUPTED_NO_RESULT"
RECOVERY_FINALIZED_EXISTING_RESULT = "FINALIZED_EXISTING_DURABLE_RESULT"
RECOVERY_ALREADY_FINALIZED = "ALREADY_FINALIZED_READ_ONLY"


def _verify_persisted_result(
    repository_root: Path,
    execution_root: Path,
    *,
    record: Mapping[str, Any],
) -> dict[str, Any]:
    """Cross-check persisted evidence/result without opening any raw artifact."""

    evidence = _read_evidence_artifact(execution_root, record=record)
    result = _read_result_artifact_shallow(execution_root, record=record)
    if result["candidate_evidence_digest"] != evidence["evidence_bundle_digest"]:
        raise SealedExecutionIntegrityError(
            f"{REFUSE_TO_RUN}: result and evidence digests disagree"
        )
    consumed_record = dict(record)
    consumed_record["status"] = STATE_EXECUTION_STARTED
    consumed_record["state_history"] = [
        dict(row) for row in STATE_HISTORY_CONTRACT[STATE_EXECUTION_STARTED]
    ]
    capability = _consumed_capability(consumed_record)
    validation = _validate_v3_candidate_core(
        evidence["evidence_bundle"],
        repository_root=repository_root,
        execution_mode=EXECUTION_MODE_SEALED,
        capability=capability,
    )
    expected = _sealed_execution_result(validation, record=consumed_record)
    if _canonical_json(result) != _canonical_json(expected):
        raise SealedExecutionIntegrityError(
            f"{REFUSE_TO_RUN}: persisted result semantics do not reproduce from "
            "the immutable evidence artifact"
        )
    return result


def read_finalized_result(
    repository_root: Path, *, execution_root: Path
) -> dict[str, Any]:
    """Read-only verified restore of one FINALIZED scientific result."""

    digest = validator_definition_sha256(repository_root)
    with _exclusive_executor_lock(execution_root) as root:
        record = read_execution_authorization(
            root, validator_definition_sha256=digest
        )
        if record["status"] != STATE_FINALIZED:
            raise SealedExecutionStateError(
                f"{REFUSE_TO_RUN}: finalized restore requires FINALIZED, not "
                f"{record['status']}"
            )
        result = _verify_persisted_result(
            repository_root, root, record=record
        )
        if result["result_sha256"] != record["execution_result_digest"]:
            raise SealedExecutionIntegrityError(
                f"{REFUSE_TO_RUN}: authorization result digest does not match result"
            )
        return result


def recover_sealed_execution(
    repository_root: Path, *, execution_root: Path
) -> dict[str, Any]:
    """Recover only durable artifacts; never reopen raw files or rerun a builder."""

    digest = validator_definition_sha256(repository_root)
    with _exclusive_executor_lock(execution_root) as root:
        record = read_execution_authorization(
            root, validator_definition_sha256=digest
        )
        if record["status"] == STATE_FINALIZED:
            result = _verify_persisted_result(
                repository_root, root, record=record
            )
            return {
                "operational_state": RECOVERY_ALREADY_FINALIZED,
                "result": result,
            }
        if record["status"] != STATE_EXECUTION_STARTED:
            raise SealedExecutionStateError(
                f"{REFUSE_TO_RUN}: recovery requires consumed EXECUTION_STARTED "
                f"or FINALIZED, not {record['status']}"
            )
        result_path = root / RESULT_FILENAME
        if not result_path.exists():
            return {
                "evidence_artifact_present": (root / EVIDENCE_FILENAME).exists(),
                "execution_id": record["execution_id"],
                "normal_retry_permitted": False,
                "operational_state": RECOVERY_INTERRUPTED_NO_RESULT,
                "raw_reopen_permitted": False,
                "scientific_verdict": None,
            }
        if not (root / EVIDENCE_FILENAME).exists():
            raise SealedExecutionIntegrityError(
                f"{REFUSE_TO_RUN}: durable result exists without durable evidence"
            )
        result = _verify_persisted_result(
            repository_root, root, record=record
        )
        checkpoint = dict(record)
        checkpoint["evidence_bundle_digest"] = result["candidate_evidence_digest"]
        checkpoint["execution_result_digest"] = result["result_sha256"]
        checkpoint["authorization_record_sha256"] = _authorization_digest(checkpoint)
        _write_execution_authorization(root, checkpoint)
        finalized = _transition(
            checkpoint, to_state=STATE_FINALIZED, step=TRANSITION_FINALIZE
        )
        _write_execution_authorization(root, finalized)
        return {
            "normal_retry_permitted": False,
            "operational_state": RECOVERY_FINALIZED_EXISTING_RESULT,
            "raw_reopen_permitted": False,
            "result": result,
        }


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
    if control.get("evidence_builder_module") != SEALED_EVIDENCE_BUILDER_MODULE:
        raise ValidatorError("persisted contract names another evidence-builder module")
    if control.get("evidence_builder_function") != SEALED_EVIDENCE_BUILDER_FUNCTION:
        raise ValidatorError("persisted contract names another evidence-builder function")
    if control.get("evidence_builder_definition_sha256") != (
        SEALED_EVIDENCE_BUILDER_DEFINITION_SHA256
    ):
        raise ValidatorError("persisted contract binds another evidence builder")
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
        f"- Supersedes failed executor hash: `{PREVIOUS_EXECUTOR_DEFINITION_SHA256}`",
        f"- Failure review commit: `{PREVIOUS_EXECUTOR_REVIEW_COMMIT}`",
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
        "## Control-plane enforcement",
        "",
        f"- Cross-process lock: `{EXECUTOR_LOCK_FILENAME}` with `fcntl.flock(LOCK_EX)`",
        f"- Authority: `{AUTHORIZATION_FILENAME}` at the path-bound execution root",
        f"- Manifest: `{MANIFEST_FILENAME}` (canonical and durable)",
        f"- Evidence: `{EVIDENCE_FILENAME}` (immutable)",
        f"- Result: `{RESULT_FILENAME}` (immutable)",
        f"- Fixed evidence builder: `{SEALED_EVIDENCE_BUILDER_MODULE}.{SEALED_EVIDENCE_BUILDER_FUNCTION}`",
        f"- Builder version: `{SEALED_EVIDENCE_BUILDER_VERSION}`",
        f"- Builder definition hash: `{SEALED_EVIDENCE_BUILDER_DEFINITION_SHA256}`",
        "- Persistence: fsynced temporary file, atomic `os.replace`, directory fsync",
        "- Normal execute source state: `COLLECTED_FROZEN` only",
        "- `EXECUTION_STARTED`: permanently consumed; recovery never rereads raw data",
        "- Post-start manifest: schema/self-digest/bindings revalidated, then compared to authority",
        "",
        control["execution_root_policy"],
        "",
        control["recovery_rule"],
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
